"""Bounded I5A information propagation and Narrative Opportunity shadow reference.

The output of this module is non-canonical shadow evidence only. It cannot
commit world events, create player/NPC knowledge, move actors, alter capability,
or authorize a production encounter.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse import WorldBaseline, WorldState, export_solo_replay_package, rehydrate_solo_replay_package
from awrse.model import Event, freeze_value, thaw_value

I5_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_WORLD_MUTATION = True
NO_PRODUCTION_ENCOUNTER_DENSITY_POLICY = True
NO_PX_SCORING = True
NO_LLM_OR_PROVIDER = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_GOLDEN_PATH = _ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"

_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.9.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
)
_EXPECTED_TYPES = {
    "InformationPacket": (
        "AF001.InformationPacket",
        "1.0.0-candidate",
        "INFORMATION_PROVENANCE_LIFECYCLE",
        {
            "info_id", "source_fact_or_event_refs", "classification", "source_refs",
            "verification_state", "confidence", "distortion_policy",
            "created_world_time", "propagation_scope", "expiry_policy",
        },
    ),
    "NarrativeOpportunityBroker": (
        "AF001.NarrativeOpportunityBroker",
        "1.0.0-candidate",
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
        {"broker_contract_version", "input_refs", "candidate_policy_ref", "plausibility_gate_ref"},
    ),
    "PlausibilityGate": (
        "AF001.PlausibilityGate",
        "1.0.0-candidate",
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
        {
            "gate_version", "spatial_checks", "temporal_checks", "identity_history_checks",
            "motivation_checks", "information_provenance_checks", "density_checks",
            "asset_availability_checks", "anti_repeat_checks",
        },
    ),
    "EncounterCandidate": (
        "AF001.EncounterCandidate",
        "1.0.0-candidate",
        "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
        {
            "encounter_id", "source_goal_refs", "world_scope", "time_window",
            "actor_candidate_refs", "motivation_refs", "known_information_refs",
            "affordance_refs", "forbidden_inventions", "eligibility_evidence",
            "expiry_policy",
        },
    ),
}
_EXPECTED_GOLDEN_RULES = {
    "capital_event_not_known_without_provenance",
    "candidate_requires_plausibility_before_realization",
    "delivery_channel_precedes_player_knowledge",
    "importance_alone_cannot_create_knowledge",
    "broker_cannot_lower_capability_difficulty",
    "retain_source_fact_and_channel_provenance",
}
_EXPECTED_OPEN_DECISIONS = {
    "OD-ENCOUNTER-DENSITY-001",
    "OD-PX-SCORING-001",
    "OD-PUBLICATION-POLICY-001",
}

_PACKAGE_SCHEMA = "AWRSE-I5A-INFORMATION-OPPORTUNITY-SHADOW-1"
_RESULT_STATUS_CANDIDATE = "SHADOW_ENCOUNTER_CANDIDATE"
_RESULT_STATUS_NONE = "NO_VALID_OPPORTUNITY"
_FIXTURE_AUTHORITY_CLASS = "BOUNDED_REFERENCE_FIXTURE_ONLY_NOT_CANONICAL_WORLD_EVIDENCE"
_FORBIDDEN_INVENTIONS = (
    "NO_WORLD_EVENT_COMMIT",
    "NO_ACTOR_SPAWN_OR_MOVEMENT",
    "NO_PLAYER_OR_NPC_KNOWLEDGE_MUTATION",
    "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE",
    "NO_FORCED_DIALOGUE_OR_SUCCESS",
    "NO_PX_DIRECTOR_RENDERER_ADMISSION_AUTHORITY",
)


@dataclass(frozen=True)
class ShadowPlausibilityFixture:
    fixture_id: str
    target_scene_id: str
    carrier_origin_scene_id: str
    route_available: bool
    travel_steps_required: int
    travel_steps_available: int
    identity_history_consistent: bool
    motivation_ref: str | None
    anti_repeat_allowed: bool
    asset_available: bool
    authority_class: str = _FIXTURE_AUTHORITY_CLASS


@dataclass(frozen=True)
class InformationOpportunityShadowResult:
    status: str
    source_event_id: str
    player_actor_id: str
    carrier_npc_id: str
    source_world_id: str
    source_state_version: int
    source_i1_sha256: str
    carrier_acquisition_sha256: str
    reference_fixture_sha256: str
    information_packet: Mapping[str, Any]
    broker: Mapping[str, Any]
    plausibility_gate: Mapping[str, Any]
    encounter_candidate: Mapping[str, Any] | None
    rejection_reasons: tuple[str, ...]


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
    except (TypeError, ValueError) as exc:
        raise ValueError("I5A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I5A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I5A_JSON_NONFINITE:{value}")


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _load_governed_semantics() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
        golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I5A_CANONICAL_GOVERNANCE_UNAVAILABLE") from None
    if not isinstance(contract, Mapping) or not isinstance(golden, Mapping):
        raise ValueError("I5A_CANONICAL_GOVERNANCE_INVALID")
    parent = (contract.get("contract_id"), contract.get("contract_version"), contract.get("authority_graph_version"))
    if parent != _EXPECTED_PARENT:
        raise ValueError("I5A_CANONICAL_PARENT_DRIFT")
    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I5A_TYPE_REGISTRY_MISSING")
    for name, (type_id, version, authority, fields) in _EXPECTED_TYPES.items():
        entry = registry.get(name)
        if not isinstance(entry, Mapping):
            raise ValueError(f"I5A_CANONICAL_TYPE_MISSING:{name}")
        if (entry.get("type_id"), entry.get("version"), entry.get("authority_profile_ref")) != (type_id, version, authority):
            raise ValueError(f"I5A_CANONICAL_TYPE_DRIFT:{name}")
        if set(entry.get("fields", [])) != fields:
            raise ValueError(f"I5A_CANONICAL_TYPE_FIELDS_DRIFT:{name}")
    scenarios = golden.get("scenarios")
    scenario = scenarios.get("WILDERNESS_NEWS_TRAP") if isinstance(scenarios, Mapping) else None
    if not isinstance(scenario, Mapping):
        raise ValueError("I5A_GOLDEN_WILDERNESS_NEWS_TRAP_MISSING")
    machine = scenario.get("machine_spec")
    if not isinstance(machine, Mapping):
        raise ValueError("I5A_GOLDEN_MACHINE_SPEC_MISSING")
    if machine.get("scenario_id") != "WILDERNESS_NEWS_TRAP":
        raise ValueError("I5A_GOLDEN_SCENARIO_ID_DRIFT")
    if machine.get("implementation_state") != "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED":
        raise ValueError("I5A_GOLDEN_RUNTIME_AUTHORITY_DRIFT")
    if not _EXPECTED_OPEN_DECISIONS <= set(machine.get("open_decision_dependencies", [])):
        raise ValueError("I5A_OPEN_DECISION_BOUNDARY_DRIFT")
    observed_rules: set[str] = set()
    for key in ("initial_state_predicates", "expected_event_state_predicates", "forbidden_predicates", "provenance_authority_assertions"):
        rows = machine.get(key)
        if isinstance(rows, Sequence) and not isinstance(rows, (str, bytes, bytearray)):
            for row in rows:
                if isinstance(row, Mapping):
                    for field in ("assertion", "must", "must_not"):
                        value = row.get(field)
                        if isinstance(value, str):
                            observed_rules.add(value)
    if not _EXPECTED_GOLDEN_RULES <= observed_rules:
        raise ValueError("I5A_GOLDEN_RULE_DRIFT")
    return _EXPECTED_PARENT


def _event_index(world: WorldState) -> dict[str, Event]:
    events: dict[str, Event] = {}
    for event in world.event_log:
        if event.event_id in events:
            raise ValueError(f"I5A_DUPLICATE_EVENT_ID:{event.event_id}")
        events[event.event_id] = event
    if set(events) != set(world.committed_event_ids):
        raise ValueError("I5A_CANONICAL_EVENT_INDEX_MISMATCH")
    if world.state_version != len(world.event_log):
        raise ValueError("I5A_STATE_VERSION_EVENT_COUNT_MISMATCH")
    return events


def _event_material(event: Event) -> dict[str, Any]:
    return {"event_id": event.event_id, "event_type": event.event_type, "actor_id": event.actor_id, "scene_id": event.scene_id, "baseline_version": event.baseline_version, "payload": thaw_value(event.payload), "caused_by_action_id": event.caused_by_action_id}


def _fixture_material(fixture: ShadowPlausibilityFixture) -> dict[str, Any]:
    return {"fixture_id": fixture.fixture_id, "target_scene_id": fixture.target_scene_id, "carrier_origin_scene_id": fixture.carrier_origin_scene_id, "route_available": fixture.route_available, "travel_steps_required": fixture.travel_steps_required, "travel_steps_available": fixture.travel_steps_available, "identity_history_consistent": fixture.identity_history_consistent, "motivation_ref": fixture.motivation_ref, "anti_repeat_allowed": fixture.anti_repeat_allowed, "asset_available": fixture.asset_available, "authority_class": fixture.authority_class}


def _result_material(result: InformationOpportunityShadowResult) -> dict[str, Any]:
    return json.loads(_canonical_json({"status": result.status, "source_event_id": result.source_event_id, "player_actor_id": result.player_actor_id, "carrier_npc_id": result.carrier_npc_id, "source_world_id": result.source_world_id, "source_state_version": result.source_state_version, "source_i1_sha256": result.source_i1_sha256, "carrier_acquisition_sha256": result.carrier_acquisition_sha256, "reference_fixture_sha256": result.reference_fixture_sha256, "information_packet": thaw_value(result.information_packet), "broker": thaw_value(result.broker), "plausibility_gate": thaw_value(result.plausibility_gate), "encounter_candidate": None if result.encounter_candidate is None else thaw_value(result.encounter_candidate), "rejection_reasons": list(result.rejection_reasons)}))


def _find_carrier_acquisition(world: WorldState, *, carrier_npc_id: str, source_event_id: str) -> Event:
    matches = [event for event in world.event_log if event.event_type == "NPC_KNOWLEDGE_ACQUIRED" and event.payload.get("npc_id") == carrier_npc_id and event.payload.get("source_event_id") == source_event_id]
    if len(matches) != 1:
        raise ValueError("I5A_CARRIER_SOURCE_ACQUISITION_REQUIRED_EXACTLY_ONCE")
    acquisition = matches[0]
    if acquisition.payload.get("mode") != "SAW":
        raise ValueError("I5A_REFERENCE_REQUIRES_DIRECT_SAW_PROVENANCE")
    mind = world.npc_minds[carrier_npc_id]
    if acquisition.event_id not in mind.memories:
        raise ValueError("I5A_CARRIER_ACQUISITION_NOT_IN_MEMORY_INDEX")
    if source_event_id not in mind.knowledge_boundary_refs:
        raise ValueError("I5A_CARRIER_SOURCE_NOT_IN_KNOWLEDGE_BOUNDARY")
    return acquisition


def _build_from_replay_validated_world(*, world: WorldState, source_event_id: str, carrier_npc_id: str, player_actor_id: str, fixture: ShadowPlausibilityFixture, source_i1_sha256: str) -> InformationOpportunityShadowResult:
    _load_governed_semantics()
    source_event_id = _require_string(source_event_id, "I5A_SOURCE_EVENT_ID_REQUIRED")
    carrier_npc_id = _require_string(carrier_npc_id, "I5A_CARRIER_NPC_ID_REQUIRED")
    player_actor_id = _require_string(player_actor_id, "I5A_PLAYER_ACTOR_ID_REQUIRED")
    if not isinstance(fixture, ShadowPlausibilityFixture):
        raise TypeError("I5A_SHADOW_FIXTURE_REQUIRED")
    if fixture.authority_class != _FIXTURE_AUTHORITY_CLASS:
        raise ValueError("I5A_REFERENCE_FIXTURE_AUTHORITY_CLASS_INVALID")
    _require_string(fixture.fixture_id, "I5A_FIXTURE_ID_REQUIRED")
    _require_string(fixture.target_scene_id, "I5A_TARGET_SCENE_ID_REQUIRED")
    _require_string(fixture.carrier_origin_scene_id, "I5A_CARRIER_ORIGIN_SCENE_ID_REQUIRED")
    if fixture.travel_steps_required < 0 or fixture.travel_steps_available < 0:
        raise ValueError("I5A_TRAVEL_STEPS_INVALID")
    events = _event_index(world)
    source = events.get(source_event_id)
    if source is None:
        raise ValueError("I5A_SOURCE_EVENT_NOT_CANONICAL")
    if carrier_npc_id not in world.npc_minds or carrier_npc_id not in world.actors:
        raise ValueError("I5A_CARRIER_NPC_NOT_CANONICAL")
    if player_actor_id not in world.actors or player_actor_id == carrier_npc_id:
        raise ValueError("I5A_PLAYER_ACTOR_NOT_CANONICAL")
    if source.actor_id is None or source.actor_id not in world.actors:
        raise ValueError("I5A_SOURCE_EVENT_ACTOR_REQUIRED")
    acquisition = _find_carrier_acquisition(world, carrier_npc_id=carrier_npc_id, source_event_id=source_event_id)
    illegal_player_acquisitions = [event.event_id for event in world.event_log if event.event_type == "NPC_KNOWLEDGE_ACQUIRED" and event.payload.get("npc_id") == player_actor_id and event.payload.get("source_event_id") == source_event_id]
    if illegal_player_acquisitions:
        raise ValueError("I5A_PLAYER_KNOWLEDGE_INJECTION_DETECTED")
    player_scene = world.actors[player_actor_id].scene_id
    carrier_scene = world.actors[carrier_npc_id].scene_id
    info_id = f"INFO:{source_event_id}:{carrier_npc_id}"
    information_packet = {"info_id": info_id, "source_fact_or_event_refs": [source_event_id], "classification": "REFERENCE_WORLD_EVENT_NEWS", "source_refs": [acquisition.event_id], "verification_state": "DIRECT_WITNESS_REFERENCE_ONLY", "confidence": 1.0, "distortion_policy": "NO_DISTORTION_MODEL_SELECTED_IN_I5A_REFERENCE", "created_world_time": None, "propagation_scope": "SHADOW_REFERENCE_ONLY", "expiry_policy": "NO_PRODUCTION_EXPIRY_POLICY_SELECTED"}
    rejections: list[str] = []
    spatial_checks = [f"PLAYER_SCENE_MATCH:{fixture.target_scene_id == player_scene}", f"CARRIER_ORIGIN_MATCH:{fixture.carrier_origin_scene_id == carrier_scene}", f"ROUTE_AVAILABLE:{fixture.route_available}"]
    if fixture.target_scene_id != player_scene:
        rejections.append("TARGET_SCENE_NOT_PLAYER_LOCATION")
    if fixture.carrier_origin_scene_id != carrier_scene:
        rejections.append("CARRIER_ORIGIN_HISTORY_CONFLICT")
    if not fixture.route_available:
        rejections.append("NO_VALID_ROUTE")
    temporal_checks = [f"TRAVEL_STEPS_REQUIRED:{fixture.travel_steps_required}", f"TRAVEL_STEPS_AVAILABLE:{fixture.travel_steps_available}"]
    if fixture.travel_steps_required > fixture.travel_steps_available:
        rejections.append("INSUFFICIENT_TRAVEL_TIME")
    identity_checks = [f"IDENTITY_HISTORY_CONSISTENT:{fixture.identity_history_consistent}"]
    if not fixture.identity_history_consistent:
        rejections.append("IDENTITY_HISTORY_CONFLICT")
    motivation_present = isinstance(fixture.motivation_ref, str) and bool(fixture.motivation_ref.strip())
    motivation_checks = [f"MOTIVATION_PRESENT:{motivation_present}"]
    if not motivation_present:
        rejections.append("MOTIVATION_EVIDENCE_MISSING")
    if not fixture.asset_available:
        rejections.append("REFERENCE_ASSET_UNAVAILABLE")
    if not fixture.anti_repeat_allowed:
        rejections.append("ANTI_REPEAT_GATE_REJECTED")
    gate = {"gate_version": "I5A-SHADOW-REFERENCE-1", "spatial_checks": spatial_checks, "temporal_checks": temporal_checks, "identity_history_checks": identity_checks, "motivation_checks": motivation_checks, "information_provenance_checks": [f"SOURCE_EVENT_CANONICAL:{source_event_id}", f"CARRIER_ACQUISITION:{acquisition.event_id}", "CARRIER_MODE:SAW", "PLAYER_REMAINS_UNMODIFIED_BY_IMPORTANCE"], "density_checks": ["OD-ENCOUNTER-DENSITY-001_DEFERRED", "SINGLE_REFERENCE_CANDIDATE_ONLY"], "asset_availability_checks": [f"REFERENCE_ASSET_AVAILABLE:{fixture.asset_available}"], "anti_repeat_checks": [f"REFERENCE_ANTI_REPEAT_ALLOWED:{fixture.anti_repeat_allowed}", "NO_PRODUCTION_RETRY_BUDGET_SELECTED"]}
    broker = {"broker_contract_version": "1.0.0-candidate", "input_refs": [source_event_id, acquisition.event_id, player_actor_id, carrier_npc_id, fixture.fixture_id], "candidate_policy_ref": "I5A-REFERENCE-POLICY-NON_PRODUCTION", "plausibility_gate_ref": "I5A-SHADOW-REFERENCE-1"}
    candidate: Mapping[str, Any] | None = None
    status = _RESULT_STATUS_NONE
    if not rejections:
        status = _RESULT_STATUS_CANDIDATE
        candidate = {"encounter_id": f"SHADOW:{source_event_id}:{carrier_npc_id}:{player_actor_id}:{fixture.fixture_id}", "source_goal_refs": [f"REFERENCE_INFORMATION_OPPORTUNITY:{info_id}"], "world_scope": {"world_id": world.world_id, "target_scene_id": fixture.target_scene_id, "shadow_only": True}, "time_window": {"required_steps": fixture.travel_steps_required, "available_steps": fixture.travel_steps_available, "reference_only": True}, "actor_candidate_refs": [carrier_npc_id, player_actor_id], "motivation_refs": [fixture.motivation_ref], "known_information_refs": [info_id], "affordance_refs": ["REFERENCE_CONVERSATION_POSSIBLE_NOT_COMMITTED"], "forbidden_inventions": list(_FORBIDDEN_INVENTIONS), "eligibility_evidence": [source_event_id, acquisition.event_id, fixture.fixture_id, "PLAUSIBILITY_GATE_PASS", "REFERENCE_FIXTURE_NOT_CANONICAL_WORLD_EVIDENCE"], "expiry_policy": "NO_PRODUCTION_EXPIRY_POLICY_SELECTED"}
    acquisition_material = {"acquisition_event": _event_material(acquisition), "memory_index_contains": acquisition.event_id in world.npc_minds[carrier_npc_id].memories, "knowledge_boundary_contains": source_event_id in world.npc_minds[carrier_npc_id].knowledge_boundary_refs}
    return InformationOpportunityShadowResult(status=status, source_event_id=source_event_id, player_actor_id=player_actor_id, carrier_npc_id=carrier_npc_id, source_world_id=world.world_id, source_state_version=world.state_version, source_i1_sha256=source_i1_sha256, carrier_acquisition_sha256=_sha256(acquisition_material), reference_fixture_sha256=_sha256(_fixture_material(fixture)), information_packet=freeze_value(information_packet), broker=freeze_value(broker), plausibility_gate=freeze_value(gate), encounter_candidate=None if candidate is None else freeze_value(candidate), rejection_reasons=tuple(rejections))


def build_information_opportunity_shadow(*, baseline: WorldBaseline, world: WorldState, source_event_id: str, carrier_npc_id: str, player_actor_id: str, fixture: ShadowPlausibilityFixture, caller_information_packet: Mapping[str, Any] | None = None) -> InformationOpportunityShadowResult:
    if caller_information_packet is not None:
        raise ValueError("I5A_CALLER_AUTHORED_INFORMATION_PACKET_FORBIDDEN")
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I5A_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I5A_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    solo_package = export_solo_replay_package(baseline, world)
    return _build_from_replay_validated_world(world=world, source_event_id=source_event_id, carrier_npc_id=carrier_npc_id, player_actor_id=player_actor_id, fixture=fixture, source_i1_sha256=hashlib.sha256(solo_package).hexdigest())


def export_information_opportunity_shadow_package(*, baseline: WorldBaseline, world: WorldState, source_event_id: str, carrier_npc_id: str, player_actor_id: str, fixture: ShadowPlausibilityFixture) -> bytes:
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I5A_BASELINE_AND_WORLD_REQUIRED")
    solo_package = export_solo_replay_package(baseline, world)
    result = _build_from_replay_validated_world(world=world, source_event_id=source_event_id, carrier_npc_id=carrier_npc_id, player_actor_id=player_actor_id, fixture=fixture, source_i1_sha256=hashlib.sha256(solo_package).hexdigest())
    payload = {"package_schema": _PACKAGE_SCHEMA, "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"), "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(), "source_event_id": source_event_id, "carrier_npc_id": carrier_npc_id, "player_actor_id": player_actor_id, "fixture": _fixture_material(fixture), "expected_result": _result_material(result)}
    return _canonical_json({"payload": payload, "sha256": _sha256(payload)}).encode("utf-8")


def replay_information_opportunity_shadow_package(package: bytes | bytearray | memoryview) -> InformationOpportunityShadowResult:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I5A_SHADOW_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(bytes(package).decode("utf-8"), object_pairs_hook=_reject_duplicate_keys, parse_constant=_reject_nonfinite)
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I5A_SHADOW_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I5A_SHADOW_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I5A_SHADOW_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I5A_SHADOW_PACKAGE_TAMPERED")
    encoded = _require_string(payload.get("source_i1_replay_b64"), "I5A_I1_REPLAY_REQUIRED")
    try:
        solo_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I5A_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get("source_i1_replay_sha256"):
        raise ValueError("I5A_I1_REPLAY_DIGEST_MISMATCH")
    world = rehydrate_solo_replay_package(solo_package)
    fixture_raw = payload.get("fixture")
    if not isinstance(fixture_raw, Mapping) or set(fixture_raw) != {"fixture_id", "target_scene_id", "carrier_origin_scene_id", "route_available", "travel_steps_required", "travel_steps_available", "identity_history_consistent", "motivation_ref", "anti_repeat_allowed", "asset_available", "authority_class"}:
        raise ValueError("I5A_SHADOW_FIXTURE_SCHEMA_INVALID")
    fixture = ShadowPlausibilityFixture(**dict(fixture_raw))
    result = _build_from_replay_validated_world(world=world, source_event_id=payload.get("source_event_id"), carrier_npc_id=payload.get("carrier_npc_id"), player_actor_id=payload.get("player_actor_id"), fixture=fixture, source_i1_sha256=hashlib.sha256(solo_package).hexdigest())
    if _result_material(result) != payload.get("expected_result"):
        raise ValueError("I5A_SHADOW_RESULT_MATERIALIZATION_MISMATCH")
    return result
