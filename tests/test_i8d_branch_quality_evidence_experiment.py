import base64
import hashlib
import json

import pytest

import evals.i8d_branch_quality_evidence_experiment as i8d_reference
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
from evals.i5a_information_opportunity_shadow_reference import (
    ShadowPlausibilityFixture,
    export_information_opportunity_shadow_package,
)
from evals.i7a_player_private_world_echo_reference import (
    ReferencePrivateEchoFilter,
    build_player_private_world_echo_reference,
    export_player_private_world_echo_package,
)
from evals.i8c_storylet_eligibility_reference import export_storylet_eligibility_package
from evals.i8d_branch_quality_evidence_experiment import (
    I8D_STAGE_A_EVALUATION_ONLY,
    NO_BRANCH_QUALITY_PRODUCTION_CONTRACT,
    NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE,
    NO_LLM_DIRECTOR_RENDERER_AUTHORITY,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PX_RANKING_OR_WEIGHTS,
    NO_RETCON_RESURRECTION_OR_RECONVERGENCE,
    NO_STORYLET_OR_ENCOUNTER_REALIZATION,
    NO_UNIVERSAL_QUALITY_SCORE,
    NO_WORLD_OR_KNOWLEDGE_MUTATION,
    BranchEvidenceExperimentFixture,
    evaluate_branch_evidence_experiment,
    export_branch_evidence_experiment_package,
    replay_branch_evidence_experiment_package,
)

# I5A wilderness-news fixture identifiers.
I5_SOURCE = "I8D-I5-SOURCE"
I5_CARRIER = "I8D-I5-CARRIER"
I5_PLAYER = "I8D-I5-PLAYER"
I5_NOTICE = "I8D-I5-NOTICE"
I5_CAPITAL = "I8D-I5-CAPITAL"
I5_WILDERNESS = "I8D-I5-WILDERNESS"
I5_PRINCIPAL = "principal://i8d/i5/source"

# I7A persistent World Echo identifiers.
I7_PLAYER = "I8D-I7-PLAYER"
I7_NPC = "I8D-I7-NPC"
I7_DOOR = "I8D-I7-DOOR"
I7_CRATE = "I8D-I7-CRATE"
I7_SCENE = "I8D-I7-TAVERN"
I7_PRINCIPAL = "principal://i8d/i7/player"

# I8C promise/Storylet identifiers.
I8_PLAYER = "I8D-I8-PLAYER"
I8_NPC = "I8D-I8-INNKEEPER"
I8_DOOR = "I8D-I8-DOOR"
I8_CRATE = "I8D-I8-CRATE"
I8_SCENE = "I8D-I8-TAVERN"
I8_PRINCIPAL = "principal://i8d/i8/player"

AXES = {
    "causal_world_integrity",
    "character_relationship_continuity",
    "agency_legibility",
    "knowledge_provenance_integrity",
    "genre_theme_design_fit",
    "meaningful_state_information_relationship_delta",
    "setup_promise_anchor_continuity",
    "recoverable_thread_availability",
    "contrivance_repetition_risk",
    "legal_dead_end_opportunity_scarcity_risk",
}


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def refresh_digest(envelope: dict) -> bytes:
    envelope["sha256"] = hashlib.sha256(
        canonical_json_bytes(envelope["payload"])
    ).hexdigest()
    return canonical_json_bytes(envelope)


def fixture(**overrides):
    values = {
        "fixture_id": "I8D-EVAL-FIXTURE-001",
        "authored_design_fit": "SUPPORTED",
        "meaningful_delta_refs": (),
        "recoverable_thread_refs": ("AUTHORED_THREAD:OPTIONAL_FOLLOWUP",),
        "repetition_key": None,
        "prior_occurrence_count": 0,
    }
    values.update(overrides)
    return BranchEvidenceExperimentFixture(**values)


# ------------------------- I5A source corpus -------------------------


