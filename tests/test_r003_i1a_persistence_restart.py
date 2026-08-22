import base64
import hashlib
import itertools
import json

import pytest

from awrse import (
    ActionCompiler,
    ActorState,
    LEGACY_EVENT_PROFILE_ID,
    NPCMindState,
    ObjectState,
    PERSISTENCE_PROFILE_ID,
    PERSISTENCE_PROFILE_VERSION,
    ResolutionStatus,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
    export_solo_replay_package,
    import_solo_replay_package,
    rehydrate_solo_replay_package,
)


PRINCIPAL = "principal://r003-i1a-player"


def make_world() -> WorldState:
    return WorldState(
        "WORLD_R003_I1A",
        "STREET_001",
        "R003-I1A-BASELINE-v1",
        actors={
            "PLAYER": ActorState(
                "PLAYER",
                "玩家",
                "STREET_001",
                capabilities={
                    "SPEAK", "HIT", "PICK", "DROP", "THROW", "OPEN", "CLOSE", "WALK"
                },
                zone_id="ZONE_FRONT",
            ),
            "GUARD_001": ActorState(
                "GUARD_001",
                "守卫",
                "STREET_001",
                zone_id="ZONE_FRONT",
            ),
        },
        objects={
            "BOTTLE_001": ObjectState(
                "BOTTLE_001",
                "酒瓶",
                "STREET_001",
                0.5,
                True,
                0.4,
                zone_id="ZONE_FRONT",
                affordances={"PICK", "DROP", "THROW"},
            ),
            "DOOR_001": ObjectState(
                "DOOR_001",
                "铁门",
                "STREET_001",
                50.0,
                False,
                0.3,
                zone_id="ZONE_FRONT",
                affordances={"OPEN", "CLOSE"},
            ),
        },
        npc_minds={"GUARD_001": NPCMindState("GUARD_001", "GUARD")},
        scenes={
            "STREET_001": SceneState(
                "STREET_001",
                ["asset://street/master"],
                ["BOTTLE_001", "DOOR_001"],
                ["PLAYER", "GUARD_001"],
            ),
            "BAR_001": SceneState("BAR_001", ["asset://bar/master"]),
        },
        principal_actor_bindings={PRINCIPAL: {"PLAYER"}},
        visible_pairs={("BOTTLE_001", "GUARD_001")},
        zone_scene_bindings={
            "ZONE_FRONT": "STREET_001",
            "ZONE_BACK": "STREET_001",
            "BAR_ZONE": "BAR_001",
        },
        zone_adjacency_pairs={("ZONE_FRONT", "ZONE_BACK")},
    )


def compile_action(world: WorldState, text: str):
    return ActionCompiler().compile(text, "PLAYER", world, PRINCIPAL)


def build_source_world():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()
    engine.resolve_and_commit(compile_action(world, "打开铁门"), world)
    engine.resolve_and_commit(compile_action(world, "拿起酒瓶"), world)
    engine.resolve_and_commit(compile_action(world, "走到ZONE_BACK"), world)
    engine.resolve_and_commit(compile_action(world, "放下酒瓶"), world)
    engine.transition_active_scene("BAR_001", world)
    engine.transition_active_scene("STREET_001", world)
    return baseline, world


def canonical_projection_view(world: WorldState) -> dict:
    return {
        "world_id": world.world_id,
        "baseline_version": world.baseline_version,
        "state_version": world.state_version,
        "active_scene_id": world.active_scene_id,
        "actors": {
            actor_id: {
                "scene_id": actor.scene_id,
                "zone_id": actor.zone_id,
                "free_hands": actor.free_hands,
                "inventory_refs": list(actor.inventory_refs),
                "capabilities": sorted(actor.capabilities),
            }
            for actor_id, actor in sorted(world.actors.items())
        },
        "objects": {
            object_id: {
                "scene_id": obj.scene_id,
                "zone_id": obj.zone_id,
                "damage_state": obj.damage_state,
                "contamination_state": obj.contamination_state,
                "is_open": obj.is_open,
                "owner_actor_id": obj.owner_actor_id,
                "affordances": sorted(obj.affordances),
            }
            for object_id, obj in sorted(world.objects.items())
        },
        "npc_minds": {
            npc_id: {
                "memories": list(mind.memories),
                "knowledge_boundary_refs": list(mind.knowledge_boundary_refs),
                "relationship_to_player": mind.relationship_to_player,
            }
            for npc_id, mind in sorted(world.npc_minds.items())
        },
        "scenes": {
            scene_id: {
                "persistent_delta_refs": list(scene.persistent_delta_refs),
                "relevant_event_refs": list(scene.relevant_event_refs),
            }
            for scene_id, scene in sorted(world.scenes.items())
        },
        "event_ids": [event.event_id for event in world.event_log],
        "event_types": [event.event_type for event in world.event_log],
        "committed_event_ids": sorted(world.committed_event_ids),
    }


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")


