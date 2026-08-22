import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EVAL_PATH = ROOT / "evals" / "R003-I1A-RESTART-REFERENCE.json"
TEST_PATH = ROOT / "tests" / "test_r003_i1a_persistence_restart.py"


def test_r003_i1a_eval_registry_is_bounded_and_points_to_real_executable_cases():
    data = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    test_source = TEST_PATH.read_text(encoding="utf-8")

    assert data["eval_suite_id"] == "AWRSE-R003-I1A-SOLO-RESTART-REFERENCE"
    assert data["implementation_scope"] == "SOLO_RESTART_REFERENCE_ONLY"
    assert data["canonical_release_base"] == "21fd2feaa2d5e7a2aef7b0111d5535440d68d051"
    assert data["projection_is_persistence_authority"] is False
    assert data["backend_selected"] is False
    assert data["vnext_event_migration_implemented"] is False
    assert data["open_decisions_resolved"] == []

    cases = data["executable_cases"]
    assert len(cases) == 14
    assert len({case["case_id"] for case in cases}) == 14
    for case in cases:
        node = case["pytest_node"]
        assert node.startswith("tests/test_r003_i1a_persistence_restart.py::")
        function_name = node.split("::", 1)[1]
        assert f"def {function_name}(" in test_source
        assert case["asserts"]

    non_goals = set(data["explicit_non_goals"])
    assert "DATABASE_OR_EVENT_STORE_BACKEND_SELECTION" in non_goals
    assert "AF001_VNEXT_EVENT_MIGRATION" in non_goals
    assert "PARTY_OR_PUBLIC_CONCURRENCY" in non_goals
    assert "H3_OR_MATRIX_GAME_INTEGRATION" in non_goals
