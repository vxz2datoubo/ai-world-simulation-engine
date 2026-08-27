"""Canonical bounded AF-D reference instance admission.

This adapter is the only executable issuer for Issue #66's bounded reference
manifest. Callers can request known identities, but cannot supply an allowlist,
manifest, issuer, authority epoch, or admitted set. Verification always reloads
and re-derives from the parent-registered canonical manifest.

A receipt is derived evidence, not a bearer capability and not a cryptographic
signature. Copying a valid receipt grants no authority to add or recombine
instances because verification re-derives every admitted identity from the
canonical manifest.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import hashlib
import json
from pathlib import Path
from typing import Any, Mapping, Sequence


I3_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_REAL_RENDERER_IMPLEMENTED = True
NO_PROVIDER_INTEGRATION = True
NO_AI_FILM_FEDERATION_IMPLEMENTED = True

_ROOT = Path(__file__).resolve().parents[2]
_PARENT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_BINDING_PATH = _ROOT / "contracts" / "AF001-AF-D-INSTANCE-ADMISSION-BINDING.json"
_MANIFEST_PATH = _ROOT / "registries" / "AF001-AF-D-REFERENCE-INSTANCES.json"

_BINDING_ID = "AWRSE-AF001-AF-D-INSTANCE-ADMISSION-BINDING"
_BINDING_VERSION = "1.0.0-candidate"
_EPOCH = "AF001-AF-D-INSTANCE-ADMISSION-001@1"
_ISSUER_ID = "AWRSE-AF-D-REFERENCE-INSTANCE-ADMISSION-ISSUER"
_ISSUER_VERSION = "1.0.0-candidate"
_RECEIPT_SCHEMA_ID = "AF001.AFDInstanceAdmissionReceipt"
_RECEIPT_SCHEMA_VERSION = "1.0.0-candidate"
_MANIFEST_ID = "AWRSE-AF001-AF-D-REFERENCE-INSTANCE-MANIFEST"
_MANIFEST_VERSION = "1.0.0-candidate"
_EXPECTED_TYPE_BINDINGS = {
    "View": ("AF001.View", "1.0.0-candidate", "SPATIAL_VIEW_DEFINITION_REGISTRY"),
    "MediaAsset": ("AF001.MediaAsset", "1.0.0-candidate", "ASSET_LOGICAL_IDENTITY_REGISTRY"),
    "MediaVersion": ("AF001.MediaVersion", "1.0.0-candidate", "ASSET_IMMUTABLE_VERSION_REGISTRY"),
    "Locator": ("AF001.Locator", "1.0.0-candidate", "ASSET_LOCATOR_RESOLUTION"),
}


@dataclass(frozen=True)
class AFDInstanceAdmissionReceipt:
    receipt_schema_id: str
    receipt_schema_version: str
    issuer_id: str
    issuer_version: str
    parent_contract_id: str
    parent_contract_version: str
    parent_authority_graph_version: str
    af_d_instance_admission_authority_epoch: str
    binding_id: str
    binding_version: str
    manifest_id: str
    manifest_version: str
    manifest_sha256: str
    requested_view_ids: tuple[str, ...]
    requested_asset_bindings: tuple[tuple[str, str, str], ...]
    admitted_view_ids: tuple[str, ...]
    admitted_asset_bindings: tuple[tuple[str, str, str], ...]
    receipt_sha256: str


@dataclass(frozen=True)
class VerifiedAFDInstances:
    view_ids: tuple[str, ...]
    asset_bindings: tuple[tuple[str, str, str], ...]
    manifest_id: str
    manifest_version: str
    manifest_sha256: str
    authority_epoch: str


def _canonical_json(value: Any) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _canonical_sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _load_json(path: Path, error: str) -> Mapping[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        raise ValueError(error) from None
    if not isinstance(value, Mapping):
        raise ValueError(error)
    return value


def _require_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _normalize_view_ids(value: Any) -> tuple[str, ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError("AF_D_INSTANCE_ADMISSION_VIEW_REQUEST_INVALID")
    normalized = tuple(
        _require_string(item, "AF_D_INSTANCE_ADMISSION_VIEW_REQUEST_INVALID")
        for item in value
    )
    if len(normalized) != len(set(normalized)):
        raise ValueError("AF_D_INSTANCE_ADMISSION_DUPLICATE_VIEW_REQUEST")
    return tuple(sorted(normalized))


def _normalize_asset_bindings(value: Any) -> tuple[tuple[str, str, str], ...]:
    if isinstance(value, (str, bytes, bytearray)) or not isinstance(value, Sequence):
        raise ValueError("AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID")
    normalized: list[tuple[str, str, str]] = []
    for row in value:
        if isinstance(row, Mapping):
            triple = (
                _require_string(row.get("media_asset_id"), "AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID"),
                _require_string(row.get("media_version_id"), "AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID"),
                _require_string(row.get("locator_id"), "AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID"),
            )
        elif (
            isinstance(row, Sequence)
            and not isinstance(row, (str, bytes, bytearray))
            and len(row) == 3
        ):
            triple = tuple(
                _require_string(item, "AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID")
                for item in row
            )
        else:
            raise ValueError("AF_D_INSTANCE_ADMISSION_ASSET_REQUEST_INVALID")
        normalized.append(triple)  # type: ignore[arg-type]
    if len(normalized) != len(set(normalized)):
        raise ValueError("AF_D_INSTANCE_ADMISSION_DUPLICATE_ASSET_REQUEST")
    return tuple(sorted(normalized))


def _validate_type_bindings(parent: Mapping[str, Any], binding: Mapping[str, Any], manifest: Mapping[str, Any]) -> None:
    parent_registry = parent.get("type_registry")
    binding_rows = binding.get("authority_profile_bindings")
    manifest_rows = manifest.get("authority_profile_bindings")
    if not all(isinstance(rows, Mapping) for rows in (parent_registry, binding_rows, manifest_rows)):
        raise ValueError("AF_D_INSTANCE_ADMISSION_TYPE_BINDING_INVALID")
    for name, expected in _EXPECTED_TYPE_BINDINGS.items():
        for source in (parent_registry, binding_rows, manifest_rows):
            row = source.get(name)
            if not isinstance(row, Mapping):
                raise ValueError(f"AF_D_INSTANCE_ADMISSION_TYPE_BINDING_MISSING:{name}")
            actual = (row.get("type_id"), row.get("version"), row.get("authority_profile_ref"))
            if actual != expected:
                raise ValueError(f"AF_D_INSTANCE_ADMISSION_TYPE_BINDING_DRIFT:{name}")


def _load_authority() -> tuple[Mapping[str, Any], Mapping[str, Any], Mapping[str, Any], str]:
    parent = _load_json(_PARENT_PATH, "AF_D_INSTANCE_ADMISSION_PARENT_UNAVAILABLE")
    binding = _load_json(_BINDING_PATH, "AF_D_INSTANCE_ADMISSION_BINDING_UNAVAILABLE")
    manifest = _load_json(_MANIFEST_PATH, "AF_D_INSTANCE_ADMISSION_MANIFEST_UNAVAILABLE")

    parent_id = _require_string(parent.get("contract_id"), "AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")
    parent_version = _require_string(parent.get("contract_version"), "AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")
    authority_graph = _require_string(parent.get("authority_graph_version"), "AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")
    if parent.get("af_d_instance_admission_authority_epoch") != _EPOCH:
        raise ValueError("AF_D_INSTANCE_ADMISSION_AUTHORITY_EPOCH_MISMATCH")

    registration = parent.get("registered_contract_extensions", {}).get(_BINDING_ID)
    if not isinstance(registration, Mapping):
        raise ValueError("AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")
    if (
        registration.get("path") != "contracts/AF001-AF-D-INSTANCE-ADMISSION-BINDING.json"
        or registration.get("binding_version") != _BINDING_VERSION
        or registration.get("parent_contract_id") != parent_id
        or registration.get("parent_contract_version") != parent_version
        or registration.get("parent_authority_graph_version") != authority_graph
        or registration.get("af_d_instance_admission_authority_epoch") != _EPOCH
        or registration.get("authority") != "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        or registration.get("governance_issue_ref") != "#66"
        or registration.get("bounded_reference_adapter_implementation_authorized") is not True
        or registration.get("runtime_implementation_authorized") is not False
    ):
        raise ValueError("AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")

    if binding.get("binding_id") != _BINDING_ID or binding.get("binding_version") != _BINDING_VERSION:
        raise ValueError("AF_D_INSTANCE_ADMISSION_BINDING_IDENTITY_INVALID")
    binding_digest = _canonical_sha256(binding)
    if registration.get("binding_canonical_sha256") != binding_digest:
        raise ValueError("AF_D_INSTANCE_ADMISSION_BINDING_DIGEST_MISMATCH")
    parent_ref = binding.get("parent_machine_contract")
    if not isinstance(parent_ref, Mapping) or (
        parent_ref.get("contract_id") != parent_id
        or parent_ref.get("contract_version") != parent_version
        or parent_ref.get("authority_graph_version") != authority_graph
        or parent_ref.get("af_d_instance_admission_authority_epoch") != _EPOCH
    ):
        raise ValueError("AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")

    manifest_ref = binding.get("canonical_instance_manifest")
    registered_manifest = registration.get("canonical_instance_manifest")
    if not isinstance(manifest_ref, Mapping) or not isinstance(registered_manifest, Mapping):
        raise ValueError("AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")

    manifest_digest = _canonical_sha256(manifest)
    expected_manifest_fields = {
        "path": "registries/AF001-AF-D-REFERENCE-INSTANCES.json",
        "manifest_id": _MANIFEST_ID,
        "manifest_version": _MANIFEST_VERSION,
        "canonical_sha256": manifest_digest,
    }
    for field, expected in expected_manifest_fields.items():
        if manifest_ref.get(field) != expected or registered_manifest.get(field) != expected:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_DIGEST_MISMATCH")

    if manifest.get("manifest_id") != _MANIFEST_ID or manifest.get("manifest_version") != _MANIFEST_VERSION:
        raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_IDENTITY_INVALID")
    if manifest.get("status") != "CANONICAL_BOUNDED_REFERENCE_INSTANCE_MANIFEST":
        raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_STATUS_INVALID")
    manifest_parent = manifest.get("parent_machine_contract")
    if not isinstance(manifest_parent, Mapping) or (
        manifest_parent.get("contract_id") != parent_id
        or manifest_parent.get("contract_version") != parent_version
        or manifest_parent.get("authority_graph_version") != authority_graph
        or manifest_parent.get("af_d_instance_admission_authority_epoch") != _EPOCH
    ):
        raise ValueError("AF_D_INSTANCE_ADMISSION_PARENT_REGISTRATION_INVALID")

    if manifest.get("canonicalization_provenance", {}).get("historical_design_evidence_authority") != "NONAUTHORITY_INPUT_ONLY":
        raise ValueError("AF_D_INSTANCE_ADMISSION_NONAUTHORITY_EVAL_REJECTED")

    _validate_type_bindings(parent, binding, manifest)
    return parent, binding, manifest, manifest_digest


def _manifest_indexes(manifest: Mapping[str, Any]) -> tuple[set[str], set[tuple[str, str, str]]]:
    views: set[str] = set()
    for row in manifest.get("views", []):
        if not isinstance(row, Mapping):
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_VIEW_INVALID")
        view_id = _require_string(row.get("view_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_VIEW_INVALID")
        if view_id in views:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_DUPLICATE_VIEW")
        views.add(view_id)

    assets: set[str] = set()
    asset_view_refs: dict[str, str | None] = {}
    for row in manifest.get("media_assets", []):
        if not isinstance(row, Mapping):
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_ASSET_INVALID")
        asset_id = _require_string(row.get("media_asset_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_ASSET_INVALID")
        if asset_id in assets:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_DUPLICATE_ASSET")
        view_ref = row.get("view_ref_optional")
        if view_ref is not None and view_ref not in views:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_ASSET_VIEW_UNKNOWN")
        assets.add(asset_id)
        asset_view_refs[asset_id] = view_ref

    versions: dict[str, str] = {}
    for row in manifest.get("media_versions", []):
        if not isinstance(row, Mapping):
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_VERSION_INVALID")
        version_id = _require_string(row.get("media_version_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_VERSION_INVALID")
        asset_id = _require_string(row.get("media_asset_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_VERSION_INVALID")
        if version_id in versions or asset_id not in assets:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_VERSION_INVALID")
        _require_string(row.get("content_hash"), "AF_D_INSTANCE_ADMISSION_MANIFEST_VERSION_INVALID")
        versions[version_id] = asset_id

    bindings: set[tuple[str, str, str]] = set()
    locator_ids: set[str] = set()
    for row in manifest.get("locators", []):
        if not isinstance(row, Mapping):
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_LOCATOR_INVALID")
        locator_id = _require_string(row.get("locator_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_LOCATOR_INVALID")
        version_id = _require_string(row.get("media_version_id"), "AF_D_INSTANCE_ADMISSION_MANIFEST_LOCATOR_INVALID")
        if locator_id in locator_ids or version_id not in versions:
            raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_LOCATOR_INVALID")
        locator_ids.add(locator_id)
        bindings.add((versions[version_id], version_id, locator_id))

    if not views or not bindings:
        raise ValueError("AF_D_INSTANCE_ADMISSION_MANIFEST_EMPTY")
    return views, bindings


def _receipt_material(receipt: AFDInstanceAdmissionReceipt | Mapping[str, Any]) -> dict[str, Any]:
    if isinstance(receipt, AFDInstanceAdmissionReceipt):
        value = asdict(receipt)
    elif isinstance(receipt, Mapping):
        value = dict(receipt)
    else:
        raise ValueError("AF_D_INSTANCE_ADMISSION_RECEIPT_INVALID")
    value.pop("receipt_sha256", None)
    return value


def _materialize_receipt(
    requested_view_ids: Any,
    requested_asset_bindings: Any,
) -> AFDInstanceAdmissionReceipt:
    parent, binding, manifest, manifest_digest = _load_authority()
    views, bindings = _manifest_indexes(manifest)
    request_views = _normalize_view_ids(requested_view_ids)
    request_bindings = _normalize_asset_bindings(requested_asset_bindings)
    if not request_views and not request_bindings:
        raise ValueError("AF_D_INSTANCE_ADMISSION_EMPTY_REQUEST")
    for view_id in request_views:
        if view_id not in views:
            raise ValueError(f"AF_D_INSTANCE_ADMISSION_VIEW_UNKNOWN:{view_id}")
    for asset_binding in request_bindings:
        if asset_binding not in bindings:
            raise ValueError("AF_D_INSTANCE_ADMISSION_ASSET_BINDING_UNKNOWN:" + "|".join(asset_binding))

    issuer = binding.get("issuer_profile")
    if not isinstance(issuer, Mapping):
        raise ValueError("AF_D_INSTANCE_ADMISSION_ISSUER_MISMATCH")
    values = {
        "receipt_schema_id": _RECEIPT_SCHEMA_ID,
        "receipt_schema_version": _RECEIPT_SCHEMA_VERSION,
        "issuer_id": _require_string(issuer.get("issuer_id"), "AF_D_INSTANCE_ADMISSION_ISSUER_MISMATCH"),
        "issuer_version": _require_string(issuer.get("issuer_version"), "AF_D_INSTANCE_ADMISSION_ISSUER_MISMATCH"),
        "parent_contract_id": parent["contract_id"],
        "parent_contract_version": parent["contract_version"],
        "parent_authority_graph_version": parent["authority_graph_version"],
        "af_d_instance_admission_authority_epoch": _EPOCH,
        "binding_id": _BINDING_ID,
        "binding_version": _BINDING_VERSION,
        "manifest_id": _MANIFEST_ID,
        "manifest_version": _MANIFEST_VERSION,
        "manifest_sha256": manifest_digest,
        "requested_view_ids": request_views,
        "requested_asset_bindings": request_bindings,
        "admitted_view_ids": request_views,
        "admitted_asset_bindings": request_bindings,
    }
    digest = _canonical_sha256(values)
    return AFDInstanceAdmissionReceipt(**values, receipt_sha256=digest)


def issue_admission_receipt(
    *,
    requested_view_ids: Sequence[str] = (),
    requested_asset_bindings: Sequence[Any] = (),
) -> AFDInstanceAdmissionReceipt:
    """Issue derived admission evidence for identities already in canonical manifest."""
    return _materialize_receipt(requested_view_ids, requested_asset_bindings)


def verify_admission_receipt(
    receipt: AFDInstanceAdmissionReceipt | Mapping[str, Any],
) -> VerifiedAFDInstances:
    """Verify by re-deriving the complete receipt from canonical authority."""
    if isinstance(receipt, AFDInstanceAdmissionReceipt):
        supplied = asdict(receipt)
    elif isinstance(receipt, Mapping):
        supplied = dict(receipt)
    else:
        raise ValueError("AF_D_INSTANCE_ADMISSION_RECEIPT_INVALID")

    required = {
        "receipt_schema_id", "receipt_schema_version", "issuer_id", "issuer_version",
        "parent_contract_id", "parent_contract_version", "parent_authority_graph_version",
        "af_d_instance_admission_authority_epoch", "binding_id", "binding_version",
        "manifest_id", "manifest_version", "manifest_sha256", "requested_view_ids",
        "requested_asset_bindings", "admitted_view_ids", "admitted_asset_bindings",
        "receipt_sha256",
    }
    if set(supplied) != required:
        raise ValueError("AF_D_INSTANCE_ADMISSION_RECEIPT_INVALID")

    supplied_digest = supplied.get("receipt_sha256")
    if not isinstance(supplied_digest, str) or supplied_digest != _canonical_sha256(_receipt_material(supplied)):
        raise ValueError("AF_D_INSTANCE_ADMISSION_RECEIPT_DIGEST_MISMATCH")

    expected = _materialize_receipt(
        supplied.get("requested_view_ids"),
        supplied.get("requested_asset_bindings"),
    )
    expected_map = asdict(expected)
    normalized_supplied = dict(supplied)
    normalized_supplied["requested_view_ids"] = tuple(supplied["requested_view_ids"])
    normalized_supplied["admitted_view_ids"] = tuple(supplied["admitted_view_ids"])
    normalized_supplied["requested_asset_bindings"] = tuple(tuple(x) for x in supplied["requested_asset_bindings"])
    normalized_supplied["admitted_asset_bindings"] = tuple(tuple(x) for x in supplied["admitted_asset_bindings"])
    if normalized_supplied != expected_map:
        if supplied.get("issuer_id") != _ISSUER_ID or supplied.get("issuer_version") != _ISSUER_VERSION:
            raise ValueError("AF_D_INSTANCE_ADMISSION_ISSUER_MISMATCH")
        raise ValueError("AF_D_INSTANCE_ADMISSION_RECEIPT_MATERIALIZATION_MISMATCH")

    return VerifiedAFDInstances(
        view_ids=expected.admitted_view_ids,
        asset_bindings=expected.admitted_asset_bindings,
        manifest_id=expected.manifest_id,
        manifest_version=expected.manifest_version,
        manifest_sha256=expected.manifest_sha256,
        authority_epoch=expected.af_d_instance_admission_authority_epoch,
    )