def refresh_digests(data: dict, *, refresh_events: bool = False) -> bytes:
    if refresh_events:
        data["event_sequence_digest"] = hashlib.sha256(
            canonical_json_bytes(data["ordered_events"])
        ).hexdigest()
    unsigned = dict(data)
    unsigned.pop("package_digest", None)
    data["package_digest"] = hashlib.sha256(canonical_json_bytes(unsigned)).hexdigest()
    return canonical_json_bytes(data)


def decode_package(package: bytes) -> dict:
    return json.loads(package.decode("utf-8"))


def test_r003_i1a_01_real_bytes_boundary_rehydrates_exact_canonical_state(tmp_path):
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)

    path = tmp_path / "solo-replay-package.json"
    path.write_bytes(package)
    fresh_bytes = path.read_bytes()
    rebuilt = rehydrate_solo_replay_package(fresh_bytes, engine=SimulationEngine())

    assert canonical_projection_view(rebuilt) == canonical_projection_view(source)
    assert rebuilt is not source
    assert rebuilt.objects["BOTTLE_001"] is not source.objects["BOTTLE_001"]
    assert rebuilt.is_live is True
    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        rebuilt.objects["DOOR_001"].is_open = False


def test_r003_i1a_02_export_is_deterministic_for_identical_canonical_evidence():
    baseline, source = build_source_world()
    first = export_solo_replay_package(baseline, source)
    second = export_solo_replay_package(baseline, source)

    assert first == second
    decoded = decode_package(first)
    assert decoded["profile_id"] == PERSISTENCE_PROFILE_ID
    assert decoded["profile_version"] == PERSISTENCE_PROFILE_VERSION
    assert decoded["scope"] == "SOLO"
    assert decoded["event_profile_id"] == LEGACY_EVENT_PROFILE_ID
    assert decoded["source_event_count"] == len(source.event_log)
    assert decoded["expected_state_version"] == source.state_version
    assert [event["event_id"] for event in decoded["ordered_events"]] == [
        event.event_id for event in source.event_log
    ]


def test_r003_i1a_03_package_carries_legacy_events_only_and_no_materialized_truth():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))

    assert "materialized_state" not in decoded
    assert "actors" not in decoded
    assert "objects" not in decoded
    expected_event_fields = {
        "event_id", "event_type", "actor_id", "scene_id",
        "baseline_version", "payload", "caused_by_action_id",
    }
    assert all(set(record) == expected_event_fields for record in decoded["ordered_events"])
    assert all("schema_version" not in record for record in decoded["ordered_events"])
    assert all("ruleset_version" not in record for record in decoded["ordered_events"])
    assert all("authority_scope_ref" not in record for record in decoded["ordered_events"])


def test_r003_i1a_04_baseline_payload_tamper_fails_closed_even_with_refreshed_package_digest():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))
    raw = bytearray(base64.b64decode(decoded["baseline_payload"]))
    raw[-1] ^= 1
    decoded["baseline_payload"] = base64.b64encode(bytes(raw)).decode("ascii")

    with pytest.raises(ValueError, match="BASELINE_SNAPSHOT_INTEGRITY_FAILURE"):
        import_solo_replay_package(refresh_digests(decoded))


def test_r003_i1a_05_event_payload_or_order_tamper_fails_event_integrity():
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)

    payload_tamper = decode_package(package)
    payload_tamper["ordered_events"][0]["payload"]["object_id"] = "FAKE_OBJECT"
    with pytest.raises(ValueError, match="EVENT_SEQUENCE_INTEGRITY_FAILURE"):
        import_solo_replay_package(refresh_digests(payload_tamper))

    order_tamper = decode_package(package)
    order_tamper["ordered_events"][0], order_tamper["ordered_events"][1] = (
        order_tamper["ordered_events"][1], order_tamper["ordered_events"][0]
    )
    with pytest.raises(ValueError, match="EVENT_SEQUENCE_INTEGRITY_FAILURE"):
        import_solo_replay_package(refresh_digests(order_tamper))


def test_r003_i1a_06_duplicate_event_ids_fail_closed_after_integrity_recomputed():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))
    assert len(decoded["ordered_events"]) >= 2
    decoded["ordered_events"][1]["event_id"] = decoded["ordered_events"][0]["event_id"]

    with pytest.raises(ValueError, match="DUPLICATE_COMMITTED_EVENT_ID"):
        import_solo_replay_package(refresh_digests(decoded, refresh_events=True))


def test_r003_i1a_07_world_and_baseline_identity_mismatch_fail_closed():
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)

    wrong_world = decode_package(package)
    wrong_world["world_id"] = "WORLD_OTHER"
    with pytest.raises(ValueError, match="WORLD_ID_MISMATCH"):
        import_solo_replay_package(refresh_digests(wrong_world))

    wrong_baseline = decode_package(package)
    wrong_baseline["baseline_version"] = "WRONG-BASELINE"
    with pytest.raises(ValueError, match="BASELINE_VERSION_MISMATCH"):
        import_solo_replay_package(refresh_digests(wrong_baseline))


