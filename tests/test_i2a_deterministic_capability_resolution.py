import math

import pytest

from runtime.awrse.capability_resolution import resolve_capability


PROVENANCE = {
    "profile_schema_ref": "AF-C-v1.1",
    "ruleset_family_ref": "SMALL_CORE_V1",
    "replay_input_ref": "replay-001",
}


def _envelope(attributes=None, skills=None):
    return {
        "validated_actor_base_attributes": attributes or {},
        "validated_skill_ledger_values": skills or {},
    }


def _demand(attributes=(), skills=(), difficulty=6):
    return {
        "required_attributes": attributes,
        "required_skills": skills,
        "difficulty_or_resistance": difficulty,
    }


def test_i2a_resolution_replays_same_canonical_inputs():
    envelope = _envelope({"strength": 5}, {"climb": 3})
    demand = _demand(("strength",), ("climb",), 6)
    first = resolve_capability(capability_envelope=envelope, action_demand_profile=demand, provenance=PROVENANCE)
    second = resolve_capability(capability_envelope=envelope, action_demand_profile=demand, provenance=PROVENANCE)
    assert first == second
    assert first.effective_capability == 8
    assert first.margin == 2


def test_i2a_unrelated_validated_attribute_does_not_affect_result():
    result = resolve_capability(
        capability_envelope=_envelope({"strength": 5, "poetry": 1000}, {"climb": 3}),
        action_demand_profile=_demand(("strength",), ("climb",), 6),
        provenance=PROVENANCE,
    )
    assert result.effective_capability == 8
    assert result.margin == 2


def test_i2a_unrelated_validated_skill_does_not_affect_result():
    result = resolve_capability(
        capability_envelope=_envelope({"strength": 5}, {"climb": 3, "poetry": 1000}),
        action_demand_profile=_demand(("strength",), ("climb",), 6),
        provenance=PROVENANCE,
    )
    assert result.effective_capability == 8
    assert result.margin == 2


@pytest.mark.parametrize(
    ("attributes", "skills", "required_attributes", "required_skills"),
    [({}, {"climb": 100}, ("strength",), ()), ({"strength": 100}, {}, (), ("climb",))],
)
def test_i2a_missing_required_key_fails_feasibility_before_margin(
    attributes, skills, required_attributes, required_skills
):
    result = resolve_capability(
        capability_envelope=_envelope(attributes, skills),
        action_demand_profile=_demand(required_attributes, required_skills, 1),
        provenance=PROVENANCE,
    )
    assert result.feasible is False
    assert result.effective_capability is None
    assert result.margin is None


@pytest.mark.parametrize("value", ["strength", {"strength"}, 1, None, ("",), (1,)])
def test_i2a_malformed_required_attributes_fail_closed(value):
    with pytest.raises(ValueError, match="I2A_REQUIRED_ATTRIBUTES_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 5}, {"climb": 3}),
            action_demand_profile=_demand(value, ("climb",), 6),
            provenance=PROVENANCE,
        )


@pytest.mark.parametrize("value", ["climb", {"climb"}, 1, None, ("",), (1,)])
def test_i2a_malformed_required_skills_fail_closed(value):
    with pytest.raises(ValueError, match="I2A_REQUIRED_SKILLS_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 5}, {"climb": 3}),
            action_demand_profile=_demand(("strength",), value, 6),
            provenance=PROVENANCE,
        )


@pytest.mark.parametrize(
    ("required_attributes", "required_skills"),
    [(("strength", "strength"), ("climb",)), (("strength",), ("climb", "climb"))],
)
def test_i2a_duplicate_demand_references_fail_closed(required_attributes, required_skills):
    with pytest.raises(ValueError, match="I2A_DUPLICATE_DEMAND_REFERENCE"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 5}, {"climb": 3}),
            action_demand_profile=_demand(required_attributes, required_skills, 6),
            provenance=PROVENANCE,
        )


def test_i2a_very_large_finite_integer_capability_is_supported():
    capability = 10**1000
    result = resolve_capability(
        capability_envelope=_envelope({"strength": capability}, {}),
        action_demand_profile=_demand(("strength",), (), 1),
        provenance=PROVENANCE,
    )
    assert result.effective_capability == capability
    assert result.margin == capability - 1


def test_i2a_very_large_finite_integer_difficulty_is_supported():
    difficulty = 10**1000
    result = resolve_capability(
        capability_envelope=_envelope({"strength": difficulty + 5}, {}),
        action_demand_profile=_demand(("strength",), (), difficulty),
        provenance=PROVENANCE,
    )
    assert result.effective_capability == difficulty + 5
    assert result.margin == 5


def test_i2a_mixed_huge_integer_and_float_arithmetic_fails_closed():
    with pytest.raises(ValueError, match="I2A_CAPABILITY_ARITHMETIC_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 10**1000}, {"climb": 1.0}),
            action_demand_profile=_demand(("strength",), ("climb",), 1),
            provenance=PROVENANCE,
        )


def test_i2a_finite_float_inputs_cannot_produce_nonfinite_effective_capability():
    with pytest.raises(ValueError, match="I2A_CAPABILITY_ARITHMETIC_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 1e308}, {"climb": 1e308}),
            action_demand_profile=_demand(("strength",), ("climb",), 0.0),
            provenance=PROVENANCE,
        )


@pytest.mark.parametrize("value", [True, "5", math.nan, math.inf, -math.inf])
def test_i2a_invalid_required_capability_value_rejected(value):
    with pytest.raises(ValueError, match="I2A_CAPABILITY_VALUE_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": value}, {"climb": 3}),
            action_demand_profile=_demand(("strength",), ("climb",), 6),
            provenance=PROVENANCE,
        )


@pytest.mark.parametrize("difficulty", [True, "6", math.nan, math.inf, -math.inf])
def test_i2a_invalid_difficulty_rejected(difficulty):
    with pytest.raises(ValueError, match="I2A_DEMAND_DIFFICULTY_INVALID"):
        resolve_capability(
            capability_envelope=_envelope({"strength": 5}, {"climb": 3}),
            action_demand_profile=_demand(("strength",), ("climb",), difficulty),
            provenance=PROVENANCE,
        )


def test_i2a_rejects_unprovenance_bound_capability_maps():
    with pytest.raises(ValueError, match="I2A_VALIDATED_CAPABILITY_INPUT_REQUIRED"):
        resolve_capability(
            capability_envelope={"base_attribute_map": {"strength": 99}, "skill_values": {"climb": 99}},
            action_demand_profile=_demand((), (), 1),
            provenance=PROVENANCE,
        )
