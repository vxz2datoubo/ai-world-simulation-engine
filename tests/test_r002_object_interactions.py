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
    capture_pristine_baseline,
)


PRINCIPAL = "principal://r002-player"


def make_r002_world(
    *,
    free_hands: int = 2,
    visible_pairs: set[tuple[str, str]] | None = None,
) -> WorldState:
    return WorldState(
        "WORLD_R002",
        "STREET_001",
        "R002-TEST-BASELINE-v1",
        actors={
            "PLAYER": ActorState(
                "PLAYER",
                "玩家",
                "STREET_001",
                free_hands=free_hands,
                capabilities={
                    "SPEAK",
                    "HIT",
                    "PICK",
                    "DROP",
                    "THROW",
                    "OPEN",
                    "CLOSE",
                    "WALK",
                },
                zone_id="ZONE_FRONT",
            ),
            "GUARD_001": ActorState(
                "GUARD_001",
                "守卫",
                "STREET_001",
                zone_id="ZONE_FRONT",
            ),
            "BYSTANDER_001": ActorState(
                "BYSTANDER_001",
                "路人",
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
            "CRATE_001": ObjectState(
                "CRATE_001",
                "木箱",
                "STREET_001",
                20.0,
                False,
                0.3,
                zone_id="ZONE_FRONT",
                affordances={"PICK"},
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
            "REMOTE_001": ObjectState(
                "REMOTE_001",
                "遥控器",
                "STREET_001",
                0.2,
                True,
                0.2,
                zone_id="ZONE_BACK",
                affordances={"PICK", "DROP", "THROW"},
            ),
        },
        npc_minds={
            "GUARD_001": NPCMindState("GUARD_001", "GUARD"),
            "BYSTANDER_001": NPCMindState("BYSTANDER_001", "BYSTANDER"),
        },
        scenes={
            "STREET_001": SceneState(
                "STREET_001",
                ["asset://street/master"],
                ["BOTTLE_001", "CRATE_001", "DOOR_001", "REMOTE_001"],
                ["PLAYER", "GUARD_001", "BYSTANDER_001"],
            ),
            "BAR_001": SceneState("BAR_001", ["asset://bar/master"]),
        },
        principal_actor_bindings={PRINCIPAL: {"PLAYER"}},
        visible_pairs=set() if visible_pairs is None else visible_pairs,
        zone_scene_bindings={
            "ZONE_FRONT": "STREET_001",
            "ZONE_BACK": "STREET_001",
            "ZONE_SIDE": "STREET_001",
            "BAR_ZONE": "BAR_001",
        },
        zone_adjacency_pairs={
            ("ZONE_FRONT", "ZONE_BACK"),
            ("ZONE_BACK", "ZONE_SIDE"),
        },
    )


def compile_r002(world: WorldState, text: str):
    return ActionCompiler().compile(text, "PLAYER", world, PRINCIPAL)


def test_r002_01_reachable_graspable_object_can_be_picked_and_becomes_possessed():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起酒瓶"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert resolution.events[0].event_type == "OBJECT_PICKED_UP"
    assert world.objects["BOTTLE_001"].owner_actor_id == "PLAYER"
    assert world.objects["BOTTLE_001"].zone_id == "ZONE_FRONT"
    assert world.actors["PLAYER"].inventory_refs == ("BOTTLE_001",)
    assert world.actors["PLAYER"].free_hands == 1


def test_r002_02_non_graspable_object_cannot_be_picked_up():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起木箱"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "TARGET_NOT_GRASPABLE"
    assert world.objects["CRATE_001"].owner_actor_id is None
    assert tuple(world.event_log) == ()


def test_r002_03_unreachable_object_cannot_be_picked_up():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起遥控器"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "TARGET_NOT_REACHABLE"
    assert world.objects["REMOTE_001"].owner_actor_id is None


def test_r002_04_no_free_hand_condition_fails_closed():
    world = make_r002_world(free_hands=0)
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起酒瓶"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "NO_FREE_HAND"
    assert world.actors["PLAYER"].inventory_refs == ()


def test_r002_05_drop_updates_possession_location_and_replays_correctly():
    world = make_r002_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()
    engine.resolve_and_commit(compile_r002(world, "拿起酒瓶"), world)
    drop = engine.resolve_and_commit(compile_r002(world, "放下酒瓶"), world)

    assert drop.events[0].event_type == "OBJECT_DROPPED"
    assert world.objects["BOTTLE_001"].owner_actor_id is None
    assert world.objects["BOTTLE_001"].scene_id == "STREET_001"
    assert world.objects["BOTTLE_001"].zone_id == "ZONE_FRONT"
    assert world.actors["PLAYER"].inventory_refs == ()
    assert world.actors["PLAYER"].free_hands == 2

    replayed = engine.replay(baseline, tuple(world.event_log))
    assert replayed.objects["BOTTLE_001"].owner_actor_id is None
    assert replayed.objects["BOTTLE_001"].zone_id == "ZONE_FRONT"
    assert replayed.actors["PLAYER"].inventory_refs == ()
    assert replayed.actors["PLAYER"].free_hands == 2


@pytest.mark.parametrize("text", ["放下酒瓶", "扔酒瓶"])
def test_r002_06_drop_or_throw_unpossessed_object_fails_closed(text: str):
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, text),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "OBJECT_NOT_POSSESSED"
    assert tuple(world.event_log) == ()


def test_r002_07_unsupported_affordance_opening_non_openable_object_fails_closed():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "打开酒瓶"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "AFFORDANCE_MISSING"
    assert world.objects["BOTTLE_001"].is_open is False


def test_r002_08_movement_outside_explicit_topology_fails_closed():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "走到ZONE_SIDE"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.REJECTED_PRECONDITION
    assert resolution.action.failure_reason == "TARGET_ZONE_NOT_ADJACENT"
    assert world.actors["PLAYER"].zone_id == "ZONE_FRONT"
    assert tuple(world.event_log) == ()


def test_r002_09_valid_movement_changes_reachability_without_scene_identity_drift():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "走到ZONE_BACK"),
        world,
    )

    assert resolution.action.resolution_status == ResolutionStatus.RESOLVED_SUCCESS
    assert resolution.events[0].event_type == "ACTOR_MOVED"
    assert world.actors["PLAYER"].zone_id == "ZONE_BACK"
    assert world.actors["PLAYER"].scene_id == "STREET_001"
    assert world.active_scene_id == "STREET_001"
    assert world.is_reachable("PLAYER", "REMOTE_001")
    assert not world.is_reachable("PLAYER", "BOTTLE_001")


