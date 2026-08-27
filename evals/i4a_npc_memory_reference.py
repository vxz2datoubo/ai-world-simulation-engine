"""Bounded I4A NPC cognition projection and restart reference.

The source of truth is the already-accepted canonical SOLO event history. This
module derives AF-E-shaped perception, episodic-memory, belief, sparse
relationship, and context projections from that history. It does not create a
memory store, new knowledge-acquisition authority, database, LLM authority, or
new gameplay runtime semantics.
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
    rehydrate_solo_replay_package,
)
from awrse.model import Event, freeze_value, thaw_value

I4_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_MEMORY_BACKEND_SELECTED = True
NO_LLM_MEMORY_AUTHORITY = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.9.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
)
_EXPECTED_TYPES = {
    "NPCPerceptionEvent": ("AF001.NPCPerceptionEvent", "1.0.0-candidate", "KNOWLEDGE_DERIVED_PROJECTION"),
    "NPCEpisodicMemory": ("AF001.NPCEpisodicMemory", "1.0.0-candidate", "KNOWLEDGE_DERIVED_PROJECTION"),
    "BeliefState": ("AF001.BeliefState", "1.0.0-candidate", "KNOWLEDGE_DERIVED_PROJECTION"),
    "NPCPlayerRelationshipState": ("AF001.NPCPlayerRelationshipState", "1.0.0-candidate", "KNOWLEDGE_DERIVED_PROJECTION"),
    "NPCContextBundle": ("AF001.NPCContextBundle", "1.0.0-candidate", "KNOWLEDGE_DERIVED_PROJECTION"),
}
_REQUIRED_AF_E_INVARIANTS = {
    "PLAYER_KNOWLEDGE_NE_NPC_KNOWLEDGE",
    "RECIPIENT_PROJECTION_CANNOT_CREATE_ACQUISITION_EVIDENCE",
    "SUMMARY_REFLECTION_IS_DERIVED_CACHE",
}
_IMPLEMENTED_REFERENCE_MODES = {"SAW", "HEARD", "WAS_TOLD"}
_MODE_CONFIDENCE = {"SAW": 1.0, "HEARD": 0.55, "WAS_TOLD": 0.45}
_MODE_SALIENCE = {"SAW": 0.9, "HEARD": 0.55, "WAS_TOLD": 0.5}
_CLAIM_RE = re.compile(r"(?:^|\s)CLAIM_EVENT_ACTOR:([A-Za-z0-9_.:-]+):([A-Za-z0-9_.:-]+)(?:\s|$)")
_RELEVANT_HIDDEN_EVENT_TYPES = {"OBJECT_DAMAGED", "ACTOR_STRUCK", "SPEECH_UTTERED"}
_PACKAGE_SCHEMA = "AWRSE-I4A-NPC-COGNITION-REPLAY-1"


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
        raise ValueError("I4A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256_text(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I4A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I4A_JSON_NONFINITE:{value}")


def _load_authority() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I4A_CANONICAL_CONTRACT_UNAVAILABLE") from None
    if not isinstance(contract, Mapping):
        raise ValueError("I4A_CANONICAL_CONTRACT_INVALID")
    actual_parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if actual_parent != _EXPECTED_PARENT:
        raise ValueError("I4A_CANONICAL_PARENT_DRIFT")
    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I4A_TYPE_REGISTRY_MISSING")
    for name, expected in _EXPECTED_TYPES.items():
        entry = registry.get(name)
        if not isinstance(entry, Mapping):
            raise ValueError(f"I4A_CANONICAL_TYPE_MISSING:{name}")
        actual = (entry.get("type_id"), entry.get("version"), entry.get("authority_profile_ref"))
        if actual != expected:
            raise ValueError(f"I4A_CANONICAL_TYPE_DRIFT:{name}")
    af_e = contract.get("freeze_domains", {}).get("AF-E")
    if not isinstance(af_e, Mapping):
        raise ValueError("I4A_AF_E_AUTHORITY_MISSING")
    if not _REQUIRED_AF_E_INVARIANTS <= set(af_e.get("invariants", [])):
        raise ValueError("I4A_AF_E_INVARIANT_DRIFT")
    if not _IMPLEMENTED_REFERENCE_MODES <= set(af_e.get("knowledge_modes", [])):
        raise ValueError("I4A_AF_E_KNOWLEDGE_MODE_DRIFT")
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


def _indexed_events(world: WorldState) -> tuple[tuple[Event, ...], dict[str, Event], dict[str, int]]:
    events = tuple(world.event_log)
    by_id: dict[str, Event] = {}
    index_by_id: dict[str, int] = {}
    for index, event in enumerate(events, start=1):
        event_id = _require_string(event.event_id, "I4A_EVENT_ID_REQUIRED")
        if event_id in by_id:
            raise ValueError(f"I4A_DUPLICATE_EVENT_ID:{event_id}")
        if event.baseline_version != world.baseline_version:
            raise ValueError(f"I4A_EVENT_BASELINE_DRIFT:{event_id}")
        by_id[event_id] = event
        index_by_id[event_id] = index
    if set(by_id) != set(world.committed_event_ids):
        raise ValueError("I4A_CANONICAL_EVENT_INDEX_MISMATCH")
    if world.state_version != len(events):
        raise ValueError("I4A_STATE_VERSION_EVENT_COUNT_MISMATCH")
    return events, by_id, index_by_id


def _claim_from_speech(event: Event) -> tuple[str, str] | None:
    if event.event_type != "SPEECH_UTTERED":
        return None
    payload = event.payload
    if payload.get("trust_class") != "UNTRUSTED_DATA" or payload.get("authority") != "NONE_OVER_TARGET_INTERNAL_STATE":
        raise ValueError("I4A_SPEECH_TRUST_BOUNDARY_DRIFT")
    literal = payload.get("literal_content")
    if not isinstance(literal, str):
        return None
    match = _CLAIM_RE.search(literal)
    if match is None:
        return None
    return match.group(1), match.group(2)


def _reference_material(reference: "NPCMemoryReference") -> dict[str, Any]:
    return json.loads(_canonical_json({
        "npc_id": reference.npc_id,
        "player_ids": list(reference.player_ids),
        "contract_id": reference.contract_id,
        "contract_version": reference.contract_version,
        "authority_graph_version": reference.authority_graph_version,
        "source_world_id": reference.source_world_id,
        "source_baseline_version": reference.source_baseline_version,
        "source_state_version": reference.source_state_version,
        "source_event_sha256": reference.source_event_sha256,
        "perception_events": [thaw_value(item) for item in reference.perception_events],
        "episodic_memories": [thaw_value(item) for item in reference.episodic_memories],
        "belief_states": [thaw_value(item) for item in reference.belief_states],
        "relationship_states": [thaw_value(item) for item in reference.relationship_states],
        "context_bundle": thaw_value(reference.context_bundle),
    }))


@dataclass(frozen=True)
class NPCMemoryReference:
    npc_id: str
    player_ids: tuple[str, ...]
    contract_id: str
    contract_version: str
    authority_graph_version: str
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    source_event_sha256: str
    perception_events: tuple[Mapping[str, Any], ...]
    episodic_memories: tuple[Mapping[str, Any], ...]
    belief_states: tuple[Mapping[str, Any], ...]
    relationship_states: tuple[Mapping[str, Any], ...]
    context_bundle: Mapping[str, Any]


def build_npc_memory_reference(
    *,
    world: WorldState,
    npc_id: str,
    player_ids: Sequence[str],
    caller_memory_evidence: Mapping[str, Any] | None = None,
) -> NPCMemoryReference:
    """Derive one NPC's AF-E reference projection from accepted event evidence only."""
    if caller_memory_evidence is not None:
        raise ValueError("I4A_CALLER_AUTHORED_MEMORY_EVIDENCE_FORBIDDEN")
    if not isinstance(world, WorldState):
        raise TypeError("I4A_WORLD_STATE_REQUIRED")
    contract_id, contract_version, authority_graph = _load_authority()
    npc_id = _require_string(npc_id, "I4A_NPC_ID_REQUIRED")
    if npc_id not in world.npc_minds or npc_id not in world.actors:
        raise ValueError("I4A_NPC_NOT_FOUND")

    raw_players = _require_sequence(player_ids, "I4A_PLAYER_IDS_REQUIRED")
    players = tuple(_require_string(value, "I4A_PLAYER_ID_INVALID") for value in raw_players)
    if not players or len(players) != len(set(players)):
        raise ValueError("I4A_PLAYER_IDS_INVALID_OR_DUPLICATE")
    if npc_id in players or any(player_id not in world.actors for player_id in players):
        raise ValueError("I4A_PLAYER_ID_NOT_CANONICAL_ACTOR")

    events, by_id, index_by_id = _indexed_events(world)
    mind = world.npc_minds[npc_id]
    acquisition_ids = tuple(mind.memories)
    if len(acquisition_ids) != len(set(acquisition_ids)):
        raise ValueError("I4A_DUPLICATE_NPC_MEMORY_EVENT_REF")

    acquired_source_ids: list[str] = []
    perception_rows: list[dict[str, Any]] = []
    memory_rows: list[dict[str, Any]] = []
    memory_id_by_acquisition: dict[str, str] = {}
    memory_id_by_source: dict[str, list[str]] = {}

    for acquisition_id in acquisition_ids:
        acquisition = by_id.get(acquisition_id)
        if acquisition is None:
            raise ValueError(f"I4A_MEMORY_ACQUISITION_EVENT_UNKNOWN:{acquisition_id}")
        if acquisition.event_type != "NPC_KNOWLEDGE_ACQUIRED":
            raise ValueError(f"I4A_MEMORY_EVENT_TYPE_INVALID:{acquisition_id}")
        if acquisition.payload.get("npc_id") != npc_id:
            raise ValueError(f"I4A_CROSS_NPC_MEMORY_LEAK:{acquisition_id}")
        mode = acquisition.payload.get("mode")
        if mode not in _IMPLEMENTED_REFERENCE_MODES:
            raise ValueError(f"I4A_UNIMPLEMENTED_KNOWLEDGE_MODE:{mode}")
        source_id = _require_string(
            acquisition.payload.get("source_event_id"),
            f"I4A_MEMORY_SOURCE_EVENT_REQUIRED:{acquisition_id}",
        )
        source = by_id.get(source_id)
        if source is None:
            raise ValueError(f"I4A_MEMORY_SOURCE_EVENT_UNKNOWN:{source_id}")
        if index_by_id[source_id] >= index_by_id[acquisition_id]:
            raise ValueError(f"I4A_MEMORY_SOURCE_ORDER_INVALID:{acquisition_id}")
        if source_id not in mind.knowledge_boundary_refs:
            raise ValueError(f"I4A_MEMORY_SOURCE_NOT_IN_KNOWLEDGE_BOUNDARY:{source_id}")

        perception_id = f"PERCEPTION:{acquisition_id}"
        memory_id = f"MEMORY:{acquisition_id}"
        memory_id_by_acquisition[acquisition_id] = memory_id
        memory_id_by_source.setdefault(source_id, []).append(memory_id)
        acquired_source_ids.append(source_id)
        cursor = f"{world.baseline_version}:{index_by_id[acquisition_id]}"
        perception_rows.append({
            "perception_id": perception_id,
            "npc_id": npc_id,
            "mode": mode,
            "source_event_ref": source_id,
            "source_actor_ref_optional": source.actor_id,
            "scene_id": acquisition.scene_id,
            "acquisition_provenance": f"CANONICAL_{mode}_KNOWLEDGE_ACQUISITION_EVENT",
            "ordering_cursor": cursor,
        })
        memory_rows.append({
            "memory_id": memory_id,
            "npc_id": npc_id,
            "source_perception_refs": [perception_id],
            "source_world_event_refs": [source_id],
            "provenance_kind": mode,
            "confidence": _MODE_CONFIDENCE[mode],
            "salience": _MODE_SALIENCE[mode],
            "world_time": None,
            "ordering_cursor": cursor,
            "supersession_refs": [],
            "reference_weight_policy": "I4A_DETERMINISTIC_REFERENCE_ONLY_NOT_PRODUCTION_COGNITION_TUNING",
        })

    if len(mind.knowledge_boundary_refs) != len(set(mind.knowledge_boundary_refs)):
        raise ValueError("I4A_DUPLICATE_KNOWLEDGE_BOUNDARY_REF")
    if set(mind.knowledge_boundary_refs) != set(acquired_source_ids):
        raise ValueError("I4A_KNOWLEDGE_BOUNDARY_NOT_REBUILT_FROM_ACQUISITION_EVENTS")

    # Build deterministic, provenance-preserving belief projections. A strict
    # CLAIM_EVENT_ACTOR marker is parsed only as an untrusted claim about the
    # actor_id of a specific canonical event. It can never create/change that
    # event. Direct SAW evidence for that exact source event outranks the claim.
    direct_event_actor_evidence: dict[str, tuple[str, str]] = {}
    for acquisition_id in acquisition_ids:
        acquisition = by_id[acquisition_id]
        if acquisition.payload.get("mode") != "SAW":
            continue
        source_id = str(acquisition.payload["source_event_id"])
        source = by_id[source_id]
        if source.actor_id is not None:
            direct_event_actor_evidence[source_id] = (
                source.actor_id,
                memory_id_by_acquisition[acquisition_id],
            )

    belief_rows: list[dict[str, Any]] = []
    seen_belief_ids: set[str] = set()
    for acquisition_id in acquisition_ids:
        acquisition = by_id[acquisition_id]
        mode = str(acquisition.payload["mode"])
        source_id = str(acquisition.payload["source_event_id"])
        source = by_id[source_id]
        memory_id = memory_id_by_acquisition[acquisition_id]

        if mode == "SAW" and source.actor_id is not None:
            belief_id = f"BELIEF:WITNESSED_EVENT_ACTOR:{source_id}:{source.actor_id}"
            if belief_id not in seen_belief_ids:
                belief_rows.append({
                    "belief_id": belief_id,
                    "npc_id": npc_id,
                    "proposition_ref": f"WITNESSED_EVENT_ACTOR:{source_id}:{source.actor_id}",
                    "confidence": 1.0,
                    "supporting_refs": [memory_id],
                    "contradicting_refs": [],
                    "status": "BELIEVED",
                    "last_revision_cursor": f"{world.baseline_version}:{index_by_id[acquisition_id]}",
                })
                seen_belief_ids.add(belief_id)

        if mode != "HEARD":
            continue
        claim = _claim_from_speech(source)
        if claim is None:
            continue
        claimed_event_id, claimed_actor_id = claim
        belief_id = f"BELIEF:HEARD_EVENT_ACTOR_CLAIM:{claimed_event_id}:{claimed_actor_id}"
        if belief_id in seen_belief_ids:
            continue
        direct = direct_event_actor_evidence.get(claimed_event_id)
        if direct is None:
            status = "DOUBTED"
            confidence = 0.35
            contradicting: list[str] = []
        elif direct[0] == claimed_actor_id:
            status = "BELIEVED"
            confidence = 0.9
            contradicting = []
        else:
            status = "DISBELIEVED"
            confidence = 0.1
            contradicting = [direct[1]]
        supporting = [memory_id]
        if direct is not None and direct[0] == claimed_actor_id:
            supporting.append(direct[1])
        belief_rows.append({
            "belief_id": belief_id,
            "npc_id": npc_id,
            "proposition_ref": f"HEARD_EVENT_ACTOR_CLAIM:{claimed_event_id}:{claimed_actor_id}",
            "confidence": confidence,
            "supporting_refs": supporting,
            "contradicting_refs": contradicting,
            "status": status,
            "last_revision_cursor": f"{world.baseline_version}:{index_by_id[acquisition_id]}",
        })
        seen_belief_ids.add(belief_id)

    relationship_events: dict[str, list[Event]] = {player_id: [] for player_id in players}
    for event in events:
        if event.event_type != "RELATIONSHIP_CHANGED" or event.payload.get("npc_id") != npc_id:
            continue
        actor_id = event.actor_id
        if actor_id in relationship_events:
            relationship_events[actor_id].append(event)

    relationship_rows: list[dict[str, Any]] = []
    relationship_refs: list[str] = []
    for player_id in players:
        pair_events = relationship_events[player_id]
        if not pair_events:
            continue
        delta = sum(int(event.payload["delta"]) for event in pair_events)
        ref = f"REL:{npc_id}:{player_id}"
        relationship_refs.append(ref)
        relationship_rows.append({
            "relationship_ref": ref,
            "npc_id": npc_id,
            "player_id": player_id,
            "dimension_map": {"legacy_relationship_delta": delta},
            "source_refs": [event.event_id for event in pair_events],
            "last_revision_cursor": f"{world.baseline_version}:{index_by_id[pair_events[-1].event_id]}",
            "projection_policy": "SPARSE_EVENT_DERIVED_REFERENCE_ONLY_RELATIONSHIP_MATH_REMAINS_OPEN_DECISION",
        })

    acquired_source_set = set(acquired_source_ids)
    forbidden_hidden = [
        event.event_id
        for event in events
        if event.event_type in _RELEVANT_HIDDEN_EVENT_TYPES
        and event.event_id not in acquired_source_set
        and event.actor_id != npc_id
    ]
    # A speech/object fact explicitly acquired by this NPC is never hidden here;
    # canonical events with no acquisition path stay blocked from context.
    context = {
        "npc_id": npc_id,
        "world_cursor": world.world_state_version,
        "current_perception_refs": [],
        "relationship_refs": relationship_refs,
        "episodic_memory_refs": [row["memory_id"] for row in memory_rows],
        "belief_refs": [row["belief_id"] for row in belief_rows],
        "forbidden_hidden_fact_refs": forbidden_hidden,
        "bundle_version": "1.0.0-candidate",
        "source_authority": "CANONICAL_EVENT_HISTORY_AND_MODE_SPECIFIC_ACQUISITION_EVIDENCE",
    }

    source_records = [_event_record(event) for event in events]
    return NPCMemoryReference(
        npc_id=npc_id,
        player_ids=players,
        contract_id=contract_id,
        contract_version=contract_version,
        authority_graph_version=authority_graph,
        source_world_id=world.world_id,
        source_baseline_version=world.baseline_version,
        source_state_version=world.state_version,
        source_event_sha256=_sha256_text(source_records),
        perception_events=tuple(freeze_value(row) for row in perception_rows),
        episodic_memories=tuple(freeze_value(row) for row in memory_rows),
        belief_states=tuple(freeze_value(row) for row in belief_rows),
        relationship_states=tuple(freeze_value(row) for row in relationship_rows),
        context_bundle=freeze_value(context),
    )


