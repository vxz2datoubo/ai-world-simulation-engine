from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from typing import Any

from evals.current_observation_evidence_reference import (
    CurrentObservationEvidence,
    validate_current_observation,
)
from evals.world_echo_opportunity_reference import derive_world_echo_opportunity
from runtime.awrse.model import WorldState


COMPOSITION_SCHEMA = "AWRSE.WorldEchoObservationComposition.Reference/v1"


class WorldEchoCompositionError(ValueError):
    pass


@dataclass(frozen=True)
class ComposedWorldEchoOpportunity:
    schema: str
    opportunity_id: str
    authority: str
    world_id: str
    world_state_version: str
    speaker_npc_id: str
    entity_id: str
    attribution_state: str
    culprit_actor_ref: str | None
    response_concept: str
    internal_provenance_refs: tuple[str, ...]
    historical_knowledge_refs: tuple[str, ...]
    current_observation_ref: str
    speaker_visible_claim_refs: tuple[str, ...]
    opportunity_eligible: bool
    canonical_world_authority: bool
    knowledge_write_authority: bool
    speech_commit_authority: bool

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _fail(code: str) -> WorldEchoCompositionError:
    return WorldEchoCompositionError(code)


def _id(payload: dict[str, Any]) -> str:
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return "WEOC-" + hashlib.sha256(encoded).hexdigest()[:24]


def compose_world_echo_with_observation(
    *,
    world: WorldState,
    speaker_npc_id: str,
    entity_id: str,
    source_event_id: str,
    observation_receipt: CurrentObservationEvidence,
) -> ComposedWorldEchoOpportunity:
    """Compose historical attribution with exact current observation evidence.

    The source event may be used as internal provenance, but an observer without valid
    historical acquisition receives `UNKNOWN_CAUSE`; simulator-known actor identity is
    never copied into speaker-visible claims for that path.
    """
    validate_current_observation(world=world, receipt=observation_receipt)
    if observation_receipt.observer_actor_id != speaker_npc_id:
        raise _fail("OBSERVATION_SPEAKER_MISMATCH")
    if observation_receipt.entity_id != entity_id:
        raise _fail("OBSERVATION_ENTITY_MISMATCH")
    if observation_receipt.world_state_version != world.world_state_version:
        raise _fail("OBSERVATION_WORLD_VERSION_MISMATCH")

    damage_refs = [
        ref for ref in observation_receipt.observable_state_refs
        if ref.startswith(f"OBJECT_DAMAGE_STATE:{entity_id}:")
    ]
    if len(damage_refs) != 1 or damage_refs[0].endswith(":INTACT"):
        raise _fail("CURRENT_OBSERVATION_DOES_NOT_PROVE_DAMAGE")

    historical = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id=speaker_npc_id,
        entity_id=entity_id,
        source_event_id=source_event_id,
    )

    if historical.status == "CANDIDATE_BLOCKED_PENDING_CURRENT_PERCEPTION" and historical.opportunity:
        candidate = historical.opportunity
        attribution_state = candidate.attribution_state
        culprit = candidate.culprit_actor_ref
        response_concept = candidate.response_concept
        historical_refs = candidate.knowledge_attribution_refs
        visible_claims = tuple(observation_receipt.observable_state_refs) + (
            f"KNOWN_CULPRIT:{culprit}",
        )
    elif historical.status == "NO_VALID_OPPORTUNITY" and historical.reason == "NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION":
        attribution_state = "UNKNOWN_CAUSE"
        culprit = None
        response_concept = "REMARK_UNKNOWN_DAMAGE"
        historical_refs = ()
        visible_claims = tuple(observation_receipt.observable_state_refs)
    else:
        raise _fail("HISTORICAL_EVIDENCE_NOT_COMPOSABLE_BY_V1")

    identity = {
        "schema": COMPOSITION_SCHEMA,
        "world_id": world.world_id,
        "world_state_version": world.world_state_version,
        "speaker_npc_id": speaker_npc_id,
        "entity_id": entity_id,
        "source_event_id": source_event_id,
        "observation_receipt_id": observation_receipt.receipt_id,
        "historical_knowledge_refs": list(historical_refs),
        "attribution_state": attribution_state,
        "response_concept": response_concept,
    }
    return ComposedWorldEchoOpportunity(
        schema=COMPOSITION_SCHEMA,
        opportunity_id=_id(identity),
        authority="NARRATIVE_OPPORTUNITY_NON_CANONICAL",
        world_id=world.world_id,
        world_state_version=world.world_state_version,
        speaker_npc_id=speaker_npc_id,
        entity_id=entity_id,
        attribution_state=attribution_state,
        culprit_actor_ref=culprit,
        response_concept=response_concept,
        internal_provenance_refs=(source_event_id, observation_receipt.receipt_id),
        historical_knowledge_refs=tuple(historical_refs),
        current_observation_ref=observation_receipt.receipt_id,
        speaker_visible_claim_refs=visible_claims,
        opportunity_eligible=True,
        canonical_world_authority=False,
        knowledge_write_authority=False,
        speech_commit_authority=False,
    )
