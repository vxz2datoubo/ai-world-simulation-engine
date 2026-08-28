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

# I5 held-out world
I5_SOURCE = "A2-I5-SOURCE"
I5_CARRIER = "A2-I5-CARRIER"
I5_PLAYER = "A2-I5-PLAYER"
I5_NOTICE = "A2-I5-NOTICE"
I5_CAPITAL = "A2-I5-CAPITAL"
I5_WILDERNESS = "A2-I5-WILDERNESS"
I5_PRINCIPAL = "principal://i8d-a2/i5-source"

# I7 held-out world
I7_PLAYER = "A2-I7-PLAYER"
I7_NPC = "A2-I7-NPC"
I7_DOOR = "A2-I7-DOOR"
I7_CRATE = "A2-I7-CRATE"
I7_SCENE = "A2-I7-SCENE"
I7_PRINCIPAL = "principal://i8d-a2/i7-player"

# I8 held-out world
I8_PLAYER = "A2-I8-PLAYER"
I8_NPC = "A2-I8-INNKEEPER"
I8_DOOR = "A2-I8-DOOR"
I8_CRATE = "A2-I8-CRATE"
I8_SCENE = "A2-I8-SCENE"
I8_PRINCIPAL = "principal://i8d-a2/i8-player"


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def digest_value(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def refresh_outer_digest(envelope: dict) -> bytes:
    envelope["sha256"] = digest_value(envelope["payload"])
    return canonical_json_bytes(envelope)


def compare_fixture(kind: str, *, comparison_id: str | None = None):
    return StageA2ComparisonFixture(
        comparison_id=comparison_id or f"A2-COMPARE:{kind}",
        comparison_kind=kind,
    )


def stage_a_fixture(**overrides):
    values = {
        "fixture_id": "A2-STAGE-A-METADATA",
        "authored_design_fit": "NOT_APPLICABLE",
        "meaningful_delta_refs": (),
        "recoverable_thread_refs": (),
        "repetition_key": None,
        "prior_occurrence_count": 0,
    }
    values.update(overrides)
    return BranchEvidenceExperimentFixture(**values)


def make_i5_source(*, route_available: bool = True):
    world = WorldState(
        world_id="WORLD-A2-I5",
        active_scene_id=I5_CAPITAL,
        baseline_version="A2-I5-BASELINE-v1",
        actors={
            I5_SOURCE: ActorState(I5_SOURCE, "卫兵", I5_CAPITAL, capabilities={"HIT"}),
            I5_CARRIER: ActorState(I5_CARRIER, "行商", I5_CAPITAL, capabilities={"SPEAK"}),
            I5_PLAYER: ActorState(I5_PLAYER, "旅人", I5_WILDERNESS, capabilities={"SPEAK"}),
        },
        objects={
            I5_NOTICE: ObjectState(
                I5_NOTICE,
                "告示牌",
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
                ["asset://a2/i5/capital"],
                [I5_NOTICE],
                [I5_SOURCE, I5_CARRIER],
            ),
            I5_WILDERNESS: SceneState(
                I5_WILDERNESS,
                ["asset://a2/i5/wilderness"],
                [],
                [I5_PLAYER],
            ),
        },
        principal_actor_bindings={I5_PRINCIPAL: {I5_SOURCE}},
        reachable_pairs={(I5_SOURCE, I5_NOTICE)},
        visible_pairs={(I5_NOTICE, I5_CARRIER)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸告示牌", I5_SOURCE, world, I5_PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    fixture = ShadowPlausibilityFixture(
        fixture_id="A2-I5-ROUTE",
        target_scene_id=I5_WILDERNESS,
        carrier_origin_scene_id=I5_CAPITAL,
        route_available=route_available,
        travel_steps_required=2,
        travel_steps_available=4,
        identity_history_consistent=True,
        motivation_ref="MOTIVE:A2-MERCHANT-TRAVEL",
        anti_repeat_allowed=True,
        asset_available=True,
    )
    package = export_information_opportunity_shadow_package(
        baseline=baseline,
        world=world,
        source_event_id=source.event_id,
        carrier_npc_id=I5_CARRIER,
        player_actor_id=I5_PLAYER,
        fixture=fixture,
    )
    return source, package


def make_i7_source(*, suppressed: bool = False, add_later: bool = False):
    world = WorldState(
        world_id="WORLD-A2-I7",
        active_scene_id=I7_SCENE,
        baseline_version="A2-I7-BASELINE-v1",
        primary_player_actor_id=I7_PLAYER,
        actors={
            I7_PLAYER: ActorState(
                I7_PLAYER,
                "旅人",
                I7_SCENE,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            I7_NPC: ActorState(I7_NPC, "路人", I7_SCENE, capabilities={"SPEAK"}),
        },
        objects={
            I7_DOOR: ObjectState(
                I7_DOOR,
                "旧门",
                I7_SCENE,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            I7_CRATE: ObjectState(
                I7_CRATE,
                "木箱",
                I7_SCENE,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={I7_NPC: NPCMindState(I7_NPC, "BYSTANDER")},
        scenes={
            I7_SCENE: SceneState(
                I7_SCENE,
                ["asset://a2/i7/scene"],
                [I7_DOOR, I7_CRATE],
                [I7_PLAYER, I7_NPC],
            )
        },
        principal_actor_bindings={I7_PRINCIPAL: {I7_PLAYER}},
        reachable_pairs={(I7_PLAYER, I7_DOOR), (I7_PLAYER, I7_CRATE)},
    )
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸旧门", I7_PLAYER, world, I7_PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)
    source = next(event for event in resolution.events if event.event_type == "OBJECT_DAMAGED")
    first_filter = ReferencePrivateEchoFilter(fixture_id="A2-I7-ECHO-FILTER")
    first = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=I7_PLAYER,
        target_object_id=I7_DOOR,
        source_event_id=source.event_id,
        fixture=first_filter,
    )
    if add_later:
        later = ActionCompiler().compile("砸木箱", I7_PLAYER, world, I7_PRINCIPAL)
        SimulationEngine().resolve_and_commit(later, world)
    final_filter = ReferencePrivateEchoFilter(
        fixture_id="A2-I7-ECHO-FILTER",
        already_seen_novelty_keys=(first.novelty_key,) if suppressed else (),
    )
    package = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=I7_PLAYER,
        target_object_id=I7_DOOR,
        source_event_id=source.event_id,
        fixture=final_filter,
    )
    return source, first.novelty_key, package


def make_i8_source(*, eligible: bool = True):
    world = WorldState(
        world_id="WORLD-A2-I8",
        active_scene_id=I8_SCENE,
        baseline_version="A2-I8-BASELINE-v1",
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
                "店主",
                I8_SCENE,
                strength=1.0,
                capabilities={"SPEAK"},
            ),
        },
        objects={
            I8_DOOR: ObjectState(
                I8_DOOR,
                "店门",
                I8_SCENE,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            I8_CRATE: ObjectState(
                I8_CRATE,
                "货箱",
                I8_SCENE,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={I8_NPC: NPCMindState(I8_NPC, "INNKEEPER")},
        scenes={
            I8_SCENE: SceneState(
                I8_SCENE,
                ["asset://a2/i8/inn"],
                [I8_DOOR, I8_CRATE],
                [I8_PLAYER, I8_NPC],
            )
        },
        principal_actor_bindings={I8_PRINCIPAL: {I8_PLAYER}},
        reachable_pairs={(I8_PLAYER, I8_DOOR), (I8_PLAYER, I8_CRATE)},
        audible_pairs={(I8_PLAYER, I8_NPC)},
    )
    baseline = capture_pristine_baseline(world)
    damage_action = ActionCompiler().compile("砸店门", I8_PLAYER, world, I8_PRINCIPAL)
    damage_resolution = SimulationEngine().resolve_and_commit(damage_action, world)
    damage = next(event for event in damage_resolution.events if event.event_type == "OBJECT_DAMAGED")
    speech_action = ActionCompiler().compile(
        f"告诉店主 PROMISE_REPAIR_OBJECT:{I8_DOOR}",
        I8_PLAYER,
        world,
        I8_PRINCIPAL,
    )
    speech_resolution = SimulationEngine().resolve_and_commit(speech_action, world)
    speech = next(event for event in speech_resolution.events if event.event_type == "SPEECH_UTTERED")
    acquisition = next(
        event
        for event in speech_resolution.events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("npc_id") == I8_NPC
        and event.payload.get("source_event_id") == speech.event_id
    )
    callback_role = I8_NPC if eligible else "A2-I8-NONCANONICAL-ROLE"
    storylet = {
        "storylet_id": "STORYLET:A2-PROMISE-CALLBACK",
        "preconditions": [
            {"kind": "CALLBACK_OPPORTUNITY_REQUIRED"},
            {"kind": "TARGET_OBJECT_PRESENT", "object_id": I8_DOOR},
            {"kind": "ACTORS_SHARE_ACTIVE_SCENE", "actor_ids": [I8_PLAYER, I8_NPC]},
            {"kind": "WORLD_EVENT_PRESENT", "event_id": speech.event_id},
        ],
        "eligible_roles": {
            "player_actor_id": I8_PLAYER,
            "callback_npc_id": callback_role,
        },
        "knowledge_constraints": [
            {
                "kind": "CALLBACK_REQUIRED_FACTS_EXACT",
                "fact_refs": [speech.event_id, acquisition.event_id, damage.event_id],
            },
            {"kind": "EXACT_CALLBACK_RECIPIENT", "npc_id": I8_NPC},
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
        "version": "1.0.0-a2-reference",
    }
    package = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=storylet,
        player_actor_id=I8_PLAYER,
        promise_recipient_npc_id=I8_NPC,
        candidate_npc_id=I8_NPC,
        target_object_id=I8_DOOR,
        source_speech_event_id=speech.event_id,
    )
    return damage, speech, acquisition, package


def make_stage_a(source_kind, source_package, **fixture_overrides):
    fixture = stage_a_fixture(**fixture_overrides)
    return export_branch_evidence_experiment_package(
        source_kind=source_kind,
        source_package=source_package,
        fixture=fixture,
    )


def core_material(package):
    result = replay_branch_evidence_experiment_package(package)
    axes = thaw_value(result.axis_evidence)
    return {
        key: axes[key]
        for key in (
            "causal_world_integrity",
            "agency_legibility",
            "knowledge_provenance_integrity",
            "legal_dead_end_opportunity_scarcity_risk",
        )
    }


def test_i8d_a2_scope_locks_keep_stage_b_and_px_blocked():
    assert I8D_STAGE_A2_EVALUATION_ONLY is True
    assert NO_STAGE_B_PRODUCTION_INTERFACE is True
    assert NO_BRANCH_QUALITY_CANONICAL_TYPE is True
    assert NO_UNIVERSAL_QUALITY_SCORE is True
    assert NO_PX_RANKING_OR_WEIGHTS is True
    assert NO_WORLD_OR_KNOWLEDGE_MUTATION is True
    assert NO_STORYLET_OR_ENCOUNTER_REALIZATION is True
    assert NO_RETCON_RESURRECTION_OR_RECONVERGENCE is True
    assert NO_LLM_DIRECTOR_RENDERER_AUTHORITY is True
    assert NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i8d_a2_observation_has_no_score_weight_rank_or_legality_field():
    names = {field.name.lower() for field in fields(MinimalCoreStabilityObservation)}
    forbidden = {"score", "weight", "rank", "legality", "legalized", "quality_score"}
    assert not (names & forbidden)


def test_i8d_a2_authored_design_fit_change_cannot_move_authority_grounded_core():
    _, source = make_i5_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="NOT_APPLICABLE")
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED")
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("AUTHORED_DESIGN_METADATA_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_core_assessments == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ("genre_theme_design_fit",)
    assert thaw_value(result.left_core_axes) == thaw_value(result.right_core_axes)


def test_i8d_a2_recoverable_thread_metadata_cannot_move_core_or_mechanism_axes():
    _, _, source = make_i7_source()
    left = make_stage_a("I7A_WORLD_ECHO", source)
    right = make_stage_a(
        "I7A_WORLD_ECHO",
        source,
        recoverable_thread_refs=("AUTHORED_THREAD:A2-OPTIONAL-RETURN",),
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("RECOVERABLE_THREAD_METADATA_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ("recoverable_thread_availability",)


def test_i8d_a2_repetition_history_changes_only_contrivance_axis():
    source_event, _, source = make_i7_source()
    left = make_stage_a(
        "I7A_WORLD_ECHO",
        source,
        repetition_key=source_event.event_id,
        prior_occurrence_count=0,
    )
    right = make_stage_a(
        "I7A_WORLD_ECHO",
        source,
        repetition_key=source_event.event_id,
        prior_occurrence_count=2,
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("REPETITION_HISTORY_ONLY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_REPETITION_HISTORY_CHANGE"
    assert result.changed_core_material == ()
    assert result.changed_core_assessments == ()
    assert result.changed_mechanism_axes == ("contrivance_repetition_risk",)
    assert result.changed_authored_axes == ()


def test_i8d_a2_i5_route_loss_changes_scarcity_assessment_not_integrity_agency_or_provenance():
    source_event, valid_source = make_i5_source(route_available=True)
    _, blocked_source = make_i5_source(route_available=False)
    left = make_stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        valid_source,
        meaningful_delta_refs=(source_event.event_id,),
    )
    right = make_stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        blocked_source,
        meaningful_delta_refs=(source_event.event_id,),
    )
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("UPSTREAM_STATUS_CHANGE", comparison_id="A2-I5-ROUTE-LOSS"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == ("legal_dead_end_opportunity_scarcity_risk",)
    left_core = thaw_value(result.left_core_axes)
    right_core = thaw_value(result.right_core_axes)
    for axis in ("causal_world_integrity", "agency_legibility", "knowledge_provenance_integrity"):
        assert left_core[axis]["assessment"] == right_core[axis]["assessment"] == "SUPPORTED"
    assert left_core["legal_dead_end_opportunity_scarcity_risk"]["assessment"] == "ABSENT"
    assert right_core["legal_dead_end_opportunity_scarcity_risk"]["assessment"] == "RISK"
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i8d_a2_i7_novelty_suppression_changes_scarcity_without_rewriting_world_or_provenance_core():
    _, _, ready_source = make_i7_source(suppressed=False)
    _, _, silent_source = make_i7_source(suppressed=True)
    left = make_stage_a("I7A_WORLD_ECHO", ready_source)
    right = make_stage_a("I7A_WORLD_ECHO", silent_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("UPSTREAM_STATUS_CHANGE", comparison_id="A2-I7-NOVELTY"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == ("legal_dead_end_opportunity_scarcity_risk",)
    assert result.left_source_status == "PRIVATE_WORLD_ECHO_READY"
    assert result.right_source_status == "SILENCE"
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i8d_a2_i8_storylet_ineligibility_remains_upstream_owned_and_only_scarcity_assessment_changes():
    _, _, _, eligible_source = make_i8_source(eligible=True)
    _, _, _, invalid_source = make_i8_source(eligible=False)
    left = make_stage_a("I8C_STORYLET", eligible_source)
    right = make_stage_a("I8C_STORYLET", invalid_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("UPSTREAM_STATUS_CHANGE", comparison_id="A2-I8-ROLE-BINDING"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == ("legal_dead_end_opportunity_scarcity_risk",)
    assert result.left_source_status == "STORYLET_ELIGIBLE"
    assert result.right_source_status == "NO_VALID_STORYLET"
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


@pytest.mark.parametrize(
    ("left_kind", "right_kind"),
    [
        ("I5A_INFORMATION_OPPORTUNITY", "I7A_WORLD_ECHO"),
        ("I7A_WORLD_ECHO", "I8C_STORYLET"),
        ("I5A_INFORMATION_OPPORTUNITY", "I8C_STORYLET"),
    ],
)
def test_i8d_a2_candidate_core_shape_exists_across_distinct_source_kinds(left_kind, right_kind):
    _, i5 = make_i5_source()
    _, _, i7 = make_i7_source()
    _, _, _, i8 = make_i8_source()
    packages = {
        "I5A_INFORMATION_OPPORTUNITY": make_stage_a("I5A_INFORMATION_OPPORTUNITY", i5),
        "I7A_WORLD_ECHO": make_stage_a("I7A_WORLD_ECHO", i7),
        "I8C_STORYLET": make_stage_a("I8C_STORYLET", i8),
    }
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=packages[left_kind],
        right_stage_a_package=packages[right_kind],
        fixture=compare_fixture("CROSS_SOURCE_CORE_SHAPE", comparison_id=f"A2-CROSS:{left_kind}:{right_kind}"),
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


def test_i8d_a2_mechanism_absence_is_preserved_as_not_applicable_not_low_quality():
    _, i5 = make_i5_source()
    _, _, _, i8 = make_i8_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", i5)
    right = make_stage_a("I8C_STORYLET", i8)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("CROSS_SOURCE_CORE_SHAPE", comparison_id="A2-NOT-APPLICABLE"),
    )
    assert "character_relationship_continuity" in result.left_not_applicable_mechanism_axes
    assert "setup_promise_anchor_continuity" in result.left_not_applicable_mechanism_axes
    assert "meaningful_state_information_relationship_delta" in result.right_not_applicable_mechanism_axes


def test_i8d_a2_metadata_only_claim_fails_if_nested_source_changed():
    _, valid_source = make_i5_source(route_available=True)
    _, blocked_source = make_i5_source(route_available=False)
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", valid_source, authored_design_fit="NOT_APPLICABLE")
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", blocked_source, authored_design_fit="SUPPORTED")
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("AUTHORED_DESIGN_METADATA_ONLY", comparison_id="A2-FALSE-METADATA-CLAIM"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "AUTHORED_METADATA_COMPARISON_REQUIRES_IDENTICAL_SOURCE" in result.integrity_failures


def test_i8d_a2_upstream_status_comparison_rejects_different_i1_history():
    _, _, ready_source = make_i7_source(suppressed=False, add_later=False)
    _, _, silent_different_history = make_i7_source(suppressed=True, add_later=True)
    left = make_stage_a("I7A_WORLD_ECHO", ready_source)
    right = make_stage_a("I7A_WORLD_ECHO", silent_different_history)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("UPSTREAM_STATUS_CHANGE", comparison_id="A2-DIFFERENT-I1"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "UPSTREAM_STATUS_COMPARISON_REQUIRES_SAME_I1_REPLAY" in result.integrity_failures


def test_i8d_a2_cross_source_claim_requires_distinct_source_kinds():
    _, source = make_i5_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, recoverable_thread_refs=("THREAD:A2",))
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("CROSS_SOURCE_CORE_SHAPE", comparison_id="A2-SAME-KIND-NOT-CROSS"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "CROSS_SOURCE_COMPARISON_REQUIRES_DISTINCT_SOURCE_KINDS" in result.integrity_failures


def test_i8d_a2_identical_control_is_exactly_stable():
    _, _, source = make_i7_source()
    package = make_stage_a("I7A_WORLD_ECHO", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=compare_fixture("IDENTICAL_CONTROL"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_IDENTICAL_CONTROL"
    assert result.changed_core_assessments == ()
    assert result.changed_core_material == ()
    assert result.changed_mechanism_axes == ()
    assert result.changed_authored_axes == ()


def test_i8d_a2_same_inputs_are_deterministic():
    _, source = make_i5_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="NOT_APPLICABLE")
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="THIN")
    fixture = compare_fixture("AUTHORED_DESIGN_METADATA_ONLY", comparison_id="A2-DETERMINISTIC")
    first = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=fixture,
    )
    second = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=fixture,
    )
    assert first == second


def test_i8d_a2_caller_cannot_supply_core_evidence():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    with pytest.raises(ValueError, match="I8D_A2_CALLER_AUTHORED_CORE_EVIDENCE_FORBIDDEN"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=compare_fixture("IDENTICAL_CONTROL"),
            caller_core_evidence={"causal_world_integrity": "TRUST_ME"},
        )


def test_i8d_a2_fixture_cannot_escalate_to_px_or_world_authority():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    forged = StageA2ComparisonFixture(
        comparison_id="A2-FORGED-AUTHORITY",
        comparison_kind="IDENTICAL_CONTROL",
        authority_class="PX_RANKING_AND_WORLD_AUTHORITY",
    )
    with pytest.raises(ValueError, match="I8D_A2_FIXTURE_AUTHORITY_ESCALATION"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=forged,
        )


def test_i8d_a2_unsupported_comparison_kind_fails_closed():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    fixture = StageA2ComparisonFixture(
        comparison_id="A2-UNSUPPORTED",
        comparison_kind="MAXIMIZE_ENGAGEMENT_SCORE",
    )
    with pytest.raises(ValueError, match="I8D_A2_COMPARISON_KIND_UNSUPPORTED"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=package,
            right_stage_a_package=package,
            fixture=fixture,
        )


def test_i8d_a2_tampered_stage_a_outer_digest_yields_integrity_failure_with_no_partial_core():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(package)
    envelope["payload"]["fixture"]["authored_design_fit"] = "SUPPORTED"
    tampered = canonical_json_bytes(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=tampered,
        right_stage_a_package=package,
        fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-TAMPER-OUTER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert thaw_value(result.left_core_axes) == {}
    assert thaw_value(result.right_core_axes) == {}
    assert result.left_evaluation_id is None
    assert result.right_evaluation_id is None


def test_i8d_a2_nested_upstream_tamper_cannot_be_laundered_by_recomputed_stage_a_digest():
    _, source = make_i5_source()
    stage_a = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(stage_a)
    nested = base64.b64decode(envelope["payload"]["source_package_b64"])
    nested_envelope = json.loads(nested)
    nested_envelope["payload"]["source_event_id"] = "FORGED-A2-EVENT"
    forged_nested = refresh_outer_digest(nested_envelope)
    envelope["payload"]["source_package_b64"] = base64.b64encode(forged_nested).decode("ascii")
    envelope["payload"]["source_package_sha256"] = hashlib.sha256(forged_nested).hexdigest()
    tampered_stage_a = refresh_outer_digest(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=tampered_stage_a,
        right_stage_a_package=stage_a,
        fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-NESTED-UPSTREAM-TAMPER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert result.integrity_failures
    assert thaw_value(result.left_core_axes) == {}


def test_i8d_a2_export_is_byte_deterministic_and_replays_exactly():
    _, source = make_i5_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="NOT_APPLICABLE")
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED")
    fixture = compare_fixture("AUTHORED_DESIGN_METADATA_ONLY", comparison_id="A2-EXPORT")
    package_a = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=fixture,
    )
    package_b = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=fixture,
    )
    assert package_a == package_b
    replayed = replay_stage_a2_axis_stability_package(package_a)
    direct = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=fixture,
    )
    assert replayed == direct


def test_i8d_a2_export_binds_exact_stage_a_hashes():
    _, _, source = make_i7_source()
    left = make_stage_a("I7A_WORLD_ECHO", source)
    right = make_stage_a(
        "I7A_WORLD_ECHO",
        source,
        recoverable_thread_refs=("AUTHORED_THREAD:A2-HASH-BIND",),
    )
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("RECOVERABLE_THREAD_METADATA_ONLY", comparison_id="A2-HASH-BIND"),
    )
    payload = json.loads(package)["payload"]
    assert payload["left_stage_a_sha256"] == hashlib.sha256(left).hexdigest()
    assert payload["right_stage_a_sha256"] == hashlib.sha256(right).hexdigest()


def test_i8d_a2_outer_package_tamper_fails_closed():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-OUTER-TAMPER"),
    )
    envelope = json.loads(exported)
    envelope["payload"]["expected_observation"]["outcome"] = "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
    with pytest.raises(ValueError, match="I8D_A2_REPLAY_PACKAGE_TAMPERED"):
        replay_stage_a2_axis_stability_package(canonical_json_bytes(envelope))


def test_i8d_a2_recomputed_outer_digest_still_cannot_launder_nested_stage_a_tamper():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-NESTED-STAGE-A-TAMPER"),
    )
    outer = json.loads(exported)
    left_stage_a = json.loads(base64.b64decode(outer["payload"]["left_stage_a_b64"]))
    left_stage_a["payload"]["fixture"]["authored_design_fit"] = "SUPPORTED"
    tampered_left = canonical_json_bytes(left_stage_a)  # intentionally stale Stage A digest
    outer["payload"]["left_stage_a_b64"] = base64.b64encode(tampered_left).decode("ascii")
    outer["payload"]["left_stage_a_sha256"] = hashlib.sha256(tampered_left).hexdigest()
    recomputed_outer = refresh_outer_digest(outer)
    with pytest.raises(ValueError, match="I8D_REPLAY_PACKAGE_TAMPERED"):
        replay_stage_a2_axis_stability_package(recomputed_outer)


def test_i8d_a2_recomputed_outer_and_forged_expected_observation_cannot_override_rebuild():
    _, source = make_i5_source()
    left = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="NOT_APPLICABLE")
    right = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source, authored_design_fit="SUPPORTED")
    exported = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("AUTHORED_DESIGN_METADATA_ONLY", comparison_id="A2-FORGED-EXPECTED"),
    )
    outer = json.loads(exported)
    outer["payload"]["expected_observation"]["changed_core_material"] = ["causal_world_integrity"]
    forged = refresh_outer_digest(outer)
    with pytest.raises(ValueError, match="I8D_A2_REPLAY_OBSERVATION_MATERIALIZATION_MISMATCH"):
        replay_stage_a2_axis_stability_package(forged)


def test_i8d_a2_authored_metadata_can_change_stage_a_diagnostic_class_without_becoming_core_authority():
    _, source = make_i5_source()
    left = make_stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        source,
        authored_design_fit="THIN",
    )
    right = make_stage_a(
        "I5A_INFORMATION_OPPORTUNITY",
        source,
        authored_design_fit="SUPPORTED",
    )
    left_stage_a = replay_branch_evidence_experiment_package(left)
    right_stage_a = replay_branch_evidence_experiment_package(right)
    assert left_stage_a.diagnostic_class != right_stage_a.diagnostic_class
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=compare_fixture("AUTHORED_DESIGN_METADATA_ONLY", comparison_id="A2-CLASS-NONAUTHORITY"),
    )
    assert result.outcome == "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
    assert result.changed_core_material == ()
    assert core_material(left) == core_material(right)


def test_i8d_a2_deferred_metric_decisions_remain_explicitly_open_in_observation():
    _, source = make_i5_source()
    package = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=package,
        right_stage_a_package=package,
        fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-DEFERRED"),
    )
    assert result.deferred_decisions == ("OD-CLUE-QUALITY-001", "OD-PX-SCORING-001")
    assert result.authority_class == "STAGE_A2_EVALUATION_OBSERVATION_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY"


def test_i8d_a2_integrity_failure_is_not_exportable_as_valid_observation():
    _, source = make_i5_source()
    stage_a = make_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    broken = stage_a + b"\nBROKEN"
    with pytest.raises(ValueError):
        export_stage_a2_axis_stability_package(
            left_stage_a_package=broken,
            right_stage_a_package=stage_a,
            fixture=compare_fixture("IDENTICAL_CONTROL", comparison_id="A2-NO-EXPORT-INTEGRITY"),
        )
