"""I8D B1 canonical BranchQualityEvidence registration and real replay provenance validator."""
from __future__ import annotations
import base64, copy, hashlib, json, re
from pathlib import Path
from typing import Any, Mapping
from awrse.model import thaw_value
import evals.i8d_branch_quality_evidence_experiment_v2 as r1

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "contracts/AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN = ROOT / "evals/AF001-GOLDEN-SCENARIOS.json"
BINDING = ROOT / "contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json"
PROVENANCE = ROOT / "evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json"
DECISIONS = ROOT / "evals/AF001-DECISION-LIFECYCLE-BINDINGS.json"
TRACE = ROOT / "docs/AF001-TRACEABILITY.md"
PARENT_VERSION = "1.10.0-candidate"
GRAPH_VERSION = "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1"
GOLDEN_VERSION = "1.8.0-candidate"
DECISION_VERSION = "1.3.0-candidate"
BINDING_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-BINDING"
FIXTURE_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES"
PROFILE_ID = "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW"
NO_RUNTIME_IMPLEMENTATION = True
NO_BRANCH_QUALITY_SCORE = True
NO_PX_RANKING_IMPLEMENTATION = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_ENGAGEMENT_RETENTION_OBJECTIVE = True


def load(path): return json.loads(path.read_text(encoding="utf-8"))
def sha_bytes(v): return hashlib.sha256(v).hexdigest()

def expected_projection(result):
    axes = thaw_value(result.axis_evidence)
    scarcity = axes["legal_dead_end_opportunity_scarcity_risk"]
    return {
        "source_kind": result.source_kind,
        "source_package_sha256": result.source_package_sha256,
        "source_i1_sha256": result.source_i1_sha256,
        "causal_world_integrity": {"assessment": axes["causal_world_integrity"]["assessment"], "source_refs": list(axes["causal_world_integrity"]["evidence_refs"])},
        "agency_legibility": {"assessment": axes["agency_legibility"]["assessment"], "source_refs": list(axes["agency_legibility"]["evidence_refs"])},
        "knowledge_provenance_integrity": {"assessment": axes["knowledge_provenance_integrity"]["assessment"], "source_refs": list(axes["knowledge_provenance_integrity"]["evidence_refs"])},
        "opportunity_scarcity_evidence": {"assessment": "RISK" if scarcity["assessment"] == "RISK" else "ABSENT", "source_refs": list(scarcity["evidence_refs"]), "upstream_status_ref": result.source_status},
        "mechanism_evidence": {name: {"assessment": axes[name]["assessment"], "source_refs": list(axes[name]["evidence_refs"])} for name in ("character_relationship_continuity","meaningful_state_information_relationship_delta","setup_promise_anchor_continuity","contrivance_repetition_risk")},
    }


def validate_b1_canonical_registration() -> dict[str, Any]:
    parent, golden, binding, prov, decisions = map(load, (PARENT, GOLDEN, BINDING, PROVENANCE, DECISIONS))
    if parent.get("contract_version") != PARENT_VERSION or parent.get("authority_graph_version") != GRAPH_VERSION: raise ValueError("B1_PARENT_TUPLE_INVALID")
    reg = parent.get("registered_contract_extensions", {}).get(BINDING_ID)
    if not isinstance(reg, Mapping) or reg.get("parent_contract_version") != PARENT_VERSION or reg.get("parent_authority_graph_version") != GRAPH_VERSION: raise ValueError("B1_PARENT_INVERSE_REGISTRATION_INVALID")
    profile = parent.get("authority_semantics", {}).get("profiles", {}).get(PROFILE_ID)
    if not isinstance(profile, Mapping) or profile.get("canonical_data_authority") != ["NONE"]: raise ValueError("B1_PROFILE_AUTHORITY_INVALID")
    t = parent.get("type_registry", {}).get("BranchQualityEvidence")
    if not isinstance(t, Mapping) or t.get("type_id") != "AF001.BranchQualityEvidence" or t.get("authority_profile_ref") != PROFILE_ID: raise ValueError("B1_TYPE_REGISTRATION_INVALID")
    if golden.get("suite_version") != GOLDEN_VERSION or golden.get("required_contract_version") != PARENT_VERSION: raise ValueError("B1_GOLDEN_TUPLE_INVALID")
    freg = golden.get("registered_fixture_extensions", {}).get(FIXTURE_ID)
    if not isinstance(freg, Mapping) or freg.get("path") != "evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json" or freg.get("parent_suite_version") != GOLDEN_VERSION: raise ValueError("B1_GOLDEN_INVERSE_REGISTRATION_INVALID")
    if decisions.get("version") != DECISION_VERSION or decisions.get("required_contract_version") != PARENT_VERSION: raise ValueError("B1_DECISION_REGISTRY_MIGRATION_INVALID")
    if prov.get("evidence_class") != "REAL_REPLAY_REBUILT_CANONICAL_SOURCE_PROOF" or prov.get("synthetic_b0_fixture_is_source_proof") is not False: raise ValueError("B1_PROVENANCE_CLASS_INVALID")
    seen = set()
    for case in prov.get("cases", []):
        package = base64.b64decode(case["stage_a_r1_package_b64"], validate=True)
        if sha_bytes(package) != case["stage_a_r1_package_sha256"]: raise ValueError("B1_STAGE_A_PACKAGE_DIGEST_INVALID")
        result = r1.replay_branch_evidence_experiment_package(package)
        expected = expected_projection(result)
        evidence = case["branch_quality_evidence"]
        for key, value in expected.items():
            if evidence.get(key) != value: raise ValueError(f"B1_REPLAY_PROJECTION_MISMATCH:{case['case_id']}:{key}")
        if evidence.get("evidence_version") != "1.0.0-candidate" or evidence.get("authority_class") != "DERIVED_EVIDENCE_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY": raise ValueError("B1_EVIDENCE_AUTHORITY_INVALID")
        seen.add(result.source_kind)
    if seen != {"I5A_INFORMATION_OPPORTUNITY","I7A_WORLD_ECHO","I8C_STORYLET"}: raise ValueError("B1_REAL_REPLAY_SOURCE_COVERAGE_INCOMPLETE")
    trace = TRACE.read_text(encoding="utf-8")
    for decision in ("OD-CLUE-QUALITY-001","OD-PX-SCORING-001"):
        if f"### {decision} " not in trace: raise ValueError("B1_OPEN_DECISION_MISSING")
    return {"cases": len(prov["cases"]), "source_kinds": sorted(seen), "parent": PARENT_VERSION, "graph": GRAPH_VERSION, "golden": GOLDEN_VERSION}


def historical_tuple_authorizes(parent_version: str, graph_version: str, golden_version: str, binding_registered: bool=True, fixture_registered: bool=True) -> bool:
    return bool(parent_version == PARENT_VERSION and graph_version == GRAPH_VERSION and golden_version == GOLDEN_VERSION and binding_registered and fixture_registered)
