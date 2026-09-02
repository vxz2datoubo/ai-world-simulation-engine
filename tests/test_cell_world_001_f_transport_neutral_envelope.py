import copy
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

import evals.i9a_director_beat_packet_federation_mock as i9a
import evals.i9a_transport_neutral_envelope_experiment as transport


def _load_accepted_i9a_fixture_module():
    path = Path(__file__).with_name("test_i9a_director_beat_packet_federation_mock.py")
    spec = importlib.util.spec_from_file_location("_cell_world_f_i9a_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CELL_WORLD_F_I9A_FIXTURE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_accepted_i9a_fixture_module()


def _sources(**kwargs):
    i8c_package, i3a_package, *_ = FIXTURE.make_packages(**kwargs)
    return i8c_package, i3a_package


def _decode(envelope_bytes):
    return json.loads(envelope_bytes.decode("utf-8"))


def _reencode(envelope):
    payload = envelope["payload"]
    envelope["sha256"] = hashlib.sha256(
        i9a._canonical_json(payload).encode("utf-8")
    ).hexdigest()
    return i9a._canonical_json(envelope).encode("utf-8")


def test_scope_locks_are_transport_neutral_and_non_authoritative():
    assert transport.TRANSPORT_NEUTRAL_EXPERIMENT_ONLY is True
    assert transport.NO_PRODUCTION_TRANSPORT_SELECTED is True
    assert transport.NO_NETWORK_INTEGRATION is True
    assert transport.NO_PROVIDER_INTEGRATION is True
    assert transport.NO_RENDERER_INTEGRATION is True
    assert transport.NO_WORLD_MUTATION is True
    assert transport.NO_KNOWLEDGE_MUTATION is True
    assert transport.NO_STAGING_AUTHORITY is True
    assert transport.NO_CANONICAL_DATA_AUTHORITY is True
    assert transport.NO_BEARER_CAPABILITY_SEMANTICS is True


def test_same_replay_sources_export_byte_identical_envelope_and_verify_round_trip():
    i8c_package, i3a_package = _sources()
    envelope_a = transport.export_transport_neutral_envelope(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    envelope_b = transport.export_transport_neutral_envelope(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert envelope_a == envelope_b

    receipt = transport.verify_transport_neutral_envelope(
        envelope_bytes=envelope_a,
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert packet is not None
    assert receipt.status == "TRANSPORT_NEUTRAL_ENVELOPE_REPLAY_VERIFIED"
    assert receipt.packet_sha256 == i9a.packet_sha256(packet)
    assert receipt.protected_material_sha256 == i9a.protected_material_sha256(packet)
    assert receipt.beat_id == packet.beat_id
    assert receipt.world_state_version == packet.world_state_version
    assert receipt.canonical_data_authority == "NONE"
    assert receipt.staging_authority == "NONE"
    assert receipt.transport_selection_authority == "NONE"
    assert receipt.world_mutation_count == 0
    assert receipt.provider_call_count == 0
    assert receipt.authority_class == (
        "NON_CANONICAL_I9A_TRANSPORT_CONFORMANCE_EVIDENCE_ONLY"
    )


def test_envelope_carries_no_production_transport_selection_metadata():
    i8c_package, i3a_package = _sources()
    envelope = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )
    assert set(envelope) == {"payload", "sha256"}
    assert set(envelope["payload"]) == {
        "schema",
        "packet_type_version",
        "contract_version",
        "packet_authority_class",
        "packet_sha256",
        "protected_material_sha256",
        "reference_material",
    }
    encoded_keys = set(envelope["payload"])
    assert not encoded_keys.intersection(
        {
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
    )


@pytest.mark.parametrize(
    "mutator, expected",
    [
        (
            lambda envelope: envelope["payload"].__setitem__(
                "schema", "AWRSE-I9A-TRANSPORT-NEUTRAL-ENVELOPE-EXPERIMENT/v2"
            ),
            "I9A_TRANSPORT_ENVELOPE_SCHEMA_UNSUPPORTED",
        ),
        (
            lambda envelope: envelope["payload"].__setitem__(
                "packet_type_version", "9.9.9-unreviewed"
            ),
            "I9A_TRANSPORT_PACKET_TYPE_VERSION_MISMATCH",
        ),
        (
            lambda envelope: envelope["payload"].__setitem__(
                "contract_version", "99.0.0-unreviewed"
            ),
            "I9A_TRANSPORT_CONTRACT_VERSION_MISMATCH",
        ),
        (
            lambda envelope: envelope["payload"].__setitem__(
                "packet_authority_class", "CANONICAL_WORLD_AUTHORITY"
            ),
            "I9A_TRANSPORT_PACKET_AUTHORITY_CLASS_MISMATCH",
        ),
    ],
)
def test_version_and_authority_skew_fail_closed_even_with_recomputed_outer_digest(
    mutator, expected
):
    i8c_package, i3a_package = _sources()
    envelope = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )
    mutator(envelope)
    forged = _reencode(envelope)
    with pytest.raises(ValueError, match=expected):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=forged,
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_tampered_reference_material_fails_after_attacker_recomputes_outer_digest():
    i8c_package, i3a_package = _sources()
    envelope = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )
    envelope["payload"]["reference_material"]["packet"]["presentation_goal"] = (
        "FORGED_FORCE_OUTCOME"
    )
    forged = _reencode(envelope)
    with pytest.raises(ValueError, match="I9A_TRANSPORT_REFERENCE_MATERIAL_MISMATCH"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=forged,
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_packet_and_protected_digests_cannot_be_forged_with_outer_digest_refresh():
    i8c_package, i3a_package = _sources()
    for key, expected in (
        ("packet_sha256", "I9A_TRANSPORT_PACKET_DIGEST_MISMATCH"),
        (
            "protected_material_sha256",
            "I9A_TRANSPORT_PROTECTED_MATERIAL_DIGEST_MISMATCH",
        ),
    ):
        envelope = _decode(
            transport.export_transport_neutral_envelope(
                i8c_replay_package=i8c_package,
                i3a_replay_package_json=i3a_package,
            )
        )
        envelope["payload"][key] = "0" * 64
        forged = _reencode(envelope)
        with pytest.raises(ValueError, match=expected):
            transport.verify_transport_neutral_envelope(
                envelope_bytes=forged,
                i8c_replay_package=i8c_package,
                i3a_replay_package_json=i3a_package,
            )


def test_cross_source_substitution_fails_against_rebuilt_packet():
    i8c_a, i3a_a = _sources(later_target=FIXTURE.CRATE)
    i8c_b, i3a_b = _sources(later_target=FIXTURE.CRATE_ALT)
    assert i3a_a == i3a_b
    envelope = transport.export_transport_neutral_envelope(
        i8c_replay_package=i8c_a,
        i3a_replay_package_json=i3a_a,
    )
    with pytest.raises(
        ValueError,
        match="I9A_TRANSPORT_PACKET_DIGEST_MISMATCH|I9A_TRANSPORT_REFERENCE_MATERIAL_MISMATCH",
    ):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=envelope,
            i8c_replay_package=i8c_b,
            i3a_replay_package_json=i3a_b,
        )


@pytest.mark.parametrize(
    "bad_bytes, expected",
    [
        (b"{", "I9A_TRANSPORT_ENVELOPE_JSON_INVALID"),
        (b"\xff\xfe", "I9A_TRANSPORT_ENVELOPE_JSON_INVALID"),
        (
            b'{"payload":{},"payload":{},"sha256":"x"}',
            "I9A_JSON_DUPLICATE_KEY:payload",
        ),
        (
            b'{"payload":{"x":NaN},"sha256":"x"}',
            "I9A_JSON_NONFINITE:NaN",
        ),
    ],
)
def test_malformed_duplicate_and_nonfinite_envelopes_fail_closed(bad_bytes, expected):
    i8c_package, i3a_package = _sources()
    with pytest.raises(ValueError, match=expected):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=bad_bytes,
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_missing_or_extra_top_and_payload_fields_fail_closed():
    i8c_package, i3a_package = _sources()
    original = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )

    top_extra = copy.deepcopy(original)
    top_extra["transport"] = "queue"
    with pytest.raises(ValueError, match="I9A_TRANSPORT_ENVELOPE_FIELDS_INVALID"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=i9a._canonical_json(top_extra).encode("utf-8"),
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )

    payload_extra = copy.deepcopy(original)
    payload_extra["payload"]["transport"] = "service-api"
    with pytest.raises(ValueError, match="I9A_TRANSPORT_PAYLOAD_FIELDS_INVALID"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=_reencode(payload_extra),
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )

    payload_missing = copy.deepcopy(original)
    del payload_missing["payload"]["reference_material"]
    with pytest.raises(ValueError, match="I9A_TRANSPORT_PAYLOAD_FIELDS_INVALID"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=_reencode(payload_missing),
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_envelope_digest_mismatch_fails_before_any_source_promotion():
    i8c_package, i3a_package = _sources()
    envelope = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )
    envelope["sha256"] = "f" * 64
    with pytest.raises(ValueError, match="I9A_TRANSPORT_ENVELOPE_DIGEST_MISMATCH"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=i9a._canonical_json(envelope).encode("utf-8"),
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_failure_isolation_keeps_sources_byte_identical_and_module_offline():
    i8c_package, i3a_package = _sources()
    before_i8c = bytes(i8c_package)
    before_i3a = str(i3a_package)
    envelope = _decode(
        transport.export_transport_neutral_envelope(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
    )
    envelope["payload"]["reference_material"]["authority_class"] = (
        "FORGED_CANONICAL_AUTHORITY"
    )
    forged = _reencode(envelope)

    with pytest.raises(ValueError, match="I9A_TRANSPORT_REFERENCE_MATERIAL_MISMATCH"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=forged,
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )

    assert i8c_package == before_i8c
    assert i3a_package == before_i3a
    source = inspect.getsource(transport)
    assert "import requests" not in source
    assert "import urllib" not in source
    assert "import socket" not in source
    assert "import subprocess" not in source
    assert "open(" not in source
    assert "Path(" not in source
