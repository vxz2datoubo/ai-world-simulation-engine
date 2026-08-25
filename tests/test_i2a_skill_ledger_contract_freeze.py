import copy
import json
import math
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN_PATH = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"


def _load(path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def _profile_cases(suite):
    fighter = suite["scenarios"]["FIGHTER_VS_SCHOLAR"]["machine_spec"]
    cases = list(fighter["profile_provenance_replay_cases"])
    cases.extend(suite["profile_provenance_fixture_extensions"]["FIGHTER_VS_SCHOLAR"])
    return {case["case_id"]: case for case in cases}


def _skill_cases(suite):
    extension = suite["skill_ledger_fixture_extensions"]["FIGHTER_VS_SCHOLAR"]
    assert extension["evaluation_scope"] == "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
    return {case["case_id"]: case for case in extension["cases"]}


def _contract_gate_receipt(contract, suite, case):
    spec = contract["versioning_and_migration"]["skill_ledger_admission"]
    profile_cases = _profile_cases(suite)

    if case.get("schema_version") != spec["schema_version"]:
        return {"admission": "REJECT_FAIL_CLOSED_UNSUPPORTED_SKILL_LEDGER_SCHEMA"}

    actor_id = case.get("actor_id")
    if not isinstance(actor_id, str) or not actor_id.strip():
        return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}

    paired_profile_id = case.get("paired_profile_case_id")
    if paired_profile_id:
        paired_profile = profile_cases[paired_profile_id]
        if actor_id != paired_profile.get("actor_id"):
            return {"admission": "REJECT_FAIL_CLOSED_ACTOR_BINDING_MISMATCH"}

    cursor = case.get("source_event_cursor")
    authorized_cursor = case.get("authorized_source_event_cursor")
    if not isinstance(cursor, str) or not cursor.strip() or cursor != authorized_cursor:
        return {"admission": "REJECT_FAIL_CLOSED_MISSING_SKILL_PROVENANCE"}

    entries = case.get("skill_entries")
    if not isinstance(entries, list) or not entries:
        return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}

    authorized_refs = set(case.get("authorized_source_event_refs", []))
    projection = {}
    for entry in entries:
        if not isinstance(entry, dict):
            return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}
        if set(spec["entry_required_fields"]) - set(entry):
            return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}

        skill_id = entry.get("skill_id")
        if not isinstance(skill_id, str) or not skill_id.strip():
            return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}
        if skill_id in projection:
            return {"admission": "REJECT_FAIL_CLOSED_DUPLICATE_SKILL_ID"}

        value = entry.get("value")
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}
        if isinstance(value, float) and not math.isfinite(value):
            return {"admission": "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"}

        refs = entry.get("source_event_refs")
        if (
            not isinstance(refs, list)
            or not refs
            or any(not isinstance(ref, str) or not ref.strip() for ref in refs)
            or not set(refs) <= authorized_refs
        ):
            return {"admission": "REJECT_FAIL_CLOSED_MISSING_SKILL_PROVENANCE"}

        projection[skill_id] = value

    return {
        "admission": "ACCEPT_V1_1_SKILL_LEDGER",
        "validated_skill_ledger_values": projection,
    }


def test_contract_and_golden_versions_are_bound_for_skill_ledger_freeze():
    contract = _load(CONTRACT_PATH)
    suite = _load(GOLDEN_PATH)

    assert contract["contract_version"] == "1.9.0-candidate"
    assert suite["required_contract_version"] == contract["contract_version"]
    assert suite["suite_version"] == "1.7.0-candidate"


def test_skill_ledger_contract_freezes_minimum_admission_without_tuning():
    contract = _load(CONTRACT_PATH)
    ledger = contract["type_registry"]["SkillLedger"]
    spec = contract["versioning_and_migration"]["skill_ledger_admission"]

    assert ledger["version"] == spec["schema_version"] == "1.1.0-candidate"
    assert ledger["implementation_state"] == "CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED"
    assert set(ledger["fields"]) == {"actor_id", "skill_entries", "source_event_cursor", "schema_version"}
    assert set(ledger["entry_contract"]["required_fields"]) == {"skill_id", "value", "source_event_refs"}
    assert spec["duplicate_skill_identity_policy"] == "REJECT_FAIL_CLOSED_NO_LAST_WRITE_WINS_NO_AGGREGATION"
    assert spec["unknown_or_unsupported_schema_policy"] == "REJECT_FAIL_CLOSED"
    assert spec["empty_or_malformed_policy"] == "REJECT_FAIL_CLOSED"
    assert "MUST_EQUAL_profile.actor_id_EXACTLY" in spec["actor_binding_rule"]
    assert "EACH_ENTRY_REQUIRES_SOURCE_EVENT_REFS" in spec["provenance_rule"]

    deferred = set(spec["deferred_policy_tracks"])
    assert {
        "SKILL_SCALE_AND_RANGE",
        "XP_PRACTICE_AND_TRAINING_FORMULAS",
        "PROGRESSION_THRESHOLDS",
        "SKILL_DECAY",
        "TRAINING_COEFFICIENTS",
        "ACTION_DEMAND_SKILL_WEIGHTING",
        "ABILITIES_AND_TECHNIQUES",
        "GENRE_SPECIFIC_SKILL_NAMESPACES",
        "PLAYER_FACING_BALANCE",
    } <= deferred


