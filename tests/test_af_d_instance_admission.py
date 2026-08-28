import copy
from dataclasses import asdict, FrozenInstanceError
import hashlib
import json
from pathlib import Path

import pytest

import registries.af_d_instance_admission as admission
from registries.af_d_instance_admission import (
    I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_AI_FILM_FEDERATION_IMPLEMENTED,
    NO_PROVIDER_INTEGRATION,
    NO_REAL_RENDERER_IMPLEMENTED,
    issue_admission_receipt,
    verify_admission_receipt,
)


ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING = ROOT / "contracts" / "AF001-AF-D-INSTANCE-ADMISSION-BINDING.json"
MANIFEST = ROOT / "registries" / "AF001-AF-D-REFERENCE-INSTANCES.json"
CONFORMANCE = ROOT / "evals" / "AF001-ASSET-SPATIAL-CONFORMANCE.json"

WEST_A = ("AST-DAY-WEST", "VER-DAY-WEST-1", "LOC-DAY-WEST-A")
WEST_B = ("AST-DAY-WEST", "VER-DAY-WEST-1", "LOC-DAY-WEST-B")
EAST = ("AST-DAY-EAST", "VER-DAY-EAST-1", "LOC-DAY-EAST")
NIGHT_WEST = ("AST-NIGHT-WEST", "VER-NIGHT-WEST-1", "LOC-NIGHT-WEST")


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _digest_without_receipt_sha(value):
    material = copy.deepcopy(value)
    material.pop("receipt_sha256", None)
    encoded = json.dumps(
        material,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _forge(receipt, **changes):
    value = asdict(receipt)
    value.update(changes)
    value["receipt_sha256"] = _digest_without_receipt_sha(value)
    return value


def test_scope_locks_keep_authority_slice_bounded():
    assert I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_REAL_RENDERER_IMPLEMENTED is True
    assert NO_PROVIDER_INTEGRATION is True
    assert NO_AI_FILM_FEDERATION_IMPLEMENTED is True


def test_parent_explicitly_registers_binding_manifest_and_scoped_epoch():
    parent = _load(PARENT)
    binding = _load(BINDING)
    manifest = _load(MANIFEST)

    assert parent["contract_version"] == "1.10.0-candidate"
    assert parent["af_d_instance_admission_authority_epoch"] == "AF001-AF-D-INSTANCE-ADMISSION-001@1"
    registration = parent["registered_contract_extensions"][binding["binding_id"]]
    assert registration["path"] == "contracts/AF001-AF-D-INSTANCE-ADMISSION-BINDING.json"
    assert registration["binding_version"] == binding["binding_version"]
    assert registration["parent_contract_id"] == parent["contract_id"]
    assert registration["parent_contract_version"] == parent["contract_version"]
    assert registration["parent_authority_graph_version"] == parent["authority_graph_version"]
    assert registration["af_d_instance_admission_authority_epoch"] == parent["af_d_instance_admission_authority_epoch"]
    assert registration["authority"] == "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
    assert registration["governance_issue_ref"] == "#66"
    assert registration["runtime_implementation_authorized"] is False
    assert registration["bounded_reference_adapter_implementation_authorized"] is True

    canonical_binding_digest = hashlib.sha256(
        json.dumps(binding, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    canonical_manifest_digest = hashlib.sha256(
        json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")
    ).hexdigest()
    assert registration["binding_canonical_sha256"] == canonical_binding_digest
    assert registration["canonical_instance_manifest"] == {
        "path": "registries/AF001-AF-D-REFERENCE-INSTANCES.json",
        "manifest_id": manifest["manifest_id"],
        "manifest_version": manifest["manifest_version"],
        "canonical_sha256": canonical_manifest_digest,
    }

    discriminator = parent["versioning_and_migration"]["af_d_instance_admission_authority_discriminator"]
    assert discriminator["field"] == "af_d_instance_admission_authority_epoch"
    assert discriminator["current"] == "AF001-AF-D-INSTANCE-ADMISSION-001@1"
    assert discriminator["pre_af_d_instance_admission_state"] == "FIELD_ABSENT"
    assert discriminator["authorization_tuple"] == [
        "contract_id",
        "contract_version",
        "authority_graph_version",
        "af_d_instance_admission_authority_epoch",
    ]


def test_conformance_eval_remains_explicitly_nonauthority():
    conformance = _load(CONFORMANCE)
    manifest = _load(MANIFEST)
    assert conformance["status"] == "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    assert manifest["canonicalization_provenance"]["historical_design_evidence_authority"] == "NONAUTHORITY_INPUT_ONLY"
    assert "PRIOR_EVAL_OCCURRENCE_CONFERS_NO_INSTANCE_AUTHORITY" in manifest["canonicalization_provenance"]["rule"]


def test_canonical_receipt_is_deterministic_and_verifies_by_rederivation():
    a = issue_admission_receipt(
        requested_view_ids=["VIEW-WEST", "VIEW-EAST"],
        requested_asset_bindings=[WEST_A, EAST],
    )
    b = issue_admission_receipt(
        requested_view_ids=["VIEW-EAST", "VIEW-WEST"],
        requested_asset_bindings=[EAST, WEST_A],
    )
    assert a == b
    assert len(a.receipt_sha256) == 64

    verified = verify_admission_receipt(a)
    assert verified.view_ids == ("VIEW-EAST", "VIEW-WEST")
    assert verified.asset_bindings == tuple(sorted((WEST_A, EAST)))
    assert verified.authority_epoch == "AF001-AF-D-INSTANCE-ADMISSION-001@1"


def test_unknown_view_cannot_be_minted_by_request():
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_VIEW_UNKNOWN:VIEW-INVENTED"):
        issue_admission_receipt(requested_view_ids=["VIEW-INVENTED"])


def test_fully_invented_asset_chain_cannot_be_minted_by_request():
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_ASSET_BINDING_UNKNOWN"):
        issue_admission_receipt(
            requested_asset_bindings=[("AST-INVENTED", "VER-INVENTED-1", "LOC-INVENTED")]
        )


def test_real_ids_recombined_into_false_relationship_fail_closed():
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_ASSET_BINDING_UNKNOWN"):
        issue_admission_receipt(
            requested_asset_bindings=[("AST-DAY-WEST", "VER-DAY-EAST-1", "LOC-DAY-EAST")]
        )


def test_reviewer_attack_forged_complete_envelope_with_novel_issuer_and_invented_ids_is_rejected():
    baseline = issue_admission_receipt(requested_view_ids=["VIEW-WEST"], requested_asset_bindings=[WEST_A])
    forged = _forge(
        baseline,
        issuer_id="caller://forged-af-d-authority",
        requested_view_ids=("VIEW-INVENTED",),
        admitted_view_ids=("VIEW-INVENTED",),
        requested_asset_bindings=(("AST-INVENTED", "VER-INVENTED-1", "LOC-INVENTED"),),
        admitted_asset_bindings=(("AST-INVENTED", "VER-INVENTED-1", "LOC-INVENTED"),),
    )
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_VIEW_UNKNOWN"):
        verify_admission_receipt(forged)


def test_copying_canonical_issuer_strings_cannot_author_altered_admitted_set():
    baseline = issue_admission_receipt(requested_view_ids=["VIEW-WEST"], requested_asset_bindings=[WEST_A])
    forged = _forge(
        baseline,
        admitted_view_ids=("VIEW-WEST", "VIEW-INVENTED"),
    )
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_RECEIPT_MATERIALIZATION_MISMATCH"):
        verify_admission_receipt(forged)


def test_unknown_issuer_rejected_even_for_otherwise_canonical_request():
    baseline = issue_admission_receipt(requested_view_ids=["VIEW-WEST"], requested_asset_bindings=[WEST_A])
    forged = _forge(baseline, issuer_id="caller://not-the-canonical-issuer")
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_ISSUER_MISMATCH"):
        verify_admission_receipt(forged)


def test_receipt_digest_tampering_fails_before_materialization():
    baseline = asdict(issue_admission_receipt(requested_view_ids=["VIEW-WEST"]))
    baseline["manifest_sha256"] = "0" * 64
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_RECEIPT_DIGEST_MISMATCH"):
        verify_admission_receipt(baseline)


def test_old_parent_without_scoped_epoch_cannot_authorize_new_extension(tmp_path, monkeypatch):
    parent = _load(PARENT)
    parent.pop("af_d_instance_admission_authority_epoch")
    parent["registered_contract_extensions"].pop("AWRSE-AF001-AF-D-INSTANCE-ADMISSION-BINDING")
    path = tmp_path / "old-parent.json"
    path.write_text(json.dumps(parent), encoding="utf-8")
    monkeypatch.setattr(admission, "_PARENT_PATH", path)
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_AUTHORITY_EPOCH_MISMATCH"):
        issue_admission_receipt(requested_view_ids=["VIEW-WEST"])


def test_manifest_tamper_is_detected_by_parent_registered_digest(tmp_path, monkeypatch):
    manifest = _load(MANIFEST)
    manifest["views"][0]["view_id"] = "VIEW-INVENTED"
    path = tmp_path / "tampered-manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(admission, "_MANIFEST_PATH", path)
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_MANIFEST_DIGEST_MISMATCH"):
        issue_admission_receipt(requested_view_ids=["VIEW-WEST"])


def test_binding_tamper_is_detected_by_parent_registered_digest(tmp_path, monkeypatch):
    binding = _load(BINDING)
    binding["issuer_profile"]["issuer_id"] = "caller://forged-issuer"
    path = tmp_path / "tampered-binding.json"
    path.write_text(json.dumps(binding), encoding="utf-8")
    monkeypatch.setattr(admission, "_BINDING_PATH", path)
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_BINDING_DIGEST_MISMATCH"):
        issue_admission_receipt(requested_view_ids=["VIEW-WEST"])


def test_nonauthority_eval_file_cannot_be_substituted_as_manifest(monkeypatch):
    monkeypatch.setattr(admission, "_MANIFEST_PATH", CONFORMANCE)
    with pytest.raises(ValueError, match="AF_D_INSTANCE_ADMISSION_MANIFEST_DIGEST_MISMATCH"):
        issue_admission_receipt(requested_view_ids=["VIEW-WEST"])


def test_locator_migration_changes_only_locator_not_asset_or_version_identity():
    before = verify_admission_receipt(
        issue_admission_receipt(requested_asset_bindings=[WEST_A])
    ).asset_bindings[0]
    after = verify_admission_receipt(
        issue_admission_receipt(requested_asset_bindings=[WEST_B])
    ).asset_bindings[0]
    assert before[:2] == after[:2] == ("AST-DAY-WEST", "VER-DAY-WEST-1")
    assert before[2] != after[2]


def test_request_mutation_after_issue_cannot_mutate_receipt_or_manifest_truth():
    views = ["VIEW-WEST"]
    bindings = [list(WEST_A)]
    receipt = issue_admission_receipt(
        requested_view_ids=views,
        requested_asset_bindings=bindings,
    )
    views[0] = "VIEW-INVENTED"
    bindings[0][0] = "AST-INVENTED"

    assert receipt.requested_view_ids == ("VIEW-WEST",)
    assert receipt.requested_asset_bindings == (WEST_A,)
    assert verify_admission_receipt(receipt).view_ids == ("VIEW-WEST",)


def test_receipt_object_is_frozen_read_only_derived_evidence():
    receipt = issue_admission_receipt(requested_view_ids=["VIEW-WEST"])
    with pytest.raises(FrozenInstanceError):
        receipt.issuer_id = "caller://mutation"
