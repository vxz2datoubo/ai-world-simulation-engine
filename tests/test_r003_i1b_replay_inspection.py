import base64
import hashlib
import json
import os
import subprocess
import sys
from dataclasses import asdict
from pathlib import Path

import pytest

from awrse import (
    ActorState,
    ObjectState,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
    compare_replays,
    export_solo_replay_package,
    import_solo_replay_package,
    inspect_timeline,
)
from awrse.model import Event, _encode_world_snapshot


BASELINE_VERSION = "R003-I1B-BASELINE-v1"


def make_baseline():
    world = WorldState(
        world_id="WORLD_R003_I1B",
        active_scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        actors={
            "PLAYER": ActorState(
                actor_id="PLAYER",
                name="Player",
                scene_id="SCENE_001",
            )
        },
        objects={
            "DOOR_001": ObjectState(
                object_id="DOOR_001",
                name="Door",
                scene_id="SCENE_001",
                graspable=False,
                affordances={"OPEN"},
            )
        },
        scenes={
            "SCENE_001": SceneState(
                scene_id="SCENE_001",
                object_state_refs=["DOOR_001"],
                actor_state_refs=["PLAYER"],
            )
        },
        reachable_pairs={("PLAYER", "DOOR_001")},
    )
    return capture_pristine_baseline(world)


def common_event() -> Event:
    return Event(
        event_id="E1",
        event_type="OBJECT_DAMAGED",
        actor_id="PLAYER",
        scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        payload={"object_id": "DOOR_001", "damage_state": "DAMAGED"},
        caused_by_action_id="A1",
    )


def left_events() -> tuple[Event, ...]:
    return (
        common_event(),
        Event(
            event_id="E2-LEFT",
            event_type="OBJECT_OPENED",
            actor_id="PLAYER",
            scene_id="SCENE_001",
            baseline_version=BASELINE_VERSION,
            payload={"object_id": "DOOR_001", "actor_id": "PLAYER"},
            caused_by_action_id="A2",
        ),
    )


def right_events() -> tuple[Event, ...]:
    return (
        common_event(),
        Event(
            event_id="E2-RIGHT",
            event_type="OBJECT_DAMAGED",
            actor_id="PLAYER",
            scene_id="SCENE_001",
            baseline_version=BASELINE_VERSION,
            payload={"object_id": "DOOR_001", "damage_state": "BROKEN"},
            caused_by_action_id="A2",
        ),
    )


def inspection_payload(left_package: bytes, right_package: bytes) -> dict:
    left = import_solo_replay_package(left_package)
    right = import_solo_replay_package(right_package)
    checkpoints = inspect_timeline(left.baseline, left.events)
    divergence = compare_replays(
        left.baseline,
        left.events,
        right.baseline,
        right.events,
    )
    return {
        "checkpoints": [asdict(checkpoint) for checkpoint in checkpoints],
        "divergence": None if divergence is None else asdict(divergence),
    }


def test_identical_canonical_replays_have_identical_inspection():
    baseline = make_baseline()
    events = left_events()

    first = inspect_timeline(baseline, events)
    second = inspect_timeline(baseline, tuple(events))

    assert first == second
    assert compare_replays(baseline, events, baseline, tuple(events)) is None
    assert [(item.event_id, item.state_version) for item in first] == [
        (None, 0),
        ("E1", 1),
        ("E2-LEFT", 2),
    ]
    assert all(item.marker == f"sha256:{item.state_digest}" for item in first)


def test_public_api_rejects_fabricated_step_dictionaries():
    baseline = make_baseline()

    with pytest.raises(TypeError, match="WORLD_BASELINE_REQUIRED"):
        inspect_timeline({"steps": []}, ())  # type: ignore[arg-type]

    with pytest.raises(TypeError, match="ORDERED_CANONICAL_EVENTS_REQUIRED"):
        inspect_timeline(baseline, ({"event_id": "fabricated"},))  # type: ignore[arg-type]


def test_semantically_invalid_event_fails_through_canonical_replay_validation():
    baseline = make_baseline()
    fabricated = Event(
        event_id="E-BAD",
        event_type="OBJECT_OPENED",
        actor_id="PLAYER",
        scene_id="SCENE_001",
        baseline_version=BASELINE_VERSION,
        payload={"object_id": "MISSING", "actor_id": "PLAYER"},
    )

    with pytest.raises(ValueError, match="INVALID_OBJECT_OPEN_CLOSE_EVENT"):
        inspect_timeline(baseline, (fabricated,))


