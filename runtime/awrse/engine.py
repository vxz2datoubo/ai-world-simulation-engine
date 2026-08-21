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

        elif event.event_type == "ACTOR_MOVED":
            actor_id = str(event.payload["actor_id"])
            to_zone_id = str(event.payload["to_zone_id"])
            actor = world.actors[actor_id]
            actor.zone_id = to_zone_id
            for object_id in tuple(actor.inventory_refs):
                obj = world.objects[object_id]
                obj.scene_id = actor.scene_id
                obj.zone_id = to_zone_id
            delta = f"{actor_id}:zone_id={to_zone_id}"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type == "OBJECT_PICKED_UP":
            object_id = str(event.payload["object_id"])
            actor_id = str(event.payload["actor_id"])
            actor = world.actors[actor_id]
            obj = world.objects[object_id]
            if object_id not in actor.inventory_refs:
                actor.inventory_refs.append(object_id)
            actor.free_hands -= 1
            obj.owner_actor_id = actor_id
            obj.scene_id = actor.scene_id
            obj.zone_id = actor.zone_id
            delta = f"{object_id}:owner_actor_id={actor_id}"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type in {"OBJECT_DROPPED", "OBJECT_THROWN"}:
            object_id = str(event.payload["object_id"])
            actor_id = str(event.payload["actor_id"])
            zone_id = str(event.payload["zone_id"])
            actor = world.actors[actor_id]
            obj = world.objects[object_id]
            if object_id in actor.inventory_refs:
                actor.inventory_refs.remove(object_id)
            actor.free_hands += 1
            obj.owner_actor_id = None
            obj.scene_id = actor.scene_id
            obj.zone_id = zone_id
            delta = f"{object_id}:owner_actor_id=None:zone_id={zone_id}"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type == "OBJECT_OPENED":
            object_id = str(event.payload["object_id"])
            world.objects[object_id].is_open = True
            delta = f"{object_id}:is_open=True"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)

        elif event.event_type == "OBJECT_CLOSED":
            object_id = str(event.payload["object_id"])
            world.objects[object_id].is_open = False
            delta = f"{object_id}:is_open=False"
            if delta not in scene.persistent_delta_refs:
                scene.persistent_delta_refs.append(delta)


