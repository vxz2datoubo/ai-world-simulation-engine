import copy
import hashlib
import inspect
import itertools
import json

import pytest

import evals.i9a_director_beat_packet_federation_mock as i9a
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
from evals.i3a_presentation_reference import (
    build_presentation_reference,
    export_replay_package as export_i3a_package,
)
from evals.i8c_storylet_eligibility_reference import (
    export_storylet_eligibility_package,
)

PLAYER = "ACTOR-I9A-PLAYER"
NPC = "NPC-I9A-INNKEEPER"
DOOR = "OBJ-I9A-DOOR"
CRATE = "OBJ-I9A-CRATE"
CRATE_ALT = "OBJ-I9A-BARREL"
SCENE = "SCN-PLAZA"
PRINCIPAL = "principal://i9a/player"
BASELINE_VERSION = "I9A-BASELINE-v1"

I3A_ASSETS = {
    "OBJ-COAT": {
        "media_asset_id": "AST-DAY-WEST",
        "media_version_id": "VER-DAY-WEST-1",
        "locator_id": "LOC-DAY-WEST-A",
    },
    "MAT-LINEN": {
        "media_asset_id": "AST-DAY-EAST",
        "media_version_id": "VER-DAY-EAST-1",
        "locator_id": "LOC-DAY-EAST",
    },
}
I3A_INVENTORY = ["OBJ-COAT", "MAT-LINEN"]
ALLOWED_POLICY_TOKENS = {
    "MUST_RENDER_IF_VISIBLE_IN_SHOT",
    "MUST_NOT_CONTRADICT",
    "HIDDEN_BY_CLOTHING",
    "PRESENTATION_OPTIONAL",
}

STAGING_A = {
    "camera_intent": "MOCK_CAMERA_A",
    "performance_intent": "MOCK_PERFORMANCE_A",
    "edit_intent": "MOCK_EDIT_A",
    "sound_intent": "MOCK_SOUND_A",
}
STAGING_B = {
    "camera_intent": "MOCK_CAMERA_B",
    "performance_intent": "MOCK_PERFORMANCE_B",
    "edit_intent": "MOCK_EDIT_B",
    "sound_intent": "MOCK_SOUND_B",
}


def canonical_json(value):
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )


def refresh_envelope_digest(envelope):
    envelope["sha256"] = hashlib.sha256(
        canonical_json(envelope["payload"]).encode("utf-8")
    ).hexdigest()


def reset_legacy_allocators():
    ActionCompiler._counter = itertools.count(1)
    SimulationEngine._event_counter = itertools.count(1)


