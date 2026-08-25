"""Bounded deterministic I2A capability resolution reference.

This module implements only the deterministic substrate: hard feasibility,
EffectiveCapability derivation, and Margin calculation. It does not implement
I2 runtime gameplay authority, stochastic resolution, progression, balance, or
injury gameplay.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Any


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True


@dataclass(frozen=True)
class CapabilityResolution:
    feasible: bool
    effective_capability: int | None
    margin: int | None
    provenance: Mapping[str, str]


def resolve_capability(
    *,
    base_attribute_map: Mapping[str, int],
    skill_values: Mapping[str, int],
    difficulty_or_resistance: int,
    required_attributes: tuple[str, ...] = (),
    required_skills: tuple[str, ...] = (),
    provenance: Mapping[str, str],
) -> CapabilityResolution:
    """Resolve bounded deterministic capability ordering.

    Order is fixed: hard feasibility -> EffectiveCapability -> Margin.
    Inputs are caller supplied but must carry schema/ruleset provenance.
    """
    if not provenance.get("profile_schema_ref") or not provenance.get("ruleset_family_ref"):
        raise ValueError("I2A_PROVENANCE_REQUIRED")

    missing_attributes = [key for key in required_attributes if key not in base_attribute_map]
    missing_skills = [key for key in required_skills if key not in skill_values]
    if missing_attributes or missing_skills:
        return CapabilityResolution(False, None, None, dict(provenance))

    effective = sum(base_attribute_map.values()) + sum(skill_values.values())
    margin = effective - difficulty_or_resistance
    return CapabilityResolution(True, effective, margin, dict(provenance))
