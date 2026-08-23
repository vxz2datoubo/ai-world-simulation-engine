"""Read-only deterministic inspection over canonical replay executions.

The public API accepts only the accepted replay inputs: a pristine
:class:`WorldBaseline` plus an ordered sequence of legacy :class:`Event`
objects. Every checkpoint is rebuilt through ``SimulationEngine.replay()``.
This module never applies events, repairs history, or materializes a second
world-state authority.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any

from .engine import SimulationEngine
from .model import Event, WorldBaseline, WorldState, _world_to_data


@dataclass(frozen=True)
class ReplayInspectionCheckpoint:
    step: int
    event_index: int | None
    event_id: str | None
    event_type: str | None
    state_version: int
    state_version_ref: str
    state_digest: str
    marker: str


@dataclass(frozen=True)
class ReplayDivergence:
    first_divergence_point: int | None
    event_boundary: str | None
    left_event_id: str | None
    right_event_id: str | None
    event_differences: tuple[str, ...]
    state_differences: tuple[str, ...]
    left_state_marker: str | None
    right_state_marker: str | None


@dataclass(frozen=True)
class ReplayInspectionResult:
    checkpoints: tuple[ReplayInspectionCheckpoint, ...]
    divergence: ReplayDivergence | None


def inspect_timeline(
    baseline: WorldBaseline,
    events: Iterable[Event],
) -> tuple[ReplayInspectionCheckpoint, ...]:
    """Return deterministic checkpoints derived only from canonical replay."""

    event_sequence = _require_replay_inputs(baseline, events)
    return _inspect_timeline_from_sequence(baseline, event_sequence)


def compare_replays(
    left_baseline: WorldBaseline,
    left_events: Iterable[Event],
    right_baseline: WorldBaseline,
    right_events: Iterable[Event],
) -> ReplayDivergence | None:
    """Find the first canonical world-state divergence between two replays.

    Event/provenance differences are diagnostic evidence only. They are
    attached to a ``ReplayDivergence`` after the canonical replay projections
    differ; an Event metadata difference alone cannot mint world divergence.
    """

    left_sequence = _require_replay_inputs(left_baseline, left_events)
    right_sequence = _require_replay_inputs(right_baseline, right_events)
    return _compare_sequences(
        left_baseline,
        left_sequence,
        right_baseline,
        right_sequence,
    )


def inspect_replays(
    left_baseline: WorldBaseline,
    left_events: Iterable[Event],
    right_baseline: WorldBaseline | None = None,
    right_events: Iterable[Event] = (),
) -> ReplayInspectionResult:
    """Inspect one canonical replay and optionally compare it with another.

    Each public iterable is normalized exactly once so one-shot generators are
    consumed a single time and the same accepted sequence is reused for both
    timeline inspection and comparison.
    """

    left_sequence = _require_replay_inputs(left_baseline, left_events)
    checkpoints = _inspect_timeline_from_sequence(left_baseline, left_sequence)
    divergence = None
    if right_baseline is not None:
        right_sequence = _require_replay_inputs(right_baseline, right_events)
        divergence = _compare_sequences(
            left_baseline,
            left_sequence,
            right_baseline,
            right_sequence,
        )
    return ReplayInspectionResult(checkpoints=checkpoints, divergence=divergence)


def _require_replay_inputs(
    baseline: WorldBaseline,
    events: Iterable[Event],
) -> tuple[Event, ...]:
    if not isinstance(baseline, WorldBaseline):
        raise TypeError("WORLD_BASELINE_REQUIRED")
    try:
        event_sequence = tuple(events)
    except TypeError as exc:
        raise TypeError("ORDERED_CANONICAL_EVENTS_REQUIRED") from exc
    if any(not isinstance(event, Event) for event in event_sequence):
        raise TypeError("ORDERED_CANONICAL_EVENTS_REQUIRED")
    return event_sequence


def _inspect_timeline_from_sequence(
    baseline: WorldBaseline,
    events: tuple[Event, ...],
) -> tuple[ReplayInspectionCheckpoint, ...]:
    states = _replay_prefix_states(baseline, events)
    checkpoints = [_checkpoint(step=0, event_index=None, event=None, world=states[0])]
    checkpoints.extend(
        _checkpoint(
            step=index + 1,
            event_index=index,
            event=event,
            world=states[index + 1],
        )
        for index, event in enumerate(events)
    )
    return tuple(checkpoints)


def _compare_sequences(
    left_baseline: WorldBaseline,
    left_sequence: tuple[Event, ...],
    right_baseline: WorldBaseline,
    right_sequence: tuple[Event, ...],
) -> ReplayDivergence | None:
    left_states = _replay_prefix_states(left_baseline, left_sequence)
    right_states = _replay_prefix_states(right_baseline, right_sequence)

    baseline_state_diff = _canonical_projection_diff(left_states[0], right_states[0])
    if baseline_state_diff:
        return ReplayDivergence(
            first_divergence_point=0,
            event_boundary="baseline",
            left_event_id=None,
            right_event_id=None,
            event_differences=("baseline",),
            state_differences=baseline_state_diff,
            left_state_marker=_state_marker(left_states[0]),
            right_state_marker=_state_marker(right_states[0]),
        )

    limit = min(len(left_sequence), len(right_sequence))
    for index in range(limit):
        left_event = left_sequence[index]
        right_event = right_sequence[index]
        left_state = left_states[index + 1]
        right_state = right_states[index + 1]
        state_differences = _canonical_projection_diff(left_state, right_state)
        if state_differences:
            return ReplayDivergence(
                first_divergence_point=index,
                event_boundary=f"event-index:{index}",
                left_event_id=left_event.event_id,
                right_event_id=right_event.event_id,
                event_differences=_event_diff(left_event, right_event),
                state_differences=state_differences,
                left_state_marker=_state_marker(left_state),
                right_state_marker=_state_marker(right_state),
            )

    if len(left_sequence) != len(right_sequence):
        index = limit
        left_event = left_sequence[index] if index < len(left_sequence) else None
        right_event = right_sequence[index] if index < len(right_sequence) else None
        left_state = left_states[index + 1] if left_event is not None else left_states[index]
        right_state = right_states[index + 1] if right_event is not None else right_states[index]
        state_differences = _canonical_projection_diff(left_state, right_state)
        if state_differences:
            return ReplayDivergence(
                first_divergence_point=index,
                event_boundary=f"event-index:{index}",
                left_event_id=None if left_event is None else left_event.event_id,
                right_event_id=None if right_event is None else right_event.event_id,
                event_differences=("timeline_length",),
                state_differences=state_differences,
                left_state_marker=_state_marker(left_state),
                right_state_marker=_state_marker(right_state),
            )

    return None


def _replay_prefix_states(
    baseline: WorldBaseline,
    events: tuple[Event, ...],
) -> tuple[WorldState, ...]:
    states: list[WorldState] = []
    for prefix_length in range(len(events) + 1):
        rebuilt = SimulationEngine().replay(baseline, events[:prefix_length])
        if not rebuilt.is_live:
            raise RuntimeError("REPLAY_INSPECTION_REQUIRES_SEALED_WORLD_STATE")
        states.append(rebuilt)
    return tuple(states)


def _checkpoint(
    *,
    step: int,
    event_index: int | None,
    event: Event | None,
    world: WorldState,
) -> ReplayInspectionCheckpoint:
    digest = _state_digest(world)
    return ReplayInspectionCheckpoint(
        step=step,
        event_index=event_index,
        event_id=None if event is None else event.event_id,
        event_type=None if event is None else event.event_type,
        state_version=world.state_version,
        state_version_ref=world.world_state_version,
        state_digest=digest,
        marker=f"sha256:{digest}",
    )


def _canonical_projection_data(world: WorldState) -> dict[str, Any]:
    data = dict(_world_to_data(world))
    for evidence_field in ("event_log", "committed_event_ids"):
        data.pop(evidence_field, None)
    return data


def _state_digest(world: WorldState) -> str:
    payload = json.dumps(
        _canonical_projection_data(world),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _state_marker(world: WorldState) -> str:
    return f"sha256:{_state_digest(world)}"


def _event_diff(left: Event, right: Event) -> tuple[str, ...]:
    fields = (
        "event_id",
        "event_type",
        "actor_id",
        "scene_id",
        "baseline_version",
        "payload",
        "caused_by_action_id",
    )
    return tuple(field for field in fields if getattr(left, field) != getattr(right, field))


def _canonical_projection_diff(left: WorldState, right: WorldState) -> tuple[str, ...]:
    """Diff the canonical projected world, excluding Event evidence metadata."""

    return tuple(
        _diff_paths(
            _canonical_projection_data(left),
            _canonical_projection_data(right),
        )
    )


def _diff_paths(left: Any, right: Any, prefix: str = "") -> list[str]:
    if isinstance(left, Mapping) and isinstance(right, Mapping):
        paths: list[str] = []
        for key in sorted(set(left) | set(right), key=str):
            path = f"{prefix}.{key}" if prefix else str(key)
            if key not in left or key not in right:
                paths.append(path)
                continue
            paths.extend(_diff_paths(left[key], right[key], path))
        return paths
    if left != right:
        return [prefix or "$world"]
    return []
