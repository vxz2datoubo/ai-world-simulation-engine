import pytest

from awrse import (
    ActionCompiler,
    ActorState,
    NPCMindState,
    ObjectState,
    SceneState,
    SimulationEngine,
    WorldState,
    capture_pristine_baseline,
)
from awrse.model import Event


PRINCIPAL = "principal://r002-player"


def make_world(*, visible_pairs=None):
    return WorldState(
        "WORLD_R002",
        "STREET",
        "R002-B04-B06-v1",
        actors={
            "PLAYER": ActorState(
                "PLAYER",
                "玩家",
                "STREET",
                free_hands=2,
                capabilities={"SPEAK", "HIT", "PICK", "DROP", "THROW", "OPEN", "CLOSE", "WALK"},
                zone_id="FRONT",
            ),
            "NPC": ActorState("NPC", "路人", "STREET", zone_id="FRONT"),
        },
        objects={
            "BOTTLE": ObjectState(
                "BOTTLE", "酒瓶", "STREET", 0.5, True, 0.4,
                zone_id="FRONT", affordances={"PICK", "DROP", "THROW"},
            ),
            "DOOR": ObjectState(
                "DOOR", "铁门", "STREET", 50.0, False, 0.3,
                zone_id="FRONT", affordances={"OPEN", "CLOSE"},
            ),
            "BAR_OBJ": ObjectState(
                "BAR_OBJ", "酒吧杯", "BAR", 0.2, True, 0.2,
                zone_id="BAR_ZONE", affordances={"PICK", "DROP", "THROW"},
            ),
        },
        npc_minds={"NPC": NPCMindState("NPC", "BYSTANDER")},
        scenes={"STREET": SceneState("STREET"), "BAR": SceneState("BAR")},
        principal_actor_bindings={PRINCIPAL: {"PLAYER"}},
        visible_pairs=set() if visible_pairs is None else visible_pairs,
        zone_scene_bindings={"FRONT": "STREET", "BACK": "STREET", "BAR_ZONE": "BAR"},
        zone_adjacency_pairs={("FRONT", "BACK")},
    )


def compile_action(world, text):
    return ActionCompiler().compile(text, "PLAYER", world, PRINCIPAL)


def forge_saw(world, source, observed="BOTTLE", scene="STREET"):
    return Event(
        event_id=f"{source.event_id}-SAW-FORGED",
        event_type="NPC_KNOWLEDGE_ACQUIRED",
        actor_id="PLAYER",
        scene_id=scene,
        baseline_version=world.baseline_version,
        payload={
            "npc_id": "NPC",
            "mode": "SAW",
            "source_event_id": source.event_id,
            "observed_entity_id": observed,
        },
    )


def test_b04_no_visible_pair_forged_saw_rejected():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    source = SimulationEngine().resolve_and_commit(compile_action(world, "拿起酒瓶"), world).events[0]
    with pytest.raises(ValueError, match="INVALID_SAW_VISIBILITY_PATH"):
        SimulationEngine().replay(baseline, (source, forge_saw(world, source)))


def test_b04_wrong_observed_object_rejected_even_if_visible():
    world = make_world(visible_pairs={("BOTTLE", "NPC"), ("DOOR", "NPC")})
    baseline = capture_pristine_baseline(world)
    source = SimulationEngine().resolve_and_commit(compile_action(world, "拿起酒瓶"), world).events[0]
    with pytest.raises(ValueError, match="INVALID_SAW_OBSERVED_ENTITY"):
        SimulationEngine().replay(baseline, (source, forge_saw(world, source, observed="DOOR")))


def test_b04_unsupported_source_event_type_rejected():
    world = make_world(visible_pairs={("BOTTLE", "NPC")})
    baseline = capture_pristine_baseline(world)
    source = Event(
        "SPEECH-1", "SPEECH_UTTERED", "PLAYER", "STREET", world.baseline_version,
        {"literal_content": "hello", "trust_class": "UNTRUSTED_DATA", "authority": "NONE_OVER_TARGET_INTERNAL_STATE"},
    )
    with pytest.raises(ValueError, match="INVALID_SAW_SOURCE_EVENT_TYPE"):
        SimulationEngine().replay(baseline, (source, forge_saw(world, source)))


def test_b04_wrong_source_scene_rejected():
    world = make_world(visible_pairs={("BAR_OBJ", "NPC")})
    baseline = capture_pristine_baseline(world)
    source = Event(
        "BAR-DAMAGE", "OBJECT_DAMAGED", "PLAYER", "BAR", world.baseline_version,
        {"object_id": "BAR_OBJ", "damage_state": "DAMAGED"},
    )
    saw = forge_saw(world, source, observed="BAR_OBJ", scene="STREET")
    with pytest.raises(ValueError, match="INVALID_SAW_SOURCE_SCENE"):
        SimulationEngine().replay(baseline, (source, saw))


