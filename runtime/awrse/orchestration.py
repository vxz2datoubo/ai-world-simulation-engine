"""Deterministic, non-canonical coordination substrate for Living World Stage 1.

This module intentionally has no dependency on ``SimulationEngine`` or mutable
world state.  It schedules receiver *evaluation* from already committed event
evidence; it cannot commit an event, resolve an outcome, or mutate a domain.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from types import MappingProxyType
from typing import Iterable, Mapping


class OrchestrationViolation(ValueError):
    """Raised whenever non-canonical coordination evidence is not admissible."""


_KNOWN_AUTHORITY_SCOPES = frozenset({"AF-A", "AF-B", "AF-C", "AF-D", "AF-E", "AF-F", "AF-G", "AF-H"})
_EVENT_VIEW_SEAL = object()
_MODULE_ADMISSION_SEAL = object()


@dataclass(frozen=True)
class Stage1Provenance:
    """Immutable identity required by the legacy runtime-tree exception."""

    task_id: str
    snapshot_id: str
    baseline_sha: str


_REQUIRED_STAGE1_PROVENANCE = Stage1Provenance(
    task_id="LW-STAGE1-ORCH-001-R1",
    snapshot_id="AWRSE-LW-STAGE1-ORCH-001-R1-SNAPSHOT-001",
    baseline_sha="37dd0310a2740013cf971100789fba0e7d45f7e1",
)
STAGE1_PROVENANCE = _REQUIRED_STAGE1_PROVENANCE


def _stage1_provenance_matches(provenance: Stage1Provenance) -> bool:
    """Return true only for the immutable, snapshot-bound Stage 1 identity."""
    return provenance == _REQUIRED_STAGE1_PROVENANCE


def _canonical_digest(value: object) -> str:
    encoded = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _require_text(value: str, code: str) -> str:
    if not isinstance(value, str) or not value:
        raise OrchestrationViolation(code)
    return value


def _stable_unique(values: Iterable[str], code: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise OrchestrationViolation(code)
    if len(result) != len(set(result)):
        raise OrchestrationViolation(code)
    return tuple(sorted(result))


def _ordered_unique(values: Iterable[str], code: str) -> tuple[str, ...]:
    result = tuple(values)
    if any(not isinstance(value, str) or not value for value in result):
        raise OrchestrationViolation(code)
    if len(result) != len(set(result)):
        raise OrchestrationViolation(code)
    return result


@dataclass(frozen=True)
class WorldCursor:
    world_id: str
    state_version: str

    def __post_init__(self) -> None:
        _require_text(self.world_id, "WORLD_ID_REQUIRED")
        _require_text(self.state_version, "WORLD_STATE_VERSION_REQUIRED")


@dataclass(frozen=True)
class CommittedEventEvidence:
    """Read-only proof of an event already admitted by the canonical ledger."""

    event_id: str
    event_type: str
    canonical_order: int

    def __post_init__(self) -> None:
        _require_text(self.event_id, "COMMITTED_EVENT_ID_REQUIRED")
        _require_text(self.event_type, "COMMITTED_EVENT_TYPE_REQUIRED")
        if isinstance(self.canonical_order, bool) or not isinstance(self.canonical_order, int) or self.canonical_order < 0:
            raise OrchestrationViolation("COMMITTED_EVENT_ORDER_INVALID")

    def identity_material(self) -> dict[str, object]:
        return {"event_id": self.event_id, "event_type": self.event_type, "canonical_order": self.canonical_order}


@dataclass(frozen=True)
class _CommittedEventView:
    """Runtime-owned read view, never a caller-supplied event iterable.

    Stage 1 deliberately does not create a world ledger.  Its only safe input
    is a sealed read view prepared at the canonical boundary.  The seal is an
    object-identity capability, so plain event dataclasses, mappings, and
    lookalike views cannot become source proof merely by matching fields.
    """

    _events: tuple[CommittedEventEvidence, ...]
    _cursor: WorldCursor
    _seal: object

    def __post_init__(self) -> None:
        if self._seal is not _EVENT_VIEW_SEAL:
            raise OrchestrationViolation("COMMITTED_EVENT_VIEW_UNTRUSTED")

    @property
    def cursor(self) -> WorldCursor:
        return self._cursor

    def events(self) -> tuple[CommittedEventEvidence, ...]:
        return self._events


def _admit_committed_event_view(
    cursor: WorldCursor, events: Iterable[CommittedEventEvidence]
) -> _CommittedEventView:
    """Canonical-boundary adapter used by the owning runtime and test seam.

    It validates a read-only snapshot only; it cannot commit, replay, mutate,
    or assign canonical authority to an event.
    """
    material = tuple(events)
    if any(not isinstance(event, CommittedEventEvidence) for event in material):
        raise OrchestrationViolation("COMMITTED_EVENT_EVIDENCE_INVALID")
    _validate_event_collection(material)
    return _CommittedEventView(material, cursor, _EVENT_VIEW_SEAL)


@dataclass(frozen=True)
class DomainModuleManifest:
    """A metadata declaration.  Admission never grants the declared authority."""

    module_id: str
    version: str
    authority_scope: str
    accepted_event_types: tuple[str, ...]
    output_request_types: tuple[str, ...]
    dependencies: tuple[str, ...] = ()
    enabled: bool = True
    contract_ref: str = "AF001-LIVING-STORY-CONTRACTS@1"

    def __post_init__(self) -> None:
        _require_text(self.module_id, "MODULE_ID_REQUIRED")
        _require_text(self.version, "MODULE_VERSION_REQUIRED")
        if self.authority_scope not in _KNOWN_AUTHORITY_SCOPES:
            raise OrchestrationViolation("MODULE_SCOPE_UNKNOWN")
        object.__setattr__(self, "accepted_event_types", _stable_unique(self.accepted_event_types, "MODULE_EVENT_TYPES_INVALID"))
        object.__setattr__(self, "output_request_types", _stable_unique(self.output_request_types, "MODULE_OUTPUT_TYPES_INVALID"))
        object.__setattr__(self, "dependencies", _stable_unique(self.dependencies, "MODULE_DEPENDENCIES_INVALID"))
        _require_text(self.contract_ref, "MODULE_CONTRACT_REF_REQUIRED")
        if not isinstance(self.enabled, bool):
            raise OrchestrationViolation("MODULE_ENABLED_INVALID")

    def identity_material(self) -> dict[str, object]:
        return {
            "module_id": self.module_id,
            "version": self.version,
            "authority_scope": self.authority_scope,
            "accepted_event_types": self.accepted_event_types,
            "output_request_types": self.output_request_types,
            "dependencies": self.dependencies,
            "enabled": self.enabled,
            "contract_ref": self.contract_ref,
        }


@dataclass(frozen=True)
class _ModuleAdmissionView:
    """Sealed module-admission projection from the owning authority boundary."""

    _manifests: tuple[DomainModuleManifest, ...]
    _admission_digest: str
    _seal: object

    def __post_init__(self) -> None:
        if self._seal is not _MODULE_ADMISSION_SEAL:
            raise OrchestrationViolation("MODULE_ADMISSION_VIEW_UNTRUSTED")


def _admit_module_view(manifests: Iterable[DomainModuleManifest]) -> _ModuleAdmissionView:
    """Create a read-only admission view without accepting a caller catalog.

    This is the Stage 1 boundary seam.  It verifies a fixed, complete manifest
    projection and returns only a sealed view.  It does not grant capability,
    domain, event, or consequence authority.
    """
    admitted: dict[str, DomainModuleManifest] = {}
    for manifest in manifests:
        if not isinstance(manifest, DomainModuleManifest):
            raise OrchestrationViolation("MODULE_MANIFEST_INVALID")
        if manifest.module_id in admitted:
            raise OrchestrationViolation("DUPLICATE_MODULE_ID")
        admitted[manifest.module_id] = manifest
    if not admitted:
        raise OrchestrationViolation("MODULE_ADMISSION_EMPTY")
    for manifest in admitted.values():
        if set(manifest.dependencies).difference(admitted):
            raise OrchestrationViolation("MODULE_DEPENDENCY_UNREGISTERED")
    ordered = tuple(sorted(admitted.values(), key=lambda item: (item.module_id, item.version)))
    return _ModuleAdmissionView(
        ordered,
        _canonical_digest([item.identity_material() for item in ordered]),
        _MODULE_ADMISSION_SEAL,
    )


class DomainModuleRegistry:
    """Routes only a sealed admission view; callers cannot self-register scope."""

    def __init__(self, admission: _ModuleAdmissionView) -> None:
        if not isinstance(admission, _ModuleAdmissionView):
            raise OrchestrationViolation("MODULE_ADMISSION_VIEW_REQUIRED")
        # Recompute instead of trusting a caller-provided digest.  The digest
        # carries provenance for deterministic correlation, not authority.
        expected_digest = _canonical_digest(
            [item.identity_material() for item in admission._manifests]
        )
        if admission._admission_digest != expected_digest:
            raise OrchestrationViolation("MODULE_ADMISSION_VIEW_TAMPERED")
        self._manifests = MappingProxyType(
            {item.module_id: item for item in admission._manifests}
        )

    def get(self, module_id: str) -> DomainModuleManifest:
        try:
            return self._manifests[module_id]
        except KeyError as error:
            raise OrchestrationViolation("MODULE_UNREGISTERED") from error

    def enabled(self) -> tuple[DomainModuleManifest, ...]:
        return tuple(sorted((item for item in self._manifests.values() if item.enabled), key=lambda item: (item.module_id, item.version, item.authority_scope)))


@dataclass(frozen=True)
class DomainChangeNotice:
    world_cursor: WorldCursor
    source_event_refs: tuple[str, ...]
    originating_authority_scope: str
    affected_domain_hints: tuple[str, ...]
    correlation_id: str
    causation_ref: str
    policy_version: str = "LW-STAGE1-ORCH-001@1"

    def __post_init__(self) -> None:
        # Event order is evidence.  Unlike hints and manifest metadata, it must
        # retain the supplied canonical-ledger order so a reordered caller list
        # can be rejected rather than silently normalized.
        object.__setattr__(self, "source_event_refs", _ordered_unique(self.source_event_refs, "SOURCE_EVENT_REFS_INVALID"))
        object.__setattr__(self, "affected_domain_hints", _stable_unique(self.affected_domain_hints, "AFFECTED_DOMAIN_HINTS_INVALID"))
        if self.originating_authority_scope not in _KNOWN_AUTHORITY_SCOPES:
            raise OrchestrationViolation("ORIGINATING_SCOPE_UNKNOWN")
        _require_text(self.correlation_id, "CORRELATION_ID_REQUIRED")
        _require_text(self.causation_ref, "CAUSATION_REF_REQUIRED")
        _require_text(self.policy_version, "POLICY_VERSION_REQUIRED")


@dataclass(frozen=True)
class DomainEvaluationRequest:
    """A receiver must revalidate this request before proposing any later work."""

    request_id: str
    receiver_module_id: str
    receiver_authority_scope: str
    world_cursor: WorldCursor
    source_event_refs: tuple[str, ...]
    correlation_id: str
    causation_ref: str
    request_type: str
    canonical_authority: bool = False

    def __post_init__(self) -> None:
        _require_text(self.request_id, "REQUEST_ID_REQUIRED")
        _require_text(self.receiver_module_id, "RECEIVER_ID_REQUIRED")
        if self.receiver_authority_scope not in _KNOWN_AUTHORITY_SCOPES:
            raise OrchestrationViolation("RECEIVER_SCOPE_UNKNOWN")
        object.__setattr__(self, "source_event_refs", _ordered_unique(self.source_event_refs, "REQUEST_SOURCE_EVENT_REFS_INVALID"))
        _require_text(self.correlation_id, "REQUEST_CORRELATION_ID_REQUIRED")
        _require_text(self.causation_ref, "REQUEST_CAUSATION_REF_REQUIRED")
        _require_text(self.request_type, "REQUEST_TYPE_REQUIRED")
        if self.canonical_authority:
            raise OrchestrationViolation("STAGE1_REQUEST_CANNOT_BE_CANONICAL")


@dataclass(frozen=True)
class WorldOrchestrationPlan:
    plan_id: str
    world_cursor: WorldCursor
    notice: DomainChangeNotice
    requests: tuple[DomainEvaluationRequest, ...]
    source_event_set_digest: str


@dataclass(frozen=True)
class ReceiverEvaluation:
    request_id: str
    receiver_module_id: str
    status: str
    canonical_authority: bool = False
    proposed_event: None = None

    def __post_init__(self) -> None:
        if self.canonical_authority or self.proposed_event is not None:
            raise OrchestrationViolation("STAGE1_RECEIVER_CANNOT_PROPOSE_CANONICAL_EVENT")


class WorldOrchestrator:
    """Pure scheduler/router/correlator; deliberately exposes no mutation surface."""

    def __init__(self, registry: DomainModuleRegistry, policy_version: str = "LW-STAGE1-ORCH-001@1") -> None:
        self._registry = registry
        self._policy_version = _require_text(policy_version, "POLICY_VERSION_REQUIRED")

    def plan(
        self,
        notice: DomainChangeNotice,
        committed_events: _CommittedEventView,
    ) -> WorldOrchestrationPlan:
        if notice.policy_version != self._policy_version:
            raise OrchestrationViolation("NOTICE_POLICY_VERSION_MISMATCH")
        if not isinstance(committed_events, _CommittedEventView):
            raise OrchestrationViolation("COMMITTED_EVENT_VIEW_REQUIRED")
        if committed_events.cursor != notice.world_cursor:
            raise OrchestrationViolation("COMMITTED_EVENT_CURSOR_MISMATCH")
        evidence_by_id = self._validate_committed_evidence(committed_events.events())
        source_events = tuple(evidence_by_id.get(event_id) for event_id in notice.source_event_refs)
        if any(event is None for event in source_events):
            raise OrchestrationViolation("SOURCE_EVENT_NOT_COMMITTED")
        ordered_sources = tuple(sorted(source_events, key=lambda event: event.canonical_order))
        if tuple(event.event_id for event in ordered_sources) != notice.source_event_refs:
            raise OrchestrationViolation("SOURCE_EVENT_ORDER_NOT_CANONICAL")
        source_digest = _canonical_digest([event.identity_material() for event in ordered_sources])
        candidates = [
            manifest
            for manifest in self._registry.enabled()
            if any(event.event_type in manifest.accepted_event_types for event in ordered_sources)
        ]
        ordered_manifests = self._dependency_order(candidates)
        requests = tuple(
            self._request_for(manifest, notice, source_digest)
            for manifest in ordered_manifests
        )
        plan_id = _canonical_digest(
            {
                "policy_version": self._policy_version,
                "world_id": notice.world_cursor.world_id,
                "state_version": notice.world_cursor.state_version,
                "source_event_set_digest": source_digest,
                "requests": [request.request_id for request in requests],
            }
        )
        return WorldOrchestrationPlan(plan_id, notice.world_cursor, notice, requests, source_digest)

    def revalidate(self, request: DomainEvaluationRequest, current_cursor: WorldCursor) -> ReceiverEvaluation:
        if request.world_cursor != current_cursor:
            raise OrchestrationViolation("RECEIVER_REJECTED_STALE_NOTICE")
        manifest = self._registry.get(request.receiver_module_id)
        if not manifest.enabled:
            raise OrchestrationViolation("RECEIVER_DISABLED")
        if manifest.authority_scope != request.receiver_authority_scope:
            raise OrchestrationViolation("RECEIVER_SCOPE_MISMATCH")
        return ReceiverEvaluation(request.request_id, request.receiver_module_id, "RECEIVER_REVALIDATION_REQUIRED")

    @staticmethod
    def _validate_committed_evidence(events: Iterable[CommittedEventEvidence]) -> Mapping[str, CommittedEventEvidence]:
        evidence = tuple(events)
        _validate_event_collection(evidence)
        return MappingProxyType({event.event_id: event for event in evidence})

    @staticmethod
    def _dependency_order(candidates: Iterable[DomainModuleManifest]) -> tuple[DomainModuleManifest, ...]:
        chosen = {manifest.module_id: manifest for manifest in candidates}
        for manifest in chosen.values():
            if set(manifest.dependencies).difference(chosen):
                # A dependency that was not routed is not silently "already
                # satisfied".  The caller must start an explicit, auditable
                # cycle containing the required upstream receiver.
                raise OrchestrationViolation("ORCHESTRATION_DEPENDENCY_NOT_ROUTABLE")
        result: list[DomainModuleManifest] = []
        pending = dict(chosen)
        while pending:
            ready = sorted(
                (
                    manifest
                    for manifest in pending.values()
                    if all(dependency not in pending for dependency in manifest.dependencies)
                ),
                key=lambda manifest: (manifest.module_id, manifest.version, manifest.authority_scope),
            )
            if not ready:
                raise OrchestrationViolation("ORCHESTRATION_DEPENDENCY_CYCLE")
            for manifest in ready:
                result.append(manifest)
                del pending[manifest.module_id]
        return tuple(result)

    def _request_for(self, manifest: DomainModuleManifest, notice: DomainChangeNotice, source_digest: str) -> DomainEvaluationRequest:
        request_type = manifest.output_request_types[0] if manifest.output_request_types else "EVALUATE"
        request_id = _canonical_digest(
            {
                "policy_version": self._policy_version,
                "receiver_module_id": manifest.module_id,
                "receiver_version": manifest.version,
                "receiver_scope": manifest.authority_scope,
                "world_id": notice.world_cursor.world_id,
                "state_version": notice.world_cursor.state_version,
                "source_event_set_digest": source_digest,
                "correlation_id": notice.correlation_id,
                "causation_ref": notice.causation_ref,
                "request_type": request_type,
            }
        )
        return DomainEvaluationRequest(
            request_id=request_id,
            receiver_module_id=manifest.module_id,
            receiver_authority_scope=manifest.authority_scope,
            world_cursor=notice.world_cursor,
            source_event_refs=notice.source_event_refs,
            correlation_id=notice.correlation_id,
            causation_ref=notice.causation_ref,
            request_type=request_type,
        )


def _validate_event_collection(events: tuple[CommittedEventEvidence, ...]) -> None:
    if any(not isinstance(event, CommittedEventEvidence) for event in events):
        raise OrchestrationViolation("COMMITTED_EVENT_EVIDENCE_INVALID")
    by_id = {event.event_id: event for event in events}
    if len(by_id) != len(events):
        raise OrchestrationViolation("COMMITTED_EVENT_ID_DUPLICATE")
    orders = [event.canonical_order for event in events]
    if len(set(orders)) != len(orders):
        raise OrchestrationViolation("COMMITTED_EVENT_ORDER_DUPLICATE")
