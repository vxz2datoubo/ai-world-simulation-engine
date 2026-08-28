import base64
from dataclasses import fields
import hashlib
import json

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
    BranchEvidenceExperimentFixture,
    export_branch_evidence_experiment_package,
    replay_branch_evidence_experiment_package,
)
from evals.i8d_stage_a2_axis_stability_experiment import (
    I8D_STAGE_A2_EVALUATION_ONLY,
    NO_BRANCH_QUALITY_CANONICAL_TYPE,
    NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE,
    NO_LLM_DIRECTOR_RENDERER_AUTHORITY,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PX_RANKING_OR_WEIGHTS,
    NO_RETCON_RESURRECTION_OR_RECONVERGENCE,
    NO_STAGE_B_PRODUCTION_INTERFACE,
    NO_STORYLET_OR_ENCOUNTER_REALIZATION,
    NO_UNIVERSAL_QUALITY_SCORE,
    NO_WORLD_OR_KNOWLEDGE_MUTATION,
    MinimalCoreStabilityObservation,
    StageA2ComparisonFixture,
    evaluate_stage_a2_axis_stability,
    export_stage_a2_axis_stability_package,
    replay_stage_a2_axis_stability_package,
)


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


def comparison(kind, label=None):
    return StageA2ComparisonFixture(
        comparison_id=label or f"A2:{kind}", comparison_kind=kind
    )


def stage_a_fixture(**overrides):
    values = {
        "fixture_id": "A2-STAGE-A-CONTROL",
        "authored_design_fit": "NOT_APPLICABLE",
        "meaningful_delta_refs": (),
        "recoverable_thread_refs": (),
        "repetition_key": None,
        "prior_occurrence_count": 0,
    }
    values.update(overrides)
    return BranchEvidenceExperimentFixture(**values)


def stage_a(kind, source_package, **fixture_overrides):
    return export_branch_evidence_experiment_package(
        source_kind=kind,
        source_package=source_package,
        fixture=stage_a_fixture(**fixture_overrides),
    )


