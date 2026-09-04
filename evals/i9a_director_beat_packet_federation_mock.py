"""Current-AF-H I9A DirectorBeatPacket reference adapter.

This eval-only adapter preserves the accepted pre-DPI replay, asset, presentation,
and staging validation helpers in ``i9a_legacy_pre_dpi_reference`` while rebinding
the packet to the current canonical AF-H interface. It does not implement a
WorldInstance runtime, DramaticPresentationIntent runtime, provider, renderer, or
production transport. Serialized bytes remain evidence only and never become
canonical authority.
"""
from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import Any

from awrse.model import freeze_value, thaw_value
import evals.i9a_legacy_pre_dpi_reference as _legacy

I9A_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_PROVIDER_INTEGRATION = True
NO_NETWORK_INTEGRATION = True
NO_REAL_RENDERER_IMPLEMENTED = True
NO_WORLD_MUTATION = True
NO_KNOWLEDGE_MUTATION = True
NO_BRANCH_QUALITY_AUTHORITY = True
NO_PX_AUTHORITY = True
NO_LIVE_AI_FILM_REPOSITORY_WRITE = True
NO_WORLD_INSTANCE_RUNTIME_AUTHORITY = True
NO_DPI_RUNTIME_AUTHORITY = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_AF_D_MANIFEST_PATH = _ROOT / "registries" / "AF001-AF-D-REFERENCE-INSTANCES.json"

_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.10.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1",
)
_EXPECTED_PACKET_TYPE = (
    "AF001.DIRECTOR-BEAT-PACKET",
    "1.0.0-candidate",
    "AWRSE_DIRECTOR_HANDOFF",
)
_EXPECTED_PACKET_FIELDS = {
    "beat_id",
    "world_instance_id",
    "world_state_version",
    "confirmed_event_refs",
    "scene_view_asset_refs",
    "player_visible_knowledge_refs",
    "public_visible_knowledge_refs",
    "private_forbidden_knowledge_refs",
    "actor_presentation_requirements",
    "dramatic_presentation_intent_ref",
    "presentation_goal",
    "forbidden_inventions",
    "contract_version",
}
_EXPECTED_PRESENTATION_TYPE = _legacy._EXPECTED_PRESENTATION_TYPE
_EXPECTED_PRESENTATION_FIELDS = _legacy._EXPECTED_PRESENTATION_FIELDS
_EXPECTED_DIRECTOR_MUTATION_CONSTRAINT = _legacy._EXPECTED_DIRECTOR_MUTATION_CONSTRAINT
_EXPECTED_PRESENTATION_MUTATION_CONSTRAINT = _legacy._EXPECTED_PRESENTATION_MUTATION_CONSTRAINT
_EXPECTED_DPI_TYPE = (
    "AF001.DramaticPresentationIntent",
    "1.0.0-candidate",
    "AF-H",
    "AWRSE_DIRECTOR_HANDOFF_EXTENSION",
    "INTERFACE_ONLY_NOT_RUNTIME_IMPLEMENTED",
)
_EXPECTED_DPI_FIELDS = {
    "intent_id",
    "parent_director_beat_packet_ref",
    "world_instance_id",
    "world_state_version",
    "confirmed_event_refs",
    "confirmed_event_set_digest",
    "causal_emphasis_refs",
    "emotional_objective",
    "reveal_timing_bounds",
    "continuity_refs",
    "allowed_information_refs",
    "forbidden_inventions",
}
_EXPECTED_DPI_BINDING = {
    "binding_id": "AF001-MIDS-DPI-TO-DIRECTOR-BEAT-PACKET-001",
    "binding_version": "1.0.0-candidate",
    "parent_type_ref": "DIRECTOR-BEAT-PACKET",
    "extension_type_ref": "DramaticPresentationIntent",
    "parent_reference_field": "DIRECTOR-BEAT-PACKET.dramatic_presentation_intent_ref",
    "extension_back_reference_field": "DramaticPresentationIntent.parent_director_beat_packet_ref",
    "authority_rule": "EXTENSION_REFINES_PRESENTATION_INTENT_ONLY; PARENT_REMAINS_THE_SINGLE_AWRSE_DIRECTOR_HANDOFF_BOUNDARY; EXTENSION_HAS_NO_WORLD_EVENT_KNOWLEDGE_DIRECTOR_OR_RENDER_AUTHORITY",
    "runtime_implementation_authorized": False,
}
_EXPECTED_DPI_CORRELATION_RULES = (
    "PARENT_REFERENCE_AND_EXTENSION_BACK_REFERENCE_MUST_BE_BIDIRECTIONALLY_EQUAL",
    "DramaticPresentationIntent.world_instance_id_MUST_EQUAL_DIRECTOR-BEAT-PACKET.world_instance_id",
    "DramaticPresentationIntent.world_state_version_MUST_EQUAL_DIRECTOR-BEAT-PACKET.world_state_version",
    "DramaticPresentationIntent.confirmed_event_refs_MUST_EQUAL_DIRECTOR-BEAT-PACKET.confirmed_event_refs_AS_AN_ORDERED_SET",
    "DramaticPresentationIntent.confirmed_event_set_digest_MUST_BIND_THE_EXACT_CONFIRMED_EVENT_REFS",
    "CAUSAL_EMPHASIS_REFS_MUST_BE_A_SUBSET_OF_CONFIRMED_EVENT_REFS",
    "ALLOWED_INFORMATION_REFS_MUST_NOT_EXCEED_PARENT_PLAYER_OR_PUBLIC_VISIBLE_KNOWLEDGE_REFS",
    "ORPHAN_DUPLICATE_WORLD_MISMATCH_STALE_CURSOR_EVENT_MISMATCH_OR_INFORMATION_SUPERSET_FAILS_CLOSED",
)
_EXPECTED_PACKET_AUTHORITY = "NON_CANONICAL_I9A_DIRECTOR_BEAT_PACKET_REFERENCE_ONLY"
_EXPECTED_DPI_AUTHORITY = "NON_CANONICAL_I9A_DPI_INTERFACE_EVIDENCE_ONLY"
_EXPECTED_MOCK_AUTHORITY = "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"

