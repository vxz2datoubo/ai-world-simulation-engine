import copy
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
PARENT_PATH = ROOT / "contracts" / "AF001-LIVING-STORY-CONTRACTS.json"
EVAL_PATH = ROOT / "evals" / "AF001-WORLD-ECHO-CONFORMANCE.json"

REQUIRED_PARENT_TYPES = {
    "NPCPerceptionEvent",
    "NPCEpisodicMemory",
    "BeliefState",
    "NPCPlayerRelationshipState",
    "NPCContextBundle",
    "WorldEchoOpportunity",
    "ResponseConcept",
    "PlayerAutoExpressionPolicy",
}


def load_json(path: Path):
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def by_id(items, key):
    out = {}
    for item in items:
        value = item[key]
        assert value not in out, f"DUPLICATE_ID:{key}:{value}"
        out[value] = item
    return out


def _projection_by(items, key):
    return {item[key]: item for item in items}


def _validate(doc):
    fixture = doc["synthetic_fixture"]
    objects = fixture["canonical_objects"]
    p = fixture["eval_only_projections"]

    perceptions = by_id(objects["NPCPerceptionEvent"], "perception_id")
    memories = by_id(objects["NPCEpisodicMemory"], "memory_id")
    beliefs = by_id(objects["BeliefState"], "belief_id")
    contexts = by_id(objects["NPCContextBundle"], "npc_id")
    echoes = by_id(objects["WorldEchoOpportunity"], "echo_id")
    responses = by_id(objects["ResponseConcept"], "response_concept_id")
    policies = by_id(objects["PlayerAutoExpressionPolicy"], "player_id")
    attrs = _projection_by(p["attributions"], "attribution_id")
    knowledge = _projection_by(p["context_knowledge"], "npc_id")
    realizations = _projection_by(p["realizations"], "echo_id")

    world_history = p["world_history"]
    delta = p["environmental_delta"]
    known_world_events = set(world_history["known_event_refs"])

    for memory in memories.values():
        for perception_ref in memory["source_perception_refs"]:
            if perception_ref not in perceptions:
                return "MEMORY_PERCEPTION_REF_UNKNOWN"
            if perceptions[perception_ref]["npc_id"] != memory["npc_id"]:
                return "MEMORY_PERCEPTION_OWNER_MISMATCH"
        if not memory["source_perception_refs"]:
            return "MEMORY_REQUIRES_ACQUISITION_EVIDENCE"

    for belief in beliefs.values():
        for evidence_ref in belief["supporting_refs"] + belief["contradicting_refs"]:
            if evidence_ref not in memories:
                return "BELIEF_EVIDENCE_REF_UNKNOWN"
            if memories[evidence_ref]["npc_id"] != belief["npc_id"]:
                return "BELIEF_EVIDENCE_OWNER_MISMATCH"

    for npc_id, context in contexts.items():
        for memory_ref in context["episodic_memory_refs"]:
            if memory_ref not in memories:
                return "CONTEXT_MEMORY_REF_UNKNOWN"
            if memories[memory_ref]["npc_id"] != npc_id:
                return "CONTEXT_CROSS_NPC_MEMORY_LEAK"
        for belief_ref in context["belief_refs"]:
            if belief_ref not in beliefs:
                return "CONTEXT_BELIEF_REF_UNKNOWN"
            if beliefs[belief_ref]["npc_id"] != npc_id:
                return "CONTEXT_CROSS_NPC_BELIEF_LEAK"
        available = set(knowledge[npc_id]["available_fact_refs"])
        hidden = set(context["forbidden_hidden_fact_refs"])
        if available & hidden:
            return "FORBIDDEN_HIDDEN_FACT_DISCLOSED"

    for attr in attrs.values():
        speaker = attr["speaker_id"]
        for memory_ref in attr["evidence_memory_refs"]:
            if memory_ref not in memories or memories[memory_ref]["npc_id"] != speaker:
                return "ATTRIBUTION_EVIDENCE_INVALID"
        if attr["kind"] == "WITNESSED_CAUSE":
            if not attr["evidence_memory_refs"]:
                return "WITNESS_ATTRIBUTION_REQUIRES_DIRECT_EVIDENCE"
            if any(memories[m]["provenance_kind"] != "SAW" for m in attr["evidence_memory_refs"]):
                return "WITNESS_ATTRIBUTION_REQUIRES_DIRECT_EVIDENCE"
            if attr["certainty"] != "DIRECT":
                return "WITNESS_ATTRIBUTION_REQUIRES_DIRECT_EVIDENCE"
        if attr["kind"] in {"RUMORED_CAUSE", "TOLD_CAUSE"} and attr["certainty"] != "HEDGED":
            return "RUMOR_ATTRIBUTION_MUST_REMAIN_HEDGED"
        if attr["kind"] == "UNKNOWN_CAUSE":
            culprit_ref = "FACT-CULPRIT-PLAYER-A"
            if culprit_ref in attr["authorized_fact_refs"]:
                return "UNKNOWN_CULPRIT_FACT_LEAK"

    for rel in objects["NPCPlayerRelationshipState"]:
        if "minted_memory_ref" in rel or "minted_perception_ref" in rel:
            return "RELATIONSHIP_CANNOT_AUTHOR_EPISTEMIC_EVIDENCE"

    audit = p["belief_audit"]
    audited = beliefs[audit["belief_id"]]
    if not set(audit["must_preserve_support_refs"]) <= set(audited["supporting_refs"]):
        return "BELIEF_CORRECTION_ERASED_SOURCE_HISTORY"
    if not set(audit["must_preserve_contradiction_refs"]) <= set(audited["contradicting_refs"]):
        return "BELIEF_CORRECTION_ERASED_SOURCE_HISTORY"

    if not delta["exists"]:
        if any(r.get("selected") for r in p["realizations"]):
            return "ECHO_REQUIRES_ENVIRONMENTAL_DELTA"
    if delta["source_event_ref"] not in known_world_events:
        return "ECHO_SOURCE_EVENT_UNKNOWN"

    for echo_id, echo in echoes.items():
        if delta["delta_id"] not in echo["source_event_or_delta_refs"]:
            return "ECHO_SOURCE_DELTA_MISMATCH"
        if not set(echo["source_event_or_delta_refs"]).issubset(known_world_events | {delta["delta_id"]}):
            return "ECHO_SOURCE_REF_UNKNOWN"
        if len(echo["speaker_candidate_refs"]) != 1 or len(echo["knowledge_attribution_refs"]) != 1:
            return "ECHO_BINDING_AMBIGUOUS"
        speaker = echo["speaker_candidate_refs"][0]
        attr_ref = echo["knowledge_attribution_refs"][0]
        if attr_ref not in attrs or attrs[attr_ref]["speaker_id"] != speaker:
            return "ECHO_ATTRIBUTION_SPEAKER_MISMATCH"
        for response_ref in echo["response_concept_refs"]:
            if response_ref not in responses:
                return "ECHO_RESPONSE_CONCEPT_UNKNOWN"

        realization = realizations[echo_id]
        if realization["speaker_id"] != speaker:
            return "ECHO_REALIZATION_SPEAKER_MISMATCH"
        response = responses[echo["response_concept_refs"][0]]
        available = set(knowledge[speaker]["available_fact_refs"])
        if not set(response["required_fact_refs"]).issubset(available):
            return "RESPONSE_REQUIRED_FACT_UNAVAILABLE"
        if not set(realization["claim_fact_refs"]).issubset(set(attrs[attr_ref]["authorized_fact_refs"]) | set(response["required_fact_refs"])):
            return "RESPONSE_CLAIM_NOT_AUTHORIZED"
        if set(realization["claim_classes"]) & set(response["forbidden_claim_classes"]):
            return "RESPONSE_FORBIDDEN_CLAIM_CLASS"

        if realization.get("selected"):
            if echo["novelty_key"] in p["echo_history"]["seen_novelty_keys"]:
                return "DUPLICATE_ECHO_MUST_SUPPRESS"
            if world_history["current_world_time"] > echo["expiry_policy"]["until_world_time"]:
                return "ECHO_EXPIRED_MUST_SUPPRESS"
            if echo_id in p["commentary_budget"]["suppressed_echo_ids"] or echo_id not in p["commentary_budget"]["allowed_echo_ids"]:
                return "COMMENTARY_BUDGET_SUPPRESSION_REQUIRED"

    player_probe = p["player_realization"]
    policy = policies[player_probe["player_id"]]
    if player_probe["mode"] == "PRIVATE_INNER_COMMENTARY":
        if player_probe["audible"] or player_probe["world_event_created"]:
            return "PRIVATE_COMMENTARY_MUST_BE_NON_DIEGETIC"
    if player_probe["risk_class"] in {"R2_SENSITIVE", "R3_HIGH_IMPACT"} and player_probe["audible"]:
        if not player_probe["explicit_player_intent_ref"]:
            return "HIGH_RISK_SPEECH_REQUIRES_EXPLICIT_INTENT"
    if player_probe["mode"] == "AUTHORIZED_LOW_RISK_DIEGETIC_BARK":
        if not policy["authorized_low_risk_bark_enabled"] or player_probe["risk_class"] not in policy["allowed_risk_classes"]:
            return "PLAYER_AUTO_BARK_NOT_AUTHORIZED"

    if p["generated_summary_probe"]["claims_memory_authority"]:
        return "SUMMARY_CANNOT_AUTHOR_MEMORY"
    if p["downstream_presentation_probe"]["invented_fact_refs"]:
        return "DOWNSTREAM_CANNOT_INVENT_WORLD_FACT"

    return None


