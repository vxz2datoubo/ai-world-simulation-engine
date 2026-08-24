import copy
import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "evals" / "CAPABILITY-ROBUSTNESS-EVALS.json"
PREDECESSOR_PATH = ROOT / "evals" / "CAPABILITY-OPEN-DECISION-EVALS.json"
EVALUATOR_PATH = ROOT / "evals" / "capability_robustness_eval.py"
REPORT_PATH = ROOT / "docs" / "research" / "CAPABILITY-ROBUSTNESS-EVALUATION.md"

module_spec = importlib.util.spec_from_file_location("capability_robustness_eval", EVALUATOR_PATH)
cap2 = importlib.util.module_from_spec(module_spec)
assert module_spec and module_spec.loader
module_spec.loader.exec_module(cap2)


def load_inputs():
    return cap2.load_inputs(SPEC_PATH, PREDECESSOR_PATH)


def _task_semantics(task):
    return {
        key: copy.deepcopy(value)
        for key, value in task.items()
        if key not in {"task_id", "family", "method_class", "description"}
    }


def _rename_actor(spec, old, new):
    actor = next(row for row in spec["held_out_actors"] if row["actor_id"] == old)
    actor["actor_id"] = new
    for relation in spec["qualitative_relations"]:
        if relation["left_actor"] == old:
            relation["left_actor"] = new
        if relation["right_actor"] == old:
            relation["right_actor"] = new
    for probe in spec["collision_probes"]:
        if probe["actor_left"] == old:
            probe["actor_left"] = new
        if probe["actor_right"] == old:
            probe["actor_right"] = new
    for fixture in spec["genre_extension_fixtures"]:
        if fixture["actor_id"] == old:
            fixture["actor_id"] = new
    diagnostics = spec["math_diagnostic_cases"]
    for case in diagnostics["monotonic_cases"]:
        if case["actor_id"] == old:
            case["actor_id"] = new
    for key in ("reasoning_isolation_case", "relevant_tool_condition_case"):
        if diagnostics[key]["actor_id"] == old:
            diagnostics[key]["actor_id"] = new


def _rename_task(spec, old, new):
    task = next(row for row in spec["held_out_tasks"] if row["task_id"] == old)
    task["task_id"] = new
    for relation in spec["qualitative_relations"]:
        if relation["task_id"] == old:
            relation["task_id"] = new
    for probe in spec["collision_probes"]:
        if probe["task_id"] == old:
            probe["task_id"] = new
    for fixture in spec["genre_extension_fixtures"]:
        if fixture["base_task_id"] == old:
            fixture["base_task_id"] = new
    diagnostics = spec["math_diagnostic_cases"]
    for case in diagnostics["monotonic_cases"]:
        if case["task_id"] == old:
            case["task_id"] = new
    for key in ("reasoning_isolation_case", "relevant_tool_condition_case"):
        if diagnostics[key]["task_id"] == old:
            diagnostics[key]["task_id"] = new


def _rename_representation(spec, predecessor, old, new):
    candidate = next(
        row for row in predecessor["representation_candidates"] if row["candidate_id"] == old
    )
    candidate["candidate_id"] = new
    spec["representation_candidate_refs"] = [
        new if value == old else value for value in spec["representation_candidate_refs"]
    ]
    for actor in spec["held_out_actors"]:
        actor["representations"][new] = actor["representations"].pop(old)
    for task in spec["held_out_tasks"]:
        task["representation_weights"][new] = task["representation_weights"].pop(old)


def _rename_math(spec, predecessor, old, new):
    candidate = next(
        row for row in predecessor["math_policy_candidates"] if row["candidate_id"] == old
    )
    candidate["candidate_id"] = new
    spec["math_policy_candidate_refs"] = [
        new if value == old else value for value in spec["math_policy_candidate_refs"]
    ]


