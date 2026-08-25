import copy
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT_REGISTRY = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
BINDING = ROOT / "contracts" / "AF001-ACTION-DEMAND-PROJECTION-BINDING.json"
GOLDEN_REGISTRY = ROOT / "evals" / "AF001-GOLDEN-SCENARIOS.json"
FIXTURES = ROOT / "evals" / "AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json"


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _contract_extension_is_canonical(parent, child, expected_path: str) -> bool:
    registration = parent.get("registered_contract_extensions", {}).get(child.get("binding_id"))
    return bool(
        isinstance(registration, dict)
        and registration.get("path") == expected_path
        and registration.get("binding_version") == child.get("binding_version")
        and registration.get("parent_contract_id") == parent.get("contract_id")
        and registration.get("parent_contract_version") == parent.get("contract_version")
        and registration.get("authority") == "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION"
        and registration.get("runtime_implementation_authorized") is False
    )


def _fixture_extension_is_canonical(parent, fixture, binding) -> bool:
    registration = parent.get("registered_fixture_extensions", {}).get(fixture.get("fixture_id"))
    return bool(
        isinstance(registration, dict)
        and registration.get("path") == "evals/AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json"
        and registration.get("fixture_version") == fixture.get("fixture_version")
        and registration.get("parent_eval_suite_id") == parent.get("eval_suite_id")
        and registration.get("parent_suite_version") == parent.get("suite_version")
        and registration.get("binding_id") == binding.get("binding_id")
        and registration.get("authority") == "GOLDEN_EXECUTABLE_SPEC_REGISTRY_DELEGATED_EXTENSION"
    )


def test_canonical_machine_registry_explicitly_delegates_action_demand_binding():
    parent = _load(CONTRACT_REGISTRY)
    binding = _load(BINDING)

    assert parent["artifact_roles"]["contracts/AF001-LIVING-STORY-CONTRACTS.json"] == "MACHINE_CONTRACT_REGISTRY"
    assert _contract_extension_is_canonical(
        parent,
        binding,
        "contracts/AF001-ACTION-DEMAND-PROJECTION-BINDING.json",
    )
    assert parent["contract_extension_authority_rule"] == (
        "ONLY_EXTENSIONS_EXPLICITLY_REGISTERED_BY_THIS_MACHINE_CONTRACT_REGISTRY_ARE_CANONICAL; "
        "CHILD_TO_PARENT_SELF_DECLARATION_ALONE_CONFERS_NO_AUTHORITY"
    )


def test_canonical_golden_registry_explicitly_delegates_action_demand_fixtures():
    golden = _load(GOLDEN_REGISTRY)
    fixture = _load(FIXTURES)
    binding = _load(BINDING)

    contract = _load(CONTRACT_REGISTRY)
    assert contract["artifact_roles"]["evals/AF001-GOLDEN-SCENARIOS.json"] == "GOLDEN_EXECUTABLE_SPEC_REGISTRY"
    assert _fixture_extension_is_canonical(golden, fixture, binding)
    assert golden["fixture_extension_authority_rule"] == (
        "ONLY_FIXTURE_EXTENSIONS_EXPLICITLY_REGISTERED_BY_THIS_GOLDEN_EXECUTABLE_SPEC_REGISTRY_ARE_CANONICAL; "
        "CHILD_TO_PARENT_SELF_DECLARATION_ALONE_CONFERS_NO_AUTHORITY"
    )
    assert "ACTION_DEMAND_PROJECTION_FIXTURE_EXTENSION_EXPLICITLY_REGISTERED_BY_CANONICAL_SUITE" in golden["suite_acceptance"]


def test_orphan_sidecar_cannot_self_declare_canonical_authority():
    parent = _load(CONTRACT_REGISTRY)
    binding = _load(BINDING)
    golden = _load(GOLDEN_REGISTRY)
    fixture = _load(FIXTURES)

    orphan_binding = copy.deepcopy(binding)
    orphan_binding["binding_id"] = "AWRSE-AF001-ORPHAN-SELF-DECLARED-BINDING"
    orphan_binding["artifact_role"] = "BOUNDING_CONTRACT_EXTENSION_NON_COMPETING"
    orphan_binding["parent_machine_contract"] = copy.deepcopy(binding["parent_machine_contract"])

    orphan_fixture = copy.deepcopy(fixture)
    orphan_fixture["fixture_id"] = "AWRSE-AF001-ORPHAN-SELF-DECLARED-FIXTURES"
    orphan_fixture["fixture_role"] = "GOLDEN_EXECUTABLE_SPEC_EXTENSION_NON_COMPETING"
    orphan_fixture["parent_golden_registry"] = "evals/AF001-GOLDEN-SCENARIOS.json"

    assert not _contract_extension_is_canonical(
        parent,
        orphan_binding,
        "contracts/AF001-ACTION-DEMAND-PROJECTION-BINDING.json",
    )
    assert not _fixture_extension_is_canonical(golden, orphan_fixture, binding)
