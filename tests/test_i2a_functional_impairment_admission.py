import copy
import json
from pathlib import Path
from types import MappingProxyType

import pytest

from runtime.awrse.action_demand_admission import ActionDemandAdmissionReceipt
from runtime.awrse.actor_profile_admission import ActorBaseProfileAdmissionReceipt
from runtime.awrse.functional_impairment_admission import (
    FunctionalImpairmentAdmissionReceipt,
    admit_functional_impairment_applicability,
)
import runtime.awrse.functional_impairment_admission as impairment_module


ROOT = Path(__file__).resolve().parents[1]
FIXTURES_PATH = ROOT / "evals" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-FIXTURES.json"
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING_PATH = ROOT / "contracts" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _cases():
    return {case["case_id"]: case for case in _load(FIXTURES_PATH)["cases"]}


def _actor_receipt(actor_id="ACTOR-FIGHTER-001"):
    return ActorBaseProfileAdmissionReceipt(
        actor_id=actor_id,
        profile_version="1.1.0-candidate",
        profile_schema_ref="PROFILE-SCHEMA-A@1",
        ruleset_family_ref="RULESET-FAMILY-A@1",
        admitted_base_attribute_map=MappingProxyType({"strength": 8, "reasoning": 4}),
        source_event_refs=("E-ACTOR-001",),
        canonical_contract_id="AWRSE-AF001-LIVING-STORY-CONTRACTS",
        canonical_contract_version="1.9.0-candidate",
    )


def _demand_receipt(case):
    demand = case["demand"]
    return ActionDemandAdmissionReceipt(
        demand_id=demand["demand_id"],
        action_family="TEST-ACTION-FAMILY",
        method_id="TEST-METHOD",
        ruleset_version=demand["ruleset_version"],
        hard_prerequisites=(),
        required_body_functions=tuple(sorted(demand["required_body_functions"])),
        required_attributes=("strength",),
        required_skills=(),
        difficulty_or_resistance=1,
        provenance=MappingProxyType(
            {
                "source_demand_ref": case["source_demand_ref"],
                "demand_id": demand["demand_id"],
                "action_family": "TEST-ACTION-FAMILY",
                "method_id": "TEST-METHOD",
                "ruleset_version": demand["ruleset_version"],
                "difficulty_source_ref": "DIFFICULTY-TEST@1",
                "replay_input_ref": case["replay_input_ref"],
                "hard_prerequisite_receipt_ref": "NOT_APPLICABLE",
            }
        ),
        canonical_contract_id="AWRSE-AF001-LIVING-STORY-CONTRACTS",
        canonical_contract_version="1.9.0-candidate",
        binding_id="AWRSE-AF001-ACTION-DEMAND-PROJECTION-BINDING",
        binding_version="1.0.0-candidate",
        resolver_projection=MappingProxyType(
            {
                "required_attributes": ("strength",),
                "required_skills": (),
                "difficulty_or_resistance": 1,
            }
        ),
    )


def _admit(case, *, actor_receipt=None, demand_receipt=None, demand=None, injury_sources=None):
    return admit_functional_impairment_applicability(
        actor_receipt or _actor_receipt(case["actor_id"]),
        demand_receipt or _demand_receipt(case),
        copy.deepcopy(case["demand"] if demand is None else demand),
        copy.deepcopy(case["injury_sources"] if injury_sources is None else injury_sources),
        source_demand_ref=case["source_demand_ref"],
        replay_input_ref=case["replay_input_ref"],
    )


def _logical_projection(receipt):
    projection = receipt.projection
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


def test_fic01_exact_right_grip_is_structurally_applicable_without_numeric_effect():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    receipt = _admit(case)
    assert isinstance(receipt, FunctionalImpairmentAdmissionReceipt)
    assert _logical_projection(receipt) == case["expected"]
    assert receipt.authority_graph_version == "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
    assert receipt.numeric_effect_status == "DEFERRED_RULESET_TUNING"
    assert "severity" not in receipt.projection
    assert "penalty" not in receipt.projection
    assert "coefficient" not in receipt.projection
    assert "multiplier" not in receipt.projection


@pytest.mark.parametrize(
    "case_id",
    [
        "FIC-02-SAME-INJURY-UNRELATED-REASONING-ZERO-EFFECT",
        "FIC-03-LOWER-LIMB-CANNOT-SPREAD",
        "FIC-04-EMPTY-IMPAIRMENT-EVIDENCE-ZERO-EFFECT",
    ],
)
def test_unrelated_or_empty_evidence_has_zero_applicability(case_id):
    case = _cases()[case_id]
    receipt = _admit(case)
    assert _logical_projection(receipt) == case["expected"]
    assert dict(receipt.applicable_impairment_refs_by_function) == {}


