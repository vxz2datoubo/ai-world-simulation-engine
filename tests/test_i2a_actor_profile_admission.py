import json
from pathlib import Path

import pytest

from runtime.awrse.actor_profile_admission import admit_actor_base_profile


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"


def _walk_cases(value):
    if isinstance(value, dict):
        if "case_id" in value:
            yield value
        for child in value.values():
            yield from _walk_cases(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_cases(child)


def _golden_case(case_id):
    data = json.loads(GOLDEN.read_text(encoding="utf-8"))
    matches = [case for case in _walk_cases(data) if case.get("case_id") == case_id]
    assert len(matches) == 1
    return matches[0]


def _profile_from_case(case):
    return {
        "actor_id": case.get("actor_id"),
        "profile_version": case.get("profile_version"),
        "profile_schema_ref": case.get("profile_schema_ref"),
        "ruleset_family_ref": case.get("ruleset_family_ref"),
        "base_attribute_map": case.get("base_attribute_map"),
        "source_event_refs": case.get("source_event_refs"),
    }


def _valid_profile():
    return _profile_from_case(_golden_case("FS-P1-MATCHING-V1_1"))


def test_fs_p1_matching_v1_1_profile_is_admitted_with_canonical_provenance():
    profile = _valid_profile()
    receipt = admit_actor_base_profile(profile)
    assert receipt.actor_id == profile["actor_id"]
    assert receipt.profile_version == "1.1.0-candidate"
    assert receipt.profile_schema_ref == profile["profile_schema_ref"]
    assert receipt.ruleset_family_ref == profile["ruleset_family_ref"]
    assert receipt.admitted_base_attribute_map == profile["base_attribute_map"]
    assert receipt.source_event_refs == tuple(profile["source_event_refs"])
    assert receipt.canonical_contract_id == "AWRSE-AF001-LIVING-STORY-CONTRACTS"
    assert receipt.canonical_contract_version


def test_fs_p2_missing_profile_schema_ruleset_provenance_fails_closed():
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SCHEMA_REF_REQUIRED"):
        admit_actor_base_profile(_profile_from_case(_golden_case("FS-P2-MISSING-PROVENANCE")))


def test_fs_p3_mismatched_profile_schema_ruleset_fails_closed():
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SCHEMA_RULESET_INCOMPATIBLE"):
        admit_actor_base_profile(_profile_from_case(_golden_case("FS-P3-MISMATCHED-PROVENANCE")))


@pytest.mark.parametrize("actor_id", [None, "", "   "])
def test_missing_or_blank_actor_id_fails_closed(actor_id):
    profile = _valid_profile()
    profile["actor_id"] = actor_id
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_ACTOR_ID_REQUIRED"):
        admit_actor_base_profile(profile)


def test_wrong_profile_version_fails_closed():
    profile = _valid_profile()
    profile["profile_version"] = "2.0.0-candidate"
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_VERSION_UNSUPPORTED"):
        admit_actor_base_profile(profile)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_or_blank_profile_schema_ref_fails_closed(value):
    profile = _valid_profile()
    profile["profile_schema_ref"] = value
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SCHEMA_REF_REQUIRED"):
        admit_actor_base_profile(profile)


@pytest.mark.parametrize("value", [None, "", "   "])
def test_missing_or_blank_ruleset_family_ref_fails_closed(value):
    profile = _valid_profile()
    profile["ruleset_family_ref"] = value
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_RULESET_FAMILY_REF_REQUIRED"):
        admit_actor_base_profile(profile)


@pytest.mark.parametrize("value", [{}, [], "strength", None])
def test_empty_or_nonmapping_base_attribute_map_fails_closed(value):
    profile = _valid_profile()
    profile["base_attribute_map"] = value
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_BASE_ATTRIBUTE_MAP_INVALID"):
        admit_actor_base_profile(profile)


@pytest.mark.parametrize("value", [[], (), "E1", {"E1"}, [""], [1], None])
def test_empty_or_malformed_source_event_refs_fail_closed(value):
    profile = _valid_profile()
    profile["source_event_refs"] = value
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SOURCE_EVENT_REFS_INVALID"):
        admit_actor_base_profile(profile)


def test_duplicate_source_event_refs_fail_closed():
    profile = _valid_profile()
    profile["source_event_refs"] = ["E1", "E1"]
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_DUPLICATE_SOURCE_EVENT_REF"):
        admit_actor_base_profile(profile)


def test_admission_copies_caller_owned_mapping_and_sequence():
    attributes = {"strength": {"basis": ["CANONICAL_BASE"]}}
    refs = ["E_PROFILE_FIGHTER_CREATED"]
    profile = _valid_profile()
    profile["base_attribute_map"] = attributes
    profile["source_event_refs"] = refs

    receipt = admit_actor_base_profile(profile)
    attributes["strength"]["basis"].append("MUTATED")
    refs.append("E_AFTER_ADMISSION")

    assert receipt.admitted_base_attribute_map == {"strength": {"basis": ["CANONICAL_BASE"]}}
    assert receipt.source_event_refs == ("E_PROFILE_FIGHTER_CREATED",)


def test_unknown_profile_schema_fails_closed():
    profile = _valid_profile()
    profile["profile_schema_ref"] = "PROFILE-SCHEMA-UNKNOWN@1"
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SCHEMA_RULESET_INCOMPATIBLE"):
        admit_actor_base_profile(profile)


def test_unknown_ruleset_family_fails_closed():
    profile = _valid_profile()
    profile["ruleset_family_ref"] = "RULESET-FAMILY-UNKNOWN@1"
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_SCHEMA_RULESET_INCOMPATIBLE"):
        admit_actor_base_profile(profile)


def test_legacy_profile_is_not_silently_transformed():
    profile = _valid_profile()
    profile["profile_version"] = "1.0.0-candidate"
    profile.pop("profile_schema_ref")
    profile.pop("ruleset_family_ref")
    with pytest.raises(ValueError, match="I2A_ACTOR_PROFILE_LEGACY_TRANSFORMATION_NOT_AUTHORIZED"):
        admit_actor_base_profile(profile)


def test_identical_admitted_inputs_produce_equal_receipts():
    profile = _valid_profile()
    first = admit_actor_base_profile(profile)
    second = admit_actor_base_profile(profile)
    assert first == second
