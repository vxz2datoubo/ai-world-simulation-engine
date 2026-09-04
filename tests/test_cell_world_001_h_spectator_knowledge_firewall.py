from dataclasses import FrozenInstanceError
import inspect

import pytest

from evals.current_observation_evidence_reference import (
    CurrentObservationEvidenceError,
    assess_current_visual_observation_gap,
    capture_current_visual_observation,
)
from evals.publication_projection_source_bound_reference import (
    build_source_bound_publication_candidate,
    derive_source_bound_publication_evidence,
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
    """Read-only test view: current visibility changes without rewriting history."""

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
        world_id="CELL-WORLD-001-H",
        active_scene_id="S1",
        baseline_version="CELL-H-R1",
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
                base_asset_refs=["asset://cell-h-room"],
                object_state_refs=["DOOR"],
                actor_state_refs=["A", "B", "C"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("DOOR", "B"), ("A", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _commit_damage():
    world = _world()
    assert world.can_see("DOOR", "C") is False
    assert world.can_see("A", "C") is False
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    source = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    assert source.actor_id == "A"
    assert str(source.payload.get("object_id", "")) == "DOOR"
    package = export_solo_replay_package(baseline, world)
    return baseline, world, source, package


def _assert_c_has_no_source_knowledge(world, source_event_id: str) -> None:
    npc = world.npc_minds["C"]
    assert source_event_id not in npc.knowledge_boundary_refs
    assert not any(
        event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and str(event.payload.get("npc_id", "")) == "C"
        and str(event.payload.get("source_event_id", "")) == source_event_id
        for event in world.event_log
    )


def _source_information_ref(package: bytes, source_event_id: str) -> str:
    evidence = derive_source_bound_publication_evidence(package)
    index = evidence.source_event_refs.index(source_event_id)
    info_ref = evidence.source_information_refs[index]
    material_digest = evidence.source_material_digests[index]
    assert info_ref == f"EVENT_FACT:{source_event_id}:{material_digest}"
    assert len(material_digest) == 64
    return info_ref


def test_same_canonical_damage_fact_can_reach_spectator_without_entering_npc_c_knowledge():
    _, world, source, package = _commit_damage()
    _assert_c_has_no_source_knowledge(world, source.event_id)

    info_ref = _source_information_ref(package, source.event_id)
    spectator = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )

    assert source.event_id in spectator.source_event_refs
    assert info_ref in spectator.allowed_information_refs
    assert spectator.knowledge_write_authority == "NONE"
    assert spectator.world_mutation_authority == "NONE"
    assert spectator.canonical_data_authority == "NONE"
    _assert_c_has_no_source_knowledge(world, source.event_id)

    strict_player = build_source_bound_publication_candidate(
        package,
        audience_class="STRICT_PLAYER_EQUIVALENT",
    )
    assert strict_player.source_event_refs == ()
    assert strict_player.allowed_information_refs == ()


def test_spectator_reveal_plus_later_visibility_cannot_retroactively_mint_culprit_knowledge():
    baseline, world, source, package = _commit_damage()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_state_version = world.world_state_version
    before_damage = world.objects["DOOR"].damage_state
    before_memories = tuple(world.npc_minds["C"].memories)
    before_boundary = tuple(world.npc_minds["C"].knowledge_boundary_refs)
    before_package = export_solo_replay_package(baseline, world)
    assert before_package == package

    historical = derive_world_echo_opportunity(
        world=world,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    assert historical.status == "NO_VALID_OPPORTUNITY"
    assert historical.reason == "NO_PROVEN_ACQUISITION_OR_CURRENT_PERCEPTION"
    assert historical.opportunity is None

    spectator = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    assert _source_information_ref(package, source.event_id) in spectator.allowed_information_refs

    later = _LaterCurrentVisibilityView(world, entity_id="DOOR", observer_actor_id="C")
    assert later.can_see("DOOR", "C") is True
    assert later.can_see("A", "C") is False

    echo_after_reveal = derive_world_echo_opportunity(
        world=later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=source.event_id,
    )
    assert echo_after_reveal == historical
    assert echo_after_reveal.opportunity is None

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

    _assert_c_has_no_source_knowledge(world, source.event_id)
    assert tuple(event.event_id for event in world.event_log) == before_event_ids
    assert world.world_state_version == before_state_version
    assert world.objects["DOOR"].damage_state == before_damage
    assert tuple(world.npc_minds["C"].memories) == before_memories
    assert tuple(world.npc_minds["C"].knowledge_boundary_refs) == before_boundary
    assert export_solo_replay_package(baseline, world) == before_package


def test_publication_projection_is_read_only_and_cannot_flow_back_across_restart_replay():
    _, world, source, package = _commit_damage()
    first = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    info_ref = _source_information_ref(package, source.event_id)
    assert info_ref in first.allowed_information_refs

    with pytest.raises(FrozenInstanceError):
        first.knowledge_write_authority = "ATTACKER"

    rebuilt = rehydrate_solo_replay_package(package)
    replayed_source = next(event for event in rebuilt.event_log if event.event_id == source.event_id)
    assert replayed_source.actor_id == "A"
    assert str(replayed_source.payload.get("object_id", "")) == "DOOR"
    _assert_c_has_no_source_knowledge(rebuilt, replayed_source.event_id)

    later = _LaterCurrentVisibilityView(rebuilt, entity_id="DOOR", observer_actor_id="C")
    replay_echo = derive_world_echo_opportunity(
        world=later,
        speaker_npc_id="C",
        entity_id="DOOR",
        source_event_id=replayed_source.event_id,
    )
    replay_gap = assess_current_visual_observation_gap(
        world=later,
        observer_actor_id="C",
        entity_id="DOOR",
    )
    assert replay_echo.status == "NO_VALID_OPPORTUNITY"
    assert replay_echo.opportunity is None
    assert replay_gap.visibility_eligible is True
    assert replay_gap.status == "NO_TRUSTED_OBSERVATION_TRIGGER"
    assert replay_gap.receipt_available is False

    second = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    assert second == first
    _assert_c_has_no_source_knowledge(rebuilt, replayed_source.event_id)


def test_coordinated_caller_minted_secret_refs_cannot_enter_h_source_bound_pipeline():
    _, world, source, package = _commit_damage()
    fake_ref = "EVENT_FACT:ATTACKER:CALLER-MINTED-SECRET"
    signature = inspect.signature(build_source_bound_publication_candidate)
    forbidden_positive_inputs = {
        "available_information_refs",
        "player_visible_information_refs",
        "spectator_visible_information_refs",
        "allowed_information_refs",
        "source_event_refs",
    }
    assert forbidden_positive_inputs.isdisjoint(signature.parameters)

    with pytest.raises(TypeError):
        build_source_bound_publication_candidate(
            package,
            audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
            available_information_refs={fake_ref},
            player_visible_information_refs={fake_ref},
            spectator_visible_information_refs={fake_ref},
            allowed_information_refs={fake_ref},
            source_event_refs={fake_ref},
        )

    spectator = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    assert fake_ref not in spectator.allowed_information_refs
    assert fake_ref not in spectator.source_event_refs
    assert _source_information_ref(package, source.event_id) in spectator.allowed_information_refs
    _assert_c_has_no_source_knowledge(world, source.event_id)