def _mutate(doc, mutation):
    if mutation == "NONE":
        return
    o = doc["synthetic_fixture"]["canonical_objects"]
    p = doc["synthetic_fixture"]["eval_only_projections"]

    if mutation == "OMNISCIENT_CULPRIT_LEAK":
        next(a for a in p["attributions"] if a["attribution_id"] == "ATTR-NEWCOMER")["authorized_fact_refs"].append("FACT-CULPRIT-PLAYER-A")
    elif mutation == "MISSING_PERCEPTION_FOR_WITNESS":
        next(m for m in o["NPCEpisodicMemory"] if m["memory_id"] == "M-WITNESS")["source_perception_refs"] = ["P-MISSING"]
    elif mutation == "CROSS_NPC_MEMORY_LEAK":
        next(c for c in o["NPCContextBundle"] if c["npc_id"] == "NPC-NEWCOMER")["episodic_memory_refs"] = ["M-WITNESS"]
    elif mutation == "RUMOR_UPGRADED_TO_DIRECT":
        a = next(a for a in p["attributions"] if a["attribution_id"] == "ATTR-RUMOR")
        a["kind"] = "WITNESSED_CAUSE"
        a["certainty"] = "DIRECT"
    elif mutation == "RUMOR_UNHEDGED_CLAIM":
        r = next(r for r in p["realizations"] if r["echo_id"] == "ECHO-RUMOR")
        r["claim_classes"] = ["ASSERT_WITNESSED_CAUSE"]
    elif mutation == "NEWCOMER_NAMES_CULPRIT":
        r = next(r for r in p["realizations"] if r["echo_id"] == "ECHO-NEWCOMER")
        r["claim_fact_refs"].append("FACT-CULPRIT-PLAYER-A")
    elif mutation == "MEMORY_NPC_ID_DRIFT":
        next(m for m in o["NPCEpisodicMemory"] if m["memory_id"] == "M-WITNESS")["npc_id"] = "NPC-RUMOR"
    elif mutation == "MEMORY_SOURCE_PERCEPTION_UNKNOWN":
        next(m for m in o["NPCEpisodicMemory"] if m["memory_id"] == "M-RUMOR")["source_perception_refs"] = ["P-UNKNOWN"]
    elif mutation == "BELIEF_SUPPORT_UNKNOWN":
        next(b for b in o["BeliefState"] if b["belief_id"] == "B-RUMOR-CULPRIT")["supporting_refs"] = ["M-UNKNOWN"]
    elif mutation == "CORRECTION_ERASES_RUMOR_HISTORY":
        next(b for b in o["BeliefState"] if b["belief_id"] == "B-RUMOR-CULPRIT")["supporting_refs"] = []
    elif mutation == "RELATIONSHIP_MINTS_MEMORY":
        o["NPCPlayerRelationshipState"][0]["minted_memory_ref"] = "M-FORGED"
    elif mutation == "FORBIDDEN_HIDDEN_FACT_DISCLOSED":
        next(k for k in p["context_knowledge"] if k["npc_id"] == "NPC-RUMOR")["available_fact_refs"].append("FACT-CULPRIT-PLAYER-A")
    elif mutation == "ECHO_SOURCE_DELTA_DRIFT":
        next(e for e in o["WorldEchoOpportunity"] if e["echo_id"] == "ECHO-WITNESS")["source_event_or_delta_refs"] = ["E-DOOR-BREAK", "DELTA-OTHER"]
    elif mutation == "ECHO_SPEAKER_ATTRIBUTION_MISMATCH":
        next(e for e in o["WorldEchoOpportunity"] if e["echo_id"] == "ECHO-WITNESS")["knowledge_attribution_refs"] = ["ATTR-RUMOR"]
    elif mutation == "RESPONSE_REQUIRED_FACT_MISSING":
        next(rc for rc in o["ResponseConcept"] if rc["response_concept_id"] == "RC-NEWCOMER")["required_fact_refs"].append("FACT-CULPRIT-PLAYER-A")
    elif mutation == "PRIVATE_COMMENTARY_BECOMES_AUDIBLE":
        p["player_realization"]["audible"] = True
    elif mutation == "AUDIBLE_LOW_RISK_WITHOUT_POLICY":
        p["player_realization"].update({"mode": "AUTHORIZED_LOW_RISK_DIEGETIC_BARK", "audible": True, "world_event_created": True})
        o["PlayerAutoExpressionPolicy"][0]["authorized_low_risk_bark_enabled"] = False
    elif mutation == "HIGH_RISK_AUTO_SPEECH":
        p["player_realization"].update({"mode": "AUTHORIZED_LOW_RISK_DIEGETIC_BARK", "risk_class": "R3_HIGH_IMPACT", "audible": True, "world_event_created": True, "explicit_player_intent_ref": None})
    elif mutation == "DUPLICATE_NOVELTY_FIRES":
        p["echo_history"]["seen_novelty_keys"].append("DOOR-CALLBACK:NPC-WITNESS:V1")
    elif mutation == "EXPIRED_ECHO_FIRES":
        p["world_history"]["current_world_time"] = 999
    elif mutation == "BUDGET_SUPPRESSED_BUT_FIRES":
        p["commentary_budget"]["suppressed_echo_ids"].append("ECHO-WITNESS")
    elif mutation == "RENDERER_INVENTS_CULPRIT":
        p["downstream_presentation_probe"]["invented_fact_refs"].append("FACT-CULPRIT-PLAYER-A")
    elif mutation == "SUMMARY_MINTS_MEMORY":
        p["generated_summary_probe"]["claims_memory_authority"] = True
    elif mutation == "NO_DELTA_BUT_ECHO":
        p["environmental_delta"]["exists"] = False
    else:
        raise AssertionError(f"UNKNOWN_MUTATION:{mutation}")


