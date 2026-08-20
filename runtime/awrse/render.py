from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any, Mapping

from .model import Event, WorldState, freeze_value


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


def build_render_packet(world: WorldState, events: list[Event]) -> WorldRenderPacket:
    scene = world.scenes[world.active_scene_id]
    actor_refs = tuple(
        f"actor://{actor.actor_id}@{world.world_state_version}"
        for actor in sorted(world.actors.values(), key=lambda item: item.actor_id)
        if actor.scene_id == world.active_scene_id
    )
    object_deltas = tuple(
        freeze_value(
            {
                "kind": "OBJECT_STATE",
                "object_id": obj.object_id,
                "damage_state": obj.damage_state,
                "contamination_state": obj.contamination_state,
            }
        )
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
        confirmed_events=tuple(events),
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
    rendered_object_states: Mapping[str, str] | None = None,
    rendered_scene_id: str | None = None,
    extra_claims: set[str] | None = None,
) -> RenderValidation:
    canonical_event_ids = {event.event_id for event in packet.confirmed_events}
    missing = tuple(sorted(canonical_event_ids - rendered_event_ids))
    extras = tuple(sorted(extra_claims or set()))
    contradictions: list[str] = []

    if rendered_scene_id is not None and rendered_scene_id != packet.scene_id:
        contradictions.append(f"SCENE_ID:{rendered_scene_id}!={packet.scene_id}")

    canonical_object_states = {
        str(delta["object_id"]): str(delta["damage_state"])
        for delta in packet.environment_delta
        if delta.get("kind") == "OBJECT_STATE"
    }
    if canonical_object_states and rendered_object_states is None:
        contradictions.append("OBJECT_STATE_CLAIMS_REQUIRED")
    elif rendered_object_states is not None:
        for object_id, canonical_state in canonical_object_states.items():
            if object_id not in rendered_object_states:
                contradictions.append(f"MISSING_OBJECT_STATE:{object_id}")
                continue
            rendered_state = rendered_object_states[object_id]
            if canonical_state != rendered_state:
                contradictions.append(
                    f"OBJECT_STATE:{object_id}:{rendered_state}!={canonical_state}"
                )
        for object_id in rendered_object_states:
            if object_id not in canonical_object_states:
                contradictions.append(f"UNCONFIRMED_OBJECT:{object_id}")

    if missing or extras or contradictions:
        return RenderValidation(
            "RENDER_MISMATCH",
            missing_canonical_events=missing,
            unauthorized_claims=extras,
            semantic_contradictions=tuple(sorted(contradictions)),
        )
    return RenderValidation("RENDER_ALIGNED")
