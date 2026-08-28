import base64
import hashlib
import json

import pytest

from awrse.model import thaw_value
import evals.i8d_branch_quality_evidence_experiment as v1
import evals.i8d_branch_quality_evidence_experiment_v2 as r1
from evals.i8d_branch_quality_evidence_experiment_v2 import (
    BranchEvidenceExperimentFixture,
    evaluate_branch_evidence_experiment,
    export_branch_evidence_experiment_package,
    replay_branch_evidence_experiment_package,
)
from tests.test_i8d_branch_quality_evidence_experiment import (
    AXES,
    I5_CARRIER,
    I7_DOOR,
    I8_PLAYER,
    canonical_json_bytes,
    fixture,
    make_i5_source,
    make_i7_source,
    make_i8_source,
    refresh_digest,
)


def material_from_source(source_kind, package):
    _, material = v1._strict_replay_source(source_kind, package)
    return material


def repaired_fixture(**overrides):
    return fixture(**overrides)


def test_r1_scope_locks_and_supersession_are_explicit():
    assert r1.I8D_STAGE_A_R1_SEMANTIC_REPAIR is True
    assert r1.HISTORICAL_STAGE_A_V1_RETAINED is True
    assert r1.HISTORICAL_STAGE_A_V1_NOT_CURRENT_FOR_DOWNSTREAM_EVIDENCE is True
    assert r1.NO_REINTERPRETATION_OF_V1_PACKAGES is True
    assert r1.NO_BRANCH_QUALITY_PRODUCTION_CONTRACT is True
    assert r1.NO_UNIVERSAL_QUALITY_SCORE is True
    assert r1.NO_PX_RANKING_OR_WEIGHTS is True
    assert r1.NO_WORLD_OR_KNOWLEDGE_MUTATION is True
    assert r1.NO_STORYLET_OR_ENCOUNTER_REALIZATION is True
    assert r1.NO_RETCON_RESURRECTION_OR_RECONVERGENCE is True
    assert r1.NO_LLM_DIRECTOR_RENDERER_AUTHORITY is True
    assert r1.NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE is True
    assert r1.HISTORICAL_V1_PACKAGE_SCHEMA == "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-1"
    assert r1.REPAIRED_PACKAGE_SCHEMA == "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-2"


def test_r1_repair_guard_keeps_same_nonauthority_governance():
    assert r1._load_repair_guard() == (
        "AWRSE-AF001-LIVING-STORY-CONTRACTS",
        "1.9.0-candidate",
        "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
    )


# ---------------- I5 field-specific semantic domain ----------------


def test_r1_i5_source_event_is_valid_meaningful_delta():
    _, _, source, package = make_i5_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I5-VALID-SOURCE-EVENT",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert axes["meaningful_state_information_relationship_delta"]["assessment"] == "SUPPORTED"
    assert axes["meaningful_state_information_relationship_delta"]["evidence_refs"] == [source.event_id]


@pytest.mark.parametrize(
    "bad_ref",
    [
        "WORLD-I8D-I5",
        "SHADOW_ENCOUNTER_CANDIDATE",
        I5_CARRIER,
        "BOUNDED_REFERENCE_FIXTURE_ONLY_NOT_CANONICAL_WORLD_EVIDENCE",
    ],
)
def test_r1_i5_unrelated_recursive_strings_cannot_mint_meaningful_delta(bad_ref):
    _, _, _, package = make_i5_source()
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I5A_INFORMATION_OPPORTUNITY",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I5-REJECT-UNRELATED",
                meaningful_delta_refs=(bad_ref,),
            ),
        )


def test_r1_i5_source_event_cannot_cross_mint_repetition_identity():
    _, _, source, package = make_i5_source()
    with pytest.raises(
        ValueError, match="I8D_R1_REPETITION_KEY_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I5A_INFORMATION_OPPORTUNITY",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I5-EVENT-NOT-REPETITION",
                repetition_key=source.event_id,
                prior_occurrence_count=1,
            ),
        )


def test_r1_i5_explicit_information_identity_can_be_repetition_key():
    _, _, _, package = make_i5_source()
    source_material = material_from_source("I5A_INFORMATION_OPPORTUNITY", package)
    info_id = source_material["information_packet"]["info_id"]
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I5-INFO-IDENTITY",
            repetition_key=info_id,
            prior_occurrence_count=2,
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert axes["contrivance_repetition_risk"]["assessment"] == "RISK"
    assert axes["contrivance_repetition_risk"]["evidence_refs"] == [info_id]


# ---------------- I7 field-specific semantic domain ----------------


