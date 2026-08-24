import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
ARCH_PATH = ROOT / "ARCHITECTURE.md"
TRACE_PATH = ROOT / "docs" / "AF001-TRACEABILITY.md"
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN_PATH = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
CAP_EVAL_001_PATH = ROOT / "evals" / "CAPABILITY-OPEN-DECISION-EVALS.json"
CAP_EVAL_002_PATH = ROOT / "evals" / "CAPABILITY-ROBUSTNESS-EVALS.json"
HANDOFF_PATH = ROOT / "AI_HANDOFF.yaml"

ATTR_OD = "OD-CAPABILITY-ATTR-001"
MATH_OD = "OD-CAPABILITY-MATH-001"


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def decision_section(trace: str, decision_id: str) -> str:
    pattern = rf"^### {re.escape(decision_id)}.*?$(.*?)(?=^### OD-|^## |\Z)"
    match = re.search(pattern, trace, re.MULTILINE | re.DOTALL)
    assert match, f"missing durable decision record {decision_id}"
    return match.group(1)


def test_capability_architecture_is_resolved_without_resolving_tuning():
    architecture = ARCH_PATH.read_text(encoding="utf-8")

    assert "RESOLVED_ARCHITECTURAL_SUBSTRATE" in architecture
    assert "DEFERRED_RULESET_TUNING" in architecture
    assert "DEFERRED_PLAYER_BALANCE" in architecture
    assert "DEFERRED_GENRE_EXTENSION_POLICY" in architecture

    assert "`ActorBaseProfile` remains canonical persistent/versioned actor capability truth" in architecture
    assert "`SkillLedger` remains separate persistent competence truth" in architecture
    assert "`DerivedCapability` is a current derived projection" in architecture
    assert "Action resolution remains method-specific through `ActionDemandProfile`" in architecture
    assert "may not invent undocumented actor capability truth" in architecture
    assert "not an eternal universal stat ontology" in architecture
    assert "Genre-specific capability remains an explicit extension namespace" in architecture

    assert "An infeasible action is a hard failure" in architecture
    assert "no fabricated numeric margin" in architecture
    assert "`Margin = EffectiveCapability - DifficultyOrResistance`" in architecture
    assert "Relevant impairment effects remain function-local" in architecture
    assert "Success and hazard/injury remain separate axes" in architecture
    assert "Outcome-band thresholds are ruleset-versioned policy" in architecture
    assert "Randomness is optional and downstream of feasibility" in architecture
    assert "deterministic provenance sufficient for exact replay" in architecture


def test_historical_open_decision_evidence_is_preserved_but_split_by_status():
    trace = TRACE_PATH.read_text(encoding="utf-8")
    attr = decision_section(trace, ATTR_OD)
    math = decision_section(trace, MATH_OD)

    for section in (attr, math):
        assert "RESOLVED_ARCHITECTURAL_SUBSTRATE" in section
        assert "Historical OPEN_DECISION preserved" in section
        assert "DEFERRED_RULESET_TUNING" in section
        assert "DEFERRED_PLAYER_BALANCE" in section
        assert "Issue #24 / merged PR #25 CAP-EVAL-001" in section
        assert "Issue #26 / merged PR #27 CAP-EVAL-002" in section
        assert "5004524795" in section

    assert "91a46c7c1ac8a5c7e13f389a81497a5307166ca0" in trace
    assert "DEFERRED_GENRE_EXTENSION_POLICY" in attr
    assert "stack-nonlocality failure" in math
    assert "not evidence against the deterministic feasibility/margin substrate" in math


def test_existing_contract_surface_already_binds_the_resolved_substrate():
    contract = load_json(CONTRACT_PATH)
    registry = contract["type_registry"]

    profile_fields = set(registry["ActorBaseProfile"]["fields"])
    skill_fields = set(registry["SkillLedger"]["fields"])
    derived_fields = set(registry["DerivedCapability"]["fields"])
    demand_fields = set(registry["ActionDemandProfile"]["fields"])
    receipt_fields = set(registry["ActionResolutionReceipt"]["fields"])

    assert {"profile_version", "profile_schema_ref", "ruleset_family_ref", "base_attribute_map", "source_event_refs"} <= profile_fields
    profile = registry["ActorBaseProfile"]
    assert profile["field_semantics"]["profile_schema_ref"].startswith("IMMUTABLE_IDENTIFIER")
    assert "FAILS_CLOSED" in profile["field_semantics"]["profile_schema_ref"]
    assert "profile_schema_ref_AND_ruleset_family_ref" in profile["field_semantics"]["base_attribute_map"]
    assert "PROFILE_SCHEMA_AND_RULESET_FAMILY_REQUIRED" in profile["migration_invariants"]
    assert "UNKNOWN_OR_MISMATCHED_PROFILE_SCHEMA_FAILS_CLOSED" in profile["migration_invariants"]
    assert {"skill_entries", "source_event_cursor", "schema_version"} <= skill_fields
    assert {"source_profile_ref", "source_condition_refs", "ruleset_version"} <= derived_fields
    assert {"method_id", "hard_prerequisites", "ruleset_version"} <= demand_fields
    assert {
        "method_id",
        "feasibility",
        "effective_capability",
        "difficulty_or_resistance",
        "outcome_band",
        "hazard_outcome",
        "random_provenance_optional",
        "ruleset_version",
    } <= receipt_fields

    af_c = contract["freeze_domains"]["AF-C"]
    assert "IMPOSSIBLE_ACTION_FAILS_BEFORE_PROBABILITY" in af_c["invariants"]
    assert "SUCCESS_AND_INJURY_ARE_INDEPENDENT_AXES" in af_c["invariants"]
    assert "RANDOMNESS_REQUIRES_DETERMINISTIC_REPLAY_PROVENANCE" in af_c["invariants"]


