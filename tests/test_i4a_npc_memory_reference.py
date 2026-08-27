import base64
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
from awrse.model import thaw_value
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

PERCEPTION_FIELDS = {"perception_id", "npc_id", "mode", "source_event_ref", "source_actor_ref_optional", "scene_id", "acquisition_provenance", "ordering_cursor"}
MEMORY_FIELDS = {"memory_id", "npc_id", "source_perception_refs", "source_world_event_refs", "provenance_kind", "confidence", "salience", "world_time", "supersession_refs"}
BELIEF_FIELDS = {"belief_id", "npc_id", "proposition_ref", "confidence", "supporting_refs", "contradicting_refs", "status", "last_revision_cursor"}
RELATIONSHIP_FIELDS = {"npc_id", "player_id", "dimension_map", "source_refs", "last_revision_cursor"}
CONTEXT_FIELDS = {"npc_id", "world_cursor", "current_perception_refs", "relationship_refs", "episodic_memory_refs", "belief_refs", "forbidden_hidden_fact_refs", "bundle_version"}


def make_world(*, world_id: str = "WORLD_I4A") -> WorldState:
    return WorldState(
        world_id=world_id,
        active_scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        actors={
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
        principal_actor_bindings={PRINCIPAL_A: {PLAYER_A}, PRINCIPAL_B: {PLAYER_B}},
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

    witnessed = engine.resolve_and_commit(
        compile_action(world, PLAYER_B, PRINCIPAL_B, "砸铁门"), world
    )
    damage_event = next(
        event for event in witnessed.events if event.event_type == "OBJECT_DAMAGED"
    )

    engine.resolve_and_commit(
        compile_action(
            world,
            PLAYER_A,
            PRINCIPAL_A,
            f"告诉守卫 CLAIM_EVENT_ACTOR:{damage_event.event_id}:{PLAYER_A}",
        ),
        world,
    )

    hidden = engine.resolve_and_commit(
        compile_action(world, PLAYER_A, PRINCIPAL_A, "砸隐藏箱"), world
    )
    hidden_event = next(
        event for event in hidden.events if event.event_type == "OBJECT_DAMAGED"
    )

    engine.resolve_and_commit(
        compile_action(world, PLAYER_A, PRINCIPAL_A, "骂守卫蠢货"), world
    )
    return baseline, world, damage_event.event_id, hidden_event.event_id


def build_reference():
    baseline, world, damage_event_id, hidden_event_id = build_source_world()
    reference = build_npc_memory_reference(
        baseline=baseline,
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    return baseline, world, reference, damage_event_id, hidden_event_id


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


def test_i4a_golden_preserves_witness_heard_hidden_and_sparse_relationship():
    _, _, reference, damage_event_id, hidden_event_id = build_reference()

    assert all(set(item) == PERCEPTION_FIELDS for item in reference.perception_events)
    assert all(set(item) == MEMORY_FIELDS for item in reference.episodic_memories)
    assert all(set(item) == BELIEF_FIELDS for item in reference.belief_states)
    assert all(set(item) == RELATIONSHIP_FIELDS for item in reference.relationship_states)
    assert set(reference.context_bundle) == CONTEXT_FIELDS

    modes = [item["provenance_kind"] for item in reference.episodic_memories]
    assert modes.count("SAW") == 1
    assert modes.count("HEARD") == 2
    memory_sources = {
        ref
        for item in reference.episodic_memories
        for ref in item["source_world_event_refs"]
    }
    assert damage_event_id in memory_sources
    assert hidden_event_id not in memory_sources
    assert hidden_event_id in reference.context_bundle["forbidden_hidden_fact_refs"]

    relationships = [thaw_value(item) for item in reference.relationship_states]
    assert len(relationships) == 1
    assert relationships[0]["npc_id"] == NPC
    assert relationships[0]["player_id"] == PLAYER_A
    assert relationships[0]["dimension_map"] == {"legacy_relationship_delta": -10}
    assert relationships[0]["source_refs"]


def test_i4a_untrusted_heard_claim_cannot_override_direct_witness():
    _, _, reference, damage_event_id, _ = build_reference()
    beliefs = {row["proposition_ref"]: row for row in reference.belief_states}
    direct = f"WITNESSED_EVENT_ACTOR:{damage_event_id}:{PLAYER_B}"
    false_claim = f"HEARD_EVENT_ACTOR_CLAIM:{damage_event_id}:{PLAYER_A}"
    assert beliefs[direct]["status"] == "BELIEVED"
    assert beliefs[direct]["confidence"] == 1.0
    assert beliefs[false_claim]["status"] == "DISBELIEVED"
    assert len(beliefs[false_claim]["supporting_refs"]) == 1
    assert len(beliefs[false_claim]["contradicting_refs"]) == 1


def test_i4a_player_identity_is_machine_id_not_display_name():
    _, world, reference, _, _ = build_reference()
    assert world.actors[PLAYER_A].name == world.actors[PLAYER_B].name == "Alex"
    assert [row["player_id"] for row in reference.relationship_states] == [PLAYER_A]


def test_i4a_hidden_world_truth_without_acquisition_does_not_become_memory():
    _, world, reference, _, hidden_event_id = build_reference()
    assert hidden_event_id in {event.event_id for event in world.event_log}
    assert hidden_event_id not in set(world.npc_minds[NPC].knowledge_boundary_refs)
    assert hidden_event_id in reference.context_bundle["forbidden_hidden_fact_refs"]
    assert all(
        hidden_event_id not in item["source_world_event_refs"]
        for item in reference.episodic_memories
    )


def test_i4a_caller_summary_cannot_mint_memory_evidence():
    baseline, world, _, _ = build_source_world()
    with pytest.raises(
        ValueError, match="I4A_CALLER_AUTHORED_MEMORY_EVIDENCE_FORBIDDEN"
    ):
        build_npc_memory_reference(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
            caller_memory_evidence={
                "memory_id": "MEMORY:FORGED",
                "claim": "I remember everything",
            },
        )


def test_i4a_world_echo_eval_fixture_cannot_be_memory_authority():
    baseline, world, _, _ = build_source_world()
    path = (
        Path(__file__).resolve().parents[1]
        / "evals"
        / "AF001-WORLD-ECHO-CONFORMANCE.json"
    )
    evidence = json.loads(path.read_text(encoding="utf-8"))
    assert evidence["status"] == "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    with pytest.raises(
        ValueError, match="I4A_CALLER_AUTHORED_MEMORY_EVIDENCE_FORBIDDEN"
    ):
        build_npc_memory_reference(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
            caller_memory_evidence=evidence,
        )


def test_i4a_wrong_baseline_cannot_admit_plausible_world_history():
    _, world, _, _ = build_source_world()
    forged_baseline = capture_pristine_baseline(make_world(world_id="WORLD_FORGED"))
    with pytest.raises(ValueError, match="WORLD_ID_MISMATCH"):
        build_npc_memory_reference(
            baseline=forged_baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
        )


def test_i4a_relationship_event_does_not_itself_mint_memory():
    _, world, reference, _, _ = build_reference()
    relationship_events = {
        event.event_id
        for event in world.event_log
        if event.event_type == "RELATIONSHIP_CHANGED"
    }
    memory_sources = {
        ref
        for item in reference.episodic_memories
        for ref in item["source_world_event_refs"]
    }
    assert relationship_events
    assert relationship_events.isdisjoint(memory_sources)


def test_i4a_reference_is_deterministic_and_recursively_read_only():
    baseline, world, first, _, _ = build_reference()
    second = build_npc_memory_reference(
        baseline=baseline,
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    assert first == second
    assert material(first) == material(second)
    with pytest.raises(TypeError):
        first.context_bundle["belief_refs"] = ()
    with pytest.raises(TypeError):
        first.relationship_states[0]["dimension_map"]["legacy_relationship_delta"] = 999


def test_i4a_existing_i1_replay_rehydrates_exact_cognition_projection():
    baseline, world, expected, _, _ = build_reference()
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
        baseline=baseline,
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    second = export_npc_memory_replay_package(
        baseline=baseline,
        world=world,
        npc_id=NPC,
        player_ids=[PLAYER_A, PLAYER_B],
    )
    assert first == second


def test_i4a_outer_replay_tamper_fails_before_rebuild():
    baseline, world, _, _ = build_source_world()
    envelope = json.loads(
        export_npc_memory_replay_package(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
        ).decode("utf-8")
    )
    envelope["payload"]["npc_id"] = "NPC_FORGED"
    with pytest.raises(ValueError, match="I4A_REPLAY_PACKAGE_TAMPERED"):
        replay_npc_memory_package(canonical_json_bytes(envelope))


def test_i4a_forged_expected_projection_fails_with_recomputed_outer_digest():
    baseline, world, _, _ = build_source_world()
    envelope = json.loads(
        export_npc_memory_replay_package(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
        ).decode("utf-8")
    )
    envelope["payload"]["expected_reference"]["context_bundle"]["belief_refs"].append(
        "BELIEF:FORGED"
    )
    with pytest.raises(
        ValueError, match="I4A_REPLAY_PROJECTION_MATERIALIZATION_MISMATCH"
    ):
        replay_npc_memory_package(refresh_outer_digest(envelope))


def test_i4a_inner_i1_history_tamper_cannot_be_laundered_by_outer_digest():
    baseline, world, _, _ = build_source_world()
    envelope = json.loads(
        export_npc_memory_replay_package(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_B],
        ).decode("utf-8")
    )
    inner = json.loads(
        base64.b64decode(envelope["payload"]["source_i1_replay_b64"]).decode("utf-8")
    )
    inner["expected_state_version"] += 1
    bad_inner = canonical_json_bytes(inner)
    envelope["payload"]["source_i1_replay_b64"] = base64.b64encode(bad_inner).decode("ascii")
    envelope["payload"]["source_i1_replay_sha256"] = hashlib.sha256(bad_inner).hexdigest()
    with pytest.raises(ValueError, match="PERSISTENCE_PACKAGE_INTEGRITY_FAILURE"):
        replay_npc_memory_package(refresh_outer_digest(envelope))


def test_i4a_invalid_npc_and_player_identity_inputs_fail_closed():
    baseline, world, _, _ = build_source_world()
    with pytest.raises(ValueError, match="I4A_NPC_NOT_FOUND"):
        build_npc_memory_reference(
            baseline=baseline,
            world=world,
            npc_id="NPC_UNKNOWN",
            player_ids=[PLAYER_A],
        )
    with pytest.raises(ValueError, match="I4A_PLAYER_IDS_INVALID_OR_DUPLICATE"):
        build_npc_memory_reference(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=[PLAYER_A, PLAYER_A],
        )
    with pytest.raises(ValueError, match="I4A_PLAYER_ID_NOT_CANONICAL_ACTOR"):
        build_npc_memory_reference(
            baseline=baseline,
            world=world,
            npc_id=NPC,
            player_ids=["PLAYER_UNKNOWN"],
        )
