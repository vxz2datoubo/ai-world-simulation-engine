from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from runtime.awrse.model import Event, WorldState


WORLD_ECHO_REFERENCE_VERSION = "AWRSE-WORLD-ECHO-OPPORTUNITY-REFERENCE/v2"
NON_CANONICAL_AUTHORITY = "NARRATIVE_OPPORTUNITY_NON_CANONICAL"


class WorldEchoEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class WorldEchoOpportunityCandidate:
    schema: str
    opportunity_id: str
    authority: str
    world_id: str
    world_state_version: str
    speaker_npc_id: str
    entity_id: str
    source_event_or_delta_refs: tuple[str, ...]
    knowledge_attribution_refs: tuple[str, ...]
    attribution_state: str
    culprit_actor_ref: str | None
    response_concept: str
    realization_gate: str
    realization_authorized: bool
    canonical_world_authority: bool
    knowledge_write_authority: bool
    speech_commit_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WorldEchoDecision:
    status: str
    reason: str
    opportunity: WorldEchoOpportunityCandidate | None = None


def _fail(code: str) -> WorldEchoEvidenceError:
    return WorldEchoEvidenceError(code)


def _exact_committed_event(world: WorldState, event_id: str) -> tuple[int, Event]:
    matches = [
        (index, event)
        for index, event in enumerate(world.event_log, start=1)
        if event.event_id == event_id
    ]
    if not matches:
        raise _fail("SOURCE_EVENT_NOT_COMMITTED")
    if len(matches) != 1:
        raise _fail("SOURCE_EVENT_NOT_EXACTLY_ONCE")
    index, event = matches[0]
    if event.event_id not in world.committed_event_ids:
        raise _fail("SOURCE_EVENT_INDEX_MISMATCH")
    return index, event


def _matching_acquisitions(world: WorldState, speaker_npc_id: str, source_event_id: str) -> tuple[Event, ...]:
    npc = world.npc_minds[speaker_npc_id]
    by_id = {event.event_id: event for event in world.event_log}
    matches: list[Event] = []
    for memory_ref in npc.memories:
        event = by_id.get(memory_ref)
        if event is None:
            raise _fail("NPC_MEMORY_REF_NOT_COMMITTED")
        if event.event_type != "NPC_KNOWLEDGE_ACQUIRED":
            continue
        if str(event.payload.get("npc_id", "")) != speaker_npc_id:
            raise _fail("NPC_MEMORY_RECIPIENT_MISMATCH")
        if str(event.payload.get("source_event_id", "")) == source_event_id:
            matches.append(event)

    has_boundary_ref = source_event_id in npc.knowledge_boundary_refs
    if has_boundary_ref != bool(matches):
        raise _fail("NPC_KNOWLEDGE_PROJECTION_INCONSISTENT")
    return tuple(matches)


def _event_position(world: WorldState, event: Event) -> int:
    return next(
        index for index, candidate in enumerate(world.event_log, start=1)
        if candidate.event_id == event.event_id
    )


def _opportunity_id(payload: dict[str, Any]) -> str:
    material = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "WEO-" + hashlib.sha256(material).hexdigest()[:24]


