from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path
from typing import Iterable, Mapping


POLICY_NEUTRAL_EXPERIMENT_ONLY = True
NO_PRODUCTION_AUDIENCE_POLICY_SELECTED = True
NO_WORLD_MUTATION = True
NO_PLAYER_KNOWLEDGE_WRITE = True
NO_NPC_KNOWLEDGE_WRITE = True
NO_PROVIDER_OR_NETWORK = True
NO_PUBLICATION_BACKEND = True

_ROOT = Path(__file__).resolve().parents[1]
_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_EXPECTED_PUBLICATION_FIELDS = {
    "publication_id",
    "audience_class",
    "source_event_refs",
    "allowed_information_refs",
    "redacted_information_refs",
    "presentation_refs",
    "policy_version",
}
_EXPECTED_AUTHORITY_PROFILE = "PUBLICATION_DERIVED_PROJECTION"
_EXPECTED_MUTATION_FRAGMENT = "CANNOT_FLOW_BACK_INTO_PLAYER_OR_NPC_KNOWLEDGE"

AUDIENCE_CANDIDATES = frozenset(
    {
        "STRICT_PLAYER_EQUIVALENT",
        "OMNISCIENT_SPECTATOR_CANDIDATE",
        "DELAYED_REVEAL_CANDIDATE",
        "PER_PROJECT_POLICY_CANDIDATE",
    }
)


@dataclass(frozen=True)
class PublicationProjectionEvidence:
    publication_id: str
    audience_class: str
    source_event_refs: tuple[str, ...]
    allowed_information_refs: tuple[str, ...]
    redacted_information_refs: tuple[str, ...]
    presentation_refs: tuple[str, ...]
    policy_id: str
    policy_version: str
    current_cursor: int
    reveal_cursor: int | None
    canonical_data_authority: str = "NONE"
    player_knowledge_write_authority: str = "NONE"
    npc_knowledge_write_authority: str = "NONE"
    world_mutation_count: int = 0
    knowledge_mutation_count: int = 0
    authority_class: str = "NON_CANONICAL_PUBLICATION_POLICY_EVAL_ONLY"


def _strict_unique_refs(values: Iterable[str], code: str) -> tuple[str, ...]:
    refs = tuple(values)
    if any(not isinstance(ref, str) or not ref.strip() for ref in refs):
        raise ValueError(code)
    if len(set(refs)) != len(refs):
        raise ValueError(f"{code}_DUPLICATE")
    return tuple(sorted(refs))


def _load_contract_guard() -> None:
    data = json.loads(_CONTRACT_PATH.read_text(encoding="utf-8"))
    publication = data["type_registry"]["PublicationProjection"]
    if publication.get("authority_profile_ref") != _EXPECTED_AUTHORITY_PROFILE:
        raise ValueError("PUBLICATION_AUTHORITY_PROFILE_DRIFT")
    if set(publication.get("fields", ())) != _EXPECTED_PUBLICATION_FIELDS:
        raise ValueError("PUBLICATION_FIELDS_DRIFT")
    profile = data["authority_semantics"]["profiles"][_EXPECTED_AUTHORITY_PROFILE]
    if profile.get("producer_or_assembler") != ["RENDERER_PUBLICATION"]:
        raise ValueError("PUBLICATION_PRODUCER_DRIFT")
    mutation_constraint = str(profile.get("mutation_constraint", ""))
    if _EXPECTED_MUTATION_FRAGMENT not in mutation_constraint:
        raise ValueError("PUBLICATION_FLOWBACK_GUARD_DRIFT")


def _projection_id(material: Mapping[str, object]) -> str:
    encoded = json.dumps(material, sort_keys=True, separators=(",", ":"), allow_nan=False)
    return "PUB-EVAL-" + hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:24]


