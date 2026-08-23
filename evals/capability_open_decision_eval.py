"""Deterministic, evaluation-only capability OPEN_DECISION evidence generator.

This module is not runtime capability resolution. It consumes the governed
CAP-EVAL-001 spec and compares non-canonical candidates without network, LLM,
wall-clock, or hidden global state dependencies.
"""

from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping


SPEC_PATH = Path(__file__).with_name("CAPABILITY-OPEN-DECISION-EVALS.json")
ALLOWED_MATH_KINDS = {
    "DETERMINISTIC_MARGIN",
    "ADDITIVE_MULTIPLICATIVE_STACK",
    "TAGGED_PRIORITY",
    "BOUNDED_SEEDED_STOCHASTIC",
}


class EvaluationSpecError(ValueError):
    """Fail-closed error for malformed or unknown evaluation inputs."""


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def load_spec(path: Path | str = SPEC_PATH) -> dict[str, Any]:
    with Path(path).open("r", encoding="utf-8") as handle:
        spec = json.load(handle)
    validate_spec(spec)
    return spec


def _index(items: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    result: dict[str, Mapping[str, Any]] = {}
    for item in items:
        item_id = item.get(key)
        if not isinstance(item_id, str) or not item_id or item_id in result:
            raise EvaluationSpecError(f"invalid or duplicate {key}: {item_id!r}")
        result[item_id] = item
    return result


def _finite_number(value: Any, *, low: float | None = None, high: float | None = None) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    if not math.isfinite(float(value)):
        return False
    if low is not None and value < low:
        return False
    if high is not None and value > high:
        return False
    return True


def validate_spec(spec: Mapping[str, Any]) -> None:
    required = {
        "suite_id",
        "suite_version",
        "status",
        "release_base",
        "source_open_decision_refs",
        "all_candidates_non_canonical",
        "candidate_status_required",
        "provenance",
        "representation_candidates",
        "math_policy_candidates",
        "actor_fixtures",
        "task_corpus",
        "condition_probes",
        "sweep_definitions",
        "explicit_invariants",
        "expected_report_fields",
        "recommendation_policy",
    }
    missing = required - set(spec)
    if missing:
        raise EvaluationSpecError(f"missing spec fields: {sorted(missing)}")
    if spec["status"] != "EVALUATION_ONLY_NON_CANONICAL":
        raise EvaluationSpecError("suite must remain evaluation-only and non-canonical")
    if spec["all_candidates_non_canonical"] is not True:
        raise EvaluationSpecError("all candidates must be explicitly non-canonical")
    if set(spec["source_open_decision_refs"]) != {
        "OD-CAPABILITY-ATTR-001",
        "OD-CAPABILITY-MATH-001",
    }:
        raise EvaluationSpecError("unexpected capability OPEN_DECISION refs")

    candidate_status = spec["candidate_status_required"]
    if candidate_status != "EVALUATION_CANDIDATE_ONLY":
        raise EvaluationSpecError("unexpected candidate status policy")

    representations = _index(spec["representation_candidates"], "candidate_id")
    if len(representations) < 3:
        raise EvaluationSpecError("at least three representation candidates are required")
    required_families = {
        "ACTION_DEMAND_ONLY_PRIMITIVES",
        "SMALL_MUNDANE_CORE_VECTOR",
        "RICHER_GENRE_NEUTRAL_VECTOR",
    }
    if {candidate.get("family") for candidate in representations.values()} != required_families:
        raise EvaluationSpecError("representation option families do not match the released ablation")
    for candidate_id, candidate in representations.items():
        if candidate.get("status") != candidate_status:
            raise EvaluationSpecError(f"{candidate_id} has an authority-bearing status")
        dimensions = candidate.get("dimensions")
        if not isinstance(dimensions, dict) or not dimensions:
            raise EvaluationSpecError(f"{candidate_id} has no dimensions")
        for dimension, definition in dimensions.items():
            tags = definition.get("tags") if isinstance(definition, dict) else None
            if not isinstance(tags, list) or not tags or not all(isinstance(tag, str) for tag in tags):
                raise EvaluationSpecError(f"{candidate_id}.{dimension} has invalid tags")

    math_policies = _index(spec["math_policy_candidates"], "candidate_id")
    if len(math_policies) < 4:
        raise EvaluationSpecError("at least four math-policy candidates are required")
    for candidate_id, candidate in math_policies.items():
        if candidate.get("status") != candidate_status:
            raise EvaluationSpecError(f"{candidate_id} has an authority-bearing status")
        if candidate.get("kind") not in ALLOWED_MATH_KINDS:
            raise EvaluationSpecError(f"unknown math-policy kind for {candidate_id}")

    actors = _index(spec["actor_fixtures"], "actor_id")
    if {actor.get("role") for actor in actors.values()} != {"TRAINED_FIGHTER", "WEAK_SCHOLAR"}:
        raise EvaluationSpecError("FIGHTER_VS_SCHOLAR fixtures are incomplete")
    for actor_id, actor in actors.items():
        actor_representations = actor.get("representations", {})
        if set(actor_representations) != set(representations):
            raise EvaluationSpecError(f"{actor_id} does not cover every representation candidate")
        for representation_id, values in actor_representations.items():
            expected_dimensions = set(representations[representation_id]["dimensions"])
            if set(values) != expected_dimensions:
                raise EvaluationSpecError(f"{actor_id}.{representation_id} dimension mismatch")
            if not all(_finite_number(value, low=0, high=100) for value in values.values()):
                raise EvaluationSpecError(f"{actor_id}.{representation_id} has invalid values")
        if not all(_finite_number(value, low=0, high=100) for value in actor.get("skills", {}).values()):
            raise EvaluationSpecError(f"{actor_id} has invalid skill values")
        if not isinstance(actor.get("available_tools"), list):
            raise EvaluationSpecError(f"{actor_id} has invalid tool fixture")

    tasks = _index(spec["task_corpus"], "task_id")
    required_families_in_corpus = {
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
    if {task.get("family") for task in tasks.values()} != required_families_in_corpus:
        raise EvaluationSpecError("cross-domain task corpus is incomplete")
    for task_id, task in tasks.items():
        if not _finite_number(task.get("difficulty"), low=0, high=100):
            raise EvaluationSpecError(f"{task_id} has invalid difficulty")
        if not _finite_number(task.get("hazard"), low=0, high=100):
            raise EvaluationSpecError(f"{task_id} has invalid hazard")
        weights_by_representation = task.get("representation_weights", {})
        if set(weights_by_representation) != set(representations):
            raise EvaluationSpecError(f"{task_id} does not cover every representation")
        for representation_id, weights in weights_by_representation.items():
            if not weights or any(dimension not in representations[representation_id]["dimensions"] for dimension in weights):
                raise EvaluationSpecError(f"{task_id}.{representation_id} has unknown dimensions")
            if not all(_finite_number(weight, low=0) for weight in weights.values()) or sum(weights.values()) <= 0:
                raise EvaluationSpecError(f"{task_id}.{representation_id} has invalid weights")
        skill_weights = task.get("skill_weights", {})
        if not skill_weights or not all(_finite_number(weight, low=0) for weight in skill_weights.values()):
            raise EvaluationSpecError(f"{task_id} has invalid skill weights")
        prerequisite = task.get("hard_prerequisites", {})
        if set(prerequisite) - {"required_tool"}:
            raise EvaluationSpecError(f"{task_id} has an unknown hard prerequisite")

    conditions = _index(spec["condition_probes"], "condition_id")
    for condition_id, condition in conditions.items():
        if condition.get("status") != "EVALUATION_PROBE_ONLY":
            raise EvaluationSpecError(f"{condition_id} is not evaluation-only")
        if not condition.get("affected_tags"):
            raise EvaluationSpecError(f"{condition_id} has no affected tags")
        if not _finite_number(condition.get("multiplier"), low=0.01, high=1.0):
            raise EvaluationSpecError(f"{condition_id} has invalid multiplier")

    sweeps = _index(spec["sweep_definitions"], "sweep_id")
    if len(sweeps) < 3:
        raise EvaluationSpecError("fighter plus two non-combat sweeps are required")
    for sweep_id, sweep in sweeps.items():
        if sweep.get("task_id") not in tasks or sweep.get("actor_id") not in actors:
            raise EvaluationSpecError(f"{sweep_id} references unknown fixture")
        representation_id = sweep.get("representation_id")
        if representation_id not in representations:
            raise EvaluationSpecError(f"{sweep_id} references unknown representation")
        if sweep.get("math_policy_id") not in math_policies:
            raise EvaluationSpecError(f"{sweep_id} references unknown math policy")
        if sweep.get("relevant_dimension") not in representations[representation_id]["dimensions"]:
            raise EvaluationSpecError(f"{sweep_id} references unknown relevant dimension")
        for condition_set in sweep.get("conditions", []):
            if any(condition_id not in conditions for condition_id in condition_set):
                raise EvaluationSpecError(f"{sweep_id} references unknown condition")

    if len(spec["explicit_invariants"]) < 12:
        raise EvaluationSpecError("adversarial invariant set is incomplete")


def _indexes(spec: Mapping[str, Any]) -> tuple[dict[str, Any], ...]:
    return (
        dict(_index(spec["representation_candidates"], "candidate_id")),
        dict(_index(spec["math_policy_candidates"], "candidate_id")),
        dict(_index(spec["actor_fixtures"], "actor_id")),
        dict(_index(spec["task_corpus"], "task_id")),
        dict(_index(spec["condition_probes"], "condition_id")),
    )


def _weighted(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total = float(sum(weights.values()))
    if total <= 0:
        raise EvaluationSpecError("weight total must be positive")
    return sum(float(values[key]) * float(weight) for key, weight in weights.items()) / total


def _apply_conditions(
    representation: Mapping[str, Any],
    raw_values: Mapping[str, float],
    conditions: Iterable[Mapping[str, Any]],
) -> dict[str, float]:
    adjusted: dict[str, float] = {}
    condition_list = list(conditions)
    for dimension, raw_value in raw_values.items():
        factor = 1.0
        dimension_tags = set(representation["dimensions"][dimension]["tags"])
        for condition in condition_list:
            if dimension_tags.intersection(condition["affected_tags"]):
                factor *= float(condition["multiplier"])
        adjusted[dimension] = max(0.0, min(100.0, float(raw_value) * factor))
    return adjusted


def _outcome_band(margin: float) -> str:
    if margin >= 15:
        return "SUCCESS_CLEAR"
    if margin >= 0:
        return "SUCCESS_NARROW"
    if margin >= -12:
        return "PARTIAL_OR_FAIL_EDGE"
    return "FAIL"


def _hazard_band(score: float) -> str:
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    if score >= 15:
        return "LOW"
    return "MINIMAL"


def _stochastic_bucket(margin: float) -> tuple[str, int]:
    if margin <= -20:
        return "VERY_UNFAVORABLE", 15
    if margin <= -8:
        return "UNFAVORABLE", 30
    if margin <= 8:
        return "EVEN_BAND", 50
    if margin <= 20:
        return "FAVORABLE", 70
    return "VERY_FAVORABLE", 85


def _actor_input_fingerprint(actor: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "representations": actor["representations"],
        "skills": actor["skills"],
        "available_tools": sorted(actor["available_tools"]),
    }


def evaluate_case(
    spec: Mapping[str, Any],
    representation_id: str,
    math_policy_id: str,
    actor_id: str,
    task_id: str,
    condition_ids: Iterable[str] = (),
    *,
    dimension_offsets: Mapping[str, float] | None = None,
    difficulty_offset: float = 0.0,
) -> dict[str, Any]:
    """Evaluate one fixture without mutating the spec or any global state."""

    validate_spec(spec)
    representations, math_policies, actors, tasks, conditions = _indexes(spec)
    try:
        representation = representations[representation_id]
        math_policy = math_policies[math_policy_id]
        actor = actors[actor_id]
        task = tasks[task_id]
    except KeyError as exc:
        raise EvaluationSpecError(f"unknown evaluation reference: {exc.args[0]}") from exc

    normalized_condition_ids = tuple(sorted(condition_ids))
    try:
        active_conditions = [conditions[condition_id] for condition_id in normalized_condition_ids]
    except KeyError as exc:
        raise EvaluationSpecError(f"unknown condition reference: {exc.args[0]}") from exc

    raw_values = dict(actor["representations"][representation_id])
    for dimension, offset in (dimension_offsets or {}).items():
        if dimension not in raw_values or not _finite_number(offset):
            raise EvaluationSpecError(f"invalid dimension offset: {dimension}")
        raw_values[dimension] = max(0.0, min(100.0, float(raw_values[dimension]) + float(offset)))

    prerequisite = task["hard_prerequisites"]
    required_tool = prerequisite.get("required_tool")
    feasible = required_tool is None or required_tool in actor["available_tools"]
    difficulty = max(0.0, min(100.0, float(task["difficulty"]) + float(difficulty_offset)))

    receipt_base = {
        "subject_ref": actor_id,
        "representation_candidate_id": representation_id,
        "math_policy_candidate_id": math_policy_id,
        "task_id": task_id,
        "method_id": task["method_id"],
        "ruleset_version": spec["provenance"]["evaluation_ruleset_version"],
        "conditions": list(normalized_condition_ids),
        "difficulty_or_resistance": round(difficulty, 6),
        "candidate_status": spec["candidate_status_required"],
    }

    if not feasible:
        return {
            **receipt_base,
            "feasibility": "HARD_FAIL_MISSING_REQUIRED_TOOL",
            "effective_capability": None,
            "margin": None,
            "outcome_band": "INFEASIBLE",
            "hazard_outcome": _hazard_band(float(task["hazard"])),
            "random_provenance_optional": None,
        }

    adjusted_values = _apply_conditions(representation, raw_values, active_conditions)
    representation_weights = task["representation_weights"][representation_id]
    raw_attribute_score = _weighted(raw_values, representation_weights)
    adjusted_attribute_score = _weighted(adjusted_values, representation_weights)
    skill_score = _weighted(actor["skills"], task["skill_weights"])
    tool_bonus = 6.0 if required_tool is not None else 0.0
    condition_factor = adjusted_attribute_score / raw_attribute_score if raw_attribute_score else 1.0

    kind = math_policy["kind"]
    if kind == "DETERMINISTIC_MARGIN":
        effective = 0.75 * adjusted_attribute_score + 0.25 * skill_score + tool_bonus
    elif kind == "ADDITIVE_MULTIPLICATIVE_STACK":
        effective = (0.75 * raw_attribute_score + 0.25 * skill_score + tool_bonus) * condition_factor
    elif kind == "TAGGED_PRIORITY":
        bottleneck = min(adjusted_values[dimension] for dimension in representation_weights)
        effective = 0.55 * adjusted_attribute_score + 0.25 * skill_score + 0.20 * bottleneck + tool_bonus
    elif kind == "BOUNDED_SEEDED_STOCHASTIC":
        effective = 0.75 * adjusted_attribute_score + 0.25 * skill_score + tool_bonus
    else:
        raise EvaluationSpecError(f"unsupported math-policy kind: {kind}")

    effective = max(0.0, min(100.0, effective))
    margin = effective - difficulty
    condition_burden = max(0.0, 1.0 - condition_factor) * 20.0
    overexertion = max(0.0, -margin) * 0.15
    hazard_score = max(0.0, min(100.0, float(task["hazard"]) + condition_burden + overexertion))

    random_receipt = None
    if kind == "BOUNDED_SEEDED_STOCHASTIC":
        probability_band, threshold_percent = _stochastic_bucket(margin)
        seed_material = {
            "seed_salt": spec["provenance"]["seed_salt"],
            "representation_candidate_id": representation_id,
            "math_policy_candidate_id": math_policy_id,
            "task_id": task_id,
            "method_id": task["method_id"],
            "conditions": list(normalized_condition_ids),
            "actor_candidate_inputs": _actor_input_fingerprint({
                **actor,
                "representations": {**actor["representations"], representation_id: raw_values},
            }),
            "difficulty": difficulty,
        }
        digest = hashlib.sha256(canonical_json(seed_material).encode("utf-8")).hexdigest()
        roll_bucket = int(digest[:8], 16) % 100
        sampled_success = roll_bucket < threshold_percent
        outcome = "SAMPLED_SUCCESS" if sampled_success else "SAMPLED_FAIL"
        random_receipt = {
            "seed_digest": digest,
            "roll_bucket_0_99": roll_bucket,
            "mapping_band": probability_band,
            "threshold_bucket_percent": threshold_percent,
            "calibration_status": "EVALUATION_BUCKET_NOT_SCIENTIFIC_PROBABILITY",
        }
    else:
        outcome = _outcome_band(margin)

    return {
        **receipt_base,
        "feasibility": "FEASIBLE",
        "effective_capability": round(effective, 6),
        "margin": round(margin, 6),
        "outcome_band": outcome,
        "hazard_outcome": _hazard_band(hazard_score),
        "hazard_score_evaluation_only": round(hazard_score, 6),
        "random_provenance_optional": random_receipt,
    }


def _resolution_signature(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: value
        for key, value in receipt.items()
        if key not in {"subject_ref"}
    }


def _fighter_vs_scholar(spec: Mapping[str, Any]) -> dict[str, Any]:
    representations, math_policies, _, _, _ = _indexes(spec)
    output: dict[str, Any] = {}
    for representation_id in sorted(representations):
        output[representation_id] = {}
        for math_policy_id in sorted(math_policies):
            output[representation_id][math_policy_id] = {}
            for task_id in ("RESTRAINT_FORCE", "RESTRAINT_TECHNIQUE", "RESTRAINT_TOOL"):
                fighter = evaluate_case(spec, representation_id, math_policy_id, "FIGHTER_A", task_id)
                scholar = evaluate_case(spec, representation_id, math_policy_id, "SCHOLAR_B", task_id)
                output[representation_id][math_policy_id][task_id] = {
                    "fighter": fighter,
                    "scholar": scholar,
                    "margin_delta_fighter_minus_scholar": (
                        None if fighter["margin"] is None or scholar["margin"] is None
                        else round(float(fighter["margin"]) - float(scholar["margin"]), 6)
                    ),
                }
    return output


def _locality_probes(spec: Mapping[str, Any]) -> dict[str, Any]:
    representations, _, _, _, _ = _indexes(spec)
    output: dict[str, Any] = {}
    for representation_id in sorted(representations):
        reasoning_base = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
        reasoning_hand = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM", ["HAND_ARM_IMPAIRMENT"])
        reasoning_leg = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM", ["LEG_IMPAIRMENT"])
        force_base = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE")
        force_hand = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE", ["HAND_ARM_IMPAIRMENT"])
        balance_base = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "BEAM_BALANCE")
        balance_leg = evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "BEAM_BALANCE", ["LEG_IMPAIRMENT"])
        output[representation_id] = {
            "reasoning_unchanged_by_hand": reasoning_base["margin"] == reasoning_hand["margin"],
            "reasoning_unchanged_by_leg": reasoning_base["margin"] == reasoning_leg["margin"],
            "force_reduced_by_hand": float(force_hand["margin"]) < float(force_base["margin"]),
            "balance_reduced_by_leg": float(balance_leg["margin"]) < float(balance_base["margin"]),
            "receipts": {
                "reasoning_base": reasoning_base,
                "reasoning_hand": reasoning_hand,
                "reasoning_leg": reasoning_leg,
                "force_base": force_base,
                "force_hand": force_hand,
                "balance_base": balance_base,
                "balance_leg": balance_leg,
            },
        }
    return output


def _sensitivity_sweeps(spec: Mapping[str, Any]) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for sweep in sorted(spec["sweep_definitions"], key=lambda item: item["sweep_id"]):
        rows = []
        for condition_ids in sweep["conditions"]:
            for difficulty_offset in sweep["difficulty_offsets"]:
                margins = []
                for capability_offset in sweep["capability_offsets"]:
                    receipt = evaluate_case(
                        spec,
                        sweep["representation_id"],
                        sweep["math_policy_id"],
                        sweep["actor_id"],
                        sweep["task_id"],
                        condition_ids,
                        dimension_offsets={sweep["relevant_dimension"]: capability_offset},
                        difficulty_offset=difficulty_offset,
                    )
                    margins.append(float(receipt["margin"]))
                    rows.append({
                        "conditions": list(condition_ids),
                        "difficulty_offset": difficulty_offset,
                        "capability_offset": capability_offset,
                        "margin": receipt["margin"],
                        "outcome_band": receipt["outcome_band"],
                    })
                nondecreasing = all(left <= right for left, right in zip(margins, margins[1:]))
                if not nondecreasing:
                    raise EvaluationSpecError(f"sweep reversal detected in {sweep['sweep_id']}")
        sorted_rows = sorted(rows, key=lambda row: (tuple(row["conditions"]), row["difficulty_offset"], row["capability_offset"]))
        unique_margins = {row["margin"] for row in sorted_rows}
        output[sweep["sweep_id"]] = {
            "rows": sorted_rows,
            "reversal_detected": False,
            "dead_zone_detected": len(unique_margins) == 1,
            "parameter_grid_size": len(sorted_rows),
        }
    return output


def _candidate_dimensions(spec: Mapping[str, Any]) -> dict[str, Any]:
    representations, _, _, tasks, _ = _indexes(spec)
    fighter_matrix = _fighter_vs_scholar(spec)
    output: dict[str, Any] = {}
    for representation_id, candidate in sorted(representations.items()):
        demand_weight_count = sum(len(task["representation_weights"][representation_id]) for task in tasks.values())
        signatures = {
            canonical_json(task["representation_weights"][representation_id])
            for task in tasks.values()
        }
        deterministic = fighter_matrix[representation_id]["DETERMINISTIC_MARGIN_V1"]
        discrimination = sum(
            abs(float(entry["margin_delta_fighter_minus_scholar"])) >= 5
            for entry in deterministic.values()
        )
        output[representation_id] = {
            "status": candidate["status"],
            "family": candidate["family"],
            "base_dimension_count": len(candidate["dimensions"]),
            "task_weight_parameter_count": demand_weight_count,
            "distinct_task_method_signatures": len(signatures),
            "restraint_route_discrimination_count": discrimination,
            "fighter_force_advantage": deterministic["RESTRAINT_FORCE"]["margin_delta_fighter_minus_scholar"] > 0,
            "scholar_tool_advantage": deterministic["RESTRAINT_TOOL"]["margin_delta_fighter_minus_scholar"] < 0,
            "genre_extension_note": candidate["genre_extension_note"],
            "strongest_counterexample": candidate["strongest_counterexample"],
            "fake_precision_note": "No candidate receives a scientific-validity score; dimensions and burdens remain separate evidence fields.",
            "af001_boundary_compatibility": [
                "ActorBaseProfile/base_attribute_map_or_equivalent_candidate_inputs",
                "ActionDemandProfile/attribute_weights+skill_weights+hard_prerequisites+required_body_functions",
                "ActionResolutionReceipt/feasibility+effective_capability+difficulty_or_resistance+outcome_band+hazard_outcome+random_provenance_optional+ruleset_version",
            ],
        }
    return output


def _math_policy_checks(spec: Mapping[str, Any]) -> dict[str, Any]:
    _, math_policies, _, _, _ = _indexes(spec)
    output: dict[str, Any] = {}
    for policy_id, policy in sorted(math_policies.items()):
        low = evaluate_case(spec, "SMALL_CORE_V1", policy_id, "FIGHTER_A", "RESTRAINT_FORCE", dimension_offsets={"strength": -10})
        high = evaluate_case(spec, "SMALL_CORE_V1", policy_id, "FIGHTER_A", "RESTRAINT_FORCE", dimension_offsets={"strength": 10})
        repeated_a = evaluate_case(spec, "SMALL_CORE_V1", policy_id, "SCHOLAR_B", "DISARM_TRAP")
        repeated_b = evaluate_case(spec, "SMALL_CORE_V1", policy_id, "SCHOLAR_B", "DISARM_TRAP")
        output[policy_id] = {
            "kind": policy["kind"],
            "status": policy["status"],
            "relevant_capability_monotonic": (
                low["margin"] is not None and high["margin"] is not None and float(high["margin"]) >= float(low["margin"])
            ),
            "repeat_deterministic": canonical_json(repeated_a) == canonical_json(repeated_b),
            "hard_feasibility_precedes_resolution": True,
            "success_hazard_separate_axes": "hazard_outcome" in repeated_a and "outcome_band" in repeated_a,
            "strongest_counterexample": policy["strongest_counterexample"],
        }
    return output


def _core_results(spec: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "candidate_dimensions": _candidate_dimensions(spec),
        "fighter_vs_scholar": _fighter_vs_scholar(spec),
        "locality_probes": _locality_probes(spec),
        "math_policy_checks": _math_policy_checks(spec),
        "sensitivity_sweeps": _sensitivity_sweeps(spec),
    }


def _adversarial_checks(spec: Mapping[str, Any]) -> dict[str, bool]:
    checks: dict[str, bool] = {}

    renamed = copy.deepcopy(spec)
    fighter = next(actor for actor in renamed["actor_fixtures"] if actor["actor_id"] == "FIGHTER_A")
    fighter["actor_id"] = "RENAMED_SUBJECT"
    validate_spec(renamed)
    original_receipt = evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "FIGHTER_A", "RESTRAINT_FORCE")
    renamed_receipt = evaluate_case(renamed, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "RENAMED_SUBJECT", "RESTRAINT_FORCE")
    checks["actor_identity_not_bonus"] = _resolution_signature(original_receipt) == _resolution_signature(renamed_receipt)

    irrelevant = copy.deepcopy(spec)
    scholar = next(actor for actor in irrelevant["actor_fixtures"] if actor["actor_id"] == "SCHOLAR_B")
    scholar["representations"]["SMALL_CORE_V1"]["strength"] = 100
    before = evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    after = evaluate_case(irrelevant, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    checks["irrelevant_factor_isolated"] = _resolution_signature(before) == _resolution_signature(after)

    missing_tool = copy.deepcopy(spec)
    scholar_no_tool = next(actor for actor in missing_tool["actor_fixtures"] if actor["actor_id"] == "SCHOLAR_B")
    scholar_no_tool["available_tools"] = []
    impossible = evaluate_case(missing_tool, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
    checks["impossible_not_rescued_by_probability"] = (
        impossible["feasibility"].startswith("HARD_FAIL") and impossible["random_provenance_optional"] is None
    )
    checks["no_unowned_tool_bonus"] = impossible["effective_capability"] is None

    weak = evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE", dimension_offsets={"strength": -10})
    strong = evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE", dimension_offsets={"strength": 10})
    checks["stronger_relevant_capability_not_worse"] = float(strong["margin"]) >= float(weak["margin"])

    reasoning_base = evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM")
    reasoning_injured = evaluate_case(spec, "SMALL_CORE_V1", "DETERMINISTIC_MARGIN_V1", "SCHOLAR_B", "SOLVE_MECHANISM", ["HAND_ARM_IMPAIRMENT"])
    checks["local_injury_does_not_reduce_unrelated_cognition"] = reasoning_base["margin"] == reasoning_injured["margin"]

    sentinel_before = evaluate_case(spec, "RICH_GENRE_NEUTRAL_V1", "TAGGED_PRIORITY_V1", "SCHOLAR_B", "OBSERVE_TRACKS")
    for representation_id in sorted(candidate["candidate_id"] for candidate in spec["representation_candidates"]):
        evaluate_case(spec, representation_id, "DETERMINISTIC_MARGIN_V1", "FIGHTER_A", "RESTRAINT_FORCE")
    sentinel_after = evaluate_case(spec, "RICH_GENRE_NEUTRAL_V1", "TAGGED_PRIORITY_V1", "SCHOLAR_B", "OBSERVE_TRACKS")
    checks["evaluation_order_no_mutation"] = canonical_json(sentinel_before) == canonical_json(sentinel_after)

    reordered = copy.deepcopy(spec)
    reordered["representation_candidates"] = list(reversed(reordered["representation_candidates"]))
    reordered["math_policy_candidates"] = list(reversed(reordered["math_policy_candidates"]))
    checks["candidate_order_independent"] = canonical_json(_core_results(spec)) == canonical_json(_core_results(reordered))

    checks["repeated_structure_stable"] = canonical_json(_core_results(spec)) == canonical_json(_core_results(spec))

    stochastic_a = evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
    stochastic_b = evaluate_case(spec, "SMALL_CORE_V1", "BOUNDED_SEEDED_STOCHASTIC_V1", "SCHOLAR_B", "RESTRAINT_TOOL")
    checks["seeded_stochastic_reproducible"] = canonical_json(stochastic_a) == canonical_json(stochastic_b)

    malformed = copy.deepcopy(spec)
    malformed["sweep_definitions"][0]["representation_id"] = "DOES_NOT_EXIST"
    try:
        validate_spec(malformed)
        malformed_failed_closed = False
    except EvaluationSpecError:
        malformed_failed_closed = True
    checks["malformed_reference_fails_closed"] = malformed_failed_closed

    labels = []
    labels.extend(candidate["status"] for candidate in spec["representation_candidates"])
    labels.extend(candidate["status"] for candidate in spec["math_policy_candidates"])
    forbidden_authority_labels = {"CANONICAL", "ACCEPTED", "FROZEN", "PRODUCTION"}
    checks["candidate_labels_non_authoritative"] = all(
        not any(token in label for token in forbidden_authority_labels)
        for label in labels
    )

    checks["all_checks_pass"] = all(checks.values())
    return checks


def run_evaluation(spec: Mapping[str, Any]) -> dict[str, Any]:
    validate_spec(spec)
    core = _core_results(spec)
    adversarial = _adversarial_checks(spec)
    recommendation_policy = spec["recommendation_policy"]
    recommendation = {
        "status": recommendation_policy["default_status"],
        "open_decisions_resolved": [],
        "reason": recommendation_policy["reason"],
        "narrowing_observations": [
            "SMALL_CORE_V1 uses fewer durable base dimensions than RICH_GENRE_NEUTRAL_V1 while preserving the bounded corpus route discrimination.",
            "DEMAND_PRIMITIVES_V1 remains useful as a method-demand representation but risks becoming a hidden second actor sheet without durable evidence binding.",
            "All four math candidates remain evaluation candidates; deterministic margin is the simplest audit baseline, while seeded stochastic mapping remains reproducible but uncalibrated.",
            "Tagged bottleneck and whole-stack multiplicative policies retain explicit counterexamples that require broader calibration before any governance resolution."
        ],
    }
    strongest_counterevidence = [
        "The corpus and actor values are deliberately synthetic and bounded; no human playtest or production telemetry calibrates the candidate scales or weights.",
        "Genre extension pressure is represented only by structural metadata, not by executable wuxia/xianxia/science-fiction task corpora.",
        "Injury probes establish locality properties but do not validate medical, healing, fatigue, or canonical injury runtime semantics.",
        "A passing deterministic sensitivity grid cannot prove that any probability curve or parameter set feels fair or fun in production."
    ]
    result = {
        **core,
        "adversarial_checks": adversarial,
        "recommendation": recommendation,
        "strongest_counterevidence": strongest_counterevidence,
        "provenance": {
            "suite_id": spec["suite_id"],
            "suite_version": spec["suite_version"],
            "release_base": spec["release_base"],
            "evaluation_ruleset_version": spec["provenance"]["evaluation_ruleset_version"],
            "spec_sha256": hashlib.sha256(canonical_json(spec).encode("utf-8")).hexdigest(),
            "source_open_decision_refs": list(spec["source_open_decision_refs"]),
            "all_candidates_non_canonical": True,
            "runtime_semantics_changed": False,
            "open_decision_status_changed": False,
            "i2_runtime_implemented": False,
        },
    }
    missing_report_fields = set(spec["expected_report_fields"]) - set(result)
    if missing_report_fields:
        raise EvaluationSpecError(f"report fields missing: {sorted(missing_report_fields)}")
    if not adversarial["all_checks_pass"]:
        raise EvaluationSpecError("adversarial evaluation invariant failed")
    return result


def main() -> int:
    spec = load_spec()
    print(canonical_json(run_evaluation(spec)))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
