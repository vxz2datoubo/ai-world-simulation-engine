"""Bounded functional-impairment applicability admission for I2A-009.

This module implements only the structural, deterministic projection frozen by
I2A-008. It validates canonical authority, binds the projection to already
admitted ActorBaseProfile and ActionDemand receipts, and projects exact
function-local InjuryState evidence. It does not implement numeric impairment,
healing, combat, probability, persistence, or capability-resolver changes.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
import json
from pathlib import Path
from types import MappingProxyType
from typing import Any

from .action_demand_admission import ActionDemandAdmissionReceipt
from .actor_profile_admission import ActorBaseProfileAdmissionReceipt


I2_RUNTIME_AUTHORITY_NOT_GRANTED = True
NO_I2_RUNTIME_IMPLEMENTED = True
RUNTIME_SEMANTICS_UNCHANGED = True

_ROOT = Path(__file__).resolve().parents[2]
_CANONICAL_CONTRACT_PATH = _ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
_BINDING_PATH = _ROOT / "contracts" / "AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"
_CONTRACT_RELATIVE_PATH = "contracts/AF001-LIVING-STORY-CONTRACTS.json"
_BINDING_RELATIVE_PATH = "contracts/AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json"
_EXPECTED_AUTHORITY_GRAPH_VERSION = "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
_EXPECTED_LOCKS = {
    "I2_RUNTIME_AUTHORITY_NOT_GRANTED": True,
    "NO_I2_RUNTIME_IMPLEMENTED": True,
    "RUNTIME_SEMANTICS_UNCHANGED": True,
}
_NUMERIC_OVERRIDE_FIELDS = {"penalty", "coefficient", "multiplier", "numeric_effect"}
_PRESENTATION_SOURCE_TYPES = {
    "DressingState",
    "ActorPresentationState",
    "ActorPresentationRequirements",
}


@dataclass(frozen=True)
class FunctionalImpairmentAdmissionReceipt:
    actor_id: str
    demand_id: str
    ruleset_version: str
    required_body_functions: tuple[str, ...]
    applicable_impairment_refs_by_function: Mapping[str, tuple[str, ...]]
    source_injury_refs: tuple[str, ...]
    source_event_refs: tuple[str, ...]
    source_demand_ref: str
    replay_input_ref: str
    numeric_effect_status: str
    canonical_contract_id: str
    canonical_contract_version: str
    authority_graph_version: str
    binding_id: str
    binding_version: str
    projection: Mapping[str, Any]


def _require_nonempty_string(value: Any, error: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(error)
    return value


def _load_json(path: Path, unavailable_error: str) -> Mapping[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            value = json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise ValueError(unavailable_error) from None
    if not isinstance(value, Mapping):
        raise ValueError(unavailable_error.replace("UNAVAILABLE", "INVALID"))
    return value


def _load_canonical_authority() -> tuple[str, str, str, str, str, str]:
    error = "I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID"
    source_type_error = "I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH"

    contract = _load_json(_CANONICAL_CONTRACT_PATH, error)
    binding = _load_json(_BINDING_PATH, error)

    contract_id = _require_nonempty_string(contract.get("contract_id"), error)
    contract_version = _require_nonempty_string(contract.get("contract_version"), error)
    authority_graph_version = _require_nonempty_string(contract.get("authority_graph_version"), error)
    if authority_graph_version != _EXPECTED_AUTHORITY_GRAPH_VERSION:
        raise ValueError(error)

    artifact_roles = contract.get("artifact_roles")
    if not isinstance(artifact_roles, Mapping) or artifact_roles.get(_CONTRACT_RELATIVE_PATH) != "MACHINE_CONTRACT_REGISTRY":
        raise ValueError(error)

    binding_id = _require_nonempty_string(binding.get("binding_id"), error)
    binding_version = _require_nonempty_string(binding.get("binding_version"), error)
    registrations = contract.get("registered_contract_extensions")
    if not isinstance(registrations, Mapping):
        raise ValueError(error)
    registration = registrations.get(binding_id)
    if not isinstance(registration, Mapping):
        raise ValueError(error)
    if (
        registration.get("path") != _BINDING_RELATIVE_PATH
        or registration.get("binding_version") != binding_version
        or registration.get("parent_contract_id") != contract_id
        or registration.get("parent_contract_version") != contract_version
        or registration.get("parent_authority_graph_version") != authority_graph_version
        or registration.get("authority") != "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        or registration.get("registration_class") != "ADDITIVE_NON_RUNTIME_CANDIDATE_EXTENSION"
        or registration.get("runtime_implementation_authorized") is not False
    ):
        raise ValueError(error)

    parent = binding.get("parent_machine_contract")
    if not isinstance(parent, Mapping):
        raise ValueError(error)
    if (
        parent.get("path") != _CONTRACT_RELATIVE_PATH
        or parent.get("contract_id") != contract_id
        or parent.get("contract_version") != contract_version
        or parent.get("authority_graph_version") != authority_graph_version
    ):
        raise ValueError(error)

    if binding.get("runtime_implementation_authorized") is not False:
        raise ValueError(error)
    if binding.get("authority_locks") != _EXPECTED_LOCKS:
        raise ValueError(error)

    authority_rule = contract.get("functional_impairment_extension_authority_rule")
    if not isinstance(authority_rule, str) or "PRE_I2A008_1_9_WITHOUT_AUTHORITY_GRAPH_DISCRIMINATOR_CANNOT_AUTHORIZE" not in authority_rule:
        raise ValueError(error)
    graph = contract.get("versioning_and_migration", {}).get("authority_graph_discriminator")
    if not isinstance(graph, Mapping):
        raise ValueError(error)
    if (
        graph.get("current") != authority_graph_version
        or graph.get("pre_i2a008_state") != "FIELD_ABSENT"
        or graph.get("authorization_tuple") != ["contract_id", "contract_version", "authority_graph_version"]
    ):
        raise ValueError(error)

    decisions = binding.get("canonical_decisions")
    projection = binding.get("projection_schema")
    if not isinstance(decisions, Mapping) or not isinstance(projection, Mapping):
        raise ValueError(error)
    if (
        decisions.get("required_body_functions_role") != "EXACT_FUNCTION_NAMESPACE_APPLICABILITY_FILTER_ONLY"
        or decisions.get("function_identity_rule") != "EXACT_NONEMPTY_VERSION_BOUND_STRING_EQUALITY_ONLY_NO_ALIAS_OR_ANATOMY_INFERENCE"
        or decisions.get("numeric_effect_status") != "DEFERRED_RULESET_TUNING"
        or decisions.get("numeric_application_authorized") is not False
        or decisions.get("severity_consumed_for_numeric_effect") is not False
        or decisions.get("caller_penalty_or_coefficient_consumed") is not False
        or projection.get("numeric_projection_rule") != "NO_NUMERIC_PENALTY_MULTIPLIER_SEVERITY_MAPPING_STACKING_OR_RECOVERY_VALUE_IS_MATERIALIZED_BY_THIS_CONTRACT"
    ):
        raise ValueError(error)

    source_bindings = binding.get("source_type_bindings")
    registry = contract.get("type_registry")
    if not isinstance(source_bindings, Mapping) or not isinstance(registry, Mapping):
        raise ValueError(source_type_error)
    for name in ("ActorBaseProfile", "ActionDemandProfile", "InjuryState", "DressingState"):
        frozen = source_bindings.get(name)
        actual = registry.get(name)
        if not isinstance(frozen, Mapping) or not isinstance(actual, Mapping):
            raise ValueError(source_type_error)
        if actual.get("type_id") != frozen.get("type_id") or actual.get("version") != frozen.get("version"):
            raise ValueError(source_type_error)

    injury_version = _require_nonempty_string(source_bindings["InjuryState"].get("version"), source_type_error)
    return contract_id, contract_version, authority_graph_version, binding_id, binding_version, injury_version


def _bind_admitted_inputs(
    actor_receipt: ActorBaseProfileAdmissionReceipt,
    demand_receipt: ActionDemandAdmissionReceipt,
    demand: Mapping[str, Any],
    source_demand_ref: str,
    replay_input_ref: str,
    *,
    canonical_contract_id: str,
    canonical_contract_version: str,
) -> tuple[str, str, str, tuple[str, ...], str, str]:
    if not isinstance(actor_receipt, ActorBaseProfileAdmissionReceipt):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH")
    if not isinstance(demand_receipt, ActionDemandAdmissionReceipt):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH")
    if not isinstance(demand, Mapping):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH")

    if (
        actor_receipt.canonical_contract_id != canonical_contract_id
        or actor_receipt.canonical_contract_version != canonical_contract_version
        or demand_receipt.canonical_contract_id != canonical_contract_id
        or demand_receipt.canonical_contract_version != canonical_contract_version
    ):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_CANONICAL_BINDING_INVALID")

    actor_id = _require_nonempty_string(
        actor_receipt.actor_id,
        "I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH",
    )
    demand_id = _require_nonempty_string(
        demand.get("demand_id"),
        "I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH",
    )
    ruleset_version = _require_nonempty_string(
        demand.get("ruleset_version"),
        "I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH",
    )
    if demand_id != demand_receipt.demand_id or ruleset_version != demand_receipt.ruleset_version:
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH")

    source_ref = _require_nonempty_string(
        source_demand_ref,
        "I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH",
    )
    replay_ref = _require_nonempty_string(
        replay_input_ref,
        "I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH",
    )
    if (
        demand_receipt.provenance.get("source_demand_ref") != source_ref
        or demand_receipt.provenance.get("replay_input_ref") != replay_ref
    ):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_DEMAND_BINDING_MISMATCH")

    required = demand.get("required_body_functions")
    if not isinstance(required, list):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID")
    required_refs: list[str] = []
    for ref in required:
        required_refs.append(
            _require_nonempty_string(ref, "I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID")
        )

    return actor_id, demand_id, ruleset_version, tuple(sorted(required_refs)), source_ref, replay_ref


def _project_injury_sources(
    injury_sources: Sequence[Mapping[str, Any]],
    *,
    actor_id: str,
    required_body_functions: tuple[str, ...],
    expected_injury_version: str,
) -> tuple[Mapping[str, tuple[str, ...]], tuple[str, ...], tuple[str, ...]]:
    if isinstance(injury_sources, (str, bytes)) or not isinstance(injury_sources, Sequence):
        raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")

    required_set = set(required_body_functions)
    seen_impairment_refs: set[str] = set()
    source_injury_refs: list[str] = []
    source_event_refs: list[str] = []
    applicable: dict[str, list[str]] = {}

    for source in injury_sources:
        if not isinstance(source, Mapping):
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        source_type = source.get("source_type")
        if source_type != "InjuryState":
            if source_type in _PRESENTATION_SOURCE_TYPES:
                raise ValueError("I2A_PRESENTATION_CANNOT_AUTHOR_FUNCTIONAL_IMPAIRMENT")
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        if source.get("source_type_version") != expected_injury_version:
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_SOURCE_TYPE_VERSION_MISMATCH")
        if source.get("actor_id") != actor_id:
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_ACTOR_BINDING_MISMATCH")

        injury_id = _require_nonempty_string(
            source.get("injury_id"),
            "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED",
        )
        event_ref = _require_nonempty_string(
            source.get("source_event_ref"),
            "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED",
        )
        source_injury_refs.append(injury_id)
        source_event_refs.append(event_ref)

        impairments = source.get("functional_impairments")
        if not isinstance(impairments, list):
            raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
        for impairment in impairments:
            if not isinstance(impairment, Mapping):
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")
            extras = set(impairment) - {"impairment_ref", "function_ref"}
            if extras & _NUMERIC_OVERRIDE_FIELDS:
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_NUMERIC_OVERRIDE_NOT_AUTHORIZED")
            if extras:
                raise ValueError("I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED")

            impairment_ref = _require_nonempty_string(
                impairment.get("impairment_ref"),
                "I2A_FUNCTIONAL_IMPAIRMENT_EVIDENCE_MALFORMED",
            )
            function_ref = _require_nonempty_string(
                impairment.get("function_ref"),
                "I2A_FUNCTIONAL_IMPAIRMENT_FUNCTION_REF_INVALID",
            )
            if impairment_ref in seen_impairment_refs:
                raise ValueError("I2A_DUPLICATE_FUNCTIONAL_IMPAIRMENT_REFERENCE")
            seen_impairment_refs.add(impairment_ref)

            if function_ref in required_set:
                applicable.setdefault(function_ref, []).append(impairment_ref)

    frozen_applicable = MappingProxyType(
        {key: tuple(sorted(values)) for key, values in sorted(applicable.items())}
    )
    return (
        frozen_applicable,
        tuple(sorted(source_injury_refs)),
        tuple(sorted(source_event_refs)),
    )


def admit_functional_impairment_applicability(
    actor_receipt: ActorBaseProfileAdmissionReceipt,
    demand_receipt: ActionDemandAdmissionReceipt,
    demand: Mapping[str, Any],
    injury_sources: Sequence[Mapping[str, Any]],
    *,
    source_demand_ref: str,
    replay_input_ref: str,
) -> FunctionalImpairmentAdmissionReceipt:
    """Validate and materialize the structural impairment applicability projection."""
    (
        contract_id,
        contract_version,
        authority_graph_version,
        binding_id,
        binding_version,
        injury_version,
    ) = _load_canonical_authority()

    (
        actor_id,
        demand_id,
        ruleset_version,
        required_body_functions,
        source_ref,
        replay_ref,
    ) = _bind_admitted_inputs(
        actor_receipt,
        demand_receipt,
        demand,
        source_demand_ref,
        replay_input_ref,
        canonical_contract_id=contract_id,
        canonical_contract_version=contract_version,
    )

    applicable, source_injury_refs, source_event_refs = _project_injury_sources(
        injury_sources,
        actor_id=actor_id,
        required_body_functions=required_body_functions,
        expected_injury_version=injury_version,
    )

    projection = MappingProxyType(
        {
            "actor_id": actor_id,
            "demand_id": demand_id,
            "ruleset_version": ruleset_version,
            "required_body_functions": required_body_functions,
            "applicable_impairment_refs_by_function": applicable,
            "source_injury_refs": source_injury_refs,
            "source_event_refs": source_event_refs,
            "source_demand_ref": source_ref,
            "replay_input_ref": replay_ref,
            "numeric_effect_status": "DEFERRED_RULESET_TUNING",
        }
    )

    return FunctionalImpairmentAdmissionReceipt(
        actor_id=actor_id,
        demand_id=demand_id,
        ruleset_version=ruleset_version,
        required_body_functions=required_body_functions,
        applicable_impairment_refs_by_function=applicable,
        source_injury_refs=source_injury_refs,
        source_event_refs=source_event_refs,
        source_demand_ref=source_ref,
        replay_input_ref=replay_ref,
        numeric_effect_status="DEFERRED_RULESET_TUNING",
        canonical_contract_id=contract_id,
        canonical_contract_version=contract_version,
        authority_graph_version=authority_graph_version,
        binding_id=binding_id,
        binding_version=binding_version,
        projection=projection,
    )