def evaluate_publication_projection(
    *,
    audience_class: str,
    policy_id: str,
    policy_version: str,
    source_event_refs: Iterable[str],
    available_information_refs: Iterable[str],
    requested_allowed_information_refs: Iterable[str],
    requested_redacted_information_refs: Iterable[str],
    presentation_refs: Iterable[str] = (),
    player_visible_information_refs: Iterable[str] = (),
    spectator_visible_information_refs: Iterable[str] = (),
    current_cursor: int = 0,
    reveal_cursor: int | None = None,
) -> PublicationProjectionEvidence:
    _load_contract_guard()
    if audience_class not in AUDIENCE_CANDIDATES:
        raise ValueError("PUBLICATION_AUDIENCE_CANDIDATE_UNSUPPORTED")
    if not isinstance(policy_id, str) or not policy_id.strip():
        raise ValueError("PUBLICATION_POLICY_ID_REQUIRED")
    if not isinstance(policy_version, str) or not policy_version.strip():
        raise ValueError("PUBLICATION_POLICY_VERSION_REQUIRED")
    if not isinstance(current_cursor, int) or current_cursor < 0:
        raise ValueError("PUBLICATION_CURRENT_CURSOR_INVALID")

    sources = _strict_unique_refs(source_event_refs, "PUBLICATION_SOURCE_EVENT_REF_INVALID")
    available = set(_strict_unique_refs(available_information_refs, "PUBLICATION_INFORMATION_REF_INVALID"))
    allowed = _strict_unique_refs(requested_allowed_information_refs, "PUBLICATION_ALLOWED_REF_INVALID")
    redacted = _strict_unique_refs(requested_redacted_information_refs, "PUBLICATION_REDACTED_REF_INVALID")
    presentation = _strict_unique_refs(presentation_refs, "PUBLICATION_PRESENTATION_REF_INVALID")
    player_visible = set(_strict_unique_refs(player_visible_information_refs, "PUBLICATION_PLAYER_VISIBLE_REF_INVALID"))
    spectator_visible = set(_strict_unique_refs(spectator_visible_information_refs, "PUBLICATION_SPECTATOR_VISIBLE_REF_INVALID"))

    if set(allowed) & set(redacted):
        raise ValueError("PUBLICATION_ALLOWED_REDACTED_OVERLAP")
    if not set(allowed) <= available or not set(redacted) <= available:
        raise ValueError("PUBLICATION_INFORMATION_NOT_PROVEN_BY_AVAILABLE_SOURCE")
    if player_visible - available or spectator_visible - available:
        raise ValueError("PUBLICATION_VISIBILITY_SET_NOT_PROVEN_BY_AVAILABLE_SOURCE")

    if audience_class == "STRICT_PLAYER_EQUIVALENT":
        if not set(allowed) <= player_visible:
            raise ValueError("PUBLICATION_PLAYER_EQUIVALENT_INFORMATION_EXPANSION")
    elif audience_class == "OMNISCIENT_SPECTATOR_CANDIDATE":
        if not set(allowed) <= spectator_visible:
            raise ValueError("PUBLICATION_SPECTATOR_INFORMATION_EXPANSION")
    elif audience_class == "DELAYED_REVEAL_CANDIDATE":
        if reveal_cursor is None or not isinstance(reveal_cursor, int) or reveal_cursor < 0:
            raise ValueError("PUBLICATION_REVEAL_CURSOR_REQUIRED")
        if current_cursor < reveal_cursor and allowed:
            raise ValueError("PUBLICATION_DELAYED_REVEAL_NOT_YET_ELIGIBLE")
        if set(allowed) - spectator_visible:
            raise ValueError("PUBLICATION_DELAYED_REVEAL_INFORMATION_EXPANSION")
    elif audience_class == "PER_PROJECT_POLICY_CANDIDATE":
        # The caller must provide the candidate allow/redact partition explicitly.
        # This eval validates it but does not promote it into product policy.
        if set(allowed) | set(redacted) != available:
            raise ValueError("PUBLICATION_PROJECT_POLICY_PARTITION_INCOMPLETE")

    material = {
        "audience_class": audience_class,
        "policy_id": policy_id,
        "policy_version": policy_version,
        "source_event_refs": list(sources),
        "allowed_information_refs": list(allowed),
        "redacted_information_refs": list(redacted),
        "presentation_refs": list(presentation),
        "current_cursor": current_cursor,
        "reveal_cursor": reveal_cursor,
    }
    return PublicationProjectionEvidence(
        publication_id=_projection_id(material),
        audience_class=audience_class,
        source_event_refs=sources,
        allowed_information_refs=allowed,
        redacted_information_refs=redacted,
        presentation_refs=presentation,
        policy_id=policy_id,
        policy_version=policy_version,
        current_cursor=current_cursor,
        reveal_cursor=reveal_cursor,
    )
