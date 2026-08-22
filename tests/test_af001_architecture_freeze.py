import json
import re
from dataclasses import fields
from pathlib import Path

from awrse.model import ActorState, Event, ObjectState


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
    "SAW", "HEARD", "WAS_TOLD", "DOCUMENTED", "RUMORED", "INFERRED", "UNKNOWN"
}
FOUNDATION_FILES = {
    "schemas/ACTION-DSL.yaml": "AWRSE-ACTION-DSL",
    "schemas/WORLD-STATE.yaml": "AWRSE-WORLD-STATE",
    "contracts/WORLD-RENDER-PACKET.yaml": "AWRSE-WORLD-RENDER-PACKET",
    "evals/AWRSE-CORE-EVALS.yaml": "AWRSE-CORE-EVALS",
}
REQUIRED_FREEZE_TYPES = {
    "PlayerIdentity", "PlayerChronicle", "PlayerSnapshot", "IntentBelief",
    "CharacterCore", "EnactedPersonaHypothesis", "PlayerAutoExpressionPolicy",
    "WorldInstance", "NPCPerceptionEvent", "NPCPerceptionStream", "EventDeckEntry",
    "WorldFrame", "Scene", "Zone", "Portal", "ActorAggregate", "ObjectAggregate",
    "ActorBaseProfile", "SkillLedger", "DerivedCapability", "ActionDemandProfile",
    "ActionResolutionReceipt", "InjuryState", "FatigueState", "StatusEffect",
    "EquipmentModifier", "EquipmentLoadout", "ActorPresentationState", "OutfitState",
    "DressingState", "SurfaceState", "CameraAnchor", "View", "MediaAsset",
    "MediaVersion", "Locator", "ActorAppearanceSnapshot", "NPCEpisodicMemory",
    "BeliefState", "NPCPlayerRelationshipState", "NPCContextBundle", "StoryDNA",
    "StoryBible", "GenreEngine", "CharacterDramaticCore", "HardCausalAnchor",
    "SoftDramaticAttractor", "Storylet", "InformationPacket", "NarrativePromise",
    "NarrativeOpportunityBroker", "PlausibilityGate", "EncounterCandidate",
    "WorldEchoOpportunity", "ResponseConcept", "PXRankingReceipt",
    "DIRECTOR-BEAT-PACKET", "ActorPresentationRequirements", "PublicationProjection",
}
EXPECTED_SCENARIO_OD_DEPS = {
    "WILDERNESS_NEWS_TRAP": {
        "OD-CAPABILITY-ATTR-001", "OD-CAPABILITY-MATH-001",
        "OD-ENCOUNTER-DENSITY-001", "OD-PX-SCORING-001", "OD-PUBLICATION-POLICY-001",
    },
    "BROKEN_DOOR_WORLD_ECHO": {
        "OD-COMMENTARY-BUDGET-001", "OD-PX-SCORING-001", "OD-MEMORY-DECAY-001",
    },
    "FIGHTER_VS_SCHOLAR": {"OD-CAPABILITY-ATTR-001", "OD-CAPABILITY-MATH-001"},
    "PROMISE_RETURN_CALLBACK": {
        "OD-MEMORY-STORE-001", "OD-MEMORY-DECAY-001", "OD-RELATIONSHIP-MATH-001",
    },
    "PERSONA_SPEECH_BOUNDARY": set(),
    "ASSET_APPEARANCE_REVISIT": {"OD-DIRECTOR-ADAPTER-001"},
    "HOSTILE_PLAYER_BREAKS_PLOT": {
        "OD-GENRE-REGISTRY-001", "OD-CLUE-QUALITY-001", "OD-PX-SCORING-001",
    },
    "MULTIPLAYER_DIFFERENT_KNOWLEDGE": {
        "OD-CONCURRENCY-001", "OD-PUBLICATION-POLICY-001",
    },
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _all_open_decision_refs(contract):
    refs = set()
    for domain in contract["freeze_domains"].values():
        refs.update(domain.get("open_decision_refs", []))
    return refs


def _decision_sections(trace: str):
    matches = list(re.finditer(r"^### (OD-[A-Z0-9-]+).*?$", trace, re.MULTILINE))
    sections = {}
    for index, match in enumerate(matches):
        start = match.end()
        next_od = matches[index + 1].start() if index + 1 < len(matches) else len(trace)
        next_h2_match = re.search(r"^## ", trace[start:next_od], re.MULTILINE)
        end = start + next_h2_match.start() if next_h2_match else next_od
        sections[match.group(1)] = trace[start:end]
    return sections


def _iter_type_refs(value):
    if isinstance(value, dict):
        for key, item in value.items():
            if key in {"type_ref", "subject_type_ref"}:
                yield item
            else:
                yield from _iter_type_refs(item)
    elif isinstance(value, list):
        for item in value:
            yield from _iter_type_refs(item)


def test_af001_artifact_authority_roles_are_structured_and_unique():
    contract = load_json(CONTRACT_PATH)
    roles = contract["artifact_roles"]
    assert roles["ARCHITECTURE.md"] == "CANONICAL_ARCHITECTURE_MASTER"
    assert list(roles.values()).count("CANONICAL_ARCHITECTURE_MASTER") == 1
    assert roles["contracts/AF001-LIVING-STORY-CONTRACTS.json"] == "MACHINE_CONTRACT_REGISTRY"
    assert roles["evals/AF001-GOLDEN-SCENARIOS.json"] == "GOLDEN_EXECUTABLE_SPEC_REGISTRY"
    assert roles["docs/AF001-TRACEABILITY.md"] == "TRACEABILITY_OPEN_DECISION_REGISTRY"

    architecture = ARCH_PATH.read_text(encoding="utf-8")
    assert "Authority role: `CANONICAL_ARCHITECTURE_MASTER`" in architecture
    assert "RUNTIME_EXPANSION_BLOCKED_UNTIL_AF001_ACCEPTED" in architecture

    trace = TRACE_PATH.read_text(encoding="utf-8")
    block = re.search(r"```json\n(\{.*?\})\n```", trace, re.DOTALL)
    assert block, "structured artifact authority-role JSON block missing"
    assert json.loads(block.group(1)) == roles


def test_af001_contract_registry_freezes_all_domains_without_runtime_claim():
    contract = load_json(CONTRACT_PATH)
    assert contract["contract_id"] == "AWRSE-AF001-LIVING-STORY-CONTRACTS"
    assert contract["status"] == "ARCHITECTURE_FREEZE_CANDIDATE"
    assert contract["authority_order"] == EXPECTED_AUTHORITY_ORDER
    assert len(set(contract["authority_order"])) == len(EXPECTED_AUTHORITY_ORDER)
    assert set(contract["freeze_domains"]) == EXPECTED_DOMAINS
    for domain_id, domain in contract["freeze_domains"].items():
        assert domain["implementation_state"].startswith("FREEZE_INTERFACE_ONLY"), domain_id
    assert set(contract["freeze_domains"]["AF-E"]["knowledge_modes"]) == EXPECTED_KNOWLEDGE_MODES
    assert contract["freeze_domains"]["AF-E"]["runtime_rule"].endswith("PROVENANCE_OR_FAILS_CLOSED")


def test_af001_preserves_r001_r002_foundation_files_and_invariants():
    contract = load_json(CONTRACT_PATH)
    assert set(contract["foundations"]["preserved_contracts"]) == set(FOUNDATION_FILES)
    for relative_path, marker in FOUNDATION_FILES.items():
        text = (ROOT / relative_path).read_text(encoding="utf-8")
        assert marker in text, relative_path
    render_contract = (ROOT / "contracts" / "WORLD-RENDER-PACKET.yaml").read_text(encoding="utf-8")
    assert "no_world_rule_mutation" in render_contract
    assert "no_unconfirmed_outcome_invention" in render_contract
    assert "mismatch_policy" in render_contract


def test_b01_legacy_event_profile_exactly_covers_accepted_runtime_event_shape():
    contract = load_json(CONTRACT_PATH)
    legacy = contract["event_profiles"]["LEGACY_R001_R002_EVENT_PROFILE"]
    runtime_fields = [field.name for field in fields(Event)]
    assert legacy["required_fields"] == runtime_fields
    assert legacy["source_type"] == "runtime.awrse.model.Event"
    assert legacy["implementation_state"] == "ACCEPTED_RUNTIME_ACTIVE"
    assert legacy["replay_status"] == "FULLY_LEGAL_FOR_ACCEPTED_R001_R002_HISTORY"
    assert legacy["source_event_rewrite_allowed"] is False


def test_b01_vnext_event_profile_has_nonretroactive_nonfabricating_bridge():
    contract = load_json(CONTRACT_PATH)
    compat = contract["event_compatibility"]
    vnext = contract["event_profiles"]["AF001_VNEXT_EVENT_ENVELOPE"]
    assert vnext["implementation_state"] == "FUTURE_CONTRACT_NOT_RUNTIME_ACTIVE"
    assert vnext["retroactive_requirement"] is False
    assert "LATER_BOUNDED" in vnext["mandatory_activation_gate"]
    assert compat["adapter_class"] == "NON_MUTATING_COMPATIBILITY_VIEW_ONLY"
    assert compat["source_events_never_rewritten"] is True
    assert compat["lossless_mapping"]["baseline_version"] == "legacy_baseline_version"
    for field in {"schema_version", "ruleset_version", "world_id", "authority_scope_ref", "ordering_or_version_cursor"}:
        assert field in compat["not_inferable_from_legacy_event"]
        assert "UNKNOWN" in compat["not_inferable_from_legacy_event"][field]
    assert "DO_NOT_TREAT_baseline_version_AS_schema_version" in compat["prohibited_inference"]
    assert "DO_NOT_TREAT_baseline_version_AS_ruleset_version" in compat["prohibited_inference"]


def test_b02_state_ownership_registry_has_single_truth_and_rebuild_direction():
    contract = load_json(CONTRACT_PATH)
    registry = contract["state_ownership_registry"]
    required = {
        "legal_social_ownership", "physical_possession", "inventory", "worn_state",
        "equipped_state", "location", "knowledge_acquisition_evidence",
    }
    assert set(registry) == required
    mandatory = {
        "canonical_owner", "projection_or_index_copies", "authorized_mutation_source",
        "consistency_invariant", "rebuild_direction", "legacy_r002_mapping",
    }
    for relation, spec in registry.items():
        assert mandatory <= set(spec), relation
        for field in mandatory:
            assert spec[field], f"{relation}.{field}"

    possession = registry["physical_possession"]
    inventory = registry["inventory"]
    ownership = registry["legal_social_ownership"]
    assert possession["canonical_owner"] == "ObjectAggregate.possessor_ref"
    assert possession["projection_or_index_copies"] == ["ActorAggregate.inventory_refs"]
    assert "owner_actor_id_MAPS_TO_ObjectAggregate.possessor_ref" in possession["legacy_r002_mapping"]
    assert inventory["canonical_owner"] == "DERIVED_INDEX_FROM_ObjectAggregate.possessor_ref"
    assert "NO_LOSSLESS_MAPPING" in ownership["legacy_r002_mapping"]


def test_b02_legacy_model_semantics_are_not_reinterpreted_as_legal_ownership():
    contract = load_json(CONTRACT_PATH)
    object_fields = {field.name for field in fields(ObjectState)}
    actor_fields = {field.name for field in fields(ActorState)}
    assert "owner_actor_id" in object_fields
    assert "inventory_refs" in actor_fields
    possession = contract["state_ownership_registry"]["physical_possession"]
    legal = contract["state_ownership_registry"]["legal_social_ownership"]
    assert "owner_actor_id" in possession["legacy_r002_mapping"]
    assert "possessor_ref" in possession["legacy_r002_mapping"]
    assert "owner_actor_id" in legal["legacy_r002_mapping"]
    assert "UNKNOWN" in legal["legacy_r002_mapping"]


def test_b02_epistemic_projections_cannot_create_knowledge_evidence():
    contract = load_json(CONTRACT_PATH)
    knowledge = contract["state_ownership_registry"]["knowledge_acquisition_evidence"]
    assert knowledge["canonical_owner"] == "PROVENANCE_BEARING_ACQUISITION_OR_PERCEPTION_EVENT_PATH"
    assert "PlayerChronicle" in knowledge["projection_or_index_copies"]
    assert "NPCEpisodicMemory" in knowledge["projection_or_index_copies"]
    assert "MAY_NOT_CREATE_NEW_KNOWLEDGE_EVIDENCE" in knowledge["consistency_invariant"]
    assert knowledge["rebuild_direction"] == "ACQUISITION_EVIDENCE_TO_RECIPIENT_LOCAL_PROJECTIONS"


def test_b03_required_freeze_surface_types_resolve_with_owner_version_and_state():
    contract = load_json(CONTRACT_PATH)
    registry = contract["type_registry"]
    missing = REQUIRED_FREEZE_TYPES - set(registry)
    assert not missing, f"missing freeze types: {sorted(missing)}"
    for name in REQUIRED_FREEZE_TYPES:
        spec = registry[name]
        assert spec["type_id"]
        assert spec["version"]
        assert spec["domain"] in EXPECTED_DOMAINS
        assert spec["authority_owner"]
        assert spec["implementation_state"]
        assert spec["fields"], name
    for domain in contract["freeze_domains"].values():
        for ref in domain.get("type_refs", []):
            assert ref in registry, ref


def test_b03_event_deck_is_explicit_storylet_alias_not_duplicate_truth():
    registry = load_json(CONTRACT_PATH)["type_registry"]
    entry = registry["EventDeckEntry"]
    assert entry["alias_of"] == "Storylet"
    assert entry["implementation_state"] == "ALIAS_INTERFACE_ONLY"
    assert "CANNOT_CREATE_SEPARATE_WORLD_TRUTH" in entry["alias_semantics"]


def test_b04_human_golden_scenarios_remain_complete():
    suite = load_json(GOLDEN_PATH)
    scenarios = suite["scenarios"]
    required_fields = set(suite["required_fields_per_scenario"])
    assert set(scenarios) == EXPECTED_SCENARIOS
    for scenario_id, scenario in scenarios.items():
        for field in required_fields:
            assert field in scenario, f"{scenario_id}.{field} missing"
            assert isinstance(scenario[field], list), f"{scenario_id}.{field} not list"
            assert scenario[field], f"{scenario_id}.{field} empty"
        assert scenario.get("purpose")


def test_b04_machine_specs_have_real_resolvable_type_refs_and_predicates():
    contract = load_json(CONTRACT_PATH)
    suite = load_json(GOLDEN_PATH)
    registry = contract["type_registry"]
    required_machine = set(suite["machine_required_fields"])
    for scenario_id, scenario in suite["scenarios"].items():
        machine = scenario.get("machine_spec")
        assert machine, scenario_id
        assert required_machine <= set(machine), f"{scenario_id} machine fields"
        assert machine["scenario_id"] == scenario_id
        assert machine["scenario_version"]
        assert machine["implementation_state"] == "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
        assert machine["actual_type_refs"], scenario_id
        for ref in machine["actual_type_refs"]:
            assert ref in registry, f"{scenario_id} unresolved actual_type_ref {ref}"
        for field in (
            "initial_state_predicates", "expected_event_state_predicates", "forbidden_predicates",
            "provenance_authority_assertions", "ordering_assertions", "replay_restart_assertions",
        ):
            assert isinstance(machine[field], list) and machine[field], f"{scenario_id}.{field}"
        for ref in _iter_type_refs(machine):
            assert ref in registry, f"{scenario_id} unresolved nested type ref {ref}"


def test_b04_open_decision_sections_are_independently_bounded_and_complete():
    contract = load_json(CONTRACT_PATH)
    trace = TRACE_PATH.read_text(encoding="utf-8")
    sections = _decision_sections(trace)
    expected_refs = _all_open_decision_refs(contract)
    assert set(sections) == expected_refs
    fields_required = (
        "**Competing options:**", "**Evidence:**", "**Dependency:**",
        "**Risk:**", "**Required experiment/research:**",
    )
    for decision_id, section in sections.items():
        assert "### OD-" not in section, f"{decision_id} section leaked into next decision"
        for marker in fields_required:
            assert marker in section, f"{decision_id} missing {marker}"
            tail = section.split(marker, 1)[1].split("\n", 1)[0].strip()
            assert tail, f"{decision_id} empty {marker}"


def test_b04_scenario_open_decision_dependencies_are_explicit_and_resolve():
    contract = load_json(CONTRACT_PATH)
    suite = load_json(GOLDEN_PATH)
    available = _all_open_decision_refs(contract)
    for scenario_id, expected in EXPECTED_SCENARIO_OD_DEPS.items():
        actual = set(suite["scenarios"][scenario_id]["machine_spec"]["open_decision_dependencies"])
        assert actual == expected, f"{scenario_id}: expected {sorted(expected)}, got {sorted(actual)}"
        assert actual <= available


def test_b04_authority_and_ordering_assertions_are_not_empty_placeholders():
    suite = load_json(GOLDEN_PATH)
    for scenario_id, scenario in suite["scenarios"].items():
        machine = scenario["machine_spec"]
        for assertion in machine["provenance_authority_assertions"]:
            assert assertion.get("assertion_id")
            assert assertion.get("subject_type_ref")
            assert assertion.get("must") or assertion.get("must_not")
        for assertion in machine["ordering_assertions"]:
            assert assertion.get("assertion_id")
            assert assertion.get("before")
            assert assertion.get("after")
            assert assertion["before"] != assertion["after"], scenario_id
        for assertion in machine["replay_restart_assertions"]:
            assert assertion.get("assertion_id")
            assert assertion.get("type_ref")
            assert assertion.get("assertion")


def test_af001_traceability_covers_design_inputs_governance_and_single_registries():
    contract = load_json(CONTRACT_PATH)
    suite = load_json(GOLDEN_PATH)
    trace = TRACE_PATH.read_text(encoding="utf-8")
    for issue_number in range(5, 16):
        assert f"Issue #{issue_number}" in trace
    for phrase in (
        "Authority matrix", "State ownership matrix", "Dependency graph",
        "Golden Scenario coverage matrix", "Migration/versioning obligations",
        "Historical R001/R002 non-regression map", "OPEN_DECISION registry",
        "Independent Reviewer + Control Tower",
    ):
        assert phrase in trace
    assert contract["canonical_architecture_master"] == "ARCHITECTURE.md"
    assert contract["traceability_registry"] == "docs/AF001-TRACEABILITY.md"
    assert contract["golden_scenario_registry"] == "evals/AF001-GOLDEN-SCENARIOS.json"
    assert suite["contract_registry"] == "contracts/AF001-LIVING-STORY-CONTRACTS.json"
    assert suite["foundation_eval_registry"] == "evals/AWRSE-CORE-EVALS.yaml"