def test_spec_is_evaluation_only_and_governance_locked():
    spec, predecessor = load_inputs()
    assert spec["suite_id"] == "AWRSE-CAP-EVAL-002-ROBUSTNESS"
    assert spec["release_base"] == "32e2a1a830f0685af207275da0ad4849e7637ea4"
    assert spec["status"] == "EVALUATION_ONLY_NON_CANONICAL"
    assert spec["governance_locks"] == {
        "RUNTIME_SEMANTICS_UNCHANGED": True,
        "OPEN_DECISION_STATUS_UNCHANGED": True,
        "NO_I2_RUNTIME_IMPLEMENTED": True,
        "all_candidates_non_canonical": True,
    }
    assert all(
        row["status"] == "EVALUATION_CANDIDATE_ONLY"
        for row in predecessor["representation_candidates"]
    )
    assert all(
        row["status"] == "EVALUATION_CANDIDATE_ONLY"
        for row in predecessor["math_policy_candidates"]
    )


def test_true_heldout_corpus_is_distinct_from_predecessor_ids_and_semantics():
    spec, predecessor = load_inputs()
    heldout_ids = {task["task_id"] for task in spec["held_out_tasks"]}
    predecessor_ids = {task["task_id"] for task in predecessor["task_corpus"]}
    assert not heldout_ids.intersection(predecessor_ids)

    predecessor_semantics = {
        cap2.canonical_json(_task_semantics(task)) for task in predecessor["task_corpus"]
    }
    heldout_semantics = {
        cap2.canonical_json(_task_semantics(task)) for task in spec["held_out_tasks"]
    }
    assert not heldout_semantics.intersection(predecessor_semantics)
    assert {task["family"] for task in spec["held_out_tasks"]} == {
        "EXPLOSIVE_RAPID_FORCE",
        "WHOLE_BODY_CHANGE_OF_DIRECTION",
        "PRECISION_UNDER_TIME_PRESSURE",
        "MULTI_STAGE_TOOL_HARD_PREREQUISITE",
        "NOISY_AMBIGUOUS_OBSERVATION",
        "REASONING_IRRELEVANT_PHYSICAL_IMPAIRMENT",
        "SUSTAINED_COORDINATED_PHYSICAL",
        "ASSISTANCE_TEAMWORK_REPRESENTATION_PRESSURE",
    }


def test_missing_tool_is_explicit_feasibility_not_magic_margin_across_math_candidates():
    spec, predecessor = load_inputs()
    for rep_id in spec["representation_candidate_refs"]:
        for math_id in spec["math_policy_candidate_refs"]:
            receipt = cap2.evaluate_case(
                spec,
                predecessor,
                rep_id,
                math_id,
                "BURST_SPECIALIST",
                "VALVE_BYPASS_SEQUENCE",
            )
            assert receipt["feasibility"] == "HARD_FAIL_MISSING_REQUIRED_TOOL"
            assert receipt["margin"] is None
            assert receipt["margin_band"] == "INFEASIBLE"
            assert receipt["random_receipt"] is None
            assert receipt["sampled_outcome"] is None


def test_feasibility_dominance_relation_is_executable_and_never_subtracts_none():
    spec, predecessor = load_inputs()
    result = cap2.run_evaluation(spec, predecessor)
    for rep_id in spec["representation_candidate_refs"]:
        for math_id in spec["math_policy_candidate_refs"]:
            rows = {
                row["relation_id"]: row
                for row in result["qualitative_relation_evidence"][rep_id][math_id]["rows"]
            }
            relation = rows["TECH_TOOL_SEQUENCE"]
            assert relation["comparison_basis"] == "FEASIBILITY_DOMINANCE"
            assert relation["holds"] is True
            assert relation["margin_delta_left_minus_right"] is None
            assert relation["margin_comparison_performed"] is False
            assert relation["left_feasibility"] == "FEASIBLE"
            assert relation["right_feasibility"] == "HARD_FAIL_MISSING_REQUIRED_TOOL"


