from __future__ import annotations

import base64
import hashlib
import hmac
import json
from collections.abc import Mapping
from dataclasses import dataclass, field
from typing import Any

from .engine import SimulationEngine
from .model import Event, WorldBaseline, WorldState, _encode_world_snapshot, thaw_value


PERSISTENCE_PROFILE_ID = "AWRSE_R003_I1A_SOLO_REPLAY_PACKAGE"
PERSISTENCE_PROFILE_VERSION = "1.0.0"
PERSISTENCE_SCOPE = "SOLO"
LEGACY_EVENT_PROFILE_ID = "LEGACY_R001_R002_EVENT_PROFILE"
BASELINE_PAYLOAD_ENCODING = "BASE64"

_EVENT_FIELDS = frozenset(
    {
        "event_id",
        "event_type",
        "actor_id",
        "scene_id",
        "baseline_version",
        "payload",
        "caused_by_action_id",
    }
)
_ENVELOPE_FIELDS = frozenset(
    {
        "profile_id",
        "profile_version",
        "scope",
        "world_id",
        "baseline_version",
        "baseline_payload_encoding",
        "baseline_payload",
        "baseline_integrity_digest",
        "event_profile_id",
        "ordered_events",
        "source_event_count",
        "expected_state_version",
        "event_sequence_digest",
        "package_digest",
    }
)


@dataclass(frozen=True)
class SoloReplayEvidence:
    """Validated replay evidence decoded from a persistence package.

    This is not a materialized-world authority. Rehydration must still pass the
    pristine baseline and ordered legacy events through SimulationEngine.replay.
    """

    world_id: str
    baseline_version: str
    baseline: WorldBaseline = field(repr=False)
    events: tuple[Event, ...]
    expected_state_version: int
    event_sequence_digest: str
    package_digest: str


