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

module_spec = importlib.util.spec_from_file_location("capability_robustness_eval", EVALUATOR_PATH)
cap2 = importlib.util.module_from_spec(module_spec)
assert module_spec and module_spec.loader
module_spec.loader.exec_module(cap2)


def load_inputs():
    return cap2.load_inputs(SPEC_PATH, PREDECESSOR_PATH)


def _task_semantics(task):
    return {k: copy.deepcopy(v) for k, v in task.items() if k not in {"task_id", "family", "method_class", "description"}}


def _rename_actor(spec, old, new):
    actor = next(item for item in spec["held_out_actors"] if item["actor_id"] == old)
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
    task = next(item for item in spec["held_out_tasks"] if item["task_id"] == old)
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
    candidate = next(item for item in predecessor["representation_candidates"] if item["candidate_id"] == old)
    candidate["candidate_id"] = new
    spec["representation_candidate_refs"] = [new if item == old else item for item in spec["representation_candidate_refs"]]
    for actor in spec["held_out_actors"]:
        actor["representations"][new] = actor["representations"].pop(old)
    for task in spec["held_out_tasks"]:
        task["representation_weights"][new] = task["representation_weights"].pop(old)


def _rename_math(spec, predecessor, old, new):
    candidate = next(item for item in predecessor["math_policy_candidates"] if item["candidate_id"] == old)
    candidate["candidate_id"] = new
    spec["math_policy_candidate_refs"] = [new if item == old else item for item in spec["math_policy_candidate_refs"]]


def test_spec_is_evaluation_only_and_keeps_governance_locks():
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
    assert all(item["status"] == "EVALUATION_CANDIDATE_ONLY" for item in predecessor["representation_candidates"])
    assert all(item["status"] == "EVALUATION_CANDIDATE_ONLY" for item in predecessor["math_policy_candidates"])


def test_true_heldout_corpus_is_distinct_from_predecessor_ids_and_semantics():
    spec, predecessor = load_inputs()
    heldout_ids = {task["task_id"] for task in spec["held_out_tasks"]}
    predecessor_ids = {task["task_id"] for task in predecessor["task_corpus"]}
    assert not heldout_ids.intersection(predecessor_ids)
    predecessor_semantics = {cap2.canonical_json(_task_semantics(task)) for task in predecessor["task_corpus"]}
    heldout_semantics = {cap2.canonical_json(_task_semantics(task)) for task in spec["held_out_tasks"]}
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


def test_collision_probes_are_non_vacuous_and_not_expected_winner_labels():
    spec, predecessor = load_inputs()
    serialized = cap2.canonical_json(spec).lower()
    assert '"expected_winner"' not in serialized
    result = cap2.run_evaluation(spec, predecessor)["representation_collision_evidence"]
    assert result
    for probe in result.values():
        states = {row["distinguishes"] for row in probe["candidate_rows"].values()}
        assert states == {False, True}
        assert probe["distinguishing_candidates_observed"]
        assert probe["colliding_candidates_observed"]


def test_candidate_code_has_no_expected_winner_branch_or_fixture_name_bonus():
    source = EVALUATOR_PATH.read_text(encoding="utf-8").lower()
    assert "burst_specialist" not in source
    assert "steady_strong" not in source
    assert "field_tech" not in source
    assert "scout" not in source
    for candidate_id in (
        "small_core_v1", "demand_primitives_v1", "rich_genre_neutral_v1",
        "deterministic_margin_v1", "additive_multiplicative_stack_v1",
        "tagged_priority_v1", "bounded_seeded_stochastic_v1",
    ):
        assert candidate_id not in source


def test_actor_task_representation_and_math_rename_do_not_change_semantic_resolution():
    spec, predecessor = load_inputs()
    baseline = cap2.evaluate_case(
        spec, predecessor, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH", "VALVE_BYPASS_SEQUENCE"
    )

    actor_spec = copy.deepcopy(spec)
    _rename_actor(actor_spec, "FIELD_TECH", "ACTOR_RENAMED")
    actor_receipt = cap2.evaluate_case(
        actor_spec, predecessor, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1",
        "ACTOR_RENAMED", "VALVE_BYPASS_SEQUENCE"
    )
    assert cap2.semantic_receipt_signature(actor_receipt) == cap2.semantic_receipt_signature(baseline)

    task_spec = copy.deepcopy(spec)
    _rename_task(task_spec, "VALVE_BYPASS_SEQUENCE", "TASK_RENAMED")
    task_receipt = cap2.evaluate_case(
        task_spec, predecessor, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH", "TASK_RENAMED"
    )
    assert cap2.semantic_receipt_signature(task_receipt) == cap2.semantic_receipt_signature(baseline)

    rep_spec = copy.deepcopy(spec)
    rep_pred = copy.deepcopy(predecessor)
    _rename_representation(rep_spec, rep_pred, "SMALL_CORE_V1", "REP_RENAMED")
    rep_receipt = cap2.evaluate_case(
        rep_spec, rep_pred, "REP_RENAMED", "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH", "VALVE_BYPASS_SEQUENCE"
    )
    assert cap2.semantic_receipt_signature(rep_receipt) == cap2.semantic_receipt_signature(baseline)

    math_spec = copy.deepcopy(spec)
    math_pred = copy.deepcopy(predecessor)
    _rename_math(math_spec, math_pred, "BOUNDED_SEEDED_STOCHASTIC_V1", "MATH_RENAMED")
    math_receipt = cap2.evaluate_case(
        math_spec, math_pred, "SMALL_CORE_V1", "MATH_RENAMED",
        "FIELD_TECH", "VALVE_BYPASS_SEQUENCE"
    )
    assert cap2.semantic_receipt_signature(math_receipt) == cap2.semantic_receipt_signature(baseline)


