"""Bounded I6A deterministic encounter orchestration control-packet reference.

This module consumes an already validated I5A shadow package and produces only
non-canonical orchestration control evidence. It never commits world events,
chooses a player action, writes dialogue, creates knowledge, or resolves an
encounter outcome.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse.model import freeze_value, thaw_value
from evals.i5a_information_opportunity_shadow_reference import (
    InformationOpportunityShadowResult,
    replay_information_opportunity_shadow_package,
)

I6_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_AUTO_ENCOUNTER_COMMIT = True
NO_AUTO_PLAYER_ACTION = True
NO_AUTO_SPEECH_OR_KNOWLEDGE = True
NO_CAPABILITY_OVERRIDE = True
NO_LLM_OR_PROVIDER = True
NO_PX_DIRECTOR_RENDERER = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_GOLDEN_PATH = _ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
_SCENARIO_ID = "WILDERNESS_NEWS_TRAP"
_EXPECTED_SCENARIO_VERSION = "1.2.0-candidate"
_EXPECTED_IMPLEMENTATION_STATE = "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
_EXPECTED_OPEN_DECISIONS = {
    "OD-ENCOUNTER-DENSITY-001",
    "OD-PX-SCORING-001",
    "OD-PUBLICATION-POLICY-001",
}
_EXPECTED_ALLOWED_PLAYER_INTENTS = (
    "help or attempt rescue by force",
    "inspect or use a real tool",
    "seek assistance",
    "ask questions",
    "ignore or leave",
    "threaten, rob or attack if otherwise legal",
    "invent another method subject to authority/affordance/capability checks",
)
_EXPECTED_FORBIDDEN_OUTCOMES = {
    "Direct PlayerChronicle injection of E_CAPITAL_ASSASSINATION.",
    "Teleporting a carrier or fabricating travel time.",
    "Secretly lowering rescue difficulty because narrative wants success.",
    "Forcing every isolated traveler to be a main-plot carrier.",
}

_FIXTURE_AUTHORITY_CLASS = "AUTHORED_REFERENCE_ORCHESTRATION_ONLY_NOT_WORLD_TRUTH"
_OPENING_AFFORDANCE = "REFERENCE_ENCOUNTER_PRESENCE_ONLY_NOT_COMMITTED"
_PACKET_AUTHORITY_CLASS = "DERIVED_REFERENCE_CONTROL_EVIDENCE_ONLY_NOT_WORLD_TRUTH"
_PACKAGE_SCHEMA = "AWRSE-I6A-ENCOUNTER-ORCHESTRATION-CONTROL-1"
_DECISION_GATE = "AWAIT_EXPLICIT_PLAYER_INTENT"
_NEXT_HANDOFF = {
    "compiler_authority": "runtime.awrse.ActionCompiler",
    "resolver_authority": "runtime.awrse.SimulationEngine",
    "commit_rule": "ONLY_AFTER_EXPLICIT_PLAYER_ACTION_AND_CANONICAL_VALIDATION",
}
_FORBIDDEN_AUTO_EFFECTS = (
    "NO_WORLD_EVENT_AUTO_COMMIT",
    "NO_ACTOR_AUTO_SPAWN_OR_MOVEMENT",
    "NO_AUTO_PLAYER_ACTION",
    "NO_AUTO_SPEECH",
    "NO_AUTO_PLAYER_OR_NPC_KNOWLEDGE",
    "NO_AUTO_RESCUE_SUCCESS_OR_FAILURE",
    "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE",
    "NO_INFORMATION_PROVENANCE_INVENTION",
    "NO_AUTO_QUEST_TRADE_PROMISE_ALLIANCE_ACCEPTANCE",
    "NO_PX_DIRECTOR_RENDERER_LLM_PROVIDER_AUTHORITY",
)
_REQUIRED_I5_FORBIDDEN = {
    "NO_WORLD_EVENT_COMMIT",
    "NO_ACTOR_SPAWN_OR_MOVEMENT",
    "NO_PLAYER_OR_NPC_KNOWLEDGE_MUTATION",
    "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE",
    "NO_FORCED_DIALOGUE_OR_SUCCESS",
    "NO_PX_DIRECTOR_RENDERER_ADMISSION_AUTHORITY",
}


@dataclass(frozen=True)
class AuthoredEncounterOrchestrationFixture:
    fixture_id: str
    candidate_encounter_id: str
    source_event_id: str
    player_actor_id: str
    carrier_npc_id: str
    information_ref: str
    scenario_id: str = _SCENARIO_ID
    opening_affordance: str = _OPENING_AFFORDANCE
    authority_class: str = _FIXTURE_AUTHORITY_CLASS


@dataclass(frozen=True)
class EncounterOrchestrationControlPacket:
    status: str
    packet_id: str
    scenario_id: str
    source_i5_sha256: str
    accepted_candidate_sha256: str
    candidate_encounter_id: str
    source_event_id: str
    player_actor_id: str
    carrier_npc_id: str
    known_information_refs: tuple[str, ...]
    opening_affordance: str
    allowed_player_intents: tuple[str, ...]
    decision_gate: str
    next_authority_handoff: Mapping[str, Any]
    forbidden_auto_effects: tuple[str, ...]
    authority_class: str
    world_mutation_count: int


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
        raise ValueError("I6A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I6A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I6A_JSON_NONFINITE:{value}")


def _load_golden_scenario() -> Mapping[str, Any]:
    try:
        golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I6A_CANONICAL_GOLDEN_UNAVAILABLE") from None
    if not isinstance(golden, Mapping):
        raise ValueError("I6A_CANONICAL_GOLDEN_INVALID")
    scenarios = golden.get("scenarios")
    scenario = scenarios.get(_SCENARIO_ID) if isinstance(scenarios, Mapping) else None
    if not isinstance(scenario, Mapping):
        raise ValueError("I6A_GOLDEN_SCENARIO_MISSING")
    machine = scenario.get("machine_spec")
    if not isinstance(machine, Mapping):
        raise ValueError("I6A_GOLDEN_MACHINE_SPEC_MISSING")
    if machine.get("scenario_id") != _SCENARIO_ID:
        raise ValueError("I6A_GOLDEN_SCENARIO_ID_DRIFT")
    if machine.get("scenario_version") != _EXPECTED_SCENARIO_VERSION:
        raise ValueError("I6A_GOLDEN_SCENARIO_VERSION_DRIFT")
    if machine.get("implementation_state") != _EXPECTED_IMPLEMENTATION_STATE:
        raise ValueError("I6A_GOLDEN_RUNTIME_AUTHORITY_DRIFT")
    if not _EXPECTED_OPEN_DECISIONS <= set(machine.get("open_decision_dependencies", [])):
        raise ValueError("I6A_OPEN_DECISION_BOUNDARY_DRIFT")
    allowed = scenario.get("allowed_player_intents")
    if not isinstance(allowed, Sequence) or isinstance(allowed, (str, bytes, bytearray)):
        raise ValueError("I6A_GOLDEN_ALLOWED_INTENTS_INVALID")
    if tuple(allowed) != _EXPECTED_ALLOWED_PLAYER_INTENTS:
        raise ValueError("I6A_GOLDEN_ALLOWED_INTENTS_DRIFT")
    forbidden = scenario.get("forbidden_outcomes")
    if not isinstance(forbidden, Sequence) or isinstance(forbidden, (str, bytes, bytearray)):
        raise ValueError("I6A_GOLDEN_FORBIDDEN_OUTCOMES_INVALID")
    if not _EXPECTED_FORBIDDEN_OUTCOMES <= set(forbidden):
        raise ValueError("I6A_GOLDEN_ANTI_RAILROAD_RULES_DRIFT")
    return scenario


def _fixture_material(fixture: AuthoredEncounterOrchestrationFixture) -> dict[str, Any]:
    return {
        "fixture_id": fixture.fixture_id,
        "candidate_encounter_id": fixture.candidate_encounter_id,
        "source_event_id": fixture.source_event_id,
        "player_actor_id": fixture.player_actor_id,
        "carrier_npc_id": fixture.carrier_npc_id,
        "information_ref": fixture.information_ref,
        "scenario_id": fixture.scenario_id,
        "opening_affordance": fixture.opening_affordance,
        "authority_class": fixture.authority_class,
    }


def _packet_material(packet: EncounterOrchestrationControlPacket) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "status": packet.status,
                "packet_id": packet.packet_id,
                "scenario_id": packet.scenario_id,
                "source_i5_sha256": packet.source_i5_sha256,
                "accepted_candidate_sha256": packet.accepted_candidate_sha256,
                "candidate_encounter_id": packet.candidate_encounter_id,
                "source_event_id": packet.source_event_id,
                "player_actor_id": packet.player_actor_id,
                "carrier_npc_id": packet.carrier_npc_id,
                "known_information_refs": list(packet.known_information_refs),
                "opening_affordance": packet.opening_affordance,
                "allowed_player_intents": list(packet.allowed_player_intents),
                "decision_gate": packet.decision_gate,
                "next_authority_handoff": thaw_value(packet.next_authority_handoff),
                "forbidden_auto_effects": list(packet.forbidden_auto_effects),
                "authority_class": packet.authority_class,
                "world_mutation_count": packet.world_mutation_count,
            }
        )
    )


def _validate_fixture_binding(
    fixture: AuthoredEncounterOrchestrationFixture,
    result: InformationOpportunityShadowResult,
    candidate: Mapping[str, Any],
    information: Mapping[str, Any],
) -> None:
    if not isinstance(fixture, AuthoredEncounterOrchestrationFixture):
        raise TypeError("I6A_AUTHORED_FIXTURE_REQUIRED")
    if fixture.authority_class != _FIXTURE_AUTHORITY_CLASS:
        raise ValueError("I6A_FIXTURE_AUTHORITY_CLASS_INVALID")
    if fixture.scenario_id != _SCENARIO_ID:
        raise ValueError("I6A_FIXTURE_SCENARIO_MISMATCH")
    if fixture.opening_affordance != _OPENING_AFFORDANCE:
        raise ValueError("I6A_OPENING_AFFORDANCE_NOT_AUTHORIZED")
    _require_string(fixture.fixture_id, "I6A_FIXTURE_ID_REQUIRED")

    bindings = {
        "candidate_encounter_id": candidate.get("encounter_id"),
        "source_event_id": result.source_event_id,
        "player_actor_id": result.player_actor_id,
        "carrier_npc_id": result.carrier_npc_id,
        "information_ref": information.get("info_id"),
    }
    for field, expected in bindings.items():
        actual = getattr(fixture, field)
        if actual != expected:
            raise ValueError(f"I6A_FIXTURE_BINDING_MISMATCH:{field}")


def build_encounter_orchestration_control_packet(
    *,
    i5_shadow_package: bytes | bytearray | memoryview,
    fixture: AuthoredEncounterOrchestrationFixture,
    caller_preselected_player_action: Any = None,
    caller_preselected_outcome: Any = None,
    caller_prewritten_dialogue: Any = None,
) -> EncounterOrchestrationControlPacket:
    if caller_preselected_player_action is not None:
        raise ValueError("I6A_PRESELECTED_PLAYER_ACTION_FORBIDDEN")
    if caller_preselected_outcome is not None:
        raise ValueError("I6A_PRESELECTED_OUTCOME_FORBIDDEN")
    if caller_prewritten_dialogue is not None:
        raise ValueError("I6A_PREWRITTEN_DIALOGUE_FORBIDDEN")
    if not isinstance(i5_shadow_package, (bytes, bytearray, memoryview)):
        raise TypeError("I6A_I5_SHADOW_PACKAGE_BYTES_REQUIRED")

    _load_golden_scenario()
    source_bytes = bytes(i5_shadow_package)
    result = replay_information_opportunity_shadow_package(source_bytes)
    if result.status != "SHADOW_ENCOUNTER_CANDIDATE" or result.encounter_candidate is None:
        raise ValueError("I6A_REQUIRES_ACCEPTED_I5_SHADOW_CANDIDATE")

    candidate = thaw_value(result.encounter_candidate)
    information = thaw_value(result.information_packet)
    if not isinstance(candidate, Mapping) or not isinstance(information, Mapping):
        raise ValueError("I6A_I5_MATERIAL_INVALID")
    if candidate.get("world_scope", {}).get("shadow_only") is not True:
        raise ValueError("I6A_I5_CANDIDATE_NOT_SHADOW_ONLY")
    if not _REQUIRED_I5_FORBIDDEN <= set(candidate.get("forbidden_inventions", [])):
        raise ValueError("I6A_I5_ANTI_AUTHORITY_GUARDS_MISSING")
    if candidate.get("actor_candidate_refs") != [result.carrier_npc_id, result.player_actor_id]:
        raise ValueError("I6A_I5_PARTICIPANT_BINDING_INVALID")
    known_information_refs = candidate.get("known_information_refs")
    if known_information_refs != [information.get("info_id")]:
        raise ValueError("I6A_I5_INFORMATION_BINDING_INVALID")

    _validate_fixture_binding(fixture, result, candidate, information)

    source_i5_sha256 = hashlib.sha256(source_bytes).hexdigest()
    accepted_candidate_sha256 = _sha256(candidate)
    identity_material = {
        "source_i5_sha256": source_i5_sha256,
        "candidate_encounter_id": candidate["encounter_id"],
        "fixture_id": fixture.fixture_id,
        "scenario_id": _SCENARIO_ID,
    }
    packet_id = f"I6A:{_sha256(identity_material)[:24]}"

    return EncounterOrchestrationControlPacket(
        status="ORCHESTRATION_CONTROL_PACKET_READY",
        packet_id=packet_id,
        scenario_id=_SCENARIO_ID,
        source_i5_sha256=source_i5_sha256,
        accepted_candidate_sha256=accepted_candidate_sha256,
        candidate_encounter_id=str(candidate["encounter_id"]),
        source_event_id=result.source_event_id,
        player_actor_id=result.player_actor_id,
        carrier_npc_id=result.carrier_npc_id,
        known_information_refs=tuple(str(value) for value in known_information_refs),
        opening_affordance=_OPENING_AFFORDANCE,
        allowed_player_intents=_EXPECTED_ALLOWED_PLAYER_INTENTS,
        decision_gate=_DECISION_GATE,
        next_authority_handoff=freeze_value(_NEXT_HANDOFF),
        forbidden_auto_effects=_FORBIDDEN_AUTO_EFFECTS,
        authority_class=_PACKET_AUTHORITY_CLASS,
        world_mutation_count=0,
    )


def export_encounter_orchestration_control_package(
    *,
    i5_shadow_package: bytes | bytearray | memoryview,
    fixture: AuthoredEncounterOrchestrationFixture,
) -> bytes:
    source_bytes = bytes(i5_shadow_package)
    packet = build_encounter_orchestration_control_packet(
        i5_shadow_package=source_bytes,
        fixture=fixture,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "source_i5_b64": base64.b64encode(source_bytes).decode("ascii"),
        "source_i5_sha256": hashlib.sha256(source_bytes).hexdigest(),
        "fixture": _fixture_material(fixture),
        "expected_packet": _packet_material(packet),
    }
    envelope = {"payload": payload, "sha256": _sha256(payload)}
    return _canonical_json(envelope).encode("utf-8")


def replay_encounter_orchestration_control_package(
    package: bytes | bytearray | memoryview,
) -> EncounterOrchestrationControlPacket:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I6A_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I6A_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I6A_PACKAGE_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I6A_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I6A_PACKAGE_TAMPERED")

    encoded = _require_string(payload.get("source_i5_b64"), "I6A_SOURCE_I5_REQUIRED")
    try:
        source_i5 = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I6A_SOURCE_I5_ENCODING_INVALID") from None
    if hashlib.sha256(source_i5).hexdigest() != payload.get("source_i5_sha256"):
        raise ValueError("I6A_SOURCE_I5_DIGEST_MISMATCH")

    fixture_raw = payload.get("fixture")
    expected_fixture_fields = {
        "fixture_id",
        "candidate_encounter_id",
        "source_event_id",
        "player_actor_id",
        "carrier_npc_id",
        "information_ref",
        "scenario_id",
        "opening_affordance",
        "authority_class",
    }
    if not isinstance(fixture_raw, Mapping) or set(fixture_raw) != expected_fixture_fields:
        raise ValueError("I6A_FIXTURE_SCHEMA_INVALID")
    fixture = AuthoredEncounterOrchestrationFixture(**dict(fixture_raw))
    packet = build_encounter_orchestration_control_packet(
        i5_shadow_package=source_i5,
        fixture=fixture,
    )
    if _packet_material(packet) != payload.get("expected_packet"):
        raise ValueError("I6A_PACKET_MATERIALIZATION_MISMATCH")
    return packet
