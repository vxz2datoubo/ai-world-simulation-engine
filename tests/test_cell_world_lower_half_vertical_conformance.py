from runtime.awrse import (
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
    export_solo_replay_package,
    import_solo_replay_package,
    rehydrate_solo_replay_package,
    validate_render_claims,
)


def _bootstrap_cell_world() -> WorldState:
    return WorldState(
        world_id="CELL-WORLD-001-A",
        active_scene_id="S1",
        baseline_version="CELL-WORLD-R1",
        primary_player_actor_id="A",
        actors={
            "A": ActorState(
                actor_id="A",
                name="玩家",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"PICK"},
            ),
            "B": ActorState(
                actor_id="B",
                name="目击者",
                scene_id="S1",
                zone_id="Z1",
                capabilities={"SPEAK"},
            ),
        },
        objects={
            "O": ObjectState(
                object_id="O",
                name="钥匙",
                scene_id="S1",
                zone_id="Z1",
                graspable=True,
                affordances={"PICK"},
            )
        },
        npc_minds={
            "B": NPCMindState(npc_id="B", role="WITNESS")
        },
        scenes={
            "S1": SceneState(
                scene_id="S1",
                base_asset_refs=["asset://cell-room"],
                object_state_refs=["O"],
                actor_state_refs=["A", "B"],
            )
        },
        principal_actor_bindings={"P1": {"A"}},
        visible_pairs={("O", "B")},
        zone_scene_bindings={"Z1": "S1"},
    )


def _rendered_object_truth(owner_actor_id="A"):
    return {
        "O": {
            "damage_state": "INTACT",
            "contamination_state": "CLEAN",
            "is_open": False,
            "owner_actor_id": owner_actor_id,
            "zone_id": "Z1",
        }
    }


def test_lower_half_cell_runs_from_natural_language_to_replay_and_render_truth():
    world = _bootstrap_cell_world()
    baseline = capture_pristine_baseline(world)

    action = ActionCompiler().compile("拿起钥匙", "A", world, principal_id="P1")
    assert action.verb == "PICK"
    assert action.target_ids == ["O"]
    assert action.literal_user_input == "拿起钥匙"
    assert action.authority_scope.may_control_actor is True

    resolution = SimulationEngine().resolve_and_commit(action, world)
    assert resolution.action.resolution_status is ResolutionStatus.RESOLVED_SUCCESS
    assert [event.event_type for event in resolution.events] == [
        "OBJECT_PICKED_UP",
        "NPC_KNOWLEDGE_ACQUIRED",
    ]

    pick_event, witness_event = resolution.events
    assert witness_event.payload["mode"] == "SAW"
    assert witness_event.payload["source_event_id"] == pick_event.event_id
    assert witness_event.payload["npc_id"] == "B"

    # Canonical event evidence drives both possession and recipient-local knowledge projection.
    assert world.objects["O"].owner_actor_id == "A"
    assert tuple(world.actors["A"].inventory_refs) == ("O",)
    assert world.actors["A"].free_hands == 1
    assert pick_event.event_id in world.npc_minds["B"].knowledge_boundary_refs
    assert witness_event.event_id in world.npc_minds["B"].memories
    assert tuple(world.event_log) == resolution.events
    assert world.state_version == len(resolution.events) == 2

    # Persistence authority is pristine baseline + ordered canonical events, never a serialized projection shortcut.
    package = export_solo_replay_package(baseline, world)
    evidence = import_solo_replay_package(package)
    assert evidence.world_id == world.world_id
    assert evidence.baseline_version == world.baseline_version
    assert tuple(event.event_id for event in evidence.events) == tuple(
        event.event_id for event in world.event_log
    )
    assert evidence.expected_state_version == world.state_version

    rebuilt = rehydrate_solo_replay_package(package)
    assert rebuilt.is_live is True
    assert rebuilt.world_state_version == world.world_state_version
    assert rebuilt.objects["O"].owner_actor_id == "A"
    assert tuple(rebuilt.actors["A"].inventory_refs) == ("O",)
    assert rebuilt.actors["A"].free_hands == 1
    assert tuple(rebuilt.npc_minds["B"].knowledge_boundary_refs) == tuple(
        world.npc_minds["B"].knowledge_boundary_refs
    )
    assert tuple(rebuilt.npc_minds["B"].memories) == tuple(world.npc_minds["B"].memories)
    assert tuple(event.event_id for event in rebuilt.event_log) == tuple(
        event.event_id for event in world.event_log
    )

    # Renderer receives only replayed/canonical truth and can validate a faithful projection.
    packet = build_render_packet(rebuilt, rebuilt.event_log)
    aligned = validate_render_claims(
        packet,
        rendered_event_ids={event.event_id for event in packet.confirmed_events},
        rendered_object_states=_rendered_object_truth("A"),
        rendered_scene_id=packet.scene_id,
        rendered_actor_state_refs=packet.actor_state_refs,
        rendered_camera=packet.camera,
    )
    assert aligned.status == "RENDER_ALIGNED"


