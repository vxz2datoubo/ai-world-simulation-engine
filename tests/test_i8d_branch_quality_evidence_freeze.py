import copy
import json
from pathlib import Path

import pytest

import evals.i8d_branch_quality_evidence_freeze as b0


ROOT = Path(__file__).resolve().parents[1]


def load(path: str):
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def valid_instance():
    return copy.deepcopy(
        load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")["positive_cases"][0][
            "instance"
        ]
    )


def test_b0_hard_locks_are_explicit():
    assert b0.B0_INTERFACE_FREEZE_ONLY is True
    assert b0.B0_CANDIDATE_NOT_CANONICAL is True
    assert b0.STAGE_B1_CANONICAL_REGISTRATION_NOT_AUTHORIZED is True
    assert b0.NO_RUNTIME_IMPLEMENTATION is True
    assert b0.NO_BRANCH_QUALITY_SCORE is True
    assert b0.NO_PX_RANKING_IMPLEMENTATION is True
    assert b0.NO_WORLD_OR_KNOWLEDGE_MUTATION is True
    assert b0.NO_STORYLET_OR_ENCOUNTER_REALIZATION is True
    assert b0.NO_RETCON_RESURRECTION_OR_RECONVERGENCE is True
    assert b0.NO_LLM_DIRECTOR_RENDERER_PROVIDER_AUTHORITY is True
    assert b0.NO_ENGAGEMENT_RETENTION_OBJECTIVE is True
    assert b0.NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_freeze_candidate_validates_and_is_not_registered():
    receipt = b0.validate_freeze_candidate()
    assert receipt.parent_contract_version == "1.9.0-candidate"
    assert receipt.golden_suite_version == "1.7.0-candidate"
    assert receipt.canonical_registration_present is False
    assert receipt.b1_required is True
    assert len(receipt.binding_sha256) == 64
    assert len(receipt.fixture_sha256) == 64


def test_parent_registry_does_not_yet_grant_candidate_authority():
    parent = load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    assert b0.BINDING_ID not in parent["registered_contract_extensions"]
    assert parent["contract_extension_authority_rule"].startswith(
        "ONLY_EXTENSIONS_EXPLICITLY_REGISTERED"
    )


def test_current_parent_and_golden_versions_are_frozen_review_context():
    parent = load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    golden = load("evals/AF001-GOLDEN-SCENARIOS.json")
    assert parent["contract_version"] == b0.PARENT_VERSION
    assert parent["authority_graph_version"] == b0.PARENT_AUTHORITY_GRAPH
    assert golden["suite_version"] == b0.GOLDEN_VERSION
    assert golden["required_contract_version"] == b0.PARENT_VERSION


def test_authority_profile_has_no_canonical_data_authority():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    profile = binding["proposed_authority_profile"]
    assert profile["canonical_data_authority"] == ["NONE"]
    assert profile["contract_schema_steward"] == "AWRSE_AF_F_CONTRACT_STEWARD"
    assert profile["producer_or_assembler"] == ["AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER"]
    assert profile["downstream_consumer"] == ["NARRATIVE_OPPORTUNITY", "PX_RANKING", "AI_DIRECTOR"]
    assert profile["staging_authority"] == ["NONE"]


def test_portability_is_assessment_level_not_material_identity():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert binding["proposed_type"]["portable_integrity_invariant"] == (
        "ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL"
    )
    assert binding["promotion_gate"][
        "b1_must_preserve_assessment_level_not_material_identity_invariant"
    ] is True


def test_exact_three_portable_integrity_axes():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert tuple(
        binding["proposed_type"]["field_groups"]["portable_integrity_assessments"]
    ) == b0.INTEGRITY_AXES


def test_scarcity_is_structurally_separate_from_integrity():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    groups = binding["proposed_type"]["field_groups"]
    assert groups["dynamic_opportunity_state"] == ["opportunity_scarcity_evidence"]
    assert "opportunity_scarcity_evidence" not in groups["portable_integrity_assessments"]


def test_mechanism_axes_are_optional_source_scoped_set():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert set(binding["proposed_type"]["field_groups"]["mechanism_local_optional"]) == b0.MECHANISM_AXES
    assert "NOT_APPLICABLE" in binding["proposed_type"]["mechanism_assessment_vocabulary"]


def test_authored_metadata_is_quarantined_from_payload():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert set(binding["proposed_type"]["authored_design_metadata_excluded"]) == b0.AUTHORED_METADATA_EXCLUDED
    assert b0.AUTHORED_METADATA_EXCLUDED.isdisjoint(binding["proposed_type"]["fields"])


