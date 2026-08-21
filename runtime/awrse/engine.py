from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Iterable, Mapping

from .compiler import declared_superhuman_effect
from .model import (
    Action,
    Event,
    ResolutionStatus,
    WorldBaseline,
    WorldState,
    _LIVE_MUTATION_TOKEN,
    _clone_world_state,
)


@dataclass(frozen=True)
class Resolution:
    action: Action
    events: tuple[Event, ...] = ()


class WorldProjector:
    """Authorized deterministic projection from canonical events to mutable staging state."""

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
            world.npc_minds[npc_id].relationship_to_player += int(event.payload["delta"])

        elif event.event_type == "ACTIVE_SCENE_CHANGED":
            world.active_scene_id = str(event.payload["to_scene_id"])


class SimulationEngine:
    _event_counter = itertools.count(1)
    _implemented_player_verbs = frozenset({"SPEAK", "HIT"})
    _supported_event_types = frozenset(
        {
            "SPEECH_UTTERED",
            "OBJECT_DAMAGED",
            "ACTOR_STRUCK",
            "NPC_KNOWLEDGE_ACQUIRED",
            "RELATIONSHIP_CHANGED",
            "ACTIVE_SCENE_CHANGED",
        }
    )

    def resolve(self, action: Action, world: WorldState) -> Resolution:
        """Resolve for inspection only. Sealing prevents caller mutation after live evaluation begins."""
        world.seal_live()
        return self.__resolve_authoritatively(action, world)

    def commit(self, resolution: Resolution, world: WorldState) -> Resolution:
        raise PermissionError("DIRECT_COMMIT_FORBIDDEN_USE_RESOLVE_AND_COMMIT")

    def resolve_and_commit(self, action: Action, world: WorldState) -> Resolution:
        world.seal_live()
        resolution = self.__resolve_authoritatively(action, world)
        if resolution.action.resolution_status in {
            ResolutionStatus.RESOLVED_SUCCESS,
            ResolutionStatus.RESOLVED_PARTIAL,
        }:
            self.__commit_events(world, resolution.events)
        return resolution

    def replay(self, baseline: WorldBaseline, events: Iterable[Event]) -> WorldState:
        rebuilt = baseline.instantiate()
        if rebuilt.event_log or rebuilt.committed_event_ids or rebuilt.state_version != 0:
            raise ValueError("BASELINE_MUST_BE_PRISTINE")
        if rebuilt.baseline_version != baseline.baseline_version:
            raise ValueError("BASELINE_VERSION_MISMATCH")
        rebuilt.seal_live()
        self.__commit_events(rebuilt, tuple(events))
        return rebuilt

    def transition_active_scene(self, target_scene_id: str, world: WorldState) -> Event:
        """Minimal authorized deterministic scene-selection transition used by revisit coverage."""
        world.seal_live()
        if target_scene_id not in world.scenes:
            raise ValueError("TARGET_SCENE_NOT_FOUND")
        event = self._new_event(
            event_type="ACTIVE_SCENE_CHANGED",
            actor_id=None,
            scene_id=world.active_scene_id,
            world=world,
            payload={"to_scene_id": target_scene_id},
        )
        self.__commit_events(world, (event,))
        return event

    def propagate_knowledge(
        self,
        source_npc_id: str,
        recipient_npc_id: str,
        source_event_id: str,
        world: WorldState,
    ) -> Event | None:
        world.seal_live()
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
        self.__commit_events(world, (event,))
        return event

    def __resolve_authoritatively(self, action: Action, world: WorldState) -> Resolution:
        if action.resolution_status == ResolutionStatus.UNKNOWN_REQUIRES_DISAMBIGUATION:
            return Resolution(action)

        actor = world.actors.get(action.actor_id)
        if actor is None:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "ACTOR_NOT_FOUND")
        if actor.scene_id != world.active_scene_id:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "ACTOR_NOT_IN_ACTIVE_SCENE")
        if not action.authority_scope.may_control_actor or not world.can_principal_control(action.principal_id, action.actor_id):
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
                if action.verb not in world.actors[action.actor_id].capabilities:
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
        events: list[Event] = [speech]
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
        action.failure_reason = None
        return Resolution(action, tuple(events))

    def _resolve_hit(self, action: Action, world: WorldState) -> Resolution:
        if not action.target_ids:
            return self._reject(action, ResolutionStatus.REJECTED_PRECONDITION, "TARGET_REQUIRED")
        target_id = action.target_ids[0]
        if target_id in world.objects:
            obj = world.objects[target_id]
            actor = world.actors[action.actor_id]
            damage_state = "BROKEN" if actor.strength >= obj.fragility else "DAMAGED"
            object_event = self._event(
                "OBJECT_DAMAGED", action, world, {"object_id": target_id, "damage_state": damage_state}
            )
            events: list[Event] = [object_event]
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
            action.failure_reason = None
            return Resolution(action, tuple(events))

        event = self._event(
            "ACTOR_STRUCK", action, world, {"target_id": target_id, "effect": "NORMAL_HUMAN_STRIKE"}
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, (event,))

    def __commit_events(self, world: WorldState, events: Iterable[Event]) -> None:
        new_events = self.__prevalidate_event_batch(world, tuple(events))
        if not new_events:
            return

        staged = _clone_world_state(world)
        self.__apply_prevalidated_events(staged, new_events)
        staged._seal_graph_authorized(_LIVE_MUTATION_TOKEN)
        world._adopt_authorized_state(staged, _LIVE_MUTATION_TOKEN)

    def __prevalidate_event_batch(self, world: WorldState, events: tuple[Event, ...]) -> tuple[Event, ...]:
        existing_by_id: dict[str, Event] = {}
        for existing in world.event_log:
            prior = existing_by_id.get(existing.event_id)
            if prior is not None and prior != existing:
                raise ValueError(f"CANONICAL_EVENT_LOG_CONFLICT:{existing.event_id}")
            if prior is not None:
                raise ValueError(f"CANONICAL_EVENT_LOG_DUPLICATE:{existing.event_id}")
            existing_by_id[existing.event_id] = existing
        if set(existing_by_id) != set(world.committed_event_ids):
            raise ValueError("CANONICAL_EVENT_INDEX_MISMATCH")

        batch_by_id: dict[str, Event] = {}
        candidates: list[Event] = []
        available_event_ids = set(existing_by_id)
        for event in events:
            if not event.event_id:
                raise ValueError("EVENT_ID_REQUIRED")
            if event.baseline_version != world.baseline_version:
                raise ValueError("EVENT_BASELINE_VERSION_MISMATCH")
            if event.scene_id not in world.scenes:
                raise ValueError(f"EVENT_SCENE_NOT_FOUND:{event.scene_id}")
            if event.event_type not in self._supported_event_types:
                raise ValueError(f"UNSUPPORTED_EVENT_TYPE:{event.event_type}")

            existing = existing_by_id.get(event.event_id)
            if existing is not None:
                if existing != event:
                    raise ValueError(f"EVENT_ID_CONFLICT:{event.event_id}")
                continue
            prior = batch_by_id.get(event.event_id)
            if prior is not None:
                if prior != event:
                    raise ValueError(f"EVENT_ID_CONFLICT:{event.event_id}")
                continue

            self.__validate_event_semantics(world, event, available_event_ids)
            batch_by_id[event.event_id] = event
            candidates.append(event)
            available_event_ids.add(event.event_id)
        return tuple(candidates)

    def __validate_event_semantics(self, world: WorldState, event: Event, available_event_ids: set[str]) -> None:
        payload: Mapping[str, object] = event.payload

        if event.event_type == "OBJECT_DAMAGED":
            object_id = str(payload.get("object_id", ""))
            obj = world.objects.get(object_id)
            if obj is None or obj.scene_id != event.scene_id:
                raise ValueError("INVALID_OBJECT_DAMAGED_EVENT")
            if payload.get("damage_state") not in {"DAMAGED", "BROKEN"}:
                raise ValueError("INVALID_OBJECT_DAMAGE_STATE")
            return

        if event.event_type == "SPEECH_UTTERED":
            actor = world.actors.get(event.actor_id or "")
            if actor is None or actor.scene_id != event.scene_id:
                raise ValueError("INVALID_SPEECH_EVENT_ACTOR")
            if payload.get("trust_class") != "UNTRUSTED_DATA":
                raise ValueError("INVALID_SPEECH_TRUST_CLASS")
            if payload.get("authority") != "NONE_OVER_TARGET_INTERNAL_STATE":
                raise ValueError("INVALID_SPEECH_AUTHORITY")
            return

        if event.event_type == "ACTOR_STRUCK":
            actor = world.actors.get(event.actor_id or "")
            target = world.actors.get(str(payload.get("target_id", "")))
            if actor is None or target is None:
                raise ValueError("INVALID_ACTOR_STRUCK_EVENT")
            if actor.scene_id != event.scene_id or target.scene_id != event.scene_id:
                raise ValueError("INVALID_ACTOR_STRUCK_SCENE")
            return

        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED":
            npc_id = str(payload.get("npc_id", ""))
            npc_actor = world.actors.get(npc_id)
            if npc_id not in world.npc_minds or npc_actor is None or npc_actor.scene_id != event.scene_id:
                raise ValueError("INVALID_NPC_KNOWLEDGE_EVENT")
            if payload.get("mode") not in {"SAW", "HEARD", "WAS_TOLD", "INFERRED", "RUMORED", "DOCUMENTED", "UNKNOWN"}:
                raise ValueError("INVALID_KNOWLEDGE_MODE")
            source_event_id = str(payload.get("source_event_id", ""))
            if source_event_id not in available_event_ids or source_event_id == event.event_id:
                raise ValueError("INVALID_KNOWLEDGE_SOURCE_EVENT")
            return

        if event.event_type == "RELATIONSHIP_CHANGED":
            npc_id = str(payload.get("npc_id", ""))
            npc_actor = world.actors.get(npc_id)
            if npc_id not in world.npc_minds or npc_actor is None or npc_actor.scene_id != event.scene_id:
                raise ValueError("INVALID_RELATIONSHIP_EVENT")
            delta = payload.get("delta")
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise ValueError("INVALID_RELATIONSHIP_DELTA")
            return

        if event.event_type == "ACTIVE_SCENE_CHANGED":
            if str(payload.get("to_scene_id", "")) not in world.scenes:
                raise ValueError("INVALID_ACTIVE_SCENE_TRANSITION")
            return

        raise ValueError(f"UNSUPPORTED_EVENT_TYPE:{event.event_type}")

    @staticmethod
    def __apply_prevalidated_events(world: WorldState, events: tuple[Event, ...]) -> None:
        for event in events:
            world.event_log.append(event)
            world.committed_event_ids.add(event.event_id)
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