def test_robustness_separates_feasibility_dominance_from_margin_stability():
    spec, predecessor = load_inputs()
    robustness = cap2.run_evaluation(spec, predecessor)["parameter_robustness"]
    expected_total = (
        len(spec["parameter_perturbation_grid"]["actor_offsets"])
        * len(spec["parameter_perturbation_grid"]["actor_offsets"])
        * len(spec["parameter_perturbation_grid"]["difficulty_offsets"])
        * len(spec["parameter_perturbation_grid"]["weight_scale_factors"])
    )
    for rep_id in spec["representation_candidate_refs"]:
        for math_id in spec["math_policy_candidate_refs"]:
            rows = {
                row["relation_id"]: row
                for row in robustness[rep_id][math_id]["relations"]
            }
            feasibility_relation = rows["TECH_TOOL_SEQUENCE"]
            assert feasibility_relation["total"] == expected_total
            assert feasibility_relation["feasibility_dominance_count"] == expected_total
            assert feasibility_relation["margin_comparison_count"] == 0
            assert feasibility_relation["margin_band_stability_fraction"] is None
            assert feasibility_relation["preserved"] == expected_total

            margin_relation = rows["SCOUT_NOISY_OBSERVE"]
            assert margin_relation["total"] == expected_total
            assert margin_relation["margin_comparison_count"] == expected_total
            assert margin_relation["feasibility_dominance_count"] == 0
            assert margin_relation["margin_band_stability_fraction"] is not None


def test_collision_probes_are_non_vacuous_without_expected_winner_labels():
    spec, predecessor = load_inputs()
    assert '"expected_winner"' not in cap2.canonical_json(spec).lower()
    result = cap2.run_evaluation(spec, predecessor)["representation_collision_evidence"]
    assert result
    for probe in result.values():
        states = {row["distinguishes"] for row in probe["candidate_rows"].values()}
        assert states == {False, True}
        assert probe["distinguishing_candidates_observed"]
        assert probe["colliding_candidates_observed"]


def test_evaluator_source_has_no_fixture_or_candidate_id_bonus():
    source = EVALUATOR_PATH.read_text(encoding="utf-8").lower()
    for forbidden in (
        "burst_specialist",
        "steady_strong",
        "field_tech",
        "scout",
        "small_core_v1",
        "demand_primitives_v1",
        "rich_genre_neutral_v1",
        "deterministic_margin_v1",
        "additive_multiplicative_stack_v1",
        "tagged_priority_v1",
        "bounded_seeded_stochastic_v1",
        "expected_winner",
    ):
        assert forbidden not in source


def test_actor_task_representation_and_math_rename_preserve_semantic_receipt():
    spec, predecessor = load_inputs()
    baseline = cap2.evaluate_case(
        spec,
        predecessor,
        "SMALL_CORE_V1",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH",
        "VALVE_BYPASS_SEQUENCE",
    )

    actor_spec = copy.deepcopy(spec)
    _rename_actor(actor_spec, "FIELD_TECH", "ACTOR_RENAMED")
    actor_receipt = cap2.evaluate_case(
        actor_spec,
        predecessor,
        "SMALL_CORE_V1",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "ACTOR_RENAMED",
        "VALVE_BYPASS_SEQUENCE",
    )
    assert cap2.semantic_receipt_signature(actor_receipt) == cap2.semantic_receipt_signature(
        baseline
    )

    task_spec = copy.deepcopy(spec)
    _rename_task(task_spec, "VALVE_BYPASS_SEQUENCE", "TASK_RENAMED")
    task_receipt = cap2.evaluate_case(
        task_spec,
        predecessor,
        "SMALL_CORE_V1",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH",
        "TASK_RENAMED",
    )
    assert cap2.semantic_receipt_signature(task_receipt) == cap2.semantic_receipt_signature(
        baseline
    )

    rep_spec = copy.deepcopy(spec)
    rep_predecessor = copy.deepcopy(predecessor)
    _rename_representation(rep_spec, rep_predecessor, "SMALL_CORE_V1", "REP_RENAMED")
    rep_receipt = cap2.evaluate_case(
        rep_spec,
        rep_predecessor,
        "REP_RENAMED",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH",
        "VALVE_BYPASS_SEQUENCE",
    )
    assert cap2.semantic_receipt_signature(rep_receipt) == cap2.semantic_receipt_signature(
        baseline
    )

    math_spec = copy.deepcopy(spec)
    math_predecessor = copy.deepcopy(predecessor)
    _rename_math(
        math_spec,
        math_predecessor,
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "MATH_RENAMED",
    )
    math_receipt = cap2.evaluate_case(
        math_spec,
        math_predecessor,
        "SMALL_CORE_V1",
        "MATH_RENAMED",
        "FIELD_TECH",
        "VALVE_BYPASS_SEQUENCE",
    )
    assert cap2.semantic_receipt_signature(
        math_receipt
    ) == cap2.semantic_receipt_signature(baseline)


