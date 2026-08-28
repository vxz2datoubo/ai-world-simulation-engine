"""Bounded I8B recipient-specific promise callback opportunity reference.

This module consumes canonical I8A promise evidence plus the existing I4A
recipient-local memory projection. It produces only a non-canonical AF-G
ResponseConcept opportunity, or NO_VALID_CALLBACK. It never creates speech,
relationship effects, promise payoff, Storylet realization, PX ranking,
Director output, or world events.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse import (
    WorldBaseline,
    WorldState,
    export_solo_replay_package,
    import_solo_replay_package,
    rehydrate_solo_replay_package,
)
from awrse.model import freeze_value, thaw_value
import evals.i4a_npc_memory_reference as i4a_reference
import evals.i8a_narrative_promise_reference as i8a_reference

I8B_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_SECOND_MEMORY_LEDGER = True
NO_AUTOMATIC_SPEECH_EVENT = True
NO_RELATIONSHIP_MUTATION = True
NO_PROMISE_PAYOFF_OR_BREACH = True
NO_STORYLET_REALIZATION = True
NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.10.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1",
)
_EXPECTED_RESPONSE_TYPE = (
    "AF001.ResponseConcept",
    "1.0.0-candidate",
    "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
)
_EXPECTED_RESPONSE_FIELDS = {
    "response_concept_id",
    "speech_risk_class",
    "required_fact_refs",
    "forbidden_claim_classes",
    "realization_constraints",
}
_REQUIRED_AF_G_INVARIANTS = {
    "NO_VALID_OPPORTUNITY_IS_VALID",
    "PX_MAY_RANK_ONLY_LEGAL_CANDIDATES",
    "PX_CANNOT_INVENT_FACTS_OR_INJECT_KNOWLEDGE",
}
_PACKAGE_SCHEMA = "AWRSE-I8B-PROMISE-CALLBACK-REPLAY-1"
_AUTHORITY_CLASS = "NON_CANONICAL_RECIPIENT_SPECIFIC_PROMISE_CALLBACK_OPPORTUNITY_ONLY"


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


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
        raise ValueError("I8B_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I8B_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I8B_JSON_NONFINITE:{value}")


def _load_authority() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I8B_CANONICAL_CONTRACT_UNAVAILABLE") from None
    if not isinstance(contract, Mapping):
        raise ValueError("I8B_CANONICAL_CONTRACT_INVALID")
    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I8B_CANONICAL_PARENT_DRIFT")
    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I8B_TYPE_REGISTRY_MISSING")
    entry = registry.get("ResponseConcept")
    if not isinstance(entry, Mapping):
        raise ValueError("I8B_RESPONSE_CONCEPT_TYPE_MISSING")
    actual = (
        entry.get("type_id"),
        entry.get("version"),
        entry.get("authority_profile_ref"),
    )
    if actual != _EXPECTED_RESPONSE_TYPE:
        raise ValueError("I8B_RESPONSE_CONCEPT_TYPE_DRIFT")
    if set(entry.get("fields", [])) != _EXPECTED_RESPONSE_FIELDS:
        raise ValueError("I8B_RESPONSE_CONCEPT_FIELDS_DRIFT")
    af_g = contract.get("freeze_domains", {}).get("AF-G")
    if not isinstance(af_g, Mapping):
        raise ValueError("I8B_AF_G_AUTHORITY_MISSING")
    if not _REQUIRED_AF_G_INVARIANTS <= set(af_g.get("invariants", [])):
        raise ValueError("I8B_AF_G_INVARIANT_DRIFT")
    profile = contract.get("authority_semantics", {}).get("profiles", {}).get(
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL"
    )
    if not isinstance(profile, Mapping):
        raise ValueError("I8B_OPPORTUNITY_AUTHORITY_PROFILE_MISSING")
    if profile.get("canonical_data_authority") != ["NONE"]:
        raise ValueError("I8B_OPPORTUNITY_CANONICAL_AUTHORITY_DRIFT")
    if profile.get("staging_authority") != ["NONE"]:
        raise ValueError("I8B_OPPORTUNITY_STAGING_AUTHORITY_DRIFT")
    return _EXPECTED_PARENT


@dataclass(frozen=True)
class PromiseCallbackOpportunityReference:
    player_actor_id: str
    promise_recipient_npc_id: str
    candidate_npc_id: str
    target_object_id: str
    source_speech_event_id: str
    source_acquisition_event_id: str
    source_promise_id: str
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    contract_id: str
    contract_version: str
    authority_graph_version: str
    outcome: str
    reason: str
    response_concept: Mapping[str, Any] | None
    authority_class: str


def _reference_material(reference: PromiseCallbackOpportunityReference) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "player_actor_id": reference.player_actor_id,
                "promise_recipient_npc_id": reference.promise_recipient_npc_id,
                "candidate_npc_id": reference.candidate_npc_id,
                "target_object_id": reference.target_object_id,
                "source_speech_event_id": reference.source_speech_event_id,
                "source_acquisition_event_id": reference.source_acquisition_event_id,
                "source_promise_id": reference.source_promise_id,
                "source_world_id": reference.source_world_id,
                "source_baseline_version": reference.source_baseline_version,
                "source_state_version": reference.source_state_version,
                "contract_id": reference.contract_id,
                "contract_version": reference.contract_version,
                "authority_graph_version": reference.authority_graph_version,
                "outcome": reference.outcome,
                "reason": reference.reason,
                "response_concept": (
                    None
                    if reference.response_concept is None
                    else thaw_value(reference.response_concept)
                ),
                "authority_class": reference.authority_class,
            }
        )
    )


def _make_result(
    *,
    world: WorldState,
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
    source_acquisition_event_id: str,
    source_promise_id: str,
    contract: tuple[str, str, str],
    outcome: str,
    reason: str,
    response_concept: Mapping[str, Any] | None,
) -> PromiseCallbackOpportunityReference:
    return PromiseCallbackOpportunityReference(
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
        source_acquisition_event_id=source_acquisition_event_id,
        source_promise_id=source_promise_id,
        source_world_id=world.world_id,
        source_baseline_version=world.baseline_version,
        source_state_version=world.state_version,
        contract_id=contract[0],
        contract_version=contract[1],
        authority_graph_version=contract[2],
        outcome=outcome,
        reason=reason,
        response_concept=(
            None if response_concept is None else freeze_value(dict(response_concept))
        ),
        authority_class=_AUTHORITY_CLASS,
    )


def _build_from_replay_validated_world(
    *,
    world: WorldState,
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> PromiseCallbackOpportunityReference:
    contract = _load_authority()
    player_actor_id = _require_string(player_actor_id, "I8B_PLAYER_ACTOR_ID_REQUIRED")
    promise_recipient_npc_id = _require_string(
        promise_recipient_npc_id, "I8B_PROMISE_RECIPIENT_NPC_ID_REQUIRED"
    )
    candidate_npc_id = _require_string(candidate_npc_id, "I8B_CANDIDATE_NPC_ID_REQUIRED")
    target_object_id = _require_string(target_object_id, "I8B_TARGET_OBJECT_ID_REQUIRED")
    source_speech_event_id = _require_string(
        source_speech_event_id, "I8B_SOURCE_SPEECH_EVENT_ID_REQUIRED"
    )
    if player_actor_id != world.primary_player_actor_id or player_actor_id not in world.actors:
        raise ValueError("I8B_PLAYER_NOT_CANONICAL_PRIMARY_ACTOR")
    if promise_recipient_npc_id not in world.npc_minds:
        raise ValueError("I8B_PROMISE_RECIPIENT_NPC_NOT_FOUND")
    if candidate_npc_id not in world.npc_minds or candidate_npc_id not in world.actors:
        raise ValueError("I8B_CANDIDATE_NPC_NOT_FOUND")

    promise_ref = i8a_reference._build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        recipient_npc_id=promise_recipient_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )
    promise = thaw_value(promise_ref.narrative_promise)
    promise_id = _require_string(promise.get("promise_id"), "I8B_SOURCE_PROMISE_ID_REQUIRED")

    def no_valid(reason: str) -> PromiseCallbackOpportunityReference:
        return _make_result(
            world=world,
            player_actor_id=player_actor_id,
            promise_recipient_npc_id=promise_recipient_npc_id,
            candidate_npc_id=candidate_npc_id,
            target_object_id=target_object_id,
            source_speech_event_id=source_speech_event_id,
            source_acquisition_event_id=promise_ref.source_acquisition_event_id,
            source_promise_id=promise_id,
            contract=contract,
            outcome="NO_VALID_CALLBACK",
            reason=reason,
            response_concept=None,
        )

    if promise.get("status") != "CALLBACK_ELIGIBLE" or not bool(
        promise.get("callback_eligibility", {}).get("eligible")
    ):
        return no_valid("PROMISE_NOT_CALLBACK_ELIGIBLE")

    candidate_memory = i4a_reference._build_from_replay_validated_world(
        world=world,
        npc_id=candidate_npc_id,
        player_ids=[player_actor_id],
    )
    if candidate_npc_id != promise_recipient_npc_id:
        return no_valid("CANDIDATE_NOT_BOUND_PROMISE_RECIPIENT")

    player_scene = world.actors[player_actor_id].scene_id
    candidate_scene = world.actors[candidate_npc_id].scene_id
    if (
        player_scene != world.active_scene_id
        or candidate_scene != world.active_scene_id
        or player_scene != candidate_scene
    ):
        return no_valid("CURRENT_REPLAY_VALID_SCENE_CONTEXT_NOT_SHARED")

    expected_perception_ref = f"PERCEPTION:{promise_ref.source_acquisition_event_id}"
    matching_memories = []
    for row in candidate_memory.episodic_memories:
        material = thaw_value(row)
        if (
            material.get("npc_id") == candidate_npc_id
            and material.get("provenance_kind") == "HEARD"
            and material.get("source_world_event_refs") == [source_speech_event_id]
            and material.get("source_perception_refs") == [expected_perception_ref]
        ):
            matching_memories.append(material)
    if len(matching_memories) != 1:
        return no_valid("EXACT_RECIPIENT_HEARD_MEMORY_REQUIRED")

    required_fact_refs = list(promise.get("source_refs", []))
    if required_fact_refs != [
        promise_ref.source_speech_event_id,
        promise_ref.source_acquisition_event_id,
        promise_ref.source_damage_event_id,
    ]:
        raise ValueError("I8B_PROMISE_SOURCE_REF_BINDING_DRIFT")

    response_concept = {
        "response_concept_id": f"RESPONSE:PROMISE_CALLBACK:{promise_id}:{candidate_npc_id}",
        "speech_risk_class": "NPC_KNOWING_CALLBACK_CONCEPT_ONLY",
        "required_fact_refs": required_fact_refs,
        "forbidden_claim_classes": [
            "INVENTED_PRIOR_PROMISE",
            "UNACQUIRED_THIRD_PARTY_PROMISE_KNOWLEDGE",
            "PLAYER_FULFILLMENT_NOT_IN_EVIDENCE",
            "PLAYER_BREACH_NOT_IN_EVIDENCE",
            "PLAYER_CURRENT_INTENT_NOT_IN_EVIDENCE",
        ],
        "realization_constraints": [
            "NON_CANONICAL_OPPORTUNITY_ONLY",
            "BOUND_NPC_MAY_REFERENCE_ONLY_EXACT_ACQUIRED_PROMISE",
            "NO_AUTOMATIC_SPEECH_EVENT",
            "NO_RELATIONSHIP_MUTATION",
            "NO_PROMISE_PAYOFF_OR_BREACH",
            "NO_STORYLET_REALIZATION",
            "REVALIDATE_CURRENT_WORLD_BEFORE_ANY_LATER_REALIZATION",
        ],
    }
    if set(response_concept) != _EXPECTED_RESPONSE_FIELDS:
        raise ValueError("I8B_RESPONSE_CONCEPT_MATERIALIZATION_FIELDS_INVALID")
    return _make_result(
        world=world,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
        source_acquisition_event_id=promise_ref.source_acquisition_event_id,
        source_promise_id=promise_id,
        contract=contract,
        outcome="CALLBACK_OPPORTUNITY",
        reason="EXACT_RECIPIENT_HEARD_PROMISE_AND_CURRENT_CONTEXT_VALID",
        response_concept=response_concept,
    )


def build_promise_callback_opportunity_reference(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
    caller_callback_evidence: Mapping[str, Any] | None = None,
) -> PromiseCallbackOpportunityReference:
    """Validate world truth through I1, then derive a non-canonical callback opportunity."""
    if caller_callback_evidence is not None:
        raise ValueError("I8B_CALLER_AUTHORED_CALLBACK_EVIDENCE_FORBIDDEN")
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8B_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I8B_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    export_solo_replay_package(baseline, world)
    return _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )


def export_promise_callback_package(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> bytes:
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8B_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I8B_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    solo_package = export_solo_replay_package(baseline, world)
    reference = _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "player_actor_id": player_actor_id,
        "promise_recipient_npc_id": promise_recipient_npc_id,
        "candidate_npc_id": candidate_npc_id,
        "target_object_id": target_object_id,
        "source_speech_event_id": source_speech_event_id,
        "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(),
        "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"),
        "expected_reference": _reference_material(reference),
    }
    return _canonical_json({"payload": payload, "sha256": _sha256(payload)}).encode("utf-8")


def replay_promise_callback_package(
    package: bytes | bytearray | memoryview,
) -> PromiseCallbackOpportunityReference:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8B_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8B_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8B_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I8B_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8B_REPLAY_PACKAGE_TAMPERED")
    replay_b64 = _require_string(payload.get("source_i1_replay_b64"), "I8B_I1_REPLAY_REQUIRED")
    try:
        solo_package = base64.b64decode(replay_b64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8B_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get("source_i1_replay_sha256"):
        raise ValueError("I8B_I1_REPLAY_DIGEST_MISMATCH")
    evidence = import_solo_replay_package(solo_package)
    world = rehydrate_solo_replay_package(solo_package)
    rebuilt = _build_from_replay_validated_world(
        world=world,
        player_actor_id=payload.get("player_actor_id"),
        promise_recipient_npc_id=payload.get("promise_recipient_npc_id"),
        candidate_npc_id=payload.get("candidate_npc_id"),
        target_object_id=payload.get("target_object_id"),
        source_speech_event_id=payload.get("source_speech_event_id"),
    )
    if rebuilt.source_world_id != evidence.world_id or rebuilt.source_baseline_version != evidence.baseline_version:
        raise ValueError("I8B_REPLAY_I1_SOURCE_BINDING_MISMATCH")
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I8B_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH")
    return rebuilt
