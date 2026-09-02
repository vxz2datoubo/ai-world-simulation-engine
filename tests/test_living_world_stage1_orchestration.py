from __future__ import annotations

import inspect
import re

import pytest

from awrse.orchestration import (
    CommittedEventEvidence,
    DomainChangeNotice,
    DomainModuleManifest,
    DomainModuleRegistry,
    OrchestrationViolation,
    WorldCursor,
    WorldOrchestrator,
)


def cursor(version: str = "B1:7", world_id: str = "WORLD-1") -> WorldCursor:
    return WorldCursor(world_id, version)


def evidence(*items: tuple[str, str, int]) -> tuple[CommittedEventEvidence, ...]:
    return tuple(CommittedEventEvidence(*item) for item in items)


def manifest(
    module_id: str,
    scope: str,
    *,
    accepts: tuple[str, ...] = ("OBJECT_DAMAGED",),
    dependencies: tuple[str, ...] = (),
    enabled: bool = True,
) -> DomainModuleManifest:
    return DomainModuleManifest(module_id, "1", scope, accepts, ("EVALUATE",), dependencies, enabled)


def orchestrator(*manifests: DomainModuleManifest, catalog: dict[str, str] | None = None) -> WorldOrchestrator:
    return WorldOrchestrator(DomainModuleRegistry(manifests, catalog or {item.module_id: item.authority_scope for item in manifests}))


def notice(*, source_refs: tuple[str, ...] = ("E1",), hints: tuple[str, ...] = ("AF-E",), current: WorldCursor | None = None) -> DomainChangeNotice:
    return DomainChangeNotice(current or cursor(), source_refs, "AF-B", hints, "CORR-1", "CAUSE-E1")


def test_deterministic_plan_routes_only_admitted_receivers_and_revalidates() -> None:
    physical = manifest("physical", "AF-B")
    legal = manifest("legal", "AF-E", dependencies=("physical",))
    runtime = orchestrator(legal, physical)
    plan = runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4)))
    assert [item.receiver_module_id for item in plan.requests] == ["physical", "legal"]
    assert [item.canonical_authority for item in plan.requests] == [False, False]
    evaluation = runtime.revalidate(plan.requests[0], cursor())
    assert evaluation.status == "RECEIVER_REVALIDATION_REQUIRED"
    assert evaluation.canonical_authority is False
    assert evaluation.proposed_event is None


def test_same_inputs_with_different_manifest_insertion_order_replay_identically() -> None:
    alpha = manifest("alpha", "AF-B")
    beta = manifest("beta", "AF-E", dependencies=("alpha",))
    inputs = evidence(("E1", "OBJECT_DAMAGED", 4))
    first = orchestrator(alpha, beta).plan(notice(), inputs)
    second = orchestrator(beta, alpha).plan(notice(), inputs)
    assert first == second


def test_hint_is_not_a_command_and_cannot_force_receiver_consequence() -> None:
    legal = manifest("legal", "AF-E", accepts=("SPEECH_UTTERED",))
    plan = orchestrator(legal).plan(notice(hints=("AF-E",)), evidence(("E1", "OBJECT_DAMAGED", 4)))
    assert plan.requests == ()


def test_orchestrator_exposes_no_world_or_event_mutation_api() -> None:
    names = set(dir(WorldOrchestrator))
    forbidden = {"commit", "commit_event", "mutate", "mutate_world", "apply_event", "resolve"}
    assert not names.intersection(forbidden)
    assert "SimulationEngine" not in inspect.getsource(WorldOrchestrator)


def test_disabled_module_cannot_receive_or_revalidate_work() -> None:
    disabled = manifest("physical", "AF-B", enabled=False)
    runtime = orchestrator(disabled)
    plan = runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4)))
    assert plan.requests == ()
    with pytest.raises(OrchestrationViolation, match="RECEIVER_DISABLED"):
        runtime.revalidate(
            __import__("awrse.orchestration", fromlist=["DomainEvaluationRequest"]).DomainEvaluationRequest(
                "request", "physical", "AF-B", cursor(), ("E1",), "CORR", "CAUSE", "EVALUATE"
            ),
            cursor(),
        )


def test_unregistered_module_and_scope_escalation_fail_closed() -> None:
    with pytest.raises(OrchestrationViolation, match="MODULE_UNREGISTERED"):
        DomainModuleRegistry((manifest("invented", "AF-B"),), {"other": "AF-B"})
    with pytest.raises(OrchestrationViolation, match="MODULE_SCOPE_ESCALATION"):
        DomainModuleRegistry((manifest("legal", "AF-B"),), {"legal": "AF-E"})


