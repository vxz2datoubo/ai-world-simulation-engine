"""I8D Stage A2 held-out branch-evidence stability experiment.

This module compares strictly replay-valid I8D Stage A experiment packages.  It
asks whether a small candidate core of authority-grounded diagnostic axes stays
stable when only non-authority metadata changes, and whether expected upstream
status changes affect only the core semantics they are allowed to affect.

Stage A2 is evaluation evidence only.  It does not create a BranchQuality
production contract, score or rank a branch, legalize a Storylet/opportunity,
mutate world or knowledge state, resolve PX weights, or grant Director/renderer
or LLM authority.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from typing import Any

from awrse.model import freeze_value, thaw_value
import evals.i8d_branch_quality_evidence_experiment as i8d_stage_a

I8D_STAGE_A2_EVALUATION_ONLY = True
NO_STAGE_B_PRODUCTION_INTERFACE = True
NO_BRANCH_QUALITY_CANONICAL_TYPE = True
NO_UNIVERSAL_QUALITY_SCORE = True
NO_PX_RANKING_OR_WEIGHTS = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_RETCON_RESURRECTION_OR_RECONVERGENCE = True
NO_LLM_DIRECTOR_RENDERER_AUTHORITY = True
NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_CORE_AXES = (
    "causal_world_integrity",
    "agency_legibility",
    "knowledge_provenance_integrity",
    "legal_dead_end_opportunity_scarcity_risk",
)
_MECHANISM_AXES = (
    "character_relationship_continuity",
    "meaningful_state_information_relationship_delta",
    "setup_promise_anchor_continuity",
    "contrivance_repetition_risk",
)
_AUTHORED_AXES = (
    "genre_theme_design_fit",
    "recoverable_thread_availability",
)
_ALL_AXES = _CORE_AXES + _MECHANISM_AXES + _AUTHORED_AXES
_ALLOWED_COMPARISON_KINDS = {
    "IDENTICAL_CONTROL",
    "AUTHORED_DESIGN_METADATA_ONLY",
    "RECOVERABLE_THREAD_METADATA_ONLY",
    "REPETITION_HISTORY_ONLY",
    "UPSTREAM_STATUS_CHANGE",
    "CROSS_SOURCE_CORE_SHAPE",
}
_ALLOWED_OUTCOMES = {
    "CORE_STABLE_UNDER_IDENTICAL_CONTROL",
    "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE",
    "CORE_STABLE_UNDER_REPETITION_HISTORY_CHANGE",
    "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE",
    "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS",
    "CORE_INTEGRITY_FAILURE",
    "COMPARISON_NOT_VALID",
}
_ALLOWED_AXIS_ASSESSMENTS = {
    "SUPPORTED",
    "THIN",
    "ABSENT",
    "RISK",
    "INTEGRITY_FAILURE",
    "NOT_APPLICABLE",
}
_DEFERRED_DECISIONS = ("OD-CLUE-QUALITY-001", "OD-PX-SCORING-001")
_STAGE_A_SCHEMA = "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-1"
_PACKAGE_SCHEMA = "AWRSE-I8D-STAGE-A2-AXIS-STABILITY-1"
_AUTHORITY_CLASS = "STAGE_A2_EVALUATION_OBSERVATION_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY"
_FIXTURE_AUTHORITY_CLASS = "STAGE_A2_COMPARISON_FIXTURE_ONLY_NOT_SOURCE_OR_QUALITY_AUTHORITY"


@dataclass(frozen=True)
class StageA2ComparisonFixture:
    comparison_id: str
    comparison_kind: str
    authority_class: str = _FIXTURE_AUTHORITY_CLASS


@dataclass(frozen=True)
class MinimalCoreStabilityObservation:
    observation_id: str
    outcome: str
    comparison_kind: str
    left_stage_a_sha256: str
    right_stage_a_sha256: str
    left_evaluation_id: str | None
    right_evaluation_id: str | None
    left_source_kind: str | None
    right_source_kind: str | None
    left_source_status: str | None
    right_source_status: str | None
    left_source_package_sha256: str | None
    right_source_package_sha256: str | None
    left_source_i1_sha256: str | None
    right_source_i1_sha256: str | None
    left_core_axes: Mapping[str, Any]
    right_core_axes: Mapping[str, Any]
    changed_core_assessments: tuple[str, ...]
    changed_core_material: tuple[str, ...]
    changed_mechanism_axes: tuple[str, ...]
    changed_authored_axes: tuple[str, ...]
    left_not_applicable_mechanism_axes: tuple[str, ...]
    right_not_applicable_mechanism_axes: tuple[str, ...]
    integrity_failures: tuple[str, ...]
    deferred_decisions: tuple[str, ...]
    authority_class: str


def _canonical_json(value: Any) -> str:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        )
    except (TypeError, ValueError) as exc:
        raise ValueError("I8D_A2_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _require_sequence(value: Any, code: str) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError(code)
    return tuple(value)


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"I8D_A2_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I8D_A2_JSON_NONFINITE:{value}")


def _validate_governance() -> None:
    # Stage A owns the canonical governance guard. Reusing it ensures Stage A2
    # cannot quietly reinterpret AF-F/AF-G authority, promote BranchQuality, or
    # close the still-open clue-quality/PX decisions.
    i8d_stage_a._load_governance()


def _validate_fixture(fixture: StageA2ComparisonFixture) -> StageA2ComparisonFixture:
    if not isinstance(fixture, StageA2ComparisonFixture):
        raise TypeError("I8D_A2_COMPARISON_FIXTURE_REQUIRED")
    if fixture.authority_class != _FIXTURE_AUTHORITY_CLASS:
        raise ValueError("I8D_A2_FIXTURE_AUTHORITY_ESCALATION")
    comparison_id = _require_string(fixture.comparison_id, "I8D_A2_COMPARISON_ID_REQUIRED")
    comparison_kind = _require_string(
        fixture.comparison_kind, "I8D_A2_COMPARISON_KIND_REQUIRED"
    )
    if comparison_kind not in _ALLOWED_COMPARISON_KINDS:
        raise ValueError("I8D_A2_COMPARISON_KIND_UNSUPPORTED")
    return StageA2ComparisonFixture(
        comparison_id=comparison_id,
        comparison_kind=comparison_kind,
        authority_class=fixture.authority_class,
    )


def _fixture_material(fixture: StageA2ComparisonFixture) -> dict[str, Any]:
    return {
        "comparison_id": fixture.comparison_id,
        "comparison_kind": fixture.comparison_kind,
        "authority_class": fixture.authority_class,
    }


def _parse_stage_a_payload(package: bytes) -> Mapping[str, Any]:
    try:
        envelope = json.loads(
            package.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8D_A2_STAGE_A_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8D_A2_STAGE_A_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _STAGE_A_SCHEMA:
        raise ValueError("I8D_A2_STAGE_A_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8D_A2_STAGE_A_OUTER_DIGEST_MISMATCH")
    return payload


def _stage_a_fixture(payload: Mapping[str, Any]) -> Mapping[str, Any]:
    fixture = payload.get("fixture")
    if not isinstance(fixture, Mapping):
        raise ValueError("I8D_A2_STAGE_A_FIXTURE_MISSING")
    expected = {
        "fixture_id",
        "authored_design_fit",
        "meaningful_delta_refs",
        "recoverable_thread_refs",
        "repetition_key",
        "prior_occurrence_count",
        "authority_class",
    }
    if set(fixture) != expected:
        raise ValueError("I8D_A2_STAGE_A_FIXTURE_SCHEMA_INVALID")
    return fixture


def _axis_material(result: Any) -> dict[str, dict[str, Any]]:
    raw = thaw_value(result.axis_evidence)
    if not isinstance(raw, Mapping) or set(raw) != set(_ALL_AXES):
        raise ValueError("I8D_A2_STAGE_A_AXIS_SHAPE_DRIFT")
    normalized: dict[str, dict[str, Any]] = {}
    for name in _ALL_AXES:
        axis = raw.get(name)
        if not isinstance(axis, Mapping) or set(axis) != {
            "assessment",
            "evidence_refs",
            "interpretation",
        }:
            raise ValueError(f"I8D_A2_STAGE_A_AXIS_SCHEMA_INVALID:{name}")
        assessment = axis.get("assessment")
        if assessment not in _ALLOWED_AXIS_ASSESSMENTS:
            raise ValueError(f"I8D_A2_STAGE_A_AXIS_ASSESSMENT_INVALID:{name}")
        refs = _require_sequence(
            axis.get("evidence_refs"), f"I8D_A2_STAGE_A_AXIS_REFS_INVALID:{name}"
        )
        normalized[name] = {
            "assessment": assessment,
            "evidence_refs": list(refs),
            "interpretation": _require_string(
                axis.get("interpretation"),
                f"I8D_A2_STAGE_A_AXIS_INTERPRETATION_INVALID:{name}",
            ),
        }
    return normalized


def _core_axes(axes: Mapping[str, Any]) -> dict[str, Any]:
    return {name: axes[name] for name in _CORE_AXES}


def _changed_axes(
    left: Mapping[str, Any], right: Mapping[str, Any], names: Sequence[str]
) -> tuple[str, ...]:
    return tuple(sorted(name for name in names if left[name] != right[name]))


def _changed_assessments(
    left: Mapping[str, Any], right: Mapping[str, Any], names: Sequence[str]
) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in names
            if left[name]["assessment"] != right[name]["assessment"]
        )
    )


def _not_applicable_mechanism_axes(axes: Mapping[str, Any]) -> tuple[str, ...]:
    return tuple(
        sorted(
            name
            for name in _MECHANISM_AXES
            if axes[name]["assessment"] == "NOT_APPLICABLE"
        )
    )


def _stage_a_fixture_diff(
    left: Mapping[str, Any], right: Mapping[str, Any]
) -> tuple[str, ...]:
    return tuple(sorted(key for key in left if left.get(key) != right.get(key)))


def _integrity_observation(
    *,
    fixture: StageA2ComparisonFixture,
    left_bytes: bytes,
    right_bytes: bytes,
    failures: Sequence[str],
) -> MinimalCoreStabilityObservation:
    failure_tuple = tuple(sorted(set(_require_string(value, "I8D_A2_FAILURE_CODE_INVALID") for value in failures)))
    identity = _sha256(
        {
            "comparison": _fixture_material(fixture),
            "left": _sha256_bytes(left_bytes),
            "right": _sha256_bytes(right_bytes),
            "failures": list(failure_tuple),
        }
    )
    return MinimalCoreStabilityObservation(
        observation_id=f"I8D:A2:INTEGRITY:{identity[:24]}",
        outcome="CORE_INTEGRITY_FAILURE",
        comparison_kind=fixture.comparison_kind,
        left_stage_a_sha256=_sha256_bytes(left_bytes),
        right_stage_a_sha256=_sha256_bytes(right_bytes),
        left_evaluation_id=None,
        right_evaluation_id=None,
        left_source_kind=None,
        right_source_kind=None,
        left_source_status=None,
        right_source_status=None,
        left_source_package_sha256=None,
        right_source_package_sha256=None,
        left_source_i1_sha256=None,
        right_source_i1_sha256=None,
        left_core_axes=freeze_value({}),
        right_core_axes=freeze_value({}),
        changed_core_assessments=(),
        changed_core_material=(),
        changed_mechanism_axes=(),
        changed_authored_axes=(),
        left_not_applicable_mechanism_axes=(),
        right_not_applicable_mechanism_axes=(),
        integrity_failures=failure_tuple,
        deferred_decisions=_DEFERRED_DECISIONS,
        authority_class=_AUTHORITY_CLASS,
    )


def _comparison_outcome(
    *,
    comparison_kind: str,
    left_result: Any,
    right_result: Any,
    left_payload: Mapping[str, Any],
    right_payload: Mapping[str, Any],
    left_axes: Mapping[str, Any],
    right_axes: Mapping[str, Any],
) -> tuple[str, tuple[str, ...]]:
    failures: list[str] = []
    changed_core_material = _changed_axes(left_axes, right_axes, _CORE_AXES)
    changed_core_assessments = _changed_assessments(left_axes, right_axes, _CORE_AXES)
    changed_mechanism = _changed_axes(left_axes, right_axes, _MECHANISM_AXES)
    changed_authored = _changed_axes(left_axes, right_axes, _AUTHORED_AXES)
    left_fixture = _stage_a_fixture(left_payload)
    right_fixture = _stage_a_fixture(right_payload)
    fixture_diff = _stage_a_fixture_diff(left_fixture, right_fixture)

    if comparison_kind == "IDENTICAL_CONTROL":
        if left_payload != right_payload or changed_core_material or changed_mechanism or changed_authored:
            failures.append("IDENTICAL_CONTROL_MATERIAL_DRIFT")
        return (
            "CORE_STABLE_UNDER_IDENTICAL_CONTROL" if not failures else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    same_source = left_result.source_package_sha256 == right_result.source_package_sha256
    same_kind = left_result.source_kind == right_result.source_kind
    same_status = left_result.source_status == right_result.source_status

    if comparison_kind == "AUTHORED_DESIGN_METADATA_ONLY":
        if not (same_source and same_kind and same_status):
            failures.append("AUTHORED_METADATA_COMPARISON_REQUIRES_IDENTICAL_SOURCE")
        if fixture_diff != ("authored_design_fit",):
            failures.append("AUTHORED_METADATA_COMPARISON_HAS_EXTRA_FIXTURE_CHANGES")
        if changed_core_material:
            failures.append("AUTHORED_METADATA_CHANGED_AUTHORITY_GROUNDED_CORE")
        if changed_mechanism:
            failures.append("AUTHORED_METADATA_CHANGED_MECHANISM_DIAGNOSTIC")
        if set(changed_authored) - {"genre_theme_design_fit"}:
            failures.append("AUTHORED_METADATA_CHANGED_UNRELATED_AUTHORED_AXIS")
        return (
            "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
            if not failures
            else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    if comparison_kind == "RECOVERABLE_THREAD_METADATA_ONLY":
        if not (same_source and same_kind and same_status):
            failures.append("THREAD_METADATA_COMPARISON_REQUIRES_IDENTICAL_SOURCE")
        if fixture_diff != ("recoverable_thread_refs",):
            failures.append("THREAD_METADATA_COMPARISON_HAS_EXTRA_FIXTURE_CHANGES")
        if changed_core_material:
            failures.append("THREAD_METADATA_CHANGED_AUTHORITY_GROUNDED_CORE")
        if changed_mechanism:
            failures.append("THREAD_METADATA_CHANGED_MECHANISM_DIAGNOSTIC")
        if set(changed_authored) - {"recoverable_thread_availability"}:
            failures.append("THREAD_METADATA_CHANGED_UNRELATED_AUTHORED_AXIS")
        return (
            "CORE_STABLE_UNDER_NONAUTHORITY_METADATA_CHANGE"
            if not failures
            else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    if comparison_kind == "REPETITION_HISTORY_ONLY":
        if not (same_source and same_kind and same_status):
            failures.append("REPETITION_COMPARISON_REQUIRES_IDENTICAL_SOURCE")
        if not fixture_diff or set(fixture_diff) - {"repetition_key", "prior_occurrence_count"}:
            failures.append("REPETITION_COMPARISON_HAS_NON_REPETITION_FIXTURE_CHANGE")
        if changed_core_material:
            failures.append("REPETITION_HISTORY_CHANGED_AUTHORITY_GROUNDED_CORE")
        if set(changed_mechanism) - {"contrivance_repetition_risk"}:
            failures.append("REPETITION_HISTORY_CHANGED_UNRELATED_MECHANISM_AXIS")
        if changed_authored:
            failures.append("REPETITION_HISTORY_CHANGED_AUTHORED_METADATA_AXIS")
        return (
            "CORE_STABLE_UNDER_REPETITION_HISTORY_CHANGE"
            if not failures
            else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    if comparison_kind == "UPSTREAM_STATUS_CHANGE":
        if not same_kind:
            failures.append("UPSTREAM_STATUS_COMPARISON_REQUIRES_SAME_SOURCE_KIND")
        if same_source or same_status:
            failures.append("UPSTREAM_STATUS_COMPARISON_REQUIRES_DISTINCT_SOURCE_STATUS")
        if left_result.source_i1_sha256 != right_result.source_i1_sha256:
            failures.append("UPSTREAM_STATUS_COMPARISON_REQUIRES_SAME_I1_REPLAY")
        expected = {"legal_dead_end_opportunity_scarcity_risk"}
        if set(changed_core_assessments) != expected:
            failures.append("UPSTREAM_STATUS_CHANGED_UNEXPECTED_CORE_ASSESSMENTS")
        for stable_axis in (
            "causal_world_integrity",
            "agency_legibility",
            "knowledge_provenance_integrity",
        ):
            if left_axes[stable_axis]["assessment"] != right_axes[stable_axis]["assessment"]:
                failures.append(f"UPSTREAM_STATUS_DESTABILIZED_CORE:{stable_axis}")
        return (
            "EXPECTED_CORE_AXIS_CHANGE_FROM_UPSTREAM_STATUS_CHANGE"
            if not failures
            else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    if comparison_kind == "CROSS_SOURCE_CORE_SHAPE":
        if same_kind:
            failures.append("CROSS_SOURCE_COMPARISON_REQUIRES_DISTINCT_SOURCE_KINDS")
        for side_name, axes in (("LEFT", left_axes), ("RIGHT", right_axes)):
            for stable_axis in (
                "causal_world_integrity",
                "agency_legibility",
                "knowledge_provenance_integrity",
            ):
                if axes[stable_axis]["assessment"] != "SUPPORTED":
                    failures.append(f"{side_name}_CROSS_SOURCE_CORE_NOT_SUPPORTED:{stable_axis}")
            if axes["legal_dead_end_opportunity_scarcity_risk"]["assessment"] not in {
                "ABSENT",
                "RISK",
            }:
                failures.append(f"{side_name}_SCARCITY_CORE_SHAPE_INVALID")
            if any(axes[name]["assessment"] == "NOT_APPLICABLE" for name in _CORE_AXES):
                failures.append(f"{side_name}_CORE_AXIS_NOT_APPLICABLE")
        return (
            "CORE_SHAPE_STABLE_ACROSS_SOURCE_KINDS"
            if not failures
            else "COMPARISON_NOT_VALID",
            tuple(failures),
        )

    raise ValueError("I8D_A2_INTERNAL_COMPARISON_KIND_UNREACHABLE")


def _build_observation(
    *,
    left_bytes: bytes,
    right_bytes: bytes,
    left_result: Any,
    right_result: Any,
    left_payload: Mapping[str, Any],
    right_payload: Mapping[str, Any],
    fixture: StageA2ComparisonFixture,
) -> MinimalCoreStabilityObservation:
    left_axes = _axis_material(left_result)
    right_axes = _axis_material(right_result)
    outcome, failures = _comparison_outcome(
        comparison_kind=fixture.comparison_kind,
        left_result=left_result,
        right_result=right_result,
        left_payload=left_payload,
        right_payload=right_payload,
        left_axes=left_axes,
        right_axes=right_axes,
    )
    if outcome not in _ALLOWED_OUTCOMES:
        raise ValueError("I8D_A2_INTERNAL_OUTCOME_INVALID")
    changed_core_assessments = _changed_assessments(left_axes, right_axes, _CORE_AXES)
    changed_core_material = _changed_axes(left_axes, right_axes, _CORE_AXES)
    changed_mechanism = _changed_axes(left_axes, right_axes, _MECHANISM_AXES)
    changed_authored = _changed_axes(left_axes, right_axes, _AUTHORED_AXES)
    material = {
        "comparison": _fixture_material(fixture),
        "left_stage_a_sha256": _sha256_bytes(left_bytes),
        "right_stage_a_sha256": _sha256_bytes(right_bytes),
        "left_evaluation_id": left_result.evaluation_id,
        "right_evaluation_id": right_result.evaluation_id,
        "outcome": outcome,
        "changed_core_assessments": list(changed_core_assessments),
        "changed_core_material": list(changed_core_material),
        "failures": list(failures),
    }
    identity = _sha256(material)
    return MinimalCoreStabilityObservation(
        observation_id=f"I8D:A2:{identity[:24]}",
        outcome=outcome,
        comparison_kind=fixture.comparison_kind,
        left_stage_a_sha256=_sha256_bytes(left_bytes),
        right_stage_a_sha256=_sha256_bytes(right_bytes),
        left_evaluation_id=left_result.evaluation_id,
        right_evaluation_id=right_result.evaluation_id,
        left_source_kind=left_result.source_kind,
        right_source_kind=right_result.source_kind,
        left_source_status=left_result.source_status,
        right_source_status=right_result.source_status,
        left_source_package_sha256=left_result.source_package_sha256,
        right_source_package_sha256=right_result.source_package_sha256,
        left_source_i1_sha256=left_result.source_i1_sha256,
        right_source_i1_sha256=right_result.source_i1_sha256,
        left_core_axes=freeze_value(_core_axes(left_axes)),
        right_core_axes=freeze_value(_core_axes(right_axes)),
        changed_core_assessments=changed_core_assessments,
        changed_core_material=changed_core_material,
        changed_mechanism_axes=changed_mechanism,
        changed_authored_axes=changed_authored,
        left_not_applicable_mechanism_axes=_not_applicable_mechanism_axes(left_axes),
        right_not_applicable_mechanism_axes=_not_applicable_mechanism_axes(right_axes),
        integrity_failures=tuple(sorted(set(failures))),
        deferred_decisions=_DEFERRED_DECISIONS,
        authority_class=_AUTHORITY_CLASS,
    )


def evaluate_stage_a2_axis_stability(
    *,
    left_stage_a_package: bytes | bytearray | memoryview,
    right_stage_a_package: bytes | bytearray | memoryview,
    fixture: StageA2ComparisonFixture,
    caller_core_evidence: Mapping[str, Any] | None = None,
) -> MinimalCoreStabilityObservation:
    """Compare two Stage A packages without granting their diagnostics authority."""
    if caller_core_evidence is not None:
        raise ValueError("I8D_A2_CALLER_AUTHORED_CORE_EVIDENCE_FORBIDDEN")
    _validate_governance()
    fixture = _validate_fixture(fixture)
    if not isinstance(left_stage_a_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_A2_LEFT_STAGE_A_PACKAGE_BYTES_REQUIRED")
    if not isinstance(right_stage_a_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_A2_RIGHT_STAGE_A_PACKAGE_BYTES_REQUIRED")
    left_bytes = bytes(left_stage_a_package)
    right_bytes = bytes(right_stage_a_package)
    failures: list[str] = []
    try:
        left_result = i8d_stage_a.replay_branch_evidence_experiment_package(left_bytes)
        left_payload = _parse_stage_a_payload(left_bytes)
    except (ValueError, TypeError) as exc:
        failures.append(f"LEFT_STAGE_A_REJECTED:{str(exc) or exc.__class__.__name__}")
        left_result = None
        left_payload = None
    try:
        right_result = i8d_stage_a.replay_branch_evidence_experiment_package(right_bytes)
        right_payload = _parse_stage_a_payload(right_bytes)
    except (ValueError, TypeError) as exc:
        failures.append(f"RIGHT_STAGE_A_REJECTED:{str(exc) or exc.__class__.__name__}")
        right_result = None
        right_payload = None
    if failures:
        return _integrity_observation(
            fixture=fixture,
            left_bytes=left_bytes,
            right_bytes=right_bytes,
            failures=failures,
        )
    assert left_result is not None and right_result is not None
    assert left_payload is not None and right_payload is not None
    if left_result.diagnostic_class == "INTEGRITY_FAILURE_PRESENT" or right_result.diagnostic_class == "INTEGRITY_FAILURE_PRESENT":
        return _integrity_observation(
            fixture=fixture,
            left_bytes=left_bytes,
            right_bytes=right_bytes,
            failures=("STAGE_A_INTEGRITY_FAILURE_RESULT_NOT_COMPARABLE",),
        )
    return _build_observation(
        left_bytes=left_bytes,
        right_bytes=right_bytes,
        left_result=left_result,
        right_result=right_result,
        left_payload=left_payload,
        right_payload=right_payload,
        fixture=fixture,
    )


def _observation_material(observation: MinimalCoreStabilityObservation) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "observation_id": observation.observation_id,
                "outcome": observation.outcome,
                "comparison_kind": observation.comparison_kind,
                "left_stage_a_sha256": observation.left_stage_a_sha256,
                "right_stage_a_sha256": observation.right_stage_a_sha256,
                "left_evaluation_id": observation.left_evaluation_id,
                "right_evaluation_id": observation.right_evaluation_id,
                "left_source_kind": observation.left_source_kind,
                "right_source_kind": observation.right_source_kind,
                "left_source_status": observation.left_source_status,
                "right_source_status": observation.right_source_status,
                "left_source_package_sha256": observation.left_source_package_sha256,
                "right_source_package_sha256": observation.right_source_package_sha256,
                "left_source_i1_sha256": observation.left_source_i1_sha256,
                "right_source_i1_sha256": observation.right_source_i1_sha256,
                "left_core_axes": thaw_value(observation.left_core_axes),
                "right_core_axes": thaw_value(observation.right_core_axes),
                "changed_core_assessments": list(observation.changed_core_assessments),
                "changed_core_material": list(observation.changed_core_material),
                "changed_mechanism_axes": list(observation.changed_mechanism_axes),
                "changed_authored_axes": list(observation.changed_authored_axes),
                "left_not_applicable_mechanism_axes": list(observation.left_not_applicable_mechanism_axes),
                "right_not_applicable_mechanism_axes": list(observation.right_not_applicable_mechanism_axes),
                "integrity_failures": list(observation.integrity_failures),
                "deferred_decisions": list(observation.deferred_decisions),
                "authority_class": observation.authority_class,
            }
        )
    )


def export_stage_a2_axis_stability_package(
    *,
    left_stage_a_package: bytes | bytearray | memoryview,
    right_stage_a_package: bytes | bytearray | memoryview,
    fixture: StageA2ComparisonFixture,
) -> bytes:
    """Export a deterministic Stage A2 observation from strict Stage A inputs."""
    _validate_governance()
    fixture = _validate_fixture(fixture)
    if not isinstance(left_stage_a_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_A2_LEFT_STAGE_A_PACKAGE_BYTES_REQUIRED")
    if not isinstance(right_stage_a_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_A2_RIGHT_STAGE_A_PACKAGE_BYTES_REQUIRED")
    left_bytes = bytes(left_stage_a_package)
    right_bytes = bytes(right_stage_a_package)
    # Export requires both Stage A inputs to replay strictly. Integrity failures
    # remain observable through evaluate(), but are never packaged as if valid.
    i8d_stage_a.replay_branch_evidence_experiment_package(left_bytes)
    i8d_stage_a.replay_branch_evidence_experiment_package(right_bytes)
    observation = evaluate_stage_a2_axis_stability(
        left_stage_a_package=left_bytes,
        right_stage_a_package=right_bytes,
        fixture=fixture,
    )
    if observation.outcome == "CORE_INTEGRITY_FAILURE":
        raise ValueError("I8D_A2_INTEGRITY_FAILURE_NOT_EXPORTABLE")
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "fixture": _fixture_material(fixture),
        "left_stage_a_sha256": _sha256_bytes(left_bytes),
        "right_stage_a_sha256": _sha256_bytes(right_bytes),
        "left_stage_a_b64": base64.b64encode(left_bytes).decode("ascii"),
        "right_stage_a_b64": base64.b64encode(right_bytes).decode("ascii"),
        "expected_observation": _observation_material(observation),
    }
    return _canonical_json({"payload": payload, "sha256": _sha256(payload)}).encode("utf-8")


def replay_stage_a2_axis_stability_package(
    package: bytes | bytearray | memoryview,
) -> MinimalCoreStabilityObservation:
    """Strict replay prevents Stage A or nested upstream tamper laundering."""
    _validate_governance()
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_A2_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8D_A2_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8D_A2_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I8D_A2_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8D_A2_REPLAY_PACKAGE_TAMPERED")

    fixture_raw = payload.get("fixture")
    if not isinstance(fixture_raw, Mapping) or set(fixture_raw) != {
        "comparison_id",
        "comparison_kind",
        "authority_class",
    }:
        raise ValueError("I8D_A2_REPLAY_FIXTURE_SCHEMA_INVALID")
    fixture = _validate_fixture(StageA2ComparisonFixture(**dict(fixture_raw)))

    decoded: list[bytes] = []
    for side in ("left", "right"):
        encoded = _require_string(
            payload.get(f"{side}_stage_a_b64"),
            f"I8D_A2_REPLAY_{side.upper()}_STAGE_A_REQUIRED",
        )
        try:
            stage_a_bytes = base64.b64decode(encoded.encode("ascii"), validate=True)
        except (ValueError, UnicodeEncodeError):
            raise ValueError(f"I8D_A2_REPLAY_{side.upper()}_STAGE_A_ENCODING_INVALID") from None
        if _sha256_bytes(stage_a_bytes) != payload.get(f"{side}_stage_a_sha256"):
            raise ValueError(f"I8D_A2_REPLAY_{side.upper()}_STAGE_A_DIGEST_MISMATCH")
        # Do not trust a self-consistent Stage A envelope. Replay the complete
        # Stage A -> I5/I7/I8 chain before rebuilding Stage A2.
        i8d_stage_a.replay_branch_evidence_experiment_package(stage_a_bytes)
        decoded.append(stage_a_bytes)

    rebuilt = evaluate_stage_a2_axis_stability(
        left_stage_a_package=decoded[0],
        right_stage_a_package=decoded[1],
        fixture=fixture,
    )
    if rebuilt.outcome == "CORE_INTEGRITY_FAILURE":
        raise ValueError("I8D_A2_REPLAY_NESTED_INTEGRITY_FAILURE")
    if _observation_material(rebuilt) != payload.get("expected_observation"):
        raise ValueError("I8D_A2_REPLAY_OBSERVATION_MATERIALIZATION_MISMATCH")
    return rebuilt