def test_r1_i7_source_event_and_persistent_delta_are_meaningful_facts():
    _, _, source, _, package = make_i7_source()
    source_material = material_from_source("I7A_WORLD_ECHO", package)
    persistent_delta = next(
        ref for ref in source_material["canonical_fact_refs"] if ":damage_state=" in ref
    )
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I7-FACTS",
            meaningful_delta_refs=(source.event_id, persistent_delta),
        ),
    )
    axis = thaw_value(result.axis_evidence)[
        "meaningful_state_information_relationship_delta"
    ]
    assert axis["assessment"] == "SUPPORTED"
    assert set(axis["evidence_refs"]) == {source.event_id, persistent_delta}


def test_r1_i7_only_explicit_novelty_key_mints_repetition():
    _, _, _, novelty_key, package = make_i7_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I7-NOVELTY",
            repetition_key=novelty_key,
            prior_occurrence_count=3,
        ),
    )
    axis = thaw_value(result.axis_evidence)["contrivance_repetition_risk"]
    assert axis["assessment"] == "RISK"
    assert axis["evidence_refs"] == [novelty_key]


@pytest.mark.parametrize(
    "bad_ref",
    [
        "WORLD-I8D-I7",
        I7_DOOR,
        "PRIVATE_WORLD_ECHO_READY",
    ],
)
def test_r1_i7_world_target_and_status_cannot_mint_delta(bad_ref):
    _, _, _, _, package = make_i7_source()
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I7A_WORLD_ECHO",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I7-REJECT-DELTA",
                meaningful_delta_refs=(bad_ref,),
            ),
        )


def test_r1_i7_source_action_id_is_not_meaningful_delta_or_repetition():
    _, _, _, _, package = make_i7_source()
    source_material = material_from_source("I7A_WORLD_ECHO", package)
    action_id = source_material["source_action_id"]
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I7A_WORLD_ECHO",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I7-ACTION-NOT-DELTA",
                meaningful_delta_refs=(action_id,),
            ),
        )
    with pytest.raises(
        ValueError, match="I8D_R1_REPETITION_KEY_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I7A_WORLD_ECHO",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I7-ACTION-NOT-REPEAT",
                repetition_key=action_id,
                prior_occurrence_count=1,
            ),
        )


def test_r1_i7_novelty_key_cannot_cross_mint_meaningful_delta():
    _, _, _, novelty_key, package = make_i7_source()
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I7A_WORLD_ECHO",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I7-NOVELTY-NOT-DELTA",
                meaningful_delta_refs=(novelty_key,),
            ),
        )


# ---------------- I8 Storylet semantic domain and consistency ----------------


def test_r1_i8_typed_knowledge_fact_is_valid_meaningful_delta_and_axis_materializes_it():
    _, _, damage, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I8-DAMAGE",
            meaningful_delta_refs=(damage.event_id,),
            recoverable_thread_refs=(),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.source_status == "STORYLET_ELIGIBLE"
    assert result.diagnostic_class == "ROBUST_BRANCH_EVIDENCE"
    assert axes["meaningful_state_information_relationship_delta"] == {
        "assessment": "SUPPORTED",
        "evidence_refs": [damage.event_id],
        "interpretation": (
            "TYPED_STORYLET_EVENT_OR_KNOWLEDGE_FACT_DELTA_IS_VISIBLE_"
            "WITHOUT_REALIZATION_OR_FORCED_PAYOFF"
        ),
    }


@pytest.mark.parametrize(
    "bad_ref",
    [
        "STORYLET:I8D-PROMISE-CALLBACK",
        I8_PLAYER,
        "STORYLET_ELIGIBLE",
        "ALL_AUTHORED_PRECONDITIONS_REVALIDATED_FROM_CANONICAL_EVIDENCE",
    ],
)
def test_r1_i8_identity_actor_status_reason_cannot_mint_meaningful_delta(bad_ref):
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I8-REJECT-NONFACT",
                meaningful_delta_refs=(bad_ref,),
            ),
        )


def test_r1_i8_storylet_identity_is_repetition_only_not_delta():
    _, _, _, _, _, package = make_i8_source()
    storylet_id = "STORYLET:I8D-PROMISE-CALLBACK"
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I8-STORYLET-REPEAT",
            repetition_key=storylet_id,
            prior_occurrence_count=2,
        ),
    )
    assert thaw_value(result.axis_evidence)["contrivance_repetition_risk"][
        "evidence_refs"
    ] == [storylet_id]
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I8-STORYLET-NOT-DELTA",
                meaningful_delta_refs=(storylet_id,),
            ),
        )


def test_r1_i8_event_fact_cannot_cross_mint_repetition_identity():
    _, _, damage, _, _, package = make_i8_source()
    with pytest.raises(
        ValueError, match="I8D_R1_REPETITION_KEY_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I8-EVENT-NOT-REPEAT",
                repetition_key=damage.event_id,
                prior_occurrence_count=1,
            ),
        )