def test_r003_i1a_08_unsupported_persistence_and_event_profiles_fail_closed():
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)

    wrong_profile = decode_package(package)
    wrong_profile["profile_version"] = "99.0.0"
    with pytest.raises(ValueError, match="UNSUPPORTED_PERSISTENCE_PROFILE_VERSION"):
        import_solo_replay_package(refresh_digests(wrong_profile))

    wrong_event_profile = decode_package(package)
    wrong_event_profile["event_profile_id"] = "AF001_VNEXT_EVENT_ENVELOPE"
    with pytest.raises(ValueError, match="UNSUPPORTED_EVENT_PROFILE"):
        import_solo_replay_package(refresh_digests(wrong_event_profile))


def test_r003_i1a_09_event_count_and_expected_state_version_mismatch_fail_closed():
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)

    wrong_count = decode_package(package)
    wrong_count["source_event_count"] += 1
    with pytest.raises(ValueError, match="SOURCE_EVENT_COUNT_MISMATCH"):
        import_solo_replay_package(refresh_digests(wrong_count))

    wrong_state_version = decode_package(package)
    wrong_state_version["expected_state_version"] += 1
    with pytest.raises(ValueError, match="EXPECTED_STATE_VERSION_EVENT_COUNT_MISMATCH"):
        import_solo_replay_package(refresh_digests(wrong_state_version))


def test_r003_i1a_10_materialized_projection_injection_is_rejected_not_trusted():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))
    decoded["materialized_state"] = {
        "objects": {"DOOR_001": {"is_open": False}},
        "claim": "override replayed truth",
    }

    with pytest.raises(ValueError, match="PERSISTENCE_ENVELOPE_SCHEMA_MISMATCH"):
        import_solo_replay_package(refresh_digests(decoded))


def test_r003_i1a_11_malformed_or_vnext_shaped_event_record_is_rejected():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))
    decoded["ordered_events"][0]["schema_version"] = "fabricated"

    with pytest.raises(ValueError, match="MALFORMED_LEGACY_EVENT_RECORD"):
        import_solo_replay_package(refresh_digests(decoded, refresh_events=True))


def test_r003_i1a_12_imported_evidence_is_fresh_and_replay_preserves_knowledge_refs():
    baseline, source = build_source_world()
    package = bytes(export_solo_replay_package(baseline, source))
    evidence = import_solo_replay_package(package)
    rebuilt = SimulationEngine().replay(evidence.baseline, evidence.events)

    assert evidence.baseline is not baseline
    assert evidence.events is not source.event_log
    assert tuple(event.event_id for event in evidence.events) == tuple(
        event.event_id for event in source.event_log
    )
    assert rebuilt.npc_minds["GUARD_001"].knowledge_boundary_refs == (
        source.npc_minds["GUARD_001"].knowledge_boundary_refs
    )
    assert rebuilt.state_version == source.state_version


def test_r003_i1a_13_fresh_process_allocator_reset_can_continue_without_id_collision():
    baseline, source = build_source_world()
    package = export_solo_replay_package(baseline, source)
    historical_event_ids = {event.event_id for event in source.event_log}
    historical_action_ids = {
        event.caused_by_action_id
        for event in source.event_log
        if event.caused_by_action_id is not None
    }

    # Simulate a fresh process where legacy class-global counters have forgotten
    # their prior positions. Rehydration must restore them from canonical evidence.
    SimulationEngine._event_counter = itertools.count(1)
    ActionCompiler._counter = itertools.count(1)

    rebuilt = rehydrate_solo_replay_package(package, engine=SimulationEngine())
    before_version = rebuilt.state_version
    next_action = ActionCompiler().compile(
        "走到ZONE_FRONT", "PLAYER", rebuilt, PRINCIPAL
    )
    result = SimulationEngine().resolve_and_commit(next_action, rebuilt)

    assert result.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert result.events
    assert result.action.action_id not in historical_action_ids
    assert all(event.event_id not in historical_event_ids for event in result.events)
    assert all(
        event.caused_by_action_id == result.action.action_id for event in result.events
    )
    assert rebuilt.state_version == before_version + len(result.events)
    assert rebuilt.actors["PLAYER"].zone_id == "ZONE_FRONT"


def test_r003_i1a_14_semantically_unsupported_event_fails_replay_after_digests_recomputed():
    baseline, source = build_source_world()
    decoded = decode_package(export_solo_replay_package(baseline, source))
    decoded["ordered_events"][0]["event_type"] = "FUTURE_UNAUTHORIZED_EVENT"

    with pytest.raises(ValueError, match="UNSUPPORTED_EVENT_TYPE"):
        import_solo_replay_package(refresh_digests(decoded, refresh_events=True))
