from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping


class SourceChannel(str, Enum):
    PLAYER_ACTION_DECLARATION = "PLAYER_ACTION_DECLARATION"
    PLAYER_DIEGETIC_SPEECH = "PLAYER_DIEGETIC_SPEECH"
    DIRECT_CONTROL_INPUT = "DIRECT_CONTROL_INPUT"


class ResolutionStatus(str, Enum):
    PARSED = "PARSED"
    REJECTED_AUTHORITY = "REJECTED_AUTHORITY"
    REJECTED_PRECONDITION = "REJECTED_PRECONDITION"
    REJECTED_PHYSICS = "REJECTED_PHYSICS"
    RESOLVED_SUCCESS = "RESOLVED_SUCCESS"
    RESOLVED_PARTIAL = "RESOLVED_PARTIAL"
    RESOLVED_FAILURE = "RESOLVED_FAILURE"
    UNKNOWN_REQUIRES_DISAMBIGUATION = "UNKNOWN_REQUIRES_DISAMBIGUATION"


def freeze_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return MappingProxyType({key: freeze_value(item) for key, item in value.items()})
    if isinstance(value, list):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, tuple):
        return tuple(freeze_value(item) for item in value)
    if isinstance(value, set):
        return frozenset(freeze_value(item) for item in value)
    return value


