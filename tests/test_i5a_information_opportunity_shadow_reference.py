import base64
import hashlib
import json

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
from awrse.model import thaw_value
from evals.i5a_information_opportunity_shadow_reference import (
    I5_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_LLM_OR_PROVIDER,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PRODUCTION_ENCOUNTER_DENSITY_POLICY,
    NO_PX_SCORING,
    NO_WORLD_MUTATION,
    ShadowPlausibilityFixture,
    build_information_opportunity_shadow,
    export_information_opportunity_shadow_package,
    replay_information_opportunity_shadow_package,
)

SOURCE = "ACTOR_CAPITAL"
CARRIER = "NPC_MERCHANT"
PLAYER = "PLAYER_WILDERNESS"
NOTICE = "NOTICE_BOARD"
CAPITAL = "SCENE_CAPITAL"
WILDERNESS = "SCENE_WILDERNESS"
PRINCIPAL = "principal://i5a/source"
BASELINE_VERSION = "I5A-BASELINE-v1"

INFO_FIELDS = {"info_id", "source_fact_or_event_refs", "classification", "source_refs", "verification_state", "confidence", "distortion_policy", "created_world_time", "propagation_scope", "expiry_policy"}
BROKER_FIELDS = {"broker_contract_version", "input_refs", "candidate_policy_ref", "plausibility_gate_ref"}
GATE_FIELDS = {"gate_version", "spatial_checks", "temporal_checks", "identity_history_checks", "motivation_checks", "information_provenance_checks", "density_checks", "asset_availability_checks", "anti_repeat_checks"}
CANDIDATE_FIELDS = {"encounter_id", "source_goal_refs", "world_scope", "time_window", "actor_candidate_refs", "motivation_refs", "known_information_refs", "affordance_refs", "forbidden_inventions", "eligibility_evidence", "expiry_policy"}


def make_world(*, carrier_can_see: bool = True) -> WorldState:
    return WorldState(
        world_id="WORLD_I5A",
        active_scene_id=CAPITAL,
        baseline_version=BASELINE_VERSION,
        actors={
            SOURCE: ActorState(SOURCE, "都城卫兵", CAPITAL, capabilities={"HIT"}),
            CARRIER: ActorState(CARRIER, "行商", CAPITAL, capabilities={"SPEAK"}),
            PLAYER: ActorState(PLAYER, "旅人", WILDERNESS, capabilities={"SPEAK"}),
        },
        objects={
            NOTICE: ObjectState(NOTICE, "公告牌", CAPITAL, mass=20.0, graspable=False, fragility=0.5),
        },
        npc_minds={CARRIER: NPCMindState(CARRIER, "MERCHANT")},
        scenes={
            CAPITAL: SceneState(CAPITAL, ["asset://i5a/capital"], [NOTICE], [SOURCE, CARRIER]),
            WILDERNESS: SceneState(WILDERNESS, ["asset://i5a/wilderness"], [], [PLAYER]),
        },
        principal_actor_bindings={PRINCIPAL: {SOURCE}},
        reachable_pairs={(SOURCE, NOTICE)},
        visible_pairs={(NOTICE, CARRIER)} if carrier_can_see else set(),
    )


def build_source_world(*, carrier_can_see: bool = True):
    world = make_world(carrier_can_see=carrier_can_see)
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸公告牌", SOURCE, world, PRINCIPAL)
    result = SimulationEngine().resolve_and_commit(action, world)
    source_event = next(event for event in result.events if event.event_type == "OBJECT_DAMAGED")
    return baseline, world, source_event.event_id


def valid_fixture(**overrides):
    values = {
        "fixture_id": "I5A-WILDERNESS-ROUTE-001",
        "target_scene_id": WILDERNESS,
        "carrier_origin_scene_id": CAPITAL,
        "route_available": True,
        "travel_steps_required": 3,
        "travel_steps_available": 5,
        "identity_history_consistent": True,
        "motivation_ref": "MOTIVE:MERCHANT_TRAVEL_TO_NEXT_MARKET",
        "anti_repeat_allowed": True,
        "asset_available": True,
    }
    values.update(overrides)
    return ShadowPlausibilityFixture(**values)


