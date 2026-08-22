"""Read-only deterministic replay inspection helpers.

This module observes canonical replay evidence. It does not execute, mutate,
or repair simulation history.
"""

from dataclasses import dataclass
from typing import Any, Iterable


@dataclass(frozen=True)
class ReplayInspectionCheckpoint:
    step: int
    event_id: str
    state_version: str
    marker: str | None = None


@dataclass(frozen=True)
class ReplayDivergence:
    first_divergence_point: int | None
    event_boundary: str | None
    left_event_id: str | None
    right_event_id: str | None
    state_differences: tuple[str, ...]


@dataclass(frozen=True)
class ReplayInspectionResult:
    checkpoints: tuple[ReplayInspectionCheckpoint, ...]
    divergence: ReplayDivergence | None


def inspect_timeline(execution: dict[str, Any]) -> tuple[ReplayInspectionCheckpoint, ...]:
    """Create a deterministic read-only timeline view from replay evidence."""
    return tuple(
        ReplayInspectionCheckpoint(
            step=index,
            event_id=str(item["event_id"]),
            state_version=str(item.get("state_version", "UNKNOWN")),
            marker=item.get("marker"),
        )
        for index, item in enumerate(execution.get("steps", ()))
    )


def compare_replays(left: dict[str, Any], right: dict[str, Any]) -> ReplayDivergence | None:
    """Find the first canonical replay evidence divergence.

    Inputs are accepted replay evidence snapshots. This function only compares
    them and never creates a world state or alternate truth source.
    """
    left_steps = list(left.get("steps", ()))
    right_steps = list(right.get("steps", ()))
    limit = min(len(left_steps), len(right_steps))

    for index in range(limit):
        if left_steps[index] != right_steps[index]:
            return ReplayDivergence(
                first_divergence_point=index,
                event_boundary=f"step:{index}",
                left_event_id=str(left_steps[index].get("event_id")),
                right_event_id=str(right_steps[index].get("event_id")),
                state_differences=_state_diff(left_steps[index], right_steps[index]),
            )

    if len(left_steps) != len(right_steps):
        index = limit
        return ReplayDivergence(
            first_divergence_point=index,
            event_boundary=f"step:{index}",
            left_event_id=_event_id(left_steps, index),
            right_event_id=_event_id(right_steps, index),
            state_differences=("timeline_length",),
        )

    return None


def inspect_replays(*executions: dict[str, Any]) -> ReplayInspectionResult:
    """Inspect replay timelines and compare the first two executions only."""
    if len(executions) < 2:
        return ReplayInspectionResult(
            checkpoints=inspect_timeline(executions[0]) if executions else (),
            divergence=None,
        )
    return ReplayInspectionResult(
        checkpoints=inspect_timeline(executions[0]),
        divergence=compare_replays(executions[0], executions[1]),
    )


def _event_id(steps: list[dict[str, Any]], index: int) -> str | None:
    return str(steps[index].get("event_id")) if index < len(steps) else None


def _state_diff(left: dict[str, Any], right: dict[str, Any]) -> tuple[str, ...]:
    return tuple(
        key
        for key in sorted(set(left) | set(right))
        if left.get(key) != right.get(key)
    )
