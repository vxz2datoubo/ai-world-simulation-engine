from dataclasses import replace

import pytest

from evals.current_observation_evidence_reference import (
    OBSERVATION_POLICY_DIGEST,
    OBSERVATION_POLICY_VERSION,
    CurrentObservationEvidenceError,
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


def test_explicit_visual_sample_produces_object_only_noncanonical_receipt():
    _, world = _sealed_world()
    before_events = world.event_log
    before_memories = world.npc_minds["B"].memories
    receipt = capture_current_visual_observation(
        world=world,
        observer_actor_id="B",
        entity_id="DOOR",
    )

    assert receipt.capture_semantics == "EXPLICIT_OBSERVATION_SAMPLE"
    assert receipt.observation_mode == "VISUAL"
    assert receipt.world_state_version == world.world_state_version
    assert receipt.source_event_cursor == 0
    assert receipt.observer_actor_id == "B"
    assert receipt.entity_id == "DOOR"
    assert receipt.observable_state_refs == (
        "OBJECT_PRESENT:DOOR",
        "OBJECT_DAMAGE_STATE:DOOR:BROKEN",
        "OBJECT_OPEN_STATE:DOOR:OPEN",
    )
    assert receipt.observation_policy_version == OBSERVATION_POLICY_VERSION
    assert receipt.observation_policy_digest == OBSERVATION_POLICY_DIGEST
    assert receipt.canonical_world_authority is False
    assert receipt.knowledge_write_authority is False
    assert receipt.narrative_realization_authority is False
    assert world.event_log == before_events
    assert world.npc_minds["B"].memories == before_memories


def test_visual_receipt_does_not_expose_hidden_cause_owner_or_internal_actor_values():
    _, world = _sealed_world()
    receipt = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    encoded = "\n".join(receipt.observable_state_refs)
    forbidden = ["culprit", "caused_by", "owner", "possessor", "relationship", "belief", "injury"]
    assert all(token not in encoded.lower() for token in forbidden)

    with pytest.raises(CurrentObservationEvidenceError, match="OBJECTS_ONLY"):
        capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="A")


def test_visibility_predicate_is_required_but_caller_cannot_assert_observed_true():
    _, world = _sealed_world(visible=False)
    with pytest.raises(CurrentObservationEvidenceError, match="VISUAL_ELIGIBILITY_NOT_PROVEN"):
        capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")


def test_policy_version_is_bound_and_old_policy_fails_closed():
    _, world = _sealed_world()
    with pytest.raises(CurrentObservationEvidenceError, match="OBSERVATION_POLICY_VERSION_MISMATCH"):
        capture_current_visual_observation(
            world=world,
            observer_actor_id="B",
            entity_id="DOOR",
            observation_policy_version="AWRSE-CURRENT-VISUAL-OBSERVATION-POLICY/v0",
        )


def test_same_world_state_sample_is_idempotent_not_receipt_spam():
    _, world = _sealed_world()
    first = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    second = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    assert second == first
    assert second.receipt_id == first.receipt_id


def test_receipt_becomes_stale_after_world_event_cursor_advances():
    _, world = _sealed_world()
    receipt = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    validate_current_observation(world=world, receipt=receipt)

    action = ActionCompiler().compile("告诉B门还坏着", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    assert len(world.event_log) > receipt.source_event_cursor

    with pytest.raises(CurrentObservationEvidenceError, match="STALE_OBSERVATION_WORLD_STATE_VERSION"):
        validate_current_observation(world=world, receipt=receipt)

    fresh = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    assert fresh.receipt_id != receipt.receipt_id
    assert fresh.source_event_cursor == len(world.event_log)


def test_forged_receipt_fields_fail_current_validation():
    _, world = _sealed_world()
    receipt = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")

    with pytest.raises(CurrentObservationEvidenceError):
        validate_current_observation(world=world, receipt=replace(receipt, world_id="FORGED"))
    with pytest.raises(CurrentObservationEvidenceError):
        validate_current_observation(world=world, receipt=replace(receipt, source_event_cursor=99))
    with pytest.raises(CurrentObservationEvidenceError):
        validate_current_observation(
            world=world,
            receipt=replace(receipt, observable_state_refs=("OBJECT_DAMAGE_STATE:DOOR:INTACT",)),
        )
    with pytest.raises(CurrentObservationEvidenceError):
        validate_current_observation(
            world=world,
            receipt=replace(receipt, observation_policy_digest="0" * 64),
        )


def test_restart_replay_rebuilds_same_receipt_from_same_state_and_policy():
    baseline, world = _sealed_world()
    first = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    second = capture_current_visual_observation(world=rebuilt, observer_actor_id="B", entity_id="DOOR")
    assert second == first
    validate_current_observation(world=rebuilt, receipt=second)


def test_receipt_is_immutable_and_has_no_authority_upgrade_path():
    _, world = _sealed_world()
    receipt = capture_current_visual_observation(world=world, observer_actor_id="B", entity_id="DOOR")
    with pytest.raises(Exception):
        receipt.knowledge_write_authority = True
    with pytest.raises(Exception):
        receipt.narrative_realization_authority = True
    with pytest.raises(Exception):
        receipt.observable_state_refs += ("CULPRIT:A",)
