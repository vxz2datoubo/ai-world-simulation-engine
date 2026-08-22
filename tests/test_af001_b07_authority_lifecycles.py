import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"


def load_contract():
    with CONTRACT_PATH.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def profile_for(contract, type_name):
    ref = contract["type_registry"][type_name]["authority_profile_ref"]
    return ref, contract["authority_semantics"]["profiles"][ref]


def test_b07_information_packet_uses_provenance_lifecycle_not_authored_narrative():
    contract = load_contract()
    type_spec = contract["type_registry"]["InformationPacket"]
    profile_ref, profile = profile_for(contract, "InformationPacket")

    assert profile_ref == "INFORMATION_PROVENANCE_LIFECYCLE"
    assert profile_ref != "NARRATIVE_DESIGN_NON_CANONICAL"
    assert "PROVENANCE_BEARING_SOURCE_EVIDENCE" in profile["canonical_data_authority"]
    assert "WORLD_RULES_AUTHORITY" in profile["canonical_data_authority"]
    assert profile["producer_or_assembler"] == ["AWRSE_INFORMATION_PACKET_ASSEMBLER"]
    assert "AWRSE_NARRATIVE_DESIGN_LOADER" not in profile["producer_or_assembler"]
    assert "NARRATIVE_DESIGN_NON_CANONICAL" not in profile["producer_or_assembler"]
    assert set(type_spec["source_authority_requirements"]) == {
        "source_fact_or_event_refs", "source_refs", "verification_state", "confidence"
    }
    assert type_spec["lifecycle"] == (
        "WORLD_EVENT_TO_SOURCE_WITNESS_TO_INFORMATION_PACKET_TO_CARRIER_CHANNEL_"
        "TO_PERCEPTION_COMMUNICATION_TO_PLAYER_NPC_KNOWLEDGE"
    )
    assert "CANNOT_INVENT_SOURCE_FACTS" in profile["mutation_constraint"]
    assert "RECIPIENT_KNOWLEDGE_EVIDENCE" in profile["mutation_constraint"]


def test_b07_narrative_promise_is_evidence_derived_not_authored_truth():
    contract = load_contract()
    type_spec = contract["type_registry"]["NarrativePromise"]
    profile_ref, profile = profile_for(contract, "NarrativePromise")

    assert profile_ref == "EVIDENCE_DERIVED_PROMISE_LIFECYCLE"
    assert profile_ref != "NARRATIVE_DESIGN_NON_CANONICAL"
    assert type_spec["implementation_state"] == "INTERFACE_ONLY_DERIVED_LIFECYCLE"
    assert type_spec["authored_creation_allowed"] is False
    assert type_spec["lifecycle_source_requirements"] == ["source_refs"]
    assert "EXPLICIT_SPEECH_OR_ACTION_SOURCE_EVENT" in type_spec["lifecycle"]
    assert "PROVENANCE_BEARING_SOURCE_EVIDENCE" in profile["canonical_data_authority"]
    assert profile["producer_or_assembler"] == ["AWRSE_PROMISE_LIFECYCLE_PROJECTOR"]
    assert "AWRSE_NARRATIVE_DESIGN_LOADER" not in profile["producer_or_assembler"]
    assert "AUTHORED_NARRATIVE_CANNOT_INVENT_A_PROMISE" in profile["mutation_constraint"]
    assert "SOURCE_HISTORY" in profile["mutation_constraint"]


def test_b07_authored_narrative_types_stay_noncanonical_but_evidence_types_do_not():
    contract = load_contract()
    registry = contract["type_registry"]

    authored = {
        "StoryDNA", "StoryBible", "GenreEngine", "CharacterDramaticCore",
        "HardCausalAnchor", "SoftDramaticAttractor", "Storylet", "EventDeckEntry",
    }
    for type_name in authored:
        assert registry[type_name]["authority_profile_ref"] == "NARRATIVE_DESIGN_NON_CANONICAL"

    assert registry["InformationPacket"]["authority_profile_ref"] != "NARRATIVE_DESIGN_NON_CANONICAL"
    assert registry["NarrativePromise"]["authority_profile_ref"] != "NARRATIVE_DESIGN_NON_CANONICAL"


def test_b07_asset_identity_version_locator_have_distinct_registry_profiles():
    contract = load_contract()
    registry = contract["type_registry"]

    expected = {
        "MediaAsset": "ASSET_LOGICAL_IDENTITY_REGISTRY",
        "MediaVersion": "ASSET_IMMUTABLE_VERSION_REGISTRY",
        "Locator": "ASSET_LOCATOR_RESOLUTION",
    }
    actual = {name: registry[name]["authority_profile_ref"] for name in expected}
    assert actual == expected
    assert len(set(actual.values())) == 3

    for type_name, profile_ref in expected.items():
        assert profile_ref != "PRESENTATION_CANONICAL_STATE"
        profile = contract["authority_semantics"]["profiles"][profile_ref]
        assert "AWRSE_WORLD_STATE_PROJECTOR" not in profile["producer_or_assembler"], type_name
        assert profile["staging_authority"] == ["NONE"]

    assert registry["MediaAsset"]["identity_semantics"] == "STABLE_LOGICAL_ASSET_IDENTITY"
    assert registry["MediaVersion"]["identity_semantics"] == "IMMUTABLE_MEDIA_REVISION"
    assert registry["Locator"]["identity_semantics"] == "REPLACEABLE_RETRIEVAL_OR_STORAGE_LOCATION"