NON_CANONICAL_MOCK_STAGING_VARIANTS = _legacy.NON_CANONICAL_MOCK_STAGING_VARIANTS
_ALLOWED_STAGING_KEYS = frozenset(NON_CANONICAL_MOCK_STAGING_VARIANTS)
_MANDATORY_AF_H_FORBIDDEN = _legacy._MANDATORY_AF_H_FORBIDDEN

# Mechanical helper reuse only. These helpers do not grant the legacy packet schema
# any authority over the current adapter.
_canonical_json = _legacy._canonical_json
_sha256_json = _legacy._sha256_json
_sha256_bytes = _legacy._sha256_bytes
_require_string = _legacy._require_string
_strict_json_from_bytes = _legacy._strict_json_from_bytes
_strict_json_from_text = _legacy._strict_json_from_text
_load_json_file = _legacy._load_json_file
_decode_i8c_sources = _legacy._decode_i8c_sources
_ordered_confirmed_event_refs = _legacy._ordered_confirmed_event_refs
_scene_view_material = _legacy._scene_view_material
_presentation_requirements = _legacy._presentation_requirements
_coverage_gaps = _legacy._coverage_gaps
_beat_id = _legacy._beat_id
_normalize_staging = _legacy._normalize_staging
MockAIFilmReceipt = _legacy.MockAIFilmReceipt


