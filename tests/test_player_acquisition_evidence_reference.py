import copy
import json

import pytest

from evals.player_acquisition_evidence_reference import (
    DIRECT_PARTICIPATION,
    PlayerAcquisitionEvidenceError,
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
from runtime.awrse.model import Event, ResolutionStatus


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
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    pick_event = next(event for event in resolution.events if event.event_type == "OBJECT_PICKED_UP")
    return baseline, world, resolution.action, pick_event


def test_direct_participation_receipt_is_derived_evidence_not_authority():
    _, world, action, event = _committed_pick()
    before_event_ids = tuple(item.event_id for item in world.event_log)
    before_owner = world.objects["O"].owner_actor_id

    receipt = derive_direct_participation_evidence(
        world=world, player_id="P1", action=action, event=event
    )

    assert receipt.acquisition_mode == DIRECT_PARTICIPATION
    assert receipt.player_id == "P1"
    assert receipt.actor_id == "A"
    assert receipt.source_event_id == event.event_id
    assert receipt.caused_by_action_id == action.action_id
    assert receipt.action_target_ids == ("O",)
    assert receipt.literal_input_present is True
    assert receipt.source_event_cursor == 1
    assert receipt.canonical_world_authority is False
    assert receipt.knowledge_projection_authority is False
    assert receipt.chronicle_write_authority is False

    assert validate_supported_claim(receipt, f"EVENT_OCCURRED:{event.event_id}:OBJECT_PICKED_UP")
    assert validate_supported_claim(receipt, "DIRECT_ACTOR:A")
    assert validate_supported_claim(receipt, "EXPLICIT_ACTION_TARGET:O")
    assert not validate_supported_claim(receipt, "NPC_B_SECRET_MOTIVE:STEAL_KEY")
    assert not validate_supported_claim(receipt, "OBJECT_IS_LEGALLY_OWNED_BY:A")

    # Derivation is read-only and does not persist raw user text into the receipt.
    encoded = json.dumps(receipt.to_dict(), ensure_ascii=False, sort_keys=True)
    assert "拿起钥匙" not in encoded
    assert tuple(item.event_id for item in world.event_log) == before_event_ids
    assert world.objects["O"].owner_actor_id == before_owner == "A"


def test_uncommitted_or_wrongly_bound_evidence_fails_closed():
    _, world, action, event = _committed_pick()

    uncommitted = Event(
        event_id="E-FAKE",
        event_type="OBJECT_PICKED_UP",
        actor_id="A",
        scene_id="S1",
        baseline_version=world.baseline_version,
        payload={"object_id": "O"},
        caused_by_action_id=action.action_id,
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_NOT_COMMITTED"):
        derive_direct_participation_evidence(
            world=world, player_id="P1", action=action, event=uncommitted
        )

    with pytest.raises(PlayerAcquisitionEvidenceError, match="PLAYER_ACTION_PRINCIPAL_MISMATCH"):
        derive_direct_participation_evidence(
            world=world, player_id="P2", action=action, event=event
        )

    forged_binding_action = copy.deepcopy(action)
    forged_binding_action.principal_id = "P2"
    with pytest.raises(PlayerAcquisitionEvidenceError, match="PLAYER_ACTOR_BINDING_NOT_PROVEN"):
        derive_direct_participation_evidence(
            world=world, player_id="P2", action=forged_binding_action, event=event
        )


def test_wrong_action_cause_rejected_action_and_arbitrary_mode_fail_closed():
    _, world, action, event = _committed_pick()

    wrong_cause = copy.deepcopy(action)
    wrong_cause.action_id = "A-WRONG"
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_ACTION_CAUSE_MISMATCH"):
        derive_direct_participation_evidence(
            world=world, player_id="P1", action=wrong_cause, event=event
        )

    rejected = copy.deepcopy(action)
    rejected.resolution_status = ResolutionStatus.REJECTED_AUTHORITY
    with pytest.raises(PlayerAcquisitionEvidenceError, match="ACTION_NOT_SUCCESSFULLY_RESOLVED"):
        derive_direct_participation_evidence(
            world=world, player_id="P1", action=rejected, event=event
        )

    with pytest.raises(PlayerAcquisitionEvidenceError, match="DIRECT_PARTICIPATION_MODE_ONLY"):
        derive_direct_participation_evidence(
            world=world, player_id="P1", action=action, event=event, acquisition_mode="SAW"
        )


def test_receipt_identity_is_stable_across_replay_for_same_source_evidence():
    baseline, world, action, event = _committed_pick()
    first = derive_direct_participation_evidence(
        world=world, player_id="P1", action=action, event=event
    )

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_event = next(item for item in rebuilt.event_log if item.event_id == event.event_id)
    second = derive_direct_participation_evidence(
        world=rebuilt, player_id="P1", action=action, event=replayed_event
    )

    assert second.receipt_id == first.receipt_id
    assert second.source_event_cursor == first.source_event_cursor
    assert second.supported_claim_refs == first.supported_claim_refs
    assert second.world_state_version == first.world_state_version


def test_receipt_is_immutable_and_cannot_be_promoted_by_caller_mutation():
    _, world, action, event = _committed_pick()
    receipt = derive_direct_participation_evidence(
        world=world, player_id="P1", action=action, event=event
    )
    with pytest.raises(Exception):
        receipt.canonical_world_authority = True
    with pytest.raises(Exception):
        receipt.chronicle_write_authority = True