def test_stale_cursor_and_wrong_world_fail_closed_at_receiver_boundary() -> None:
    runtime = orchestrator(manifest("physical", "AF-B"))
    request = runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4))).requests[0]
    with pytest.raises(OrchestrationViolation, match="RECEIVER_REJECTED_STALE_NOTICE"):
        runtime.revalidate(request, cursor("B1:8"))
    with pytest.raises(OrchestrationViolation, match="RECEIVER_REJECTED_STALE_NOTICE"):
        runtime.revalidate(request, cursor("B1:7", "OTHER-WORLD"))


def test_forged_or_noncanonical_source_event_ref_fails_closed() -> None:
    runtime = orchestrator(manifest("physical", "AF-B"))
    with pytest.raises(OrchestrationViolation, match="SOURCE_EVENT_NOT_COMMITTED"):
        runtime.plan(notice(source_refs=("FORGED",)), evidence(("E1", "OBJECT_DAMAGED", 4)))
    with pytest.raises(OrchestrationViolation, match="SOURCE_EVENT_ORDER_NOT_CANONICAL"):
        runtime.plan(
            notice(source_refs=("E2", "E1")),
            evidence(("E1", "OBJECT_DAMAGED", 4), ("E2", "SPEECH_UTTERED", 5)),
        )


def test_duplicate_event_evidence_fails_closed() -> None:
    runtime = orchestrator(manifest("physical", "AF-B"))
    with pytest.raises(OrchestrationViolation, match="COMMITTED_EVENT_ID_DUPLICATE"):
        runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4), ("E1", "OBJECT_DAMAGED", 5)))
    with pytest.raises(OrchestrationViolation, match="COMMITTED_EVENT_ORDER_DUPLICATE"):
        runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4), ("E2", "OBJECT_DAMAGED", 4)))


def test_dependency_cycle_fails_deterministically() -> None:
    alpha = manifest("alpha", "AF-B", dependencies=("beta",))
    beta = manifest("beta", "AF-E", dependencies=("alpha",))
    with pytest.raises(OrchestrationViolation, match="ORCHESTRATION_DEPENDENCY_CYCLE"):
        orchestrator(alpha, beta).plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4)))


def test_dependency_that_was_not_routed_fails_closed() -> None:
    physical = manifest("physical", "AF-B", accepts=("OBJECT_MOVED",))
    legal = manifest("legal", "AF-E", dependencies=("physical",))
    with pytest.raises(OrchestrationViolation, match="ORCHESTRATION_DEPENDENCY_NOT_ROUTABLE"):
        orchestrator(physical, legal).plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4)))


def test_policy_version_mismatch_fails_closed() -> None:
    runtime = orchestrator(manifest("physical", "AF-B"))
    invalid = DomainChangeNotice(cursor(), ("E1",), "AF-B", (), "CORR", "CAUSE", "OTHER-POLICY")
    with pytest.raises(OrchestrationViolation, match="NOTICE_POLICY_VERSION_MISMATCH"):
        runtime.plan(invalid, evidence(("E1", "OBJECT_DAMAGED", 4)))


def test_no_wall_clock_uuid_or_network_dependency_in_runtime_source() -> None:
    source = inspect.getsource(__import__("awrse.orchestration", fromlist=["WorldOrchestrator"]))
    imported_modules = set(re.findall(r"^(?:from|import)\s+([\w.]+)", source, flags=re.MULTILINE))
    assert not imported_modules.intersection({"time", "uuid", "requests", "urllib", "http", "socket", "asyncio"})


def test_receiver_requests_cannot_be_promoted_to_canonical_events() -> None:
    runtime = orchestrator(manifest("physical", "AF-B"))
    request = runtime.plan(notice(), evidence(("E1", "OBJECT_DAMAGED", 4))).requests[0]
    assert request.canonical_authority is False
    with pytest.raises(OrchestrationViolation, match="STAGE1_REQUEST_CANNOT_BE_CANONICAL"):
        type(request)(
            request.request_id,
            request.receiver_module_id,
            request.receiver_authority_scope,
            request.world_cursor,
            request.source_event_refs,
            request.correlation_id,
            request.causation_ref,
            request.request_type,
            canonical_authority=True,
        )