def make_i5_world():
    return WorldState(
        world_id="WORLD-I8D-I5",
        active_scene_id=I5_CAPITAL,
        baseline_version="I8D-I5-BASELINE-v1",
        actors={
            I5_SOURCE: ActorState(
                I5_SOURCE, "都城卫兵", I5_CAPITAL, capabilities={"HIT"}
            ),
            I5_CARRIER: ActorState(
                I5_CARRIER, "行商", I5_CAPITAL, capabilities={"SPEAK"}
            ),
            I5_PLAYER: ActorState(
                I5_PLAYER, "旅人", I5_WILDERNESS, capabilities={"SPEAK"}
            ),
        },
        objects={
            I5_NOTICE: ObjectState(
                I5_NOTICE,
                "公告牌",
                I5_CAPITAL,
                mass=20.0,
                graspable=False,
                fragility=0.5,
            )
        },
        npc_minds={I5_CARRIER: NPCMindState(I5_CARRIER, "MERCHANT")},
        scenes={
            I5_CAPITAL: SceneState(
                I5_CAPITAL,
                ["asset://i8d/capital"],
                [I5_NOTICE],
                [I5_SOURCE, I5_CARRIER],
            ),
            I5_WILDERNESS: SceneState(
                I5_WILDERNESS,
                ["asset://i8d/wilderness"],
                [],
                [I5_PLAYER],
            ),
        },
        principal_actor_bindings={I5_PRINCIPAL: {I5_SOURCE}},
        reachable_pairs={(I5_SOURCE, I5_NOTICE)},
        visible_pairs={(I5_NOTICE, I5_CARRIER)},
    )


def make_i5_source(*, route_available=True, anti_repeat_allowed=True):
    world = make_i5_world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸公告牌", I5_SOURCE, world, I5_PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(
        event for event in resolution.events if event.event_type == "OBJECT_DAMAGED"
    )
    plausibility = ShadowPlausibilityFixture(
        fixture_id="I8D-I5-ROUTE-001",
        target_scene_id=I5_WILDERNESS,
        carrier_origin_scene_id=I5_CAPITAL,
        route_available=route_available,
        travel_steps_required=3,
        travel_steps_available=5,
        identity_history_consistent=True,
        motivation_ref="MOTIVE:MERCHANT_TRAVEL",
        anti_repeat_allowed=anti_repeat_allowed,
        asset_available=True,
    )
    package = export_information_opportunity_shadow_package(
        baseline=baseline,
        world=world,
        source_event_id=source.event_id,
        carrier_npc_id=I5_CARRIER,
        player_actor_id=I5_PLAYER,
        fixture=plausibility,
    )
    return baseline, world, source, package


# ------------------------- I7A source corpus -------------------------


