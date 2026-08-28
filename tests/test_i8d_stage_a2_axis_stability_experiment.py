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
import evals.i8d_branch_quality_evidence_experiment as stage_a_v1
import evals.i8d_branch_quality_evidence_experiment_v2 as stage_a_r1
import evals.i8d_stage_a2_axis_stability_experiment as a2
from evals.i8d_stage_a2_axis_stability_experiment import (
    HISTORICAL_STAGE_A2_V1_NOT_CURRENT,
    HISTORICAL_STAGE_A_V1_REJECTED,
    I8D_STAGE_A2_EVALUATION_ONLY,
    I8D_STAGE_A2_R1_MIGRATION,
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


def digest_material(value) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def refresh_outer(envelope: dict) -> bytes:
    envelope["sha256"] = digest_material(envelope["payload"])
    return canonical_json_bytes(envelope)


def comparison(kind: str, label: str | None = None) -> StageA2ComparisonFixture:
    return StageA2ComparisonFixture(
        comparison_id=label or f"A2-R1:{kind}",
        comparison_kind=kind,
    )


def stage_a_fixture(**overrides):
    values = {
        "fixture_id": "A2-R1-STAGE-A-CONTROL",
        "authored_design_fit": "NOT_APPLICABLE",
        "meaningful_delta_refs": (),
        "recoverable_thread_refs": (),
        "repetition_key": None,
        "prior_occurrence_count": 0,
    }
    values.update(overrides)
    return stage_a_r1.BranchEvidenceExperimentFixture(**values)


def stage_a(kind: str, source_package: bytes, **fixture_overrides) -> bytes:
    return stage_a_r1.export_branch_evidence_experiment_package(
        source_kind=kind,
        source_package=source_package,
        fixture=stage_a_fixture(**fixture_overrides),
    )


def historical_stage_a(kind: str, source_package: bytes, **fixture_overrides) -> bytes:
    return stage_a_v1.export_branch_evidence_experiment_package(
        source_kind=kind,
        source_package=source_package,
        fixture=stage_a_fixture(**fixture_overrides),
    )


def stage_a_payload(package: bytes) -> dict:
    return json.loads(package.decode("utf-8"))["payload"]


def make_i5_pair():
    source_actor = "A2R1-I5-SOURCE"
    carrier = "A2R1-I5-CARRIER"
    player = "A2R1-I5-PLAYER"
    notice = "A2R1-I5-NOTICE"
    capital = "A2R1-I5-CAPITAL"
    wilderness = "A2R1-I5-WILDERNESS"
    principal = "principal://a2r1/i5"
    world = WorldState(
        world_id="WORLD-A2R1-I5",
        active_scene_id=capital,
        baseline_version="A2R1-I5-BASELINE-v1",
        actors={
            source_actor: ActorState(source_actor, "卫兵", capital, capabilities={"HIT"}),
            carrier: ActorState(carrier, "行商", capital, capabilities={"SPEAK"}),
            player: ActorState(player, "旅人", wilderness, capabilities={"SPEAK"}),
        },
        objects={
            notice: ObjectState(
                notice,
                "告示牌",
                capital,
                mass=20.0,
                graspable=False,
                fragility=0.5,
            )
        },
        npc_minds={carrier: NPCMindState(carrier, "MERCHANT")},
        scenes={
            capital: SceneState(
                capital,
                ["asset://a2r1/i5/capital"],
                [notice],
                [source_actor, carrier],
            ),
            wilderness: SceneState(
                wilderness,
                ["asset://a2r1/i5/wilderness"],
                [],
                [player],
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

    def export(route_available: bool) -> bytes:
        fixture = ShadowPlausibilityFixture(
            fixture_id="A2R1-I5-ROUTE",
            target_scene_id=wilderness,
            carrier_origin_scene_id=capital,
            route_available=route_available,
            travel_steps_required=2,
            travel_steps_available=4,
            identity_history_consistent=True,
            motivation_ref="MOTIVE:A2R1-MERCHANT-TRAVEL",
            anti_repeat_allowed=True,
            asset_available=True,
        )
        return export_information_opportunity_shadow_package(
            baseline=baseline,
            world=world,
            source_event_id=source.event_id,
            carrier_npc_id=carrier,
            player_actor_id=player,
            fixture=fixture,
        )

    return source, export(True), export(False)


def make_i7_pair(*, mutate_history_between: bool = False):
    player = "A2R1-I7-PLAYER"
    npc = "A2R1-I7-NPC"
    door = "A2R1-I7-DOOR"
    crate = "A2R1-I7-CRATE"
    scene = "A2R1-I7-SCENE"
    principal = "principal://a2r1/i7"
    world = WorldState(
        world_id="WORLD-A2R1-I7",
        active_scene_id=scene,
        baseline_version="A2R1-I7-BASELINE-v1",
        primary_player_actor_id=player,
        actors={
            player: ActorState(
                player,
                "旅人",
                scene,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            npc: ActorState(npc, "路人", scene, capabilities={"SPEAK"}),
        },
        objects={
            door: ObjectState(
                door,
                "旧门",
                scene,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            crate: ObjectState(
                crate,
                "木箱",
                scene,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={npc: NPCMindState(npc, "BYSTANDER")},
        scenes={
            scene: SceneState(
                scene,
                ["asset://a2r1/i7/scene"],
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
    ready_filter = ReferencePrivateEchoFilter(fixture_id="A2R1-I7-ECHO")
    reference = build_player_private_world_echo_reference(
        baseline=baseline,
        world=world,
        player_actor_id=player,
        target_object_id=door,
        source_event_id=source.event_id,
        fixture=ready_filter,
    )
    ready = export_player_private_world_echo_package(
        baseline=baseline,
        world=world,
        player_actor_id=player,
        target_object_id=door,
        source_event_id=source.event_id,
        fixture=ready_filter,
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
            fixture_id="A2R1-I7-ECHO",
            already_seen_novelty_keys=(reference.novelty_key,),
        ),
    )
    return source, reference.novelty_key, ready, suppressed


def make_i8_pair():
    player = "A2R1-I8-PLAYER"
    npc = "A2R1-I8-INNKEEPER"
    door = "A2R1-I8-DOOR"
    crate = "A2R1-I8-CRATE"
    scene = "A2R1-I8-SCENE"
    principal = "principal://a2r1/i8"
    world = WorldState(
        world_id="WORLD-A2R1-I8",
        active_scene_id=scene,
        baseline_version="A2R1-I8-BASELINE-v1",
        primary_player_actor_id=player,
        actors={
            player: ActorState(
                player,
                "旅人",
                scene,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            npc: ActorState(npc, "店主", scene, capabilities={"SPEAK"}),
        },
        objects={
            door: ObjectState(
                door,
                "店门",
                scene,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            crate: ObjectState(
                crate,
                "货箱",
                scene,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={npc: NPCMindState(npc, "INNKEEPER")},
        scenes={
            scene: SceneState(
                scene,
                ["asset://a2r1/i8/inn"],
                [door, crate],
                [player, npc],
            )
        },
        principal_actor_bindings={principal: {player}},
        reachable_pairs={(player, door), (player, crate)},
        audible_pairs={(player, npc)},
    )
    baseline = capture_pristine_baseline(world)
    damage_resolution = SimulationEngine().resolve_and_commit(
        ActionCompiler().compile("砸店门", player, world, principal), world
    )
    damage = next(e for e in damage_resolution.events if e.event_type == "OBJECT_DAMAGED")
    speech_resolution = SimulationEngine().resolve_and_commit(
        ActionCompiler().compile(
            f"告诉店主 PROMISE_REPAIR_OBJECT:{door}", player, world, principal
        ),
        world,
    )
    speech = next(e for e in speech_resolution.events if e.event_type == "SPEECH_UTTERED")
    acquisition = next(
        e
        for e in speech_resolution.events
        if e.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and e.payload.get("npc_id") == npc
        and e.payload.get("source_event_id") == speech.event_id
    )
    SimulationEngine().resolve_and_commit(
        ActionCompiler().compile("砸货箱", player, world, principal), world
    )

    def storylet(callback_role: str):
        return {
            "storylet_id": "STORYLET:A2R1-PROMISE",
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
            "dramatic_purpose": "A2R1_HELD_OUT_OPTIONAL_PROMISE_CALLBACK",
            "forbidden_contradictions": [
                "NO_RETCON_OR_RESURRECTION",
                "NO_BRANCH_WELDING",
                "NO_AUTOMATIC_SPEECH",
                "NO_AUTOMATIC_PAYOFF_OR_BREACH",
            ],
            "consequence_templates": ["NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"],
            "repeat_policy": {"mode": "NO_AUTO_REALIZATION"},
            "version": "2.0.0-a2r1",
        }

    def export(definition) -> bytes:
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

    return (
        damage,
        speech,
        acquisition,
        export(storylet(npc)),
        export(storylet("A2R1-I8-WRONG-ROLE")),
    )


def test_scope_locks_keep_stage_b_blocked_and_migration_explicit():
    assert I8D_STAGE_A2_EVALUATION_ONLY
    assert I8D_STAGE_A2_R1_MIGRATION
    assert HISTORICAL_STAGE_A_V1_REJECTED
    assert HISTORICAL_STAGE_A2_V1_NOT_CURRENT
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
    assert a2._REPAIRED_STAGE_A_SCHEMA == stage_a_r1.REPAIRED_PACKAGE_SCHEMA
    assert a2._HISTORICAL_STAGE_A_SCHEMA == stage_a_r1.HISTORICAL_V1_PACKAGE_SCHEMA
    assert a2._PACKAGE_SCHEMA != a2._HISTORICAL_A2_SCHEMA


def test_observation_has_no_score_weight_rank_legality_or_quality_field():
    names = {f.name.lower() for f in fields(MinimalCoreStabilityObservation)}
    assert not names & {"score", "weight", "rank", "legality", "quality_score"}


def test_identical_control_is_byte_and_core_stable():
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


def test_recoverable_thread_is_quarantined_from_core_and_mechanism():
    _, _, source, _ = make_i7_pair()
    left = stage_a("I7A_WORLD_ECHO", source)
    right = stage_a(
        "I7A_WORLD_ECHO",
        source,
        recoverable_thread_refs=("AUTHORED_THREAD:A2R1-RETURN",),
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


def test_repetition_history_changes_only_repetition_mechanism_axis():
    _, novelty_key, source, _ = make_i7_pair()
    left = stage_a("I7A_WORLD_ECHO", source)
    right = stage_a(
        "I7A_WORLD_ECHO",
        source,
        repetition_key=novelty_key,
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


def test_i5_status_change_same_i1_moves_only_scarcity_core_assessment():
    _, ready_source, blocked_source = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", ready_source)
    right = stage_a("I5A_INFORMATION_OPPORTUNITY", blocked_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2R1:I5-STATUS"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i7_status_change_same_i1_moves_only_scarcity_core_assessment():
    _, _, ready_source, silent_source = make_i7_pair()
    left = stage_a("I7A_WORLD_ECHO", ready_source)
    right = stage_a("I7A_WORLD_ECHO", silent_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2R1:I7-STATUS"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_i8_status_change_same_i1_moves_only_scarcity_core_assessment():
    _, _, _, eligible_source, invalid_source = make_i8_pair()
    left = stage_a("I8C_STORYLET", eligible_source)
    right = stage_a("I8C_STORYLET", invalid_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2R1:I8-STATUS"),
    )
    assert result.outcome == "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
    assert result.changed_core_assessments == (
        "legal_dead_end_opportunity_scarcity_risk",
    )
    assert result.left_source_i1_sha256 == result.right_source_i1_sha256


def test_status_change_with_different_i1_is_not_valid_comparison():
    _, _, ready_source, silent_source = make_i7_pair(mutate_history_between=True)
    left = stage_a("I7A_WORLD_ECHO", ready_source)
    right = stage_a("I7A_WORLD_ECHO", silent_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2R1:I7-DRIFTED-I1"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert "UPSTREAM_STATUS_COMPARISON_REQUIRES_SAME_I1_REPLAY" in result.integrity_failures


def test_cross_source_core_shape_is_stable_i5_i7_i8():
    _, i5_source, _ = make_i5_pair()
    _, _, i7_source, _ = make_i7_pair()
    _, _, _, i8_source, _ = make_i8_pair()
    packages = [
        stage_a("I5A_INFORMATION_OPPORTUNITY", i5_source),
        stage_a("I7A_WORLD_ECHO", i7_source),
        stage_a("I8C_STORYLET", i8_source),
    ]
    for left, right in ((packages[0], packages[1]), (packages[1], packages[2]), (packages[0], packages[2])):
        result = evaluate_stage_a2_axis_stability(
            left_stage_a_package=left,
            right_stage_a_package=right,
            fixture=comparison("CROSS_SOURCE_CORE_SHAPE"),
        )
        assert result.outcome == "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
        for axes in (thaw_value(result.left_core_axes), thaw_value(result.right_core_axes)):
            assert axes["causal_world_integrity"]["assessment"] == "SUPPORTED"
            assert axes["agency_legibility"]["assessment"] == "SUPPORTED"
            assert axes["knowledge_provenance_integrity"]["assessment"] == "SUPPORTED"


def test_historical_stage_a_v1_is_rejected_as_current_a2_evidence():
    _, source, _ = make_i5_pair()
    legacy = historical_stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    repaired = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=legacy,
        right_stage_a_package=repaired,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:LEGACY-REJECT"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert any("LEFT_STAGE_A_R1_REJECTED" in item for item in result.integrity_failures)
    with pytest.raises(ValueError):
        export_stage_a2_axis_stability_package(
            left_stage_a_package=legacy,
            right_stage_a_package=repaired,
            fixture=comparison("IDENTICAL_CONTROL", "A2R1:LEGACY-EXPORT"),
        )


def test_repaired_stage_a_payload_binds_schema_supersession_and_semantic_domain():
    _, source, _ = make_i5_pair()
    package = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    payload = a2._parse_stage_a_payload(package)
    assert payload["package_schema"] == stage_a_r1.REPAIRED_PACKAGE_SCHEMA
    assert payload["supersedes_schema"] == stage_a_r1.HISTORICAL_V1_PACKAGE_SCHEMA
    assert payload["semantic_reference_domains_sha256"] == digest_material(
        payload["semantic_reference_domains"]
    )


def test_observation_binds_exact_left_and_right_semantic_domain_digests():
    _, ready_source, blocked_source = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", ready_source)
    right = stage_a("I5A_INFORMATION_OPPORTUNITY", blocked_source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2R1:DOMAIN-BIND"),
    )
    assert result.left_semantic_domain_sha256 == stage_a_payload(left)[
        "semantic_reference_domains_sha256"
    ]
    assert result.right_semantic_domain_sha256 == stage_a_payload(right)[
        "semantic_reference_domains_sha256"
    ]
    assert len(result.left_semantic_domain_sha256) == 64
    assert len(result.right_semantic_domain_sha256) == 64


def test_i8_selected_semantic_delta_materializes_supported_axis_without_moving_core():
    damage, _, _, eligible_source, _ = make_i8_pair()
    left = stage_a("I8C_STORYLET", eligible_source)
    right = stage_a(
        "I8C_STORYLET",
        eligible_source,
        meaningful_delta_refs=(damage.event_id,),
    )
    left_result = stage_a_r1.replay_branch_evidence_experiment_package(left)
    right_result = stage_a_r1.replay_branch_evidence_experiment_package(right)
    assert thaw_value(left_result.axis_evidence)[
        "meaningful_state_information_relationship_delta"
    ]["assessment"] == "NOT_APPLICABLE"
    right_delta = thaw_value(right_result.axis_evidence)[
        "meaningful_state_information_relationship_delta"
    ]
    assert right_delta["assessment"] == "SUPPORTED"
    assert right_delta["evidence_refs"] == (damage.event_id,) or right_delta["evidence_refs"] == [damage.event_id]
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left,
        right_stage_a_package=right,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:I8-DELTA-NOT-IDENTICAL"),
    )
    assert result.outcome == "COMPARISON_NOT_VALID"
    assert result.changed_core_material == ()
    assert "meaningful_state_information_relationship_delta" in result.changed_mechanism_axes


def test_i7_novelty_key_cannot_cross_mint_meaningful_delta_before_a2():
    _, novelty_key, source, _ = make_i7_pair()
    with pytest.raises(ValueError, match="MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"):
        stage_a(
            "I7A_WORLD_ECHO",
            source,
            meaningful_delta_refs=(novelty_key,),
        )


def test_i8_storylet_identity_cannot_cross_mint_meaningful_delta_before_a2():
    _, _, _, source, _ = make_i8_pair()
    with pytest.raises(ValueError, match="MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"):
        stage_a(
            "I8C_STORYLET",
            source,
            meaningful_delta_refs=("STORYLET:A2R1-PROMISE",),
        )


def test_event_ref_cannot_cross_mint_repetition_identity_before_a2():
    damage, _, _, source, _ = make_i8_pair()
    with pytest.raises(ValueError, match="REPETITION_KEY_NOT_IN_SEMANTIC_DOMAIN"):
        stage_a(
            "I8C_STORYLET",
            source,
            repetition_key=damage.event_id,
            prior_occurrence_count=1,
        )


def test_r1_semantic_domain_material_tamper_cannot_be_laundered_into_a2():
    _, source, _ = make_i5_pair()
    valid = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(valid.decode("utf-8"))
    envelope["payload"]["semantic_reference_domains"]["meaningful_delta_refs"].append(
        "WORLD-A2R1-I5"
    )
    envelope["payload"]["semantic_reference_domains_sha256"] = digest_material(
        envelope["payload"]["semantic_reference_domains"]
    )
    forged = refresh_outer(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=forged,
        right_stage_a_package=valid,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:DOMAIN-LAUNDER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"
    assert any("LEFT_STAGE_A_R1_REJECTED" in item for item in result.integrity_failures)


def test_r1_semantic_domain_digest_tamper_cannot_be_laundered_into_a2():
    _, source, _ = make_i5_pair()
    valid = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(valid.decode("utf-8"))
    envelope["payload"]["semantic_reference_domains_sha256"] = "0" * 64
    forged = refresh_outer(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=forged,
        right_stage_a_package=valid,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:DOMAIN-DIGEST-LAUNDER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"


def test_r1_expected_result_tamper_cannot_be_laundered_into_a2():
    _, source, _ = make_i5_pair()
    valid = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    envelope = json.loads(valid.decode("utf-8"))
    envelope["payload"]["expected_result"]["diagnostic_class"] = "ROBUST_BY_FIAT"
    forged = refresh_outer(envelope)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=forged,
        right_stage_a_package=valid,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:RESULT-LAUNDER"),
    )
    assert result.outcome == "CORE_INTEGRITY_FAILURE"


def test_a2_v2_export_binds_migration_and_repaired_stage_a_schema():
    _, source, _ = make_i5_pair()
    left = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=left,
        right_stage_a_package=left,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:EXPORT-BIND"),
    )
    payload = json.loads(package.decode("utf-8"))["payload"]
    assert payload["package_schema"] == a2._PACKAGE_SCHEMA
    assert payload["supersedes_schema"] == a2._HISTORICAL_A2_SCHEMA
    assert payload["required_stage_a_schema"] == stage_a_r1.REPAIRED_PACKAGE_SCHEMA
    assert payload["historical_stage_a_schema_rejected"] == stage_a_r1.HISTORICAL_V1_PACKAGE_SCHEMA
    assert payload["left_semantic_domain_sha256"] == stage_a_payload(left)[
        "semantic_reference_domains_sha256"
    ]


def test_historical_a2_v1_identity_cannot_replay_as_repaired_a2():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:HIST-A2"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["package_schema"] = a2._HISTORICAL_A2_SCHEMA
    forged = refresh_outer(envelope)
    with pytest.raises(ValueError, match="HISTORICAL_A2_V1_REJECTED"):
        replay_stage_a2_axis_stability_package(forged)


def test_a2_required_stage_a_binding_tamper_fails_closed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:SCHEMA-BIND-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["required_stage_a_schema"] = stage_a_v1._PACKAGE_SCHEMA
    forged = refresh_outer(envelope)
    with pytest.raises(ValueError, match="REQUIRED_STAGE_A_SCHEMA_DRIFT"):
        replay_stage_a2_axis_stability_package(forged)


def test_nested_r1_domain_laundering_fails_even_when_a2_digests_are_recomputed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:NESTED-DOMAIN"),
    )
    outer = json.loads(package.decode("utf-8"))
    nested = json.loads(
        base64.b64decode(outer["payload"]["left_stage_a_b64"]).decode("utf-8")
    )
    nested["payload"]["semantic_reference_domains"]["meaningful_delta_refs"].append(
        "STATUS:FORGED"
    )
    nested["payload"]["semantic_reference_domains_sha256"] = digest_material(
        nested["payload"]["semantic_reference_domains"]
    )
    nested_bytes = refresh_outer(nested)
    outer["payload"]["left_stage_a_b64"] = base64.b64encode(nested_bytes).decode("ascii")
    outer["payload"]["left_stage_a_sha256"] = hashlib.sha256(nested_bytes).hexdigest()
    outer["payload"]["left_semantic_domain_sha256"] = nested["payload"][
        "semantic_reference_domains_sha256"
    ]
    forged = refresh_outer(outer)
    with pytest.raises(ValueError, match="SEMANTIC_DOMAIN_MISMATCH"):
        replay_stage_a2_axis_stability_package(forged)


def test_a2_expected_observation_tamper_with_recomputed_outer_fails_closed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:OBS-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_observation"]["outcome"] = "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
    forged = refresh_outer(envelope)
    with pytest.raises(ValueError, match="OBSERVATION_MATERIALIZATION_MISMATCH"):
        replay_stage_a2_axis_stability_package(forged)


def test_a2_outer_tamper_without_digest_refresh_fails_closed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    package = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL", "A2R1:OUTER-TAMPER"),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["fixture"]["comparison_id"] = "FORGED"
    forged = canonical_json_bytes(envelope)
    with pytest.raises(ValueError, match="REPLAY_PACKAGE_TAMPERED"):
        replay_stage_a2_axis_stability_package(forged)


def test_export_is_byte_deterministic_and_replay_exact():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    fixture = comparison("IDENTICAL_CONTROL", "A2R1:DETERMINISM")
    first = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=fixture,
    )
    second = export_stage_a2_axis_stability_package(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=fixture,
    )
    assert first == second
    rebuilt = replay_stage_a2_axis_stability_package(first)
    assert rebuilt.outcome == "CORE_STABLE_UNDER_IDENTICAL_CONTROL"
    assert rebuilt.observation_id.startswith("I8D:A2:R1:")


def test_caller_cannot_supply_core_evidence():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    with pytest.raises(ValueError, match="CALLER_AUTHORED_CORE_EVIDENCE_FORBIDDEN"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=stage,
            right_stage_a_package=stage,
            fixture=comparison("IDENTICAL_CONTROL"),
            caller_core_evidence={"score": 999, "legal": True},
        )


def test_fixture_authority_escalation_fails_closed():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    forged = StageA2ComparisonFixture(
        comparison_id="A2R1:AUTHORITY-FORGE",
        comparison_kind="IDENTICAL_CONTROL",
        authority_class="CANONICAL_BRANCH_QUALITY_AUTHORITY",
    )
    with pytest.raises(ValueError, match="FIXTURE_AUTHORITY_ESCALATION"):
        evaluate_stage_a2_axis_stability(
            left_stage_a_package=stage,
            right_stage_a_package=stage,
            fixture=forged,
        )


def test_result_remains_evaluation_only_and_open_decisions_remain_deferred():
    _, source, _ = make_i5_pair()
    stage = stage_a("I5A_INFORMATION_OPPORTUNITY", source)
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage,
        right_stage_a_package=stage,
        fixture=comparison("IDENTICAL_CONTROL"),
    )
    assert result.authority_class == (
        "STAGE_A2_EVALUATION_OBSERVATION_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY"
    )
    assert result.deferred_decisions == (
        "OD-CLUE-QUALITY-001",
        "OD-PX-SCORING-001",
    )
    assert result.integrity_failures == ()
