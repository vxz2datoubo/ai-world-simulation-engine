import pytest

from awrse import (
    ActionCompiler,
    ActorState,
    NPCMindState,
    ObjectState,
    ResolutionStatus,
    SceneState,
    SimulationEngine,
    WorldState,
    build_render_packet,
    capture_pristine_baseline,
    validate_render_claims,
)
from awrse.model import Event

PRINCIPAL = "principal://r002-review"


def make_world() -> WorldState:
    return WorldState(
        "WORLD_R002_REVIEW",
        "STREET",
        "R002-REVIEW-v1",
        actors={
            "PLAYER": ActorState(
                "PLAYER", "玩家", "STREET", free_hands=2,
                capabilities={"SPEAK", "HIT", "PICK", "DROP", "THROW", "OPEN", "CLOSE", "WALK"},
                zone_id="FRONT",
            ),
            "GUARD": ActorState("GUARD", "守卫", "STREET", zone_id="FRONT"),
        },
        objects={
            "BOTTLE_A": ObjectState(
                "BOTTLE_A", "瓶A", "STREET", mass=0.5, graspable=True, zone_id="FRONT",
                affordances={"PICK", "DROP", "THROW"},
            ),
            "BOTTLE_B": ObjectState(
                "BOTTLE_B", "瓶B", "STREET", mass=0.5, graspable=True, zone_id="FRONT",
                affordances={"PICK", "DROP", "THROW"},
            ),
            "DOOR_A": ObjectState(
                "DOOR_A", "门A", "STREET", mass=50.0, graspable=False, zone_id="FRONT",
                affordances={"OPEN", "CLOSE"},
            ),
            "DOOR_B": ObjectState(
                "DOOR_B", "门B", "STREET", mass=50.0, graspable=False, zone_id="FRONT",
                affordances={"OPEN", "CLOSE"},
            ),
            "REMOTE": ObjectState(
                "REMOTE", "遥控", "STREET", mass=0.2, graspable=True, zone_id="BACK",
                affordances={"PICK", "DROP", "THROW"},
            ),
        },
        npc_minds={"GUARD": NPCMindState("GUARD", "GUARD")},
        scenes={
            "STREET": SceneState(
                "STREET", ["asset://street"],
                ["BOTTLE_A", "BOTTLE_B", "DOOR_A", "DOOR_B", "REMOTE"],
                ["PLAYER", "GUARD"],
            ),
            "BAR": SceneState("BAR", ["asset://bar"]),
        },
        principal_actor_bindings={PRINCIPAL: {"PLAYER"}},
        zone_scene_bindings={"FRONT": "STREET", "BACK": "STREET", "SIDE": "STREET", "BAR_ZONE": "BAR"},
        zone_adjacency_pairs={("FRONT", "BACK"), ("BACK", "SIDE")},
    )


def compile_action(world: WorldState, text: str):
    return ActionCompiler().compile(text, "PLAYER", world, PRINCIPAL)


def assert_zero_mutation(world: WorldState) -> None:
    assert world.state_version == 0
    assert tuple(world.event_log) == ()
    assert world.committed_event_ids == frozenset()


@pytest.mark.parametrize(
    "text",
    [
        "拿起 BOTTLE_A BOTTLE_B",
        "打开 DOOR_A DOOR_B",
    ],
)
def test_b01_multi_target_pick_or_open_fails_closed(text: str):
    world = make_world()
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, text), world)
    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "EXACTLY_ONE_OBJECT_TARGET_REQUIRED"
    assert_zero_mutation(world)
    assert world.objects["BOTTLE_A"].owner_actor_id is None
    assert world.objects["BOTTLE_B"].owner_actor_id is None
    assert world.objects["DOOR_A"].is_open is False
    assert world.objects["DOOR_B"].is_open is False


@pytest.mark.parametrize("text", ["放下 BOTTLE_A BOTTLE_B", "扔 BOTTLE_A BOTTLE_B"])
def test_b01_multi_target_release_fails_closed(text: str):
    world = make_world()
    player = world.actors["PLAYER"]
    player.inventory_refs.extend(["BOTTLE_A", "BOTTLE_B"])
    player.free_hands = 0
    for object_id in ("BOTTLE_A", "BOTTLE_B"):
        world.objects[object_id].owner_actor_id = "PLAYER"
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, text), world)
    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "EXACTLY_ONE_OBJECT_TARGET_REQUIRED"
    assert_zero_mutation(world)
    assert set(world.actors["PLAYER"].inventory_refs) == {"BOTTLE_A", "BOTTLE_B"}
    assert world.objects["BOTTLE_A"].owner_actor_id == "PLAYER"
    assert world.objects["BOTTLE_B"].owner_actor_id == "PLAYER"


