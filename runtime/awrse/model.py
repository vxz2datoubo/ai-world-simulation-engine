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


class _SealableState:
    __slots__ = ("_sealed",)

    def __setattr__(self, name: str, value: Any) -> None:
        if name == "_sealed":
            raise AttributeError("CANONICAL_SEAL_STATE_IS_INTERNAL")
        if getattr(self, "_sealed", False):
            raise AttributeError("LIVE_CANONICAL_STATE_IS_READ_ONLY")
        object.__setattr__(self, name, value)

    def __delattr__(self, name: str) -> None:
        if name == "_sealed":
            raise AttributeError("CANONICAL_SEAL_STATE_IS_INTERNAL")
        if getattr(self, "_sealed", False):
            raise AttributeError("LIVE_CANONICAL_STATE_IS_READ_ONLY")
        object.__delattr__(self, name)

    def _seal_read_only(self) -> None:
        object.__setattr__(self, "_sealed", True)

    @property
    def is_read_only(self) -> bool:
        return bool(getattr(self, "_sealed", False))


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


@dataclass(slots=True)
class ActorState(_SealableState):
    actor_id: str
    name: str
    scene_id: str
    strength: float = 1.0
    fatigue: float = 0.0
    injury: float = 0.0
    free_hands: int = 2
    inventory_refs: list[str] | tuple[str, ...] = field(default_factory=list)
    max_targets_per_strike: int = 1
    capabilities: set[str] | frozenset[str] = field(default_factory=lambda: {"SPEAK", "HIT"})
    zone_id: str | None = None

    def _seal_graph(self) -> None:
        object.__setattr__(self, "inventory_refs", tuple(self.inventory_refs))
        object.__setattr__(self, "capabilities", frozenset(self.capabilities))
        self._seal_read_only()


@dataclass(slots=True)
class ObjectState(_SealableState):
    object_id: str
    name: str
    scene_id: str
    mass: float = 1.0
    graspable: bool = True
    fragility: float = 0.5
    damage_state: str = "INTACT"
    contamination_state: str = "CLEAN"
    zone_id: str | None = None
    affordances: set[str] | frozenset[str] = field(default_factory=set)
    is_open: bool = False
    owner_actor_id: str | None = None

    def _seal_graph(self) -> None:
        object.__setattr__(self, "affordances", frozenset(self.affordances))
        self._seal_read_only()


@dataclass(slots=True)
class NPCMindState(_SealableState):
    npc_id: str
    role: str
    beliefs: list[str] | tuple[str, ...] = field(default_factory=list)
    memories: list[str] | tuple[str, ...] = field(default_factory=list)
    emotion_state: str = "NEUTRAL"
    relationship_to_player: int = 0
    knowledge_boundary_refs: list[str] | tuple[str, ...] = field(default_factory=list)

    def _seal_graph(self) -> None:
        object.__setattr__(self, "beliefs", tuple(self.beliefs))
        object.__setattr__(self, "memories", tuple(self.memories))
        object.__setattr__(self, "knowledge_boundary_refs", tuple(self.knowledge_boundary_refs))
        self._seal_read_only()


@dataclass(slots=True)
class SceneState(_SealableState):
    scene_id: str
    base_asset_refs: list[str] | tuple[str, ...] = field(default_factory=list)
    object_state_refs: list[str] | tuple[str, ...] = field(default_factory=list)
    actor_state_refs: list[str] | tuple[str, ...] = field(default_factory=list)
    persistent_delta_refs: list[str] | tuple[str, ...] = field(default_factory=list)
    relevant_event_refs: list[str] | tuple[str, ...] = field(default_factory=list)

    def _seal_graph(self) -> None:
        object.__setattr__(self, "base_asset_refs", tuple(self.base_asset_refs))
        object.__setattr__(self, "object_state_refs", tuple(self.object_state_refs))
        object.__setattr__(self, "actor_state_refs", tuple(self.actor_state_refs))
        object.__setattr__(self, "persistent_delta_refs", tuple(self.persistent_delta_refs))
        object.__setattr__(self, "relevant_event_refs", tuple(self.relevant_event_refs))
        self._seal_read_only()


_LIVE_MUTATION_TOKEN = object()