def test_hostile_presentation_claims_fail_closed_without_mutating_world_truth():
    world = _bootstrap_cell_world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("拿起钥匙", "A", world, principal_id="P1")
    SimulationEngine().resolve_and_commit(action, world)
    rebuilt = rehydrate_solo_replay_package(export_solo_replay_package(baseline, world))
    packet = build_render_packet(rebuilt, rebuilt.event_log)

    before_owner = rebuilt.objects["O"].owner_actor_id
    before_inventory = tuple(rebuilt.actors["A"].inventory_refs)
    before_event_ids = tuple(event.event_id for event in rebuilt.event_log)

    contradictory = validate_render_claims(
        packet,
        rendered_event_ids={event.event_id for event in packet.confirmed_events},
        rendered_object_states=_rendered_object_truth(None),
        rendered_scene_id=packet.scene_id,
        rendered_actor_state_refs=packet.actor_state_refs,
        rendered_camera=packet.camera,
    )
    assert contradictory.status == "RENDER_MISMATCH"
    assert any(
        item.startswith("OBJECT_STATE:O:owner_actor_id:")
        for item in contradictory.semantic_contradictions
    )

    invented_event = validate_render_claims(
        packet,
        rendered_event_ids={event.event_id for event in packet.confirmed_events} | {"E-INVENTED"},
        rendered_object_states=_rendered_object_truth("A"),
        rendered_scene_id=packet.scene_id,
        rendered_actor_state_refs=packet.actor_state_refs,
        rendered_camera=packet.camera,
    )
    assert invented_event.status == "RENDER_MISMATCH"
    assert "UNCONFIRMED_EVENT_ID:E-INVENTED" in invented_event.unauthorized_claims

    # Presentation failure is never authority to repair or rewrite canonical/replayed truth.
    assert rebuilt.objects["O"].owner_actor_id == before_owner == "A"
    assert tuple(rebuilt.actors["A"].inventory_refs) == before_inventory == ("O",)
    assert tuple(event.event_id for event in rebuilt.event_log) == before_event_ids


def test_unauthorized_player_cannot_enter_cell_event_chain():
    world = _bootstrap_cell_world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("拿起钥匙", "A", world, principal_id="P-UNAUTHORIZED")
    resolution = SimulationEngine().resolve_and_commit(action, world)

    assert resolution.action.resolution_status is ResolutionStatus.REJECTED_AUTHORITY
    assert resolution.events == ()
    assert world.state_version == 0
    assert tuple(world.event_log) == ()
    assert world.objects["O"].owner_actor_id is None
    assert tuple(world.actors["A"].inventory_refs) == ()
    assert tuple(world.npc_minds["B"].knowledge_boundary_refs) == ()

    # A rejected attempted action does not contaminate persistence evidence.
    package = export_solo_replay_package(baseline, world)
    evidence = import_solo_replay_package(package)
    assert evidence.events == ()
    assert evidence.expected_state_version == 0