def make_i7_world():
    world = WorldState(
        world_id="WORLD-I8D-I7",
        active_scene_id=I7_SCENE,
        baseline_version="I8D-I7-BASELINE-v1",
        primary_player_actor_id=I7_PLAYER,
        actors={
            I7_PLAYER: ActorState(
                I7_PLAYER,
                "旅人",
                I7_SCENE,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            I7_NPC: ActorState(I7_NPC, "酒馆老板", I7_SCENE, capabilities={"SPEAK"}),
        },
        objects={
            I7_DOOR: ObjectState(
                I7_DOOR, "木门", I7_SCENE, mass=25.0, graspable=False, fragility=0.5
            ),
            I7_CRATE: ObjectState(
                I7_CRATE, "木箱", I7_SCENE, mass=10.0, graspable=True, fragility=0.8
            ),
        },
        npc_minds={I7_NPC: NPCMindState(I7_NPC, "TAVERN_KEEPER")},
        scenes={
            I7_SCENE: SceneState(
                I7_SCENE,
                ["asset://i8d/tavern"],
                [I7_DOOR, I7_CRATE],
                [I7_PLAYER, I7_NPC],
            )
        },
        principal_actor_bindings={I7_PRINCIPAL: {I7_PLAYER}},
        reachable_pairs={(I7_PLAYER, I7_DOOR), (I7_PLAYER, I7_CRATE)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸木门", I7_PLAYER, world, I7_PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(
        event for event in resolution.events if event.event_type == "OBJECT_DAMAGED"
    )
    return baseline, world, source


def make_i7_source(*, repeated=False, urgent=False):
    baseline, world, source = make_i7_world()
    base_filter = ReferencePrivateEchoFilter(
        fixture_id="I8D-I7-ECHO-BASE",
        already_seen_novelty_keys=(),
        urgent_context=False,
        private_commentary_enabled=True,
    )
    initial = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=I7_PLAYER,
        target_object_id=I7_DOOR,
        source_event_id=source.event_id,
        fixture=base_filter,
    )
    chosen_filter = ReferencePrivateEchoFilter(
        fixture_id="I8D-I7-ECHO-SELECTED",
        already_seen_novelty_keys=(initial.novelty_key,) if repeated else (),
        urgent_context=urgent,
        private_commentary_enabled=True,
    )
    package = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=I7_PLAYER,
        target_object_id=I7_DOOR,
        source_event_id=source.event_id,
        fixture=chosen_filter,
    )
    return baseline, world, source, initial.novelty_key, package


# ------------------------- I8C source corpus -------------------------


def make_i8_world():
    world = WorldState(
        world_id="WORLD-I8D-I8",
        active_scene_id=I8_SCENE,
        baseline_version="I8D-I8-BASELINE-v1",
        primary_player_actor_id=I8_PLAYER,
        actors={
            I8_PLAYER: ActorState(
                I8_PLAYER,
                "旅人",
                I8_SCENE,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            I8_NPC: ActorState(
                I8_NPC,
                "酒馆老板",
                I8_SCENE,
                strength=1.0,
                capabilities={"SPEAK"},
            ),
        },
        objects={
            I8_DOOR: ObjectState(
                I8_DOOR, "木门", I8_SCENE, mass=25.0, graspable=False, fragility=0.5
            ),
            I8_CRATE: ObjectState(
                I8_CRATE, "木箱", I8_SCENE, mass=10.0, graspable=True, fragility=0.8
            ),
        },
        npc_minds={I8_NPC: NPCMindState(I8_NPC, "INNKEEPER")},
        scenes={
            I8_SCENE: SceneState(
                I8_SCENE,
                ["asset://i8d/promise-tavern"],
                [I8_DOOR, I8_CRATE],
                [I8_PLAYER, I8_NPC],
            )
        },
        principal_actor_bindings={I8_PRINCIPAL: {I8_PLAYER}},
        reachable_pairs={(I8_PLAYER, I8_DOOR), (I8_PLAYER, I8_CRATE)},
        audible_pairs={(I8_PLAYER, I8_NPC)},
    )
    return world, capture_pristine_baseline(world)


def make_i8_storylet(damage, speech, acquisition):
    return {
        "storylet_id": "STORYLET:I8D-PROMISE-CALLBACK",
        "preconditions": [
            {"kind": "CALLBACK_OPPORTUNITY_REQUIRED"},
            {"kind": "TARGET_OBJECT_PRESENT", "object_id": I8_DOOR},
            {"kind": "ACTORS_SHARE_ACTIVE_SCENE", "actor_ids": [I8_PLAYER, I8_NPC]},
            {"kind": "WORLD_EVENT_PRESENT", "event_id": speech.event_id},
        ],
        "eligible_roles": {
            "player_actor_id": I8_PLAYER,
            "callback_npc_id": I8_NPC,
        },
        "knowledge_constraints": [
            {
                "kind": "CALLBACK_REQUIRED_FACTS_EXACT",
                "fact_refs": [speech.event_id, acquisition.event_id, damage.event_id],
            },
            {"kind": "EXACT_CALLBACK_RECIPIENT", "npc_id": I8_NPC},
        ],
        "dramatic_purpose": "OPTIONAL_PROMISE_CALLBACK_WITHOUT_FORCED_PAYOFF",
        "forbidden_contradictions": [
            "NO_RETCON_OR_RESURRECTION",
            "NO_BRANCH_WELDING",
            "NO_AUTOMATIC_SPEECH",
            "NO_AUTOMATIC_PAYOFF_OR_BREACH",
        ],
        "consequence_templates": ["NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"],
        "repeat_policy": {"mode": "NO_AUTO_REALIZATION"},
        "version": "1.0.0-i8d-eval",
    }


def make_i8_source(*, authored_route_broken=False):
    world, baseline = make_i8_world()
    damage_action = ActionCompiler().compile("砸木门", I8_PLAYER, world, I8_PRINCIPAL)
    damage_resolution = SimulationEngine().resolve_and_commit(
        damage_action, world
    )
    damage = next(
        event for event in damage_resolution.events if event.event_type == "OBJECT_DAMAGED"
    )
    speech_action = ActionCompiler().compile(
        f"告诉酒馆老板 PROMISE_REPAIR_OBJECT:{I8_DOOR}",
        I8_PLAYER,
        world,
        I8_PRINCIPAL,
    )
    speech_resolution = SimulationEngine().resolve_and_commit(speech_action, world)
    speech = next(
        event for event in speech_resolution.events if event.event_type == "SPEECH_UTTERED"
    )
    acquisition = next(
        event
        for event in speech_resolution.events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("npc_id") == I8_NPC
        and event.payload.get("source_event_id") == speech.event_id
    )
    later = ActionCompiler().compile("砸木箱", I8_PLAYER, world, I8_PRINCIPAL)
    SimulationEngine().resolve_and_commit(later, world)

    definition = make_i8_storylet(damage, speech, acquisition)
    if authored_route_broken:
        definition["preconditions"][3]["event_id"] = "EVENT:AUTHORED_ROUTE_NEVER_HAPPENED"
    package = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=I8_PLAYER,
        promise_recipient_npc_id=I8_NPC,
        candidate_npc_id=I8_NPC,
        target_object_id=I8_DOOR,
        source_speech_event_id=speech.event_id,
    )
    return baseline, world, damage, speech, acquisition, package


