import copy
import hashlib
import json
from pathlib import Path

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
VIEWS = ["VIEW-WEST", "VIEW-EAST"]
INVENTORY = ["OBJ-COAT", "OBJ-BOOTS", "MAT-LINEN"]
ASSETS = {
    "OBJ-COAT": {
        "media_asset_id": "AST-DAY-WEST",
        "media_version_id": "VER-DAY-WEST-1",
        "locator_id": "LOC-DAY-WEST-A",
    },
    "OBJ-BOOTS": {
        "media_asset_id": "AST-NIGHT-WEST",
        "media_version_id": "VER-NIGHT-WEST-1",
        "locator_id": "LOC-NIGHT-WEST",
    },
    "MAT-LINEN": {
        "media_asset_id": "AST-DAY-EAST",
        "media_version_id": "VER-DAY-EAST-1",
        "locator_id": "LOC-DAY-EAST",
    },
}
FORGED_IDENTITY_EVIDENCE = {
    "status": "UPSTREAM_PREVALIDATED_IDENTITY_EVIDENCE",
    "authority_identity": {
        "canonical_contract_id": "AWRSE-AF001-LIVING-STORY-CONTRACTS",
        "canonical_contract_version": "1.9.0-candidate",
        "admission_authority_ref": "caller://forged-af-d-authority",
        "view_authority_profile_ref": "SPATIAL_VIEW_DEFINITION_REGISTRY",
        "asset_authority_profile_ref": "ASSET_LOGICAL_IDENTITY_REGISTRY",
        "version_authority_profile_ref": "ASSET_IMMUTABLE_VERSION_REGISTRY",
        "locator_authority_profile_ref": "ASSET_LOCATOR_RESOLUTION",
    },
    "admitted_view_ids": ["VIEW-INVENTED"],
    "admitted_asset_bindings": [
        {"media_asset_id": "AST-INVENTED", "media_version_id": "VER-INVENTED-1", "locator_id": "LOC-INVENTED"},
    ],
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


def build(events=None, *, view_id=VIEWS[0], inventory=None, assets=None, evidence=None, valid_view_ids=None):
    return build_presentation_reference(
        actor_id=ACTOR,
        events=copy.deepcopy(EVENTS if events is None else events),
        inventory_object_refs=list(INVENTORY if inventory is None else inventory),
        asset_registry=copy.deepcopy(ASSETS if assets is None else assets),
        view_id=view_id,
        valid_view_ids=valid_view_ids,
        identity_evidence=copy.deepcopy(evidence),
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


def package(reference):
    return export_replay_package(
        reference=reference,
        events=EVENTS,
        inventory_object_refs=INVENTORY,
        asset_registry=ASSETS,
    )


def _recompute_package_digest(envelope):
    canonical_payload = json.dumps(
        envelope["payload"], sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    )
    envelope["sha256"] = hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


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
    assert reference.identity_admission_issuer_id == "AWRSE-AF-D-REFERENCE-INSTANCE-ADMISSION-ISSUER"
    assert reference.identity_admission_issuer_version == "1.0.0-candidate"
    assert reference.identity_admission_authority_epoch == "AF001-AF-D-INSTANCE-ADMISSION-001@1"
    assert reference.identity_manifest_id == "AWRSE-AF001-AF-D-REFERENCE-INSTANCE-MANIFEST"
    assert len(reference.identity_manifest_sha256) == 64
    assert len(reference.identity_receipt_sha256) == 64


def test_mock_render_exact_claims_align():
    reference = build()
    assert validate_mock_render_claims(reference, aligned_claims(reference)).status == "RENDER_ALIGNED"


def test_inventory_owned_does_not_silently_become_worn():
    reference = build()
    claims = aligned_claims(reference)
    claims["outfit_slots"]["feet"] = "OBJ-BOOTS"
    result = validate_mock_render_claims(reference, claims)
    assert result.status == "RENDER_MISMATCH"
    assert any(item.startswith("OUTFIT_SLOT:feet:") for item in result.contradictions)


def test_wear_transition_requires_real_possession():
    with pytest.raises(ValueError, match="I3A_WORN_OBJECT_NOT_POSSESSED:OBJ-BOOTS"):
        build(inventory=[ref for ref in INVENTORY if ref != "OBJ-BOOTS"])


def test_renderer_wrong_dressing_side_fails_closed():
    reference = build()
    claims = aligned_claims(reference)
    claims["dressings"][0]["side"] = "LEFT"
    assert "DRESSING:DRESS-RF-1:side:LEFT!=RIGHT" in validate_mock_render_claims(reference, claims).contradictions


def test_renderer_body_region_drift_fails_closed():
    reference = build()
    claims = aligned_claims(reference)
    claims["dressings"][0]["body_region"] = "UPPER_ARM"
    assert any("body_region" in item for item in validate_mock_render_claims(reference, claims).contradictions)


def test_dressing_treatment_provenance_cannot_self_redirect():
    events = copy.deepcopy(EVENTS)
    events[3]["source_treatment_event_ref"] = "E-FAKE-TREATMENT"
    with pytest.raises(ValueError, match="I3A_DRESSING_TREATMENT_PROVENANCE_MISMATCH"):
        build(events)


def test_removed_dressing_cannot_be_resurrected_by_old_generated_claim():
    events = copy.deepcopy(EVENTS)
    events.append({"event_id": "E-I3A-006-REMOVE-DRESSING", "cursor": 106, "actor_id": ACTOR, "kind": "REMOVE_DRESSING", "dressing_id": "DRESS-RF-1"})
    reference = build(events)
    claims = aligned_claims(reference)
    claims["dressings"] = [{"dressing_id": "DRESS-RF-1", "body_region": "FOREARM", "side": "RIGHT", "material_ref": "MAT-LINEN", "appearance_state": {"color": "WHITE", "wrap_style": "SPIRAL", "stain": "LIGHT_BLOOD"}}]
    assert "OBSOLETE_OR_UNKNOWN_DRESSING:DRESS-RF-1" in validate_mock_render_claims(reference, claims).contradictions


def test_renderer_or_generated_pixels_cannot_request_upstream_mutation():
    reference = build()
    claims = aligned_claims(reference)
    claims.update({"mutation_requested": True, "generated_media_as_authority": True})
    assert set(validate_mock_render_claims(reference, claims).unauthorized_claims) == {
        "GENERATED_PIXELS_CANNOT_AUTHOR_PRESENTATION_STATE",
        "RENDERER_CANNOT_MUTATE_PRESENTATION_STATE",
    }


def test_asset_registry_rejects_live_presentation_contamination():
    assets = copy.deepcopy(ASSETS)
    assets["OBJ-COAT"]["slot_bindings"] = {"torso_outer": "OBJ-COAT"}
    with pytest.raises(ValueError, match="I3A_DYNAMIC_PRESENTATION_CONTAMINATES_ASSET_REGISTRY"):
        build(assets=assets)


def test_caller_cannot_self_authorize_invented_asset_identity_chain():
    assets = copy.deepcopy(ASSETS)
    assets["OBJ-COAT"] = {"media_asset_id": "AST-INVENTED", "media_version_id": "VER-INVENTED-1", "locator_id": "LOC-INVENTED-A"}
    with pytest.raises(ValueError, match="I3A_ASSET_BINDING_NOT_ADMITTED"):
        build(assets=assets)


def test_mixed_real_ids_cannot_forge_asset_version_locator_relationship():
    assets = copy.deepcopy(ASSETS)
    assets["OBJ-COAT"]["media_version_id"] = "VER-NIGHT-WEST-1"
    assets["OBJ-COAT"]["locator_id"] = "LOC-NIGHT-WEST"
    with pytest.raises(ValueError, match="I3A_ASSET_BINDING_NOT_ADMITTED"):
        build(assets=assets)


def test_nonauthority_conformance_fixture_cannot_mint_instance_admission():
    path = Path(__file__).resolve().parents[1] / "evals" / "AF001-ASSET-SPATIAL-CONFORMANCE.json"
    evidence = json.loads(path.read_text(encoding="utf-8"))
    with pytest.raises(ValueError, match="I3A_CALLER_AUTHORED_IDENTITY_EVIDENCE_FORBIDDEN"):
        build(evidence=evidence)


def test_structurally_complete_forged_prevalidated_envelope_is_rejected():
    with pytest.raises(ValueError, match="I3A_CALLER_AUTHORED_IDENTITY_EVIDENCE_FORBIDDEN"):
        build(evidence=FORGED_IDENTITY_EVIDENCE)


def test_old_identity_evidence_path_is_rejected_even_with_canonical_ids():
    evidence = copy.deepcopy(FORGED_IDENTITY_EVIDENCE)
    evidence["authority_identity"]["admission_authority_ref"] = "registries/AF001-AF-D-REFERENCE-INSTANCES.json"
    evidence["admitted_view_ids"] = ["VIEW-WEST"]
    evidence["admitted_asset_bindings"] = [copy.deepcopy(ASSETS["OBJ-COAT"])]
    with pytest.raises(ValueError, match="I3A_CALLER_AUTHORED_IDENTITY_EVIDENCE_FORBIDDEN"):
        build(evidence=evidence)


def test_locator_migration_does_not_change_presentation_identity_or_history():
    before = build()
    migrated = copy.deepcopy(ASSETS)
    migrated["OBJ-COAT"]["locator_id"] = "LOC-DAY-WEST-B"
    after = build(assets=migrated)
    assert before.outfit_state == after.outfit_state
    assert before.dressing_states == after.dressing_states
    assert before.surface_states == after.surface_states
    assert before.presentation_state == after.presentation_state
    assert before.appearance_snapshot == after.appearance_snapshot
    assert before.identity_receipt_sha256 != after.identity_receipt_sha256


def test_view_change_does_not_change_actor_presentation_truth():
    west, east = build(view_id=VIEWS[0]), build(view_id=VIEWS[1])
    assert west.view_id != east.view_id
    assert west.outfit_state == east.outfit_state
    assert west.dressing_states == east.dressing_states
    assert west.surface_states == east.surface_states
    assert west.presentation_state == east.presentation_state
    assert west.appearance_snapshot == east.appearance_snapshot
    assert west.identity_receipt_sha256 != east.identity_receipt_sha256


def test_nonadmitted_view_is_rejected_even_if_caller_allowlist_contains_it():
    with pytest.raises(ValueError, match="I3A_VIEW_NOT_ADMITTED"):
        build(view_id="VIEW-INVENTED", valid_view_ids=["VIEW-INVENTED"])


def test_caller_allowlist_cannot_revoke_or_mint_admitted_view_identity():
    assert build(view_id="VIEW-WEST", valid_view_ids=["VIEW-INVENTED"]).view_id == "VIEW-WEST"


def test_replay_package_is_byte_deterministic_and_rebuilds_exact_reference():
    reference = build()
    package_a, package_b = package(reference), package(reference)
    assert package_a == package_b
    assert replay_package(package_a) == reference


def test_replay_payload_tampering_is_rejected_before_rebuild():
    reference = build()
    envelope = json.loads(package(reference))
    envelope["payload"]["inputs"]["events"][3]["side"] = "LEFT"
    with pytest.raises(ValueError, match="I3A_REPLAY_PACKAGE_TAMPERED"):
        replay_package(json.dumps(envelope))


def test_replay_cannot_accept_forged_expected_snapshot_even_with_recomputed_digest():
    reference = build()
    envelope = json.loads(package(reference))
    envelope["payload"]["expected_reference"]["appearance_snapshot"]["world_event_cursor"] = 999
    _recompute_package_digest(envelope)
    with pytest.raises(ValueError, match="I3A_REPLAY_MATERIALIZATION_MISMATCH"):
        replay_package(json.dumps(envelope, ensure_ascii=False))


def test_replay_package_cannot_reconstitute_identity_authority_from_embedded_data():
    reference = build()
    envelope = json.loads(package(reference))
    assert "identity_evidence" not in envelope["payload"]["inputs"]
    assert set(envelope["payload"]["identity_admission_binding"]) == {
        "issuer_id",
        "issuer_version",
        "authority_epoch",
        "manifest_id",
        "manifest_version",
        "manifest_sha256",
        "receipt_sha256",
    }


def test_replay_rejects_forged_view_even_with_recomputed_package_digest():
    reference = build()
    envelope = json.loads(package(reference))
    envelope["payload"]["inputs"]["view_id"] = "VIEW-INVENTED"
    _recompute_package_digest(envelope)
    with pytest.raises(ValueError, match="I3A_VIEW_NOT_ADMITTED"):
        replay_package(json.dumps(envelope, ensure_ascii=False))


def test_replay_rejects_admission_binding_tamper_even_with_recomputed_package_digest():
    reference = build()
    envelope = json.loads(package(reference))
    envelope["payload"]["identity_admission_binding"]["manifest_sha256"] = "0" * 64
    _recompute_package_digest(envelope)
    with pytest.raises(ValueError, match="I3A_REPLAY_IDENTITY_ADMISSION_MISMATCH"):
        replay_package(json.dumps(envelope, ensure_ascii=False))


def test_replay_rejects_legacy_caller_identity_evidence_path():
    reference = build()
    with pytest.raises(ValueError, match="I3A_CALLER_AUTHORED_IDENTITY_EVIDENCE_FORBIDDEN"):
        replay_package(package(reference), identity_evidence=FORGED_IDENTITY_EVIDENCE)


def test_event_cursor_must_be_strictly_monotonic():
    events = copy.deepcopy(EVENTS)
    events[2]["cursor"] = 102
    with pytest.raises(ValueError, match="I3A_EVENT_CURSOR_INVALID"):
        build(events)


def test_dressing_appearance_cannot_mint_functional_injury():
    reference = build()
    claims = aligned_claims(reference)
    claims["inferred_injury_refs"] = ["INJURY-INFERRED-FROM-BANDAGE"]
    assert "DRESSING_APPEARANCE_CANNOT_AUTHOR_FUNCTIONAL_INJURY" in validate_mock_render_claims(reference, claims).unauthorized_claims


def test_reference_nested_state_is_read_only():
    reference = build()
    with pytest.raises(TypeError):
        reference.outfit_state["slot_bindings"]["feet"] = "OBJ-BOOTS"
    with pytest.raises(TypeError):
        reference.dressing_states[0]["appearance_state"]["color"] = "BLACK"


def test_hidden_dressing_is_not_forced_visible_but_wrong_claim_still_fails():
    events = copy.deepcopy(EVENTS)
    events[3]["covered_by_refs"] = ["OBJ-COAT"]
    reference = build(events)
    claims = aligned_claims(reference)
    claims["dressings"] = []
    assert validate_mock_render_claims(reference, claims).status == "RENDER_ALIGNED"
    claims["dressings"] = [{"dressing_id": "DRESS-RF-1", "body_region": "FOREARM", "side": "LEFT", "material_ref": "MAT-LINEN", "appearance_state": {"color": "WHITE", "wrap_style": "SPIRAL", "stain": "LIGHT_BLOOD"}}]
    assert validate_mock_render_claims(reference, claims).status == "RENDER_MISMATCH"


def test_cleared_surface_cannot_be_resurrected():
    events = copy.deepcopy(EVENTS)
    events.append({"event_id": "E-I3A-006-CLEAN-COAT", "cursor": 106, "actor_id": ACTOR, "kind": "CLEAR_SURFACE", "surface_state_id": "SURF-COAT-MUD"})
    reference = build(events)
    claims = aligned_claims(reference)
    claims["surface_states"] = [{"surface_state_id": "SURF-COAT-MUD", "target_ref": "OBJ-COAT", "surface_type": "MUD", "intensity": 0.4}]
    assert "OBSOLETE_OR_UNKNOWN_SURFACE:SURF-COAT-MUD" in validate_mock_render_claims(reference, claims).contradictions
