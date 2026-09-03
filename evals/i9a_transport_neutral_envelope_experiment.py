"""Transport-neutral I9A serialization experiment for OD-DIRECTOR-ADAPTER-001.

This module intentionally does not select a production transport. It proves only that
an AF-H DirectorBeatPacket reference may cross a byte boundary without the byte
envelope becoming a second authority. Verification always rebuilds the accepted I9A
packet from replay-valid sources and compares the transported material exactly.
"""
from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
import hashlib
from typing import Any

import evals.i9a_director_beat_packet_federation_mock as i9a


TRANSPORT_NEUTRAL_EXPERIMENT_ONLY = True
NO_PRODUCTION_TRANSPORT_SELECTED = True
NO_NETWORK_INTEGRATION = True
NO_PROVIDER_INTEGRATION = True
NO_RENDERER_INTEGRATION = True
NO_WORLD_MUTATION = True
NO_KNOWLEDGE_MUTATION = True
NO_STAGING_AUTHORITY = True
NO_CANONICAL_DATA_AUTHORITY = True
NO_BEARER_CAPABILITY_SEMANTICS = True

_ENVELOPE_SCHEMA = "AWRSE-I9A-TRANSPORT-NEUTRAL-ENVELOPE-EXPERIMENT/v1"
_RECEIPT_AUTHORITY = "NON_CANONICAL_I9A_TRANSPORT_CONFORMANCE_EVIDENCE_ONLY"
_EXPECTED_TOP_FIELDS = {"payload", "sha256"}
_EXPECTED_PAYLOAD_FIELDS = {
    "schema",
    "packet_type_version",
    "contract_version",
    "packet_authority_class",
    "packet_sha256",
    "protected_material_sha256",
    "reference_material",
}
_FORBIDDEN_TRANSPORT_SELECTION_FIELDS = {
    "transport",
    "transport_kind",
    "transport_selection",
    "queue",
    "endpoint",
    "url",
    "file_path",
    "service",
    "socket",
}


@dataclass(frozen=True)
class TransportNeutralVerificationReceipt:
    status: str
    envelope_sha256: str
    packet_sha256: str
    protected_material_sha256: str
    beat_id: str
    world_state_version: str
    canonical_data_authority: str
    staging_authority: str
    transport_selection_authority: str
    world_mutation_count: int
    provider_call_count: int
    authority_class: str


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _payload_for_packet(packet: i9a.DirectorBeatPacketReference) -> dict[str, Any]:
    return {
        "schema": _ENVELOPE_SCHEMA,
        "packet_type_version": packet.packet_type_version,
        "contract_version": packet.contract_version,
        "packet_authority_class": packet.authority_class,
        "packet_sha256": i9a.packet_sha256(packet),
        "protected_material_sha256": i9a.protected_material_sha256(packet),
        "reference_material": i9a._reference_material(packet),
    }


def _canonical_envelope_bytes(payload: Mapping[str, Any]) -> bytes:
    material = dict(payload)
    envelope = {
        "payload": material,
        "sha256": hashlib.sha256(
            i9a._canonical_json(material).encode("utf-8")
        ).hexdigest(),
    }
    return i9a._canonical_json(envelope).encode("utf-8")


def export_transport_neutral_envelope(
    *,
    i8c_replay_package: bytes,
    i3a_replay_package_json: str,
) -> bytes:
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_replay_package,
        i3a_replay_package_json=i3a_replay_package_json,
    )
    if packet is None:
        raise ValueError("I9A_TRANSPORT_NO_VALID_DIRECTOR_PACKET")
    return _canonical_envelope_bytes(_payload_for_packet(packet))


def _require_exact_fields(
    value: Mapping[str, Any],
    expected: set[str],
    code: str,
) -> None:
    if set(value) != expected:
        raise ValueError(code)