# ------------------------- scope and governance -------------------------


def test_i8d_scope_locks_keep_stage_a_non_authoritative():
    assert I8D_STAGE_A_EVALUATION_ONLY is True
    assert NO_BRANCH_QUALITY_PRODUCTION_CONTRACT is True
    assert NO_UNIVERSAL_QUALITY_SCORE is True
    assert NO_PX_RANKING_OR_WEIGHTS is True
    assert NO_WORLD_OR_KNOWLEDGE_MUTATION is True
    assert NO_STORYLET_OR_ENCOUNTER_REALIZATION is True
    assert NO_RETCON_RESURRECTION_OR_RECONVERGENCE is True
    assert NO_LLM_DIRECTOR_RENDERER_AUTHORITY is True
    assert NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i8d_governance_gate_confirms_open_decisions_and_no_production_type():
    assert i8d_reference._load_governance() == (
        "AWRSE-AF001-LIVING-STORY-CONTRACTS",
        "1.10.0-candidate",
        "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1",
    )


def test_i8d_px_authority_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(i8d_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["authority_semantics"]["profiles"]["PX_RANKING_NON_CANONICAL"][
        "canonical_data_authority"
    ] = ["PX_RANKING"]
    path = tmp_path / "contract-px-drift.json"
    path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i8d_reference, "_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match="I8D_PX_AUTHORITY_DRIFT"):
        i8d_reference._load_governance()


def test_i8d_premature_branch_quality_type_promotion_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(i8d_reference._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["type_registry"]["BranchQualityEvidence"] = {
        "type_id": "FORGED.BranchQualityEvidence"
    }
    path = tmp_path / "contract-premature-type.json"
    path.write_text(json.dumps(contract, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i8d_reference, "_CONTRACT_PATH", path)
    with pytest.raises(
        ValueError, match="I8D_STAGE_B_PRODUCTION_TYPE_PREMATURELY_PROMOTED"
    ):
        i8d_reference._load_governance()


def test_i8d_open_decision_trace_removal_fails_closed(tmp_path, monkeypatch):
    text = i8d_reference._TRACEABILITY_PATH.read_text(encoding="utf-8")
    text = text.replace("### OD-PX-SCORING-001", "### OD-PX-SCORING-REMOVED")
    path = tmp_path / "traceability-drift.md"
    path.write_text(text, encoding="utf-8")
    monkeypatch.setattr(i8d_reference, "_TRACEABILITY_PATH", path)
    with pytest.raises(ValueError, match="I8D_OPEN_DECISION_TRACE_MISSING"):
        i8d_reference._load_governance()


def test_i8d_required_golden_corpus_drift_fails_closed(tmp_path, monkeypatch):
    golden = json.loads(i8d_reference._GOLDEN_PATH.read_text(encoding="utf-8"))
    del golden["scenarios"]["HOSTILE_PLAYER_BREAKS_PLOT"]
    path = tmp_path / "golden-drift.json"
    path.write_text(json.dumps(golden, ensure_ascii=False), encoding="utf-8")
    monkeypatch.setattr(i8d_reference, "_GOLDEN_PATH", path)
    with pytest.raises(ValueError, match="I8D_REQUIRED_GOLDEN_CORPUS_DRIFT"):
        i8d_reference._load_governance()


# ------------------------- required discriminability corpus -------------------------


def test_i8d_promise_return_callback_is_robust_but_never_forced_payoff():
    _, _, damage, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-PROMISE-ROBUST",
            meaningful_delta_refs=(damage.event_id,),
            recoverable_thread_refs=("AUTHORED_THREAD:PROMISE_OPTIONAL_FOLLOWUP",),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.diagnostic_class == "ROBUST_BRANCH_EVIDENCE"
    assert result.source_status == "STORYLET_ELIGIBLE"
    assert axes["setup_promise_anchor_continuity"]["assessment"] == "SUPPORTED"
    assert axes["character_relationship_continuity"]["assessment"] == "SUPPORTED"
    assert axes["agency_legibility"]["assessment"] == "SUPPORTED"
    assert result.authority_class == (
        "EVALUATION_EVIDENCE_ONLY_NOT_LEGALITY_WORLD_OR_PX_AUTHORITY"
    )


def test_i8d_hostile_player_breaks_authored_route_without_branch_welding():
    _, _, _, _, _, package = make_i8_source(authored_route_broken=True)
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-HOSTILE-PLAYER-BREAKS-PLOT",
            authored_design_fit="THIN",
            recoverable_thread_refs=(),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "NO_VALID_STORYLET"
    assert result.diagnostic_class == "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    assert axes["agency_legibility"]["assessment"] == "SUPPORTED"
    assert axes["legal_dead_end_opportunity_scarcity_risk"]["assessment"] == "RISK"
    assert "NO_CURRENT_VALID_STORYLET" in result.risks


def test_i8d_wilderness_news_no_route_is_valid_no_current_opportunity():
    _, _, source, package = make_i5_source(route_available=False)
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-WILDERNESS-NO-ROUTE",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "NO_VALID_OPPORTUNITY"
    assert result.diagnostic_class == "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    assert axes["knowledge_provenance_integrity"]["assessment"] == "SUPPORTED"
    assert axes["agency_legibility"]["assessment"] == "SUPPORTED"
    assert axes["legal_dead_end_opportunity_scarcity_risk"]["assessment"] == "RISK"


def test_i8d_broken_door_world_echo_is_robust_continuity_without_mandatory_plot():
    _, _, source, _, package = make_i7_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-BROKEN-DOOR-WORLD-ECHO",
            meaningful_delta_refs=(source.event_id,),
            recoverable_thread_refs=("AUTHORED_THREAD:RETURN_TO_DAMAGE_LATER",),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "PRIVATE_WORLD_ECHO_READY"
    assert result.diagnostic_class == "ROBUST_BRANCH_EVIDENCE"
    assert axes["meaningful_state_information_relationship_delta"]["assessment"] == "SUPPORTED"
    assert axes["knowledge_provenance_integrity"]["assessment"] == "SUPPORTED"
    assert axes["agency_legibility"]["assessment"] == "SUPPORTED"


def test_i8d_repeated_equivalent_world_echo_surfaces_risk_without_changing_legality():
    _, _, _, novelty_key, package = make_i7_source(repeated=True)
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-REPEATED-WORLD-ECHO",
            repetition_key=novelty_key,
            prior_occurrence_count=2,
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "SILENCE"
    assert result.diagnostic_class == "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
    assert axes["contrivance_repetition_risk"]["assessment"] == "RISK"
    assert "REPETITION_OR_CONTRIVANCE_RISK_PRESENT" in result.risks


def test_i8d_thin_but_coherent_legal_storylet_remains_legal():
    _, _, _, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=fixture(
            fixture_id="I8D-THIN-BUT-LEGAL",
            authored_design_fit="THIN",
            meaningful_delta_refs=(),
            recoverable_thread_refs=(),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "STORYLET_ELIGIBLE"
    assert result.diagnostic_class == "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
    assert axes["genre_theme_design_fit"]["assessment"] == "THIN"
    assert axes["causal_world_integrity"]["assessment"] == "SUPPORTED"
    assert not result.integrity_failures


def test_i8d_forged_upstream_source_becomes_integrity_failure_not_dramatic_candidate():
    _, _, _, package = make_i5_source()
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["source_event_id"] = "EVENT:FORGED-CLUE"
    forged = refresh_digest(envelope)
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=forged,
        fixture=fixture(
            fixture_id="I8D-FORGED-CLUE",
            authored_design_fit="SUPPORTED",
            recoverable_thread_refs=("AUTHORED_THREAD:VERY_DRAMATIC",),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.diagnostic_class == "INTEGRITY_FAILURE_PRESENT"
    assert result.source_status == "UPSTREAM_REFERENCE_REJECTED"
    assert axes["causal_world_integrity"]["assessment"] == "INTEGRITY_FAILURE"
    assert axes["knowledge_provenance_integrity"]["assessment"] == "INTEGRITY_FAILURE"
    assert not result.strengths
    assert result.risks == ("UPSTREAM_INTEGRITY_FAILURE",)


# ------------------------- authority / anti-laundering tests -------------------------


def test_i8d_hard_integrity_failure_cannot_be_compensated_by_authored_strengths():
    _, _, _, package = make_i5_source()
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["source_event_id"] = "EVENT:RESURRECTED-CAUSE"
    forged = refresh_digest(envelope)
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=forged,
        fixture=fixture(
            fixture_id="I8D-NON-COMPENSATION",
            authored_design_fit="SUPPORTED",
            recoverable_thread_refs=(
                "AUTHORED_THREAD:HIGH_THEME_FIT",
                "AUTHORED_THREAD:HIGH_DRAMA",
            ),
        ),
    )
    assert result.diagnostic_class == "INTEGRITY_FAILURE_PRESENT"
    assert result.strengths == ()


def test_i8d_caller_cannot_supply_branch_quality_evidence():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(
        ValueError, match="I8D_CALLER_AUTHORED_BRANCH_QUALITY_EVIDENCE_FORBIDDEN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=fixture(),
            caller_branch_quality_evidence={
                "score": 999,
                "legal": True,
                "force_reconvergence": True,
            },
        )


def test_i8d_fixture_cannot_invent_meaningful_world_delta_ref():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(
        ValueError, match="I8D_MEANINGFUL_DELTA_REF_NOT_IN_VALIDATED_SOURCE"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=fixture(meaningful_delta_refs=("EVENT:INVENTED-WORLD-DELTA",)),
        )


def test_i8d_fixture_cannot_invent_repetition_identity():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(ValueError, match="I8D_REPETITION_KEY_NOT_IN_VALIDATED_SOURCE"):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=fixture(
                repetition_key="STORYLET:INVENTED",
                prior_occurrence_count=3,
            ),
        )


def test_i8d_fixture_authority_escalation_fails_closed():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(ValueError, match="I8D_FIXTURE_AUTHORITY_ESCALATION"):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=fixture(authority_class="CANONICAL_BRANCH_TRUTH_AUTHORITY"),
        )


def test_i8d_negative_occurrence_count_fails_closed():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(ValueError, match="I8D_PRIOR_OCCURRENCE_COUNT_NEGATIVE"):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=fixture(prior_occurrence_count=-1),
        )


def test_i8d_unsupported_source_kind_fails_closed():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(ValueError, match="I8D_SOURCE_KIND_UNSUPPORTED"):
        evaluate_branch_evidence_experiment(
            source_kind="FREEFORM_LLM_JUDGE",
            source_package=package,
            fixture=fixture(),
        )


def test_i8d_result_has_exact_ten_axes_and_no_score_rank_engagement_retention_fields():
    _, _, _, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=fixture(),
    )
    material = i8d_reference._result_material(result)
    assert set(thaw_value(result.axis_evidence)) == AXES
    forbidden_tokens = ("score", "rank", "engagement", "retention")
    assert not [
        key
        for key in material
        if any(token in key.lower() for token in forbidden_tokens)
    ]
    assert result.deferred_decisions == (
        "OD-CLUE-QUALITY-001",
        "OD-PX-SCORING-001",
    )


