from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from runtime.awrse.model import WorldState


OBSERVATION_POLICY_VERSION = "AWRSE-CURRENT-VISUAL-OBSERVATION-POLICY/v1"
OBSERVATION_POLICY_DIGEST = hashlib.sha256(
    b"VISUAL_OBJECT_ONLY|EXPLICIT_OBSERVATION_SAMPLE|WORLDSTATE_CAN_SEE|NO_KNOWLEDGE_WRITE|NO_HIDDEN_CAUSE"
).hexdigest()


class CurrentObservationEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class CurrentObservationEvidence:
    schema: str
    receipt_id: str
    capture_semantics: str
    observation_mode: str
    world_id: str
    world_state_version: str
    baseline_version: str
    source_event_cursor: int
    observer_actor_id: str
    entity_id: str
    scene_id: str
    observer_zone_id: str | None
    entity_zone_id: str | None
    observable_state_refs: tuple[str, ...]
    observation_policy_version: str
    observation_policy_digest: str
    canonical_world_authority: bool
    knowledge_write_authority: bool
    narrative_realization_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(code: str) -> CurrentObservationEvidenceError:
    return CurrentObservationEvidenceError(code)


def _receipt_id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "COE-" + hashlib.sha256(encoded).hexdigest()[:24]


def _observable_state_refs(world: WorldState, entity_id: str) -> tuple[str, ...]:
    obj = world.objects.get(entity_id)
    if obj is None:
        raise _fail("V1_VISUAL_OBSERVATION_SUPPORTS_OBJECTS_ONLY")
    return (
        f"OBJECT_PRESENT:{entity_id}",
        f"OBJECT_DAMAGE_STATE:{entity_id}:{obj.damage_state}",
        f"OBJECT_OPEN_STATE:{entity_id}:{'OPEN' if obj.is_open else 'CLOSED'}",
    )


def capture_current_visual_observation(
    *,
    world: WorldState,
    observer_actor_id: str,
    entity_id: str,
    observation_policy_version: str = OBSERVATION_POLICY_VERSION,
) -> CurrentObservationEvidence:
    if observation_policy_version != OBSERVATION_POLICY_VERSION:
        raise _fail("OBSERVATION_POLICY_VERSION_MISMATCH")
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    observer = world.actors.get(observer_actor_id)
    if observer is None:
        raise _fail("OBSERVER_ACTOR_NOT_FOUND")
    obj = world.objects.get(entity_id)
    if obj is None:
        raise _fail("V1_VISUAL_OBSERVATION_SUPPORTS_OBJECTS_ONLY")
    if not world.can_see(entity_id, observer_actor_id):
        raise _fail("VISUAL_ELIGIBILITY_NOT_PROVEN")
    if observer.scene_id != obj.scene_id:
        raise _fail("OBSERVATION_SCENE_MISMATCH")

    source_event_cursor = len(world.event_log)
    state_refs = _observable_state_refs(world, entity_id)
    identity_payload = {
        "schema": "AWRSE.CurrentObservationEvidence.Reference/v1",
        "capture_semantics": "EXPLICIT_OBSERVATION_SAMPLE",
        "mode": "VISUAL",
        "world_id": world.world_id,
        "world_state_version": world.world_state_version,
        "baseline_version": world.baseline_version,
        "source_event_cursor": source_event_cursor,
        "observer_actor_id": observer_actor_id,
        "entity_id": entity_id,
        "scene_id": observer.scene_id,
        "observer_zone_id": observer.zone_id,
        "entity_zone_id": obj.zone_id,
        "observable_state_refs": list(state_refs),
        "observation_policy_version": OBSERVATION_POLICY_VERSION,
        "observation_policy_digest": OBSERVATION_POLICY_DIGEST,
    }
    return CurrentObservationEvidence(
        schema="AWRSE.CurrentObservationEvidence.Reference/v1",
        receipt_id=_receipt_id(identity_payload),
        capture_semantics="EXPLICIT_OBSERVATION_SAMPLE",
        observation_mode="VISUAL",
        world_id=world.world_id,
        world_state_version=world.world_state_version,
        baseline_version=world.baseline_version,
        source_event_cursor=source_event_cursor,
        observer_actor_id=observer_actor_id,
        entity_id=entity_id,
        scene_id=observer.scene_id,
        observer_zone_id=observer.zone_id,
        entity_zone_id=obj.zone_id,
        observable_state_refs=state_refs,
        observation_policy_version=OBSERVATION_POLICY_VERSION,
        observation_policy_digest=OBSERVATION_POLICY_DIGEST,
        canonical_world_authority=False,
        knowledge_write_authority=False,
        narrative_realization_authority=False,
    )


def validate_current_observation(*, world: WorldState, receipt: CurrentObservationEvidence) -> None:
    if receipt.schema != "AWRSE.CurrentObservationEvidence.Reference/v1":
        raise _fail("OBSERVATION_SCHEMA_MISMATCH")
    if receipt.observation_policy_version != OBSERVATION_POLICY_VERSION:
        raise _fail("OBSERVATION_POLICY_VERSION_MISMATCH")
    if receipt.observation_policy_digest != OBSERVATION_POLICY_DIGEST:
        raise _fail("OBSERVATION_POLICY_DIGEST_MISMATCH")
    if receipt.world_id != world.world_id:
        raise _fail("OBSERVATION_WORLD_MISMATCH")
    if receipt.baseline_version != world.baseline_version:
        raise _fail("OBSERVATION_BASELINE_MISMATCH")
    if receipt.world_state_version != world.world_state_version:
        raise _fail("STALE_OBSERVATION_WORLD_STATE_VERSION")
    if receipt.source_event_cursor != len(world.event_log):
        raise _fail("STALE_OBSERVATION_EVENT_CURSOR")

    fresh = capture_current_visual_observation(
        world=world,
        observer_actor_id=receipt.observer_actor_id,
        entity_id=receipt.entity_id,
    )
    if fresh != receipt:
        raise _fail("OBSERVATION_RECEIPT_DOES_NOT_MATCH_CURRENT_EVIDENCE")
