"""CAP-EVAL-002 held-out robustness evaluator. Evaluation-only, no runtime authority."""
from __future__ import annotations

import copy
import hashlib
import json
import math
from pathlib import Path
from typing import Any, Iterable, Mapping

HERE = Path(__file__).resolve().parent
SPEC_PATH = HERE / "CAPABILITY-ROBUSTNESS-EVALS.json"
PREDECESSOR_SPEC_PATH = HERE / "CAPABILITY-OPEN-DECISION-EVALS.json"
MATH_KINDS = {
    "DETERMINISTIC_MARGIN",
    "ADDITIVE_MULTIPLICATIVE_STACK",
    "TAGGED_PRIORITY",
    "BOUNDED_SEEDED_STOCHASTIC",
}


class RobustnessSpecError(ValueError):
    pass


def canonical_json(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def _hash(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


def _index(items: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    out: dict[str, Mapping[str, Any]] = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in out:
            raise RobustnessSpecError(f"invalid/duplicate {key}: {value!r}")
        out[value] = item
    return out


def _finite(value: Any, low: float = -math.inf, high: float = math.inf) -> bool:
    return (
        not isinstance(value, bool)
        and isinstance(value, (int, float))
        and math.isfinite(float(value))
        and low <= float(value) <= high
    )


def _drop(row: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {key: copy.deepcopy(value) for key, value in row.items() if key not in keys}


def _task_semantics(task: Mapping[str, Any]) -> dict[str, Any]:
    return _drop(task, "task_id", "family", "method_class", "description")


def _candidate_semantics(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return _drop(candidate, "candidate_id", "strongest_counterexample", "genre_extension_note")


def _maps(predecessor: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return (
        dict(_index(predecessor["representation_candidates"], "candidate_id")),
        dict(_index(predecessor["math_policy_candidates"], "candidate_id")),
    )


def _heldout(spec: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        dict(_index(spec["held_out_actors"], "actor_id")),
        dict(_index(spec["held_out_tasks"], "task_id")),
        dict(_index(spec["condition_probes"], "condition_id")),
    )


def _math_id(predecessor: Mapping[str, Any], kind: str) -> str:
    matches = [
        candidate_id
        for candidate_id, row in _maps(predecessor)[1].items()
        if row.get("kind") == kind
    ]
    if len(matches) != 1:
        raise RobustnessSpecError(f"math kind not unique: {kind}")
    return matches[0]


def load_inputs(
    spec_path: Path | str = SPEC_PATH,
    predecessor_path: Path | str = PREDECESSOR_SPEC_PATH,
) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    predecessor = json.loads(Path(predecessor_path).read_text(encoding="utf-8"))
    validate_inputs(spec, predecessor)
    return spec, predecessor


def validate_inputs(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> None:
    required = {
        "suite_id",
        "suite_version",
        "status",
        "release_base",
        "predecessor",
        "source_open_decision_refs",
        "candidate_status_required",
        "representation_candidate_refs",
        "math_policy_candidate_refs",
        "provenance",
        "held_out_corpus_declared_before_interpretation",
        "predecessor_task_ids",
        "held_out_actors",
        "held_out_tasks",
        "qualitative_relations",
        "collision_probes",
        "genre_extension_fixtures",
        "condition_probes",
        "parameter_perturbation_grid",
        "math_diagnostic_cases",
        "overfit_guards",
        "genre_core_pollution_guard",
        "recommendation_policy",
        "governance_locks",
    }
    missing = required - set(spec)
    if missing:
        raise RobustnessSpecError(f"missing fields: {sorted(missing)}")
    if spec["status"] != "EVALUATION_ONLY_NON_CANONICAL":
        raise RobustnessSpecError("suite must remain evaluation-only")
    if spec["release_base"] != "32e2a1a830f0685af207275da0ad4849e7637ea4":
        raise RobustnessSpecError("release base changed")
    if set(spec["source_open_decision_refs"]) != {
        "OD-CAPABILITY-ATTR-001",
        "OD-CAPABILITY-MATH-001",
    }:
        raise RobustnessSpecError("OPEN_DECISION refs changed")
    if spec["candidate_status_required"] != "EVALUATION_CANDIDATE_ONLY":
        raise RobustnessSpecError("candidate status changed")
    if spec["held_out_corpus_declared_before_interpretation"] is not True:
        raise RobustnessSpecError("held-out declaration guard changed")
    if spec["governance_locks"] != {
        "RUNTIME_SEMANTICS_UNCHANGED": True,
        "OPEN_DECISION_STATUS_UNCHANGED": True,
        "NO_I2_RUNTIME_IMPLEMENTED": True,
        "all_candidates_non_canonical": True,
    }:
        raise RobustnessSpecError("governance locks changed")

    predecessor_meta = spec["predecessor"]
    if predecessor_meta.get("accepted_head") != "6e665ca3f02795564119383f52f7643190997eec":
        raise RobustnessSpecError("predecessor accepted head changed")
    if predecessor_meta.get("merge_commit") != spec["release_base"]:
        raise RobustnessSpecError("predecessor merge commit changed")

    reps, maths = _maps(predecessor)
    if set(spec["representation_candidate_refs"]) != set(reps):
        raise RobustnessSpecError("representation registry mismatch")
    if set(spec["math_policy_candidate_refs"]) != set(maths):
        raise RobustnessSpecError("math registry mismatch")
    if any(
        row.get("status") != "EVALUATION_CANDIDATE_ONLY"
        for row in [*reps.values(), *maths.values()]
    ):
        raise RobustnessSpecError("candidate gained authority")
    if {row.get("kind") for row in maths.values()} != MATH_KINDS:
        raise RobustnessSpecError("math families changed")

    actors, tasks, conditions = _heldout(spec)
    required_families = {
        "EXPLOSIVE_RAPID_FORCE",
        "WHOLE_BODY_CHANGE_OF_DIRECTION",
        "PRECISION_UNDER_TIME_PRESSURE",
        "MULTI_STAGE_TOOL_HARD_PREREQUISITE",
        "NOISY_AMBIGUOUS_OBSERVATION",
        "REASONING_IRRELEVANT_PHYSICAL_IMPAIRMENT",
        "SUSTAINED_COORDINATED_PHYSICAL",
        "ASSISTANCE_TEAMWORK_REPRESENTATION_PRESSURE",
    }
    if len(tasks) < 8 or {task.get("family") for task in tasks.values()} != required_families:
        raise RobustnessSpecError("held-out families incomplete")
    if set(tasks) & set(spec["predecessor_task_ids"]):
        raise RobustnessSpecError("held-out IDs overlap predecessor")
    predecessor_semantics = {
        _hash(_task_semantics(task)) for task in predecessor.get("task_corpus", [])
    }
    if any(_hash(_task_semantics(task)) in predecessor_semantics for task in tasks.values()):
        raise RobustnessSpecError("held-out semantic duplicate")

    rep_ids = set(reps)
    for actor_id, actor in actors.items():
        if set(actor.get("representations", {})) != rep_ids:
            raise RobustnessSpecError(f"representation mismatch: {actor_id}")
        if not actor.get("skills") or not isinstance(actor.get("available_tools"), list):
            raise RobustnessSpecError(f"invalid actor fixture: {actor_id}")
        if not isinstance(actor.get("extension_inputs"), dict):
            raise RobustnessSpecError(f"invalid extension inputs: {actor_id}")
        for rep_id, values in actor["representations"].items():
            if set(values) != set(reps[rep_id]["dimensions"]):
                raise RobustnessSpecError(f"dimension mismatch: {actor_id}.{rep_id}")
            if not all(_finite(value, 0, 100) for value in values.values()):
                raise RobustnessSpecError(f"invalid actor values: {actor_id}.{rep_id}")
        if not all(_finite(value, 0, 100) for value in actor["skills"].values()):
            raise RobustnessSpecError(f"invalid skills: {actor_id}")

    for task_id, task in tasks.items():
        if set(task.get("representation_weights", {})) != rep_ids:
            raise RobustnessSpecError(f"representation coverage missing: {task_id}")
        if not _finite(task.get("difficulty"), 0, 100) or not task.get("skill_weights"):
            raise RobustnessSpecError(f"invalid task: {task_id}")
        for actor in actors.values():
            if any(skill not in actor["skills"] for skill in task["skill_weights"]):
                raise RobustnessSpecError(f"unknown task skill: {task_id}")
        for rep_id, weights in task["representation_weights"].items():
            if (
                not weights
                or any(dimension not in reps[rep_id]["dimensions"] for dimension in weights)
                or not all(_finite(weight, 0) for weight in weights.values())
            ):
                raise RobustnessSpecError(f"invalid task weights: {task_id}.{rep_id}")

    for relation in spec["qualitative_relations"]:
        if (
            relation.get("task_id") not in tasks
            or relation.get("left_actor") not in actors
            or relation.get("right_actor") not in actors
            or relation.get("direction") not in {"LEFT_GT_RIGHT", "RIGHT_GT_LEFT"}
        ):
            raise RobustnessSpecError("bad qualitative relation")

    for probe in spec["collision_probes"]:
        if (
            probe.get("task_id") not in tasks
            or probe.get("actor_left") not in actors
            or probe.get("actor_right") not in actors
        ):
            raise RobustnessSpecError("bad collision probe")

    if {row.get("genre") for row in spec["genre_extension_fixtures"]} != {
        "WUXIA",
        "XIANXIA",
        "SF",
    }:
        raise RobustnessSpecError("genre pressure incomplete")
    for row in spec["genre_extension_fixtures"]:
        if (
            row.get("actor_id") not in actors
            or row.get("base_task_id") not in tasks
            or not _finite(row.get("extension_weight"), 0, 0.5)
        ):
            raise RobustnessSpecError("bad genre fixture")

    for condition_id, condition in conditions.items():
        if (
            condition.get("status") != "EVALUATION_PROBE_ONLY"
            or not condition.get("affected_tags")
            or not _finite(condition.get("multiplier"), 0.01, 1)
        ):
            raise RobustnessSpecError(f"bad condition: {condition_id}")

    grid = spec["parameter_perturbation_grid"]
    for key in ("actor_offsets", "difficulty_offsets", "weight_scale_factors"):
        values = grid.get(key, [])
        if len(values) < 3 or not all(_finite(value) for value in values):
            raise RobustnessSpecError(f"bad perturbation grid: {key}")
    if not _finite(grid.get("stability_band"), 0):
        raise RobustnessSpecError("bad stability band")
    if not _finite(grid.get("fragile_reversal_threshold"), 0, 1):
        raise RobustnessSpecError("bad fragile threshold")

    diagnostics = spec["math_diagnostic_cases"]
    if diagnostics.get("representation_family") not in {
        row.get("family") for row in reps.values()
    }:
        raise RobustnessSpecError("bad diagnostic representation")
    diagnostic_cases = [
        *diagnostics.get("monotonic_cases", []),
        diagnostics.get("reasoning_isolation_case", {}),
        diagnostics.get("relevant_tool_condition_case", {}),
    ]
    for case in diagnostic_cases:
        if case.get("actor_id") not in actors or case.get("task_id") not in tasks:
            raise RobustnessSpecError("bad diagnostic fixture")
        if "condition_id" in case and case["condition_id"] not in conditions:
            raise RobustnessSpecError("bad diagnostic condition")

    policy = spec["recommendation_policy"]
    if policy.get("recommendation_is_not_resolution_authority") is not True:
        raise RobustnessSpecError("recommendation authority boundary changed")
    if policy.get(
        "attr_resolution_requires_all_heldout_relations_and_collision_coverage_without_fragile_reversal"
    ) is not True:
        raise RobustnessSpecError("attribute recommendation gate changed")
    if policy.get(
        "math_resolution_requires_deterministic_baseline_monotonic_and_stack_nonlocality_absent"
    ) is not True:
        raise RobustnessSpecError("math recommendation gate changed")
    if not policy.get("attr_allowed_prefixes") or not policy.get("math_allowed_prefixes"):
        raise RobustnessSpecError("recommendation classes missing")


def _weighted(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total = float(sum(weights.values()))
    if total <= 0:
        raise RobustnessSpecError("non-positive weights")
    return sum(float(values[key]) * float(weight) for key, weight in weights.items()) / total


def _tilt(weights: Mapping[str, float], factor: float) -> dict[str, float]:
    if factor <= 0:
        raise RobustnessSpecError("weight factor must be positive")
    keys = sorted(weights)
    center = (len(keys) - 1) / 2
    return {
        key: float(weights[key]) * (factor ** (index - center))
        for index, key in enumerate(keys)
    }


def _apply_condition(
    representation: Mapping[str, Any],
    values: Mapping[str, float],
    condition: Mapping[str, Any] | None,
) -> dict[str, float]:
    if condition is None:
        return {key: float(value) for key, value in values.items()}
    affected = set(condition["affected_tags"])
    multiplier = float(condition["multiplier"])
    return {
        key: (
            float(value) * multiplier
            if set(representation["dimensions"][key]["tags"]) & affected
            else float(value)
        )
        for key, value in values.items()
    }


def _bucket(margin: float) -> tuple[str, int]:
    if margin <= -20:
        return "VERY_UNFAVORABLE", 15
    if margin <= -8:
        return "UNFAVORABLE", 30
    if margin <= 8:
        return "EVEN_BAND", 50
    if margin <= 20:
        return "FAVORABLE", 70
    return "VERY_FAVORABLE", 85


def _band(margin: float) -> str:
    if margin >= 12:
        return "CLEAR_POSITIVE"
    if margin >= 0:
        return "NARROW_POSITIVE"
    if margin >= -12:
        return "NARROW_NEGATIVE"
    return "CLEAR_NEGATIVE"


def _semantic_seed(
    spec: Mapping[str, Any],
    representation: Mapping[str, Any],
    math_policy: Mapping[str, Any],
    actor: Mapping[str, Any],
    representation_id: str,
    task: Mapping[str, Any],
    condition: Mapping[str, Any] | None,
    difficulty: float,
    adjusted_values: Mapping[str, float],
    extension_detail: Mapping[str, Any] | None,
) -> str:
    rep_keys = sorted(task["representation_weights"][representation_id])
    skill_keys = sorted(task["skill_weights"])
    material = {
        "salt": spec["provenance"]["seed_salt"],
        "ruleset": spec["provenance"]["evaluation_ruleset_version"],
        "representation": _candidate_semantics(representation),
        "math": _candidate_semantics(math_policy),
        "task": {
            "difficulty": task["difficulty"],
            "required_tool": task.get("required_tool"),
            "representation_weights": {
                key: task["representation_weights"][representation_id][key]
                for key in rep_keys
            },
            "skill_weights": {key: task["skill_weights"][key] for key in skill_keys},
        },
        "actor": {
            "representation_values": {
                key: actor["representations"][representation_id][key] for key in rep_keys
            },
            "skills": {key: actor["skills"][key] for key in skill_keys},
            "required_tool_present": (
                task.get("required_tool") is None
                or task.get("required_tool") in actor["available_tools"]
            ),
        },
        "effective_values": {
            key: round(float(adjusted_values[key]), 6) for key in rep_keys
        },
        "condition": None if condition is None else _drop(condition, "condition_id"),
        "difficulty": round(float(difficulty), 6),
        "extension": extension_detail,
    }
    return _hash(material)


def evaluate_case(
    spec: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    representation_id: str,
    math_policy_id: str,
    actor_id: str,
    task_id: str,
    *,
    actor_offset: float = 0,
    difficulty_offset: float = 0,
    weight_scale_factor: float = 1,
    condition_id: str | None = None,
    extension_fixture: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    validate_inputs(spec, predecessor)
    reps, maths = _maps(predecessor)
    actors, tasks, conditions = _heldout(spec)
    try:
        representation = reps[representation_id]
        math_policy = maths[math_policy_id]
        actor = actors[actor_id]
        task = tasks[task_id]
        condition = None if condition_id is None else conditions[condition_id]
    except KeyError as exc:
        raise RobustnessSpecError(f"unknown ref: {exc.args[0]}") from exc

    receipt_base = {
        "actor_ref": actor_id,
        "task_ref": task_id,
        "representation_ref": representation_id,
        "math_policy_ref": math_policy_id,
        "candidate_status": "EVALUATION_CANDIDATE_ONLY",
    }

    required_tool = task.get("required_tool")
    if required_tool is not None and required_tool not in actor["available_tools"]:
        return {
            **receipt_base,
            "feasibility": "HARD_FAIL_MISSING_REQUIRED_TOOL",
            "effective_capability": None,
            "difficulty": round(float(task["difficulty"]) + float(difficulty_offset), 6),
            "margin": None,
            "margin_band": "INFEASIBLE",
            "sampled_outcome": None,
            "random_receipt": None,
            "extension_applied": False,
            "extension_detail": None,
        }

    relevant = set(task["representation_weights"][representation_id])
    raw = {
        key: max(
            0.0,
            min(
                100.0,
                float(value) + (float(actor_offset) if key in relevant else 0.0),
            ),
        )
        for key, value in actor["representations"][representation_id].items()
    }
    adjusted = _apply_condition(representation, raw, condition)
    rep_weights = _tilt(
        task["representation_weights"][representation_id], float(weight_scale_factor)
    )
    skill_weights = _tilt(task["skill_weights"], float(weight_scale_factor))
    raw_attr = _weighted(raw, rep_weights)
    adjusted_attr = _weighted(adjusted, rep_weights)
    skill = _weighted(actor["skills"], skill_weights)
    tool_bonus = 6.0 if required_tool is not None else 0.0
    condition_factor = adjusted_attr / raw_attr if raw_attr else 1.0

    kind = math_policy["kind"]
    if kind in {"DETERMINISTIC_MARGIN", "BOUNDED_SEEDED_STOCHASTIC"}:
        effective = 0.75 * adjusted_attr + 0.25 * skill + tool_bonus
    elif kind == "ADDITIVE_MULTIPLICATIVE_STACK":
        effective = (0.75 * raw_attr + 0.25 * skill + tool_bonus) * condition_factor
    elif kind == "TAGGED_PRIORITY":
        bottleneck = min(adjusted[key] for key in rep_weights)
        effective = (
            0.55 * adjusted_attr + 0.25 * skill + 0.20 * bottleneck + tool_bonus
        )
    else:
        raise RobustnessSpecError(f"unsupported math kind: {kind}")

    extension_detail = None
    if extension_fixture is not None:
        extension_namespace = actor["extension_inputs"].get(
            str(extension_fixture["genre"]).lower(), {}
        )
        extension_weights = extension_fixture["extension_skill_weights"]
        resource_key = extension_fixture["extension_resource_key"]
        if any(key not in extension_namespace for key in extension_weights):
            raise RobustnessSpecError("missing explicit extension skill")
        if resource_key not in extension_namespace:
            raise RobustnessSpecError("missing explicit extension resource")
        component = 0.8 * _weighted(
            extension_namespace, extension_weights
        ) + 0.2 * float(extension_namespace[resource_key])
        extension_weight = float(extension_fixture["extension_weight"])
        effective = (1 - extension_weight) * effective + extension_weight * component
        extension_detail = {
            "genre": extension_fixture["genre"],
            "component": round(component, 6),
            "extension_weight": extension_weight,
        }

    effective = max(0.0, min(100.0, effective))
    difficulty = max(
        0.0, min(100.0, float(task["difficulty"]) + float(difficulty_offset))
    )
    margin = effective - difficulty

    random_receipt = None
    sampled = None
    if kind == "BOUNDED_SEEDED_STOCHASTIC":
        mapping, threshold = _bucket(margin)
        seed = _semantic_seed(
            spec,
            representation,
            math_policy,
            actor,
            representation_id,
            task,
            condition,
            difficulty,
            adjusted,
            extension_detail,
        )
        roll = int(seed[:8], 16) % 100
        sampled = "SAMPLED_SUCCESS" if roll < threshold else "SAMPLED_FAIL"
        random_receipt = {
            "semantic_seed_digest": seed,
            "roll_bucket_0_99": roll,
            "mapping_band": mapping,
            "threshold_bucket_percent": threshold,
            "calibration_status": "UNCALIBRATED_EVALUATION_BUCKET",
        }

    return {
        **receipt_base,
        "feasibility": "FEASIBLE",
        "effective_capability": round(effective, 6),
        "difficulty": round(difficulty, 6),
        "margin": round(margin, 6),
        "margin_band": _band(margin),
        "sampled_outcome": sampled,
        "random_receipt": random_receipt,
        "extension_applied": extension_fixture is not None,
        "extension_detail": extension_detail,
    }


def semantic_receipt_signature(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {
        key: copy.deepcopy(value)
        for key, value in receipt.items()
        if key not in {"actor_ref", "task_ref", "representation_ref", "math_policy_ref"}
    }


def _expected_side(direction: str) -> str:
    if direction == "LEFT_GT_RIGHT":
        return "LEFT"
    if direction == "RIGHT_GT_LEFT":
        return "RIGHT"
    raise RobustnessSpecError(f"unknown direction: {direction}")


def _compare_receipts(
    direction: str,
    left: Mapping[str, Any],
    right: Mapping[str, Any],
) -> dict[str, Any]:
    left_feasible = left["feasibility"] == "FEASIBLE"
    right_feasible = right["feasibility"] == "FEASIBLE"
    expected_side = _expected_side(direction)

    if left_feasible != right_feasible:
        feasible_side = "LEFT" if left_feasible else "RIGHT"
        return {
            "comparison_basis": "FEASIBILITY_DOMINANCE",
            "holds": feasible_side == expected_side,
            "feasible_side": feasible_side,
            "left_feasibility": left["feasibility"],
            "right_feasibility": right["feasibility"],
            "margin_delta_left_minus_right": None,
            "margin_comparison_performed": False,
        }

    if not left_feasible and not right_feasible:
        return {
            "comparison_basis": "BOTH_INFEASIBLE_NO_MARGIN_ORDER",
            "holds": False,
            "feasible_side": None,
            "left_feasibility": left["feasibility"],
            "right_feasibility": right["feasibility"],
            "margin_delta_left_minus_right": None,
            "margin_comparison_performed": False,
        }

    left_margin = float(left["margin"])
    right_margin = float(right["margin"])
    holds = left_margin > right_margin if direction == "LEFT_GT_RIGHT" else right_margin > left_margin
    return {
        "comparison_basis": "MARGIN_ORDER",
        "holds": holds,
        "feasible_side": "BOTH",
        "left_feasibility": left["feasibility"],
        "right_feasibility": right["feasibility"],
        "margin_delta_left_minus_right": round(left_margin - right_margin, 6),
        "margin_comparison_performed": True,
    }


def _relations(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for rep_id in sorted(spec["representation_candidate_refs"]):
        out[rep_id] = {}
        for math_id in sorted(spec["math_policy_candidate_refs"]):
            rows = []
            for relation in sorted(
                spec["qualitative_relations"], key=lambda row: row["relation_id"]
            ):
                left = evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    relation["left_actor"],
                    relation["task_id"],
                )
                right = evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    relation["right_actor"],
                    relation["task_id"],
                )
                comparison = _compare_receipts(relation["direction"], left, right)
                rows.append({"relation_id": relation["relation_id"], **comparison})
            out[rep_id][math_id] = {
                "preserved_count": sum(bool(row["holds"]) for row in rows),
                "total": len(rows),
                "rows": rows,
            }
    return out


def _collisions(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    math_id = _math_id(predecessor, "DETERMINISTIC_MARGIN")
    out: dict[str, Any] = {}
    for probe in sorted(spec["collision_probes"], key=lambda row: row["probe_id"]):
        rows = {}
        for rep_id in sorted(spec["representation_candidate_refs"]):
            left = evaluate_case(
                spec, predecessor, rep_id, math_id, probe["actor_left"], probe["task_id"]
            )
            right = evaluate_case(
                spec, predecessor, rep_id, math_id, probe["actor_right"], probe["task_id"]
            )
            if left["feasibility"] != "FEASIBLE" or right["feasibility"] != "FEASIBLE":
                raise RobustnessSpecError("collision probe requires two feasible actors")
            delta = round(float(left["margin"]) - float(right["margin"]), 6)
            rows[rep_id] = {
                "margin_delta_left_minus_right": delta,
                "collides": abs(delta) <= 1e-9,
                "distinguishes": abs(delta) > 1e-9,
            }
        out[probe["probe_id"]] = {
            "semantic_axis": probe["semantic_axis"],
            "candidate_rows": rows,
            "distinguishing_candidates_observed": sorted(
                key for key, value in rows.items() if value["distinguishes"]
            ),
            "colliding_candidates_observed": sorted(
                key for key, value in rows.items() if value["collides"]
            ),
        }
    return out


def _genres(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    math_id = _math_id(predecessor, "DETERMINISTIC_MARGIN")
    actors = _heldout(spec)[0]
    out: dict[str, Any] = {}
    for fixture in sorted(
        spec["genre_extension_fixtures"], key=lambda row: row["extension_id"]
    ):
        rows = {}
        for rep_id in sorted(spec["representation_candidate_refs"]):
            before = evaluate_case(
                spec,
                predecessor,
                rep_id,
                math_id,
                fixture["actor_id"],
                fixture["base_task_id"],
            )
            mutated = copy.deepcopy(spec)
            actor = next(
                row
                for row in mutated["held_out_actors"]
                if row["actor_id"] == fixture["actor_id"]
            )
            extension_namespace = actor["extension_inputs"][fixture["genre"].lower()]
            for key in extension_namespace:
                extension_namespace[key] = min(
                    100.0, float(extension_namespace[key]) + 7.0
                )
            after = evaluate_case(
                mutated,
                predecessor,
                rep_id,
                math_id,
                fixture["actor_id"],
                fixture["base_task_id"],
            )
            extension = evaluate_case(
                spec,
                predecessor,
                rep_id,
                math_id,
                fixture["actor_id"],
                fixture["base_task_id"],
                extension_fixture=fixture,
            )
            rows[rep_id] = {
                "mundane_ignores_extension_mutation": (
                    semantic_receipt_signature(before)
                    == semantic_receipt_signature(after)
                ),
                "base_representation_snapshot_digest": _hash(
                    actors[fixture["actor_id"]]["representations"][rep_id]
                ),
                "extension_receipt": extension,
            }
        out[fixture["extension_id"]] = {"genre": fixture["genre"], "rows": rows}
    return out


def _robustness(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    grid = spec["parameter_perturbation_grid"]
    out: dict[str, Any] = {}
    for rep_id in sorted(spec["representation_candidate_refs"]):
        out[rep_id] = {}
        for math_id in sorted(spec["math_policy_candidate_refs"]):
            relation_rows = []
            for relation in sorted(
                spec["qualitative_relations"], key=lambda row: row["relation_id"]
            ):
                baseline_left = evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    relation["left_actor"],
                    relation["task_id"],
                )
                baseline_right = evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    relation["right_actor"],
                    relation["task_id"],
                )
                baseline = _compare_receipts(
                    relation["direction"], baseline_left, baseline_right
                )
                baseline_delta = baseline["margin_delta_left_minus_right"]

                total = 0
                preserved = 0
                feasibility_dominance_count = 0
                margin_comparison_count = 0
                margin_stable_count = 0
                reversals = []

                for left_offset in grid["actor_offsets"]:
                    for right_offset in grid["actor_offsets"]:
                        for difficulty_offset in grid["difficulty_offsets"]:
                            for weight_factor in grid["weight_scale_factors"]:
                                total += 1
                                left = evaluate_case(
                                    spec,
                                    predecessor,
                                    rep_id,
                                    math_id,
                                    relation["left_actor"],
                                    relation["task_id"],
                                    actor_offset=left_offset,
                                    difficulty_offset=difficulty_offset,
                                    weight_scale_factor=weight_factor,
                                )
                                right = evaluate_case(
                                    spec,
                                    predecessor,
                                    rep_id,
                                    math_id,
                                    relation["right_actor"],
                                    relation["task_id"],
                                    actor_offset=right_offset,
                                    difficulty_offset=difficulty_offset,
                                    weight_scale_factor=weight_factor,
                                )
                                comparison = _compare_receipts(
                                    relation["direction"], left, right
                                )
                                if comparison["holds"]:
                                    preserved += 1
                                else:
                                    reversals.append(
                                        {
                                            "left_actor_offset": left_offset,
                                            "right_actor_offset": right_offset,
                                            "difficulty_offset": difficulty_offset,
                                            "weight_scale_factor": weight_factor,
                                            "comparison_basis": comparison["comparison_basis"],
                                            "left_feasibility": comparison["left_feasibility"],
                                            "right_feasibility": comparison["right_feasibility"],
                                            "margin_delta_left_minus_right": comparison[
                                                "margin_delta_left_minus_right"
                                            ],
                                        }
                                    )

                                if comparison["comparison_basis"] == "FEASIBILITY_DOMINANCE":
                                    feasibility_dominance_count += 1
                                elif comparison["comparison_basis"] == "MARGIN_ORDER":
                                    margin_comparison_count += 1
                                    if baseline_delta is not None:
                                        if (
                                            abs(
                                                float(
                                                    comparison[
                                                        "margin_delta_left_minus_right"
                                                    ]
                                                )
                                                - float(baseline_delta)
                                            )
                                            <= float(grid["stability_band"])
                                        ):
                                            margin_stable_count += 1

                fraction = preserved / total
                margin_stability_fraction = (
                    None
                    if baseline_delta is None or margin_comparison_count == 0
                    else round(margin_stable_count / margin_comparison_count, 6)
                )
                relation_rows.append(
                    {
                        "relation_id": relation["relation_id"],
                        "baseline_comparison_basis": baseline["comparison_basis"],
                        "preserved": preserved,
                        "total": total,
                        "preservation_fraction": round(fraction, 6),
                        "feasibility_dominance_count": feasibility_dominance_count,
                        "margin_comparison_count": margin_comparison_count,
                        "margin_band_stability_fraction": margin_stability_fraction,
                        "reversal_locations": reversals,
                        "fragile": fraction
                        < float(grid["fragile_reversal_threshold"]),
                    }
                )
            out[rep_id][math_id] = {
                "relations": relation_rows,
                "mean_preservation_fraction": round(
                    sum(row["preservation_fraction"] for row in relation_rows)
                    / len(relation_rows),
                    6,
                ),
                "fragile_relation_count": sum(
                    bool(row["fragile"]) for row in relation_rows
                ),
            }
    return out


def _burden(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    reps, maths = _maps(predecessor)
    return {
        "representations": {
            rep_id: {
                "durable_dimension_count": len(reps[rep_id]["dimensions"]),
                "heldout_representation_weight_count": sum(
                    len(task["representation_weights"][rep_id])
                    for task in spec["held_out_tasks"]
                ),
                "independently_named_base_dimensions": sorted(
                    reps[rep_id]["dimensions"]
                ),
            }
            for rep_id in sorted(spec["representation_candidate_refs"])
        },
        "math_policies": {
            math_id: {
                "kind": maths[math_id]["kind"],
                "probability_bucket_tuning_required": (
                    maths[math_id]["kind"] == "BOUNDED_SEEDED_STOCHASTIC"
                ),
                "bottleneck_weight_tuning_required": (
                    maths[math_id]["kind"] == "TAGGED_PRIORITY"
                ),
                "condition_stack_interaction": (
                    "GLOBAL_MULTIPLICATIVE"
                    if maths[math_id]["kind"] == "ADDITIVE_MULTIPLICATIVE_STACK"
                    else "LOCAL_OR_NONE"
                ),
            }
            for math_id in sorted(spec["math_policy_candidate_refs"])
        },
    }


def _math_diagnostics(
    spec: Mapping[str, Any], predecessor: Mapping[str, Any]
) -> dict[str, Any]:
    reps, maths = _maps(predecessor)
    diagnostics = spec["math_diagnostic_cases"]
    matching = [
        rep_id
        for rep_id, row in reps.items()
        if row.get("family") == diagnostics["representation_family"]
    ]
    if len(matching) != 1:
        raise RobustnessSpecError("diagnostic representation not unique")
    rep_id = matching[0]

    results: dict[str, Any] = {}
    for math_id in sorted(spec["math_policy_candidate_refs"]):
        monotonic = True
        for case in diagnostics["monotonic_cases"]:
            margins = [
                evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    case["actor_id"],
                    case["task_id"],
                    actor_offset=offset,
                )["margin"]
                for offset in (-5, 0, 5)
            ]
            if any(margin is None for margin in margins):
                raise RobustnessSpecError(
                    "monotonic diagnostic must remain feasible"
                )
            monotonic = monotonic and all(
                float(left) <= float(right)
                for left, right in zip(margins, margins[1:])
            )

        reasoning = diagnostics["reasoning_isolation_case"]
        tool = diagnostics["relevant_tool_condition_case"]
        reasoning_base = evaluate_case(
            spec,
            predecessor,
            rep_id,
            math_id,
            reasoning["actor_id"],
            reasoning["task_id"],
        )
        reasoning_conditioned = evaluate_case(
            spec,
            predecessor,
            rep_id,
            math_id,
            reasoning["actor_id"],
            reasoning["task_id"],
            condition_id=reasoning["condition_id"],
        )
        tool_base = evaluate_case(
            spec,
            predecessor,
            rep_id,
            math_id,
            tool["actor_id"],
            tool["task_id"],
        )
        tool_conditioned = evaluate_case(
            spec,
            predecessor,
            rep_id,
            math_id,
            tool["actor_id"],
            tool["task_id"],
            condition_id=tool["condition_id"],
        )
        if any(
            receipt["margin"] is None
            for receipt in (
                reasoning_base,
                reasoning_conditioned,
                tool_base,
                tool_conditioned,
            )
        ):
            raise RobustnessSpecError("math diagnostics require feasible cases")

        replay = True
        if maths[math_id]["kind"] == "BOUNDED_SEEDED_STOCHASTIC":
            replay = (
                tool_base
                == evaluate_case(
                    spec,
                    predecessor,
                    rep_id,
                    math_id,
                    tool["actor_id"],
                    tool["task_id"],
                )
                and tool_base["random_receipt"] is not None
            )

        results[math_id] = {
            "kind": maths[math_id]["kind"],
            "monotonic_on_heldout_offsets": bool(monotonic),
            "unrelated_condition_leaves_reasoning_margin_unchanged": (
                reasoning_base["margin"] == reasoning_conditioned["margin"]
            ),
            "relevant_condition_changes_tool_margin": (
                tool_base["margin"] != tool_conditioned["margin"]
            ),
            "tool_condition_penalty": round(
                float(tool_base["margin"]) - float(tool_conditioned["margin"]), 6
            ),
            "stochastic_exact_replay_if_applicable": replay,
            "probability_calibration_claimed": False,
        }

    baseline_penalty = next(
        row["tool_condition_penalty"]
        for row in results.values()
        if row["kind"] == "DETERMINISTIC_MARGIN"
    )
    for row in results.values():
        row["excess_tool_condition_penalty_vs_deterministic"] = round(
            float(row["tool_condition_penalty"]) - float(baseline_penalty), 6
        )
    return results


def _recommendations(
    spec: Mapping[str, Any],
    predecessor: Mapping[str, Any],
    relations: Mapping[str, Any],
    collisions: Mapping[str, Any],
    robustness: Mapping[str, Any],
    diagnostics: Mapping[str, Any],
) -> dict[str, Any]:
    policy = spec["recommendation_policy"]
    deterministic_id = _math_id(predecessor, "DETERMINISTIC_MARGIN")
    additive_id = _math_id(predecessor, "ADDITIVE_MULTIPLICATIVE_STACK")
    tagged_id = _math_id(predecessor, "TAGGED_PRIORITY")

    structural: dict[str, Any] = {}
    for rep_id in sorted(spec["representation_candidate_refs"]):
        relation_summary = relations[rep_id][deterministic_id]
        robustness_summary = robustness[rep_id][deterministic_id]
        structural[rep_id] = {
            "all_heldout_relations_hold": (
                relation_summary["preserved_count"] == relation_summary["total"]
            ),
            "collision_coverage": sum(
                bool(probe["candidate_rows"][rep_id]["distinguishes"])
                for probe in collisions.values()
            ),
            "collision_total": len(collisions),
            "fragile_relation_count": robustness_summary["fragile_relation_count"],
            "mean_preservation_fraction": robustness_summary[
                "mean_preservation_fraction"
            ],
        }

    attr_gate_enabled = bool(
        policy[
            "attr_resolution_requires_all_heldout_relations_and_collision_coverage_without_fragile_reversal"
        ]
    )
    attr_resolvers = [
        rep_id
        for rep_id, row in structural.items()
        if (
            not attr_gate_enabled
            or (
                row["all_heldout_relations_hold"]
                and row["collision_coverage"] == row["collision_total"]
                and row["fragile_relation_count"] == 0
            )
        )
    ]
    attr_recommendation = "KEEP_ATTR_OPEN"
    if len(attr_resolvers) == 1:
        burdens = _burden(spec, predecessor)["representations"]
        chosen = burdens[attr_resolvers[0]]
        min_dimensions = min(row["durable_dimension_count"] for row in burdens.values())
        min_weights = min(
            row["heldout_representation_weight_count"] for row in burdens.values()
        )
        materially_larger = (
            chosen["durable_dimension_count"] > min_dimensions + 2
            or chosen["heldout_representation_weight_count"] > min_weights + 4
        )
        if not materially_larger:
            attr_recommendation = f"NARROW_ATTR_TO_{attr_resolvers[0]}"

    deterministic_evidence = diagnostics[deterministic_id]
    deterministic_baseline_ok = (
        deterministic_evidence["monotonic_on_heldout_offsets"]
        and deterministic_evidence[
            "unrelated_condition_leaves_reasoning_margin_unchanged"
        ]
        and deterministic_evidence["relevant_condition_changes_tool_margin"]
    )
    stack_nonlocality_absent = all(
        abs(
            float(
                diagnostics[math_id][
                    "excess_tool_condition_penalty_vs_deterministic"
                ]
            )
        )
        <= 1e-9
        for math_id in (additive_id, tagged_id)
    )
    math_gate_satisfied = (
        deterministic_baseline_ok
        and (
            stack_nonlocality_absent
            if policy[
                "math_resolution_requires_deterministic_baseline_monotonic_and_stack_nonlocality_absent"
            ]
            else True
        )
    )
    math_recommendation = (
        "RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN"
        if math_gate_satisfied
        else "KEEP_MATH_OPEN"
    )

    if not any(
        attr_recommendation.startswith(prefix)
        for prefix in policy["attr_allowed_prefixes"]
    ):
        raise RobustnessSpecError("derived ATTR recommendation violates policy")
    if not any(
        math_recommendation.startswith(prefix)
        for prefix in policy["math_allowed_prefixes"]
    ):
        raise RobustnessSpecError("derived MATH recommendation violates policy")

    return {
        "ATTR": attr_recommendation,
        "MATH": math_recommendation,
        "candidate_structural_evidence": structural,
        "policy_evidence": {
            "attr_gate_enabled": attr_gate_enabled,
            "attr_resolvers": sorted(attr_resolvers),
            "deterministic_baseline_ok": deterministic_baseline_ok,
            "stack_nonlocality_absent": stack_nonlocality_absent,
            "math_resolution_gate_satisfied": math_gate_satisfied,
            "math_policy_contract_consumed": True,
        },
        "resolution_authority": False,
        "open_decisions_mutated": False,
    }


def _normalized(
    spec: Mapping[str, Any], predecessor: Mapping[str, Any]
) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_spec = copy.deepcopy(spec)
    for key in (
        "representation_candidate_refs",
        "math_policy_candidate_refs",
        "predecessor_task_ids",
        "overfit_guards",
    ):
        normalized_spec[key] = sorted(normalized_spec[key])
    for key, id_key in (
        ("held_out_actors", "actor_id"),
        ("held_out_tasks", "task_id"),
        ("qualitative_relations", "relation_id"),
        ("collision_probes", "probe_id"),
        ("genre_extension_fixtures", "extension_id"),
        ("condition_probes", "condition_id"),
    ):
        normalized_spec[key] = sorted(
            normalized_spec[key], key=lambda row: row[id_key]
        )
    normalized_predecessor = {
        "representation_candidates": sorted(
            copy.deepcopy(predecessor["representation_candidates"]),
            key=lambda row: row["candidate_id"],
        ),
        "math_policy_candidates": sorted(
            copy.deepcopy(predecessor["math_policy_candidates"]),
            key=lambda row: row["candidate_id"],
        ),
    }
    return normalized_spec, normalized_predecessor


def run_evaluation(
    spec: Mapping[str, Any], predecessor: Mapping[str, Any]
) -> dict[str, Any]:
    validate_inputs(spec, predecessor)
    pristine_spec = copy.deepcopy(spec)
    pristine_predecessor = copy.deepcopy(predecessor)

    relations = _relations(spec, predecessor)
    collisions = _collisions(spec, predecessor)
    genres = _genres(spec, predecessor)
    robustness = _robustness(spec, predecessor)
    burden = _burden(spec, predecessor)
    diagnostics = _math_diagnostics(spec, predecessor)
    recommendations = _recommendations(
        spec,
        predecessor,
        relations,
        collisions,
        robustness,
        diagnostics,
    )

    if spec != pristine_spec or predecessor != pristine_predecessor:
        raise RobustnessSpecError("hidden mutation")

    normalized_spec, normalized_predecessor = _normalized(spec, predecessor)
    return {
        "suite_id": spec["suite_id"],
        "suite_version": spec["suite_version"],
        "status": spec["status"],
        "release_base": spec["release_base"],
        "held_out_task_count": len(spec["held_out_tasks"]),
        "held_out_task_semantic_digests": sorted(
            _hash(_task_semantics(task)) for task in spec["held_out_tasks"]
        ),
        "qualitative_relation_evidence": relations,
        "representation_collision_evidence": collisions,
        "genre_extension_pressure": genres,
        "parameter_robustness": robustness,
        "parameter_burden": burden,
        "math_policy_diagnostics": diagnostics,
        "recommendations": recommendations,
        "overfit_guards": {
            "heldout_declared_before_interpretation": True,
            "candidate_specific_task_omission": False,
            "expected_winner_field_present": False,
            "id_names_excluded_from_stochastic_seed_material": True,
            "hidden_global_mutation": False,
        },
        "evidence_limits": {
            "synthetic_corpus": True,
            "player_fairness_calibrated": False,
            "probability_buckets_calibrated": False,
            "architecture_invariants_can_be_tested": True,
            "later_ruleset_tuning_still_required": True,
        },
        "governance_locks": copy.deepcopy(spec["governance_locks"]),
        "provenance": {
            "predecessor_accepted_head": spec["predecessor"]["accepted_head"],
            "predecessor_merge_commit": spec["predecessor"]["merge_commit"],
            "predecessor_candidate_registry_digest": _hash(normalized_predecessor),
            "cap_eval_002_spec_digest": _hash(normalized_spec),
            "serialization": spec["provenance"]["serialization"],
        },
    }


def main() -> None:
    spec, predecessor = load_inputs()
    print(canonical_json(run_evaluation(spec, predecessor)))


if __name__ == "__main__":
    main()