def test_candidate_and_task_order_do_not_change_full_structured_evidence():
    spec, predecessor = load_inputs()
    baseline = cap2.run_evaluation(spec, predecessor)

    shuffled = copy.deepcopy(spec)
    shuffled_predecessor = copy.deepcopy(predecessor)
    shuffled["representation_candidate_refs"].reverse()
    shuffled["math_policy_candidate_refs"].reverse()
    shuffled["held_out_tasks"].reverse()
    shuffled["held_out_actors"].reverse()
    shuffled["qualitative_relations"].reverse()
    shuffled["collision_probes"].reverse()
    shuffled["genre_extension_fixtures"].reverse()
    shuffled_predecessor["representation_candidates"].reverse()
    shuffled_predecessor["math_policy_candidates"].reverse()
    shuffled_predecessor["task_corpus"].reverse()

    assert cap2.canonical_json(
        cap2.run_evaluation(shuffled, shuffled_predecessor)
    ) == cap2.canonical_json(baseline)


def test_genre_extensions_do_not_pollute_mundane_core():
    spec, predecessor = load_inputs()
    result = cap2.run_evaluation(spec, predecessor)["genre_extension_pressure"]
    assert {row["genre"] for row in result.values()} == {"WUXIA", "XIANXIA", "SF"}
    for fixture in result.values():
        for row in fixture["rows"].values():
            assert row["mundane_ignores_extension_mutation"] is True
            assert row["extension_receipt"]["extension_applied"] is True
            assert row["extension_receipt"]["extension_detail"] is not None


def test_parameter_weight_and_actor_perturbation_paths_are_non_vacuous():
    spec, predecessor = load_inputs()
    base = cap2.evaluate_case(
        spec,
        predecessor,
        "RICH_GENRE_NEUTRAL_V1",
        "DETERMINISTIC_MARGIN_V1",
        "SCOUT",
        "CROWD_DODGE_CUT",
    )
    actor_shift = cap2.evaluate_case(
        spec,
        predecessor,
        "RICH_GENRE_NEUTRAL_V1",
        "DETERMINISTIC_MARGIN_V1",
        "SCOUT",
        "CROWD_DODGE_CUT",
        actor_offset=5,
    )
    difficulty_shift = cap2.evaluate_case(
        spec,
        predecessor,
        "RICH_GENRE_NEUTRAL_V1",
        "DETERMINISTIC_MARGIN_V1",
        "SCOUT",
        "CROWD_DODGE_CUT",
        difficulty_offset=5,
    )
    weight_shift = cap2.evaluate_case(
        spec,
        predecessor,
        "RICH_GENRE_NEUTRAL_V1",
        "DETERMINISTIC_MARGIN_V1",
        "SCOUT",
        "CROWD_DODGE_CUT",
        weight_scale_factor=1.1,
    )
    assert actor_shift["margin"] != base["margin"]
    assert difficulty_shift["margin"] != base["margin"]
    assert weight_shift["margin"] != base["margin"]


def test_math_policy_diagnostics_cover_monotonicity_locality_and_seed_replay():
    spec, predecessor = load_inputs()
    diagnostics = cap2.run_evaluation(spec, predecessor)["math_policy_diagnostics"]
    assert {row["kind"] for row in diagnostics.values()} == {
        "DETERMINISTIC_MARGIN",
        "ADDITIVE_MULTIPLICATIVE_STACK",
        "TAGGED_PRIORITY",
        "BOUNDED_SEEDED_STOCHASTIC",
    }
    assert all(row["monotonic_on_heldout_offsets"] for row in diagnostics.values())
    assert all(
        row["unrelated_condition_leaves_reasoning_margin_unchanged"]
        for row in diagnostics.values()
    )
    assert all(
        row["relevant_condition_changes_tool_margin"] for row in diagnostics.values()
    )
    stochastic = next(
        row
        for row in diagnostics.values()
        if row["kind"] == "BOUNDED_SEEDED_STOCHASTIC"
    )
    assert stochastic["stochastic_exact_replay_if_applicable"] is True
    assert stochastic["probability_calibration_claimed"] is False


