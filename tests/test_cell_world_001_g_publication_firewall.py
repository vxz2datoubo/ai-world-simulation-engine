from dataclasses import FrozenInstanceError

import pytest

from evals.publication_projection_policy_neutral_reference import (
    AUDIENCE_CANDIDATES,
    NO_NPC_KNOWLEDGE_WRITE,
    NO_PLAYER_KNOWLEDGE_WRITE,
    NO_PRODUCTION_AUDIENCE_POLICY_SELECTED,
    NO_PROVIDER_OR_NETWORK,
    NO_PUBLICATION_BACKEND,
    NO_WORLD_MUTATION,
    POLICY_NEUTRAL_EXPERIMENT_ONLY,
    evaluate_publication_projection,
)


SOURCES = ("E-DOOR-BROKEN", "E-SECRET-PROMISE")
INFO = ("INFO-DOOR-BROKEN", "INFO-SECRET-PROMISE")
PLAYER_VISIBLE = ("INFO-DOOR-BROKEN",)
SPECTATOR_VISIBLE = INFO


def _project(**overrides):
    args = {
        "audience_class": "STRICT_PLAYER_EQUIVALENT",
        "policy_id": "POLICY-CANDIDATE-1",
        "policy_version": "v1-eval",
        "source_event_refs": SOURCES,
        "available_information_refs": INFO,
        "requested_allowed_information_refs": PLAYER_VISIBLE,
        "requested_redacted_information_refs": ("INFO-SECRET-PROMISE",),
        "presentation_refs": ("PRESENTATION-S1",),
        "player_visible_information_refs": PLAYER_VISIBLE,
        "spectator_visible_information_refs": SPECTATOR_VISIBLE,
        "current_cursor": 20,
        "reveal_cursor": None,
    }
    args.update(overrides)
    return evaluate_publication_projection(**args)


def test_scope_locks_keep_publication_eval_policy_neutral_and_non_authoritative():
    assert POLICY_NEUTRAL_EXPERIMENT_ONLY is True
    assert NO_PRODUCTION_AUDIENCE_POLICY_SELECTED is True
    assert NO_WORLD_MUTATION is True
    assert NO_PLAYER_KNOWLEDGE_WRITE is True
    assert NO_NPC_KNOWLEDGE_WRITE is True
    assert NO_PROVIDER_OR_NETWORK is True
    assert NO_PUBLICATION_BACKEND is True
    assert AUDIENCE_CANDIDATES == {
        "STRICT_PLAYER_EQUIVALENT",
        "OMNISCIENT_SPECTATOR_CANDIDATE",
        "DELAYED_REVEAL_CANDIDATE",
        "PER_PROJECT_POLICY_CANDIDATE",
    }


def test_strict_player_equivalent_can_publish_only_explicit_player_visible_information():
    projection = _project()
    assert projection.allowed_information_refs == ("INFO-DOOR-BROKEN",)
    assert projection.redacted_information_refs == ("INFO-SECRET-PROMISE",)
    assert projection.canonical_data_authority == "NONE"
    assert projection.player_knowledge_write_authority == "NONE"
    assert projection.npc_knowledge_write_authority == "NONE"
    assert projection.world_mutation_count == 0
    assert projection.knowledge_mutation_count == 0

    with pytest.raises(ValueError, match="PLAYER_EQUIVALENT_INFORMATION_EXPANSION"):
        _project(requested_allowed_information_refs=INFO, requested_redacted_information_refs=())


def test_omniscient_candidate_can_differ_from_player_view_without_flowing_back():
    strict = _project()
    omniscient = _project(
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
        requested_allowed_information_refs=INFO,
        requested_redacted_information_refs=(),
    )
    assert strict.allowed_information_refs != omniscient.allowed_information_refs
    assert omniscient.allowed_information_refs == tuple(sorted(INFO))
    assert omniscient.player_knowledge_write_authority == "NONE"
    assert omniscient.npc_knowledge_write_authority == "NONE"
    assert omniscient.knowledge_mutation_count == 0
    assert strict.source_event_refs == omniscient.source_event_refs


