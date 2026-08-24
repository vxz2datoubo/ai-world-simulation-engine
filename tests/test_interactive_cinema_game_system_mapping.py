from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "INTERACTIVE-CINEMA-GAME-SYSTEM-MAPPING-SKILL.yaml"
MAP = ROOT / "docs" / "research" / "INTERACTIVE-CINEMA-GAME-SYSTEM-MAP.md"
HANDOFF = ROOT / "AI_HANDOFF.yaml"


def test_mapping_skill_keeps_knowledge_lenses_and_authority_boundaries_explicit():
    content = SKILL.read_text(encoding="utf-8")

    for marker in (
        "K0_USER_EXPLICIT:",
        "K1_EVIDENCE_DERIVED:",
        "K2_ACCESSIBLE_DOMAIN_MODEL:",
        "K3_MATERIAL_UNKNOWN:",
        "WORLD_MODEL_SYSTEM:",
        "AI_FILM_SYSTEM:",
        "SECOND_BRAIN_SYSTEM:",
        "RENDERER_PROVIDER:",
        "DIRECTOR-BEAT-PACKET",
    ):
        assert marker in content

    assert "cannot amend canonical history" in content
    assert "Does not grant I2 or any other runtime implementation authority" in content


def test_mapping_skill_covers_all_required_system_handoffs_and_release_checks():
    content = SKILL.read_text(encoding="utf-8")

    for module in (
        "M01_WORLD_TRUTH",
        "M02_PLAYER_FREEDOM_AND_RESOLUTION",
        "M03_CAPABILITY_INJURY",
        "M04_PERCEPTION_MEMORY_RELATIONSHIP",
        "M05_INTERACTIVE_NARRATIVE",
        "M06_EXPERIENCE_AND_OPPORTUNITY",
        "M07_ASSET_SPACE_CONTINUITY",
        "M08_DIRECTOR_HANDOFF",
        "M09_RENDER_AND_PUBLICATION",
        "M10_EVALUATION_AND_LEARNING",
    ):
        assert module in content

    assert "CAPABILITY-ARCH-RESOLUTION-001 / PR-29" in content
    assert "KEEP_ATTR_OPEN and KEEP_MATH_OPEN" in content
    assert "separately reviewed bounded exemption" in content
    assert "I2_CAPABILITY_FEASIBILITY_REFERENCE" in content
    assert "DIRECTOR_PACKET_REFERENCE_LOOP" in content
    assert "OWASP LLM Prompt Injection and AI Agent Security cheat sheets" in content


def test_research_map_teaches_project_status_without_claiming_provider_or_runtime_success():
    content = MAP.read_text(encoding="utf-8")

    assert "CANDIDATE_RESEARCH_MAPPING / NOT_RUNTIME_AUTHORIZATION" in content
    assert "What already runs, what is only designed" in content
    assert "PR #29 still requires changes" in content
    assert "A historical lifecycle label is not an exemption" in content
    assert "not a product capability claim" in content
    assert "K1 never silently becomes K0" in content
    assert "A renderer cannot send pixels" in content
    assert "back to mutate the world" in content
    assert "Canonical event history ----> replayable world state" in content
    assert "SIMA" in content
    assert "OWASP prompt-injection guidance" in content


def test_mapping_handoff_preserves_the_required_independent_review_chain():
    content = HANDOFF.read_text(encoding="utf-8")

    for marker in (
        "agent_id: CODEX",
        "source_agent: CODEX",
        "target_agent: GPT_INDEPENDENT_REVIEWER",
        "reviewer: GPT_INDEPENDENT_REVIEWER_REQUIRED",
        "handoff_status: READY_FOR_INDEPENDENT_REVIEW",
        "runtime_authority: NOT_GRANTED",
        "merge_authority: NOT_GRANTED",
        "independent_review_required: true",
    ):
        assert marker in content
