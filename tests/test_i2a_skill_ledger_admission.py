import copy
from dataclasses import replace
import json
from pathlib import Path

import pytest

from runtime.awrse.actor_profile_admission import admit_actor_base_profile
from runtime.awrse.capability_resolution import resolve_capability
import runtime.awrse.skill_ledger_admission as skill_module
from runtime.awrse.skill_ledger_admission import admit_skill_ledger


ROOT = Path(__file__).resolve().parents[1]
GOLDEN = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
CONTRACT = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"


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


def _admitted_profile():
    return admit_actor_base_profile(_profile_from_case(_golden_case("FS-P1-MATCHING-V1_1")))


def _ledger_from_case(case):
    return {
        "actor_id": case.get("actor_id"),
        "skill_entries": copy.deepcopy(case.get("skill_entries")),
        "source_event_cursor": case.get("source_event_cursor"),
        "schema_version": case.get("schema_version"),
    }


def _valid_ledger():
    return _ledger_from_case(_golden_case("FS-S1-VALID-ACTOR-BOUND-LEDGER"))


def test_fs_s1_valid_actor_bound_ledger_admits_from_canonical_contract():
    profile = _admitted_profile()
    ledger = _valid_ledger()
    receipt = admit_skill_ledger(ledger, admitted_actor_profile=profile)

    assert receipt.actor_id == ledger["actor_id"] == profile.actor_id
    assert receipt.schema_version == "1.1.0-candidate"
    assert tuple(entry.skill_id for entry in receipt.admitted_skill_entries) == ("climb", "poetry")
    assert tuple(entry.source_event_refs for entry in receipt.admitted_skill_entries) == (
        ("E_SKILL_CLIMB_TRAINED",),
        ("E_SKILL_POETRY_TRAINED",),
    )
    assert dict(receipt.validated_skill_ledger_values) == {"climb": 3, "poetry": 1000}
    assert receipt.source_event_cursor == ledger["source_event_cursor"]
    assert receipt.canonical_contract_id == "AWRSE-AF001-LIVING-STORY-CONTRACTS"
    assert receipt.canonical_contract_version == profile.canonical_contract_version


def test_fs_s2_missing_ledger_cursor_provenance_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S2-MISSING-PROVENANCE"))
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_SOURCE_EVENT_CURSOR_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_fs_s3_wrong_actor_binding_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S3-WRONG-ACTOR-BINDING"))
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_ACTOR_BINDING_MISMATCH"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_fs_s4_duplicate_skill_identity_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S4-DUPLICATE-SKILL-ID"))
    with pytest.raises(ValueError, match="I2A_DUPLICATE_SKILL_ID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_fs_s5_unsupported_schema_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S5-UNSUPPORTED-SCHEMA"))
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_SCHEMA_VERSION_UNSUPPORTED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_fs_s6_identical_input_yields_equal_receipt_and_projection():
    ledger = _ledger_from_case(_golden_case("FS-S6-DETERMINISTIC-REPLAY-PROJECTION"))
    profile = _admitted_profile()
    first = admit_skill_ledger(ledger, admitted_actor_profile=profile)
    second = admit_skill_ledger(copy.deepcopy(ledger), admitted_actor_profile=profile)
    assert first == second
    assert dict(first.validated_skill_ledger_values) == dict(second.validated_skill_ledger_values)


