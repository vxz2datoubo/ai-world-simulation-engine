import importlib.util
import json
from pathlib import Path

import evals.i9a_director_beat_packet_federation_mock as i9a
from runtime.awrse.model import thaw_value
from runtime.awrse.render import build_render_packet, validate_render_claims


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"


def _load_accepted_i9a_fixture_module():
    path = Path(__file__).with_name("test_i9a_director_beat_packet_federation_mock.py")
    spec = importlib.util.spec_from_file_location("_cell_world_e_i9a_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CELL_WORLD_E_I9A_FIXTURE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_accepted_i9a_fixture_module()


def _director_handoff_profile():
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return contract["authority_semantics"]["profiles"]["AWRSE_DIRECTOR_HANDOFF"]


def _materials(staging=None):
    (
        i8c_package,
        i3a_package,
        world,
        definition,
        damage,
        speech,
        acquisition,
    ) = FIXTURE.make_packages()
    director_packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert director_packet is not None
    receipt = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=FIXTURE.good_mock_response(
            director_packet,
            FIXTURE.STAGING_A if staging is None else staging,
        ),
    )
    confirmed = tuple(
        event
        for event in world.event_log
        if event.event_id in set(director_packet.confirmed_event_refs)
    )
    render_packet = build_render_packet(world, confirmed)
    return world, director_packet, receipt, render_packet, damage, speech, acquisition


def _rendered_object_states(render_packet):
    result = {}
    for raw in render_packet.environment_delta:
        delta = thaw_value(raw)
        if delta.get("kind") != "OBJECT_STATE":
            continue
        result[delta["object_id"]] = {
            key: value
            for key, value in delta.items()
            if key not in {"kind", "object_id"}
        }
    return result


def _aligned_validation(render_packet):
    return validate_render_claims(
        render_packet,
        rendered_event_ids={event.event_id for event in render_packet.confirmed_events},
        rendered_object_states=_rendered_object_states(render_packet),
        rendered_scene_id=render_packet.scene_id,
        rendered_actor_state_refs=render_packet.actor_state_refs,
        rendered_camera=render_packet.camera,
    )


def test_contract_authorizes_bounded_director_staging_but_not_fact_rewrite():
    profile = _director_handoff_profile()

    assert profile["contract_schema_steward"] == "AWRSE_AF_H_CONTRACT_STEWARD"
    assert "AWRSE_DIRECTOR_PACKET_ASSEMBLER" in profile["producer_or_assembler"]
    assert "AI_DIRECTOR" in profile["downstream_consumer"]
    assert "RENDERER_PUBLICATION" in profile["downstream_consumer"]
    assert profile["staging_authority"] == ["AI_DIRECTOR"]
    assert (
        profile["mutation_constraint"]
        == "AI_DIRECTOR_MAY_CHOOSE_STAGING_CAMERA_PERFORMANCE_EDIT_AND_SOUND_ONLY_INSIDE_THE_PACKET_ENVELOPE_AND_MAY_NOT_REWRITE_PACKET_FACTS_KNOWLEDGE_VISIBILITY_ACTOR_IDENTITY_OR_PRESENTATION_REQUIREMENTS"
    )


def test_valid_i9a_staging_and_canonical_render_packet_can_coexist_without_being_same_authority():
    _, director_packet, receipt, render_packet, damage, speech, acquisition = _materials()

    assert director_packet.confirmed_event_refs == (
        damage.event_id,
        speech.event_id,
        acquisition.event_id,
    )
    assert tuple(event.event_id for event in render_packet.confirmed_events) == (
        damage.event_id,
        speech.event_id,
        acquisition.event_id,
    )
    assert receipt.status == "MOCK_AI_FILM_STAGING_ACCEPTED"
    assert receipt.world_mutation_count == 0
    assert receipt.provider_call_count == 0
    assert _aligned_validation(render_packet).status == "RENDER_ALIGNED"

    # Contract-level staging authority exists, but the accepted I9A staging tokens are
    # not yet a runtime render-camera claim or an adapter receipt.
    assert set(thaw_value(render_packet.camera)) == {"mode", "framing"}
    assert set(thaw_value(receipt.staging_metadata)) == {
        "camera_intent",
        "performance_intent",
        "edit_intent",
        "sound_intent",
    }
    assert not hasattr(receipt, "render_camera")
    assert not hasattr(receipt, "render_adapter_receipt")


