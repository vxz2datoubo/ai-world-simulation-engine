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
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
    export_solo_replay_package,
    rehydrate_solo_replay_package,
)
from runtime.awrse.model import ResolutionStatus


class _CurrentVisibilityView:
    """Read-only current-eligibility view over a sealed canonical world."""

    def __init__(self, world: WorldState, *, visible_entity_id: str, observer_actor_id: str):
        self._world = world
        self._visible_entity_id = visible_entity_id
        self._observer_actor_id = observer_actor_id

    def __getattr__(self, name):
        return getattr(self._world, name)

    def can_see(self, entity_id: str, observer_actor_id: str) -> bool:
        if entity_id == self._visible_entity_id and observer_actor_id == self._observer_actor_id:
            return True
        return self._world.can_see(entity_id, observer_actor_id)


def _world() -> WorldState:
    return WorldState(
        world_id="CELL-WORLD-001-B2",
        active_scene_id="S1",
        baseline_version="CELL-B2-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="玩家", scene_id="S1", zone_id="Z1"),
            "B": ActorState(actor_id="B", name="观察者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
            "C": ActorState(actor_id="C", name="后来观察者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
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
                base_asset_refs=["asset://tavern"],
                object_state_refs=["DOOR"],
                actor_state_refs=["A", "B", "C"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("DOOR", "B"), ("A", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _damaged_world():
    world = _world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    source_event = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    return baseline, world, source_event


def _compose(world: WorldState, source_event_id: str, observer_actor_id: str = "B"):
    echo = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id=observer_actor_id,
        entity_id="DOOR",
        source_event_id=source_event_id,
    )
    gap = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=observer_actor_id,
        entity_id="DOOR",
    )
    return echo, gap


def test_historical_object_witness_plus_current_visibility_stays_blocked_without_observation_trigger():
    _, world, source_event = _damaged_world()
    assert world.can_see("DOOR", "B") is True
    assert world.can_see("A", "B") is True
    echo, gap = _compose(world, source_event.event_id)
    assert echo.status == "CANDIDATE_BLOCKED_PENDING_CURRENT_PERCEPTION"
    assert echo.opportunity is not None
    assert echo.opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"
    assert echo.opportunity.culprit_actor_ref is None
    assert echo.opportunity.realization_authorized is False
    assert gap.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert gap.visibility_eligible is True
    assert gap.receipt_available is False
    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")


def test_nonwitness_plus_current_visibility_cannot_be_laundered_into_historical_knowledge_or_echo():
    _, world, source_event = _damaged_world()
    assert source_event.event_id not in world.npc_minds["C"].knowledge_boundary_refs
    assert world.can_see("DOOR", "C") is False

    echo = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )
    assert echo.status == "NO_VALID_OPPORTUNITY"
    assert echo.reason == "NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION"
    assert echo.opportunity is None

    current_view = _CurrentVisibilityView(world, visible_entity_id="DOOR", observer_actor_id="C")
    assert current_view.is_live is True
    assert current_view.can_see("DOOR", "C") is True
    assert source_event.event_id not in current_view.npc_minds["C"].knowledge_boundary_refs
    assert tuple(current_view.event_log) == tuple(world.event_log)
    assert current_view.world_state_version == world.world_state_version

    gap = assess_current_visual_observation_gap(
        world=current_view,
        observer_actor_id="C",
        entity_id="DOOR",
    )
    assert gap.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert gap.visibility_eligible is True
    assert gap.trusted_discrete_trigger_available is False
    assert gap.receipt_available is False
    assert gap.knowledge_write_authority is False
    assert gap.narrative_realization_authority is False
    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(world=current_view, observer_actor_id="C", entity_id="DOOR")

    assert derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    ) == echo


def test_simulator_knows_actor_but_composition_cannot_launder_it_into_speaker_culprit():
    _, world, source_event = _damaged_world()
    assert source_event.actor_id == "A"
    assert world.can_see("A", "B") is True
    echo, gap = _compose(world, source_event.event_id)
    assert echo.opportunity is not None
    assert echo.opportunity.culprit_actor_ref is None
    assert echo.opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"
    assert echo.opportunity.response_concept == "REMARK_OBSERVED_DAMAGE_CAUSE_UNKNOWN"
    assert gap.receipt_available is False


def test_restart_replay_reproduces_same_fail_closed_composition():
    baseline, world, source_event = _damaged_world()
    first_echo, first_gap = _compose(world, source_event.event_id)
    assert first_echo.opportunity is not None
    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_source = next(event for event in rebuilt.event_log if event.event_id == source_event.event_id)
    second_echo, second_gap = _compose(rebuilt, replayed_source.event_id)
    assert second_echo.status == first_echo.status
    assert second_echo.opportunity is not None
    assert second_echo.opportunity.opportunity_id == first_echo.opportunity.opportunity_id
    assert second_echo.opportunity.culprit_actor_ref is None
    assert second_echo.opportunity.realization_authorized is False
    assert second_gap == first_gap
    assert second_gap.receipt_available is False


def test_composition_has_no_upgrade_path_from_gap_proof_to_narrative_realization():
    _, world, source_event = _damaged_world()
    echo, gap = _compose(world, source_event.event_id)
    assert echo.opportunity is not None
    with pytest.raises(Exception):
        echo.opportunity.realization_authorized = True
    with pytest.raises(Exception):
        echo.opportunity.culprit_actor_ref = "A"
    with pytest.raises(Exception):
        gap.receipt_available = True
    with pytest.raises(Exception):
        gap.narrative_realization_authority = True
