import hashlib
import json

import pytest

import evals.i8b_promise_callback_opportunity_reference as i8b_reference
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
from evals.i8b_promise_callback_opportunity_reference import (
    I8B_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_AUTOMATIC_SPEECH_EVENT,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PROMISE_PAYOFF_OR_BREACH,
    NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY,
    NO_RELATIONSHIP_MUTATION,
    NO_SECOND_MEMORY_LEDGER,
    NO_STORYLET_REALIZATION,
    build_promise_callback_opportunity_reference,
    export_promise_callback_package,
    replay_promise_callback_package,
)

PLAYER = "PLAYER-A"
NPC = "NPC-INNKEEPER"
NPC_SAME_NAME = "NPC-INNKEEPER-OTHER"
DOOR = "OBJ-TAVERN-DOOR"
CRATE = "OBJ-CRATE"
SCENE = "SCN-TAVERN"
PLAYER_PRINCIPAL = "principal://i8b/player"
BASELINE_VERSION = "I8B-BASELINE-v1"


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
        world_id="WORLD-I8B",
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
            NPC_SAME_NAME: ActorState(
                NPC_SAME_NAME,
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
        npc_minds={
            NPC: NPCMindState(NPC, "INNKEEPER"),
            NPC_SAME_NAME: NPCMindState(NPC_SAME_NAME, "INNKEEPER"),
        },
        scenes={
            SCENE: SceneState(
                SCENE,
                ["asset://i8b/tavern"],
                [DOOR, CRATE],
                [PLAYER, NPC, NPC_SAME_NAME],
            )
        },
        principal_actor_bindings={PLAYER_PRINCIPAL: {PLAYER}},
        reachable_pairs={(PLAYER, DOOR), (PLAYER, CRATE)},
        audible_pairs={(PLAYER, NPC)},
    )
    return world, capture_pristine_baseline(world)


def make_history(*, add_later=True):
    world, baseline = make_world()
    damage_action = ActionCompiler().compile("砸木门", PLAYER, world, PLAYER_PRINCIPAL)
    damage_resolution = SimulationEngine().resolve_and_commit(damage_action, world)
    damage = next(event for event in damage_resolution.events if event.event_type == "OBJECT_DAMAGED")

    speech_action = ActionCompiler().compile(
        f"告诉酒馆老板 PROMISE_REPAIR_OBJECT:{DOOR}",
        PLAYER,
        world,
        PLAYER_PRINCIPAL,
    )
    speech_resolution = SimulationEngine().resolve_and_commit(speech_action, world)
    speech = next(event for event in speech_resolution.events if event.event_type == "SPEECH_UTTERED")
    acquisition = next(
        event
        for event in speech_resolution.events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("npc_id") == NPC
        and event.payload.get("source_event_id") == speech.event_id
    )
    if add_later:
        later = ActionCompiler().compile("砸木箱", PLAYER, world, PLAYER_PRINCIPAL)
        SimulationEngine().resolve_and_commit(later, world)
    return baseline, world, damage, speech, acquisition


def build_for(candidate=NPC, *, add_later=True):
    baseline, world, damage, speech, acquisition = make_history(add_later=add_later)
    reference = build_promise_callback_opportunity_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=candidate,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    return baseline, world, damage, speech, acquisition, reference