def _load_af_h_authority() -> tuple[str, str, str]:
    contract = _load_json_file(_CONTRACT_PATH, "I9A_CANONICAL_CONTRACT_UNAVAILABLE")
    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I9A_CANONICAL_PARENT_DRIFT")

    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I9A_TYPE_REGISTRY_MISSING")
    packet = registry.get("DIRECTOR-BEAT-PACKET")
    presentation = registry.get("ActorPresentationRequirements")
    dpi = registry.get("DramaticPresentationIntent")
    if not isinstance(packet, Mapping):
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_TYPE_MISSING")
    if not isinstance(presentation, Mapping):
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_TYPE_MISSING")
    if not isinstance(dpi, Mapping):
        raise ValueError("I9A_DPI_TYPE_MISSING")

    if (
        packet.get("type_id"), packet.get("version"), packet.get("authority_profile_ref")
    ) != _EXPECTED_PACKET_TYPE:
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_TYPE_DRIFT")
    if set(packet.get("fields", ())) != _EXPECTED_PACKET_FIELDS:
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_FIELDS_DRIFT")
    if (
        presentation.get("type_id"),
        presentation.get("version"),
        presentation.get("authority_profile_ref"),
    ) != _EXPECTED_PRESENTATION_TYPE:
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_TYPE_DRIFT")
    if set(presentation.get("fields", ())) != _EXPECTED_PRESENTATION_FIELDS:
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_FIELDS_DRIFT")
    if (
        dpi.get("type_id"),
        dpi.get("version"),
        dpi.get("domain"),
        dpi.get("authority_profile_ref"),
        dpi.get("implementation_state"),
    ) != _EXPECTED_DPI_TYPE:
        raise ValueError("I9A_DPI_TYPE_DRIFT")
    if set(dpi.get("fields", ())) != _EXPECTED_DPI_FIELDS:
        raise ValueError("I9A_DPI_FIELDS_DRIFT")

    binding = contract.get("director_handoff_extension_binding")
    if not isinstance(binding, Mapping):
        raise ValueError("I9A_DPI_BINDING_MISSING")
    for key, expected in _EXPECTED_DPI_BINDING.items():
        if binding.get(key) != expected:
            raise ValueError(f"I9A_DPI_BINDING_DRIFT:{key}")
    if tuple(binding.get("correlation_rules", ())) != _EXPECTED_DPI_CORRELATION_RULES:
        raise ValueError("I9A_DPI_CORRELATION_RULES_DRIFT")

    profiles = contract.get("authority_semantics", {}).get("profiles")
    if not isinstance(profiles, Mapping):
        raise ValueError("I9A_AUTHORITY_PROFILES_MISSING")
    director = profiles.get("AWRSE_DIRECTOR_HANDOFF")
    presentation_profile = profiles.get("AWRSE_PRESENTATION_REQUIREMENTS")
    if not isinstance(director, Mapping) or not isinstance(presentation_profile, Mapping):
        raise ValueError("I9A_AF_H_AUTHORITY_PROFILE_MISSING")
    if director.get("staging_authority") != ["AI_DIRECTOR"]:
        raise ValueError("I9A_DIRECTOR_STAGING_AUTHORITY_DRIFT")
    if director.get("mutation_constraint") != _EXPECTED_DIRECTOR_MUTATION_CONSTRAINT:
        raise ValueError("I9A_DIRECTOR_MUTATION_CONSTRAINT_DRIFT")
    if presentation_profile.get("staging_authority") != ["NONE"]:
        raise ValueError("I9A_PRESENTATION_STAGING_AUTHORITY_DRIFT")
    if presentation_profile.get("mutation_constraint") != _EXPECTED_PRESENTATION_MUTATION_CONSTRAINT:
        raise ValueError("I9A_PRESENTATION_MUTATION_CONSTRAINT_DRIFT")
    return parent


def _load_af_d_manifest() -> Mapping[str, Any]:
    manifest = _load_json_file(_AF_D_MANIFEST_PATH, "I9A_AF_D_MANIFEST_UNAVAILABLE")
    parent = manifest.get("parent_machine_contract")
    if not isinstance(parent, Mapping):
        raise ValueError("I9A_AF_D_MANIFEST_PARENT_MISSING")
    if (
        parent.get("contract_id"),
        parent.get("contract_version"),
        parent.get("authority_graph_version"),
    ) != _EXPECTED_PARENT:
        raise ValueError("I9A_AF_D_MANIFEST_PARENT_DRIFT")
    return manifest


