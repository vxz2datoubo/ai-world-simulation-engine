"""I8D Stage A branch-quality evidence discriminability experiment.

This module is evaluation evidence only. It consumes packages emitted by already
canonical bounded references (I5A, I7A, I8C), replays those references through
their own validators, and materializes inspectable diagnostic axes. It does not
create a BranchQuality production contract, assign a universal score, rank
candidates, legalize narrative opportunities, mutate world truth, or grant PX,
Director, renderer, or LLM authority.
"""
from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Any

from awrse import import_solo_replay_package
from awrse.model import freeze_value, thaw_value
import evals.i5a_information_opportunity_shadow_reference as i5a_reference
import evals.i7a_player_private_world_echo_reference as i7a_reference
import evals.i8c_storylet_eligibility_reference as i8c_reference

I8D_STAGE_A_EVALUATION_ONLY = True
NO_BRANCH_QUALITY_PRODUCTION_CONTRACT = True
NO_UNIVERSAL_QUALITY_SCORE = True
NO_PX_RANKING_OR_WEIGHTS = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_RETCON_RESURRECTION_OR_RECONVERGENCE = True
NO_LLM_DIRECTOR_RENDERER_AUTHORITY = True
NO_ENGAGEMENT_OR_RETENTION_OBJECTIVE = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_GOLDEN_PATH = _ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
_TRACEABILITY_PATH = _ROOT / "docs" / "AF001-TRACEABILITY.md"

