import base64
import copy
import hashlib
import json
from pathlib import Path

import pytest

from awrse import (
    ActionCompiler,
    ActorState,
    NPCMindState,
    ObjectState,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
)
from awrse.model import Event, thaw_value
from evals.i4a_npc_memory_reference import (
    I4_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_LLM_MEMORY_AUTHORITY,
    NO_MEMORY_BACKEND_SELECTED,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    build_npc_memory_reference,
    export_npc_memory_replay_package,
    replay_npc_memory_package,
)


PLAYER_A = "PLAYER_A"
PLAYER_B = "PLAYER_B"
NPC = "NPC_GUARD"
DOOR = "DOOR_001"
HIDDEN_BOX = "BOX_HIDDEN"
PRINCIPAL_A = "principal://i4a/a"
PRINCIPAL_B = "principal://i4a/b"
BASELINE_VERSION = "I4A-BASELINE-v1"


def make_world() -> WorldState:
    return WorldState(
        world_id="WORLD_I4A",
        active_scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        actors={
            # Deliberately identical display names prove machine IDs remain the
            # relationship/memory identity, never human-readable names.
            PLAYER_A: ActorState(PLAYER_A, "Alex", "SCENE_001", capabilities={"SPEAK", "HIT"}),
            PLAYER_B: ActorState(PLAYER_B, "Alex", "SCENE_001", capabilities={"SPEAK", "HIT"}),
            NPC: ActorState(NPC, "守卫", "SCENE_001", capabilities={"SPEAK", "HIT"}),
        },
        objects={
            DOOR: ObjectState(DOOR, "铁门", "SCENE_001", mass=40.0, graspable=False, fragility=0.4),
            HIDDEN_BOX: ObjectState(HIDDEN_BOX, "隐藏箱", "SCENE_001", mass=10.0, graspable=False, fragility=0.4),
        },
        npc_minds={NPC: NPCMindState(NPC, "GUARD")},
        scenes={
            "SCENE_001": SceneState(
                "SCENE_001",
                ["asset://i4a/scene"],
                [DOOR, HIDDEN_BOX],
                [PLAYER_A, PLAYER_B, NPC],
            )
        },
        principal_actor_bindings={
            PRINCIPAL_A: {PLAYER_A},
            PRINCIPAL_B: {PLAYER_B},
        },
        reachable_pairs={
            (PLAYER_A, DOOR),
            (PLAYER_A, HIDDEN_BOX),
            (PLAYER_B, DOOR),
            (PLAYER_B, HIDDEN_BOX),
        },
        audible_pairs={(PLAYER_A, NPC), (PLAYER_B, NPC)},
        visible_pairs={(DOOR, NPC)},
    )


def compile_action(world: WorldState, actor_id: str, principal_id: str, text: str):
    return ActionCompiler().compile(text, actor_id, world, principal_id)


def build_source_world():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()

    # PLAYER_B creates a canonical object event while the NPC has a valid SAW path.
    damage = engine.resolve_and_commit(
        compile_action(world, PLAYER_B, PRINCIPAL_B, "砸铁门"),
        world,
    )
    damage_event = next(event for event in damage.events if event.event_type == "OBJECT_DAMAGED")

    # PLAYER_A later makes a low-authority claim about the exact canonical event.
    # The NPC may remember hearing the claim, but the claim cannot rewrite actor_id.
    engine.resolve_and_commit(
        compile_action(
            world,
            PLAYER_A,
            PRINCIPAL_A,
            f"告诉守卫 CLAIM_EVENT_ACTOR:{damage_event.event_id}:{PLAYER_A}",
        ),
        world,
    )

    # This is canonical world truth but HIDDEN_BOX has no NPC visibility path.
    hidden = engine.resolve_and_commit(
        compile_action(world, PLAYER_A, PRINCIPAL_A, "砸隐藏箱"),
        world,
    )
    hidden_event = next(event for event in hidden.events if event.event_type == "OBJECT_DAMAGED")

    # Canonical social interaction creates a sparse relationship projection for A only.
    engine.resolve_and_commit(
        compile_action(world, PLAYER_A, PRINCIPAL_A, "骂守卫蠢货"),
        world,
    )
    return baseline, world, damage_event.event_id, hidden_event.event_id