@dataclass(frozen=True)
class DramaticPresentationIntentReference:
    intent_id: str
    parent_director_beat_packet_ref: str
    world_instance_id: str
    world_state_version: str
    confirmed_event_refs: tuple[str, ...]
    confirmed_event_set_digest: str
    causal_emphasis_refs: tuple[str, ...]
    emotional_objective: str
    reveal_timing_bounds: tuple[str, ...]
    continuity_refs: tuple[str, ...]
    allowed_information_refs: tuple[str, ...]
    forbidden_inventions: tuple[str, ...]
    authority_class: str


@dataclass(frozen=True)
class DirectorBeatPacketReference:
    beat_id: str
    world_instance_id: str
    world_state_version: str
    confirmed_event_refs: tuple[str, ...]
    scene_view_asset_refs: Mapping[str, Any]
    player_visible_knowledge_refs: tuple[str, ...]
    public_visible_knowledge_refs: tuple[str, ...]
    private_forbidden_knowledge_refs: tuple[str, ...]
    actor_presentation_requirements: tuple[Mapping[str, Any], ...]
    dramatic_presentation_intent_ref: str
    presentation_goal: str
    forbidden_inventions: tuple[str, ...]
    contract_version: str
    packet_type_version: str
    source_i8c_sha256: str
    source_i3a_sha256: str
    source_world_id: str
    source_baseline_version: str
    source_state_version: int
    source_i1_event_sequence_digest: str
    source_storylet_sha256: str
    coverage_gaps: tuple[str, ...]
    dramatic_presentation_intent: DramaticPresentationIntentReference
    authority_class: str


def _parent_packet_ref(beat_id: str) -> str:
    return f"DIRECTOR-BEAT-PACKET:{_require_string(beat_id, 'I9A_BEAT_ID_REQUIRED')}"


def _confirmed_event_set_digest(refs: Sequence[str]) -> str:
    normalized = tuple(_require_string(ref, "I9A_DPI_EVENT_REF_INVALID") for ref in refs)
    if len(set(normalized)) != len(normalized):
        raise ValueError("I9A_DPI_CONFIRMED_EVENT_REFS_DUPLICATE")
    return _sha256_json(list(normalized))


def _dpi_intent_id(beat_id: str, event_set_digest: str) -> str:
    digest = _require_string(event_set_digest, "I9A_DPI_EVENT_SET_DIGEST_REQUIRED")
    return f"DPI:{beat_id}:{digest[:32]}"


def _dpi_material(dpi: DramaticPresentationIntentReference) -> dict[str, Any]:
    material = {
        "intent_id": dpi.intent_id,
        "parent_director_beat_packet_ref": dpi.parent_director_beat_packet_ref,
        "world_instance_id": dpi.world_instance_id,
        "world_state_version": dpi.world_state_version,
        "confirmed_event_refs": list(dpi.confirmed_event_refs),
        "confirmed_event_set_digest": dpi.confirmed_event_set_digest,
        "causal_emphasis_refs": list(dpi.causal_emphasis_refs),
        "emotional_objective": dpi.emotional_objective,
        "reveal_timing_bounds": list(dpi.reveal_timing_bounds),
        "continuity_refs": list(dpi.continuity_refs),
        "allowed_information_refs": list(dpi.allowed_information_refs),
        "forbidden_inventions": list(dpi.forbidden_inventions),
    }
    if set(material) != _EXPECTED_DPI_FIELDS:
        raise ValueError("I9A_INTERNAL_DPI_FIELD_SHAPE_DRIFT")
    return material


