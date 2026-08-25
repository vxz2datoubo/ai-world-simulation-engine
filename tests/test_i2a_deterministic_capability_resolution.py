from runtime.awrse.capability_resolution import resolve_capability


def test_i2a_resolution_order_is_deterministic():
    result = resolve_capability(
        base_attribute_map={"strength": 5},
        skill_values={"climb": 3},
        difficulty_or_resistance=6,
        required_attributes=("strength",),
        required_skills=("climb",),
        provenance={"profile_schema_ref": "AF-C-v1.1", "ruleset_family_ref": "SMALL_CORE_V1"},
    )

    assert result.feasible is True
    assert result.effective_capability == 8
    assert result.margin == 2


def test_i2a_hard_feasibility_precedes_margin():
    result = resolve_capability(
        base_attribute_map={},
        skill_values={"climb": 100},
        difficulty_or_resistance=1,
        required_attributes=("strength",),
        provenance={"profile_schema_ref": "AF-C-v1.1", "ruleset_family_ref": "SMALL_CORE_V1"},
    )

    assert result.feasible is False
    assert result.effective_capability is None
    assert result.margin is None
