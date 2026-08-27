import hashlib
import json

import pytest

import evals.i7a_player_private_world_echo_reference as i7a_reference
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
from evals.i7a_player_private_world_echo_reference import (
    I7_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_DIEGETIC_PLAYER_SPEECH,
    NO_LLM_OR_PROVIDER,
    NO_NPC_KNOWLEDGE_MUTATION,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PX_DIRECTOR_RENDERER_AUTHORITY,
    NO_WORLD_EVENT_COMMIT,
    ReferencePrivateEchoFilter,
    build_player_private_world_echo_reference,
    export_player_private_world_echo_package,
    replay_player_private_world_echo_package,
)

PLAYER = "PLAYER-A"
NPC = "NPC-BYSTANDER"
DOOR = "OBJ-TAVERN-DOOR"
CRATE = "OBJ-CRATE"
TAVERN = "SCN-TAVERN"
PRINCIPAL = "principal://i7a/player"
BASELINE_VERSION = "I7A-BASELINE-v1"


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


def make_world():
    world = WorldState(
        world_id="WORLD-I7A",
        active_scene_id=TAVERN,
        baseline_version=BASELINE_VERSION,
        primary_player_actor_id=PLAYER,
        actors={
            PLAYER: ActorState(
                PLAYER,
                "旅人",
                TAVERN,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            NPC: ActorState(
                NPC,
                "酒馆老板",
                TAVERN,
                capabilities={"SPEAK"},
            ),
        },
        objects={
            DOOR: ObjectState(
                DOOR,
                "木门",
                TAVERN,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            CRATE: ObjectState(
                CRATE,
                "木箱",
                TAVERN,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={NPC: NPCMindState(NPC, "TAVERN_KEEPER")},
        scenes={
            TAVERN: SceneState(
                TAVERN,
                ["asset://i7a/tavern"],
                [DOOR, CRATE],
                [PLAYER, NPC],
            )
        },
        principal_actor_bindings={PRINCIPAL: {PLAYER}},
        reachable_pairs={(PLAYER, DOOR), (PLAYER, CRATE)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", PLAYER, world, PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(
        event for event in resolution.events if event.event_type == "OBJECT_DAMAGED"
    )
    return baseline, world, source


def make_filter(**overrides):
    values = {
        "fixture_id": "I7A-PRIVATE-ECHO-FILTER-001",
        "already_seen_novelty_keys": (),
        "urgent_context": False,
        "private_commentary_enabled": True,
    }
    values.update(overrides)
    return ReferencePrivateEchoFilter(**values)


def build_valid_reference(**filter_overrides):
    baseline, world, source = make_world()
    fixture = make_filter(**filter_overrides)
    reference = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    return baseline, world, source, fixture, reference


def _build_with_drifted_contract(tmp_path, monkeypatch, mutate, expected_error):
    baseline, world, source = make_world()
    contract = json.loads(i7a_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(contract)
    drifted = tmp_path / "AF001-LIVING-STORY-CONTRACTS-drifted.json"
    drifted.write_text(
        json.dumps(contract, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(i7a_reference, "_CONTRACT_PATH", drifted)
    with pytest.raises(ValueError, match=expected_error):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_scope_locks_preserve_player_and_world_authority():
    assert I7_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_DIEGETIC_PLAYER_SPEECH is True
    assert NO_WORLD_EVENT_COMMIT is True
    assert NO_NPC_KNOWLEDGE_MUTATION is True
    assert NO_LLM_OR_PROVIDER is True
    assert NO_PX_DIRECTOR_RENDERER_AUTHORITY is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i7a_self_caused_persistent_damage_builds_private_echo_only():
    _, _, source, _, reference = build_valid_reference()
    opportunity = thaw_value(reference.world_echo_opportunity)
    concept = thaw_value(reference.response_concept)
    realization = thaw_value(reference.realization)

    assert reference.status == "PRIVATE_WORLD_ECHO_READY"
    assert reference.player_actor_id == PLAYER
    assert reference.target_object_id == DOOR
    assert reference.source_event_id == source.event_id
    assert reference.attribution_kind == (
        "SELF_KNOWN_CAUSE_FROM_CANONICAL_PLAYER_ACTION_EVENT"
    )
    assert opportunity["speaker_candidate_refs"] == [PLAYER]
    assert opportunity["novelty_key"] == reference.novelty_key
    assert concept["speech_risk_class"] == "R1_LOW_RISK_OBSERVATION"
    assert realization["mode"] == "PRIVATE_INNER_COMMENTARY"
    assert realization["audible"] is False
    assert realization["diegetic_speech"] is False
    assert realization["world_event_created"] is False
    assert realization["npc_knowledge_mutation_count"] == 0
    assert realization["player_intent_created"] is False
    assert realization["social_consequence_created"] is False
    assert realization["surface_realization"] == "UNREALIZED_TYPED_CONCEPT_ONLY"


def test_i7a_build_is_read_only_for_world_and_npc_state():
    baseline, world, source = make_world()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_state_version = world.state_version
    before_memories = tuple(world.npc_minds[NPC].memories)
    before_knowledge = tuple(world.npc_minds[NPC].knowledge_boundary_refs)

    build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=make_filter(),
    )

    assert tuple(event.event_id for event in world.event_log) == before_event_ids
    assert world.state_version == before_state_version
    assert tuple(world.npc_minds[NPC].memories) == before_memories
    assert tuple(world.npc_minds[NPC].knowledge_boundary_refs) == before_knowledge


def test_i7a_caller_cannot_substitute_non_primary_player():
    baseline, world, source = make_world()
    with pytest.raises(ValueError, match="I7A_PLAYER_ACTOR_NOT_CANONICAL_PRIMARY_PLAYER"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=NPC,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_caller_cannot_substitute_target_object():
    baseline, world, source = make_world()
    with pytest.raises(ValueError, match="I7A_SOURCE_EVENT_OBJECT_BINDING_MISMATCH"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=CRATE,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_non_damage_source_event_cannot_mint_echo():
    baseline, world, _ = make_world()
    other = SimulationEngine().transition_active_scene(TAVERN, world)
    with pytest.raises(ValueError, match="I7A_SOURCE_EVENT_TYPE_NOT_OBJECT_DAMAGED"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=other.event_id,
            fixture=make_filter(),
        )


def test_i7a_caller_authored_echo_evidence_is_forbidden():
    baseline, world, source = make_world()
    with pytest.raises(ValueError, match="I7A_CALLER_AUTHORED_ECHO_EVIDENCE_FORBIDDEN"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
            caller_echo_evidence={
                "culprit": PLAYER,
                "claim": "CANONICAL",
                "source_event_id": source.event_id,
            },
        )


def test_i7a_reference_filter_cannot_escalate_to_player_policy_authority():
    baseline, world, source = make_world()
    fixture = make_filter(authority_class="PLAYER_EXPLICIT_AUTHORITY")
    with pytest.raises(ValueError, match="I7A_REFERENCE_FILTER_AUTHORITY_ESCALATION"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=fixture,
        )


def test_i7a_seen_novelty_suppresses_without_changing_canonical_facts():
    baseline, world, source = make_world()
    first = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=make_filter(),
    )
    suppressed = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=make_filter(already_seen_novelty_keys=(first.novelty_key,)),
    )
    realization = thaw_value(suppressed.realization)

    assert suppressed.status == "SILENCE"
    assert suppressed.canonical_fact_refs == first.canonical_fact_refs
    assert suppressed.novelty_key == first.novelty_key
    assert realization["mode"] == "SILENCE"
    assert realization["suppression_reason"] == "NOVELTY_ALREADY_SEEN"
    assert realization["claim_fact_refs"] == []
    assert realization["world_event_created"] is False


@pytest.mark.parametrize(
    ("filter_overrides", "reason"),
    [
        (
            {"urgent_context": True},
            "URGENT_CONTEXT_SUPPRESSES_LOW_RISK_CALLBACK",
        ),
        (
            {"private_commentary_enabled": False},
            "REFERENCE_PRIVATE_COMMENTARY_DISABLED",
        ),
    ],
)
def test_i7a_reference_filter_only_suppresses(filter_overrides, reason):
    _, _, _, _, reference = build_valid_reference(**filter_overrides)
    realization = thaw_value(reference.realization)
    assert reference.status == "SILENCE"
    assert realization["suppression_reason"] == reason
    assert realization["audible"] is False
    assert realization["world_event_created"] is False
    assert realization["player_intent_created"] is False


def test_i7a_same_exact_inputs_are_deterministic():
    baseline, world, source = make_world()
    fixture = make_filter()
    first = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    second = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    assert first == second


def test_i7a_package_is_byte_deterministic_and_replays_exactly():
    baseline, world, source = make_world()
    fixture = make_filter()
    first = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    second = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    assert first == second
    rebuilt = replay_player_private_world_echo_package(first)
    expected = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=fixture,
    )
    assert rebuilt == expected


def test_i7a_outer_package_tamper_fails_closed():
    baseline, world, source = make_world()
    package = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=make_filter(),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["target_object_id"] = CRATE
    with pytest.raises(ValueError, match="I7A_REPLAY_PACKAGE_TAMPERED"):
        replay_player_private_world_echo_package(canonical_json_bytes(envelope))


def test_i7a_forged_diegetic_expected_realization_with_recomputed_digest_fails_closed():
    baseline, world, source = make_world()
    package = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        target_object_id=DOOR,
        source_event_id=source.event_id,
        fixture=make_filter(),
    )
    envelope = json.loads(package.decode("utf-8"))
    realization = envelope["payload"]["expected_reference"]["realization"]
    realization["mode"] = "DIEGETIC_PLAYER_SPEECH"
    realization["audible"] = True
    realization["diegetic_speech"] = True
    realization["world_event_created"] = True
    with pytest.raises(ValueError, match="I7A_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH"):
        replay_player_private_world_echo_package(refresh_outer_digest(envelope))


def test_i7a_materialized_world_damage_tamper_fails_closed_through_i1():
    baseline, world, source = make_world()
    object.__setattr__(world.objects[DOOR], "damage_state", "INTACT")
    with pytest.raises(ValueError):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_canonical_world_echo_type_version_drift_fails_closed_through_public_build(
    tmp_path, monkeypatch
):
    def mutate(contract):
        contract["type_registry"]["WorldEchoOpportunity"]["version"] = "999-drift"

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I7A_CANONICAL_TYPE_DRIFT:WorldEchoOpportunity",
    )


def test_i7a_af_g_invariant_drift_fails_closed_through_public_build(
    tmp_path, monkeypatch
):
    def mutate(contract):
        contract["freeze_domains"]["AF-G"]["invariants"].remove(
            "COMMENTARY_REQUIRES_PROVENANCE_AND_ANTI_REPEAT_POLICY"
        )

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I7A_AF_G_INVARIANT_DRIFT",
    )


def test_i7a_world_echo_conformance_cannot_promote_itself_to_authority(
    tmp_path, monkeypatch
):
    baseline, world, source = make_world()
    conformance = json.loads(
        i7a_reference._CONFORMANCE_PATH.read_text(encoding="utf-8")
    )
    conformance["status"] = "CANONICAL_WORLD_ECHO_AUTHORITY"
    drifted = tmp_path / "AF001-WORLD-ECHO-CONFORMANCE-promoted.json"
    drifted.write_text(
        json.dumps(conformance, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(i7a_reference, "_CONFORMANCE_PATH", drifted)
    with pytest.raises(ValueError, match="I7A_CONFORMANCE_AUTHORITY_ESCALATION"):
        build_player_private_world_echo_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def _replace_source_event(world, source, **changes):
    values = {
        "event_id": source.event_id,
        "event_type": source.event_type,
        "actor_id": source.actor_id,
        "scene_id": source.scene_id,
        "baseline_version": source.baseline_version,
        "payload": source.payload,
        "caused_by_action_id": source.caused_by_action_id,
    }
    values.update(changes)
    replacement = type(source)(**values)
    object.__setattr__(
        world,
        "event_log",
        tuple(replacement if event.event_id == source.event_id else event for event in world.event_log),
    )
    return replacement


def test_i7a_source_event_actor_must_equal_canonical_primary_player_guard():
    _, world, source = make_world()
    _replace_source_event(world, source, actor_id=NPC)
    with pytest.raises(ValueError, match="I7A_SELF_ATTRIBUTION_ACTOR_MISMATCH"):
        i7a_reference._build_from_replay_validated_world(
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_committed_damage_source_requires_player_action_provenance_guard():
    _, world, source = make_world()
    _replace_source_event(world, source, caused_by_action_id=None)
    with pytest.raises(
        ValueError,
        match="I7A_SOURCE_EVENT_REQUIRES_PLAYER_ACTION_PROVENANCE",
    ):
        i7a_reference._build_from_replay_validated_world(
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )


def test_i7a_persistent_scene_damage_delta_missing_or_mismatched_guard():
    _, world, source = make_world()
    object.__setattr__(world.scenes[TAVERN], "persistent_delta_refs", tuple())
    with pytest.raises(ValueError, match="I7A_PERSISTENT_DAMAGE_DELTA_MISSING"):
        i7a_reference._build_from_replay_validated_world(
            world=world,
            player_actor_id=PLAYER,
            target_object_id=DOOR,
            source_event_id=source.event_id,
            fixture=make_filter(),
        )
