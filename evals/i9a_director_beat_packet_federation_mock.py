"""I9A V0 deterministic AWRSE -> mock AI-Film federation reference.

This is an eval/reference slice only. It replays already-accepted I8C and I3A
evidence, derives the frozen AF-H DirectorBeatPacket fields, and validates a
semantically sterile mock staging response. It never calls a provider, renderer,
network service, or mutates canonical world/knowledge/presentation state.

The mock staging tokens are NON_CANONICAL_MOCK_STAGING_VARIANTS. They exist only
to prove the federation authority boundary and are not an AI-Film production
vocabulary.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse import import_solo_replay_package, rehydrate_solo_replay_package
from awrse.model import freeze_value, thaw_value
from evals.i3a_presentation_reference import replay_package as replay_i3a_package
from evals.i8c_storylet_eligibility_reference import replay_storylet_eligibility_package

I9A_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_PROVIDER_INTEGRATION = True
NO_NETWORK_INTEGRATION = True
NO_REAL_RENDERER_IMPLEMENTED = True
NO_WORLD_MUTATION = True
NO_KNOWLEDGE_MUTATION = True
NO_BRANCH_QUALITY_AUTHORITY = True
NO_PX_AUTHORITY = True
NO_LIVE_AI_FILM_REPOSITORY_WRITE = True

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
    "world_state_version",
    "confirmed_event_refs",
    "scene_view_asset_refs",
    "player_visible_knowledge_refs",
    "public_visible_knowledge_refs",
    "private_forbidden_knowledge_refs",
    "actor_presentation_requirements",
    "presentation_goal",
    "forbidden_inventions",
    "contract_version",
}
_EXPECTED_PRESENTATION_TYPE = (
    "AF001.ActorPresentationRequirements",
    "1.0.0-candidate",
    "AWRSE_PRESENTATION_REQUIREMENTS",
)
_EXPECTED_PRESENTATION_FIELDS = {
    "actor_id",
    "identity_refs",
    "outfit_refs",
    "dressing_refs",
    "visible_condition_cues",
    "visibility_policy",
    "state_version",
}
_EXPECTED_DIRECTOR_MUTATION_CONSTRAINT = (
    "AI_DIRECTOR_MAY_CHOOSE_STAGING_CAMERA_PERFORMANCE_EDIT_AND_SOUND_ONLY_INSIDE_THE_PACKET_ENVELOPE_AND_MAY_NOT_REWRITE_PACKET_FACTS_KNOWLEDGE_VISIBILITY_ACTOR_IDENTITY_OR_PRESENTATION_REQUIREMENTS"
)
_EXPECTED_PRESENTATION_MUTATION_CONSTRAINT = (
    "AI_DIRECTOR_AND_RENDERER_MUST_CONSUME_THE_REQUIREMENTS_AS_CONSTRAINTS_AND_CANNOT_AUTHOR_OR_REWRITE_IDENTITY_OUTFIT_DRESSING_VISIBLE_CONDITION_OR_VISIBILITY_TRUTH"
)
_EXPECTED_PACKET_AUTHORITY = "NON_CANONICAL_I9A_DIRECTOR_BEAT_PACKET_REFERENCE_ONLY"
_EXPECTED_MOCK_AUTHORITY = "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"

_ALLOWED_VISIBILITY_POLICY_TOKENS = {
    "MUST_RENDER_IF_VISIBLE_IN_SHOT",
    "MUST_NOT_CONTRADICT",
    "HIDDEN_BY_CLOTHING",
    "PRESENTATION_OPTIONAL",
}
NON_CANONICAL_MOCK_STAGING_VARIANTS = {
    "camera_intent": frozenset({"MOCK_CAMERA_A", "MOCK_CAMERA_B"}),
    "performance_intent": frozenset({"MOCK_PERFORMANCE_A", "MOCK_PERFORMANCE_B"}),
    "edit_intent": frozenset({"MOCK_EDIT_A", "MOCK_EDIT_B"}),
    "sound_intent": frozenset({"MOCK_SOUND_A", "MOCK_SOUND_B"}),
}
_ALLOWED_STAGING_KEYS = frozenset(NON_CANONICAL_MOCK_STAGING_VARIANTS)

_MANDATORY_AF_H_FORBIDDEN = (
    "AF_H_NO_WORLD_OR_EVENT_OUTCOME_REWRITE",
    "AF_H_NO_KNOWLEDGE_VISIBILITY_REWRITE",
    "AF_H_NO_ACTOR_IDENTITY_REWRITE",
    "AF_H_NO_PRESENTATION_TRUTH_REWRITE",
)
_GAP_MISSING_VISIBLE_IDENTITY = "MISSING_CANONICAL_VISIBLE_IDENTITY_REF"
_GAP_SURFACE_NOT_EXPRESSIBLE = (
    "SURFACE_STATE_PRESENT_UPSTREAM_BUT_NOT_EXPRESSIBLE_IN_FROZEN_PACKET_V0"
)
_GAP_NO_VISIBLE_CUE_ASSEMBLER = (
    "NO_FUNCTIONAL_TO_VISIBLE_CONDITION_CUE_ASSEMBLER_IN_I9A_V0"
)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I9A_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I9A_JSON_NONFINITE:{value}")


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
        raise ValueError("I9A_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256_json(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _strict_json_from_bytes(value: bytes, code: str) -> Mapping[str, Any]:
    try:
        parsed = json.loads(
            value.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(code) from None
    if not isinstance(parsed, Mapping):
        raise ValueError(code)
    return parsed


def _strict_json_from_text(value: str, code: str) -> Mapping[str, Any]:
    if not isinstance(value, str):
        raise TypeError(code)
    try:
        parsed = json.loads(
            value,
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except json.JSONDecodeError:
        raise ValueError(code) from None
    if not isinstance(parsed, Mapping):
        raise ValueError(code)
    return parsed


def _load_json_file(path: Path, code: str) -> Mapping[str, Any]:
    try:
        parsed = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (OSError, json.JSONDecodeError):
        raise ValueError(code) from None
    if not isinstance(parsed, Mapping):
        raise ValueError(code)
    return parsed


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
    if not isinstance(packet, Mapping):
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_TYPE_MISSING")
    if not isinstance(presentation, Mapping):
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_TYPE_MISSING")

    if (
        packet.get("type_id"),
        packet.get("version"),
        packet.get("authority_profile_ref"),
    ) != _EXPECTED_PACKET_TYPE:
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_TYPE_DRIFT")
    if set(packet.get("fields", [])) != _EXPECTED_PACKET_FIELDS:
        raise ValueError("I9A_DIRECTOR_BEAT_PACKET_FIELDS_DRIFT")
    if (
        presentation.get("type_id"),
        presentation.get("version"),
        presentation.get("authority_profile_ref"),
    ) != _EXPECTED_PRESENTATION_TYPE:
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_TYPE_DRIFT")
    if set(presentation.get("fields", [])) != _EXPECTED_PRESENTATION_FIELDS:
        raise ValueError("I9A_PRESENTATION_REQUIREMENTS_FIELDS_DRIFT")

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
    if (
        presentation_profile.get("mutation_constraint")
        != _EXPECTED_PRESENTATION_MUTATION_CONSTRAINT
    ):
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
class DirectorBeatPacketReference:
    beat_id: str
    world_state_version: str
    confirmed_event_refs: tuple[str, ...]
    scene_view_asset_refs: Mapping[str, Any]
    player_visible_knowledge_refs: tuple[str, ...]
    public_visible_knowledge_refs: tuple[str, ...]
    private_forbidden_knowledge_refs: tuple[str, ...]
    actor_presentation_requirements: tuple[Mapping[str, Any], ...]
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
    authority_class: str


@dataclass(frozen=True)
class MockAIFilmReceipt:
    status: str
    source_packet_sha256: str
    beat_id: str
    world_state_version: str
    staging_metadata: Mapping[str, str]
    protected_material_sha256: str
    world_mutation_count: int
    provider_call_count: int
    authority_class: str


def _frozen_packet_material(packet: DirectorBeatPacketReference) -> dict[str, Any]:
    material = {
        "beat_id": packet.beat_id,
        "world_state_version": packet.world_state_version,
        "confirmed_event_refs": list(packet.confirmed_event_refs),
        "scene_view_asset_refs": thaw_value(packet.scene_view_asset_refs),
        "player_visible_knowledge_refs": list(packet.player_visible_knowledge_refs),
        "public_visible_knowledge_refs": list(packet.public_visible_knowledge_refs),
        "private_forbidden_knowledge_refs": list(packet.private_forbidden_knowledge_refs),
        "actor_presentation_requirements": [
            thaw_value(item) for item in packet.actor_presentation_requirements
        ],
        "presentation_goal": packet.presentation_goal,
        "forbidden_inventions": list(packet.forbidden_inventions),
        "contract_version": packet.contract_version,
    }
    if set(material) != _EXPECTED_PACKET_FIELDS:
        raise ValueError("I9A_INTERNAL_PACKET_FIELD_SHAPE_DRIFT")
    return material


def _reference_material(packet: DirectorBeatPacketReference) -> dict[str, Any]:
    return {
        "packet": _frozen_packet_material(packet),
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
    protected = {
        key: material[key]
        for key in (
            "world_state_version",
            "confirmed_event_refs",
            "scene_view_asset_refs",
            "player_visible_knowledge_refs",
            "public_visible_knowledge_refs",
            "private_forbidden_knowledge_refs",
            "actor_presentation_requirements",
            "presentation_goal",
            "forbidden_inventions",
            "contract_version",
        )
    }
    return _sha256_json(protected)


def _decode_i8c_sources(package: bytes) -> tuple[Mapping[str, Any], Any, Any]:
    envelope = _strict_json_from_bytes(package, "I9A_I8C_PACKAGE_JSON_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("I9A_I8C_PAYLOAD_INVALID")
    encoded = _require_string(
        payload.get("source_i1_replay_b64"), "I9A_I1_REPLAY_REQUIRED"
    )
    try:
        solo_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I9A_I1_REPLAY_ENCODING_INVALID") from None
    if _sha256_bytes(solo_package) != payload.get("source_i1_replay_sha256"):
        raise ValueError("I9A_I1_REPLAY_DIGEST_MISMATCH")
    evidence = import_solo_replay_package(solo_package)
    world = rehydrate_solo_replay_package(solo_package)
    if (
        world.world_id != evidence.world_id
        or world.baseline_version != evidence.baseline_version
        or world.state_version != evidence.expected_state_version
    ):
        raise ValueError("I9A_I1_REPLAY_SOURCE_BINDING_MISMATCH")
    return payload, evidence, world


def _ordered_confirmed_event_refs(
    world: Any, storylet: Mapping[str, Any]
) -> tuple[str, ...]:
    required: list[str] = []
    for row in storylet.get("preconditions", []):
        if isinstance(row, Mapping) and row.get("kind") == "WORLD_EVENT_PRESENT":
            required.append(
                _require_string(row.get("event_id"), "I9A_WORLD_EVENT_REF_REQUIRED")
            )
    for row in storylet.get("knowledge_constraints", []):
        if isinstance(row, Mapping) and row.get("kind") == "CALLBACK_REQUIRED_FACTS_EXACT":
            refs = row.get("fact_refs")
            if isinstance(refs, (str, bytes, bytearray)) or not isinstance(
                refs, Sequence
            ):
                raise ValueError("I9A_CALLBACK_FACT_REFS_INVALID")
            required.extend(
                _require_string(ref, "I9A_CALLBACK_FACT_REF_INVALID") for ref in refs
            )

    required_set = set(required)
    if not required_set:
        raise ValueError("I9A_CONFIRMED_EVENT_REFS_REQUIRED")
    if not required_set <= set(world.committed_event_ids):
        raise ValueError("I9A_CONFIRMED_EVENT_NOT_COMMITTED_IN_SOURCE_WORLD")
    ordered = tuple(
        event.event_id for event in world.event_log if event.event_id in required_set
    )
    if set(ordered) != required_set or len(ordered) != len(required_set):
        raise ValueError("I9A_CONFIRMED_EVENT_ORDER_REBUILD_FAILED")
    return ordered


def _scene_view_material(
    *, world: Any, presentation: Any, manifest: Mapping[str, Any]
) -> Mapping[str, Any]:
    scene = world.scenes.get(world.active_scene_id)
    if scene is None:
        raise ValueError("I9A_ACTIVE_SCENE_MISSING")

    views = {
        row.get("view_id"): row
        for row in manifest.get("views", [])
        if isinstance(row, Mapping) and isinstance(row.get("view_id"), str)
    }
    view = views.get(presentation.view_id)
    if not isinstance(view, Mapping):
        raise ValueError("I9A_VIEW_NOT_IN_CANONICAL_AF_D_MANIFEST")
    if view.get("scene_id") != world.active_scene_id:
        raise ValueError("I9A_SCENE_VIEW_MISMATCH")
    if (
        presentation.identity_manifest_id != manifest.get("manifest_id")
        or presentation.identity_manifest_version != manifest.get("manifest_version")
    ):
        raise ValueError("I9A_AF_D_PRESENTATION_MANIFEST_BINDING_MISMATCH")

    asset_rows = {
        row.get("media_asset_id"): row
        for row in manifest.get("media_assets", [])
        if isinstance(row, Mapping) and isinstance(row.get("media_asset_id"), str)
    }
    base_asset_refs = tuple(
        _require_string(raw, "I9A_SCENE_BASE_ASSET_REF_INVALID")
        for raw in scene.base_asset_refs
    )
    if not base_asset_refs:
        raise ValueError("I9A_SCENE_BASE_ASSET_REFS_REQUIRED")
    if len(set(base_asset_refs)) != len(base_asset_refs):
        raise ValueError("I9A_SCENE_BASE_ASSET_REFS_DUPLICATE")

    for asset_id in base_asset_refs:
        asset = asset_rows.get(asset_id)
        if not isinstance(asset, Mapping):
            raise ValueError("I9A_SCENE_ASSET_NOT_IN_CANONICAL_AF_D_MANIFEST")
        bound_view = asset.get("view_ref_optional")
        if bound_view is not None and bound_view != presentation.view_id:
            raise ValueError("I9A_SCENE_ASSET_VIEW_MISMATCH")

    # Frozen scene truth stays at logical View + MediaAsset identity. I3A's
    # MediaVersion/Locator admission remains source provenance only.
    return freeze_value(
        {
            "scene_id": world.active_scene_id,
            "view_id": presentation.view_id,
            "base_media_asset_refs": base_asset_refs,
        }
    )


def _require_presentation_world_object(
    *,
    world: Any,
    object_ref: Any,
    actor_id: str,
    missing_code: str,
    require_actor_possession: bool,
) -> str:
    ref = _require_string(object_ref, missing_code)
    obj = world.objects.get(ref)
    if obj is None:
        raise ValueError(f"{missing_code}:{ref}")
    if obj.scene_id != world.active_scene_id:
        raise ValueError(f"I9A_PRESENTATION_WORLD_OBJECT_SCENE_MISMATCH:{ref}")
    if require_actor_possession:
        actor = world.actors.get(actor_id)
        if actor is None:
            raise ValueError("I9A_PRESENTATION_ACTOR_ABSENT_FROM_SOURCE_WORLD")
        if ref not in set(actor.inventory_refs):
            raise ValueError(f"I9A_PRESENTATION_OBJECT_NOT_IN_ACTOR_INVENTORY:{ref}")
        if obj.owner_actor_id != actor_id:
            raise ValueError(f"I9A_PRESENTATION_OBJECT_OWNER_MISMATCH:{ref}")
    return ref


def _require_surface_target_in_world(*, world: Any, target_ref: Any) -> str:
    ref = _require_string(
        target_ref, "I9A_PRESENTATION_SURFACE_TARGET_ABSENT_FROM_SOURCE_WORLD"
    )
    obj = world.objects.get(ref)
    if obj is not None:
        if obj.scene_id != world.active_scene_id:
            raise ValueError(f"I9A_PRESENTATION_SURFACE_TARGET_SCENE_MISMATCH:{ref}")
        return ref
    actor = world.actors.get(ref)
    if actor is not None:
        if actor.scene_id != world.active_scene_id:
            raise ValueError(f"I9A_PRESENTATION_SURFACE_TARGET_SCENE_MISMATCH:{ref}")
        return ref
    raise ValueError(f"I9A_PRESENTATION_SURFACE_TARGET_ABSENT_FROM_SOURCE_WORLD:{ref}")


def _presentation_requirements(
    *, world: Any, presentation: Any
) -> tuple[Mapping[str, Any], ...]:
    outfit = thaw_value(presentation.outfit_state)
    slots = outfit.get("slot_bindings", {}) if isinstance(outfit, Mapping) else {}
    if not isinstance(slots, Mapping):
        raise ValueError("I9A_OUTFIT_SLOT_BINDINGS_INVALID")
    outfit_refs = tuple(
        sorted(
            {
                _require_string(ref, "I9A_OUTFIT_REF_INVALID")
                for ref in slots.values()
            }
        )
    )
    for ref in outfit_refs:
        _require_presentation_world_object(
            world=world,
            object_ref=ref,
            actor_id=presentation.actor_id,
            missing_code="I9A_PRESENTATION_OUTFIT_OBJECT_ABSENT_FROM_SOURCE_WORLD",
            require_actor_possession=True,
        )

    dressing_rows: list[Mapping[str, Any]] = []
    for raw in presentation.dressing_states:
        row = thaw_value(raw)
        if not isinstance(row, Mapping):
            raise ValueError("I9A_DRESSING_STATE_INVALID")
        if row.get("actor_id") != presentation.actor_id:
            raise ValueError("I9A_DRESSING_ACTOR_MISMATCH")
        material_ref = _require_string(
            row.get("material_ref"), "I9A_DRESSING_MATERIAL_REF_INVALID"
        )
        _require_presentation_world_object(
            world=world,
            object_ref=material_ref,
            actor_id=presentation.actor_id,
            missing_code="I9A_PRESENTATION_DRESSING_MATERIAL_ABSENT_FROM_SOURCE_WORLD",
            require_actor_possession=False,
        )
        covered_raw = row.get("covered_by_refs", ())
        if isinstance(covered_raw, (str, bytes, bytearray)) or not isinstance(
            covered_raw, Sequence
        ):
            raise ValueError("I9A_DRESSING_COVER_REFS_INVALID")
        for covered_ref in covered_raw:
            _require_presentation_world_object(
                world=world,
                object_ref=covered_ref,
                actor_id=presentation.actor_id,
                missing_code="I9A_PRESENTATION_COVER_OBJECT_ABSENT_FROM_SOURCE_WORLD",
                require_actor_possession=False,
            )
        dressing_rows.append(row)
    dressing_rows.sort(
        key=lambda row: _require_string(
            row.get("dressing_id"), "I9A_DRESSING_REF_INVALID"
        )
    )
    dressing_refs = tuple(row["dressing_id"] for row in dressing_rows)

    for raw in presentation.surface_states:
        row = thaw_value(raw)
        if not isinstance(row, Mapping):
            raise ValueError("I9A_SURFACE_STATE_INVALID")
        _require_surface_target_in_world(
            world=world,
            target_ref=row.get("target_ref"),
        )

    policies: list[tuple[str, str]] = []
    worn = set(outfit_refs)
    for ref in outfit_refs:
        policies.append((ref, "MUST_NOT_CONTRADICT"))
    for row in dressing_rows:
        dressing_id = row["dressing_id"]
        covered_raw = row.get("covered_by_refs", ())
        if isinstance(covered_raw, (str, bytes, bytearray)) or not isinstance(
            covered_raw, Sequence
        ):
            raise ValueError("I9A_DRESSING_COVER_REFS_INVALID")
        covered = {
            _require_string(ref, "I9A_DRESSING_COVER_REF_INVALID")
            for ref in covered_raw
        }
        token = (
            "HIDDEN_BY_CLOTHING"
            if covered.intersection(worn)
            else "MUST_RENDER_IF_VISIBLE_IN_SHOT"
        )
        if token not in _ALLOWED_VISIBILITY_POLICY_TOKENS:
            raise ValueError("I9A_VISIBILITY_POLICY_TOKEN_INVALID")
        policies.append((dressing_id, token))

    requirement = {
        "actor_id": presentation.actor_id,
        "identity_refs": (),
        "outfit_refs": outfit_refs,
        "dressing_refs": dressing_refs,
        "visible_condition_cues": (),
        "visibility_policy": tuple(policies),
        "state_version": str(presentation.presentation_state["state_version"]),
    }
    if set(requirement) != _EXPECTED_PRESENTATION_FIELDS:
        raise ValueError("I9A_INTERNAL_PRESENTATION_FIELD_SHAPE_DRIFT")
    return (freeze_value(requirement),)


def _coverage_gaps(presentation: Any) -> tuple[str, ...]:
    gaps = [_GAP_MISSING_VISIBLE_IDENTITY, _GAP_NO_VISIBLE_CUE_ASSEMBLER]
    if presentation.surface_states:
        gaps.append(_GAP_SURFACE_NOT_EXPRESSIBLE)
    return tuple(gaps)


def _beat_id(
    *, storylet_reference: Any, i1_event_sequence_digest: str
) -> str:
    material = {
        "storylet_id": storylet_reference.storylet_id,
        "authored_storylet_sha256": storylet_reference.authored_storylet_sha256,
        "source_world_id": storylet_reference.source_world_id,
        "source_baseline_version": storylet_reference.source_baseline_version,
        "source_state_version": storylet_reference.source_state_version,
        "event_sequence_digest": _require_string(
            i1_event_sequence_digest, "I9A_I1_EVENT_SEQUENCE_DIGEST_REQUIRED"
        ),
    }
    return f"I9A-BEAT-{_sha256_json(material)[:32]}"


def build_director_beat_packet_reference(
    *,
    i8c_replay_package: bytes | bytearray | memoryview,
    i3a_replay_package_json: str,
) -> DirectorBeatPacketReference | None:
    """Replay upstream authority and derive one bounded non-canonical packet."""
    parent = _load_af_h_authority()
    manifest = _load_af_d_manifest()
    if not isinstance(i8c_replay_package, (bytes, bytearray, memoryview)):
        raise TypeError("I9A_I8C_REPLAY_PACKAGE_BYTES_REQUIRED")
    i8c_bytes = bytes(i8c_replay_package)

    storylet_reference = replay_storylet_eligibility_package(i8c_bytes)
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
    expected_world_version = (
        f"{storylet_reference.source_baseline_version}:"
        f"{storylet_reference.source_state_version}"
    )
    if world.world_state_version != expected_world_version:
        raise ValueError("I9A_WORLD_STATE_VERSION_MISMATCH")

    _strict_json_from_text(
        i3a_replay_package_json, "I9A_I3A_REPLAY_PACKAGE_JSON_INVALID"
    )
    presentation = replay_i3a_package(i3a_replay_package_json)
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
    scene_view_asset_refs = _scene_view_material(
        world=world,
        presentation=presentation,
        manifest=manifest,
    )
    actor_requirements = _presentation_requirements(
        world=world, presentation=presentation
    )

    authored_forbidden = tuple(
        _require_string(value, "I9A_FORBIDDEN_INVENTION_INVALID")
        for value in storylet.get("forbidden_contradictions", [])
    )
    forbidden = tuple(
        dict.fromkeys(authored_forbidden + _MANDATORY_AF_H_FORBIDDEN)
    )
    presentation_goal = _require_string(
        storylet.get("dramatic_purpose"), "I9A_PRESENTATION_GOAL_REQUIRED"
    )

    i8c_digest = _sha256_bytes(i8c_bytes)
    i3a_digest = hashlib.sha256(
        i3a_replay_package_json.encode("utf-8")
    ).hexdigest()

    return DirectorBeatPacketReference(
        beat_id=_beat_id(
            storylet_reference=storylet_reference,
            i1_event_sequence_digest=i1_evidence.event_sequence_digest,
        ),
        world_state_version=world.world_state_version,
        confirmed_event_refs=confirmed_event_refs,
        scene_view_asset_refs=scene_view_asset_refs,
        player_visible_knowledge_refs=(),
        public_visible_knowledge_refs=(),
        private_forbidden_knowledge_refs=(),
        actor_presentation_requirements=actor_requirements,
        presentation_goal=presentation_goal,
        forbidden_inventions=forbidden,
        contract_version=parent[1],
        packet_type_version=_EXPECTED_PACKET_TYPE[1],
        source_i8c_sha256=i8c_digest,
        source_i3a_sha256=i3a_digest,
        source_world_id=storylet_reference.source_world_id,
        source_baseline_version=storylet_reference.source_baseline_version,
        source_state_version=storylet_reference.source_state_version,
        source_i1_event_sequence_digest=i1_evidence.event_sequence_digest,
        source_storylet_sha256=storylet_reference.authored_storylet_sha256,
        coverage_gaps=_coverage_gaps(presentation),
        authority_class=_EXPECTED_PACKET_AUTHORITY,
    )


def _normalize_staging(staging: Any) -> Mapping[str, str]:
    if not isinstance(staging, Mapping):
        raise ValueError("I9A_STAGING_METADATA_MAPPING_REQUIRED")
    unknown = set(staging) - _ALLOWED_STAGING_KEYS
    if unknown:
        raise ValueError(
            f"I9A_STAGING_METADATA_AUTHORITY_EXPANSION_FORBIDDEN:"
            f"{sorted(unknown)[0]}"
        )

    normalized: dict[str, str] = {}
    for key in sorted(staging):
        value = staging[key]
        if not isinstance(value, str):
            raise ValueError(f"I9A_STAGING_FREE_TEXT_FORBIDDEN:{key}")
        if value not in NON_CANONICAL_MOCK_STAGING_VARIANTS[key]:
            raise ValueError(f"I9A_STAGING_VARIANT_INVALID:{key}")
        normalized[key] = value
    return freeze_value(normalized)


def consume_mock_ai_film_response(
    *,
    i8c_replay_package: bytes | bytearray | memoryview,
    i3a_replay_package_json: str,
    response: Mapping[str, Any],
) -> MockAIFilmReceipt:
    """Rebuild packet, then accept only eval-local staging enum tokens."""
    packet = build_director_beat_packet_reference(
        i8c_replay_package=i8c_replay_package,
        i3a_replay_package_json=i3a_replay_package_json,
    )
    if packet is None:
        raise ValueError("I9A_NO_VALID_STORYLET_NO_PACKET")
    if not isinstance(response, Mapping):
        raise ValueError("I9A_AI_FILM_RESPONSE_MAPPING_REQUIRED")

    expected_keys = {
        "source_packet_sha256",
        "protected_material_sha256",
        "staging_metadata",
    }
    extras = set(response) - expected_keys
    missing = expected_keys - set(response)
    if extras:
        raise ValueError(
            f"I9A_AI_FILM_PROTECTED_OR_UNKNOWN_FIELD_FORBIDDEN:"
            f"{sorted(extras)[0]}"
        )
    if missing:
        raise ValueError(
            f"I9A_AI_FILM_RESPONSE_FIELD_MISSING:{sorted(missing)[0]}"
        )

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