_EXPECTED_PARENT = (
    "AWRSE-AF001-LIVING-STORY-CONTRACTS",
    "1.9.0-candidate",
    "AF001-AUTHORITY-GRAPH-1.9-I2A008@1",
)
_EXPECTED_NARRATIVE_PROFILE = {
    "canonical_data_authority": ["NONE"],
    "contract_schema_steward": "AWRSE_AF_F_CONTRACT_STEWARD",
    "producer_or_assembler": [
        "AWRSE_NARRATIVE_DESIGN_LOADER",
        "NARRATIVE_DESIGN_NON_CANONICAL",
    ],
    "downstream_consumer": ["NARRATIVE_OPPORTUNITY", "PX_RANKING", "AI_DIRECTOR"],
    "staging_authority": ["NONE"],
    "mutation_constraint": (
        "AUTHORED_NARRATIVE_CONSTRAINTS_MAY_PROPOSE_OR_FILTER_BUT_CANNOT_RETCON_CANONICAL_WORLD_TRUTH"
    ),
}
_EXPECTED_PX_PROFILE = {
    "canonical_data_authority": ["NONE"],
    "contract_schema_steward": "AWRSE_AF_G_CONTRACT_STEWARD",
    "producer_or_assembler": ["AWRSE_PX_RANKER", "PX_RANKING"],
    "downstream_consumer": ["AI_DIRECTOR", "WORLD_ACTION_AUTHORITY"],
    "staging_authority": ["NONE"],
    "mutation_constraint": (
        "PX_MAY_RANK_ONLY_ALREADY_LEGAL_CANDIDATES_AND_CANNOT_LEGALIZE_INVALID_CANDIDATES_OR_CREATE_FACTS"
    ),
}
_REQUIRED_AF_F_INVARIANTS = {
    "STORY_STRUCTURE_IS_NOT_WORLD_TRUTH",
    "AUTHORED_NARRATIVE_NE_PROMISE_HISTORY",
    "BRANCH_QUALITY_CANNOT_JUSTIFY_RETCON_OR_RESURRECTION",
}
_REQUIRED_AF_G_INVARIANTS = {
    "NO_VALID_OPPORTUNITY_IS_VALID",
    "PX_CANNOT_INVENT_FACTS_OR_INJECT_KNOWLEDGE",
}
_REQUIRED_GOLDEN_SCENARIOS = {
    "HOSTILE_PLAYER_BREAKS_PLOT",
    "PROMISE_RETURN_CALLBACK",
    "WILDERNESS_NEWS_TRAP",
    "BROKEN_DOOR_WORLD_ECHO",
}
_DEFERRED_DECISIONS = ("OD-CLUE-QUALITY-001", "OD-PX-SCORING-001")
_AXIS_NAMES = (
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
_ALLOWED_ASSESSMENTS = {
    "SUPPORTED",
    "THIN",
    "ABSENT",
    "RISK",
    "INTEGRITY_FAILURE",
    "NOT_APPLICABLE",
}
_ALLOWED_AUTHORED_FIT = {"SUPPORTED", "THIN", "NOT_APPLICABLE"}
_SOURCE_KINDS = {"I5A_INFORMATION_OPPORTUNITY", "I7A_WORLD_ECHO", "I8C_STORYLET"}
_EVIDENCE_TOKEN_PREFIXES = (
    "KNOWLEDGE_FACT:",
    "WORLD_EVENT:",
    "PRECONDITION:CALLBACK:",
    "CALLBACK:",
    "OBJECT_PRESENT:",
    "ACTIVE_SCENE_ACTOR:",
    "ROLE:PLAYER:",
    "ROLE:NPC:",
    "KNOWLEDGE_RECIPIENT:",
)
_AUTHORITY_CLASS = "EVALUATION_EVIDENCE_ONLY_NOT_LEGALITY_WORLD_OR_PX_AUTHORITY"
_FIXTURE_AUTHORITY_CLASS = "BOUNDED_EVAL_FIXTURE_ONLY_NOT_WORLD_OR_PX_EVIDENCE"
_PACKAGE_SCHEMA = "AWRSE-I8D-BRANCH-EVIDENCE-EXPERIMENT-1"


@dataclass(frozen=True)
class BranchEvidenceExperimentFixture:
    fixture_id: str
    authored_design_fit: str = "NOT_APPLICABLE"
    meaningful_delta_refs: tuple[str, ...] = ()
    recoverable_thread_refs: tuple[str, ...] = ()
    repetition_key: str | None = None
    prior_occurrence_count: int = 0
    authority_class: str = _FIXTURE_AUTHORITY_CLASS


@dataclass(frozen=True)
class BranchEvidenceExperimentResult:
    evaluation_id: str
    diagnostic_class: str
    source_kind: str
    source_status: str
    source_world_id: str | None
    source_baseline_version: str | None
    source_state_version: int | None
    source_i1_sha256: str | None
    source_package_sha256: str
    source_reference_sha256: str | None
    axis_evidence: Mapping[str, Any]
    integrity_failures: tuple[str, ...]
    strengths: tuple[str, ...]
    risks: tuple[str, ...]
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
        raise ValueError("I8D_VALUE_NOT_CANONICAL_JSON") from exc


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
            raise ValueError(f"I8D_JSON_DUPLICATE_KEY:{key}")
        result[key] = value
    return result


def _reject_nonfinite(value: str) -> None:
    raise ValueError(f"I8D_JSON_NONFINITE:{value}")


def _decision_section(traceability: str, decision: str) -> str:
    heading = f"### {decision}"
    start = traceability.find(heading)
    if start < 0:
        raise ValueError(f"I8D_OPEN_DECISION_TRACE_MISSING:{decision}")
    candidates = [
        value
        for value in (
            traceability.find("\n### OD-", start + len(heading)),
            traceability.find("\n## ", start + len(heading)),
        )
        if value >= 0
    ]
    end = min(candidates) if candidates else len(traceability)
    return traceability[start:end]


def _load_governance() -> tuple[str, str, str]:
    try:
        contract = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
        golden = json.loads(_GOLDEN_PATH.read_text(encoding="utf-8"))
        traceability = _TRACEABILITY_PATH.read_text(encoding="utf-8")
    except (OSError, json.JSONDecodeError):
        raise ValueError("I8D_CANONICAL_GOVERNANCE_UNAVAILABLE") from None
    if not isinstance(contract, Mapping) or not isinstance(golden, Mapping):
        raise ValueError("I8D_CANONICAL_GOVERNANCE_INVALID")

    parent = (
        contract.get("contract_id"),
        contract.get("contract_version"),
        contract.get("authority_graph_version"),
    )
    if parent != _EXPECTED_PARENT:
        raise ValueError("I8D_CANONICAL_PARENT_DRIFT")

    profiles = contract.get("authority_semantics", {}).get("profiles")
    if not isinstance(profiles, Mapping):
        raise ValueError("I8D_AUTHORITY_PROFILES_MISSING")
    narrative = profiles.get("NARRATIVE_DESIGN_NON_CANONICAL")
    px = profiles.get("PX_RANKING_NON_CANONICAL")
    if not isinstance(narrative, Mapping) or dict(narrative) != _EXPECTED_NARRATIVE_PROFILE:
        raise ValueError("I8D_NARRATIVE_DESIGN_AUTHORITY_DRIFT")
    if not isinstance(px, Mapping) or dict(px) != _EXPECTED_PX_PROFILE:
        raise ValueError("I8D_PX_AUTHORITY_DRIFT")

    freeze = contract.get("freeze_domains")
    if not isinstance(freeze, Mapping):
        raise ValueError("I8D_FREEZE_DOMAINS_MISSING")
    af_f = freeze.get("AF-F")
    af_g = freeze.get("AF-G")
    if not isinstance(af_f, Mapping) or not _REQUIRED_AF_F_INVARIANTS <= set(
        af_f.get("invariants", [])
    ):
        raise ValueError("I8D_AF_F_INVARIANT_DRIFT")
    if not isinstance(af_g, Mapping) or not _REQUIRED_AF_G_INVARIANTS <= set(
        af_g.get("invariants", [])
    ):
        raise ValueError("I8D_AF_G_INVARIANT_DRIFT")

    registry = contract.get("type_registry")
    if not isinstance(registry, Mapping):
        raise ValueError("I8D_TYPE_REGISTRY_MISSING")
    forbidden_promotions = {"BranchQuality", "BranchQualityEvidence", "BranchQualityScore"}
    if forbidden_promotions & set(registry):
        raise ValueError("I8D_STAGE_B_PRODUCTION_TYPE_PREMATURELY_PROMOTED")

    scenarios = golden.get("scenarios")
    if not isinstance(scenarios, Mapping):
        raise ValueError("I8D_GOLDEN_SCENARIOS_MISSING")
    if not _REQUIRED_GOLDEN_SCENARIOS <= set(scenarios):
        raise ValueError("I8D_REQUIRED_GOLDEN_CORPUS_DRIFT")

    for decision in _DEFERRED_DECISIONS:
        section = _decision_section(traceability, decision)
        if "- **Required experiment/research:**" not in section:
            raise ValueError(f"I8D_OPEN_DECISION_RESEARCH_GATE_DRIFT:{decision}")
        if "RESOLVED_ARCHITECTURAL_SUBSTRATE" in section:
            raise ValueError(f"I8D_OPEN_DECISION_PREMATURELY_RESOLVED:{decision}")
    return _EXPECTED_PARENT


def _fixture_material(fixture: BranchEvidenceExperimentFixture) -> dict[str, Any]:
    return {
        "fixture_id": fixture.fixture_id,
        "authored_design_fit": fixture.authored_design_fit,
        "meaningful_delta_refs": list(fixture.meaningful_delta_refs),
        "recoverable_thread_refs": list(fixture.recoverable_thread_refs),
        "repetition_key": fixture.repetition_key,
        "prior_occurrence_count": fixture.prior_occurrence_count,
        "authority_class": fixture.authority_class,
    }


def _result_material(result: BranchEvidenceExperimentResult) -> dict[str, Any]:
    return json.loads(
        _canonical_json(
            {
                "evaluation_id": result.evaluation_id,
                "diagnostic_class": result.diagnostic_class,
                "source_kind": result.source_kind,
                "source_status": result.source_status,
                "source_world_id": result.source_world_id,
                "source_baseline_version": result.source_baseline_version,
                "source_state_version": result.source_state_version,
                "source_i1_sha256": result.source_i1_sha256,
                "source_package_sha256": result.source_package_sha256,
                "source_reference_sha256": result.source_reference_sha256,
                "axis_evidence": thaw_value(result.axis_evidence),
                "integrity_failures": list(result.integrity_failures),
                "strengths": list(result.strengths),
                "risks": list(result.risks),
                "deferred_decisions": list(result.deferred_decisions),
                "authority_class": result.authority_class,
            }
        )
    )


def _validate_fixture_intrinsics(
    fixture: BranchEvidenceExperimentFixture,
) -> tuple[tuple[str, ...], tuple[str, ...], str | None]:
    if not isinstance(fixture, BranchEvidenceExperimentFixture):
        raise TypeError("I8D_BRANCH_EVIDENCE_FIXTURE_REQUIRED")
    if fixture.authority_class != _FIXTURE_AUTHORITY_CLASS:
        raise ValueError("I8D_FIXTURE_AUTHORITY_ESCALATION")
    _require_string(fixture.fixture_id, "I8D_FIXTURE_ID_REQUIRED")
    if fixture.authored_design_fit not in _ALLOWED_AUTHORED_FIT:
        raise ValueError("I8D_AUTHORED_DESIGN_FIT_INVALID")

    meaningful = tuple(
        _require_string(value, "I8D_MEANINGFUL_DELTA_REF_INVALID")
        for value in _require_sequence(
            fixture.meaningful_delta_refs,
            "I8D_MEANINGFUL_DELTA_REFS_SEQUENCE_REQUIRED",
        )
    )
    if len(meaningful) != len(set(meaningful)):
        raise ValueError("I8D_DUPLICATE_MEANINGFUL_DELTA_REF")

    threads = tuple(
        _require_string(value, "I8D_RECOVERABLE_THREAD_REF_INVALID")
        for value in _require_sequence(
            fixture.recoverable_thread_refs,
            "I8D_RECOVERABLE_THREAD_REFS_SEQUENCE_REQUIRED",
        )
    )
    if len(threads) != len(set(threads)):
        raise ValueError("I8D_DUPLICATE_RECOVERABLE_THREAD_REF")

    repetition_key = fixture.repetition_key
    if repetition_key is not None:
        repetition_key = _require_string(repetition_key, "I8D_REPETITION_KEY_INVALID")
    if isinstance(fixture.prior_occurrence_count, bool) or not isinstance(
        fixture.prior_occurrence_count, int
    ):
        raise TypeError("I8D_PRIOR_OCCURRENCE_COUNT_INT_REQUIRED")
    if fixture.prior_occurrence_count < 0:
        raise ValueError("I8D_PRIOR_OCCURRENCE_COUNT_NEGATIVE")
    if fixture.prior_occurrence_count and repetition_key is None:
        raise ValueError("I8D_REPETITION_KEY_REQUIRED_WHEN_PRIOR_OCCURRENCES_EXIST")
    return meaningful, threads, repetition_key


def _normalize_fixture(
    fixture: BranchEvidenceExperimentFixture,
    *,
    allowed_source_refs: set[str],
) -> BranchEvidenceExperimentFixture:
    meaningful, threads, repetition_key = _validate_fixture_intrinsics(fixture)
    invented = sorted(set(meaningful) - allowed_source_refs)
    if invented:
        raise ValueError(
            f"I8D_MEANINGFUL_DELTA_REF_NOT_IN_VALIDATED_SOURCE:{invented[0]}"
        )
    if repetition_key is not None and repetition_key not in allowed_source_refs:
        raise ValueError("I8D_REPETITION_KEY_NOT_IN_VALIDATED_SOURCE")

    return BranchEvidenceExperimentFixture(
        fixture_id=fixture.fixture_id,
        authored_design_fit=fixture.authored_design_fit,
        meaningful_delta_refs=tuple(sorted(meaningful)),
        recoverable_thread_refs=tuple(sorted(threads)),
        repetition_key=repetition_key,
        prior_occurrence_count=fixture.prior_occurrence_count,
        authority_class=fixture.authority_class,
    )


def _string_leaves(value: Any) -> set[str]:
    leaves: set[str] = set()
    if isinstance(value, str):
        leaves.add(value)
        for prefix in _EVIDENCE_TOKEN_PREFIXES:
            if value.startswith(prefix) and len(value) > len(prefix):
                leaves.add(value[len(prefix) :])
    elif isinstance(value, Mapping):
        for child in value.values():
            leaves.update(_string_leaves(child))
    elif isinstance(value, Sequence) and not isinstance(value, (str, bytes, bytearray)):
        for child in value:
            leaves.update(_string_leaves(child))
    return leaves


def _decode_source_envelope(
    source_package: bytes,
) -> tuple[Mapping[str, Any], str | None, str | None]:
    try:
        envelope = json.loads(
            source_package.decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8D_SOURCE_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping):
        raise ValueError("I8D_SOURCE_PACKAGE_ENVELOPE_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("I8D_SOURCE_PACKAGE_PAYLOAD_INVALID")
    encoded = payload.get("source_i1_replay_b64")
    expected_i1 = payload.get("source_i1_replay_sha256")
    if not isinstance(encoded, str) or not isinstance(expected_i1, str):
        return payload, None, None
    try:
        solo_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8D_SOURCE_I1_REPLAY_ENCODING_INVALID") from None
    actual_i1 = hashlib.sha256(solo_package).hexdigest()
    if actual_i1 != expected_i1:
        raise ValueError("I8D_SOURCE_I1_REPLAY_DIGEST_MISMATCH")
    evidence = import_solo_replay_package(solo_package)
    return payload, evidence.baseline_version, actual_i1


def _strict_replay_source(
    source_kind: str, source_package: bytes
) -> tuple[Any, dict[str, Any]]:
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_SOURCE_KIND_UNSUPPORTED")
    if source_kind == "I5A_INFORMATION_OPPORTUNITY":
        result = i5a_reference.replay_information_opportunity_shadow_package(source_package)
        material = i5a_reference._result_material(result)
    elif source_kind == "I7A_WORLD_ECHO":
        result = i7a_reference.replay_player_private_world_echo_package(source_package)
        material = i7a_reference._reference_material(result)
    else:
        result = i8c_reference.replay_storylet_eligibility_package(source_package)
        material = i8c_reference._reference_material(result)
    return result, material


def _source_metadata(
    source_kind: str,
    result: Any,
    material: Mapping[str, Any],
    source_package: bytes,
) -> dict[str, Any]:
    _, baseline_version, decoded_i1_sha = _decode_source_envelope(source_package)
    if source_kind == "I5A_INFORMATION_OPPORTUNITY":
        status = result.status
        world_id = result.source_world_id
        state_version = result.source_state_version
        i1_sha = result.source_i1_sha256
    elif source_kind == "I7A_WORLD_ECHO":
        status = result.status
        world_id = result.source_world_id
        state_version = result.source_state_version
        i1_sha = decoded_i1_sha
    else:
        status = result.outcome
        world_id = result.source_world_id
        state_version = result.source_state_version
        i1_sha = decoded_i1_sha
    if decoded_i1_sha is not None and i1_sha is not None and decoded_i1_sha != i1_sha:
        raise ValueError("I8D_SOURCE_I1_PROVENANCE_DISAGREEMENT")
    return {
        "status": status,
        "world_id": world_id,
        "baseline_version": baseline_version,
        "state_version": state_version,
        "i1_sha256": i1_sha,
        "reference_sha256": _sha256(material),
        "allowed_source_refs": _string_leaves(material),
    }


def _axis(assessment: str, refs: Sequence[str], interpretation: str) -> dict[str, Any]:
    if assessment not in _ALLOWED_ASSESSMENTS:
        raise ValueError("I8D_INTERNAL_AXIS_ASSESSMENT_INVALID")
    return {
        "assessment": assessment,
        "evidence_refs": sorted({ref for ref in refs if isinstance(ref, str) and ref}),
        "interpretation": interpretation,
    }


def _empty_axes() -> dict[str, Any]:
    return {
        name: _axis(
            "NOT_APPLICABLE", (), "NO_EVIDENCE_FOR_THIS_AXIS_IN_CURRENT_SOURCE"
        )
        for name in _AXIS_NAMES
    }


def _validated_axes(
    *,
    source_kind: str,
    source_status: str,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> tuple[dict[str, Any], str, tuple[str, ...], tuple[str, ...]]:
    axes = _empty_axes()
    strengths: list[str] = []
    risks: list[str] = []

    source_refs = sorted(_string_leaves(source_material))
    axes["causal_world_integrity"] = _axis(
        "SUPPORTED",
        source_refs[:12],
        "UPSTREAM_CANONICAL_REFERENCE_REPLAYED_SUCCESSFULLY",
    )
    strengths.append("UPSTREAM_REFERENCE_REPLAY_VALID")

    if source_kind == "I5A_INFORMATION_OPPORTUNITY":
        axes["knowledge_provenance_integrity"] = _axis(
            "SUPPORTED",
            [source_material["source_event_id"]],
            "INFORMATION_OPPORTUNITY_PRESERVES_SOURCE_AND_CARRIER_PROVENANCE",
        )
        axes["agency_legibility"] = _axis(
            "SUPPORTED",
            [source_status],
            "NO_OPPORTUNITY_OR_CANDIDATE_STATUS_DOES_NOT_FORCE_PLAYER_ACTION",
        )
        if source_status == "SHADOW_ENCOUNTER_CANDIDATE":
            axes["meaningful_state_information_relationship_delta"] = _axis(
                "SUPPORTED" if fixture.meaningful_delta_refs else "THIN",
                fixture.meaningful_delta_refs,
                "VALIDATED_INFORMATION_DELTA_IS_VISIBLE_WITHOUT_COMMITTING_AN_ENCOUNTER",
            )
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "ABSENT",
                (),
                "AT_LEAST_ONE_SHADOW_CANDIDATE_SURVIVES_PLAUSIBILITY",
            )
        else:
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "RISK",
                list(source_material.get("rejection_reasons", [])),
                "NO_CURRENT_LEGAL_INFORMATION_OPPORTUNITY_IS_AVAILABLE",
            )
            risks.append("NO_CURRENT_LEGAL_INFORMATION_OPPORTUNITY")

    elif source_kind == "I7A_WORLD_ECHO":
        axes["agency_legibility"] = _axis(
            "SUPPORTED",
            [source_status],
            "PRIVATE_ECHO_NEVER_CREATES_PLAYER_INTENT_OR_DIEGETIC_SPEECH",
        )
        axes["knowledge_provenance_integrity"] = _axis(
            "SUPPORTED",
            list(source_material.get("canonical_fact_refs", [])),
            "WORLD_ECHO_CLAIMS_ARE_BOUND_TO_CANONICAL_SELF_KNOWN_CAUSE_FACTS",
        )
        axes["meaningful_state_information_relationship_delta"] = _axis(
            "SUPPORTED" if fixture.meaningful_delta_refs else "THIN",
            fixture.meaningful_delta_refs,
            "PERSISTENT_WORLD_DELTA_CAN_SUPPORT_CONTINUITY_WITHOUT_MANDATORY_PLOT",
        )
        realization = source_material.get("realization", {})
        suppression = (
            realization.get("suppression_reason")
            if isinstance(realization, Mapping)
            else None
        )
        if source_status == "SILENCE":
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "RISK",
                [suppression] if isinstance(suppression, str) else (),
                "CURRENT_PRIVATE_CALLBACK_IS_SUPPRESSED_WITHOUT_CHANGING_WORLD_TRUTH",
            )
            risks.append("CURRENT_WORLD_ECHO_SUPPRESSED")
        else:
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "ABSENT", (), "CURRENT_PRIVATE_WORLD_ECHO_IS_AVAILABLE"
            )

    else:
        axes["agency_legibility"] = _axis(
            "SUPPORTED",
            [source_material.get("reason", "")],
            "STORYLET_ELIGIBILITY_RECOMPUTE_CANNOT_FORCE_RECONVERGENCE_OR_REALIZATION",
        )
        axes["knowledge_provenance_integrity"] = _axis(
            "SUPPORTED",
            list(source_material.get("eligibility_evidence", [])),
            "CALLBACK_KNOWLEDGE_AND_RECIPIENT_IDENTITY_ARE_REVALIDATED_UPSTREAM",
        )
        callback = source_material.get("source_callback_concept_id")
        if isinstance(callback, str):
            axes["setup_promise_anchor_continuity"] = _axis(
                "SUPPORTED",
                [callback],
                "PROMISE_CALLBACK_CONTINUITY_EXISTS_WITHOUT_FORCING_PAYOFF",
            )
        if source_status == "STORYLET_ELIGIBLE":
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "ABSENT",
                (),
                "AT_LEAST_ONE_AUTHORED_STORYLET_IS_CURRENTLY_ELIGIBLE",
            )
        else:
            axes["legal_dead_end_opportunity_scarcity_risk"] = _axis(
                "RISK",
                [source_material.get("reason", "")],
                "CURRENT_AUTHORED_STORYLET_IS_NOT_LEGAL_AND_IS_NOT_WELDED_BACK",
            )
            risks.append("NO_CURRENT_VALID_STORYLET")

    fit_assessment = {
        "SUPPORTED": "SUPPORTED",
        "THIN": "THIN",
        "NOT_APPLICABLE": "NOT_APPLICABLE",
    }[fixture.authored_design_fit]
    axes["genre_theme_design_fit"] = _axis(
        fit_assessment,
        [fixture.fixture_id],
        "AUTHORED_FIT_IS_EVALUATION_METADATA_ONLY_AND_NEVER_WORLD_TRUTH",
    )
    if fixture.authored_design_fit == "SUPPORTED":
        strengths.append("AUTHORED_DESIGN_FIT_EVIDENCE_PRESENT")
    elif fixture.authored_design_fit == "THIN":
        risks.append("AUTHORED_DESIGN_FIT_EVIDENCE_THIN")

    if fixture.recoverable_thread_refs:
        axes["recoverable_thread_availability"] = _axis(
            "SUPPORTED",
            fixture.recoverable_thread_refs,
            "AUTHORED_RECOVERABLE_THREADS_EXIST_BUT_ARE_NOT_CANONICAL_FACTS",
        )
        strengths.append("RECOVERABLE_AUTHORED_THREAD_PRESENT")
    else:
        axes["recoverable_thread_availability"] = _axis(
            "ABSENT", (), "NO_RECOVERABLE_AUTHORED_THREAD_EVIDENCE_SUPPLIED"
        )

    repetition_detected = fixture.prior_occurrence_count > 0
    if source_kind == "I7A_WORLD_ECHO":
        realization = source_material.get("realization", {})
        if (
            isinstance(realization, Mapping)
            and realization.get("suppression_reason") == "NOVELTY_ALREADY_SEEN"
        ):
            repetition_detected = True
    if repetition_detected:
        refs = [fixture.repetition_key] if fixture.repetition_key else []
        axes["contrivance_repetition_risk"] = _axis(
            "RISK",
            refs,
            "REPEATED_EQUIVALENT_OPPORTUNITY_IS_VISIBLE_AS_RISK_WITHOUT_CHANGING_LEGALITY",
        )
        risks.append("REPETITION_OR_CONTRIVANCE_RISK_PRESENT")
    else:
        axes["contrivance_repetition_risk"] = _axis(
            "ABSENT", (), "NO_REPETITION_EVIDENCE_IN_CURRENT_EXPERIMENT_INPUT"
        )

    if source_status in {"NO_VALID_OPPORTUNITY", "NO_VALID_STORYLET"}:
        diagnostic = "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    elif source_kind == "I7A_WORLD_ECHO" and source_status == "SILENCE":
        if repetition_detected:
            diagnostic = "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
        else:
            diagnostic = "NO_CURRENT_DRAMATIC_OPPORTUNITY_EVIDENCE"
    elif (
        fixture.authored_design_fit == "THIN"
        and not fixture.meaningful_delta_refs
        and not fixture.recoverable_thread_refs
    ):
        diagnostic = "THIN_BUT_LEGAL_BRANCH_EVIDENCE"
    else:
        diagnostic = "ROBUST_BRANCH_EVIDENCE"

    storylet_continuity = (
        source_kind == "I8C_STORYLET" and source_status == "STORYLET_ELIGIBLE"
    )
    axes["character_relationship_continuity"] = _axis(
        "SUPPORTED" if storylet_continuity else "NOT_APPLICABLE",
        [source_material.get("candidate_npc_id", "")] if storylet_continuity else (),
        "RECIPIENT_SPECIFIC_CALLBACK_RELATIONSHIP_CONTINUITY"
        if storylet_continuity
        else "CURRENT_SOURCE_DOES_NOT_PROVE_RELATIONSHIP_CONTINUITY",
    )

    return axes, diagnostic, tuple(sorted(set(strengths))), tuple(sorted(set(risks)))