@dataclass(slots=True)
class WorldState(_SealableState):
    world_id: str
    active_scene_id: str
    baseline_version: str = "R001-UNVERSIONED"
    state_version: int = 0
    primary_player_actor_id: str = "PLAYER"
    actors: Mapping[str, ActorState] = field(default_factory=dict)
    objects: Mapping[str, ObjectState] = field(default_factory=dict)
    npc_minds: Mapping[str, NPCMindState] = field(default_factory=dict)
    scenes: Mapping[str, SceneState] = field(default_factory=dict)
    event_log: list[Event] | tuple[Event, ...] = field(default_factory=list)
    committed_event_ids: set[str] | frozenset[str] = field(default_factory=set)
    principal_actor_bindings: Mapping[str, set[str] | frozenset[str]] = field(default_factory=dict)
    reachable_pairs: set[tuple[str, str]] | frozenset[tuple[str, str]] = field(default_factory=set)
    audible_pairs: set[tuple[str, str]] | frozenset[tuple[str, str]] = field(default_factory=set)
    visible_pairs: set[tuple[str, str]] | frozenset[tuple[str, str]] = field(default_factory=set)
    zone_scene_bindings: Mapping[str, str] = field(default_factory=dict)
    zone_adjacency_pairs: set[tuple[str, str]] | frozenset[tuple[str, str]] = field(default_factory=set)

    @property
    def world_state_version(self) -> str:
        return f"{self.baseline_version}:{self.state_version}"

    @property
    def is_live(self) -> bool:
        return self.is_read_only

    @property
    def has_symbolic_spatial_substrate(self) -> bool:
        return bool(self.zone_scene_bindings)

    def entity_exists(self, entity_id: str) -> bool:
        return (
            entity_id in self.actors
            or entity_id in self.objects
            or entity_id in self.npc_minds
            or entity_id in self.scenes
            or entity_id in self.zone_scene_bindings
        )

    def can_principal_control(self, principal_id: str | None, actor_id: str) -> bool:
        if principal_id is None:
            return False
        return actor_id in self.principal_actor_bindings.get(principal_id, frozenset())

    def _symbolic_spatial_claimed(self) -> bool:
        return bool(
            self.zone_scene_bindings
            or self.zone_adjacency_pairs
            or any(actor.zone_id is not None for actor in self.actors.values())
            or any(obj.zone_id is not None for obj in self.objects.values())
        )

    def _zone_matches_scene(self, zone_id: str | None, scene_id: str) -> bool:
        if zone_id is None:
            return False
        return self.zone_scene_bindings.get(zone_id) == scene_id

    def _validate_spatial_integrity(self) -> None:
        if not self._symbolic_spatial_claimed():
            return
        if not self.zone_scene_bindings:
            raise ValueError("SPATIAL_ZONE_BINDINGS_REQUIRED")

        for zone_id, scene_id in self.zone_scene_bindings.items():
            if not zone_id or scene_id not in self.scenes:
                raise ValueError(f"INVALID_ZONE_SCENE_BINDING:{zone_id}")

        for actor_id, actor in self.actors.items():
            if actor.zone_id is None:
                continue
            if actor.zone_id not in self.zone_scene_bindings:
                raise ValueError(f"ACTOR_ZONE_UNKNOWN:{actor_id}:{actor.zone_id}")
            if not self._zone_matches_scene(actor.zone_id, actor.scene_id):
                raise ValueError(f"ACTOR_ZONE_SCENE_MISMATCH:{actor_id}:{actor.zone_id}")

        for object_id, obj in self.objects.items():
            if obj.zone_id is None:
                continue
            if obj.zone_id not in self.zone_scene_bindings:
                raise ValueError(f"OBJECT_ZONE_UNKNOWN:{object_id}:{obj.zone_id}")
            if not self._zone_matches_scene(obj.zone_id, obj.scene_id):
                raise ValueError(f"OBJECT_ZONE_SCENE_MISMATCH:{object_id}:{obj.zone_id}")

        for pair in self.zone_adjacency_pairs:
            if len(pair) != 2:
                raise ValueError("INVALID_ZONE_ADJACENCY_PAIR")
            left, right = pair
            if left not in self.zone_scene_bindings or right not in self.zone_scene_bindings:
                raise ValueError(f"ZONE_ADJACENCY_UNKNOWN_ENDPOINT:{left}:{right}")
            if self.zone_scene_bindings[left] != self.zone_scene_bindings[right]:
                raise ValueError(f"ZONE_ADJACENCY_CROSS_SCENE:{left}:{right}")

    def is_reachable(self, actor_id: str, target_id: str) -> bool:
        actor = self.actors.get(actor_id)
        if actor is None:
            return False
        possessed_by_actor = False
        if target_id in self.actors:
            target = self.actors[target_id]
            target_scene = target.scene_id
            target_zone = target.zone_id
        elif target_id in self.objects:
            target = self.objects[target_id]
            possessed_by_actor = target.owner_actor_id == actor_id
            target_scene = target.scene_id
            target_zone = target.zone_id
        else:
            return False

        if target_scene != actor.scene_id:
            return False
        if self._symbolic_spatial_claimed():
            if not self._zone_matches_scene(actor.zone_id, actor.scene_id):
                return False
            if not self._zone_matches_scene(target_zone, target_scene):
                return False
            if actor.zone_id != target_zone:
                return False
            if possessed_by_actor:
                return target_id in actor.inventory_refs
            return True
        if possessed_by_actor:
            return target_id in actor.inventory_refs
        return (actor_id, target_id) in self.reachable_pairs

    def zone_is_adjacent(self, actor_id: str, target_zone_id: str) -> bool:
        actor = self.actors.get(actor_id)
        if actor is None or actor.zone_id is None:
            return False
        if not self._zone_matches_scene(actor.zone_id, actor.scene_id):
            return False
        if target_zone_id not in self.zone_scene_bindings:
            return False
        if self.zone_scene_bindings[target_zone_id] != actor.scene_id:
            return False
        pair = (actor.zone_id, target_zone_id)
        reverse = (target_zone_id, actor.zone_id)
        return pair in self.zone_adjacency_pairs or reverse in self.zone_adjacency_pairs

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
        return entity_scene == observer.scene_id and (entity_id, observer_id) in self.visible_pairs

    def seal_live(self) -> None:
        """Seal pristine bootstrap/config state into caller-read-only live canonical state."""
        if self.is_live:
            return
        if self.event_log or self.committed_event_ids or self.state_version != 0:
            raise ValueError("UNTRUSTED_EVENTFUL_BOOTSTRAP_STATE")
        self._validate_spatial_integrity()
        self._seal_graph_authorized(_LIVE_MUTATION_TOKEN)

    def _seal_graph_authorized(self, token: object) -> None:
        if token is not _LIVE_MUTATION_TOKEN:
            raise PermissionError("CANONICAL_MUTATION_CAPABILITY_REQUIRED")
        if self.is_live:
            return
        self._validate_spatial_integrity()
        for actor in self.actors.values():
            actor._seal_graph()
        for obj in self.objects.values():
            obj._seal_graph()
        for npc in self.npc_minds.values():
            npc._seal_graph()
        for scene in self.scenes.values():
            scene._seal_graph()
        object.__setattr__(self, "actors", MappingProxyType(dict(self.actors)))
        object.__setattr__(self, "objects", MappingProxyType(dict(self.objects)))
        object.__setattr__(self, "npc_minds", MappingProxyType(dict(self.npc_minds)))
        object.__setattr__(self, "scenes", MappingProxyType(dict(self.scenes)))
        object.__setattr__(self, "event_log", tuple(self.event_log))
        object.__setattr__(self, "committed_event_ids", frozenset(self.committed_event_ids))
        object.__setattr__(
            self,
            "principal_actor_bindings",
            MappingProxyType({principal: frozenset(actor_ids) for principal, actor_ids in self.principal_actor_bindings.items()}),
        )
        object.__setattr__(self, "reachable_pairs", frozenset(self.reachable_pairs))
        object.__setattr__(self, "audible_pairs", frozenset(self.audible_pairs))
        object.__setattr__(self, "visible_pairs", frozenset(self.visible_pairs))
        object.__setattr__(self, "zone_scene_bindings", MappingProxyType(dict(self.zone_scene_bindings)))
        object.__setattr__(self, "zone_adjacency_pairs", frozenset(self.zone_adjacency_pairs))
        self._seal_read_only()

    def _adopt_authorized_state(self, candidate: WorldState, token: object) -> None:
        if token is not _LIVE_MUTATION_TOKEN:
            raise PermissionError("CANONICAL_MUTATION_CAPABILITY_REQUIRED")
        if not candidate.is_live:
            candidate._seal_graph_authorized(token)
        for name in (
            "world_id",
            "active_scene_id",
            "baseline_version",
            "state_version",
            "primary_player_actor_id",
            "actors",
            "objects",
            "npc_minds",
            "scenes",
            "event_log",
            "committed_event_ids",
            "principal_actor_bindings",
            "reachable_pairs",
            "audible_pairs",
            "visible_pairs",
            "zone_scene_bindings",
            "zone_adjacency_pairs",
        ):
            object.__setattr__(self, name, getattr(candidate, name))
        object.__setattr__(self, "_sealed", True)


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
                "zone_id": actor.zone_id,
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
                "zone_id": obj.zone_id,
                "affordances": sorted(obj.affordances),
                "is_open": obj.is_open,
                "owner_actor_id": obj.owner_actor_id,
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
            principal: sorted(actor_ids)
            for principal, actor_ids in world.principal_actor_bindings.items()
        },
        "reachable_pairs": [list(pair) for pair in sorted(world.reachable_pairs)],
        "audible_pairs": [list(pair) for pair in sorted(world.audible_pairs)],
        "visible_pairs": [list(pair) for pair in sorted(world.visible_pairs)],
        "zone_scene_bindings": dict(world.zone_scene_bindings),
        "zone_adjacency_pairs": [list(pair) for pair in sorted(world.zone_adjacency_pairs)],
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
            inventory_refs=[str(v) for v in item["inventory_refs"]],
            max_targets_per_strike=int(item["max_targets_per_strike"]),
            capabilities={str(v) for v in item["capabilities"]},
            zone_id=None if item.get("zone_id") is None else str(item["zone_id"]),
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
            zone_id=None if item.get("zone_id") is None else str(item["zone_id"]),
            affordances={str(v) for v in item.get("affordances", [])},
            is_open=bool(item.get("is_open", False)),
            owner_actor_id=None if item.get("owner_actor_id") is None else str(item["owner_actor_id"]),
        )
        for object_id, item in data["objects"].items()
    }
    npc_minds = {
        npc_id: NPCMindState(
            npc_id=str(item["npc_id"]),
            role=str(item["role"]),
            beliefs=[str(v) for v in item["beliefs"]],
            memories=[str(v) for v in item["memories"]],
            emotion_state=str(item["emotion_state"]),
            relationship_to_player=int(item["relationship_to_player"]),
            knowledge_boundary_refs=[str(v) for v in item["knowledge_boundary_refs"]],
        )
        for npc_id, item in data["npc_minds"].items()
    }
    scenes = {
        scene_id: SceneState(
            scene_id=str(item["scene_id"]),
            base_asset_refs=[str(v) for v in item["base_asset_refs"]],
            object_state_refs=[str(v) for v in item["object_state_refs"]],
            actor_state_refs=[str(v) for v in item["actor_state_refs"]],
            persistent_delta_refs=[str(v) for v in item["persistent_delta_refs"]],
            relevant_event_refs=[str(v) for v in item["relevant_event_refs"]],
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
            caused_by_action_id=None if item["caused_by_action_id"] is None else str(item["caused_by_action_id"]),
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
        committed_event_ids={str(v) for v in data["committed_event_ids"]},
        principal_actor_bindings={
            str(p): {str(a) for a in ids}
            for p, ids in data["principal_actor_bindings"].items()
        },
        reachable_pairs={tuple(str(v) for v in pair) for pair in data["reachable_pairs"]},
        audible_pairs={tuple(str(v) for v in pair) for pair in data["audible_pairs"]},
        visible_pairs={tuple(str(v) for v in pair) for pair in data["visible_pairs"]},
        zone_scene_bindings={
            str(zone_id): str(scene_id)
            for zone_id, scene_id in data.get("zone_scene_bindings", {}).items()
        },
        zone_adjacency_pairs={
            tuple(str(v) for v in pair)
            for pair in data.get("zone_adjacency_pairs", [])
        },
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
    world._validate_spatial_integrity()
    snapshot = _encode_world_snapshot(world)
    return WorldBaseline(
        baseline_version=world.baseline_version,
        snapshot_digest=hashlib.sha256(snapshot).hexdigest(),
        _snapshot=snapshot,
    )
