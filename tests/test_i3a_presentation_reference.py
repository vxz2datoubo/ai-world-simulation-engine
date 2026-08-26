import copy
import hashlib
import json

import pytest

from evals.i3a_presentation_reference import (
    I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_PROVIDER_INTEGRATION,
    NO_REAL_RENDERER_IMPLEMENTED,
    build_presentation_reference,
    export_replay_package,
    replay_package,
    validate_mock_render_claims,
)
from awrse.model import thaw_value


ACTOR = "ACTOR-I3A-001"
VIEWS = ["VIEW-PLAZA-WEST", "VIEW-PLAZA-EAST"]
INVENTORY = ["OBJ-COAT", "OBJ-BOOTS", "MAT-LINEN"]
ASSETS = {
    "OBJ-COAT": {
        "media_asset_id": "AST-COAT",
        "media_version_id": "VER-COAT-1",
        "locator_id": "LOC-COAT-A",
    },
    "OBJ-BOOTS": {
        "media_asset_id": "AST-BOOTS",
        "media_version_id": "VER-BOOTS-1",
        "locator_id": "LOC-BOOTS-A",
    },
    "MAT-LINEN": {
        "media_asset_id": "AST-LINEN",
        "media_version_id": "VER-LINEN-1",
        "locator_id": "LOC-LINEN-A",
    },
}
EVENTS = [
    {"event_id": "E-I3A-001-WEAR-COAT", "cursor": 101, "actor_id": ACTOR, "kind": "WEAR_SLOT", "slot": "torso_outer", "object_ref": "OBJ-COAT"},
    {"event_id": "E-I3A-002-WEAR-BOOTS", "cursor": 102, "actor_id": ACTOR, "kind": "WEAR_SLOT", "slot": "feet", "object_ref": "OBJ-BOOTS"},
    {"event_id": "E-I3A-003-REMOVE-BOOTS", "cursor": 103, "actor_id": ACTOR, "kind": "CLEAR_SLOT", "slot": "feet"},
    {
        "event_id": "E-I3A-004-DRESS-RIGHT-FOREARM", "cursor": 104, "actor_id": ACTOR,
        "kind": "APPLY_DRESSING", "dressing_id": "DRESS-RF-1", "body_region": "FOREARM", "side": "RIGHT",
        "material_ref": "MAT-LINEN",
        "appearance_state": {"color": "WHITE", "wrap_style": "SPIRAL", "stain": "LIGHT_BLOOD"},
        "covered_by_refs": [],
    },
    {
        "event_id": "E-I3A-005-MUD-COAT", "cursor": 105, "actor_id": ACTOR, "kind": "SET_SURFACE",
        "surface_state_id": "SURF-COAT-MUD", "target_ref": "OBJ-COAT", "surface_type": "MUD", "intensity": 0.4,
    },
]


def build(events=None, *, view_id=VIEWS[0], inventory=None, assets=None):
    return build_presentation_reference(
        actor_id=ACTOR,
        events=copy.deepcopy(EVENTS if events is None else events),
        inventory_object_refs=list(INVENTORY if inventory is None else inventory),
        asset_registry=copy.deepcopy(ASSETS if assets is None else assets),
        view_id=view_id,
        valid_view_ids=VIEWS,
    )


def aligned_claims(reference):
    return {
        "view_id": reference.view_id,
        "outfit_slots": thaw_value(reference.outfit_state["slot_bindings"]),
        "dressings": [
            {
                "dressing_id": item["dressing_id"], "body_region": item["body_region"], "side": item["side"],
                "material_ref": item["material_ref"], "appearance_state": thaw_value(item["appearance_state"]),
            }
            for item in reference.dressing_states
        ],
        "surface_states": [
            {
                "surface_state_id": item["surface_state_id"], "target_ref": item["target_ref"],
                "surface_type": item["surface_type"], "intensity": item["intensity"],
            }
            for item in reference.surface_states
        ],
    }


def test_scope_locks_remain_narrow():
    assert I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_REAL_RENDERER_IMPLEMENTED is True
    assert NO_PROVIDER_INTEGRATION is True


def test_golden_06_reference_keeps_no_shoes_right_dressing_and_surface_state():
    reference = build()
    slots = thaw_value(reference.outfit_state["slot_bindings"])
    assert slots == {"torso_outer": "OBJ-COAT"}
    assert "OBJ-BOOTS" in INVENTORY
    assert "feet" not in slots
    dressing = reference.dressing_states[0]
    assert dressing["body_region"] == "FOREARM"
    assert dressing["side"] == "RIGHT"
    assert dressing["material_ref"] == "MAT-LINEN"
    assert dressing["source_treatment_event_ref"] == "E-I3A-004-DRESS-RIGHT-FOREARM"
    assert reference.surface_states[0]["surface_type"] == "MUD"
    assert reference.appearance_snapshot["world_event_cursor"] == 105


