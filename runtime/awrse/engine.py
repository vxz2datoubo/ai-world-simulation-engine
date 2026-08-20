from __future__ import annotations

import itertools
from dataclasses import dataclass, field

from .compiler import declared_superhuman_effect
from .model import Action, Event, ResolutionStatus, WorldBaseline, WorldState


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
            object_id = str(event.payload["object_id"])
            damage_state = str(event.payload["damage_state"])
            world.objects[object_id].damage_state = damage_state
            delta = f"{object_id}:damage_state={damage_state}"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type == "NPC_KNOWLEDGE_ACQUIRED":
            npc_id = str(event.payload["npc_id"])
            npc = world.npc_minds[npc_id]
            if event.event_id not in npc.memories:
                npc.memories.append(event.event_id)
            knowledge_ref = str(event.payload["source_event_id"])
            if knowledge_ref not in npc.knowledge_boundary_refs:
                npc.knowledge_boundary_refs.append(knowledge_ref)

        elif event.event_type == "RELATIONSHIP_CHANGED":
            npc_id = str(event.payload["npc_id"])
            delta = int(event.payload["delta"])
            world.npc_minds[npc_id].relationship_to_player += delta


class SimulationEngine:
    _event_counter = itertools.count(1)
    _implemented_player_verbs = frozenset({"SPEAK", "HIT"})

    def resolve(self, action: Action, world: WorldState) -> Resolution:
        if action.resolution_status == ResolutionStatus.UNKNOWN_REQUIRES_DISAMBIGUATION:
            return Resolution(action)

        actor = world.actors.get(action.actor_id)
        if actor is None:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "ACTOR_NOT_FOUND")
        if actor.scene_id != world.active_scene_id:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "ACTOR_NOT_IN_ACTIVE_SCENE")

        if (
            not action.authority_scope.may_control_actor
            or not world.can_principal_control(action.principal_id, action.actor_id)
        ):
            return self._reject(action, ResolutionStatus.REJECTED_AUTHORITY, "PRINCIPAL_NOT_AUTHORIZED_FOR_ACTOR")
        if action.authority_scope.may_control_target_internal_state or action.authority_scope.may_modify_world_rules:
            return self._reject(action, ResolutionStatus.REJECTED_AUTHORITY, "UNAUTHORIZED_SCOPE_ESCALATION")

        if declared_superhuman_effect(action.literal_user_input):
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PHYSICS,
                "DECLARED_EFFECT_EXCEEDS_NORMAL_HUMAN_CAPABILITY",
            )

        precondition_failure = self._evaluate_preconditions(action, world)
        if precondition_failure is not None:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, precondition_failure)

        if action.verb not in self._implemented_player_verbs:
            return self._reject(action, ResolutionStatus.RESOLVED_FAILURE, "UNIMPLEMENTED_ACTION_FAMILY")

        if action.verb == "HIT" and len(action.target_ids) > actor.max_targets_per_strike:
            return self._reject(action, ResolutionStatus.REJECTED_PHYSICS, "TOO_MANY_TARGETS_FOR_SINGLE_STRIKE")
        if action.verb == "SPEAK":
            return self._resolve_speech(action, world)
        return self._resolve_hit(action, world)

    def commit(self, resolution: Resolution, world: WorldState) -> Resolution:
        if resolution.action.resolution_status not in {
            ResolutionStatus.RESOLVED_SUCCESS,
            ResolutionStatus.RESOLVED_PARTIAL,
        }:
            return resolution
        self._commit_events(world, resolution.events)
        return resolution

    def resolve_and_commit(self, action: Action, world: WorldState) -> Resolution:
        return self.commit(self.resolve(action, world), world)

    def replay(self, baseline: WorldBaseline, events: list[Event]) -> WorldState:
        rebuilt = baseline.instantiate()
        if rebuilt.event_log or rebuilt.committed_event_ids or rebuilt.state_version != 0:
            raise ValueError("BASELINE_MUST_BE_PRISTINE")
        if rebuilt.baseline_version != baseline.baseline_version:
            raise ValueError("BASELINE_VERSION_MISMATCH")
        self._commit_events(rebuilt, events)
        return rebuilt

    def propagate_knowledge(
        self,
        source_npc_id: str,
        recipient_npc_id: str,
        source_event_id: str,
        world: WorldState,
    ) -> Event | None:
        source = world.npc_minds.get(source_npc_id)
        recipient = world.npc_minds.get(recipient_npc_id)
        if source is None or recipient is None:
            return None
        if source_event_id not in source.knowledge_boundary_refs:
            return None
        if not world.can_hear(source_npc_id, recipient_npc_id):
            return None
        event = self._new_event(
            event_type="NPC_KNOWLEDGE_ACQUIRED",
            actor_id=source_npc_id,
            scene_id=world.actors[source_npc_id].scene_id,
            world=world,
            payload={
                "npc_id": recipient_npc_id,
                "mode": "WAS_TOLD",
                "source_event_id": source_event_id,
                "source_npc_id": source_npc_id,
            },
        )
        self._commit_events(world, [event])
        return event

    def _evaluate_preconditions(self, action: Action, world: WorldState) -> str | None:
        required_by_verb = {
            "HIT": {"TARGET_REACHABLE", "CAPABILITY_PRESENT"},
            "SPEAK": {"CAPABILITY_PRESENT"},
        }
        required = required_by_verb.get(action.verb, set())
        missing_required = required - set(action.preconditions)
        if missing_required:
            return "MISSING_REQUIRED_PRECONDITION:" + ",".join(sorted(missing_required))
        if action.verb == "HIT" and not action.target_ids:
            return "TARGET_REQUIRED"

        for condition in action.preconditions:
            if condition == "TARGET_EXISTS":
                if any(not world.entity_exists(target) for target in action.target_ids):
                    return "TARGET_NOT_FOUND"
            elif condition == "TARGET_REACHABLE":
                if not action.target_ids:
                    return "TARGET_REQUIRED"
                if any(not world.is_reachable(action.actor_id, target) for target in action.target_ids):
                    return "TARGET_NOT_REACHABLE"
            elif condition == "CAPABILITY_PRESENT":
                actor = world.actors[action.actor_id]
                if action.verb not in actor.capabilities:
                    return "CAPABILITY_MISSING"
            else:
                return f"UNSUPPORTED_PRECONDITION:{condition}"
        return None

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
        for npc_id in sorted(world.npc_minds):
            if not world.can_hear(action.actor_id, npc_id):
                continue
            events.append(
                self._event(
                    "NPC_KNOWLEDGE_ACQUIRED",
                    action,
                    world,
                    {
                        "npc_id": npc_id,
                        "mode": "HEARD",
                        "source_event_id": speech.event_id,
                        "speaker_id": action.actor_id,
                    },
                )
            )
            if npc_id in action.target_ids and self._is_insult(action.literal_user_input):
                events.append(
                    self._event(
                        "RELATIONSHIP_CHANGED",
                        action,
                        world,
                        {"npc_id": npc_id, "delta": -10, "reason": "AUDIBLE_INSULT"},
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
            actor = world.actors[action.actor_id]
            damage_state = "BROKEN" if actor.strength >= obj.fragility else "DAMAGED"
            object_event = self._event(
                "OBJECT_DAMAGED",
                action,
                world,
                {"object_id": target_id, "damage_state": damage_state},
            )
            events = [object_event]
            for npc_id in sorted(world.npc_minds):
                if world.can_see(target_id, npc_id):
                    events.append(
                        self._event(
                            "NPC_KNOWLEDGE_ACQUIRED",
                            action,
                            world,
                            {
                                "npc_id": npc_id,
                                "mode": "SAW",
                                "source_event_id": object_event.event_id,
                                "observed_entity_id": target_id,
                            },
                        )
                    )
            action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
            return Resolution(action, events)

        event = self._event(
            "ACTOR_STRUCK",
            action,
            world,
            {"target_id": target_id, "effect": "NORMAL_HUMAN_STRIKE"},
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        return Resolution(action, [event])

    def _commit_events(self, world: WorldState, events: list[Event]) -> None:
        existing_by_id = {event.event_id: event for event in world.event_log}
        for event in events:
            if event.baseline_version != world.baseline_version:
                raise ValueError("EVENT_BASELINE_VERSION_MISMATCH")
            existing = existing_by_id.get(event.event_id)
            if existing is not None:
                if existing != event:
                    raise ValueError(f"EVENT_ID_CONFLICT:{event.event_id}")
                continue
            world.event_log.append(event)
            world.committed_event_ids.add(event.event_id)
            existing_by_id[event.event_id] = event
            WorldProjector.apply(world, event)
            world.state_version += 1

    @staticmethod
    def _is_insult(text: str) -> bool:
        lowered = text.lower()
        return any(token in lowered for token in ("骂", "insult", "idiot", "蠢货"))

    @staticmethod
    def _reject(action: Action, status: ResolutionStatus, reason: str) -> Resolution:
        action.resolution_status = status
        action.failure_reason = reason
        return Resolution(action)

    def _event(self, event_type: str, action: Action, world: WorldState, payload: dict) -> Event:
        return self._new_event(
            event_type=event_type,
            actor_id=action.actor_id,
            scene_id=world.active_scene_id,
            world=world,
            payload=payload,
            caused_by_action_id=action.action_id,
        )

    def _new_event(
        self,
        event_type: str,
        actor_id: str | None,
        scene_id: str,
        world: WorldState,
        payload: dict,
        caused_by_action_id: str | None = None,
    ) -> Event:
        return Event(
            event_id=f"E{next(self._event_counter):06d}",
            event_type=event_type,
            actor_id=actor_id,
            scene_id=scene_id,
            baseline_version=world.baseline_version,
            payload=payload,
            caused_by_action_id=caused_by_action_id,
        )
