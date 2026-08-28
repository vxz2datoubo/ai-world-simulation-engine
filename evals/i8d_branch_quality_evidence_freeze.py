"""I8D Stage B0 BranchQualityEvidence interface-freeze validator.

Evaluation/governance only. This module validates the proposed B0 contract and
fixtures while mechanically proving that the candidate is NOT canonical before
B1 inverse registration. It does not implement a runtime producer, PX ranker,
legality gate, world mutation, Storylet realization, or universal score.
"""
from __future__ import annotations

from dataclasses import dataclass
import copy
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Mapping, Sequence

B0_INTERFACE_FREEZE_ONLY = True
B0_CANDIDATE_NOT_CANONICAL = True
STAGE_B1_CANONICAL_REGISTRATION_NOT_AUTHORIZED = True
NO_RUNTIME_IMPLEMENTATION = True
NO_BRANCH_QUALITY_SCORE = True
NO_PX_RANKING_IMPLEMENTATION = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_RETCON_RESURRECTION_OR_RECONVERGENCE = True
NO_LLM_DIRECTOR_RENDERER_PROVIDER_AUTHORITY = True
NO_ENGAGEMENT_RETENTION_OBJECTIVE = True
NO_PARTY_PUBLIC_IMPLEMENTED = True

ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "contracts" / "AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json"
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN_PATH = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
FIXTURES_PATH = ROOT / "evals" / "AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json"

BINDING_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-BINDING"
TYPE_ID = "AF001.BranchQualityEvidence"
EVIDENCE_VERSION = "0.1-freeze-candidate"
AUTHORITY_CLASS = "DERIVED_EVIDENCE_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY"
PARENT_ID = "AWRSE-AF001-LIVING-STORY-CONTRACTS"
PARENT_VERSION = "1.9.0-candidate"
PARENT_AUTHORITY_GRAPH = "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
GOLDEN_ID = "AWRSE-AF001-GOLDEN-SCENARIOS"
GOLDEN_VERSION = "1.7.0-candidate"

VALIDATED_SOURCE_KINDS = {
    "I5A_INFORMATION_OPPORTUNITY",
    "I7A_WORLD_ECHO",
    "I8C_STORYLET",
}
INTEGRITY_AXES = (
    "causal_world_integrity",
    "agency_legibility",
    "knowledge_provenance_integrity",
)
MECHANISM_AXES = {
    "character_relationship_continuity",
    "meaningful_state_information_relationship_delta",
    "setup_promise_anchor_continuity",
    "contrivance_repetition_risk",
}
AUTHORED_METADATA_EXCLUDED = {
    "genre_theme_design_fit",
    "recoverable_thread_availability",
}
INTEGRITY_ASSESSMENTS = {"SUPPORTED", "INTEGRITY_FAILURE"}
SCARCITY_ASSESSMENTS = {"ABSENT", "RISK"}
MECHANISM_ASSESSMENTS = {"SUPPORTED", "THIN", "ABSENT", "RISK", "NOT_APPLICABLE"}
TOP_LEVEL_FIELDS = {
    "evidence_id",
    "source_candidate_ref",
    "source_kind",
    "source_package_sha256",
    "source_i1_sha256",
    "evidence_version",
    "authority_class",
    *INTEGRITY_AXES,
    "opportunity_scarcity_evidence",
    "mechanism_evidence",
}
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class B0FreezeReceipt:
    binding_sha256: str
    fixture_sha256: str
    parent_contract_version: str
    golden_suite_version: str
    canonical_registration_present: bool
    b1_required: bool


def _load_json(path: Path) -> Mapping[str, Any]:
    def reject_pairs(pairs: Sequence[tuple[str, Any]]) -> dict[str, Any]:
        out: dict[str, Any] = {}
        for key, value in pairs:
            if key in out:
                raise ValueError("B0_JSON_DUPLICATE_KEY")
            out[key] = value
        return out

    def reject_constant(_: str) -> None:
        raise ValueError("B0_JSON_NONFINITE_FORBIDDEN")

    try:
        value = json.loads(
            path.read_text(encoding="utf-8"),
            object_pairs_hook=reject_pairs,
            parse_constant=reject_constant,
        )
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError("B0_JSON_READ_OR_PARSE_FAILURE") from exc
    if not isinstance(value, Mapping):
        raise ValueError("B0_JSON_ROOT_MAPPING_REQUIRED")
    return value


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _require_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(code)
    return value