def build_shadow(*, fixture=None, carrier_can_see=True):
    baseline, world, source_event_id = build_source_world(carrier_can_see=carrier_can_see)
    result = build_information_opportunity_shadow(
        baseline=baseline,
        world=world,
        source_event_id=source_event_id,
        carrier_npc_id=CARRIER,
        player_actor_id=PLAYER,
        fixture=fixture or valid_fixture(),
    )
    return baseline, world, source_event_id, result


def canonical_json_bytes(value) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def refresh_outer_digest(envelope: dict) -> bytes:
    envelope["sha256"] = hashlib.sha256(canonical_json_bytes(envelope["payload"])).hexdigest()
    return canonical_json_bytes(envelope)


def test_i5a_scope_locks_are_shadow_only():
    assert I5_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_WORLD_MUTATION is True
    assert NO_PRODUCTION_ENCOUNTER_DENSITY_POLICY is True
    assert NO_PX_SCORING is True
    assert NO_LLM_OR_PROVIDER is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i5a_valid_wilderness_information_opportunity_is_noncanonical_shadow_candidate():
    _, world, source_event_id, result = build_shadow()
    assert result.status == "SHADOW_ENCOUNTER_CANDIDATE"
    assert result.source_event_id == source_event_id
    assert set(result.information_packet) == INFO_FIELDS
    assert set(result.broker) == BROKER_FIELDS
    assert set(result.plausibility_gate) == GATE_FIELDS
    assert result.encounter_candidate is not None
    assert set(result.encounter_candidate) == CANDIDATE_FIELDS
    info = thaw_value(result.information_packet)
    candidate = thaw_value(result.encounter_candidate)
    assert info["source_fact_or_event_refs"] == [source_event_id]
    assert len(info["source_refs"]) == 1
    assert info["verification_state"] == "DIRECT_WITNESS_REFERENCE_ONLY"
    assert candidate["world_scope"]["shadow_only"] is True
    assert "NO_WORLD_EVENT_COMMIT" in candidate["forbidden_inventions"]
    assert "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE" in candidate["forbidden_inventions"]
    assert world.actors[PLAYER].scene_id == WILDERNESS
    assert world.actors[CARRIER].scene_id == CAPITAL


def test_i5a_importance_alone_does_not_create_player_knowledge_or_world_mutation():
    baseline, world, source_event_id = build_source_world()
    before_event_ids = tuple(event.event_id for event in world.event_log)
    before_committed = frozenset(world.committed_event_ids)
    before_carrier_memories = tuple(world.npc_minds[CARRIER].memories)
    before_player_scene = world.actors[PLAYER].scene_id
    result = build_information_opportunity_shadow(
        baseline=baseline,
        world=world,
        source_event_id=source_event_id,
        carrier_npc_id=CARRIER,
        player_actor_id=PLAYER,
        fixture=valid_fixture(),
    )
    assert result.status == "SHADOW_ENCOUNTER_CANDIDATE"
    assert tuple(event.event_id for event in world.event_log) == before_event_ids
    assert frozenset(world.committed_event_ids) == before_committed
    assert tuple(world.npc_minds[CARRIER].memories) == before_carrier_memories
    assert world.actors[PLAYER].scene_id == before_player_scene
    assert not [event for event in world.event_log if event.event_type == "NPC_KNOWLEDGE_ACQUIRED" and event.payload.get("npc_id") == PLAYER and event.payload.get("source_event_id") == source_event_id]


def test_i5a_caller_cannot_mint_information_packet():
    baseline, world, source_event_id = build_source_world()
    with pytest.raises(ValueError, match="I5A_CALLER_AUTHORED_INFORMATION_PACKET_FORBIDDEN"):
        build_information_opportunity_shadow(
            baseline=baseline,
            world=world,
            source_event_id=source_event_id,
            carrier_npc_id=CARRIER,
            player_actor_id=PLAYER,
            fixture=valid_fixture(),
            caller_information_packet={"info_id": "FORGED", "source_fact_or_event_refs": ["INVENTED"], "verification_state": "CONFIRMED"},
        )