def material(reference):
    return {
        "npc_id": reference.npc_id,
        "player_ids": list(reference.player_ids),
        "contract_id": reference.contract_id,
        "contract_version": reference.contract_version,
        "authority_graph_version": reference.authority_graph_version,
        "source_world_id": reference.source_world_id,
        "source_baseline_version": reference.source_baseline_version,
        "source_state_version": reference.source_state_version,
        "source_event_sha256": reference.source_event_sha256,
        "perception_events": [thaw_value(item) for item in reference.perception_events],
        "episodic_memories": [thaw_value(item) for item in reference.episodic_memories],
        "belief_states": [thaw_value(item) for item in reference.belief_states],
        "relationship_states": [thaw_value(item) for item in reference.relationship_states],
        "context_bundle": thaw_value(reference.context_bundle),
    }


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def refresh_outer_digest(envelope: dict) -> bytes:
    envelope["sha256"] = hashlib.sha256(
        canonical_json_bytes(envelope["payload"])
    ).hexdigest()
    return canonical_json_bytes(envelope)


def test_i4a_scope_locks_remain_narrow():
    assert I4_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_MEMORY_BACKEND_SELECTED is True
    assert NO_LLM_MEMORY_AUTHORITY is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i4a_golden_one_npc_two_players_preserves_witness_heard_hidden_and_sparse_relationship():
    _, world, damage_event_id, hidden_event_id = build_source_world()
    reference = build_npc_memory_reference(
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )

    modes = [item["provenance_kind"] for item in reference.episodic_memories]
    assert modes.count("SAW") == 1
    assert modes.count("HEARD") == 2
    assert all(item["npc_id"] == NPC for item in reference.episodic_memories)

    memory_source_refs = {
        ref
        for item in reference.episodic_memories
        for ref in item["source_world_event_refs"]
    }
    assert damage_event_id in memory_source_refs
    assert hidden_event_id not in memory_source_refs
    assert hidden_event_id in reference.context_bundle["forbidden_hidden_fact_refs"]

    relationships = [thaw_value(item) for item in reference.relationship_states]
    assert relationships == [
        {
            "relationship_ref": f"REL:{NPC}:{PLAYER_A}",
            "npc_id": NPC,
            "player_id": PLAYER_A,
            "dimension_map": {"legacy_relationship_delta": -10},
            "source_refs": relationships[0]["source_refs"],
            "last_revision_cursor": relationships[0]["last_revision_cursor"],
            "projection_policy": "SPARSE_EVENT_DERIVED_REFERENCE_ONLY_RELATIONSHIP_MATH_REMAINS_OPEN_DECISION",
        }
    ]
    assert all(row["player_id"] != PLAYER_B for row in relationships)