def test_mock_render_exact_claims_align():
    reference = build()
    assert validate_mock_render_claims(reference, aligned_claims(reference)).status == "RENDER_ALIGNED"


def test_inventory_owned_does_not_silently_become_worn():
    reference = build(); claims = aligned_claims(reference); claims["outfit_slots"]["feet"] = "OBJ-BOOTS"
    result = validate_mock_render_claims(reference, claims)
    assert result.status == "RENDER_MISMATCH"
    assert any(item.startswith("OUTFIT_SLOT:feet:") for item in result.contradictions)


def test_wear_transition_requires_real_possession():
    inventory = [ref for ref in INVENTORY if ref != "OBJ-BOOTS"]
    with pytest.raises(ValueError, match="I3A_WORN_OBJECT_NOT_POSSESSED:OBJ-BOOTS"):
        build(inventory=inventory)


def test_renderer_wrong_dressing_side_fails_closed():
    reference = build(); claims = aligned_claims(reference); claims["dressings"][0]["side"] = "LEFT"
    result = validate_mock_render_claims(reference, claims)
    assert "DRESSING:DRESS-RF-1:side:LEFT!=RIGHT" in result.contradictions


def test_renderer_body_region_drift_fails_closed():
    reference = build(); claims = aligned_claims(reference); claims["dressings"][0]["body_region"] = "UPPER_ARM"
    assert any("body_region" in item for item in validate_mock_render_claims(reference, claims).contradictions)


def test_dressing_treatment_provenance_cannot_self_redirect():
    events = copy.deepcopy(EVENTS); events[3]["source_treatment_event_ref"] = "E-FAKE-TREATMENT"
    with pytest.raises(ValueError, match="I3A_DRESSING_TREATMENT_PROVENANCE_MISMATCH"):
        build(events)


def test_removed_dressing_cannot_be_resurrected_by_old_generated_claim():
    events = copy.deepcopy(EVENTS)
    events.append({"event_id": "E-I3A-006-REMOVE-DRESSING", "cursor": 106, "actor_id": ACTOR, "kind": "REMOVE_DRESSING", "dressing_id": "DRESS-RF-1"})
    reference = build(events); claims = aligned_claims(reference)
    claims["dressings"] = [{"dressing_id": "DRESS-RF-1", "body_region": "FOREARM", "side": "RIGHT", "material_ref": "MAT-LINEN", "appearance_state": {"color": "WHITE", "wrap_style": "SPIRAL", "stain": "LIGHT_BLOOD"}}]
    assert "OBSOLETE_OR_UNKNOWN_DRESSING:DRESS-RF-1" in validate_mock_render_claims(reference, claims).contradictions


def test_renderer_or_generated_pixels_cannot_request_upstream_mutation():
    reference = build(); claims = aligned_claims(reference); claims.update({"mutation_requested": True, "generated_media_as_authority": True})
    assert set(validate_mock_render_claims(reference, claims).unauthorized_claims) == {"GENERATED_PIXELS_CANNOT_AUTHOR_PRESENTATION_STATE", "RENDERER_CANNOT_MUTATE_PRESENTATION_STATE"}


def test_asset_registry_rejects_live_presentation_contamination():
    assets = copy.deepcopy(ASSETS); assets["OBJ-COAT"]["slot_bindings"] = {"torso_outer": "OBJ-COAT"}
    with pytest.raises(ValueError, match="I3A_DYNAMIC_PRESENTATION_CONTAMINATES_ASSET_REGISTRY"):
        build(assets=assets)


def test_locator_migration_does_not_change_presentation_identity_or_history():
    before = build(); migrated = copy.deepcopy(ASSETS); migrated["OBJ-COAT"]["locator_id"] = "LOC-COAT-B"; migrated["MAT-LINEN"]["locator_id"] = "LOC-LINEN-B"; after = build(assets=migrated)
    assert before.outfit_state == after.outfit_state
    assert before.dressing_states == after.dressing_states
    assert before.surface_states == after.surface_states
    assert before.presentation_state == after.presentation_state
    assert before.appearance_snapshot == after.appearance_snapshot