def make_world(
    *,
    scene_id=SCENE,
    base_asset_refs=None,
    add_later=True,
    later_target=CRATE,
):
    reset_legacy_allocators()
    base_asset_refs = (
        ["AST-DAY-WEST"] if base_asset_refs is None else list(base_asset_refs)
    )
    world = WorldState(
        world_id=f"WORLD-I9A-{scene_id}",
        active_scene_id=scene_id,
        baseline_version=BASELINE_VERSION,
        primary_player_actor_id=PLAYER,
        actors={
            PLAYER: ActorState(
                PLAYER,
                "旅人",
                scene_id,
                strength=1.0,
                capabilities={"HIT", "SPEAK"},
            ),
            NPC: ActorState(
                NPC,
                "酒馆老板",
                scene_id,
                strength=1.0,
                capabilities={"SPEAK"},
            ),
        },
        objects={
            DOOR: ObjectState(
                DOOR,
                "木门",
                scene_id,
                mass=25.0,
                graspable=False,
                fragility=0.5,
            ),
            CRATE: ObjectState(
                CRATE,
                "木箱",
                scene_id,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
            CRATE_ALT: ObjectState(
                CRATE_ALT,
                "木桶",
                scene_id,
                mass=10.0,
                graspable=True,
                fragility=0.8,
            ),
        },
        npc_minds={NPC: NPCMindState(NPC, "INNKEEPER")},
        scenes={
            scene_id: SceneState(
                scene_id,
                base_asset_refs,
                [DOOR, CRATE, CRATE_ALT],
                [PLAYER, NPC],
            )
        },
        principal_actor_bindings={PRINCIPAL: {PLAYER}},
        reachable_pairs={
            (PLAYER, DOOR),
            (PLAYER, CRATE),
            (PLAYER, CRATE_ALT),
        },
        audible_pairs={(PLAYER, NPC)},
    )
    baseline = capture_pristine_baseline(world)

    damage_action = ActionCompiler().compile("砸木门", PLAYER, world, PRINCIPAL)
    damage_resolution = SimulationEngine().resolve_and_commit(damage_action, world)
    damage = next(
        event
        for event in damage_resolution.events
        if event.event_type == "OBJECT_DAMAGED"
    )

    speech_action = ActionCompiler().compile(
        f"告诉酒馆老板 PROMISE_REPAIR_OBJECT:{DOOR}",
        PLAYER,
        world,
        PRINCIPAL,
    )
    speech_resolution = SimulationEngine().resolve_and_commit(
        speech_action, world
    )
    speech = next(
        event
        for event in speech_resolution.events
        if event.event_type == "SPEECH_UTTERED"
    )
    acquisition = next(
        event
        for event in speech_resolution.events
        if event.event_type == "NPC_KNOWLEDGE_ACQUIRED"
        and event.payload.get("npc_id") == NPC
        and event.payload.get("source_event_id") == speech.event_id
    )

    if add_later:
        if later_target == CRATE:
            later_text = "砸木箱"
        elif later_target == CRATE_ALT:
            later_text = "砸木桶"
        else:
            raise ValueError("unsupported later target")
        later = ActionCompiler().compile(later_text, PLAYER, world, PRINCIPAL)
        SimulationEngine().resolve_and_commit(later, world)

    return baseline, world, damage, speech, acquisition


def storylet(damage, speech, acquisition):
    return {
        "storylet_id": "STORYLET:I9A-PROMISE-RETURN-CALLBACK",
        "preconditions": [
            {"kind": "CALLBACK_OPPORTUNITY_REQUIRED"},
            {"kind": "TARGET_OBJECT_PRESENT", "object_id": DOOR},
            {
                "kind": "ACTORS_SHARE_ACTIVE_SCENE",
                "actor_ids": [PLAYER, NPC],
            },
            {"kind": "WORLD_EVENT_PRESENT", "event_id": speech.event_id},
        ],
        "eligible_roles": {
            "player_actor_id": PLAYER,
            "callback_npc_id": NPC,
        },
        "knowledge_constraints": [
            {
                "kind": "CALLBACK_REQUIRED_FACTS_EXACT",
                "fact_refs": [
                    speech.event_id,
                    acquisition.event_id,
                    damage.event_id,
                ],
            },
            {"kind": "EXACT_CALLBACK_RECIPIENT", "npc_id": NPC},
        ],
        "dramatic_purpose": "RETURN_TO_OLD_PROMISE_WITHOUT_FORCING_OUTCOME",
        "forbidden_contradictions": [
            "NO_RETCON_OR_RESURRECTION",
            "NO_BRANCH_WELDING",
            "NO_AUTOMATIC_SPEECH",
            "NO_AUTOMATIC_PAYOFF_OR_BREACH",
        ],
        "consequence_templates": [
            "NON_CANONICAL_CALLBACK_SCENE_CANDIDATE_ONLY"
        ],
        "repeat_policy": {"mode": "NO_AUTO_REALIZATION"},
        "version": "1.0.0-reference",
    }


def make_i8c_package(
    *,
    scene_id=SCENE,
    base_asset_refs=None,
    add_later=True,
    later_target=CRATE,
    storylet_mutator=None,
):
    baseline, world, damage, speech, acquisition = make_world(
        scene_id=scene_id,
        base_asset_refs=base_asset_refs,
        add_later=add_later,
        later_target=later_target,
    )
    definition = storylet(damage, speech, acquisition)
    if storylet_mutator is not None:
        storylet_mutator(definition)
    package = export_storylet_eligibility_package(
        baseline=baseline,
        world=world,
        storylet_definition=definition,
        player_actor_id=PLAYER,
        promise_recipient_npc_id=NPC,
        candidate_npc_id=NPC,
        target_object_id=DOOR,
        source_speech_event_id=speech.event_id,
    )
    return package, world, definition, damage, speech, acquisition


def make_i3a_package(
    *,
    actor_id=PLAYER,
    locator_id="LOC-DAY-WEST-A",
    view_id="VIEW-WEST",
    cover_dressing=False,
    include_surface=True,
):
    assets = copy.deepcopy(I3A_ASSETS)
    assets["OBJ-COAT"]["locator_id"] = locator_id
    events = [
        {
            "event_id": "E-I9A-PRES-001-WEAR-COAT",
            "cursor": 201,
            "actor_id": actor_id,
            "kind": "WEAR_SLOT",
            "slot": "torso_outer",
            "object_ref": "OBJ-COAT",
        },
        {
            "event_id": "E-I9A-PRES-002-DRESS-RIGHT-FOREARM",
            "cursor": 202,
            "actor_id": actor_id,
            "kind": "APPLY_DRESSING",
            "dressing_id": "DRESS-I9A-RF-1",
            "body_region": "FOREARM",
            "side": "RIGHT",
            "material_ref": "MAT-LINEN",
            "appearance_state": {
                "color": "WHITE",
                "wrap_style": "SPIRAL",
                "stain": "LIGHT_BLOOD",
            },
            "covered_by_refs": ["OBJ-COAT"] if cover_dressing else [],
        },
    ]
    if include_surface:
        events.append(
            {
                "event_id": "E-I9A-PRES-003-MUD-COAT",
                "cursor": 203,
                "actor_id": actor_id,
                "kind": "SET_SURFACE",
                "surface_state_id": "SURF-I9A-COAT-MUD",
                "target_ref": "OBJ-COAT",
                "surface_type": "MUD",
                "intensity": 0.4,
            }
        )
    reference = build_presentation_reference(
        actor_id=actor_id,
        events=events,
        inventory_object_refs=I3A_INVENTORY,
        asset_registry=assets,
        view_id=view_id,
    )
    return export_i3a_package(
        reference=reference,
        events=events,
        inventory_object_refs=I3A_INVENTORY,
        asset_registry=assets,
    )


def make_packages(**world_kwargs):
    i8c_package, world, definition, damage, speech, acquisition = (
        make_i8c_package(**world_kwargs)
    )
    return (
        i8c_package,
        make_i3a_package(),
        world,
        definition,
        damage,
        speech,
        acquisition,
    )


def good_mock_response(packet, staging=None):
    return {
        "source_packet_sha256": i9a.packet_sha256(packet),
        "protected_material_sha256": i9a.protected_material_sha256(packet),
        "staging_metadata": dict(STAGING_A if staging is None else staging),
    }


def actor_requirements(packet):
    return [
        thaw_value(item)
        for item in packet.actor_presentation_requirements
    ]


def normalized_policy(requirement):
    return tuple(tuple(item) for item in requirement["visibility_policy"])


def test_scope_locks_keep_i9a_reference_non_authoritative_and_offline():
    assert i9a.I9A_BROAD_RUNTIME_AUTHORITY_NOT_GRANTED is True
    assert i9a.NO_PROVIDER_INTEGRATION is True
    assert i9a.NO_NETWORK_INTEGRATION is True
    assert i9a.NO_REAL_RENDERER_IMPLEMENTED is True
    assert i9a.NO_WORLD_MUTATION is True
    assert i9a.NO_KNOWLEDGE_MUTATION is True
    assert i9a.NO_BRANCH_QUALITY_AUTHORITY is True
    assert i9a.NO_PX_AUTHORITY is True
    assert i9a.NO_LIVE_AI_FILM_REPOSITORY_WRITE is True


def test_i9a_builds_packet_only_from_replayed_canonical_sources():
    (
        i8c_package,
        i3a_package,
        world,
        definition,
        damage,
        speech,
        acquisition,
    ) = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert packet is not None
    assert packet.world_state_version == world.world_state_version
    assert packet.world_state_version == (
        f"{world.baseline_version}:{world.state_version}"
    )
    assert packet.confirmed_event_refs == (
        damage.event_id,
        speech.event_id,
        acquisition.event_id,
    )
    assert packet.player_visible_knowledge_refs == ()
    assert packet.public_visible_knowledge_refs == ()
    assert packet.private_forbidden_knowledge_refs == ()
    assert packet.presentation_goal == definition["dramatic_purpose"]
    assert packet.contract_version == "1.10.0-candidate"
    assert packet.packet_type_version == "1.0.0-candidate"
    assert len(packet.source_i1_event_sequence_digest) == 64
    assert len(packet.source_storylet_sha256) == 64
    assert packet.authority_class == (
        "NON_CANONICAL_I9A_DIRECTOR_BEAT_PACKET_REFERENCE_ONLY"
    )
    for item in definition["forbidden_contradictions"]:
        assert item in packet.forbidden_inventions
    assert "AF_H_NO_WORLD_OR_EVENT_OUTCOME_REWRITE" in packet.forbidden_inventions
    assert "AF_H_NO_KNOWLEDGE_VISIBILITY_REWRITE" in packet.forbidden_inventions
    assert "AF_H_NO_ACTOR_IDENTITY_REWRITE" in packet.forbidden_inventions
    assert "AF_H_NO_PRESENTATION_TRUTH_REWRITE" in packet.forbidden_inventions


def test_scene_view_asset_refs_stay_at_logical_identity_level():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    scene = thaw_value(packet.scene_view_asset_refs)
    assert scene == {
        "scene_id": "SCN-PLAZA",
        "view_id": "VIEW-WEST",
        "base_media_asset_refs": ["AST-DAY-WEST"],
    }
    encoded = canonical_json(scene)
    assert "media_version_id" not in encoded
    assert "locator_id" not in encoded
    assert "VER-DAY-WEST-1" not in encoded
    assert "LOC-DAY-WEST-A" not in encoded
    assert "receipt" not in encoded.lower()


def test_frozen_actor_presentation_shape_is_refs_only_plural_and_safe():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert isinstance(packet.actor_presentation_requirements, tuple)
    requirements = actor_requirements(packet)
    assert len(requirements) == 1
    actor = requirements[0]
    assert set(actor) == {
        "actor_id",
        "identity_refs",
        "outfit_refs",
        "dressing_refs",
        "visible_condition_cues",
        "visibility_policy",
        "state_version",
    }
    assert actor["actor_id"] == PLAYER
    assert tuple(actor["identity_refs"]) == ()
    assert tuple(actor["outfit_refs"]) == ("OBJ-COAT",)
    assert tuple(actor["dressing_refs"]) == ("DRESS-I9A-RF-1",)
    assert tuple(actor["visible_condition_cues"]) == ()
    policy = normalized_policy(actor)
    assert ("OBJ-COAT", "MUST_NOT_CONTRADICT") in policy
    assert (
        "DRESS-I9A-RF-1",
        "MUST_RENDER_IF_VISIBLE_IN_SHOT",
    ) in policy
    assert {token for _, token in policy} <= ALLOWED_POLICY_TOKENS


def test_scene_view_admission_cannot_mint_actor_visual_identity_refs():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    actor = actor_requirements(packet)[0]
    assert tuple(actor["identity_refs"]) == ()
    assert "MISSING_CANONICAL_VISIBLE_IDENTITY_REF" in packet.coverage_gaps
    encoded_actor = canonical_json(actor)
    assert "VIEW-WEST" not in encoded_actor
    assert "AF_D_MANIFEST" not in encoded_actor
    assert "AF_D_ADMISSION" not in encoded_actor


def test_surface_state_is_validated_but_not_smuggled_into_visible_cues():
    i8c_package, *_ = make_i8c_package()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(include_surface=True),
    )
    actor = actor_requirements(packet)[0]
    assert tuple(actor["visible_condition_cues"]) == ()
    encoded_actor = canonical_json(actor)
    assert "SURF-I9A-COAT-MUD" not in encoded_actor
    assert '"MUD"' not in encoded_actor
    assert (
        "SURFACE_STATE_PRESENT_UPSTREAM_BUT_NOT_EXPRESSIBLE_IN_FROZEN_PACKET_V0"
        in packet.coverage_gaps
    )