def test_i4a_untrusted_heard_claim_cannot_override_direct_witnessed_event_actor():
    _, world, damage_event_id, _ = build_source_world()
    reference = build_npc_memory_reference(
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    beliefs = {row["proposition_ref"]: row for row in reference.belief_states}

    direct_key = f"WITNESSED_EVENT_ACTOR:{damage_event_id}:{PLAYER_B}"
    false_claim_key = f"HEARD_EVENT_ACTOR_CLAIM:{damage_event_id}:{PLAYER_A}"
    assert beliefs[direct_key]["status"] == "BELIEVED"
    assert beliefs[direct_key]["confidence"] == 1.0
    assert beliefs[false_claim_key]["status"] == "DISBELIEVED"
    assert len(beliefs[false_claim_key]["supporting_refs"]) == 1
    assert len(beliefs[false_claim_key]["contradicting_refs"]) == 1


def test_i4a_player_identity_is_machine_id_not_same_display_name():
    _, world, _, _ = build_source_world()
    assert world.actors[PLAYER_A].name == world.actors[PLAYER_B].name == "Alex"
    reference = build_npc_memory_reference(
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    relationships = [thaw_value(item) for item in reference.relationship_states]
    assert [row["player_id"] for row in relationships] == [PLAYER_A]


def test_i4a_canonical_world_truth_without_acquisition_path_does_not_become_memory():
    _, world, _, hidden_event_id = build_source_world()
    assert hidden_event_id in {event.event_id for event in world.event_log}
    assert hidden_event_id not in set(world.npc_minds[NPC].knowledge_boundary_refs)
    reference = build_npc_memory_reference(
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    assert hidden_event_id in reference.context_bundle["forbidden_hidden_fact_refs"]
    assert all(
        hidden_event_id not in item["source_world_event_refs"]
        for item in reference.episodic_memories
    )


def test_i4a_caller_or_summary_mapping_cannot_mint_memory_evidence():
    _, world, _, _ = build_source_world()
    forged = {
        "npc_id": NPC,
        "memory_id": "MEMORY:FORGED",
        "claim": "I remember everything",
    }
    with pytest.raises(ValueError, match="I4A_CALLER_AUTHORED_MEMORY_EVIDENCE_FORBIDDEN"):
        build_npc_memory_reference(
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
            caller_memory_evidence=forged,
        )


def test_i4a_prior_world_echo_eval_fixture_cannot_be_supplied_as_memory_authority():
    _, world, _, _ = build_source_world()
    path = Path(__file__).resolve().parents[1] / "evals" / "AF001-WORLD-ECHO-CONFORMANCE.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["status"] == "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    with pytest.raises(ValueError, match="I4A_CALLER_AUTHORED_MEMORY_EVIDENCE_FORBIDDEN"):
        build_npc_memory_reference(
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
            caller_memory_evidence=evidence,
        )


def test_i4a_cross_npc_acquisition_ref_fails_closed():
    world = make_world()
    speech = Event(
        event_id="E-SOURCE",
        event_type="SPEECH_UTTERED",
        actor_id=PLAYER_A,
        scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        payload={
            "literal_content": "hello",
            "trust_class": "UNTRUSTED_DATA",
            "authority": "NONE_OVER_TARGET_INTERNAL_STATE",
        },
    )
    wrong_acquisition = Event(
        event_id="E-WRONG-NPC",
        event_type="NPC_KNOWLEDGE_ACQUIRED",
        actor_id=PLAYER_A,
        scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        payload={
            "npc_id": "NPC_OTHER",
            "mode": "HEARD",
            "source_event_id": speech.event_id,
            "speaker_id": PLAYER_A,
        },
    )
    world.event_log = [speech, wrong_acquisition]
    world.committed_event_ids = {speech.event_id, wrong_acquisition.event_id}
    world.state_version = 2
    world.npc_minds[NPC].memories = [wrong_acquisition.event_id]
    world.npc_minds[NPC].knowledge_boundary_refs = [speech.event_id]

    with pytest.raises(ValueError, match="I4A_CROSS_NPC_MEMORY_LEAK"):
        build_npc_memory_reference(
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
        )


def test_i4a_relationship_event_does_not_itself_mint_memory():
    _, world, _, _ = build_source_world()
    relationship_event_ids = {
        event.event_id
        for event in world.event_log
        if event.event_type == "RELATIONSHIP_CHANGED"
    }
    assert relationship_event_ids
    reference = build_npc_memory_reference(
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    memory_sources = {
        ref
        for item in reference.episodic_memories
        for ref in item["source_world_event_refs"]
    }
    assert relationship_event_ids.isdisjoint(memory_sources)


def test_i4a_reference_is_deterministic_and_recursively_read_only():
    _, world, _, _ = build_source_world()
    first = build_npc_memory_reference(world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B])
    second = build_npc_memory_reference(world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B])
    assert first == second
    assert material(first) == material(second)
    with pytest.raises(TypeError):
        first.context_bundle["belief_refs"] = ()
    with pytest.raises(TypeError):
        first.relationship_states[0]["dimension_map"]["legacy_relationship_delta"] = 999


def test_i4a_existing_i1_replay_rehydrates_exact_cognition_projection():
    baseline, world, _, _ = build_source_world()
    expected = build_npc_memory_reference(world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B])
    package = export_npc_memory_replay_package(
        baseline=baseline,
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    rebuilt = replay_npc_memory_package(package)
    assert rebuilt == expected
    assert material(rebuilt) == material(expected)


def test_i4a_replay_package_is_byte_deterministic():
    baseline, world, _, _ = build_source_world()
    first = export_npc_memory_replay_package(
        baseline=baseline, world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B]
    )
    second = export_npc_memory_replay_package(
        baseline=baseline, world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B]
    )
    assert first == second


