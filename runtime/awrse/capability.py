"""Bounded I2A capability admission and deterministic feasibility reference.

This module deliberately does not calculate capability magnitudes, margins,
outcome bands, hazards, or randomness.  It only admits a provenance-complete
profile and answers whether a method's explicitly declared hard prerequisites
are present.  The result can be exported and replay-verified without treating
the export as new canonical authority.
"""

from __future__ import annotations

import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


I2A_PROFILE_ID = "AWRSE_I2A_CAPABILITY_REPLAY_PACKAGE"
I2A_PROFILE_VERSION = "1.0.0"
I2A_SCOPE = "IN_PROCESS_NON_PRODUCTION"
_PACKAGE_FIELDS = frozenset({"profile_id", "profile_version", "scope", "policy", "actor_profile", "skill_ledger", "action_demand", "receipt", "package_digest"})


@dataclass(frozen=True)
class CapabilityReplayEvidence:
    """Validated I2A inputs and receipt; not a mutable world-state authority."""

    policy: Mapping[str, Any]
    actor_profile: Mapping[str, Any]
    skill_ledger: Mapping[str, Any]
    action_demand: Mapping[str, Any]
    receipt: Mapping[str, Any]
    package_digest: str


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("I2A_VALUE_NOT_CANONICAL_JSON") from exc


