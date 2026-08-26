import copy
import hashlib
import json
import math
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING_PATH = ROOT / "contracts" / "AF001-CAPABILITY-DECISION-RECEIPT-BINDING.json"
ACTION_BINDING_PATH = ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
IMPAIRMENT_BINDING_PATH = ROOT / "contracts" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"
FIXTURES_PATH = ROOT / "evals" / "AF001-CAPABILITY-DECISION-RECEIPT-FIXTURES.json"

CONTRACT_ID = "AWRSE-AF001-LIVING-STORY-CONTRACTS"
CONTRACT_VERSION = "1.9.0-candidate"
AUTHORITY_GRAPH = "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
RECEIPT_EPOCH = "AF001-CAPABILITY-DECISION-RECEIPT-I2A010@1"
RECEIPT_BINDING_ID = "AWRSE-AF001-CAPABILITY-DECISION-RECEIPT-BINDING"
UPSTREAM_ERROR = "I2A_CAPABILITY_DECISION_RECEIPT_UPSTREAM_ADMISSION_AUTHORITY_MISMATCH"
LOCKS = {
    "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
    "NO_I2_RUNTIME_IMPLEMENTED": True,
    "RUNTIME_SEMANTICS_UNCHANGED": True,
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _canonical_bytes(value):
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")


def _digest(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _expected_upstream(parent):
    action = _load(ACTION_BINDING_PATH)
    impairment = _load(IMPAIRMENT_BINDING_PATH)
    return {
        "ActorBaseProfileAdmissionReceipt": {
            "canonical_contract_id": parent["contract_id"],
            "canonical_contract_version": parent["contract_version"],
        },
        "SkillLedgerAdmissionReceipt": {
            "canonical_contract_id": parent["contract_id"],
            "canonical_contract_version": parent["contract_version"],
        },
        "ActionDemandAdmissionReceipt": {
            "canonical_contract_id": parent["contract_id"],
            "canonical_contract_version": parent["contract_version"],
            "binding_id": action["binding_id"],
            "binding_version": action["binding_version"],
        },
        "FunctionalImpairmentAdmissionReceipt": {
            "canonical_contract_id": parent["contract_id"],
            "canonical_contract_version": parent["contract_version"],
            "authority_graph_version": parent["authority_graph_version"],
            "binding_id": impairment["binding_id"],
            "binding_version": impairment["binding_version"],
        },
        "drift_policy": (
            "ANY_MISSING_OR_MISMATCHED_UPSTREAM_ADMISSION_AUTHORITY_IDENTITY_"
            "FAILS_CLOSED_BEFORE_DIGEST_MATERIALIZATION"
        ),
    }


def _authority_fields(binding, key):
    return binding["upstream_admission_authority_identity"][key]


def _require_authority(value, expected):
    if not isinstance(value, Mapping):
        raise ValueError(UPSTREAM_ERROR)
    for field, literal in expected.items():
        if value.get(field) != literal:
            raise ValueError(UPSTREAM_ERROR)


def _validate_authority(parent, binding):
    if (
        parent.get("contract_id") != CONTRACT_ID
        or parent.get("contract_version") != CONTRACT_VERSION
        or parent.get("authority_graph_version") != AUTHORITY_GRAPH
    ):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID")
    if parent.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH")
    reg = parent["registered_contract_extensions"].get(RECEIPT_BINDING_ID)
    if not isinstance(reg, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID")
    if (
        reg.get("parent_contract_id") != CONTRACT_ID
        or reg.get("parent_contract_version") != CONTRACT_VERSION
        or reg.get("parent_authority_graph_version") != AUTHORITY_GRAPH
        or reg.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH
        or reg.get("runtime_implementation_authorized") is not False
    ):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID")
    if binding["authority_locks"] != LOCKS:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID")
    if binding.get("upstream_admission_authority_identity") != _expected_upstream(parent):
        raise ValueError(UPSTREAM_ERROR)


def _validate_evidence(evidence):
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    _validate_authority(parent, binding)

    actor = copy.deepcopy(evidence["actor_profile_evidence"])
    skill = copy.deepcopy(evidence["skill_ledger_evidence"])
    demand = copy.deepcopy(evidence["action_demand_evidence"])
    impairment = copy.deepcopy(evidence["functional_impairment_evidence"])

    _require_authority(actor, _authority_fields(binding, "ActorBaseProfileAdmissionReceipt"))
    _require_authority(skill, _authority_fields(binding, "SkillLedgerAdmissionReceipt"))
    _require_authority(demand, _authority_fields(binding, "ActionDemandAdmissionReceipt"))
    if skill["actor_id"] != actor["actor_id"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")

    required_attrs = tuple(sorted(demand["required_attributes"]))
    required_skills = tuple(sorted(demand["required_skills"]))
    body_functions = tuple(sorted(demand["required_body_functions"]))
    if len(required_attrs) != len(set(required_attrs)) or len(required_skills) != len(set(required_skills)):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")

    if impairment["state"] == "ABSENT":
        if impairment["receipt"] is not None:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    else:
        rec = impairment["receipt"]
        _require_authority(
            rec, _authority_fields(binding, "FunctionalImpairmentAdmissionReceipt")
        )
        if (
            rec["actor_id"] != actor["actor_id"]
            or rec["demand_id"] != demand["demand_id"]
            or rec["ruleset_version"] != demand["ruleset_version"]
            or rec["source_demand_ref"] != demand["source_demand_ref"]
            or rec["replay_input_ref"] != demand["replay_input_ref"]
            or tuple(sorted(rec["required_body_functions"])) != body_functions
        ):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")

    attrs = actor["admitted_base_attribute_map"]
    skills = {entry["skill_id"]: entry["value"] for entry in skill["admitted_skill_entries"]}
    missing = [x for x in required_attrs if x not in attrs] + [x for x in required_skills if x not in skills]
    if missing:
        result = {"feasible": False, "effective_capability": None, "margin": None}
    else:
        values = [attrs[x] for x in required_attrs] + [skills[x] for x in required_skills]
        if any(isinstance(x, bool) or not isinstance(x, (int, float)) or (isinstance(x, float) and not math.isfinite(x)) for x in values):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_NUMERIC_INVALID")
        effective = sum(values)
        difficulty = demand["difficulty_or_resistance"]
        result = {
            "feasible": True,
            "effective_capability": effective,
            "margin": effective - difficulty,
        }

    material = {
        "receipt_schema_id": "AF001.CapabilityDecisionReceipt",
        "receipt_schema_version": "1.0.0-candidate",
        "parent_contract_id": CONTRACT_ID,
        "parent_contract_version": CONTRACT_VERSION,
        "parent_authority_graph_version": AUTHORITY_GRAPH,
        "capability_decision_receipt_authority_epoch": RECEIPT_EPOCH,
        "resolver_id": "AWRSE-I2A-DETERMINISTIC-CAPABILITY-RESOLVER",
        "resolver_version": "1.0.0-candidate",
        "actor_id": actor["actor_id"],
        "actor_profile_evidence": actor,
        "skill_ledger_evidence": skill,
        "action_demand_evidence": demand,
        "functional_impairment_evidence": impairment,
        "hard_prerequisite_receipt_ref": demand["hard_prerequisite_receipt_ref"],
        "difficulty_source_ref": demand["difficulty_source_ref"],
        "replay_input_ref": demand["replay_input_ref"],
    }
    return {**material, "input_digest_sha256": _digest(material), **result}


def _base():
    case = _load(FIXTURES_PATH)["base_feasible_case"]
    return {
        "actor_profile_evidence": copy.deepcopy(case["actor_profile_evidence"]),
        "skill_ledger_evidence": copy.deepcopy(case["skill_ledger_evidence"]),
        "action_demand_evidence": copy.deepcopy(case["action_demand_evidence"]),
        "functional_impairment_evidence": copy.deepcopy(case["functional_impairment_evidence"]),
    }


def _git_object(path):
    return subprocess.run(
        ["git", "rev-parse", f"HEAD:{path}"],
        cwd=ROOT, check=True, capture_output=True, text=True,
    ).stdout.strip()


def test_parent_epoch_and_complete_upstream_authority_registry_are_exact():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    _validate_authority(parent, binding)
    assert parent["contract_version"] == CONTRACT_VERSION
    assert parent["authority_graph_version"] == AUTHORITY_GRAPH
    assert binding["canonical_digest"][
        "input_material_includes_complete_upstream_admission_authority_identity"
    ] is True
    assert binding["authority_and_mutation_rules"][
        "reduced_caller_evidence_can_reconstitute_upstream_admission_authority"
    ] is False


def test_pre_i2a010_parent_and_orphan_child_fail_closed():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    pre = copy.deepcopy(parent)
    pre.pop("capability_decision_receipt_authority_epoch")
    with pytest.raises(ValueError, match="AUTHORITY_EPOCH_MISMATCH"):
        _validate_authority(pre, binding)
    orphan = copy.deepcopy(parent)
    orphan["registered_contract_extensions"].pop(RECEIPT_BINDING_ID)
    with pytest.raises(ValueError, match="CANONICAL_BINDING_INVALID"):
        _validate_authority(orphan, binding)


def test_identical_inputs_are_deterministic_and_result_is_exact():
    fixture = _load(FIXTURES_PATH)
    first = _validate_evidence(_base())
    second = _validate_evidence(_base())
    assert first == second
    assert first["input_digest_sha256"] == second["input_digest_sha256"]
    assert {
        "feasible": first["feasible"],
        "effective_capability": first["effective_capability"],
        "margin": first["margin"],
    } == fixture["base_feasible_case"]["expected_result"]


@pytest.mark.parametrize(
    ("path", "field", "drift"),
    [
        (("actor_profile_evidence",), "canonical_contract_id", "FORGED"),
        (("actor_profile_evidence",), "canonical_contract_version", "0-forged"),
        (("skill_ledger_evidence",), "canonical_contract_id", "FORGED"),
        (("skill_ledger_evidence",), "canonical_contract_version", "0-forged"),
        (("action_demand_evidence",), "binding_id", "FORGED"),
        (("action_demand_evidence",), "binding_version", "0-forged"),
        (("functional_impairment_evidence", "receipt"), "authority_graph_version", "FORGED"),
        (("functional_impairment_evidence", "receipt"), "binding_id", "FORGED"),
        (("functional_impairment_evidence", "receipt"), "binding_version", "0-forged"),
    ],
)
def test_upstream_admission_authority_drift_fails_closed_before_digest(path, field, drift):
    evidence = _base()
    target = evidence
    for key in path:
        target = target[key]
    target[field] = drift
    with pytest.raises(ValueError, match=f"^{UPSTREAM_ERROR}$"):
        _validate_evidence(evidence)


@pytest.mark.parametrize(
    ("section", "field"),
    [
        ("actor_profile_evidence", "canonical_contract_id"),
        ("actor_profile_evidence", "canonical_contract_version"),
        ("skill_ledger_evidence", "canonical_contract_id"),
        ("skill_ledger_evidence", "canonical_contract_version"),
        ("action_demand_evidence", "binding_id"),
        ("action_demand_evidence", "binding_version"),
    ],
)
def test_upstream_authority_identity_is_present_in_digest_material(section, field):
    receipt = _validate_evidence(_base())
    assert receipt[section][field] == _base()[section][field]


def test_functional_impairment_authority_identity_is_present_in_digest_material():
    receipt = _validate_evidence(_base())["functional_impairment_evidence"]["receipt"]
    expected = _base()["functional_impairment_evidence"]["receipt"]
    for field in (
        "canonical_contract_id", "canonical_contract_version",
        "authority_graph_version", "binding_id", "binding_version",
    ):
        assert receipt[field] == expected[field]


def test_business_evidence_changes_identity_and_caller_mutation_is_isolated():
    baseline = _validate_evidence(_base())
    changed = _base()
    changed["skill_ledger_evidence"]["admitted_skill_entries"][0]["value"] = 6
    assert _validate_evidence(changed)["input_digest_sha256"] != baseline["input_digest_sha256"]
    evidence = _base()
    frozen = _validate_evidence(evidence)
    before = copy.deepcopy(frozen)
    evidence["actor_profile_evidence"]["admitted_base_attribute_map"]["strength"] = 999
    assert frozen == before


def test_absent_vs_zero_applicability_are_distinct_with_same_numeric_result():
    fixture = _load(FIXTURES_PATH)
    zero = _base()
    zero["functional_impairment_evidence"] = copy.deepcopy(
        fixture["zero_applicability_case"]["functional_impairment_evidence"]
    )
    absent = _base()
    absent["functional_impairment_evidence"] = copy.deepcopy(
        fixture["absent_impairment_case"]["functional_impairment_evidence"]
    )
    z = _validate_evidence(zero)
    a = _validate_evidence(absent)
    assert z["input_digest_sha256"] != a["input_digest_sha256"]
    assert (z["feasible"], z["effective_capability"], z["margin"]) == (
        a["feasible"], a["effective_capability"], a["margin"]
    )


def test_infeasible_result_has_null_numerics():
    fixture = _load(FIXTURES_PATH)
    evidence = _base()
    evidence["action_demand_evidence"].update(fixture["infeasible_case"]["action_demand_override"])
    r = _validate_evidence(evidence)
    assert {
        "feasible": r["feasible"],
        "effective_capability": r["effective_capability"],
        "margin": r["margin"],
    } == fixture["infeasible_case"]["expected_result"]


def test_runtime_and_r003_persistence_authority_are_unchanged():
    fixture = _load(FIXTURES_PATH)["unchanged_evidence"]
    assert _git_object("runtime") == fixture["runtime_tree_sha"]
    assert _git_object("runtime/awrse/persistence.py") == fixture["persistence_runtime_blob_sha"]
    assert _git_object("evals/R003-I1A-RESTART-REFERENCE.json") == fixture["r003_i1a_reference_blob_sha"]


def test_required_adversarial_proofs_and_locks_are_machine_registered():
    fixture = _load(FIXTURES_PATH)
    ids = {case["case_id"] for case in fixture["required_adversarial_cases"]}
    for n in range(1, 25):
        assert any(case_id.startswith(f"CDR-{n:02d}-") for case_id in ids)
    assert fixture["authority_locks"] == LOCKS
    assert _load(BINDING_PATH)["authority_locks"] == LOCKS