class SimulationEngine:
    _event_counter = itertools.count(1)
    _r002_player_verbs = frozenset({"PICK", "DROP", "THROW", "OPEN", "CLOSE", "WALK"})
    _single_object_target_verbs = frozenset({"PICK", "DROP", "THROW", "OPEN", "CLOSE"})
    _visual_witness_object_event_types = frozenset(
        {
            "OBJECT_DAMAGED",
            "OBJECT_PICKED_UP",
            "OBJECT_DROPPED",
            "OBJECT_THROWN",
            "OBJECT_OPENED",
            "OBJECT_CLOSED",
        }
    )
    _implemented_player_verbs = frozenset({"SPEAK", "HIT"}) | _r002_player_verbs
    _supported_event_types = frozenset(
        {
            "SPEECH_UTTERED",
            "OBJECT_DAMAGED",
            "ACTOR_STRUCK",
            "NPC_KNOWLEDGE_ACQUIRED",
            "RELATIONSHIP_CHANGED",
            "ACTIVE_SCENE_CHANGED",
            "ACTOR_MOVED",
            "OBJECT_PICKED_UP",
            "OBJECT_DROPPED",
            "OBJECT_THROWN",
            "OBJECT_OPENED",
            "OBJECT_CLOSED",
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
        if (
            not action.authority_scope.may_control_actor
            or not world.can_principal_control(action.principal_id, action.actor_id)
        ):
            return self._reject(
                action,
                ResolutionStatus.REJECTED_AUTHORITY,
                "PRINCIPAL_NOT_AUTHORIZED_FOR_ACTOR",
            )
        if (
            action.authority_scope.may_control_target_internal_state
            or action.authority_scope.may_modify_world_rules
        ):
            return self._reject(
                action,
                ResolutionStatus.REJECTED_AUTHORITY,
                "UNAUTHORIZED_SCOPE_ESCALATION",
            )
        if declared_superhuman_effect(action.literal_user_input):
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PHYSICS,
                "DECLARED_EFFECT_EXCEEDS_NORMAL_HUMAN_CAPABILITY",
            )

        if action.verb in self._r002_player_verbs and not world.has_symbolic_spatial_substrate:
            return self._reject(
                action,
                ResolutionStatus.RESOLVED_FAILURE,
                "UNIMPLEMENTED_ACTION_FAMILY",
            )

        if action.verb in self._single_object_target_verbs:
            if len(action.target_ids) != 1:
                return self._reject(
                    action,
                    ResolutionStatus.REJECTED_PRECONDITION,
                    "EXACTLY_ONE_OBJECT_TARGET_REQUIRED",
                )
            if action.target_ids[0] not in world.objects:
                return self._reject(
                    action,
                    ResolutionStatus.REJECTED_PRECONDITION,
                    "OBJECT_TARGET_REQUIRED",
                )

        if action.verb == "WALK":
            if len(action.target_ids) != 1 or action.target_ids[0] not in world.zone_scene_bindings:
                return self._reject(
                    action,
                    ResolutionStatus.REJECTED_PRECONDITION,
                    "EXACTLY_ONE_ZONE_TARGET_REQUIRED",
                )

        precondition_failure = self._evaluate_preconditions(action, world)
        if precondition_failure is not None:
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PRECONDITION,
                precondition_failure,
            )
        if action.verb not in self._implemented_player_verbs:
            return self._reject(
                action,
                ResolutionStatus.RESOLVED_FAILURE,
                "UNIMPLEMENTED_ACTION_FAMILY",
            )
        if action.verb == "HIT" and len(action.target_ids) > actor.max_targets_per_strike:
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PHYSICS,
                "TOO_MANY_TARGETS_FOR_SINGLE_STRIKE",
            )

        if action.verb == "SPEAK":
            return self._resolve_speech(action, world)
        if action.verb == "HIT":
            return self._resolve_hit(action, world)
        if action.verb == "PICK":
            return self._resolve_pick(action, world)
        if action.verb == "DROP":
            return self._resolve_drop_or_throw(action, world, "OBJECT_DROPPED")
        if action.verb == "THROW":
            return self._resolve_drop_or_throw(action, world, "OBJECT_THROWN")
        if action.verb == "OPEN":
            return self._resolve_open_close(action, world, opening=True)
        if action.verb == "CLOSE":
            return self._resolve_open_close(action, world, opening=False)
        if action.verb == "WALK":
            return self._resolve_walk(action, world)
        return self._reject(
            action,
            ResolutionStatus.RESOLVED_FAILURE,
            "UNIMPLEMENTED_ACTION_FAMILY",
        )

    def _evaluate_preconditions(self, action: Action, world: WorldState) -> str | None:
        required_by_verb = {
            "HIT": {"TARGET_REACHABLE", "CAPABILITY_PRESENT"},
            "SPEAK": {"CAPABILITY_PRESENT"},
            "PICK": {
                "TARGET_REACHABLE",
                "CAPABILITY_PRESENT",
                "AFFORDANCE_PRESENT",
                "TARGET_GRASPABLE",
                "FREE_HAND_AVAILABLE",
                "TARGET_UNPOSSESSED",
            },
            "DROP": {
                "CAPABILITY_PRESENT",
                "AFFORDANCE_PRESENT",
                "POSSESSION_REQUIRED",
            },
            "THROW": {
                "CAPABILITY_PRESENT",
                "AFFORDANCE_PRESENT",
                "POSSESSION_REQUIRED",
            },
            "OPEN": {
                "TARGET_REACHABLE",
                "CAPABILITY_PRESENT",
                "AFFORDANCE_PRESENT",
            },
            "CLOSE": {
                "TARGET_REACHABLE",
                "CAPABILITY_PRESENT",
                "AFFORDANCE_PRESENT",
            },
            "WALK": {"CAPABILITY_PRESENT", "ADJACENT_ZONE"},
        }
        required = required_by_verb.get(action.verb, set())
        missing_required = required - set(action.preconditions)
        if missing_required:
            return "MISSING_REQUIRED_PRECONDITION:" + ",".join(sorted(missing_required))

        if action.verb in {"HIT", "PICK", "DROP", "THROW", "OPEN", "CLOSE", "WALK"}:
            if not action.target_ids:
                return "TARGET_REQUIRED"

        for condition in action.preconditions:
            if condition == "TARGET_EXISTS":
                if any(not world.entity_exists(target) for target in action.target_ids):
                    return "TARGET_NOT_FOUND"

            elif condition == "TARGET_REACHABLE":
                if not action.target_ids:
                    return "TARGET_REQUIRED"
                if any(
                    target not in world.objects and target not in world.actors
                    for target in action.target_ids
                ):
                    return "TARGET_NOT_REACHABLE"
                if any(
                    not world.is_reachable(action.actor_id, target)
                    for target in action.target_ids
                ):
                    return "TARGET_NOT_REACHABLE"

            elif condition == "CAPABILITY_PRESENT":
                if action.verb not in world.actors[action.actor_id].capabilities:
                    return "CAPABILITY_MISSING"

            elif condition == "AFFORDANCE_PRESENT":
                for target_id in action.target_ids:
                    obj = world.objects.get(target_id)
                    if obj is None:
                        return "OBJECT_TARGET_REQUIRED"
                    if action.verb not in obj.affordances:
                        return "AFFORDANCE_MISSING"

            elif condition == "TARGET_GRASPABLE":
                for target_id in action.target_ids:
                    obj = world.objects.get(target_id)
                    if obj is None or not obj.graspable:
                        return "TARGET_NOT_GRASPABLE"

            elif condition == "FREE_HAND_AVAILABLE":
                if world.actors[action.actor_id].free_hands <= 0:
                    return "NO_FREE_HAND"

            elif condition == "TARGET_UNPOSSESSED":
                for target_id in action.target_ids:
                    obj = world.objects.get(target_id)
                    if obj is None:
                        return "OBJECT_TARGET_REQUIRED"
                    if obj.owner_actor_id is not None:
                        return "TARGET_ALREADY_POSSESSED"

            elif condition == "POSSESSION_REQUIRED":
                actor = world.actors[action.actor_id]
                for target_id in action.target_ids:
                    obj = world.objects.get(target_id)
                    if (
                        obj is None
                        or obj.owner_actor_id != action.actor_id
                        or target_id not in actor.inventory_refs
                    ):
                        return "OBJECT_NOT_POSSESSED"

            elif condition == "ADJACENT_ZONE":
                target_zone_ids = [
                    target
                    for target in action.target_ids
                    if target in world.zone_scene_bindings
                ]
                if len(target_zone_ids) != 1:
                    return "ZONE_TARGET_REQUIRED"
                target_zone_id = target_zone_ids[0]
                actor = world.actors[action.actor_id]
                if actor.zone_id == target_zone_id:
                    return "ALREADY_IN_TARGET_ZONE"
                if not world.zone_is_adjacent(action.actor_id, target_zone_id):
                    return "TARGET_ZONE_NOT_ADJACENT"

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
            events = self._with_visual_witnesses(object_event, action, world, target_id)
            action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
            action.failure_reason = None
            return Resolution(action, events)

        event = self._event(
            "ACTOR_STRUCK",
            action,
            world,
            {"target_id": target_id, "effect": "NORMAL_HUMAN_STRIKE"},
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, (event,))

    def _resolve_pick(self, action: Action, world: WorldState) -> Resolution:
        target_id = action.target_ids[0]
        actor = world.actors[action.actor_id]
        obj = world.objects[target_id]
        event = self._event(
            "OBJECT_PICKED_UP",
            action,
            world,
            {
                "object_id": target_id,
                "actor_id": action.actor_id,
                "from_zone_id": obj.zone_id,
                "to_zone_id": actor.zone_id,
            },
        )
        events = self._with_visual_witnesses(event, action, world, target_id)
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, events)

    def _resolve_drop_or_throw(
        self,
        action: Action,
        world: WorldState,
        event_type: str,
    ) -> Resolution:
        target_id = action.target_ids[0]
        actor = world.actors[action.actor_id]
        event = self._event(
            event_type,
            action,
            world,
            {
                "object_id": target_id,
                "actor_id": action.actor_id,
                "zone_id": actor.zone_id,
            },
        )
        events = self._with_visual_witnesses(event, action, world, target_id)
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, events)

    def _resolve_open_close(
        self,
        action: Action,
        world: WorldState,
        *,
        opening: bool,
    ) -> Resolution:
        target_id = action.target_ids[0]
        obj = world.objects[target_id]
        if opening and obj.is_open:
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PRECONDITION,
                "OBJECT_ALREADY_OPEN",
            )
        if not opening and not obj.is_open:
            return self._reject(
                action,
                ResolutionStatus.REJECTED_PRECONDITION,
                "OBJECT_ALREADY_CLOSED",
            )
        event = self._event(
            "OBJECT_OPENED" if opening else "OBJECT_CLOSED",
            action,
            world,
            {"object_id": target_id, "actor_id": action.actor_id},
        )
        events = self._with_visual_witnesses(event, action, world, target_id)
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, events)

    def _resolve_walk(self, action: Action, world: WorldState) -> Resolution:
        actor = world.actors[action.actor_id]
        target_zone_id = next(
            target
            for target in action.target_ids
            if target in world.zone_scene_bindings
        )
        event = self._event(
            "ACTOR_MOVED",
            action,
            world,
            {
                "actor_id": action.actor_id,
                "from_zone_id": actor.zone_id,
                "to_zone_id": target_zone_id,
            },
        )
        action.resolution_status = ResolutionStatus.RESOLVED_SUCCESS
        action.failure_reason = None
        return Resolution(action, (event,))

    def _with_visual_witnesses(
        self,
        primary_event: Event,
        action: Action,
        world: WorldState,
        observed_entity_id: str,
    ) -> tuple[Event, ...]:
        events: list[Event] = [primary_event]
        for npc_id in sorted(world.npc_minds):
            if not world.can_see(observed_entity_id, npc_id):
                continue
            events.append(
                self._event(
                    "NPC_KNOWLEDGE_ACQUIRED",
                    action,
                    world,
                    {
                        "npc_id": npc_id,
                        "mode": "SAW",
                        "source_event_id": primary_event.event_id,
                        "observed_entity_id": observed_entity_id,
                    },
                )
            )
        return tuple(events)

    def __commit_events(self, world: WorldState, events: Iterable[Event]) -> None:
        new_events = self.__prevalidate_event_batch(world, tuple(events))
        if not new_events:
            return

        staged = _clone_world_state(world)
        self.__apply_prevalidated_events(staged, new_events)
        staged._seal_graph_authorized(_LIVE_MUTATION_TOKEN)
        world._adopt_authorized_state(staged, _LIVE_MUTATION_TOKEN)

    def __prevalidate_event_batch(
        self,
        world: WorldState,
        events: tuple[Event, ...],
    ) -> tuple[Event, ...]:
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
        available_events: dict[str, Event] = dict(existing_by_id)
        semantic_world = _clone_world_state(world)

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

            self.__validate_event_semantics(
                semantic_world,
                event,
                available_events,
            )
            batch_by_id[event.event_id] = event
            candidates.append(event)
            available_events[event.event_id] = event
            self.__apply_prevalidated_events(semantic_world, (event,))

        return tuple(candidates)

    def __validate_event_semantics(
        self,
        world: WorldState,
        event: Event,
        available_events: Mapping[str, Event],
    ) -> None:
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
            if (
                npc_id not in world.npc_minds
                or npc_actor is None
                or npc_actor.scene_id != event.scene_id
            ):
                raise ValueError("INVALID_NPC_KNOWLEDGE_EVENT")
            mode = payload.get("mode")
            if mode not in {
                "SAW",
                "HEARD",
                "WAS_TOLD",
                "INFERRED",
                "RUMORED",
                "DOCUMENTED",
                "UNKNOWN",
            }:
                raise ValueError("INVALID_KNOWLEDGE_MODE")
            source_event_id = str(payload.get("source_event_id", ""))
            source_event = available_events.get(source_event_id)
            if source_event is None or source_event_id == event.event_id:
                raise ValueError("INVALID_KNOWLEDGE_SOURCE_EVENT")

            if mode == "SAW":
                if source_event.event_type not in self._visual_witness_object_event_types:
                    raise ValueError("INVALID_SAW_SOURCE_EVENT_TYPE")
                if source_event.scene_id != event.scene_id:
                    raise ValueError("INVALID_SAW_SOURCE_SCENE")
                observed_entity_id = str(payload.get("observed_entity_id", ""))
                source_object_id = str(source_event.payload.get("object_id", ""))
                if not observed_entity_id or observed_entity_id != source_object_id:
                    raise ValueError("INVALID_SAW_OBSERVED_ENTITY")
                observed_object = world.objects.get(observed_entity_id)
                if observed_object is None or observed_object.scene_id != event.scene_id:
                    raise ValueError("INVALID_SAW_OBSERVED_OBJECT_SCENE")
                if not world.can_see(observed_entity_id, npc_id):
                    raise ValueError("INVALID_SAW_VISIBILITY_PATH")
            return

        if event.event_type == "RELATIONSHIP_CHANGED":
            npc_id = str(payload.get("npc_id", ""))
            npc_actor = world.actors.get(npc_id)
            if (
                npc_id not in world.npc_minds
                or npc_actor is None
                or npc_actor.scene_id != event.scene_id
            ):
                raise ValueError("INVALID_RELATIONSHIP_EVENT")
            delta = payload.get("delta")
            if isinstance(delta, bool) or not isinstance(delta, int):
                raise ValueError("INVALID_RELATIONSHIP_DELTA")
            return

        if event.event_type == "ACTIVE_SCENE_CHANGED":
            if str(payload.get("to_scene_id", "")) not in world.scenes:
                raise ValueError("INVALID_ACTIVE_SCENE_TRANSITION")
            return

        if event.event_type == "ACTOR_MOVED":
            world._validate_spatial_integrity()
            actor_id = str(payload.get("actor_id", ""))
            actor = world.actors.get(actor_id)
            from_zone_id = payload.get("from_zone_id")
            to_zone_id = str(payload.get("to_zone_id", ""))
            if actor is None or actor_id != event.actor_id:
                raise ValueError("INVALID_ACTOR_MOVED_EVENT")
            if actor.scene_id != event.scene_id:
                raise ValueError("INVALID_ACTOR_MOVED_SCENE")
            if actor.zone_id != from_zone_id:
                raise ValueError("INVALID_ACTOR_MOVED_FROM_ZONE")
            if not world.zone_is_adjacent(actor_id, to_zone_id):
                raise ValueError("INVALID_ACTOR_MOVED_TOPOLOGY")
            return

        if event.event_type == "OBJECT_PICKED_UP":
            world._validate_spatial_integrity()
            world._validate_possession_integrity()
            object_id = str(payload.get("object_id", ""))
            actor_id = str(payload.get("actor_id", ""))
            actor = world.actors.get(actor_id)
            obj = world.objects.get(object_id)
            if actor is None or obj is None or actor_id != event.actor_id:
                raise ValueError("INVALID_OBJECT_PICKED_UP_EVENT")
            if actor.scene_id != event.scene_id or obj.scene_id != event.scene_id:
                raise ValueError("INVALID_OBJECT_PICKED_UP_SCENE")
            if obj.owner_actor_id is not None or object_id in actor.inventory_refs:
                raise ValueError("INVALID_OBJECT_PICKED_UP_POSSESSION")
            if actor.free_hands <= 0:
                raise ValueError("INVALID_OBJECT_PICKED_UP_HAND_STATE")
            if not obj.graspable or "PICK" not in obj.affordances:
                raise ValueError("INVALID_OBJECT_PICKED_UP_AFFORDANCE")
            if not world.is_reachable(actor_id, object_id):
                raise ValueError("INVALID_OBJECT_PICKED_UP_REACHABILITY")

            from_zone_id = payload.get("from_zone_id")
            to_zone_id = payload.get("to_zone_id")
            if from_zone_id != obj.zone_id:
                raise ValueError("INVALID_OBJECT_PICKED_UP_FROM_ZONE")
            if to_zone_id != actor.zone_id:
                raise ValueError("INVALID_OBJECT_PICKED_UP_TO_ZONE")
            if not world._zone_matches_scene(obj.zone_id, obj.scene_id):
                raise ValueError("INVALID_OBJECT_PICKED_UP_FROM_ZONE_BINDING")
            if not world._zone_matches_scene(actor.zone_id, actor.scene_id):
                raise ValueError("INVALID_OBJECT_PICKED_UP_TO_ZONE_BINDING")
            return

        if event.event_type in {"OBJECT_DROPPED", "OBJECT_THROWN"}:
            world._validate_spatial_integrity()
            world._validate_possession_integrity()
            object_id = str(payload.get("object_id", ""))
            actor_id = str(payload.get("actor_id", ""))
            actor = world.actors.get(actor_id)
            obj = world.objects.get(object_id)
            zone_id = str(payload.get("zone_id", ""))
            required_affordance = (
                "DROP" if event.event_type == "OBJECT_DROPPED" else "THROW"
            )
            if actor is None or obj is None or actor_id != event.actor_id:
                raise ValueError("INVALID_OBJECT_RELEASE_EVENT")
            if actor.scene_id != event.scene_id or obj.scene_id != event.scene_id:
                raise ValueError("INVALID_OBJECT_RELEASE_SCENE")
            if obj.owner_actor_id != actor_id or object_id not in actor.inventory_refs:
                raise ValueError("INVALID_OBJECT_RELEASE_POSSESSION")
            if required_affordance not in obj.affordances:
                raise ValueError("INVALID_OBJECT_RELEASE_AFFORDANCE")
            if zone_id != actor.zone_id:
                raise ValueError("INVALID_OBJECT_RELEASE_ZONE")
            return

        if event.event_type in {"OBJECT_OPENED", "OBJECT_CLOSED"}:
            world._validate_spatial_integrity()
            object_id = str(payload.get("object_id", ""))
            actor_id = str(payload.get("actor_id", ""))
            actor = world.actors.get(actor_id)
            obj = world.objects.get(object_id)
            required_affordance = (
                "OPEN" if event.event_type == "OBJECT_OPENED" else "CLOSE"
            )
            if actor is None or obj is None or actor_id != event.actor_id:
                raise ValueError("INVALID_OBJECT_OPEN_CLOSE_EVENT")
            if actor.scene_id != event.scene_id or obj.scene_id != event.scene_id:
                raise ValueError("INVALID_OBJECT_OPEN_CLOSE_SCENE")
            if required_affordance not in obj.affordances:
                raise ValueError("INVALID_OBJECT_OPEN_CLOSE_AFFORDANCE")
            if not world.is_reachable(actor_id, object_id):
                raise ValueError("INVALID_OBJECT_OPEN_CLOSE_REACHABILITY")
            if event.event_type == "OBJECT_OPENED" and obj.is_open:
                raise ValueError("INVALID_OBJECT_ALREADY_OPEN")
            if event.event_type == "OBJECT_CLOSED" and not obj.is_open:
                raise ValueError("INVALID_OBJECT_ALREADY_CLOSED")
            return

        raise ValueError(f"UNSUPPORTED_EVENT_TYPE:{event.event_type}")

    @staticmethod
    def __apply_prevalidated_events(
        world: WorldState,
        events: tuple[Event, ...],
    ) -> None:
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
    def _reject(
        action: Action,
        status: ResolutionStatus,
        reason: str,
    ) -> Resolution:
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
