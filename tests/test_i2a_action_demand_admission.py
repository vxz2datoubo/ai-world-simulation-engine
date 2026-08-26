import copy
import json
import math
from pathlib import Path

import pytest

from runtime.awrse.actor_profile_admission import admit_actor_base_profile
import runtime.awrse.action_demand_admission as demand_module
from runtime.awrse.action_demand_admission import admit_action_demand
from runtime.awrse.capability_resolution import resolve_capability
from runtime.awrse.skill_ledger_admission import admit_skill_ledger


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "evals" / "AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json"
CONTRACT = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING = ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"


def _cases():
    data = json.loads(FIXTURES.read_text(encoding="utf-8"))
    return {case["case_id"]: case for case in data["cases"]}


def _context_for(case):
    demand = case["demand"]
    context = {
        "source_demand_ref": f"demand-ref:{demand.get('demand_id', 'unknown')}",
        "replay_input_ref": f"replay:{case['case_id']}",
        "hard_prerequisite_receipt_ref": (
            "feasibility:passed" if demand.get("hard_prerequisites") else "NOT_APPLICABLE"
        ),
        "difficulty_binding": {
            "demand_id": demand.get("demand_id"),
            "action_family": demand.get("action_family"),
            "method_id": demand.get("method_id"),
            "ruleset_version": demand.get("ruleset_version"),
            "difficulty_source_ref": f"difficulty-binding:{demand.get('demand_id', 'unknown')}",
            "difficulty_or_resistance": 1,
        },
    }
    context.update(copy.deepcopy(case.get("context", {})))
    return context


def _admit_case(case):
    context = _context_for(case)
    return admit_action_demand(
        copy.deepcopy(case["demand"]),
        source_demand_ref=context["source_demand_ref"],
        hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
        replay_input_ref=context["replay_input_ref"],
        difficulty_binding=context["difficulty_binding"],
    )


def test_adp_01_valid_projection_admits_with_exact_canonical_authority():
    case = _cases()["ADP-01-VALID-BOUNDED-PROJECTION"]
    receipt = _admit_case(case)

    assert receipt.demand_id == case["demand"]["demand_id"]
    assert receipt.action_family == case["demand"]["action_family"]
    assert receipt.method_id == case["demand"]["method_id"]
    assert receipt.ruleset_version == case["demand"]["ruleset_version"]
    assert receipt.hard_prerequisites == tuple(case["demand"]["hard_prerequisites"])
    assert receipt.required_attributes == tuple(case["expected"]["required_attributes"])
    assert receipt.required_skills == tuple(case["expected"]["required_skills"])
    assert receipt.difficulty_or_resistance == case["expected"]["difficulty_or_resistance"]
    assert dict(receipt.resolver_projection) == {
        "required_attributes": ("agility", "strength"),
        "required_skills": ("climb",),
        "difficulty_or_resistance": 7,
    }
    assert receipt.canonical_contract_id == "AWRSE-AF001-LIVING-STORY-CONTRACTS"
    assert receipt.canonical_contract_version == "1.9.0-candidate"
    assert receipt.binding_id == "AWRSE-AF001-ACTION-DEMAND-PROJECTION-BINDING"
    assert receipt.binding_version == "1.0.0-candidate"


@pytest.mark.parametrize(
    ("case_id", "error"),
    [
        ("ADP-02-MALFORMED-ATTRIBUTE-REFERENCE", "I2A_REQUIRED_ATTRIBUTES_INVALID"),
        ("ADP-03-MALFORMED-SKILL-REFERENCE", "I2A_REQUIRED_SKILLS_INVALID"),
        ("ADP-04-EMPTY-BOUNDED-REFERENCE-SET", "I2A_EMPTY_BOUNDED_DEMAND_REFERENCE_SET"),
        ("ADP-05-HARD-PREREQUISITE-UNATTESTED", "I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED"),
        ("ADP-06-DIFFICULTY-BINDING-MISMATCH", "I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH"),
    ],
)
def test_canonical_invalid_fixtures_fail_closed(case_id, error):
    with pytest.raises(ValueError, match=f"^{error}$"):
        _admit_case(_cases()[case_id])