# ------------------------- determinism / replay / tamper -------------------------


def test_i8d_same_validated_source_and_fixture_are_deterministic():
    _, _, source, _, package = make_i7_source()
    experiment_fixture = fixture(
        fixture_id="I8D-DETERMINISM",
        meaningful_delta_refs=(source.event_id,),
    )
    first = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=experiment_fixture,
    )
    second = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=experiment_fixture,
    )
    assert i8d_reference._result_material(first) == i8d_reference._result_material(second)


def test_i8d_export_package_is_byte_deterministic_and_replays_exactly():
    _, _, damage, _, _, source_package = make_i8_source()
    experiment_fixture = fixture(
        fixture_id="I8D-REPLAY-EXACT",
        meaningful_delta_refs=(damage.event_id,),
    )
    package_a = export_branch_evidence_experiment_package(
        source_kind="I8C_STORYLET",
        source_package=source_package,
        fixture=experiment_fixture,
    )
    package_b = export_branch_evidence_experiment_package(
        source_kind="I8C_STORYLET",
        source_package=source_package,
        fixture=experiment_fixture,
    )
    assert package_a == package_b
    rebuilt = replay_branch_evidence_experiment_package(package_a)
    assert rebuilt.diagnostic_class == "ROBUST_BRANCH_EVIDENCE"
    assert rebuilt.source_status == "STORYLET_ELIGIBLE"