def _require_sha256(value: Any, code: str) -> str:
    value = _require_string(value, code)
    if not _SHA256_RE.fullmatch(value):
        raise ValueError(code)
    return value


def _reject_numeric_scalars(value: Any) -> None:
    if isinstance(value, bool) or value is None:
        return
    if isinstance(value, (int, float)):
        raise ValueError("B0_NUMERIC_SCALAR_FORBIDDEN")
    if isinstance(value, Mapping):
        for nested in value.values():
            _reject_numeric_scalars(nested)
    elif isinstance(value, (list, tuple)):
        for nested in value:
            _reject_numeric_scalars(nested)


def _validate_axis(value: Any, allowed: set[str], prefix: str) -> None:
    if not isinstance(value, Mapping) or set(value) != {"assessment", "source_refs"}:
        raise ValueError(f"{prefix}_SCHEMA_INVALID")
    assessment = _require_string(value.get("assessment"), f"{prefix}_ASSESSMENT_REQUIRED")
    if assessment not in allowed:
        raise ValueError(f"{prefix}_ASSESSMENT_INVALID")
    refs = value.get("source_refs")
    if not isinstance(refs, list) or any(not isinstance(item, str) or not item for item in refs):
        raise ValueError(f"{prefix}_SOURCE_REFS_INVALID")
    if assessment in {"SUPPORTED", "THIN", "RISK", "INTEGRITY_FAILURE"} and not refs:
        raise ValueError(f"{prefix}_SOURCE_REFS_REQUIRED")


def validate_evidence_instance(instance: Mapping[str, Any]) -> None:
    if not isinstance(instance, Mapping):
        raise TypeError("B0_EVIDENCE_MAPPING_REQUIRED")
    _reject_numeric_scalars(instance)
    unknown = set(instance) - TOP_LEVEL_FIELDS
    missing = TOP_LEVEL_FIELDS - set(instance)
    if unknown:
        raise ValueError("B0_EVIDENCE_UNKNOWN_FIELDS")
    if missing:
        raise ValueError("B0_EVIDENCE_REQUIRED_FIELDS_MISSING")

    _require_string(instance.get("evidence_id"), "B0_EVIDENCE_ID_REQUIRED")
    _require_string(instance.get("source_candidate_ref"), "B0_SOURCE_CANDIDATE_REF_REQUIRED")
    source_kind = _require_string(instance.get("source_kind"), "B0_SOURCE_KIND_REQUIRED")
    if source_kind not in VALIDATED_SOURCE_KINDS:
        raise ValueError("B0_SOURCE_KIND_NOT_EVIDENCE_VALIDATED")
    _require_sha256(instance.get("source_package_sha256"), "B0_SOURCE_PACKAGE_SHA256_INVALID")
    _require_sha256(instance.get("source_i1_sha256"), "B0_SOURCE_I1_SHA256_INVALID")
    if instance.get("evidence_version") != EVIDENCE_VERSION:
        raise ValueError("B0_EVIDENCE_VERSION_INVALID")
    if instance.get("authority_class") != AUTHORITY_CLASS:
        raise ValueError("B0_AUTHORITY_CLASS_INVALID")

    for name in INTEGRITY_AXES:
        _validate_axis(instance.get(name), INTEGRITY_ASSESSMENTS, f"B0_{name.upper()}")

    scarcity = instance.get("opportunity_scarcity_evidence")
    if not isinstance(scarcity, Mapping) or set(scarcity) != {
        "assessment",
        "source_refs",
        "upstream_status_ref",
    }:
        raise ValueError("B0_SCARCITY_SCHEMA_INVALID")
    assessment = _require_string(
        scarcity.get("assessment"), "B0_SCARCITY_ASSESSMENT_REQUIRED"
    )
    if assessment not in SCARCITY_ASSESSMENTS:
        raise ValueError("B0_SCARCITY_ASSESSMENT_INVALID")
    refs = scarcity.get("source_refs")
    if not isinstance(refs, list) or any(not isinstance(item, str) or not item for item in refs):
        raise ValueError("B0_SCARCITY_SOURCE_REFS_INVALID")
    _require_string(scarcity.get("upstream_status_ref"), "B0_SCARCITY_STATUS_REF_REQUIRED")
    if assessment == "RISK" and not refs:
        raise ValueError("B0_SCARCITY_RISK_REFS_REQUIRED")

    mechanisms = instance.get("mechanism_evidence")
    if not isinstance(mechanisms, Mapping):
        raise ValueError("B0_MECHANISM_EVIDENCE_MAPPING_REQUIRED")
    for name, value in mechanisms.items():
        if name not in MECHANISM_AXES:
            raise ValueError("B0_MECHANISM_AXIS_UNKNOWN")
        if not isinstance(value, Mapping) or set(value) != {"assessment", "source_refs"}:
            raise ValueError("B0_MECHANISM_SCHEMA_INVALID")
        mechanism_assessment = _require_string(
            value.get("assessment"), "B0_MECHANISM_ASSESSMENT_REQUIRED"
        )
        if mechanism_assessment not in MECHANISM_ASSESSMENTS:
            raise ValueError("B0_MECHANISM_ASSESSMENT_INVALID")
        mechanism_refs = value.get("source_refs")
        if not isinstance(mechanism_refs, list) or any(
            not isinstance(item, str) or not item for item in mechanism_refs
        ):
            raise ValueError("B0_MECHANISM_SOURCE_REFS_INVALID")
        if mechanism_assessment == "NOT_APPLICABLE" and mechanism_refs:
            raise ValueError("B0_MECHANISM_NOT_APPLICABLE_REFS_FORBIDDEN")
        if mechanism_assessment != "NOT_APPLICABLE" and not mechanism_refs:
            raise ValueError("B0_MECHANISM_EVIDENCE_REFS_REQUIRED")