def test_directly_wiring_i9a_camera_intent_into_runtime_renderer_fails_closed():
    _, _, receipt, render_packet, *_ = _materials()

    unsafe_direct_camera_wiring = {
        "camera_intent": thaw_value(receipt.staging_metadata)["camera_intent"]
    }
    verdict = validate_render_claims(
        render_packet,
        rendered_event_ids={event.event_id for event in render_packet.confirmed_events},
        rendered_object_states=_rendered_object_states(render_packet),
        rendered_scene_id=render_packet.scene_id,
        rendered_actor_state_refs=render_packet.actor_state_refs,
        rendered_camera=unsafe_direct_camera_wiring,
    )

    assert verdict.status == "RENDER_MISMATCH"
    assert "CAMERA_INTENT_MISMATCH" in verdict.semantic_contradictions
    assert verdict.missing_canonical_events == ()
    assert verdict.unauthorized_claims == ()


def test_failed_direct_wiring_cannot_repair_or_mutate_canonical_render_truth():
    world, _, receipt, render_packet, *_ = _materials()
    before_version = world.world_state_version
    before_events = tuple(world.event_log)
    before_objects = {
        object_id: (
            obj.damage_state,
            obj.contamination_state,
            obj.is_open,
            obj.owner_actor_id,
            obj.zone_id,
        )
        for object_id, obj in world.objects.items()
    }
    before_camera = thaw_value(render_packet.camera)
    before_environment = tuple(thaw_value(row) for row in render_packet.environment_delta)

    verdict = validate_render_claims(
        render_packet,
        rendered_event_ids={event.event_id for event in render_packet.confirmed_events},
        rendered_object_states=_rendered_object_states(render_packet),
        rendered_scene_id=render_packet.scene_id,
        rendered_actor_state_refs=render_packet.actor_state_refs,
        rendered_camera={
            "camera_intent": thaw_value(receipt.staging_metadata)["camera_intent"]
        },
    )
    assert verdict.status == "RENDER_MISMATCH"

    assert world.world_state_version == before_version
    assert tuple(world.event_log) == before_events
    assert {
        object_id: (
            obj.damage_state,
            obj.contamination_state,
            obj.is_open,
            obj.owner_actor_id,
            obj.zone_id,
        )
        for object_id, obj in world.objects.items()
    } == before_objects
    assert thaw_value(render_packet.camera) == before_camera
    assert tuple(thaw_value(row) for row in render_packet.environment_delta) == before_environment


def test_two_valid_director_staging_choices_do_not_change_canonical_render_truth():
    world_a, packet_a, receipt_a, render_a, *_ = _materials(FIXTURE.STAGING_A)
    world_b, packet_b, receipt_b, render_b, *_ = _materials(FIXTURE.STAGING_B)

    assert receipt_a.staging_metadata != receipt_b.staging_metadata
    assert receipt_a.source_packet_sha256 == receipt_b.source_packet_sha256
    assert receipt_a.protected_material_sha256 == receipt_b.protected_material_sha256
    assert i9a.packet_sha256(packet_a) == i9a.packet_sha256(packet_b)

    assert world_a.world_state_version == world_b.world_state_version
    assert tuple(event.event_id for event in world_a.event_log) == tuple(
        event.event_id for event in world_b.event_log
    )
    assert thaw_value(render_a.camera) == thaw_value(render_b.camera)
    assert tuple(thaw_value(row) for row in render_a.environment_delta) == tuple(
        thaw_value(row) for row in render_b.environment_delta
    )
    assert tuple(event.event_id for event in render_a.confirmed_events) == tuple(
        event.event_id for event in render_b.confirmed_events
    )
    assert _aligned_validation(render_a).status == "RENDER_ALIGNED"
    assert _aligned_validation(render_b).status == "RENDER_ALIGNED"


def test_gap_proof_classifies_missing_runtime_adapter_without_redesigning_af_h():
    _, _, receipt, render_packet, *_ = _materials()
    profile = _director_handoff_profile()

    # AF-H already authorizes bounded staging. The missing piece is the governed runtime
    # translation/admission bridge into the current renderer camera vocabulary.
    staging = thaw_value(receipt.staging_metadata)
    camera = thaw_value(render_packet.camera)
    assert profile["staging_authority"] == ["AI_DIRECTOR"]
    assert "RENDERER_PUBLICATION" in profile["downstream_consumer"]
    assert "camera_intent" in staging
    assert "camera_intent" not in camera
    assert "mode" in camera
    assert "mode" not in staging
    assert receipt.authority_class == "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"
    assert render_packet.renderer_constraints["no_world_rule_mutation"] is True
    assert render_packet.renderer_constraints["no_unconfirmed_outcome_invention"] is True
    assert render_packet.renderer_constraints["preserve_object_state"] is True