def test_no_surface_gap_when_upstream_has_no_surface_state():
    i8c_package, *_ = make_i8c_package()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(include_surface=False),
    )
    assert (
        "SURFACE_STATE_PRESENT_UPSTREAM_BUT_NOT_EXPRESSIBLE_IN_FROZEN_PACKET_V0"
        not in packet.coverage_gaps
    )


def test_covered_dressing_uses_only_frozen_hidden_policy_token():
    i8c_package, *_ = make_i8c_package()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(cover_dressing=True),
    )
    policy = normalized_policy(actor_requirements(packet)[0])
    assert ("DRESS-I9A-RF-1", "HIDDEN_BY_CLOTHING") in policy
    assert {token for _, token in policy} <= ALLOWED_POLICY_TOKENS


def test_identical_replay_inputs_are_deterministic_across_rebuild():
    i8c_package, i3a_package, *_ = make_packages()
    packet_a = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    packet_b = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert packet_a == packet_b
    assert i9a.packet_sha256(packet_a) == i9a.packet_sha256(packet_b)


def test_locator_migration_preserves_narrative_beat_and_scene_truth():
    i8c_package, *_ = make_i8c_package()
    packet_a = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(
            locator_id="LOC-DAY-WEST-A"
        ),
    )
    packet_b = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(
            locator_id="LOC-DAY-WEST-B"
        ),
    )
    assert packet_a.source_i3a_sha256 != packet_b.source_i3a_sha256
    assert packet_a.beat_id == packet_b.beat_id
    assert packet_a.scene_view_asset_refs == packet_b.scene_view_asset_refs
    assert (
        i9a.protected_material_sha256(packet_a)
        == i9a.protected_material_sha256(packet_b)
    )
    assert i9a.packet_sha256(packet_a) != i9a.packet_sha256(packet_b)
    assert (
        actor_requirements(packet_a)[0]
        == actor_requirements(packet_b)[0]
    )


