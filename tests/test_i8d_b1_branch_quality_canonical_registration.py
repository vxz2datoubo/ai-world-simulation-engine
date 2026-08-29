import base64, copy, json
from pathlib import Path
import pytest
import evals.i8d_b1_branch_quality_canonical_registration as b1

ROOT = Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

def test_b1_canonical_registration_and_real_replay_provenance():
    receipt = b1.validate_b1_canonical_registration()
    assert receipt["cases"] == 3
    assert receipt["source_kinds"] == ["I5A_INFORMATION_OPPORTUNITY","I7A_WORLD_ECHO","I8C_STORYLET"]

def test_old_parent_graph_golden_tuple_cannot_authorize():
    assert not b1.historical_tuple_authorizes("1.9.0-candidate", b1.GRAPH_VERSION, b1.GOLDEN_VERSION)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, "AF001-AUTHORITY-GRAPH-1.9-I2A008@1", b1.GOLDEN_VERSION)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, "1.7.0-candidate")
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION, binding_registered=False)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION, fixture_registered=False)
    assert b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION)

def test_parent_profile_has_no_canonical_data_authority_and_px_is_downstream_only():
    parent=load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    p=parent["authority_semantics"]["profiles"][b1.PROFILE_ID]
    assert p["canonical_data_authority"] == ["NONE"]
    assert p["producer_or_assembler"] == ["AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER"]
    assert p["downstream_consumer"] == ["NARRATIVE_OPPORTUNITY","PX_RANKING","AI_DIRECTOR"]
    assert p["staging_authority"] == ["NONE"]

def test_branch_quality_type_preserves_frozen_shape_and_no_score():
    parent=load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    t=parent["type_registry"]["BranchQualityEvidence"]
    assert t["portable_integrity_invariant"] == "ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL"
    assert set(t["fields"]) == {"evidence_id","evaluated_subject_ref","source_kind","source_package_sha256","source_i1_sha256","evidence_version","authority_class","causal_world_integrity","agency_legibility","knowledge_provenance_integrity","opportunity_scarcity_evidence","mechanism_evidence"}
    assert not {"score","weight","rank","legality_result","player_intent"} & set(t["fields"])

def test_synthetic_b0_fixture_is_not_registered_as_source_proof():
    golden=load("evals/AF001-GOLDEN-SCENARIOS.json")
    assert "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES" not in golden["registered_fixture_extensions"]
    p=load("evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json")
    assert p["synthetic_b0_fixture_is_source_proof"] is False
    assert p["synthetic_b0_fixture_ref"] == "evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json"

def test_real_replay_package_tamper_fails_closed():
    p=load("evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json")
    case=copy.deepcopy(p["cases"][0])
    raw=bytearray(base64.b64decode(case["stage_a_r1_package_b64"]))
    raw[-2] ^= 1
    case["stage_a_r1_package_b64"] = base64.b64encode(bytes(raw)).decode("ascii")
    case["stage_a_r1_package_sha256"] = b1.sha_bytes(bytes(raw))
    import evals.i8d_branch_quality_evidence_experiment_v2 as r1
    with pytest.raises(ValueError): r1.replay_branch_evidence_experiment_package(bytes(raw))

def test_decision_lifecycle_migrates_registry_identity_without_resolving_quality_or_px():
    d=load("evals/AF001-DECISION-LIFECYCLE-BINDINGS.json")
    assert d["version"] == "1.3.0-candidate"
    assert d["required_contract_version"] == "1.10.0-candidate"
    trace=(ROOT/"docs/AF001-TRACEABILITY.md").read_text(encoding="utf-8")
    assert "### OD-CLUE-QUALITY-001 " in trace
    assert "### OD-PX-SCORING-001 " in trace

def test_hard_locks_keep_runtime_and_optimizer_authority_closed():
    assert b1.NO_RUNTIME_IMPLEMENTATION
    assert b1.NO_BRANCH_QUALITY_SCORE
    assert b1.NO_PX_RANKING_IMPLEMENTATION
    assert b1.NO_WORLD_OR_KNOWLEDGE_MUTATION
    assert b1.NO_STORYLET_OR_ENCOUNTER_REALIZATION
    assert b1.NO_ENGAGEMENT_RETENTION_OBJECTIVE