def test_i8d_outer_package_tamper_fails_closed():
    _, _, _, _, _, source_package = make_i8_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I8C_STORYLET",
        source_package=source_package,
        fixture=fixture(fixture_id="I8D-OUTER-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_result"]["diagnostic_class"] = "FORCED_BEST_BRANCH"
    forged = canonical_json_bytes(envelope)
    with pytest.raises(ValueError, match="I8D_REPLAY_PACKAGE_TAMPERED"):
        replay_branch_evidence_experiment_package(forged)


def test_i8d_recomputed_outer_digest_cannot_launder_forged_expected_result():
    _, _, _, _, _, source_package = make_i8_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I8C_STORYLET",
        source_package=source_package,
        fixture=fixture(fixture_id="I8D-EXPECTED-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_result"]["diagnostic_class"] = "ROBUST_BY_FIAT"
    forged = refresh_digest(envelope)
    with pytest.raises(
        ValueError, match="I8D_REPLAY_RESULT_MATERIALIZATION_MISMATCH"
    ):
        replay_branch_evidence_experiment_package(forged)


def test_i8d_nested_upstream_expected_result_tamper_cannot_be_laundered():
    _, _, _, source_package = make_i5_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=source_package,
        fixture=fixture(fixture_id="I8D-NESTED-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    nested = json.loads(
        base64.b64decode(envelope["payload"]["source_package_b64"]).decode("utf-8")
    )
    nested["payload"]["expected_result"]["status"] = "FORGED_CANONICAL_OPPORTUNITY"
    nested_bytes = refresh_digest(nested)
    envelope["payload"]["source_package_b64"] = base64.b64encode(nested_bytes).decode("ascii")
    envelope["payload"]["source_package_sha256"] = hashlib.sha256(nested_bytes).hexdigest()
    forged = refresh_digest(envelope)
    with pytest.raises(ValueError, match="MATERIALIZATION_MISMATCH"):
        replay_branch_evidence_experiment_package(forged)


