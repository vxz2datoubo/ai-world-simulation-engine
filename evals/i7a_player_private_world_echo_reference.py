"""Bounded I7A player-private World Echo self-callback reference.

Canonical SOLO history remains world truth. This module derives only a non-canonical
World Echo opportunity and a private, non-diegetic presentation reference from a
replay-validated self-caused persistent object-damage event.
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
from awrse.model import Event, freeze_value, thaw_value

I7_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_DIEGETIC_PLAYER_SPEECH = True
NO_WORLD_EVENT_COMMIT = True
NO_NPC_KNOWLEDGE_MUTATION = True
NO_LLM_OR_PROVIDER = True
NO_PX_DIRECTOR_RENDERER_AUTHORITY = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_CONFORMANCE_PATH = _ROOT / "evals" / "AF001-WORLD-ECHO-CONFORMANCE.json"
_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.9.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
)
_EXPECTED_TYPES = {
    "WorldEchoOpportunity": (
        "AF001.WorldEchoOpportunity",
        "1.0.0-candidate",
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
    ),
    "ResponseConcept": (
        "AF001.ResponseConcept",
        "1.0.0-candidate",
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
    ),
    "PlayerAutoExpressionPolicy": (
        "AF001.PlayerAutoExpressionPolicy",
        "1.0.0-candidate",
        "PLAYER_EXPLICIT_AUTO_EXPRESSION_POLICY",
    ),
}
_EXPECTED_FIELDS = {
    "WorldEchoOpportunity": {
        "echo_id",
        "source_event_or_delta_refs",
        "speaker_candidate_refs",
        "knowledge_attribution_refs",
        "response_concept_refs",
        "novelty_key",
        "expiry_policy",
    },
    "ResponseConcept": {
        "response_concept_id",
        "speech_risk_class",
        "required_fact_refs",
        "forbidden_claim_classes",
        "realization_constraints",
    },
    "PlayerAutoExpressionPolicy": {
        "player_id",
        "policy_version",
        "private_commentary_enabled",
        "authorized_low_risk_bark_enabled",
        "allowed_risk_classes",
        "explicit_override_ref",
    },
}
_REQUIRED_AF_G_INVARIANTS = {
    "NO_VALID_OPPORTUNITY_IS_VALID",
    "PX_CANNOT_INVENT_FACTS_OR_INJECT_KNOWLEDGE",
    "COMMENTARY_REQUIRES_PROVENANCE_AND_ANTI_REPEAT_POLICY",
}
_REFERENCE_FILTER_AUTHORITY = (
    "AUTHORED_REFERENCE_PRESENTATION_FILTER_ONLY_NOT_PLAYER_POLICY_AUTHORITY"
)
_REFERENCE_AUTHORITY_CLASS = (
    "DERIVED_PRIVATE_WORLD_ECHO_REFERENCE_ONLY_NOT_WORLD_OR_PLAYER_INTENT_TRUTH"
)
_PACKAGE_SCHEMA = "AWRSE-I7A-PLAYER-PRIVATE-WORLD-ECHO-REPLAY-1"


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
        raise ValueError("I7A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I7A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I7A_JSON_NONFINITE:{value}")


def _load_authority() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
        conformance = json.loads(_CONFORMANCE_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I7A_CANONICAL_AUTHORITY_INPUT_UNAVAILABLE") from None

    if not isinstance(contract, Mapping):
        raise ValueError("I7A_CANONICAL_CONTRACT_INVALID")
    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I7A_CANONICAL_PARENT_DRIFT")

    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I7A_TYPE_REGISTRY_MISSING")
    for name, expected in _EXPECTED_TYPES.items():
        entry = registry.get(name)
        if not isinstance(entry, Mapping):
            raise ValueError(f"I7A_CANONICAL_TYPE_MISSING:{name}")
        actual = (
            entry.get("type_id"),
            entry.get("version"),
            entry.get("authority_profile_ref"),
        )
        if actual != expected:
            raise ValueError(f"I7A_CANONICAL_TYPE_DRIFT:{name}")
        if set(entry.get("fields", [])) != _EXPECTED_FIELDS[name]:
            raise ValueError(f"I7A_CANONICAL_TYPE_FIELDS_DRIFT:{name}")

    af_g = contract.get("freeze_domains", {}).get("AF-G")
    if not isinstance(af_g, Mapping):
        raise ValueError("I7A_AF_G_AUTHORITY_MISSING")
    if not _REQUIRED_AF_G_INVARIANTS <= set(af_g.get("invariants", [])):
        raise ValueError("I7A_AF_G_INVARIANT_DRIFT")

    if not isinstance(conformance, Mapping):
        raise ValueError("I7A_WORLD_ECHO_CONFORMANCE_INVALID")
    if (
        conformance.get("status")
        != "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    ):
        raise ValueError("I7A_CONFORMANCE_AUTHORITY_ESCALATION")
    boundary = conformance.get("authority_boundary")
    if (
        not isinstance(boundary, Mapping)
        or boundary.get("does_not_register_new_canonical_types") is not True
    ):
        raise ValueError("I7A_CONFORMANCE_NONAUTHORITY_BOUNDARY_DRIFT")
    return _EXPECTED_PARENT


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


def _indexed_events(world: WorldState) -> tuple[tuple[Event, ...], dict[str, Event]]:
    events = tuple(world.event_log)
    by_id: dict[str, Event] = {}
    for event in events:
        event_id = _require_string(event.event_id, "I7A_EVENT_ID_REQUIRED")
        if event_id in by_id:
            raise ValueError(f"I7A_DUPLICATE_EVENT_ID:{event_id}")
        if event.baseline_version != world.baseline_version:
            raise ValueError(f"I7A_EVENT_BASELINE_DRIFT:{event_id}")
        by_id[event_id] = event
    if set(by_id) != set(world.committed_event_ids):
        raise ValueError("I7A_CANONICAL_EVENT_INDEX_MISMATCH")
    if world.state_version != len(events):
        raise ValueError("I7A_STATE_VERSION_EVENT_COUNT_MISMATCH")
    return events, by_id


@dataclass(frozen=True)
class ReferencePrivateEchoFilter:
    fixture_id: str
    already_seen_novelty_keys: tuple[str, ...] = ()
    urgent_context: bool = False
    private_commentary_enabled: bool = True
    authority_class: str = _REFERENCE_FILTER_AUTHORITY


@dataclass(frozen=True)
class PlayerPrivateWorldEchoReference:
    status: str
    player_actor_id: str
    target_object_id: str
    source_event_id: str
    source_action_id: str
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    world_state_version: str
    source_event_sha256: str
    canonical_fact_refs: tuple[str, ...]
    attribution_kind: str
    novelty_key: str
    world_echo_opportunity: Mapping[str, Any]
    response_concept: Mapping[str, Any]
    realization: Mapping[str, Any]
    authority_class: str


def _filter_material(fixture: ReferencePrivateEchoFilter) -> dict[str, Any]:
    return {
        "fixture_id": fixture.fixture_id,
        "already_seen_novelty_keys": list(fixture.already_seen_novelty_keys),
        "urgent_context": fixture.urgent_context,
        "private_commentary_enabled": fixture.private_commentary_enabled,
        "authority_class": fixture.authority_class,
    }


def _reference_material(reference: PlayerPrivateWorldEchoReference) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "status": reference.status,
                "player_actor_id": reference.player_actor_id,
                "target_object_id": reference.target_object_id,
                "source_event_id": reference.source_event_id,
                "source_action_id": reference.source_action_id,
                "source_world_id": reference.source_world_id,
                "source_baseline_version": reference.source_baseline_version,
                "source_state_version": reference.source_state_version,
                "world_state_version": reference.world_state_version,
                "source_event_sha256": reference.source_event_sha256,
                "canonical_fact_refs": list(reference.canonical_fact_refs),
                "attribution_kind": reference.attribution_kind,
                "novelty_key": reference.novelty_key,
                "world_echo_opportunity": thaw_value(reference.world_echo_opportunity),
                "response_concept": thaw_value(reference.response_concept),
                "realization": thaw_value(reference.realization),
                "authority_class": reference.authority_class,
            }
        )
    )


def _normalize_filter(fixture: ReferencePrivateEchoFilter) -> tuple[str, ...]:
    if not isinstance(fixture, ReferencePrivateEchoFilter):
        raise TypeError("I7A_REFERENCE_PRIVATE_ECHO_FILTER_REQUIRED")
    if fixture.authority_class != _REFERENCE_FILTER_AUTHORITY:
        raise ValueError("I7A_REFERENCE_FILTER_AUTHORITY_ESCALATION")
    _require_string(fixture.fixture_id, "I7A_REFERENCE_FILTER_ID_REQUIRED")
    keys = tuple(
        _require_string(value, "I7A_NOVELTY_KEY_INVALID")
        for value in _require_sequence(
            fixture.already_seen_novelty_keys,
            "I7A_NOVELTY_KEYS_SEQUENCE_REQUIRED",
        )
    )
    if len(keys) != len(set(keys)):
        raise ValueError("I7A_DUPLICATE_NOVELTY_KEY")
    if not isinstance(fixture.urgent_context, bool):
        raise TypeError("I7A_URGENT_CONTEXT_BOOL_REQUIRED")
    if not isinstance(fixture.private_commentary_enabled, bool):
        raise TypeError("I7A_PRIVATE_COMMENTARY_ENABLED_BOOL_REQUIRED")
    return tuple(sorted(keys))


def _build_from_replay_validated_world(
    *,
    world: WorldState,
    player_actor_id: str,
    target_object_id: str,
    source_event_id: str,
    fixture: ReferencePrivateEchoFilter,
) -> PlayerPrivateWorldEchoReference:
    _load_authority()
    seen_keys = _normalize_filter(fixture)

    player_actor_id = _require_string(player_actor_id, "I7A_PLAYER_ACTOR_ID_REQUIRED")
    target_object_id = _require_string(target_object_id, "I7A_TARGET_OBJECT_ID_REQUIRED")
    source_event_id = _require_string(source_event_id, "I7A_SOURCE_EVENT_ID_REQUIRED")

    if player_actor_id != world.primary_player_actor_id:
        raise ValueError("I7A_PLAYER_ACTOR_NOT_CANONICAL_PRIMARY_PLAYER")
    player = world.actors.get(player_actor_id)
    if player is None:
        raise ValueError("I7A_PRIMARY_PLAYER_ACTOR_NOT_FOUND")
    target = world.objects.get(target_object_id)
    if target is None:
        raise ValueError("I7A_TARGET_OBJECT_NOT_FOUND")

    events, by_id = _indexed_events(world)
    source = by_id.get(source_event_id)
    if source is None:
        raise ValueError("I7A_SOURCE_EVENT_NOT_CANONICAL_COMMITTED")
    if source.event_type != "OBJECT_DAMAGED":
        raise ValueError("I7A_SOURCE_EVENT_TYPE_NOT_OBJECT_DAMAGED")
    if source.actor_id != player_actor_id:
        raise ValueError("I7A_SELF_ATTRIBUTION_ACTOR_MISMATCH")
    source_action_id = _require_string(
        source.caused_by_action_id,
        "I7A_SOURCE_EVENT_REQUIRES_PLAYER_ACTION_PROVENANCE",
    )
    if source.payload.get("object_id") != target_object_id:
        raise ValueError("I7A_SOURCE_EVENT_OBJECT_BINDING_MISMATCH")
    damage_state = source.payload.get("damage_state")
    if damage_state not in {"DAMAGED", "BROKEN"}:
        raise ValueError("I7A_SOURCE_DAMAGE_STATE_INVALID")
    if target.damage_state != damage_state:
        raise ValueError("I7A_CURRENT_OBJECT_STATE_NO_LONGER_MATCHES_SOURCE_DAMAGE")
    if target.scene_id != source.scene_id:
        raise ValueError("I7A_TARGET_SCENE_DRIFT")
    if player.scene_id != target.scene_id or world.active_scene_id != target.scene_id:
        raise ValueError("I7A_PLAYER_NOT_CURRENTLY_ENCOUNTERING_TARGET")

    scene = world.scenes.get(target.scene_id)
    if scene is None:
        raise ValueError("I7A_TARGET_SCENE_NOT_FOUND")
    if source_event_id not in scene.relevant_event_refs:
        raise ValueError("I7A_SOURCE_EVENT_NOT_BOUND_TO_SCENE_HISTORY")
    persistent_delta = f"{target_object_id}:damage_state={damage_state}"
    if persistent_delta not in scene.persistent_delta_refs:
        raise ValueError("I7A_PERSISTENT_DAMAGE_DELTA_MISSING")

    source_event_sha256 = _sha256(_event_record(source))
    canonical_fact_refs = (
        source_event_id,
        persistent_delta,
        f"SELF_CAUSED:{source_event_id}:{player_actor_id}",
    )
    identity = {
        "world_id": world.world_id,
        "baseline_version": world.baseline_version,
        "source_event_id": source_event_id,
        "source_event_sha256": source_event_sha256,
        "player_actor_id": player_actor_id,
        "target_object_id": target_object_id,
        "damage_state": damage_state,
    }
    identity_sha = _sha256(identity)
    echo_id = f"I7A:ECHO:{identity_sha[:24]}"
    response_concept_id = f"I7A:RC:{identity_sha[:24]}"
    novelty_key = f"I7A:SELF_DAMAGE:{identity_sha[:24]}"
    attribution_ref = f"I7A:ATTR:SELF:{identity_sha[:24]}"

    opportunity = {
        "echo_id": echo_id,
        "source_event_or_delta_refs": [source_event_id, persistent_delta],
        "speaker_candidate_refs": [player_actor_id],
        "knowledge_attribution_refs": [attribution_ref],
        "response_concept_refs": [response_concept_id],
        "novelty_key": novelty_key,
        "expiry_policy": {
            "policy": "REFERENCE_VALID_WHILE_EXACT_PERSISTENT_DAMAGE_STATE_MATCHES"
        },
    }
    response_concept = {
        "response_concept_id": response_concept_id,
        "speech_risk_class": "R1_LOW_RISK_OBSERVATION",
        "required_fact_refs": list(canonical_fact_refs),
        "forbidden_claim_classes": [
            "DIEGETIC_CONFESSION",
            "DIEGETIC_THREAT",
            "PLAYER_COMMITMENT",
            "NPC_KNOWLEDGE_INJECTION",
            "INVENTED_CULPRIT_OR_DAMAGE_FACT",
        ],
        "realization_constraints": [
            "PRIVATE_INNER_COMMENTARY_ONLY",
            "NO_DIEGETIC_SPEECH",
            "NO_WORLD_EVENT",
            "NO_NPC_HEARING",
            "NO_SOCIAL_OR_LEGAL_CONSEQUENCE",
            "NO_PLAYER_INTENT_CREATION",
            "NO_LLM_FACT_AUTHORITY",
        ],
    }

    suppression_reason = None
    if not fixture.private_commentary_enabled:
        suppression_reason = "REFERENCE_PRIVATE_COMMENTARY_DISABLED"
    elif fixture.urgent_context:
        suppression_reason = "URGENT_CONTEXT_SUPPRESSES_LOW_RISK_CALLBACK"
    elif novelty_key in seen_keys:
        suppression_reason = "NOVELTY_ALREADY_SEEN"

    status = "SILENCE" if suppression_reason is not None else "PRIVATE_WORLD_ECHO_READY"
    realization = {
        "mode": "SILENCE" if suppression_reason is not None else "PRIVATE_INNER_COMMENTARY",
        "suppression_reason": suppression_reason,
        "audible": False,
        "diegetic_speech": False,
        "world_event_created": False,
        "npc_knowledge_mutation_count": 0,
        "player_intent_created": False,
        "social_consequence_created": False,
        "claim_fact_refs": list(canonical_fact_refs) if suppression_reason is None else [],
        "surface_realization": "UNREALIZED_TYPED_CONCEPT_ONLY",
        "policy_authority": "NONE_REFERENCE_FILTER_ONLY",
    }

    return PlayerPrivateWorldEchoReference(
        status=status,
        player_actor_id=player_actor_id,
        target_object_id=target_object_id,
        source_event_id=source_event_id,
        source_action_id=source_action_id,
        source_world_id=world.world_id,
        source_baseline_version=world.baseline_version,
        source_state_version=world.state_version,
        world_state_version=world.world_state_version,
        source_event_sha256=source_event_sha256,
        canonical_fact_refs=canonical_fact_refs,
        attribution_kind="SELF_KNOWN_CAUSE_FROM_CANONICAL_PLAYER_ACTION_EVENT",
        novelty_key=novelty_key,
        world_echo_opportunity=freeze_value(opportunity),
        response_concept=freeze_value(response_concept),
        realization=freeze_value(realization),
        authority_class=_REFERENCE_AUTHORITY_CLASS,
    )


def build_player_private_world_echo_reference(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    target_object_id: str,
    source_event_id: str,
    fixture: ReferencePrivateEchoFilter,
    caller_echo_evidence: Mapping[str, Any] | None = None,
) -> PlayerPrivateWorldEchoReference:
    """Validate canonical history through I1, then derive private World Echo evidence."""
    if caller_echo_evidence is not None:
        raise ValueError("I7A_CALLER_AUTHORED_ECHO_EVIDENCE_FORBIDDEN")
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I7A_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I7A_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    export_solo_replay_package(baseline, world)
    return _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        target_object_id=target_object_id,
        source_event_id=source_event_id,
        fixture=fixture,
    )


def export_player_private_world_echo_package(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    player_actor_id: str,
    target_object_id: str,
    source_event_id: str,
    fixture: ReferencePrivateEchoFilter,
) -> bytes:
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I7A_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I7A_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    solo_package = export_solo_replay_package(baseline, world)
    reference = _build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        target_object_id=target_object_id,
        source_event_id=source_event_id,
        fixture=fixture,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "player_actor_id": reference.player_actor_id,
        "target_object_id": reference.target_object_id,
        "source_event_id": reference.source_event_id,
        "fixture": _filter_material(fixture),
        "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(),
        "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"),
        "expected_reference": _reference_material(reference),
    }
    envelope = {"payload": payload, "sha256": _sha256(payload)}
    return _canonical_json(envelope).encode("utf-8")


def replay_player_private_world_echo_package(
    package: bytes | bytearray | memoryview,
) -> PlayerPrivateWorldEchoReference:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I7A_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I7A_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I7A_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I7A_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I7A_REPLAY_PACKAGE_TAMPERED")

    encoded = _require_string(
        payload.get("source_i1_replay_b64"),
        "I7A_I1_REPLAY_PAYLOAD_REQUIRED",
    )
    try:
        solo_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I7A_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get("source_i1_replay_sha256"):
        raise ValueError("I7A_I1_REPLAY_DIGEST_MISMATCH")

    fixture_raw = payload.get("fixture")
    expected_fixture_fields = {
        "fixture_id",
        "already_seen_novelty_keys",
        "urgent_context",
        "private_commentary_enabled",
        "authority_class",
    }
    if not isinstance(fixture_raw, Mapping) or set(fixture_raw) != expected_fixture_fields:
        raise ValueError("I7A_REFERENCE_FILTER_SCHEMA_INVALID")
    fixture = ReferencePrivateEchoFilter(
        fixture_id=fixture_raw["fixture_id"],
        already_seen_novelty_keys=tuple(fixture_raw["already_seen_novelty_keys"]),
        urgent_context=fixture_raw["urgent_context"],
        private_commentary_enabled=fixture_raw["private_commentary_enabled"],
        authority_class=fixture_raw["authority_class"],
    )

    evidence = import_solo_replay_package(solo_package)
    rebuilt_world = rehydrate_solo_replay_package(solo_package)
    rebuilt = _build_from_replay_validated_world(
        world=rebuilt_world,
        player_actor_id=payload.get("player_actor_id"),
        target_object_id=payload.get("target_object_id"),
        source_event_id=payload.get("source_event_id"),
        fixture=fixture,
    )
    if (
        rebuilt.source_world_id != evidence.world_id
        or rebuilt.source_baseline_version != evidence.baseline_version
    ):
        raise ValueError("I7A_REPLAY_I1_SOURCE_BINDING_MISMATCH")
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I7A_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH")
    return rebuilt