def test_r002_10_object_interaction_state_survives_revisit_and_replay():
    world = make_r002_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()

    engine.resolve_and_commit(compile_r002(world, "打开铁门"), world)
    engine.resolve_and_commit(compile_r002(world, "拿起酒瓶"), world)
    engine.resolve_and_commit(compile_r002(world, "走到ZONE_BACK"), world)
    engine.resolve_and_commit(compile_r002(world, "放下酒瓶"), world)
    engine.transition_active_scene("BAR_001", world)
    engine.transition_active_scene("STREET_001", world)

    assert world.objects["DOOR_001"].is_open is True
    assert world.objects["BOTTLE_001"].owner_actor_id is None
    assert world.objects["BOTTLE_001"].zone_id == "ZONE_BACK"
    assert world.objects["BOTTLE_001"].scene_id == "STREET_001"

    replayed = engine.replay(baseline, tuple(world.event_log))
    assert replayed.active_scene_id == "STREET_001"
    assert replayed.objects["DOOR_001"].is_open is True
    assert replayed.objects["BOTTLE_001"].owner_actor_id is None
    assert replayed.objects["BOTTLE_001"].zone_id == "ZONE_BACK"


def test_r002_11_unwitnessed_object_event_does_not_leak_into_npc_knowledge():
    world = make_r002_world()
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起酒瓶"),
        world,
    )
    source = next(event for event in resolution.events if event.event_type == "OBJECT_PICKED_UP")

    assert source.event_id not in world.npc_minds["GUARD_001"].knowledge_boundary_refs
    assert source.event_id not in world.npc_minds["BYSTANDER_001"].knowledge_boundary_refs


