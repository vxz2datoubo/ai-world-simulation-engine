"""Authority-root adapters for the deliberately non-canonical Stage 1 scheduler.

This module is the only bridge from an already committed/replayed engine world
and the fixed Stage 1 registry into :mod:`awrse.orchestration`.  It never
creates events, changes world state, registers a caller manifest, or opens a
second ledger.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

from .orchestration import (
    CommittedEventEvidence,
    DomainModuleManifest,
    DomainModuleRegistry,
    OrchestrationViolation,
    WorldCursor,
    _CommittedEventView,
    _ModuleAdmissionView,
    _canonical_digest,
)

if TYPE_CHECKING:
    from .engine import SimulationEngine
    from .model import WorldState


_REGISTRY_PATH = Path(__file__).resolve().parents[2] / "registries" / "AF001-LW-STAGE1-DOMAIN-MODULES.json"


class Stage1AuthorityInputs:
    """Read-only scheduler inputs derived by the existing engine authority."""

    __slots__ = ("event_view", "registry")

    def __init__(self, event_view: _CommittedEventView, registry: DomainModuleRegistry) -> None:
        self.event_view = event_view
        self.registry = registry


class _CommittedEngineRoot:
    """Rechecks the existing engine commit/replay boundary on every use."""

    __slots__ = ("_engine", "_world")

    def __init__(self, engine: "SimulationEngine", world: "WorldState") -> None:
        self._engine = engine
        self._world = world

    def validate_event_view(self, cursor: WorldCursor, events: tuple[CommittedEventEvidence, ...]) -> bool:
        try:
            committed = self._engine._stage1_read_committed_events(self._world)
        except (AttributeError, ValueError):
            return False
        expected = tuple(CommittedEventEvidence(item.event_id, item.event_type, index) for index, item in enumerate(committed))
        return cursor == WorldCursor(self._world.world_id, self._world.world_state_version) and events == expected


class _GovernedRegistryRoot:
    """Binds an admission view to the fixed snapshot-authorized file."""

    __slots__ = ("_manifests", "_digest")

    def __init__(self, manifests: tuple[DomainModuleManifest, ...]) -> None:
        self._manifests = manifests
        self._digest = _canonical_digest([item.identity_material() for item in manifests])

    def validate_module_view(self, manifests: tuple[DomainModuleManifest, ...], digest: str) -> bool:
        return manifests == self._manifests and digest == self._digest


def _load_fixed_registry() -> DomainModuleRegistry:
    """Load the snapshot-authorized registry; caller data has no input here."""
    try:
        decoded = json.loads(_REGISTRY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_UNAVAILABLE") from exc
    if not isinstance(decoded, dict) or decoded.get("schema") != "AF001-LW-STAGE1-DOMAIN-MODULES/v1":
        raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_INVALID")
    raw_modules = decoded.get("modules")
    if not isinstance(raw_modules, list) or not raw_modules:
        raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_EMPTY")
    manifests: list[DomainModuleManifest] = []
    for item in raw_modules:
        if not isinstance(item, dict):
            raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_INVALID")
        manifests.append(DomainModuleManifest(
            item.get("module_id"), item.get("version"), item.get("authority_scope"),
            tuple(item.get("accepted_event_types", ())), tuple(item.get("output_request_types", ())),
            tuple(item.get("dependencies", ())), item.get("enabled"), item.get("contract_ref"),
        ))
    ordered = tuple(sorted(manifests, key=lambda item: (item.module_id, item.version)))
    if len({item.module_id for item in ordered}) != len(ordered):
        raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_DUPLICATE")
    if any(set(item.dependencies).difference({candidate.module_id for candidate in ordered}) for item in ordered):
        raise OrchestrationViolation("STAGE1_GOVERNED_REGISTRY_DEPENDENCY_INVALID")
    root = _GovernedRegistryRoot(ordered)
    return DomainModuleRegistry(_ModuleAdmissionView(ordered, root._digest, root))


def inputs_from_committed_engine(engine: "SimulationEngine", world: "WorldState") -> Stage1AuthorityInputs:
    """Project only evidence whose current fingerprint was committed/replayed by *engine*.

    A sealed lookalike world, hand-built event tuple, or caller supplied module
    catalog cannot satisfy the engine provenance check.
    """
    events = engine._stage1_read_committed_events(world)
    cursor = WorldCursor(world.world_id, world.world_state_version)
    evidence = tuple(
        CommittedEventEvidence(event.event_id, event.event_type, index)
        for index, event in enumerate(events)
    )
    root = _CommittedEngineRoot(engine, world)
    return Stage1AuthorityInputs(_CommittedEventView(evidence, cursor, root), _load_fixed_registry())