def _validate_dpi_correlation(packet: DirectorBeatPacketReference) -> None:
    dpi = packet.dramatic_presentation_intent
    if packet.world_instance_id != packet.source_world_id:
        raise ValueError("I9A_WORLD_INSTANCE_REFERENCE_SOURCE_MISMATCH")
    if packet.dramatic_presentation_intent_ref != dpi.intent_id:
        raise ValueError("I9A_DPI_PARENT_REFERENCE_MISMATCH")
    if dpi.parent_director_beat_packet_ref != _parent_packet_ref(packet.beat_id):
        raise ValueError("I9A_DPI_BACK_REFERENCE_MISMATCH")
    if dpi.world_instance_id != packet.world_instance_id:
        raise ValueError("I9A_DPI_WORLD_INSTANCE_MISMATCH")
    if dpi.world_state_version != packet.world_state_version:
        raise ValueError("I9A_DPI_WORLD_STATE_VERSION_MISMATCH")
    if dpi.confirmed_event_refs != packet.confirmed_event_refs:
        raise ValueError("I9A_DPI_CONFIRMED_EVENT_REFS_MISMATCH")
    if dpi.confirmed_event_set_digest != _confirmed_event_set_digest(packet.confirmed_event_refs):
        raise ValueError("I9A_DPI_CONFIRMED_EVENT_SET_DIGEST_MISMATCH")
    if not set(dpi.causal_emphasis_refs) <= set(packet.confirmed_event_refs):
        raise ValueError("I9A_DPI_CAUSAL_EMPHASIS_OUTSIDE_CONFIRMED_EVENTS")
    allowed_parent = set(packet.player_visible_knowledge_refs) | set(packet.public_visible_knowledge_refs)
    if not set(dpi.allowed_information_refs) <= allowed_parent:
        raise ValueError("I9A_DPI_ALLOWED_INFORMATION_SUPERSET")


def _frozen_packet_material(packet: DirectorBeatPacketReference) -> dict[str, Any]:
    _validate_dpi_correlation(packet)
    material = {
        "beat_id": packet.beat_id,
        "world_instance_id": packet.world_instance_id,
        "world_state_version": packet.world_state_version,
        "confirmed_event_refs": list(packet.confirmed_event_refs),
        "scene_view_asset_refs": thaw_value(packet.scene_view_asset_refs),
        "player_visible_knowledge_refs": list(packet.player_visible_knowledge_refs),
        "public_visible_knowledge_refs": list(packet.public_visible_knowledge_refs),
        "private_forbidden_knowledge_refs": list(packet.private_forbidden_knowledge_refs),
        "actor_presentation_requirements": [thaw_value(item) for item in packet.actor_presentation_requirements],
        "dramatic_presentation_intent_ref": packet.dramatic_presentation_intent_ref,
        "presentation_goal": packet.presentation_goal,
        "forbidden_inventions": list(packet.forbidden_inventions),
        "contract_version": packet.contract_version,
    }
    if set(material) != _EXPECTED_PACKET_FIELDS:
        raise ValueError("I9A_INTERNAL_PACKET_FIELD_SHAPE_DRIFT")
    return material


def _reference_material(packet: DirectorBeatPacketReference) -> dict[str, Any]:
    _validate_dpi_correlation(packet)
    return {
        "packet": _frozen_packet_material(packet),
        "dramatic_presentation_intent": _dpi_material(packet.dramatic_presentation_intent),
        "dpi_authority_class": packet.dramatic_presentation_intent.authority_class,
        "packet_type_version": packet.packet_type_version,
        "source_i8c_sha256": packet.source_i8c_sha256,
        "source_i3a_sha256": packet.source_i3a_sha256,
        "source_world_id": packet.source_world_id,
        "source_baseline_version": packet.source_baseline_version,
        "source_state_version": packet.source_state_version,
        "source_i1_event_sequence_digest": packet.source_i1_event_sequence_digest,
        "source_storylet_sha256": packet.source_storylet_sha256,
        "coverage_gaps": list(packet.coverage_gaps),
        "authority_class": packet.authority_class,
    }


def packet_sha256(packet: DirectorBeatPacketReference) -> str:
    return _sha256_json(_reference_material(packet))