def _integrity_failure_result(
    *,
    source_kind: str,
    source_package: bytes,
    error: Exception,
) -> BranchEvidenceExperimentResult:
    source_digest = _sha256_bytes(source_package)
    error_code = str(error) or error.__class__.__name__
    axes = _empty_axes()
    axes["causal_world_integrity"] = _axis(
        "INTEGRITY_FAILURE",
        [error_code],
        "UPSTREAM_CANONICAL_REFERENCE_REJECTED_SOURCE_EVIDENCE_OR_PACKAGE",
    )
    axes["knowledge_provenance_integrity"] = _axis(
        "INTEGRITY_FAILURE",
        [error_code],
        "INVALID_UPSTREAM_EVIDENCE_CANNOT_BE_COMPENSATED_BY_DRAMATIC_STRENGTHS",
    )
    identity = _sha256(
        {
            "source_kind": source_kind,
            "source_package_sha256": source_digest,
            "error_code": error_code,
        }
    )
    return BranchEvidenceExperimentResult(
        evaluation_id=f"I8D:EVAL:INTEGRITY:{identity[:24]}",
        diagnostic_class="INTEGRITY_FAILURE_PRESENT",
        source_kind=source_kind,
        source_status="UPSTREAM_REFERENCE_REJECTED",
        source_world_id=None,
        source_baseline_version=None,
        source_state_version=None,
        source_i1_sha256=None,
        source_package_sha256=source_digest,
        source_reference_sha256=None,
        axis_evidence=freeze_value(axes),
        integrity_failures=(error_code,),
        strengths=(),
        risks=("UPSTREAM_INTEGRITY_FAILURE",),
        deferred_decisions=_DEFERRED_DECISIONS,
        authority_class=_AUTHORITY_CLASS,
    )


