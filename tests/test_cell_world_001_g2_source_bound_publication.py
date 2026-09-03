from dataclasses import FrozenInstanceError
import inspect
import json

import pytest

from evals.publication_projection_source_bound_reference import (
    POLICY_VERSION,
    build_source_bound_publication_candidate,
    derive_source_bound_publication_evidence,
)
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


def _bootstrap_world() -> WorldState:
    return WorldState(
        world_id="CELL-WORLD-001-G2",
        active_scene_id="S1",
        baseline_version="CELL-WORLD-G2-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(
                actor_id="A",
                name="Player",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"PICK"},
            ),
            "B": ActorState(
                actor_id="B",
                name="Witness",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"SPEAK"},
            ),
        },
        objects={
            "O": ObjectState(
                object_id="O",
                name="Key",
                scene_id="S1",
                zone_id="Z1",
                graspable=True,
                affordances={"PICK"},
            )
        },
        npc_minds={"B": NPCMindState(npc_id="B", role="WITNESS")},
        scenes={
            "S1": SceneState(
                scene_id="S1",
                object_state_refs=["O"],
                actor_state_refs=["A", "B"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("O", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _canonical_package() -> bytes:
    world = _bootstrap_world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("pick up the key", "A", world, principal_id="P1")
    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    assert len(resolution.events) == 2
    return export_solo_replay_package(baseline, world)


def test_source_evidence_is_derived_from_validated_committed_events_only():
    package = _canonical_package()
    evidence = derive_source_bound_publication_evidence(package)
    rebuilt = rehydrate_solo_replay_package(package)

    assert evidence.source_event_refs == tuple(event.event_id for event in rebuilt.event_log)
    assert len(evidence.source_information_refs) == len(rebuilt.event_log) == 2
    assert len(evidence.source_material_digests) == len(rebuilt.event_log)
    for event, info_ref, material_digest in zip(
        rebuilt.event_log,
        evidence.source_information_refs,
        evidence.source_material_digests,
        strict=True,
    ):
        assert info_ref == f"EVENT_FACT:{event.event_id}:{material_digest}"
        assert len(material_digest) == 64

    assert evidence.canonical_data_authority == "NONE"
    assert evidence.publication_authority == "NONE"
    assert evidence.player_knowledge_authority == "NONE"
    assert evidence.npc_knowledge_authority == "NONE"
    assert evidence.current_observation_authority == "NONE"


def test_reviewer_p1_caller_controlled_field_agreement_cannot_mint_provenance():
    package = _canonical_package()
    fake_ref = "INVENTED_SECRET:CALLER-MINTED"

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

    candidate = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    assert fake_ref not in candidate.allowed_information_refs
    assert fake_ref not in candidate.source_event_refs


def test_omniscient_candidate_can_only_select_source_bound_committed_event_facts():
    package = _canonical_package()
    evidence = derive_source_bound_publication_evidence(package)
    candidate = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )

    assert candidate.source_event_refs == evidence.source_event_refs
    assert candidate.allowed_information_refs == evidence.source_information_refs
    assert candidate.redacted_information_refs == ()
    assert candidate.presentation_refs == ()
    assert candidate.policy_version == POLICY_VERSION
    assert candidate.canonical_data_authority == "NONE"
    assert candidate.staging_authority == "NONE"
    assert candidate.knowledge_write_authority == "NONE"
    assert candidate.world_mutation_authority == "NONE"


def test_strict_player_equivalent_fails_closed_without_explicit_player_provenance():
    package = _canonical_package()
    evidence = derive_source_bound_publication_evidence(package)
    candidate = build_source_bound_publication_candidate(
        package,
        audience_class="STRICT_PLAYER_EQUIVALENT",
    )

    # Actor binding and the simulator knowing who acted are not accepted
    # replay-positive DIRECT_PARTICIPATION provenance for player knowledge.
    assert candidate.source_event_refs == ()
    assert candidate.allowed_information_refs == ()
    assert candidate.redacted_information_refs == evidence.source_information_refs

    with pytest.raises(ValueError, match="STRICT_PLAYER_EQUIVALENT_FAILS_CLOSED"):
        build_source_bound_publication_candidate(
            package,
            audience_class="STRICT_PLAYER_EQUIVALENT",
            publication_cursor_event_count=1,
        )


def test_delayed_candidate_cursor_can_only_restrict_never_invent_source_facts():
    package = _canonical_package()
    evidence = derive_source_bound_publication_evidence(package)

    hidden = build_source_bound_publication_candidate(
        package,
        audience_class="DELAYED_REVEAL_CANDIDATE",
        publication_cursor_event_count=0,
    )
    first = build_source_bound_publication_candidate(
        package,
        audience_class="DELAYED_REVEAL_CANDIDATE",
        publication_cursor_event_count=1,
    )
    all_revealed = build_source_bound_publication_candidate(
        package,
        audience_class="DELAYED_REVEAL_CANDIDATE",
        publication_cursor_event_count=len(evidence.source_event_refs),
    )

    assert hidden.allowed_information_refs == ()
    assert hidden.redacted_information_refs == evidence.source_information_refs
    assert first.allowed_information_refs == evidence.source_information_refs[:1]
    assert first.source_event_refs == evidence.source_event_refs[:1]
    assert all_revealed.allowed_information_refs == evidence.source_information_refs

    with pytest.raises(ValueError, match="DELAYED_REVEAL_CURSOR_OUT_OF_RANGE"):
        build_source_bound_publication_candidate(
            package,
            audience_class="DELAYED_REVEAL_CANDIDATE",
            publication_cursor_event_count=len(evidence.source_event_refs) + 1,
        )


def test_tampered_or_malformed_replay_package_fails_before_publication_derivation():
    package = _canonical_package()
    decoded = json.loads(package.decode("utf-8"))
    decoded["world_id"] = "ATTACKER-WORLD"
    tampered = json.dumps(decoded, sort_keys=True, separators=(",", ":")).encode("utf-8")

    with pytest.raises(ValueError):
        derive_source_bound_publication_evidence(tampered)
    with pytest.raises(ValueError):
        build_source_bound_publication_candidate(
            b"{not-json",
            audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
        )


def test_publication_derivation_is_deterministic_immutable_and_has_zero_flowback():
    package = _canonical_package()
    before = rehydrate_solo_replay_package(package)
    before_event_ids = tuple(event.event_id for event in before.event_log)
    before_owner = before.objects["O"].owner_actor_id
    before_npc_knowledge = tuple(before.npc_minds["B"].knowledge_boundary_refs)

    first = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    second = build_source_bound_publication_candidate(
        package,
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
    )
    assert first == second

    with pytest.raises(FrozenInstanceError):
        first.audience_class = "ATTACKER"

    after = rehydrate_solo_replay_package(package)
    assert tuple(event.event_id for event in after.event_log) == before_event_ids
    assert after.objects["O"].owner_actor_id == before_owner == "A"
    assert tuple(after.npc_minds["B"].knowledge_boundary_refs) == before_npc_knowledge


def test_unknown_audience_and_cursor_shape_fail_closed():
    package = _canonical_package()
    with pytest.raises(ValueError, match="UNSUPPORTED_PUBLICATION_AUDIENCE_CLASS"):
        build_source_bound_publication_candidate(package, audience_class="ATTACKER")
    with pytest.raises(ValueError, match="DELAYED_REVEAL_CURSOR_REQUIRED"):
        build_source_bound_publication_candidate(
            package,
            audience_class="DELAYED_REVEAL_CANDIDATE",
        )
    with pytest.raises(ValueError, match="OMNISCIENT_CANDIDATE_DOES_NOT_ACCEPT_CURSOR"):
        build_source_bound_publication_candidate(
            package,
            audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
            publication_cursor_event_count=0,
        )
