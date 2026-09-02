import importlib.util
from pathlib import Path

import pytest

import evals.i9a_director_beat_packet_federation_mock as i9a
from evals.current_observation_evidence_reference import (
    assess_current_visual_observation_gap,
)
from evals.player_acquisition_evidence_reference import (
    assess_direct_participation_gap,
)


def _load_accepted_i9a_fixture_module():
    """Reuse the accepted I9A deterministic fixture without changing its accepted test blob."""
    path = Path(__file__).with_name("test_i9a_director_beat_packet_federation_mock.py")
    spec = importlib.util.spec_from_file_location("_cell_world_d_i9a_fixture", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("CELL_WORLD_D_I9A_FIXTURE_IMPORT_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


FIXTURE = _load_accepted_i9a_fixture_module()


def _materials():
    (
        i8c_package,
        i3a_package,
        world,
        definition,
        damage,
        speech,
        acquisition,
    ) = FIXTURE.make_packages()
    packet = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert packet is not None
    return (
        i8c_package,
        i3a_package,
        world,
        definition,
        damage,
        speech,
        acquisition,
        packet,
    )


def test_director_confirmed_event_context_is_not_character_knowledge():
    (
        _,
        _,
        world,
        _,
        damage,
        speech,
        acquisition,
        packet,
    ) = _materials()

    # Director staging may consume replay-validated canonical event context.
    assert packet.confirmed_event_refs == (
        damage.event_id,
        speech.event_id,
        acquisition.event_id,
    )
    assert damage.event_id in world.committed_event_ids

    # But V0 has no authority to reinterpret those event refs as any character-facing
    # knowledge partition. Event context and epistemic possession are different planes.
    assert packet.player_visible_knowledge_refs == ()
    assert packet.public_visible_knowledge_refs == ()
    assert packet.private_forbidden_knowledge_refs == ()
    assert "AF_H_NO_KNOWLEDGE_VISIBILITY_REWRITE" in packet.forbidden_inventions
    assert packet.authority_class == "NON_CANONICAL_I9A_DIRECTOR_BEAT_PACKET_REFERENCE_ONLY"


def test_director_event_visibility_does_not_cure_player_direct_participation_gap():
    _, _, world, _, damage, _, _, packet = _materials()

    assert damage.event_id in packet.confirmed_event_refs
    before = assess_direct_participation_gap(
        world=world,
        player_id=FIXTURE.PRINCIPAL,
        event=damage,
    )
    assert before.player_actor_binding_proven is True
    assert before.primary_event_eligibility_proven is True
    assert before.replay_explicit_player_action_provenance_available is False
    assert before.receipt_available is False
    assert before.status == "BLOCKED_MISSING_REPLAY_PLAYER_ACTION_PROVENANCE"

    # Merely constructing/possessing a Director packet is a downstream read. It cannot
    # promote the world event into player-local acquisition evidence.
    after = assess_direct_participation_gap(
        world=world,
        player_id=FIXTURE.PRINCIPAL,
        event=damage,
    )
    assert after == before
    assert packet.player_visible_knowledge_refs == ()


def test_director_packet_construction_does_not_mint_current_observation():
    _, _, world, _, _, _, _, packet = _materials()

    before = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=FIXTURE.NPC,
        entity_id=FIXTURE.DOOR,
    )
    assert before.receipt_available is False
    assert before.trusted_discrete_trigger_available is False

    # I9A derives a staging packet from separately replayed upstream evidence. That action
    # cannot become a trusted discrete perception trigger in this world instance.
    after = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=FIXTURE.NPC,
        entity_id=FIXTURE.DOOR,
    )
    assert after == before
    assert packet.player_visible_knowledge_refs == ()
    assert packet.public_visible_knowledge_refs == ()


