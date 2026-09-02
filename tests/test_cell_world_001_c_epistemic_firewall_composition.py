import pytest

from evals.current_observation_evidence_reference import (
    CurrentObservationEvidenceError,
    assess_current_visual_observation_gap,
    capture_current_visual_observation,
)
from evals.player_acquisition_evidence_reference import (
    PlayerAcquisitionEvidenceError,
    assess_direct_participation_gap,
    derive_direct_participation_evidence,
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


def _world() -> WorldState:
    return WorldState(
        world_id="CELL-WORLD-001-C",
        active_scene_id="S1",
        baseline_version="CELL-C-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(
                actor_id="A",
                name="玩家",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"PICK"},
            ),
            "B": ActorState(
                actor_id="B",
                name="旁观者",
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
            ),
            "KEY": ObjectState(
                object_id="KEY",
                name="钥匙",
                scene_id="S1",
                zone_id="Z1",
                graspable=True,
                affordances={"PICK"},
            ),
        },
        npc_minds={"B": NPCMindState(npc_id="B", role="WITNESS")},
        scenes={
            "S1": SceneState(
                scene_id="S1",
                base_asset_refs=["asset://cell-world-c"],
                object_state_refs=["DOOR", "KEY"],
                actor_state_refs=["A", "B"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        # These are deliberately generous symbolic visibility conditions. They still must
        # not become event-time causal recognition or a current discrete observation receipt.
        visible_pairs={("DOOR", "B"), ("KEY", "B"), ("A", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _committed_world():
    world = _world()
    baseline = capture_pristine_baseline(world)

    damage_action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    damage_resolution = SimulationEngine().resolve_and_commit(damage_action, world)
    assert damage_resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    damage_event = next(
        event for event in damage_resolution.events if event.event_type == "OBJECT_DAMAGED"
    )

    pick_action = ActionCompiler().compile("拿起钥匙", "A", world, principal_id="P1")
    pick_resolution = SimulationEngine().resolve_and_commit(pick_action, world)
    assert pick_resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    pick_event = next(
        event for event in pick_resolution.events if event.event_type == "OBJECT_PICKED_UP"
    )

    return baseline, world, damage_event, pick_event


def _compose(world: WorldState, damage_event, participation_event):
    echo = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=damage_event.event_id,
    )
    observation_gap = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id="B",
        entity_id="DOOR",
    )
    participation_gap = assess_direct_participation_gap(
        world=world,
        player_id="P1",
        event=participation_event,
    )
    return echo, observation_gap, participation_gap


def test_world_truth_player_binding_npc_history_and_current_visibility_remain_distinct():
    _, world, damage_event, pick_event = _committed_world()

    assert damage_event.actor_id == "A"
    assert pick_event.actor_id == "A"
    assert world.can_principal_control("P1", "A") is True
    assert world.can_see("DOOR", "B") is True
    assert world.can_see("A", "B") is True

    echo, observation_gap, participation_gap = _compose(world, damage_event, pick_event)

    assert participation_gap.player_actor_binding_proven is True
    assert participation_gap.primary_event_eligibility_proven is True
    assert participation_gap.replay_explicit_player_action_provenance_available is False
    assert participation_gap.receipt_available is False
    assert participation_gap.status == "BLOCKED_MISSING_REPLAY_PLAYER_ACTION_PROVENANCE"

    assert echo.status == "CANDIDATE_BLOCKED_PENDING_CURRENT_PERCEPTION"
    assert echo.opportunity is not None
    assert echo.opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"
    assert echo.opportunity.culprit_actor_ref is None
    assert echo.opportunity.realization_authorized is False

    assert observation_gap.visibility_eligible is True
    assert observation_gap.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert observation_gap.trusted_discrete_trigger_available is False
    assert observation_gap.receipt_available is False

    # All three planes are evidence/proof surfaces only, never canonicalizing authorities.
    assert participation_gap.canonical_world_authority is False
    assert participation_gap.knowledge_projection_authority is False
    assert participation_gap.chronicle_write_authority is False
    assert echo.opportunity.canonical_world_authority is False
    assert echo.opportunity.knowledge_write_authority is False
    assert echo.opportunity.speech_commit_authority is False
    assert observation_gap.canonical_world_authority is False
    assert observation_gap.knowledge_write_authority is False
    assert observation_gap.narrative_realization_authority is False


def test_same_player_caused_damage_event_still_cannot_bridge_player_and_npc_knowledge_planes():
    _, world, damage_event, _ = _committed_world()

    # The exact same committed event simultaneously demonstrates the separation:
    # world knows the actor, player binding is proven, but replay lacks explicit-player
    # source provenance and the NPC lacks causal-actor acquisition provenance.
    participation_gap = assess_direct_participation_gap(
        world=world,
        player_id="P1",
        event=damage_event,
    )
    echo = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=damage_event.event_id,
    )

    assert damage_event.actor_id == "A"
    assert participation_gap.actor_id == "A"
    assert participation_gap.player_actor_binding_proven is True
    assert participation_gap.receipt_available is False
    assert echo.opportunity is not None
    assert echo.opportunity.culprit_actor_ref is None
    assert echo.opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"

    with pytest.raises(
        PlayerAcquisitionEvidenceError,
        match="EXPLICIT_PLAYER_ACTION_PROVENANCE_NOT_REPLAY_AVAILABLE",
    ):
        derive_direct_participation_evidence(
            world=world,
            player_id="P1",
            event=damage_event,
        )


def test_npc_acquisition_cannot_be_laundered_into_player_direct_participation():
    _, world, damage_event, _ = _committed_world()

    npc_acquisition = next(
        event
        for event in world.event_log
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and str(event.payload.get("npc_id", "")) == "B"
        and str(event.payload.get("source_event_id", "")) == damage_event.event_id
    )

    with pytest.raises(
        PlayerAcquisitionEvidenceError,
        match="SOURCE_EVENT_NOT_PRIMARY_DIRECT_PARTICIPATION_RESULT",
    ):
        assess_direct_participation_gap(
            world=world,
            player_id="P1",
            event=npc_acquisition,
        )

    # NPC-local acquisition remains sufficient only for the bounded object-state echo path;
    # it still does not prove causal actor recognition.
    echo = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=damage_event.event_id,
    )
    assert echo.opportunity is not None
    assert echo.opportunity.culprit_actor_ref is None


def test_current_visibility_and_caller_invocation_cannot_complete_any_missing_evidence_plane():
    _, world, damage_event, pick_event = _committed_world()
    echo, observation_gap, participation_gap = _compose(world, damage_event, pick_event)

    assert world.can_see("DOOR", "B") is True
    assert world.can_see("A", "B") is True
    assert echo.opportunity is not None
    assert echo.opportunity.realization_authorized is False
    assert observation_gap.receipt_available is False
    assert participation_gap.receipt_available is False

    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(
            world=world,
            observer_actor_id="B",
            entity_id="DOOR",
        )

    with pytest.raises(
        PlayerAcquisitionEvidenceError,
        match="EXPLICIT_PLAYER_ACTION_PROVENANCE_NOT_REPLAY_AVAILABLE",
    ):
        derive_direct_participation_evidence(
            world=world,
            player_id="P1",
            event=pick_event,
        )


def test_restart_replay_reconstructs_the_same_three_fail_closed_dispositions():
    baseline, world, damage_event, pick_event = _committed_world()
    first_echo, first_observation, first_participation = _compose(
        world,
        damage_event,
        pick_event,
    )
    assert first_echo.opportunity is not None

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_damage = next(
        event for event in rebuilt.event_log if event.event_id == damage_event.event_id
    )
    replayed_pick = next(
        event for event in rebuilt.event_log if event.event_id == pick_event.event_id
    )

    second_echo, second_observation, second_participation = _compose(
        rebuilt,
        replayed_damage,
        replayed_pick,
    )

    assert second_echo.status == first_echo.status
    assert second_echo.opportunity is not None
    assert second_echo.opportunity.opportunity_id == first_echo.opportunity.opportunity_id
    assert second_echo.opportunity.culprit_actor_ref is None
    assert second_echo.opportunity.realization_authorized is False
    assert second_observation == first_observation
    assert second_participation == first_participation
    assert second_observation.receipt_available is False
    assert second_participation.receipt_available is False


def test_gap_and_candidate_objects_are_immutable_and_cannot_be_promoted_by_mutation():
    _, world, damage_event, pick_event = _committed_world()
    echo, observation_gap, participation_gap = _compose(world, damage_event, pick_event)
    assert echo.opportunity is not None

    with pytest.raises(Exception):
        echo.opportunity.culprit_actor_ref = "A"
    with pytest.raises(Exception):
        echo.opportunity.realization_authorized = True
    with pytest.raises(Exception):
        observation_gap.receipt_available = True
    with pytest.raises(Exception):
        observation_gap.narrative_realization_authority = True
    with pytest.raises(Exception):
        participation_gap.receipt_available = True
    with pytest.raises(Exception):
        participation_gap.chronicle_write_authority = True
