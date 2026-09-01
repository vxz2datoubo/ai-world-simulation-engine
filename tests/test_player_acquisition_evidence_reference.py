import json

import pytest

from evals.player_acquisition_evidence_reference import (
    DIRECT_PARTICIPATION,
    ELIGIBILITY_POLICY_DIGEST,
    ELIGIBILITY_POLICY_VERSION,
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
    action_id = resolution.action.action_id
    del action
    return baseline, world, pick_event, action_id


def test_direct_participation_receipt_uses_committed_event_not_caller_action():
    _, world, event, action_id = _committed_pick()
    before_event_ids = tuple(item.event_id for item in world.event_log)
    before_owner = world.objects["O"].owner_actor_id

    receipt = derive_direct_participation_evidence(world=world, player_id="P1", event=event)

    assert receipt.acquisition_mode == DIRECT_PARTICIPATION
    assert receipt.source_evidence_basis == "COMMITTED_PRIMARY_EVENT_PLUS_REPLAYED_PLAYER_ACTOR_BINDING"
    assert receipt.player_id == "P1"
    assert receipt.actor_id == "A"
    assert receipt.source_event_id == event.event_id
    assert receipt.caused_by_action_id == action_id
    assert receipt.event_supported_target_refs == ("O",)
    assert receipt.source_event_cursor == 1
    assert receipt.eligibility_policy_version == ELIGIBILITY_POLICY_VERSION
    assert receipt.eligibility_policy_digest == ELIGIBILITY_POLICY_DIGEST
    assert receipt.canonical_world_authority is False
    assert receipt.knowledge_projection_authority is False
    assert receipt.chronicle_write_authority is False

    assert validate_supported_claim(receipt, f"EVENT_OCCURRED:{event.event_id}:OBJECT_PICKED_UP")
    assert validate_supported_claim(receipt, "DIRECT_ACTOR:A")
    assert validate_supported_claim(receipt, "EVENT_SUPPORTED_TARGET:O")
    assert not validate_supported_claim(receipt, "EVENT_SUPPORTED_TARGET:B")
    assert not validate_supported_claim(receipt, "NPC_B_SECRET_MOTIVE:STEAL_KEY")
    assert not validate_supported_claim(receipt, "OBJECT_IS_LEGALLY_OWNED_BY:A")

    encoded = json.dumps(receipt.to_dict(), ensure_ascii=False, sort_keys=True)
    assert "拿起钥匙" not in encoded
    assert tuple(item.event_id for item in world.event_log) == before_event_ids
    assert world.objects["O"].owner_actor_id == before_owner == "A"


def test_secondary_witness_event_cannot_be_laundered_as_player_direct_participation():
    _, world, _, action_id = _committed_pick()
    witness_event = next(event for event in world.event_log if event.event_type == "NPC_KNOWLEDGE_ACQUIRED")
    assert witness_event.caused_by_action_id == action_id
    assert witness_event.payload["npc_id"] == "B"

    with pytest.raises(
        PlayerAcquisitionEvidenceError,
        match="SOURCE_EVENT_NOT_PRIMARY_DIRECT_PARTICIPATION_RESULT",
    ):
        derive_direct_participation_evidence(world=world, player_id="P1", event=witness_event)


def test_uncommitted_event_and_unbound_player_fail_closed():
    _, world, event, action_id = _committed_pick()
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
        derive_direct_participation_evidence(world=world, player_id="P1", event=uncommitted)

    with pytest.raises(PlayerAcquisitionEvidenceError, match="PLAYER_ACTOR_BINDING_NOT_PROVEN"):
        derive_direct_participation_evidence(world=world, player_id="P2", event=event)


def test_same_event_id_mutated_target_or_cause_cannot_mint_claims():
    _, world, event, _ = _committed_pick()
    forged_target = Event(
        event_id=event.event_id,
        event_type=event.event_type,
        actor_id=event.actor_id,
        scene_id=event.scene_id,
        baseline_version=event.baseline_version,
        payload={"object_id": "B", "actor_id": "A", "from_zone_id": "Z1", "to_zone_id": "Z1"},
        caused_by_action_id=event.caused_by_action_id,
    )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="SOURCE_EVENT_OBJECT_MISMATCH"):
        derive_direct_participation_evidence(world=world, player_id="P1", event=forged_target)

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
        derive_direct_participation_evidence(world=world, player_id="P1", event=forged_cause)


def test_arbitrary_mode_and_policy_version_fail_closed():
    _, world, event, _ = _committed_pick()
    with pytest.raises(PlayerAcquisitionEvidenceError, match="DIRECT_PARTICIPATION_MODE_ONLY"):
        derive_direct_participation_evidence(
            world=world, player_id="P1", event=event, acquisition_mode="SAW"
        )
    with pytest.raises(PlayerAcquisitionEvidenceError, match="ELIGIBILITY_POLICY_VERSION_MISMATCH"):
        derive_direct_participation_evidence(
            world=world,
            player_id="P1",
            event=event,
            eligibility_policy_version="AWRSE-DIRECT-PARTICIPATION-EVENT-POLICY/v0",
        )


def test_replay_rederivation_discards_pre_restart_action_object_entirely():
    baseline, world, event, _ = _committed_pick()
    first = derive_direct_participation_evidence(world=world, player_id="P1", event=event)

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_event = next(item for item in rebuilt.event_log if item.event_id == event.event_id)
    second = derive_direct_participation_evidence(world=rebuilt, player_id="P1", event=replayed_event)

    assert second.receipt_id == first.receipt_id
    assert second.source_event_cursor == first.source_event_cursor
    assert second.supported_claim_refs == first.supported_claim_refs
    assert second.world_state_version == first.world_state_version
    assert second.eligibility_policy_version == first.eligibility_policy_version
    assert second.eligibility_policy_digest == first.eligibility_policy_digest


def test_old_policy_version_cannot_reinterpret_historical_replay_event():
    baseline, world, event, _ = _committed_pick()
    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    replayed_event = next(item for item in rebuilt.event_log if item.event_id == event.event_id)
    with pytest.raises(PlayerAcquisitionEvidenceError, match="ELIGIBILITY_POLICY_VERSION_MISMATCH"):
        derive_direct_participation_evidence(
            world=rebuilt,
            player_id="P1",
            event=replayed_event,
            eligibility_policy_version="AWRSE-DIRECT-PARTICIPATION-EVENT-POLICY/v0",
        )


def test_receipt_is_immutable_and_cannot_be_promoted_by_caller_mutation():
    _, world, event, _ = _committed_pick()
    receipt = derive_direct_participation_evidence(world=world, player_id="P1", event=event)
    with pytest.raises(Exception):
        receipt.canonical_world_authority = True
    with pytest.raises(Exception):
        receipt.chronicle_write_authority = True
    with pytest.raises(Exception):
        receipt.eligibility_policy_version = "attacker/v999"
