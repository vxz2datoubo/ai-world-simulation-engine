import copy
import importlib.util
import json
import math
import subprocess
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC_PATH = ROOT / "evals" / "CAPABILITY-OPEN-DECISION-EVALS.json"
EVALUATOR_PATH = ROOT / "evals" / "capability_open_decision_eval.py"

module_spec = importlib.util.spec_from_file_location("capability_open_decision_eval", EVALUATOR_PATH)
cap_eval = importlib.util.module_from_spec(module_spec)
assert module_spec and module_spec.loader
module_spec.loader.exec_module(cap_eval)


def load_spec():
    return cap_eval.load_spec(SPEC_PATH)


def _walk_numbers(value):
    if isinstance(value, dict):
        for item in value.values():
            yield from _walk_numbers(item)
    elif isinstance(value, list):
        for item in value:
            yield from _walk_numbers(item)
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        yield float(value)


def _signature(receipt):
    return {key: value for key, value in receipt.items() if key != "subject_ref"}


def test_cap_eval_spec_is_evaluation_only_and_covers_released_open_decisions():
    spec = load_spec()
    assert spec["suite_id"] == "AWRSE-CAP-EVAL-001-OPEN-DECISION"
    assert spec["status"] == "EVALUATION_ONLY_NON_CANONICAL"
    assert spec["release_base"] == "15abb16b3892d69aeed14ee2327211d2af672500"
    assert set(spec["source_open_decision_refs"]) == {
        "OD-CAPABILITY-ATTR-001",
        "OD-CAPABILITY-MATH-001",
    }
    assert spec["all_candidates_non_canonical"] is True
    assert spec["provenance"]["network_dependency"] is False
    assert spec["provenance"]["model_dependency"] is False
    assert spec["provenance"]["wall_clock_dependency"] is False


def test_attribute_ablation_and_cross_domain_corpus_match_issue_24_surface():
    spec = load_spec()
    representations = {candidate["family"] for candidate in spec["representation_candidates"]}
    assert representations == {
        "ACTION_DEMAND_ONLY_PRIMITIVES",
        "SMALL_MUNDANE_CORE_VECTOR",
        "RICHER_GENRE_NEUTRAL_VECTOR",
    }
    families = {task["family"] for task in spec["task_corpus"]}
    assert families == {
        "RESTRAINT_ESCAPE_FORCE",
        "RESTRAINT_ESCAPE_TECHNIQUE",
        "RESTRAINT_ESCAPE_TOOL_ASSISTED",
        "LIFT_PUSH_PULL_FORCE",
        "SUSTAINED_EFFORT",
        "PRECISION_MANUAL",
        "COORDINATION_BALANCE",
        "PERCEPTION_OBSERVATION",
        "REASONING_PROBLEM_SOLVING",
    }
    assert all(candidate["status"] == "EVALUATION_CANDIDATE_ONLY" for candidate in spec["representation_candidates"])


def test_math_policy_ablation_covers_required_candidate_families():
    spec = load_spec()
    kinds = {candidate["kind"] for candidate in spec["math_policy_candidates"]}
    assert kinds == {
        "DETERMINISTIC_MARGIN",
        "ADDITIVE_MULTIPLICATIVE_STACK",
        "TAGGED_PRIORITY",
        "BOUNDED_SEEDED_STOCHASTIC",
    }
    assert all(candidate["status"] == "EVALUATION_CANDIDATE_ONLY" for candidate in spec["math_policy_candidates"])


