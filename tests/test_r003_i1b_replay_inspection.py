from runtime.awrse.replay_inspection import compare_replays, inspect_timeline


def baseline():
    return {
        "steps": [
            {"event_id": "e1", "state_version": "v1", "marker": "checkpoint-1"},
            {"event_id": "e2", "state_version": "v2", "marker": "checkpoint-2"},
        ]
    }


def test_identical_replays_have_identical_inspection():
    assert compare_replays(baseline(), baseline()) is None
    assert inspect_timeline(baseline()) == inspect_timeline(baseline())


def test_changed_event_has_stable_first_divergence():
    changed = baseline()
    changed["steps"] = list(changed["steps"])
    changed["steps"][1] = {"event_id": "eX", "state_version": "v2", "marker": "checkpoint-2"}

    first = compare_replays(baseline(), changed)
    second = compare_replays(baseline(), changed)

    assert first == second
    assert first is not None
    assert first.first_divergence_point == 1
    assert first.event_boundary == "step:1"


def test_inspection_does_not_mutate_input():
    replay = baseline()
    before = repr(replay)
    inspect_timeline(replay)
    assert repr(replay) == before


def test_fresh_object_boundary_same_result():
    left = {"steps": [{"event_id": "same", "state_version": "v1"}]}
    right = {"steps": [{"event_id": "same", "state_version": "v1"}]}
    assert compare_replays(left, right) is None
