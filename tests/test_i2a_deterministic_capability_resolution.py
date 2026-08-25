import pytest

from runtime.awrse.capability_resolution import resolve_capability


PROVENANCE = {
    "profile_schema_ref": "AF-C-v1.1",
    "ruleset_family_ref": "SMALL_CORE_V1",
    "replay_input_ref": "replay-001",
}


def test_i2a_resolution_replays_same_canonical_inputs():
    envelope = {
        "validated_actor_base_attributes": {"strength": 5},
        "validated_skill_ledger_values": {"climb": 3},
    }
    demand = {
        "required_attributes": ("strength",),
        "required_skills": ("climb",),
        "difficulty_or_resistance": 6,
    }

    first = resolve_capability(
        capability_envelope=envelope,
        action_demand_profile=demand,
        provenance=PROVENANCE,
    )
    second = resolve_capability(
        capability_envelope=envelope,
        action_demand_profile=demand,
        provenance=PROVENANCE,
    )

    assert first.effective_capability == second.effective_capability == 8
    assert first.margin == second.margin == 2


def test_i2a_rejects_unprovenance_bound_capability_maps():
    with pytest.raises(ValueError, match="I2A_VALIDATED_CAPABILITY_INPUT_REQUIRED"):
        resolve_capability(
            capability_envelope={
                "base_attribute_map": {"strength": 99},
                "skill_values": {"climb": 99},
            },
            action_demand_profile={"difficulty_or_resistance": 1},
            provenance=PROVENANCE,
        )


def test_i2a_hard_feasibility_precedes_margin():
    result = resolve_capability(
        capability_envelope={
            "validated_actor_base_attributes": {},
            "validated_skill_ledger_values": {"climb": 100},
        },
        action_demand_profile={
            "required_attributes": ("strength",),
            "difficulty_or_resistance": 1,
        },
        provenance=PROVENANCE,
    )

    assert result.feasible is False
    assert result.effective_capability is None
    assert result.margin is None
