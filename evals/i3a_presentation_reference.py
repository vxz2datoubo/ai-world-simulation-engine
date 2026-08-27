"""Bounded I3A actor-presentation replay and mock render-continuity reference.

This module consumes already-frozen AF-D presentation interfaces plus explicit
upstream-prevalidated identity evidence. It does not mint View/asset identity,
does not treat eval fixtures as instance authority, and remains isolated from
the canonical runtime loop.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from copy import deepcopy
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse.model import freeze_value, thaw_value

I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_REAL_RENDERER_IMPLEMENTED = True
NO_PROVIDER_INTEGRATION = True

_ROOT = Path(__file__).resolve().parents[1]
_CANONICAL_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_NONAUTHORITY_EVAL_STATUS = "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
_PREVALIDATED_STATUS = "UPSTREAM_PREVALIDATED_IDENTITY_EVIDENCE"
_EXPECTED_TYPES = {
    "ActorPresentationState": ("AF001.ActorPresentationState", "1.0.0-candidate", "PRESENTATION_CANONICAL_STATE"),
    "OutfitState": ("AF001.OutfitState", "1.0.0-candidate", "PRESENTATION_CANONICAL_STATE"),
    "DressingState": ("AF001.DressingState", "1.0.0-candidate", "PRESENTATION_CANONICAL_STATE"),
    "SurfaceState": ("AF001.SurfaceState", "1.0.0-candidate", "PRESENTATION_CANONICAL_STATE"),
    "ActorAppearanceSnapshot": ("AF001.ActorAppearanceSnapshot", "1.0.0-candidate", "PRESENTATION_CANONICAL_STATE"),
    "View": ("AF001.View", "1.0.0-candidate", "SPATIAL_VIEW_DEFINITION_REGISTRY"),
    "MediaAsset": ("AF001.MediaAsset", "1.0.0-candidate", "ASSET_LOGICAL_IDENTITY_REGISTRY"),
    "MediaVersion": ("AF001.MediaVersion", "1.0.0-candidate", "ASSET_IMMUTABLE_VERSION_REGISTRY"),
    "Locator": ("AF001.Locator", "1.0.0-candidate", "ASSET_LOCATOR_RESOLUTION"),
}
_REQUIRED_AF_D_INVARIANTS = {
    "FUNCTIONAL_INJURY_NE_VISIBLE_TREATMENT",
    "CAMERA_POSITION_NE_CAMERA_FACING",
    "MEDIA_ASSET_IDENTITY_NE_MEDIA_VERSION_NE_LOCATOR",
    "DYNAMIC_PRESENTATION_STATE_NE_ASSET_REGISTRY_TRUTH",
    "LOCATOR_MIGRATION_NE_ASSET_OR_VERSION_IDENTITY_CHANGE",
    "GENERATED_PIXELS_CANNOT_CREATE_CANONICAL_STATE",
    "INVENTORY_OWNED_NE_WORN",
}
_DYNAMIC_ASSET_FIELDS = {
    "outfit_state_ref", "dressing_state_refs", "surface_state_refs", "body_region",
    "side", "appearance_state", "worn", "slot_bindings", "presentation_state_ref",
}
_ALLOWED_EVENT_KINDS = {
    "WEAR_SLOT", "CLEAR_SLOT", "APPLY_DRESSING", "REMOVE_DRESSING",
    "SET_SURFACE", "CLEAR_SURFACE",
}
_ALLOWED_SIDES = {"LEFT", "RIGHT", "MIDLINE"}


def _require_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _require_sequence(value: Any, error: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(error)
    return tuple(value)


def _canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def _json_normalized(value: Any) -> Any:
    return json.loads(_canonical_json(value))


def _load_authority() -> tuple[str, str, Mapping[str, Any]]:
    try:
        with _CANONICAL_CONTRACT_PATH.open("r", encoding="utf-8") as handle:
            contract = json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise ValueError("I3A_CANONICAL_CONTRACT_UNAVAILABLE") from None
    if not isinstance(contract, Mapping):
        raise ValueError("I3A_CANONICAL_CONTRACT_INVALID")
    contract_id = _require_string(contract.get("contract_id"), "I3A_CANONICAL_CONTRACT_INVALID")
    contract_version = _require_string(contract.get("contract_version"), "I3A_CANONICAL_CONTRACT_INVALID")
    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I3A_CANONICAL_CONTRACT_INVALID")
    for name, expected in _EXPECTED_TYPES.items():
        entry = registry.get(name)
        if not isinstance(entry, Mapping):
            raise ValueError(f"I3A_CANONICAL_TYPE_MISSING:{name}")
        actual = (entry.get("type_id"), entry.get("version"), entry.get("authority_profile_ref"))
        if actual != expected:
            raise ValueError(f"I3A_CANONICAL_TYPE_DRIFT:{name}")
    af_d = contract.get("freeze_domains", {}).get("AF-D")
    if not isinstance(af_d, Mapping):
        raise ValueError("I3A_AF_D_AUTHORITY_MISSING")
    if not _REQUIRED_AF_D_INVARIANTS <= set(af_d.get("invariants", [])):
        raise ValueError("I3A_AF_D_INVARIANT_DRIFT")
    return contract_id, contract_version, registry


def _consume_prevalidated_identity_evidence(
    evidence: Any,
    contract_id: str,
    contract_version: str,
) -> tuple[frozenset[str], frozenset[tuple[str, str, str]], str, str]:
    """Consume an upstream trust-boundary result without minting/admitting it locally.

    This function validates the *shape and authority identity* of evidence that
    upstream has already admitted. It does not authenticate the upstream issuer
    and therefore must never be described as an AF-D admission authority.
    """
    if not isinstance(evidence, Mapping):
        raise ValueError("I3A_PREVALIDATED_IDENTITY_EVIDENCE_REQUIRED")
    status = evidence.get("status")
    if status in {_NONAUTHORITY_EVAL_STATUS, "NONCANONICAL_EVAL_ONLY"}:
        raise ValueError("I3A_NONAUTHORITY_EVAL_CANNOT_MINT_IDENTITY_ADMISSION")
    if status != _PREVALIDATED_STATUS:
        raise ValueError("I3A_PREVALIDATED_IDENTITY_EVIDENCE_STATUS_INVALID")
    identity = evidence.get("authority_identity")
    if not isinstance(identity, Mapping):
        raise ValueError("I3A_PREVALIDATED_IDENTITY_AUTHORITY_REQUIRED")
    if (
        identity.get("canonical_contract_id") != contract_id
        or identity.get("canonical_contract_version") != contract_version
    ):
        raise ValueError("I3A_PREVALIDATED_IDENTITY_PARENT_DRIFT")
    expected_profiles = {
        "view_authority_profile_ref": _EXPECTED_TYPES["View"][2],
        "asset_authority_profile_ref": _EXPECTED_TYPES["MediaAsset"][2],
        "version_authority_profile_ref": _EXPECTED_TYPES["MediaVersion"][2],
        "locator_authority_profile_ref": _EXPECTED_TYPES["Locator"][2],
    }
    for field, expected in expected_profiles.items():
        if identity.get(field) != expected:
            raise ValueError(f"I3A_PREVALIDATED_IDENTITY_AUTHORITY_DRIFT:{field}")
    authority_ref = _require_string(
        identity.get("admission_authority_ref"),
        "I3A_PREVALIDATED_IDENTITY_AUTHORITY_REF_REQUIRED",
    )
    if authority_ref == "evals/AF001-ASSET-SPATIAL-CONFORMANCE.json":
        raise ValueError("I3A_NONAUTHORITY_EVAL_CANNOT_MINT_IDENTITY_ADMISSION")

    views = frozenset(
        _require_string(v, "I3A_PREVALIDATED_VIEW_ID_INVALID")
        for v in _require_sequence(
            evidence.get("admitted_view_ids"),
            "I3A_PREVALIDATED_VIEW_IDS_REQUIRED",
        )
    )
    if not views:
        raise ValueError("I3A_PREVALIDATED_VIEW_IDS_EMPTY")

    bindings: set[tuple[str, str, str]] = set()
    for row in _require_sequence(
        evidence.get("admitted_asset_bindings"),
        "I3A_PREVALIDATED_ASSET_BINDINGS_REQUIRED",
    ):
        if not isinstance(row, Mapping):
            raise ValueError("I3A_PREVALIDATED_ASSET_BINDING_INVALID")
        binding = (
            _require_string(row.get("media_asset_id"), "I3A_PREVALIDATED_MEDIA_ASSET_ID_INVALID"),
            _require_string(row.get("media_version_id"), "I3A_PREVALIDATED_MEDIA_VERSION_ID_INVALID"),
            _require_string(row.get("locator_id"), "I3A_PREVALIDATED_LOCATOR_ID_INVALID"),
        )
        if binding in bindings:
            raise ValueError("I3A_DUPLICATE_PREVALIDATED_ASSET_BINDING")
        bindings.add(binding)
    if not bindings:
        raise ValueError("I3A_PREVALIDATED_ASSET_BINDINGS_EMPTY")

    digest = hashlib.sha256(
        _canonical_json(_json_normalized(evidence)).encode("utf-8")
    ).hexdigest()
    return views, frozenset(bindings), authority_ref, digest


@dataclass(frozen=True)
class PresentationReference:
    actor_id: str
    contract_id: str
    contract_version: str
    world_event_cursor: int
    view_id: str
    identity_admission_authority_ref: str
    identity_evidence_sha256: str
    outfit_state: Mapping[str, Any]
    dressing_states: tuple[Mapping[str, Any], ...]
    surface_states: tuple[Mapping[str, Any], ...]
    presentation_state: Mapping[str, Any]
    appearance_snapshot: Mapping[str, Any]
    source_event_ids: tuple[str, ...]


@dataclass(frozen=True)
class MockRenderValidation:
    status: str
    contradictions: tuple[str, ...] = ()
    unauthorized_claims: tuple[str, ...] = ()


def _normalize_inventory(value: Any) -> frozenset[str]:
    refs = _require_sequence(value, "I3A_INVENTORY_REFS_INVALID")
    normalized = [_require_string(ref, "I3A_INVENTORY_REF_INVALID") for ref in refs]
    if len(normalized) != len(set(normalized)):
        raise ValueError("I3A_DUPLICATE_INVENTORY_REF")
    return frozenset(normalized)


def _validate_asset_registry(
    asset_registry: Any,
    admitted_bindings: frozenset[tuple[str, str, str]],
) -> None:
    if not isinstance(asset_registry, Mapping):
        raise ValueError("I3A_ASSET_REGISTRY_REQUIRED")
    for object_ref, record in asset_registry.items():
        _require_string(object_ref, "I3A_ASSET_OBJECT_REF_INVALID")
        if not isinstance(record, Mapping):
            raise ValueError("I3A_ASSET_RECORD_INVALID")
        if _DYNAMIC_ASSET_FIELDS & set(record):
            raise ValueError("I3A_DYNAMIC_PRESENTATION_CONTAMINATES_ASSET_REGISTRY")
        binding = (
            _require_string(record.get("media_asset_id"), "I3A_MEDIA_ASSET_ID_REQUIRED"),
            _require_string(record.get("media_version_id"), "I3A_MEDIA_VERSION_ID_REQUIRED"),
            _require_string(record.get("locator_id"), "I3A_LOCATOR_ID_REQUIRED"),
        )
        if binding not in admitted_bindings:
            raise ValueError(f"I3A_ASSET_BINDING_NOT_ADMITTED:{object_ref}")


def _event_common(event: Any, actor_id: str, previous_cursor: int) -> tuple[str, int, str]:
    if not isinstance(event, Mapping):
        raise ValueError("I3A_EVENT_INVALID")
    event_id = _require_string(event.get("event_id"), "I3A_EVENT_ID_REQUIRED")
    if event.get("actor_id") != actor_id:
        raise ValueError(f"I3A_EVENT_ACTOR_MISMATCH:{event_id}")
    cursor = event.get("cursor")
    if isinstance(cursor, bool) or not isinstance(cursor, int) or cursor <= previous_cursor:
        raise ValueError(f"I3A_EVENT_CURSOR_INVALID:{event_id}")
    kind = event.get("kind")
    if kind not in _ALLOWED_EVENT_KINDS:
        raise ValueError(f"I3A_EVENT_KIND_INVALID:{event_id}")
    return event_id, cursor, kind


def build_presentation_reference(
    *,
    actor_id: str,
    events: Sequence[Mapping[str, Any]],
    inventory_object_refs: Sequence[str],
    asset_registry: Mapping[str, Mapping[str, Any]],
    view_id: str,
    identity_evidence: Mapping[str, Any],
    valid_view_ids: Sequence[str] | None = None,
    schema_version: str = "1.0.0-candidate",
    ruleset_version: str = "AF-D-PRESENTATION-REFERENCE-1",
) -> PresentationReference:
    """Rebuild presentation state from transitions plus upstream-admitted identities.

    ``identity_evidence`` is a declared external trust boundary. I3A validates
    its shape/authority identity and consumes the already-admitted identities;
    I3A does not authenticate, register, or mint that admission.
    ``valid_view_ids`` is a legacy caller hint and has no admission power.
    """
    contract_id, contract_version, _ = _load_authority()
    admitted_views, admitted_bindings, authority_ref, evidence_digest = (
        _consume_prevalidated_identity_evidence(
            identity_evidence,
            contract_id,
            contract_version,
        )
    )
    actor_id = _require_string(actor_id, "I3A_ACTOR_ID_REQUIRED")
    view_id = _require_string(view_id, "I3A_VIEW_ID_REQUIRED")
    if valid_view_ids is not None:
        _require_sequence(valid_view_ids, "I3A_VIEW_HINTS_INVALID")
    if view_id not in admitted_views:
        raise ValueError("I3A_VIEW_NOT_ADMITTED")
    schema_version = _require_string(schema_version, "I3A_SCHEMA_VERSION_REQUIRED")
    ruleset_version = _require_string(ruleset_version, "I3A_RULESET_VERSION_REQUIRED")
    inventory = _normalize_inventory(inventory_object_refs)
    _validate_asset_registry(asset_registry, admitted_bindings)
    ordered_events = _require_sequence(events, "I3A_EVENTS_INVALID")
    if not ordered_events:
        raise ValueError("I3A_EVENTS_REQUIRED")

    slots: dict[str, str] = {}
    dressings: dict[str, dict[str, Any]] = {}
    surfaces: dict[str, dict[str, Any]] = {}
    source_event_ids: list[str] = []
    seen_event_ids: set[str] = set()
    outfit_source_refs: list[str] = []
    previous_cursor = -1

    for raw_event in ordered_events:
        event_id, cursor, kind = _event_common(raw_event, actor_id, previous_cursor)
        previous_cursor = cursor
        if event_id in seen_event_ids:
            raise ValueError(f"I3A_DUPLICATE_EVENT_ID:{event_id}")
        seen_event_ids.add(event_id)
        source_event_ids.append(event_id)

        if kind == "WEAR_SLOT":
            slot = _require_string(raw_event.get("slot"), f"I3A_OUTFIT_SLOT_REQUIRED:{event_id}")
            object_ref = _require_string(raw_event.get("object_ref"), f"I3A_WEAR_OBJECT_REQUIRED:{event_id}")
            if object_ref not in inventory:
                raise ValueError(f"I3A_WORN_OBJECT_NOT_POSSESSED:{object_ref}")
            if object_ref not in asset_registry:
                raise ValueError(f"I3A_WORN_OBJECT_ASSET_UNKNOWN:{object_ref}")
            slots[slot] = object_ref
            outfit_source_refs.append(event_id)
        elif kind == "CLEAR_SLOT":
            slot = _require_string(raw_event.get("slot"), f"I3A_OUTFIT_SLOT_REQUIRED:{event_id}")
            slots.pop(slot, None)
            outfit_source_refs.append(event_id)
        elif kind == "APPLY_DRESSING":
            dressing_id = _require_string(raw_event.get("dressing_id"), f"I3A_DRESSING_ID_REQUIRED:{event_id}")
            if raw_event.get("source_treatment_event_ref", event_id) != event_id:
                raise ValueError(f"I3A_DRESSING_TREATMENT_PROVENANCE_MISMATCH:{dressing_id}")
            material_ref = _require_string(raw_event.get("material_ref"), f"I3A_DRESSING_MATERIAL_REQUIRED:{event_id}")
            if material_ref not in asset_registry:
                raise ValueError(f"I3A_DRESSING_ASSET_UNKNOWN:{material_ref}")
            side = _require_string(raw_event.get("side"), f"I3A_SIDE_REQUIRED:{event_id}")
            if side not in _ALLOWED_SIDES:
                raise ValueError(f"I3A_SIDE_INVALID:{event_id}")
            appearance_state = raw_event.get("appearance_state")
            if not isinstance(appearance_state, Mapping):
                raise ValueError(f"I3A_DRESSING_APPEARANCE_INVALID:{event_id}")
            covered = tuple(
                _require_string(ref, f"I3A_DRESSING_COVER_REF_INVALID:{event_id}")
                for ref in _require_sequence(
                    raw_event.get("covered_by_refs", ()),
                    f"I3A_DRESSING_COVER_REFS_INVALID:{event_id}",
                )
            )
            dressings[dressing_id] = {
                "dressing_id": dressing_id,
                "actor_id": actor_id,
                "body_region": _require_string(raw_event.get("body_region"), f"I3A_BODY_REGION_REQUIRED:{event_id}"),
                "side": side,
                "material_ref": material_ref,
                "appearance_state": deepcopy(dict(appearance_state)),
                "source_treatment_event_ref": event_id,
                "covered_by_refs": covered,
            }
        elif kind == "REMOVE_DRESSING":
            dressing_id = _require_string(raw_event.get("dressing_id"), f"I3A_DRESSING_ID_REQUIRED:{event_id}")
            if dressing_id not in dressings:
                raise ValueError(f"I3A_REMOVE_UNKNOWN_DRESSING:{dressing_id}")
            del dressings[dressing_id]
        elif kind == "SET_SURFACE":
            surface_id = _require_string(raw_event.get("surface_state_id"), f"I3A_SURFACE_ID_REQUIRED:{event_id}")
            target_ref = _require_string(raw_event.get("target_ref"), f"I3A_SURFACE_TARGET_REQUIRED:{event_id}")
            intensity = raw_event.get("intensity")
            if isinstance(intensity, bool) or not isinstance(intensity, (int, float)) or not 0 <= intensity <= 1:
                raise ValueError(f"I3A_SURFACE_INTENSITY_INVALID:{event_id}")
            surfaces[surface_id] = {
                "surface_state_id": surface_id,
                "target_ref": target_ref,
                "surface_type": _require_string(raw_event.get("surface_type"), f"I3A_SURFACE_TYPE_REQUIRED:{event_id}"),
                "intensity": intensity,
                "source_event_refs": (event_id,),
            }
        elif kind == "CLEAR_SURFACE":
            surface_id = _require_string(raw_event.get("surface_state_id"), f"I3A_SURFACE_ID_REQUIRED:{event_id}")
            if surface_id not in surfaces:
                raise ValueError(f"I3A_CLEAR_UNKNOWN_SURFACE:{surface_id}")
            del surfaces[surface_id]

    cursor = previous_cursor
    outfit_ref = f"outfit://{actor_id}@{cursor}"
    presentation_ref = f"presentation://{actor_id}@{cursor}"
    outfit_state = {
        "actor_id": actor_id,
        "slot_bindings": dict(sorted(slots.items())),
        "source_event_refs": tuple(outfit_source_refs),
        "state_version": str(cursor),
    }
    dressing_states_raw = tuple(deepcopy(dressings[key]) for key in sorted(dressings))
    surface_states_raw = tuple(deepcopy(surfaces[key]) for key in sorted(surfaces))
    presentation_state = {
        "actor_id": actor_id,
        "outfit_state_ref": outfit_ref,
        "dressing_state_refs": tuple(item["dressing_id"] for item in dressing_states_raw),
        "surface_state_refs": tuple(item["surface_state_id"] for item in surface_states_raw),
        "visible_equipment_refs": tuple(sorted(set(slots.values()))),
        "state_version": str(cursor),
    }
    snapshot = {
        "actor_id": actor_id,
        "presentation_state_ref": presentation_ref,
        "world_event_cursor": cursor,
        "schema_version": schema_version,
        "ruleset_version": ruleset_version,
    }
    return PresentationReference(
        actor_id=actor_id,
        contract_id=contract_id,
        contract_version=contract_version,
        world_event_cursor=cursor,
        view_id=view_id,
        identity_admission_authority_ref=authority_ref,
        identity_evidence_sha256=evidence_digest,
        outfit_state=freeze_value(outfit_state),
        dressing_states=tuple(freeze_value(item) for item in dressing_states_raw),
        surface_states=tuple(freeze_value(item) for item in surface_states_raw),
        presentation_state=freeze_value(presentation_state),
        appearance_snapshot=freeze_value(snapshot),
        source_event_ids=tuple(source_event_ids),
    )


def _reference_material(reference: PresentationReference) -> dict[str, Any]:
    return _json_normalized({
        "actor_id": reference.actor_id,
        "contract_id": reference.contract_id,
        "contract_version": reference.contract_version,
        "world_event_cursor": reference.world_event_cursor,
        "view_id": reference.view_id,
        "identity_admission_authority_ref": reference.identity_admission_authority_ref,
        "identity_evidence_sha256": reference.identity_evidence_sha256,
        "outfit_state": thaw_value(reference.outfit_state),
        "dressing_states": [thaw_value(item) for item in reference.dressing_states],
        "surface_states": [thaw_value(item) for item in reference.surface_states],
        "presentation_state": thaw_value(reference.presentation_state),
        "appearance_snapshot": thaw_value(reference.appearance_snapshot),
        "source_event_ids": list(reference.source_event_ids),
    })


def export_replay_package(
    *,
    reference: PresentationReference,
    events: Sequence[Mapping[str, Any]],
    inventory_object_refs: Sequence[str],
    asset_registry: Mapping[str, Mapping[str, Any]],
) -> str:
    payload = {
        "package_schema": "AWRSE-I3A-PRESENTATION-REPLAY-1",
        "identity_evidence_binding": {
            "admission_authority_ref": reference.identity_admission_authority_ref,
            "evidence_sha256": reference.identity_evidence_sha256,
        },
        "inputs": {
            "actor_id": reference.actor_id,
            "events": deepcopy(list(events)),
            "inventory_object_refs": list(inventory_object_refs),
            "asset_registry": deepcopy(dict(asset_registry)),
            "view_id": reference.view_id,
            "schema_version": reference.appearance_snapshot["schema_version"],
            "ruleset_version": reference.appearance_snapshot["ruleset_version"],
        },
        "expected_reference": _reference_material(reference),
    }
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    return _canonical_json({"payload": payload, "sha256": digest})


def replay_package(
    package_json: str,
    *,
    identity_evidence: Mapping[str, Any],
) -> PresentationReference:
    """Replay with separately supplied upstream identity evidence.

    The replay package deliberately cannot carry/reconstitute its own admission
    authority. It only carries a ref+digest binding to evidence supplied again
    across the external trust boundary at replay time.
    """
    try:
        envelope = json.loads(package_json)
    except (TypeError, json.JSONDecodeError):
        raise ValueError("I3A_REPLAY_PACKAGE_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I3A_REPLAY_PACKAGE_INVALID")
    payload = envelope["payload"]
    if not isinstance(payload, Mapping) or payload.get("package_schema") != "AWRSE-I3A-PRESENTATION-REPLAY-1":
        raise ValueError("I3A_REPLAY_PACKAGE_SCHEMA_INVALID")
    digest = hashlib.sha256(_canonical_json(payload).encode("utf-8")).hexdigest()
    if envelope.get("sha256") != digest:
        raise ValueError("I3A_REPLAY_PACKAGE_TAMPERED")
    inputs = payload.get("inputs")
    binding = payload.get("identity_evidence_binding")
    if not isinstance(inputs, Mapping) or not isinstance(binding, Mapping):
        raise ValueError("I3A_REPLAY_INPUTS_INVALID")
    rebuilt = build_presentation_reference(
        actor_id=inputs.get("actor_id"),
        events=inputs.get("events"),
        inventory_object_refs=inputs.get("inventory_object_refs"),
        asset_registry=inputs.get("asset_registry"),
        view_id=inputs.get("view_id"),
        identity_evidence=identity_evidence,
        schema_version=inputs.get("schema_version"),
        ruleset_version=inputs.get("ruleset_version"),
    )
    if (
        rebuilt.identity_admission_authority_ref != binding.get("admission_authority_ref")
        or rebuilt.identity_evidence_sha256 != binding.get("evidence_sha256")
    ):
        raise ValueError("I3A_REPLAY_IDENTITY_EVIDENCE_MISMATCH")
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I3A_REPLAY_MATERIALIZATION_MISMATCH")
    return rebuilt


def validate_mock_render_claims(
    reference: PresentationReference,
    claims: Mapping[str, Any],
) -> MockRenderValidation:
    if not isinstance(claims, Mapping):
        raise ValueError("I3A_RENDER_CLAIMS_REQUIRED")
    contradictions: list[str] = []
    unauthorized: list[str] = []

    if claims.get("mutation_requested"):
        unauthorized.append("RENDERER_CANNOT_MUTATE_PRESENTATION_STATE")
    if claims.get("generated_media_as_authority"):
        unauthorized.append("GENERATED_PIXELS_CANNOT_AUTHOR_PRESENTATION_STATE")
    if claims.get("inferred_injury_refs"):
        unauthorized.append("DRESSING_APPEARANCE_CANNOT_AUTHOR_FUNCTIONAL_INJURY")

    claimed_view = claims.get("view_id")
    if claimed_view != reference.view_id:
        contradictions.append(f"VIEW_ID:{claimed_view}!={reference.view_id}")

    canonical_slots = dict(reference.outfit_state["slot_bindings"])
    claimed_slots = claims.get("outfit_slots")
    if not isinstance(claimed_slots, Mapping):
        contradictions.append("OUTFIT_SLOT_CLAIMS_REQUIRED")
    else:
        for slot in sorted(set(canonical_slots) | set(claimed_slots)):
            expected = canonical_slots.get(slot)
            actual = claimed_slots.get(slot)
            if actual != expected:
                contradictions.append(f"OUTFIT_SLOT:{slot}:{actual}!={expected}")

    canonical_dressings = {
        item["dressing_id"]: item for item in reference.dressing_states
    }
    raw_dressings = claims.get("dressings", [])
    if isinstance(raw_dressings, (str, bytes, bytearray)) or not isinstance(raw_dressings, Sequence):
        contradictions.append("DRESSING_CLAIMS_INVALID")
        claimed_dressings: dict[str, Mapping[str, Any]] = {}
    else:
        claimed_dressings = {}
        for item in raw_dressings:
            if not isinstance(item, Mapping) or not isinstance(item.get("dressing_id"), str):
                contradictions.append("DRESSING_CLAIM_INVALID")
                continue
            dressing_id = item["dressing_id"]
            if dressing_id in claimed_dressings:
                contradictions.append(f"DUPLICATE_DRESSING_CLAIM:{dressing_id}")
                continue
            claimed_dressings[dressing_id] = item

    worn_refs = set(canonical_slots.values())
    visible_required = {
        dressing_id
        for dressing_id, canonical in canonical_dressings.items()
        if not set(canonical.get("covered_by_refs", ())).intersection(worn_refs)
    }
    for dressing_id in sorted(visible_required - set(claimed_dressings)):
        contradictions.append(f"MISSING_VISIBLE_DRESSING:{dressing_id}")
    for dressing_id, claim in claimed_dressings.items():
        canonical = canonical_dressings.get(dressing_id)
        if canonical is None:
            contradictions.append(f"OBSOLETE_OR_UNKNOWN_DRESSING:{dressing_id}")
            continue
        for field in ("body_region", "side", "material_ref", "appearance_state"):
            if claim.get(field) != thaw_value(canonical.get(field)):
                contradictions.append(
                    f"DRESSING:{dressing_id}:{field}:{claim.get(field)}!={thaw_value(canonical.get(field))}"
                )

    canonical_surfaces = {
        item["surface_state_id"]: item for item in reference.surface_states
    }
    raw_surfaces = claims.get("surface_states", [])
    if not isinstance(raw_surfaces, Sequence) or isinstance(raw_surfaces, (str, bytes, bytearray)):
        contradictions.append("SURFACE_CLAIMS_INVALID")
    else:
        by_id: dict[str, Mapping[str, Any]] = {}
        for item in raw_surfaces:
            if isinstance(item, Mapping) and isinstance(item.get("surface_state_id"), str):
                by_id[item["surface_state_id"]] = item
            else:
                contradictions.append("SURFACE_CLAIM_INVALID")
        for surface_id, canonical in canonical_surfaces.items():
            claim = by_id.get(surface_id)
            if claim is None:
                contradictions.append(f"MISSING_SURFACE_STATE:{surface_id}")
                continue
            for field in ("target_ref", "surface_type", "intensity"):
                if claim.get(field) != thaw_value(canonical.get(field)):
                    contradictions.append(f"SURFACE:{surface_id}:{field}:MISMATCH")
        for surface_id in set(by_id) - set(canonical_surfaces):
            contradictions.append(f"OBSOLETE_OR_UNKNOWN_SURFACE:{surface_id}")

    if contradictions or unauthorized:
        return MockRenderValidation(
            status="RENDER_MISMATCH",
            contradictions=tuple(sorted(contradictions)),
            unauthorized_claims=tuple(sorted(unauthorized)),
        )
    return MockRenderValidation(status="RENDER_ALIGNED")