@pytest.mark.parametrize(
    "case_id",
    [
        "FIC-05-DUPLICATE-IMPAIRMENT-REF-FAILS-CLOSED",
        "FIC-06-BLANK-FUNCTION-REF-FAILS-CLOSED",
        "FIC-07-DRESSING-CANNOT-AUTHOR-IMPAIRMENT",
        "FIC-08-CALLER-NUMERIC-OVERRIDE-NOT-AUTHORIZED",
    ],
)
def test_canonical_invalid_fixtures_fail_closed(case_id):
    case = _cases()[case_id]
    with pytest.raises(ValueError, match=f"^{case['expected_error']}$"):
        _admit(case)


def test_actor_binding_comes_from_admitted_actor_receipt_and_mismatch_fails_closed():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["injury_sources"][0]["actor_id"] = "ACTOR-OTHER"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH$"):
        _admit(case)

    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH$"):
        admit_functional_impairment_applicability(
            {"actor_id": case["actor_id"]},
            _demand_receipt(case),
            case["demand"],
            case["injury_sources"],
            source_demand_ref=case["source_demand_ref"],
            replay_input_ref=case["replay_input_ref"],
        )


def test_raw_caller_demand_receipt_and_identity_or_provenance_bypass_fail_closed():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH$"):
        admit_functional_impairment_applicability(
            _actor_receipt(case["actor_id"]),
            {"demand_id": case["demand"]["demand_id"]},
            case["demand"],
            case["injury_sources"],
            source_demand_ref=case["source_demand_ref"],
            replay_input_ref=case["replay_input_ref"],
        )

    wrong_identity = copy.deepcopy(case["demand"])
    wrong_identity["demand_id"] = "FORGED-DEMAND"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH$"):
        _admit(case, demand=wrong_identity)

    receipt = _demand_receipt(case)
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH$"):
        admit_functional_impairment_applicability(
            _actor_receipt(case["actor_id"]),
            receipt,
            case["demand"],
            case["injury_sources"],
            source_demand_ref="FORGED-SOURCE-REF",
            replay_input_ref=case["replay_input_ref"],
        )


def test_same_admitted_receipt_cannot_rebind_required_body_functions():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    admitted_receipt = _demand_receipt(case)
    original = case["demand"]["required_body_functions"]
    variants = [
        [],
        original + ["cognition.reasoning@1"],
        ["body.lower_limb.left.balance@1"],
    ]
    for required_body_functions in variants:
        forged = copy.deepcopy(case["demand"])
        forged["required_body_functions"] = required_body_functions
        with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH$"):
            _admit(case, demand_receipt=admitted_receipt, demand=forged)


def test_same_admitted_receipt_accepts_order_only_change():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = [
        "cognition.reasoning@1",
        "body.upper_limb.right.grip@1",
    ]
    admitted_receipt = _demand_receipt(case)
    reordered = copy.deepcopy(case["demand"])
    reordered["required_body_functions"].reverse()
    receipt = _admit(case, demand_receipt=admitted_receipt, demand=reordered)
    assert receipt.required_body_functions == (
        "body.upper_limb.right.grip@1",
        "cognition.reasoning@1",
    )


def test_unsupported_injury_version_missing_identity_or_provenance_fail_closed():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]

    wrong_version = copy.deepcopy(case["injury_sources"])
    wrong_version[0]["source_type_version"] = "0.9.0-candidate"
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH$"):
        _admit(case, injury_sources=wrong_version)

    for field in ("injury_id", "source_event_ref"):
        malformed = copy.deepcopy(case["injury_sources"])
        malformed[0][field] = "   "
        with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED$"):
            _admit(case, injury_sources=malformed)


def test_empty_required_body_functions_is_valid_zero_applicability_when_admitted_empty():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = []
    receipt = _admit(case)
    assert receipt.required_body_functions == ()
    assert dict(receipt.applicable_impairment_refs_by_function) == {}


def test_required_function_ref_must_be_nonblank_string():
    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    admitted_receipt = _demand_receipt(case)
    for value in (None, "   ", 123):
        demand = copy.deepcopy(case["demand"])
        demand["required_body_functions"] = [value]
        with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID$"):
            _admit(case, demand_receipt=admitted_receipt, demand=demand)