def test_different_canonical_history_same_state_count_changes_beat_id():
    package_a, world_a, definition_a, *_ = make_i8c_package(
        later_target=CRATE
    )
    package_b, world_b, definition_b, *_ = make_i8c_package(
        later_target=CRATE_ALT
    )
    assert world_a.world_id == world_b.world_id
    assert world_a.baseline_version == world_b.baseline_version
    assert world_a.state_version == world_b.state_version
    assert definition_a == definition_b

    i3a_package = make_i3a_package()
    packet_a = i9a.build_director_beat_packet_reference(
        i8c_replay_package=package_a,
        i3a_replay_package_json=i3a_package,
    )
    packet_b = i9a.build_director_beat_packet_reference(
        i8c_replay_package=package_b,
        i3a_replay_package_json=i3a_package,
    )
    assert packet_a.source_state_version == packet_b.source_state_version
    assert packet_a.source_storylet_sha256 == packet_b.source_storylet_sha256
    assert (
        packet_a.source_i1_event_sequence_digest
        != packet_b.source_i1_event_sequence_digest
    )
    assert packet_a.beat_id != packet_b.beat_id


def test_changed_authored_storylet_material_same_id_changes_beat_id():
    package_a, _, definition_a, *_ = make_i8c_package()

    def mutate(definition):
        definition["dramatic_purpose"] = (
            "RETURN_TO_OLD_PROMISE_WITH_A_DIFFERENT_STAGING_PURPOSE"
        )

    package_b, _, definition_b, *_ = make_i8c_package(
        storylet_mutator=mutate
    )
    assert definition_a["storylet_id"] == definition_b["storylet_id"]

    i3a_package = make_i3a_package()
    packet_a = i9a.build_director_beat_packet_reference(
        i8c_replay_package=package_a,
        i3a_replay_package_json=i3a_package,
    )
    packet_b = i9a.build_director_beat_packet_reference(
        i8c_replay_package=package_b,
        i3a_replay_package_json=i3a_package,
    )
    assert (
        packet_a.source_i1_event_sequence_digest
        == packet_b.source_i1_event_sequence_digest
    )
    assert packet_a.source_storylet_sha256 != packet_b.source_storylet_sha256
    assert packet_a.beat_id != packet_b.beat_id


