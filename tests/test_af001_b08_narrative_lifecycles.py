import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN_PATH = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
ARCHITECTURE_PATH = ROOT / "ARCHITECTURE.md"


def load_json(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def test_b08_hard_causal_anchor_definition_and_status_have_separate_field_authority():
    contract = load_json(CONTRACT_PATH)
    anchor = contract["type_registry"]["HardCausalAnchor"]
    field_profiles = anchor["field_authority_profiles"]

    assert anchor["authority_profile_ref"] == "NARRATIVE_MIXED_DEFINITION_DERIVED_VIEW"
    assert anchor["implementation_state"] == "INTERFACE_ONLY_COMPOSITE_AUTHORED_DEFINITION_PLUS_DERIVED_VALIDITY"
    assert field_profiles["authored_definition"]["profile_ref"] == "NARRATIVE_DESIGN_NON_CANONICAL"
    assert set(field_profiles["authored_definition"]["fields"]) == {
        "cause_refs", "planned_event_or_process", "revalidation_predicates"
    }
    assert field_profiles["derived_lifecycle"]["profile_ref"] == "CAUSAL_ANCHOR_VALIDITY_LIFECYCLE"
    assert field_profiles["derived_lifecycle"]["fields"] == ["status"]


def test_b08_authored_loader_cannot_independently_advance_or_restore_anchor_status():
    contract = load_json(CONTRACT_PATH)
    profiles = contract["authority_semantics"]["profiles"]
    status_profile = profiles["CAUSAL_ANCHOR_VALIDITY_LIFECYCLE"]

    assert status_profile["producer_or_assembler"] == ["AWRSE_CAUSAL_ANCHOR_REVALIDATOR"]
    assert "AWRSE_NARRATIVE_DESIGN_LOADER" not in status_profile["producer_or_assembler"]
    assert "NARRATIVE_DESIGN_NON_CANONICAL" not in status_profile["canonical_data_authority"]
    constraint = status_profile["mutation_constraint"]
    assert "NARRATIVE_DESIGN_CANNOT_SET_ADVANCE_OR_RESTORE_VALID_STATUS" in constraint
    assert "ONLY_LEGITIMATE_CAUSE_EVENT_EVIDENCE_PLUS_REVALIDATION_MAY_CHANGE_DERIVED_STATUS" in constraint


def test_b08_invalid_destroyed_missing_or_unresolved_required_cause_fails_closed():
    contract = load_json(CONTRACT_PATH)
    anchor = contract["type_registry"]["HardCausalAnchor"]
    lifecycle = anchor["field_authority_profiles"]["derived_lifecycle"]
    profile = contract["authority_semantics"]["profiles"][lifecycle["profile_ref"]]

    assert "INVALID_DESTROYED_MISSING_OR_UNRESOLVED_REQUIRED_CAUSE_FAILS_CLOSED" in lifecycle["rebuild_semantics"]
    assert "DESTROYED_INVALID_MISSING_OR_UNRESOLVED_REQUIRED_CAUSE_FAILS_CLOSED_TO_NON_VALID" in profile["mutation_constraint"]
    assert "WORLD_RULES_AUTHORITY" in profile["canonical_data_authority"]
    assert "PROVENANCE_BEARING_SOURCE_EVIDENCE" in profile["canonical_data_authority"]


def test_b08_anchor_status_rebuild_and_rehydration_are_evidence_bound_and_deterministic():
    contract = load_json(CONTRACT_PATH)
    lifecycle = contract["type_registry"]["HardCausalAnchor"]["field_authority_profiles"]["derived_lifecycle"]

    assert set(lifecycle["source_evidence_requirements"]) == {
        "cause_refs",
        "CANONICAL_CAUSE_STATE_OR_EVENT_EVIDENCE",
        "CANONICAL_EVENT_CURSOR_OR_EQUIVALENT_ORDERING_EVIDENCE",
    }
    assert lifecycle["rebuild_semantics"].startswith("DETERMINISTIC_REBUILD_FROM_CAUSE_REFS_PLUS_CANONICAL_EVENTS_OR_EVIDENCE")
    assert "RECOMPUTE_DERIVED_STATUS_FROM_BOUND_CAUSES_AND_EVENT_EVIDENCE" in lifecycle["rehydration_semantics"]
    assert "NEVER_REHYDRATE_STATUS_FROM_AUTHORED_DESIRE_OR_STALE_CACHE" in lifecycle["rehydration_semantics"]


def test_b08_legitimate_new_cause_or_event_evidence_can_trigger_revalidation():
    contract = load_json(CONTRACT_PATH)
    lifecycle = contract["type_registry"]["HardCausalAnchor"]["field_authority_profiles"]["derived_lifecycle"]
    profile = contract["authority_semantics"]["profiles"]["CAUSAL_ANCHOR_VALIDITY_LIFECYCLE"]

    assert lifecycle["revalidation_transition_rule"] == (
        "ONLY_LEGITIMATE_NEW_CAUSE_OR_EVENT_EVIDENCE_MAY_TRIGGER_REVALIDATION_AND_CHANGE_DERIVED_STATUS"
    )
    assert "ONLY_LEGITIMATE_CAUSE_EVENT_EVIDENCE_PLUS_REVALIDATION_MAY_CHANGE_DERIVED_STATUS" in profile["mutation_constraint"]


def test_b08_golden_destroyed_cause_and_rebuild_assertions_are_preserved_and_resolved():
    golden = load_json(GOLDEN_PATH)
    rules = golden["machine_semantics"]["assertion_rule_registry"]

    destroyed = rules["destroyed_cause_invalidates_dependent_anchor"]
    rebuilt = rules["anchor_status_rebuilds_from_causes_and_events"]

    assert destroyed["allowed_type_refs"] == ["HardCausalAnchor"]
    assert set(destroyed["field_refs"]) == {
        "HardCausalAnchor.cause_refs",
        "HardCausalAnchor.revalidation_predicates",
        "HardCausalAnchor.status",
    }
    assert rebuilt["allowed_type_refs"] == ["HardCausalAnchor"]
    assert set(rebuilt["field_refs"]) == {
        "HardCausalAnchor.cause_refs", "HardCausalAnchor.status"
    }

    machine = golden["scenarios"]["HOSTILE_PLAYER_BREAKS_PLOT"]["machine_spec"]
    expected = {p["assertion"] for p in machine["expected_event_state_predicates"]}
    replay = {p["assertion"] for p in machine["replay_restart_assertions"]}
    assert "destroyed_cause_invalidates_dependent_anchor" in expected
    assert "anchor_status_rebuilds_from_causes_and_events" in replay


def test_b08_narrative_desire_cannot_override_invalid_anchor_in_master_and_contract():
    contract = load_json(CONTRACT_PATH)
    master = ARCHITECTURE_PATH.read_text(encoding="utf-8")
    af_f = set(contract["freeze_domains"]["AF-F"]["invariants"])

    assert "NARRATIVE_DESIRE_CANNOT_RESTORE_INVALID_CAUSAL_ANCHOR" in af_f
    assert "AUTHORED_HARD_CAUSAL_ANCHOR_DEFINITION_NE_DERIVED_VALIDITY_STATUS" in af_f
    assert "HARD_CAUSAL_ANCHOR_STATUS_REBUILDS_FROM_CAUSE_EVENT_EVIDENCE" in af_f
    assert "narrative design cannot set, advance or restore current-valid status" in master
    assert "legitimate cause restoration/change may permit revalidation" in master


def test_b08_soft_attractor_adjacent_audit_separates_authored_definition_from_dynamic_status():
    contract = load_json(CONTRACT_PATH)
    attractor = contract["type_registry"]["SoftDramaticAttractor"]
    fields = attractor["field_authority_profiles"]
    profile = contract["authority_semantics"]["profiles"]["SOFT_ATTRACTOR_STATUS_LIFECYCLE"]

    assert attractor["authority_profile_ref"] == "NARRATIVE_MIXED_DEFINITION_DERIVED_VIEW"
    assert set(fields["authored_definition"]["fields"]) == {
        "dramatic_function", "eligibility_predicates", "expiry_policy"
    }
    assert fields["authored_definition"]["profile_ref"] == "NARRATIVE_DESIGN_NON_CANONICAL"
    assert fields["derived_lifecycle"]["fields"] == ["status"]
    assert fields["derived_lifecycle"]["profile_ref"] == "SOFT_ATTRACTOR_STATUS_LIFECYCLE"
    assert profile["producer_or_assembler"] == ["AWRSE_SOFT_ATTRACTOR_STATUS_PROJECTOR"]
    assert "AUTHORED_DRAMATIC_DESIRE_CANNOT_FORCE" in profile["mutation_constraint"]


def test_b08_character_arc_adjacent_audit_separates_authored_core_from_history_derived_arc_state():
    contract = load_json(CONTRACT_PATH)
    core = contract["type_registry"]["CharacterDramaticCore"]
    fields = core["field_authority_profiles"]
    profile = contract["authority_semantics"]["profiles"]["CHARACTER_ARC_STATE_LIFECYCLE"]

    assert core["authority_profile_ref"] == "NARRATIVE_MIXED_DEFINITION_DERIVED_VIEW"
    assert "arc_state" not in fields["authored_definition"]["fields"]
    assert fields["derived_lifecycle"]["fields"] == ["arc_state"]
    assert fields["derived_lifecycle"]["profile_ref"] == "CHARACTER_ARC_STATE_LIFECYCLE"
    assert profile["producer_or_assembler"] == ["AWRSE_CHARACTER_ARC_PROJECTOR"]
    assert "RECORDED_HISTORY_CHOICES_AND_EVIDENCE" in profile["mutation_constraint"]
    assert "AUTHORED_ARC_DESIRE_CANNOT_ADVANCE_OR_REWRITE_CURRENT_ARC_STATE" in profile["mutation_constraint"]


def test_b08_preserves_b01_through_b07_critical_contract_boundaries():
    contract = load_json(CONTRACT_PATH)
    registry = contract["type_registry"]

    # B01 legacy/vNext compatibility remains non-retroactive and non-fabricating.
    assert contract["event_profiles"]["LEGACY_R001_R002_EVENT_PROFILE"]["implementation_state"] == "ACCEPTED_RUNTIME_ACTIVE"
    assert contract["event_profiles"]["AF001_VNEXT_EVENT_ENVELOPE"]["retroactive_requirement"] is False
    assert contract["event_compatibility"]["source_events_never_rewritten"] is True

    # B02 ownership/provenance single-source boundaries remain explicit.
    ownership = contract["state_ownership_registry"]
    assert ownership["physical_possession"]["canonical_owner"] == "ObjectAggregate.possessor_ref"
    assert ownership["inventory"]["canonical_owner"] == "DERIVED_INDEX_FROM_ObjectAggregate.possessor_ref"
    assert ownership["knowledge_acquisition_evidence"]["canonical_owner"] == "PROVENANCE_BEARING_ACQUISITION_OR_PERCEPTION_EVENT_PATH"

    # B05 Director / player-policy authority remains downstream-safe.
    expected = {
        "CharacterCore": "PLAYER_EXPLICIT_CHARACTER_CORE",
        "EnactedPersonaHypothesis": "EVIDENCE_DERIVED_PERSONA_HYPOTHESIS",
        "PlayerAutoExpressionPolicy": "PLAYER_EXPLICIT_AUTO_EXPRESSION_POLICY",
        "DIRECTOR-BEAT-PACKET": "AWRSE_DIRECTOR_HANDOFF",
        "ActorPresentationRequirements": "AWRSE_PRESENTATION_REQUIREMENTS",
        "PublicationProjection": "PUBLICATION_DERIVED_PROJECTION",
    }
    for type_name, profile_ref in expected.items():
        assert registry[type_name]["authority_profile_ref"] == profile_ref

    # B07 information/promise/asset/spatial lifecycles remain split.
    assert registry["InformationPacket"]["authority_profile_ref"] == "INFORMATION_PROVENANCE_LIFECYCLE"
    assert registry["NarrativePromise"]["authority_profile_ref"] == "EVIDENCE_DERIVED_PROMISE_LIFECYCLE"
    assert registry["CameraAnchor"]["authority_profile_ref"] == "SPATIAL_VIEW_DEFINITION_REGISTRY"
    assert registry["View"]["authority_profile_ref"] == "SPATIAL_VIEW_DEFINITION_REGISTRY"
    assert registry["MediaAsset"]["authority_profile_ref"] == "ASSET_LOGICAL_IDENTITY_REGISTRY"
    assert registry["MediaVersion"]["authority_profile_ref"] == "ASSET_IMMUTABLE_VERSION_REGISTRY"
    assert registry["Locator"]["authority_profile_ref"] == "ASSET_LOCATOR_RESOLUTION"