def export_npc_memory_replay_package(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    npc_id: str,
    player_ids: Sequence[str],
) -> bytes:
    """Wrap existing I1 SOLO replay evidence plus a rebuildable derived cache."""
    reference = build_npc_memory_reference(
        world=world,
        npc_id=npc_id,
        player_ids=player_ids,
    )
    solo_package = export_solo_replay_package(baseline, world)
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "npc_id": reference.npc_id,
        "player_ids": list(reference.player_ids),
        "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(),
        "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"),
        "expected_reference": _reference_material(reference),
    }
    envelope = {"payload": payload, "sha256": _sha256_text(payload)}
    return _canonical_json(envelope).encode("utf-8")


def replay_npc_memory_package(package: bytes | bytearray | memoryview) -> NPCMemoryReference:
    """Rehydrate canonical world evidence first, then rebuild the AF-E projection."""
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I4A_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I4A_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I4A_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I4A_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256_text(payload):
        raise ValueError("I4A_REPLAY_PACKAGE_TAMPERED")

    replay_b64 = _require_string(payload.get("source_i1_replay_b64"), "I4A_I1_REPLAY_PAYLOAD_REQUIRED")
    try:
        solo_package = base64.b64decode(replay_b64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I4A_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get("source_i1_replay_sha256"):
        raise ValueError("I4A_I1_REPLAY_DIGEST_MISMATCH")

    rebuilt_world = rehydrate_solo_replay_package(solo_package)
    rebuilt = build_npc_memory_reference(
        world=rebuilt_world,
        npc_id=payload.get("npc_id"),
        player_ids=payload.get("player_ids"),
    )
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I4A_REPLAY_PROJECTION_MATERIALIZATION_MISMATCH")
    return rebuilt