def test_no_valid_storylet_produces_no_packet():
    i8c_package, *_ = make_i8c_package(add_later=False)
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=make_i3a_package(),
    )
    assert packet is None


def test_scene_view_mismatch_fails_closed():
    i8c_package, *_ = make_i8c_package(scene_id="SCN-TAVERN")
    with pytest.raises(ValueError, match="I9A_SCENE_VIEW_MISMATCH"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=make_i3a_package(),
        )


def test_noncanonical_scene_asset_fails_closed():
    i8c_package, *_ = make_i8c_package(
        base_asset_refs=["AST-INVENTED"]
    )
    with pytest.raises(
        ValueError,
        match="I9A_SCENE_ASSET_NOT_IN_CANONICAL_AF_D_MANIFEST",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=make_i3a_package(),
        )


def test_scene_asset_bound_to_other_view_fails_closed():
    i8c_package, *_ = make_i8c_package(
        base_asset_refs=["AST-DAY-EAST"]
    )
    with pytest.raises(ValueError, match="I9A_SCENE_ASSET_VIEW_MISMATCH"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=make_i3a_package(view_id="VIEW-WEST"),
        )


def test_presentation_actor_must_exist_in_replayed_world():
    i8c_package, *_ = make_i8c_package()
    with pytest.raises(
        ValueError,
        match="I9A_PRESENTATION_ACTOR_ABSENT_FROM_SOURCE_WORLD",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=make_i3a_package(
                actor_id="ACTOR-NOT-IN-WORLD"
            ),
        )