def _canonical_json_bytes(value: Any) -> bytes:
    try:
        return json.dumps(
            value,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise ValueError("PERSISTENCE_VALUE_NOT_CANONICAL_JSON") from exc


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _require_nonempty_string(value: Any, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise ValueError(code)
    return value


def _require_nonnegative_int(value: Any, code: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise ValueError(code)
    return value


def _event_to_record(event: Event) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "scene_id": event.scene_id,
        "baseline_version": event.baseline_version,
        "payload": thaw_value(event.payload),
        "caused_by_action_id": event.caused_by_action_id,
    }


def _event_from_record(record: Any, baseline_version: str) -> Event:
    if not isinstance(record, Mapping) or set(record) != _EVENT_FIELDS:
        raise ValueError("MALFORMED_LEGACY_EVENT_RECORD")

    event_id = _require_nonempty_string(record["event_id"], "EVENT_ID_REQUIRED")
    event_type = _require_nonempty_string(record["event_type"], "EVENT_TYPE_REQUIRED")
    scene_id = _require_nonempty_string(record["scene_id"], "EVENT_SCENE_REQUIRED")
    record_baseline = _require_nonempty_string(
        record["baseline_version"], "EVENT_BASELINE_VERSION_REQUIRED"
    )
    if record_baseline != baseline_version:
        raise ValueError("EVENT_BASELINE_VERSION_MISMATCH")

    actor_id = record["actor_id"]
    if actor_id is not None and not isinstance(actor_id, str):
        raise ValueError("EVENT_ACTOR_ID_INVALID")
    caused_by_action_id = record["caused_by_action_id"]
    if caused_by_action_id is not None and not isinstance(caused_by_action_id, str):
        raise ValueError("EVENT_CAUSED_BY_ACTION_ID_INVALID")
    payload = record["payload"]
    if not isinstance(payload, Mapping):
        raise ValueError("EVENT_PAYLOAD_MAPPING_REQUIRED")

    return Event(
        event_id=event_id,
        event_type=event_type,
        actor_id=actor_id,
        scene_id=scene_id,
        baseline_version=record_baseline,
        payload=dict(payload),
        caused_by_action_id=caused_by_action_id,
    )


def _package_digest(data_without_digest: Mapping[str, Any]) -> str:
    return _sha256(_canonical_json_bytes(dict(data_without_digest)))


def export_solo_replay_package(baseline: WorldBaseline, world: WorldState) -> bytes:
    """Export authoritative replay evidence, never the current projection itself."""

    if not isinstance(baseline, WorldBaseline) or not isinstance(world, WorldState):
        raise TypeError("BASELINE_AND_WORLD_REQUIRED")

    pristine = baseline.instantiate()
    if pristine.event_log or pristine.committed_event_ids or pristine.state_version != 0:
        raise ValueError("BASELINE_MUST_BE_PRISTINE")
    if pristine.world_id != world.world_id:
        raise ValueError("WORLD_ID_MISMATCH")
    if baseline.baseline_version != world.baseline_version:
        raise ValueError("BASELINE_VERSION_MISMATCH")

    events = tuple(world.event_log)
    event_ids = tuple(event.event_id for event in events)
    if any(not event_id for event_id in event_ids):
        raise ValueError("EVENT_ID_REQUIRED")
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("DUPLICATE_COMMITTED_EVENT_ID")
    if set(event_ids) != set(world.committed_event_ids):
        raise ValueError("CANONICAL_EVENT_INDEX_MISMATCH")
    if world.state_version != len(events):
        raise ValueError("SOURCE_STATE_VERSION_EVENT_COUNT_MISMATCH")
    if any(event.baseline_version != baseline.baseline_version for event in events):
        raise ValueError("EVENT_BASELINE_VERSION_MISMATCH")

    # The export path verifies the supplied projection against replay evidence,
    # but does not serialize that projection as authority.
    replayed = SimulationEngine().replay(baseline, events)
    if _encode_world_snapshot(replayed) != _encode_world_snapshot(world):
        raise ValueError("SOURCE_PROJECTION_DOES_NOT_MATCH_REPLAY_EVIDENCE")

    baseline_payload = baseline._snapshot
    baseline_digest = _sha256(baseline_payload)
    if not hmac.compare_digest(baseline_digest, baseline.snapshot_digest):
        raise ValueError("BASELINE_SNAPSHOT_INTEGRITY_FAILURE")

    ordered_events = [_event_to_record(event) for event in events]
    event_sequence_digest = _sha256(_canonical_json_bytes(ordered_events))
    envelope: dict[str, Any] = {
        "profile_id": PERSISTENCE_PROFILE_ID,
        "profile_version": PERSISTENCE_PROFILE_VERSION,
        "scope": PERSISTENCE_SCOPE,
        "world_id": world.world_id,
        "baseline_version": baseline.baseline_version,
        "baseline_payload_encoding": BASELINE_PAYLOAD_ENCODING,
        "baseline_payload": base64.b64encode(baseline_payload).decode("ascii"),
        "baseline_integrity_digest": baseline.snapshot_digest,
        "event_profile_id": LEGACY_EVENT_PROFILE_ID,
        "ordered_events": ordered_events,
        "source_event_count": len(events),
        "expected_state_version": world.state_version,
        "event_sequence_digest": event_sequence_digest,
    }
    envelope["package_digest"] = _package_digest(envelope)
    return _canonical_json_bytes(envelope)


def import_solo_replay_package(package: bytes | bytearray | memoryview) -> SoloReplayEvidence:
    """Decode and integrity-check replay evidence without trusting projection state."""

    if not isinstance(package, (bytes, bytearray, memoryview)):
        raise TypeError("PERSISTENCE_PACKAGE_BYTES_REQUIRED")
    try:
        decoded = json.loads(bytes(package).decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("PERSISTENCE_PACKAGE_JSON_INVALID") from exc
    if not isinstance(decoded, dict) or set(decoded) != _ENVELOPE_FIELDS:
        raise ValueError("PERSISTENCE_ENVELOPE_SCHEMA_MISMATCH")

    supplied_package_digest = _require_nonempty_string(
        decoded["package_digest"], "PACKAGE_DIGEST_REQUIRED"
    )
    without_digest = dict(decoded)
    del without_digest["package_digest"]
    actual_package_digest = _package_digest(without_digest)
    if not hmac.compare_digest(actual_package_digest, supplied_package_digest):
        raise ValueError("PERSISTENCE_PACKAGE_INTEGRITY_FAILURE")

    if decoded["profile_id"] != PERSISTENCE_PROFILE_ID:
        raise ValueError("UNSUPPORTED_PERSISTENCE_PROFILE")
    if decoded["profile_version"] != PERSISTENCE_PROFILE_VERSION:
        raise ValueError("UNSUPPORTED_PERSISTENCE_PROFILE_VERSION")
    if decoded["scope"] != PERSISTENCE_SCOPE:
        raise ValueError("UNSUPPORTED_PERSISTENCE_SCOPE")
    if decoded["event_profile_id"] != LEGACY_EVENT_PROFILE_ID:
        raise ValueError("UNSUPPORTED_EVENT_PROFILE")
    if decoded["baseline_payload_encoding"] != BASELINE_PAYLOAD_ENCODING:
        raise ValueError("UNSUPPORTED_BASELINE_PAYLOAD_ENCODING")

    world_id = _require_nonempty_string(decoded["world_id"], "WORLD_ID_REQUIRED")
    baseline_version = _require_nonempty_string(
        decoded["baseline_version"], "BASELINE_VERSION_REQUIRED"
    )
    baseline_digest = _require_nonempty_string(
        decoded["baseline_integrity_digest"], "BASELINE_DIGEST_REQUIRED"
    )
    baseline_payload_text = _require_nonempty_string(
        decoded["baseline_payload"], "BASELINE_PAYLOAD_REQUIRED"
    )
    try:
        baseline_payload = base64.b64decode(
            baseline_payload_text.encode("ascii"), validate=True
        )
    except (UnicodeEncodeError, ValueError) as exc:
        raise ValueError("BASELINE_PAYLOAD_ENCODING_INVALID") from exc
    if not hmac.compare_digest(_sha256(baseline_payload), baseline_digest):
        raise ValueError("BASELINE_SNAPSHOT_INTEGRITY_FAILURE")

    baseline = WorldBaseline(
        baseline_version=baseline_version,
        snapshot_digest=baseline_digest,
        _snapshot=baseline_payload,
    )
    pristine = baseline.instantiate()
    if pristine.event_log or pristine.committed_event_ids or pristine.state_version != 0:
        raise ValueError("BASELINE_MUST_BE_PRISTINE")
    if pristine.world_id != world_id:
        raise ValueError("WORLD_ID_MISMATCH")
    if pristine.baseline_version != baseline_version:
        raise ValueError("BASELINE_VERSION_MISMATCH")

    raw_events = decoded["ordered_events"]
    if not isinstance(raw_events, list):
        raise ValueError("ORDERED_EVENT_SEQUENCE_REQUIRED")
    expected_event_sequence_digest = _require_nonempty_string(
        decoded["event_sequence_digest"], "EVENT_SEQUENCE_DIGEST_REQUIRED"
    )
    actual_event_sequence_digest = _sha256(_canonical_json_bytes(raw_events))
    if not hmac.compare_digest(
        actual_event_sequence_digest, expected_event_sequence_digest
    ):
        raise ValueError("EVENT_SEQUENCE_INTEGRITY_FAILURE")

    source_event_count = _require_nonnegative_int(
        decoded["source_event_count"], "SOURCE_EVENT_COUNT_INVALID"
    )
    expected_state_version = _require_nonnegative_int(
        decoded["expected_state_version"], "EXPECTED_STATE_VERSION_INVALID"
    )
    if source_event_count != len(raw_events):
        raise ValueError("SOURCE_EVENT_COUNT_MISMATCH")
    if expected_state_version != source_event_count:
        raise ValueError("EXPECTED_STATE_VERSION_EVENT_COUNT_MISMATCH")

    events = tuple(_event_from_record(record, baseline_version) for record in raw_events)
    event_ids = tuple(event.event_id for event in events)
    if len(set(event_ids)) != len(event_ids):
        raise ValueError("DUPLICATE_COMMITTED_EVENT_ID")

    return SoloReplayEvidence(
        world_id=world_id,
        baseline_version=baseline_version,
        baseline=baseline,
        events=events,
        expected_state_version=expected_state_version,
        event_sequence_digest=expected_event_sequence_digest,
        package_digest=supplied_package_digest,
    )


def rehydrate_solo_replay_package(
    package: bytes | bytearray | memoryview,
    *,
    engine: SimulationEngine | None = None,
) -> WorldState:
    """Rebuild a sealed canonical projection through the accepted replay path."""

    evidence = import_solo_replay_package(package)
    replay_engine = SimulationEngine() if engine is None else engine
    rebuilt = replay_engine.replay(evidence.baseline, evidence.events)

    if rebuilt.world_id != evidence.world_id:
        raise ValueError("REHYDRATED_WORLD_ID_MISMATCH")
    if rebuilt.baseline_version != evidence.baseline_version:
        raise ValueError("REHYDRATED_BASELINE_VERSION_MISMATCH")
    if rebuilt.state_version != evidence.expected_state_version:
        raise ValueError("REHYDRATED_STATE_VERSION_MISMATCH")
    if len(rebuilt.event_log) != len(evidence.events):
        raise ValueError("REHYDRATED_EVENT_COUNT_MISMATCH")
    if tuple(event.event_id for event in rebuilt.event_log) != tuple(
        event.event_id for event in evidence.events
    ):
        raise ValueError("REHYDRATED_EVENT_ORDER_MISMATCH")
    if set(rebuilt.committed_event_ids) != {
        event.event_id for event in evidence.events
    }:
        raise ValueError("REHYDRATED_EVENT_INDEX_MISMATCH")
    if not rebuilt.is_live:
        raise ValueError("REHYDRATED_STATE_MUST_BE_LIVE_AND_READ_ONLY")
    return rebuilt
