from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .model import Event, WorldState, freeze_value, thaw_value


_render_counter = itertools.count(1)


@dataclass(frozen=True)
class WorldRenderPacket:
    render_request_id: str
    world_state_version: str
    scene_id: str
    scene_asset_refs: tuple[str, ...]
    camera: Mapping[str, Any]
    player_state_ref: str
    actor_state_refs: tuple[str, ...]
    confirmed_events: tuple[Event, ...]
    environment_delta: tuple[Mapping[str, Any], ...]
    continuity_refs: Mapping[str, Any]
    renderer_constraints: Mapping[str, Any]
    output_contract: Mapping[str, Any]


@dataclass(frozen=True)
class RenderValidation:
    status: str
    missing_canonical_events: tuple[str, ...] = ()
    unauthorized_claims: tuple[str, ...] = ()
    semantic_contradictions: tuple[str, ...] = ()


def _canonical_confirmed_events(world: WorldState, events: Iterable[Event]) -> tuple[Event, ...]:
    canonical_by_id: dict[str, Event] = {}
    for canonical in world.event_log:
        if canonical.event_id in canonical_by_id:
            raise ValueError(f"CANONICAL_EVENT_LOG_DUPLICATE:{canonical.event_id}")
        canonical_by_id[canonical.event_id] = canonical
    if set(canonical_by_id) != set(world.committed_event_ids):
        raise ValueError("CANONICAL_EVENT_INDEX_MISMATCH")

    confirmed: list[Event] = []
    requested_ids: set[str] = set()
    for event in events:
        if event.event_id in requested_ids:
            raise ValueError(f"DUPLICATE_CONFIRMED_EVENT_REQUEST:{event.event_id}")
        requested_ids.add(event.event_id)
        if event.baseline_version != world.baseline_version:
            raise ValueError(f"CONFIRMED_EVENT_BASELINE_MISMATCH:{event.event_id}")
        if event.scene_id != world.active_scene_id:
            raise ValueError(f"CONFIRMED_EVENT_WRONG_SCENE:{event.event_id}")
        if event.event_id not in world.committed_event_ids:
            raise ValueError(f"UNCOMMITTED_CONFIRMED_EVENT:{event.event_id}")
        canonical = canonical_by_id.get(event.event_id)
        if canonical is None:
            raise ValueError(f"COMMITTED_EVENT_NOT_IN_LOG:{event.event_id}")
        if canonical != event:
            raise ValueError(f"CONFIRMED_EVENT_MISMATCH:{event.event_id}")
        confirmed.append(canonical)
    return tuple(confirmed)


def _object_render_state(world: WorldState, obj: Any) -> dict[str, Any]:
    state: dict[str, Any] = {
        "kind": "OBJECT_STATE",
        "object_id": obj.object_id,
        "damage_state": obj.damage_state,
        "contamination_state": obj.contamination_state,
    }
    # R001 worlds remain contract-compatible with the historical two-field object
    # claim. R002 symbolic worlds project the additional persistent canonical truth.
    if world.has_symbolic_spatial_substrate:
        state.update(
            {
                "is_open": obj.is_open,
                "owner_actor_id": obj.owner_actor_id,
                "zone_id": obj.zone_id,
            }
        )
    return state


def build_render_packet(world: WorldState, events: Iterable[Event]) -> WorldRenderPacket:
    world.seal_live()
    scene = world.scenes[world.active_scene_id]
    confirmed_events = _canonical_confirmed_events(world, events)
    actor_refs = tuple(
        f"actor://{actor.actor_id}@{world.world_state_version}"
        for actor in sorted(world.actors.values(), key=lambda item: item.actor_id)
        if actor.scene_id == world.active_scene_id
    )
    object_deltas = tuple(
        freeze_value(_object_render_state(world, obj))
        for obj in sorted(world.objects.values(), key=lambda item: item.object_id)
        if obj.scene_id == world.active_scene_id
    )
    return WorldRenderPacket(
        render_request_id=f"RRP-{next(_render_counter):06d}",
        world_state_version=world.world_state_version,
        scene_id=world.active_scene_id,
        scene_asset_refs=tuple(scene.base_asset_refs),
        camera=freeze_value({"mode": "CANONICAL_SCENE_DEFAULT", "framing": "UNSPECIFIED"}),
        player_state_ref=f"actor://{world.primary_player_actor_id}@{world.world_state_version}",
        actor_state_refs=actor_refs,
        confirmed_events=confirmed_events,
        environment_delta=object_deltas,
        continuity_refs=freeze_value(
            {
                "scene_canonical_bundle_ref": f"scene://{scene.scene_id}@{world.world_state_version}",
                "prior_frame_ref": None,
                "prior_clip_ref": None,
                "character_reference_refs": actor_refs,
            }
        ),
        renderer_constraints=freeze_value(
            {
                "no_world_rule_mutation": True,
                "no_unconfirmed_outcome_invention": True,
                "preserve_identity": True,
                "preserve_object_state": True,
            }
        ),
        output_contract=freeze_value(
            {
                "duration_seconds": None,
                "resolution_class": "UNSPECIFIED",
                "audio_required": False,
                "latency_class": "UNSPECIFIED",
            }
        ),
    )