def thaw_value(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): thaw_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [thaw_value(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((thaw_value(item) for item in value), key=repr)
    return value


@dataclass(frozen=True)
class AuthorityScope:
    may_control_actor: bool = False
    may_control_target_internal_state: bool = False
    may_modify_world_rules: bool = False


@dataclass
class Action:
    action_id: str
    principal_id: str | None
    actor_id: str
    verb: str
    source_channel: SourceChannel
    literal_user_input: str
    target_ids: list[str] = field(default_factory=list)
    instrument_ids: list[str] = field(default_factory=list)
    declared_intent: dict[str, Any] = field(default_factory=dict)
    preconditions: list[str] = field(default_factory=list)
    authority_scope: AuthorityScope = field(default_factory=AuthorityScope)
    resolution_status: ResolutionStatus = ResolutionStatus.PARSED
    failure_reason: str | None = None


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    actor_id: str | None
    scene_id: str
    baseline_version: str
    payload: Mapping[str, Any]
    caused_by_action_id: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "payload", freeze_value(dict(self.payload)))


@dataclass
class ActorState:
    actor_id: str
    name: str
    scene_id: str
    strength: float = 1.0
    fatigue: float = 0.0
    injury: float = 0.0
    free_hands: int = 2
    inventory_refs: list[str] = field(default_factory=list)
    max_targets_per_strike: int = 1
    capabilities: set[str] = field(default_factory=lambda: {"SPEAK", "HIT"})


@dataclass
class ObjectState:
    object_id: str
    name: str
    scene_id: str
    mass: float = 1.0
    graspable: bool = True
    fragility: float = 0.5
    damage_state: str = "INTACT"
    contamination_state: str = "CLEAN"


@dataclass
class NPCMindState:
    npc_id: str
    role: str
    beliefs: list[str] = field(default_factory=list)
    memories: list[str] = field(default_factory=list)
    emotion_state: str = "NEUTRAL"
    relationship_to_player: int = 0
    knowledge_boundary_refs: list[str] = field(default_factory=list)


@dataclass
class SceneState:
    scene_id: str
    base_asset_refs: list[str] = field(default_factory=list)
    object_state_refs: list[str] = field(default_factory=list)
    actor_state_refs: list[str] = field(default_factory=list)
    persistent_delta_refs: list[str] = field(default_factory=list)
    relevant_event_refs: list[str] = field(default_factory=list)


@dataclass
class WorldState:
    world_id: str
    active_scene_id: str
    baseline_version: str = "R001-UNVERSIONED"
    state_version: int = 0
    primary_player_actor_id: str = "PLAYER"
    actors: dict[str, ActorState] = field(default_factory=dict)
    objects: dict[str, ObjectState] = field(default_factory=dict)
    npc_minds: dict[str, NPCMindState] = field(default_factory=dict)
    scenes: dict[str, SceneState] = field(default_factory=dict)
    event_log: list[Event] = field(default_factory=list)
    committed_event_ids: set[str] = field(default_factory=set)
    principal_actor_bindings: dict[str, set[str]] = field(default_factory=dict)
    reachable_pairs: set[tuple[str, str]] = field(default_factory=set)
    audible_pairs: set[tuple[str, str]] = field(default_factory=set)
    visible_pairs: set[tuple[str, str]] = field(default_factory=set)

    @property
    def world_state_version(self) -> str:
        return f"{self.baseline_version}:{self.state_version}"

    def entity_exists(self, entity_id: str) -> bool:
        return (
            entity_id in self.actors
            or entity_id in self.objects
            or entity_id in self.npc_minds
            or entity_id in self.scenes
        )

    def can_principal_control(self, principal_id: str | None, actor_id: str) -> bool:
        if principal_id is None:
            return False
        return actor_id in self.principal_actor_bindings.get(principal_id, set())

    def is_reachable(self, actor_id: str, target_id: str) -> bool:
        actor = self.actors.get(actor_id)
        if actor is None:
            return False
        target_scene = None
        if target_id in self.actors:
            target_scene = self.actors[target_id].scene_id
        elif target_id in self.objects:
            target_scene = self.objects[target_id].scene_id
        if target_scene != actor.scene_id:
            return False
        return (actor_id, target_id) in self.reachable_pairs

    def can_hear(self, speaker_id: str, listener_id: str) -> bool:
        speaker = self.actors.get(speaker_id)
        listener = self.actors.get(listener_id)
        if speaker is None or listener is None or speaker.scene_id != listener.scene_id:
            return False
        return (speaker_id, listener_id) in self.audible_pairs

    def can_see(self, entity_id: str, observer_id: str) -> bool:
        observer = self.actors.get(observer_id)
        if observer is None:
            return False
        if entity_id in self.objects:
            entity_scene = self.objects[entity_id].scene_id
        elif entity_id in self.actors:
            entity_scene = self.actors[entity_id].scene_id
        else:
            return False
        if entity_scene != observer.scene_id:
            return False
        return (entity_id, observer_id) in self.visible_pairs


@dataclass(frozen=True)
class WorldBaseline:
    baseline_version: str
    snapshot_digest: str
    _snapshot: bytes = field(repr=False, compare=False)

    def instantiate(self) -> WorldState:
        actual_digest = hashlib.sha256(self._snapshot).hexdigest()
        if actual_digest != self.snapshot_digest:
            raise ValueError("BASELINE_SNAPSHOT_INTEGRITY_FAILURE")
        rebuilt = _decode_world_snapshot(self._snapshot)
        if rebuilt.baseline_version != self.baseline_version:
            raise ValueError("BASELINE_VERSION_MISMATCH")
        return rebuilt


def _event_to_data(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "scene_id": event.scene_id,
        "baseline_version": event.baseline_version,
        "payload": thaw_value(event.payload),
        "caused_by_action_id": event.caused_by_action_id,
    }


def _world_to_data(world: WorldState) -> dict[str, Any]:
    return {
        "world_id": world.world_id,
        "active_scene_id": world.active_scene_id,
        "baseline_version": world.baseline_version,
        "state_version": world.state_version,
        "primary_player_actor_id": world.primary_player_actor_id,
        "actors": {
            actor_id: {
                "actor_id": actor.actor_id,
                "name": actor.name,
                "scene_id": actor.scene_id,
                "strength": actor.strength,
                "fatigue": actor.fatigue,
                "injury": actor.injury,
                "free_hands": actor.free_hands,
                "inventory_refs": list(actor.inventory_refs),
                "max_targets_per_strike": actor.max_targets_per_strike,
                "capabilities": sorted(actor.capabilities),
            }
            for actor_id, actor in world.actors.items()
        },
        "objects": {
            object_id: {
                "object_id": obj.object_id,
                "name": obj.name,
                "scene_id": obj.scene_id,
                "mass": obj.mass,
                "graspable": obj.graspable,
                "fragility": obj.fragility,
                "damage_state": obj.damage_state,
                "contamination_state": obj.contamination_state,
            }
            for object_id, obj in world.objects.items()
        },
        "npc_minds": {
            npc_id: {
                "npc_id": npc.npc_id,
                "role": npc.role,
                "beliefs": list(npc.beliefs),
                "memories": list(npc.memories),
                "emotion_state": npc.emotion_state,
                "relationship_to_player": npc.relationship_to_player,
                "knowledge_boundary_refs": list(npc.knowledge_boundary_refs),
            }
            for npc_id, npc in world.npc_minds.items()
        },
        "scenes": {
            scene_id: {
                "scene_id": scene.scene_id,
                "base_asset_refs": list(scene.base_asset_refs),
                "object_state_refs": list(scene.object_state_refs),
                "actor_state_refs": list(scene.actor_state_refs),
                "persistent_delta_refs": list(scene.persistent_delta_refs),
                "relevant_event_refs": list(scene.relevant_event_refs),
            }
            for scene_id, scene in world.scenes.items()
        },
        "event_log": [_event_to_data(event) for event in world.event_log],
        "committed_event_ids": sorted(world.committed_event_ids),
        "principal_actor_bindings": {
            principal_id: sorted(actor_ids)
            for principal_id, actor_ids in world.principal_actor_bindings.items()
        },
        "reachable_pairs": [list(pair) for pair in sorted(world.reachable_pairs)],
        "audible_pairs": [list(pair) for pair in sorted(world.audible_pairs)],
        "visible_pairs": [list(pair) for pair in sorted(world.visible_pairs)],
    }


def _world_from_data(data: Mapping[str, Any]) -> WorldState:
    actors = {
        actor_id: ActorState(
            actor_id=str(item["actor_id"]),
            name=str(item["name"]),
            scene_id=str(item["scene_id"]),
            strength=float(item["strength"]),
            fatigue=float(item["fatigue"]),
            injury=float(item["injury"]),
            free_hands=int(item["free_hands"]),
            inventory_refs=[str(value) for value in item["inventory_refs"]],
            max_targets_per_strike=int(item["max_targets_per_strike"]),
            capabilities={str(value) for value in item["capabilities"]},
        )
        for actor_id, item in data["actors"].items()
    }
    objects = {
        object_id: ObjectState(
            object_id=str(item["object_id"]),
            name=str(item["name"]),
            scene_id=str(item["scene_id"]),
            mass=float(item["mass"]),
            graspable=bool(item["graspable"]),
            fragility=float(item["fragility"]),
            damage_state=str(item["damage_state"]),
            contamination_state=str(item["contamination_state"]),
        )
        for object_id, item in data["objects"].items()
    }
    npc_minds = {
        npc_id: NPCMindState(
            npc_id=str(item["npc_id"]),
            role=str(item["role"]),
            beliefs=[str(value) for value in item["beliefs"]],
            memories=[str(value) for value in item["memories"]],
            emotion_state=str(item["emotion_state"]),
            relationship_to_player=int(item["relationship_to_player"]),
            knowledge_boundary_refs=[str(value) for value in item["knowledge_boundary_refs"]],
        )
        for npc_id, item in data["npc_minds"].items()
    }
    scenes = {
        scene_id: SceneState(
            scene_id=str(item["scene_id"]),
            base_asset_refs=[str(value) for value in item["base_asset_refs"]],
            object_state_refs=[str(value) for value in item["object_state_refs"]],
            actor_state_refs=[str(value) for value in item["actor_state_refs"]],
            persistent_delta_refs=[str(value) for value in item["persistent_delta_refs"]],
            relevant_event_refs=[str(value) for value in item["relevant_event_refs"]],
        )
        for scene_id, item in data["scenes"].items()
    }
    events = [
        Event(
            event_id=str(item["event_id"]),
            event_type=str(item["event_type"]),
            actor_id=None if item["actor_id"] is None else str(item["actor_id"]),
            scene_id=str(item["scene_id"]),
            baseline_version=str(item["baseline_version"]),
            payload=dict(item["payload"]),
            caused_by_action_id=(
                None if item["caused_by_action_id"] is None else str(item["caused_by_action_id"])
            ),
        )
        for item in data["event_log"]
    ]
    return WorldState(
        world_id=str(data["world_id"]),
        active_scene_id=str(data["active_scene_id"]),
        baseline_version=str(data["baseline_version"]),
        state_version=int(data["state_version"]),
        primary_player_actor_id=str(data["primary_player_actor_id"]),
        actors=actors,
        objects=objects,
        npc_minds=npc_minds,
        scenes=scenes,
        event_log=events,
        committed_event_ids={str(value) for value in data["committed_event_ids"]},
        principal_actor_bindings={
            str(principal_id): {str(actor_id) for actor_id in actor_ids}
            for principal_id, actor_ids in data["principal_actor_bindings"].items()
        },
        reachable_pairs={tuple(str(value) for value in pair) for pair in data["reachable_pairs"]},
        audible_pairs={tuple(str(value) for value in pair) for pair in data["audible_pairs"]},
        visible_pairs={tuple(str(value) for value in pair) for pair in data["visible_pairs"]},
    )


def _encode_world_snapshot(world: WorldState) -> bytes:
    return json.dumps(
        _world_to_data(world),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def _decode_world_snapshot(snapshot: bytes) -> WorldState:
    return _world_from_data(json.loads(snapshot.decode("utf-8")))


def _clone_world_state(world: WorldState) -> WorldState:
    return _decode_world_snapshot(_encode_world_snapshot(world))


def capture_pristine_baseline(world: WorldState) -> WorldBaseline:
    if world.event_log or world.committed_event_ids or world.state_version != 0:
        raise ValueError("BASELINE_MUST_BE_PRISTINE")
    if not world.baseline_version or world.baseline_version == "R001-UNVERSIONED":
        raise ValueError("BASELINE_VERSION_REQUIRED")
    snapshot = _encode_world_snapshot(world)
    return WorldBaseline(
        baseline_version=world.baseline_version,
        snapshot_digest=hashlib.sha256(snapshot).hexdigest(),
        _snapshot=snapshot,
    )
