from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


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


@dataclass(frozen=True)
class AuthorityScope:
    may_control_actor: bool = True
    may_control_target_internal_state: bool = False
    may_modify_world_rules: bool = False


@dataclass
class Action:
    action_id: str
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
    payload: dict[str, Any]
    caused_by_action_id: str | None = None


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
    actors: dict[str, ActorState] = field(default_factory=dict)
    objects: dict[str, ObjectState] = field(default_factory=dict)
    npc_minds: dict[str, NPCMindState] = field(default_factory=dict)
    scenes: dict[str, SceneState] = field(default_factory=dict)
    event_log: list[Event] = field(default_factory=list)

    def entity_exists(self, entity_id: str) -> bool:
        return (
            entity_id in self.actors
            or entity_id in self.objects
            or entity_id in self.npc_minds
            or entity_id in self.scenes
        )