def test_ai_film_response_cannot_return_protected_knowledge_or_world_fields():
    i8c_package, i3a_package, _, _, damage, _, _, packet = _materials()

    for protected_key, protected_value in (
        ("player_visible_knowledge_refs", [damage.event_id]),
        ("public_visible_knowledge_refs", [damage.event_id]),
        ("confirmed_event_refs", [damage.event_id]),
        ("world_state_version", "FORGED-WORLD-VERSION"),
    ):
        response = FIXTURE.good_mock_response(packet)
        response[protected_key] = protected_value
        with pytest.raises(
            ValueError,
            match="I9A_AI_FILM_PROTECTED_OR_UNKNOWN_FIELD_FORBIDDEN",
        ):
            i9a.consume_mock_ai_film_response(
                i8c_replay_package=i8c_package,
                i3a_replay_package_json=i3a_package,
                response=response,
            )


def test_ai_film_staging_metadata_cannot_hide_a_knowledge_side_channel():
    i8c_package, i3a_package, _, _, damage, _, _, packet = _materials()

    response = FIXTURE.good_mock_response(packet)
    response["staging_metadata"]["knowledge_hint"] = damage.event_id
    with pytest.raises(
        ValueError,
        match="I9A_STAGING_METADATA_AUTHORITY_EXPANSION_FORBIDDEN:knowledge_hint",
    ):
        i9a.consume_mock_ai_film_response(
            i8c_replay_package=i8c_package,
            i3a_replay_package_json=i3a_package,
            response=response,
        )


def test_valid_staging_changes_only_staging_and_has_zero_side_effect_authority():
    i8c_package, i3a_package, world, _, damage, _, _, packet = _materials()
    participation_before = assess_direct_participation_gap(
        world=world,
        player_id=FIXTURE.PRINCIPAL,
        event=damage,
    )
    observation_before = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=FIXTURE.NPC,
        entity_id=FIXTURE.DOOR,
    )

    receipt_a = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=FIXTURE.good_mock_response(packet, FIXTURE.STAGING_A),
    )
    receipt_b = i9a.consume_mock_ai_film_response(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
        response=FIXTURE.good_mock_response(packet, FIXTURE.STAGING_B),
    )

    assert receipt_a.status == "MOCK_AI_FILM_STAGING_ACCEPTED"
    assert receipt_b.status == "MOCK_AI_FILM_STAGING_ACCEPTED"
    assert receipt_a.source_packet_sha256 == receipt_b.source_packet_sha256
    assert receipt_a.protected_material_sha256 == receipt_b.protected_material_sha256
    assert receipt_a.staging_metadata != receipt_b.staging_metadata
    assert receipt_a.world_mutation_count == receipt_b.world_mutation_count == 0
    assert receipt_a.provider_call_count == receipt_b.provider_call_count == 0
    assert receipt_a.authority_class == "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"
    assert receipt_b.authority_class == "NON_CANONICAL_MOCK_AI_FILM_STAGING_EVIDENCE_ONLY"

    participation_after = assess_direct_participation_gap(
        world=world,
        player_id=FIXTURE.PRINCIPAL,
        event=damage,
    )
    observation_after = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=FIXTURE.NPC,
        entity_id=FIXTURE.DOOR,
    )
    assert participation_after == participation_before
    assert observation_after == observation_before


def test_rebuild_is_deterministic_without_epistemic_promotion():
    i8c_package, i3a_package, world, _, damage, _, _, first = _materials()
    second = i9a.build_director_beat_packet_reference(
        i8c_replay_package=i8c_package,
        i3a_replay_package_json=i3a_package,
    )
    assert second is not None

    assert i9a.packet_sha256(second) == i9a.packet_sha256(first)
    assert i9a.protected_material_sha256(second) == i9a.protected_material_sha256(first)
    assert second.confirmed_event_refs == first.confirmed_event_refs
    assert second.player_visible_knowledge_refs == first.player_visible_knowledge_refs == ()
    assert second.public_visible_knowledge_refs == first.public_visible_knowledge_refs == ()
    assert second.private_forbidden_knowledge_refs == first.private_forbidden_knowledge_refs == ()

    participation = assess_direct_participation_gap(
        world=world,
        player_id=FIXTURE.PRINCIPAL,
        event=damage,
    )
    observation = assess_current_visual_observation_gap(
        world=world,
        observer_actor_id=FIXTURE.NPC,
        entity_id=FIXTURE.DOOR,
    )
    assert participation.receipt_available is False
    assert observation.receipt_available is False
