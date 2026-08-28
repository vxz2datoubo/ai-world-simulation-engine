from tests.test_i8d_stage_a2_axis_stability_experiment import (
    comparison,
    make_i8_pair,
    stage_a,
)
from evals.i8d_stage_a2_axis_stability_experiment import evaluate_stage_a2_axis_stability


def test_temp_i8_a2_failure_code_diagnostic():
    _, eligible, invalid = make_i8_pair()
    result = evaluate_stage_a2_axis_stability(
        left_stage_a_package=stage_a("I8C_STORYLET", eligible),
        right_stage_a_package=stage_a("I8C_STORYLET", invalid),
        fixture=comparison("UPSTREAM_STATUS_CHANGE", "A2-I8-DIAGNOSTIC"),
    )
    assert result.integrity_failures == (), (
        result.integrity_failures,
        result.changed_core_assessments,
        result.changed_core_material,
        result.left_source_i1_sha256,
        result.right_source_i1_sha256,
        result.left_source_package_sha256,
        result.right_source_package_sha256,
        result.left_source_status,
        result.right_source_status,
    )