def test_fighter_vs_scholar_same_restraint_is_method_specific_not_actor_name_bonus():
    spec = load_spec()
    for representation in [candidate["candidate_id"] for candidate in spec["representation_candidates"]]:
        fighter_force = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE")
        scholar_force = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "RESTRAINT_FORCE")
        fighter_tool = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_TOOL")
        scholar_tool = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
        fighter_technique = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_TECHNIQUE")
        scholar_technique = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "RESTRAINT_TECHNIQUE")

        assert fighter_force["margin"] > scholar_force["margin"]
        assert scholar_tool["margin"] > fighter_tool["margin"]
        assert (fighter_force["margin"], fighter_technique["margin"], fighter_tool["margin"]) != (
            scholar_force["margin"], scholar_technique["margin"], scholar_tool["margin"]
        )

    renamed = copy.deepcopy(spec)
    actor = next(actor for actor in renamed["actor_fixtures"] if actor["actor_id"] == "FIGHTER_A")
    actor["actor_id"] = "SOME_OTHER_ID"
    original = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "FIGHTER_A", "RESTRAINT_FORCE")
    changed_id = cap_eval.evaluate_case(renamed, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SOME_OTHER_ID", "RESTRAINT_FORCE")
    assert _signature(original) == _signature(changed_id)


def test_missing_real_tool_fails_before_stochastic_mapping_and_gets_no_bonus():
    spec = load_spec()
    mutated = copy.deepcopy(spec)
    scholar = next(actor for actor in mutated["actor_fixtures"] if actor["actor_id"] == "SCHOLAR_B")
    scholar["available_tools"] = []
    receipt = cap_eval.evaluate_case(
        mutated,
        "SMALL_CORE_V1",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
        "SCHOLAR_B",
        "RESTRAINT_TOOL",
    )
    assert receipt["feasibility"] == "HARD_FAIL_MISSING_REQUIRED_TOOL"
    assert receipt["effective_capability"] is None
    assert receipt["margin"] is None
    assert receipt["outcome_band"] == "INFEASIBLE"
    assert receipt["random_provenance_optional"] is None


def test_function_local_injury_changes_relevant_routes_not_reasoning():
    spec = load_spec()
    for representation in [candidate["candidate_id"] for candidate in spec["representation_candidates"]]:
        force_base = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE")
        force_hand = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE", ["HAND_ARM_IMPAIRMENT"])
        balance_base = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "BEAM_BALANCE")
        balance_leg = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "BEAM_BALANCE", ["LEG_IMPAIRMENT"])
        reasoning_base = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
        reasoning_hand = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM", ["HAND_ARM_IMPAIRMENT"])
        reasoning_leg = cap_eval.evaluate_case(spec, representation, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM", ["LEG_IMPAIRMENT"])

        assert force_hand["margin"] < force_base["margin"]
        assert balance_leg["margin"] < balance_base["margin"]
        assert reasoning_hand["margin"] == reasoning_base["margin"]
        assert reasoning_leg["margin"] == reasoning_base["margin"]


def test_irrelevant_attribute_perturbation_does_not_change_unrelated_reasoning():
    spec = load_spec()
    mutated = copy.deepcopy(spec)
    scholar = next(actor for actor in mutated["actor_fixtures"] if actor["actor_id"] == "SCHOLAR_B")
    scholar["representations"]["SMALL_CORE_V1"]["strength"] = 100
    before = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    after = cap_eval.evaluate_case(mutated, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    assert _signature(before) == _signature(after)


def test_stronger_relevant_capability_never_worsens_deterministic_margin():
    spec = load_spec()
    for policy in ("DETERMINISTIC_MARGIN_V1", "ADDITIVE_MULTIPLICATIVE_STACK_V1", "TAGGED_PRIORITY_V1"):
        margins = [
            cap_eval.evaluate_case(
                spec,
                "SMALL_CORE_V1",
                policy,
                "FIGHTER_A",
                "RESTRAINT_FORCE",
                dimension_offsets={"strength": offset},
            )["margin"]
            for offset in (-20, -10, 0, 10, 20)
        ]
        assert all(left <= right for left, right in zip(margins, margins[1:]))


def test_success_and_hazard_are_separate_axes():
    spec = load_spec()
    safe_reasoning = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    hazardous_trap = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "DISARM_TRAP")
    assert safe_reasoning["outcome_band"].startswith("SUCCESS")
    assert hazardous_trap["outcome_band"].startswith("SUCCESS")
    assert safe_reasoning["hazard_outcome"] != hazardous_trap["hazard_outcome"]


def test_seeded_stochastic_receipt_is_exactly_reproducible_without_free_reroll_input():
    spec = load_spec()
    first = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
    second = cap_eval.evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
    assert first == second
    receipt = first["random_provenance_optional"]
    assert receipt["seed_digest"]
    assert 0 <= receipt["roll_bucket_0_99"] <= 99
    assert receipt["calibration_status"] == "EVALUATION_BUCKET_NOT_SCIENTIFIC_PROBABILITY"


def test_full_evaluation_is_order_independent_and_does_not_mutate_input():
    spec = load_spec()
    pristine = copy.deepcopy(spec)
    result = cap_eval.run_evaluation(spec)
    assert spec == pristine
    assert result["adversarial_checks"]["evaluation_order_no_mutation"] is True
    assert result["adversarial_checks"]["candidate_order_independent"] is True
    assert result["adversarial_checks"]["all_checks_pass"] is True


def test_repeated_execution_is_canonical_structure_stable_and_fresh_process_stable():
    spec = load_spec()
    first = cap_eval.canonical_json(cap_eval.run_evaluation(spec))
    second = cap_eval.canonical_json(cap_eval.run_evaluation(spec))
    assert first == second

    process_a = subprocess.run([sys.executable, str(EVALUATOR_PATH)], check=True, capture_output=True, text=True).stdout
    process_b = subprocess.run([sys.executable, str(EVALUATOR_PATH)], check=True, capture_output=True, text=True).stdout
    assert process_a == process_b
    assert cap_eval.canonical_json(json.loads(process_a)) == first


def test_sensitivity_sweeps_cover_fighter_and_two_noncombat_families_without_reversal():
    spec = load_spec()
    result = cap_eval.run_evaluation(spec)
    sweeps = result["sensitivity_sweeps"]
    assert set(sweeps) == {"FIGHTER_FORCE_SWEEP", "MANUAL_SWEEP", "REASONING_SWEEP"}
    assert all(entry["reversal_detected"] is False for entry in sweeps.values())
    assert all(entry["dead_zone_detected"] is False for entry in sweeps.values())
    assert all(entry["parameter_grid_size"] >= 30 for entry in sweeps.values())


def test_malformed_or_unknown_candidate_inputs_fail_closed():
    spec = load_spec()
    with pytest.raises(cap_eval.EvaluationSpecError):
        cap_eval.evaluate_case(spec, "UNKNOWN_REPRESENTATION", "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE")

    malformed = copy.deepcopy(spec)
    malformed["task_corpus"][0]["representation_weights"]["SMALL_CORE_V1"]["nonexistent_dimension"] = 0.1
    with pytest.raises(cap_eval.EvaluationSpecError):
        cap_eval.validate_spec(malformed)


def test_no_candidate_output_is_labeled_canonical_accepted_frozen_or_production():
    spec = load_spec()
    result = cap_eval.run_evaluation(spec)
    labels = [entry["status"] for entry in result["candidate_dimensions"].values()]
    labels.extend(entry["status"] for entry in result["math_policy_checks"].values())
    for label in labels:
        assert label == "EVALUATION_CANDIDATE_ONLY"
        assert all(token not in label for token in ("CANONICAL", "ACCEPTED", "FROZEN", "PRODUCTION"))
    assert result["provenance"]["all_candidates_non_canonical"] is True


def test_report_separates_evidence_dimensions_and_keeps_open_decisions_open():
    spec = load_spec()
    result = cap_eval.run_evaluation(spec)
    assert set(spec["expected_report_fields"]) <= set(result)
    assert result["recommendation"]["status"] == "INSUFFICIENT_EVIDENCE_KEEP_OPEN"
    assert result["recommendation"]["open_decisions_resolved"] == []
    assert result["strongest_counterevidence"]
    assert result["provenance"]["runtime_semantics_changed"] is False
    assert result["provenance"]["open_decision_status_changed"] is False
    assert result["provenance"]["i2_runtime_implemented"] is False


def test_all_numeric_outputs_are_finite():
    result = cap_eval.run_evaluation(load_spec())
    assert all(math.isfinite(value) for value in _walk_numbers(result))
