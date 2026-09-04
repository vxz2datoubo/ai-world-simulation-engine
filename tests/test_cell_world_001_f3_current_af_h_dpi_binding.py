import dataclasses
import hashlib
import importlib.util
import inspect
import json
from pathlib import Path

import pytest

import evals.i9a_director_beat_packet_federation_mock as i9a
import evals.i9a_transport_neutral_envelope_experiment as transport


def _load_fixture_module():
    path = Path(__file__).with_name("test_i9a_director_beat_packet_federation_mock.py")
    spec = importlib.util.spec_from_file_location("_cell_world_f3_i9a_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CELL_WORLD_F3_I9A_FIXTURE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_fixture_module()


def _sources():
    i8c_package, i3a_package, *_ = FIXTURE.make_packages()
    return i8c_package, i3a_package


def _packet():
    i8c_package, i3a_package = _sources()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert packet is not None
    return packet


def _canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def test_current_af_h_packet_and_dpi_are_exactly_correlated_and_non_runtime():
    packet = _packet()
    dpi = packet.dramatic_presentation_intent

    assert i9a.NO_WORLD_INSTANCE_RUNTIME_AUTHORITY is True
    assert i9a.NO_DPI_RUNTIME_AUTHORITY is True
    assert set(i9a._frozen_packet_material(packet)) == i9a._EXPECTED_PACKET_FIELDS
    assert set(i9a._dpi_material(dpi)) == i9a._EXPECTED_DPI_FIELDS
    assert packet.world_instance_id == packet.source_world_id
    assert packet.dramatic_presentation_intent_ref == dpi.intent_id
    assert dpi.parent_director_beat_packet_ref == i9a._parent_packet_ref(packet.beat_id)
    assert dpi.world_instance_id == packet.world_instance_id
    assert dpi.world_state_version == packet.world_state_version
    assert dpi.confirmed_event_refs == packet.confirmed_event_refs
    assert dpi.confirmed_event_set_digest == i9a._confirmed_event_set_digest(
        packet.confirmed_event_refs
    )
    assert dpi.causal_emphasis_refs == ()
    assert dpi.allowed_information_refs == ()
    assert dpi.authority_class == "NON_CANONICAL_I9A_DPI_INTERFACE_EVIDENCE_ONLY"


def test_world_instance_and_dpi_are_derived_not_caller_supplied():
    params = set(inspect.signature(i9a.build_director_beat_packet_reference).parameters)
    assert params == {"i8c_replay_package", "i3a_replay_package_json"}
    assert "world_instance_id" not in params
    assert "dramatic_presentation_intent" not in params
    assert "dramatic_presentation_intent_ref" not in params


@pytest.mark.parametrize(
    "mutator, expected",
    [
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, parent_director_beat_packet_ref="DIRECTOR-BEAT-PACKET:FORGED"
            ),
            "I9A_DPI_BACK_REFERENCE_MISMATCH",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, world_instance_id="WORLD-INSTANCE-FORGED"
            ),
            "I9A_DPI_WORLD_INSTANCE_MISMATCH",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, world_state_version="FORGED:999"
            ),
            "I9A_DPI_WORLD_STATE_VERSION_MISMATCH",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, confirmed_event_refs=tuple(reversed(dpi.confirmed_event_refs))
            ),
            "I9A_DPI_CONFIRMED_EVENT_REFS_MISMATCH",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, confirmed_event_set_digest="0" * 64
            ),
            "I9A_DPI_CONFIRMED_EVENT_SET_DIGEST_MISMATCH",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, causal_emphasis_refs=("EVENT-NOT-CONFIRMED",)
            ),
            "I9A_DPI_CAUSAL_EMPHASIS_OUTSIDE_CONFIRMED_EVENTS",
        ),
        (
            lambda packet, dpi: dataclasses.replace(
                dpi, allowed_information_refs=("KNOWLEDGE-NOT-AVAILABLE",)
            ),
            "I9A_DPI_ALLOWED_INFORMATION_SUPERSET",
        ),
    ],
)
def test_dpi_correlation_attacks_fail_closed_before_hashing(mutator, expected):
    packet = _packet()
    forged_dpi = mutator(packet, packet.dramatic_presentation_intent)
    forged_packet = dataclasses.replace(
        packet, dramatic_presentation_intent=forged_dpi
    )
    with pytest.raises(ValueError, match=expected):
        i9a.packet_sha256(forged_packet)


def test_packet_dpi_reference_substitution_fails_closed():
    packet = _packet()
    forged = dataclasses.replace(
        packet, dramatic_presentation_intent_ref="DPI:FORGED"
    )
    with pytest.raises(ValueError, match="I9A_DPI_PARENT_REFERENCE_MISMATCH"):
        i9a.protected_material_sha256(forged)


def test_packet_world_instance_substitution_cannot_detach_from_replay_world():
    packet = _packet()
    forged_dpi = dataclasses.replace(
        packet.dramatic_presentation_intent,
        world_instance_id="WORLD-INSTANCE-FORGED",
    )
    forged = dataclasses.replace(
        packet,
        world_instance_id="WORLD-INSTANCE-FORGED",
        dramatic_presentation_intent=forged_dpi,
    )
    with pytest.raises(ValueError, match="I9A_WORLD_INSTANCE_REFERENCE_SOURCE_MISMATCH"):
        i9a.packet_sha256(forged)


def test_recomputed_outer_digest_cannot_smuggle_forged_dpi_material():
    i8c_package, i3a_package = _sources()
    envelope_bytes = transport.export_transport_neutral_envelope(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    envelope = json.loads(envelope_bytes.decode("utf-8"))
    envelope["payload"]["reference_material"]["dramatic_presentation_intent"][
        "allowed_information_refs"
    ] = ["KNOWLEDGE-FORGED"]
    envelope["sha256"] = hashlib.sha256(
        _canonical_json(envelope["payload"]).encode("utf-8")
    ).hexdigest()
    forged_bytes = _canonical_json(envelope).encode("utf-8")

    with pytest.raises(ValueError, match="I9A_TRANSPORT_REFERENCE_MATERIAL_MISMATCH"):
        transport.verify_transport_neutral_envelope(
            envelope_bytes=forged_bytes,
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_current_canonical_dpi_correlation_rule_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(i9a._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["director_handoff_extension_binding"]["correlation_rules"].pop()
    path = tmp_path / "contract-dpi-rule-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package = _sources()

    with pytest.raises(ValueError, match="I9A_DPI_CORRELATION_RULES_DRIFT"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_dpi_runtime_activation_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(i9a._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["director_handoff_extension_binding"]["runtime_implementation_authorized"] = True
    path = tmp_path / "contract-dpi-runtime-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package = _sources()

    with pytest.raises(
        ValueError,
        match="I9A_DPI_BINDING_DRIFT:runtime_implementation_authorized",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_dpi_field_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(i9a._CONTRACT_PATH.read_text(encoding="utf-8"))
    contract["type_registry"]["DramaticPresentationIntent"]["fields"].remove(
        "allowed_information_refs"
    )
    path = tmp_path / "contract-dpi-field-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package = _sources()

    with pytest.raises(ValueError, match="I9A_DPI_FIELDS_DRIFT"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )
