import base64
import hashlib
import json

import pytest

import evals.i6a_encounter_orchestration_reference as i6a_reference
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
    ShadowPlausibilityFixture,
    export_information_opportunity_shadow_package,
    replay_information_opportunity_shadow_package,
)
from evals.i6a_encounter_orchestration_reference import (
    AuthoredEncounterOrchestrationFixture,
    I6_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED,
    NO_AUTO_ENCOUNTER_COMMIT,
    NO_AUTO_PLAYER_ACTION,
    NO_AUTO_SPEECH_OR_KNOWLEDGE,
    NO_CAPABILITY_OVERRIDE,
    NO_LLM_OR_PROVIDER,
    NO_PARTY_PUBLIC_IMPLEMENTED,
    NO_PX_DIRECTOR_RENDERER,
    build_encounter_orchestration_control_packet,
    export_encounter_orchestration_control_package,
    replay_encounter_orchestration_control_package,
)

SOURCE = "ACTOR_CAPITAL"
CARRIER = "NPC_MERCHANT"
PLAYER = "PLAYER_WILDERNESS"
NOTICE = "NOTICE_BOARD"
CAPITAL = "SCENE_CAPITAL"
WILDERNESS = "SCENE_WILDERNESS"
PRINCIPAL = "principal://i6a/source"
BASELINE_VERSION = "I6A-BASELINE-v1"

EXPECTED_ALLOWED_INTENTS = (
    "help or attempt rescue by force",
    "inspect or use a real tool",
    "seek assistance",
    "ask questions",
    "ignore or leave",
    "threaten, rob or attack if otherwise legal",
    "invent another method subject to authority/affordance/capability checks",
)


def canonical_json_bytes(value) -> bytes:
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def refresh_outer_digest(envelope: dict) -> bytes:
    envelope["sha256"] = hashlib.sha256(
        canonical_json_bytes(envelope["payload"])
    ).hexdigest()
    return canonical_json_bytes(envelope)


def make_world(*, carrier_can_see: bool = True) -> WorldState:
    return WorldState(
        world_id="WORLD_I6A",
        active_scene_id=CAPITAL,
        baseline_version=BASELINE_VERSION,
        actors={
            SOURCE: ActorState(SOURCE, "都城卫兵", CAPITAL, capabilities={"HIT"}),
            CARRIER: ActorState(CARRIER, "行商", CAPITAL, capabilities={"SPEAK"}),
            PLAYER: ActorState(PLAYER, "旅人", WILDERNESS, capabilities={"SPEAK"}),
        },
        objects={
            NOTICE: ObjectState(
                NOTICE,
                "公告牌",
                CAPITAL,
                mass=20.0,
                graspable=False,
                fragility=0.5,
            ),
        },
        npc_minds={CARRIER: NPCMindState(CARRIER, "MERCHANT")},
        scenes={
            CAPITAL: SceneState(
                CAPITAL,
                ["asset://i6a/capital"],
                [NOTICE],
                [SOURCE, CARRIER],
            ),
            WILDERNESS: SceneState(
                WILDERNESS,
                ["asset://i6a/wilderness"],
                [],
                [PLAYER],
            ),
        },
        principal_actor_bindings={PRINCIPAL: {SOURCE}},
        reachable_pairs={(SOURCE, NOTICE)},
        visible_pairs={(NOTICE, CARRIER)} if carrier_can_see else set(),
    )


def make_i5_package(*, route_available: bool = True) -> bytes:
    world = make_world()
    baseline = capture_pristine_baseline(world)
    action = ActionCompiler().compile("砸公告牌", SOURCE, world, PRINCIPAL)
    result = SimulationEngine().resolve_and_commit(action, world)
    source_event = next(
        event for event in result.events if event.event_type == "OBJECT_DAMAGED"
    )
    fixture = ShadowPlausibilityFixture(
        fixture_id="I6A-UPSTREAM-I5-ROUTE-001",
        target_scene_id=WILDERNESS,
        carrier_origin_scene_id=CAPITAL,
        route_available=route_available,
        travel_steps_required=3,
        travel_steps_available=5,
        identity_history_consistent=True,
        motivation_ref="MOTIVE:MERCHANT_TRAVEL_TO_NEXT_MARKET",
        anti_repeat_allowed=True,
        asset_available=True,
    )
    return export_information_opportunity_shadow_package(
        baseline=baseline,
        world=world,
        source_event_id=source_event.event_id,
        carrier_npc_id=CARRIER,
        player_actor_id=PLAYER,
        fixture=fixture,
    )