def test_r1_i8_thin_but_legal_stays_thin_without_semantic_delta():
    _, _, _, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I8-THIN",
            authored_design_fit="THIN",
            meaningful_delta_refs=(),
            recoverable_thread_refs=(),
        ),
    )
    axes = thaw_value(result.axis_evidence)
    assert result.diagnostic_class == "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
    assert axes["meaningful_state_information_relationship_delta"][
        "assessment"
    ] == "NOT_APPLICABLE"


def test_r1_i8_no_valid_storylet_cannot_become_robust_from_authored_metadata():
    _, _, _, _, _, package = make_i8_source(authored_route_broken=True)
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I8-NO-WELD",
            authored_design_fit="SUPPORTED",
            recoverable_thread_refs=("AUTHORED_THREAD:VERY_DESIRABLE",),
        ),
    )
    assert result.source_status == "NO_VALID_STORYLET"
    assert result.diagnostic_class == "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"


def test_r1_i8_callback_identity_is_repetition_domain_only():
    _, _, _, _, _, package = make_i8_source()
    source_material = material_from_source("I8C_STORYLET", package)
    callback = source_material["source_callback_concept_id"]
    assert callback
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-I8-CALLBACK-REPEAT",
            repetition_key=callback,
            prior_occurrence_count=1,
        ),
    )
    assert thaw_value(result.axis_evidence)["contrivance_repetition_risk"][
        "evidence_refs"
    ] == [callback]
    with pytest.raises(
        ValueError, match="I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=repaired_fixture(
                fixture_id="R1-I8-CALLBACK-NOT-DELTA",
                meaningful_delta_refs=(callback,),
            ),
        )


# ---------------- source-domain shape / quarantine ----------------


def test_r1_semantic_domains_exclude_recursive_noise_for_all_three_sources():
    _, _, _, i5_package = make_i5_source()
    _, _, _, _, i7_package = make_i7_source()
    _, _, _, _, _, i8_package = make_i8_source()

    i5 = r1._semantic_reference_domains(
        "I5A_INFORMATION_OPPORTUNITY",
        material_from_source("I5A_INFORMATION_OPPORTUNITY", i5_package),
    )
    i7 = r1._semantic_reference_domains(
        "I7A_WORLD_ECHO",
        material_from_source("I7A_WORLD_ECHO", i7_package),
    )
    i8 = r1._semantic_reference_domains(
        "I8C_STORYLET",
        material_from_source("I8C_STORYLET", i8_package),
    )

    assert "WORLD-I8D-I5" not in i5["meaningful_delta_refs"]
    assert I5_CARRIER not in i5["meaningful_delta_refs"]
    assert "WORLD-I8D-I7" not in i7["meaningful_delta_refs"]
    assert I7_DOOR not in i7["repetition_keys"]
    assert I8_PLAYER not in i8["meaningful_delta_refs"]
    assert "STORYLET:I8D-PROMISE-CALLBACK" not in i8["meaningful_delta_refs"]
    assert "STORYLET:I8D-PROMISE-CALLBACK" in i8["repetition_keys"]


def test_r1_result_keeps_exact_ten_axes_and_no_score_rank_fields():
    _, _, damage, _, _, package = make_i8_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I8C_STORYLET",
        source_package=package,
        fixture=repaired_fixture(
            fixture_id="R1-TEN-AXES",
            meaningful_delta_refs=(damage.event_id,),
        ),
    )
    material = v1._result_material(result)
    assert set(thaw_value(result.axis_evidence)) == AXES
    forbidden = ("score", "rank", "engagement", "retention")
    assert not [
        key
        for key in material
        if any(token in key.lower() for token in forbidden)
    ]


def test_r1_caller_cannot_supply_quality_authority():
    _, _, _, _, _, package = make_i8_source()
    with pytest.raises(
        ValueError, match="I8D_R1_CALLER_AUTHORED_BRANCH_QUALITY_EVIDENCE_FORBIDDEN"
    ):
        evaluate_branch_evidence_experiment(
            source_kind="I8C_STORYLET",
            source_package=package,
            fixture=repaired_fixture(),
            caller_branch_quality_evidence={"legal": True, "score": 999},
        )


# ---------------- migration / replay / anti-laundering ----------------


def test_r1_export_is_deterministic_and_binds_semantic_domains():
    _, _, source, _, package = make_i7_source()
    fx = repaired_fixture(
        fixture_id="R1-EXPORT",
        meaningful_delta_refs=(source.event_id,),
    )
    first = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=fx,
    )
    second = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=package,
        fixture=fx,
    )
    assert first == second
    envelope = json.loads(first.decode("utf-8"))
    payload = envelope["payload"]
    assert payload["package_schema"] == r1.REPAIRED_PACKAGE_SCHEMA
    assert payload["supersedes_schema"] == r1.HISTORICAL_V1_PACKAGE_SCHEMA
    assert payload["semantic_reference_domains_sha256"] == r1._sha256(
        payload["semantic_reference_domains"]
    )
    rebuilt = replay_branch_evidence_experiment_package(first)
    assert rebuilt.source_package_sha256 == hashlib.sha256(package).hexdigest()