def test_omniscient_candidate_still_cannot_publish_caller_invented_information():
    with pytest.raises(ValueError, match="INFORMATION_NOT_PROVEN_BY_AVAILABLE_SOURCE"):
        _project(
            audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
            requested_allowed_information_refs=("INFO-CALLER-INVENTED",),
            requested_redacted_information_refs=(),
        )

    with pytest.raises(ValueError, match="SPECTATOR_INFORMATION_EXPANSION"):
        _project(
            audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
            requested_allowed_information_refs=("INFO-SECRET-PROMISE",),
            requested_redacted_information_refs=("INFO-DOOR-BROKEN",),
            spectator_visible_information_refs=PLAYER_VISIBLE,
        )


def test_delayed_reveal_candidate_fails_before_explicit_reveal_cursor():
    with pytest.raises(ValueError, match="DELAYED_REVEAL_NOT_YET_ELIGIBLE"):
        _project(
            audience_class="DELAYED_REVEAL_CANDIDATE",
            requested_allowed_information_refs=("INFO-SECRET-PROMISE",),
            requested_redacted_information_refs=("INFO-DOOR-BROKEN",),
            current_cursor=19,
            reveal_cursor=20,
        )

    revealed = _project(
        audience_class="DELAYED_REVEAL_CANDIDATE",
        requested_allowed_information_refs=("INFO-SECRET-PROMISE",),
        requested_redacted_information_refs=("INFO-DOOR-BROKEN",),
        current_cursor=20,
        reveal_cursor=20,
    )
    assert revealed.allowed_information_refs == ("INFO-SECRET-PROMISE",)
    assert revealed.knowledge_mutation_count == 0


def test_per_project_candidate_requires_complete_explicit_partition_but_does_not_promote_it():
    projection = _project(
        audience_class="PER_PROJECT_POLICY_CANDIDATE",
        policy_id="PROJECT-X-SPOILER-CANDIDATE",
        requested_allowed_information_refs=("INFO-DOOR-BROKEN",),
        requested_redacted_information_refs=("INFO-SECRET-PROMISE",),
    )
    assert projection.policy_id == "PROJECT-X-SPOILER-CANDIDATE"
    assert projection.authority_class == "NON_CANONICAL_PUBLICATION_POLICY_EVAL_ONLY"

    with pytest.raises(ValueError, match="PROJECT_POLICY_PARTITION_INCOMPLETE"):
        _project(
            audience_class="PER_PROJECT_POLICY_CANDIDATE",
            requested_allowed_information_refs=("INFO-DOOR-BROKEN",),
            requested_redacted_information_refs=(),
        )


def test_allowed_and_redacted_refs_must_be_disjoint_unique_and_source_proven():
    with pytest.raises(ValueError, match="ALLOWED_REDACTED_OVERLAP"):
        _project(
            requested_allowed_information_refs=("INFO-DOOR-BROKEN",),
            requested_redacted_information_refs=("INFO-DOOR-BROKEN",),
        )
    with pytest.raises(ValueError, match="PUBLICATION_ALLOWED_REF_INVALID_DUPLICATE"):
        _project(
            requested_allowed_information_refs=("INFO-DOOR-BROKEN", "INFO-DOOR-BROKEN"),
            requested_redacted_information_refs=("INFO-SECRET-PROMISE",),
        )
    with pytest.raises(ValueError, match="INFORMATION_NOT_PROVEN_BY_AVAILABLE_SOURCE"):
        _project(
            requested_allowed_information_refs=("INFO-UNKNOWN",),
            requested_redacted_information_refs=("INFO-SECRET-PROMISE",),
        )


def test_projection_identity_is_deterministic_and_immutable():
    a = _project()
    b = _project()
    assert a == b
    assert a.publication_id == b.publication_id
    with pytest.raises((FrozenInstanceError, AttributeError)):
        a.player_knowledge_write_authority = "WRITE"


def test_publication_evidence_cannot_be_treated_as_gameplay_knowledge_receipt():
    projection = _project(
        audience_class="OMNISCIENT_SPECTATOR_CANDIDATE",
        requested_allowed_information_refs=INFO,
        requested_redacted_information_refs=(),
    )
    assert "INFO-SECRET-PROMISE" in projection.allowed_information_refs
    assert not hasattr(projection, "player_chronicle_write")
    assert not hasattr(projection, "npc_memory_write")
    assert not hasattr(projection, "belief_write")
    assert projection.player_knowledge_write_authority == "NONE"
    assert projection.npc_knowledge_write_authority == "NONE"