def _digest(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _reject_duplicate_json_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I2A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite_json_constant(value: str) -> None:
    raise ValueError(f"I2A_JSON_NONFINITE_NUMBER:{value}")


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _require_mapping(value: Any, code: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ValueError(code)
    return value


def _require_string_list(value: Any, code: str) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError(code)
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError(code)
    if len(set(value)) != len(value):
        raise ValueError(code)
    return tuple(value)


def _copy_json_mapping(value: Mapping[str, Any]) -> dict[str, Any]:
    return json.loads(_canonical_json_bytes(dict(value)).decode("utf-8"))


def policy_from_af_c_contract(contract: Mapping[str, Any]) -> dict[str, Any]:
    """Extract the I2A admission policy from the versioned AF-C contract."""

    contract = _require_mapping(contract, "I2A_CONTRACT_MAPPING_REQUIRED")
    version = _require_string(contract.get("contract_version"), "I2A_CONTRACT_VERSION_REQUIRED")
    migration = _require_mapping(
        _require_mapping(contract.get("versioning_and_migration"), "I2A_MIGRATION_SECTION_REQUIRED").get("actor_base_profile_migration"),
        "I2A_PROFILE_MIGRATION_REQUIRED",
    )
    fields = _require_string_list(migration.get("vnext_required_fields"), "I2A_VNEXT_FIELDS_REQUIRED")
    rules = _require_mapping(migration.get("vnext_required_field_admission_rules"), "I2A_FIELD_RULES_REQUIRED")
    if set(fields) != set(rules):
        raise ValueError("I2A_FIELD_RULES_DO_NOT_COVER_PROFILE")
    compatibility = _require_mapping(migration.get("profile_schema_ruleset_compatibility_registry"), "I2A_COMPATIBILITY_REGISTRY_REQUIRED")
    allowed = _require_mapping(compatibility.get("by_profile_schema_ref"), "I2A_COMPATIBILITY_MAPPING_REQUIRED")
    normalized_allowed = {schema: list(_require_string_list(list(rulesets), "I2A_RULESET_LIST_REQUIRED")) for schema, rulesets in allowed.items() if isinstance(schema, str) and schema}
    if not normalized_allowed:
        raise ValueError("I2A_COMPATIBILITY_MAPPING_REQUIRED")
    return {
        "contract_id": _require_string(contract.get("contract_id"), "I2A_CONTRACT_ID_REQUIRED"),
        "contract_version": version,
        "vnext_profile_contract_version": _require_string(migration.get("vnext_profile_contract_version"), "I2A_VNEXT_VERSION_REQUIRED"),
        "required_fields": list(fields),
        "field_rules": dict(rules),
        "schema_to_rulesets": normalized_allowed,
    }


def validate_actor_base_profile(profile: Mapping[str, Any], policy: Mapping[str, Any]) -> dict[str, Any]:
    """Return a canonical profile or fail closed without inferring missing truth."""

    profile = _require_mapping(profile, "I2A_PROFILE_MAPPING_REQUIRED")
    policy = _require_mapping(policy, "I2A_POLICY_MAPPING_REQUIRED")
    required_fields = _require_string_list(policy.get("required_fields"), "I2A_POLICY_REQUIRED_FIELDS")
    rules = _require_mapping(policy.get("field_rules"), "I2A_POLICY_FIELD_RULES")
    if set(profile) != set(required_fields):
        raise ValueError("I2A_PROFILE_SHAPE_MISMATCH")
    expected_version = _require_string(policy.get("vnext_profile_contract_version"), "I2A_POLICY_VERSION_REQUIRED")

    for field in required_fields:
        rule = rules.get(field)
        value = profile.get(field)
        if rule == "NONEMPTY_STRING":
            _require_string(value, f"I2A_PROFILE_{field.upper()}_REQUIRED")
        elif rule == "EXACT_VNEXT_PROFILE_CONTRACT_VERSION":
            if value != expected_version:
                raise ValueError("I2A_PROFILE_VERSION_MISMATCH")
        elif rule == "NONEMPTY_MAP":
            if not isinstance(value, Mapping) or not value:
                raise ValueError(f"I2A_PROFILE_{field.upper()}_REQUIRED")
        elif rule == "NONEMPTY_EVENT_REF_LIST":
            _require_string_list(value, f"I2A_PROFILE_{field.upper()}_REQUIRED")
        else:
            raise ValueError("I2A_UNKNOWN_PROFILE_FIELD_RULE")

    schema = profile["profile_schema_ref"]
    ruleset = profile["ruleset_family_ref"]
    allowed = _require_mapping(policy.get("schema_to_rulesets"), "I2A_POLICY_COMPATIBILITY_REQUIRED")
    if ruleset not in set(allowed.get(schema, [])):
        raise ValueError("I2A_PROFILE_SCHEMA_RULESET_MISMATCH")
    return _copy_json_mapping(profile)


def resolve_i2a_feasibility(
    *,
    policy: Mapping[str, Any],
    actor_profile: Mapping[str, Any],
    skill_ledger: Mapping[str, Any],
    action_demand: Mapping[str, Any],
    action_id: str,
) -> dict[str, Any]:
    """Resolve hard feasibility only; no hidden scores, tuning, or stochasticity."""

    profile = validate_actor_base_profile(actor_profile, policy)
    ledger = _require_mapping(skill_ledger, "I2A_SKILL_LEDGER_MAPPING_REQUIRED")
    demand = _require_mapping(action_demand, "I2A_ACTION_DEMAND_MAPPING_REQUIRED")
    if set(ledger) != {"actor_id", "skill_entries", "source_event_cursor", "schema_version"}:
        raise ValueError("I2A_SKILL_LEDGER_SHAPE_MISMATCH")
    if ledger.get("actor_id") != profile["actor_id"]:
        raise ValueError("I2A_SKILL_LEDGER_ACTOR_MISMATCH")
    skills = _require_string_list(ledger.get("skill_entries"), "I2A_SKILL_ENTRIES_REQUIRED")
    _require_string(ledger.get("source_event_cursor"), "I2A_SKILL_CURSOR_REQUIRED")
    _require_string(ledger.get("schema_version"), "I2A_SKILL_SCHEMA_VERSION_REQUIRED")
    if set(demand) != {"demand_id", "action_family", "method_id", "hard_prerequisites", "ruleset_version"}:
        raise ValueError("I2A_ACTION_DEMAND_SHAPE_MISMATCH")
    _require_string(demand.get("demand_id"), "I2A_DEMAND_ID_REQUIRED")
    _require_string(demand.get("action_family"), "I2A_ACTION_FAMILY_REQUIRED")
    method_id = _require_string(demand.get("method_id"), "I2A_METHOD_ID_REQUIRED")
    if demand.get("ruleset_version") != profile["ruleset_family_ref"]:
        raise ValueError("I2A_DEMAND_RULESET_MISMATCH")
    prerequisites = _require_mapping(demand.get("hard_prerequisites"), "I2A_PREREQUISITES_MAPPING_REQUIRED")
    if set(prerequisites) != {"required_attribute_keys", "required_skill_ids"}:
        raise ValueError("I2A_PREREQUISITES_SHAPE_MISMATCH")
    required_attributes = _require_string_list(prerequisites.get("required_attribute_keys"), "I2A_REQUIRED_ATTRIBUTES_REQUIRED")
    required_skills = _require_string_list(prerequisites.get("required_skill_ids"), "I2A_REQUIRED_SKILLS_REQUIRED")
    missing_attributes = sorted(set(required_attributes) - set(profile["base_attribute_map"]))
    missing_skills = sorted(set(required_skills) - set(skills))
    if missing_attributes:
        feasibility = "HARD_FAIL_MISSING_REQUIRED_ATTRIBUTE"
        reason = ",".join(missing_attributes)
    elif missing_skills:
        feasibility = "HARD_FAIL_MISSING_REQUIRED_SKILL"
        reason = ",".join(missing_skills)
    else:
        feasibility = "FEASIBLE"
        reason = None
    receipt = {
        "action_id": _require_string(action_id, "I2A_ACTION_ID_REQUIRED"),
        "method_id": method_id,
        "feasibility": feasibility,
        "failure_reason": reason,
        "effective_capability": "NOT_COMPUTED_IN_I2A",
        "difficulty_or_resistance": "NOT_COMPUTED_IN_I2A",
        "outcome_band": "NOT_RESOLVED_I2A",
        "hazard_outcome": "NOT_EVALUATED_I2A",
        "random_provenance_optional": None,
        "ruleset_version": demand["ruleset_version"],
        "policy_digest": _digest(policy),
        "actor_profile_digest": _digest(profile),
        "skill_ledger_digest": _digest(ledger),
        "action_demand_digest": _digest(demand),
    }
    return receipt


def export_i2a_replay_package(*, policy: Mapping[str, Any], actor_profile: Mapping[str, Any], skill_ledger: Mapping[str, Any], action_demand: Mapping[str, Any], receipt: Mapping[str, Any]) -> bytes:
    """Export canonical I2A inputs plus an already-derived receipt for replay checking."""

    expected = resolve_i2a_feasibility(policy=policy, actor_profile=actor_profile, skill_ledger=skill_ledger, action_demand=action_demand, action_id=_require_string(receipt.get("action_id"), "I2A_ACTION_ID_REQUIRED"))
    if _copy_json_mapping(receipt) != expected:
        raise ValueError("I2A_RECEIPT_DOES_NOT_MATCH_CANONICAL_INPUTS")
    envelope: dict[str, Any] = {
        "profile_id": I2A_PROFILE_ID,
        "profile_version": I2A_PROFILE_VERSION,
        "scope": I2A_SCOPE,
        "policy": _copy_json_mapping(policy),
        "actor_profile": _copy_json_mapping(actor_profile),
        "skill_ledger": _copy_json_mapping(skill_ledger),
        "action_demand": _copy_json_mapping(action_demand),
        "receipt": _copy_json_mapping(receipt),
    }
    envelope["package_digest"] = _digest(envelope)
    return _canonical_json_bytes(envelope)


def import_i2a_replay_package(package: bytes | bytearray | memoryview) -> CapabilityReplayEvidence:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I2A_PACKAGE_BYTES_REQUIRED")
    try:
        decoded = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_json_keys,
            parse_constant=_reject_nonfinite_json_constant,
        )
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("I2A_PACKAGE_JSON_INVALID") from exc
    if not isinstance(decoded, dict) or set(decoded) != _PACKAGE_FIELDS:
        raise ValueError("I2A_PACKAGE_SHAPE_MISMATCH")
    digest = _require_string(decoded["package_digest"], "I2A_PACKAGE_DIGEST_REQUIRED")
    unsigned = dict(decoded)
    del unsigned["package_digest"]
    if not hmac.compare_digest(_digest(unsigned), digest):
        raise ValueError("I2A_PACKAGE_INTEGRITY_FAILURE")
    if decoded["profile_id"] != I2A_PROFILE_ID or decoded["profile_version"] != I2A_PROFILE_VERSION or decoded["scope"] != I2A_SCOPE:
        raise ValueError("I2A_PACKAGE_PROFILE_UNSUPPORTED")
    expected = resolve_i2a_feasibility(policy=decoded["policy"], actor_profile=decoded["actor_profile"], skill_ledger=decoded["skill_ledger"], action_demand=decoded["action_demand"], action_id=_require_string(_require_mapping(decoded["receipt"], "I2A_RECEIPT_MAPPING_REQUIRED").get("action_id"), "I2A_ACTION_ID_REQUIRED"))
    if decoded["receipt"] != expected:
        raise ValueError("I2A_RECEIPT_REPLAY_MISMATCH")
    return CapabilityReplayEvidence(policy=decoded["policy"], actor_profile=decoded["actor_profile"], skill_ledger=decoded["skill_ledger"], action_demand=decoded["action_demand"], receipt=decoded["receipt"], package_digest=digest)


def rehydrate_i2a_replay_package(package: bytes | bytearray | memoryview) -> dict[str, Any]:
    """Replay the package through admission/feasibility and return the receipt."""

    return _copy_json_mapping(import_i2a_replay_package(package).receipt)