def verify_transport_neutral_envelope(
    *,
    envelope_bytes: bytes,
    i8c_replay_package: bytes,
    i3a_replay_package_json: str,
) -> TransportNeutralVerificationReceipt:
    envelope = i9a._strict_json_from_bytes(
        envelope_bytes,
        "I9A_TRANSPORT_ENVELOPE_JSON_INVALID",
    )
    _require_exact_fields(
        envelope,
        _EXPECTED_TOP_FIELDS,
        "I9A_TRANSPORT_ENVELOPE_FIELDS_INVALID",
    )

    payload = envelope.get("payload")
    if not isinstance(payload, Mapping):
        raise ValueError("I9A_TRANSPORT_PAYLOAD_INVALID")
    _require_exact_fields(
        payload,
        _EXPECTED_PAYLOAD_FIELDS,
        "I9A_TRANSPORT_PAYLOAD_FIELDS_INVALID",
    )
    if _FORBIDDEN_TRANSPORT_SELECTION_FIELDS.intersection(payload):
        raise ValueError("I9A_TRANSPORT_SELECTION_METADATA_FORBIDDEN")

    supplied_digest = envelope.get("sha256")
    if not isinstance(supplied_digest, str) or len(supplied_digest) != 64:
        raise ValueError("I9A_TRANSPORT_ENVELOPE_DIGEST_INVALID")
    expected_digest = hashlib.sha256(
        i9a._canonical_json(dict(payload)).encode("utf-8")
    ).hexdigest()
    if supplied_digest != expected_digest:
        raise ValueError("I9A_TRANSPORT_ENVELOPE_DIGEST_MISMATCH")

    if payload.get("schema") != _ENVELOPE_SCHEMA:
        raise ValueError("I9A_TRANSPORT_ENVELOPE_SCHEMA_UNSUPPORTED")

    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_replay_package,
        i3a_replay_package_json=i3a_replay_package_json,
    )
    if packet is None:
        raise ValueError("I9A_TRANSPORT_NO_VALID_DIRECTOR_PACKET")

    if payload.get("packet_type_version") != packet.packet_type_version:
        raise ValueError("I9A_TRANSPORT_PACKET_TYPE_VERSION_MISMATCH")
    if payload.get("contract_version") != packet.contract_version:
        raise ValueError("I9A_TRANSPORT_CONTRACT_VERSION_MISMATCH")
    if payload.get("packet_authority_class") != packet.authority_class:
        raise ValueError("I9A_TRANSPORT_PACKET_AUTHORITY_CLASS_MISMATCH")

    rebuilt_packet_sha256 = i9a.packet_sha256(packet)
    rebuilt_protected_sha256 = i9a.protected_material_sha256(packet)
    if payload.get("packet_sha256") != rebuilt_packet_sha256:
        raise ValueError("I9A_TRANSPORT_PACKET_DIGEST_MISMATCH")
    if payload.get("protected_material_sha256") != rebuilt_protected_sha256:
        raise ValueError("I9A_TRANSPORT_PROTECTED_MATERIAL_DIGEST_MISMATCH")

    transported_reference = payload.get("reference_material")
    if not isinstance(transported_reference, Mapping):
        raise ValueError("I9A_TRANSPORT_REFERENCE_MATERIAL_INVALID")
    rebuilt_reference = i9a._reference_material(packet)
    if transported_reference != rebuilt_reference:
        raise ValueError("I9A_TRANSPORT_REFERENCE_MATERIAL_MISMATCH")

    return TransportNeutralVerificationReceipt(
        status="TRANSPORT_NEUTRAL_ENVELOPE_REPLAY_VERIFIED",
        envelope_sha256=_sha256_bytes(envelope_bytes),
        packet_sha256=rebuilt_packet_sha256,
        protected_material_sha256=rebuilt_protected_sha256,
        beat_id=packet.beat_id,
        world_state_version=packet.world_state_version,
        canonical_data_authority="NONE",
        staging_authority="NONE",
        transport_selection_authority="NONE",
        world_mutation_count=0,
        provider_call_count=0,
        authority_class=_RECEIPT_AUTHORITY,
    )
