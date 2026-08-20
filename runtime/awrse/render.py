from __future__ import annotations

from dataclasses import dataclass

from .model import Event, WorldState


@dataclass(frozen=True)
class WorldRenderPacket:
    scene_id: str
    base_asset_refs: tuple[str, ...]
    persistent_deltas: tuple[str, ...]
    confirmed_event_ids: tuple[str, ...]
    confirmed_event_types: tuple[str, ...]
    actor_ids: tuple[str, ...]
    object_states: tuple[tuple[str, str], ...]
    authority_note: str = "RENDERER_IS_PROJECTION_ONLY"


@dataclass(frozen=True)
class RenderValidation:
    status: str
    missing_canonical_events: tuple[str, ...] = ()
    unauthorized_claims: tuple[str, ...] = ()


def build_render_packet(world: WorldState, events: list[Event]) -> WorldRenderPacket:
    scene = world.scenes[world.active_scene_id]
    scene_objects = tuple(
        sorted(
            (obj.object_id, obj.damage_state)
            for obj in world.objects.values()
            if obj.scene_id == world.active_scene_id
        )
    )
    scene_actors = tuple(
        sorted(actor.actor_id for actor in world.actors.values() if actor.scene_id == world.active_scene_id)
    )
    return WorldRenderPacket(
        scene_id=world.active_scene_id,
        base_asset_refs=tuple(scene.base_asset_refs),
        persistent_deltas=tuple(scene.persistent_delta_refs),
        confirmed_event_ids=tuple(event.event_id for event in events),
        confirmed_event_types=tuple(event.event_type for event in events),
        actor_ids=scene_actors,
        object_states=scene_objects,
    )


def validate_render_claims(packet: WorldRenderPacket, rendered_event_ids: set[str], extra_claims: set[str] | None = None) -> RenderValidation:
    """Validate renderer self-reported semantic claims against canonical packet.

    Real video understanding is intentionally out of scope for R001. This contract
    gives later VLM/video evaluators a deterministic authority boundary to target.
    """

    canonical = set(packet.confirmed_event_ids)
    missing = tuple(sorted(canonical - rendered_event_ids))
    extras = tuple(sorted(extra_claims or set()))
    if missing or extras:
        return RenderValidation("RENDER_MISMATCH", missing, extras)
    return RenderValidation("RENDER_ALIGNED")