def test_validated_source_kinds_are_limited_to_stage_a2_corpus():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert set(binding["evidence_basis"]["validated_source_kinds"]) == b0.VALIDATED_SOURCE_KINDS


def test_b1_requires_version_advance_and_inverse_registration():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    gate = binding["promotion_gate"]
    assert gate["parent_contract_version_must_advance"] is True
    assert gate["golden_suite_version_must_advance"] is True
    assert gate["parent_inverse_registration_required"] is True
    assert gate["golden_inverse_registration_required"] is True
    assert gate["historical_parent_tuple_cannot_authorize_new_extension"] is True
    assert gate["child_self_declaration_confers_no_authority"] is True


def test_open_decisions_remain_open():
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert set(binding["open_decisions"]) == {"OD-CLUE-QUALITY-001", "OD-PX-SCORING-001"}
    assert all("OPEN" in value for value in binding["open_decisions"].values())


@pytest.mark.parametrize(
    "fragment",
    [
        "score",
        "weight",
        "rank",
        "selected",
        "legality",
        "legalize",
        "world_mutation",
        "event_commit",
        "realize_storylet",
        "realize_encounter",
        "engagement",
        "retention",
        "hidden_truth",
        "player_intent",
        "reconverge",
        "resurrect",
        "retcon",
    ],
)
def test_forbidden_capability_fragments_are_declared(fragment):
    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    assert fragment in binding["forbidden_capabilities"]["field_name_fragments"]


def test_all_positive_fixtures_validate():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    for case in fixtures["positive_cases"]:
        b0.validate_evidence_instance(case["instance"])


def test_all_negative_fixtures_fail_with_exact_expected_code():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    positive_by_id = {
        case["fixture_id"]: case["instance"] for case in fixtures["positive_cases"]
    }
    for case in fixtures["negative_cases"]:
        instance = b0.materialize_negative_fixture(
            case, positive_by_id=positive_by_id
        )
        with pytest.raises((ValueError, TypeError), match=f"^{case['expected_error']}$"):
            b0.validate_evidence_instance(instance)


def test_negative_fixture_recipes_are_declared_mutations_not_copied_instances():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    assert fixtures["mutation_fixture_schema"] == (
        "BASE_POSITIVE_INSTANCE_PLUS_DECLARED_PATH_MUTATIONS"
    )
    for case in fixtures["negative_cases"]:
        assert "instance" not in case
        assert case["base_fixture_ref"]
        assert case["mutations"]
        for mutation in case["mutations"]:
            assert mutation["op"] in {"set", "delete"}
            assert mutation["path"]


def test_negative_fixture_materialization_is_deterministic_and_non_mutating():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    positives = {case["fixture_id"]: case["instance"] for case in fixtures["positive_cases"]}
    case = fixtures["negative_cases"][0]
    baseline_before = copy.deepcopy(positives[case["base_fixture_ref"]])
    first = b0.materialize_negative_fixture(case, positive_by_id=positives)
    second = b0.materialize_negative_fixture(case, positive_by_id=positives)
    assert first == second
    assert positives[case["base_fixture_ref"]] == baseline_before
    assert first != baseline_before


def test_candidate_payload_has_no_numeric_values():
    instance = valid_instance()
    b0.validate_evidence_instance(instance)
    instance["mechanism_evidence"]["contrivance_repetition_risk"] = {
        "assessment": "RISK",
        "source_refs": ["NOVELTY:1"],
        "weight": 0.2,
    }
    with pytest.raises(ValueError, match="^B0_NUMERIC_SCALAR_FORBIDDEN$"):
        b0.validate_evidence_instance(instance)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("quality_score", "HIGH"),
        ("rank", "1"),
        ("selected_ref", "CANDIDATE:2"),
        ("legality_result", "LEGAL"),
        ("world_mutation", "PATCH"),
        ("event_commit", "EVENT:1"),
        ("realize_storylet", "S1"),
        ("realize_encounter", "E1"),
        ("engagement_score", "HIGH"),
        ("retention_score", "HIGH"),
        ("hidden_truth", "SECRET"),
        ("player_intent", "ACCEPT"),
    ],
)
def test_unknown_authority_or_optimizer_fields_fail_closed(field, value):
    instance = valid_instance()
    instance[field] = value
    with pytest.raises(ValueError, match="^B0_EVIDENCE_UNKNOWN_FIELDS$"):
        b0.validate_evidence_instance(instance)


@pytest.mark.parametrize("field", ["genre_theme_design_fit", "recoverable_thread_availability"])
def test_authored_metadata_injection_fails_closed(field):
    instance = valid_instance()
    instance[field] = "HIGH"
    with pytest.raises(ValueError, match="^B0_EVIDENCE_UNKNOWN_FIELDS$"):
        b0.validate_evidence_instance(instance)