def test_insertion_order_is_deterministic_and_canonically_sorted():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    case["demand"]["required_body_functions"] = [
        "cognition.reasoning@1",
        "body.upper_limb.right.grip@1",
    ]
    case["injury_sources"] = [
        {
            "source_type": "InjuryState",
            "source_type_version": "1.0.0-candidate",
            "injury_id": "INJURY-B",
            "actor_id": case["actor_id"],
            "source_event_ref": "EVENT-B",
            "functional_impairments": [
                {
                    "impairment_ref": "IMP-B",
                    "function_ref": "body.upper_limb.right.grip@1",
                }
            ],
        },
        {
            "source_type": "InjuryState",
            "source_type_version": "1.0.0-candidate",
            "injury_id": "INJURY-A",
            "actor_id": case["actor_id"],
            "source_event_ref": "EVENT-A",
            "functional_impairments": [
                {
                    "impairment_ref": "IMP-A",
                    "function_ref": "body.upper_limb.right.grip@1",
                }
            ],
        },
    ]
    demand_receipt = _demand_receipt(case)
    first = _admit(case, demand_receipt=demand_receipt)

    reversed_case = copy.deepcopy(case)
    reversed_case["demand"]["required_body_functions"].reverse()
    reversed_case["injury_sources"].reverse()
    for source in reversed_case["injury_sources"]:
        source["functional_impairments"].reverse()
    second = _admit(reversed_case, demand_receipt=_demand_receipt(reversed_case))

    assert first.projection == second.projection
    assert first.required_body_functions == (
        "body.upper_limb.right.grip@1",
        "cognition.reasoning@1",
    )
    assert first.source_injury_refs == ("INJURY-A", "INJURY-B")
    assert first.source_event_refs == ("EVENT-A", "EVENT-B")
    assert first.applicable_impairment_refs_by_function["body.upper_limb.right.grip@1"] == (
        "IMP-A",
        "IMP-B",
    )


def test_projection_is_copy_isolated_from_caller_mutation():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    receipt = _admit(case)
    before = receipt.projection
    case["demand"]["required_body_functions"].append("FORGED@1")
    case["injury_sources"][0]["functional_impairments"][0]["impairment_ref"] = "FORGED"
    assert receipt.projection == before
    assert "FORGED@1" not in receipt.required_body_functions
    assert "FORGED" not in receipt.applicable_impairment_refs_by_function["body.upper_limb.right.grip@1"]


def test_same_injury_id_is_not_collapsed_and_duplicate_impairment_identity_is_the_fail_closed_key():
    case = copy.deepcopy(_cases()["FIC-01-RIGHT-GRIP-RELEVANT"])
    second = copy.deepcopy(case["injury_sources"][0])
    second["source_event_ref"] = "E-INJURY-RIGHT-HAND-002"
    second["functional_impairments"][0]["impairment_ref"] = "IMPAIR-RIGHT-GRIP-002"
    case["injury_sources"].append(second)
    receipt = _admit(case)
    assert receipt.source_injury_refs == ("INJURY-RIGHT-HAND-001", "INJURY-RIGHT-HAND-001")
    assert receipt.applicable_impairment_refs_by_function["body.upper_limb.right.grip@1"] == (
        "IMPAIR-RIGHT-GRIP-001",
        "IMPAIR-RIGHT-GRIP-002",
    )


def test_pre_i2a008_same_version_parent_without_authority_graph_fails_closed(tmp_path, monkeypatch):
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    parent.pop("authority_graph_version")
    parent.get("versioning_and_migration", {}).pop("authority_graph_discriminator", None)

    parent_path = tmp_path / "parent.json"
    binding_path = tmp_path / "binding.json"
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(impairment_module, "_CANONICAL_CONTRACT_PATH", parent_path)
    monkeypatch.setattr(impairment_module, "_BINDING_PATH", binding_path)

    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID$"):
        _admit(case)


def test_child_self_declaration_without_parent_registration_fails_closed(tmp_path, monkeypatch):
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    parent["registered_contract_extensions"].pop(binding["binding_id"])

    parent_path = tmp_path / "parent.json"
    binding_path = tmp_path / "binding.json"
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(impairment_module, "_CANONICAL_CONTRACT_PATH", parent_path)
    monkeypatch.setattr(impairment_module, "_BINDING_PATH", binding_path)

    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID$"):
        _admit(case)


def test_binding_or_source_type_version_drift_fails_closed(tmp_path, monkeypatch):
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    parent["type_registry"]["InjuryState"]["version"] = "0.9.0-candidate"

    parent_path = tmp_path / "parent.json"
    binding_path = tmp_path / "binding.json"
    parent_path.write_text(json.dumps(parent), encoding="utf-8")
    binding_path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(impairment_module, "_CANONICAL_CONTRACT_PATH", parent_path)
    monkeypatch.setattr(impairment_module, "_BINDING_PATH", binding_path)

    case = _cases()["FIC-01-RIGHT-GRIP-RELEVANT"]
    with pytest.raises(ValueError, match="^I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH$"):
        _admit(case)


def test_no_resolver_or_numeric_application_authority_is_exported():
    assert impairment_module.I2_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert impairment_module.NO_I2_RUNTIME_IMPLEMENTED is True
    assert impairment_module.RUNTIME_SEMANTICS_UNCHANGED is True
    assert not hasattr(impairment_module, "resolve_capability")
    assert "penalty" not in FunctionalImpairmentAdmissionReceipt.__dataclass_fields__
    assert "severity" not in FunctionalImpairmentAdmissionReceipt.__dataclass_fields__