def test_skill_ledger_golden_fixtures_execute_required_admission_boundaries():
    contract = _load(CONTRACT_PATH)
    suite = _load(GOLDEN_PATH)
    cases = _skill_cases(suite)

    assert set(cases) == {
        "FS-S1-VALID-ACTOR-BOUND-LEDGER",
        "FS-S2-MISSING-PROVENANCE",
        "FS-S3-WRONG-ACTOR-BINDING",
        "FS-S4-DUPLICATE-SKILL-ID",
        "FS-S5-UNSUPPORTED-SCHEMA",
        "FS-S6-DETERMINISTIC-REPLAY-PROJECTION",
        "FS-S7-UNRELATED-SKILL-PRESERVED-ZERO-EFFECT",
        "FS-S8-SKILL-TRUTH-SEPARATE-FROM-PROFILE",
        "FS-S9-EMPTY-LEDGER",
        "FS-S10-MALFORMED-ENTRY-PROVENANCE",
    }

    for case in cases.values():
        actual = _contract_gate_receipt(contract, suite, case)
        assert actual["admission"] == case["expected_receipt"]["admission"]
        if actual["admission"] == "ACCEPT_V1_1_SKILL_LEDGER":
            assert actual["validated_skill_ledger_values"] == case["expected_receipt"]["validated_skill_ledger_values"]


def test_projection_is_deterministic_one_to_one_and_unrelated_skill_is_preserved():
    contract = _load(CONTRACT_PATH)
    suite = _load(GOLDEN_PATH)
    cases = _skill_cases(suite)
    spec = contract["versioning_and_migration"]["skill_ledger_admission"]["validated_projection"]

    replay_case = cases["FS-S6-DETERMINISTIC-REPLAY-PROJECTION"]
    first = _contract_gate_receipt(contract, suite, copy.deepcopy(replay_case))
    second = _contract_gate_receipt(contract, suite, copy.deepcopy(replay_case))
    assert first == second
    assert replay_case["expected_receipt"]["deterministic_equality"] is True

    unrelated = cases["FS-S7-UNRELATED-SKILL-PRESERVED-ZERO-EFFECT"]
    receipt = _contract_gate_receipt(contract, suite, unrelated)
    assert receipt["validated_skill_ledger_values"] == {"climb": 3, "poetry": 1000}
    selected = {
        key: receipt["validated_skill_ledger_values"][key]
        for key in unrelated["action_demand_required_skills"]
    }
    assert selected == unrelated["expected_receipt"]["resolver_selected_skill_values"] == {"climb": 3}
    assert unrelated["expected_receipt"]["unrelated_skill_effect"] == "ZERO_WHEN_UNREFERENCED"
    assert spec["no_skill_dropping"] is True
    assert spec["no_weighting"] is True
    assert spec["no_aggregation"] is True
    assert spec["no_authority_gain"] is True


def test_skill_value_shape_is_finite_numeric_without_freezing_scale_or_progression():
    contract = _load(CONTRACT_PATH)
    suite = _load(GOLDEN_PATH)
    base = _skill_cases(suite)["FS-S1-VALID-ACTOR-BOUND-LEDGER"]

    for invalid in (True, "3", None, math.nan, math.inf, -math.inf):
        case = copy.deepcopy(base)
        case["skill_entries"][0]["value"] = invalid
        assert _contract_gate_receipt(contract, suite, case)["admission"] == "REJECT_FAIL_CLOSED_EMPTY_OR_MALFORMED_SKILL_LEDGER"

    entry_semantics = contract["type_registry"]["SkillLedger"]["entry_contract"]["field_semantics"]["value"]
    assert "FINITE_NON_BOOLEAN_INT_OR_FLOAT" in entry_semantics
    assert "SCALE_RANGE_PROGRESSION_AND_BALANCE_MEANING_REMAIN" in entry_semantics