def test_i5a_carrier_without_valid_acquisition_cannot_carry_fact():
    baseline, world, source_event_id = build_source_world(carrier_can_see=False)
    with pytest.raises(ValueError, match="I5A_CARRIER_SOURCE_ACQUISITION_REQUIRED_EXACTLY_ONCE"):
        build_information_opportunity_shadow(
            baseline=baseline,
            world=world,
            source_event_id=source_event_id,
            carrier_npc_id=CARRIER,
            player_actor_id=PLAYER,
            fixture=valid_fixture(),
        )


@pytest.mark.parametrize(
    ("fixture", "reason"),
    [
        (valid_fixture(route_available=False), "NO_VALID_ROUTE"),
        (valid_fixture(travel_steps_required=9, travel_steps_available=2), "INSUFFICIENT_TRAVEL_TIME"),
        (valid_fixture(identity_history_consistent=False), "IDENTITY_HISTORY_CONFLICT"),
        (valid_fixture(motivation_ref=None), "MOTIVATION_EVIDENCE_MISSING"),
        (valid_fixture(asset_available=False), "REFERENCE_ASSET_UNAVAILABLE"),
        (valid_fixture(anti_repeat_allowed=False), "ANTI_REPEAT_GATE_REJECTED"),
        (valid_fixture(target_scene_id=CAPITAL), "TARGET_SCENE_NOT_PLAYER_LOCATION"),
        (valid_fixture(carrier_origin_scene_id=WILDERNESS), "CARRIER_ORIGIN_HISTORY_CONFLICT"),
    ],
)
def test_i5a_plausibility_failures_return_first_class_no_valid_opportunity(fixture, reason):
    _, _, _, result = build_shadow(fixture=fixture)
    assert result.status == "NO_VALID_OPPORTUNITY"
    assert result.encounter_candidate is None
    assert reason in result.rejection_reasons


def test_i5a_no_valid_opportunity_is_legal_deterministic_result_not_exception():
    fixture = valid_fixture(route_available=False, anti_repeat_allowed=False)
    baseline, world, source_event_id = build_source_world()
    first = build_information_opportunity_shadow(
        baseline=baseline,
        world=world,
        source_event_id=source_event_id,
        carrier_npc_id=CARRIER,
        player_actor_id=PLAYER,
        fixture=fixture,
    )
    second = build_information_opportunity_shadow(
        baseline=baseline,
        world=world,
        source_event_id=source_event_id,
        carrier_npc_id=CARRIER,
        player_actor_id=PLAYER,
        fixture=fixture,
    )
    assert first.status == second.status == "NO_VALID_OPPORTUNITY"
    assert first.rejection_reasons == second.rejection_reasons
    assert thaw_value(first.plausibility_gate) == thaw_value(second.plausibility_gate)


def test_i5a_forged_reference_authority_label_fails_closed():
    fixture = valid_fixture(authority_class="CANONICAL_WORLD_ROUTE_AUTHORITY_I_PROMISE")
    baseline, world, source_event_id = build_source_world()
    with pytest.raises(ValueError, match="I5A_REFERENCE_FIXTURE_AUTHORITY_CLASS_INVALID"):
        build_information_opportunity_shadow(
            baseline=baseline,
            world=world,
            source_event_id=source_event_id,
            carrier_npc_id=CARRIER,
            player_actor_id=PLAYER,
            fixture=fixture,
        )


def test_i5a_invented_source_event_fails_closed():
    baseline, world, _ = build_source_world()
    with pytest.raises(ValueError, match="I5A_SOURCE_EVENT_NOT_CANONICAL"):
        build_information_opportunity_shadow(
            baseline=baseline,
            world=world,
            source_event_id="E-INVENTED",
            carrier_npc_id=CARRIER,
            player_actor_id=PLAYER,
            fixture=valid_fixture(),
        )


