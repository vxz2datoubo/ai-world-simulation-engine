import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN_PATH = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
ARCH_PATH = ROOT / "ARCHITECTURE.md"
TRACE_PATH = ROOT / "docs" / "AF001-TRACEABILITY.md"

EXPECTED_DOMAINS = {f"AF-{letter}" for letter in "ABCDEFGH"}
EXPECTED_SCENARIOS = {
    "WILDERNESS_NEWS_TRAP",
    "BROKEN_DOOR_WORLD_ECHO",
    "FIGHTER_VS_SCHOLAR",
    "PROMISE_RETURN_CALLBACK",
    "PERSONA_SPEECH_BOUNDARY",
    "ASSET_APPEARANCE_REVISIT",
    "HOSTILE_PLAYER_BREAKS_PLOT",
    "MULTIPLAYER_DIFFERENT_KNOWLEDGE",
}
EXPECTED_AUTHORITY_ORDER = [
    "WORLD_RULES_AUTHORITY",
    "CAPABILITY_STATE_RESOLUTION",
    "KNOWLEDGE_MEMORY",
    "NARRATIVE_OPPORTUNITY",
    "PX_RANKING",
    "AI_DIRECTOR",
    "RENDERER_PUBLICATION",
]
EXPECTED_KNOWLEDGE_MODES = {
    "SAW",
    "HEARD",
    "WAS_TOLD",
    "DOCUMENTED",
    "RUMORED",
    "INFERRED",
    "UNKNOWN",
}
FOUNDATION_FILES = {
    "schemas/ACTION-DSL.yaml": "AWRSE-ACTION-DSL",
    "schemas/WORLD-STATE.yaml": "AWRSE-WORLD-STATE",
    "contracts/WORLD-RENDER-PACKET.yaml": "AWRSE-WORLD-RENDER-PACKET",
    "evals/AWRSE-CORE-EVALS.yaml": "AWRSE-CORE-EVALS",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_af001_single_authority_and_required_artifacts_exist():
    assert ARCH_PATH.is_file()
    assert CONTRACT_PATH.is_file()
    assert GOLDEN_PATH.is_file()
    assert TRACE_PATH.is_file()

    architecture = ARCH_PATH.read_text(encoding="utf-8")
    assert "single current architecture master" in architecture
    assert "AF001_ARCHITECTURE_FREEZE_CANDIDATE" in architecture
    assert "RUNTIME_EXPANSION_BLOCKED_UNTIL_AF001_ACCEPTED" in architecture
    for domain in sorted(EXPECTED_DOMAINS):
        assert domain in architecture


def test_af001_contract_registry_freezes_all_domains_without_claiming_runtime_implementation():
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_id"] == "AWRSE-AF001-LIVING-STORY-CONTRACTS"
    assert contract["status"] == "ARCHITECTURE_FREEZE_CANDIDATE"
    assert contract["authority_order"] == EXPECTED_AUTHORITY_ORDER
    assert len(set(contract["authority_order"])) == len(EXPECTED_AUTHORITY_ORDER)

    domains = contract["freeze_domains"]
    assert set(domains) == EXPECTED_DOMAINS
    for domain_id, domain in domains.items():
        assert domain["implementation_state"].startswith("FREEZE_INTERFACE_ONLY"), domain_id
        assert domain.get("name")

    assert set(domains["AF-E"]["knowledge_modes"]) == EXPECTED_KNOWLEDGE_MODES
    assert (
        domains["AF-E"]["runtime_rule"]
        == "EACH_IMPLEMENTED_MODE_REQUIRES_EXECUTABLE_MODE_SPECIFIC_PROVENANCE_OR_FAILS_CLOSED"
    )
    assert "DOWNSTREAM_CANNOT_REWRITE_UPSTREAM_TRUTH" in domains["AF-A"]["invariants"]
    assert "FUNCTIONAL_INJURY_NE_VISIBLE_TREATMENT" in domains["AF-D"]["invariants"]
    assert "NO_VALID_OPPORTUNITY_IS_VALID" in domains["AF-G"]["invariants"]
    assert "AI_DIRECTOR_IS_DOWNSTREAM_READ_ONLY" in domains["AF-H"]["invariants"]


def test_af001_preserves_and_references_r001_r002_foundations_instead_of_shadowing_them():
    contract = load_json(CONTRACT_PATH)
    preserved = set(contract["foundations"]["preserved_contracts"])
    assert preserved == set(FOUNDATION_FILES)

    for relative_path, marker in FOUNDATION_FILES.items():
        path = ROOT / relative_path
        assert path.is_file(), relative_path
        text = path.read_text(encoding="utf-8")
        assert marker in text, relative_path

    render_contract = (ROOT / "contracts" / "WORLD-RENDER-PACKET.yaml").read_text(
        encoding="utf-8"
    )
    assert "no_world_rule_mutation" in render_contract
    assert "no_unconfirmed_outcome_invention" in render_contract
    assert "mismatch_policy" in render_contract


def test_af001_golden_scenarios_are_complete_and_contract_bound():
    contract = load_json(CONTRACT_PATH)
    suite = load_json(GOLDEN_PATH)
    scenarios = suite["scenarios"]
    required_fields = set(suite["required_fields_per_scenario"])

    assert set(scenarios) == EXPECTED_SCENARIOS
    assert required_fields == {
        "initial_canonical_state",
        "allowed_player_intents",
        "required_contracts",
        "expected_canonical_events",
        "projection_changes",
        "knowledge_consequences",
        "narrative_consequences",
        "presentation_requirements",
        "forbidden_outcomes",
        "replay_restart_expectations",
        "adversarial_variants",
        "acceptance_criteria",
    }

    available_contracts = set(contract["freeze_domains"])
    for scenario_id, scenario in scenarios.items():
        missing = required_fields - set(scenario)
        assert not missing, f"{scenario_id} missing {sorted(missing)}"
        for field in required_fields:
            value = scenario[field]
            assert isinstance(value, list), f"{scenario_id}.{field} must be a list"
            assert value, f"{scenario_id}.{field} must be non-empty"
        assert set(scenario["required_contracts"]).issubset(available_contracts)
        assert scenario["forbidden_outcomes"]
        assert scenario["adversarial_variants"]
        assert scenario["replay_restart_expectations"]
        assert scenario["acceptance_criteria"]


def test_af001_golden_scenarios_cover_every_freeze_domain_and_high_risk_boundaries():
    suite = load_json(GOLDEN_PATH)
    scenarios = suite["scenarios"]
    covered = set()
    for scenario in scenarios.values():
        covered.update(scenario["required_contracts"])
    assert covered == EXPECTED_DOMAINS

    assert "AF-E" in scenarios["MULTIPLAYER_DIFFERENT_KNOWLEDGE"]["required_contracts"]
    assert "AF-G" in scenarios["PERSONA_SPEECH_BOUNDARY"]["required_contracts"]
    assert "AF-C" in scenarios["FIGHTER_VS_SCHOLAR"]["required_contracts"]
    assert "AF-D" in scenarios["ASSET_APPEARANCE_REVISIT"]["required_contracts"]
    assert "AF-F" in scenarios["HOSTILE_PLAYER_BREAKS_PLOT"]["required_contracts"]


def test_af001_open_decisions_are_explicit_and_cross_referenced():
    contract = load_json(CONTRACT_PATH)
    trace = TRACE_PATH.read_text(encoding="utf-8")

    decision_refs = set()
    for domain in contract["freeze_domains"].values():
        decision_refs.update(domain.get("open_decision_refs", []))

    assert decision_refs
    for decision_id in sorted(decision_refs):
        assert f"### {decision_id}" in trace
        section = trace.split(f"### {decision_id}", 1)[1]
        assert "**Competing options:**" in section
        assert "**Evidence:**" in section
        assert "**Dependency:**" in section
        assert "**Risk:**" in section
        assert "**Required experiment/research:**" in section


def test_af001_traceability_covers_all_design_inputs_and_governance():
    trace = TRACE_PATH.read_text(encoding="utf-8")
    for issue_number in range(5, 16):
        assert f"Issue #{issue_number}" in trace or f"# {issue_number}" in trace

    for phrase in (
        "Authority matrix",
        "Dependency graph",
        "Golden Scenario coverage matrix",
        "Migration/versioning obligations",
        "Historical R001/R002 non-regression map",
        "OPEN_DECISION registry",
        "Independent Reviewer + Control Tower",
    ):
        assert phrase in trace


def test_af001_no_machine_contract_duplicates_architecture_master_role():
    contract = load_json(CONTRACT_PATH)
    suite = load_json(GOLDEN_PATH)
    assert contract["canonical_architecture_master"] == "ARCHITECTURE.md"
    assert contract["traceability_registry"] == "docs/AF001-TRACEABILITY.md"
    assert contract["golden_scenario_registry"] == "evals/AF001-GOLDEN-SCENARIOS.json"
    assert suite["contract_registry"] == "contracts/AF001-LIVING-STORY-CONTRACTS.json"
    assert suite["foundation_eval_registry"] == "evals/AWRSE-CORE-EVALS.yaml"
