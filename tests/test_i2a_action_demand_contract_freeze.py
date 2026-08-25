import copy
import json
import math
from dataclasses import dataclass
from pathlib import Path
from types import MappingProxyType
from typing import Mapping


ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
FIXTURE_PATH = ROOT / "evals" / "AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json"
PARENT_CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"


@dataclass(frozen=True)
class _ProjectionReceipt:
    required_attributes: tuple[str, ...]
    required_skills: tuple[str, ...]
    difficulty_or_resistance: int | float
    provenance: Mapping[str, str]


def _load(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def _mapping_keys(value, error):
    if not isinstance(value, dict):
        raise ValueError(error)
    keys = tuple(value.keys())
    if any(not _nonempty(key) for key in keys):
        raise ValueError(error)
    if len(keys) != len(set(keys)):
        raise ValueError("I2A_DUPLICATE_DEMAND_REFERENCE")
    return keys


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("I2A_DEMAND_DIFFICULTY_INVALID")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("I2A_DEMAND_DIFFICULTY_INVALID")
    return value


def _contract_gate_projection(demand, context):
    for field in ("demand_id", "action_family", "method_id", "ruleset_version"):
        if not _nonempty(demand.get(field)):
            raise ValueError("I2A_DEMAND_BINDING_MALFORMED")

    hard = demand.get("hard_prerequisites")
    if not isinstance(hard, list) or any(not _nonempty(ref) for ref in hard):
        raise ValueError("I2A_DEMAND_BINDING_MALFORMED")
    if len(hard) != len(set(hard)):
        raise ValueError("I2A_DUPLICATE_DEMAND_REFERENCE")

    required_attributes = _mapping_keys(
        demand.get("attribute_weights"), "I2A_REQUIRED_ATTRIBUTES_INVALID"
    )
    required_skills = _mapping_keys(
        demand.get("skill_weights"), "I2A_REQUIRED_SKILLS_INVALID"
    )
    if not required_attributes and not required_skills:
        raise ValueError("I2A_EMPTY_BOUNDED_DEMAND_REFERENCE_SET")

    prerequisite_ref = context.get("hard_prerequisite_receipt_ref")
    if hard:
        if not _nonempty(prerequisite_ref) or prerequisite_ref == "NOT_APPLICABLE":
            raise ValueError("I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED")
    elif prerequisite_ref != "NOT_APPLICABLE":
        raise ValueError("I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED")

    difficulty_binding = context.get("difficulty_binding")
    if not isinstance(difficulty_binding, dict):
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")
    for identity_field in ("demand_id", "action_family", "method_id", "ruleset_version"):
        if difficulty_binding.get(identity_field) != demand[identity_field]:
            raise ValueError("I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH")
    if not _nonempty(difficulty_binding.get("difficulty_source_ref")):
        raise ValueError("I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH")
    if "difficulty_or_resistance" not in difficulty_binding:
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")
    difficulty = _finite_number(difficulty_binding["difficulty_or_resistance"])

    source_demand_ref = context.get("source_demand_ref")
    replay_input_ref = context.get("replay_input_ref")
    if not _nonempty(source_demand_ref) or not _nonempty(replay_input_ref):
        raise ValueError("I2A_DEMAND_BINDING_MALFORMED")

    provenance = MappingProxyType(
        {
            "source_demand_ref": str(source_demand_ref),
            "demand_id": str(demand["demand_id"]),
            "action_family": str(demand["action_family"]),
            "method_id": str(demand["method_id"]),
            "ruleset_version": str(demand["ruleset_version"]),
            "difficulty_source_ref": str(difficulty_binding["difficulty_source_ref"]),
            "replay_input_ref": str(replay_input_ref),
            "hard_prerequisite_receipt_ref": str(prerequisite_ref),
        }
    )
    return _ProjectionReceipt(
        required_attributes=tuple(required_attributes),
        required_skills=tuple(required_skills),
        difficulty_or_resistance=difficulty,
        provenance=provenance,
    )


def _case_map():
    fixtures = _load(FIXTURE_PATH)
    return {case["case_id"]: case for case in fixtures["cases"]}


def _valid_context(case):
    context = copy.deepcopy(case.get("context", {}))
    context.setdefault("source_demand_ref", f"demand-ref:{case['demand']['demand_id']}")
    context.setdefault("replay_input_ref", f"replay:{case['case_id']}")
    if "hard_prerequisite_receipt_ref" not in context:
        context["hard_prerequisite_receipt_ref"] = (
            "feasibility:passed" if case["demand"].get("hard_prerequisites") else "NOT_APPLICABLE"
        )
    if "difficulty_binding" not in context:
        context["difficulty_binding"] = {
            "demand_id": case["demand"]["demand_id"],
            "action_family": case["demand"]["action_family"],
            "method_id": case["demand"]["method_id"],
            "ruleset_version": case["demand"]["ruleset_version"],
            "difficulty_source_ref": f"difficulty-binding:{case['demand']['demand_id']}",
            "difficulty_or_resistance": 1,
        }
    return context


def test_binding_is_exactly_parented_and_runtime_authority_remains_locked():
    binding = _load(BINDING_PATH)
    parent = _load(PARENT_CONTRACT_PATH)
    fixtures = _load(FIXTURE_PATH)

    assert binding["binding_version"] == "1.0.0-candidate"
    assert binding["parent_machine_contract"]["contract_id"] == parent["contract_id"]
    assert binding["parent_machine_contract"]["contract_version"] == parent["contract_version"] == "1.8.0-candidate"
    assert binding["parent_machine_contract"]["type_ref"] == "AF001.ActionDemandProfile"
    assert binding["parent_machine_contract"]["type_version"] == parent["type_registry"]["ActionDemandProfile"]["version"] == "1.0.0-candidate"
    assert fixtures["required_binding"]["binding_version"] == binding["binding_version"]
    assert fixtures["evaluation_scope"] == "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
    assert binding["runtime_implementation_authorized"] is False
    assert binding["authority_locks"] == {
        "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
        "NO_I2_RUNTIME_IMPLEMENTED": True,
        "RUNTIME_SEMANTICS_UNCHANGED": True,
    }


def test_binding_freezes_projection_without_authorizing_weight_semantics():
    binding = _load(BINDING_PATH)
    decisions = binding["canonical_decisions"]
    projection = binding["projection_schema"]

    assert decisions["resolver_projection_authorized"] is True
    assert decisions["projection_is_non_authoritative"] is True
    assert decisions["required_attributes_source"] == "ORDERED_KEYS_OF_ActionDemandProfile.attribute_weights_ONLY"
    assert decisions["required_skills_source"] == "ORDERED_KEYS_OF_ActionDemandProfile.skill_weights_ONLY"
    assert decisions["weight_values_consumed"] is False
    assert decisions["weight_semantics_status"] == "DEFERRED_RULESET_TUNING"
    assert decisions["difficulty_source"] == "CAPABILITY_STATE_RESOLUTION_VERSIONED_DEMAND_BINDING"
    assert projection["consumer_fields"] == [
        "required_attributes",
        "required_skills",
        "difficulty_or_resistance",
    ]
    deferred = set(binding["explicitly_deferred"])
    assert {"ATTRIBUTE_WEIGHT_VALUES", "SKILL_WEIGHT_VALUES", "DIFFICULTY_FORMULA", "PROBABILITY"} <= deferred


def test_golden_valid_projection_is_exact_and_weight_values_are_unconsumed():
    case = _case_map()["ADP-01-VALID-BOUNDED-PROJECTION"]
    receipt = _contract_gate_projection(copy.deepcopy(case["demand"]), copy.deepcopy(case["context"]))
    expected = case["expected"]

    assert receipt.required_attributes == tuple(expected["required_attributes"])
    assert receipt.required_skills == tuple(expected["required_skills"])
    assert receipt.difficulty_or_resistance == expected["difficulty_or_resistance"]

    mutated_weights = copy.deepcopy(case["demand"])
    mutated_weights["attribute_weights"]["strength"] = -10**100
    mutated_weights["attribute_weights"]["agility"] = "opaque-deferred-weight"
    mutated_weights["skill_weights"]["climb"] = None
    second = _contract_gate_projection(mutated_weights, copy.deepcopy(case["context"]))
    assert second == receipt


def test_malformed_and_empty_reference_shapes_fail_closed():
    cases = _case_map()
    for case_id in (
        "ADP-02-MALFORMED-ATTRIBUTE-REFERENCE",
        "ADP-03-MALFORMED-SKILL-REFERENCE",
        "ADP-04-EMPTY-BOUNDED-REFERENCE-SET",
    ):
        case = copy.deepcopy(cases[case_id])
        try:
            _contract_gate_projection(case["demand"], _valid_context(case))
        except ValueError as exc:
            assert str(exc) == case["expected_error"]
        else:
            raise AssertionError(f"{case_id} unexpectedly accepted")

    duplicate_pair_shape = copy.deepcopy(cases["ADP-01-VALID-BOUNDED-PROJECTION"])
    duplicate_pair_shape["demand"]["attribute_weights"] = [["strength", 1], ["strength", 2]]
    try:
        _contract_gate_projection(duplicate_pair_shape["demand"], duplicate_pair_shape["context"])
    except ValueError as exc:
        assert str(exc) == "I2A_REQUIRED_ATTRIBUTES_INVALID"
    else:
        raise AssertionError("non-mapping duplicate representation unexpectedly accepted")


def test_hard_prerequisite_and_difficulty_authority_fail_closed():
    cases = _case_map()
    for case_id in (
        "ADP-05-HARD-PREREQUISITE-UNATTESTED",
        "ADP-06-DIFFICULTY-BINDING-MISMATCH",
    ):
        case = copy.deepcopy(cases[case_id])
        context = _valid_context(case)
        context.update(case.get("context", {}))
        try:
            _contract_gate_projection(case["demand"], context)
        except ValueError as exc:
            assert str(exc) == case["expected_error"]
        else:
            raise AssertionError(f"{case_id} unexpectedly accepted")


def test_difficulty_numeric_semantics_are_total_and_fail_closed():
    case = copy.deepcopy(_case_map()["ADP-01-VALID-BOUNDED-PROJECTION"])
    for invalid in (True, "7", None, math.nan, math.inf, -math.inf):
        context = copy.deepcopy(case["context"])
        context["difficulty_binding"]["difficulty_or_resistance"] = invalid
        try:
            _contract_gate_projection(copy.deepcopy(case["demand"]), context)
        except ValueError as exc:
            assert str(exc) == "I2A_DEMAND_DIFFICULTY_INVALID"
        else:
            raise AssertionError(f"invalid difficulty {invalid!r} unexpectedly accepted")

    huge = _case_map()["ADP-07-HUGE-INTEGER-DIFFICULTY-TOTAL"]
    receipt = _contract_gate_projection(copy.deepcopy(huge["demand"]), copy.deepcopy(huge["context"]))
    assert receipt.difficulty_or_resistance == huge["expected"]["difficulty_or_resistance"]


def test_projection_is_deterministic_mutation_isolated_and_scoped_to_references():
    case = copy.deepcopy(_case_map()["ADP-01-VALID-BOUNDED-PROJECTION"])
    first = _contract_gate_projection(copy.deepcopy(case["demand"]), copy.deepcopy(case["context"]))
    second = _contract_gate_projection(copy.deepcopy(case["demand"]), copy.deepcopy(case["context"]))
    assert first == second

    source = copy.deepcopy(case["demand"])
    receipt = _contract_gate_projection(source, copy.deepcopy(case["context"]))
    source["attribute_weights"].clear()
    source["skill_weights"]["unrelated"] = 999999
    source["demand_id"] = "caller-mutated"
    assert receipt == first

    capability_envelope = {
        "validated_actor_base_attributes": {"strength": 3, "agility": 4, "charisma": 10**9},
        "validated_skill_ledger_values": {"climb": 5, "poetry": 10**9},
    }
    selected_attributes = {
        key: capability_envelope["validated_actor_base_attributes"][key]
        for key in receipt.required_attributes
    }
    selected_skills = {
        key: capability_envelope["validated_skill_ledger_values"][key]
        for key in receipt.required_skills
    }
    assert selected_attributes == {"strength": 3, "agility": 4}
    assert selected_skills == {"climb": 5}
    assert "charisma" not in selected_attributes
    assert "poetry" not in selected_skills

    try:
        receipt.provenance["ruleset_version"] = "caller-overwrite"
    except TypeError:
        pass
    else:
        raise AssertionError("projection provenance unexpectedly mutable")