def make_i5_pair():
    source_actor = "A2-I5-SOURCE"
    carrier = "A2-I5-CARRIER"
    player = "A2-I5-PLAYER"
    notice = "A2-I5-NOTICE"
    capital = "A2-I5-CAPITAL"
    wilderness = "A2-I5-WILDERNESS"
    principal = "principal://a2/i5"
    world = WorldState(
        world_id="WORLD-A2-I5",
        active_scene_id=capital,
        baseline_version="A2-I5-BASELINE-v1",
        actors={
            source_actor: ActorState(source_actor, "卫兵", capital, capabilities={"HIT"}),
            carrier: ActorState(carrier, "行商", capital, capabilities={"SPEAK"}),
            player: ActorState(player, "旅人", wilderness, capabilities={"SPEAK"}),
        },
        objects={
            notice: ObjectState(
                notice, "告示牌", capital, mass=20.0, graspable=False, fragility=0.5
            )
        },
        npc_minds={carrier: NPCMindState(carrier, "MERCHANT")},
        scenes={
            capital: SceneState(
                capital,
                ["asset://a2/i5/capital"],
                [notice],
                [source_actor, carrier],
            ),
            wilderness: SceneState(
                wilderness, ["asset://a2/i5/wilderness"], [], [player]
            ),
        },
        principal_actor_bindings={principal: {source_actor}},
        reachable_pairs={(source_actor, notice)},
        visible_pairs={(notice, carrier)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸告示牌", source_actor, world, principal)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(e for e in resolution.events if e.event_type == "OBJECT_DAMAGED")

    def fixture(route_available):
        return ShadowPlausibilityFixture(
            fixture_id="A2-I5-ROUTE",
            target_scene_id=wilderness,
            carrier_origin_scene_id=capital,
            route_available=route_available,
            travel_steps_required=2,
            travel_steps_available=4,
            identity_history_consistent=True,
            motivation_ref="MOTIVE:A2-MERCHANT-TRAVEL",
            anti_repeat_allowed=True,
            asset_available=True,
        )

    valid = export_information_opportunity_shadow_package(
        baseline=baseline,
        world=world,
        source_event_id=source.event_id,
        carrier_npc_id=carrier,
        player_actor_id=player,
        fixture=fixture(True),
    )
    blocked = export_information_opportunity_shadow_package(
        baseline=baseline,
        world=world,
        source_event_id=source.event_id,
        carrier_npc_id=carrier,
        player_actor_id=player,
        fixture=fixture(False),
    )
    return source, valid, blocked


def make_i7_pair(*, mutate_history_between=False):
    player = "A2-I7-PLAYER"
    npc = "A2-I7-NPC"
    door = "A2-I7-DOOR"
    crate = "A2-I7-CRATE"
    scene = "A2-I7-SCENE"
    principal = "principal://a2/i7"
    world = WorldState(
        world_id="WORLD-A2-I7",
        active_scene_id=scene,
        baseline_version="A2-I7-BASELINE-v1",
        primary_player_actor_id=player,
        actors={
            player: ActorState(
                player, "旅人", scene, strength=1.0, capabilities={"HIT", "SPEAK"}
            ),
            npc: ActorState(npc, "路人", scene, capabilities={"SPEAK"}),
        },
        objects={
            door: ObjectState(
                door, "旧门", scene, mass=25.0, graspable=False, fragility=0.5
            ),
            crate: ObjectState(
                crate, "木箱", scene, mass=10.0, graspable=True, fragility=0.8
            ),
        },
        npc_minds={npc: NPCMindState(npc, "BYSTANDER")},
        scenes={
            scene: SceneState(
                scene,
                ["asset://a2/i7/scene"],
                [door, crate],
                [player, npc],
            )
        },
        principal_actor_bindings={principal: {player}},
        reachable_pairs={(player, door), (player, crate)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸旧门", player, world, principal)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(e for e in resolution.events if e.event_type == "OBJECT_DAMAGED")
    first_filter = ReferencePrivateEchoFilter(fixture_id="A2-I7-ECHO")
    first = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=player,
        target_object_id=door,
        source_event_id=source.event_id,
        fixture=first_filter,
    )
    ready = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=player,
        target_object_id=door,
        source_event_id=source.event_id,
        fixture=first_filter,
    )
    if mutate_history_between:
        later = ActionCompiler().compile("砸木箱", player, world, principal)
        SimulationEngine().resolve_and_commit(later, world)
    suppressed = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=player,
        target_object_id=door,
        source_event_id=source.event_id,
        fixture=ReferencePrivateEchoFilter(
            fixture_id="A2-I7-ECHO",
            already_seen_novelty_keys=(first.novelty_key,),
        ),
    )
    return source, ready, suppressed


def make_i8_pair():
    player = "A2-I8-PLAYER"
    npc = "A2-I8-INNKEEPER"
    door = "A2-I8-DOOR"
    scene = "A2-I8-SCENE"
    principal = "principal://a2/i8"
    world = WorldState(
        world_id="WORLD-A2-I8",
        active_scene_id=scene,
        baseline_version="A2-I8-BASELINE-v1",
        primary_player_actor_id=player,
        actors={
            player: ActorState(
                player, "旅人", scene, strength=1.0, capabilities={"HIT", "SPEAK"}
            ),
            npc: ActorState(npc, "店主", scene, capabilities={"SPEAK"}),
        },
        objects={
            door: ObjectState(
                door, "店门", scene, mass=25.0, graspable=False, fragility=0.5
            )
        },
        npc_minds={npc: NPCMindState(npc, "INNKEEPER")},
        scenes={
            scene: SceneState(scene, ["asset://a2/i8/inn"], [door], [player, npc])
        },
        principal_actor_bindings={principal: {player}},
        reachable_pairs={(player, door)},
        audible_pairs={(player, npc)},
    )
    baseline = capture_pristine_baseline(world)
    damage_action = ActionCompiler().compile("砸店门", player, world, principal)
    damage_resolution = SimulationEngine().resolve_and_commit(damage_action, world)
    damage = next(e for e in damage_resolution.events if e.event_type == "OBJECT_DAMAGED")
    speech_action = ActionCompiler().compile(
        f"告诉店主 PROMISE_REPAIR_OBJECT:{door}", player, world, principal
    )
    speech_resolution = SimulationEngine().resolve_and_commit(speech_action, world)
    speech = next(e for e in speech_resolution.events if e.event_type == "SPEECH_UTTERED")
    acquisition = next(
        e
        for e in speech_resolution.events
        if e.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and e.payload.get("npc_id") == npc
        and e.payload.get("source_event_id") == speech.event_id
    )

    def storylet(callback_role):
        return {
            "storylet_id": "STORYLET:A2-PROMISE",
            "preconditions": [
                {"kind": "CALLBACK_OPPORTUNITY_REQUIRED"},
                {"kind": "TARGET_OBJECT_PRESENT", "object_id": door},
                {"kind": "ACTORS_SHARE_ACTIVE_SCENE", "actor_ids": [player, npc]},
                {"kind": "WORLD_EVENT_PRESENT", "event_id": speech.event_id},
            ],
            "eligible_roles": {
                "player_actor_id": player,
                "callback_npc_id": callback_role,
            },
            "knowledge_constraints": [
                {
                    "kind": "CALLBACK_REQUIRED_FACTS_EXACT",
                    "fact_refs": [speech.event_id, acquisition.event_id, damage.event_id],
                },
                {"kind": "EXACT_CALLBACK_RECIPIENT", "npc_id": npc},
            ],
            "dramatic_purpose": "A2_HELD_OUT_OPTIONAL_PROMISE_CALLBACK",
            "forbidden_contradictions": [
                "NO_RETCON_OR_RESURRECTION",
                "NO_BRANCH_WELDING",
                "NO_AUTOMATIC_SPEECH",
                "NO_AUTOMATIC_PAYOFF_OR_BREACH",
            ],
            "consequence_templates": ["NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"],
            "repeat_policy": {"mode": "NO_AUTO_REALIZATION"},
            "version": "1.0.0-a2",
        }

    def export(definition):
        return export_storylet_eligibility_package(
            baseline=baseline,
            world=world,
            storylet_definition=definition,
            player_actor_id=player,
            promise_recipient_npc_id=npc,
            candidate_npc_id=npc,
            target_object_id=door,
            source_speech_event_id=speech.event_id,
        )

    return damage, export(storylet(npc)), export(storylet("A2-I8-WRONG-ROLE"))


def test_scope_locks_keep_stage_b_blocked():
    assert I8D_STAGE_A2_EVALUATION_ONLY
    assert NO_STAGE_B_PRODUCTION_INTERFACE
    assert NO_BRANCH_QUALITY_CANONICAL_TYPE
    assert NO_UNIVERSAL_QUALITY_SCORE
    assert NO_PX_RANKING_OR_WEIGHTS
    assert NO_WORLD_OR_KNOWLEDGE_MUTATION
    assert NO_STORYLET_OR_ENCOUNTER_REALIZATION
    assert NO_RETCON_RESURRECTION_OR_RECONVERGENCE
    assert NO_LLM_DIRECTOR_RENDERER_AUTHORITY
    assert NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE
    assert NO_PARTY_PUBLIC_IMPLEMENTED


def test_observation_has_no_score_weight_rank_or_legality_field():
    names = {f.name.lower() for f in fields(MinimalCoreStabilityObservation)}
    assert not names & {"score", "weight", "rank", "legality", "quality_score"}


def test_authored_fit_is_quarantined_from_core():
    _, source, _ = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    right = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED"
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("AUTHORED_DESIGN_METADATA_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ("genre_theme_design_fit",)
    assert thaw_value(result.left_core_axes) == thaw_value(result.right_core_axes)


def test_recoverable_thread_is_quarantined_from_core_and_mechanism_axes():
    _, source, _ = make_i7_pair()
    left = stage_a("I7A_WORLD_ECHO", source)
    right = stage_a(
        "I7A_WORLD_ECHO",
        source,
        recoverable_thread_refs=("AUTHORED_THREAD:A2-RETURN",),
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("RECOVERABLE_THREAD_METADATA_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ("recoverable_thread_availability",)


def test_repetition_history_only_moves_contrivance_axis():
    source_event, source, _ = make_i7_pair()
    left = stage_a(
        "I7A_WORLD_ECHO",
        source,
        repetition_key=source_event.event_id,
        prior_occurrence_count=0,
    )
    right = stage_a(
        "I7A_WORLD_ECHO",
        source,
        repetition_key=source_event.event_id,
        prior_occurrence_count=2,
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("REPETITION_HISTORY_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_REPETITION_HISTORY_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ("contrivance_repetition_risk",)
    assert result.changed_authored_axes == ()


def test_i5_route_loss_changes_only_core_scarcity_assessment_on_same_i1():
    source_event, valid, blocked = make_i5_pair()
    left = stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        valid,
        meaningful_delta_refs=(source_event.event_id,),
    )
    right = stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        blocked,
        meaningful_delta_refs=(source_event.event_id,),
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2-I5-ROUTE"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i7_novelty_suppression_changes_only_core_scarcity_assessment_on_same_i1():
    _, ready, suppressed = make_i7_pair()
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I7A_WORLD_ECHO", ready),
        right_stage_a_package=stage_a("I7A_WORLD_ECHO", suppressed),
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2-I7-NOVELTY"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.left_source_status == "PRIVATE_WORLD_ECHO_READY"
    assert result.right_source_status == "SILENCE"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i8_storylet_ineligibility_remains_upstream_owned_on_same_i1():
    _, eligible, invalid = make_i8_pair()
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I8C_STORYLET", eligible),
        right_stage_a_package=stage_a("I8C_STORYLET", invalid),
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2-I8-ROLE"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.left_source_status == "STORYLET_ELIGIBLE"
    assert result.right_source_status == "NO_VALID_STORYLET"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


@pytest.mark.parametrize(
    "pair",
    [("I5A_INFORMATION_OPPORTUNITY", "I7A_WORLD_ECHO"),
     ("I7A_WORLD_ECHO", "I8C_STORYLET"),
     ("I5A_INFORMATION_OPPORTUNITY", "I8C_STORYLET")],
)
def test_core_shape_is_present_across_i5_i7_i8(pair):
    _, i5, _ = make_i5_pair()
    _, i7, _ = make_i7_pair()
    _, i8, _ = make_i8_pair()
    packages = {
        "I5A_INFORMATION_OPPORTUNITY": stage_a("I5A_INFORMATION_OPPORTUNITY", i5),
        "I7A_WORLD_ECHO": stage_a("I7A_WORLD_ECHO", i7),
        "I8C_STORYLET": stage_a("I8C_STORYLET", i8),
    }
    left_kind, right_kind = pair
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=packages[left_kind],
        right_stage_a_package=packages[right_kind],
        fixture=comparison("CROSS_SOURCE_CORE_SHAPE", f"A2-CROSS:{left_kind}:{right_kind}"),
    )
    assert result.outcome == "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
    for core in (thaw_value(result.left_core_axes), thaw_value(result.right_core_axes)):
        assert set(core) == {
            "causal_world_integrity",
            "agency_legibility",
            "knowledge_provenance_integrity",
            "legal_dead_end_opportunity_scarcity_risk",
        }
        assert core["causal_world_integrity"]["assessment"] == "SUPPORTED"
        assert core["agency_legibility"]["assessment"] == "SUPPORTED"
        assert core["knowledge_provenance_integrity"]["assessment"] == "SUPPORTED"
        assert core["legal_dead_end_opportunity_scarcity_risk"]["assessment"] in {"ABSENT", "RISK"}


def test_mechanism_absence_stays_not_applicable_not_bad_quality():
    _, i5, _ = make_i5_pair()
    _, i8, _ = make_i8_pair()
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I5A_INFORMATION_OPPORTUNITY", i5),
        right_stage_a_package=stage_a("I8C_STORYLET", i8),
        fixture=comparison("CROSS_SOURCE_CORE_SHAPE", "A2-NOT-APPLICABLE"),
    )
    assert "character_relationship_continuity" in result.left_not_applicable_mechanism_axes
    assert "setup_promise_anchor_continuity" in result.left_not_applicable_mechanism_axes
    assert "meaningful_state_information_relationship_delta" in result.right_not_applicable_mechanism_axes


def test_false_metadata_only_claim_is_rejected_when_source_changed():
    _, valid, blocked = make_i5_pair()
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I5A_INFORMATION_OPPORTUNITY", valid),
        right_stage_a_package=stage_a(
            "I5A_INFORMATION_OPPORTUNITY", blocked, authored_design_fit="SUPPORTED"
        ),
        fixture=comparison("AUTHORED_DESIGN_METADATA_ONLY", "A2-FALSE-METADATA"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "AUTHORED_METADATA_COMPARISON_REQUIRES_IDENTICAL_SOURCE" in result.integrity_failures


def test_status_change_comparison_rejects_different_i1_history():
    _, ready, suppressed_after_new_event = make_i7_pair(mutate_history_between=True)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I7A_WORLD_ECHO", ready),
        right_stage_a_package=stage_a("I7A_WORLD_ECHO", suppressed_after_new_event),
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2-DIFFERENT-I1"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "UPSTREAM_STATUS_COMPARISON_REQUIRES_SAME_I1_REPLAY" in result.integrity_failures


def test_identical_control_is_exactly_stable():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=comparison("IDENTICAL_CONTROL"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_IDENTICAL_CONTROL"
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ()


def test_caller_cannot_mint_core_evidence():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    with pytest.raises(ValueError, match="I8D_A2_CALLER_AUTHORED_CORE_EVIDENCE_FORBIDDEN"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=comparison("IDENTICAL_CONTROL"),
            caller_core_evidence={"causal_world_integrity": "TRUST_ME"},
        )


def test_fixture_cannot_escalate_to_px_authority():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    forged = StageA2ComparisonFixture(
        comparison_id="A2-FORGED",
        comparison_kind="IDENTICAL_CONTROL",
        authority_class="PX_AND_WORLD_AUTHORITY",
    )
    with pytest.raises(ValueError, match="I8D_A2_FIXTURE_AUTHORITY_ESCALATION"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=forged,
        )


def test_unsupported_comparison_kind_fails_closed():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    forged = StageA2ComparisonFixture("A2-BAD-KIND", "MAXIMIZE_ENGAGEMENT")
    with pytest.raises(ValueError, match="I8D_A2_COMPARISON_KIND_UNSUPPORTED"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=forged,
        )


def test_stage_a_outer_tamper_yields_integrity_failure_without_partial_core():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(package)
    envelope["payload"]["fixture"]["authored_design_fit"] = "SUPPORTED"
    tampered = canonical_json_bytes(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=tampered,
        right_stage_a_package=package,
        fixture=comparison("IDENTICAL_CONTROL", "A2-STAGE-A-TAMPER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert thaw_value(result.left_core_axes) == {}
    assert thaw_value(result.right_core_axes) == {}
    assert result.left_evaluation_id is None


def test_nested_upstream_tamper_cannot_be_laundered_by_recomputed_stage_a_digest():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(package)
    nested = json.loads(base64.b64decode(envelope["payload"]["source_package_b64"]))
    nested["payload"]["source_event_id"] = "FORGED-A2-EVENT"
    forged_nested = refresh_outer_digest(nested)
    envelope["payload"]["source_package_b64"] = base64.b64encode(forged_nested).decode("ascii")
    envelope["payload"]["source_package_sha256"] = hashlib.sha256(forged_nested).hexdigest()
    forged_stage_a = refresh_outer_digest(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=forged_stage_a,
        right_stage_a_package=package,
        fixture=comparison("IDENTICAL_CONTROL", "A2-NESTED-TAMPER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert thaw_value(result.left_core_axes) == {}
    assert result.integrity_failures


def test_same_inputs_are_deterministic():
    _, source, _ = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    right = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED"
    )
    fixture = comparison("AUTHORED_DESIGN_METADATA_ONLY", "A2-DETERMINISTIC")
    first = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left, right_stage_a_package=right, fixture=fixture
    )
    second = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left, right_stage_a_package=right, fixture=fixture
    )
    assert first == second


def test_export_is_byte_deterministic_and_replays_exactly():
    _, source, _ = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    right = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED"
    )
    fixture = comparison("AUTHORED_DESIGN_METADATA_ONLY", "A2-EXPORT")
    first = export_stage_a2_axis_stability_package(
        left_stage_a_package=left, right_stage_a_package=right, fixture=fixture
    )
    second = export_stage_a2_axis_stability_package(
        left_stage_a_package=left, right_stage_a_package=right, fixture=fixture
    )
    assert first == second
    assert replay_stage_a2_axis_stability_package(first) == evaluate_stage_a2_axis_stability(
        left_stage_a_package=left, right_stage_a_package=right, fixture=fixture
    )


def test_export_binds_exact_stage_a_hashes():
    _, source, _ = make_i7_pair()
    left = stage_a("I7A_WORLD_ECHO", source)
    right = stage_a(
        "I7A_WORLD_ECHO", source, recoverable_thread_refs=("THREAD:A2-HASH",)
    )
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("RECOVERABLE_THREAD_METADATA_ONLY", "A2-HASH"),
    )
    payload = json.loads(exported)["payload"]
    assert payload["left_stage_a_sha256"] == hashlib.sha256(left).hexdigest()
    assert payload["right_stage_a_sha256"] == hashlib.sha256(right).hexdigest()


def test_stage_a2_outer_tamper_fails_closed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2-OUTER"),
    )
    envelope = json.loads(exported)
    envelope["payload"]["expected_observation"]["outcome"] = "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
    with pytest.raises(ValueError, match="I8D_A2_REPLAY_PACKAGE_TAMPERED"):
        replay_stage_a2_axis_stability_package(canonical_json_bytes(envelope))


def test_recomputed_a2_outer_still_cannot_launder_nested_stage_a_tamper():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2-NESTED-STAGE-A"),
    )
    envelope = json.loads(exported)
    left = json.loads(base64.b64decode(envelope["payload"]["left_stage_a_b64"]))
    left["payload"]["fixture"]["authored_design_fit"] = "SUPPORTED"
    tampered_left = canonical_json_bytes(left)
    envelope["payload"]["left_stage_a_b64"] = base64.b64encode(tampered_left).decode("ascii")
    envelope["payload"]["left_stage_a_sha256"] = hashlib.sha256(tampered_left).hexdigest()
    with pytest.raises(ValueError, match="I8D_REPLAY_PACKAGE_TAMPERED"):
        replay_stage_a2_axis_stability_package(refresh_outer_digest(envelope))


def test_recomputed_outer_cannot_forge_expected_observation():
    _, source, _ = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    right = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED"
    )
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("AUTHORED_DESIGN_METADATA_ONLY", "A2-FORGE-EXPECTED"),
    )
    envelope = json.loads(exported)
    envelope["payload"]["expected_observation"]["changed_core_material"] = [
        "causal_world_integrity"
    ]
    with pytest.raises(ValueError, match="I8D_A2_REPLAY_OBSERVATION_MATERIALIZATION_MISMATCH"):
        replay_stage_a2_axis_stability_package(refresh_outer_digest(envelope))


