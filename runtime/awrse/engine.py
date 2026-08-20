from __future__ import annotations

import copy
import itertools
from dataclasses import dataclass, field

from .compiler import declared_superhuman_effect
from .model import Action, Event, ResolutionStatus, WorldState


@dataclass
class Resolution:
    action: Action
    events: list[Event] = field(default_factory=list)


class WorldProjector:
    """Authorized deterministic projection from canonical events to current state."""

    @staticmethod
    def apply(world: WorldState, event: Event) -> None:
        scene = world.scenes[event.scene_id]
        if event.event_id not in scene.relevant_event_refs:
            scene.relevant_event_refs.append(event.event_id)

        if event.event_type == "OBJECT_DAMAGED":
            object_id = event.payload["object_id"]
            damage_state = event.payload["damage_state"]
            world.objects[object_id].damage_state = damage_state
            delta = f"{object_id}:damage_state={damage_state}"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type == "NPC_KNOWLEDGE_ACQUIRED":
            npc_id = event.payload["npc_id"]
            npc = world.npc_minds[npc_id]
            if event.event_id not in npc.memories:
                npc.memories.append(event.event_id)
            knowledge_ref = event.payload["source_event_id"]
            if knowledge_ref not in npc.knowledge_boundary_refs:
                npc.knowledge_boundary_refs.append(knowledge_ref)

        elif event.event_type == "RELATIONSHIP_CHANGED":
            npc_id = event.payload["npc_id"]
            delta = int(event.payload["delta"])
            world.npc_minds[npc_id].relationship_to_player += delta


class SimulationEngine:
    _event_counter = itertools.count(1)

    def resolve(self, action: Action, world: WorldState) -> Resolution:
        if action.resolution_status == ResolutionStatus.UNKNOWN_REQUIRES_DISAMBIGUATION:
            return Resolution(action)

        actor = world.actors.get(action.actor_id)
        if actor is None:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "ACTOR_NOT_FOUND")

        missing_targets = [target for target in action.target_ids if not world.entity_exists(target)]
        if missing_targets:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "TARGET_NOT_FOUND")

        if declared_superhuman_effect(action.literal_user_input):
            return self._reject(action, ResolutionStatus.REJECTED_PHYSICS, "DECLARED_EFFECT_EXCEEDS_NORMAL_HUMAN_CAPABILITY")

        if action.verb == "HIT" and len(action.target_ids) > actor.max_targets_per_strike:
            return self._reject(action, ResolutionStatus.REJECTED_PHYSICS, "TOO_MANY_TARGETS_FOR_SINGLE_STRIKE")

        if action.verb == "SPEAK":
            return self._resolve_speech(action, world)

        if action.verb == "HIT":
            return self._resolve_hit(action, world)

        return self._resolve_generic(action, world)

    def commit(self, resolution: Resolution, world: WorldState) -> Resolution:
        if resolution.action.resolution_status not in {
            ResolutionStatus.RESOLVED_SUCCESS,
            ResolutionStatus.RESOLVED_PARTIAL,
        }:
            return resolution

        for event in resolution.events:
            world.event_log.append(event)
            WorldProjector.apply(world, event)
        return resolution

    def resolve_and_commit(self, action: Action, world: WorldState) -> Resolution:
        return self.commit(self.resolve(action, world), world)

    def replay(self, base_world: WorldState, events: list[Event]) -> WorldState:
        rebuilt = copy.deepcopy(base_world)
        rebuilt.event_log = []
        for scene in rebuilt.scenes.values():
            scene.relevant_event_refs = []
            scene.persistent_delta_refs = []
        for npc in rebuilt.npc_minds.values():
            npc.memories = []
            npc.knowledge_boundary_refs = []
        for event in events:
            rebuilt.event_log.append(event)
            WorldProjector.apply(rebuilt, event)
        return rebuilt

    def _resolve_speech(self, action: Action, world: WorldState) -> Resolution:
        speech = self._event(
            "SPEECH_UTTERED",
            action,
            world,
            {
                "literal_content": action.literal_user_input,
                "trust_class": "UNTRUSTED_DATA",
                "authority": "NONE_OVER_TARGET_INTERNAL_STATE",
            },
        )
        events = [speech]
        for target_id in action.target_ids:
            if target_id not in world.npc_minds:
                continue
            target_actor = world.actors.get(target_id)
            if target_actor is not None and target_actor.scene_id != world.active_scene_id:
                continue
            events.append(
                self._event(
                    "NPC_KNOWLEDGE_ACQUIRED",
                    action,
                    world,
                    {
                        "npc_id": target_id,
                        "mode": "HEARD",
                        "source_event_id": speech.event_id,
                        "content": action.literal_user_input,
                    },
                )
            )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        return Resolution(action, events)

    def _resolve_hit(self, action: Action, world: WorldState) -> Resolution:
        if not action.target_ids:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "TARGET_REQUIRED")

        target_id = action.target_ids[0]
        if target_id in world.objects:
            obj = world.objects[target_id]
            if obj.scene_id != world.active_scene_id:
                return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "TARGET_NOT_IN_ACTIVE_SCENE")
            actor = world.actors[action.actor_id]
            damage_state = "BROKEN" if actor.strength >= obj.fragility else "DAMAGED"
            event = self._event(
                "OBJECT_DAMAGED",
                action,
                world,
                {"object_id": target_id, "damage_state": damage_state},
            )
            action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
            return Resolution(action, [event])

        event = self._event(
            "ACTOR_STRUCK",
            action,
            world,
            {"target_id": target_id, "effect": "NORMAL_HUMAN_STRIKE"},
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        return Resolution(action, [event])

    def _resolve_generic(self, action: Action, world: WorldState) -> Resolution:
        event = self._event(
            "ACTION_RESOLVED",
            action,
            world,
            {"verb": action.verb, "target_ids": list(action.target_ids)},
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        return Resolution(action, [event])

    @staticmethod
    def _reject(action: Action, status: ResolutionStatus, reason: str) -> Resolution:
        action.resolution_status = status
        action.failure_reason = reason
        return Resolution(action)

    def _event(
        self,
        event_type: str,
        action: Action,
        world: WorldState,
        payload: dict,
    ) -> Event:
        return Event(
            event_id=f"E{next(self._event_counter):06d}",
            event_type=event_type,
            actor_id=action.actor_id,
            scene_id=world.active_scene_id,
            payload=payload,
            caused_by_action_id=action.action_id,
        )
