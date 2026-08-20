from __future__ import annotations

import copy
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
    _state: WorldState = field(repr=False, compare=False)

    def instantiate(self) -> WorldState:
        return copy.deepcopy(self._state)


def capture_pristine_baseline(world: WorldState) -> WorldBaseline:
    if world.event_log or world.committed_event_ids or world.state_version != 0:
        raise ValueError("BASELINE_MUST_BE_PRISTINE")
    if not world.baseline_version or world.baseline_version == "R001-UNVERSIONED":
        raise ValueError("BASELINE_VERSION_REQUIRED")
    return WorldBaseline(world.baseline_version, copy.deepcopy(world))