def test_adp_07_huge_python_integer_difficulty_is_total():
    case = _cases()["ADP-07-HUGE-INTEGER-DIFFICULTY-TOTAL"]
    receipt = _admit_case(case)
    assert receipt.difficulty_or_resistance == case["expected"]["difficulty_or_resistance"]
    assert isinstance(receipt.difficulty_or_resistance, int)


@pytest.mark.parametrize("invalid", [True, "7", None, math.nan, math.inf, -math.inf])
def test_invalid_difficulty_numeric_shapes_fail_closed(invalid):
    case = copy.deepcopy(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])
    context = _context_for(case)
    context["difficulty_binding"]["difficulty_or_resistance"] = invalid
    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_INVALID$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=context["difficulty_binding"],
        )


def test_weight_values_are_opaque_unconsumed_and_order_is_canonical():
    case = copy.deepcopy(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])
    baseline = _admit_case(case)

    mutated = copy.deepcopy(case)
    mutated["demand"]["attribute_weights"] = {
        "strength": object(),
        "agility": -(10**1000),
    }
    mutated["demand"]["skill_weights"] = {"climb": None}
    mutated["demand"]["difficulty_or_resistance"] = -999999999
    second = _admit_case(mutated)

    reordered = copy.deepcopy(case)
    reordered["demand"]["attribute_weights"] = {"agility": "opaque", "strength": 10**200}
    reordered["demand"]["skill_weights"] = {"climb": {"not": "consumed"}}
    third = _admit_case(reordered)

    assert second == baseline
    assert third == baseline
    assert second.required_attributes == ("agility", "strength")


def test_caller_mutation_cannot_change_admitted_receipt_or_provenance():
    case = copy.deepcopy(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])
    context = _context_for(case)
    demand = case["demand"]
    difficulty_binding = context["difficulty_binding"]
    receipt = admit_action_demand(
        demand,
        source_demand_ref=context["source_demand_ref"],
        hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
        replay_input_ref=context["replay_input_ref"],
        difficulty_binding=difficulty_binding,
    )
    before = copy.deepcopy(dict(receipt.resolver_projection))
    before_provenance = dict(receipt.provenance)

    demand["attribute_weights"].clear()
    demand["skill_weights"]["poetry"] = 10**100
    demand["hard_prerequisites"].clear()
    demand["demand_id"] = "caller-mutated"
    difficulty_binding["difficulty_or_resistance"] = -10**100
    difficulty_binding["difficulty_source_ref"] = "caller-mutated"

    assert dict(receipt.resolver_projection) == before
    assert dict(receipt.provenance) == before_provenance
    with pytest.raises(TypeError):
        receipt.provenance["ruleset_version"] = "overwrite"
    with pytest.raises(TypeError):
        receipt.resolver_projection["difficulty_or_resistance"] = 0


def test_identical_canonical_inputs_produce_equal_receipts():
    case = _cases()["ADP-01-VALID-BOUNDED-PROJECTION"]
    assert _admit_case(case) == _admit_case(copy.deepcopy(case))


def test_malformed_public_input_shapes_fail_closed():
    case = copy.deepcopy(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])
    context = _context_for(case)

    with pytest.raises(ValueError, match="^I2A_ACTION_DEMAND_PROFILE_REQUIRED$"):
        admit_action_demand(
            None,
            source_demand_ref="x",
            hard_prerequisite_receipt_ref="x",
            replay_input_ref="x",
            difficulty_binding={},
        )

    for field in ("demand_id", "action_family", "method_id", "ruleset_version"):
        broken = copy.deepcopy(case["demand"])
        broken[field] = ""
        with pytest.raises(ValueError, match="^I2A_DEMAND_BINDING_MALFORMED$"):
            admit_action_demand(
                broken,
                source_demand_ref=context["source_demand_ref"],
                hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
                replay_input_ref=context["replay_input_ref"],
                difficulty_binding=context["difficulty_binding"],
            )

    duplicate = copy.deepcopy(case["demand"])
    duplicate["hard_prerequisites"] = ["HAS_REACHABLE_SURFACE", "HAS_REACHABLE_SURFACE"]
    with pytest.raises(ValueError, match="^I2A_DUPLICATE_DEMAND_REFERENCE$"):
        admit_action_demand(
            duplicate,
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=context["difficulty_binding"],
        )

    bad_key = copy.deepcopy(case["demand"])
    bad_key["attribute_weights"] = {1: "opaque"}
    with pytest.raises(ValueError, match="^I2A_REQUIRED_ATTRIBUTES_INVALID$"):
        admit_action_demand(
            bad_key,
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=context["difficulty_binding"],
        )


