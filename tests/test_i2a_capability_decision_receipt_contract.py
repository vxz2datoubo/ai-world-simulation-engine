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
R003_PATH = ROOT / "evals" / "R003-I1A-RESTART-REFERENCE.json"
PERSISTENCE_PATH = ROOT / "runtime" / "awrse" / "persistence.py"
RESOLVER_PATH = ROOT / "runtime" / "awrse" / "capability_resolution.py"

CONTRACT_ID = "AWRSE-AF001-LIVING-STORY-CONTRACTS"
CONTRACT_VERSION = "1.9.0-candidate"
AUTHORITY_GRAPH_VERSION = "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
RECEIPT_EPOCH = "AF001-CAPABILITY-DECISION-RECEIPT-I2A010@1"
BINDING_ID = "AWRSE-AF001-CAPABILITY-DECISION-RECEIPT-BINDING"
BINDING_VERSION = "1.0.0-candidate"
RECEIPT_SCHEMA_ID = "AF001.CapabilityDecisionReceipt"
RECEIPT_SCHEMA_VERSION = "1.0.0-candidate"
RESOLVER_ID = "AWRSE-I2A-DETERMINISTIC-CAPABILITY-RESOLVER"
RESOLVER_VERSION = "1.0.0-candidate"
EXPECTED_LOCKS = {
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


def _finite_number(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_NUMERIC_INVALID")
    if isinstance(value, float) and not math.isfinite(value):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_NUMERIC_INVALID")
    return value


def _ordered_string_refs(value, *, allow_empty, error):
    if not isinstance(value, list):
        raise ValueError(error)
    if not allow_empty and not value:
        raise ValueError(error)
    if any(not isinstance(ref, str) or not ref.strip() for ref in value):
        raise ValueError(error)
    return list(value)


def _canonical_unique_refs(value, error):
    refs = _ordered_string_refs(value, allow_empty=True, error=error)
    if len(refs) != len(set(refs)):
        raise ValueError(error)
    return sorted(refs)


def _canonical_body_functions(value):
    refs = _ordered_string_refs(
        value,
        allow_empty=True,
        error="I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    return sorted(refs)


def _canonical_json_bytes(value):
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_NUMERIC_INVALID") from exc


def _digest(value):
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _validate_source_types(parent, binding):
    registry = parent.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
    for name, frozen in binding["source_type_bindings"].items():
        actual = registry.get(name)
        if not isinstance(actual, Mapping):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
        if actual.get("type_id") != frozen.get("type_id") or actual.get("version") != frozen.get("version"):
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")


def _validate_authority(parent, binding):
    error = "I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID"
    if (
        parent.get("contract_id") != CONTRACT_ID
        or parent.get("contract_version") != CONTRACT_VERSION
        or parent.get("authority_graph_version") != AUTHORITY_GRAPH_VERSION
    ):
        raise ValueError(error)
    if parent.get("capability_decision_receipt_authority_epoch") != RECEIPT_EPOCH:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH")

    registrations = parent.get("registered_contract_extensions")
    if not isinstance(registrations, Mapping):
        raise ValueError(error)
    registration = registrations.get(BINDING_ID)
    if not isinstance(registration, Mapping):
        raise ValueError(error)
    if (
        registration.get("path") != "contracts/AF001-CAPABILITY-DECISION-RECEIPT-BINDING.json"
        or registration.get("binding_version") != BINDING_VERSION
        or registration.get("parent_contract_id") != CONTRACT_ID
        or registration.get("parent_contract_version") != CONTRACT_VERSION
        or registration.get("parent_authority_graph_version") != AUTHORITY_GRAPH_VERSION
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
        or parent_ref.get("authority_graph_version") != AUTHORITY_GRAPH_VERSION
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
        or "PRE_I2A010_PARENT_WITHOUT_RECEIPT_EPOCH_CANNOT_AUTHORIZE" not in discriminator.get(
            "authorization_rule", ""
        )
    ):
        raise ValueError(error)

    authority_rule = parent.get("capability_decision_receipt_extension_authority_rule")
    if not isinstance(authority_rule, str) or (
        "PRE_I2A010_PARENT_WITHOUT_RECEIPT_EPOCH_CANNOT_AUTHORIZE" not in authority_rule
    ):
        raise ValueError(error)

    if binding.get("runtime_implementation_authorized") is not False:
        raise ValueError(error)
    if binding.get("implementation_scope") != "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED":
        raise ValueError(error)
    if binding.get("authority_locks") != EXPECTED_LOCKS:
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
    ):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_RESOLVER_MISMATCH")

    _validate_source_types(parent, binding)


def _canonical_actor_profile(value, binding):
    if not isinstance(value, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    expected = set(binding["admitted_evidence_contract"]["actor_profile_evidence_required_fields"])
    if set(value) != expected:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    actor_id = _nonempty(
        value.get("actor_id"), "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH"
    )
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
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    for key in attrs:
        _nonempty(key, "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    source_refs = _ordered_string_refs(
        value.get("source_event_refs"),
        allow_empty=False,
        error="I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH",
    )
    return {
        "actor_id": actor_id,
        "profile_version": value["profile_version"],
        "profile_schema_ref": schema_ref,
        "ruleset_family_ref": ruleset_ref,
        "admitted_base_attribute_map": copy.deepcopy(dict(attrs)),
        "source_event_refs": source_refs,
    }


def _canonical_skill_ledger(value, binding, actor_id):
    if not isinstance(value, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    expected = set(binding["admitted_evidence_contract"]["skill_ledger_evidence_required_fields"])
    if set(value) != expected or value.get("actor_id") != actor_id:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    if value.get("schema_version") != binding["source_type_bindings"]["SkillLedger"]["version"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH")
    cursor = _nonempty(
        value.get("source_event_cursor"),
        "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH",
    )
    entries = value.get("admitted_skill_entries")
    if not isinstance(entries, list) or not entries:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
    expected_entry = set(binding["admitted_evidence_contract"]["skill_entry_required_fields"])
    frozen_entries = []
    seen = set()
    values = {}
    for entry in entries:
        if not isinstance(entry, Mapping) or set(entry) != expected_entry:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
        skill_id = _nonempty(
            entry.get("skill_id"), "I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH"
        )
        if skill_id in seen:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH")
        seen.add(skill_id)
        skill_value = _finite_number(entry.get("value"))
        source_refs = _ordered_string_refs(
            entry.get("source_event_refs"),
            allow_empty=False,
            error="I2A_CAPABILITY_DECISION_RECEIPT_ACTOR_BINDING_MISMATCH",
        )
        frozen_entries.append(
            {
                "skill_id": skill_id,
                "value": skill_value,
                "source_event_refs": source_refs,
            }
        )
        values[skill_id] = skill_value
    return (
        {
            "actor_id": actor_id,
            "schema_version": value["schema_version"],
            "admitted_skill_entries": frozen_entries,
            "source_event_cursor": cursor,
        },
        values,
    )


def _canonical_action_demand(value, binding):
    if not isinstance(value, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    expected = set(binding["admitted_evidence_contract"]["action_demand_evidence_required_fields"])
    if set(value) != expected:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    demand_id = _nonempty(
        value.get("demand_id"), "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
    )
    action_family = _nonempty(
        value.get("action_family"), "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
    )
    method_id = _nonempty(
        value.get("method_id"), "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
    )
    ruleset_version = _nonempty(
        value.get("ruleset_version"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    hard_prerequisites = _ordered_string_refs(
        value.get("hard_prerequisites"),
        allow_empty=True,
        error="I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    required_body_functions = _canonical_body_functions(value.get("required_body_functions"))
    required_attributes = _canonical_unique_refs(
        value.get("required_attributes"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    required_skills = _canonical_unique_refs(
        value.get("required_skills"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    if not required_attributes and not required_skills:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    difficulty = _finite_number(value.get("difficulty_or_resistance"))
    source_demand_ref = _nonempty(
        value.get("source_demand_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    difficulty_source_ref = _nonempty(
        value.get("difficulty_source_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    replay_input_ref = _nonempty(
        value.get("replay_input_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_REPLAY_BINDING_MISMATCH",
    )
    prerequisite_ref = _nonempty(
        value.get("hard_prerequisite_receipt_ref"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    if hard_prerequisites and prerequisite_ref == "NOT_APPLICABLE":
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    if not hard_prerequisites and prerequisite_ref != "NOT_APPLICABLE":
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
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
    }


def _canonical_functional_impairment(value, binding, *, actor_id, demand):
    if not isinstance(value, Mapping) or set(value) != {"state", "receipt"}:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    state = value.get("state")
    if state not in binding["admitted_evidence_contract"]["functional_impairment_evidence_states"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    receipt = value.get("receipt")
    if state == "ABSENT":
        if receipt is not None:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
        return {"state": "ABSENT", "receipt": None}

    expected = set(
        binding["admitted_evidence_contract"][
            "functional_impairment_receipt_required_fields_when_provided"
        ]
    )
    if not isinstance(receipt, Mapping) or set(receipt) != expected:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    if (
        receipt.get("actor_id") != actor_id
        or receipt.get("demand_id") != demand["demand_id"]
        or receipt.get("ruleset_version") != demand["ruleset_version"]
        or receipt.get("source_demand_ref") != demand["source_demand_ref"]
        or receipt.get("replay_input_ref") != demand["replay_input_ref"]
    ):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    body_functions = _canonical_body_functions(receipt.get("required_body_functions"))
    if body_functions != demand["required_body_functions"]:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    if receipt.get("numeric_effect_status") != "DEFERRED_RULESET_TUNING":
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")

    applicable = receipt.get("applicable_impairment_refs_by_function")
    if not isinstance(applicable, Mapping):
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    frozen_applicable = {}
    for function_ref in sorted(applicable):
        _nonempty(
            function_ref, "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH"
        )
        if function_ref not in body_functions:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
        refs = _canonical_unique_refs(
            applicable[function_ref],
            "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
        )
        if not refs:
            raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
        frozen_applicable[function_ref] = refs
    source_injury_refs = _canonical_unique_refs(
        receipt.get("source_injury_refs"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    source_event_refs = _canonical_unique_refs(
        receipt.get("source_event_refs"),
        "I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH",
    )
    if state == "PROVIDED_ZERO_APPLICABILITY" and frozen_applicable:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
    if state == "PROVIDED_APPLICABLE" and not frozen_applicable:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH")
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
        },
    }


def _resolve(actor_profile, skill_values, demand):
    attributes = actor_profile["admitted_base_attribute_map"]
    missing_attributes = [ref for ref in demand["required_attributes"] if ref not in attributes]
    missing_skills = [ref for ref in demand["required_skills"] if ref not in skill_values]
    if missing_attributes or missing_skills:
        return {"feasible": False, "effective_capability": None, "margin": None}
    selected = []
    for ref in demand["required_attributes"]:
        selected.append(_finite_number(attributes[ref]))
    for ref in demand["required_skills"]:
        selected.append(_finite_number(skill_values[ref]))
    effective = 0
    for value in selected:
        effective = _finite_number(effective + value)
    margin = _finite_number(effective - demand["difficulty_or_resistance"])
    return {
        "feasible": True,
        "effective_capability": effective,
        "margin": margin,
    }


def _materialize(evidence, *, parent=None, binding=None, supplied_result=None):
    parent = copy.deepcopy(parent if parent is not None else _load(PARENT_PATH))
    binding = copy.deepcopy(binding if binding is not None else _load(BINDING_PATH))
    _validate_authority(parent, binding)

    actor_profile = _canonical_actor_profile(evidence["actor_profile_evidence"], binding)
    actor_id = actor_profile["actor_id"]
    skill_ledger, skill_values = _canonical_skill_ledger(
        evidence["skill_ledger_evidence"], binding, actor_id
    )
    demand = _canonical_action_demand(evidence["action_demand_evidence"], binding)
    impairment = _canonical_functional_impairment(
        evidence["functional_impairment_evidence"],
        binding,
        actor_id=actor_id,
        demand=demand,
    )
    result = _resolve(actor_profile, skill_values, demand)
    if supplied_result is not None and supplied_result != result:
        raise ValueError("I2A_CAPABILITY_DECISION_RECEIPT_RESULT_MISMATCH")

    material = {
        "receipt_schema_id": RECEIPT_SCHEMA_ID,
        "receipt_schema_version": RECEIPT_SCHEMA_VERSION,
        "parent_contract_id": CONTRACT_ID,
        "parent_contract_version": CONTRACT_VERSION,
        "parent_authority_graph_version": AUTHORITY_GRAPH_VERSION,
        "capability_decision_receipt_authority_epoch": RECEIPT_EPOCH,
        "resolver_id": RESOLVER_ID,
        "resolver_version": RESOLVER_VERSION,
        "actor_id": actor_id,
        "actor_profile_evidence": actor_profile,
        "skill_ledger_evidence": skill_ledger,
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


def _base_evidence():
    fixture = _load(FIXTURES_PATH)
    case = fixture["base_feasible_case"]
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


def test_parent_registers_receipt_with_extension_specific_epoch_without_version_cascade():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)
    fixture = _load(FIXTURES_PATH)
    _validate_authority(parent, binding)
    assert parent["contract_version"] == CONTRACT_VERSION
    assert parent["authority_graph_version"] == AUTHORITY_GRAPH_VERSION
    assert fixture["parent_contract_version"] == CONTRACT_VERSION
    assert fixture["parent_authority_graph_version"] == AUTHORITY_GRAPH_VERSION
    assert fixture["capability_decision_receipt_authority_epoch"] == RECEIPT_EPOCH

    action_binding = _load(ACTION_BINDING_PATH)
    impairment_binding = _load(IMPAIRMENT_BINDING_PATH)
    action_registration = parent["registered_contract_extensions"][action_binding["binding_id"]]
    impairment_registration = parent["registered_contract_extensions"][impairment_binding["binding_id"]]
    assert action_registration["parent_contract_version"] == CONTRACT_VERSION
    assert action_binding["parent_machine_contract"]["contract_version"] == CONTRACT_VERSION
    assert impairment_registration["parent_contract_version"] == CONTRACT_VERSION
    assert impairment_registration["parent_authority_graph_version"] == AUTHORITY_GRAPH_VERSION
    assert impairment_binding["parent_machine_contract"]["authority_graph_version"] == AUTHORITY_GRAPH_VERSION


def test_orphan_child_and_pre_i2a010_same_version_parent_fail_closed():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)

    orphan = copy.deepcopy(parent)
    orphan["registered_contract_extensions"].pop(BINDING_ID)
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_CANONICAL_BINDING_INVALID$"):
        _validate_authority(orphan, binding)

    pre_i2a010 = copy.deepcopy(parent)
    pre_i2a010.pop("capability_decision_receipt_authority_epoch")
    pre_i2a010["versioning_and_migration"].pop(
        "capability_decision_receipt_authority_discriminator"
    )
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH$"):
        _validate_authority(pre_i2a010, binding)

    wrong_epoch = copy.deepcopy(parent)
    wrong_epoch["capability_decision_receipt_authority_epoch"] = "I2A010-DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_AUTHORITY_EPOCH_MISMATCH$"):
        _validate_authority(wrong_epoch, binding)


def test_source_type_and_resolver_drift_fail_closed():
    parent = _load(PARENT_PATH)
    binding = _load(BINDING_PATH)

    broken_parent = copy.deepcopy(parent)
    broken_parent["type_registry"]["SkillLedger"]["version"] = "DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH$"):
        _validate_authority(broken_parent, binding)

    broken_binding = copy.deepcopy(binding)
    broken_binding["resolver_reference"]["resolver_version"] = "DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_RESOLVER_MISMATCH$"):
        _validate_authority(parent, broken_binding)


def test_identical_inputs_have_identical_digest_and_exact_current_feasible_result():
    fixture = _load(FIXTURES_PATH)
    evidence = _base_evidence()
    first = _materialize(copy.deepcopy(evidence))
    second = _materialize(copy.deepcopy(evidence))
    assert first == second
    assert first["input_digest_sha256"] == second["input_digest_sha256"]
    assert {
        "feasible": first["feasible"],
        "effective_capability": first["effective_capability"],
        "margin": first["margin"],
    } == fixture["base_feasible_case"]["expected_result"]
    assert len(first["input_digest_sha256"]) == 64


def test_each_bound_upstream_evidence_class_changes_receipt_identity():
    baseline = _materialize(_base_evidence())["input_digest_sha256"]

    actor_changed = _base_evidence()
    actor_changed["actor_profile_evidence"]["admitted_base_attribute_map"]["strength"] = 8
    assert _materialize(actor_changed)["input_digest_sha256"] != baseline

    skill_changed = _base_evidence()
    skill_changed["skill_ledger_evidence"]["admitted_skill_entries"][0]["value"] = 6
    assert _materialize(skill_changed)["input_digest_sha256"] != baseline

    demand_changed = _base_evidence()
    demand_changed["action_demand_evidence"]["difficulty_or_resistance"] = 11
    assert _materialize(demand_changed)["input_digest_sha256"] != baseline

    body_changed = _base_evidence()
    body_changed["action_demand_evidence"]["required_body_functions"].append("LEFT_GRIP")
    body_changed["functional_impairment_evidence"]["receipt"]["required_body_functions"].append(
        "LEFT_GRIP"
    )
    assert _materialize(body_changed)["input_digest_sha256"] != baseline

    impairment_changed = _base_evidence()
    impairment_changed["functional_impairment_evidence"]["receipt"][
        "source_event_refs"
    ][0] = "E-INJURY-002"
    assert _materialize(impairment_changed)["input_digest_sha256"] != baseline


def test_upstream_nonsemantic_body_function_order_is_canonical_but_ordered_provenance_is_sensitive():
    baseline_evidence = _base_evidence()
    baseline = _materialize(copy.deepcopy(baseline_evidence))

    reordered = copy.deepcopy(baseline_evidence)
    reordered["action_demand_evidence"]["required_body_functions"].reverse()
    reordered["functional_impairment_evidence"]["receipt"]["required_body_functions"].reverse()
    assert _materialize(reordered)["input_digest_sha256"] == baseline["input_digest_sha256"]

    provenance_reordered = copy.deepcopy(baseline_evidence)
    provenance_reordered["actor_profile_evidence"]["source_event_refs"].reverse()
    assert _materialize(provenance_reordered)["input_digest_sha256"] != baseline["input_digest_sha256"]

    ledger_reordered = copy.deepcopy(baseline_evidence)
    ledger_reordered["skill_ledger_evidence"]["admitted_skill_entries"].reverse()
    assert _materialize(ledger_reordered)["input_digest_sha256"] != baseline["input_digest_sha256"]


def test_unrelated_impairment_is_bound_but_has_zero_numeric_effect_and_absent_is_distinct():
    fixture = _load(FIXTURES_PATH)
    base = _base_evidence()
    applicable = _materialize(copy.deepcopy(base))

    zero = copy.deepcopy(base)
    zero["functional_impairment_evidence"] = copy.deepcopy(
        fixture["zero_applicability_case"]["functional_impairment_evidence"]
    )
    zero_receipt = _materialize(zero)

    absent = copy.deepcopy(base)
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
    assert zero_receipt["input_digest_sha256"] != absent_receipt["input_digest_sha256"]
    assert applicable["input_digest_sha256"] != zero_receipt["input_digest_sha256"]


def test_infeasible_result_is_null_numeric_and_supplied_materialized_result_cannot_override():
    fixture = _load(FIXTURES_PATH)
    evidence = _base_evidence()
    evidence["action_demand_evidence"].update(
        fixture["infeasible_case"]["action_demand_override"]
    )
    receipt = _materialize(evidence)
    assert {
        "feasible": receipt["feasible"],
        "effective_capability": receipt["effective_capability"],
        "margin": receipt["margin"],
    } == fixture["infeasible_case"]["expected_result"]

    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_RESULT_MISMATCH$"):
        _materialize(
            _base_evidence(),
            supplied_result={"feasible": True, "effective_capability": 999, "margin": 999},
        )


def test_caller_mutation_after_materialization_cannot_change_frozen_receipt():
    evidence = _base_evidence()
    receipt = _materialize(evidence)
    frozen = copy.deepcopy(receipt)
    evidence["actor_profile_evidence"]["admitted_base_attribute_map"]["strength"] = 1000
    evidence["skill_ledger_evidence"]["admitted_skill_entries"][0]["value"] = 1000
    evidence["action_demand_evidence"]["required_body_functions"].append("MUTATED")
    assert receipt == frozen


def test_schema_ruleset_and_replay_mismatch_fail_closed_or_change_bound_identity():
    baseline = _materialize(_base_evidence())

    bad_schema = _base_evidence()
    bad_schema["actor_profile_evidence"]["profile_version"] = "DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_SOURCE_TYPE_VERSION_MISMATCH$"):
        _materialize(bad_schema)

    bad_ruleset = _base_evidence()
    bad_ruleset["action_demand_evidence"]["ruleset_version"] = "RULESET-DRIFTED"
    with pytest.raises(ValueError, match="^I2A_CAPABILITY_DECISION_RECEIPT_DEMAND_BINDING_MISMATCH$"):
        _materialize(bad_ruleset)

    replay_changed = _base_evidence()
    replay_changed["action_demand_evidence"]["replay_input_ref"] = "REPLAY-INPUT-002"
    replay_changed["functional_impairment_evidence"]["receipt"]["replay_input_ref"] = (
        "REPLAY-INPUT-002"
    )
    assert _materialize(replay_changed)["input_digest_sha256"] != baseline["input_digest_sha256"]


def test_runtime_tree_and_r003_persistence_authority_are_exactly_unchanged_from_i2a009_base():
    fixture = _load(FIXTURES_PATH)["unchanged_evidence"]
    assert _git_object("runtime") == fixture["runtime_tree_sha"]
    assert _git_object("runtime/awrse/persistence.py") == fixture["persistence_runtime_blob_sha"]
    assert _git_object("evals/R003-I1A-RESTART-REFERENCE.json") == fixture[
        "r003_i1a_reference_blob_sha"
    ]
    assert PERSISTENCE_PATH.exists()
    assert R003_PATH.exists()


def test_resolver_reference_freezes_only_existing_deterministic_semantics():
    binding = _load(BINDING_PATH)
    source = RESOLVER_PATH.read_text(encoding="utf-8")
    assert "Hard feasibility" in source
    assert "EffectiveCapability" in source
    assert "Margin = EffectiveCapability - DifficultyOrResistance" in source
    assert "required_attributes" in source and "required_skills" in source
    assert binding["result_binding"]["functional_impairment_numeric_effect"].startswith(
        "NONE_IN_I2A010"
    )
    assert "probability" not in binding["receipt_fields"]
    assert "outcome_band" not in binding["receipt_fields"]
    assert "hazard_outcome" not in binding["receipt_fields"]


def test_receipt_never_becomes_upstream_or_persistence_authority_and_carrier_remains_open():
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


def test_all_required_adversarial_proofs_and_locks_are_machine_registered():
    fixture = _load(FIXTURES_PATH)
    case_ids = {case["case_id"] for case in fixture["required_adversarial_cases"]}
    assert case_ids == {
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
    }
    assert fixture["authority_locks"] == EXPECTED_LOCKS
    assert _load(BINDING_PATH)["authority_locks"] == EXPECTED_LOCKS