def _build_with_drifted_contract(tmp_path, monkeypatch, mutate, expected_error):
    baseline, world, _, speech, _ = make_history()
    contract = json.loads(i8b_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    mutate(contract)
    path = tmp_path / "AF001-LIVING-STORY-CONTRACTS-drifted.json"
    path.write_text(json.dumps(contract, ensure_ascii=False, sort_keys=True), encoding="utf-8")
    monkeypatch.setattr(i8b_reference, "_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match=expected_error):
        build_promise_callback_opportunity_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8b_scope_locks_preserve_authority_boundaries():
    assert I8B_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_SECOND_MEMORY_LEDGER is True
    assert NO_AUTOMATIC_SPEECH_EVENT is True
    assert NO_RELATIONSHIP_MUTATION is True
    assert NO_PROMISE_PAYOFF_OR_BREACH is True
    assert NO_STORYLET_REALIZATION is True
    assert NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i8b_exact_recipient_with_heard_memory_gets_noncanonical_callback_opportunity():
    _, _, damage, speech, acquisition, reference = build_for(NPC)
    concept = thaw_value(reference.response_concept)

    assert reference.outcome == "CALLBACK_OPPORTUNITY"
    assert reference.reason == "EXACT_RECIPIENT_HEARD_PROMISE_AND_CURRENT_CONTEXT_VALID"
    assert reference.candidate_npc_id == NPC
    assert reference.source_speech_event_id == speech.event_id
    assert reference.source_acquisition_event_id == acquisition.event_id
    assert concept["required_fact_refs"] == [speech.event_id, acquisition.event_id, damage.event_id]
    assert concept["speech_risk_class"] == "NPC_KNOWING_CALLBACK_CONCEPT_ONLY"
    assert "NO_AUTOMATIC_SPEECH_EVENT" in concept["realization_constraints"]
    assert "PLAYER_FULFILLMENT_NOT_IN_EVIDENCE" in concept["forbidden_claim_classes"]
    assert set(concept) == {
        "response_concept_id",
        "speech_risk_class",
        "required_fact_refs",
        "forbidden_claim_classes",
        "realization_constraints",
    }


def test_i8b_same_display_name_npc_without_acquisition_gets_no_valid_callback():
    _, _, _, _, _, reference = build_for(NPC_SAME_NAME)
    assert reference.outcome == "NO_VALID_CALLBACK"
    assert reference.reason == "CANDIDATE_NOT_BOUND_PROMISE_RECIPIENT"
    assert reference.response_concept is None


def test_i8b_deferred_promise_does_not_become_callback_just_because_npc_knows_it():
    _, _, _, _, _, reference = build_for(NPC, add_later=False)
    assert reference.outcome == "NO_VALID_CALLBACK"
    assert reference.reason == "PROMISE_NOT_CALLBACK_ELIGIBLE"
    assert reference.response_concept is None


def test_i8b_projection_is_read_only_and_does_not_create_speech_or_relationship_events():
    baseline, world, _, speech, _ = make_history()
    before_ids = tuple(event.event_id for event in world.event_log)
    before_version = world.state_version
    before_relationship = world.npc_minds[NPC].relationship_to_player

    build_promise_callback_opportunity_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )

    assert tuple(event.event_id for event in world.event_log) == before_ids
    assert world.state_version == before_version
    assert world.npc_minds[NPC].relationship_to_player == before_relationship


def test_i8b_caller_authored_callback_evidence_is_rejected():
    baseline, world, _, speech, _ = make_history()
    with pytest.raises(ValueError, match="I8B_CALLER_AUTHORED_CALLBACK_EVIDENCE_FORBIDDEN"):
        build_promise_callback_opportunity_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
            caller_callback_evidence={"npc_knows": True, "authority": "CANONICAL"},
        )


def test_i8b_unknown_candidate_npc_fails_closed():
    baseline, world, _, speech, _ = make_history()
    with pytest.raises(ValueError, match="I8B_CANDIDATE_NPC_NOT_FOUND"):
        build_promise_callback_opportunity_reference(
            baseline=baseline,
            world=world,
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id="NPC-NOT-THERE",
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8b_same_exact_inputs_are_deterministic():
    baseline, world, _, speech, _ = make_history()
    first = build_promise_callback_opportunity_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    second = build_promise_callback_opportunity_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert first == second


def test_i8b_package_is_byte_deterministic_and_replays_exactly():
    baseline, world, _, speech, _ = make_history()
    first = export_promise_callback_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    second = export_promise_callback_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert first == second
    rebuilt = replay_promise_callback_package(first)
    expected = build_promise_callback_opportunity_reference(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert rebuilt == expected


def test_i8b_outer_package_tamper_fails_closed():
    baseline, world, _, speech, _ = make_history()
    package = export_promise_callback_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["candidate_npc_id"] = NPC_SAME_NAME
    with pytest.raises(ValueError, match="I8B_REPLAY_PACKAGE_TAMPERED"):
        replay_promise_callback_package(canonical_json_bytes(envelope))


def test_i8b_recomputed_digest_cannot_forge_callback_for_unqualified_npc():
    baseline, world, _, speech, _ = make_history()
    package = export_promise_callback_package(
        baseline=baseline,
        world=world,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC_SAME_NAME,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    envelope = json.loads(package.decode("utf-8"))
    expected = envelope["payload"]["expected_reference"]
    expected["outcome"] = "CALLBACK_OPPORTUNITY"
    expected["reason"] = "FORGED"
    expected["response_concept"] = {
        "response_concept_id": "FORGED",
        "speech_risk_class": "FORGED",
        "required_fact_refs": [],
        "forbidden_claim_classes": [],
        "realization_constraints": [],
    }
    with pytest.raises(ValueError, match="I8B_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH"):
        replay_promise_callback_package(refresh_outer_digest(envelope))


def test_i8b_response_concept_type_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["type_registry"]["ResponseConcept"]["version"] = "999-drift"

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8B_RESPONSE_CONCEPT_TYPE_DRIFT",
    )


def test_i8b_af_g_no_valid_opportunity_invariant_drift_fails_closed(tmp_path, monkeypatch):
    def mutate(contract):
        contract["freeze_domains"]["AF-G"]["invariants"].remove(
            "NO_VALID_OPPORTUNITY_IS_VALID"
        )

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8B_AF_G_INVARIANT_DRIFT",
    )


def test_i8b_opportunity_authority_cannot_be_promoted_to_canonical(tmp_path, monkeypatch):
    def mutate(contract):
        contract["authority_semantics"]["profiles"][
            "NARRATIVE_OPPORTUNITY_NON_CANONICAL"
        ]["canonical_data_authority"] = ["NARRATIVE_OPPORTUNITY"]

    _build_with_drifted_contract(
        tmp_path,
        monkeypatch,
        mutate,
        "I8B_OPPORTUNITY_CANONICAL_AUTHORITY_DRIFT",
    )