def make_i6_fixture(i5_package: bytes, **overrides):
    result = replay_information_opportunity_shadow_package(i5_package)
    candidate = thaw_value(result.encounter_candidate)
    information = thaw_value(result.information_packet)
    values = {
        "fixture_id": "I6A-WILDERNESS-ORCHESTRATION-001",
        "candidate_encounter_id": candidate["encounter_id"],
        "source_event_id": result.source_event_id,
        "player_actor_id": result.player_actor_id,
        "carrier_npc_id": result.carrier_npc_id,
        "information_ref": information["info_id"],
    }
    values.update(overrides)
    return AuthoredEncounterOrchestrationFixture(**values)


def build_valid_packet():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    packet = build_encounter_orchestration_control_packet(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    return i5_package, fixture, packet


def _build_with_drifted_golden(tmp_path, monkeypatch, mutate, expected_error):
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    golden = json.loads(i6a_reference._GOLDEN_PATH.read_text(encoding="utf-8"))
    scenario = golden["scenarios"]["WILDERNESS_NEWS_TRAP"]
    mutate(scenario)
    drifted = tmp_path / "AF001-GOLDEN-SCENARIOS-drifted.json"
    drifted.write_text(
        json.dumps(golden, ensure_ascii=False, sort_keys=True),
        encoding="utf-8",
    )
    monkeypatch.setattr(i6a_reference, "_GOLDEN_PATH", drifted)
    with pytest.raises(ValueError, match=expected_error):
        build_encounter_orchestration_control_packet(
            i5_shadow_package=i5_package,
            fixture=fixture,
        )


def test_i6a_scope_locks_preserve_world_and_player_authority():
    assert I6_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert NO_AUTO_ENCOUNTER_COMMIT is True
    assert NO_AUTO_PLAYER_ACTION is True
    assert NO_AUTO_SPEECH_OR_KNOWLEDGE is True
    assert NO_CAPABILITY_OVERRIDE is True
    assert NO_LLM_OR_PROVIDER is True
    assert NO_PX_DIRECTOR_RENDERER is True
    assert NO_PARTY_PUBLIC_IMPLEMENTED is True


def test_i6a_valid_i5_candidate_builds_control_packet_not_encounter_truth():
    i5_package, _, packet = build_valid_packet()
    upstream = replay_information_opportunity_shadow_package(i5_package)
    candidate = thaw_value(upstream.encounter_candidate)
    information = thaw_value(upstream.information_packet)

    assert packet.status == "ORCHESTRATION_CONTROL_PACKET_READY"
    assert packet.candidate_encounter_id == candidate["encounter_id"]
    assert packet.source_event_id == upstream.source_event_id
    assert packet.player_actor_id == PLAYER
    assert packet.carrier_npc_id == CARRIER
    assert packet.known_information_refs == (information["info_id"],)
    assert packet.world_mutation_count == 0
    assert packet.authority_class == "DERIVED_REFERENCE_CONTROL_EVIDENCE_ONLY_NOT_WORLD_TRUTH"
    assert packet.source_i5_sha256 == hashlib.sha256(i5_package).hexdigest()


def test_i6a_requires_explicit_player_decision_before_world_handoff():
    _, _, packet = build_valid_packet()
    handoff = thaw_value(packet.next_authority_handoff)
    assert packet.decision_gate == "AWAIT_EXPLICIT_PLAYER_INTENT"
    assert handoff == {
        "compiler_authority": "runtime.awrse.ActionCompiler",
        "resolver_authority": "runtime.awrse.SimulationEngine",
        "commit_rule": "ONLY_AFTER_EXPLICIT_PLAYER_ACTION_AND_CANONICAL_VALIDATION",
    }
    assert packet.allowed_player_intents == EXPECTED_ALLOWED_INTENTS


def test_i6a_packet_cannot_auto_commit_speech_knowledge_success_or_capability_override():
    _, _, packet = build_valid_packet()
    forbidden = set(packet.forbidden_auto_effects)
    assert {
        "NO_WORLD_EVENT_AUTO_COMMIT",
        "NO_ACTOR_AUTO_SPAWN_OR_MOVEMENT",
        "NO_AUTO_PLAYER_ACTION",
        "NO_AUTO_SPEECH",
        "NO_AUTO_PLAYER_OR_NPC_KNOWLEDGE",
        "NO_AUTO_RESCUE_SUCCESS_OR_FAILURE",
        "NO_CAPABILITY_OR_DIFFICULTY_OVERRIDE",
        "NO_INFORMATION_PROVENANCE_INVENTION",
        "NO_AUTO_QUEST_TRADE_PROMISE_ALLIANCE_ACCEPTANCE",
        "NO_PX_DIRECTOR_RENDERER_LLM_PROVIDER_AUTHORITY",
    } <= forbidden
    assert packet.opening_affordance == "REFERENCE_ENCOUNTER_PRESENCE_ONLY_NOT_COMMITTED"


def test_i6a_no_valid_i5_opportunity_cannot_be_orchestrated():
    i5_package = make_i5_package(route_available=False)
    upstream = replay_information_opportunity_shadow_package(i5_package)
    assert upstream.status == "NO_VALID_OPPORTUNITY"
    fixture = AuthoredEncounterOrchestrationFixture(
        fixture_id="I6A-INVALID-NO-CANDIDATE",
        candidate_encounter_id="SHADOW:INVENTED",
        source_event_id=upstream.source_event_id,
        player_actor_id=upstream.player_actor_id,
        carrier_npc_id=upstream.carrier_npc_id,
        information_ref=thaw_value(upstream.information_packet)["info_id"],
    )
    with pytest.raises(ValueError, match="I6A_REQUIRES_ACCEPTED_I5_SHADOW_CANDIDATE"):
        build_encounter_orchestration_control_packet(
            i5_shadow_package=i5_package,
            fixture=fixture,
        )


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("candidate_encounter_id", "SHADOW:INVENTED"),
        ("source_event_id", "E-INVENTED"),
        ("player_actor_id", "PLAYER-INVENTED"),
        ("carrier_npc_id", "NPC-INVENTED"),
        ("information_ref", "INFO:INVENTED"),
    ],
)
def test_i6a_authored_fixture_cannot_substitute_upstream_identity(field, value):
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package, **{field: value})
    with pytest.raises(ValueError, match=f"I6A_FIXTURE_BINDING_MISMATCH:{field}"):
        build_encounter_orchestration_control_packet(
            i5_shadow_package=i5_package,
            fixture=fixture,
        )


