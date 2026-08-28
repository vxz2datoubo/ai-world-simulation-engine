import hashlib
import json

import pytest

import evals.i8c_storylet_eligibility_reference as i8c_reference
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
from evals.i8c_storylet_eligibility_reference import (
    I8C_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_AUTOMATIC_SPEECH_OR_ENCOUNTER,
    NO_BRANCH_WELDING_OR_RECONVERGENCE,
    NO_EVENT_DECK_AUTHORITY,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PROMISE_PAYOFF_OR_BREACH,
    NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY,
    NO_RETCON_OR_RESURRECTION,
    NO_STORYLET_REALIZATION,
    build_storylet_eligibility_reference,
    export_storylet_eligibility_package,
    replay_storylet_eligibility_package,
)

PLAYER = "PLAYER-A"
NPC = "NPC-INNKEEPER"
NPC_SAME_NAME = "NPC-INNKEEPER-OTHER"
DOOR = "OBJ-TAVERN-DOOR"
CRATE = "OBJ-CRATE"
SCENE = "SCN-TAVERN"
PLAYER_PRINCIPAL = "principal://i8c/player"
BASELINE_VERSION = "I8C-BASELINE-v1"


def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def refresh_outer_digest(envelope: dict) -> bytes:
    envelope["sha256"] = hashlib.sha256(canonical_json_bytes(envelope["payload"])).hexdigest()
    return canonical_json_bytes(envelope)


