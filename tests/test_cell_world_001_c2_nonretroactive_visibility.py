from dataclasses import FrozenInstanceError

import pytest

from evals.current_observation_evidence_reference import (
    CurrentObservationEvidenceError,
    assess_current_visual_observation_gap,
    capture_current_visual_observation,
)
from evals.world_echo_opportunity_reference import derive_world_echo_opportunity
from runtime.awrse import (
    ActionCompiler,
    ActorState,
    NPCMindState,
    ObjectState,
    ResolutionStatus,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
    export_solo_replay_package,
    rehydrate_solo_replay_package,
)


class _LaterCurrentVisibilityView:
    """Read-only test view: visibility changes after the historical event only."""

    def __init__(self, world: WorldState, *, entity_id: str, observer_actor_id: str):
        self._world = world
        self._entity_id = entity_id
        self._observer_actor_id = observer_actor_id

    def __getattr__(self, name):
        return getattr(self._world, name)

    def can_see(self, entity_id: str, observer_actor_id: str) -> bool:
        if entity_id == self._entity_id and observer_actor_id == self._observer_actor_id:
            return True
        return self._world.can_see(entity_id, observer_actor_id)


def _world() -> WorldState:
    return WorldState(
        world_id="CELL-WORLD-001-C2",
        active_scene_id="S1",
        baseline_version="CELL-C2-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="Player", scene_id="S1", zone_id="Z1"),
            "B": ActorState(
                actor_id="B",
                name="Event-time witness",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"SPEAK"},
            ),
            "C": ActorState(
                actor_id="C",
                name="Historical nonwitness",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"SPEAK"},
            ),
        },
        objects={
            "DOOR": ObjectState(
                object_id="DOOR",
                name="木门",
                scene_id="S1",
                zone_id="Z1",
                fragility=0.25,
            )
        },
        npc_minds={
            "B": NPCMindState(npc_id="B", role="WITNESS"),
            "C": NPCMindState(npc_id="C", role="NEWCOMER"),
        },
        scenes={
            "S1": SceneState(
                scene_id="S1",
                base_asset_refs=["asset://cell-c2-room"],
                object_state_refs=["DOOR"],
                actor_state_refs=["A", "B", "C"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        # B is event-time eligible. C is deliberately absent from every relevant
        # visibility pair until the read-only later-current view is created.
        visible_pairs={("DOOR", "B"), ("A", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _commit_historical_damage():
    world = _world()
    assert world.can_see("DOOR", "C") is False
    assert world.can_see("A", "C") is False
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    source = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    return baseline, world, source


def _assert_historical_nonwitness(world: WorldState, source_event_id: str) -> None:
    npc = world.npc_minds["C"]
    assert source_event_id not in npc.knowledge_boundary_refs
    acquisition_events = [
        event
        for event in world.event_log
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and str(event.payload.get("npc_id", "")) == "C"
        and str(event.payload.get("source_event_id", "")) == source_event_id
    ]
    assert acquisition_events == []


def test_historical_nonwitness_then_later_visibility_cannot_retroactively_mint_witness_or_cause():
    _, world, source = _commit_historical_damage()
    _assert_historical_nonwitness(world, source.event_id)
    assert source.actor_id == "A"  # simulator provenance exists

    historical = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    assert historical.status == "NO_VALID_OPPORTUNITY"
    assert historical.reason == "NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION"
    assert historical.opportunity is None

    later = _LaterCurrentVisibilityView(world, entity_id="DOOR", observer_actor_id="C")
    assert later.can_see("DOOR", "C") is True
    assert later.can_see("A", "C") is False
    _assert_historical_nonwitness(later, source.event_id)

    # Later visibility does not rewrite the historical acquisition ledger.
    after_visibility_echo = derive_world_echo_opportunity(
        world=later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    assert after_visibility_echo == historical
    assert after_visibility_echo.opportunity is None

    gap = assess_current_visual_observation_gap(
        world=later,
        observer_actor_id="C",
        entity_id="DOOR",
    )
    assert gap.visibility_eligible is True
    assert gap.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert gap.trusted_discrete_trigger_available is False
    assert gap.receipt_available is False
    assert gap.knowledge_write_authority is False
    assert gap.narrative_realization_authority is False
    assert gap.canonical_world_authority is False

    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(
            world=later,
            observer_actor_id="C",
            entity_id="DOOR",
        )


def test_later_visibility_cannot_upgrade_simulator_known_actor_into_culprit_attribution():
    _, world, source = _commit_historical_damage()
    assert source.actor_id == "A"
    later = _LaterCurrentVisibilityView(world, entity_id="DOOR", observer_actor_id="C")

    decision = derive_world_echo_opportunity(
        world=later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    assert decision.status == "NO_VALID_OPPORTUNITY"
    assert decision.opportunity is None
    assert source.event_id not in later.npc_minds["C"].knowledge_boundary_refs
    assert not any(
        event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and str(event.payload.get("npc_id", "")) == "C"
        and str(event.payload.get("source_event_id", "")) == source.event_id
        for event in later.event_log
    )


def test_later_visibility_view_is_read_only_and_does_not_mutate_world_or_knowledge():
    _, world, source = _commit_historical_damage()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_state_version = world.world_state_version
    before_damage = world.objects["DOOR"].damage_state
    before_memories = tuple(world.npc_minds["C"].memories)
    before_boundary = tuple(world.npc_minds["C"].knowledge_boundary_refs)

    later = _LaterCurrentVisibilityView(world, entity_id="DOOR", observer_actor_id="C")
    gap = assess_current_visual_observation_gap(
        world=later,
        observer_actor_id="C",
        entity_id="DOOR",
    )
    assert gap.visibility_eligible is True

    assert tuple(world.event_log[i].event_id for i in range(len(world.event_log))) == before_event_ids
    assert world.world_state_version == before_state_version
    assert world.objects["DOOR"].damage_state == before_damage
    assert tuple(world.npc_minds["C"].memories) == before_memories
    assert tuple(world.npc_minds["C"].knowledge_boundary_refs) == before_boundary
    _assert_historical_nonwitness(world, source.event_id)

    with pytest.raises(FrozenInstanceError):
        gap.receipt_available = True
    with pytest.raises(FrozenInstanceError):
        gap.narrative_realization_authority = True


def test_restart_replay_preserves_historical_nonwitness_then_later_visibility_disposition():
    baseline, world, source = _commit_historical_damage()
    first_later = _LaterCurrentVisibilityView(world, entity_id="DOOR", observer_actor_id="C")
    first_echo = derive_world_echo_opportunity(
        world=first_later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    first_gap = assess_current_visual_observation_gap(
        world=first_later,
        observer_actor_id="C",
        entity_id="DOOR",
    )

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_source = next(event for event in rebuilt.event_log if event.event_id == source.event_id)
    assert replayed_source.actor_id == "A"
    assert rebuilt.can_see("DOOR", "C") is False
    _assert_historical_nonwitness(rebuilt, replayed_source.event_id)

    second_later = _LaterCurrentVisibilityView(rebuilt, entity_id="DOOR", observer_actor_id="C")
    second_echo = derive_world_echo_opportunity(
        world=second_later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=replayed_source.event_id,
    )
    second_gap = assess_current_visual_observation_gap(
        world=second_later,
        observer_actor_id="C",
        entity_id="DOOR",
    )

    assert second_echo == first_echo
    assert second_echo.status == "NO_VALID_OPPORTUNITY"
    assert second_echo.opportunity is None
    assert second_gap == first_gap
    assert second_gap.visibility_eligible is True
    assert second_gap.receipt_available is False
    _assert_historical_nonwitness(rebuilt, replayed_source.event_id)
