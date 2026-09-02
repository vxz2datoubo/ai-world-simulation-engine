import inspect

import pytest

from evals.world_echo_opportunity_reference import (
    NON_CANONICAL_AUTHORITY,
    WorldEchoEvidenceError,
    derive_world_echo_opportunity,
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


def _world(*, actor_visible_to_b=False) -> WorldState:
    visible_pairs = {("DOOR", "B")}
    if actor_visible_to_b:
        visible_pairs.add(("A", "B"))
    return WorldState(
        world_id="WORLD-ECHO-EVAL-001",
        active_scene_id="S1",
        baseline_version="WORLD-ECHO-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(actor_id="A", name="玩家", scene_id="S1", zone_id="Z1"),
            "B": ActorState(actor_id="B", name="目击者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
            "C": ActorState(actor_id="C", name="未目击者", scene_id="S1", zone_id="Z1", capabilities={"SPEAK"}),
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
        visible_pairs=visible_pairs,
        zone_scene_bindings={"Z1": "S1"},
    )


def _damaged_world(*, actor_visible_to_b=False):
    world = _world(actor_visible_to_b=actor_visible_to_b)
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    source_event = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    witness_event = next(event for event in resolution.events if event.event_type == "NPC_KNOWLEDGE_ACQUIRED")
    assert witness_event.payload["npc_id"] == "B"
    assert witness_event.payload["mode"] == "SAW"
    assert witness_event.payload["source_event_id"] == source_event.event_id
    return baseline, world, source_event, witness_event


def test_object_event_witness_gets_unknown_cause_candidate_not_simulator_actor_identity():
    _, world, source_event, witness_event = _damaged_world()
    assert source_event.actor_id == "A"
    assert world.can_see("DOOR", "B") is True
    assert world.can_see("A", "B") is False

    result = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )

    assert result.status == "CANDIDATE_BLOCKED_PENDING_CURRENT_PERCEPTION"
    assert result.reason == "OBJECT_DAMAGE_ACQUIRED_CAUSAL_ACTOR_NOT_PROVEN"
    assert result.opportunity is not None
    opportunity = result.opportunity
    assert opportunity.authority == NON_CANONICAL_AUTHORITY
    assert opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"
    assert opportunity.culprit_actor_ref is None
    assert opportunity.knowledge_attribution_refs == (witness_event.event_id,)
    assert opportunity.response_concept == "REMARK_OBSERVED_DAMAGE_CAUSE_UNKNOWN"
    assert opportunity.realization_gate == "CURRENT_PERCEPTION_EVIDENCE_REQUIRED"
    assert opportunity.realization_authorized is False
    assert opportunity.canonical_world_authority is False
    assert opportunity.knowledge_write_authority is False
    assert opportunity.speech_commit_authority is False


def test_current_symbolic_actor_visibility_still_does_not_retroactively_prove_event_time_causal_observation():
    _, world, source_event, _ = _damaged_world(actor_visible_to_b=True)
    assert world.can_see("A", "B") is True
    result = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )
    assert result.opportunity is not None
    assert result.opportunity.culprit_actor_ref is None
    assert result.opportunity.attribution_state == "OBJECT_STATE_WITNESSED_CAUSE_UNPROVEN"


def test_nonwitness_cannot_inherit_simulator_omniscience_or_name_culprit():
    _, world, source_event, _ = _damaged_world()
    assert source_event.actor_id == "A"
    assert source_event.event_id not in world.npc_minds["C"].knowledge_boundary_refs

    result = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )
    assert result.status == "NO_VALID_OPPORTUNITY"
    assert result.reason == "NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION"
    assert result.opportunity is None


def test_api_has_no_caller_attribution_or_culprit_override_surface():
    parameters = set(inspect.signature(derive_world_echo_opportunity).parameters)
    assert "attribution_state" not in parameters
    assert "culprit_actor_ref" not in parameters
    assert "knowledge_ref" not in parameters
    assert "actor_witnessed" not in parameters