@pytest.mark.parametrize(
    ("argument", "error"),
    [
        ("caller_preselected_player_action", "I6A_PRESELECTED_PLAYER_ACTION_FORBIDDEN"),
        ("caller_preselected_outcome", "I6A_PRESELECTED_OUTCOME_FORBIDDEN"),
        ("caller_prewritten_dialogue", "I6A_PREWRITTEN_DIALOGUE_FORBIDDEN"),
    ],
)
def test_i6a_caller_cannot_preselect_player_action_outcome_or_dialogue(argument, error):
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    kwargs = {argument: "FORGED"}
    with pytest.raises(ValueError, match=error):
        build_encounter_orchestration_control_packet(
            i5_shadow_package=i5_package,
            fixture=fixture,
            **kwargs,
        )


@pytest.mark.parametrize(
    ("overrides", "error"),
    [
        ({"scenario_id": "INVENTED_SCENARIO"}, "I6A_FIXTURE_SCENARIO_MISMATCH"),
        ({"opening_affordance": "AUTO_START_DIALOGUE"}, "I6A_OPENING_AFFORDANCE_NOT_AUTHORIZED"),
        ({"authority_class": "CANONICAL_ENCOUNTER_AUTHORITY"}, "I6A_FIXTURE_AUTHORITY_CLASS_INVALID"),
    ],
)
def test_i6a_fixture_cannot_escalate_to_world_authority(overrides, error):
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package, **overrides)
    with pytest.raises(ValueError, match=error):
        build_encounter_orchestration_control_packet(
            i5_shadow_package=i5_package,
            fixture=fixture,
        )


def test_i6a_golden_scenario_version_drift_fails_closed_through_public_build(tmp_path, monkeypatch):
    def mutate(scenario):
        scenario["machine_spec"]["scenario_version"] = "999.0-drift"

    _build_with_drifted_golden(
        tmp_path,
        monkeypatch,
        mutate,
        "I6A_GOLDEN_SCENARIO_VERSION_DRIFT",
    )


def test_i6a_golden_allowed_player_intent_drift_fails_closed_through_public_build(tmp_path, monkeypatch):
    def mutate(scenario):
        scenario["allowed_player_intents"][0] = "auto obey narrative instruction"

    _build_with_drifted_golden(
        tmp_path,
        monkeypatch,
        mutate,
        "I6A_GOLDEN_ALLOWED_INTENTS_DRIFT",
    )