@pytest.mark.parametrize("source_ref", [None, "", "   "])
def test_missing_source_demand_provenance_fails_closed(source_ref):
    case = _cases()["ADP-01-VALID-BOUNDED-PROJECTION"]
    context = _context_for(case)
    with pytest.raises(ValueError, match="^I2A_DEMAND_BINDING_MALFORMED$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=source_ref,
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=context["difficulty_binding"],
        )


@pytest.mark.parametrize("replay_ref", [None, "", "   "])
def test_missing_replay_provenance_fails_closed(replay_ref):
    case = _cases()["ADP-01-VALID-BOUNDED-PROJECTION"]
    context = _context_for(case)
    with pytest.raises(ValueError, match="^I2A_DEMAND_BINDING_MALFORMED$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=replay_ref,
            difficulty_binding=context["difficulty_binding"],
        )


def test_difficulty_binding_is_separate_exact_identity_authority():
    case = copy.deepcopy(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])
    context = _context_for(case)

    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_REQUIRED$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=None,
        )

    missing_value = copy.deepcopy(context["difficulty_binding"])
    missing_value.pop("difficulty_or_resistance")
    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_REQUIRED$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=missing_value,
        )

    blank_source = copy.deepcopy(context["difficulty_binding"])
    blank_source["difficulty_source_ref"] = ""
    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH$"):
        admit_action_demand(
            case["demand"],
            source_demand_ref=context["source_demand_ref"],
            hard_prerequisite_receipt_ref=context["hard_prerequisite_receipt_ref"],
            replay_input_ref=context["replay_input_ref"],
            difficulty_binding=blank_source,
        )


def _write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")


def test_orphan_self_declared_binding_is_not_canonical(monkeypatch, tmp_path):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    contract["registered_contract_extensions"].pop(binding["binding_id"])

    contract_path = tmp_path / "contract.json"
    binding_path = tmp_path / "binding.json"
    _write_json(contract_path, contract)
    _write_json(binding_path, binding)
    monkeypatch.setattr(demand_module, "_CANONICAL_CONTRACT_PATH", contract_path)
    monkeypatch.setattr(demand_module, "_PROJECTION_BINDING_PATH", binding_path)

    with pytest.raises(ValueError, match="^I2A_ACTION_DEMAND_CANONICAL_BINDING_INVALID$"):
        _admit_case(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])


def test_pre_registration_parent_version_cannot_authorize_new_binding(monkeypatch, tmp_path):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    contract["contract_version"] = "1.8.0-candidate"
    registration = contract["registered_contract_extensions"][binding["binding_id"]]
    registration["parent_contract_version"] = "1.8.0-candidate"
    binding["parent_machine_contract"]["contract_version"] = "1.8.0-candidate"

    contract_path = tmp_path / "contract.json"
    binding_path = tmp_path / "binding.json"
    _write_json(contract_path, contract)
    _write_json(binding_path, binding)
    monkeypatch.setattr(demand_module, "_CANONICAL_CONTRACT_PATH", contract_path)
    monkeypatch.setattr(demand_module, "_PROJECTION_BINDING_PATH", binding_path)

    with pytest.raises(ValueError, match="^I2A_ACTION_DEMAND_CANONICAL_BINDING_INVALID$"):
        _admit_case(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])


