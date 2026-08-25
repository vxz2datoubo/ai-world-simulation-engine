"""Bounded ActorBaseProfile admission and provenance binding for I2A.

This module validates an untrusted AF-C v1.1 ActorBaseProfile-shaped input
against the canonical AF001 machine contract registry. It does not migrate
legacy profiles or implement capability/gameplay resolution.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import json
from pathlib import Path
from typing import Any


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True

_CANONICAL_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
)
_EXPECTED_PROFILE_VERSION = "1.1.0-candidate"
_LEGACY_PROFILE_VERSION = "1.0.0-candidate"


@dataclass(frozen=True)
class ActorBaseProfileAdmissionReceipt:
    actor_id: str
    profile_version: str
    profile_schema_ref: str
    ruleset_family_ref: str
    admitted_base_attribute_map: Mapping[str, Any]
    source_event_refs: tuple[str, ...]
    canonical_contract_id: str
    canonical_contract_version: str


def _require_nonempty_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _find_unique_mapping_by_type_id(root: Any, type_id: str) -> Mapping[str, Any]:
    matches: list[Mapping[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            if value.get("type_id") == type_id:
                matches.append(value)
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)
    if len(matches) != 1:
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
    return matches[0]


def _find_unique_named_mapping(root: Any, key: str) -> Mapping[str, Any]:
    matches: list[Mapping[str, Any]] = []

    def walk(value: Any) -> None:
        if isinstance(value, Mapping):
            if key in value and isinstance(value[key], Mapping):
                matches.append(value[key])
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(root)
    if len(matches) != 1:
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
    return matches[0]


def _load_canonical_authority() -> tuple[str, str, str, Mapping[str, Sequence[str]]]:
    try:
        with _CANONICAL_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_UNAVAILABLE") from None

    if not isinstance(contract, Mapping):
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")

    contract_id = _require_nonempty_string(
        contract.get("contract_id"), "I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID"
    )
    contract_version = _require_nonempty_string(
        contract.get("contract_version"), "I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID"
    )

    profile_type = _find_unique_mapping_by_type_id(contract, "AF001.ActorBaseProfile")
    canonical_profile_version = _require_nonempty_string(
        profile_type.get("version"), "I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID"
    )
    if canonical_profile_version != _EXPECTED_PROFILE_VERSION:
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")

    migration = _find_unique_named_mapping(contract, "actor_base_profile_migration")
    if migration.get("vnext_profile_contract_version") != canonical_profile_version:
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")

    registry = migration.get("profile_schema_ruleset_compatibility_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
    by_schema = registry.get("by_profile_schema_ref")
    if not isinstance(by_schema, Mapping) or not by_schema:
        raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")

    normalized: dict[str, tuple[str, ...]] = {}
    for schema_ref, ruleset_refs in by_schema.items():
        if not isinstance(schema_ref, str) or not schema_ref:
            raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
        if not isinstance(ruleset_refs, list) or not ruleset_refs:
            raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
        if any(not isinstance(ref, str) or not ref for ref in ruleset_refs):
            raise ValueError("I2A_ACTOR_PROFILE_CANONICAL_CONTRACT_INVALID")
        normalized[schema_ref] = tuple(ruleset_refs)

    return contract_id, contract_version, canonical_profile_version, normalized


def _require_source_event_refs(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError("I2A_ACTOR_PROFILE_SOURCE_EVENT_REFS_INVALID")
    refs = tuple(value)
    if not refs or any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError("I2A_ACTOR_PROFILE_SOURCE_EVENT_REFS_INVALID")
    if len(refs) != len(set(refs)):
        raise ValueError("I2A_ACTOR_PROFILE_DUPLICATE_SOURCE_EVENT_REF")
    return refs


def admit_actor_base_profile(profile: Mapping[str, Any]) -> ActorBaseProfileAdmissionReceipt:
    """Admit exactly one AF-C v1.1 ActorBaseProfile or fail closed."""
    if not isinstance(profile, Mapping):
        raise ValueError("I2A_ACTOR_PROFILE_REQUIRED")

    contract_id, contract_version, canonical_profile_version, compatibility = (
        _load_canonical_authority()
    )

    actor_id = _require_nonempty_string(
        profile.get("actor_id"), "I2A_ACTOR_PROFILE_ACTOR_ID_REQUIRED"
    )

    profile_version = profile.get("profile_version")
    if profile_version == _LEGACY_PROFILE_VERSION:
        raise ValueError("I2A_ACTOR_PROFILE_LEGACY_TRANSFORMATION_NOT_AUTHORIZED")
    if profile_version != canonical_profile_version:
        raise ValueError("I2A_ACTOR_PROFILE_VERSION_UNSUPPORTED")

    profile_schema_ref = _require_nonempty_string(
        profile.get("profile_schema_ref"), "I2A_ACTOR_PROFILE_SCHEMA_REF_REQUIRED"
    )
    ruleset_family_ref = _require_nonempty_string(
        profile.get("ruleset_family_ref"), "I2A_ACTOR_PROFILE_RULESET_FAMILY_REF_REQUIRED"
    )

    base_attribute_map = profile.get("base_attribute_map")
    if not isinstance(base_attribute_map, Mapping) or not base_attribute_map:
        raise ValueError("I2A_ACTOR_PROFILE_BASE_ATTRIBUTE_MAP_INVALID")
    try:
        admitted_attributes = deepcopy(dict(base_attribute_map))
    except Exception:
        raise ValueError("I2A_ACTOR_PROFILE_BASE_ATTRIBUTE_MAP_INVALID") from None

    source_event_refs = _require_source_event_refs(profile.get("source_event_refs"))

    allowed_rulesets = compatibility.get(profile_schema_ref)
    if allowed_rulesets is None or ruleset_family_ref not in allowed_rulesets:
        raise ValueError("I2A_ACTOR_PROFILE_SCHEMA_RULESET_INCOMPATIBLE")

    return ActorBaseProfileAdmissionReceipt(
        actor_id=actor_id,
        profile_version=profile_version,
        profile_schema_ref=profile_schema_ref,
        ruleset_family_ref=ruleset_family_ref,
        admitted_base_attribute_map=admitted_attributes,
        source_event_refs=source_event_refs,
        canonical_contract_id=contract_id,
        canonical_contract_version=contract_version,
    )