def test_fabricated_source_or_secondary_event_cannot_mint_echo():
    _, world, source_event, witness_event = _damaged_world()
    with pytest.raises(WorldEchoEvidenceError, match="SOURCE_EVENT_NOT_COMMITTED"):
        derive_world_echo_opportunity(
            world=world,
            speaker_npc_id="B",
            entity_id="DOOR",
            source_event_id="E-FABRICATED",
        )

    with pytest.raises(WorldEchoEvidenceError, match="SOURCE_EVENT_NOT_SUPPORTED_WORLD_ECHO_DAMAGE"):
        derive_world_echo_opportunity(
            world=world,
            speaker_npc_id="B",
            entity_id="DOOR",
            source_event_id=witness_event.event_id,
        )
    assert source_event.event_id != witness_event.event_id


def test_wrong_speaker_and_wrong_entity_fail_closed():
    _, world, source_event, _ = _damaged_world()
    with pytest.raises(WorldEchoEvidenceError, match="SPEAKER_NPC_NOT_FOUND"):
        derive_world_echo_opportunity(
            world=world,
            speaker_npc_id="A",
            entity_id="DOOR",
            source_event_id=source_event.event_id,
        )
    with pytest.raises(WorldEchoEvidenceError, match="ECHO_ENTITY_NOT_OBJECT"):
        derive_world_echo_opportunity(
            world=world,
            speaker_npc_id="B",
            entity_id="A",
            source_event_id=source_event.event_id,
        )


def test_generation_is_read_only_and_cannot_invent_npc_knowledge():
    _, world, source_event, _ = _damaged_world()
    event_ids = tuple(event.event_id for event in world.event_log)
    b_memories = world.npc_minds["B"].memories
    c_memories = world.npc_minds["C"].memories
    c_boundary = world.npc_minds["C"].knowledge_boundary_refs
    damage = world.objects["DOOR"].damage_state

    derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )
    assert tuple(event.event_id for event in world.event_log) == event_ids
    assert world.npc_minds["B"].memories == b_memories
    assert world.npc_minds["C"].memories == c_memories
    assert world.npc_minds["C"].knowledge_boundary_refs == c_boundary
    assert world.objects["DOOR"].damage_state == damage

    with pytest.raises(Exception):
        world.npc_minds["C"].knowledge_boundary_refs += (source_event.event_id,)


def test_candidate_identity_and_unknown_attribution_are_stable_across_restart_replay():
    baseline, world, source_event, _ = _damaged_world()
    first = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    ).opportunity
    assert first is not None

    package = export_solo_replay_package(baseline, world)
    rebuilt = rehydrate_solo_replay_package(package)
    second = derive_world_echo_opportunity(
        world=rebuilt,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    ).opportunity
    assert second is not None
    assert second.opportunity_id == first.opportunity_id
    assert second.attribution_state == first.attribution_state
    assert second.culprit_actor_ref is None
    assert first.culprit_actor_ref is None
    assert second.source_event_or_delta_refs == first.source_event_or_delta_refs
    assert second.knowledge_attribution_refs == first.knowledge_attribution_refs


def test_even_historical_object_witness_still_requires_future_current_perception_receipt():
    _, world, source_event, _ = _damaged_world()
    assert world.can_see("DOOR", "B") is True
    result = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    )
    assert result.opportunity is not None
    assert result.opportunity.realization_authorized is False
    assert result.opportunity.realization_gate == "CURRENT_PERCEPTION_EVIDENCE_REQUIRED"


def test_opportunity_is_immutable_and_cannot_be_promoted_by_caller():
    _, world, source_event, _ = _damaged_world()
    opportunity = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="B",
        entity_id="DOOR",
        source_event_id=source_event.event_id,
    ).opportunity
    assert opportunity is not None
    with pytest.raises(Exception):
        opportunity.canonical_world_authority = True
    with pytest.raises(Exception):
        opportunity.realization_authorized = True
    with pytest.raises(Exception):
        opportunity.culprit_actor_ref = "A"
