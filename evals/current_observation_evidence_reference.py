from __future__ import annotations

import hashlib
from dataclasses import asdict, dataclass
from typing import Any

from runtime.awrse.model import WorldState


OBSERVATION_POLICY_VERSION = "AWRSE-CURRENT-VISUAL-OBSERVATION-POLICY/v2-GAP-PROOF"
OBSERVATION_POLICY_DIGEST = hashlib.sha256(
    b"VISUAL_OBJECT_ONLY|WORLDSTATE_CAN_SEE_IS_ELIGIBILITY_ONLY|TRUSTED_DISCRETE_TRIGGER_REQUIRED|NO_CALLER_MINT|NO_KNOWLEDGE_WRITE|NO_HIDDEN_CAUSE"
).hexdigest()


class CurrentObservationEvidenceError(ValueError):
    pass


@dataclass(frozen=True)
class CurrentObservationEvidence:
    """Candidate receipt shape only. Current accepted runtime cannot authoritatively mint it."""

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
    trusted_trigger_ref: str
    canonical_world_authority: bool = False
    knowledge_write_authority: bool = False
    narrative_realization_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CurrentObservationGapProof:
    schema: str
    status: str
    reason: str
    world_id: str
    world_state_version: str
    baseline_version: str
    source_event_cursor: int
    observer_actor_id: str
    entity_id: str
    scene_id: str
    visibility_eligible: bool
    trusted_discrete_trigger_available: bool
    receipt_available: bool
    observation_policy_version: str
    observation_policy_digest: str
    required_future_trigger_fields: tuple[str, ...]
    canonical_world_authority: bool = False
    knowledge_write_authority: bool = False
    narrative_realization_authority: bool = False

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(code: str) -> CurrentObservationEvidenceError:
    return CurrentObservationEvidenceError(code)


def _validate_eligibility_inputs(
    *,
    world: WorldState,
    observer_actor_id: str,
    entity_id: str,
    observation_policy_version: str,
):
    if observation_policy_version != OBSERVATION_POLICY_VERSION:
        raise _fail("OBSERVATION_POLICY_VERSION_MISMATCH")
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    observer = world.actors.get(observer_actor_id)
    if observer is None:
        raise _fail("OBSERVER_ACTOR_NOT_FOUND")
    obj = world.objects.get(entity_id)
    if obj is None:
        raise _fail("V2_VISUAL_OBSERVATION_SUPPORTS_OBJECTS_ONLY")
    if observer.scene_id != obj.scene_id:
        raise _fail("OBSERVATION_SCENE_MISMATCH")
    return observer, obj


def assess_current_visual_observation_gap(
    *,
    world: WorldState,
    observer_actor_id: str,
    entity_id: str,
    observation_policy_version: str = OBSERVATION_POLICY_VERSION,
) -> CurrentObservationGapProof:
    """Prove the current runtime gap without converting visibility into observation.

    `WorldState.can_see()` answers only whether observation would be physically/symbolically
    eligible at this state. The accepted runtime has no trusted discrete perception trigger
    proving that this observer actually sampled this entity at this exact cursor. Therefore
    even when visibility is true this function returns a gap proof, never a receipt.
    """
    observer, _ = _validate_eligibility_inputs(
        world=world,
        observer_actor_id=observer_actor_id,
        entity_id=entity_id,
        observation_policy_version=observation_policy_version,
    )
    visible = bool(world.can_see(entity_id, observer_actor_id))
    return CurrentObservationGapProof(
        schema="AWRSE.CurrentObservationEvidence.GapProof/v1",
        status="NO_TRUSTED_OBSERVATION_TRIGGER" if visible else "VISUAL_ELIGIBILITY_NOT_PROVEN",
        reason=(
            "VISIBILITY_TRUE_BUT_ACCEPTED_RUNTIME_HAS_NO_NON_CALLER_MINTABLE_DISCRETE_OBSERVATION_TRIGGER"
            if visible
            else "WORLDSTATE_CAN_SEE_FALSE"
        ),
        world_id=world.world_id,
        world_state_version=world.world_state_version,
        baseline_version=world.baseline_version,
        source_event_cursor=len(world.event_log),
        observer_actor_id=observer_actor_id,
        entity_id=entity_id,
        scene_id=observer.scene_id,
        visibility_eligible=visible,
        trusted_discrete_trigger_available=False,
        receipt_available=False,
        observation_policy_version=OBSERVATION_POLICY_VERSION,
        observation_policy_digest=OBSERVATION_POLICY_DIGEST,
        required_future_trigger_fields=(
            "trigger_id",
            "trusted_trigger_authority_ref",
            "world_id",
            "baseline_version",
            "world_state_version",
            "source_event_cursor",
            "observer_actor_id",
            "entity_id",
            "observation_mode",
            "triggered_at_world_time_or_tick",
            "visibility_policy_version",
            "integrity_digest",
        ),
        canonical_world_authority=False,
        knowledge_write_authority=False,
        narrative_realization_authority=False,
    )


def capture_current_visual_observation(
    *,
    world: WorldState,
    observer_actor_id: str,
    entity_id: str,
    observation_policy_version: str = OBSERVATION_POLICY_VERSION,
) -> CurrentObservationEvidence:
    """Fail closed: callers cannot turn eligibility into a provenance-bearing observation."""
    assessment = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=observer_actor_id,
        entity_id=entity_id,
        observation_policy_version=observation_policy_version,
    )
    if not assessment.visibility_eligible:
        raise _fail("VISUAL_ELIGIBILITY_NOT_PROVEN")
    raise _fail("NO_TRUSTED_OBSERVATION_TRIGGER")


def validate_current_observation(*, world: WorldState, receipt: CurrentObservationEvidence) -> None:
    """No caller-constructed receipt is trusted until a real runtime trigger authority exists."""
    if not world.is_live:
        raise _fail("LIVE_SEALED_WORLD_REQUIRED")
    if receipt.observation_policy_version != OBSERVATION_POLICY_VERSION:
        raise _fail("OBSERVATION_POLICY_VERSION_MISMATCH")
    if receipt.observation_policy_digest != OBSERVATION_POLICY_DIGEST:
        raise _fail("OBSERVATION_POLICY_DIGEST_MISMATCH")
    if receipt.canonical_world_authority or receipt.knowledge_write_authority or receipt.narrative_realization_authority:
        raise _fail("OBSERVATION_AUTHORITY_ESCALATION_FORBIDDEN")
    raise _fail("UNTRUSTED_OBSERVATION_RECEIPT_UNSUPPORTED_BY_CURRENT_RUNTIME")
