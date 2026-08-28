"""I8D Stage A semantic evidence repair (R1).

This module supersedes Stage A v1 for future branch-evidence evaluation while
preserving the historical v1 implementation and package schema for provenance.

The repair is evaluation-only. It narrows caller-supplied evidence references to
source-kind-specific semantic domains and mechanically couples diagnostic
classification to the axis evidence that actually materializes those refs.
It does not create world truth, legality, Storylet realization, PX authority,
a production BranchQuality contract, or a universal score.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any

from awrse.model import freeze_value, thaw_value
import evals.i8d_branch_quality_evidence_experiment as v1

I8D_STAGE_A_R1_SEMANTIC_REPAIR = True
HISTORICAL_STAGE_A_V1_RETAINED = True
HISTORICAL_STAGE_A_V1_NOT_CURRENT_FOR_DOWNSTREAM_EVIDENCE = True
NO_REINTERPRETATION_OF_V1_PACKAGES = True
NO_BRANCH_QUALITY_PRODUCTION_CONTRACT = True
NO_UNIVERSAL_QUALITY_SCORE = True
NO_PX_RANKING_OR_WEIGHTS = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_RETCON_RESURRECTION_OR_RECONVERGENCE = True
NO_LLM_DIRECTOR_RENDERER_AUTHORITY = True
NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

HISTORICAL_V1_PACKAGE_SCHEMA = "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-1"
REPAIRED_PACKAGE_SCHEMA = "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-2"
_REPAIR_AUTHORITY_CLASS = (
    "EVALUATION_EVIDENCE_ONLY_NOT_LEGALITY_WORLD_OR_PX_AUTHORITY"
)
_REPAIR_FIXTURE_AUTHORITY_CLASS = (
    "BOUNDED_EVAL_FIXTURE_ONLY_NOT_WORLD_OR_PX_EVIDENCE"
)
_SOURCE_KINDS = {
    "I5A_INFORMATION_OPPORTUNITY",
    "I7A_WORLD_ECHO",
    "I8C_STORYLET",
}
_MEANINGFUL_AXIS = "meaningful_state_information_relationship_delta"
_REPETITION_AXIS = "contrivance_repetition_risk"
_EXPECTED_AXES = (
    "causal_world_integrity",
    "character_relationship_continuity",
    "agency_legibility",
    "knowledge_provenance_integrity",
    "genre_theme_design_fit",
    "meaningful_state_information_relationship_delta",
    "setup_promise_anchor_continuity",
    "recoverable_thread_availability",
    "contrivance_repetition_risk",
    "legal_dead_end_opportunity_scarcity_risk",
)

BranchEvidenceExperimentFixture = v1.BranchEvidenceExperimentFixture
BranchEvidenceExperimentResult = v1.BranchEvidenceExperimentResult


def _canonical_json(value: Any) -> str:
    return v1._canonical_json(value)


def _sha256(value: Any) -> str:
    return v1._sha256(value)


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _require_string(value: Any, code: str) -> str:
    return v1._require_string(value, code)


def _require_sequence(value: Any, code: str) -> tuple[Any, ...]:
    return v1._require_sequence(value, code)


def _strings(value: Any, code: str) -> tuple[str, ...]:
    return tuple(
        _require_string(item, code)
        for item in _require_sequence(value, code)
    )


def _load_repair_guard() -> tuple[str, str, str]:
    parent = v1._load_governance()
    if v1._PACKAGE_SCHEMA != HISTORICAL_V1_PACKAGE_SCHEMA:
        raise ValueError("I8D_R1_HISTORICAL_V1_SCHEMA_DRIFT")
    if set(v1._SOURCE_KINDS) != _SOURCE_KINDS:
        raise ValueError("I8D_R1_HISTORICAL_SOURCE_KIND_DRIFT")
    if tuple(v1._AXIS_NAMES) != _EXPECTED_AXES:
        raise ValueError("I8D_R1_HISTORICAL_AXIS_SHAPE_DRIFT")
    if v1._AUTHORITY_CLASS != _REPAIR_AUTHORITY_CLASS:
        raise ValueError("I8D_R1_HISTORICAL_AUTHORITY_CLASS_DRIFT")
    if v1._FIXTURE_AUTHORITY_CLASS != _REPAIR_FIXTURE_AUTHORITY_CLASS:
        raise ValueError("I8D_R1_HISTORICAL_FIXTURE_AUTHORITY_DRIFT")
    return parent


def _i5_semantic_domains(source_material: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    source_event_id = _require_string(
        source_material.get("source_event_id"),
        "I8D_R1_I5_SOURCE_EVENT_ID_REQUIRED",
    )
    packet = source_material.get("information_packet")
    if not isinstance(packet, Mapping):
        raise ValueError("I8D_R1_I5_INFORMATION_PACKET_REQUIRED")

    source_fact_refs = set(
        _strings(
            packet.get("source_fact_or_event_refs"),
            "I8D_R1_I5_SOURCE_FACT_REFS_REQUIRED",
        )
    )
    source_provenance_refs = set(
        _strings(packet.get("source_refs"), "I8D_R1_I5_SOURCE_REFS_REQUIRED")
    )
    if source_event_id not in source_fact_refs:
        raise ValueError("I8D_R1_I5_SOURCE_EVENT_NOT_IN_TYPED_FACT_REFS")

    meaningful = {source_event_id} | source_fact_refs | source_provenance_refs

    repetition: set[str] = set()
    info_id = packet.get("info_id")
    if isinstance(info_id, str) and info_id.strip():
        repetition.add(info_id)

    candidate = source_material.get("encounter_candidate")
    if candidate is not None:
        if not isinstance(candidate, Mapping):
            raise ValueError("I8D_R1_I5_ENCOUNTER_CANDIDATE_INVALID")
        encounter_id = candidate.get("encounter_id")
        if isinstance(encounter_id, str) and encounter_id.strip():
            repetition.add(encounter_id)
    return meaningful, repetition


def _i7_semantic_domains(source_material: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    canonical_facts = set(
        _strings(
            source_material.get("canonical_fact_refs"),
            "I8D_R1_I7_CANONICAL_FACT_REFS_REQUIRED",
        )
    )
    if not canonical_facts:
        raise ValueError("I8D_R1_I7_CANONICAL_FACT_REFS_EMPTY")

    source_event_id = _require_string(
        source_material.get("source_event_id"),
        "I8D_R1_I7_SOURCE_EVENT_ID_REQUIRED",
    )
    if source_event_id not in canonical_facts:
        raise ValueError("I8D_R1_I7_SOURCE_EVENT_NOT_CANONICAL_FACT")

    opportunity = source_material.get("world_echo_opportunity")
    if not isinstance(opportunity, Mapping):
        raise ValueError("I8D_R1_I7_WORLD_ECHO_OPPORTUNITY_REQUIRED")
    opportunity_refs = set(
        _strings(
            opportunity.get("source_event_or_delta_refs"),
            "I8D_R1_I7_OPPORTUNITY_SOURCE_REFS_REQUIRED",
        )
    )
    if not opportunity_refs or not opportunity_refs <= canonical_facts:
        raise ValueError("I8D_R1_I7_OPPORTUNITY_REFS_OUTSIDE_CANONICAL_FACTS")

    novelty_key = _require_string(
        source_material.get("novelty_key"),
        "I8D_R1_I7_NOVELTY_KEY_REQUIRED",
    )
    if opportunity.get("novelty_key") != novelty_key:
        raise ValueError("I8D_R1_I7_NOVELTY_KEY_BINDING_DRIFT")

    return canonical_facts, {novelty_key}


def _i8_semantic_domains(source_material: Mapping[str, Any]) -> tuple[set[str], set[str]]:
    evidence = _strings(
        source_material.get("eligibility_evidence"),
        "I8D_R1_I8_ELIGIBILITY_EVIDENCE_REQUIRED",
    )
    meaningful: set[str] = set()
    typed_prefixes = ("KNOWLEDGE_FACT:", "WORLD_EVENT:")
    for token in evidence:
        for prefix in typed_prefixes:
            if token.startswith(prefix) and len(token) > len(prefix):
                meaningful.add(token[len(prefix) :])
                break

    repetition: set[str] = {
        _require_string(
            source_material.get("storylet_id"),
            "I8D_R1_I8_STORYLET_ID_REQUIRED",
        )
    }
    callback_id = source_material.get("source_callback_concept_id")
    if callback_id is not None:
        repetition.add(
            _require_string(callback_id, "I8D_R1_I8_CALLBACK_CONCEPT_ID_INVALID")
        )
    return meaningful, repetition


def _semantic_reference_domains(
    source_kind: str,
    source_material: Mapping[str, Any],
) -> dict[str, tuple[str, ...]]:
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_R1_SOURCE_KIND_UNSUPPORTED")
    if not isinstance(source_material, Mapping):
        raise TypeError("I8D_R1_SOURCE_MATERIAL_MAPPING_REQUIRED")
    if source_kind == "I5A_INFORMATION_OPPORTUNITY":
        meaningful, repetition = _i5_semantic_domains(source_material)
    elif source_kind == "I7A_WORLD_ECHO":
        meaningful, repetition = _i7_semantic_domains(source_material)
    else:
        meaningful, repetition = _i8_semantic_domains(source_material)
    return {
        "meaningful_delta_refs": tuple(sorted(meaningful)),
        "repetition_keys": tuple(sorted(repetition)),
    }


def _normalize_fixture(
    fixture: BranchEvidenceExperimentFixture,
    *,
    domains: Mapping[str, Sequence[str]],
) -> BranchEvidenceExperimentFixture:
    meaningful, threads, repetition_key = v1._validate_fixture_intrinsics(fixture)
    meaningful_domain = set(
        _strings(
            domains.get("meaningful_delta_refs"),
            "I8D_R1_MEANINGFUL_DOMAIN_REQUIRED",
        )
    )
    repetition_domain = set(
        _strings(
            domains.get("repetition_keys"),
            "I8D_R1_REPETITION_DOMAIN_REQUIRED",
        )
    )

    for ref in meaningful:
        if ref not in meaningful_domain:
            raise ValueError(
                f"I8D_R1_MEANINGFUL_DELTA_REF_NOT_IN_SEMANTIC_DOMAIN:{ref}"
            )
    if repetition_key is not None and repetition_key not in repetition_domain:
        raise ValueError(
            f"I8D_R1_REPETITION_KEY_NOT_IN_SEMANTIC_DOMAIN:{repetition_key}"
        )

    return BranchEvidenceExperimentFixture(
        fixture_id=fixture.fixture_id,
        authored_design_fit=fixture.authored_design_fit,
        meaningful_delta_refs=tuple(sorted(meaningful)),
        recoverable_thread_refs=tuple(sorted(threads)),
        repetition_key=repetition_key,
        prior_occurrence_count=fixture.prior_occurrence_count,
        authority_class=fixture.authority_class,
    )


def _repetition_detected(
    source_kind: str,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> bool:
    if fixture.prior_occurrence_count > 0:
        return True
    if source_kind == "I7A_WORLD_ECHO":
        realization = source_material.get("realization")
        return (
            isinstance(realization, Mapping)
            and realization.get("suppression_reason") == "NOVELTY_ALREADY_SEEN"
        )
    return False


def _diagnostic_class(
    *,
    source_kind: str,
    source_status: str,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> str:
    if source_status in {"NO_VALID_OPPORTUNITY", "NO_VALID_STORYLET"}:
        return "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    if source_kind == "I7A_WORLD_ECHO" and source_status == "SILENCE":
        if _repetition_detected(source_kind, source_material, fixture):
            return "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
        return "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    if (
        fixture.authored_design_fit == "THIN"
        and not fixture.meaningful_delta_refs
        and not fixture.recoverable_thread_refs
    ):
        return "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
    return "ROBUST_BRANCH_EVIDENCE"


def _validated_axes(
    *,
    source_kind: str,
    source_status: str,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> tuple[dict[str, Any], str, tuple[str, ...], tuple[str, ...]]:
    axes, _v1_diagnostic, strengths, risks = v1._validated_axes(
        source_kind=source_kind,
        source_status=source_status,
        source_material=source_material,
        fixture=fixture,
    )

    if source_kind == "I8C_STORYLET":
        if fixture.meaningful_delta_refs:
            axes[_MEANINGFUL_AXIS] = v1._axis(
                "SUPPORTED",
                fixture.meaningful_delta_refs,
                (
                    "TYPED_STORYLET_EVENT_OR_KNOWLEDGE_FACT_DELTA_IS_VISIBLE_"
                    "WITHOUT_REALIZATION_OR_FORCED_PAYOFF"
                ),
            )
        else:
            axes[_MEANINGFUL_AXIS] = v1._axis(
                "NOT_APPLICABLE",
                (),
                "NO_TYPED_STORYLET_EVENT_OR_KNOWLEDGE_FACT_DELTA_SELECTED",
            )

    diagnostic = _diagnostic_class(
        source_kind=source_kind,
        source_status=source_status,
        source_material=source_material,
        fixture=fixture,
    )
    _assert_axis_diagnostic_consistency(
        source_kind=source_kind,
        source_status=source_status,
        fixture=fixture,
        axes=axes,
        diagnostic=diagnostic,
        source_material=source_material,
    )
    return axes, diagnostic, strengths, risks


def _assert_axis_diagnostic_consistency(
    *,
    source_kind: str,
    source_status: str,
    fixture: BranchEvidenceExperimentFixture,
    axes: Mapping[str, Any],
    diagnostic: str,
    source_material: Mapping[str, Any],
) -> None:
    if set(axes) != set(_EXPECTED_AXES):
        raise ValueError("I8D_R1_AXIS_SHAPE_DRIFT")

    meaningful_axis = axes.get(_MEANINGFUL_AXIS)
    repetition_axis = axes.get(_REPETITION_AXIS)
    if not isinstance(meaningful_axis, Mapping) or not isinstance(
        repetition_axis, Mapping
    ):
        raise ValueError("I8D_R1_REQUIRED_AXIS_MISSING")

    if fixture.meaningful_delta_refs:
        if meaningful_axis.get("assessment") != "SUPPORTED":
            raise ValueError("I8D_R1_MEANINGFUL_REFS_WITHOUT_SUPPORTED_AXIS")
        if set(meaningful_axis.get("evidence_refs", [])) != set(
            fixture.meaningful_delta_refs
        ):
            raise ValueError("I8D_R1_MEANINGFUL_AXIS_REF_MISMATCH")
    elif source_kind == "I8C_STORYLET":
        if meaningful_axis.get("assessment") != "NOT_APPLICABLE":
            raise ValueError("I8D_R1_I8_EMPTY_MEANINGFUL_AXIS_MUST_BE_NOT_APPLICABLE")

    repetition = _repetition_detected(source_kind, source_material, fixture)
    if fixture.prior_occurrence_count > 0:
        if repetition_axis.get("assessment") != "RISK":
            raise ValueError("I8D_R1_REPETITION_HISTORY_WITHOUT_RISK_AXIS")
        expected_refs = (
            {fixture.repetition_key}
            if fixture.repetition_key is not None
            else set()
        )
        if set(repetition_axis.get("evidence_refs", [])) != expected_refs:
            raise ValueError("I8D_R1_REPETITION_AXIS_REF_MISMATCH")

    if source_status in {"NO_VALID_OPPORTUNITY", "NO_VALID_STORYLET"}:
        if diagnostic != "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE":
            raise ValueError("I8D_R1_INVALID_SOURCE_BECAME_DRAMATIC_CANDIDATE")

    if diagnostic == "THIN_BUT_LEGAL_BRANCH_EVIDENCE":
        if (
            source_kind != "I7A_WORLD_ECHO"
            or source_status != "SILENCE"
            or not repetition
        ):
            if fixture.meaningful_delta_refs or fixture.recoverable_thread_refs:
                raise ValueError("I8D_R1_THIN_DIAGNOSTIC_CONTRADICTS_FIXTURE_EVIDENCE")


def _evaluate_validated_source(
    *,
    source_kind: str,
    source_package: bytes,
    result: Any,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> tuple[BranchEvidenceExperimentResult, dict[str, tuple[str, ...]]]:
    governance = _load_repair_guard()
    metadata = v1._source_metadata(
        source_kind,
        result,
        source_material,
        source_package,
    )
    domains = _semantic_reference_domains(source_kind, source_material)
    normalized_fixture = _normalize_fixture(fixture, domains=domains)
    axes, diagnostic, strengths, risks = _validated_axes(
        source_kind=source_kind,
        source_status=metadata["status"],
        source_material=source_material,
        fixture=normalized_fixture,
    )
    identity = _sha256(
        {
            "repair_schema": REPAIRED_PACKAGE_SCHEMA,
            "governance": governance,
            "source_kind": source_kind,
            "source_package_sha256": _sha256_bytes(source_package),
            "source_reference_sha256": metadata["reference_sha256"],
            "semantic_reference_domains": {
                key: list(value) for key, value in domains.items()
            },
            "fixture": v1._fixture_material(normalized_fixture),
            "diagnostic_class": diagnostic,
            "axis_evidence": axes,
        }
    )
    repaired = BranchEvidenceExperimentResult(
        evaluation_id=f"I8D:R1:EVAL:{identity[:24]}",
        diagnostic_class=diagnostic,
        source_kind=source_kind,
        source_status=metadata["status"],
        source_world_id=metadata["world_id"],
        source_baseline_version=metadata["baseline_version"],
        source_state_version=metadata["state_version"],
        source_i1_sha256=metadata["i1_sha256"],
        source_package_sha256=_sha256_bytes(source_package),
        source_reference_sha256=metadata["reference_sha256"],
        axis_evidence=freeze_value(axes),
        integrity_failures=(),
        strengths=strengths,
        risks=risks,
        deferred_decisions=v1._DEFERRED_DECISIONS,
        authority_class=_REPAIR_AUTHORITY_CLASS,
    )
    return repaired, domains


def evaluate_branch_evidence_experiment(
    *,
    source_kind: str,
    source_package: bytes | bytearray | memoryview,
    fixture: BranchEvidenceExperimentFixture,
    caller_branch_quality_evidence: Mapping[str, Any] | None = None,
) -> BranchEvidenceExperimentResult:
    if caller_branch_quality_evidence is not None:
        raise ValueError("I8D_R1_CALLER_AUTHORED_BRANCH_QUALITY_EVIDENCE_FORBIDDEN")
    _load_repair_guard()
    source_kind = _require_string(source_kind, "I8D_R1_SOURCE_KIND_REQUIRED")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_R1_SOURCE_KIND_UNSUPPORTED")
    if not isinstance(source_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_R1_SOURCE_PACKAGE_BYTES_REQUIRED")
    v1._validate_fixture_intrinsics(fixture)
    package_bytes = bytes(source_package)
    try:
        result, source_material = v1._strict_replay_source(source_kind, package_bytes)
    except (ValueError, TypeError) as exc:
        return v1._integrity_failure_result(
            source_kind=source_kind,
            source_package=package_bytes,
            error=exc,
        )
    repaired, _ = _evaluate_validated_source(
        source_kind=source_kind,
        source_package=package_bytes,
        result=result,
        source_material=source_material,
        fixture=fixture,
    )
    return repaired


def export_branch_evidence_experiment_package(
    *,
    source_kind: str,
    source_package: bytes | bytearray | memoryview,
    fixture: BranchEvidenceExperimentFixture,
) -> bytes:
    _load_repair_guard()
    source_kind = _require_string(source_kind, "I8D_R1_SOURCE_KIND_REQUIRED")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_R1_SOURCE_KIND_UNSUPPORTED")
    if not isinstance(source_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_R1_SOURCE_PACKAGE_BYTES_REQUIRED")
    v1._validate_fixture_intrinsics(fixture)
    package_bytes = bytes(source_package)
    result, source_material = v1._strict_replay_source(source_kind, package_bytes)
    repaired, domains = _evaluate_validated_source(
        source_kind=source_kind,
        source_package=package_bytes,
        result=result,
        source_material=source_material,
        fixture=fixture,
    )
    domain_material = {key: list(value) for key, value in domains.items()}
    payload = {
        "package_schema": REPAIRED_PACKAGE_SCHEMA,
        "supersedes_schema": HISTORICAL_V1_PACKAGE_SCHEMA,
        "source_kind": source_kind,
        "source_package_sha256": _sha256_bytes(package_bytes),
        "source_package_b64": base64.b64encode(package_bytes).decode("ascii"),
        "fixture": v1._fixture_material(fixture),
        "semantic_reference_domains": domain_material,
        "semantic_reference_domains_sha256": _sha256(domain_material),
        "expected_result": v1._result_material(repaired),
    }
    return _canonical_json(
        {"payload": payload, "sha256": _sha256(payload)}
    ).encode("utf-8")


def _decode_fixture(raw: Any) -> BranchEvidenceExperimentFixture:
    expected = {
        "fixture_id",
        "authored_design_fit",
        "meaningful_delta_refs",
        "recoverable_thread_refs",
        "repetition_key",
        "prior_occurrence_count",
        "authority_class",
    }
    if not isinstance(raw, Mapping) or set(raw) != expected:
        raise ValueError("I8D_R1_FIXTURE_SCHEMA_INVALID")
    fixture = BranchEvidenceExperimentFixture(
        fixture_id=raw["fixture_id"],
        authored_design_fit=raw["authored_design_fit"],
        meaningful_delta_refs=tuple(raw["meaningful_delta_refs"]),
        recoverable_thread_refs=tuple(raw["recoverable_thread_refs"]),
        repetition_key=raw["repetition_key"],
        prior_occurrence_count=raw["prior_occurrence_count"],
        authority_class=raw["authority_class"],
    )
    v1._validate_fixture_intrinsics(fixture)
    return fixture


def replay_branch_evidence_experiment_package(
    package: bytes | bytearray | memoryview,
) -> BranchEvidenceExperimentResult:
    _load_repair_guard()
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_R1_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=v1._reject_duplicate_keys,
            parse_constant=v1._reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8D_R1_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8D_R1_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("I8D_R1_REPLAY_PAYLOAD_INVALID")
    if payload.get("package_schema") != REPAIRED_PACKAGE_SCHEMA:
        raise ValueError("I8D_R1_REPLAY_REPAIRED_SCHEMA_REQUIRED")
    if payload.get("supersedes_schema") != HISTORICAL_V1_PACKAGE_SCHEMA:
        raise ValueError("I8D_R1_REPLAY_SUPERSESSION_BINDING_DRIFT")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8D_R1_REPLAY_PACKAGE_TAMPERED")

    source_kind = _require_string(
        payload.get("source_kind"),
        "I8D_R1_SOURCE_KIND_REQUIRED",
    )
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_R1_SOURCE_KIND_UNSUPPORTED")
    encoded = _require_string(
        payload.get("source_package_b64"),
        "I8D_R1_NESTED_SOURCE_PACKAGE_REQUIRED",
    )
    try:
        source_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8D_R1_NESTED_SOURCE_PACKAGE_ENCODING_INVALID") from None
    if _sha256_bytes(source_package) != payload.get("source_package_sha256"):
        raise ValueError("I8D_R1_NESTED_SOURCE_PACKAGE_DIGEST_MISMATCH")

    fixture = _decode_fixture(payload.get("fixture"))
    result, source_material = v1._strict_replay_source(source_kind, source_package)
    rebuilt, domains = _evaluate_validated_source(
        source_kind=source_kind,
        source_package=source_package,
        result=result,
        source_material=source_material,
        fixture=fixture,
    )

    domain_material = {key: list(value) for key, value in domains.items()}
    if payload.get("semantic_reference_domains") != domain_material:
        raise ValueError("I8D_R1_REPLAY_SEMANTIC_DOMAIN_MISMATCH")
    if payload.get("semantic_reference_domains_sha256") != _sha256(domain_material):
        raise ValueError("I8D_R1_REPLAY_SEMANTIC_DOMAIN_DIGEST_MISMATCH")
    if payload.get("expected_result") != v1._result_material(rebuilt):
        raise ValueError("I8D_R1_REPLAY_RESULT_MATERIALIZATION_MISMATCH")
    return rebuilt