def test_eval_binds_exact_parent_and_existing_authority_profiles():
    parent = load_json(PARENT_PATH)
    doc = load_json(EVAL_PATH)
    assert doc["canonical_parent"] == {
        "contract_id": parent["contract_id"],
        "contract_version": parent["contract_version"],
        "authority_graph_version": parent["authority_graph_version"],
    }
    assert set(doc["required_parent_type_bindings"]) == REQUIRED_PARENT_TYPES
    for name, expected in doc["required_parent_type_bindings"].items():
        actual = parent["type_registry"][name]
        assert actual["type_id"] == expected["type_id"]
        assert actual["version"] == expected["version"]
        assert actual["authority_profile_ref"] == expected["authority_profile_ref"]


def test_parent_frozen_invariants_are_present():
    parent = load_json(PARENT_PATH)
    af_e = set(parent["freeze_domains"]["AF-E"]["invariants"])
    af_g = set(parent["freeze_domains"]["AF-G"]["invariants"])
    assert "RECIPIENT_PROJECTION_CANNOT_CREATE_ACQUISITION_EVIDENCE" in af_e
    assert "PX_CANNOT_INVENT_FACTS_OR_INJECT_KNOWLEDGE" in af_g
    assert "COMMENTARY_REQUIRES_PROVENANCE_AND_ANTI_REPEAT_POLICY" in af_g


