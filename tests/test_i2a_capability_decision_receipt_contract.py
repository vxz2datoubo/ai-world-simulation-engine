import copy
import hashlib
import json
import subprocess
from collections.abc import Mapping
from pathlib import Path

import pytest

from runtime.awrse.capability_resolution import resolve_capability


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
RECEIPT_BINDING_VERSION = "1.0.0-candidate"
RECEIPT_SCHEMA_ID = "AF001.CapabilityDecisionReceipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-candidate"
RESOLVER_ID = "AWRSE-I2A-DETERMINISTIC-CAPABILITY-RESOLVER"
RESOLVER_VERSION = "1.0.0-candidate"

UPSTREAM_ERROR = "I2A_CAPABILITY_DECISION_RECEIPT_UPSTREAM_ADMISSION_AUTHORITY_MISMATCH"
NUMERIC_ERROR = "I2A_CAPABILITY_DECISION_RECEIPT_NUMERIC_INVALID"
LOCKS = {
    "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
    "NO_I2_RUNTIME_IMPLEMENTED": True,
    "RUNTIME_SEMANTICS_UNCHANGED": True,
}


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _nonempty(value, error):
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _canonical_bytes(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError(NUMERIC_ERROR) from exc


def _digest(value):
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


def _ordered_refs(value, *, allow_empty, error):
    if not isinstance(value, list):
        raise ValueError(error)
    if not allow_empty and not value:
        raise ValueError(error)
    if any(not isinstance(ref, str) or not ref.strip() for ref in value):
        raise ValueError(error)
    return list(value)


def _canonical_unique_refs(value, error):
    refs = _ordered_refs(value, allow_empty=True, error=error)
    if len(refs) != len(set(refs)):
        raise ValueError(error)
    return sorted(refs)


def _canonical_body_functions(value):
    return sorted(
        _ordered_refs(
            value,
            allow_empty=True,
            error="I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
        )
    )


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


def _validate_source_types(parent, binding):
    registry = parent.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
    for name, frozen in binding["source_type_bindings"].items():
        actual = registry.get(name)
        if not isinstance(actual, Mapping):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
        if (
            actual.get("type_id") != frozen.get("type_id")
            or actual.get("version") != frozen.get("version")
        ):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")


def _validate_authority(parent, binding):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID"
    if (
        parent.get("contract_id") != CONTRACT_ID
        or parent.get("contract_version") != CONTRACT_VERSION
        or parent.get("authority_graph_version") != AUTHORITY_GRAPH
    ):
        raise ValueError(error)
    if parent.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH")

    registrations = parent.get("registered_contract_extensions")
    if not isinstance(registrations, Mapping):
        raise ValueError(error)
    registration = registrations.get(RECEIPT_BINDING_ID)
    if not isinstance(registration, Mapping):
        raise ValueError(error)
    if (
        registration.get("path")
        != "contracts/AF001-CAPABILITY-DECISION-RECEIPT-BINDING.json"
        or registration.get("binding_version") != RECEIPT_BINDING_VERSION
        or registration.get("parent_contract_id") != CONTRACT_ID
        or registration.get("parent_contract_version") != CONTRACT_VERSION
        or registration.get("parent_authority_graph_version") != AUTHORITY_GRAPH
        or registration.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH
        or registration.get("authority") != "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        or registration.get("registration_class") != "ADDITIVE_NON_RUNTIME_CANDIDATE_EXTENSION"
        or registration.get("governance_issue_ref") != "#58"
        or registration.get("runtime_implementation_authorized") is not False
    ):
        raise ValueError(error)

    parent_ref = binding.get("parent_machine_contract")
    if not isinstance(parent_ref, Mapping) or (
        parent_ref.get("path") != "contracts/AF001-LIVING-STORY-CONTRACTS.json"
        or parent_ref.get("contract_id") != CONTRACT_ID
        or parent_ref.get("contract_version") != CONTRACT_VERSION
        or parent_ref.get("authority_graph_version") != AUTHORITY_GRAPH
        or parent_ref.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH
    ):
        raise ValueError(error)

    discriminator = parent.get("versioning_and_migration", {}).get(
        "capability_decision_receipt_authority_discriminator"
    )
    if not isinstance(discriminator, Mapping) or (
        discriminator.get("field") != "capability_decision_receipt_authority_epoch"
        or discriminator.get("current") != RECEIPT_EPOCH
        or discriminator.get("pre_i2a010_state") != "FIELD_ABSENT"
        or discriminator.get("authorization_tuple")
        != [
            "contract_id",
            "contract_version",
            "authority_graph_version",
            "capability_decision_receipt_authority_epoch",
        ]
    ):
        raise ValueError(error)

    if binding.get("runtime_implementation_authorized") is not False:
        raise ValueError(error)
    if binding.get("implementation_scope") != "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED":
        raise ValueError(error)
    if binding.get("authority_locks") != LOCKS:
        raise ValueError(error)

    profile = binding.get("receipt_profile")
    if not isinstance(profile, Mapping) or (
        profile.get("schema_id") != RECEIPT_SCHEMA_ID
        or profile.get("schema_version") != RECEIPT_SCHEMA_VERSION
        or profile.get("derived_evidence_only") is not True
        or profile.get("canonical_world_truth") is not False
        or profile.get("persistence_authority") is not False
    ):
        raise ValueError(error)

    resolver = binding.get("resolver_reference")
    if not isinstance(resolver, Mapping) or (
        resolver.get("resolver_id") != RESOLVER_ID
        or resolver.get("resolver_version") != RESOLVER_VERSION
        or resolver.get("implementation_evidence") != "runtime/awrse/capability_resolution.py"
        or resolver.get("semantic_order")
        != [
            "HARD_FEASIBILITY_FIRST",
            "DEMAND_SCOPED_ATTRIBUTES_AND_SKILLS_ONLY",
            "DETERMINISTIC_ADDITIVE_EFFECTIVE_CAPABILITY",
            "MARGIN_EQUALS_EFFECTIVE_CAPABILITY_MINUS_DIFFICULTY_OR_RESISTANCE",
        ]
        or resolver.get("numeric_rule")
        != "FINITE_NON_BOOLEAN_INT_OR_FLOAT; NO_PROBABILITY; NO_WEIGHTING; NO_IMPAIRMENT_NUMERIC_APPLICATION"
    ):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_RESOLVER_MISMATCH")

    if binding.get("upstream_admission_authority_identity") != _expected_upstream(parent):
        raise ValueError(UPSTREAM_ERROR)

    _validate_source_types(parent, binding)


def _canonical_actor(value, binding):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH"
    if not isinstance(value, Mapping):
        raise ValueError(error)
    expected = set(binding["admitted_evidence_contract"]["actor_profile_evidence_required_fields"])
    if set(value) != expected:
        raise ValueError(error)
    _require_authority(value, _authority_fields(binding, "ActorBaseProfileAdmissionReceipt"))

    actor_id = _nonempty(value.get("actor_id"), error)
    if value.get("profile_version") != binding["source_type_bindings"]["ActorBaseProfile"]["version"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
    schema_ref = _nonempty(
        value.get("profile_schema_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH",
    )
    ruleset_ref = _nonempty(
        value.get("ruleset_family_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH",
    )
    attrs = value.get("admitted_base_attribute_map")
    if not isinstance(attrs, Mapping) or not attrs:
        raise ValueError(error)
    for key in attrs:
        _nonempty(key, error)
    source_refs = _ordered_refs(
        value.get("source_event_refs"),
        allow_empty=False,
        error=error,
    )
    authority = _authority_fields(binding, "ActorBaseProfileAdmissionReceipt")
    return {
        "actor_id": actor_id,
        "profile_version": value["profile_version"],
        "profile_schema_ref": schema_ref,
        "ruleset_family_ref": ruleset_ref,
        "admitted_base_attribute_map": copy.deepcopy(dict(attrs)),
        "source_event_refs": source_refs,
        **authority,
    }


def _canonical_skill(value, binding, actor_id):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH"
    if not isinstance(value, Mapping):
        raise ValueError(error)
    expected = set(binding["admitted_evidence_contract"]["skill_ledger_evidence_required_fields"])
    if set(value) != expected or value.get("actor_id") != actor_id:
        raise ValueError(error)
    _require_authority(value, _authority_fields(binding, "SkillLedgerAdmissionReceipt"))
    if value.get("schema_version") != binding["source_type_bindings"]["SkillLedger"]["version"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")

    cursor = _nonempty(value.get("source_event_cursor"), error)
    entries = value.get("admitted_skill_entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError(error)
    expected_entry = set(binding["admitted_evidence_contract"]["skill_entry_required_fields"])
    frozen_entries = []
    seen = set()
    values = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != expected_entry:
            raise ValueError(error)
        skill_id = _nonempty(entry.get("skill_id"), error)
        if skill_id in seen:
            raise ValueError(error)
        seen.add(skill_id)
        source_refs = _ordered_refs(
            entry.get("source_event_refs"),
            allow_empty=False,
            error=error,
        )
        frozen_entries.append(
            {
                "skill_id": skill_id,
                "value": entry.get("value"),
                "source_event_refs": source_refs,
            }
        )
        values[skill_id] = entry.get("value")

    authority = _authority_fields(binding, "SkillLedgerAdmissionReceipt")
    return (
        {
            "actor_id": actor_id,
            "schema_version": value["schema_version"],
            "admitted_skill_entries": frozen_entries,
            "source_event_cursor": cursor,
            **authority,
        },
        values,
    )


def _canonical_demand(value, binding):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
    if not isinstance(value, Mapping):
        raise ValueError(error)
    expected = set(binding["admitted_evidence_contract"]["action_demand_evidence_required_fields"])
    if set(value) != expected:
        raise ValueError(error)
    _require_authority(value, _authority_fields(binding, "ActionDemandAdmissionReceipt"))

    demand_id = _nonempty(value.get("demand_id"), error)
    action_family = _nonempty(value.get("action_family"), error)
    method_id = _nonempty(value.get("method_id"), error)
    ruleset_version = _nonempty(value.get("ruleset_version"), error)
    hard_prerequisites = _ordered_refs(
        value.get("hard_prerequisites"),
        allow_empty=True,
        error=error,
    )
    required_body_functions = _canonical_body_functions(value.get("required_body_functions"))
    required_attributes = _canonical_unique_refs(value.get("required_attributes"), error)
    required_skills = _canonical_unique_refs(value.get("required_skills"), error)
    if not required_attributes and not required_skills:
        raise ValueError(error)

    if "difficulty_or_resistance" not in value:
        raise ValueError(error)
    difficulty = value["difficulty_or_resistance"]
    source_demand_ref = _nonempty(value.get("source_demand_ref"), error)
    difficulty_source_ref = _nonempty(value.get("difficulty_source_ref"), error)
    replay_input_ref = _nonempty(
        value.get("replay_input_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_REPLAY_BINDING_MISMATCH",
    )
    prerequisite_ref = _nonempty(value.get("hard_prerequisite_receipt_ref"), error)
    if hard_prerequisites and prerequisite_ref == "NOT_APPLICABLE":
        raise ValueError(error)
    if not hard_prerequisites and prerequisite_ref != "NOT_APPLICABLE":
        raise ValueError(error)

    authority = _authority_fields(binding, "ActionDemandAdmissionReceipt")
    return {
        "demand_id": demand_id,
        "action_family": action_family,
        "method_id": method_id,
        "ruleset_version": ruleset_version,
        "hard_prerequisites": hard_prerequisites,
        "required_body_functions": required_body_functions,
        "required_attributes": required_attributes,
        "required_skills": required_skills,
        "difficulty_or_resistance": difficulty,
        "source_demand_ref": source_demand_ref,
        "difficulty_source_ref": difficulty_source_ref,
        "replay_input_ref": replay_input_ref,
        "hard_prerequisite_receipt_ref": prerequisite_ref,
        **authority,
    }


def _canonical_impairment(value, binding, *, actor_id, demand):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
    if not isinstance(value, Mapping) or set(value) != {"state", "receipt"}:
        raise ValueError(error)
    state = value.get("state")
    if state not in binding["admitted_evidence_contract"]["functional_impairment_evidence_states"]:
        raise ValueError(error)
    receipt = value.get("receipt")
    if state == "ABSENT":
        if receipt is not None:
            raise ValueError(error)
        return {"state": "ABSENT", "receipt": None}

    expected = set(
        binding["admitted_evidence_contract"][
            "functional_impairment_receipt_required_fields_when_provided"
        ]
    )
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise ValueError(error)
    _require_authority(
        receipt,
        _authority_fields(binding, "FunctionalImpairmentAdmissionReceipt"),
    )
    if (
        receipt.get("actor_id") != actor_id
        or receipt.get("demand_id") != demand["demand_id"]
        or receipt.get("ruleset_version") != demand["ruleset_version"]
        or receipt.get("source_demand_ref") != demand["source_demand_ref"]
        or receipt.get("replay_input_ref") != demand["replay_input_ref"]
    ):
        raise ValueError(error)

    body_functions = _canonical_body_functions(receipt.get("required_body_functions"))
    if body_functions != demand["required_body_functions"]:
        raise ValueError(error)
    if receipt.get("numeric_effect_status") != "DEFERRED_RULESET_TUNING":
        raise ValueError(error)

    applicable = receipt.get("applicable_impairment_refs_by_function")
    if not isinstance(applicable, Mapping):
        raise ValueError(error)
    frozen_applicable = {}
    for function_ref in sorted(applicable):
        _nonempty(function_ref, error)
        if function_ref not in body_functions:
            raise ValueError(error)
        refs = _canonical_unique_refs(applicable[function_ref], error)
        if not refs:
            raise ValueError(error)
        frozen_applicable[function_ref] = refs

    source_injury_refs = _canonical_unique_refs(receipt.get("source_injury_refs"), error)
    source_event_refs = _canonical_unique_refs(receipt.get("source_event_refs"), error)
    if state == "PROVIDED_ZERO_APPLICABILITY" and frozen_applicable:
        raise ValueError(error)
    if state == "PROVIDED_APPLICABLE" and not frozen_applicable:
        raise ValueError(error)

    authority = _authority_fields(binding, "FunctionalImpairmentAdmissionReceipt")
    return {
        "state": state,
        "receipt": {
            "actor_id": actor_id,
            "demand_id": demand["demand_id"],
            "ruleset_version": demand["ruleset_version"],
            "required_body_functions": body_functions,
            "applicable_impairment_refs_by_function": frozen_applicable,
            "source_injury_refs": source_injury_refs,
            "source_event_refs": source_event_refs,
            "source_demand_ref": demand["source_demand_ref"],
            "replay_input_ref": demand["replay_input_ref"],
            "numeric_effect_status": "DEFERRED_RULESET_TUNING",
            **authority,
        },
    }


def _materialize(evidence, *, parent=None, binding=None, supplied_result=None):
    parent = copy.deepcopy(parent if parent is not None else _load(PARENT_PATH))
    binding = copy.deepcopy(binding if binding is not None else _load(BINDING_PATH))
    _validate_authority(parent, binding)

    actor = _canonical_actor(evidence["actor_profile_evidence"], binding)
    actor_id = actor["actor_id"]
    skill, skill_values = _canonical_skill(
        evidence["skill_ledger_evidence"],
        binding,
        actor_id,
    )
    demand = _canonical_demand(evidence["action_demand_evidence"], binding)
    impairment = _canonical_impairment(
        evidence["functional_impairment_evidence"],
        binding,
        actor_id=actor_id,
        demand=demand,
    )

    resolution = resolve_capability(
        capability_envelope={
            "validated_actor_base_attributes": actor["admitted_base_attribute_map"],
            "validated_skill_ledger_values": skill_values,
        },
        action_demand_profile={
            "required_attributes": demand["required_attributes"],
            "required_skills": demand["required_skills"],
            "difficulty_or_resistance": demand["difficulty_or_resistance"],
        },
        provenance={
            "profile_schema_ref": actor["profile_schema_ref"],
            "ruleset_family_ref": actor["ruleset_family_ref"],
            "replay_input_ref": demand["replay_input_ref"],
        },
    )
    result = {
        "feasible": resolution.feasible,
        "effective_capability": resolution.effective_capability,
        "margin": resolution.margin,
    }
    if supplied_result is not None and supplied_result != result:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_RESULT_MISMATCH")

    material = {
        "receipt_schema_id": RECEIPT_SCHEMA_ID,
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "parent_contract_id": CONTRACT_ID,
        "parent_contract_version": CONTRACT_VERSION,
        "parent_authority_graph_version": AUTHORITY_GRAPH,
        "capability_decision_receipt_authority_epoch": RECEIPT_EPOCH,
        "resolver_id": RESOLVER_ID,
        "resolver_version": RESOLVER_VERSION,
        "actor_id": actor_id,
        "actor_profile_evidence": actor,
        "skill_ledger_evidence": skill,
        "action_demand_evidence": demand,
        "functional_impairment_evidence": impairment,
        "hard_prerequisite_receipt_ref": demand["hard_prerequisite_receipt_ref"],
        "difficulty_source_ref": demand["difficulty_source_ref"],
        "replay_input_ref": demand["replay_input_ref"],
    }
    frozen = copy.deepcopy(material)
    return {
        **frozen,
        "input_digest_sha256": _digest(frozen),
        **result,
    }


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
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
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


def test_pre_i2a010_parent_orphan_child_and_authority_epoch_drift_fail_closed():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)

    pre = copy.deepcopy(parent)
    pre.pop("capability_decision_receipt_authority_epoch")
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH$"):
        _validate_authority(pre, binding)

    orphan = copy.deepcopy(parent)
    orphan["registered_contract_extensions"].pop(RECEIPT_BINDING_ID)
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID$"):
        _validate_authority(orphan, binding)

    drifted = copy.deepcopy(parent)
    drifted["capability_decision_receipt_authority_epoch"] = "DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH$"):
        _validate_authority(drifted, binding)


def test_source_type_and_resolver_identity_drift_fail_closed():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)

    broken_parent = copy.deepcopy(parent)
    broken_parent["type_registry"]["SkillLedger"]["version"] = "DRIFTED"
    with pytest.raises(
        ValueError,
        match="^I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH$",
    ):
        _validate_authority(broken_parent, binding)

    broken_binding = copy.deepcopy(binding)
    broken_binding["resolver_reference"]["resolver_version"] = "DRIFTED"
    with pytest.raises(
        ValueError,
        match="^I2A_CAPABILITY_DECISION_RECEIPT_RESOLVER_MISMATCH$",
    ):
        _materialize(_base(), binding=broken_binding)


def test_identical_inputs_are_deterministic_and_feasible_result_is_exact():
    fixture = _load(FIXTURES_PATH)
    first = _materialize(_base())
    second = _materialize(_base())
    assert first == second
    assert first["input_digest_sha256"] == second["input_digest_sha256"]
    assert {
        "feasible": first["feasible"],
        "effective_capability": first["effective_capability"],
        "margin": first["margin"],
    } == fixture["base_feasible_case"]["expected_result"]
    assert len(first["input_digest_sha256"]) == 64


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
        _materialize(evidence)


def test_complete_upstream_authority_identity_is_present_in_digest_material():
    receipt = _materialize(_base())
    evidence = _base()
    for section, fields in {
        "actor_profile_evidence": ("canonical_contract_id", "canonical_contract_version"),
        "skill_ledger_evidence": ("canonical_contract_id", "canonical_contract_version"),
        "action_demand_evidence": (
            "canonical_contract_id",
            "canonical_contract_version",
            "binding_id",
            "binding_version",
        ),
    }.items():
        for field in fields:
            assert receipt[section][field] == evidence[section][field]

    actual_impairment = receipt["functional_impairment_evidence"]["receipt"]
    expected_impairment = evidence["functional_impairment_evidence"]["receipt"]
    for field in (
        "canonical_contract_id",
        "canonical_contract_version",
        "authority_graph_version",
        "binding_id",
        "binding_version",
    ):
        assert actual_impairment[field] == expected_impairment[field]


def test_each_bound_upstream_evidence_class_changes_receipt_identity():
    baseline = _materialize(_base())["input_digest_sha256"]

    actor_changed = _base()
    actor_changed["actor_profile_evidence"]["admitted_base_attribute_map"]["strength"] = 8
    assert _materialize(actor_changed)["input_digest_sha256"] != baseline

    skill_changed = _base()
    skill_changed["skill_ledger_evidence"]["admitted_skill_entries"][0]["value"] = 6
    assert _materialize(skill_changed)["input_digest_sha256"] != baseline

    demand_changed = _base()
    demand_changed["action_demand_evidence"]["difficulty_or_resistance"] = 11
    assert _materialize(demand_changed)["input_digest_sha256"] != baseline

    body_changed = _base()
    body_changed["action_demand_evidence"]["required_body_functions"].append("LEFT_GRIP")
    body_changed["functional_impairment_evidence"]["receipt"]["required_body_functions"].append(
        "LEFT_GRIP"
    )
    assert _materialize(body_changed)["input_digest_sha256"] != baseline

    impairment_changed = _base()
    impairment_changed["functional_impairment_evidence"]["receipt"]["source_event_refs"][0] = (
        "E-INJURY-002"
    )
    assert _materialize(impairment_changed)["input_digest_sha256"] != baseline


def test_nonsemantic_order_is_canonical_but_ordered_provenance_remains_sensitive():
    baseline_evidence = _base()
    baseline = _materialize(copy.deepcopy(baseline_evidence))

    reordered = copy.deepcopy(baseline_evidence)
    reordered["action_demand_evidence"]["required_body_functions"].reverse()
    reordered["functional_impairment_evidence"]["receipt"]["required_body_functions"].reverse()
    assert _materialize(reordered)["input_digest_sha256"] == baseline["input_digest_sha256"]

    provenance_reordered = copy.deepcopy(baseline_evidence)
    provenance_reordered["actor_profile_evidence"]["source_event_refs"].reverse()
    assert (
        _materialize(provenance_reordered)["input_digest_sha256"]
        != baseline["input_digest_sha256"]
    )

    ledger_reordered = copy.deepcopy(baseline_evidence)
    ledger_reordered["skill_ledger_evidence"]["admitted_skill_entries"].reverse()
    assert (
        _materialize(ledger_reordered)["input_digest_sha256"]
        != baseline["input_digest_sha256"]
    )


def test_unrelated_impairment_is_bound_but_has_zero_numeric_effect_and_absent_is_distinct():
    fixture = _load(FIXTURES_PATH)
    applicable = _materialize(_base())

    zero = _base()
    zero["functional_impairment_evidence"] = copy.deepcopy(
        fixture["zero_applicability_case"]["functional_impairment_evidence"]
    )
    zero_receipt = _materialize(zero)

    absent = _base()
    absent["functional_impairment_evidence"] = copy.deepcopy(
        fixture["absent_impairment_case"]["functional_impairment_evidence"]
    )
    absent_receipt = _materialize(absent)

    for receipt in (applicable, zero_receipt, absent_receipt):
        assert {
            "feasible": receipt["feasible"],
            "effective_capability": receipt["effective_capability"],
            "margin": receipt["margin"],
        } == fixture["base_feasible_case"]["expected_result"]
    assert applicable["input_digest_sha256"] != zero_receipt["input_digest_sha256"]
    assert zero_receipt["input_digest_sha256"] != absent_receipt["input_digest_sha256"]


def test_infeasible_result_is_null_numeric():
    fixture = _load(FIXTURES_PATH)
    evidence = _base()
    evidence["action_demand_evidence"].update(fixture["infeasible_case"]["action_demand_override"])
    receipt = _materialize(evidence)
    assert {
        "feasible": receipt["feasible"],
        "effective_capability": receipt["effective_capability"],
        "margin": receipt["margin"],
    } == fixture["infeasible_case"]["expected_result"]


@pytest.mark.parametrize("invalid", [True, float("nan"), float("inf"), float("-inf")])
def test_difficulty_numeric_semantics_match_canonical_resolver_and_fail_closed(invalid):
    evidence = _base()
    evidence["action_demand_evidence"]["difficulty_or_resistance"] = invalid
    with pytest.raises(ValueError, match="^I2A_DEMAND_DIFFICULTY_INVALID$"):
        _materialize(evidence)


def test_supplied_materialized_result_cannot_override_recomputation():
    expected = _load(FIXTURES_PATH)["base_feasible_case"]["expected_result"]
    baseline = _materialize(_base())

    with pytest.raises(
        ValueError,
        match="^I2A_CAPABILITY_DECISION_RECEIPT_RESULT_MISMATCH$",
    ):
        _materialize(
            _base(),
            supplied_result={
                "feasible": True,
                "effective_capability": 999,
                "margin": 999,
            },
        )

    matching = _materialize(_base(), supplied_result=copy.deepcopy(expected))
    assert matching == baseline


def test_caller_mutation_after_materialization_cannot_change_frozen_receipt():
    evidence = _base()
    receipt = _materialize(evidence)
    frozen = copy.deepcopy(receipt)
    evidence["actor_profile_evidence"]["admitted_base_attribute_map"]["strength"] = 1000
    evidence["skill_ledger_evidence"]["admitted_skill_entries"][0]["value"] = 1000
    evidence["action_demand_evidence"]["required_body_functions"].append("MUTATED")
    assert receipt == frozen


def test_schema_ruleset_and_replay_drift_fail_closed_or_change_identity():
    baseline = _materialize(_base())

    bad_schema = _base()
    bad_schema["actor_profile_evidence"]["profile_version"] = "DRIFTED"
    with pytest.raises(
        ValueError,
        match="^I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH$",
    ):
        _materialize(bad_schema)

    bad_ruleset = _base()
    bad_ruleset["action_demand_evidence"]["ruleset_version"] = "RULESET-DRIFTED"
    with pytest.raises(
        ValueError,
        match="^I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH$",
    ):
        _materialize(bad_ruleset)

    replay_changed = _base()
    replay_changed["action_demand_evidence"]["replay_input_ref"] = "REPLAY-INPUT-002"
    replay_changed["functional_impairment_evidence"]["receipt"]["replay_input_ref"] = (
        "REPLAY-INPUT-002"
    )
    assert (
        _materialize(replay_changed)["input_digest_sha256"]
        != baseline["input_digest_sha256"]
    )


def test_runtime_and_r003_persistence_authority_are_exactly_unchanged():
    fixture = _load(FIXTURES_PATH)["unchanged_evidence"]
    assert _git_object("runtime") == fixture["runtime_tree_sha"]
    assert _git_object("runtime/awrse/persistence.py") == fixture["persistence_runtime_blob_sha"]
    assert _git_object("evals/R003-I1A-RESTART-REFERENCE.json") == fixture[
        "r003_i1a_reference_blob_sha"
    ]


def test_receipt_never_becomes_upstream_or_persistence_authority():
    binding = _load(BINDING_PATH)
    rules = binding["authority_and_mutation_rules"]
    assert rules["receipt_is_derived_evidence"] is True
    for key in (
        "receipt_can_author_actor_profile_truth",
        "receipt_can_author_skill_ledger_truth",
        "receipt_can_author_action_demand_truth",
        "receipt_can_author_injury_truth",
        "receipt_can_author_world_state_truth",
        "receipt_can_mutate_upstream_truth",
    ):
        assert rules[key] is False

    persistence = binding["persistence_relationship"]
    assert persistence["accepted_authority"] == "AWRSE_R003_I1A_SOLO_REPLAY_PACKAGE"
    assert persistence["status"] == "SEPARATE_AND_DEFERRED"
    assert persistence["must_not_modify_existing_package"] is True
    assert persistence["must_not_create_second_persistence_authority"] is True
    assert persistence["open_decision_id"] == "OD-I2A010-RECEIPT-CARRIER-001"


def test_required_adversarial_proofs_and_locks_are_machine_registered():
    fixture = _load(FIXTURES_PATH)
    ids = {case["case_id"] for case in fixture["required_adversarial_cases"]}
    expected = {
        "CDR-01-IDENTICAL-INPUTS-IDENTICAL-IDENTITY",
        "CDR-02-FEASIBLE-RESULT-EXACT",
        "CDR-03-INFEASIBLE-NUMERICS-NULL",
        "CDR-04-ACTOR-PROFILE-CHANGE-INVALIDATES",
        "CDR-05-SKILL-LEDGER-CHANGE-INVALIDATES",
        "CDR-06-ACTION-DEMAND-CHANGE-INVALIDATES",
        "CDR-07-BODY-FUNCTION-CHANGE-INVALIDATES",
        "CDR-08-IMPAIRMENT-EVIDENCE-CHANGE-INVALIDATES",
        "CDR-09-UNRELATED-IMPAIRMENT-ZERO-NUMERIC-EFFECT",
        "CDR-10-NONSEMANTIC-ORDER-CANONICAL",
        "CDR-11-ORDERED-PROVENANCE-SENSITIVE",
        "CDR-12-DRIFT-FAILS-CLOSED",
        "CDR-13-CALLER-MUTATION-ISOLATED",
        "CDR-14-SUPPLIED-RESULT-CANNOT-OVERRIDE",
        "CDR-15-ORPHAN-CHILD-FAILS-CLOSED",
        "CDR-16-PRE-I2A010-PARENT-FAILS-CLOSED",
        "CDR-17-R003-I1A-UNTOUCHED",
        "CDR-18-NO-RUNTIME-FILES-CHANGED",
        "CDR-19-AUTHORITY-LOCKS-PRESERVED",
        "CDR-20-ABSENT-VS-ZERO-APPLICABILITY-DISTINCT",
        "CDR-21-ACTOR-ADMISSION-AUTHORITY-DRIFT-FAILS-CLOSED",
        "CDR-22-SKILL-ADMISSION-AUTHORITY-DRIFT-FAILS-CLOSED",
        "CDR-23-ACTION-DEMAND-ADMISSION-BINDING-DRIFT-FAILS-CLOSED",
        "CDR-24-FUNCTIONAL-IMPAIRMENT-ADMISSION-AUTHORITY-DRIFT-FAILS-CLOSED",
    }
    assert ids == expected
    assert fixture["authority_locks"] == LOCKS
    assert _load(BINDING_PATH)["authority_locks"] == LOCKS