def test_i8d_nested_source_digest_mismatch_fails_before_evaluation():
    _, _, _, _, _, source_package = make_i8_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I8C_STORYLET",
        source_package=source_package,
        fixture=fixture(fixture_id="I8D-NESTED-DIGEST"),
    )
    envelope = json.loads(package.decode("utf-8"))
    nested = bytearray(base64.b64decode(envelope["payload"]["source_package_b64"]))
    nested[-2] = nested[-2] ^ 1
    envelope["payload"]["source_package_b64"] = base64.b64encode(bytes(nested)).decode("ascii")
    forged = refresh_digest(envelope)
    with pytest.raises(ValueError, match="I8D_NESTED_SOURCE_PACKAGE_DIGEST_MISMATCH"):
        replay_branch_evidence_experiment_package(forged)


# ------------------------- read-only and provenance -------------------------


def test_i8d_evaluation_is_read_only_for_original_live_world():
    _, world, source, _, source_package = make_i7_source()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_version = world.state_version
    before_memories = tuple(world.npc_minds[I7_NPC].memories)
    before_knowledge = tuple(world.npc_minds[I7_NPC].knowledge_boundary_refs)

    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=fixture(
            fixture_id="I8D-READ-ONLY",
            meaningful_delta_refs=(source.event_id,),
        ),
    )

    assert result.diagnostic_class == "ROBUST_BRANCH_EVIDENCE"
    assert tuple(event.event_id for event in world.event_log) == before_event_ids
    assert world.state_version == before_version
    assert tuple(world.npc_minds[I7_NPC].memories) == before_memories
    assert tuple(world.npc_minds[I7_NPC].knowledge_boundary_refs) == before_knowledge


def test_i8d_valid_result_binds_exact_source_replay_provenance():
    _, _, source, _, source_package = make_i7_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=fixture(
            fixture_id="I8D-PROVENANCE",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    assert result.source_world_id == "WORLD-I8D-I7"
    assert result.source_baseline_version == "I8D-I7-BASELINE-v1"
    assert isinstance(result.source_state_version, int)
    assert result.source_state_version > 0
    assert isinstance(result.source_i1_sha256, str)
    assert len(result.source_i1_sha256) == 64
    assert result.source_package_sha256 == hashlib.sha256(source_package).hexdigest()
    assert isinstance(result.source_reference_sha256, str)
    assert len(result.source_reference_sha256) == 64