def test_b04_genuine_visible_witness_replays_and_live_path_green():
    world = make_world(visible_pairs={("BOTTLE", "NPC")})
    baseline = capture_pristine_baseline(world)
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, "拿起酒瓶"), world)
    assert [event.event_type for event in resolution.events] == ["OBJECT_PICKED_UP", "NPC_KNOWLEDGE_ACQUIRED"]
    replayed = SimulationEngine().replay(baseline, resolution.events)
    source = resolution.events[0]
    assert source.event_id in replayed.npc_minds["NPC"].knowledge_boundary_refs


@pytest.mark.parametrize(
    ("from_zone", "to_zone", "error"),
    [
        ("BACK", "FRONT", "INVALID_OBJECT_PICKED_UP_FROM_ZONE"),
        ("FRONT", "BACK", "INVALID_OBJECT_PICKED_UP_TO_ZONE"),
    ],
)
def test_b05_forged_pick_zone_provenance_rejected_without_persistent_mutation(from_zone, to_zone, error):
    world = make_world()
    baseline = capture_pristine_baseline(world)
    forged = Event(
        f"PICK-{from_zone}-{to_zone}",
        "OBJECT_PICKED_UP",
        "PLAYER",
        "STREET",
        world.baseline_version,
        {"object_id": "BOTTLE", "actor_id": "PLAYER", "from_zone_id": from_zone, "to_zone_id": to_zone},
    )
    before = baseline.instantiate()
    with pytest.raises(ValueError, match=error):
        SimulationEngine().replay(baseline, (forged,))
    after = baseline.instantiate()
    assert after.state_version == before.state_version == 0
    assert tuple(after.event_log) == tuple(before.event_log) == ()
    assert after.objects["BOTTLE"].owner_actor_id == before.objects["BOTTLE"].owner_actor_id is None
    assert after.objects["BOTTLE"].zone_id == before.objects["BOTTLE"].zone_id == "FRONT"


def test_b05_generated_pick_event_replays():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    resolution = SimulationEngine().resolve_and_commit(compile_action(world, "拿起酒瓶"), world)
    replayed = SimulationEngine().replay(baseline, resolution.events)
    assert replayed.objects["BOTTLE"].owner_actor_id == "PLAYER"
    assert replayed.objects["BOTTLE"].zone_id == "FRONT"


def malformed_world(case):
    world = make_world()
    if case == "inventory_owner_none":
        world.actors["PLAYER"].inventory_refs.append("BOTTLE")
    elif case == "owner_missing_inventory":
        world.objects["BOTTLE"].owner_actor_id = "PLAYER"
    elif case == "owner_unknown":
        world.objects["BOTTLE"].owner_actor_id = "GHOST"
    elif case == "inventory_unknown":
        world.actors["PLAYER"].inventory_refs.append("GHOST_OBJECT")
    elif case == "duplicate":
        world.actors["PLAYER"].inventory_refs.extend(["BOTTLE", "BOTTLE"])
        world.objects["BOTTLE"].owner_actor_id = "PLAYER"
    elif case == "multiple_inventories":
        world.actors["PLAYER"].inventory_refs.append("BOTTLE")
        world.actors["NPC"].inventory_refs.append("BOTTLE")
        world.objects["BOTTLE"].owner_actor_id = "PLAYER"
    elif case == "carried_scene":
        world.actors["PLAYER"].inventory_refs.append("BOTTLE")
        world.objects["BOTTLE"].owner_actor_id = "PLAYER"
        world.objects["BOTTLE"].scene_id = "BAR"
        world.objects["BOTTLE"].zone_id = "BAR_ZONE"
    elif case == "carried_zone":
        world.actors["PLAYER"].inventory_refs.append("BOTTLE")
        world.objects["BOTTLE"].owner_actor_id = "PLAYER"
        world.objects["BOTTLE"].zone_id = "BACK"
    return world


@pytest.mark.parametrize(
    "case",
    [
        "inventory_owner_none",
        "owner_missing_inventory",
        "owner_unknown",
        "inventory_unknown",
        "duplicate",
        "multiple_inventories",
        "carried_scene",
        "carried_zone",
    ],
)
def test_b06_malformed_possession_graph_rejected(case):
    world = malformed_world(case)
    with pytest.raises(ValueError):
        capture_pristine_baseline(world)
    with pytest.raises(ValueError):
        world.seal_live()


def test_b06_valid_pick_walk_drop_and_replay_consistent():
    world = make_world()
    baseline = capture_pristine_baseline(world)
    engine = SimulationEngine()
    engine.resolve_and_commit(compile_action(world, "拿起酒瓶"), world)
    engine.resolve_and_commit(compile_action(world, "走到BACK"), world)
    engine.resolve_and_commit(compile_action(world, "放下酒瓶"), world)
    world._validate_possession_integrity()
    replayed = engine.replay(baseline, tuple(world.event_log))
    replayed._validate_possession_integrity()
    assert replayed.objects["BOTTLE"].owner_actor_id is None
    assert replayed.objects["BOTTLE"].zone_id == "BACK"
    assert replayed.actors["PLAYER"].inventory_refs == ()