def validate_render_claims(
    packet: WorldRenderPacket,
    rendered_event_ids: set[str],
    rendered_object_states: Mapping[str, Mapping[str, Any]] | None = None,
    rendered_scene_id: str | None = None,
    rendered_actor_state_refs: Iterable[str] | None = None,
    rendered_camera: Mapping[str, Any] | None = None,
    extra_claims: set[str] | None = None,
) -> RenderValidation:
    canonical_event_ids = {event.event_id for event in packet.confirmed_events}
    missing = tuple(sorted(canonical_event_ids - rendered_event_ids))
    unexpected_event_ids = rendered_event_ids - canonical_event_ids
    unauthorized = set(extra_claims or set())
    unauthorized.update(f"UNCONFIRMED_EVENT_ID:{event_id}" for event_id in unexpected_event_ids)
    contradictions: list[str] = []

    if rendered_scene_id is None:
        contradictions.append("SCENE_ID_CLAIM_REQUIRED")
    elif rendered_scene_id != packet.scene_id:
        contradictions.append(f"SCENE_ID:{rendered_scene_id}!={packet.scene_id}")

    canonical_actor_refs = set(packet.actor_state_refs)
    if rendered_actor_state_refs is None:
        contradictions.append("ACTOR_STATE_CLAIMS_REQUIRED")
    else:
        rendered_actor_refs = set(rendered_actor_state_refs)
        for actor_ref in sorted(canonical_actor_refs - rendered_actor_refs):
            contradictions.append(f"MISSING_ACTOR_STATE_REF:{actor_ref}")
        for actor_ref in sorted(rendered_actor_refs - canonical_actor_refs):
            contradictions.append(f"UNCONFIRMED_ACTOR_STATE_REF:{actor_ref}")

    if rendered_camera is None:
        contradictions.append("CAMERA_CLAIM_REQUIRED")
    elif thaw_value(rendered_camera) != thaw_value(packet.camera):
        contradictions.append("CAMERA_INTENT_MISMATCH")

    canonical_object_states = {
        str(delta["object_id"]): {
            key: delta[key]
            for key in delta
            if key not in {"kind", "object_id"}
        }
        for delta in packet.environment_delta
        if delta.get("kind") == "OBJECT_STATE"
    }
    if canonical_object_states and rendered_object_states is None:
        contradictions.append("OBJECT_STATE_CLAIMS_REQUIRED")
    elif rendered_object_states is not None:
        for object_id, canonical_state in canonical_object_states.items():
            rendered_state = rendered_object_states.get(object_id)
            if rendered_state is None:
                contradictions.append(f"MISSING_OBJECT_STATE:{object_id}")
                continue
            if not isinstance(rendered_state, Mapping):
                contradictions.append(f"OBJECT_STATE_FIELDS_REQUIRED:{object_id}")
                continue
            for field_name, canonical_value in canonical_state.items():
                if field_name not in rendered_state:
                    contradictions.append(f"MISSING_OBJECT_FIELD:{object_id}:{field_name}")
                    continue
                rendered_value = rendered_state[field_name]
                if rendered_value != canonical_value:
                    contradictions.append(
                        f"OBJECT_STATE:{object_id}:{field_name}:{rendered_value}!={canonical_value}"
                    )
        for object_id in rendered_object_states:
            if object_id not in canonical_object_states:
                contradictions.append(f"UNCONFIRMED_OBJECT:{object_id}")

    if missing or unauthorized or contradictions:
        return RenderValidation(
            "RENDER_MISMATCH",
            missing_canonical_events=missing,
            unauthorized_claims=tuple(sorted(unauthorized)),
            semantic_contradictions=tuple(sorted(contradictions)),
        )
    return RenderValidation("RENDER_ALIGNED")