def test_checkpoint_digest_is_exact_sealed_replay_projection():
    baseline = make_baseline()
    events = left_events()
    timeline = inspect_timeline(baseline, events)

    canonical_after_first = SimulationEngine().replay(baseline, events[:1])
    expected_digest = hashlib.sha256(
        _encode_world_snapshot(canonical_after_first)
    ).hexdigest()

    assert canonical_after_first.is_live is True
    assert timeline[1].state_digest == expected_digest
    assert timeline[1].state_version_ref == canonical_after_first.world_state_version


def test_real_event_change_has_stable_first_canonical_divergence_and_state_diff():
    baseline = make_baseline()
    left = left_events()
    right = right_events()

    first = compare_replays(baseline, left, baseline, right)
    second = compare_replays(baseline, left, baseline, right)

    assert first == second
    assert first is not None
    assert first.first_divergence_point == 1
    assert first.event_boundary == "event-index:1"
    assert first.left_event_id == "E2-LEFT"
    assert first.right_event_id == "E2-RIGHT"
    assert {"event_id", "event_type", "payload"}.issubset(first.event_differences)
    assert "objects.DOOR_001.is_open" in first.state_differences
    assert "objects.DOOR_001.damage_state" in first.state_differences

    left_world = SimulationEngine().replay(baseline, left)
    right_world = SimulationEngine().replay(baseline, right)
    assert left_world.objects["DOOR_001"].is_open is True
    assert left_world.objects["DOOR_001"].damage_state == "DAMAGED"
    assert right_world.objects["DOOR_001"].is_open is False
    assert right_world.objects["DOOR_001"].damage_state == "BROKEN"


def test_inspection_does_not_mutate_baseline_or_events():
    baseline = make_baseline()
    events = left_events()
    before_digest = baseline.snapshot_digest
    before_events = tuple(events)

    inspect_timeline(baseline, events)
    compare_replays(baseline, events, baseline, events)

    pristine = baseline.instantiate()
    assert baseline.snapshot_digest == before_digest
    assert events == before_events
    assert pristine.state_version == 0
    assert pristine.event_log == []
    assert pristine.committed_event_ids == set()


def test_fresh_python_process_reconstructs_validated_evidence_and_matches_output():
    baseline = make_baseline()
    left_world = SimulationEngine().replay(baseline, left_events())
    right_world = SimulationEngine().replay(baseline, right_events())
    left_package = export_solo_replay_package(baseline, left_world)
    right_package = export_solo_replay_package(baseline, right_world)

    parent_payload = inspection_payload(left_package, right_package)
    parent_json = json.dumps(
        parent_payload,
        sort_keys=True,
        separators=(",", ":"),
    )
    transport = json.dumps(
        {
            "left": base64.b64encode(left_package).decode("ascii"),
            "right": base64.b64encode(right_package).decode("ascii"),
        },
        sort_keys=True,
        separators=(",", ":"),
    )
    script = r'''
import base64
import json
import sys
from dataclasses import asdict
from awrse import compare_replays, import_solo_replay_package, inspect_timeline

transport = json.loads(sys.stdin.read())
left = import_solo_replay_package(base64.b64decode(transport["left"], validate=True))
right = import_solo_replay_package(base64.b64decode(transport["right"], validate=True))
checkpoints = inspect_timeline(left.baseline, left.events)
divergence = compare_replays(left.baseline, left.events, right.baseline, right.events)
payload = {
    "checkpoints": [asdict(checkpoint) for checkpoint in checkpoints],
    "divergence": None if divergence is None else asdict(divergence),
}
print(json.dumps(payload, sort_keys=True, separators=(",", ":")))
'''
    env = os.environ.copy()
    runtime_path = str(Path(__file__).resolve().parents[1] / "runtime")
    existing_pythonpath = env.get("PYTHONPATH")
    env["PYTHONPATH"] = (
        runtime_path
        if not existing_pythonpath
        else runtime_path + os.pathsep + existing_pythonpath
    )
    child = subprocess.run(
        [sys.executable, "-c", script],
        input=transport,
        text=True,
        capture_output=True,
        check=True,
        env=env,
    )
    child_json = child.stdout.strip()
    child_payload = json.loads(child_json)

    assert child_json == parent_json
    assert child_payload["divergence"]["first_divergence_point"] == 1
    assert "objects.DOOR_001.is_open" in child_payload["divergence"]["state_differences"]
