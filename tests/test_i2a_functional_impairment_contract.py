import copy
import json
from pathlib import Path
from types import MappingProxyType
from collections.abc import Mapping

import pytest


ROOT = Path(__file__).resolve().parents[1]
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING_PATH = ROOT / "contracts" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"
ACTION_DEMAND_BINDING_PATH = ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
FIXTURES_PATH = ROOT / "evals" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-FIXTURES.json"

EXPECTED_LOCKS = {
    "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
    "NO_I2_RUNTIME_IMPLEMENTED": True,
    "RUNTIME_SEMANTICS_UNCHANGED": True,
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cases():
    return {case["case_id"]: case for case in _load(FIXTURES_PATH)["cases"]}


def _nonempty(value, error):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _validate_authority(parent, binding):
    error = "I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID"
    binding_id = binding.get("binding_id")
    registrations = parent.get("registered_contract_extensions")
    if not isinstance(registrations, Mapping):
        raise ValueError(error)
    registration = registrations.get(binding_id)
    if not isinstance(registration, Mapping):
        raise ValueError(error)
    if (
        parent.get("contract_id") != "AWRSE-AF001-LIVING-STORY-CONTRACTS"
        or parent.get("contract_version") != binding.get("parent_machine_contract", {}).get("contract_version")
        or binding.get("parent_machine_contract", {}).get("contract_id") != parent.get("contract_id")
        or binding.get("parent_machine_contract", {}).get("path") != "contracts/AF001-LIVING-STORY-CONTRACTS.json"
        or registration.get("path") != "contracts/AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"
        or registration.get("binding_version") != binding.get("binding_version")
        or registration.get("parent_contract_id") != parent.get("contract_id")
        or registration.get("parent_contract_version") != parent.get("contract_version")
        or registration.get("authority") != "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        or registration.get("runtime_implementation_authorized") is not False
        or binding.get("runtime_implementation_authorized") is not False
        or binding.get("authority_locks") != EXPECTED_LOCKS
    ):
        raise ValueError(error)

    lineage = parent.get("versioning_and_migration", {}).get("contract_version_lineage")
    if not isinstance(lineage, Mapping):
        raise ValueError(error)
    delta = lineage.get("semantic_delta")
    if (
        lineage.get("previous_contract_version") != "1.9.0-candidate"
        or parent.get("contract_version") != "1.10.0-candidate"
        or not isinstance(delta, list)
        or "FUNCTIONAL_IMPAIRMENT_CAPABILITY_BINDING_CANONICAL_EXTENSION_REGISTRATION" not in delta
        or "ACTION_DEMAND_PROJECTION_BINDING_CANONICAL_EXTENSION_REGISTRATION" not in delta
    ):
        raise ValueError(error)


def _validate_source_type_bindings(parent, binding):
    error = "I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH"
    registry = parent.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError(error)
    for type_name, frozen in binding["source_type_bindings"].items():
        actual = registry.get(type_name)
        if not isinstance(actual, Mapping):
            raise ValueError(error)
        if actual.get("type_id") != frozen.get("type_id") or actual.get("version") != frozen.get("version"):
            raise ValueError(error)


def _materialize(case, *, numeric_override=None):
    binding = _load(BINDING_PATH)
    if numeric_override is not None:
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_NUMERIC_OVERRIDE_NOT_AUTHORIZED")

    actor_id = _nonempty(case.get("actor_id"), "I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH")
    source_demand_ref = _nonempty(case.get("source_demand_ref"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
    replay_input_ref = _nonempty(case.get("replay_input_ref"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
    demand = case.get("demand")
    if not isinstance(demand, Mapping):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
    demand_id = _nonempty(demand.get("demand_id"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
    ruleset_version = _nonempty(demand.get("ruleset_version"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
    required = demand.get("required_body_functions")
    if not isinstance(required, list):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID")
    if any(not isinstance(ref, str) or not ref.strip() for ref in required):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID")
    required = tuple(sorted(required))

    sources = case.get("injury_sources")
    if not isinstance(sources, list):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")

    expected_injury_version = binding["source_type_bindings"]["InjuryState"]["version"]
    seen_impairment_refs = set()
    source_injury_refs = []
    source_event_refs = []
    applicable = {}

    for source in sources:
        if not isinstance(source, Mapping):
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        if source.get("source_type") != "InjuryState":
            if source.get("source_type") in {"DressingState", "ActorPresentationState", "ActorPresentationRequirements"}:
                raise ValueError("I2A_PRESENTATION_CANNOT_AUTHOR_FUNCTIONAL_IMPAIRMENT")
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        if source.get("source_type_version") != expected_injury_version:
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH")
        if source.get("actor_id") != actor_id:
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH")

        injury_id = _nonempty(source.get("injury_id"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        event_ref = _nonempty(source.get("source_event_ref"), "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        source_injury_refs.append(injury_id)
        source_event_refs.append(event_ref)

        impairments = source.get("functional_impairments")
        if not isinstance(impairments, list):
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        for impairment in impairments:
            if not isinstance(impairment, Mapping):
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
            extras = set(impairment) - {"impairment_ref", "function_ref"}
            if extras & {"penalty", "coefficient", "multiplier", "numeric_effect"}:
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_NUMERIC_OVERRIDE_NOT_AUTHORIZED")
            if extras:
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
            impairment_ref = _nonempty(
                impairment.get("impairment_ref"),
                "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED",
            )
            function_ref = _nonempty(
                impairment.get("function_ref"),
                "I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID",
            )
            if impairment_ref in seen_impairment_refs:
                raise ValueError("I2A_DUPLICATE_FUNCTIONAL_IMPAIRMENT_REFERENCE")
            seen_impairment_refs.add(impairment_ref)
            if function_ref in required:
                applicable.setdefault(function_ref, []).append(impairment_ref)

    frozen_applicable = MappingProxyType(
        {key: tuple(sorted(values)) for key, values in sorted(applicable.items())}
    )
    return MappingProxyType(
        {
            "actor_id": actor_id,
            "demand_id": demand_id,
            "ruleset_version": ruleset_version,
            "required_body_functions": required,
            "applicable_impairment_refs_by_function": frozen_applicable,
            "source_injury_refs": tuple(sorted(source_injury_refs)),
            "source_event_refs": tuple(sorted(source_event_refs)),
            "source_demand_ref": source_demand_ref,
            "replay_input_ref": replay_input_ref,
            "numeric_effect_status": "DEFERRED_RULESET_TUNING",
        }
    )


def _logical_projection(projection):
    return {
        "required_body_functions": list(projection["required_body_functions"]),
        "applicable_impairment_refs_by_function": {
            key: list(value)
            for key, value in projection["applicable_impairment_refs_by_function"].items()
        },
        "source_injury_refs": list(projection["source_injury_refs"]),
        "source_event_refs": list(projection["source_event_refs"]),
        "numeric_effect_status": projection["numeric_effect_status"],
    }


def test_parent_registers_functional_impairment_binding_and_preserves_action_demand_extension():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    action_binding = _load(ACTION_DEMAND_BINDING_PATH)
    _validate_authority(parent, binding)
    _validate_source_type_bindings(parent, binding)

    action_registration = parent["registered_contract_extensions"][action_binding["binding_id"]]
    assert action_registration["parent_contract_version"] == "1.10.0-candidate"
    assert action_binding["parent_machine_contract"]["contract_version"] == "1.10.0-candidate"
    assert parent["contract_version"] == "1.10.0-candidate"


def test_orphan_and_pre_registration_parent_cannot_authorize_new_binding():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)

    orphan = copy.deepcopy(parent)
    orphan["registered_contract_extensions"].pop(binding["binding_id"])
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID$"):
        _validate_authority(orphan, binding)

    old_parent = copy.deepcopy(parent)
    old_binding = copy.deepcopy(binding)
    old_parent["contract_version"] = "1.9.0-candidate"
    old_parent["registered_contract_extensions"][binding["binding_id"]]["parent_contract_version"] = "1.9.0-candidate"
    old_binding["parent_machine_contract"]["contract_version"] = "1.9.0-candidate"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID$"):
        _validate_authority(old_parent, old_binding)


def test_source_type_versions_are_exact_and_fail_closed_when_mismatched():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    broken = copy.deepcopy(parent)
    broken["type_registry"]["InjuryState"]["version"] = "0.9.0-candidate"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH$"):
        _validate_source_type_bindings(broken, binding)


def test_relevant_right_grip_impairment_is_structurally_projected_without_numeric_effect():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    projection = _materialize(copy.deepcopy(case))
    assert _logical_projection(projection) == case["expected"]
    assert "severity" not in projection
    assert "penalty" not in projection


def test_same_impairment_and_lower_limb_have_zero_effect_on_unrelated_functions():
    for case_id in (
        "FIC-02-SAME-INJURY-UNRELATED-REASONING-ZERO-EFFECT",
        "FIC-03-LOWER-LIMB-CANNOT-SPREAD",
        "FIC-04-EMPTY-IMPAIRMENT-EVIDENCE-ZERO-EFFECT",
    ):
        case = _cases()[case_id]
        projection = _materialize(copy.deepcopy(case))
        assert _logical_projection(projection) == case["expected"]
        assert dict(projection["applicable_impairment_refs_by_function"]) == {}


def test_base_profile_and_skill_ledger_are_not_mutated_by_structural_projection():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    profile_before = copy.deepcopy(case["actor_base_profile"])
    skills_before = copy.deepcopy(case["skill_ledger"])
    _materialize(case)
    assert case["actor_base_profile"] == profile_before
    assert case["skill_ledger"] == skills_before


@pytest.mark.parametrize(
    "case_id",
    [
        "FIC-05-DUPLICATE-IMPAIRMENT-REF-FAILS-CLOSED",
        "FIC-06-BLANK-FUNCTION-REF-FAILS-CLOSED",
        "FIC-07-DRESSING-CANNOT-AUTHOR-IMPAIRMENT",
        "FIC-08-CALLER-NUMERIC-OVERRIDE-NOT-AUTHORIZED",
    ],
)
def test_invalid_or_unauthorized_evidence_fails_closed(case_id):
    case = _cases()[case_id]
    with pytest.raises(ValueError, match=f"^{case['expected_error']}$"):
        _materialize(copy.deepcopy(case))


def test_explicit_caller_numeric_override_is_not_authorized():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_NUMERIC_OVERRIDE_NOT_AUTHORIZED$"):
        _materialize(copy.deepcopy(case), numeric_override=-0.5)


def test_blank_required_function_ref_and_actor_mismatch_fail_closed():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = [""]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID$"):
        _materialize(case)

    mismatch = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    mismatch["injury_sources"][0]["actor_id"] = "ACTOR-OTHER"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH$"):
        _materialize(mismatch)


def test_insertion_order_is_canonical_and_caller_mutation_cannot_change_projection():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = [
        "cognition.reasoning@1",
        "body.upper_limb.right.grip@1",
    ]
    case["injury_sources"][0]["functional_impairments"] = [
        {"function_ref": "cognition.reasoning@1", "impairment_ref": "IMPAIR-REASONING-002"},
        {"impairment_ref": "IMPAIR-RIGHT-GRIP-001", "function_ref": "body.upper_limb.right.grip@1"},
    ]
    first = _materialize(case)

    reordered = copy.deepcopy(case)
    reordered["demand"]["required_body_functions"].reverse()
    reordered["injury_sources"][0]["functional_impairments"].reverse()
    second = _materialize(reordered)
    assert _logical_projection(first) == _logical_projection(second)

    before = _logical_projection(first)
    case["demand"]["required_body_functions"].clear()
    case["injury_sources"][0]["functional_impairments"].clear()
    assert _logical_projection(first) == before
    with pytest.raises(TypeError):
        first["numeric_effect_status"] = "caller-write"
    with pytest.raises(TypeError):
        first["applicable_impairment_refs_by_function"]["new"] = ("forged",)


def test_empty_required_body_functions_is_valid_zero_effect():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = []
    projection = _materialize(case)
    assert projection["required_body_functions"] == ()
    assert dict(projection["applicable_impairment_refs_by_function"]) == {}


def test_numeric_stacking_recovery_and_gameplay_authority_remain_deferred():
    binding = _load(BINDING_PATH)
    decisions = binding["canonical_decisions"]
    assert decisions["numeric_effect_status"] == "DEFERRED_RULESET_TUNING"
    assert decisions["numeric_application_authorized"] is False
    assert decisions["severity_consumed_for_numeric_effect"] is False
    assert decisions["caller_penalty_or_coefficient_consumed"] is False
    assert decisions["capability_dependency_binding_status"] == "NOT_YET_CANONICALLY_DEFINED"
    assert decisions["stacking_semantics_status"] == "DEFERRED_RULESET_TUNING"
    assert decisions["recovery_semantics_status"] == "DEFERRED_RULESET_TUNING"
    assert binding["runtime_implementation_authorized"] is False
    assert binding["authority_locks"] == EXPECTED_LOCKS
    assert "COMBAT" in binding["explicitly_deferred"]
    assert "PROBABILITY_OR_STOCHASTIC_OUTCOME" in binding["explicitly_deferred"]
    assert "PERSISTENCE_BACKEND" in binding["explicitly_deferred"]