def test_outer_i8c_tamper_fails_closed():
    i8c_package, *_ = make_i8c_package()
    envelope = json.loads(i8c_package.decode("utf-8"))
    envelope["payload"]["candidate_npc_id"] = "NPC-FORGED"
    forged = canonical_json(envelope).encode("utf-8")
    with pytest.raises(ValueError):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=forged,
            i3a_replay_package_json=make_i3a_package(),
        )


def test_embedded_i1_digest_tamper_fails_closed():
    i8c_package, *_ = make_i8c_package()
    envelope = json.loads(i8c_package.decode("utf-8"))
    envelope["payload"]["source_i1_replay_sha256"] = "0" * 64
    refresh_envelope_digest(envelope)
    with pytest.raises(ValueError):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=canonical_json(envelope).encode("utf-8"),
            i3a_replay_package_json=make_i3a_package(),
        )


def test_uncommitted_confirmed_event_cannot_be_laundered():
    i8c_package, *_ = make_i8c_package()
    envelope = json.loads(i8c_package.decode("utf-8"))
    envelope["payload"]["storylet_definition"]["preconditions"][3][
        "event_id"
    ] = "EVENT-NEVER-COMMITTED"
    refresh_envelope_digest(envelope)
    with pytest.raises(ValueError):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=canonical_json(envelope).encode("utf-8"),
            i3a_replay_package_json=make_i3a_package(),
        )


def test_i3a_payload_tampering_fails_closed():
    package = json.loads(make_i3a_package())
    package["payload"]["inputs"]["events"][1]["side"] = "LEFT"
    i8c_package, *_ = make_i8c_package()
    with pytest.raises(ValueError):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=json.dumps(package),
        )


def test_forged_asset_version_locator_relationship_fails_in_i3a_readmission():
    package = json.loads(make_i3a_package())
    package["payload"]["inputs"]["asset_registry"]["OBJ-COAT"][
        "media_version_id"
    ] = "VER-NIGHT-WEST-1"
    package["payload"]["inputs"]["asset_registry"]["OBJ-COAT"][
        "locator_id"
    ] = "LOC-NIGHT-WEST"
    refresh_envelope_digest(package)
    i8c_package, *_ = make_i8c_package()
    with pytest.raises(ValueError):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=canonical_json(package),
        )


def test_duplicate_key_i3a_transport_fails_before_ambiguous_replay():
    i8c_package, *_ = make_i8c_package()
    envelope = json.loads(make_i3a_package())
    duplicate = (
        '{"payload":'
        + canonical_json(envelope["payload"])
        + ',"sha256":'
        + json.dumps(envelope["sha256"])
        + ',"sha256":"FORGED"}'
    )
    with pytest.raises(ValueError, match="I9A_JSON_DUPLICATE_KEY:sha256"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=duplicate,
        )


def test_mock_consumer_accepts_enum_staging_and_has_zero_side_effects():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    receipt = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=good_mock_response(packet),
    )
    assert receipt.status == "MOCK_AI_FILM_STAGING_ACCEPTED"
    assert receipt.beat_id == packet.beat_id
    assert receipt.world_state_version == packet.world_state_version
    assert receipt.world_mutation_count == 0
    assert receipt.provider_call_count == 0
    assert receipt.authority_class == (
        "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"
    )
    assert thaw_value(receipt.staging_metadata) == STAGING_A


