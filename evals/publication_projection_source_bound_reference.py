from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from typing import Any

from runtime.awrse import import_solo_replay_package, rehydrate_solo_replay_package


EVAL_ID = "CELL-WORLD-001-G2-SOURCE-BOUND-PUBLICATION/v1"
POLICY_VERSION = "POLICY-NEUTRAL-PUBLICATION-EXPERIMENT/v1"
SUPPORTED_AUDIENCES = frozenset(
    {
        "OMNISCIENT_SPECTATOR_CANDIDATE",
        "DELAYED_REVEAL_CANDIDATE",
        "STRICT_PLAYER_EQUIVALENT",
    }
)


@dataclass(frozen=True)
class SourceBoundPublicationEvidence:
    world_id: str
    baseline_version: str
    expected_state_version: int
    event_sequence_digest: str
    package_digest: str
    source_event_refs: tuple[str, ...]
    source_information_refs: tuple[str, ...]
    source_material_digests: tuple[str, ...]
    canonical_data_authority: str = "NONE"
    publication_authority: str = "NONE"
    player_knowledge_authority: str = "NONE"
    npc_knowledge_authority: str = "NONE"
    current_observation_authority: str = "NONE"


@dataclass(frozen=True)
class PublicationProjectionCandidate:
    publication_id: str
    audience_class: str
    source_event_refs: tuple[str, ...]
    allowed_information_refs: tuple[str, ...]
    redacted_information_refs: tuple[str, ...]
    presentation_refs: tuple[str, ...]
    policy_version: str
    source_evidence_digest: str
    canonical_data_authority: str = "NONE"
    staging_authority: str = "NONE"
    knowledge_write_authority: str = "NONE"
    world_mutation_authority: str = "NONE"
    status: str = "SOURCE_BOUND_PUBLICATION_CANDIDATE_ONLY"


def _jsonable(value: Any) -> Any:
    if isinstance(value, Mapping):
        return {str(key): _jsonable(item) for key, item in sorted(value.items(), key=lambda kv: str(kv[0]))}
    if isinstance(value, (list, tuple)):
        return [_jsonable(item) for item in value]
    if isinstance(value, (set, frozenset)):
        return sorted((_jsonable(item) for item in value), key=repr)
    if isinstance(value, Enum):
        return value.value
    return value


