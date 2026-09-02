import importlib.util
import json
import sys
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
MODULE_PATH = ROOT / "evals" / "mids_world_design_discovery_adapter.py"
spec = importlib.util.spec_from_file_location("mids_adapter", MODULE_PATH)
m = importlib.util.module_from_spec(spec)
assert spec and spec.loader
sys.modules[spec.name] = m
spec.loader.exec_module(m)


def _option(option_id, text, material_key="", effects=(), dimensions=("decision_axis",)):
    return m.DesignOption(
        option_id,
        text,
        m.OriginClass.AI,
        material_key,
        tuple(dimensions),
        tuple(effects),
    )


class MIDSWorldDesignDiscoveryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = m.MIDSWorldDesignDiscoveryAdapter(question_budget=3)

    def _case(self, index=0):
        data = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        return m.ReplayDiscoveryCase(**data["cases"][index])

    def test_tacit_candidate_requires_trusted_subject_bound_user_evidence(self):
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            self.adapter.promote_tacit_candidate("TACIT-1", "USER:turn-9")
        with self.assertRaisesRegex(ValueError, "SUBJECT_MISMATCH"):
            self.adapter.promote_tacit_candidate("OTHER", "UE-TACIT-TACIT-1")
        decision = self.adapter.promote_tacit_candidate("TACIT-1", "UE-TACIT-TACIT-1")
        self.assertEqual(decision.origin, m.OriginClass.USER)
        self.assertEqual(decision.user_evidence_receipt_id, "UE-TACIT-TACIT-1")

    def test_ai_option_requires_trusted_acceptance_receipt_not_user_looking_string(self):
        option = _option("O1", "candidate")
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            self.adapter.accept_ai_option(option, "USER:turn-10")
        with self.assertRaisesRegex(ValueError, "SUBJECT_MISMATCH"):
            other = _option("O2", "other")
            self.adapter.accept_ai_option(other, "UE-ACCEPT-O1")
        decision = self.adapter.accept_ai_option(option, "UE-ACCEPT-O1")
        self.assertEqual(option.origin, m.OriginClass.AI)
        self.assertEqual(decision.origin, m.OriginClass.USER)

    def test_manually_constructed_user_receipt_cannot_enter_trusted_ledger(self):
        forged = m.UserEvidenceReceipt(
            "UE-FORGED",
            "USER_MESSAGE:fake",
            "ACCEPT_AI_OPTION",
            "O1",
            "AI_OPTION_ACCEPTANCE",
            m.BOUND_CANONICAL_CONTEXT_ID,
        )
        self.assertEqual(forged.issuer, "UPSTREAM_USER_INTERACTION_AUTHORITY")
        option = _option("O1", "candidate")
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            self.adapter.accept_ai_option(option, forged.receipt_id)

    def test_user_explicit_classification_requires_purpose_subject_question_and_statement_binding(self):
        statement = m._CLASSIFY_STATEMENT
        state = self.adapter.classify_epistemic_state(
            m.OriginClass.USER,
            "UE-CLASSIFY-EXAMPLE",
            subject_ref="CLASSIFY-EXAMPLE",
            question_ref="Q-CLASSIFY-EXAMPLE",
            statement=statement,
        )
        self.assertEqual(state, m.EpistemicState.USER_EXPLICIT_CONFIRMED)

        attacks = [
            {"receipt": "UE-QOC-A", "subject": "A", "question": "Q", "statement": statement, "error": "ACTION_MISMATCH"},
            {"receipt": "UE-CLASSIFY-EXAMPLE", "subject": "OTHER", "question": "Q-CLASSIFY-EXAMPLE", "statement": statement, "error": "SUBJECT_MISMATCH"},
            {"receipt": "UE-CLASSIFY-EXAMPLE", "subject": "CLASSIFY-EXAMPLE", "question": "OTHER", "statement": statement, "error": "QUESTION_MISMATCH"},
            {"receipt": "UE-CLASSIFY-EXAMPLE", "subject": "CLASSIFY-EXAMPLE", "question": "Q-CLASSIFY-EXAMPLE", "statement": "different statement", "error": "STATEMENT_MISMATCH"},
        ]
        for attack in attacks:
            with self.subTest(attack=attack):
                with self.assertRaisesRegex(ValueError, attack["error"]):
                    self.adapter.classify_epistemic_state(
                        m.OriginClass.USER,
                        attack["receipt"],
                        subject_ref=attack["subject"],
                        question_ref=attack["question"],
                        statement=attack["statement"],
                    )

    def test_user_explicit_classification_without_bound_context_fails_closed(self):
        with self.assertRaisesRegex(ValueError, "REQUIRES_BOUND_EVIDENCE_CONTEXT"):
            self.adapter.classify_epistemic_state(m.OriginClass.USER, "UE-CLASSIFY-EXAMPLE")

    def test_expert_blind_zone_translates_jargon(self):
        q = m.DiscoveryQuestion(
            "Q", "multiplicative modifier?", 5, 5, 5, 5,
            technical_jargon=True,
            scenario_translation="Should leg injury destroy footwork while preserving stationary parry?",
        )
        self.assertNotIn("multiplicative", q.user_prompt())
        bad = m.DiscoveryQuestion("B", "multiplicative modifier?", 5, 5, 5, 5, technical_jargon=True)
        with self.assertRaises(ValueError):
            bad.user_prompt()

    def test_question_budget_never_exceeds_three(self):
        questions = [m.DiscoveryQuestion(str(i), f"q{i}", 5, 5, 5, 5) for i in range(10)]
        self.assertEqual(len(self.adapter.select_questions(questions)), 3)

    def test_authority_risk_outranks_cosmetic_preference(self):
        authority = m.DiscoveryQuestion("authority", "truth?", 5, 4, 5, 5)
        cosmetic = m.DiscoveryQuestion("cosmetic", "color?", 2, 5, 1, 0)
        selected = self.adapter.select_questions([cosmetic, authority])
        self.assertEqual(selected[0].question_id, "authority")

    def test_caller_labels_cannot_mint_material_distinctness(self):
        options = [
            _option("FORGED-A", "Same design", "key-a", ["effect a"], ("axis-a",)),
            _option("FORGED-B", "Same design", "key-b", ["opposite claimed effect"], ("axis-b",)),
        ]
        self.assertEqual(
            self.adapter.material_distinctness_state(options),
            m.MaterialDistinctnessState.UNKNOWN,
        )
        self.assertFalse(self.adapter.materially_distinct_options(options))

    def test_trusted_semantic_receipts_prove_fixture_option_distinctness(self):
        options = [
            _option("O-R1-LOCAL", "Function-local impairment preserves unaffected skills.", "forged-key", ["forged"], ("forged",)),
            _option("O-R1-GLOBAL", "Global penalty degrades most combat output.", "same-key", ["same forged"], ("same",)),
        ]
        self.assertEqual(
            self.adapter.material_distinctness_state(options),
            m.MaterialDistinctnessState.DISTINCT,
        )
        self.assertTrue(self.adapter.materially_distinct_options(options))

    def test_known_option_id_with_mutated_text_cannot_reuse_semantic_receipt(self):
        options = [
            _option("O-R1-LOCAL", "Global penalty degrades most combat output."),
            _option("O-R1-GLOBAL", "Global penalty degrades most combat output."),
        ]
        self.assertEqual(
            self.adapter.material_distinctness_state(options),
            m.MaterialDistinctnessState.UNKNOWN,
        )
        self.assertFalse(self.adapter.materially_distinct_options(options))

    def test_cross_scope_semantic_receipts_cannot_be_compared_as_one_choice(self):
        options = [
            _option("O-R1-LOCAL", "Function-local impairment preserves unaffected skills."),
            _option("O-R2-CHANNEL", "Require a real source/channel/carrier/perception path."),
        ]
        self.assertEqual(
            self.adapter.material_distinctness_state(options),
            m.MaterialDistinctnessState.UNKNOWN,
        )

    def test_superseded_decision_history_requires_trusted_evidence_and_remains_queryable(self):
        q = m.DiscoveryQuestion("Q", "choice", 5, 5, 5, 5)
        record = m.QOCRecord(q)
        forged = m.DiscoveryDecision("DX", "Q", "A", m.OriginClass.USER, "USER:fake")
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            record.add_decision(forged)
        d1 = m.DiscoveryDecision("D1", "Q", "A", m.OriginClass.USER, "UE-QOC-A")
        d2 = m.DiscoveryDecision("D2", "Q", "B", m.OriginClass.USER, "UE-QOC-B")
        record.add_decision(d1)
        record.add_decision(d2)
        self.assertEqual(len(record.decisions), 2)
        self.assertFalse(record.decisions[0].effective)
        self.assertEqual(record.decisions[0].superseded_by, "D2")
        self.assertEqual(record.current_decision().decision_id, "D2")

    def test_candidate_packet_is_candidate_only_and_has_no_mutator_api(self):
        case = self._case()
        packet = self.adapter.compile_candidate_packet(case, ["world truth remains authoritative"], [], [])
        self.assertEqual(packet.authority, "CANDIDATE_ONLY / REQUIRES_ARCHITECTURE_RESOLUTION")
        self.assertTrue(any(m.BOUND_CANONICAL_CONTEXT_ID in ref for ref in packet.provenance_refs))
        forbidden = [
            name for name in dir(self.adapter)
            if name.startswith(("write_", "mutate_", "register_", "apply_canonical"))
        ]
        self.assertEqual(forbidden, [])

    def test_canonical_reconciliation_is_fixed_snapshot_not_equal_caller_strings(self):
        self.assertEqual(self.adapter.canonical_snapshot_id, m.BOUND_CANONICAL_CONTEXT_ID)
        with self.assertRaises(m.ReconciliationRequired):
            m.MIDSWorldDesignDiscoveryAdapter(canonical_snapshot_id="same-arbitrary-value")
        with self.assertRaises(m.ReconciliationRequired):
            m.MIDSWorldDesignDiscoveryAdapter(canonical_snapshot_id="stale")

    def test_discovery_input_has_no_hidden_expected_field(self):
        case = self._case()
        captured = []

        def generator(discovery_input):
            captured.append(discovery_input)
            self.assertFalse(hasattr(discovery_input, "expected_discoveries"))
            self.assertFalse(hasattr(discovery_input, "final_resolution"))
            return ["derived only from visible discovery input"]

        self.adapter.evaluate_replay_case(case, discovery_generator=generator)
        self.assertEqual(len(captured), 1)

    def test_empty_and_wrong_discovery_output_cannot_receive_full_credit(self):
        case = self._case(1)
        empty = self.adapter.evaluate_replay_case(case, discovery_generator=lambda _: [])
        wrong = self.adapter.evaluate_replay_case(
            case,
            discovery_generator=lambda _: ["camera lens color and soundtrack tempo"],
        )
        self.assertEqual(empty["critical_unknowns_discovered_before_implementation"], 0)
        self.assertEqual(empty["hidden_answer_coverage"], 0.0)
        self.assertEqual(wrong["critical_unknowns_discovered_before_implementation"], 0)
        self.assertEqual(wrong["hidden_answer_coverage"], 0.0)

    def test_generated_candidate_packet_contains_generator_output_not_expected_answers(self):
        case = self._case(2)
        generated = ["GENERATED_SENTINEL: event evidence outranks cache"]
        result = self.adapter.evaluate_replay_case(case, discovery_generator=lambda _: generated)
        packet_discoveries = result["candidate_packet"]["behavioral_contract_candidate"]
        self.assertEqual(packet_discoveries, generated)
        self.assertNotEqual(packet_discoveries, case.expected_discoveries)

    def test_reference_generator_uses_trusted_semantics_not_caller_labels(self):
        case = self._case(0)
        poisoned = []
        for raw in case.options:
            mutated = dict(raw)
            mutated["material_key"] = "forged"
            mutated["decision_dimensions"] = ["forged-dimension"]
            mutated["material_effects"] = ["forged-effect"]
            poisoned.append(mutated)
        case = m.ReplayDiscoveryCase(
            case.case_id,
            case.family,
            case.user_input,
            case.allowed_context,
            case.questions,
            poisoned,
            case.expected_discoveries,
            case.open_decision_refs,
            case.contract_refs,
        )
        result = self.adapter.evaluate_replay_case(case)
        self.assertEqual(result["material_distinctness_state"], "DISTINCT")
        generated = result["candidate_packet"]["behavioral_contract_candidate"]
        self.assertFalse(any("forged-effect" in line or "forged-dimension" in line for line in generated))

    def test_reference_generator_runs_without_provider_and_scores_after_generation(self):
        case = self._case(4)
        result = self.adapter.evaluate_replay_case(case)
        self.assertGreater(result["generated_discovery_count"], 0)
        self.assertGreaterEqual(result["hidden_answer_coverage"], 0.0)
        self.assertLessEqual(result["hidden_answer_coverage"], 1.0)
        self.assertEqual(result["provider_call_count"], 0)
        self.assertEqual(result["world_mutation_count"], 0)

    def test_open_decision_refs_traceable_not_resolved(self):
        case = self._case()
        packet = self.adapter.compile_candidate_packet(case, ["generated candidate"], [], [])
        self.assertEqual(packet.related_open_decision_refs, case.open_decision_refs)
        self.assertFalse(any("RESOLVED" in ref for ref in packet.related_open_decision_refs))

    def test_golden_output_never_claims_canonical_registration(self):
        case = self._case()
        packet = self.adapter.compile_candidate_packet(case, ["generated candidate"], [], [])
        self.assertEqual(packet.golden_scenario_candidate["status"], "GOLDEN_SCENARIO_CANDIDATE")

    def test_provider_network_and_world_mutation_counts_stay_zero(self):
        raw = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        cases = [m.ReplayDiscoveryCase(**case) for case in raw["cases"]]
        result = self.adapter.evaluate_replay_suite(cases)
        self.assertEqual(result["provider_call_count"], 0)
        self.assertEqual(result["world_mutation_count"], 0)
        self.assertEqual(result["false_canonicalization_count"], 0)
        self.assertTrue(result["all_question_budgets_respected"])

    def test_six_replay_families_are_present(self):
        raw = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        families = {case["family"] for case in raw["cases"]}
        self.assertEqual(
            families,
            {
                "capability_functional_impairment",
                "knowledge_information_delivery",
                "persistence_restart",
                "hostile_player_narrative",
                "possession_inventory_single_source",
                "presentation_cross_plane_integrity",
            },
        )


if __name__ == "__main__":
    unittest.main()