def test_r1_historical_v1_package_cannot_be_replayed_as_repaired_v2():
    _, _, source, _, source_package = make_i7_source()
    old = v1.export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-OLD-PACKAGE",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    with pytest.raises(ValueError, match="I8D_R1_REPLAY_REPAIRED_SCHEMA_REQUIRED"):
        replay_branch_evidence_experiment_package(old)


def test_r1_outer_tamper_fails_closed():
    _, _, source, _, source_package = make_i7_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-OUTER-TAMPER",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_result"]["diagnostic_class"] = "FORCED_BEST"
    forged = canonical_json_bytes(envelope)
    with pytest.raises(ValueError, match="I8D_R1_REPLAY_PACKAGE_TAMPERED"):
        replay_branch_evidence_experiment_package(forged)


def test_r1_recomputed_outer_digest_cannot_launder_expected_result():
    _, _, source, _, source_package = make_i7_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-EXPECTED-TAMPER",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["expected_result"]["diagnostic_class"] = "ROBUST_BY_FIAT"
    forged = refresh_digest(envelope)
    with pytest.raises(
        ValueError, match="I8D_R1_REPLAY_RESULT_MATERIALIZATION_MISMATCH"
    ):
        replay_branch_evidence_experiment_package(forged)


def test_r1_recomputed_outer_digest_cannot_launder_semantic_domain():
    _, _, source, _, source_package = make_i7_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-DOMAIN-TAMPER",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["semantic_reference_domains"]["meaningful_delta_refs"].append(
        "WORLD-I8D-I7"
    )
    envelope["payload"]["semantic_reference_domains_sha256"] = r1._sha256(
        envelope["payload"]["semantic_reference_domains"]
    )
    forged = refresh_digest(envelope)
    with pytest.raises(ValueError, match="I8D_R1_REPLAY_SEMANTIC_DOMAIN_MISMATCH"):
        replay_branch_evidence_experiment_package(forged)


def test_r1_nested_upstream_tamper_cannot_be_laundered():
    _, _, source, _, source_package = make_i7_source()
    package = export_branch_evidence_experiment_package(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-NESTED-TAMPER",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    envelope = json.loads(package.decode("utf-8"))
    nested = json.loads(
        base64.b64decode(envelope["payload"]["source_package_b64"]).decode("utf-8")
    )
    nested["payload"]["expected_reference"]["source_world_id"] = "WORLD:FORGED"
    nested_bytes = refresh_digest(nested)
    envelope["payload"]["source_package_b64"] = base64.b64encode(nested_bytes).decode(
        "ascii"
    )
    envelope["payload"]["source_package_sha256"] = hashlib.sha256(
        nested_bytes
    ).hexdigest()
    forged = refresh_digest(envelope)
    with pytest.raises(ValueError, match="MATERIALIZATION_MISMATCH"):
        replay_branch_evidence_experiment_package(forged)


def test_r1_exact_provenance_survives_repair():
    _, _, source, _, source_package = make_i7_source()
    result = evaluate_branch_evidence_experiment(
        source_kind="I7A_WORLD_ECHO",
        source_package=source_package,
        fixture=repaired_fixture(
            fixture_id="R1-PROVENANCE",
            meaningful_delta_refs=(source.event_id,),
        ),
    )
    assert result.source_world_id == "WORLD-I8D-I7"
    assert result.source_baseline_version == "I8D-I7-BASELINE-v1"
    assert result.source_state_version > 0
    assert len(result.source_i1_sha256) == 64
    assert result.source_package_sha256 == hashlib.sha256(source_package).hexdigest()
    assert len(result.source_reference_sha256) == 64


def test_r1_upstream_integrity_failure_still_noncompensable():
    _, _, _, package = make_i5_source()
    envelope = json.loads(package.decode("utf-8"))
    envelope["payload"]["source_event_id"] = "EVENT:FORGED"
    forged = refresh_digest(envelope)
    result = evaluate_branch_evidence_experiment(
        source_kind="I5A_INFORMATION_OPPORTUNITY",
        source_package=forged,
        fixture=repaired_fixture(
            fixture_id="R1-INTEGRITY",
            authored_design_fit="SUPPORTED",
            recoverable_thread_refs=("AUTHORED_THREAD:DESIRABLE",),
        ),
    )
    assert result.diagnostic_class == "INTEGRITY_FAILURE_PRESENT"
    assert result.strengths == ()
    assert result.risks == ("UPSTREAM_INTEGRITY_FAILURE",)