def test_view_change_does_not_change_actor_presentation_truth():
    west = build(view_id=VIEWS[0]); east = build(view_id=VIEWS[1])
    assert west.view_id != east.view_id
    assert west.outfit_state == east.outfit_state
    assert west.dressing_states == east.dressing_states
    assert west.surface_states == east.surface_states
    assert west.presentation_state == east.presentation_state
    assert west.appearance_snapshot == east.appearance_snapshot


def test_noncanonical_view_is_rejected():
    with pytest.raises(ValueError, match="I3A_VIEW_NOT_CANONICAL"):
        build(view_id="VIEW-INVENTED")


def test_replay_package_is_byte_deterministic_and_rebuilds_exact_reference():
    reference = build()
    kwargs = dict(reference=reference, events=copy.deepcopy(EVENTS), inventory_object_refs=INVENTORY, asset_registry=copy.deepcopy(ASSETS), valid_view_ids=VIEWS)
    package_a = export_replay_package(**kwargs); package_b = export_replay_package(**kwargs)
    assert package_a == package_b
    assert replay_package(package_a) == reference


def test_replay_payload_tampering_is_rejected_before_rebuild():
    reference = build(); package = export_replay_package(reference=reference, events=EVENTS, inventory_object_refs=INVENTORY, asset_registry=ASSETS, valid_view_ids=VIEWS)
    envelope = json.loads(package); envelope["payload"]["inputs"]["events"][3]["side"] = "LEFT"
    with pytest.raises(ValueError, match="I3A_REPLAY_PACKAGE_TAMPERED"):
        replay_package(json.dumps(envelope))


def test_replay_cannot_accept_forged_expected_snapshot_even_with_recomputed_digest():
    reference = build(); package = export_replay_package(reference=reference, events=EVENTS, inventory_object_refs=INVENTORY, asset_registry=ASSETS, valid_view_ids=VIEWS)
    envelope = json.loads(package); envelope["payload"]["expected_reference"]["appearance_snapshot"]["world_event_cursor"] = 999
    canonical_payload = json.dumps(envelope["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    envelope["sha256"] = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()
    with pytest.raises(ValueError, match="I3A_REPLAY_MATERIALIZATION_MISMATCH"):
        replay_package(json.dumps(envelope, ensure_ascii=False))


def test_event_cursor_must_be_strictly_monotonic():
    events = copy.deepcopy(EVENTS); events[2]["cursor"] = 102
    with pytest.raises(ValueError, match="I3A_EVENT_CURSOR_INVALID"):
        build(events)


def test_dressing_appearance_cannot_mint_functional_injury():
    reference = build(); claims = aligned_claims(reference); claims["inferred_injury_refs"] = ["INJURY-INFERRED-FROM-BANDAGE"]
    assert "DRESSING_APPEARANCE_CANNOT_AUTHOR_FUNCTIONAL_INJURY" in validate_mock_render_claims(reference, claims).unauthorized_claims


def test_reference_nested_state_is_read_only():
    reference = build()
    with pytest.raises(TypeError): reference.outfit_state["slot_bindings"]["feet"] = "OBJ-BOOTS"
    with pytest.raises(TypeError): reference.dressing_states[0]["appearance_state"]["color"] = "BLACK"


def test_hidden_dressing_is_not_forced_visible_but_wrong_claim_still_fails():
    events = copy.deepcopy(EVENTS); events[3]["covered_by_refs"] = ["OBJ-COAT"]
    reference = build(events); claims = aligned_claims(reference); claims["dressings"] = []
    assert validate_mock_render_claims(reference, claims).status == "RENDER_ALIGNED"
    claims["dressings"] = [{"dressing_id": "DRESS-RF-1", "body_region": "FOREARM", "side": "LEFT", "material_ref": "MAT-LINEN", "appearance_state": {"color": "WHITE", "wrap_style": "SPIRAL", "stain": "LIGHT_BLOOD"}}]
    assert validate_mock_render_claims(reference, claims).status == "RENDER_MISMATCH"


def test_cleared_surface_cannot_be_resurrected():
    events = copy.deepcopy(EVENTS)
    events.append({"event_id": "E-I3A-006-CLEAN-COAT", "cursor": 106, "actor_id": ACTOR, "kind": "CLEAR_SURFACE", "surface_state_id": "SURF-COAT-MUD"})
    reference = build(events); claims = aligned_claims(reference)
    claims["surface_states"] = [{"surface_state_id": "SURF-COAT-MUD", "target_ref": "OBJ-COAT", "surface_type": "MUD", "intensity": 0.4}]
    assert "OBSOLETE_OR_UNKNOWN_SURFACE:SURF-COAT-MUD" in validate_mock_render_claims(reference, claims).contradictions
