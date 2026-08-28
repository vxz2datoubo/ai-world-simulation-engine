from __future__ import annotations

import base64
import copy
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "runtime"))

OLD_PARENT = "1.9.0-candidate"
NEW_PARENT = "1.10.0-candidate"
OLD_GRAPH = "AF001-AUTHORITY-GRAPH-1.9-I2A008@1"
NEW_GRAPH = "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1"
OLD_GOLDEN = "1.7.0-candidate"
NEW_GOLDEN = "1.8.0-candidate"
OLD_DECISION = "1.2.0-candidate"
NEW_DECISION = "1.3.0-candidate"
BQ_BINDING_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-BINDING"
BQ_PROFILE = "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW"
BQ_TYPE = "BranchQualityEvidence"
BQ_TYPE_ID = "AF001.BranchQualityEvidence"
BQ_PROVENANCE_FIXTURE_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES"
BQ_PROVENANCE_PATH = "evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json"
BQ_PROVENANCE_VERSION = "1.0.0-candidate"


def load(path: str) -> Any:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def dump(path: str, value: Any) -> None:
    (ROOT / path).write_text(
        json.dumps(value, ensure_ascii=False, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )


def replace_text(path: str, old: str, new: str, *, required: bool = False) -> None:
    target = ROOT / path
    text = target.read_text(encoding="utf-8")
    if required and old not in text and new not in text:
        raise RuntimeError(f"B1_EXPECTED_TEXT_NOT_FOUND:{path}:{old}")
    target.write_text(text.replace(old, new), encoding="utf-8")


def find_object_end(text: str, key: str) -> tuple[int, int]:
    marker = f'"{key}"'
    key_pos = text.find(marker)
    if key_pos < 0:
        raise RuntimeError(f"B1_OBJECT_KEY_NOT_FOUND:{key}")
    brace = text.find("{", key_pos + len(marker))
    if brace < 0:
        raise RuntimeError(f"B1_OBJECT_OPEN_NOT_FOUND:{key}")
    depth = 0
    in_string = False
    escaped = False
    for i in range(brace, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                return brace, i
    raise RuntimeError(f"B1_OBJECT_CLOSE_NOT_FOUND:{key}")


def insert_object_member(text: str, object_key: str, member_key: str, member: Any, indent: int) -> str:
    if f'"{member_key}"' in text:
        return text
    _, end = find_object_end(text, object_key)
    body = text[:end].rstrip()
    suffix = text[end:]
    prefix = "" if body.endswith("{") else ","
    rendered = json.dumps(member, ensure_ascii=False, indent=2)
    rendered_lines = rendered.splitlines()
    rendered = rendered_lines[0] + "\n" + "\n".join(" " * (indent + 2) + line for line in rendered_lines[1:])
    addition = f'{prefix}\n{" " * indent}"{member_key}": {rendered}\n'
    return body + addition + suffix


def replace_named_object(text: str, parent_key: str, child_key: str, value: Any, indent: int) -> str:
    start_parent, end_parent = find_object_end(text, parent_key)
    parent_slice = text[start_parent:end_parent + 1]
    marker = f'"{child_key}"'
    rel = parent_slice.find(marker)
    if rel < 0:
        raise RuntimeError(f"B1_CHILD_OBJECT_NOT_FOUND:{parent_key}:{child_key}")
    abs_key = start_parent + rel
    brace = text.find("{", abs_key + len(marker))
    depth = 0
    in_string = False
    escaped = False
    end = None
    for i in range(brace, len(text)):
        ch = text[i]
        if in_string:
            if escaped:
                escaped = False
            elif ch == "\\":
                escaped = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"': in_string = True
        elif ch == "{": depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0:
                end = i
                break
    if end is None:
        raise RuntimeError("B1_CHILD_OBJECT_CLOSE_NOT_FOUND")
    rendered = json.dumps(value, ensure_ascii=False, indent=2)
    lines = rendered.splitlines()
    rendered = lines[0] + "\n" + "\n".join(" " * (indent + 2) + line for line in lines[1:])
    return text[:brace] + rendered + text[end + 1:]


def migrate_parent() -> None:
    path = ROOT / "contracts/AF001-LIVING-STORY-CONTRACTS.json"
    text = path.read_text(encoding="utf-8")
    text = text.replace(f'"contract_version": "{OLD_PARENT}"', f'"contract_version": "{NEW_PARENT}"', 1)
    text = text.replace(OLD_GRAPH, NEW_GRAPH)
    # Every current registered extension is rebound to the new parent version.
    reg_start, reg_end = find_object_end(text, "registered_contract_extensions")
    reg_slice = text[reg_start:reg_end + 1].replace(OLD_PARENT, NEW_PARENT)
    text = text[:reg_start] + reg_slice + text[reg_end + 1:]
    bq_registration = {
        "path": "contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json",
        "binding_version": "1.0.0-candidate",
        "parent_contract_id": "AWRSE-AF001-LIVING-STORY-CONTRACTS",
        "parent_contract_version": NEW_PARENT,
        "parent_authority_graph_version": NEW_GRAPH,
        "authority": "MACHINE_CONTRACT_REGISTRY_DELEGATED_EXTENSION",
        "scope": "AF_F_BRANCH_QUALITY_DERIVED_EVIDENCE_VIEW_ONLY",
        "registration_class": "ADDITIVE_NON_RUNTIME_CANDIDATE_EXTENSION",
        "governance_issue_ref": "#95",
        "runtime_implementation_authorized": False,
        "canonical_data_authority": "NONE",
    }
    text = insert_object_member(text, "registered_contract_extensions", BQ_BINDING_ID, bq_registration, 4)
    profile = {
        "canonical_data_authority": ["NONE"],
        "contract_schema_steward": "AWRSE_AF_F_CONTRACT_STEWARD",
        "producer_or_assembler": ["AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER"],
        "downstream_consumer": ["NARRATIVE_OPPORTUNITY", "PX_RANKING", "AI_DIRECTOR"],
        "staging_authority": ["NONE"],
        "mutation_constraint": "DERIVED_BRANCH_EVIDENCE_MAY_DESCRIBE_ALREADY_VALIDATED_EVIDENCE_ONLY_AND_CANNOT_LEGALIZE_INVALID_CANDIDATES_CREATE_OR_REWRITE_WORLD_FACTS_OR_KNOWLEDGE_LOWER_CAPABILITY_DIFFICULTY_CREATE_PLAYER_INTENT_FORCE_STORYLET_OR_ENCOUNTER_REALIZATION_RETCON_RESURRECT_OR_FORCE_RECONVERGENCE",
    }
    text = insert_object_member(text, "profiles", BQ_PROFILE, profile, 6)
    bq_type = {
        "type_id": BQ_TYPE_ID,
        "version": "1.0.0-candidate",
        "domain": "AF-F",
        "authority_profile_ref": BQ_PROFILE,
        "implementation_state": "INTERFACE_ONLY_DERIVED_EVIDENCE_NOT_RUNTIME_IMPLEMENTED",
        "portable_integrity_invariant": "ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL",
        "fields": [
            "evidence_id", "evaluated_subject_ref", "source_kind", "source_package_sha256", "source_i1_sha256",
            "evidence_version", "authority_class", "causal_world_integrity", "agency_legibility",
            "knowledge_provenance_integrity", "opportunity_scarcity_evidence", "mechanism_evidence"
        ],
    }
    text = insert_object_member(text, "type_registry", BQ_TYPE, bq_type, 4)
    text = text.replace(
        '"InformationPacket","NarrativePromise"]',
        '"InformationPacket","NarrativePromise","BranchQualityEvidence"]',
    )
    if '"BRANCH_QUALITY_EVIDENCE_REQUIRES_REPLAY_VALID_SOURCE_PROVENANCE"' not in text:
        text = text.replace(
            '"BRANCH_QUALITY_CANNOT_JUSTIFY_RETCON_OR_RESURRECTION"]',
            '"BRANCH_QUALITY_CANNOT_JUSTIFY_RETCON_OR_RESURRECTION","BRANCH_QUALITY_EVIDENCE_REQUIRES_REPLAY_VALID_SOURCE_PROVENANCE","BRANCH_QUALITY_EVIDENCE_CANNOT_LEGALIZE_OR_MUTATE"]',
        )
    if '"branch_quality_evidence_extension_authority_rule"' not in text:
        anchor = '  "af_d_instance_admission_extension_authority_rule":'
        pos = text.find(anchor)
        if pos < 0:
            raise RuntimeError("B1_PARENT_AUTHORITY_RULE_ANCHOR_MISSING")
        line_end = text.find("\n", pos)
        rule = '  "branch_quality_evidence_extension_authority_rule": "EXACT_PARENT_CONTRACT_ID_PLUS_CONTRACT_VERSION_PLUS_AUTHORITY_GRAPH_VERSION_PLUS_PARENT_INVERSE_REGISTRATION_PLUS_GOLDEN_REPLAY_PROVENANCE_REGISTRATION_REQUIRED; PRE_I8DB1_PARENT_OR_CHILD_SELF_DECLARATION_OR_SYNTHETIC_B0_FIXTURE_CANNOT_AUTHORIZE_BRANCH_QUALITY_EVIDENCE; CANONICAL_DATA_AUTHORITY_REMAINS_NONE",\n'
        text = text[:line_end + 1] + rule + text[line_end + 1:]
    lineage = {
        "previous_contract_version": OLD_PARENT,
        "previous_authority_graph_version": OLD_GRAPH,
        "semantic_delta": [
            "ACTION_DEMAND_PROJECTION_BINDING_CANONICAL_EXTENSION_REGISTRATION",
            "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW_CANONICAL_EXTENSION_REGISTRATION",
            "BRANCH_QUALITY_EVIDENCE_AUTHORITY_PROFILE_ADDED_WITH_CANONICAL_DATA_AUTHORITY_NONE",
            "EXISTING_REGISTERED_EXTENSIONS_REBOUND_TO_NEW_PARENT_REGISTRY_EPOCH_WITHOUT_GAMEPLAY_SEMANTIC_CHANGE",
            "PRE_I8DB1_1_9_PARENT_AUTHORITY_GRAPH_AND_GOLDEN_TUPLE_CANNOT_AUTHORIZE_BRANCH_QUALITY_EXTENSION",
        ],
        "consumer_rule": "CONTRACT_ID_CONTRACT_VERSION_AND_AUTHORITY_GRAPH_VERSION_MUST_BE_RECORDED; BRANCH_QUALITY_EVIDENCE_REQUIRES_PARENT_AND_GOLDEN_INVERSE_REGISTRATION_AND_REPLAY_VALID_PROVENANCE",
    }
    text = replace_named_object(text, "versioning_and_migration", "contract_version_lineage", lineage, 4)
    path.write_text(text, encoding="utf-8")
    # Parse gate.
    json.loads(text)


def migrate_json_current_context() -> None:
    simple_files = [
        "contracts/AF001-ACTION-DEMAND-PROJECTION-BINDING.json",
        "contracts/AF001-AF-D-INSTANCE-ADMISSION-BINDING.json",
        "contracts/AF001-CAPABILITY-DECISION-RECEIPT-BINDING.json",
        "contracts/AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-BINDING.json",
        "evals/AF001-ASSET-SPATIAL-CONFORMANCE.json",
        "evals/AF001-CAPABILITY-DECISION-RECEIPT-FIXTURES.json",
        "evals/AF001-FUNCTIONAL-IMPAIRMENT-CAPABILITY-FIXTURES.json",
        "evals/AF001-WORLD-ECHO-CONFORMANCE.json",
        "registries/AF001-AF-D-REFERENCE-INSTANCES.json",
    ]
    for rel in simple_files:
        text = (ROOT / rel).read_text(encoding="utf-8").replace(OLD_PARENT, NEW_PARENT).replace(OLD_GRAPH, NEW_GRAPH)
        (ROOT / rel).write_text(text, encoding="utf-8")
        json.loads(text)

    action_fixture = load("evals/AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json")
    action_fixture["parent_golden_registry_version"] = NEW_GOLDEN
    dump("evals/AF001-ACTION-DEMAND-PROJECTION-FIXTURES.json", action_fixture)

    decision = load("evals/AF001-DECISION-LIFECYCLE-BINDINGS.json")
    decision["version"] = NEW_DECISION
    decision["required_contract_version"] = NEW_PARENT
    decision["migration_from_version"] = OLD_DECISION
    decision["migration_reason"] = "PARENT_CONTRACT_REGISTRY_EPOCH_ADVANCED_FOR_I8D_B1_WITH_DECISION_SEMANTICS_UNCHANGED"
    dump("evals/AF001-DECISION-LIFECYCLE-BINDINGS.json", decision)


def migrate_branch_binding() -> None:
    b = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")
    b["binding_version"] = "1.0.0-candidate"
    b["status"] = "CANONICAL_REGISTERED_INTERFACE_ONLY_NO_RUNTIME"
    b["canonical_authority"] = "PARENT_MACHINE_CONTRACT_INVERSE_REGISTRATION_DERIVED_VIEW_ONLY"
    b["stage_b1_registration_authorized"] = True
    b["runtime_implementation_authorized"] = False
    b["governance_issue_ref"] = "#95"
    b["canonical_parent_context"] = {
        "parent_contract_id": "AWRSE-AF001-LIVING-STORY-CONTRACTS",
        "parent_contract_version": NEW_PARENT,
        "parent_authority_graph_version": NEW_GRAPH,
        "golden_suite_id": "AWRSE-AF001-GOLDEN-SCENARIOS",
        "golden_suite_version": NEW_GOLDEN,
        "golden_required_contract_version": NEW_PARENT,
        "decision_lifecycle_binding_version": NEW_DECISION,
    }
    b["historical_b0_review_context"] = copy.deepcopy(b["parent_review_context"])
    b["historical_b0_review_context"]["status"] = "REVIEWED_B0_PRE_PROMOTION_CONTEXT_ONLY"
    b["proposed_authority_profile"]["profile_id"] = BQ_PROFILE
    b["proposed_type"]["version"] = "1.0.0-candidate"
    b["proposed_type"]["evidence_version"] = "1.0.0-candidate"
    b["proposed_type"]["implementation_state"] = "INTERFACE_ONLY_DERIVED_EVIDENCE_NOT_RUNTIME_IMPLEMENTED"
    b["promotion_gate"] = {
        "b1_completed_by_parent_inverse_registration": True,
        "parent_contract_version_advanced": True,
        "authority_graph_version_advanced": True,
        "golden_suite_version_advanced": True,
        "parent_inverse_registration_required": True,
        "golden_inverse_registration_required": True,
        "real_replay_valid_source_provenance_required": True,
        "synthetic_b0_fixture_hashes_forbidden_as_source_proof": True,
        "historical_parent_tuple_cannot_authorize_new_extension": True,
        "child_self_declaration_confers_no_authority": True,
        "runtime_remains_separately_unauthorized": True,
        "assessment_level_not_material_identity_invariant_preserved": True,
    }
    b["promotion_gate"].update({
        "stage_b1_required": True,
        "independent_accept_of_b0_required": True,
        "parent_contract_version_must_advance": True,
        "golden_suite_version_must_advance": True,
        "b1_must_preserve_assessment_level_not_material_identity_invariant": True,
        "b1_real_replay_valid_source_provenance_required": True,
        "b1_must_not_promote_synthetic_fixture_hashes_as_source_proof": True,
        "canonical_open_decisions_must_be_fresh_reconciled_before_b1": True,
        "parent_authority_graph_version_must_advance": True,
        "b1_golden_registration_must_use_replay_valid_fixture_artifact_not_b0_synthetic_suite": True,
        "b1_must_preserve_source_ref_admission_semantics": True,
    })
    b["hard_locks"]["STAGE_B1_CANONICAL_REGISTRATION_NOT_AUTHORIZED"] = False
    b["hard_locks"]["B1_CANONICAL_REGISTRATION_COMPLETED_INTERFACE_ONLY"] = True
    b["hard_locks"]["NO_SYNTHETIC_FIXTURE_PROMOTION_AS_SOURCE_PROOF"] = True
    b["canonical_provenance_fixture_ref"] = BQ_PROVENANCE_PATH
    dump("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json", b)


def refresh_rebound_integrity_digests() -> None:
    manifest_path = "registries/AF001-AF-D-REFERENCE-INSTANCES.json"
    binding_path = "contracts/AF001-AF-D-INSTANCE-ADMISSION-BINDING.json"
    parent_path = "contracts/AF001-LIVING-STORY-CONTRACTS.json"
    binding_id = "AWRSE-AF001-AF-D-INSTANCE-ADMISSION-BINDING"

    manifest = load(manifest_path)
    manifest_digest = sha256_bytes(canonical_json_bytes(manifest))

    binding = load(binding_path)
    manifest_registration = binding.get("canonical_instance_manifest")
    if not isinstance(manifest_registration, dict):
        raise RuntimeError("B1_AF_D_MANIFEST_REGISTRATION_MISSING")
    manifest_registration["canonical_sha256"] = manifest_digest
    dump(binding_path, binding)
    binding_digest = sha256_bytes(canonical_json_bytes(binding))

    parent = load(parent_path)
    registration = parent.get("registered_contract_extensions", {}).get(binding_id)
    if not isinstance(registration, dict):
        raise RuntimeError("B1_AF_D_PARENT_REGISTRATION_MISSING")
    registration["binding_canonical_sha256"] = binding_digest
    parent_manifest = registration.get("canonical_instance_manifest")
    if not isinstance(parent_manifest, dict):
        raise RuntimeError("B1_AF_D_PARENT_MANIFEST_REGISTRATION_MISSING")
    parent_manifest["canonical_sha256"] = manifest_digest
    dump(parent_path, parent)


def load_a2_test_helpers():
    path = ROOT / "tests/test_i8d_stage_a2_axis_stability_experiment.py"
    spec = importlib.util.spec_from_file_location("_b1_a2_helpers", path)
    if spec is None or spec.loader is None:
        raise RuntimeError("B1_A2_HELPER_LOAD_FAILED")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def canonical_json_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def make_provenance_fixtures() -> None:
    helpers = load_a2_test_helpers()
    import evals.i8d_branch_quality_evidence_experiment_v2 as r1
    from awrse.model import thaw_value

    sources = []
    _, i5_ready, _ = helpers.make_i5_pair()
    sources.append(("I5A_INFORMATION_OPPORTUNITY", helpers.stage_a("I5A_INFORMATION_OPPORTUNITY", i5_ready)))
    _, _, i7_ready, _ = helpers.make_i7_pair()
    sources.append(("I7A_WORLD_ECHO", helpers.stage_a("I7A_WORLD_ECHO", i7_ready)))
    _, _, _, i8_ready, _ = helpers.make_i8_pair()
    sources.append(("I8C_STORYLET", helpers.stage_a("I8C_STORYLET", i8_ready)))

    cases = []
    for index, (kind, package) in enumerate(sources, 1):
        result = r1.replay_branch_evidence_experiment_package(package)
        axes = thaw_value(result.axis_evidence)
        scarcity_axis = axes["legal_dead_end_opportunity_scarcity_risk"]
        scarcity = "RISK" if scarcity_axis["assessment"] == "RISK" else "ABSENT"
        mechanism = {}
        for name in (
            "character_relationship_continuity",
            "meaningful_state_information_relationship_delta",
            "setup_promise_anchor_continuity",
            "contrivance_repetition_risk",
        ):
            axis = axes[name]
            mechanism[name] = {
                "assessment": axis["assessment"],
                "source_refs": list(axis["evidence_refs"]),
            }
        evidence = {
            "evidence_id": f"BQ:B1:REPLAY:{index}:{kind}",
            "evaluated_subject_ref": f"REPLAY_SUBJECT:{kind}:{result.source_status}",
            "source_kind": kind,
            "source_package_sha256": result.source_package_sha256,
            "source_i1_sha256": result.source_i1_sha256,
            "evidence_version": "1.0.0-candidate",
            "authority_class": "DERIVED_EVIDENCE_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY",
            "causal_world_integrity": {"assessment": axes["causal_world_integrity"]["assessment"], "source_refs": list(axes["causal_world_integrity"]["evidence_refs"])},
            "agency_legibility": {"assessment": axes["agency_legibility"]["assessment"], "source_refs": list(axes["agency_legibility"]["evidence_refs"])},
            "knowledge_provenance_integrity": {"assessment": axes["knowledge_provenance_integrity"]["assessment"], "source_refs": list(axes["knowledge_provenance_integrity"]["evidence_refs"])},
            "opportunity_scarcity_evidence": {"assessment": scarcity, "source_refs": list(scarcity_axis["evidence_refs"]), "upstream_status_ref": result.source_status},
            "mechanism_evidence": mechanism,
        }
        cases.append({
            "case_id": f"B1-REAL-REPLAY-{index}-{kind}",
            "source_kind": kind,
            "stage_a_r1_package_b64": base64.b64encode(package).decode("ascii"),
            "stage_a_r1_package_sha256": sha256_bytes(package),
            "source_package_sha256": result.source_package_sha256,
            "source_i1_sha256": result.source_i1_sha256,
            "source_status": result.source_status,
            "branch_quality_evidence": evidence,
        })
    fixture = {
        "fixture_id": BQ_PROVENANCE_FIXTURE_ID,
        "fixture_version": BQ_PROVENANCE_VERSION,
        "fixture_role": "GOLDEN_REPLAY_VALID_PROVENANCE_EXTENSION",
        "parent_golden_registry": "evals/AF001-GOLDEN-SCENARIOS.json",
        "parent_golden_registry_version": NEW_GOLDEN,
        "required_contract_version": NEW_PARENT,
        "required_authority_graph_version": NEW_GRAPH,
        "binding_id": BQ_BINDING_ID,
        "evidence_class": "REAL_REPLAY_REBUILT_CANONICAL_SOURCE_PROOF",
        "synthetic_b0_fixture_ref": "evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json",
        "synthetic_b0_fixture_is_source_proof": False,
        "cases": cases,
    }
    dump(BQ_PROVENANCE_PATH, fixture)


def migrate_golden() -> None:
    path = ROOT / "evals/AF001-GOLDEN-SCENARIOS.json"
    text = path.read_text(encoding="utf-8")
    text = text.replace(f'"suite_version": "{OLD_GOLDEN}"', f'"suite_version": "{NEW_GOLDEN}"', 1)
    text = text.replace(f'"required_contract_version": "{OLD_PARENT}"', f'"required_contract_version": "{NEW_PARENT}"', 1)
    reg_start, reg_end = find_object_end(text, "registered_fixture_extensions")
    reg_slice = text[reg_start:reg_end + 1].replace(OLD_GOLDEN, NEW_GOLDEN)
    text = text[:reg_start] + reg_slice + text[reg_end + 1:]
    registration = {
        "path": BQ_PROVENANCE_PATH,
        "fixture_version": BQ_PROVENANCE_VERSION,
        "parent_eval_suite_id": "AWRSE-AF001-GOLDEN-SCENARIOS",
        "parent_suite_version": NEW_GOLDEN,
        "binding_id": BQ_BINDING_ID,
        "authority": "GOLDEN_EXECUTABLE_SPEC_REGISTRY_DELEGATED_EXTENSION",
        "evidence_class": "REAL_REPLAY_REBUILT_CANONICAL_SOURCE_PROOF",
    }
    text = insert_object_member(text, "registered_fixture_extensions", BQ_PROVENANCE_FIXTURE_ID, registration, 4)
    if "BRANCH_QUALITY_REPLAY_PROVENANCE_FIXTURE_EXPLICITLY_REGISTERED_BY_CANONICAL_SUITE" not in text:
        marker = '"ACTION_DEMAND_PROJECTION_FIXTURE_EXTENSION_EXPLICITLY_REGISTERED_BY_CANONICAL_SUITE"'
        text = text.replace(marker, marker + ',\n    "BRANCH_QUALITY_REPLAY_PROVENANCE_FIXTURE_EXPLICITLY_REGISTERED_BY_CANONICAL_SUITE"')
    path.write_text(text, encoding="utf-8")
    json.loads(text)


def migrate_current_code_refs() -> None:
    graph_files = [
        "runtime/awrse/functional_impairment_admission.py",
        "evals/i4a_npc_memory_reference.py",
        "evals/i5a_information_opportunity_shadow_reference.py",
        "evals/i7a_player_private_world_echo_reference.py",
        "evals/i8a_narrative_promise_reference.py",
        "evals/i8b_promise_callback_opportunity_reference.py",
        "evals/i8c_storylet_eligibility_reference.py",
        "evals/i8d_branch_quality_evidence_experiment.py",
        "tests/test_i2a_capability_decision_receipt_contract.py",
        "tests/test_i2a_functional_impairment_admission.py",
        "tests/test_i2a_functional_impairment_contract.py",
        "tests/test_i8d_branch_quality_evidence_experiment.py",
        "tests/test_i8d_stage_a_semantic_repair.py",
    ]
    parent_files = [
        "tests/test_af_d_instance_admission.py",
        "tests/test_i2a_action_demand_admission.py",
        "tests/test_i2a_action_demand_canonical_registration.py",
        "tests/test_i2a_action_demand_contract_freeze.py",
        "tests/test_i2a_capability_decision_receipt_contract.py",
        "tests/test_i2a_functional_impairment_admission.py",
        "tests/test_i2a_functional_impairment_contract.py",
        "tests/test_i3a_presentation_reference.py",
    ]
    for rel in graph_files:
        replace_text(rel, OLD_GRAPH, NEW_GRAPH)
        replace_text(rel, OLD_PARENT, NEW_PARENT)
    for rel in parent_files:
        replace_text(rel, OLD_PARENT, NEW_PARENT)
    replace_text("tests/test_i2a_action_demand_canonical_registration.py", OLD_GOLDEN, NEW_GOLDEN)
    replace_text("tests/test_i2a_functional_impairment_contract.py", 'lineage.get("previous_contract_version") != "1.8.0-candidate"', 'lineage.get("previous_contract_version") != "1.9.0-candidate"')
    replace_text("tests/test_i2a_action_demand_canonical_registration.py", 'previous_contract_version"] == "1.8.0-candidate"', 'previous_contract_version"] == "1.9.0-candidate"')
    replace_text("tests/test_i2a_action_demand_admission.py", 'contract["contract_version"] = "1.8.0-candidate"', 'contract["contract_version"] = "1.9.0-candidate"')
    replace_text("tests/test_i2a_action_demand_admission.py", 'registration["parent_contract_version"] = "1.8.0-candidate"', 'registration["parent_contract_version"] = "1.9.0-candidate"')
    replace_text("tests/test_i2a_action_demand_admission.py", 'binding["parent_machine_contract"]["contract_version"] = "1.8.0-candidate"', 'binding["parent_machine_contract"]["contract_version"] = "1.9.0-candidate"')
    replace_text("tests/test_i2a_skill_ledger_contract_freeze.py", 'assert contract["contract_version"] == "1.9.0-candidate"', 'assert contract["contract_version"] == "1.10.0-candidate"')
    replace_text("tests/test_i2a_skill_ledger_contract_freeze.py", 'assert suite["suite_version"] == "1.7.0-candidate"', 'assert suite["suite_version"] == "1.8.0-candidate"')

    architecture_path = ROOT / "tests/test_af001_architecture_freeze.py"
    architecture_text = architecture_path.read_text(encoding="utf-8")
    old_architecture = """    assert contract["contract_version"] == "1.9.0-candidate"
    assert contract["versioning_and_migration"]["contract_version_lineage"] == {
        "previous_contract_version": "1.8.0-candidate",
        "semantic_delta": [
            "ACTION_DEMAND_PROJECTION_BINDING_CANONICAL_EXTENSION_REGISTRATION",
            "ACTION_DEMAND_PROJECTION_EXTENSION_AUTHORITY_IS_PARENT_REGISTERED_AND_VERSION_BOUND",
            "PRE_REGISTRATION_1_8_PARENT_VERSION_CANNOT_AUTHORIZE_NEW_EXTENSION",
        ],
        "consumer_rule": "CONTRACT_ID_AND_CONTRACT_VERSION_MUST_BE_RECORDED_TO_DISTINGUISH_ACTION_DEMAND_EXTENSION_AUTHORITY_FROM_PRE_REGISTRATION_1_8_STATE",
    }
    assert suite["suite_version"] == "1.7.0-candidate"
    assert suite["required_contract_version"] == contract["contract_version"]
    assert bindings["version"] == "1.2.0-candidate"
    assert bindings["required_contract_version"] == contract["contract_version"]
"""
    new_architecture = """    assert contract["contract_version"] == "1.10.0-candidate"
    lineage = contract["versioning_and_migration"]["contract_version_lineage"]
    assert lineage["previous_contract_version"] == "1.9.0-candidate"
    assert set(lineage["semantic_delta"]) >= {
        "ACTION_DEMAND_PROJECTION_BINDING_CANONICAL_EXTENSION_REGISTRATION",
        "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW_CANONICAL_EXTENSION_REGISTRATION",
        "BRANCH_QUALITY_EVIDENCE_AUTHORITY_PROFILE_ADDED_WITH_CANONICAL_DATA_AUTHORITY_NONE",
        "EXISTING_REGISTERED_EXTENSIONS_REBOUND_TO_NEW_PARENT_REGISTRY_EPOCH_WITHOUT_GAMEPLAY_SEMANTIC_CHANGE",
        "PRE_I8DB1_1_9_PARENT_AUTHORITY_GRAPH_AND_GOLDEN_TUPLE_CANNOT_AUTHORIZE_BRANCH_QUALITY_EXTENSION",
    }
    assert "BRANCH_QUALITY_EVIDENCE_REQUIRES_PARENT_AND_GOLDEN_INVERSE_REGISTRATION_AND_REPLAY_VALID_PROVENANCE" in lineage["consumer_rule"]
    assert suite["suite_version"] == "1.8.0-candidate"
    assert suite["required_contract_version"] == contract["contract_version"]
    assert bindings["version"] == "1.3.0-candidate"
    assert bindings["required_contract_version"] == contract["contract_version"]
"""
    if old_architecture in architecture_text:
        architecture_text = architecture_text.replace(old_architecture, new_architecture, 1)
    elif new_architecture not in architecture_text:
        raise RuntimeError("B1_ARCHITECTURE_CURRENT_ASSERTION_ANCHOR_MISSING")
    architecture_path.write_text(architecture_text, encoding="utf-8")


def write_b1_validator_and_tests() -> None:
    module = r'''"""I8D B1 canonical BranchQualityEvidence registration and real replay provenance validator."""
from __future__ import annotations
import base64, copy, hashlib, json, re
from pathlib import Path
from typing import Any, Mapping
from awrse.model import thaw_value
import evals.i8d_branch_quality_evidence_experiment_v2 as r1

ROOT = Path(__file__).resolve().parents[1]
PARENT = ROOT / "contracts/AF001-LIVING-STORY-CONTRACTS.json"
GOLDEN = ROOT / "evals/AF001-GOLDEN-SCENARIOS.json"
BINDING = ROOT / "contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json"
PROVENANCE = ROOT / "evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json"
DECISIONS = ROOT / "evals/AF001-DECISION-LIFECYCLE-BINDINGS.json"
TRACE = ROOT / "docs/AF001-TRACEABILITY.md"
PARENT_VERSION = "1.10.0-candidate"
GRAPH_VERSION = "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1"
GOLDEN_VERSION = "1.8.0-candidate"
DECISION_VERSION = "1.3.0-candidate"
BINDING_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-BINDING"
FIXTURE_ID = "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES"
PROFILE_ID = "BRANCH_QUALITY_EVIDENCE_DERIVED_VIEW"
NO_RUNTIME_IMPLEMENTATION = True
NO_BRANCH_QUALITY_SCORE = True
NO_PX_RANKING_IMPLEMENTATION = True
NO_WORLD_OR_KNOWLEDGE_MUTATION = True
NO_STORYLET_OR_ENCOUNTER_REALIZATION = True
NO_ENGAGEMENT_RETENTION_OBJECTIVE = True


def load(path): return json.loads(path.read_text(encoding="utf-8"))
def sha_bytes(v): return hashlib.sha256(v).hexdigest()

def expected_projection(result):
    axes = thaw_value(result.axis_evidence)
    scarcity = axes["legal_dead_end_opportunity_scarcity_risk"]
    return {
        "source_kind": result.source_kind,
        "source_package_sha256": result.source_package_sha256,
        "source_i1_sha256": result.source_i1_sha256,
        "causal_world_integrity": {"assessment": axes["causal_world_integrity"]["assessment"], "source_refs": list(axes["causal_world_integrity"]["evidence_refs"])},
        "agency_legibility": {"assessment": axes["agency_legibility"]["assessment"], "source_refs": list(axes["agency_legibility"]["evidence_refs"])},
        "knowledge_provenance_integrity": {"assessment": axes["knowledge_provenance_integrity"]["assessment"], "source_refs": list(axes["knowledge_provenance_integrity"]["evidence_refs"])},
        "opportunity_scarcity_evidence": {"assessment": "RISK" if scarcity["assessment"] == "RISK" else "ABSENT", "source_refs": list(scarcity["evidence_refs"]), "upstream_status_ref": result.source_status},
        "mechanism_evidence": {name: {"assessment": axes[name]["assessment"], "source_refs": list(axes[name]["evidence_refs"])} for name in ("character_relationship_continuity","meaningful_state_information_relationship_delta","setup_promise_anchor_continuity","contrivance_repetition_risk")},
    }


def validate_b1_canonical_registration() -> dict[str, Any]:
    parent, golden, binding, prov, decisions = map(load, (PARENT, GOLDEN, BINDING, PROVENANCE, DECISIONS))
    if parent.get("contract_version") != PARENT_VERSION or parent.get("authority_graph_version") != GRAPH_VERSION: raise ValueError("B1_PARENT_TUPLE_INVALID")
    reg = parent.get("registered_contract_extensions", {}).get(BINDING_ID)
    if not isinstance(reg, Mapping) or reg.get("parent_contract_version") != PARENT_VERSION or reg.get("parent_authority_graph_version") != GRAPH_VERSION: raise ValueError("B1_PARENT_INVERSE_REGISTRATION_INVALID")
    profile = parent.get("authority_semantics", {}).get("profiles", {}).get(PROFILE_ID)
    if not isinstance(profile, Mapping) or profile.get("canonical_data_authority") != ["NONE"]: raise ValueError("B1_PROFILE_AUTHORITY_INVALID")
    t = parent.get("type_registry", {}).get("BranchQualityEvidence")
    if not isinstance(t, Mapping) or t.get("type_id") != "AF001.BranchQualityEvidence" or t.get("authority_profile_ref") != PROFILE_ID: raise ValueError("B1_TYPE_REGISTRATION_INVALID")
    if golden.get("suite_version") != GOLDEN_VERSION or golden.get("required_contract_version") != PARENT_VERSION: raise ValueError("B1_GOLDEN_TUPLE_INVALID")
    freg = golden.get("registered_fixture_extensions", {}).get(FIXTURE_ID)
    if not isinstance(freg, Mapping) or freg.get("path") != "evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json" or freg.get("parent_suite_version") != GOLDEN_VERSION: raise ValueError("B1_GOLDEN_INVERSE_REGISTRATION_INVALID")
    if decisions.get("version") != DECISION_VERSION or decisions.get("required_contract_version") != PARENT_VERSION: raise ValueError("B1_DECISION_REGISTRY_MIGRATION_INVALID")
    if prov.get("evidence_class") != "REAL_REPLAY_REBUILT_CANONICAL_SOURCE_PROOF" or prov.get("synthetic_b0_fixture_is_source_proof") is not False: raise ValueError("B1_PROVENANCE_CLASS_INVALID")
    seen = set()
    for case in prov.get("cases", []):
        package = base64.b64decode(case["stage_a_r1_package_b64"], validate=True)
        if sha_bytes(package) != case["stage_a_r1_package_sha256"]: raise ValueError("B1_STAGE_A_PACKAGE_DIGEST_INVALID")
        result = r1.replay_branch_evidence_experiment_package(package)
        expected = expected_projection(result)
        evidence = case["branch_quality_evidence"]
        for key, value in expected.items():
            if evidence.get(key) != value: raise ValueError(f"B1_REPLAY_PROJECTION_MISMATCH:{case['case_id']}:{key}")
        if evidence.get("evidence_version") != "1.0.0-candidate" or evidence.get("authority_class") != "DERIVED_EVIDENCE_ONLY_NOT_WORLD_LEGALITY_OR_PX_AUTHORITY": raise ValueError("B1_EVIDENCE_AUTHORITY_INVALID")
        seen.add(result.source_kind)
    if seen != {"I5A_INFORMATION_OPPORTUNITY","I7A_WORLD_ECHO","I8C_STORYLET"}: raise ValueError("B1_REAL_REPLAY_SOURCE_COVERAGE_INCOMPLETE")
    trace = TRACE.read_text(encoding="utf-8")
    for decision in ("OD-CLUE-QUALITY-001","OD-PX-SCORING-001"):
        if f"### {decision} " not in trace: raise ValueError("B1_OPEN_DECISION_MISSING")
    return {"cases": len(prov["cases"]), "source_kinds": sorted(seen), "parent": PARENT_VERSION, "graph": GRAPH_VERSION, "golden": GOLDEN_VERSION}


def historical_tuple_authorizes(parent_version: str, graph_version: str, golden_version: str, binding_registered: bool=True, fixture_registered: bool=True) -> bool:
    return bool(parent_version == PARENT_VERSION and graph_version == GRAPH_VERSION and golden_version == GOLDEN_VERSION and binding_registered and fixture_registered)
'''
    test = r'''import base64, copy, json
from pathlib import Path
import pytest
import evals.i8d_b1_branch_quality_canonical_registration as b1

ROOT = Path(__file__).resolve().parents[1]
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))

def test_b1_canonical_registration_and_real_replay_provenance():
    receipt = b1.validate_b1_canonical_registration()
    assert receipt["cases"] == 3
    assert receipt["source_kinds"] == ["I5A_INFORMATION_OPPORTUNITY","I7A_WORLD_ECHO","I8C_STORYLET"]

def test_old_parent_graph_golden_tuple_cannot_authorize():
    assert not b1.historical_tuple_authorizes("1.9.0-candidate", b1.GRAPH_VERSION, b1.GOLDEN_VERSION)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, "AF001-AUTHORITY-GRAPH-1.9-I2A008@1", b1.GOLDEN_VERSION)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, "1.7.0-candidate")
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION, binding_registered=False)
    assert not b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION, fixture_registered=False)
    assert b1.historical_tuple_authorizes(b1.PARENT_VERSION, b1.GRAPH_VERSION, b1.GOLDEN_VERSION)

def test_parent_profile_has_no_canonical_data_authority_and_px_is_downstream_only():
    parent=load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    p=parent["authority_semantics"]["profiles"][b1.PROFILE_ID]
    assert p["canonical_data_authority"] == ["NONE"]
    assert p["producer_or_assembler"] == ["AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER"]
    assert p["downstream_consumer"] == ["NARRATIVE_OPPORTUNITY","PX_RANKING","AI_DIRECTOR"]
    assert p["staging_authority"] == ["NONE"]

def test_branch_quality_type_preserves_frozen_shape_and_no_score():
    parent=load("contracts/AF001-LIVING-STORY-CONTRACTS.json")
    t=parent["type_registry"]["BranchQualityEvidence"]
    assert t["portable_integrity_invariant"] == "ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL"
    assert set(t["fields"]) == {"evidence_id","evaluated_subject_ref","source_kind","source_package_sha256","source_i1_sha256","evidence_version","authority_class","causal_world_integrity","agency_legibility","knowledge_provenance_integrity","opportunity_scarcity_evidence","mechanism_evidence"}
    assert not {"score","weight","rank","legality_result","player_intent"} & set(t["fields"])

def test_synthetic_b0_fixture_is_not_registered_as_source_proof():
    golden=load("evals/AF001-GOLDEN-SCENARIOS.json")
    assert "AWRSE-AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES" not in golden["registered_fixture_extensions"]
    p=load("evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json")
    assert p["synthetic_b0_fixture_is_source_proof"] is False
    assert p["synthetic_b0_fixture_ref"] == "evals/AF001-BRANCH-QUALITY-EVIDENCE-FIXTURES.json"

def test_real_replay_package_tamper_fails_closed():
    p=load("evals/AF001-BRANCH-QUALITY-EVIDENCE-PROVENANCE-FIXTURES.json")
    case=copy.deepcopy(p["cases"][0])
    raw=bytearray(base64.b64decode(case["stage_a_r1_package_b64"]))
    raw[-2] ^= 1
    case["stage_a_r1_package_b64"] = base64.b64encode(bytes(raw)).decode("ascii")
    case["stage_a_r1_package_sha256"] = b1.sha_bytes(bytes(raw))
    import evals.i8d_branch_quality_evidence_experiment_v2 as r1
    with pytest.raises(ValueError): r1.replay_branch_evidence_experiment_package(bytes(raw))

def test_decision_lifecycle_migrates_registry_identity_without_resolving_quality_or_px():
    d=load("evals/AF001-DECISION-LIFECYCLE-BINDINGS.json")
    assert d["version"] == "1.3.0-candidate"
    assert d["required_contract_version"] == "1.10.0-candidate"
    trace=(ROOT/"docs/AF001-TRACEABILITY.md").read_text(encoding="utf-8")
    assert "### OD-CLUE-QUALITY-001 " in trace
    assert "### OD-PX-SCORING-001 " in trace

def test_hard_locks_keep_runtime_and_optimizer_authority_closed():
    assert b1.NO_RUNTIME_IMPLEMENTATION
    assert b1.NO_BRANCH_QUALITY_SCORE
    assert b1.NO_PX_RANKING_IMPLEMENTATION
    assert b1.NO_WORLD_OR_KNOWLEDGE_MUTATION
    assert b1.NO_STORYLET_OR_ENCOUNTER_REALIZATION
    assert b1.NO_ENGAGEMENT_RETENTION_OBJECTIVE
'''
    doc = f'''# I8D B1 BranchQualityEvidence canonical registration\n\nStatus: `CANONICAL_REGISTRATION_CANDIDATE / NO_RUNTIME / NO_PX_SCORING`.\n\nB1 migrates the parent machine-contract registry from `{OLD_PARENT}` to `{NEW_PARENT}`, authority graph from `{OLD_GRAPH}` to `{NEW_GRAPH}`, Golden suite from `{OLD_GOLDEN}` to `{NEW_GOLDEN}`, and decision-lifecycle bindings from `{OLD_DECISION}` to `{NEW_DECISION}`.\n\nThe B0 interface shape is preserved. Canonical registration grants schema/derived-view legitimacy only; `canonical_data_authority` remains `NONE`. The registered Golden provenance artifact contains replayable Stage A R1 packages for I5A, I7A and I8C and is mechanically replayed in tests. The B0 synthetic fixture suite remains non-source-proof evidence.\n\nHistorical tuple `{OLD_PARENT}` + `{OLD_GRAPH}` + `{OLD_GOLDEN}` cannot authorize BranchQualityEvidence. Existing registered extensions are rebound to the new parent registry epoch without changing gameplay formulas or authority scope.\n\nHard locks: no BranchQuality runtime producer, no PX scoring/weights, no world or knowledge mutation, no automatic Storylet/encounter realization, no engagement/retention objective, no provider/renderer authority.\n'''
    (ROOT/"evals/i8d_b1_branch_quality_canonical_registration.py").write_text(module, encoding="utf-8")
    (ROOT/"tests/test_i8d_b1_branch_quality_canonical_registration.py").write_text(test, encoding="utf-8")
    (ROOT/"docs/I8D-B1-BRANCH-QUALITY-CANONICAL-REGISTRATION.md").write_text(doc, encoding="utf-8")


def migrate_b0_historical_tests() -> None:
    # B0 is now historical freeze evidence. Current promotion semantics are validated by B1 tests.
    p = ROOT / "tests/test_i8d_branch_quality_evidence_freeze.py"
    text = p.read_text(encoding="utf-8")
    text = text.replace('assert b0.B0_CANDIDATE_NOT_CANONICAL is True', 'assert b0.B0_CANDIDATE_NOT_CANONICAL is True  # historical B0 declaration')
    text = text.replace('def test_freeze_candidate_validates_and_is_not_registered():', 'def test_freeze_candidate_historical_validator_is_superseded_by_b1_registration():')
    old_block = '''    receipt = b0.validate_freeze_candidate()\n    assert receipt.parent_contract_version == "1.9.0-candidate"\n    assert receipt.golden_suite_version == "1.7.0-candidate"\n    assert receipt.canonical_registration_present is False\n    assert receipt.b1_required is True\n    assert len(receipt.binding_sha256) == 64\n    assert len(receipt.fixture_sha256) == 64\n'''
    new_block = '''    binding = load("contracts/AF001-BRANCH-QUALITY-EVIDENCE-BINDING.json")\n    parent = load("contracts/AF001-LIVING-STORY-CONTRACTS.json")\n    assert binding["status"] == "CANONICAL_REGISTERED_INTERFACE_ONLY_NO_RUNTIME"\n    assert b0.BINDING_ID in parent["registered_contract_extensions"]\n    assert binding["historical_b0_review_context"]["parent_contract_version"] == "1.9.0-candidate"\n'''
    text = text.replace(old_block, new_block)
    text = text.replace('def test_parent_registry_does_not_yet_grant_candidate_authority():', 'def test_parent_registry_now_grants_only_derived_view_schema_authority():')
    text = text.replace('    assert b0.BINDING_ID not in parent["registered_contract_extensions"]', '    assert b0.BINDING_ID in parent["registered_contract_extensions"]')
    text = text.replace('assert parent["contract_version"] == b0.PARENT_VERSION', 'assert parent["contract_version"] == "1.10.0-candidate"')
    text = text.replace('assert parent["authority_graph_version"] == b0.PARENT_AUTHORITY_GRAPH', 'assert parent["authority_graph_version"] == "AF001-AUTHORITY-GRAPH-1.10-I8DB1@1"')
    text = text.replace('assert golden["suite_version"] == b0.GOLDEN_VERSION', 'assert golden["suite_version"] == "1.8.0-candidate"')
    text = text.replace('assert golden["required_contract_version"] == b0.PARENT_VERSION', 'assert golden["required_contract_version"] == "1.10.0-candidate"')
    p.write_text(text, encoding="utf-8")


def main() -> None:
    migrate_parent()
    migrate_json_current_context()
    migrate_branch_binding()
    refresh_rebound_integrity_digests()
    migrate_golden()
    migrate_current_code_refs()
    make_provenance_fixtures()
    write_b1_validator_and_tests()
    migrate_b0_historical_tests()
    print(json.dumps({"status":"B1_MIGRATION_GENERATED","parent":NEW_PARENT,"graph":NEW_GRAPH,"golden":NEW_GOLDEN,"decision":NEW_DECISION}, indent=2))

if __name__ == "__main__":
    main()
