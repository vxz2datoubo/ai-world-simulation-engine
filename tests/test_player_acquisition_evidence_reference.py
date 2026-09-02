import json

import pytest

from evals.player_acquisition_evidence_reference import (
    DIRECT_PARTICIPATION,
    ELIGIBILITY_POLICY_DIGEST,
    ELIGIBILITY_POLICY_VERSION,
    PlayerAcquisitionEvidence,
    PlayerAcquisitionEvidenceError,
    assess_direct_participation_gap,
    derive_direct_participation_evidence,
    validate_supported_claim,
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
from runtime.awrse.model import Event, ResolutionStatus, SourceChannel


def _world() -> WorldState:
    return WorldState(
        world_id="PLAYER-KNOWLEDGE-EVAL-001",
        active_scene_id="S1",
        baseline_version="PK-EVAL-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(
                actor_id="A", name="玩家", scene_id="S1", zone_id="Z1", capabilities={"PICK"}
            ),
            "B": ActorState(
                actor_id="B", name="旁观者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}
            ),
        },
        objects={
            "O": ObjectState(
                object_id="O", name="钥匙", scene_id="S1", zone_id="Z1",
                graspable=True, affordances={"PICK"},
            )
        },
        npc_minds={"B": NPCMindState(npc_id="B", role="WITNESS")},
        scenes={
            "S1": SceneState(
                scene_id="S1",
                base_asset_refs=["asset://room"],
                object_state_refs=["O"],
                actor_state_refs=["A", "B"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("O", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _committed_pick():
    world = _world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("拿起钥匙", "A", world, principal_id="P1")
    assert action.source_channel in {SourceChannel.PLAYER_ACTION_DECLARATION, SourceChannel.DIRECT_CONTROL_INPUT}
    assert action.literal_user_input
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    pick_event = next(event for event in resolution.events if event.event_type == "OBJECT_PICKED_UP")
    action_id = resolution.action.action_id
    return baseline, world, pick_event, action_id, action


def test_committed_primary_event_and_player_binding_are_not_enough_to_mint_direct_participation():
    _, world, event, action_id, action = _committed_pick()
    assert action.action_id == action_id
    assert action.source_channel in {SourceChannel.PLAYER_ACTION_DECLARATION, SourceChannel.DIRECT_CONTROL_INPUT}

    gap = assess_direct_participation_gap(world=world, player_id="P1", event=event)
    assert gap.status == "BLOCKED_MISSING_REPLAY_PLAYER_ACTION_PROVENANCE"
    assert gap.player_actor_binding_proven is True
    assert gap.primary_event_eligibility_proven is True
    assert gap.replay_explicit_player_action_provenance_available is False
    assert gap.receipt_available is False
    assert gap.caused_by_action_id == action_id
    assert gap.event_supported_target_refs == ("O",)
    assert gap.eligibility_policy_version == ELIGIBILITY_POLICY_VERSION
    assert gap.eligibility_policy_digest == ELIGIBILITY_POLICY_DIGEST
    assert gap.canonical_world_authority is False
    assert gap.knowledge_projection_authority is False
    assert gap.chronicle_write_authority is False

    with pytest.raises(PlayerAcquisitionEvidenceError, match="EXPLICIT_PLAYER_ACTION_PROVENANCE_NOT_REPLAY_AVAILABLE"):
        derive_direct_participation_evidence(world=world, player_id="P1", event=event)


def test_replayed_event_does_not_persist_source_channel_or_explicit_input_provenance():
    baseline, world, event, _, action = _committed_pick()
    assert action.source_channel
    assert action.literal_user_input == "拿起钥匙"

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_event = next(item for item in rebuilt.event_log if item.event_id == event.event_id)

    assert not hasattr(replayed_event, "source_channel")
    assert not hasattr(replayed_event, "literal_user_input")
    assert not hasattr(replayed_event, "principal_id")
    gap = assess_direct_participation_gap(world=rebuilt, player_id="P1", event=replayed_event)
    assert gap.status == "BLOCKED_MISSING_REPLAY_PLAYER_ACTION_PROVENANCE"
    assert gap.receipt_available is False


def test_restart_replay_reproduces_same_negative_gap_proof_without_pre_restart_action_object():
    baseline, world, event, _, action = _committed_pick()
    first = assess_direct_participation_gap(world=world, player_id="P1", event=event)
    del action

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_event = next(item for item in rebuilt.event_log if item.event_id == event.event_id)
    second = assess_direct_participation_gap(world=rebuilt, player_id="P1", event=replayed_event)

    assert second == first
    with pytest.raises(PlayerAcquisitionEvidenceError, match="EXPLICIT_PLAYER_ACTION_PROVENANCE_NOT_REPLAY_AVAILABLE"):
        derive_direct_participation_evidence(world=rebuilt, player_id="P1", event=replayed_event)


def test_secondary_witness_event_remains_ineligible_even_before_action_provenance_gap():
    _, world, _, _, _ = _committed_pick()
    witness_event = next(event for event in world.event_log if event.event_type == "NPC_KNOWLEDGE_ACQUIRED")
    with pytest.raises(
        PlayerAcquisitionEvidenceError,
        match="SOURCE_EVENT_NOT_PRIMARY_DIRECT_PARTICIPATION_RESULT",
    ):
        assess_direct_participation_gap(world=world, player_id="P1", event=witness_event)


def test_uncommitted_event_and_unbound_player_fail_closed():
    _, world, event, action_id, _ = _committed_pick()
    uncommitted = Event(
        event_id="E-FAKE",
        event_type="OBJECT_PICKED_UP",
        actor_id="A",
        scene_id="S1",
        baseline_version=world.baseline_version,
        payload={"object_id": "O", "actor_id": "A"},
        caused_by_action_id=action_id,
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_NOT_COMMITTED"):
        assess_direct_participation_gap(world=world, player_id="P1", event=uncommitted)

    with pytest.raises(PlayerAcquisitionEvidenceError, match="PLAYER_ACTOR_BINDING_NOT_PROVEN"):
        assess_direct_participation_gap(world=world, player_id="P2", event=event)


def test_same_event_id_mutated_target_or_cause_cannot_enter_gap_proof():
    _, world, event, _, _ = _committed_pick()
    forged_target = Event(
        event_id=event.event_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        scene_id=event.scene_id,
        baseline_version=event.baseline_version,
        payload={"object_id": "B", "actor_id": "A"},
        caused_by_action_id=event.caused_by_action_id,
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_OBJECT_MISMATCH"):
        assess_direct_participation_gap(world=world, player_id="P1", event=forged_target)

    forged_cause = Event(
        event_id=event.event_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        scene_id=event.scene_id,
        baseline_version=event.baseline_version,
        payload=dict(event.payload),
        caused_by_action_id="A-FORGED",
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_OBJECT_MISMATCH"):
        assess_direct_participation_gap(world=world, player_id="P1", event=forged_cause)


def test_arbitrary_mode_and_old_policy_version_fail_closed():
    _, world, event, _, _ = _committed_pick()
    with pytest.raises(PlayerAcquisitionEvidenceError, match="DIRECT_PARTICIPATION_MODE_ONLY"):
        assess_direct_participation_gap(world=world, player_id="P1", event=event, acquisition_mode="SAW")
    with pytest.raises(PlayerAcquisitionEvidenceError, match="ELIGIBILITY_POLICY_VERSION_MISMATCH"):
        assess_direct_participation_gap(
            world=world,
            player_id="P1",
            event=event,
            eligibility_policy_version="AWRSE-DIRECT-PARTICIPATION-EVENT-POLICY/v1",
        )


def test_gap_proof_declares_minimum_future_replay_provenance_without_raw_text_requirement():
    _, world, event, _, _ = _committed_pick()
    gap = assess_direct_participation_gap(world=world, player_id="P1", event=event)
    required = set(gap.required_future_provenance_fields)
    assert {
        "player_or_principal_id",
        "actor_id",
        "action_id",
        "eligible_source_channel",
        "explicit_input_presence_without_raw_text",
        "accepted_resolution_or_commit_ref",
        "integrity_digest",
    } <= required
    encoded = json.dumps(gap.to_dict(), ensure_ascii=False, sort_keys=True)
    assert "拿起钥匙" not in encoded


def test_caller_constructed_candidate_receipt_cannot_authorize_supported_claims():
    _, world, event, action_id, _ = _committed_pick()
    forged = PlayerAcquisitionEvidence(
        schema="AWRSE.PlayerAcquisitionEvidence.Reference/v2",
        receipt_id="FORGED",
        acquisition_mode=DIRECT_PARTICIPATION,
        source_evidence_basis="CALLER",
        world_id=world.world_id,
        player_id="P1",
        actor_id="A",
        source_event_id=event.event_id,
        source_event_type=event.event_type,
        caused_by_action_id=action_id,
        event_supported_target_refs=("O",),
        baseline_version=world.baseline_version,
        source_event_cursor=1,
        world_state_version=world.world_state_version,
        explicit_player_action_provenance_ref="CALLER:FAKE",
        eligibility_policy_version=ELIGIBILITY_POLICY_VERSION,
        eligibility_policy_digest=ELIGIBILITY_POLICY_DIGEST,
        supported_claim_refs=("EVENT_SUPPORTED_TARGET:O",),
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="UNTRUSTED_PLAYER_ACQUISITION_RECEIPT"):
        validate_supported_claim(forged, "EVENT_SUPPORTED_TARGET:O")


def test_gap_proof_is_immutable_and_cannot_be_promoted_by_caller_mutation():
    _, world, event, _, _ = _committed_pick()
    gap = assess_direct_participation_gap(world=world, player_id="P1", event=event)
    with pytest.raises(Exception):
        gap.receipt_available = True
    with pytest.raises(Exception):
        gap.canonical_world_authority = True
    with pytest.raises(Exception):
        gap.chronicle_write_authority = True