@pytest.mark.parametrize("opening,text", [(True, "打开 DOOR_A DOOR_B"), (False, "关上 DOOR_A DOOR_B")])
def test_b01_multi_target_open_close_fails_closed(opening: bool, text: str):
    world = make_world()
    if not opening:
        world.objects["DOOR_A"].is_open = True
        world.objects["DOOR_B"].is_open = True
    before = (world.objects["DOOR_A"].is_open, world.objects["DOOR_B"].is_open)
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, text), world)
    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "EXACTLY_ONE_OBJECT_TARGET_REQUIRED"
    assert_zero_mutation(world)
    assert (world.objects["DOOR_A"].is_open, world.objects["DOOR_B"].is_open) == before


def test_b01_mixed_object_and_actor_target_fails_closed():
    world = make_world()
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, "拿起 BOTTLE_A GUARD"), world)
    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "EXACTLY_ONE_OBJECT_TARGET_REQUIRED"
    assert_zero_mutation(world)


def test_b01_single_target_and_walk_positive_paths_remain_green():
    world = make_world()
    engine = SimulationEngine()
    pick = engine.resolve_and_commit(compile_action(world, "拿起 BOTTLE_A"), world)
    walk = engine.resolve_and_commit(compile_action(world, "走到BACK"), world)
    assert pick.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert walk.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert world.objects["BOTTLE_A"].owner_actor_id == "PLAYER"
    assert world.actors["PLAYER"].zone_id == "BACK"
    assert world.objects["BOTTLE_A"].zone_id == "BACK"


def packet_states(packet):
    return {
        str(delta["object_id"]): {
            key: delta[key]
            for key in delta
            if key not in {"kind", "object_id"}
        }
        for delta in packet.environment_delta
        if delta.get("kind") == "OBJECT_STATE"
    }


def validate_packet(packet, states):
    return validate_render_claims(
        packet,
        {event.event_id for event in packet.confirmed_events},
        states,
        packet.scene_id,
        packet.actor_state_refs,
        packet.camera,
    )


