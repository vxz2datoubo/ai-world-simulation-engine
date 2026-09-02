from dataclasses import replace

import pytest

from evals.current_observation_evidence_reference import (
    OBSERVATION_POLICY_DIGEST,
    OBSERVATION_POLICY_VERSION,
    CurrentObservationEvidence,
    CurrentObservationEvidenceError,
    assess_current_visual_observation_gap,
    capture_current_visual_observation,
    validate_current_observation,
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
    export_solo_replay_package,
    rehydrate_solo_replay_package,
)
from runtime.awrse.model import ResolutionStatus


def _world(*, visible=True) -> WorldState:
    return WorldState(
        world_id="CURRENT-OBSERVATION-EVAL-001",
        active_scene_id="S1",
        baseline_version="COE-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="玩家", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
            "B": ActorState(actor_id="B", name="观察者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
        },
        objects={
            "DOOR": ObjectState(
                object_id="DOOR",
                name="破门",
                scene_id="S1",
                zone_id="Z1",
                damage_state="BROKEN",
                is_open=True,
            )
        },
        npc_minds={"B": NPCMindState(npc_id="B", role="OBSERVER")},
        scenes={
            "S1": SceneState(
                scene_id="S1",
                base_asset_refs=["asset://tavern"],
                object_state_refs=["DOOR"],
                actor_state_refs=["A", "B"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("DOOR", "B")} if visible else set(),
        audible_pairs={("A", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _sealed_world(*, visible=True):
    world = _world(visible=visible)
    baseline = capture_pristine_baseline(world)
    world.seal_live()
    return baseline, world


def _forged_receipt(world: WorldState) -> CurrentObservationEvidence:
    return CurrentObservationEvidence(
        schema="AWRSE.CurrentObservationEvidence.Reference/v2",
        receipt_id="FORGED-COE",
        capture_semantics="EXPLICIT_OBSERVATION_SAMPLE",
        observation_mode="VISUAL",
        world_id=world.world_id,
        world_state_version=world.world_state_version,
        baseline_version=world.baseline_version,
        source_event_cursor=len(world.event_log),
        observer_actor_id="B",
        entity_id="DOOR",
        scene_id="S1",
        observer_zone_id="Z1",
        entity_zone_id="Z1",
        observable_state_refs=(
            "OBJECT_PRESENT:DOOR",
            "OBJECT_DAMAGE_STATE:DOOR:BROKEN",
            "OBJECT_OPEN_STATE:DOOR:OPEN",
        ),
        observation_policy_version=OBSERVATION_POLICY_VERSION,
        observation_policy_digest=OBSERVATION_POLICY_DIGEST,
        trusted_trigger_ref="CALLER:FAKE",
    )


def test_visibility_true_is_only_eligibility_and_produces_explicit_gap_proof():
    _, world = _sealed_world(visible=True)
    proof = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id="B",
        entity_id="DOOR",
    )
    assert proof.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert proof.visibility_eligible is True
    assert proof.trusted_discrete_trigger_available is False
    assert proof.receipt_available is False
    assert proof.world_state_version == world.world_state_version
    assert proof.source_event_cursor == len(world.event_log)
    assert proof.canonical_world_authority is False
    assert proof.knowledge_write_authority is False
    assert proof.narrative_realization_authority is False
    assert "trusted_trigger_authority_ref" in proof.required_future_trigger_fields


def test_can_see_true_plus_public_capture_call_cannot_mint_observation_receipt():
    _, world = _sealed_world(visible=True)
    assert world.can_see("DOOR", "B") is True
    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(
            world=world,
            observer_actor_id="B",
            entity_id="DOOR",
        )


def test_visibility_false_fails_before_any_observation_claim():
    _, world = _sealed_world(visible=False)
    proof = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id="B",
        entity_id="DOOR",
    )
    assert proof.status == "VISUAL_ELIGIBILITY_NOT_PROVEN"
    assert proof.visibility_eligible is False
    assert proof.receipt_available is False
    with pytest.raises(CurrentObservationEvidenceError, match="VISUAL_ELIGIBILITY_NOT_PROVEN"):
        capture_current_visual_observation(
            world=world,
            observer_actor_id="B",
            entity_id="DOOR",
        )


def test_arbitrary_caller_observer_or_entity_cannot_create_authority():
    _, world = _sealed_world(visible=True)
    with pytest.raises(CurrentObservationEvidenceError, match="OBSERVER_ACTOR_NOT_FOUND"):
        capture_current_visual_observation(world=world, observer_actor_id="FORGED", entity_id="DOOR")
    with pytest.raises(CurrentObservationEvidenceError, match="OBJECTS_ONLY"):
        capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="A")


def test_old_policy_version_fails_closed_before_gap_assessment():
    _, world = _sealed_world()
    with pytest.raises(CurrentObservationEvidenceError, match="OBSERVATION_POLICY_VERSION_MISMATCH"):
        assess_current_visual_observation_gap(
            world=world,
            observer_actor_id="B",
            entity_id="DOOR",
            observation_policy_version="AWRSE-CURRENT-VISUAL-OBSERVATION-POLICY/v1",
        )


def test_caller_constructed_receipt_is_never_treated_as_trusted_trigger_evidence():
    _, world = _sealed_world()
    forged = _forged_receipt(world)
    with pytest.raises(CurrentObservationEvidenceError, match="UNTRUSTED_OBSERVATION_RECEIPT"):
        validate_current_observation(world=world, receipt=forged)

    with pytest.raises(CurrentObservationEvidenceError, match="AUTHORITY_ESCALATION"):
        validate_current_observation(
            world=world,
            receipt=replace(forged, knowledge_write_authority=True),
        )


def test_world_event_advance_changes_gap_cursor_but_still_does_not_create_trigger():
    _, world = _sealed_world()
    first = assess_current_visual_observation_gap(world=world, observer_actor_id="B", entity_id="DOOR")

    action = ActionCompiler().compile("告诉B门还坏着", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS

    second = assess_current_visual_observation_gap(world=world, observer_actor_id="B", entity_id="DOOR")
    assert second.source_event_cursor > first.source_event_cursor
    assert second.world_state_version != first.world_state_version
    assert second.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert second.receipt_available is False


def test_restart_replay_reproduces_same_negative_gap_at_same_world_state():
    baseline, world = _sealed_world()
    first = assess_current_visual_observation_gap(world=world, observer_actor_id="B", entity_id="DOOR")
    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    second = assess_current_visual_observation_gap(world=rebuilt, observer_actor_id="B", entity_id="DOOR")
    assert second == first
    with pytest.raises(CurrentObservationEvidenceError, match="NO_TRUSTED_OBSERVATION_TRIGGER"):
        capture_current_visual_observation(world=rebuilt, observer_actor_id="B", entity_id="DOOR")


def test_gap_proof_exposes_no_object_state_or_hidden_cause_as_observation_claims():
    _, world = _sealed_world()
    proof = assess_current_visual_observation_gap(world=world, observer_actor_id="B", entity_id="DOOR")
    encoded = str(proof.to_dict()).lower()
    forbidden = ["culprit", "caused_by", "owner_actor_id", "possessor", "relationship", "belief", "injury"]
    assert all(token not in encoded for token in forbidden)
    assert not hasattr(proof, "observable_state_refs")


def test_gap_proof_is_immutable_and_has_no_authority_upgrade_path():
    _, world = _sealed_world()
    proof = assess_current_visual_observation_gap(world=world, observer_actor_id="B", entity_id="DOOR")
    with pytest.raises(Exception):
        proof.knowledge_write_authority = True
    with pytest.raises(Exception):
        proof.narrative_realization_authority = True
    with pytest.raises(Exception):
        proof.receipt_available = True