def test_unvalidated_source_kind_fails_closed():
    instance = valid_instance()
    instance["source_kind"] = "I9_UNKNOWN"
    with pytest.raises(ValueError, match="^B0_SOURCE_KIND_NOT_EVIDENCE_VALIDATED$"):
        b0.validate_evidence_instance(instance)


@pytest.mark.parametrize("field", ["source_package_sha256", "source_i1_sha256"])
def test_provenance_hash_must_be_exact_sha256(field):
    instance = valid_instance()
    instance[field] = "abc"
    expected = "B0_SOURCE_PACKAGE_SHA256_INVALID" if field == "source_package_sha256" else "B0_SOURCE_I1_SHA256_INVALID"
    with pytest.raises(ValueError, match=f"^{expected}$"):
        b0.validate_evidence_instance(instance)


def test_authority_class_escalation_fails_closed():
    instance = valid_instance()
    instance["authority_class"] = "CANONICAL_WORLD_AUTHORITY"
    with pytest.raises(ValueError, match="^B0_AUTHORITY_CLASS_INVALID$"):
        b0.validate_evidence_instance(instance)


def test_mechanism_not_applicable_must_not_carry_refs():
    instance = valid_instance()
    instance["mechanism_evidence"] = {
        "contrivance_repetition_risk": {
            "assessment": "NOT_APPLICABLE",
            "source_refs": ["NOVELTY:1"],
        }
    }
    with pytest.raises(ValueError, match="^B0_MECHANISM_NOT_APPLICABLE_REFS_FORBIDDEN$"):
        b0.validate_evidence_instance(instance)


def test_mechanism_supported_requires_refs():
    instance = valid_instance()
    instance["mechanism_evidence"] = {
        "contrivance_repetition_risk": {"assessment": "SUPPORTED", "source_refs": []}
    }
    with pytest.raises(ValueError, match="^B0_MECHANISM_EVIDENCE_REFS_REQUIRED$"):
        b0.validate_evidence_instance(instance)


def test_unknown_mechanism_axis_fails_closed():
    instance = valid_instance()
    instance["mechanism_evidence"] = {
        "genre_theme_design_fit": {"assessment": "SUPPORTED", "source_refs": ["META:1"]}
    }
    with pytest.raises(ValueError, match="^B0_MECHANISM_AXIS_UNKNOWN$"):
        b0.validate_evidence_instance(instance)


def test_scarcity_vocabulary_is_absent_or_risk_only():
    instance = valid_instance()
    instance["opportunity_scarcity_evidence"]["assessment"] = "SUPPORTED"
    with pytest.raises(ValueError, match="^B0_SCARCITY_ASSESSMENT_INVALID$"):
        b0.validate_evidence_instance(instance)


def test_integrity_failure_is_evidence_not_a_legality_field():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    case = next(
        item for item in fixtures["positive_cases"]
        if item["fixture_id"] == "B0-INTEGRITY-FAILURE-EVIDENCE"
    )
    b0.validate_evidence_instance(case["instance"])
    assert case["instance"]["causal_world_integrity"]["assessment"] == "INTEGRITY_FAILURE"
    assert "legality_result" not in case["instance"]
    assert "world_mutation" not in case["instance"]


def test_not_applicable_is_not_bad_quality():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    case = next(
        item for item in fixtures["positive_cases"]
        if item["fixture_id"] == "B0-I8-NO-STORYLET"
    )
    b0.validate_evidence_instance(case["instance"])
    assert case["instance"]["mechanism_evidence"]["setup_promise_anchor_continuity"] == {
        "assessment": "NOT_APPLICABLE",
        "source_refs": [],
    }


def test_no_valid_opportunity_is_scarcity_not_integrity_failure():
    fixtures = load("evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json")
    case = next(
        item for item in fixtures["positive_cases"]
        if item["fixture_id"] == "B0-I5-NO-ROUTE"
    )
    b0.validate_evidence_instance(case["instance"])
    assert case["instance"]["opportunity_scarcity_evidence"]["assessment"] == "RISK"
    assert case["instance"]["causal_world_integrity"]["assessment"] == "SUPPORTED"
    assert case["instance"]["agency_legibility"]["assessment"] == "SUPPORTED"
    assert case["instance"]["knowledge_provenance_integrity"]["assessment"] == "SUPPORTED"


def test_freeze_artifacts_are_deterministic_json():
    for path in [
        "contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json",
        "evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json",
    ]:
        value = load(path)
        encoded1 = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        encoded2 = json.dumps(json.loads(encoded1), ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)
        assert encoded1 == encoded2
