from dataclasses import replace

import pytest

from evals.current_observation_evidence_reference import (
    CurrentObservationEvidenceError,
    capture_current_visual_observation,
)
from evals.world_echo_observation_composition_reference import (
    WorldEchoCompositionError,
    compose_world_echo_with_observation,
)
from runtime.awrse import (
    ActionCompiler,
    ActorState,
    NPCMindState,
    ObjectState,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
)
from runtime.awrse.model import Event, ResolutionStatus


def _witness_world():
    world = WorldState(
        world_id="CELL-WORLD-001B-WITNESS",
        active_scene_id="S1",
        baseline_version="CELL-WORLD-COMP-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="玩家", scene_id="S1", zone_id="Z1"),
            "B": ActorState(actor_id="B", name="目击者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
        },
        objects={
            "DOOR": ObjectState(object_id="DOOR", name="木门", scene_id="S1", zone_id="Z1", fragility=0.25)
        },
        npc_minds={"B": NPCMindState(npc_id="B", role="WITNESS")},
        scenes={"S1": SceneState(scene_id="S1", object_state_refs=["DOOR"], actor_state_refs=["A", "B"])},
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("DOOR", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )
    action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    source = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    witness = next(event for event in resolution.events if event.event_type == "NPC_KNOWLEDGE_ACQUIRED")
    return world, source, witness


def _nonwitness_replayed_world():
    pristine = WorldState(
        world_id="CELL-WORLD-001B-NONWITNESS",
        active_scene_id="S1",
        baseline_version="CELL-WORLD-COMP-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="玩家", scene_id="S1", zone_id="Z1"),
            "C": ActorState(actor_id="C", name="后来者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
        },
        objects={
            "DOOR": ObjectState(object_id="DOOR", name="木门", scene_id="S1", zone_id="Z1", fragility=0.25)
        },
        npc_minds={"C": NPCMindState(npc_id="C", role="NEWCOMER")},
        scenes={"S1": SceneState(scene_id="S1", object_state_refs=["DOOR"], actor_state_refs=["A", "C"])},
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("DOOR", "C")},
        zone_scene_bindings={"Z1": "S1"},
    )
    baseline = capture_pristine_baseline(pristine)
    source = Event(
        event_id="E-DAMAGE-REPLAY-1",
        event_type="OBJECT_DAMAGED",
        actor_id="A",
        scene_id="S1",
        baseline_version="CELL-WORLD-COMP-R1",
        payload={"object_id": "DOOR", "damage_state": "BROKEN"},
        caused_by_action_id="ACTION-DAMAGE-1",
    )
    world = SimulationEngine().replay(baseline, (source,))
    assert world.objects["DOOR"].damage_state == "BROKEN"
    assert source.event_id not in world.npc_minds["C"].knowledge_boundary_refs
    assert world.npc_minds["C"].memories == ()
    return baseline, world, source


def test_witness_plus_current_observation_satisfies_opportunity_gate_without_speech_authority():
    world, source, witness = _witness_world()
    observation = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    composed = compose_world_echo_with_observation(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=observation,
    )

    assert composed.attribution_state == "WITNESSED_CAUSE"
    assert composed.culprit_actor_ref == "A"
    assert composed.historical_knowledge_refs == (witness.event_id,)
    assert composed.current_observation_ref == observation.receipt_id
    assert "KNOWN_CULPRIT:A" in composed.speaker_visible_claim_refs
    assert composed.opportunity_eligible is True
    assert composed.canonical_world_authority is False
    assert composed.knowledge_write_authority is False
    assert composed.speech_commit_authority is False


def test_nonwitness_current_observation_yields_unknown_cause_without_actor_leakage():
    _, world, source = _nonwitness_replayed_world()
    observation = capture_current_visual_observation(world=world, observer_actor_id="C", entity_id="DOOR")
    composed = compose_world_echo_with_observation(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=observation,
    )

    assert composed.attribution_state == "UNKNOWN_CAUSE"
    assert composed.culprit_actor_ref is None
    assert composed.response_concept == "REMARK_UNKNOWN_DAMAGE"
    assert composed.historical_knowledge_refs == ()
    assert all("CULPRIT" not in ref and ":A" not in ref for ref in composed.speaker_visible_claim_refs)
    assert source.event_id in composed.internal_provenance_refs
    assert source.actor_id == "A"
    assert composed.opportunity_eligible is True


