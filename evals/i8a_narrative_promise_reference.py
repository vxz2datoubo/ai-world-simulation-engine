"""Bounded I8A evidence-derived NarrativePromise lifecycle reference.

Canonical SOLO history remains world truth. This module derives only the already-
frozen AF-F NarrativePromise projection from explicit player speech plus replay-
validated world evidence. It does not create a ChoiceMemory authority, promise
truth, payoff, storylet, PX decision, Director beat, or world event.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
import re
from typing import Any

from awrse import (
    WorldBaseline,
    WorldState,
    export_solo_replay_package,
    import_solo_replay_package,
    rehydrate_solo_replay_package,
)
from awrse.model import Event, freeze_value, thaw_value

I8_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_CHOICE_MEMORY_LEDGER_AUTHORITY_CREATED = True
NO_AUTHORED_PROMISE_CREATION = True
NO_PAYOFF_OR_WORLD_EVENT_COMMIT = True
NO_LLM_OR_PROVIDER = True
NO_PX_DIRECTOR_RENDERER_AUTHORITY = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.10.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1",
)
_EXPECTED_PROMISE_TYPE = (
    "AF001.NarrativePromise",
    "1.0.0-candidate",
    "EVIDENCE_DERIVED_PROMISE_LIFECYCLE",
)
_EXPECTED_PROMISE_FIELDS = {
    "promise_id",
    "source_refs",
    "promise_type",
    "status",
    "callback_eligibility",
    "payoff_refs",
    "invalidation_reason_optional",
}
_REQUIRED_AF_F_INVARIANTS = {
    "STORY_STRUCTURE_IS_NOT_WORLD_TRUTH",
    "AUTHORED_NARRATIVE_NE_PROMISE_HISTORY",
    "NARRATIVE_PROMISE_REQUIRES_SOURCE_EVENT_EVIDENCE",
    "BRANCH_QUALITY_CANNOT_JUSTIFY_RETCON_OR_RESURRECTION",
}
_EXPECTED_PROMISE_LIFECYCLE = (
    "EXPLICIT_SPEECH_OR_ACTION_SOURCE_EVENT_TO_PROMISE_LIFECYCLE_TO_CALLBACK_OR_PAYOFF_OPPORTUNITY"
)
_EXPECTED_PROMISE_MUTATION_CONSTRAINT = (
    "UNDERLYING_PROMISE_TRUTH_REQUIRES_EXPLICIT_SPEECH_ACTION_OR_OTHER_SOURCE_EVENT_EVIDENCE; "
    "AUTHORED_NARRATIVE_CANNOT_INVENT_A_PROMISE; NARRATIVE_MAY_EVALUATE_CALLBACK_OR_PAYOFF_"
    "ELIGIBILITY_AND_WORLD_DRIVEN_INVALIDATION_ONLY_FROM_BOUND_SOURCE_HISTORY"
)
_REFERENCE_PROMISE_TYPE = "PLAYER_EXPLICIT_REPAIR_OBJECT"
_REFERENCE_AUTHORITY_CLASS = (
    "DERIVED_NARRATIVE_PROMISE_LIFECYCLE_REFERENCE_ONLY_NOT_WORLD_OR_PLAYER_INTENT_AUTHORITY"
)
_PROMISE_RE = re.compile(
    r"(?:^|\s)PROMISE_REPAIR_OBJECT:([A-Za-z0-9_.-]+)(?:\s|$)"
)
_PACKAGE_SCHEMA = "AWRSE-I8A-NARRATIVE-PROMISE-REPLAY-1"


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _require_sequence(value: Any, code: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(code)
    return tuple(value)


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("I8A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I8A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I8A_JSON_NONFINITE:{value}")


def _event_record(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "scene_id": event.scene_id,
        "baseline_version": event.baseline_version,
        "payload": thaw_value(event.payload),
        "caused_by_action_id": event.caused_by_action_id,
    }


def _load_authority() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I8A_CANONICAL_CONTRACT_UNAVAILABLE") from None
    if not isinstance(contract, Mapping):
        raise ValueError("I8A_CANONICAL_CONTRACT_INVALID")

    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I8A_CANONICAL_PARENT_DRIFT")

    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I8A_TYPE_REGISTRY_MISSING")
    entry = registry.get("NarrativePromise")
    if not isinstance(entry, Mapping):
        raise ValueError("I8A_NARRATIVE_PROMISE_TYPE_MISSING")
    actual = (
        entry.get("type_id"),
        entry.get("version"),
        entry.get("authority_profile_ref"),
    )
    if actual != _EXPECTED_PROMISE_TYPE:
        raise ValueError("I8A_NARRATIVE_PROMISE_TYPE_DRIFT")
    if set(entry.get("fields", [])) != _EXPECTED_PROMISE_FIELDS:
        raise ValueError("I8A_NARRATIVE_PROMISE_FIELDS_DRIFT")
    if entry.get("authored_creation_allowed") is not False:
        raise ValueError("I8A_AUTHORED_PROMISE_CREATION_BOUNDARY_DRIFT")
    if entry.get("lifecycle") != _EXPECTED_PROMISE_LIFECYCLE:
        raise ValueError("I8A_NARRATIVE_PROMISE_LIFECYCLE_DRIFT")
    if set(entry.get("lifecycle_source_requirements", [])) != {"source_refs"}:
        raise ValueError("I8A_PROMISE_SOURCE_REQUIREMENT_DRIFT")

    af_f = contract.get("freeze_domains", {}).get("AF-F")
    if not isinstance(af_f, Mapping):
        raise ValueError("I8A_AF_F_AUTHORITY_MISSING")
    if not _REQUIRED_AF_F_INVARIANTS <= set(af_f.get("invariants", [])):
        raise ValueError("I8A_AF_F_INVARIANT_DRIFT")

    profile = contract.get("authority_semantics", {}).get("profiles", {}).get(
        "EVIDENCE_DERIVED_PROMISE_LIFECYCLE"
    )
    if not isinstance(profile, Mapping):
        raise ValueError("I8A_PROMISE_AUTHORITY_PROFILE_MISSING")
    if profile.get("producer_or_assembler") != ["AWRSE_PROMISE_LIFECYCLE_PROJECTOR"]:
        raise ValueError("I8A_PROMISE_PROJECTOR_AUTHORITY_DRIFT")
    if profile.get("staging_authority") != ["NONE"]:
        raise ValueError("I8A_PROMISE_STAGING_AUTHORITY_DRIFT")
    if profile.get("mutation_constraint") != _EXPECTED_PROMISE_MUTATION_CONSTRAINT:
        raise ValueError("I8A_PROMISE_MUTATION_CONSTRAINT_DRIFT")
    return _EXPECTED_PARENT


def _indexed_events(world: WorldState) -> tuple[tuple[Event, ...], dict[str, Event], dict[str, int]]:
    events = tuple(world.event_log)
    by_id: dict[str, Event] = {}
    positions: dict[str, int] = {}
    for position, event in enumerate(events, start=1):
        event_id = _require_string(event.event_id, "I8A_EVENT_ID_REQUIRED")
        if event_id in by_id:
            raise ValueError(f"I8A_DUPLICATE_EVENT_ID:{event_id}")
        if event.baseline_version != world.baseline_version:
            raise ValueError(f"I8A_EVENT_BASELINE_DRIFT:{event_id}")
        by_id[event_id] = event
        positions[event_id] = position
    if set(by_id) != set(world.committed_event_ids):
        raise ValueError("I8A_CANONICAL_EVENT_INDEX_MISMATCH")
    if world.state_version != len(events):
        raise ValueError("I8A_STATE_VERSION_EVENT_COUNT_MISMATCH")
    return events, by_id, positions


def _parse_reference_promise(source: Event) -> str:
    if source.payload.get("trust_class") != "UNTRUSTED_DATA":
        raise ValueError("I8A_SPEECH_TRUST_CLASS_DRIFT")
    if source.payload.get("authority") != "NONE_OVER_TARGET_INTERNAL_STATE":
        raise ValueError("I8A_SPEECH_WORLD_AUTHORITY_DRIFT")
    literal = source.payload.get("literal_content")
    if not isinstance(literal, str):
        raise ValueError("I8A_SPEECH_LITERAL_CONTENT_REQUIRED")
    matches = _PROMISE_RE.findall(literal)
    if len(matches) != 1:
        raise ValueError("I8A_EXACTLY_ONE_EXPLICIT_PROMISE_MARKER_REQUIRED")
    return matches[0]


@dataclass(frozen=True)
class NarrativePromiseReference:
    player_actor_id: str
    recipient_npc_id: str
    target_object_id: str
    source_speech_event_id: str
    source_acquisition_event_id: str
    source_damage_event_id: str
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    contract_id: str
    contract_version: str
    authority_graph_version: str
    source_speech_sha256: str
    narrative_promise: Mapping[str, Any]
    authority_class: str


def _reference_material(reference: NarrativePromiseReference) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "player_actor_id": reference.player_actor_id,
                "recipient_npc_id": reference.recipient_npc_id,
                "target_object_id": reference.target_object_id,
                "source_speech_event_id": reference.source_speech_event_id,
                "source_acquisition_event_id": reference.source_acquisition_event_id,
                "source_damage_event_id": reference.source_damage_event_id,
                "source_world_id": reference.source_world_id,
                "source_baseline_version": reference.source_baseline_version,
                "source_state_version": reference.source_state_version,
                "contract_id": reference.contract_id,
                "contract_version": reference.contract_version,
                "authority_graph_version": reference.authority_graph_version,
                "source_speech_sha256": reference.source_speech_sha256,
                "narrative_promise": thaw_value(reference.narrative_promise),
                "authority_class": reference.authority_class,
            }
        )
    )


def _build_from_replay_validated_world(
    *,
    world: WorldState,
    player_actor_id: str,
    recipient_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> NarrativePromiseReference:
    contract_id, contract_version, authority_graph = _load_authority()
    player_actor_id = _require_string(player_actor_id, "I8A_PLAYER_ACTOR_ID_REQUIRED")
    recipient_npc_id = _require_string(recipient_npc_id, "I8A_RECIPIENT_NPC_ID_REQUIRED")
    target_object_id = _require_string(target_object_id, "I8A_TARGET_OBJECT_ID_REQUIRED")
    source_speech_event_id = _require_string(
        source_speech_event_id, "I8A_SOURCE_SPEECH_EVENT_ID_REQUIRED"
    )

    if player_actor_id != world.primary_player_actor_id:
        raise ValueError("I8A_PLAYER_ACTOR_NOT_CANONICAL_PRIMARY_PLAYER")
    if player_actor_id not in world.actors:
        raise ValueError("I8A_PRIMARY_PLAYER_ACTOR_NOT_FOUND")
    if recipient_npc_id not in world.npc_minds or recipient_npc_id not in world.actors:
        raise ValueError("I8A_RECIPIENT_NPC_NOT_FOUND")
    target = world.objects.get(target_object_id)
    if target is None:
        raise ValueError("I8A_TARGET_OBJECT_NOT_FOUND")

    events, by_id, positions = _indexed_events(world)
    source = by_id.get(source_speech_event_id)
    if source is None:
        raise ValueError("I8A_SOURCE_SPEECH_NOT_CANONICAL_COMMITTED")
    if source.event_type != "SPEECH_UTTERED":
        raise ValueError("I8A_SOURCE_EVENT_TYPE_NOT_SPEECH_UTTERED")
    if source.actor_id != player_actor_id:
        raise ValueError("I8A_PROMISE_SPEAKER_NOT_PRIMARY_PLAYER")
    _require_string(
        source.caused_by_action_id,
        "I8A_SOURCE_SPEECH_REQUIRES_PLAYER_ACTION_PROVENANCE",
    )
    marker_target_id = _parse_reference_promise(source)
    if marker_target_id != target_object_id:
        raise ValueError("I8A_EXPLICIT_PROMISE_TARGET_BINDING_MISMATCH")

    acquisition_candidates = [
        event
        for event in events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("npc_id") == recipient_npc_id
        and event.payload.get("mode") == "HEARD"
        and event.payload.get("source_event_id") == source_speech_event_id
        and event.payload.get("speaker_id") == player_actor_id
        and positions[event.event_id] > positions[source_speech_event_id]
    ]
    if len(acquisition_candidates) != 1:
        raise ValueError("I8A_PROMISE_RECIPIENT_HEARD_EVIDENCE_REQUIRED")
    acquisition = acquisition_candidates[0]

    damage_candidates = [
        event
        for event in events
        if event.event_type == "OBJECT_DAMAGED"
        and event.payload.get("object_id") == target_object_id
        and positions[event.event_id] < positions[source_speech_event_id]
    ]
    if not damage_candidates:
        raise ValueError("I8A_PROMISE_TARGET_DAMAGE_CONTEXT_REQUIRED")
    damage = max(damage_candidates, key=lambda event: positions[event.event_id])
    _require_string(
        damage.caused_by_action_id,
        "I8A_DAMAGE_CONTEXT_REQUIRES_ACTION_PROVENANCE",
    )
    damage_state = damage.payload.get("damage_state")
    if damage_state not in {"DAMAGED", "BROKEN"}:
        raise ValueError("I8A_DAMAGE_CONTEXT_STATE_INVALID")
    if target.damage_state != damage_state:
        raise ValueError("I8A_CURRENT_TARGET_STATE_NO_LONGER_MATCHES_DAMAGE_CONTEXT")
    if target.scene_id != damage.scene_id or source.scene_id != target.scene_id:
        raise ValueError("I8A_PROMISE_TARGET_SCENE_BINDING_DRIFT")
    scene = world.scenes.get(target.scene_id)
    if scene is None:
        raise ValueError("I8A_PROMISE_TARGET_SCENE_NOT_FOUND")
    persistent_delta = f"{target_object_id}:damage_state={damage_state}"
    if damage.event_id not in scene.relevant_event_refs:
        raise ValueError("I8A_DAMAGE_EVENT_NOT_BOUND_TO_SCENE_HISTORY")
    if persistent_delta not in scene.persistent_delta_refs:
        raise ValueError("I8A_PERSISTENT_DAMAGE_DELTA_MISSING")

    source_speech_sha256 = _sha256(_event_record(source))
    identity = {
        "world_id": world.world_id,
        "baseline_version": world.baseline_version,
        "player_actor_id": player_actor_id,
        "recipient_npc_id": recipient_npc_id,
        "target_object_id": target_object_id,
        "source_speech_event_id": source_speech_event_id,
        "source_speech_sha256": source_speech_sha256,
        "source_acquisition_event_id": acquisition.event_id,
        "source_damage_event_id": damage.event_id,
    }
    promise_id = f"I8A:PROMISE:{_sha256(identity)[:24]}"

    callback_eligible = world.state_version > positions[acquisition.event_id]
    callback_reason = (
        "POST_PROMISE_CANONICAL_WORLD_ADVANCE_AND_BOUND_TARGET_CONTEXT_STILL_VALID"
        if callback_eligible
        else "NO_POST_PROMISE_CANONICAL_WORLD_ADVANCE_YET"
    )
    promise = {
        "promise_id": promise_id,
        "source_refs": [source_speech_event_id, acquisition.event_id, damage.event_id],
        "promise_type": _REFERENCE_PROMISE_TYPE,
        "status": "CALLBACK_ELIGIBLE" if callback_eligible else "DEFERRED",
        "callback_eligibility": {
            "eligible": callback_eligible,
            "reason": callback_reason,
            "target_object_ref": target_object_id,
            "required_persistent_delta_ref": persistent_delta,
            "evaluation_cursor": f"{world.baseline_version}:{world.state_version}",
        },
        "payoff_refs": [],
        "invalidation_reason_optional": None,
    }
    if set(promise) != _EXPECTED_PROMISE_FIELDS:
        raise ValueError("I8A_DERIVED_PROMISE_FIELDS_DRIFT")

    return NarrativePromiseReference(
        player_actor_id=player_actor_id,
        recipient_npc_id=recipient_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
        source_acquisition_event_id=acquisition.event_id,
        source_damage_event_id=damage.event_id,
        source_world_id=world.world_id,
        source_baseline_version=world.baseline_version,
        source_state_version=world.state_version,
        contract_id=contract_id,
        contract_version=contract_version,
        authority_graph_version=authority_graph,
        source_speech_sha256=source_speech_sha256,
        narrative_promise=freeze_value(promise),
        authority_class=_REFERENCE_AUTHORITY_CLASS,
    )


def build_narrative_promise_reference(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    recipient_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
    caller_promise_evidence: Mapping[str, Any] | None = None,
) -> NarrativePromiseReference:
    """Validate source history through I1, then derive AF-F promise lifecycle evidence."""
    if caller_promise_evidence is not None:
        raise ValueError("I8A_CALLER_AUTHORED_PROMISE_EVIDENCE_FORBIDDEN")
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8A_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I8A_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    export_solo_replay_package(baseline, world)
    return _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        recipient_npc_id=recipient_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )


def export_narrative_promise_package(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    recipient_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> bytes:
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8A_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I8A_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    solo_package = export_solo_replay_package(baseline, world)
    reference = _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        recipient_npc_id=recipient_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "player_actor_id": reference.player_actor_id,
        "recipient_npc_id": reference.recipient_npc_id,
        "target_object_id": reference.target_object_id,
        "source_speech_event_id": reference.source_speech_event_id,
        "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(),
        "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"),
        "expected_reference": _reference_material(reference),
    }
    envelope = {"payload": payload, "sha256": _sha256(payload)}
    return _canonical_json(envelope).encode("utf-8")


def replay_narrative_promise_package(
    package: bytes | bytearray | memoryview,
) -> NarrativePromiseReference:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8A_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8A_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8A_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I8A_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8A_REPLAY_PACKAGE_TAMPERED")

    encoded = _require_string(
        payload.get("source_i1_replay_b64"),
        "I8A_I1_REPLAY_PAYLOAD_REQUIRED",
    )
    try:
        solo_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8A_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get("source_i1_replay_sha256"):
        raise ValueError("I8A_I1_REPLAY_DIGEST_MISMATCH")

    evidence = import_solo_replay_package(solo_package)
    rebuilt_world = rehydrate_solo_replay_package(solo_package)
    rebuilt = _build_from_replay_validated_world(
        world=rebuilt_world,
        player_actor_id=payload.get("player_actor_id"),
        recipient_npc_id=payload.get("recipient_npc_id"),
        target_object_id=payload.get("target_object_id"),
        source_speech_event_id=payload.get("source_speech_event_id"),
    )
    if (
        rebuilt.source_world_id != evidence.world_id
        or rebuilt.source_baseline_version != evidence.baseline_version
    ):
        raise ValueError("I8A_REPLAY_I1_SOURCE_BINDING_MISMATCH")
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I8A_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH")
    return rebuilt
