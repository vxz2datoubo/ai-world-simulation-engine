import json
from pathlib import Path

import pytest

from awrse import (
    export_i2a_replay_package,
    import_i2a_replay_package,
    policy_from_af_c_contract,
    rehydrate_i2a_replay_package,
    resolve_i2a_feasibility,
    validate_actor_base_profile,
)


ROOT = Path(__file__).resolve().parents[1]


def policy():
    return policy_from_af_c_contract(json.loads((ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json").read_text(encoding="utf-8")))


def profile(**overrides):
    value = {
        "actor_id": "ACTOR-FIGHTER-001",
        "profile_version": "1.1.0-candidate",
        "profile_schema_ref": "PROFILE-SCHEMA-FAMILY-A@1",
        "ruleset_family_ref": "RULESET-FAMILY-A@1",
        "base_attribute_map": {"grip": "DECLARED_BASE_ATTRIBUTE"},
        "source_event_refs": ["E_PROFILE_FIGHTER_CREATED"],
    }
    value.update(overrides)
    return value


def ledger(**overrides):
    value = {
        "actor_id": "ACTOR-FIGHTER-001",
        "skill_entries": ["LOCKPICK"],
        "source_event_cursor": "E_SKILL_LEDGER_001",
        "schema_version": "1.0.0-candidate",
    }
    value.update(overrides)
    return value


def demand(**overrides):
    value = {
        "demand_id": "DEMAND-LOCK-001",
        "action_family": "OPEN_LOCK",
        "method_id": "METHOD-LOCKPICK",
        "hard_prerequisites": {
            "required_attribute_keys": ["grip"],
            "required_skill_ids": ["LOCKPICK"],
        },
        "ruleset_version": "RULESET-FAMILY-A@1",
    }
    value.update(overrides)
    return value


def test_i2a_admits_complete_authoritative_profile_without_using_fixture_labels():
    admitted = validate_actor_base_profile(profile(), policy())

    assert admitted == profile()
    with pytest.raises(ValueError, match="I2A_PROFILE_SCHEMA_RULESET_MISMATCH"):
        validate_actor_base_profile(profile(ruleset_family_ref="RULESET-FAMILY-B@1"), policy())


@pytest.mark.parametrize(
    "overrides, code",
    [
        ({"actor_id": None}, "I2A_PROFILE_ACTOR_ID_REQUIRED"),
        ({"profile_version": "1.0.0-candidate"}, "I2A_PROFILE_VERSION_MISMATCH"),
        ({"base_attribute_map": {}}, "I2A_PROFILE_BASE_ATTRIBUTE_MAP_REQUIRED"),
        ({"source_event_refs": []}, "I2A_PROFILE_SOURCE_EVENT_REFS_REQUIRED"),
    ],
)
def test_i2a_profile_admission_fails_closed_for_incomplete_shape(overrides, code):
    with pytest.raises(ValueError, match=code):
        validate_actor_base_profile(profile(**overrides), policy())


def test_i2a_feasibility_precedes_any_outcome_or_randomness():
    receipt = resolve_i2a_feasibility(policy=policy(), actor_profile=profile(), skill_ledger=ledger(), action_demand=demand(), action_id="ACTION-001")

    assert receipt["feasibility"] == "FEASIBLE"
    assert receipt["outcome_band"] == "NOT_RESOLVED_I2A"
    assert receipt["hazard_outcome"] == "NOT_EVALUATED_I2A"
    assert receipt["random_provenance_optional"] is None
    assert receipt["effective_capability"] == "NOT_COMPUTED_IN_I2A"

    missing_skill = resolve_i2a_feasibility(policy=policy(), actor_profile=profile(), skill_ledger=ledger(skill_entries=["SPEAK"]), action_demand=demand(), action_id="ACTION-002")
    assert missing_skill["feasibility"] == "HARD_FAIL_MISSING_REQUIRED_SKILL"
    assert missing_skill["failure_reason"] == "LOCKPICK"
    assert missing_skill["outcome_band"] == "NOT_RESOLVED_I2A"


def test_i2a_receipt_replays_from_inputs_and_rejects_tampering():
    inputs = {"policy": policy(), "actor_profile": profile(), "skill_ledger": ledger(), "action_demand": demand()}
    receipt = resolve_i2a_feasibility(**inputs, action_id="ACTION-003")
    first = export_i2a_replay_package(**inputs, receipt=receipt)
    second = export_i2a_replay_package(**inputs, receipt=receipt)

    assert first == second
    evidence = import_i2a_replay_package(first)
    assert evidence.receipt == receipt
    assert rehydrate_i2a_replay_package(first) == receipt

    tampered = json.loads(first.decode("utf-8"))
    tampered["receipt"]["feasibility"] = "HARD_FAIL_MISSING_REQUIRED_SKILL"
    with pytest.raises(ValueError, match="I2A_PACKAGE_INTEGRITY_FAILURE"):
        import_i2a_replay_package(json.dumps(tampered, sort_keys=True, separators=(",", ":")).encode("utf-8"))