def test_i5a_candidate_cannot_declare_dialogue_success_movement_or_capability_override():
    _, _, _, result = build_shadow()
    candidate = thaw_value(result.encounter_candidate)
    forbidden = set(candidate["forbidden_inventions"])
    assert {"NO_WORLD_EVENT_COMMIT", "NO_ACTOR_SPAWN_OR_MOVEMENT", "NO_PLAYER_OR_NPC_KNOWLEDGE_MUTATION", "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE", "NO_FORCED_DIALOGUE_OR_SUCCESS", "NO_PX_DIRECTOR_RENDERER_ADMISSION_AUTHORITY"} <= forbidden
    assert candidate["affordance_refs"] == ["REFERENCE_CONVERSATION_POSSIBLE_NOT_COMMITTED"]


def test_i5a_same_inputs_produce_materially_deterministic_shadow():
    baseline, world, source_event_id = build_source_world()
    fixture = valid_fixture()
    first = build_information_opportunity_shadow(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=fixture)
    second = build_information_opportunity_shadow(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=fixture)
    assert first == second


def test_i5a_shadow_package_is_byte_deterministic_and_replays_exactly():
    baseline, world, source_event_id = build_source_world()
    kwargs = dict(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=valid_fixture())
    first = export_information_opportunity_shadow_package(**kwargs)
    second = export_information_opportunity_shadow_package(**kwargs)
    assert first == second
    rebuilt = replay_information_opportunity_shadow_package(first)
    expected = build_information_opportunity_shadow(**kwargs)
    assert rebuilt == expected


def test_i5a_outer_shadow_package_tamper_fails_before_rebuild():
    baseline, world, source_event_id = build_source_world()
    envelope = json.loads(export_information_opportunity_shadow_package(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=valid_fixture()).decode("utf-8"))
    envelope["payload"]["player_actor_id"] = SOURCE
    with pytest.raises(ValueError, match="I5A_SHADOW_PACKAGE_TAMPERED"):
        replay_information_opportunity_shadow_package(canonical_json_bytes(envelope))


def test_i5a_forged_expected_result_with_recomputed_outer_digest_fails_closed():
    baseline, world, source_event_id = build_source_world()
    envelope = json.loads(export_information_opportunity_shadow_package(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=valid_fixture()).decode("utf-8"))
    envelope["payload"]["expected_result"]["status"] = "CANONICAL_ENCOUNTER_COMMITTED"
    with pytest.raises(ValueError, match="I5A_SHADOW_RESULT_MATERIALIZATION_MISMATCH"):
        replay_information_opportunity_shadow_package(refresh_outer_digest(envelope))


def test_i5a_fixture_tamper_with_recomputed_outer_digest_cannot_launder_gate_result():
    baseline, world, source_event_id = build_source_world()
    envelope = json.loads(export_information_opportunity_shadow_package(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=valid_fixture()).decode("utf-8"))
    envelope["payload"]["fixture"]["route_available"] = False
    with pytest.raises(ValueError, match="I5A_SHADOW_RESULT_MATERIALIZATION_MISMATCH"):
        replay_information_opportunity_shadow_package(refresh_outer_digest(envelope))


def test_i5a_inner_i1_history_tamper_cannot_be_laundered_by_outer_digest():
    baseline, world, source_event_id = build_source_world()
    envelope = json.loads(export_information_opportunity_shadow_package(baseline=baseline, world=world, source_event_id=source_event_id, carrier_npc_id=CARRIER, player_actor_id=PLAYER, fixture=valid_fixture()).decode("utf-8"))
    inner = json.loads(base64.b64decode(envelope["payload"]["source_i1_replay_b64"]).decode("utf-8"))
    inner["expected_state_version"] += 1
    bad_inner = canonical_json_bytes(inner)
    envelope["payload"]["source_i1_replay_b64"] = base64.b64encode(bad_inner).decode("ascii")
    envelope["payload"]["source_i1_replay_sha256"] = hashlib.sha256(bad_inner).hexdigest()
    with pytest.raises(ValueError, match="PERSISTENCE_PACKAGE_INTEGRITY_FAILURE"):
        replay_information_opportunity_shadow_package(refresh_outer_digest(envelope))