def test_i4a_outer_replay_tamper_fails_before_rebuild():
    baseline, world, _, _ = build_source_world()
    package = export_npc_memory_replay_package(
        baseline=baseline, world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B]
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["npc_id"] = "NPC_FORGED"
    with pytest.raises(ValueError, match="I4A_REPLAY_PACKAGE_TAMPERED"):
        replay_npc_memory_package(canonical_json_bytes(envelope))


def test_i4a_forged_expected_projection_fails_even_with_recomputed_outer_digest():
    baseline, world, _, _ = build_source_world()
    package = export_npc_memory_replay_package(
        baseline=baseline, world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B]
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_reference"]["context_bundle"]["belief_refs"].append("BELIEF:FORGED")
    tampered = refresh_outer_digest(envelope)
    with pytest.raises(ValueError, match="I4A_REPLAY_PROJECTION_MATERIALIZATION_MISMATCH"):
        replay_npc_memory_package(tampered)


def test_i4a_inner_i1_history_tamper_still_fails_even_if_outer_digest_is_recomputed():
    baseline, world, _, _ = build_source_world()
    package = export_npc_memory_replay_package(
        baseline=baseline, world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_B]
    )
    envelope = json.loads(package.decode("utf-8"))
    inner = json.loads(base64.b64decode(envelope["payload"]["source_i1_replay_b64"]).decode("utf-8"))
    inner["expected_state_version"] += 1
    bad_inner = canonical_json_bytes(inner)
    envelope["payload"]["source_i1_replay_b64"] = base64.b64encode(bad_inner).decode("ascii")
    envelope["payload"]["source_i1_replay_sha256"] = hashlib.sha256(bad_inner).hexdigest()
    tampered = refresh_outer_digest(envelope)
    with pytest.raises(ValueError, match="PERSISTENCE_PACKAGE_INTEGRITY_FAILURE"):
        replay_npc_memory_package(tampered)


def test_i4a_unknown_npc_duplicate_players_and_noncanonical_player_fail_closed():
    _, world, _, _ = build_source_world()
    with pytest.raises(ValueError, match="I4A_NPC_NOT_FOUND"):
        build_npc_memory_reference(world=world, npc_id="NPC_UNKNOWN", player_ids=[PLAYER_A])
    with pytest.raises(ValueError, match="I4A_PLAYER_IDS_INVALID_OR_DUPLICATE"):
        build_npc_memory_reference(world=world, npc_id=NPC, player_ids=[PLAYER_A, PLAYER_A])
    with pytest.raises(ValueError, match="I4A_PLAYER_ID_NOT_CANONICAL_ACTOR"):
        build_npc_memory_reference(world=world, npc_id=NPC, player_ids=["PLAYER_UNKNOWN"])