def test_b02_open_closed_contradictions_fail_closed_both_directions():
    world = make_world()
    engine = SimulationEngine()
    opened = engine.resolve_and_commit(compile_action(world, "打开 DOOR_A"), world)
    packet = build_render_packet(world, opened.events)
    states = packet_states(packet)
    states["DOOR_A"]["is_open"] = False
    result = validate_packet(packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "OBJECT_STATE:DOOR_A:is_open:False!=True" in result.semantic_contradictions

    closed_world = make_world()
    closed_packet = build_render_packet(closed_world, ())
    states = packet_states(closed_packet)
    states["DOOR_A"]["is_open"] = True
    result = validate_packet(closed_packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "OBJECT_STATE:DOOR_A:is_open:True!=False" in result.semantic_contradictions


def test_b02_possession_contradictions_fail_closed_both_directions():
    world = make_world()
    picked = SimulationEngine().resolve_and_commit(compile_action(world, "拿起 BOTTLE_A"), world)
    packet = build_render_packet(world, picked.events)
    states = packet_states(packet)
    states["BOTTLE_A"]["owner_actor_id"] = None
    result = validate_packet(packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "OBJECT_STATE:BOTTLE_A:owner_actor_id:None!=PLAYER" in result.semantic_contradictions

    ground_world = make_world()
    ground_packet = build_render_packet(ground_world, ())
    states = packet_states(ground_packet)
    states["BOTTLE_A"]["owner_actor_id"] = "PLAYER"
    result = validate_packet(ground_packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "OBJECT_STATE:BOTTLE_A:owner_actor_id:PLAYER!=None" in result.semantic_contradictions


def test_b02_zone_mismatch_and_missing_r002_field_fail_closed():
    world = make_world()
    packet = build_render_packet(world, ())
    states = packet_states(packet)
    states["BOTTLE_A"]["zone_id"] = "BACK"
    result = validate_packet(packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "OBJECT_STATE:BOTTLE_A:zone_id:BACK!=FRONT" in result.semantic_contradictions

    states = packet_states(packet)
    del states["BOTTLE_A"]["owner_actor_id"]
    result = validate_packet(packet, states)
    assert result.status == "RENDER_MISMATCH"
    assert "MISSING_OBJECT_FIELD:BOTTLE_A:owner_actor_id" in result.semantic_contradictions


def test_b02_all_r002_object_fields_aligned_is_green():
    world = make_world()
    packet = build_render_packet(world, ())
    states = packet_states(packet)
    assert set(states["BOTTLE_A"]) == {"damage_state", "contamination_state", "is_open", "owner_actor_id", "zone_id"}
    assert validate_packet(packet, states).status == "RENDER_ALIGNED"


def test_b02_revisit_packet_uses_persistent_state_without_causative_confirmed_event():
    world = make_world()
    engine = SimulationEngine()
    engine.resolve_and_commit(compile_action(world, "打开 DOOR_A"), world)
    engine.resolve_and_commit(compile_action(world, "拿起 BOTTLE_A"), world)
    engine.resolve_and_commit(compile_action(world, "走到BACK"), world)
    engine.transition_active_scene("BAR", world)
    engine.transition_active_scene("STREET", world)

    packet = build_render_packet(world, ())
    states = packet_states(packet)
    assert packet.confirmed_events == ()
    assert states["DOOR_A"]["is_open"] is True
    assert states["BOTTLE_A"]["owner_actor_id"] == "PLAYER"
    assert states["BOTTLE_A"]["zone_id"] == "BACK"
    assert validate_packet(packet, states).status == "RENDER_ALIGNED"


def test_b03_actor_zone_scene_mismatch_rejected_before_live_seal():
    world = make_world()
    world.actors["PLAYER"].zone_id = "BAR_ZONE"
    with pytest.raises(ValueError, match="ACTOR_ZONE_SCENE_MISMATCH"):
        world.seal_live()
    assert not world.is_live


def test_b03_object_zone_scene_mismatch_rejected_before_live_seal():
    world = make_world()
    world.objects["BOTTLE_A"].zone_id = "BAR_ZONE"
    with pytest.raises(ValueError, match="OBJECT_ZONE_SCENE_MISMATCH"):
        world.seal_live()
    assert not world.is_live


@pytest.mark.parametrize("kind", ["actor", "object"])
def test_b03_unknown_entity_zone_rejected(kind: str):
    world = make_world()
    if kind == "actor":
        world.actors["PLAYER"].zone_id = "UNKNOWN_ZONE"
        pattern = "ACTOR_ZONE_UNKNOWN"
    else:
        world.objects["BOTTLE_A"].zone_id = "UNKNOWN_ZONE"
        pattern = "OBJECT_ZONE_UNKNOWN"
    with pytest.raises(ValueError, match=pattern):
        world.seal_live()


def test_b03_unknown_adjacency_endpoint_rejected():
    world = make_world()
    world.zone_adjacency_pairs.add(("FRONT", "UNKNOWN_ZONE"))
    with pytest.raises(ValueError, match="ZONE_ADJACENCY_UNKNOWN_ENDPOINT"):
        world.seal_live()


def test_b03_cross_scene_adjacency_rejected():
    world = make_world()
    world.zone_adjacency_pairs.add(("FRONT", "BAR_ZONE"))
    with pytest.raises(ValueError, match="ZONE_ADJACENCY_CROSS_SCENE"):
        world.seal_live()


def test_b03_forged_walk_from_zone_rejected_by_event_semantics():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    forged = Event(
        event_id="E-FORGED-WALK",
        event_type="ACTOR_MOVED",
        actor_id="PLAYER",
        scene_id="STREET",
        baseline_version=world.baseline_version,
        payload={"actor_id": "PLAYER", "from_zone_id": "BAR_ZONE", "to_zone_id": "BACK"},
        caused_by_action_id="A-FORGED",
    )
    with pytest.raises(ValueError, match="INVALID_ACTOR_MOVED_FROM_ZONE"):
        SimulationEngine().replay(baseline, (forged,))


def test_b03_valid_same_scene_topology_and_same_zone_reachability_remain_green():
    world = make_world()
    assert world.is_reachable("PLAYER", "BOTTLE_A")
    assert not world.is_reachable("PLAYER", "REMOTE")
    moved = SimulationEngine().resolve_and_commit(compile_action(world, "走到BACK"), world)
    assert moved.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert world.actors["PLAYER"].scene_id == "STREET"
    assert world.actors["PLAYER"].zone_id == "BACK"
    assert world.is_reachable("PLAYER", "REMOTE")