def _evaluate_validated_source(
    *,
    source_kind: str,
    source_package: bytes,
    result: Any,
    source_material: Mapping[str, Any],
    fixture: BranchEvidenceExperimentFixture,
) -> BranchEvidenceExperimentResult:
    governance = _load_governance()
    metadata = _source_metadata(source_kind, result, source_material, source_package)
    normalized_fixture = _normalize_fixture(
        fixture, allowed_source_refs=metadata["allowed_source_refs"]
    )
    axes, diagnostic, strengths, risks = _validated_axes(
        source_kind=source_kind,
        source_status=metadata["status"],
        source_material=source_material,
        fixture=normalized_fixture,
    )
    identity = _sha256(
        {
            "governance": governance,
            "source_kind": source_kind,
            "source_package_sha256": _sha256_bytes(source_package),
            "source_reference_sha256": metadata["reference_sha256"],
            "fixture": _fixture_material(normalized_fixture),
            "diagnostic_class": diagnostic,
            "axis_evidence": axes,
        }
    )
    return BranchEvidenceExperimentResult(
        evaluation_id=f"I8D:EVAL:{identity[:24]}",
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
        deferred_decisions=_DEFERRED_DECISIONS,
        authority_class=_AUTHORITY_CLASS,
    )


def evaluate_branch_evidence_experiment(
    *,
    source_kind: str,
    source_package: bytes | bytearray | memoryview,
    fixture: BranchEvidenceExperimentFixture,
    caller_branch_quality_evidence: Mapping[str, Any] | None = None,
) -> BranchEvidenceExperimentResult:
    """Evaluate a canonical reference package without changing upstream legality."""
    if caller_branch_quality_evidence is not None:
        raise ValueError("I8D_CALLER_AUTHORED_BRANCH_QUALITY_EVIDENCE_FORBIDDEN")
    _load_governance()
    source_kind = _require_string(source_kind, "I8D_SOURCE_KIND_REQUIRED")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_SOURCE_KIND_UNSUPPORTED")
    if not isinstance(source_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_SOURCE_PACKAGE_BYTES_REQUIRED")
    _validate_fixture_intrinsics(fixture)
    package_bytes = bytes(source_package)
    try:
        result, source_material = _strict_replay_source(source_kind, package_bytes)
    except (ValueError, TypeError) as exc:
        return _integrity_failure_result(
            source_kind=source_kind, source_package=package_bytes, error=exc
        )
    return _evaluate_validated_source(
        source_kind=source_kind,
        source_package=package_bytes,
        result=result,
        source_material=source_material,
        fixture=fixture,
    )


def export_branch_evidence_experiment_package(
    *,
    source_kind: str,
    source_package: bytes | bytearray | memoryview,
    fixture: BranchEvidenceExperimentFixture,
) -> bytes:
    """Export deterministic Stage A evidence only for a strictly valid upstream source."""
    _load_governance()
    source_kind = _require_string(source_kind, "I8D_SOURCE_KIND_REQUIRED")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_SOURCE_KIND_UNSUPPORTED")
    if not isinstance(source_package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_SOURCE_PACKAGE_BYTES_REQUIRED")
    _validate_fixture_intrinsics(fixture)
    package_bytes = bytes(source_package)
    result, source_material = _strict_replay_source(source_kind, package_bytes)
    evaluated = _evaluate_validated_source(
        source_kind=source_kind,
        source_package=package_bytes,
        result=result,
        source_material=source_material,
        fixture=fixture,
    )
    payload = {
        "package_schema": _PACKAGE_SCHEMA,
        "source_kind": source_kind,
        "source_package_sha256": _sha256_bytes(package_bytes),
        "source_package_b64": base64.b64encode(package_bytes).decode("ascii"),
        "fixture": _fixture_material(fixture),
        "expected_result": _result_material(evaluated),
    }
    return _canonical_json({"payload": payload, "sha256": _sha256(payload)}).encode(
        "utf-8"
    )


def replay_branch_evidence_experiment_package(
    package: bytes | bytearray | memoryview,
) -> BranchEvidenceExperimentResult:
    """Strict replay: any outer or nested upstream tamper fails closed."""
    _load_governance()
    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("I8D_REPLAY_PACKAGE_BYTES_REQUIRED")
    try:
        envelope = json.loads(
            bytes(package).decode("utf-8"),
            object_pairs_hook=_reject_duplicate_keys,
            parse_constant=_reject_nonfinite,
        )
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError("I8D_REPLAY_PACKAGE_JSON_INVALID") from None
    if not isinstance(envelope, Mapping) or set(envelope) != {"payload", "sha256"}:
        raise ValueError("I8D_REPLAY_ENVELOPE_SCHEMA_INVALID")
    payload = envelope.get("payload")
    if not isinstance(payload, Mapping) or payload.get("package_schema") != _PACKAGE_SCHEMA:
        raise ValueError("I8D_REPLAY_PACKAGE_SCHEMA_INVALID")
    if envelope.get("sha256") != _sha256(payload):
        raise ValueError("I8D_REPLAY_PACKAGE_TAMPERED")

    source_kind = _require_string(payload.get("source_kind"), "I8D_SOURCE_KIND_REQUIRED")
    if source_kind not in _SOURCE_KINDS:
        raise ValueError("I8D_SOURCE_KIND_UNSUPPORTED")
    encoded = _require_string(
        payload.get("source_package_b64"), "I8D_NESTED_SOURCE_PACKAGE_REQUIRED"
    )
    try:
        source_package = base64.b64decode(encoded.encode("ascii"), validate=True)
    except (ValueError, UnicodeEncodeError):
        raise ValueError("I8D_NESTED_SOURCE_PACKAGE_ENCODING_INVALID") from None
    if _sha256_bytes(source_package) != payload.get("source_package_sha256"):
        raise ValueError("I8D_NESTED_SOURCE_PACKAGE_DIGEST_MISMATCH")

    fixture_raw = payload.get("fixture")
    expected_fields = {
        "fixture_id",
        "authored_design_fit",
        "meaningful_delta_refs",
        "recoverable_thread_refs",
        "repetition_key",
        "prior_occurrence_count",
        "authority_class",
    }
    if not isinstance(fixture_raw, Mapping) or set(fixture_raw) != expected_fields:
        raise ValueError("I8D_FIXTURE_SCHEMA_INVALID")
    fixture = BranchEvidenceExperimentFixture(
        fixture_id=fixture_raw["fixture_id"],
        authored_design_fit=fixture_raw["authored_design_fit"],
        meaningful_delta_refs=tuple(fixture_raw["meaningful_delta_refs"]),
        recoverable_thread_refs=tuple(fixture_raw["recoverable_thread_refs"]),
        repetition_key=fixture_raw["repetition_key"],
        prior_occurrence_count=fixture_raw["prior_occurrence_count"],
        authority_class=fixture_raw["authority_class"],
    )
    _validate_fixture_intrinsics(fixture)

    # Strict nested replay is intentional. A tampered I5/I7/I8 package must not be
    # laundered into a newly self-consistent I8D package by changing expected_result.
    source_result, source_material = _strict_replay_source(source_kind, source_package)
    rebuilt = _evaluate_validated_source(
        source_kind=source_kind,
        source_package=source_package,
        result=source_result,
        source_material=source_material,
        fixture=fixture,
    )
    if _result_material(rebuilt) != payload.get("expected_result"):
        raise ValueError("I8D_REPLAY_RESULT_MATERIALIZATION_MISMATCH")
    return rebuilt