def test_i6a_golden_open_decision_drift_fails_closed_through_public_build(tmp_path, monkeypatch):
    def mutate(scenario):
        scenario["machine_spec"]["open_decision_dependencies"].remove(
            "OD-PX-SCORING-001"
        )

    _build_with_drifted_golden(
        tmp_path,
        monkeypatch,
        mutate,
        "I6A_OPEN_DECISION_BOUNDARY_DRIFT",
    )


def test_i6a_golden_anti_railroad_rule_drift_fails_closed_through_public_build(tmp_path, monkeypatch):
    def mutate(scenario):
        scenario["forbidden_outcomes"].remove(
            "Direct PlayerChronicle injection of E_CAPITAL_ASSASSINATION."
        )

    _build_with_drifted_golden(
        tmp_path,
        monkeypatch,
        mutate,
        "I6A_GOLDEN_ANTI_RAILROAD_RULES_DRIFT",
    )


def test_i6a_same_exact_inputs_are_deterministic():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    first = build_encounter_orchestration_control_packet(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    second = build_encounter_orchestration_control_packet(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    assert first == second


def test_i6a_package_is_byte_deterministic_and_replays_exactly():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    first = export_encounter_orchestration_control_package(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    second = export_encounter_orchestration_control_package(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    assert first == second
    rebuilt = replay_encounter_orchestration_control_package(first)
    expected = build_encounter_orchestration_control_packet(
        i5_shadow_package=i5_package,
        fixture=fixture,
    )
    assert rebuilt == expected


def test_i6a_outer_package_tamper_fails_closed():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    envelope = json.loads(
        export_encounter_orchestration_control_package(
            i5_shadow_package=i5_package,
            fixture=fixture,
        ).decode("utf-8")
    )
    envelope["payload"]["fixture"]["player_actor_id"] = SOURCE
    with pytest.raises(ValueError, match="I6A_PACKAGE_TAMPERED"):
        replay_encounter_orchestration_control_package(canonical_json_bytes(envelope))


def test_i6a_forged_expected_packet_with_recomputed_outer_digest_fails_closed():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    envelope = json.loads(
        export_encounter_orchestration_control_package(
            i5_shadow_package=i5_package,
            fixture=fixture,
        ).decode("utf-8")
    )
    envelope["payload"]["expected_packet"]["decision_gate"] = "AUTO_RESOLVE"
    with pytest.raises(ValueError, match="I6A_PACKET_MATERIALIZATION_MISMATCH"):
        replay_encounter_orchestration_control_package(refresh_outer_digest(envelope))


def test_i6a_fixture_tamper_with_recomputed_outer_digest_cannot_rebind_candidate():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    envelope = json.loads(
        export_encounter_orchestration_control_package(
            i5_shadow_package=i5_package,
            fixture=fixture,
        ).decode("utf-8")
    )
    envelope["payload"]["fixture"]["candidate_encounter_id"] = "SHADOW:INVENTED"
    with pytest.raises(
        ValueError,
        match="I6A_FIXTURE_BINDING_MISMATCH:candidate_encounter_id",
    ):
        replay_encounter_orchestration_control_package(refresh_outer_digest(envelope))


def test_i6a_tampered_i5_material_cannot_be_laundered_by_i6_outer_digest():
    i5_package = make_i5_package()
    fixture = make_i6_fixture(i5_package)
    envelope = json.loads(
        export_encounter_orchestration_control_package(
            i5_shadow_package=i5_package,
            fixture=fixture,
        ).decode("utf-8")
    )
    inner_i5 = json.loads(
        base64.b64decode(envelope["payload"]["source_i5_b64"]).decode("utf-8")
    )
    inner_i5["payload"]["expected_result"]["status"] = "CANONICAL_ENCOUNTER_COMMITTED"
    inner_i5["sha256"] = hashlib.sha256(
        canonical_json_bytes(inner_i5["payload"])
    ).hexdigest()
    tampered_i5 = canonical_json_bytes(inner_i5)
    envelope["payload"]["source_i5_b64"] = base64.b64encode(tampered_i5).decode("ascii")
    envelope["payload"]["source_i5_sha256"] = hashlib.sha256(tampered_i5).hexdigest()
    with pytest.raises(ValueError, match="I5A_SHADOW_RESULT_MATERIALIZATION_MISMATCH"):
        replay_encounter_orchestration_control_package(refresh_outer_digest(envelope))
