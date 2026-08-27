import hashlib
import json

import pytest

import evals.i8a_narrative_promise_reference as i8a_reference
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
from evals.i8a_narrative_promise_reference import (
    I8_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_AUTHORED_PROMISE_CREATION,
    NO_CHOICE_MEMORY_LEDGER_AUTHORITY_CREATED,
    NO_LLM_OR_PROVIDER,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PAYOFF_OR_WORLD_EVENT_COMMIT,
    NO_PX_DIRECTOR_RENDERER_AUTHORITY,
    build_narrative_promise_reference,
    export_narrative_promise_package,
    replay_narrative_promise_package,
)

PLAYER = "PLAYER-A"
NPC = "NPC-INNKEEPER"
DOOR = "OBJ-TAVERN-DOOR"
CRATE = "OBJ-CRATE"
SCENE = "SCN-TAVERN"
PLAYER_PRINCIPAL = "principal://i8a/player"
NPC_PRINCIPAL = "principal://i8a/npc-test"
BASELINE_VERSION = "I8A-BASELINE-v1"


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


def make_world(*, audible: bool = True):
    world = WorldState(
        world_id="WORLD-I8A",
        active_scene_id=SCENE,
        baseline_version=BASELINE_VERSION,
        primary_player_actor_id=PLAYER,
        actors={
            PLAYER: ActorState(
                PLAYER,
                "旅人",
                SCENE,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            NPC: ActorState(
                NPC,
                "酒馆老板",
                SCENE,
                strength=1.0,
                capabilities={"SPEAK"},
            ),
        },
        objects={
            DOOR: ObjectState(
                DOOR,
                "木门",
                SCENE,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            CRATE: ObjectState(
                CRATE,
                "木箱",
                SCENE,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={NPC: NPCMindState(NPC, "INNKEEPER")},
        scenes={
            SCENE: SceneState(
                SCENE,
                ["asset://i8a/tavern"],
                [DOOR, CRATE],
                [PLAYER, NPC],
            )
        },
        principal_actor_bindings={
            PLAYER_PRINCIPAL: {PLAYER},
            NPC_PRINCIPAL: {NPC},
        },
        reachable_pairs={(PLAYER, DOOR), (PLAYER, CRATE)},
        audible_pairs={(PLAYER, NPC)} if audible else set(),
    )
    return world, capture_pristine_baseline(world)


def commit_damage(world):
    action = ActionCompiler().compile("砸木门", PLAYER, world, PLAYER_PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    return next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")


def commit_promise(
    world,
    *,
    speaker=PLAYER,
    marker_target=DOOR,
    literal=None,
):
    if literal is None:
        literal = f"告诉酒馆老板 PROMISE_REPAIR_OBJECT:{marker_target}"
    principal = PLAYER_PRINCIPAL if speaker == PLAYER else NPC_PRINCIPAL
    action = ActionCompiler().compile(literal, speaker, world, principal)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    return next(event for event in resolution.events if event.event_type == "SPEECH_UTTERED")


def commit_later_world_progress(world):
    action = ActionCompiler().compile("砸木箱", PLAYER, world, PLAYER_PRINCIPAL)
    return SimulationEngine().resolve_and_commit(action, world)


def make_history(*, add_later=True, audible=True, marker_target=DOOR, literal=None):
    world, baseline = make_world(audible=audible)
    damage = commit_damage(world)
    speech = commit_promise(world, marker_target=marker_target, literal=literal)
    if add_later:
        commit_later_world_progress(world)
    return baseline, world, damage, speech


def build_valid(*, add_later=True):
    baseline, world, damage, speech = make_history(add_later=add_later)
    reference = build_narrative_promise_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    return baseline, world, damage, speech, reference


def _build_with_drifted_contract(tmp_path, monkeypatch, mutate, expected_error):
    baseline, world, _, speech = make_history()
    contract = json.loads(i8a_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(contract)
    drifted = tmp_path / "AF001-LIVING-STORY-CONTRACTS-drifted.json"
    drifted.write_text(
        json.dumps(contract, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(i8a_reference, "_CONTRACT_PATH", drifted)
    with pytest.raises(ValueError, match=expected_error):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_scope_locks_preserve_upstream_authority():
    assert I8_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_CHOICE_MEMORY_LEDGER_AUTHORITY_CREATED is True
    assert NO_AUTHORED_PROMISE_CREATION is True
    assert NO_PAYOFF_OR_WORLD_EVENT_COMMIT is True
    assert NO_LLM_OR_PROVIDER is True
    assert NO_PX_DIRECTOR_RENDERER_AUTHORITY is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i8a_explicit_player_promise_becomes_callback_eligible_from_canonical_history():
    _, _, damage, speech, reference = build_valid(add_later=True)
    promise = thaw_value(reference.narrative_promise)

    assert reference.player_actor_id == PLAYER
    assert reference.recipient_npc_id == NPC
    assert reference.target_object_id == DOOR
    assert reference.source_speech_event_id == speech.event_id
    assert reference.source_damage_event_id == damage.event_id
    assert promise["promise_type"] == "PLAYER_EXPLICIT_REPAIR_OBJECT"
    assert promise["status"] == "CALLBACK_ELIGIBLE"
    assert promise["callback_eligibility"]["eligible"] is True
    assert promise["payoff_refs"] == []
    assert promise["invalidation_reason_optional"] is None
    assert set(promise) == {
        "promise_id",
        "source_refs",
        "promise_type",
        "status",
        "callback_eligibility",
        "payoff_refs",
        "invalidation_reason_optional",
    }


def test_i8a_promise_is_deferred_until_world_advances_beyond_heard_acquisition():
    _, _, _, _, reference = build_valid(add_later=False)
    promise = thaw_value(reference.narrative_promise)
    assert promise["status"] == "DEFERRED"
    assert promise["callback_eligibility"] == {
        "eligible": False,
        "reason": "NO_POST_PROMISE_CANONICAL_WORLD_ADVANCE_YET",
        "target_object_ref": DOOR,
        "required_persistent_delta_ref": f"{DOOR}:damage_state=BROKEN",
        "evaluation_cursor": f"{BASELINE_VERSION}:{reference.source_state_version}",
    }


def test_i8a_source_refs_are_only_canonical_evidence_and_payoff_is_not_invented():
    _, world, damage, speech, reference = build_valid()
    promise = thaw_value(reference.narrative_promise)
    acquisition = next(
        event
        for event in world.event_log
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("source_event_id") == speech.event_id
        and event.payload.get("npc_id") == NPC
    )
    assert promise["source_refs"] == [speech.event_id, acquisition.event_id, damage.event_id]
    assert promise["payoff_refs"] == []
    assert speech.payload["trust_class"] == "UNTRUSTED_DATA"
    assert speech.payload["authority"] == "NONE_OVER_TARGET_INTERNAL_STATE"


def test_i8a_projection_is_read_only_for_world_and_npc_state():
    baseline, world, _, speech = make_history()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_state_version = world.state_version
    before_memories = tuple(world.npc_minds[NPC].memories)
    before_knowledge = tuple(world.npc_minds[NPC].knowledge_boundary_refs)

    build_narrative_promise_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )

    assert tuple(event.event_id for event in world.event_log) == before_event_ids
    assert world.state_version == before_state_version
    assert tuple(world.npc_minds[NPC].memories) == before_memories
    assert tuple(world.npc_minds[NPC].knowledge_boundary_refs) == before_knowledge


def test_i8a_caller_authored_promise_evidence_is_forbidden():
    baseline, world, _, speech = make_history()
    with pytest.raises(ValueError, match="I8A_CALLER_AUTHORED_PROMISE_EVIDENCE_FORBIDDEN"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
            caller_promise_evidence={"promise": "I promise", "authority": "CANONICAL"},
        )


def test_i8a_non_primary_speaker_cannot_mint_player_promise():
    world, baseline = make_world()
    commit_damage(world)
    speech = commit_promise(world, speaker=NPC)
    with pytest.raises(ValueError, match="I8A_PROMISE_SPEAKER_NOT_PRIMARY_PLAYER"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_source_speech_requires_player_action_provenance():
    baseline, world, _, speech = make_history()
    speech.caused_by_action_id = None
    with pytest.raises(ValueError, match="I8A_SOURCE_SPEECH_REQUIRES_PLAYER_ACTION_PROVENANCE"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_recipient_must_have_canonical_heard_acquisition():
    baseline, world, _, speech = make_history(audible=False)
    with pytest.raises(ValueError, match="I8A_PROMISE_RECIPIENT_HEARD_EVIDENCE_REQUIRED"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_unmarked_speech_cannot_be_promoted_into_promise_truth():
    baseline, world, _, speech = make_history(
        literal="告诉酒馆老板 我以后再想想这扇木门"
    )
    with pytest.raises(ValueError, match="I8A_EXACTLY_ONE_EXPLICIT_PROMISE_MARKER_REQUIRED"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_explicit_marker_cannot_be_rebound_to_another_object():
    baseline, world, _, speech = make_history(marker_target=CRATE)
    with pytest.raises(ValueError, match="I8A_EXPLICIT_PROMISE_TARGET_BINDING_MISMATCH"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8a_non_speech_event_cannot_mint_promise():
    baseline, world, damage, _ = make_history()
    with pytest.raises(ValueError, match="I8A_SOURCE_EVENT_TYPE_NOT_SPEECH_UTTERED"):
        build_narrative_promise_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            recipient_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=damage.event_id,
        )


def test_i8a_same_exact_inputs_are_deterministic():
    baseline, world, _, speech = make_history()
    first = build_narrative_promise_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    second = build_narrative_promise_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert first == second


def test_i8a_package_is_byte_deterministic_and_replays_exactly():
    baseline, world, _, speech = make_history()
    first = export_narrative_promise_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    second = export_narrative_promise_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert first == second
    rebuilt = replay_narrative_promise_package(first)
    expected = build_narrative_promise_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert rebuilt == expected


def test_i8a_outer_package_tamper_fails_closed():
    baseline, world, _, speech = make_history()
    package = export_narrative_promise_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["target_object_id"] = CRATE
    with pytest.raises(ValueError, match="I8A_REPLAY_PACKAGE_TAMPERED"):
        replay_narrative_promise_package(canonical_json_bytes(envelope))


def test_i8a_recomputed_digest_cannot_forge_payoff_or_paid_off_status():
    baseline, world, _, speech = make_history()
    package = export_narrative_promise_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        recipient_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    envelope = json.loads(package.decode("utf-8"))
    promise = envelope["payload"]["expected_reference"]["narrative_promise"]
    promise["status"] = "PAID_OFF"
    promise["payoff_refs"] = ["FAKE-PAYOFF-EVENT"]
    with pytest.raises(ValueError, match="I8A_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH"):
        replay_narrative_promise_package(refresh_outer_digest(envelope))


def test_i8a_narrative_promise_type_version_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["type_registry"]["NarrativePromise"]["version"] = "999-drift"

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8A_NARRATIVE_PROMISE_TYPE_DRIFT",
    )


def test_i8a_authored_creation_boundary_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["type_registry"]["NarrativePromise"]["authored_creation_allowed"] = True

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8A_AUTHORED_PROMISE_CREATION_BOUNDARY_DRIFT",
    )


def test_i8a_af_f_promise_invariant_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["freeze_domains"]["AF-F"]["invariants"].remove(
            "NARRATIVE_PROMISE_REQUIRES_SOURCE_EVENT_EVIDENCE"
        )

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8A_AF_F_INVARIANT_DRIFT",
    )


def test_i8a_promise_mutation_constraint_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["authority_semantics"]["profiles"][
            "EVIDENCE_DERIVED_PROMISE_LIFECYCLE"
        ]["mutation_constraint"] = "AUTHORED_STORY_MAY_CREATE_PROMISES"

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8A_PROMISE_MUTATION_CONSTRAINT_DRIFT",
    )