def test_replay_time_visibility_does_not_create_historical_witness_memory():
    _, world, source = _nonwitness_replayed_world()
    assert world.can_see("DOOR", "C") is True
    assert source.event_id not in world.npc_minds["C"].knowledge_boundary_refs
    observation = capture_current_visual_observation(world=world, observer_actor_id="C", entity_id="DOOR")
    composed = compose_world_echo_with_observation(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=observation,
    )
    assert composed.attribution_state == "UNKNOWN_CAUSE"
    assert world.npc_minds["C"].memories == ()
    assert world.npc_minds["C"].knowledge_boundary_refs == ()


def test_cross_speaker_or_forged_observation_receipt_fails_closed():
    world, source, _ = _witness_world()
    observation = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    with pytest.raises(WorldEchoCompositionError, match="OBSERVATION_SPEAKER_MISMATCH"):
        compose_world_echo_with_observation(
            world=world,
            speaker_npc_id="C",
            entity_id="DOOR",
            source_event_id=source.event_id,
            observation_receipt=observation,
        )

    forged = replace(observation, observable_state_refs=("OBJECT_DAMAGE_STATE:DOOR:INTACT",))
    with pytest.raises(CurrentObservationEvidenceError):
        compose_world_echo_with_observation(
            world=world,
            speaker_npc_id="B",
            entity_id="DOOR",
            source_event_id=source.event_id,
            observation_receipt=forged,
        )


def test_non_damage_observation_cannot_be_promoted_to_damage_echo():
    world = WorldState(
        world_id="CELL-WORLD-001B-INTACT",
        active_scene_id="S1",
        baseline_version="CELL-WORLD-COMP-R1",
        actors={"C": ActorState(actor_id="C", name="后来者", scene_id="S1", zone_id="Z1")},
        objects={"DOOR": ObjectState(object_id="DOOR", name="木门", scene_id="S1", zone_id="Z1")},
        npc_minds={"C": NPCMindState(npc_id="C", role="NEWCOMER")},
        scenes={"S1": SceneState(scene_id="S1", object_state_refs=["DOOR"], actor_state_refs=["C"])},
        visible_pairs={("DOOR", "C")},
        zone_scene_bindings={"Z1": "S1"},
    )
    world.seal_live()
    observation = capture_current_visual_observation(world=world, observer_actor_id="C", entity_id="DOOR")
    fake_source = Event(
        event_id="E-UNCOMMITTED", event_type="OBJECT_DAMAGED", actor_id=None, scene_id="S1",
        baseline_version="CELL-WORLD-COMP-R1", payload={"object_id": "DOOR", "damage_state": "BROKEN"},
    )
    with pytest.raises(WorldEchoCompositionError, match="CURRENT_OBSERVATION_DOES_NOT_PROVE_DAMAGE"):
        compose_world_echo_with_observation(
            world=world,
            speaker_npc_id="C",
            entity_id="DOOR",
            source_event_id=fake_source.event_id,
            observation_receipt=observation,
        )


def test_unknown_cause_composition_identity_is_stable_across_same_replay():
    baseline, world, source = _nonwitness_replayed_world()
    first_obs = capture_current_visual_observation(world=world, observer_actor_id="C", entity_id="DOOR")
    first = compose_world_echo_with_observation(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=first_obs,
    )

    rebuilt = SimulationEngine().replay(baseline, (source,))
    second_obs = capture_current_visual_observation(world=rebuilt, observer_actor_id="C", entity_id="DOOR")
    second = compose_world_echo_with_observation(
        world=rebuilt,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=second_obs,
    )
    assert second == first
    assert second.opportunity_id == first.opportunity_id


def test_composition_is_read_only_and_candidate_is_immutable():
    _, world, source = _nonwitness_replayed_world()
    observation = capture_current_visual_observation(world=world, observer_actor_id="C", entity_id="DOOR")
    before_events = world.event_log
    before_memories = world.npc_minds["C"].memories
    before_boundary = world.npc_minds["C"].knowledge_boundary_refs

    composed = compose_world_echo_with_observation(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
        observation_receipt=observation,
    )
    assert world.event_log == before_events
    assert world.npc_minds["C"].memories == before_memories
    assert world.npc_minds["C"].knowledge_boundary_refs == before_boundary
    with pytest.raises(Exception):
        composed.culprit_actor_ref = "A"
    with pytest.raises(Exception):
        composed.speech_commit_authority = True
