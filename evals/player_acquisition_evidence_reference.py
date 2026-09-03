from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any

from runtime.awrse.model import Event, WorldState


DIRECT_PARTICIPATION = "DIRECT_PARTICIPATION"
ELIGIBILITY_POLICY_VERSION = "AWRSE-DIRECT-PARTICIPATION-EVENT-POLICY/v2-GAP-PROOF"

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
            "required_explicit_player_provenance": [
                "player_or_principal_id",
                "actor_id",
                "action_id",
                "source_channel",
                "explicit_input_presence",
                "accepted_resolution_or_commit_binding",
                "replay_integrity_ref",
            ],
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
    """Candidate receipt shape only. Current accepted replay evidence cannot mint it safely."""

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
    explicit_player_action_provenance_ref: str
    eligibility_policy_version: str
    eligibility_policy_digest: str
    supported_claim_refs: tuple[str, ...]
    canonical_world_authority: bool = False
    knowledge_projection_authority: bool = False
    chronicle_write_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DirectParticipationGapProof:
    schema: str
    status: str
    reason: str
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
    player_actor_binding_proven: bool
    primary_event_eligibility_proven: bool
    replay_explicit_player_action_provenance_available: bool
    receipt_available: bool
    eligibility_policy_version: str
    eligibility_policy_digest: str
    required_future_provenance_fields: tuple[str, ...]
    canonical_world_authority: bool = False
    knowledge_projection_authority: bool = False
    chronicle_write_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(code: str) -> PlayerAcquisitionEvidenceError:
    return PlayerAcquisitionEvidenceError(code)


def _event_cursor(world: WorldState, event: Event) -> int:
    matches = [index for index, candidate in enumerate(world.event_log, start=1) if candidate.event_id == event.event_id]
    if len(matches) != 1:
        raise _fail("SOURCE_EVENT_NOT_EXACTLY_ONCE_IN_COMMITTED_LOG")
    return matches[0]


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


def assess_direct_participation_gap(
    *,
    world: WorldState,
    player_id: str,
    event: Event,
    acquisition_mode: str = DIRECT_PARTICIPATION,
    eligibility_policy_version: str = ELIGIBILITY_POLICY_VERSION,
) -> DirectParticipationGapProof:
    """Prove exactly why current replay evidence cannot establish DIRECT_PARTICIPATION.

    Accepted R002 replay reconstructs baseline + committed Event evidence and player/actor
    bindings. `Event.caused_by_action_id` proves a causal action identifier exists, but the
    replayed Event does not carry authoritative `source_channel` or explicit-player-input
    provenance. Therefore a system/NPC/narrative-originated action for a player-controlled
    avatar cannot be distinguished from an explicit player-originated action by this
    evidence surface alone. The safe result is a negative architecture gap proof.
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
        raise _fail("SOURCE_EVENT_ACTION_ID_REQUIRED")
    if not world.can_principal_control(player_id, event.actor_id):
        raise _fail("PLAYER_ACTOR_BINDING_NOT_PROVEN")

    target_refs = _extract_event_supported_targets(world, event)

    # This is intentionally a mechanical check of the accepted replay surface, not a
    # caller flag. Current Event does not persist the Action source channel or explicit
    # input provenance needed by Issue #107's `explicit player action` requirement.
    replay_action_provenance_available = all(
        hasattr(event, field_name)
        for field_name in ("source_channel", "literal_user_input", "principal_id")
    )
    if replay_action_provenance_available:
        raise _fail("UNEXPECTED_REPLAY_ACTION_PROVENANCE_SURFACE_REQUIRES_FRESH_ARCHITECTURE_REVIEW")

    return DirectParticipationGapProof(
        schema="AWRSE.PlayerAcquisitionEvidence.GapProof/v1",
        status="BLOCKED_MISSING_REPLAY_PLAYER_ACTION_PROVENANCE",
        reason="COMMITTED_EVENT_AND_PLAYER_ACTOR_BINDING_DO_NOT_PROVE_EXPLICIT_PLAYER_SOURCE_CHANNEL_OR_INPUT",
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
        player_actor_binding_proven=True,
        primary_event_eligibility_proven=True,
        replay_explicit_player_action_provenance_available=False,
        receipt_available=False,
        eligibility_policy_version=ELIGIBILITY_POLICY_VERSION,
        eligibility_policy_digest=ELIGIBILITY_POLICY_DIGEST,
        required_future_provenance_fields=(
            "provenance_receipt_id",
            "player_or_principal_id",
            "actor_id",
            "action_id",
            "eligible_source_channel",
            "explicit_input_presence_without_raw_text",
            "accepted_resolution_or_commit_ref",
            "baseline_version",
            "world_or_event_cursor",
            "policy_version",
            "integrity_digest",
        ),
        canonical_world_authority=False,
        knowledge_projection_authority=False,
        chronicle_write_authority=False,
    )


def derive_direct_participation_evidence(
    *,
    world: WorldState,
    player_id: str,
    event: Event,
    acquisition_mode: str = DIRECT_PARTICIPATION,
    eligibility_policy_version: str = ELIGIBILITY_POLICY_VERSION,
) -> PlayerAcquisitionEvidence:
    """Fail closed until replay contains trusted explicit-player action provenance."""
    assessment = assess_direct_participation_gap(
        world=world,
        player_id=player_id,
        event=event,
        acquisition_mode=acquisition_mode,
        eligibility_policy_version=eligibility_policy_version,
    )
    if not assessment.receipt_available:
        raise _fail("EXPLICIT_PLAYER_ACTION_PROVENANCE_NOT_REPLAY_AVAILABLE")
    raise _fail("UNREACHABLE_DIRECT_PARTICIPATION_RECEIPT_PATH")


def validate_supported_claim(receipt: PlayerAcquisitionEvidence, claim_ref: str) -> bool:
    """Caller-constructed candidate receipts are not trusted by the current runtime."""
    raise _fail("UNTRUSTED_PLAYER_ACQUISITION_RECEIPT_UNSUPPORTED_BY_CURRENT_RUNTIME")