def make_world():
    world = WorldState(
        world_id="WORLD-I8C",
        active_scene_id=SCENE,
        baseline_version=BASELINE_VERSION,
        primary_player_actor_id=PLAYER,
        actors={
            PLAYER: ActorState(PLAYER, "旅人", SCENE, strength=1.0, capabilities={"HIT", "SPEAK"}),
            NPC: ActorState(NPC, "酒馆老板", SCENE, strength=1.0, capabilities={"SPEAK"}),
            NPC_SAME_NAME: ActorState(NPC_SAME_NAME, "酒馆老板", SCENE, strength=1.0, capabilities={"SPEAK"}),
        },
        objects={
            DOOR: ObjectState(DOOR, "木门", SCENE, mass=25.0, graspable=False, fragility=0.5),
            CRATE: ObjectState(CRATE, "木箱", SCENE, mass=10.0, graspable=True, fragility=0.8),
        },
        npc_minds={
            NPC: NPCMindState(NPC, "INNKEEPER"),
            NPC_SAME_NAME: NPCMindState(NPC_SAME_NAME, "INNKEEPER"),
        },
        scenes={SCENE: SceneState(SCENE, ["asset://i8c/tavern"], [DOOR, CRATE], [PLAYER, NPC, NPC_SAME_NAME])},
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
        f"告诉酒馆老板 PROMISE_REPAIR_OBJECT:{DOOR}", PLAYER, world, PLAYER_PRINCIPAL
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


def storylet(damage, speech, acquisition, *, candidate=NPC):
    return {
        "storylet_id": "STORYLET:PROMISE-RETURN-CALLBACK",
        "preconditions": [
            {"kind": "CALLBACK_OPPORTUNITY_REQUIRED"},
            {"kind": "TARGET_OBJECT_PRESENT", "object_id": DOOR},
            {"kind": "ACTORS_SHARE_ACTIVE_SCENE", "actor_ids": [PLAYER, candidate]},
            {"kind": "WORLD_EVENT_PRESENT", "event_id": speech.event_id},
        ],
        "eligible_roles": {"player_actor_id": PLAYER, "callback_npc_id": candidate},
        "knowledge_constraints": [
            {
                "kind": "CALLBACK_REQUIRED_FACTS_EXACT",
                "fact_refs": [speech.event_id, acquisition.event_id, damage.event_id],
            },
            {"kind": "EXACT_CALLBACK_RECIPIENT", "npc_id": candidate},
        ],
        "dramatic_purpose": "RETURN_TO_OLD_PROMISE_WITHOUT_FORCING_OUTCOME",
        "forbidden_contradictions": [
            "NO_RETCON_OR_RESURRECTION",
            "NO_BRANCH_WELDING",
            "NO_AUTOMATIC_SPEECH",
            "NO_AUTOMATIC_PAYOFF_OR_BREACH",
        ],
        "consequence_templates": ["NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"],
        "repeat_policy": {"mode": "NO_AUTO_REALIZATION"},
        "version": "1.0.0-reference",
    }


def build(*, candidate=NPC, add_later=True, mutate_storylet=None):
    baseline, world, damage, speech, acquisition = make_history(add_later=add_later)
    definition = storylet(damage, speech, acquisition, candidate=candidate)
    if mutate_storylet is not None:
        mutate_storylet(definition)
    reference = build_storylet_eligibility_reference(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=candidate,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    return baseline, world, damage, speech, acquisition, definition, reference


def test_i8c_scope_locks_keep_storylet_eligibility_non_executing():
    assert I8C_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_STORYLET_REALIZATION is True
    assert NO_EVENT_DECK_AUTHORITY is True
    assert NO_BRANCH_WELDING_OR_RECONVERGENCE is True
    assert NO_RETCON_OR_RESURRECTION is True
    assert NO_AUTOMATIC_SPEECH_OR_ENCOUNTER is True
    assert NO_PROMISE_PAYOFF_OR_BREACH is True
    assert NO_PX_DIRECTOR_RENDERER_LLM_AUTHORITY is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i8c_valid_callback_and_revalidated_storylet_becomes_eligible_only():
    _, _, _, _, _, definition, reference = build()
    assert reference.outcome == "STORYLET_ELIGIBLE"
    assert reference.reason == "ALL_AUTHORED_PRECONDITIONS_REVALIDATED_FROM_CANONICAL_EVIDENCE"
    assert reference.storylet_id == definition["storylet_id"]
    assert reference.source_callback_concept_id.startswith("RESPONSE:PROMISE_CALLBACK:")
    assert reference.authority_class == "NON_CANONICAL_STORYLET_ELIGIBILITY_ONLY"
    assert any(item.startswith("KNOWLEDGE_RECIPIENT:") for item in reference.eligibility_evidence)


def test_i8c_eligibility_projection_is_read_only_and_commits_nothing():
    baseline, world, damage, speech, acquisition = make_history()
    definition = storylet(damage, speech, acquisition)
    before_ids = tuple(event.event_id for event in world.event_log)
    before_version = world.state_version
    build_storylet_eligibility_reference(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert tuple(event.event_id for event in world.event_log) == before_ids
    assert world.state_version == before_version


def test_i8c_deferred_promise_yields_no_valid_storylet_not_forced_callback():
    *_, reference = build(add_later=False)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "SOURCE_CALLBACK_NOT_CURRENTLY_VALID"


def test_i8c_same_name_uninformed_npc_cannot_gain_storylet_eligibility():
    *_, reference = build(candidate=NPC_SAME_NAME)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "SOURCE_CALLBACK_NOT_CURRENTLY_VALID"


def test_i8c_authored_role_binding_cannot_assert_current_world_role_truth():
    def mutate(definition):
        definition["eligible_roles"]["callback_npc_id"] = NPC_SAME_NAME

    *_, reference = build(mutate_storylet=mutate)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "AUTHORED_ROLE_BINDING_NOT_CURRENTLY_VALID"


def test_i8c_absent_required_actor_fails_closed_without_invention():
    def mutate(definition):
        definition["preconditions"][2]["actor_ids"] = [PLAYER, NPC, "NPC-MISSING"]

    *_, reference = build(mutate_storylet=mutate)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "REQUIRED_ACTOR_ABSENT_FROM_CANONICAL_WORLD"


def test_i8c_missing_required_object_fails_closed_without_spawning_it():
    def mutate(definition):
        definition["preconditions"][1]["object_id"] = "OBJ-MISSING"

    *_, reference = build(mutate_storylet=mutate)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "TARGET_OBJECT_NOT_PRESENT_IN_REPLAY_VALID_ACTIVE_SCENE"


def test_i8c_missing_world_event_precondition_does_not_become_true_by_narrative_need():
    def mutate(definition):
        definition["preconditions"][3]["event_id"] = "EVENT-NEVER-HAPPENED"

    *_, reference = build(mutate_storylet=mutate)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "REQUIRED_WORLD_EVENT_NOT_COMMITTED"


def test_i8c_knowledge_constraint_must_match_callback_fact_provenance_exactly():
    def mutate(definition):
        definition["knowledge_constraints"][0]["fact_refs"] = ["EVENT-FORGED"]

    *_, reference = build(mutate_storylet=mutate)
    assert reference.outcome == "NO_VALID_STORYLET"
    assert reference.reason == "STORYLET_KNOWLEDGE_REFS_DO_NOT_MATCH_CALLBACK_EVIDENCE"


def test_i8c_unknown_precondition_fails_closed_instead_of_becoming_authority():
    def mutate(definition):
        definition["preconditions"] = [{"kind": "NARRATIVE_SAYS_THIS_MUST_HAPPEN"}]

    with pytest.raises(ValueError, match="I8C_UNSUPPORTED_PRECONDITION"):
        build(mutate_storylet=mutate)


def test_i8c_unsafe_consequence_template_cannot_force_scene_or_branch():
    def mutate(definition):
        definition["consequence_templates"] = ["FORCE_PLAYER_ACCEPT_AND_COMMIT_SCENE"]

    with pytest.raises(ValueError, match="I8C_UNSAFE_OR_UNSUPPORTED_CONSEQUENCE_TEMPLATE"):
        build(mutate_storylet=mutate)


def test_i8c_storylet_must_preserve_anti_retcon_and_anti_welding_guards():
    def mutate(definition):
        definition["forbidden_contradictions"].remove("NO_BRANCH_WELDING")

    with pytest.raises(ValueError, match="I8C_REQUIRED_ANTI_WELDING_CONTRADICTIONS_MISSING"):
        build(mutate_storylet=mutate)


def test_i8c_repeat_policy_cannot_auto_realize_eligible_storylet():
    def mutate(definition):
        definition["repeat_policy"] = {"mode": "AUTO_REALIZE_ON_ELIGIBLE"}

    with pytest.raises(ValueError, match="I8C_REPEAT_POLICY_MUST_NOT_AUTO_REALIZE"):
        build(mutate_storylet=mutate)


def test_i8c_caller_authored_eligibility_evidence_is_rejected():
    baseline, world, damage, speech, acquisition = make_history()
    with pytest.raises(ValueError, match="I8C_CALLER_AUTHORED_ELIGIBILITY_EVIDENCE_FORBIDDEN"):
        build_storylet_eligibility_reference(
            baseline=baseline,
            world=world,
            storylet_definition=storylet(damage, speech, acquisition),
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
            caller_eligibility_evidence={"eligible": True},
        )


def test_i8c_replay_package_rebuilds_same_eligibility_deterministically():
    baseline, world, damage, speech, acquisition = make_history()
    definition = storylet(damage, speech, acquisition)
    package_a = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    package_b = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    assert package_a == package_b
    rebuilt = replay_storylet_eligibility_package(package_a)
    assert rebuilt.outcome == "STORYLET_ELIGIBLE"
    assert rebuilt.storylet_id == definition["storylet_id"]


def test_i8c_recomputed_outer_digest_cannot_launder_forged_expected_eligibility():
    baseline, world, damage, speech, acquisition = make_history()
    package = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=storylet(damage, speech, acquisition),
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_reference"]["outcome"] = "FORCED_REALIZED_STORYLET"
    forged = refresh_outer_digest(envelope)
    with pytest.raises(ValueError, match="I8C_REPLAY_REFERENCE_MATERIALIZATION_MISMATCH"):
        replay_storylet_eligibility_package(forged)


def test_i8c_contract_storylet_field_drift_fails_closed(tmp_path, monkeypatch):
    baseline, world, damage, speech, acquisition = make_history()
    contract = json.loads(i8c_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["type_registry"]["Storylet"]["fields"].append("invented_status")
    path = tmp_path / "contract-drift.json"
    path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i8c_reference, "_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match="I8C_STORYLET_FIELDS_DRIFT"):
        build_storylet_eligibility_reference(
            baseline=baseline,
            world=world,
            storylet_definition=storylet(damage, speech, acquisition),
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )


def test_i8c_golden_noncanonical_storylet_guard_drift_fails_closed(tmp_path, monkeypatch):
    baseline, world, damage, speech, acquisition = make_history()
    golden = json.loads(i8c_reference._GOLDEN_PATH.read_text(encoding="utf-8"))
    rows = golden["scenarios"]["HOSTILE_PLAYER_BREAKS_PLOT"]["machine_spec"]["initial_state_predicates"]
    for row in rows:
        if row.get("type_ref") == "Storylet":
            row["assertion"] = "storylet_may_force_world_fact"
    path = tmp_path / "golden-drift.json"
    path.write_text(json.dumps(golden, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i8c_reference, "_GOLDEN_PATH", path)
    with pytest.raises(ValueError, match="I8C_STORYLET_NONCANONICAL_GOLDEN_GUARD_DRIFT"):
        build_storylet_eligibility_reference(
            baseline=baseline,
            world=world,
            storylet_definition=storylet(damage, speech, acquisition),
            player_actor_id=PLAYER,
            promise_recipient_npc_id=NPC,
            candidate_npc_id=NPC,
            target_object_id=DOOR,
            source_speech_event_id=speech.event_id,
        )