def protected_material_sha256(packet: DirectorBeatPacketReference) -> str:
    material = _frozen_packet_material(packet)
    protected_packet = {
        key: material[key]
        for key in (
            "world_instance_id",
            "world_state_version",
            "confirmed_event_refs",
            "scene_view_asset_refs",
            "player_visible_knowledge_refs",
            "public_visible_knowledge_refs",
            "private_forbidden_knowledge_refs",
            "actor_presentation_requirements",
            "dramatic_presentation_intent_ref",
            "presentation_goal",
            "forbidden_inventions",
            "contract_version",
        )
    }
    return _sha256_json({
        "packet": protected_packet,
        "dramatic_presentation_intent": _dpi_material(packet.dramatic_presentation_intent),
    })


def build_director_beat_packet_reference(
    *,
    i8c_replay_package: bytes | bytearray | memoryview,
    i3a_replay_package_json: str,
) -> DirectorBeatPacketReference | None:
    parent = _load_af_h_authority()
    manifest = _load_af_d_manifest()
    if not isinstance(i8c_replay_package, (bytes, bytearray, memoryview)):
        raise TypeError("I9A_I8C_REPLAY_PACKAGE_BYTES_REQUIRED")
    i8c_bytes = bytes(i8c_replay_package)

    storylet_reference = _legacy.replay_storylet_eligibility_package(i8c_bytes)
    i8c_payload, i1_evidence, world = _decode_i8c_sources(i8c_bytes)
    if storylet_reference.outcome == "NO_VALID_STORYLET":
        return None
    if storylet_reference.outcome != "STORYLET_ELIGIBLE":
        raise ValueError("I9A_I8C_OUTCOME_UNSUPPORTED")
    if (
        storylet_reference.source_world_id != world.world_id
        or storylet_reference.source_baseline_version != world.baseline_version
        or storylet_reference.source_state_version != world.state_version
    ):
        raise ValueError("I9A_I8C_WORLD_BINDING_MISMATCH")
    expected_world_version = f"{storylet_reference.source_baseline_version}:{storylet_reference.source_state_version}"
    if world.world_state_version != expected_world_version:
        raise ValueError("I9A_WORLD_STATE_VERSION_MISMATCH")

    _strict_json_from_text(i3a_replay_package_json, "I9A_I3A_REPLAY_PACKAGE_JSON_INVALID")
    presentation = _legacy.replay_i3a_package(i3a_replay_package_json)
    if presentation.contract_version != parent[1]:
        raise ValueError("I9A_I3A_PARENT_VERSION_DRIFT")
    if presentation.actor_id not in world.actors:
        raise ValueError("I9A_PRESENTATION_ACTOR_ABSENT_FROM_SOURCE_WORLD")

    storylet = i8c_payload.get("storylet_definition")
    if not isinstance(storylet, Mapping):
        raise ValueError("I9A_STORYLET_DEFINITION_MISSING")
    if storylet.get("storylet_id") != storylet_reference.storylet_id:
        raise ValueError("I9A_STORYLET_ID_REPLAY_MISMATCH")

    confirmed_event_refs = _ordered_confirmed_event_refs(world, storylet)
    scene_view_asset_refs = _scene_view_material(world=world, presentation=presentation, manifest=manifest)
    actor_requirements = _presentation_requirements(world=world, presentation=presentation)
    authored_forbidden = tuple(
        _require_string(value, "I9A_FORBIDDEN_INVENTION_INVALID")
        for value in storylet.get("forbidden_contradictions", ())
    )
    forbidden = tuple(dict.fromkeys(authored_forbidden + _MANDATORY_AF_H_FORBIDDEN))
    presentation_goal = _require_string(storylet.get("dramatic_purpose"), "I9A_PRESENTATION_GOAL_REQUIRED")
    beat_id = _beat_id(
        storylet_reference=storylet_reference,
        i1_event_sequence_digest=i1_evidence.event_sequence_digest,
    )
    event_set_digest = _confirmed_event_set_digest(confirmed_event_refs)
    world_instance_id = world.world_id
    dpi = DramaticPresentationIntentReference(
        intent_id=_dpi_intent_id(beat_id, event_set_digest),
        parent_director_beat_packet_ref=_parent_packet_ref(beat_id),
        world_instance_id=world_instance_id,
        world_state_version=world.world_state_version,
        confirmed_event_refs=confirmed_event_refs,
        confirmed_event_set_digest=event_set_digest,
        causal_emphasis_refs=(),
        emotional_objective=presentation_goal,
        reveal_timing_bounds=(),
        continuity_refs=(),
        allowed_information_refs=(),
        forbidden_inventions=forbidden,
        authority_class=_EXPECTED_DPI_AUTHORITY,
    )
    packet = DirectorBeatPacketReference(
        beat_id=beat_id,
        world_instance_id=world_instance_id,
        world_state_version=world.world_state_version,
        confirmed_event_refs=confirmed_event_refs,
        scene_view_asset_refs=scene_view_asset_refs,
        player_visible_knowledge_refs=(),
        public_visible_knowledge_refs=(),
        private_forbidden_knowledge_refs=(),
        actor_presentation_requirements=actor_requirements,
        dramatic_presentation_intent_ref=dpi.intent_id,
        presentation_goal=presentation_goal,
        forbidden_inventions=forbidden,
        contract_version=parent[1],
        packet_type_version=_EXPECTED_PACKET_TYPE[1],
        source_i8c_sha256=_sha256_bytes(i8c_bytes),
        source_i3a_sha256=hashlib.sha256(i3a_replay_package_json.encode("utf-8")).hexdigest(),
        source_world_id=storylet_reference.source_world_id,
        source_baseline_version=storylet_reference.source_baseline_version,
        source_state_version=storylet_reference.source_state_version,
        source_i1_event_sequence_digest=i1_evidence.event_sequence_digest,
        source_storylet_sha256=storylet_reference.authored_storylet_sha256,
        coverage_gaps=_coverage_gaps(presentation),
        dramatic_presentation_intent=dpi,
        authority_class=_EXPECTED_PACKET_AUTHORITY,
    )
    _validate_dpi_correlation(packet)
    return packet


