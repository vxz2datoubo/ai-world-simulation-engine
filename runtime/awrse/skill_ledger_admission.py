"""Bounded SkillLedger admission and actor binding for I2A.

This module validates an untrusted AF-C SkillLedger-shaped input directly
against the canonical AF001 machine contract and binds it to an already
admitted ActorBaseProfile receipt. It does not implement progression,
balance, gameplay, persistence, migration, or capability resolution.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import json
import math
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .actor_profile_admission import ActorBaseProfileAdmissionReceipt


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True

_CANONICAL_CONTRACT_PATH = (
    Path(__file__).resolve().parents[2] / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
)


@dataclass(frozen=True)
class AdmittedSkillEntry:
    skill_id: str
    value: int | float
    source_event_refs: tuple[str, ...]


@dataclass(frozen=True)
class SkillLedgerAdmissionReceipt:
    actor_id: str
    schema_version: str
    admitted_skill_entries: tuple[AdmittedSkillEntry, ...]
    validated_skill_ledger_values: Mapping[str, int | float]
    source_event_cursor: str
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
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
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
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    return matches[0]


def _require_string_list(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    if any(not isinstance(item, str) or not item for item in value):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    return tuple(value)


def _load_canonical_authority() -> tuple[str, str, str]:
    try:
        with _CANONICAL_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_UNAVAILABLE") from None

    if not isinstance(contract, Mapping):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    contract_id = _require_nonempty_string(
        contract.get("contract_id"), "I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID"
    )
    contract_version = _require_nonempty_string(
        contract.get("contract_version"), "I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID"
    )

    skill_type = _find_unique_mapping_by_type_id(contract, "AF001.SkillLedger")
    admission = _find_unique_named_mapping(contract, "skill_ledger_admission")

    schema_version = _require_nonempty_string(
        skill_type.get("version"), "I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID"
    )
    if admission.get("schema_version") != schema_version:
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    type_fields = _require_string_list(skill_type.get("fields"))
    required_fields = _require_string_list(admission.get("required_fields"))
    if set(type_fields) != set(required_fields):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    if set(required_fields) != {"actor_id", "skill_entries", "source_event_cursor", "schema_version"}:
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    entry_contract = skill_type.get("entry_contract")
    if not isinstance(entry_contract, Mapping):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    type_entry_fields = _require_string_list(entry_contract.get("required_fields"))
    admission_entry_fields = _require_string_list(admission.get("entry_required_fields"))
    if set(type_entry_fields) != set(admission_entry_fields):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    if set(admission_entry_fields) != {"skill_id", "value", "source_event_refs"}:
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    duplicate_policy = admission.get("duplicate_skill_identity_policy")
    if not isinstance(duplicate_policy, str) or not duplicate_policy.startswith("REJECT_FAIL_CLOSED"):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    projection = admission.get("validated_projection")
    if not isinstance(projection, Mapping):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    if projection.get("output_field") != "validated_skill_ledger_values":
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    for flag in (
        "no_authority_gain",
        "no_weighting",
        "no_aggregation",
        "no_range_normalization",
        "no_skill_dropping",
    ):
        if projection.get(flag) is not True:
            raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    type_projection = skill_type.get("projection_contract")
    if not isinstance(type_projection, Mapping):
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")
    if type_projection.get("consumer_field") != projection["output_field"]:
        raise ValueError("I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID")

    return contract_id, contract_version, schema_version


def _require_entry_source_event_refs(value: Any) -> tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise ValueError("I2A_SKILL_ENTRY_SOURCE_EVENT_REFS_INVALID")
    refs = tuple(value)
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError("I2A_SKILL_ENTRY_SOURCE_EVENT_REFS_INVALID")
    return refs


def _require_finite_skill_value(value: Any) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("I2A_SKILL_VALUE_INVALID")
    if isinstance(value, int):
        return value
    if not math.isfinite(value):
        raise ValueError("I2A_SKILL_VALUE_INVALID")
    return value


def admit_skill_ledger(
    ledger: Mapping[str, Any],
    *,
    admitted_actor_profile: ActorBaseProfileAdmissionReceipt,
) -> SkillLedgerAdmissionReceipt:
    """Admit one canonical SkillLedger projection or fail closed."""
    if not isinstance(admitted_actor_profile, ActorBaseProfileAdmissionReceipt):
        raise ValueError("I2A_ADMITTED_ACTOR_PROFILE_REQUIRED")
    if not isinstance(admitted_actor_profile.actor_id, str) or not admitted_actor_profile.actor_id.strip():
        raise ValueError("I2A_ADMITTED_ACTOR_PROFILE_INVALID")

    if not isinstance(ledger, Mapping):
        raise ValueError("I2A_SKILL_LEDGER_REQUIRED")

    contract_id, contract_version, canonical_schema_version = _load_canonical_authority()
    if (
        admitted_actor_profile.canonical_contract_id != contract_id
        or admitted_actor_profile.canonical_contract_version != contract_version
    ):
        raise ValueError("I2A_ADMITTED_ACTOR_PROFILE_CONTRACT_MISMATCH")

    actor_id = _require_nonempty_string(
        ledger.get("actor_id"), "I2A_SKILL_LEDGER_ACTOR_ID_REQUIRED"
    )
    if actor_id != admitted_actor_profile.actor_id:
        raise ValueError("I2A_SKILL_LEDGER_ACTOR_BINDING_MISMATCH")

    schema_version = ledger.get("schema_version")
    if not isinstance(schema_version, str) or not schema_version.strip():
        raise ValueError("I2A_SKILL_LEDGER_SCHEMA_VERSION_REQUIRED")
    if schema_version != canonical_schema_version:
        raise ValueError("I2A_SKILL_LEDGER_SCHEMA_VERSION_UNSUPPORTED")

    source_event_cursor = _require_nonempty_string(
        ledger.get("source_event_cursor"), "I2A_SKILL_LEDGER_SOURCE_EVENT_CURSOR_REQUIRED"
    )

    skill_entries = ledger.get("skill_entries")
    if not isinstance(skill_entries, list) or not skill_entries:
        raise ValueError("I2A_SKILL_LEDGER_ENTRIES_INVALID")

    admitted_entries: list[AdmittedSkillEntry] = []
    validated_values: dict[str, int | float] = {}
    for entry in skill_entries:
        if not isinstance(entry, Mapping):
            raise ValueError("I2A_SKILL_ENTRY_INVALID")
        skill_id = _require_nonempty_string(entry.get("skill_id"), "I2A_SKILL_ID_REQUIRED")
        if skill_id in validated_values:
            raise ValueError("I2A_DUPLICATE_SKILL_ID")
        value = _require_finite_skill_value(entry.get("value"))
        source_event_refs = _require_entry_source_event_refs(entry.get("source_event_refs"))
        admitted_entry = AdmittedSkillEntry(
            skill_id=skill_id,
            value=value,
            source_event_refs=source_event_refs,
        )
        admitted_entries.append(admitted_entry)
        validated_values[skill_id] = value

    return SkillLedgerAdmissionReceipt(
        actor_id=actor_id,
        schema_version=schema_version,
        admitted_skill_entries=tuple(admitted_entries),
        validated_skill_ledger_values=MappingProxyType(dict(validated_values)),
        source_event_cursor=source_event_cursor,
        canonical_contract_id=contract_id,
        canonical_contract_version=contract_version,
    )
