"""Bounded ActionDemandProfile admission and resolver projection for I2A.

This module validates an untrusted AF-C ActionDemandProfile-shaped input
against the canonical AF001 machine contract and its parent-registered
ActionDemand projection binding. It materializes only the frozen,
non-authoritative resolver projection. It does not implement gameplay,
weighting, difficulty formulas, probability, hazard, persistence, or migration.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True

_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_PROJECTION_BINDING_PATH = _ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
_CONTRACT_RELATIVE_PATH = "contracts/AF001-LIVING-STORY-CONTRACTS.json"
_BINDING_RELATIVE_PATH = "contracts/AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
_EXPECTED_AUTHORITY_LOCKS = {
    "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
    "NO_I2_RUNTIME_IMPLEMENTED": True,
    "RUNTIME_SEMANTICS_UNCHANGED": True,
}
_EXPECTED_DEMAND_FIELDS = {
    "demand_id",
    "action_family",
    "method_id",
    "hard_prerequisites",
    "attribute_weights",
    "skill_weights",
    "required_body_functions",
    "hazard_profile",
    "ruleset_version",
}
_EXPECTED_PROVENANCE_FIELDS = {
    "source_demand_ref",
    "demand_id",
    "action_family",
    "method_id",
    "ruleset_version",
    "difficulty_source_ref",
    "replay_input_ref",
    "hard_prerequisite_receipt_ref",
}


@dataclass(frozen=True)
class ActionDemandAdmissionReceipt:
    demand_id: str
    action_family: str
    method_id: str
    ruleset_version: str
    hard_prerequisites: tuple[str, ...]
    required_body_functions: tuple[str, ...]
    required_attributes: tuple[str, ...]
    required_skills: tuple[str, ...]
    difficulty_or_resistance: int | float
    provenance: Mapping[str, str]
    canonical_contract_id: str
    canonical_contract_version: str
    binding_id: str
    binding_version: str
    resolver_projection: Mapping[str, Any]


def _require_nonempty_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _load_json(path: Path, unavailable_error: str) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise ValueError(unavailable_error) from None
    if not isinstance(value, Mapping):
        raise ValueError(unavailable_error.replace("UNAVAILABLE", "INVALID"))
    return value


def _load_canonical_authority() -> tuple[str, str, str, str]:
    contract = _load_json(
        _CANONICAL_CONTRACT_PATH,
        "I2A_ACTION_DEMAND_CANONICAL_CONTRACT_UNAVAILABLE",
    )
    binding = _load_json(
        _PROJECTION_BINDING_PATH,
        "I2A_ACTION_DEMAND_CANONICAL_BINDING_UNAVAILABLE",
    )

    contract_error = "I2A_ACTION_DEMAND_CANONICAL_CONTRACT_INVALID"
    binding_error = "I2A_ACTION_DEMAND_CANONICAL_BINDING_INVALID"

    contract_id = _require_nonempty_string(contract.get("contract_id"), contract_error)
    contract_version = _require_nonempty_string(contract.get("contract_version"), contract_error)
    artifact_roles = contract.get("artifact_roles")
    if not isinstance(artifact_roles, Mapping) or artifact_roles.get(_CONTRACT_RELATIVE_PATH) != "MACHINE_CONTRACT_REGISTRY":
        raise ValueError(contract_error)

    type_registry = contract.get("type_registry")
    if not isinstance(type_registry, Mapping):
        raise ValueError(contract_error)
    demand_type = type_registry.get("ActionDemandProfile")
    if not isinstance(demand_type, Mapping):
        raise ValueError(contract_error)
    if demand_type.get("type_id") != "AF001.ActionDemandProfile":
        raise ValueError(contract_error)
    demand_type_version = _require_nonempty_string(demand_type.get("version"), contract_error)
    demand_fields = demand_type.get("fields")
    if not isinstance(demand_fields, list) or set(demand_fields) != _EXPECTED_DEMAND_FIELDS:
        raise ValueError(contract_error)

    binding_id = _require_nonempty_string(binding.get("binding_id"), binding_error)
    binding_version = _require_nonempty_string(binding.get("binding_version"), binding_error)

    registrations = contract.get("registered_contract_extensions")
    if not isinstance(registrations, Mapping):
        raise ValueError(binding_error)
    registration = registrations.get(binding_id)
    if not isinstance(registration, Mapping):
        raise ValueError(binding_error)
    if (
        registration.get("path") != _BINDING_RELATIVE_PATH
        or registration.get("binding_version") != binding_version
        or registration.get("parent_contract_id") != contract_id
        or registration.get("parent_contract_version") != contract_version
        or registration.get("authority") != "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        or registration.get("runtime_implementation_authorized") is not False
    ):
        raise ValueError(binding_error)

    authority_rule = contract.get("contract_extension_authority_rule")
    if not isinstance(authority_rule, str) or "CHILD_TO_PARENT_SELF_DECLARATION_ALONE_CONFERS_NO_AUTHORITY" not in authority_rule:
        raise ValueError(binding_error)

    parent = binding.get("parent_machine_contract")
    if not isinstance(parent, Mapping):
        raise ValueError(binding_error)
    if (
        parent.get("path") != _CONTRACT_RELATIVE_PATH
        or parent.get("contract_id") != contract_id
        or parent.get("contract_version") != contract_version
        or parent.get("type_ref") != "AF001.ActionDemandProfile"
        or parent.get("type_version") != demand_type_version
    ):
        raise ValueError(binding_error)

    if binding.get("runtime_implementation_authorized") is not False:
        raise ValueError(binding_error)
    if binding.get("authority_locks") != _EXPECTED_AUTHORITY_LOCKS:
        raise ValueError(binding_error)

    decisions = binding.get("canonical_decisions")
    projection = binding.get("projection_schema")
    if not isinstance(decisions, Mapping) or not isinstance(projection, Mapping):
        raise ValueError(binding_error)
    if (
        decisions.get("resolver_projection_authorized") is not True
        or decisions.get("projection_is_non_authoritative") is not True
        or decisions.get("weight_values_consumed") is not False
        or decisions.get("required_attributes_source")
        != "CANONICALLY_SORTED_KEYS_OF_ActionDemandProfile.attribute_weights_ONLY"
        or decisions.get("required_skills_source")
        != "CANONICALLY_SORTED_KEYS_OF_ActionDemandProfile.skill_weights_ONLY"
        or decisions.get("difficulty_source")
        != "CAPABILITY_STATE_RESOLUTION_VERSIONED_DEMAND_BINDING"
    ):
        raise ValueError(binding_error)
    if projection.get("consumer") != "runtime.awrse.capability_resolution.resolve_capability":
        raise ValueError(binding_error)
    if projection.get("consumer_fields") != [
        "required_attributes",
        "required_skills",
        "difficulty_or_resistance",
    ]:
        raise ValueError(binding_error)
    required_provenance = projection.get("required_provenance")
    if not isinstance(required_provenance, list) or set(required_provenance) != _EXPECTED_PROVENANCE_FIELDS:
        raise ValueError(binding_error)

    versioning = contract.get("versioning_and_migration")
    lineage = versioning.get("contract_version_lineage") if isinstance(versioning, Mapping) else None
    if not isinstance(lineage, Mapping):
        raise ValueError(binding_error)
    previous_version = lineage.get("previous_contract_version")
    semantic_delta = lineage.get("semantic_delta")
    if (
        not isinstance(previous_version, str)
        or previous_version == contract_version
        or not isinstance(semantic_delta, list)
        or "ACTION_DEMAND_PROJECTION_BINDING_CANONICAL_EXTENSION_REGISTRATION" not in semantic_delta
    ):
        raise ValueError(binding_error)

    return contract_id, contract_version, binding_id, binding_version


def _require_hard_prerequisites(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError("I2A_DEMAND_BINDING_MALFORMED")
    refs = tuple(value)
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError("I2A_DEMAND_BINDING_MALFORMED")
    if len(refs) != len(set(refs)):
        raise ValueError("I2A_DUPLICATE_DEMAND_REFERENCE")
    return refs


def _canonical_string_refs(value: Any, error: str) -> tuple[str, ...]:
    if not isinstance(value, list):
        raise ValueError(error)
    refs = tuple(value)
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError(error)
    return tuple(sorted(refs))


def _canonical_mapping_keys(value: Any, error: str) -> tuple[str, ...]:
    if not isinstance(value, Mapping):
        raise ValueError(error)
    try:
        keys = tuple(value.keys())
    except Exception:
        raise ValueError(error) from None
    if any(not isinstance(key, str) or not key.strip() for key in keys):
        raise ValueError(error)
    return tuple(sorted(keys))


def _require_finite_number(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("I2A_DEMAND_DIFFICULTY_INVALID")
    if isinstance(value, int):
        return value
    if not math.isfinite(value):
        raise ValueError("I2A_DEMAND_DIFFICULTY_INVALID")
    return value


def admit_action_demand(
    demand: Mapping[str, Any],
    *,
    source_demand_ref: str,
    hard_prerequisite_receipt_ref: str,
    replay_input_ref: str,
    difficulty_binding: Mapping[str, Any],
) -> ActionDemandAdmissionReceipt:
    """Admit one canonical ActionDemandProfile resolver projection or fail closed."""
    if not isinstance(demand, Mapping):
        raise ValueError("I2A_ACTION_DEMAND_PROFILE_REQUIRED")

    contract_id, contract_version, binding_id, binding_version = _load_canonical_authority()

    demand_id = _require_nonempty_string(demand.get("demand_id"), "I2A_DEMAND_BINDING_MALFORMED")
    action_family = _require_nonempty_string(demand.get("action_family"), "I2A_DEMAND_BINDING_MALFORMED")
    method_id = _require_nonempty_string(demand.get("method_id"), "I2A_DEMAND_BINDING_MALFORMED")
    ruleset_version = _require_nonempty_string(demand.get("ruleset_version"), "I2A_DEMAND_BINDING_MALFORMED")

    hard_prerequisites = _require_hard_prerequisites(demand.get("hard_prerequisites"))
    required_body_functions = _canonical_string_refs(
        demand.get("required_body_functions"), "I2A_DEMAND_BINDING_MALFORMED"
    )
    required_attributes = _canonical_mapping_keys(
        demand.get("attribute_weights"), "I2A_REQUIRED_ATTRIBUTES_INVALID"
    )
    required_skills = _canonical_mapping_keys(
        demand.get("skill_weights"), "I2A_REQUIRED_SKILLS_INVALID"
    )
    if not required_attributes and not required_skills:
        raise ValueError("I2A_EMPTY_BOUNDED_DEMAND_REFERENCE_SET")

    prerequisite_ref = _require_nonempty_string(
        hard_prerequisite_receipt_ref,
        "I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED",
    )
    if hard_prerequisites:
        if prerequisite_ref == "NOT_APPLICABLE":
            raise ValueError("I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED")
    elif prerequisite_ref != "NOT_APPLICABLE":
        raise ValueError("I2A_HARD_PREREQUISITE_ATTESTATION_REQUIRED")

    if not isinstance(difficulty_binding, Mapping):
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")
    identity = {
        "demand_id": demand_id,
        "action_family": action_family,
        "method_id": method_id,
        "ruleset_version": ruleset_version,
    }
    if any(difficulty_binding.get(field) != value for field, value in identity.items()):
        raise ValueError("I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH")
    difficulty_source_ref = _require_nonempty_string(
        difficulty_binding.get("difficulty_source_ref"),
        "I2A_DEMAND_DIFFICULTY_BINDING_MISMATCH",
    )
    if "difficulty_or_resistance" not in difficulty_binding:
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")
    difficulty = _require_finite_number(difficulty_binding["difficulty_or_resistance"])

    source_ref = _require_nonempty_string(source_demand_ref, "I2A_DEMAND_BINDING_MALFORMED")
    replay_ref = _require_nonempty_string(replay_input_ref, "I2A_DEMAND_BINDING_MALFORMED")

    provenance = MappingProxyType(
        {
            "source_demand_ref": source_ref,
            "demand_id": demand_id,
            "action_family": action_family,
            "method_id": method_id,
            "ruleset_version": ruleset_version,
            "difficulty_source_ref": difficulty_source_ref,
            "replay_input_ref": replay_ref,
            "hard_prerequisite_receipt_ref": prerequisite_ref,
        }
    )
    resolver_projection = MappingProxyType(
        {
            "required_attributes": required_attributes,
            "required_skills": required_skills,
            "difficulty_or_resistance": difficulty,
        }
    )

    return ActionDemandAdmissionReceipt(
        demand_id=demand_id,
        action_family=action_family,
        method_id=method_id,
        ruleset_version=ruleset_version,
        hard_prerequisites=hard_prerequisites,
        required_body_functions=required_body_functions,
        required_attributes=required_attributes,
        required_skills=required_skills,
        difficulty_or_resistance=difficulty,
        provenance=provenance,
        canonical_contract_id=contract_id,
        canonical_contract_version=contract_version,
        binding_id=binding_id,
        binding_version=binding_version,
        resolver_projection=resolver_projection,
    )