def test_fixture_canonical_objects_use_only_parent_fields():
    parent = load_json(PARENT_PATH)
    doc = load_json(EVAL_PATH)
    for type_name, items in doc["synthetic_fixture"]["canonical_objects"].items():
        allowed = set(parent["type_registry"][type_name]["fields"])
        for item in items:
            assert set(item) <= allowed, (type_name, sorted(set(item) - allowed))


def test_eval_only_constructs_cannot_mint_canonical_types():
    parent = load_json(PARENT_PATH)
    doc = load_json(EVAL_PATH)
    boundary = doc["authority_boundary"]
    assert boundary["does_not_register_new_canonical_types"] is True
    assert boundary["does_not_modify_parent_contract"] is True
    assert boundary["fixture_only_semantics"].startswith("NONCANONICAL_EVAL_ONLY")
    assert set(boundary["fixture_only_constructs"]).isdisjoint(parent["type_registry"])

    def walk(value):
        if isinstance(value, dict):
            if "construct" in value:
                assert value.get("authority") == "NONCANONICAL_EVAL_ONLY"
            for child in value.values():
                walk(child)
        elif isinstance(value, list):
            for child in value:
                walk(child)

    walk(doc["synthetic_fixture"]["eval_only_projections"])


def test_base_broken_door_world_echo_fixture_conforms():
    assert _validate(load_json(EVAL_PATH)) is None