def materialize_negative_fixture(
    case: Mapping[str, Any],
    *,
    positive_by_id: Mapping[str, Mapping[str, Any]] | None = None,
) -> dict[str, Any]:
    """Materialize one adversarial fixture from a declared positive baseline.

    Keeping negative cases as path mutations makes each authority attack auditable
    and prevents copy-pasted full instances from drifting away from their baseline.
    """
    if not isinstance(case, Mapping):
        raise TypeError("B0_NEGATIVE_FIXTURE_MAPPING_REQUIRED")
    base_ref = _require_string(
        case.get("base_fixture_ref"), "B0_NEGATIVE_BASE_FIXTURE_REF_REQUIRED"
    )
    if positive_by_id is None:
        fixtures = _load_json(FIXTURES_PATH)
        positives = fixtures.get("positive_cases")
        if not isinstance(positives, list):
            raise ValueError("B0_POSITIVE_FIXTURES_REQUIRED")
        positive_by_id = {
            _require_string(item.get("fixture_id"), "B0_POSITIVE_FIXTURE_ID_REQUIRED"): item.get("instance")
            for item in positives
            if isinstance(item, Mapping) and isinstance(item.get("instance"), Mapping)
        }
    base = positive_by_id.get(base_ref)
    if not isinstance(base, Mapping):
        raise ValueError("B0_NEGATIVE_BASE_FIXTURE_UNKNOWN")
    instance: dict[str, Any] = copy.deepcopy(dict(base))
    mutations = case.get("mutations")
    if not isinstance(mutations, list) or not mutations:
        raise ValueError("B0_NEGATIVE_MUTATIONS_REQUIRED")
    for mutation in mutations:
        if not isinstance(mutation, Mapping):
            raise ValueError("B0_NEGATIVE_MUTATION_MAPPING_REQUIRED")
        op = mutation.get("op")
        path = mutation.get("path")
        if op not in {"set", "delete"}:
            raise ValueError("B0_NEGATIVE_MUTATION_OP_INVALID")
        if not isinstance(path, list) or not path or any(
            not isinstance(segment, str) or not segment for segment in path
        ):
            raise ValueError("B0_NEGATIVE_MUTATION_PATH_INVALID")
        cursor: dict[str, Any] = instance
        for segment in path[:-1]:
            nested = cursor.get(segment)
            if nested is None and op == "set":
                nested = {}
                cursor[segment] = nested
            if not isinstance(nested, dict):
                raise ValueError("B0_NEGATIVE_MUTATION_PATH_NOT_MAPPING")
            cursor = nested
        leaf = path[-1]
        if op == "set":
            if "value" not in mutation:
                raise ValueError("B0_NEGATIVE_MUTATION_VALUE_REQUIRED")
            cursor[leaf] = copy.deepcopy(mutation["value"])
        else:
            if leaf not in cursor:
                raise ValueError("B0_NEGATIVE_MUTATION_DELETE_TARGET_MISSING")
            del cursor[leaf]
    return instance


