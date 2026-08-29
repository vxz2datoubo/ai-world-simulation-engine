"""Bounded I8C evidence-gated Storylet eligibility reference.

Storylet definitions remain authored, non-canonical narrative design. This
module never realizes a Storylet. It consumes a replay-valid I8B callback
opportunity and asks whether one bounded authored Storylet is currently legal.
The only outputs are STORYLET_ELIGIBLE or NO_VALID_STORYLET.
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
from awrse.model import thaw_value
import evals.i8b_promise_callback_opportunity_reference as i8b_reference

I8C_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_STORYLET_REALIZATION = True
NO_EVENT_DECK_AUTHORITY = True
NO_BRANCH_WELDING_OR_RECONVERGENCE = True
NO_RETCON_OR_RESURRECTION = True
NO_AUTOMATIC_SPEECH_OR_ENCOUNTER = True
NO_PROMISE_PAYOFF_OR_BREACH = True
NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_GOLDEN_PATH = _ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.10.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1",
)
_EXPECTED_STORYLET_TYPE = (
    "AF001.Storylet",
    "1.0.0-candidate",
    "NARRATIVE_DESIGN_NON_CANONICAL",
)
_EXPECTED_STORYLET_FIELDS = {
    "storylet_id",
    "preconditions",
    "eligible_roles",
    "knowledge_constraints",
    "dramatic_purpose",
    "forbidden_contradictions",
    "consequence_templates",
    "repeat_policy",
    "version",
}
_EXPECTED_NARRATIVE_DESIGN_PROFILE = {
    "canonical_data_authority": ["NONE"],
    "contract_schema_steward": "AWRSE_AF_F_CONTRACT_STEWARD",
    "producer_or_assembler": [
        "AWRSE_NARRATIVE_DESIGN_LOADER",
        "NARRATIVE_DESIGN_NON_CANONICAL",
    ],
    "downstream_consumer": ["NARRATIVE_OPPORTUNITY", "PX_RANKING", "AI_DIRECTOR"],
    "staging_authority": ["NONE"],
    "mutation_constraint": (
        "AUTHORED_NARRATIVE_CONSTRAINTS_MAY_PROPOSE_OR_FILTER_BUT_CANNOT_RETCON_CANONICAL_WORLD_TRUTH"
    ),
}
_REQUIRED_AF_F_INVARIANTS = {
    "STORY_STRUCTURE_IS_NOT_WORLD_TRUTH",
    "AUTHORED_NARRATIVE_NE_PROMISE_HISTORY",
    "BRANCH_QUALITY_CANNOT_JUSTIFY_RETCON_OR_RESURRECTION",
}
_REQUIRED_AF_G_INVARIANTS = {"NO_VALID_OPPORTUNITY_IS_VALID"}
_REQUIRED_FORBIDDEN_CONTRADICTIONS = {
    "NO_RETCON_OR_RESURRECTION",
    "NO_BRANCH_WELDING",
    "NO_AUTOMATIC_SPEECH",
    "NO_AUTOMATIC_PAYOFF_OR_BREACH",
}
_ALLOWED_CONSEQUENCE_TEMPLATES = {"NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"}
_ALLOWED_PRECONDITIONS = {
    "CALLBACK_OPPORTUNITY_REQUIRED",
    "TARGET_OBJECT_PRESENT",
    "ACTORS_SHARE_ACTIVE_SCENE",
    "WORLD_EVENT_PRESENT",
}
_ALLOWED_KNOWLEDGE_CONSTRAINTS = {
    "CALLBACK_REQUIRED_FACTS_EXACT",
    "EXACT_CALLBACK_RECIPIENT",
}
_PACKAGE_SCHEMA = "AWRSE-I8C-STORYLET-ELIGIBILITY-REPLAY-1"
_AUTHORITY_CLASS = "NON_CANONICAL_STORYLET_ELIGIBILITY_ONLY"


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
        raise ValueError("I8C_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I8C_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I8C_JSON_NONFINITE:{value}")


def _load_authority() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I8C_CANONICAL_CONTRACT_UNAVAILABLE") from None
    if not isinstance(contract, Mapping):
        raise ValueError("I8C_CANONICAL_CONTRACT_INVALID")

    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I8C_CANONICAL_PARENT_DRIFT")

    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I8C_TYPE_REGISTRY_MISSING")
    storylet = registry.get("Storylet")
    if not isinstance(storylet, Mapping):
        raise ValueError("I8C_STORYLET_TYPE_MISSING")
    actual = (
        storylet.get("type_id"),
        storylet.get("version"),
        storylet.get("authority_profile_ref"),
    )
    if actual != _EXPECTED_STORYLET_TYPE:
        raise ValueError("I8C_STORYLET_TYPE_DRIFT")
    if set(storylet.get("fields", [])) != _EXPECTED_STORYLET_FIELDS:
        raise ValueError("I8C_STORYLET_FIELDS_DRIFT")

    authority_semantics = contract.get("authority_semantics")
    if not isinstance(authority_semantics, Mapping):
        raise ValueError("I8C_AUTHORITY_SEMANTICS_MISSING")
    profiles = authority_semantics.get("profiles")
    if not isinstance(profiles, Mapping):
        raise ValueError("I8C_AUTHORITY_PROFILES_MISSING")
    narrative_profile = profiles.get("NARRATIVE_DESIGN_NON_CANONICAL")
    if not isinstance(narrative_profile, Mapping):
        raise ValueError("I8C_NARRATIVE_DESIGN_PROFILE_MISSING")
    if dict(narrative_profile) != _EXPECTED_NARRATIVE_DESIGN_PROFILE:
        raise ValueError("I8C_NARRATIVE_DESIGN_PROFILE_DRIFT")

    freeze = contract.get("freeze_domains", {})
    af_f = freeze.get("AF-F")
    af_g = freeze.get("AF-G")
    if not isinstance(af_f, Mapping) or not _REQUIRED_AF_F_INVARIANTS <= set(
        af_f.get("invariants", [])
    ):
        raise ValueError("I8C_AF_F_INVARIANT_DRIFT")
    if not isinstance(af_g, Mapping) or not _REQUIRED_AF_G_INVARIANTS <= set(
        af_g.get("invariants", [])
    ):
        raise ValueError("I8C_AF_G_INVARIANT_DRIFT")
    return _EXPECTED_PARENT


def _load_golden_guard() -> None:
    try:
        golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        raise ValueError("I8C_GOLDEN_UNAVAILABLE") from None
    scenario = (
        golden.get("scenarios", {}).get("HOSTILE_PLAYER_BREAKS_PLOT")
        if isinstance(golden, Mapping)
        else None
    )
    if not isinstance(scenario, Mapping):
        raise ValueError("I8C_HOSTILE_PLAYER_GOLDEN_MISSING")
    machine = scenario.get("machine_spec")
    if not isinstance(machine, Mapping) or "Storylet" not in machine.get(
        "actual_type_refs", []
    ):
        raise ValueError("I8C_HOSTILE_PLAYER_GOLDEN_TYPE_DRIFT")
    initial = machine.get("initial_state_predicates", [])
    if not any(
        isinstance(row, Mapping)
        and row.get("type_ref") == "Storylet"
        and row.get("assertion") == "storylet_eligibility_cannot_force_world_fact"
        for row in initial
    ):
        raise ValueError("I8C_STORYLET_NONCANONICAL_GOLDEN_GUARD_DRIFT")
    acceptance = set(scenario.get("acceptance_criteria", []))
    if "Narrative returns legal alternative or NO_VALID_OPPORTUNITY." not in acceptance:
        raise ValueError("I8C_NO_VALID_OPPORTUNITY_GOLDEN_GUARD_DRIFT")


def _validate_storylet_definition(
    storylet_definition: Mapping[str, Any],
) -> dict[str, Any]:
    if not isinstance(storylet_definition, Mapping):
        raise TypeError("I8C_STORYLET_DEFINITION_MAPPING_REQUIRED")
    material = json.loads(_canonical_json(storylet_definition))
    if set(material) != _EXPECTED_STORYLET_FIELDS:
        raise ValueError("I8C_STORYLET_DEFINITION_FIELDS_INVALID")
    _require_string(material.get("storylet_id"), "I8C_STORYLET_ID_REQUIRED")
    _require_string(material.get("dramatic_purpose"), "I8C_DRAMATIC_PURPOSE_REQUIRED")
    _require_string(material.get("version"), "I8C_STORYLET_VERSION_REQUIRED")

    roles = material.get("eligible_roles")
    if not isinstance(roles, Mapping) or set(roles) != {
        "player_actor_id",
        "callback_npc_id",
    }:
        raise ValueError("I8C_ELIGIBLE_ROLES_REFERENCE_SHAPE_INVALID")
    for key in ("player_actor_id", "callback_npc_id"):
        _require_string(roles.get(key), f"I8C_ELIGIBLE_ROLE_REQUIRED:{key}")

    preconditions = _require_sequence(
        material.get("preconditions"), "I8C_PRECONDITIONS_SEQUENCE_REQUIRED"
    )
    if not preconditions:
        raise ValueError("I8C_PRECONDITIONS_REQUIRED")
    for row in preconditions:
        if not isinstance(row, Mapping):
            raise ValueError("I8C_PRECONDITION_MAPPING_REQUIRED")
        kind = _require_string(row.get("kind"), "I8C_PRECONDITION_KIND_REQUIRED")
        if kind not in _ALLOWED_PRECONDITIONS:
            raise ValueError(f"I8C_UNSUPPORTED_PRECONDITION:{kind}")
        expected_keys = {
            "CALLBACK_OPPORTUNITY_REQUIRED": {"kind"},
            "TARGET_OBJECT_PRESENT": {"kind", "object_id"},
            "ACTORS_SHARE_ACTIVE_SCENE": {"kind", "actor_ids"},
            "WORLD_EVENT_PRESENT": {"kind", "event_id"},
        }[kind]
        if set(row) != expected_keys:
            raise ValueError(f"I8C_PRECONDITION_SHAPE_INVALID:{kind}")

    knowledge = _require_sequence(
        material.get("knowledge_constraints"),
        "I8C_KNOWLEDGE_CONSTRAINTS_SEQUENCE_REQUIRED",
    )
    if not knowledge:
        raise ValueError("I8C_KNOWLEDGE_CONSTRAINTS_REQUIRED")
    for row in knowledge:
        if not isinstance(row, Mapping):
            raise ValueError("I8C_KNOWLEDGE_CONSTRAINT_MAPPING_REQUIRED")
        kind = _require_string(
            row.get("kind"), "I8C_KNOWLEDGE_CONSTRAINT_KIND_REQUIRED"
        )
        if kind not in _ALLOWED_KNOWLEDGE_CONSTRAINTS:
            raise ValueError(f"I8C_UNSUPPORTED_KNOWLEDGE_CONSTRAINT:{kind}")
        expected_keys = {
            "CALLBACK_REQUIRED_FACTS_EXACT": {"kind", "fact_refs"},
            "EXACT_CALLBACK_RECIPIENT": {"kind", "npc_id"},
        }[kind]
        if set(row) != expected_keys:
            raise ValueError(f"I8C_KNOWLEDGE_CONSTRAINT_SHAPE_INVALID:{kind}")

    forbidden = set(
        _require_sequence(
            material.get("forbidden_contradictions"),
            "I8C_FORBIDDEN_CONTRADICTIONS_SEQUENCE_REQUIRED",
        )
    )
    if not _REQUIRED_FORBIDDEN_CONTRADICTIONS <= forbidden:
        raise ValueError("I8C_REQUIRED_ANTI_WELDING_CONTRADICTIONS_MISSING")
    consequences = set(
        _require_sequence(
            material.get("consequence_templates"),
            "I8C_CONSEQUENCE_TEMPLATES_SEQUENCE_REQUIRED",
        )
    )
    if not consequences or not consequences <= _ALLOWED_CONSEQUENCE_TEMPLATES:
        raise ValueError("I8C_UNSAFE_OR_UNSUPPORTED_CONSEQUENCE_TEMPLATE")
    if material.get("repeat_policy") != {"mode": "NO_AUTO_REALIZATION"}:
        raise ValueError("I8C_REPEAT_POLICY_MUST_NOT_AUTO_REALIZE")
    return material


@dataclass(frozen=True)
class StoryletEligibilityReference:
    storylet_id: str
    player_actor_id: str
    candidate_npc_id: str
    source_callback_concept_id: str | None
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    contract_id: str
    contract_version: str
    authority_graph_version: str
    outcome: str
    reason: str
    eligibility_evidence: tuple[str, ...]
    authored_storylet_sha256: str
    authority_class: str


def _reference_material(reference: StoryletEligibilityReference) -> dict[str, Any]:
    return {
        "storylet_id": reference.storylet_id,
        "player_actor_id": reference.player_actor_id,
        "candidate_npc_id": reference.candidate_npc_id,
        "source_callback_concept_id": reference.source_callback_concept_id,
        "source_world_id": reference.source_world_id,
        "source_baseline_version": reference.source_baseline_version,
        "source_state_version": reference.source_state_version,
        "contract_id": reference.contract_id,
        "contract_version": reference.contract_version,
        "authority_graph_version": reference.authority_graph_version,
        "outcome": reference.outcome,
        "reason": reference.reason,
        "eligibility_evidence": list(reference.eligibility_evidence),
        "authored_storylet_sha256": reference.authored_storylet_sha256,
        "authority_class": reference.authority_class,
    }


def _build_from_replay_validated_world(
    *,
    world: WorldState,
    storylet_definition: Mapping[str, Any],
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> StoryletEligibilityReference:
    contract = _load_authority()
    _load_golden_guard()
    storylet = _validate_storylet_definition(storylet_definition)
    player_actor_id = _require_string(player_actor_id, "I8C_PLAYER_ACTOR_ID_REQUIRED")
    candidate_npc_id = _require_string(
        candidate_npc_id, "I8C_CANDIDATE_NPC_ID_REQUIRED"
    )

    callback = i8b_reference._build_from_replay_validated_world(
        world=world,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )
    callback_concept = (
        None if callback.response_concept is None else thaw_value(callback.response_concept)
    )
    callback_concept_id = (
        None
        if callback_concept is None
        else callback_concept.get("response_concept_id")
    )
    evidence: list[str] = []

    def result(outcome: str, reason: str) -> StoryletEligibilityReference:
        return StoryletEligibilityReference(
            storylet_id=storylet["storylet_id"],
            player_actor_id=player_actor_id,
            candidate_npc_id=candidate_npc_id,
            source_callback_concept_id=callback_concept_id,
            source_world_id=world.world_id,
            source_baseline_version=world.baseline_version,
            source_state_version=world.state_version,
            contract_id=contract[0],
            contract_version=contract[1],
            authority_graph_version=contract[2],
            outcome=outcome,
            reason=reason,
            eligibility_evidence=tuple(evidence),
            authored_storylet_sha256=_sha256(storylet),
            authority_class=_AUTHORITY_CLASS,
        )

    if callback.outcome != "CALLBACK_OPPORTUNITY" or callback_concept is None:
        return result("NO_VALID_STORYLET", "SOURCE_CALLBACK_NOT_CURRENTLY_VALID")
    evidence.append(f"CALLBACK:{callback_concept_id}")

    roles = storylet["eligible_roles"]
    if (
        roles.get("player_actor_id") != player_actor_id
        or roles.get("callback_npc_id") != candidate_npc_id
    ):
        return result(
            "NO_VALID_STORYLET", "AUTHORED_ROLE_BINDING_NOT_CURRENTLY_VALID"
        )
    evidence.append(f"ROLE:PLAYER:{player_actor_id}")
    evidence.append(f"ROLE:NPC:{candidate_npc_id}")

    committed = set(world.committed_event_ids)
    for row in storylet["preconditions"]:
        kind = row["kind"]
        if kind == "CALLBACK_OPPORTUNITY_REQUIRED":
            evidence.append(f"PRECONDITION:CALLBACK:{callback_concept_id}")
        elif kind == "TARGET_OBJECT_PRESENT":
            object_id = _require_string(
                row.get("object_id"), "I8C_PRECONDITION_OBJECT_ID_REQUIRED"
            )
            obj = world.objects.get(object_id)
            if obj is None or obj.scene_id != world.active_scene_id:
                return result(
                    "NO_VALID_STORYLET",
                    "TARGET_OBJECT_NOT_PRESENT_IN_REPLAY_VALID_ACTIVE_SCENE",
                )
            evidence.append(f"OBJECT_PRESENT:{object_id}")
        elif kind == "ACTORS_SHARE_ACTIVE_SCENE":
            actor_ids = tuple(
                _require_string(value, "I8C_PRECONDITION_ACTOR_ID_REQUIRED")
                for value in _require_sequence(
                    row.get("actor_ids"), "I8C_PRECONDITION_ACTOR_IDS_REQUIRED"
                )
            )
            if not actor_ids or any(actor_id not in world.actors for actor_id in actor_ids):
                return result(
                    "NO_VALID_STORYLET", "REQUIRED_ACTOR_ABSENT_FROM_CANONICAL_WORLD"
                )
            if any(
                world.actors[actor_id].scene_id != world.active_scene_id
                for actor_id in actor_ids
            ):
                return result(
                    "NO_VALID_STORYLET",
                    "REQUIRED_ACTORS_NOT_IN_REPLAY_VALID_ACTIVE_SCENE",
                )
            evidence.extend(f"ACTIVE_SCENE_ACTOR:{actor_id}" for actor_id in actor_ids)
        elif kind == "WORLD_EVENT_PRESENT":
            event_id = _require_string(
                row.get("event_id"), "I8C_PRECONDITION_EVENT_ID_REQUIRED"
            )
            if event_id not in committed:
                return result(
                    "NO_VALID_STORYLET", "REQUIRED_WORLD_EVENT_NOT_COMMITTED"
                )
            evidence.append(f"WORLD_EVENT:{event_id}")

    required_callback_facts = list(callback_concept.get("required_fact_refs", []))
    for row in storylet["knowledge_constraints"]:
        kind = row["kind"]
        if kind == "CALLBACK_REQUIRED_FACTS_EXACT":
            refs = list(
                _require_sequence(
                    row.get("fact_refs"), "I8C_KNOWLEDGE_FACT_REFS_REQUIRED"
                )
            )
            if refs != required_callback_facts:
                return result(
                    "NO_VALID_STORYLET",
                    "STORYLET_KNOWLEDGE_REFS_DO_NOT_MATCH_CALLBACK_EVIDENCE",
                )
            evidence.extend(f"KNOWLEDGE_FACT:{ref}" for ref in refs)
        elif kind == "EXACT_CALLBACK_RECIPIENT":
            npc_id = _require_string(
                row.get("npc_id"), "I8C_KNOWLEDGE_NPC_ID_REQUIRED"
            )
            if (
                npc_id != candidate_npc_id
                or npc_id != callback.promise_recipient_npc_id
            ):
                return result(
                    "NO_VALID_STORYLET",
                    "STORYLET_CALLBACK_RECIPIENT_IDENTITY_MISMATCH",
                )
            evidence.append(f"KNOWLEDGE_RECIPIENT:{npc_id}")

    return result(
        "STORYLET_ELIGIBLE",
        "ALL_AUTHORED_PRECONDITIONS_REVALIDATED_FROM_CANONICAL_EVIDENCE",
    )


def build_storylet_eligibility_reference(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    storylet_definition: Mapping[str, Any],
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
    caller_eligibility_evidence: Mapping[str, Any] | None = None,
) -> StoryletEligibilityReference:
    """Replay-admit world truth, then derive non-canonical Storylet eligibility."""
    if caller_eligibility_evidence is not None:
        raise ValueError("I8C_CALLER_AUTHORED_ELIGIBILITY_EVIDENCE_FORBIDDEN")
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8C_BASELINE_AND_WORLD_REQUIRED")
    if not world.is_live:
        raise ValueError("I8C_SOURCE_WORLD_MUST_BE_LIVE_READ_ONLY")
    export_solo_replay_package(baseline, world)
    return _build_from_replay_validated_world(
        world=world,
        storylet_definition=storylet_definition,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )


def export_storylet_eligibility_package(
    *,
    baseline: WorldBaseline,
    world: WorldState,
    storylet_definition: Mapping[str, Any],
    player_actor_id: str,
    promise_recipient_npc_id: str,
    candidate_npc_id: str,
    target_object_id: str,
    source_speech_event_id: str,
) -> bytes:
    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("I8C_BASELINE_AND_WORLD_REQUIRED")
    solo_package = export_solo_replay_package(baseline, world)
    storylet = _validate_storylet_definition(storylet_definition)
    reference = _build_from_replay_validated_world(
        world=world,
        storylet_definition=storylet,
        player_actor_id=player_actor_id,
        promise_recipient_npc_id=promise_recipient_npc_id,
        candidate_npc_id=candidate_npc_id,
        target_object_id=target_object_id,
        source_speech_event_id=source_speech_event_id,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "storylet_definition": storylet,
        "player_actor_id": player_actor_id,
        "promise_recipient_npc_id": promise_recipient_npc_id,
        "candidate_npc_id": candidate_npc_id,
        "target_object_id": target_object_id,
        "source_speech_event_id": source_speech_event_id,
        "source_i1_replay_sha256": hashlib.sha256(solo_package).hexdigest(),
        "source_i1_replay_b64": base64.b64encode(solo_package).decode("ascii"),
        "expected_reference": _reference_material(reference),
    }
    return _canonical_json({"payload": payload, "sha256": _sha256(payload)}).encode(
        "utf-8"
    )


def replay_storylet_eligibility_package(
    package: bytes | bytearray | memoryview,
) -> StoryletEligibilityReference:
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8C_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8C_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8C_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I8C_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8C_REPLAY_PACKAGE_TAMPERED")
    replay_b64 = _require_string(
        payload.get("source_i1_replay_b64"), "I8C_I1_REPLAY_REQUIRED"
    )
    try:
        solo_package = base64.b64decode(replay_b64.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8C_I1_REPLAY_ENCODING_INVALID") from None
    if hashlib.sha256(solo_package).hexdigest() != payload.get(
        "source_i1_replay_sha256"
    ):
        raise ValueError("I8C_I1_REPLAY_DIGEST_MISMATCH")
    evidence = import_solo_replay_package(solo_package)
    world = rehydrate_solo_replay_package(solo_package)
    rebuilt = _build_from_replay_validated_world(
        world=world,
        storylet_definition=payload.get("storylet_definition"),
        player_actor_id=payload.get("player_actor_id"),
        promise_recipient_npc_id=payload.get("promise_recipient_npc_id"),
        candidate_npc_id=payload.get("candidate_npc_id"),
        target_object_id=payload.get("target_object_id"),
        source_speech_event_id=payload.get("source_speech_event_id"),
    )
    if (
        rebuilt.source_world_id != evidence.world_id
        or rebuilt.source_baseline_version != evidence.baseline_version
    ):
        raise ValueError("I8C_REPLAY_I1_SOURCE_BINDING_MISMATCH")
    if _reference_material(rebuilt) != payload.get("expected_reference"):
        raise ValueError("I8C_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH")
    return rebuilt