def _canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(
        _jsonable(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: Any) -> str:
    return hashlib.sha256(_canonical_json_bytes(value)).hexdigest()


def _event_material(event: Any) -> dict[str, Any]:
    return {
        "event_id": event.event_id,
        "event_type": event.event_type,
        "actor_id": event.actor_id,
        "scene_id": event.scene_id,
        "baseline_version": event.baseline_version,
        "payload": _jsonable(event.payload),
        "caused_by_action_id": event.caused_by_action_id,
    }


def _information_ref(event: Any) -> tuple[str, str]:
    material_digest = _sha256(_event_material(event))
    return f"EVENT_FACT:{event.event_id}:{material_digest}", material_digest


def derive_source_bound_publication_evidence(
    solo_replay_package: bytes | bytearray | memoryview,
) -> SourceBoundPublicationEvidence:
    """Derive read-only publication evidence from canonical replay evidence.

    Caller-supplied positive information/source refs are intentionally absent from
    this API. Import + replay validation is the provenance boundary. The returned
    receipt is evidence for this eval only; it is not a bearer capability and has
    no authority to mutate world, knowledge, observation, or publication policy.
    """

    evidence = import_solo_replay_package(solo_replay_package)
    rebuilt = rehydrate_solo_replay_package(solo_replay_package)

    rebuilt_event_ids = tuple(event.event_id for event in rebuilt.event_log)
    evidence_event_ids = tuple(event.event_id for event in evidence.events)
    if rebuilt_event_ids != evidence_event_ids:
        raise ValueError("REPLAY_EVENT_IDENTITY_MISMATCH")
    if rebuilt.state_version != evidence.expected_state_version:
        raise ValueError("REPLAY_STATE_VERSION_MISMATCH")
    if rebuilt.world_id != evidence.world_id:
        raise ValueError("REPLAY_WORLD_ID_MISMATCH")

    information: list[str] = []
    material_digests: list[str] = []
    for event in evidence.events:
        info_ref, material_digest = _information_ref(event)
        information.append(info_ref)
        material_digests.append(material_digest)

    return SourceBoundPublicationEvidence(
        world_id=evidence.world_id,
        baseline_version=evidence.baseline_version,
        expected_state_version=evidence.expected_state_version,
        event_sequence_digest=evidence.event_sequence_digest,
        package_digest=evidence.package_digest,
        source_event_refs=evidence_event_ids,
        source_information_refs=tuple(information),
        source_material_digests=tuple(material_digests),
    )


def build_source_bound_publication_candidate(
    solo_replay_package: bytes | bytearray | memoryview,
    *,
    audience_class: str,
    publication_cursor_event_count: int | None = None,
) -> PublicationProjectionCandidate:
    """Build a policy-neutral, noncanonical PublicationProjection candidate.

    The only positive information universe comes from canonical committed events.
    `publication_cursor_event_count` may restrict a delayed candidate, but can
    never introduce a ref that did not originate in the replay evidence.

    `STRICT_PLAYER_EQUIVALENT` intentionally fails closed to zero positive refs.
    Current accepted replay evidence does not prove explicit-player direct-
    participation provenance, so actor binding or caller claims are not upgraded
    into player knowledge here.
    """

    if audience_class not in SUPPORTED_AUDIENCES:
        raise ValueError("UNSUPPORTED_PUBLICATION_AUDIENCE_CLASS")

    source = derive_source_bound_publication_evidence(solo_replay_package)
    total = len(source.source_event_refs)

    if audience_class == "OMNISCIENT_SPECTATOR_CANDIDATE":
        if publication_cursor_event_count is not None:
            raise ValueError("OMNISCIENT_CANDIDATE_DOES_NOT_ACCEPT_CURSOR")
        reveal_count = total
    elif audience_class == "DELAYED_REVEAL_CANDIDATE":
        if isinstance(publication_cursor_event_count, bool) or not isinstance(
            publication_cursor_event_count, int
        ):
            raise ValueError("DELAYED_REVEAL_CURSOR_REQUIRED")
        if publication_cursor_event_count < 0 or publication_cursor_event_count > total:
            raise ValueError("DELAYED_REVEAL_CURSOR_OUT_OF_RANGE")
        reveal_count = publication_cursor_event_count
    else:
        if publication_cursor_event_count not in (None, 0):
            raise ValueError("STRICT_PLAYER_EQUIVALENT_FAILS_CLOSED")
        reveal_count = 0

    selected_events = source.source_event_refs[:reveal_count]
    selected_information = source.source_information_refs[:reveal_count]
    redacted_information = source.source_information_refs[reveal_count:]

    candidate_material = {
        "eval_id": EVAL_ID,
        "world_id": source.world_id,
        "audience_class": audience_class,
        "source_event_refs": selected_events,
        "allowed_information_refs": selected_information,
        "redacted_information_refs": redacted_information,
        "event_sequence_digest": source.event_sequence_digest,
        "package_digest": source.package_digest,
        "policy_version": POLICY_VERSION,
    }
    source_evidence_digest = _sha256(candidate_material)

    return PublicationProjectionCandidate(
        publication_id=f"PUB-G2-{source_evidence_digest[:24]}",
        audience_class=audience_class,
        source_event_refs=selected_events,
        allowed_information_refs=selected_information,
        redacted_information_refs=redacted_information,
        presentation_refs=(),
        policy_version=POLICY_VERSION,
        source_evidence_digest=source_evidence_digest,
    )