def validate_freeze_candidate() -> B0FreezeReceipt:
    binding = _load_json(BINDING_PATH)
    parent = _load_json(PARENT_PATH)
    golden = _load_json(GOLDEN_PATH)
    fixtures = _load_json(FIXTURES_PATH)

    if binding.get("binding_id") != BINDING_ID:
        raise ValueError("B0_BINDING_ID_INVALID")
    if binding.get("status") != "STAGE_B0_INTERFACE_FREEZE_CANDIDATE_NOT_CANONICAL":
        raise ValueError("B0_BINDING_STATUS_INVALID")
    if binding.get("canonical_authority") != "NONE_UNTIL_PARENT_INVERSE_REGISTRATION":
        raise ValueError("B0_SELF_AUTHORITY_FORBIDDEN")
    if binding.get("stage_b1_registration_authorized") is not False:
        raise ValueError("B0_B1_AUTHORIZATION_MUST_BE_FALSE")
    if binding.get("runtime_implementation_authorized") is not False:
        raise ValueError("B0_RUNTIME_AUTHORIZATION_MUST_BE_FALSE")

    if parent.get("contract_id") != PARENT_ID or parent.get("contract_version") != PARENT_VERSION:
        raise ValueError("B0_PARENT_CONTRACT_CONTEXT_DRIFT")
    if parent.get("authority_graph_version") != PARENT_AUTHORITY_GRAPH:
        raise ValueError("B0_PARENT_AUTHORITY_GRAPH_DRIFT")
    registered = parent.get("registered_contract_extensions")
    if not isinstance(registered, Mapping):
        raise ValueError("B0_PARENT_EXTENSION_REGISTRY_REQUIRED")
    if BINDING_ID in registered:
        raise ValueError("B0_PREMATURE_CANONICAL_REGISTRATION")

    if golden.get("eval_suite_id") != GOLDEN_ID or golden.get("suite_version") != GOLDEN_VERSION:
        raise ValueError("B0_GOLDEN_CONTEXT_DRIFT")
    if golden.get("required_contract_version") != PARENT_VERSION:
        raise ValueError("B0_GOLDEN_PARENT_VERSION_DRIFT")

    profile = binding.get("proposed_authority_profile")
    expected_profile = {
        "profile_id": "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW",
        "canonical_data_authority": ["NONE"],
        "contract_schema_steward": "AWRSE_AF_F_CONTRACT_STEWARD",
        "producer_or_assembler": ["AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER"],
        "downstream_consumer": ["NARRATIVE_OPPORTUNITY", "PX_RANKING", "AI_DIRECTOR"],
        "staging_authority": ["NONE"],
        "mutation_constraint": "DERIVED_BRANCH_EVIDENCE_MAY_DESCRIBE_ALREADY_VALIDATED_EVIDENCE_ONLY_AND_CANNOT_LEGALIZE_INVALID_CANDIDATES_CREATE_OR_REWRITE_WORLD_FACTS_OR_KNOWLEDGE_LOWER_CAPABILITY_DIFFICULTY_CREATE_PLAYER_INTENT_FORCE_STORYLET_OR_ENCOUNTER_REALIZATION_RETCON_RESURRECT_OR_FORCE_RECONVERGENCE",
    }
    if profile != expected_profile:
        raise ValueError("B0_AUTHORITY_PROFILE_DRIFT")

    proposed = binding.get("proposed_type")
    if not isinstance(proposed, Mapping) or proposed.get("type_id") != TYPE_ID:
        raise ValueError("B0_PROPOSED_TYPE_INVALID")
    if proposed.get("domain") != "AF-F":
        raise ValueError("B0_DOMAIN_INVALID")
    if proposed.get("portable_integrity_invariant") != (
        "ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL"
    ):
        raise ValueError("B0_PORTABILITY_INVARIANT_DRIFT")
    groups = proposed.get("field_groups")
    if not isinstance(groups, Mapping):
        raise ValueError("B0_FIELD_GROUPS_REQUIRED")
    if tuple(groups.get("portable_integrity_assessments", ())) != INTEGRITY_AXES:
        raise ValueError("B0_INTEGRITY_AXIS_SHAPE_DRIFT")
    if set(groups.get("dynamic_opportunity_state", ())) != {"opportunity_scarcity_evidence"}:
        raise ValueError("B0_SCARCITY_NOT_STRUCTURALLY_SEPARATE")
    if set(groups.get("mechanism_local_optional", ())) != MECHANISM_AXES:
        raise ValueError("B0_MECHANISM_AXIS_SHAPE_DRIFT")
    if set(proposed.get("authored_design_metadata_excluded", ())) != AUTHORED_METADATA_EXCLUDED:
        raise ValueError("B0_AUTHORED_METADATA_QUARANTINE_DRIFT")
    if set(proposed.get("fields", ())) != TOP_LEVEL_FIELDS:
        raise ValueError("B0_TOP_LEVEL_FIELD_SHAPE_DRIFT")
    if proposed.get("no_numeric_scalar_fields") is not True:
        raise ValueError("B0_NUMERIC_SCALAR_GUARD_MISSING")
    if proposed.get("no_flowback_to_world_truth") is not True:
        raise ValueError("B0_WORLD_FLOWBACK_GUARD_MISSING")

    gate = binding.get("promotion_gate")
    if not isinstance(gate, Mapping):
        raise ValueError("B0_PROMOTION_GATE_REQUIRED")
    required_true = {
        "stage_b1_required",
        "independent_accept_of_b0_required",
        "parent_contract_version_must_advance",
        "golden_suite_version_must_advance",
        "parent_inverse_registration_required",
        "golden_inverse_registration_required",
        "historical_parent_tuple_cannot_authorize_new_extension",
        "child_self_declaration_confers_no_authority",
        "runtime_remains_separately_unauthorized",
        "b1_must_preserve_assessment_level_not_material_identity_invariant",
    }
    if any(gate.get(key) is not True for key in required_true):
        raise ValueError("B0_PROMOTION_GATE_INCOMPLETE")

    open_decisions = binding.get("open_decisions")
    if not isinstance(open_decisions, Mapping) or set(open_decisions) != {
        "OD-CLUE-QUALITY-001",
        "OD-PX-SCORING-001",
    }:
        raise ValueError("B0_OPEN_DECISION_BOUNDARY_DRIFT")

    positive = fixtures.get("positive_cases")
    negative = fixtures.get("negative_cases")
    if fixtures.get("mutation_fixture_schema") != (
        "BASE_POSITIVE_INSTANCE_PLUS_DECLARED_PATH_MUTATIONS"
    ):
        raise ValueError("B0_MUTATION_FIXTURE_SCHEMA_INVALID")
    if not isinstance(positive, list) or not positive:
        raise ValueError("B0_POSITIVE_FIXTURES_REQUIRED")
    if not isinstance(negative, list) or not negative:
        raise ValueError("B0_NEGATIVE_FIXTURES_REQUIRED")

    positive_by_id: dict[str, Mapping[str, Any]] = {}
    for case in positive:
        if not isinstance(case, Mapping):
            raise ValueError("B0_POSITIVE_FIXTURE_MAPPING_REQUIRED")
        fixture_id = _require_string(
            case.get("fixture_id"), "B0_POSITIVE_FIXTURE_ID_REQUIRED"
        )
        if fixture_id in positive_by_id:
            raise ValueError("B0_POSITIVE_FIXTURE_ID_DUPLICATE")
        instance = case.get("instance")
        validate_evidence_instance(instance)
        assert isinstance(instance, Mapping)
        positive_by_id[fixture_id] = instance

    for case in negative:
        if not isinstance(case, Mapping):
            raise ValueError("B0_NEGATIVE_FIXTURE_MAPPING_REQUIRED")
        expected = _require_string(
            case.get("expected_error"), "B0_NEGATIVE_EXPECTED_ERROR_REQUIRED"
        )
        instance = materialize_negative_fixture(case, positive_by_id=positive_by_id)
        try:
            validate_evidence_instance(instance)
        except (ValueError, TypeError) as exc:
            if str(exc) != expected:
                raise ValueError(
                    f"B0_NEGATIVE_FIXTURE_ERROR_MISMATCH:{case.get('fixture_id')}:{exc}"
                ) from exc
        else:
            raise ValueError(f"B0_NEGATIVE_FIXTURE_DID_NOT_FAIL:{case.get('fixture_id')}")

    return B0FreezeReceipt(
        binding_sha256=_sha256(binding),
        fixture_sha256=_sha256(fixtures),
        parent_contract_version=PARENT_VERSION,
        golden_suite_version=GOLDEN_VERSION,
        canonical_registration_present=False,
        b1_required=True,
    )