def consume_mock_ai_film_response(
    *,
    i8c_replay_package: bytes | bytearray | memoryview,
    i3a_replay_package_json: str,
    response: Mapping[str, Any],
) -> MockAIFilmReceipt:
    packet = build_director_beat_packet_reference(
        i8c_replay_package=i8c_replay_package,
        i3a_replay_package_json=i3a_replay_package_json,
    )
    if packet is None:
        raise ValueError("I9A_NO_VALID_STORYLET_NO_PACKET")
    if not isinstance(response, Mapping):
        raise ValueError("I9A_AI_FILM_RESPONSE_MAPPING_REQUIRED")
    expected_keys = {"source_packet_sha256", "protected_material_sha256", "staging_metadata"}
    extras = set(response) - expected_keys
    missing = expected_keys - set(response)
    if extras:
        raise ValueError(f"I9A_AI_FILM_PROTECTED_OR_UNKNOWN_FIELD_FORBIDDEN:{sorted(extras)[0]}")
    if missing:
        raise ValueError(f"I9A_AI_FILM_RESPONSE_FIELD_MISSING:{sorted(missing)[0]}")
    source_digest = packet_sha256(packet)
    protected_digest = protected_material_sha256(packet)
    if response.get("source_packet_sha256") != source_digest:
        raise ValueError("I9A_AI_FILM_SOURCE_PACKET_DIGEST_MISMATCH")
    if response.get("protected_material_sha256") != protected_digest:
        raise ValueError("I9A_AI_FILM_PROTECTED_MATERIAL_DIGEST_MISMATCH")
    staging = _normalize_staging(response.get("staging_metadata"))
    return MockAIFilmReceipt(
        status="MOCK_AI_FILM_STAGING_ACCEPTED",
        source_packet_sha256=source_digest,
        beat_id=packet.beat_id,
        world_state_version=packet.world_state_version,
        staging_metadata=staging,
        protected_material_sha256=protected_digest,
        world_mutation_count=0,
        provider_call_count=0,
        authority_class=_EXPECTED_MOCK_AUTHORITY,
    )