def test_fs_s7_unrelated_skill_remains_projected_but_has_zero_effect_when_unreferenced():
    case = _golden_case("FS-S7-UNRELATED-SKILL-PRESERVED-ZERO-EFFECT")
    profile = _admitted_profile()
    receipt = admit_skill_ledger(_ledger_from_case(case), admitted_actor_profile=profile)
    assert "poetry" in receipt.validated_skill_ledger_values

    demand = {
        "required_attributes": [],
        "required_skills": case["action_demand_required_skills"],
        "difficulty_or_resistance": 0,
    }
    provenance = {
        "profile_schema_ref": profile.profile_schema_ref,
        "ruleset_family_ref": profile.ruleset_family_ref,
        "replay_input_ref": receipt.source_event_cursor,
    }
    baseline = resolve_capability(
        capability_envelope={
            "validated_actor_base_attributes": profile.admitted_base_attribute_map,
            "validated_skill_ledger_values": receipt.validated_skill_ledger_values,
        },
        action_demand_profile=demand,
        provenance=provenance,
    )

    variant_ledger = _ledger_from_case(case)
    variant_ledger["skill_entries"][1]["value"] = -(10**100)
    variant = admit_skill_ledger(variant_ledger, admitted_actor_profile=profile)
    changed_unrelated = resolve_capability(
        capability_envelope={
            "validated_actor_base_attributes": profile.admitted_base_attribute_map,
            "validated_skill_ledger_values": variant.validated_skill_ledger_values,
        },
        action_demand_profile=demand,
        provenance={**provenance, "replay_input_ref": variant.source_event_cursor},
    )
    assert baseline.feasible is True
    assert baseline.effective_capability == changed_unrelated.effective_capability == 3
    assert baseline.margin == changed_unrelated.margin == 3


def test_fs_s8_skill_admission_cannot_mutate_actor_base_profile_truth():
    profile = _admitted_profile()
    before_attributes = copy.deepcopy(dict(profile.admitted_base_attribute_map))
    before_refs = tuple(profile.source_event_refs)
    admit_skill_ledger(
        _ledger_from_case(_golden_case("FS-S8-SKILL-TRUTH-SEPARATE-FROM-PROFILE")),
        admitted_actor_profile=profile,
    )
    assert dict(profile.admitted_base_attribute_map) == before_attributes
    assert profile.source_event_refs == before_refs
    assert "climb" not in profile.admitted_base_attribute_map


