from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any, Mapping

from runtime.awrse.model import Action, Event, ResolutionStatus, SourceChannel, WorldState


DIRECT_PARTICIPATION = "DIRECT_PARTICIPATION"
_ALLOWED_ACTION_CHANNELS = {
    SourceChannel.PLAYER_ACTION_DECLARATION,
    SourceChannel.DIRECT_CONTROL_INPUT,
    SourceChannel.PLAYER_DIEGETIC_SPEECH,
}
_ALLOWED_RESOLUTION_STATUSES = {
    ResolutionStatus.RESOLVED_SUCCESS,
    ResolutionStatus.RESOLVED_PARTIAL,
}


class PlayerAcquisitionEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class PlayerAcquisitionEvidence:
    schema: str
    receipt_id: str
    acquisition_mode: str
    world_id: str
    player_id: str
    actor_id: str
    source_event_id: str
    source_event_type: str
    caused_by_action_id: str
    action_source_channel: str
    action_target_ids: tuple[str, ...]
    literal_input_present: bool
    baseline_version: str
    source_event_cursor: int
    world_state_version: str
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


def derive_direct_participation_evidence(
    *,
    world: WorldState,
    player_id: str,
    action: Action,
    event: Event,
    acquisition_mode: str = DIRECT_PARTICIPATION,
) -> PlayerAcquisitionEvidence:
    """Derive noncanonical recipient-local evidence from already committed action/event evidence.

    This function intentionally emits no arbitrary proposition text and no payload-derived hidden facts.
    The receipt proves only direct participation in the source event and the explicit target identities
    already present in the player's own action declaration.
    """
    if acquisition_mode != DIRECT_PARTICIPATION:
        raise _fail("DIRECT_PARTICIPATION_MODE_ONLY")
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    if not player_id or action.principal_id != player_id:
        raise _fail("PLAYER_ACTION_PRINCIPAL_MISMATCH")
    if not world.can_principal_control(player_id, action.actor_id):
        raise _fail("PLAYER_ACTOR_BINDING_NOT_PROVEN")
    if action.source_channel not in _ALLOWED_ACTION_CHANNELS:
        raise _fail("ACTION_SOURCE_CHANNEL_NOT_DIRECT_PARTICIPATION_ELIGIBLE")
    if action.resolution_status not in _ALLOWED_RESOLUTION_STATUSES:
        raise _fail("ACTION_NOT_SUCCESSFULLY_RESOLVED")
    if not action.literal_user_input.strip():
        raise _fail("EXPLICIT_INPUT_PROVENANCE_MISSING")
    if event.event_id not in world.committed_event_ids:
        raise _fail("SOURCE_EVENT_NOT_COMMITTED")
    cursor = _event_cursor(world, event)
    committed = world.event_log[cursor - 1]
    if committed != event:
        raise _fail("SOURCE_EVENT_OBJECT_MISMATCH")
    if event.actor_id != action.actor_id:
        raise _fail("SOURCE_EVENT_ACTOR_MISMATCH")
    if event.caused_by_action_id != action.action_id:
        raise _fail("SOURCE_EVENT_ACTION_CAUSE_MISMATCH")
    if event.baseline_version != world.baseline_version:
        raise _fail("SOURCE_EVENT_BASELINE_MISMATCH")

    supported_claim_refs = (
        f"EVENT_OCCURRED:{event.event_id}:{event.event_type}",
        f"DIRECT_ACTOR:{action.actor_id}",
        *(f"EXPLICIT_ACTION_TARGET:{target_id}" for target_id in action.target_ids),
    )
    identity_payload = {
        "schema": "AWRSE.PlayerAcquisitionEvidence.Reference/v0",
        "mode": DIRECT_PARTICIPATION,
        "world_id": world.world_id,
        "player_id": player_id,
        "actor_id": action.actor_id,
        "source_event_id": event.event_id,
        "source_event_type": event.event_type,
        "action_id": action.action_id,
        "source_channel": action.source_channel.value,
        "action_target_ids": list(action.target_ids),
        "baseline_version": world.baseline_version,
        "source_event_cursor": cursor,
    }
    return PlayerAcquisitionEvidence(
        schema="AWRSE.PlayerAcquisitionEvidence.Reference/v0",
        receipt_id=_receipt_id(identity_payload),
        acquisition_mode=DIRECT_PARTICIPATION,
        world_id=world.world_id,
        player_id=player_id,
        actor_id=action.actor_id,
        source_event_id=event.event_id,
        source_event_type=event.event_type,
        caused_by_action_id=action.action_id,
        action_source_channel=action.source_channel.value,
        action_target_ids=tuple(action.target_ids),
        literal_input_present=True,
        baseline_version=world.baseline_version,
        source_event_cursor=cursor,
        world_state_version=world.world_state_version,
        supported_claim_refs=tuple(supported_claim_refs),
        canonical_world_authority=False,
        knowledge_projection_authority=False,
        chronicle_write_authority=False,
    )


def validate_supported_claim(receipt: PlayerAcquisitionEvidence, claim_ref: str) -> bool:
    """Return True only for mechanically enumerated direct-participation claims.

    This is deliberately not a free-text proposition evaluator and cannot broaden the receipt.
    """
    return claim_ref in receipt.supported_claim_refs