def test_legal_staging_a_b_change_only_receipt_staging_not_packet_authority():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    response_a = good_mock_response(packet, STAGING_A)
    response_b = good_mock_response(packet, STAGING_B)
    receipt_a = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=response_a,
    )
    receipt_b = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=response_b,
    )
    assert receipt_a.staging_metadata != receipt_b.staging_metadata
    assert (
        receipt_a.source_packet_sha256
        == receipt_b.source_packet_sha256
        == i9a.packet_sha256(packet)
    )
    assert (
        receipt_a.protected_material_sha256
        == receipt_b.protected_material_sha256
        == i9a.protected_material_sha256(packet)
    )
    assert receipt_a.beat_id == receipt_b.beat_id == packet.beat_id
    assert receipt_a.world_state_version == receipt_b.world_state_version
    assert receipt_a.world_mutation_count == receipt_b.world_mutation_count == 0
    assert receipt_a.provider_call_count == receipt_b.provider_call_count == 0


@pytest.mark.parametrize(
    "protected_field",
    [
        "confirmed_event_refs",
        "world_state_version",
        "player_visible_knowledge_refs",
        "public_visible_knowledge_refs",
        "private_forbidden_knowledge_refs",
        "actor_presentation_requirements",
        "forbidden_inventions",
        "scene_view_asset_refs",
        "outcome",
    ],
)
def test_mock_response_cannot_override_protected_material(protected_field):
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    response = good_mock_response(packet)
    response[protected_field] = ["CALLER-FORGED"]
    with pytest.raises(
        ValueError,
        match="I9A_AI_FILM_PROTECTED_OR_UNKNOWN_FIELD_FORBIDDEN",
    ):
        i9a.consume_mock_ai_film_response(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
            response=response,
        )


@pytest.mark.parametrize("key", sorted(STAGING_A))
@pytest.mark.parametrize(
    "smuggled",
    [
        "WORLD_FACT:NPC_KILLED_KING",
        "EVENT:E000123",
        "ACTOR-I9A-PLAYER",
        "AST-DAY-WEST",
        "PLAYER_KNOWS_PRIVATE_SECRET",
        "OUTCOME:FORCE_SUCCESS",
    ],
)
def test_each_staging_field_rejects_free_text_authority_smuggling(
    key, smuggled
):
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    staging = dict(STAGING_A)
    staging[key] = smuggled
    with pytest.raises(
        ValueError,
        match=rf"I9A_STAGING_VARIANT_INVALID:{key}",
    ):
        i9a.consume_mock_ai_film_response(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
            response=good_mock_response(packet, staging),
        )


@pytest.mark.parametrize("nested", [{"claim": "fact"}, ["EVENT-X"], 7, True])
def test_nested_or_nonstring_staging_values_fail_closed(nested):
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    staging = dict(STAGING_A)
    staging["camera_intent"] = nested
    with pytest.raises(
        ValueError,
        match="I9A_STAGING_FREE_TEXT_FORBIDDEN:camera_intent",
    ):
        i9a.consume_mock_ai_film_response(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
            response=good_mock_response(packet, staging),
        )


def test_unknown_and_legacy_staging_keys_fail_closed():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    for key in ("world_facts", "camera", "actor_id", "knowledge_refs"):
        staging = dict(STAGING_A)
        staging[key] = "MOCK_CAMERA_A"
        with pytest.raises(
            ValueError,
            match="I9A_STAGING_METADATA_AUTHORITY_EXPANSION_FORBIDDEN",
        ):
            i9a.consume_mock_ai_film_response(
                i8c_replay_package=i8c_package,
                i3a_replay_package_json=i3a_package,
                response=good_mock_response(packet, staging),
            )


def test_empty_staging_mapping_is_allowed_but_carries_no_semantics():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    receipt = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=good_mock_response(packet, {}),
    )
    assert thaw_value(receipt.staging_metadata) == {}
    assert receipt.source_packet_sha256 == i9a.packet_sha256(packet)


def test_mock_response_digest_mismatch_fails_closed():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    response = good_mock_response(packet)
    response["protected_material_sha256"] = "0" * 64
    with pytest.raises(
        ValueError,
        match="I9A_AI_FILM_PROTECTED_MATERIAL_DIGEST_MISMATCH",
    ):
        i9a.consume_mock_ai_film_response(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
            response=response,
        )


def test_mock_consumer_has_no_caller_packet_or_prevalidated_parameter():
    params = set(
        inspect.signature(i9a.consume_mock_ai_film_response).parameters
    )
    assert params == {
        "i8c_replay_package",
        "i3a_replay_package_json",
        "response",
    }
    build_params = set(
        inspect.signature(
            i9a.build_director_beat_packet_reference
        ).parameters
    )
    assert build_params == {
        "i8c_replay_package",
        "i3a_replay_package_json",
    }


