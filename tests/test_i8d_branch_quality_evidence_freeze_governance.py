import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
BINDING_PATH = ROOT / "contracts" / "AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json"
FIXTURES_PATH = ROOT / "evals" / "AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json"
TRACEABILITY_PATH = ROOT / "docs" / "AF001-TRACEABILITY.md"

SYNTHETIC_FIXTURE_CLASS = "SYNTHETIC_INTERFACE_SHAPE_FIXTURE_ONLY_NOT_SOURCE_PROOF"
HASH_SEMANTICS = "SHA256_SHAPE_VALIDATION_ONLY_NOT_CANONICAL_SOURCE_OR_I1_PROVENANCE_CLAIM"
OPEN_DECISIONS = ("OD-CLUE-QUALITY-001", "OD-PX-SCORING-001")


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def decision_section(text: str, decision_id: str) -> str:
    marker = f"### {decision_id} "
    start = text.find(marker)
    assert start >= 0, f"missing canonical OPEN_DECISION section: {decision_id}"
    rest = text[start + len(marker):]
    match = re.search(r"\n### OD-[A-Z0-9-]+|\n## ", rest)
    end = len(text) if match is None else start + len(marker) + match.start()
    return text[start:end]


def test_b0_fixture_suite_explicitly_denies_source_proof_authority():
    binding = load_json(BINDING_PATH)
    fixtures = load_json(FIXTURES_PATH)
    assert binding["evidence_basis"]["b0_fixture_evidence_class"] == SYNTHETIC_FIXTURE_CLASS
    assert binding["evidence_basis"]["b0_fixture_hash_semantics"] == HASH_SEMANTICS
    assert fixtures["canonical_authority"] == "NONE_UNTIL_B1_INVERSE_REGISTRATION"


def test_b1_cannot_promote_synthetic_hash_shape_as_real_provenance():
    binding = load_json(BINDING_PATH)
    gate = binding["promotion_gate"]
    locks = binding["hard_locks"]
    assert gate["b1_real_replay_valid_source_provenance_required"] is True
    assert gate["b1_must_not_promote_synthetic_fixture_hashes_as_source_proof"] is True
    assert gate["b1_golden_registration_must_use_replay_valid_fixture_artifact_not_b0_synthetic_suite"] is True
    assert locks["NO_SYNTHETIC_FIXTURE_PROMOTION_AS_SOURCE_PROOF"] is True


def test_b1_must_advance_authority_graph_and_preserve_source_ref_admission():
    binding = load_json(BINDING_PATH)
    gate = binding["promotion_gate"]
    assert gate["parent_authority_graph_version_must_advance"] is True
    assert gate["b1_must_preserve_source_ref_admission_semantics"] is True
    assert binding["proposed_type"]["source_ref_admission_semantics"] == (
        "ONLY_REFS_ALREADY_VALIDATED_BY_BOUND_SOURCE_PACKAGE_SEMANTIC_DOMAIN_MAY_BE_CARRIED; "
        "CALLER_STRINGS_CANNOT_MINT_BRANCH_EVIDENCE"
    )


def test_canonical_open_decisions_are_read_directly_from_traceability_registry():
    binding = load_json(BINDING_PATH)
    text = TRACEABILITY_PATH.read_text(encoding="utf-8")
    assert binding["parent_review_context"]["canonical_open_decision_registry"] == "docs/AF001-TRACEABILITY.md"
    assert binding["promotion_gate"]["canonical_open_decisions_must_be_fresh_reconciled_before_b1"] is True
    assert set(binding["open_decisions"]) == set(OPEN_DECISIONS)
    for decision_id in OPEN_DECISIONS:
        section = decision_section(text, decision_id)
        assert "**Competing options:**" in section
        assert "**Required experiment/research:**" in section
        assert "**Risk:**" in section


def test_open_decision_sections_still_describe_unresolved_research_not_runtime_authority():
    text = TRACEABILITY_PATH.read_text(encoding="utf-8")
    clue = decision_section(text, "OD-CLUE-QUALITY-001")
    px = decision_section(text, "OD-PX-SCORING-001")
    assert "without a validated universal metric" in clue
    assert "mystery corpus" in clue
    assert "rejects one universal fun score" in px
    assert "offline rankings" in px
    assert "opt-in player study" in px


def test_b0_fixture_hashes_are_shape_values_only_even_when_well_formed_sha256():
    fixtures = load_json(FIXTURES_PATH)
    hex64 = re.compile(r"^[0-9a-f]{64}$")
    for case in fixtures["positive_cases"]:
        instance = case["instance"]
        assert hex64.fullmatch(instance["source_package_sha256"])
        assert hex64.fullmatch(instance["source_i1_sha256"])
    binding = load_json(BINDING_PATH)
    assert binding["evidence_basis"]["b0_fixture_evidence_class"] == SYNTHETIC_FIXTURE_CLASS