def test_binding_authority_lock_mutation_fails_closed(monkeypatch, tmp_path):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    binding = json.loads(BINDING.read_text(encoding="utf-8"))
    binding["runtime_implementation_authorized"] = True

    contract_path = tmp_path / "contract.json"
    binding_path = tmp_path / "binding.json"
    _write_json(contract_path, contract)
    _write_json(binding_path, binding)
    monkeypatch.setattr(demand_module, "_CANONICAL_CONTRACT_PATH", contract_path)
    monkeypatch.setattr(demand_module, "_PROJECTION_BINDING_PATH", binding_path)

    with pytest.raises(ValueError, match="^I2A_ACTION_DEMAND_CANONICAL_BINDING_INVALID$"):
        _admit_case(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])


def test_canonical_authority_unavailable_fails_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(demand_module, "_CANONICAL_CONTRACT_PATH", tmp_path / "missing-contract.json")
    with pytest.raises(ValueError, match="^I2A_ACTION_DEMAND_CANONICAL_CONTRACT_UNAVAILABLE$"):
        _admit_case(_cases()["ADP-01-VALID-BOUNDED-PROJECTION"])


def test_admitted_projection_integrates_with_existing_resolver_without_raw_demand_bypass():
    profile = admit_actor_base_profile(
        {
            "actor_id": "ACTOR-FIGHTER-001",
            "profile_version": "1.1.0-candidate",
            "profile_schema_ref": "PROFILE-SCHEMA-FAMILY-A@1",
            "ruleset_family_ref": "RULESET-FAMILY-A@1",
            "base_attribute_map": {"strength": 3, "agility": 4, "charisma": 10**9},
            "source_event_refs": ["E_PROFILE_FIGHTER_CREATED"],
        }
    )
    ledger = admit_skill_ledger(
        {
            "actor_id": "ACTOR-FIGHTER-001",
            "schema_version": "1.1.0-candidate",
            "source_event_cursor": "CURSOR-SKILL-FIGHTER-I2A007",
            "skill_entries": [
                {"skill_id": "climb", "value": 5, "source_event_refs": ["E_SKILL_CLIMB_TRAINED"]},
                {"skill_id": "poetry", "value": 10**9, "source_event_refs": ["E_SKILL_POETRY_TRAINED"]},
            ],
        },
        admitted_actor_profile=profile,
    )
    case = _cases()["ADP-01-VALID-BOUNDED-PROJECTION"]
    demand_receipt = _admit_case(case)

    provenance = {
        "profile_schema_ref": profile.profile_schema_ref,
        "ruleset_family_ref": profile.ruleset_family_ref,
        "replay_input_ref": demand_receipt.provenance["replay_input_ref"],
    }
    capability_envelope = {
        "validated_actor_base_attributes": profile.admitted_base_attribute_map,
        "validated_skill_ledger_values": ledger.validated_skill_ledger_values,
    }

    result = resolve_capability(
        capability_envelope=capability_envelope,
        action_demand_profile=demand_receipt.resolver_projection,
        provenance=provenance,
    )
    assert result.feasible is True
    assert result.effective_capability == 12
    assert result.margin == 5

    changed_unrelated = {
        "validated_actor_base_attributes": dict(profile.admitted_base_attribute_map, charisma=-(10**12)),
        "validated_skill_ledger_values": dict(ledger.validated_skill_ledger_values, poetry=-(10**12)),
    }
    second = resolve_capability(
        capability_envelope=changed_unrelated,
        action_demand_profile=demand_receipt.resolver_projection,
        provenance=provenance,
    )
    assert second == result

    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_REQUIRED$"):
        resolve_capability(
            capability_envelope=capability_envelope,
            action_demand_profile=case["demand"],
            provenance=provenance,
        )


def test_runtime_authority_locks_remain_explicitly_ungranted():
    assert demand_module.I2_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert demand_module.NO_I2_RUNTIME_IMPLEMENTED is True
    assert demand_module.RUNTIME_SEMANTICS_UNCHANGED is True
