"""Stage 1 scheduler tests: authority inputs originate in engine + registry only."""

import pytest

from awrse import ActionCompiler, SimulationEngine
from awrse.orchestration import (
    CommittedEventEvidence,
    DomainChangeNotice,
    DomainModuleManifest,
    DomainModuleRegistry,
    OrchestrationViolation,
    WorldCursor,
    WorldOrchestrator,
    _admit_committed_event_view,
    _admit_module_view,
)
from test_r001_core_loop import PRINCIPAL, make_world


def _committed_inputs():
    world = make_world()
    engine = SimulationEngine()
    action = ActionCompiler().compile("砸碎窗户", "PLAYER", world, PRINCIPAL)
    result = engine.resolve_and_commit(action, world)
    assert result.events
    return engine, world, engine.stage1_orchestration_inputs(world)


def _notice(world, source_event_id: str) -> DomainChangeNotice:
    return DomainChangeNotice(
        WorldCursor(world.world_id, world.world_state_version), (source_event_id,),
        "AF-B", ("AF-B", "AF-E"), "CORR-1", source_event_id,
    )


def test_governed_engine_and_registry_route_deterministically() -> None:
    engine, world, inputs = _committed_inputs()
    runtime = WorldOrchestrator(inputs.registry)
    plan = runtime.plan(_notice(world, world.event_log[0].event_id), inputs.event_view)
    assert [item.receiver_module_id for item in plan.requests] == ["physical", "legal"]
    assert all(item.canonical_authority is False for item in plan.requests)
    cursor = WorldCursor(world.world_id, world.world_state_version)
    assert runtime.revalidate(plan.requests[0], cursor).status == "RECEIVER_REVALIDATION_REQUIRED"
    second_inputs = engine.stage1_orchestration_inputs(world)
    second = WorldOrchestrator(second_inputs.registry).plan(_notice(world, world.event_log[0].event_id), second_inputs.event_view)
    assert second == plan


def test_caller_material_cannot_mint_event_or_module_admission() -> None:
    with pytest.raises(OrchestrationViolation, match="AUTHORITY_ROOT_REQUIRED"):
        _admit_committed_event_view(WorldCursor("W", "B:1"), (CommittedEventEvidence("E", "OBJECT_DAMAGED", 0),))
    invented = DomainModuleManifest("invented", "1", "AF-H", ("OBJECT_DAMAGED",), ("EVALUATE",))
    with pytest.raises(OrchestrationViolation, match="AUTHORITY_ROOT_REQUIRED"):
        _admit_module_view((invented,))
    with pytest.raises(OrchestrationViolation, match="MODULE_ADMISSION_VIEW_REQUIRED"):
        DomainModuleRegistry((invented,))


def test_hand_sealed_or_uncommitted_world_cannot_become_source_proof() -> None:
    world = make_world()
    world.seal_live()
    with pytest.raises(ValueError, match="STAGE1_COMMITTED_ENGINE_PROVENANCE_REQUIRED"):
        SimulationEngine().stage1_orchestration_inputs(world)


def test_wrong_engine_and_post_commit_tamper_fail_closed() -> None:
    engine, world, _inputs = _committed_inputs()
    with pytest.raises(ValueError, match="STAGE1_COMMITTED_ENGINE_PROVENANCE_REQUIRED"):
        SimulationEngine().stage1_orchestration_inputs(world)
    altered = make_world()
    altered.seal_live()
    with pytest.raises(ValueError, match="STAGE1_COMMITTED_ENGINE_PROVENANCE_REQUIRED"):
        engine.stage1_orchestration_inputs(altered)