def test_candidate_and_task_order_do_not_change_full_structured_evidence():
    spec, predecessor = load_inputs()
    baseline = cap2.run_evaluation(spec, predecessor)
    shuffled = copy.deepcopy(spec)
    shuffled_pred = copy.deepcopy(predecessor)
    shuffled["representation_candidate_refs"].reverse()
    shuffled["math_policy_candidate_refs"].reverse()
    shuffled["held_out_tasks"].reverse()
    shuffled["held_out_actors"].reverse()
    shuffled["qualitative_relations"].reverse()
    shuffled["collision_probes"].reverse()
    shuffled["genre_extension_fixtures"].reverse()
    shuffled_pred["representation_candidates"].reverse()
    shuffled_pred["math_policy_candidates"].reverse()
    shuffled_pred["task_corpus"].reverse()
    assert cap2.canonical_json(cap2.run_evaluation(shuffled, shuffled_pred)) == cap2.canonical_json(baseline)


def test_every_heldout_task_covers_every_representation_candidate():
    spec, _ = load_inputs()
    expected = set(spec["representation_candidate_refs"])
    assert all(set(task["representation_weights"]) == expected for task in spec["held_out_tasks"])


def test_demand_primitives_are_actor_state_not_task_local_hidden_values():
    spec, _ = load_inputs()
    for task in spec["held_out_tasks"]:
        assert "representation_values" not in task
        assert "actor_values" not in task
        assert all(isinstance(value, (int, float)) for value in task["representation_weights"]["DEMAND_PRIMITIVES_V1"].values())
    assert all(actor["representations"]["DEMAND_PRIMITIVES_V1"] for actor in spec["held_out_actors"])


def test_genre_extensions_are_explicit_and_do_not_pollute_mundane_core():
    spec, predecessor = load_inputs()
    result = cap2.run_evaluation(spec, predecessor)["genre_extension_pressure"]
    assert {row["genre"] for row in result.values()} == {"WUXIA", "XIANXIA", "SF"}
    for fixture in result.values():
        for row in fixture["rows"].values():
            assert row["mundane_ignores_extension_mutation"] is True
            assert row["extension_receipt"]["extension_applied"] is True
            assert row["extension_receipt"]["extension_detail"] is not None


def test_parameter_and_weight_perturbation_paths_are_non_vacuous():
    spec, predecessor = load_inputs()
    base = cap2.evaluate_case(spec, predecessor, "RICH_GENRE_NEUTRAL_V1", "DETERMINISTIC_MARGIN_V1", "SCOUT", "CROWD_DODGE_CUT")
    actor_shift = cap2.evaluate_case(spec, predecessor, "RICH_GENRE_NEUTRAL_V1", "DETERMINISTIC_MARGIN_V1", "SCOUT", "CROWD_DODGE_CUT", actor_offset=5)
    difficulty_shift = cap2.evaluate_case(spec, predecessor, "RICH_GENRE_NEUTRAL_V1", "DETERMINISTIC_MARGIN_V1", "SCOUT", "CROWD_DODGE_CUT", difficulty_offset=5)
    weight_shift = cap2.evaluate_case(spec, predecessor, "RICH_GENRE_NEUTRAL_V1", "DETERMINISTIC_MARGIN_V1", "SCOUT", "CROWD_DODGE_CUT", weight_scale_factor=1.1)
    assert actor_shift["margin"] != base["margin"]
    assert difficulty_shift["margin"] != base["margin"]
    assert weight_shift["margin"] != base["margin"]
    robustness = cap2.run_evaluation(spec, predecessor)["parameter_robustness"]
    assert all(row["relations"] for rep in robustness.values() for row in rep.values())
    assert all(item["total"] == 81 for rep in robustness.values() for row in rep.values() for item in row["relations"])