def test_post_pr96_parent_version_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(
        i9a._CONTRACT_PATH.read_text(encoding="utf-8")
    )
    contract["contract_version"] = "1.11.0-unreviewed"
    path = tmp_path / "contract-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package, *_ = make_packages()
    with pytest.raises(ValueError, match="I9A_CANONICAL_PARENT_DRIFT"):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_af_h_packet_field_drift_fails_closed(tmp_path, monkeypatch):
    contract = json.loads(
        i9a._CONTRACT_PATH.read_text(encoding="utf-8")
    )
    contract["type_registry"]["DIRECTOR-BEAT-PACKET"]["fields"].remove(
        "forbidden_inventions"
    )
    path = tmp_path / "contract-fields-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package, *_ = make_packages()
    with pytest.raises(
        ValueError,
        match="I9A_DIRECTOR_BEAT_PACKET_FIELDS_DRIFT",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_ai_director_staging_authority_drift_fails_closed(
    tmp_path, monkeypatch
):
    contract = json.loads(
        i9a._CONTRACT_PATH.read_text(encoding="utf-8")
    )
    contract["authority_semantics"]["profiles"][
        "AWRSE_DIRECTOR_HANDOFF"
    ]["staging_authority"] = ["WORLD_RULES_AUTHORITY"]
    path = tmp_path / "contract-authority-drift.json"
    path.write_text(json.dumps(contract), encoding="utf-8")
    monkeypatch.setattr(i9a, "_CONTRACT_PATH", path)
    i8c_package, i3a_package, *_ = make_packages()
    with pytest.raises(
        ValueError,
        match="I9A_DIRECTOR_STAGING_AUTHORITY_DRIFT",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_af_d_manifest_parent_drift_fails_closed(tmp_path, monkeypatch):
    manifest = json.loads(
        i9a._AF_D_MANIFEST_PATH.read_text(encoding="utf-8")
    )
    manifest["parent_machine_contract"][
        "authority_graph_version"
    ] = "FORGED-AUTHORITY"
    path = tmp_path / "manifest-drift.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    monkeypatch.setattr(i9a, "_AF_D_MANIFEST_PATH", path)
    i8c_package, i3a_package, *_ = make_packages()
    with pytest.raises(
        ValueError,
        match="I9A_AF_D_MANIFEST_PARENT_DRIFT",
    ):
        i9a.build_director_beat_packet_reference(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
        )


def test_reference_metadata_reports_gaps_outside_frozen_packet():
    i8c_package, i3a_package, *_ = make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    frozen = i9a._frozen_packet_material(packet)
    assert set(frozen) == i9a._EXPECTED_PACKET_FIELDS
    assert "coverage_gaps" not in frozen
    assert "source_i3a_sha256" not in frozen
    assert "source_i1_event_sequence_digest" not in frozen
    assert "MISSING_CANONICAL_VISIBLE_IDENTITY_REF" in packet.coverage_gaps
    assert (
        "NO_FUNCTIONAL_TO_VISIBLE_CONDITION_CUE_ASSEMBLER_IN_I9A_V0"
        in packet.coverage_gaps
    )


def test_staging_variants_are_explicitly_eval_local_noncanonical_tokens():
    assert i9a.NON_CANONICAL_MOCK_STAGING_VARIANTS == {
        "camera_intent": frozenset({"MOCK_CAMERA_A", "MOCK_CAMERA_B"}),
        "performance_intent": frozenset(
            {"MOCK_PERFORMANCE_A", "MOCK_PERFORMANCE_B"}
        ),
        "edit_intent": frozenset({"MOCK_EDIT_A", "MOCK_EDIT_B"}),
        "sound_intent": frozenset({"MOCK_SOUND_A", "MOCK_SOUND_B"}),
    }


def test_module_contains_no_network_provider_or_subprocess_execution_path():
    source = inspect.getsource(i9a)
    assert "import requests" not in source
    assert "import urllib" not in source
    assert "import socket" not in source
    assert "import subprocess" not in source
    assert "os.system(" not in source
    assert "BranchQuality" not in source
    assert "PXRanking" not in source
