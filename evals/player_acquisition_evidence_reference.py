from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Mapping

from runtime.awrse.model import Event, WorldState


DIRECT_PARTICIPATION = "DIRECT_PARTICIPATION"
ELIGIBILITY_POLICY_VERSION = "AWRSE-DIRECT-PARTICIPATION-EVENT-POLICY/v1"

# Eval-only frozen policy snapshot of the currently accepted R002 primary player-action
# result families. Receipt identity binds both the version and digest so historical
# evidence cannot silently change meaning if a later policy revision adds/removes types.
_EVENT_TARGET_KEYS = MappingProxyType(
    {
        "SPEECH_UTTERED": (),
        "OBJECT_DAMAGED": ("object_id",),
        "ACTOR_STRUCK": ("target_id",),
        "OBJECT_PICKED_UP": ("object_id",),
        "OBJECT_DROPPED": ("object_id",),
        "OBJECT_THROWN": ("object_id",),
        "OBJECT_OPENED": ("object_id",),
        "OBJECT_CLOSED": ("object_id",),
        "ACTOR_MOVED": ("to_zone_id",),
    }
)


def _policy_digest() -> str:
    material = json.dumps(
        {
            "version": ELIGIBILITY_POLICY_VERSION,
            "event_target_keys": {key: list(value) for key, value in sorted(_EVENT_TARGET_KEYS.items())},
        },
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


ELIGIBILITY_POLICY_DIGEST = _policy_digest()


class PlayerAcquisitionEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class PlayerAcquisitionEvidence:
    schema: str
    receipt_id: str
    acquisition_mode: str
    source_evidence_basis: str
    world_id: str
    player_id: str
    actor_id: str
    source_event_id: str
    source_event_type: str
    caused_by_action_id: str
    event_supported_target_refs: tuple[str, ...]
    baseline_version: str
    source_event_cursor: int
    world_state_version: str
    eligibility_policy_version: str
    eligibility_policy_digest: str
    supported_claim_refs: tuple[str, ...]
    canonical_world_authority: bool
    knowledge_projection_authority: bool
    chronicle_write_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(code: str) -> PlayerAcquisitionEvidenceError:
    return PlayerAcquisitionEvidenceError(code)


def _event_cursor(world: WorldState, event: Event) -> int:
    matches = [index for index, candidate in enumerate(world.event_log, start=1) if candidate.event_id == event.event_id]
    if len(matches) != 1:
        raise _fail("SOURCE_EVENT_NOT_EXACTLY_ONCE_IN_COMMITTED_LOG")
    return matches[0]


def _receipt_id(payload: Mapping[str, Any]) -> str:
    encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "PAE-" + hashlib.sha256(encoded).hexdigest()[:24]


def _extract_event_supported_targets(world: WorldState, event: Event) -> tuple[str, ...]:
    target_keys = _EVENT_TARGET_KEYS.get(event.event_type)
    if target_keys is None:
        raise _fail("SOURCE_EVENT_NOT_PRIMARY_DIRECT_PARTICIPATION_RESULT")

    payload_actor = event.payload.get("actor_id")
    if payload_actor is not None and str(payload_actor) != event.actor_id:
        raise _fail("SOURCE_EVENT_PAYLOAD_ACTOR_MISMATCH")

    targets: list[str] = []
    for key in target_keys:
        value = str(event.payload.get(key, ""))
        if not value:
            raise _fail(f"SOURCE_EVENT_TARGET_FIELD_MISSING:{key}")
        if key == "to_zone_id":
            if value not in world.zone_scene_bindings:
                raise _fail("SOURCE_EVENT_TARGET_ZONE_NOT_REPLAYABLE")
        elif not world.entity_exists(value):
            raise _fail("SOURCE_EVENT_TARGET_ENTITY_NOT_REPLAYABLE")
        targets.append(value)
    return tuple(targets)


def derive_direct_participation_evidence(
    *,
    world: WorldState,
    player_id: str,
    event: Event,
    acquisition_mode: str = DIRECT_PARTICIPATION,
    eligibility_policy_version: str = ELIGIBILITY_POLICY_VERSION,
) -> PlayerAcquisitionEvidence:
    """Derive recipient-local evidence only from replay-available committed evidence.

    The caller supplies no Action object. Direct participation is proven from the exact
    committed primary event, its non-null causing action reference, the replayed
    principal↔actor binding, and a frozen/versioned event-eligibility policy. Supported
    target claims are extracted only from the committed event payload.
    """
    if acquisition_mode != DIRECT_PARTICIPATION:
        raise _fail("DIRECT_PARTICIPATION_MODE_ONLY")
    if eligibility_policy_version != ELIGIBILITY_POLICY_VERSION:
        raise _fail("ELIGIBILITY_POLICY_VERSION_MISMATCH")
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    if not player_id:
        raise _fail("PLAYER_ID_REQUIRED")
    if event.event_id not in world.committed_event_ids:
        raise _fail("SOURCE_EVENT_NOT_COMMITTED")

    cursor = _event_cursor(world, event)
    committed = world.event_log[cursor - 1]
    if committed != event:
        raise _fail("SOURCE_EVENT_OBJECT_MISMATCH")
    if event.baseline_version != world.baseline_version:
        raise _fail("SOURCE_EVENT_BASELINE_MISMATCH")
    if not event.actor_id:
        raise _fail("SOURCE_EVENT_ACTOR_REQUIRED")
    if not event.caused_by_action_id:
        raise _fail("SOURCE_EVENT_ACTION_PROVENANCE_REQUIRED")
    if not world.can_principal_control(player_id, event.actor_id):
        raise _fail("PLAYER_ACTOR_BINDING_NOT_PROVEN")

    target_refs = _extract_event_supported_targets(world, event)
    supported_claim_refs = (
        f"EVENT_OCCURRED:{event.event_id}:{event.event_type}",
        f"DIRECT_ACTOR:{event.actor_id}",
        *(f"EVENT_SUPPORTED_TARGET:{target_ref}" for target_ref in target_refs),
    )
    identity_payload = {
        "schema": "AWRSE.PlayerAcquisitionEvidence.Reference/v1",
        "mode": DIRECT_PARTICIPATION,
        "world_id": world.world_id,
        "player_id": player_id,
        "actor_id": event.actor_id,
        "source_event_id": event.event_id,
        "source_event_type": event.event_type,
        "caused_by_action_id": event.caused_by_action_id,
        "event_supported_target_refs": list(target_refs),
        "baseline_version": world.baseline_version,
        "source_event_cursor": cursor,
        "eligibility_policy_version": ELIGIBILITY_POLICY_VERSION,
        "eligibility_policy_digest": ELIGIBILITY_POLICY_DIGEST,
    }
    return PlayerAcquisitionEvidence(
        schema="AWRSE.PlayerAcquisitionEvidence.Reference/v1",
        receipt_id=_receipt_id(identity_payload),
        acquisition_mode=DIRECT_PARTICIPATION,
        source_evidence_basis="COMMITTED_PRIMARY_EVENT_PLUS_REPLAYED_PLAYER_ACTOR_BINDING",
        world_id=world.world_id,
        player_id=player_id,
        actor_id=event.actor_id,
        source_event_id=event.event_id,
        source_event_type=event.event_type,
        caused_by_action_id=event.caused_by_action_id,
        event_supported_target_refs=target_refs,
        baseline_version=world.baseline_version,
        source_event_cursor=cursor,
        world_state_version=world.world_state_version,
        eligibility_policy_version=ELIGIBILITY_POLICY_VERSION,
        eligibility_policy_digest=ELIGIBILITY_POLICY_DIGEST,
        supported_claim_refs=tuple(supported_claim_refs),
        canonical_world_authority=False,
        knowledge_projection_authority=False,
        chronicle_write_authority=False,
    )


def validate_supported_claim(receipt: PlayerAcquisitionEvidence, claim_ref: str) -> bool:
    """Return True only for claims mechanically enumerated from committed event evidence."""
    return claim_ref in receipt.supported_claim_refs