def test_math_policy_comparison_covers_local_impairment_tool_skill_and_stochastic_replay():
    spec, predecessor = load_inputs()
    diagnostics = cap2.run_evaluation(spec, predecessor)["math_policy_diagnostics"]
    assert {row["kind"] for row in diagnostics.values()} == {
        "DETERMINISTIC_MARGIN", "ADDITIVE_MULTIPLICATIVE_STACK",
        "TAGGED_PRIORITY", "BOUNDED_SEEDED_STOCHASTIC",
    }
    assert all(row["monotonic_on_heldout_offsets"] for row in diagnostics.values())
    assert all(row["unrelated_condition_leaves_reasoning_margin_unchanged"] for row in diagnostics.values())
    assert all(row["relevant_condition_changes_tool_margin"] for row in diagnostics.values())
    stochastic = next(row for row in diagnostics.values() if row["kind"] == "BOUNDED_SEEDED_STOCHASTIC")
    assert stochastic["stochastic_exact_replay_if_applicable"] is True
    additive = next(row for row in diagnostics.values() if row["kind"] == "ADDITIVE_MULTIPLICATIVE_STACK")
    assert additive["excess_tool_condition_penalty_vs_deterministic"] > 0


def test_missing_tool_hard_fails_before_seeded_stochastic_mapping():
    spec, predecessor = load_inputs()
    mutated = copy.deepcopy(spec)
    actor = next(item for item in mutated["held_out_actors"] if item["actor_id"] == "FIELD_TECH")
    actor["available_tools"] = [tool for tool in actor["available_tools"] if tool != "MULTITOOL_KIT"]
    receipt = cap2.evaluate_case(
        mutated, predecessor, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1",
        "FIELD_TECH", "VALVE_BYPASS_SEQUENCE"
    )
    assert receipt["feasibility"] == "HARD_FAIL_MISSING_REQUIRED_TOOL"
    assert receipt["margin"] is None
    assert receipt["random_receipt"] is None
    assert receipt["sampled_outcome"] is None


def test_recommendations_are_exact_classes_and_not_resolution_authority():
    spec, predecessor = load_inputs()
    recommendation = cap2.run_evaluation(spec, predecessor)["recommendations"]
    assert recommendation["ATTR"] == "KEEP_ATTR_OPEN"
    assert recommendation["MATH"] == "RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN_SUBSTRATE_WITH_SEPARATE_STOCHASTIC_TUNING"
    assert recommendation["resolution_authority"] is False
    assert recommendation["open_decisions_mutated"] is False


def test_no_authority_status_leaks_into_candidate_receipts():
    spec, predecessor = load_inputs()
    for rep in spec["representation_candidate_refs"]:
        for math_id in spec["math_policy_candidate_refs"]:
            receipt = cap2.evaluate_case(spec, predecessor, rep, math_id, "FIELD_TECH", "FOG_SIGNAL_DISCRIMINATION")
            assert receipt["candidate_status"] == "EVALUATION_CANDIDATE_ONLY"
            assert receipt["candidate_status"] not in {"CANONICAL", "ACCEPTED", "FROZEN", "PRODUCTION", "I2_AUTHORIZED"}


def test_run_is_input_immutable_and_repeated_serialization_stable():
    spec, predecessor = load_inputs()
    spec_before = copy.deepcopy(spec)
    pred_before = copy.deepcopy(predecessor)
    first = cap2.canonical_json(cap2.run_evaluation(spec, predecessor))
    second = cap2.canonical_json(cap2.run_evaluation(spec, predecessor))
    assert first == second
    assert spec == spec_before
    assert predecessor == pred_before


def test_research_report_has_exactly_one_attr_and_math_recommendation_class():
    report = (ROOT / "docs" / "research" / "CAPABILITY-ROBUSTNESS-EVALUATION.md").read_text(encoding="utf-8")
    attr_lines = [line for line in report.splitlines() if line.startswith("ATTR recommendation class:")]
    math_lines = [line for line in report.splitlines() if line.startswith("MATH recommendation class:")]
    assert attr_lines == ["ATTR recommendation class: `KEEP_ATTR_OPEN`"]
    assert math_lines == [
        "MATH recommendation class: `RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN_SUBSTRATE_WITH_SEPARATE_STOCHASTIC_TUNING`"
    ]
    assert "OPEN_DECISION_STATUS_UNCHANGED=true" in report
    assert "NO_I2_RUNTIME_IMPLEMENTED=true" in report


def test_fresh_process_reproduction_is_exact():
    first = subprocess.run([sys.executable, str(EVALUATOR_PATH)], check=True, capture_output=True, text=True).stdout
    second = subprocess.run([sys.executable, str(EVALUATOR_PATH)], check=True, capture_output=True, text=True).stdout
    assert first == second
    parsed = json.loads(first)
    assert parsed["suite_id"] == "AWRSE-CAP-EVAL-002-ROBUSTNESS"