def test_r002_12_witnessed_object_event_uses_explicit_visible_pair_path():
    world = make_r002_world(visible_pairs={("BOTTLE_001", "GUARD_001")})
    resolution = SimulationEngine().resolve_and_commit(
        compile_r002(world, "拿起酒瓶"),
        world,
    )
    source = next(event for event in resolution.events if event.event_type == "OBJECT_PICKED_UP")
    knowledge = [
        event
        for event in resolution.events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
    ]

    assert len(knowledge) == 1
    assert knowledge[0].payload["npc_id"] == "GUARD_001"
    assert knowledge[0].payload["mode"] == "SAW"
    assert knowledge[0].payload["source_event_id"] == source.event_id
    assert source.event_id in world.npc_minds["GUARD_001"].knowledge_boundary_refs
    assert source.event_id not in world.npc_minds["BYSTANDER_001"].knowledge_boundary_refs


def test_r002_13_live_state_assignment_and_deletion_guards_cover_new_fields():
    world = make_r002_world()
    SimulationEngine().resolve_and_commit(compile_r002(world, "拿起酒瓶"), world)

    before_version = world.state_version
    before_owner = world.objects["BOTTLE_001"].owner_actor_id
    before_zone = world.actors["PLAYER"].zone_id
    before_affordances = world.objects["BOTTLE_001"].affordances

    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        world.objects["BOTTLE_001"].owner_actor_id = None
    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        world.actors["PLAYER"].zone_id = "ZONE_SIDE"
    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        del world.objects["BOTTLE_001"].affordances
    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        del world.actors["PLAYER"].zone_id
    with pytest.raises(AttributeError, match="LIVE_CANONICAL_STATE_IS_READ_ONLY"):
        del world.state_version

    assert world.state_version == before_version
    assert world.objects["BOTTLE_001"].owner_actor_id == before_owner
    assert world.actors["PLAYER"].zone_id == before_zone
    assert world.objects["BOTTLE_001"].affordances == before_affordances


def test_r002_14_positive_open_close_transitions_are_event_sourced():
    world = make_r002_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()

    opened = engine.resolve_and_commit(compile_r002(world, "打开铁门"), world)
    closed = engine.resolve_and_commit(compile_r002(world, "关上铁门"), world)

    assert opened.events[0].event_type == "OBJECT_OPENED"
    assert closed.events[0].event_type == "OBJECT_CLOSED"
    assert world.objects["DOOR_001"].is_open is False

    replayed = engine.replay(baseline, tuple(world.event_log))
    assert replayed.objects["DOOR_001"].is_open is False
    assert replayed.state_version == world.state_version


def test_r002_15_positive_throw_releases_possession_into_current_zone():
    world = make_r002_world()
    engine = SimulationEngine()
    engine.resolve_and_commit(compile_r002(world, "拿起酒瓶"), world)
    engine.resolve_and_commit(compile_r002(world, "走到ZONE_BACK"), world)
    thrown = engine.resolve_and_commit(compile_r002(world, "扔酒瓶"), world)

    assert thrown.events[0].event_type == "OBJECT_THROWN"
    assert world.objects["BOTTLE_001"].owner_actor_id is None
    assert world.objects["BOTTLE_001"].zone_id == "ZONE_BACK"
    assert world.actors["PLAYER"].inventory_refs == ()
    assert world.actors["PLAYER"].free_hands == 2


def test_r002_16_r001_world_without_symbolic_substrate_keeps_new_families_fail_closed():
    world = WorldState(
        "LEGACY",
        "STREET",
        "R001-LEGACY-v1",
        actors={"PLAYER": ActorState("PLAYER", "玩家", "STREET")},
        objects={"WINDOW": ObjectState("WINDOW", "窗户", "STREET")},
        scenes={"STREET": SceneState("STREET")},
        principal_actor_bindings={PRINCIPAL: {"PLAYER"}},
        reachable_pairs={("PLAYER", "WINDOW")},
    )

    action = ActionCompiler().compile("打开窗户", "PLAYER", world, PRINCIPAL)
    resolution = SimulationEngine().resolve_and_commit(action, world)

    assert resolution.action.resolution_status == ResolutionStatus.RESOLVED_FAILURE
    assert resolution.action.failure_reason == "UNIMPLEMENTED_ACTION_FAMILY"
    assert tuple(world.event_log) == ()