def test_same_world_fact_produces_three_epistemically_distinct_valid_reactions():
    doc = load_json(EVAL_PATH)
    p = doc["synthetic_fixture"]["eval_only_projections"]
    attrs = _projection_by(p["attributions"], "speaker_id")
    assert attrs["NPC-WITNESS"]["kind"] == "WITNESSED_CAUSE"
    assert attrs["NPC-RUMOR"]["kind"] == "RUMORED_CAUSE"
    assert attrs["NPC-NEWCOMER"]["kind"] == "UNKNOWN_CAUSE"
    assert attrs["NPC-WITNESS"]["certainty"] == "DIRECT"
    assert attrs["NPC-RUMOR"]["certainty"] == "HEDGED"
    assert attrs["NPC-NEWCOMER"]["certainty"] == "UNKNOWN"
    assert _validate(doc) is None


def test_private_player_commentary_is_not_world_speech():
    probe = load_json(EVAL_PATH)["synthetic_fixture"]["eval_only_projections"]["player_realization"]
    assert probe["mode"] == "PRIVATE_INNER_COMMENTARY"
    assert probe["audible"] is False
    assert probe["world_event_created"] is False


@pytest.mark.parametrize("case", load_json(EVAL_PATH)["adversarial_cases"], ids=lambda c: c["case_id"])
def test_adversarial_world_echo_cases(case):
    doc = load_json(EVAL_PATH)
    _mutate(doc, case["mutation"])
    assert _validate(doc) == case["expected_error"]


def test_case_family_is_complete_and_unique():
    cases = load_json(EVAL_PATH)["adversarial_cases"]
    ids = [case["case_id"] for case in cases]
    assert len(ids) == len(set(ids))
    assert len(ids) >= 25
    required = {
        "OMNISCIENT_CULPRIT_LEAK", "MISSING_PERCEPTION_FOR_WITNESS",
        "CROSS_NPC_MEMORY_LEAK", "RUMOR_UPGRADED_TO_DIRECT",
        "RUMOR_UNHEDGED_CLAIM", "NEWCOMER_NAMES_CULPRIT",
        "MEMORY_NPC_ID_DRIFT", "MEMORY_SOURCE_PERCEPTION_UNKNOWN",
        "BELIEF_SUPPORT_UNKNOWN", "CORRECTION_ERASES_RUMOR_HISTORY",
        "RELATIONSHIP_MINTS_MEMORY", "FORBIDDEN_HIDDEN_FACT_DISCLOSED",
        "ECHO_SOURCE_DELTA_DRIFT", "ECHO_SPEAKER_ATTRIBUTION_MISMATCH",
        "RESPONSE_REQUIRED_FACT_MISSING", "PRIVATE_COMMENTARY_BECOMES_AUDIBLE",
        "AUDIBLE_LOW_RISK_WITHOUT_POLICY", "HIGH_RISK_AUTO_SPEECH",
        "DUPLICATE_NOVELTY_FIRES", "EXPIRED_ECHO_FIRES",
        "BUDGET_SUPPRESSED_BUT_FIRES", "RENDERER_INVENTS_CULPRIT",
        "SUMMARY_MINTS_MEMORY", "NO_DELTA_BUT_ECHO",
    }
    assert required <= {case["mutation"] for case in cases}


def test_no_runtime_llm_or_persistence_authority_is_granted():
    doc = load_json(EVAL_PATH)
    serialized = json.dumps(doc, ensure_ascii=False).lower()
    assert doc["status"] == "EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY_NOT_AUTHORITY_EXTENSION"
    for forbidden in ("runtime_implementation_authorized", "sqlite", "postgres", "redis", "openai_api", "anthropic_api"):
        assert forbidden not in serialized