def test_fighter_vs_scholar_is_not_architecture_blocked_by_deferred_tuning():
    trace = TRACE_PATH.read_text(encoding="utf-8")
    suite = load_json(GOLDEN_PATH)
    fighter = suite["scenarios"]["FIGHTER_VS_SCHOLAR"]
    machine = fighter["machine_spec"]

    assert machine["implementation_state"] == "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
    bindings = load_json(ROOT / "evals" / "AF001-DECISION-LIFECYCLE-BINDINGS.json")
    binding = bindings["scenario_bindings"]["FIGHTER_VS_SCHOLAR"]
    assert set(machine["open_decision_dependencies"]) == {ATTR_OD, MATH_OD}
    assert set(binding["historical_decision_dependencies"]) == {ATTR_OD, MATH_OD}
    assert binding["current_open_architecture_dependencies"] == []
    assert "Same ruleset/seed provenance" in " ".join(fighter["replay_restart_expectations"])
    assert "versioned rules" in " ".join(fighter["projection_changes"])

    assert "HISTORICAL_TRACE_PLUS_DEFERRED_RULESET_BINDING_NOT_ARCHITECTURE_BLOCKER" in trace
    assert "architecture-blocking capability dependency: `NONE`" in trace
    assert "I2A_ARCHITECTURALLY_UNBLOCKED_PENDING_SEPARATE_CONTROL_TOWER_RELEASE" in trace


def test_cap_eval_candidates_remain_noncanonical_evidence():
    cap_eval_001 = load_json(CAP_EVAL_001_PATH)
    cap_eval_002_text = CAP_EVAL_002_PATH.read_text(encoding="utf-8")
    trace = TRACE_PATH.read_text(encoding="utf-8")

    assert cap_eval_001["all_candidates_non_canonical"] is True
    assert cap_eval_001["candidate_status_required"] == "EVALUATION_CANDIDATE_ONLY"
    for candidate in cap_eval_001["representation_candidates"] + cap_eval_001["math_policy_candidates"]:
        assert candidate["status"] == "EVALUATION_CANDIDATE_ONLY"

    assert "EVALUATION_CANDIDATE_ONLY" in cap_eval_002_text
    for candidate_id in (
        "RICH_GENRE_NEUTRAL_V1",
        "DEMAND_PRIMITIVES_V1",
        "SMALL_CORE_V1",
        "ADDITIVE_MULTIPLICATIVE_STACK_V1",
        "TAGGED_PRIORITY_V1",
        "BOUNDED_SEEDED_STOCHASTIC_V1",
    ):
        assert candidate_id in trace

    assert "RICH_GENRE_NEUTRAL_V1` is not a universal canonical base vector" in trace
    assert "SMALL_CORE_V1` may be a bounded initial/reference ruleset family" in trace
    assert "remain evaluation/ruleset candidates, not universal canonical architecture" in trace


def test_i2_authority_and_runtime_locks_remain_closed():
    architecture = ARCH_PATH.read_text(encoding="utf-8")
    trace = TRACE_PATH.read_text(encoding="utf-8")

    for text in (architecture, trace):
        assert "I2A_ARCHITECTURALLY_UNBLOCKED_PENDING_SEPARATE_CONTROL_TOWER_RELEASE" in text
        assert "RUNTIME_SEMANTICS_UNCHANGED=true" in text
        assert "NO_I2_RUNTIME_IMPLEMENTED=true" in text
        assert "I2_RUNTIME_AUTHORITY_NOT_GRANTED=true" in text

    assert "It does **not** establish `I2_RUNTIME_IMPLEMENTATION_AUTHORIZED`" in architecture
    assert "It is not `I2_RUNTIME_IMPLEMENTATION_AUTHORIZED`" in trace


def test_remediation_handoff_preserves_independent_review_and_closed_authority():
    handoff = HANDOFF_PATH.read_text(encoding="utf-8")

    for marker in (
        "agent_id: CODEX",
        "source_agent: CODEX",
        "target_agent: GPT_INDEPENDENT_REVIEWER",
        "reviewer: GPT_INDEPENDENT_REVIEWER_REQUIRED",
        "handoff_status: READY_FOR_INDEPENDENT_REVIEW",
        "runtime_authority: NOT_GRANTED",
        "merge_authority: NOT_GRANTED",
        "independent_review_required: true",
    ):
        assert marker in handoff