def test_fs_s9_empty_ledger_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S9-EMPTY-LEDGER"))
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_ENTRIES_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_fs_s10_malformed_entry_provenance_fails_closed():
    ledger = _ledger_from_case(_golden_case("FS-S10-MALFORMED-ENTRY-PROVENANCE"))
    with pytest.raises(ValueError, match="I2A_SKILL_ENTRY_SOURCE_EVENT_REFS_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_caller_mutation_after_admission_cannot_change_receipt_or_projection():
    profile = _admitted_profile()
    ledger = _valid_ledger()
    receipt = admit_skill_ledger(ledger, admitted_actor_profile=profile)

    ledger["actor_id"] = "MUTATED"
    ledger["source_event_cursor"] = "MUTATED"
    ledger["skill_entries"][0]["value"] = 999
    ledger["skill_entries"][0]["source_event_refs"].append("E_MUTATED")
    ledger["skill_entries"].append(
        {"skill_id": "new", "value": 100, "source_event_refs": ["E_NEW"]}
    )

    assert receipt.actor_id == "ACTOR-FIGHTER-001"
    assert receipt.source_event_cursor == "CURSOR-SKILL-FIGHTER-001"
    assert receipt.admitted_skill_entries[0].value == 3
    assert receipt.admitted_skill_entries[0].source_event_refs == ("E_SKILL_CLIMB_TRAINED",)
    assert dict(receipt.validated_skill_ledger_values) == {"climb": 3, "poetry": 1000}
    with pytest.raises(TypeError):
        receipt.validated_skill_ledger_values["climb"] = 999


@pytest.mark.parametrize("value", [True, False, "3", None, float("nan"), float("inf"), float("-inf")])
def test_invalid_skill_values_fail_closed(value):
    ledger = _valid_ledger()
    ledger["skill_entries"][0]["value"] = value
    with pytest.raises(ValueError, match="I2A_SKILL_VALUE_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


def test_very_large_positive_and_negative_python_ints_admit_without_overflow():
    ledger = _valid_ledger()
    huge = 10**1000
    ledger["skill_entries"] = [
        {"skill_id": "huge-positive", "value": huge, "source_event_refs": ["E_POS"]},
        {"skill_id": "huge-negative", "value": -huge, "source_event_refs": ["E_NEG"]},
    ]
    receipt = admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())
    assert receipt.validated_skill_ledger_values["huge-positive"] == huge
    assert receipt.validated_skill_ledger_values["huge-negative"] == -huge


def test_raw_caller_map_cannot_bypass_admitted_actor_profile_boundary():
    with pytest.raises(ValueError, match="I2A_ADMITTED_ACTOR_PROFILE_REQUIRED"):
        admit_skill_ledger(
            _valid_ledger(),
            admitted_actor_profile={"actor_id": "ACTOR-FIGHTER-001"},
        )


def test_stale_or_fabricated_profile_contract_binding_fails_closed():
    profile = replace(_admitted_profile(), canonical_contract_version="0.0.0-invalid")
    with pytest.raises(ValueError, match="I2A_ADMITTED_ACTOR_PROFILE_CONTRACT_MISMATCH"):
        admit_skill_ledger(_valid_ledger(), admitted_actor_profile=profile)


def test_missing_canonical_contract_fails_closed(tmp_path, monkeypatch):
    monkeypatch.setattr(skill_module, "_CANONICAL_CONTRACT_PATH", tmp_path / "missing.json")
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_CANONICAL_CONTRACT_UNAVAILABLE"):
        admit_skill_ledger(_valid_ledger(), admitted_actor_profile=_admitted_profile())


def test_malformed_canonical_contract_json_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "contract.json"
    path.write_text("{not-json", encoding="utf-8")
    monkeypatch.setattr(skill_module, "_CANONICAL_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_CANONICAL_CONTRACT_UNAVAILABLE"):
        admit_skill_ledger(_valid_ledger(), admitted_actor_profile=_admitted_profile())


def test_malformed_canonical_contract_shape_fails_closed(tmp_path, monkeypatch):
    path = tmp_path / "contract.json"
    path.write_text("{}", encoding="utf-8")
    monkeypatch.setattr(skill_module, "_CANONICAL_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID"):
        admit_skill_ledger(_valid_ledger(), admitted_actor_profile=_admitted_profile())


def test_canonical_skill_schema_version_mismatch_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    contract["type_registry"]["SkillLedger"]["version"] = "9.9.0-invalid"
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(skill_module, "_CANONICAL_CONTRACT_PATH", path)
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_CANONICAL_CONTRACT_INVALID"):
        admit_skill_ledger(_valid_ledger(), admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("ledger", [None, [], "ledger", 7])
def test_nonmapping_ledger_input_fails_closed(ledger):
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("actor_id", [None, "", "   "])
def test_missing_or_blank_ledger_actor_id_fails_closed(actor_id):
    ledger = _valid_ledger()
    ledger["actor_id"] = actor_id
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_ACTOR_ID_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("schema_version", [None, "", "   "])
def test_missing_or_blank_schema_version_fails_closed(schema_version):
    ledger = _valid_ledger()
    ledger["schema_version"] = schema_version
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_SCHEMA_VERSION_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("cursor", [None, "", "   "])
def test_missing_or_blank_source_event_cursor_fails_closed(cursor):
    ledger = _valid_ledger()
    ledger["source_event_cursor"] = cursor
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_SOURCE_EVENT_CURSOR_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("entries", [None, {}, (), "climb", []])
def test_nonlist_or_empty_skill_entries_fail_closed(entries):
    ledger = _valid_ledger()
    ledger["skill_entries"] = entries
    with pytest.raises(ValueError, match="I2A_SKILL_LEDGER_ENTRIES_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("entry", [None, [], "climb", 3])
def test_nonmapping_skill_entry_fails_closed(entry):
    ledger = _valid_ledger()
    ledger["skill_entries"] = [entry]
    with pytest.raises(ValueError, match="I2A_SKILL_ENTRY_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("skill_id", [None, "", "   "])
def test_missing_or_blank_skill_id_fails_closed(skill_id):
    ledger = _valid_ledger()
    ledger["skill_entries"][0]["skill_id"] = skill_id
    with pytest.raises(ValueError, match="I2A_SKILL_ID_REQUIRED"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())


@pytest.mark.parametrize("refs", [None, (), {}, "E1", [], [""], ["   "], [1]])
def test_nonlist_empty_or_malformed_entry_source_refs_fail_closed(refs):
    ledger = _valid_ledger()
    ledger["skill_entries"][0]["source_event_refs"] = refs
    with pytest.raises(ValueError, match="I2A_SKILL_ENTRY_SOURCE_EVENT_REFS_INVALID"):
        admit_skill_ledger(ledger, admitted_actor_profile=_admitted_profile())