def test_governed_recommendation_policy_is_consumed_and_fail_closed():
    spec, predecessor = load_inputs()
    result = cap2.run_evaluation(spec, predecessor)
    recommendations = result["recommendations"]
    evidence = recommendations["policy_evidence"]
    policy = spec["recommendation_policy"]

    assert evidence["math_policy_contract_consumed"] is True
    assert evidence["deterministic_baseline_ok"] is True
    assert evidence["stack_nonlocality_absent"] is False
    assert evidence["math_resolution_gate_satisfied"] is False

    if evidence["math_resolution_gate_satisfied"]:
        assert recommendations["MATH"].startswith("RECOMMEND_RESOLVE_MATH_")
    else:
        assert recommendations["MATH"] == "KEEP_MATH_OPEN"

    assert any(
        recommendations["ATTR"].startswith(prefix)
        for prefix in policy["attr_allowed_prefixes"]
    )
    assert any(
        recommendations["MATH"].startswith(prefix)
        for prefix in policy["math_allowed_prefixes"]
    )
    assert recommendations["resolution_authority"] is False
    assert recommendations["open_decisions_mutated"] is False

    malformed = copy.deepcopy(spec)
    del malformed["recommendation_policy"][
        "math_resolution_requires_deterministic_baseline_monotonic_and_stack_nonlocality_absent"
    ]
    with pytest.raises(cap2.RobustnessSpecError):
        cap2.run_evaluation(malformed, predecessor)


def test_report_is_bound_to_current_executable_recommendation_not_a_test_locked_winner():
    spec, predecessor = load_inputs()
    recommendations = cap2.run_evaluation(spec, predecessor)["recommendations"]
    report = REPORT_PATH.read_text(encoding="utf-8")

    assert f"ATTR recommendation class: `{recommendations['ATTR']}`" in report
    assert f"MATH recommendation class: `{recommendations['MATH']}`" in report
    assert "OPEN_DECISION_STATUS_UNCHANGED=true" in report
    assert "NO_I2_RUNTIME_IMPLEMENTED=true" in report

    source = Path(__file__).read_text(encoding="utf-8")
    assert (
        'attr_lines == ["ATTR recommendation class: `KEEP_ATTR_OPEN`"]'
        not in source
    )
    assert (
        "RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN_SUBSTRATE_WITH_SEPARATE_STOCHASTIC_TUNING"
        not in source
    )


def test_repeated_and_fresh_process_execution_is_exact():
    spec, predecessor = load_inputs()
    first = cap2.canonical_json(cap2.run_evaluation(spec, predecessor))
    second = cap2.canonical_json(cap2.run_evaluation(spec, predecessor))
    assert first == second

    process_a = subprocess.run(
        [sys.executable, str(EVALUATOR_PATH)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    process_b = subprocess.run(
        [sys.executable, str(EVALUATOR_PATH)],
        check=True,
        capture_output=True,
        text=True,
    ).stdout
    assert process_a == process_b
    parsed = json.loads(process_a)
    assert parsed["suite_id"] == "AWRSE-CAP-EVAL-002-ROBUSTNESS"


def test_no_candidate_authority_labels_leak():
    spec, predecessor = load_inputs()
    for rep_id in spec["representation_candidate_refs"]:
        for math_id in spec["math_policy_candidate_refs"]:
            receipt = cap2.evaluate_case(
                spec,
                predecessor,
                rep_id,
                math_id,
                "FIELD_TECH",
                "FOG_SIGNAL_DISCRIMINATION",
            )
            assert receipt["candidate_status"] == "EVALUATION_CANDIDATE_ONLY"
            assert receipt["candidate_status"] not in {
                "CANONICAL",
                "ACCEPTED",
                "FROZEN",
                "PRODUCTION",
                "I2_AUTHORIZED",
            }