def test_b07_media_version_promotion_and_locator_migration_authority_are_explicit():
    contract = load_contract()
    registry = contract["type_registry"]
    profiles = contract["authority_semantics"]["profiles"]

    version = registry["MediaVersion"]
    locator = registry["Locator"]
    version_profile = profiles[version["authority_profile_ref"]]
    locator_profile = profiles[locator["authority_profile_ref"]]

    assert version["version_creation_authority"] == "ASSET_REGISTRY_AUTHORITY"
    assert version["verification_promotion_authority"] == "ASSET_VERIFICATION_PROMOTION_AUTHORITY"
    assert "ASSET_VERIFICATION_PROMOTION_AUTHORITY" in version_profile["canonical_data_authority"]
    assert "MEDIA_VERSION_CONTENT_HASH" in version_profile["mutation_constraint"]
    assert "WORLD_STATE_PROJECTOR_CANNOT_CREATE_OR_PROMOTE_MEDIA_VERSIONS" in version_profile["mutation_constraint"]

    assert locator["migration_authority"] == "ASSET_LOCATOR_REGISTRY_AUTHORITY"
    assert locator["migration_identity_effect"] == "DOES_NOT_CHANGE_MEDIA_ASSET_OR_MEDIA_VERSION_IDENTITY"
    assert locator_profile["canonical_data_authority"] == ["ASSET_LOCATOR_REGISTRY_AUTHORITY"]
    assert "LOCATOR_MIGRATION" in locator_profile["mutation_constraint"]
    assert "CANNOT_CHANGE_MEDIA_ASSET_OR_MEDIA_VERSION_IDENTITY" in locator_profile["mutation_constraint"]


def test_b07_spatial_view_definitions_are_not_dynamic_presentation_or_director_staging():
    contract = load_contract()
    registry = contract["type_registry"]
    profiles = contract["authority_semantics"]["profiles"]

    for type_name in ("CameraAnchor", "View"):
        type_spec = registry[type_name]
        assert type_spec["authority_profile_ref"] == "SPATIAL_VIEW_DEFINITION_REGISTRY"
        profile = profiles[type_spec["authority_profile_ref"]]
        assert profile["canonical_data_authority"] == ["WORLD_RULES_AUTHORITY"]
        assert profile["producer_or_assembler"] == ["AWRSE_SPATIAL_VIEW_REGISTRY"]
        assert profile["staging_authority"] == ["NONE"]
        assert "AI_DIRECTOR" not in profile["canonical_data_authority"]
        assert "RENDERER_PUBLICATION" not in profile["canonical_data_authority"]

    assert registry["View"]["definition_semantics"] == "STABLE_SPATIAL_VIEW_DEFINITION_NOT_RENDERER_CAMERA_CHOICE"


def test_b07_dynamic_presentation_and_b05_high_risk_authority_mappings_remain_intact():
    contract = load_contract()
    registry = contract["type_registry"]

    for type_name in (
        "ActorPresentationState", "OutfitState", "DressingState", "SurfaceState",
        "ActorAppearanceSnapshot",
    ):
        assert registry[type_name]["authority_profile_ref"] == "PRESENTATION_CANONICAL_STATE"

    expected_b05 = {
        "CharacterCore": "PLAYER_EXPLICIT_CHARACTER_CORE",
        "EnactedPersonaHypothesis": "EVIDENCE_DERIVED_PERSONA_HYPOTHESIS",
        "PlayerAutoExpressionPolicy": "PLAYER_EXPLICIT_AUTO_EXPRESSION_POLICY",
        "NarrativeOpportunityBroker": "NARRATIVE_OPPORTUNITY_NON_CANONICAL",
        "PXRankingReceipt": "PX_RANKING_NON_CANONICAL",
        "DIRECTOR-BEAT-PACKET": "AWRSE_DIRECTOR_HANDOFF",
        "ActorPresentationRequirements": "AWRSE_PRESENTATION_REQUIREMENTS",
        "PublicationProjection": "PUBLICATION_DERIVED_PROJECTION",
    }
    for type_name, profile_ref in expected_b05.items():
        assert registry[type_name]["authority_profile_ref"] == profile_ref


def test_b07_all_authority_profile_actors_resolve_and_lifecycle_invariants_are_frozen():
    contract = load_contract()
    actors = set(contract["authority_semantics"]["authority_actor_registry"])
    required_fields = set(contract["authority_semantics"]["required_profile_fields"])

    for profile_name, profile in contract["authority_semantics"]["profiles"].items():
        assert required_fields <= set(profile), profile_name
        assert profile["contract_schema_steward"] in actors, profile_name
        for field in (
            "canonical_data_authority", "producer_or_assembler",
            "downstream_consumer", "staging_authority",
        ):
            assert profile[field], f"{profile_name}.{field}"
            unknown = set(profile[field]) - actors
            assert not unknown, f"{profile_name}.{field}: {sorted(unknown)}"

    af_d = set(contract["freeze_domains"]["AF-D"]["invariants"])
    af_f = set(contract["freeze_domains"]["AF-F"]["invariants"])
    assert "DYNAMIC_PRESENTATION_STATE_NE_ASSET_REGISTRY_TRUTH" in af_d
    assert "LOCATOR_MIGRATION_NE_ASSET_OR_VERSION_IDENTITY_CHANGE" in af_d
    assert "AUTHORED_NARRATIVE_NE_INFORMATION_PROVENANCE_LIFECYCLE" in af_f
    assert "AUTHORED_NARRATIVE_NE_PROMISE_HISTORY" in af_f
    assert "INFORMATION_PACKET_REQUIRES_SOURCE_AND_PROVENANCE_EVIDENCE" in af_f
    assert "NARRATIVE_PROMISE_REQUIRES_SOURCE_EVENT_EVIDENCE" in af_f
