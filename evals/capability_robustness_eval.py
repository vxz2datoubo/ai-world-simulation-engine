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
    return hashlib.sha256(canonical_json(value).encode()).hexdigest()


def _index(items: Iterable[Mapping[str, Any]], key: str) -> dict[str, Mapping[str, Any]]:
    out = {}
    for item in items:
        value = item.get(key)
        if not isinstance(value, str) or not value or value in out:
            raise RobustnessSpecError(f"invalid/duplicate {key}: {value!r}")
        out[value] = item
    return out


def _finite(value: Any, low: float = -math.inf, high: float = math.inf) -> bool:
    return not isinstance(value, bool) and isinstance(value, (int, float)) and math.isfinite(float(value)) and low <= float(value) <= high


def _drop(row: Mapping[str, Any], *keys: str) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in row.items() if k not in keys}


def _task_semantics(task: Mapping[str, Any]) -> dict[str, Any]:
    return _drop(task, "task_id", "family", "method_class", "description")


def _candidate_semantics(candidate: Mapping[str, Any]) -> dict[str, Any]:
    return _drop(candidate, "candidate_id", "strongest_counterexample", "genre_extension_note")


def _maps(predecessor: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    return dict(_index(predecessor["representation_candidates"], "candidate_id")), dict(_index(predecessor["math_policy_candidates"], "candidate_id"))


def _heldout(spec: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    return (
        dict(_index(spec["held_out_actors"], "actor_id")),
        dict(_index(spec["held_out_tasks"], "task_id")),
        dict(_index(spec["condition_probes"], "condition_id")),
    )


def _math_id(predecessor: Mapping[str, Any], kind: str) -> str:
    matches = [cid for cid, row in _maps(predecessor)[1].items() if row.get("kind") == kind]
    if len(matches) != 1:
        raise RobustnessSpecError(f"math kind not unique: {kind}")
    return matches[0]


def load_inputs(spec_path: Path | str = SPEC_PATH, predecessor_path: Path | str = PREDECESSOR_SPEC_PATH) -> tuple[dict[str, Any], dict[str, Any]]:
    spec = json.loads(Path(spec_path).read_text(encoding="utf-8"))
    predecessor = json.loads(Path(predecessor_path).read_text(encoding="utf-8"))
    validate_inputs(spec, predecessor)
    return spec, predecessor


def validate_inputs(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> None:
    required = {
        "suite_id", "suite_version", "status", "release_base", "predecessor",
        "source_open_decision_refs", "candidate_status_required", "representation_candidate_refs",
        "math_policy_candidate_refs", "provenance", "held_out_corpus_declared_before_interpretation",
        "predecessor_task_ids", "held_out_actors", "held_out_tasks", "qualitative_relations",
        "collision_probes", "genre_extension_fixtures", "condition_probes", "parameter_perturbation_grid",
        "math_diagnostic_cases", "overfit_guards", "genre_core_pollution_guard", "recommendation_policy",
        "governance_locks",
    }
    if required - set(spec):
        raise RobustnessSpecError(f"missing fields: {sorted(required-set(spec))}")
    if spec["status"] != "EVALUATION_ONLY_NON_CANONICAL" or spec["release_base"] != "32e2a1a830f0685af207275da0ad4849e7637ea4":
        raise RobustnessSpecError("evaluation status/release base changed")
    if set(spec["source_open_decision_refs"]) != {"OD-CAPABILITY-ATTR-001", "OD-CAPABILITY-MATH-001"}:
        raise RobustnessSpecError("OPEN_DECISION refs changed")
    if spec["candidate_status_required"] != "EVALUATION_CANDIDATE_ONLY" or spec["held_out_corpus_declared_before_interpretation"] is not True:
        raise RobustnessSpecError("candidate/held-out guard changed")
    if spec["governance_locks"] != {
        "RUNTIME_SEMANTICS_UNCHANGED": True,
        "OPEN_DECISION_STATUS_UNCHANGED": True,
        "NO_I2_RUNTIME_IMPLEMENTED": True,
        "all_candidates_non_canonical": True,
    }:
        raise RobustnessSpecError("governance locks changed")
    predmeta = spec["predecessor"]
    if predmeta.get("accepted_head") != "6e665ca3f02795564119383f52f7643190997eec" or predmeta.get("merge_commit") != spec["release_base"]:
        raise RobustnessSpecError("predecessor provenance changed")

    reps, maths = _maps(predecessor)
    if set(spec["representation_candidate_refs"]) != set(reps) or set(spec["math_policy_candidate_refs"]) != set(maths):
        raise RobustnessSpecError("candidate registry mismatch")
    if any(row.get("status") != "EVALUATION_CANDIDATE_ONLY" for row in [*reps.values(), *maths.values()]):
        raise RobustnessSpecError("candidate gained authority")
    if {row.get("kind") for row in maths.values()} != MATH_KINDS:
        raise RobustnessSpecError("math families changed")

    actors, tasks, conditions = _heldout(spec)
    required_families = {
        "EXPLOSIVE_RAPID_FORCE", "WHOLE_BODY_CHANGE_OF_DIRECTION", "PRECISION_UNDER_TIME_PRESSURE",
        "MULTI_STAGE_TOOL_HARD_PREREQUISITE", "NOISY_AMBIGUOUS_OBSERVATION",
        "REASONING_IRRELEVANT_PHYSICAL_IMPAIRMENT", "SUSTAINED_COORDINATED_PHYSICAL",
        "ASSISTANCE_TEAMWORK_REPRESENTATION_PRESSURE",
    }
    if len(tasks) < 8 or {t.get("family") for t in tasks.values()} != required_families:
        raise RobustnessSpecError("held-out families incomplete")
    if set(tasks) & set(spec["predecessor_task_ids"]):
        raise RobustnessSpecError("held-out IDs overlap predecessor")
    old_semantics = {_hash(_task_semantics(t)) for t in predecessor.get("task_corpus", [])}
    if any(_hash(_task_semantics(t)) in old_semantics for t in tasks.values()):
        raise RobustnessSpecError("held-out semantic duplicate")

    rep_ids = set(reps)
    for aid, actor in actors.items():
        if set(actor.get("representations", {})) != rep_ids or not actor.get("skills") or not isinstance(actor.get("available_tools"), list):
            raise RobustnessSpecError(f"invalid actor fixture: {aid}")
        for rid, values in actor["representations"].items():
            if set(values) != set(reps[rid]["dimensions"]) or not all(_finite(v, 0, 100) for v in values.values()):
                raise RobustnessSpecError(f"dimension mismatch: {aid}.{rid}")
        if not all(_finite(v, 0, 100) for v in actor["skills"].values()) or not isinstance(actor.get("extension_inputs"), dict):
            raise RobustnessSpecError(f"invalid actor values: {aid}")

    for tid, task in tasks.items():
        if set(task.get("representation_weights", {})) != rep_ids or not _finite(task.get("difficulty"), 0, 100) or not task.get("skill_weights"):
            raise RobustnessSpecError(f"invalid task: {tid}")
        if any(skill not in actor["skills"] for actor in actors.values() for skill in task["skill_weights"]):
            raise RobustnessSpecError(f"unknown task skill: {tid}")
        for rid, weights in task["representation_weights"].items():
            if not weights or any(k not in reps[rid]["dimensions"] for k in weights) or not all(_finite(v, 0) for v in weights.values()):
                raise RobustnessSpecError(f"invalid task weights: {tid}.{rid}")

    if {x.get("genre") for x in spec["genre_extension_fixtures"]} != {"WUXIA", "XIANXIA", "SF"}:
        raise RobustnessSpecError("genre pressure incomplete")
    for row in spec["qualitative_relations"]:
        if row.get("task_id") not in tasks or row.get("left_actor") not in actors or row.get("right_actor") not in actors or row.get("direction") not in {"LEFT_GT_RIGHT", "RIGHT_GT_LEFT"}:
            raise RobustnessSpecError("bad qualitative relation")
    for row in spec["collision_probes"]:
        if row.get("task_id") not in tasks or row.get("actor_left") not in actors or row.get("actor_right") not in actors:
            raise RobustnessSpecError("bad collision probe")
    for row in spec["genre_extension_fixtures"]:
        if row.get("actor_id") not in actors or row.get("base_task_id") not in tasks or not _finite(row.get("extension_weight"), 0, .5):
            raise RobustnessSpecError("bad genre fixture")
    for cid, row in conditions.items():
        if row.get("status") != "EVALUATION_PROBE_ONLY" or not row.get("affected_tags") or not _finite(row.get("multiplier"), .01, 1):
            raise RobustnessSpecError(f"bad condition: {cid}")

    diag = spec["math_diagnostic_cases"]
    if diag.get("representation_family") not in {r.get("family") for r in reps.values()}:
        raise RobustnessSpecError("bad diagnostic representation")
    diag_cases = [*diag.get("monotonic_cases", []), diag.get("reasoning_isolation_case", {}), diag.get("relevant_tool_condition_case", {})]
    for row in diag_cases:
        if row.get("actor_id") not in actors or row.get("task_id") not in tasks:
            raise RobustnessSpecError("bad diagnostic fixture")
        if "condition_id" in row and row["condition_id"] not in conditions:
            raise RobustnessSpecError("bad diagnostic condition")
    grid = spec["parameter_perturbation_grid"]
    for key in ("actor_offsets", "difficulty_offsets", "weight_scale_factors"):
        if len(grid.get(key, [])) < 3 or not all(_finite(v) for v in grid[key]):
            raise RobustnessSpecError(f"bad perturbation grid: {key}")


def _weighted(values: Mapping[str, float], weights: Mapping[str, float]) -> float:
    total = float(sum(weights.values()))
    if total <= 0:
        raise RobustnessSpecError("non-positive weights")
    return sum(float(values[k]) * float(w) for k, w in weights.items()) / total


def _tilt(weights: Mapping[str, float], factor: float) -> dict[str, float]:
    if factor <= 0:
        raise RobustnessSpecError("weight factor must be positive")
    keys = sorted(weights)
    center = (len(keys) - 1) / 2
    return {k: float(weights[k]) * (factor ** (i - center)) for i, k in enumerate(keys)}


def _apply_condition(rep: Mapping[str, Any], values: Mapping[str, float], condition: Mapping[str, Any] | None) -> dict[str, float]:
    if condition is None:
        return {k: float(v) for k, v in values.items()}
    affected, multiplier = set(condition["affected_tags"]), float(condition["multiplier"])
    return {
        k: float(v) * multiplier if set(rep["dimensions"][k]["tags"]) & affected else float(v)
        for k, v in values.items()
    }


def _bucket(margin: float) -> tuple[str, int]:
    if margin <= -20: return "VERY_UNFAVORABLE", 15
    if margin <= -8: return "UNFAVORABLE", 30
    if margin <= 8: return "EVEN_BAND", 50
    if margin <= 20: return "FAVORABLE", 70
    return "VERY_FAVORABLE", 85


def _band(margin: float) -> str:
    if margin >= 12: return "CLEAR_POSITIVE"
    if margin >= 0: return "NARROW_POSITIVE"
    if margin >= -12: return "NARROW_NEGATIVE"
    return "CLEAR_NEGATIVE"


def _semantic_seed(spec: Mapping[str, Any], rep: Mapping[str, Any], math_row: Mapping[str, Any], actor: Mapping[str, Any], rid: str, task: Mapping[str, Any], condition: Mapping[str, Any] | None, difficulty: float, adjusted: Mapping[str, float], extension: Mapping[str, Any] | None) -> str:
    rep_keys = sorted(task["representation_weights"][rid])
    skill_keys = sorted(task["skill_weights"])
    material = {
        "salt": spec["provenance"]["seed_salt"],
        "ruleset": spec["provenance"]["evaluation_ruleset_version"],
        "representation": _candidate_semantics(rep),
        "math": _candidate_semantics(math_row),
        "task": {
            "difficulty": task["difficulty"], "required_tool": task.get("required_tool"),
            "representation_weights": {k: task["representation_weights"][rid][k] for k in rep_keys},
            "skill_weights": {k: task["skill_weights"][k] for k in skill_keys},
        },
        "actor": {
            "representation_values": {k: actor["representations"][rid][k] for k in rep_keys},
            "skills": {k: actor["skills"][k] for k in skill_keys},
            "required_tool_present": task.get("required_tool") is None or task.get("required_tool") in actor["available_tools"],
        },
        "effective_values": {k: round(float(adjusted[k]), 6) for k in rep_keys},
        "condition": None if condition is None else _drop(condition, "condition_id"),
        "difficulty": round(float(difficulty), 6),
        "extension": extension,
    }
    return _hash(material)


def evaluate_case(spec: Mapping[str, Any], predecessor: Mapping[str, Any], representation_id: str, math_policy_id: str, actor_id: str, task_id: str, *, actor_offset: float = 0, difficulty_offset: float = 0, weight_scale_factor: float = 1, condition_id: str | None = None, extension_fixture: Mapping[str, Any] | None = None) -> dict[str, Any]:
    validate_inputs(spec, predecessor)
    reps, maths = _maps(predecessor)
    actors, tasks, conditions = _heldout(spec)
    try:
        rep, math_row, actor, task = reps[representation_id], maths[math_policy_id], actors[actor_id], tasks[task_id]
        condition = None if condition_id is None else conditions[condition_id]
    except KeyError as exc:
        raise RobustnessSpecError(f"unknown ref: {exc.args[0]}") from exc

    required_tool = task.get("required_tool")
    if required_tool is not None and required_tool not in actor["available_tools"]:
        return {"actor_ref": actor_id, "task_ref": task_id, "representation_ref": representation_id, "math_policy_ref": math_policy_id, "candidate_status": "EVALUATION_CANDIDATE_ONLY", "feasibility": "HARD_FAIL_MISSING_REQUIRED_TOOL", "margin": None, "margin_band": "INFEASIBLE", "sampled_outcome": None, "random_receipt": None, "extension_applied": False}

    relevant = set(task["representation_weights"][representation_id])
    raw = {k: max(0, min(100, float(v) + (float(actor_offset) if k in relevant else 0))) for k, v in actor["representations"][representation_id].items()}
    adjusted = _apply_condition(rep, raw, condition)
    rep_weights, skill_weights = _tilt(task["representation_weights"][representation_id], float(weight_scale_factor)), _tilt(task["skill_weights"], float(weight_scale_factor))
    raw_attr, adjusted_attr, skill = _weighted(raw, rep_weights), _weighted(adjusted, rep_weights), _weighted(actor["skills"], skill_weights)
    tool_bonus = 6.0 if required_tool else 0.0
    factor = adjusted_attr / raw_attr if raw_attr else 1.0
    kind = math_row["kind"]
    if kind in {"DETERMINISTIC_MARGIN", "BOUNDED_SEEDED_STOCHASTIC"}:
        effective = .75 * adjusted_attr + .25 * skill + tool_bonus
    elif kind == "ADDITIVE_MULTIPLICATIVE_STACK":
        effective = (.75 * raw_attr + .25 * skill + tool_bonus) * factor
    elif kind == "TAGGED_PRIORITY":
        effective = .55 * adjusted_attr + .25 * skill + .20 * min(adjusted[k] for k in rep_weights) + tool_bonus
    else:
        raise RobustnessSpecError(f"unsupported math kind: {kind}")

    extension_detail = None
    if extension_fixture is not None:
        ext = actor["extension_inputs"].get(str(extension_fixture["genre"]).lower(), {})
        weights, resource = extension_fixture["extension_skill_weights"], extension_fixture["extension_resource_key"]
        if any(k not in ext for k in weights) or resource not in ext:
            raise RobustnessSpecError("missing explicit extension input")
        component = .8 * _weighted(ext, weights) + .2 * float(ext[resource])
        ew = float(extension_fixture["extension_weight"])
        effective = (1 - ew) * effective + ew * component
        extension_detail = {"genre": extension_fixture["genre"], "component": round(component, 6), "extension_weight": ew}

    effective = max(0, min(100, effective))
    difficulty = max(0, min(100, float(task["difficulty"]) + float(difficulty_offset)))
    margin = effective - difficulty
    random_receipt = sampled = None
    if kind == "BOUNDED_SEEDED_STOCHASTIC":
        mapping, threshold = _bucket(margin)
        seed = _semantic_seed(spec, rep, math_row, actor, representation_id, task, condition, difficulty, adjusted, extension_detail)
        roll = int(seed[:8], 16) % 100
        sampled = "SAMPLED_SUCCESS" if roll < threshold else "SAMPLED_FAIL"
        random_receipt = {"semantic_seed_digest": seed, "roll_bucket_0_99": roll, "mapping_band": mapping, "threshold_bucket_percent": threshold, "calibration_status": "UNCALIBRATED_EVALUATION_BUCKET"}
    return {"actor_ref": actor_id, "task_ref": task_id, "representation_ref": representation_id, "math_policy_ref": math_policy_id, "candidate_status": "EVALUATION_CANDIDATE_ONLY", "feasibility": "FEASIBLE", "effective_capability": round(effective, 6), "difficulty": round(difficulty, 6), "margin": round(margin, 6), "margin_band": _band(margin), "sampled_outcome": sampled, "random_receipt": random_receipt, "extension_applied": extension_fixture is not None, "extension_detail": extension_detail}


def semantic_receipt_signature(receipt: Mapping[str, Any]) -> dict[str, Any]:
    return {k: copy.deepcopy(v) for k, v in receipt.items() if k not in {"actor_ref", "task_ref", "representation_ref", "math_policy_ref"}}


def _relation_holds(direction: str, left: float, right: float) -> bool:
    return left > right if direction == "LEFT_GT_RIGHT" else right > left


def _relations(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    out = {}
    for rid in sorted(spec["representation_candidate_refs"]):
        out[rid] = {}
        for mid in sorted(spec["math_policy_candidate_refs"]):
            rows = []
            for rel in sorted(spec["qualitative_relations"], key=lambda x: x["relation_id"]):
                left = evaluate_case(spec, predecessor, rid, mid, rel["left_actor"], rel["task_id"])
                right = evaluate_case(spec, predecessor, rid, mid, rel["right_actor"], rel["task_id"])
                rows.append({"relation_id": rel["relation_id"], "holds": _relation_holds(rel["direction"], left["margin"], right["margin"]), "margin_delta_left_minus_right": round(left["margin"]-right["margin"], 6)})
            out[rid][mid] = {"preserved_count": sum(r["holds"] for r in rows), "total": len(rows), "rows": rows}
    return out


def _collisions(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    mid, out = _math_id(predecessor, "DETERMINISTIC_MARGIN"), {}
    for probe in sorted(spec["collision_probes"], key=lambda x: x["probe_id"]):
        rows = {}
        for rid in sorted(spec["representation_candidate_refs"]):
            left = evaluate_case(spec, predecessor, rid, mid, probe["actor_left"], probe["task_id"])
            right = evaluate_case(spec, predecessor, rid, mid, probe["actor_right"], probe["task_id"])
            delta = round(left["margin"] - right["margin"], 6)
            rows[rid] = {"margin_delta_left_minus_right": delta, "collides": abs(delta) <= 1e-9, "distinguishes": abs(delta) > 1e-9}
        out[probe["probe_id"]] = {"semantic_axis": probe["semantic_axis"], "candidate_rows": rows, "distinguishing_candidates_observed": sorted(k for k,v in rows.items() if v["distinguishes"]), "colliding_candidates_observed": sorted(k for k,v in rows.items() if v["collides"])}
    return out


def _genres(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    mid, actors, out = _math_id(predecessor, "DETERMINISTIC_MARGIN"), _heldout(spec)[0], {}
    for fixture in sorted(spec["genre_extension_fixtures"], key=lambda x: x["extension_id"]):
        rows = {}
        for rid in sorted(spec["representation_candidate_refs"]):
            before = evaluate_case(spec, predecessor, rid, mid, fixture["actor_id"], fixture["base_task_id"])
            mutated = copy.deepcopy(spec)
            actor = next(x for x in mutated["held_out_actors"] if x["actor_id"] == fixture["actor_id"])
            ext = actor["extension_inputs"][fixture["genre"].lower()]
            for key in ext: ext[key] = min(100, float(ext[key]) + 7)
            after = evaluate_case(mutated, predecessor, rid, mid, fixture["actor_id"], fixture["base_task_id"])
            extension = evaluate_case(spec, predecessor, rid, mid, fixture["actor_id"], fixture["base_task_id"], extension_fixture=fixture)
            rows[rid] = {"mundane_ignores_extension_mutation": semantic_receipt_signature(before) == semantic_receipt_signature(after), "base_representation_snapshot_digest": _hash(actors[fixture["actor_id"]]["representations"][rid]), "extension_receipt": extension}
        out[fixture["extension_id"]] = {"genre": fixture["genre"], "rows": rows}
    return out


def _robustness(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    grid, out = spec["parameter_perturbation_grid"], {}
    for rid in sorted(spec["representation_candidate_refs"]):
        out[rid] = {}
        for mid in sorted(spec["math_policy_candidate_refs"]):
            relation_rows = []
            for rel in sorted(spec["qualitative_relations"], key=lambda x: x["relation_id"]):
                bl = evaluate_case(spec, predecessor, rid, mid, rel["left_actor"], rel["task_id"])["margin"]
                br = evaluate_case(spec, predecessor, rid, mid, rel["right_actor"], rel["task_id"])["margin"]
                baseline_delta, total, preserved, stable, reversals = bl-br, 0, 0, 0, []
                for lo in grid["actor_offsets"]:
                    for ro in grid["actor_offsets"]:
                        for do in grid["difficulty_offsets"]:
                            for wf in grid["weight_scale_factors"]:
                                total += 1
                                left = evaluate_case(spec, predecessor, rid, mid, rel["left_actor"], rel["task_id"], actor_offset=lo, difficulty_offset=do, weight_scale_factor=wf)
                                right = evaluate_case(spec, predecessor, rid, mid, rel["right_actor"], rel["task_id"], actor_offset=ro, difficulty_offset=do, weight_scale_factor=wf)
                                delta = left["margin"] - right["margin"]
                                if _relation_holds(rel["direction"], left["margin"], right["margin"]): preserved += 1
                                else: reversals.append({"left_actor_offset": lo, "right_actor_offset": ro, "difficulty_offset": do, "weight_scale_factor": wf, "margin_delta_left_minus_right": round(delta,6)})
                                stable += abs(delta-baseline_delta) <= float(grid["stability_band"])
                fraction = preserved / total
                relation_rows.append({"relation_id": rel["relation_id"], "preserved": preserved, "total": total, "preservation_fraction": round(fraction,6), "margin_band_stability_fraction": round(stable/total,6), "reversal_locations": reversals, "fragile": fraction < float(grid["fragile_reversal_threshold"])})
            out[rid][mid] = {"relations": relation_rows, "mean_preservation_fraction": round(sum(x["preservation_fraction"] for x in relation_rows)/len(relation_rows),6), "fragile_relation_count": sum(x["fragile"] for x in relation_rows)}
    return out


def _burden(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    reps, maths = _maps(predecessor)
    return {
        "representations": {rid: {"durable_dimension_count": len(reps[rid]["dimensions"]), "heldout_representation_weight_count": sum(len(t["representation_weights"][rid]) for t in spec["held_out_tasks"]), "independently_named_base_dimensions": sorted(reps[rid]["dimensions"])} for rid in sorted(spec["representation_candidate_refs"])},
        "math_policies": {mid: {"kind": maths[mid]["kind"], "probability_bucket_tuning_required": maths[mid]["kind"] == "BOUNDED_SEEDED_STOCHASTIC", "bottleneck_weight_tuning_required": maths[mid]["kind"] == "TAGGED_PRIORITY", "condition_stack_interaction": "GLOBAL_MULTIPLICATIVE" if maths[mid]["kind"] == "ADDITIVE_MULTIPLICATIVE_STACK" else "LOCAL_OR_NONE"} for mid in sorted(spec["math_policy_candidate_refs"])},
    }


def _math_diagnostics(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    reps, maths = _maps(predecessor)
    diag = spec["math_diagnostic_cases"]
    matching = [rid for rid,row in reps.items() if row.get("family") == diag["representation_family"]]
    if len(matching) != 1: raise RobustnessSpecError("diagnostic representation not unique")
    rid, results = matching[0], {}
    for mid in sorted(spec["math_policy_candidate_refs"]):
        monotonic = True
        for case in diag["monotonic_cases"]:
            margins = [evaluate_case(spec, predecessor, rid, mid, case["actor_id"], case["task_id"], actor_offset=o)["margin"] for o in (-5,0,5)]
            monotonic &= all(a <= b for a,b in zip(margins,margins[1:]))
        reasoning, tool = diag["reasoning_isolation_case"], diag["relevant_tool_condition_case"]
        rb = evaluate_case(spec, predecessor, rid, mid, reasoning["actor_id"], reasoning["task_id"])
        rc = evaluate_case(spec, predecessor, rid, mid, reasoning["actor_id"], reasoning["task_id"], condition_id=reasoning["condition_id"])
        tb = evaluate_case(spec, predecessor, rid, mid, tool["actor_id"], tool["task_id"])
        tc = evaluate_case(spec, predecessor, rid, mid, tool["actor_id"], tool["task_id"], condition_id=tool["condition_id"])
        replay = True
        if maths[mid]["kind"] == "BOUNDED_SEEDED_STOCHASTIC":
            replay = tb == evaluate_case(spec, predecessor, rid, mid, tool["actor_id"], tool["task_id"]) and tb["random_receipt"] is not None
        results[mid] = {"kind": maths[mid]["kind"], "monotonic_on_heldout_offsets": bool(monotonic), "unrelated_condition_leaves_reasoning_margin_unchanged": rb["margin"] == rc["margin"], "relevant_condition_changes_tool_margin": tb["margin"] != tc["margin"], "tool_condition_penalty": round(tb["margin"]-tc["margin"],6), "stochastic_exact_replay_if_applicable": replay, "probability_calibration_claimed": False}
    baseline = next(row["tool_condition_penalty"] for row in results.values() if row["kind"] == "DETERMINISTIC_MARGIN")
    for row in results.values(): row["excess_tool_condition_penalty_vs_deterministic"] = round(row["tool_condition_penalty"]-baseline,6)
    return results


def _recommendations(spec: Mapping[str, Any], predecessor: Mapping[str, Any], collisions: Mapping[str, Any], robustness: Mapping[str, Any], diagnostics: Mapping[str, Any]) -> dict[str, Any]:
    det = _math_id(predecessor, "DETERMINISTIC_MARGIN")
    structural = {}
    for rid in sorted(spec["representation_candidate_refs"]):
        row = robustness[rid][det]
        structural[rid] = {"collision_coverage": sum(p["candidate_rows"][rid]["distinguishes"] for p in collisions.values()), "collision_total": len(collisions), "fragile_relation_count": row["fragile_relation_count"], "mean_preservation_fraction": row["mean_preservation_fraction"]}
    resolvers = [rid for rid,row in structural.items() if row["collision_coverage"] == row["collision_total"] and row["fragile_relation_count"] == 0 and row["mean_preservation_fraction"] >= .95]
    attr = "KEEP_ATTR_OPEN"
    if len(resolvers) == 1:
        burdens = _burden(spec, predecessor)["representations"]
        winner = burdens[resolvers[0]]
        materially_larger = winner["durable_dimension_count"] > min(x["durable_dimension_count"] for x in burdens.values()) + 2 or winner["heldout_representation_weight_count"] > min(x["heldout_representation_weight_count"] for x in burdens.values()) + 4
        if not materially_larger: attr = f"NARROW_ATTR_TO_{resolvers[0]}"
    stochastic = _math_id(predecessor, "BOUNDED_SEEDED_STOCHASTIC")
    det_ok = diagnostics[det]["monotonic_on_heldout_offsets"] and diagnostics[det]["unrelated_condition_leaves_reasoning_margin_unchanged"] and diagnostics[det]["relevant_condition_changes_tool_margin"]
    math_rec = "RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN_SUBSTRATE_WITH_SEPARATE_STOCHASTIC_TUNING" if det_ok and diagnostics[stochastic]["stochastic_exact_replay_if_applicable"] else "KEEP_MATH_OPEN"
    return {"ATTR": attr, "MATH": math_rec, "candidate_structural_evidence": structural, "resolution_authority": False, "open_decisions_mutated": False}


def _normalized(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    s = copy.deepcopy(spec)
    for key in ("representation_candidate_refs","math_policy_candidate_refs","predecessor_task_ids","overfit_guards"): s[key] = sorted(s[key])
    for key,idkey in (("held_out_actors","actor_id"),("held_out_tasks","task_id"),("qualitative_relations","relation_id"),("collision_probes","probe_id"),("genre_extension_fixtures","extension_id"),("condition_probes","condition_id")):
        s[key] = sorted(s[key], key=lambda x:x[idkey])
    p = {"representation_candidates": sorted(copy.deepcopy(predecessor["representation_candidates"]),key=lambda x:x["candidate_id"]), "math_policy_candidates": sorted(copy.deepcopy(predecessor["math_policy_candidates"]),key=lambda x:x["candidate_id"])}
    return s,p


def run_evaluation(spec: Mapping[str, Any], predecessor: Mapping[str, Any]) -> dict[str, Any]:
    validate_inputs(spec, predecessor)
    pristine_s, pristine_p = copy.deepcopy(spec), copy.deepcopy(predecessor)
    relations, collisions, genres = _relations(spec, predecessor), _collisions(spec, predecessor), _genres(spec, predecessor)
    robustness, burden, diagnostics = _robustness(spec, predecessor), _burden(spec, predecessor), _math_diagnostics(spec, predecessor)
    recommendations = _recommendations(spec, predecessor, collisions, robustness, diagnostics)
    if spec != pristine_s or predecessor != pristine_p: raise RobustnessSpecError("hidden mutation")
    ns,np = _normalized(spec, predecessor)
    return {
        "suite_id": spec["suite_id"], "suite_version": spec["suite_version"], "status": spec["status"], "release_base": spec["release_base"],
        "held_out_task_count": len(spec["held_out_tasks"]), "held_out_task_semantic_digests": sorted(_hash(_task_semantics(t)) for t in spec["held_out_tasks"]),
        "qualitative_relation_evidence": relations, "representation_collision_evidence": collisions, "genre_extension_pressure": genres,
        "parameter_robustness": robustness, "parameter_burden": burden, "math_policy_diagnostics": diagnostics, "recommendations": recommendations,
        "overfit_guards": {"heldout_declared_before_interpretation": True, "candidate_specific_task_omission": False, "expected_winner_field_present": False, "id_names_excluded_from_stochastic_seed_material": True, "hidden_global_mutation": False},
        "evidence_limits": {"synthetic_corpus": True, "player_fairness_calibrated": False, "probability_buckets_calibrated": False, "architecture_invariants_can_be_tested": True, "later_ruleset_tuning_still_required": True},
        "governance_locks": copy.deepcopy(spec["governance_locks"]),
        "provenance": {"predecessor_accepted_head": spec["predecessor"]["accepted_head"], "predecessor_merge_commit": spec["predecessor"]["merge_commit"], "predecessor_candidate_registry_digest": _hash(np), "cap_eval_002_spec_digest": _hash(ns), "serialization": spec["provenance"]["serialization"]},
    }


def main() -> None:
    spec, predecessor = load_inputs()
    print(canonical_json(run_evaluation(spec, predecessor)))


if __name__ == "__main__":
    main()
