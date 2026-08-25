"""Bounded deterministic I2A capability resolution reference.

This module consumes only provenance-bound validated capability envelopes.
It does not accept arbitrary caller capability maps as capability truth.

No I2 runtime gameplay, stochastic resolution, progression, balance, or
injury gameplay is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Mapping


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True


@dataclass(frozen=True)
class CapabilityResolution:
    feasible: bool
    effective_capability: int | float | None
    margin: int | float | None
    provenance: Mapping[str, str]


def _require_provenance(provenance: Mapping[str, str]) -> None:
    if not provenance.get("profile_schema_ref"):
        raise ValueError("I2A_PROFILE_SCHEMA_PROVENANCE_REQUIRED")
    if not provenance.get("ruleset_family_ref"):
        raise ValueError("I2A_RULESET_PROVENANCE_REQUIRED")
    if not provenance.get("replay_input_ref"):
        raise ValueError("I2A_REPLAY_PROVENANCE_REQUIRED")


def _require_demand_references(value: Any, error: str) -> tuple[str, ...]:
    if not isinstance(value, (tuple, list)):
        raise ValueError(error)
    if any(not isinstance(key, str) or not key for key in value):
        raise ValueError(error)
    references = tuple(value)
    if len(references) != len(set(references)):
        raise ValueError("I2A_DUPLICATE_DEMAND_REFERENCE")
    return references


def _require_finite_number(value: Any, error: str) -> int | float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(error)
    if isinstance(value, int):
        return value
    if not math.isfinite(value):
        raise ValueError(error)
    return value


def resolve_capability(
    *,
    capability_envelope: Mapping[str, Any],
    action_demand_profile: Mapping[str, Any],
    provenance: Mapping[str, str],
) -> CapabilityResolution:
    """Resolve canonical deterministic capability ordering.

    Order is fixed:
    1. Hard feasibility
    2. EffectiveCapability
    3. Margin = EffectiveCapability - DifficultyOrResistance

    Inputs must already be validated ActorBaseProfile derived attributes,
    SkillLedger derived values, and ActionDemandProfile semantics.
    """
    _require_provenance(provenance)

    if not isinstance(capability_envelope, Mapping):
        raise ValueError("I2A_CAPABILITY_ENVELOPE_REQUIRED")

    attributes = capability_envelope.get("validated_actor_base_attributes")
    skills = capability_envelope.get("validated_skill_ledger_values")
    if not isinstance(attributes, Mapping) or not isinstance(skills, Mapping):
        raise ValueError("I2A_VALIDATED_CAPABILITY_INPUT_REQUIRED")
    if not isinstance(action_demand_profile, Mapping):
        raise ValueError("I2A_ACTION_DEMAND_PROFILE_REQUIRED")

    required_attributes = _require_demand_references(
        action_demand_profile.get("required_attributes", ()),
        "I2A_REQUIRED_ATTRIBUTES_INVALID",
    )
    required_skills = _require_demand_references(
        action_demand_profile.get("required_skills", ()),
        "I2A_REQUIRED_SKILLS_INVALID",
    )

    missing_attributes = [key for key in required_attributes if key not in attributes]
    missing_skills = [key for key in required_skills if key not in skills]
    if missing_attributes or missing_skills:
        return CapabilityResolution(False, None, None, dict(provenance))

    if "difficulty_or_resistance" not in action_demand_profile:
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")
    difficulty = _require_finite_number(
        action_demand_profile["difficulty_or_resistance"],
        "I2A_DEMAND_DIFFICULTY_INVALID",
    )

    selected_attributes = [
        _require_finite_number(attributes[key], "I2A_CAPABILITY_VALUE_INVALID")
        for key in required_attributes
    ]
    selected_skills = [
        _require_finite_number(skills[key], "I2A_CAPABILITY_VALUE_INVALID")
        for key in required_skills
    ]

    effective = sum(selected_attributes) + sum(selected_skills)
    margin = effective - difficulty
    return CapabilityResolution(True, effective, margin, dict(provenance))