def test_authored_metadata_may_change_stage_a_class_but_still_not_core_authority():
    _, source, _ = make_i5_pair()
    thin = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="THIN"
    )
    supported = stage_a(
        "I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED"
    )
    assert (
        replay_branch_evidence_experiment_package(thin).diagnostic_class
        != replay_branch_evidence_experiment_package(supported).diagnostic_class
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=thin,
        right_stage_a_package=supported,
        fixture=comparison("AUTHORED_DESIGN_METADATA_ONLY", "A2-CLASS-QUARANTINE"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()


def test_deferred_metric_decisions_remain_open_in_every_observation():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=comparison("IDENTICAL_CONTROL", "A2-DEFERRED"),
    )
    assert result.deferred_decisions == (
        "OD-CLUE-QUALITY-001",
        "OD-PX-SCORING-001",
    )
    assert result.authority_class.endswith("NOT_WORLD_LEGALITY_OR_PX_AUTHORITY")


def test_integrity_failure_cannot_be_exported_as_valid_stage_a2_package():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    with pytest.raises(ValueError):
        export_stage_a2_axis_stability_package(
            left_stage_a_package=package + b"BROKEN",
            right_stage_a_package=package,
            fixture=comparison("IDENTICAL_CONTROL", "A2-NO-INTEGRITY-EXPORT"),
        )
