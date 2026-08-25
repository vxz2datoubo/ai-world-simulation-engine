"""Bounded deterministic I2A capability resolution reference.

This module consumes only provenance-bound validated capability envelopes.
It does not accept arbitrary caller capability maps as capability truth.

No I2 runtime gameplay, stochastic resolution, progression, balance, or
injury gameplay is implemented here.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True


@dataclass(frozen=True)
class CapabilityResolution:
    feasible: bool
    effective_capability: int | None
    margin: int | None
    provenance: Mapping[str, str]


def _require_provenance(provenance: Mapping[str, str]) -> None:
    if not provenance.get("profile_schema_ref"):
        raise ValueError("I2A_PROFILE_SCHEMA_PROVENANCE_REQUIRED")
    if not provenance.get("ruleset_family_ref"):
        raise ValueError("I2A_RULESET_PROVENANCE_REQUIRED")
    if not provenance.get("replay_input_ref"):
        raise ValueError("I2A_REPLAY_PROVENANCE_REQUIRED")


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

    required_attributes = action_demand_profile.get("required_attributes", ())
    required_skills = action_demand_profile.get("required_skills", ())
    difficulty = action_demand_profile.get("difficulty_or_resistance")

    if difficulty is None:
        raise ValueError("I2A_DEMAND_DIFFICULTY_REQUIRED")

    missing_attributes = [key for key in required_attributes if key not in attributes]
    missing_skills = [key for key in required_skills if key not in skills]
    if missing_attributes or missing_skills:
        return CapabilityResolution(False, None, None, dict(provenance))

    effective = sum(attributes.values()) + sum(skills.values())
    margin = effective - difficulty
    return CapabilityResolution(True, effective, margin, dict(provenance))