def derive_world_echo_opportunity(
    *,
    world: WorldState,
    speaker_npc_id: str,
    entity_id: str,
    source_event_id: str,
) -> WorldEchoDecision:
    """Derive only attribution claims mechanically supported by recipient-local evidence.

    Canonical R002 visual acquisition for an object event proves that the object/event was
    acquired by the NPC. It does not prove that the causal actor was visible, recognized,
    or linked to the damage by that NPC. Therefore this v2 reference deliberately keeps
    the causal actor UNKNOWN unless a separately governed causal-actor acquisition proof
    exists. Current R002 has no such proof, so source_event.actor_id remains simulator-only
    internal provenance and never enters speaker-visible attribution.
    """
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    if speaker_npc_id not in world.npc_minds or speaker_npc_id not in world.actors:
        raise _fail("SPEAKER_NPC_NOT_FOUND")
    obj = world.objects.get(entity_id)
    if obj is None:
        raise _fail("ECHO_ENTITY_NOT_OBJECT")

    source_cursor, source_event = _exact_committed_event(world, source_event_id)
    if source_event.event_type != "OBJECT_DAMAGED":
        raise _fail("SOURCE_EVENT_NOT_SUPPORTED_WORLD_ECHO_DAMAGE")
    if str(source_event.payload.get("object_id", "")) != entity_id:
        raise _fail("SOURCE_EVENT_ENTITY_MISMATCH")
    source_damage_state = str(source_event.payload.get("damage_state", ""))
    if not source_damage_state or source_damage_state not in {"DAMAGED", "BROKEN"}:
        raise _fail("SOURCE_EVENT_DAMAGE_STATE_INVALID")
    if obj.damage_state != source_damage_state:
        raise _fail("SOURCE_EVENT_NO_LONGER_MATCHES_CURRENT_OBJECT_STATE")

    scene = world.scenes.get(source_event.scene_id)
    if scene is None:
        raise _fail("SOURCE_EVENT_SCENE_NOT_FOUND")
    persistent_delta_ref = f"{entity_id}:damage_state={source_damage_state}"
    if persistent_delta_ref not in scene.persistent_delta_refs:
        raise _fail("PERSISTENT_DAMAGE_DELTA_NOT_PROVEN")

    acquisitions = _matching_acquisitions(world, speaker_npc_id, source_event_id)
    if not acquisitions:
        return WorldEchoDecision(
            status="NO_VALID_OPPORTUNITY",
            reason="NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION",
        )

    visual_object_acquisitions = [
        event for event in acquisitions if str(event.payload.get("mode", "")) == "SAW"
    ]
    if not visual_object_acquisitions:
        return WorldEchoDecision(
            status="NO_VALID_OPPORTUNITY",
            reason="ACQUISITION_MODE_NOT_SUPPORTED_BY_V2_OBJECT_ECHO_POLICY",
        )

    acquisition = min(visual_object_acquisitions, key=lambda event: _event_position(world, event))
    attribution_state = "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"
    identity_payload = {
        "schema": WORLD_ECHO_REFERENCE_VERSION,
        "world_id": world.world_id,
        "world_state_version": world.world_state_version,
        "speaker_npc_id": speaker_npc_id,
        "entity_id": entity_id,
        "source_event_id": source_event_id,
        "source_event_cursor": source_cursor,
        "acquisition_event_id": acquisition.event_id,
        "damage_state": source_damage_state,
        "attribution_state": attribution_state,
        "culprit_actor_ref": None,
    }
    opportunity = WorldEchoOpportunityCandidate(
        schema=WORLD_ECHO_REFERENCE_VERSION,
        opportunity_id=_opportunity_id(identity_payload),
        authority=NON_CANONICAL_AUTHORITY,
        world_id=world.world_id,
        world_state_version=world.world_state_version,
        speaker_npc_id=speaker_npc_id,
        entity_id=entity_id,
        source_event_or_delta_refs=(source_event_id, persistent_delta_ref),
        knowledge_attribution_refs=(acquisition.event_id,),
        attribution_state=attribution_state,
        culprit_actor_ref=None,
        response_concept="REMARK_OBSERVED_DAMAGE_CAUSE_UNKNOWN",
        realization_gate="CURRENT_PERCEPTION_EVIDENCE_REQUIRED",
        realization_authorized=False,
        canonical_world_authority=False,
        knowledge_write_authority=False,
        speech_commit_authority=False,
    )
    return WorldEchoDecision(
        status="CANDIDATE_BLOCKED_PENDING_CURRENT_PERCEPTION",
        reason="OBJECT_DAMAGE_ACQUIRED_CAUSAL_ACTOR_NOT_PROVEN",
        opportunity=opportunity,
    )
