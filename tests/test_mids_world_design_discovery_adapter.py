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


def _option(option_id, text, material_key, effects, dimensions=("decision_axis",)):
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
        option = _option("O1", "candidate", "candidate-a", ["effect a"])
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            self.adapter.accept_ai_option(option, "USER:turn-10")
        with self.assertRaisesRegex(ValueError, "SUBJECT_MISMATCH"):
            other = _option("O2", "other", "candidate-b", ["effect b"])
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
        option = _option("O1", "candidate", "candidate-a", ["effect a"])
        with self.assertRaisesRegex(ValueError, "TRUSTED_UPSTREAM_LEDGER"):
            self.adapter.accept_ai_option(option, forged.receipt_id)

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

    def test_material_key_cannot_mint_distinctness_for_semantically_equal_effects(self):
        options = [
            _option("A", "Use strict provenance", "key-a", ["source provenance required"]),
            _option("B", "Use very strict provenance", "totally-different-key", ["source provenance required"]),
        ]
        self.assertFalse(self.adapter.materially_distinct_options(options))

    def test_material_distinctness_uses_normalized_effects_and_dimensions(self):
        options = [
            _option("A", "Local", "same-key", ["local impairment preserves unaffected skill"], ("impairment_scope",)),
            _option("B", "Global", "same-key", ["global impairment degrades unaffected skill"], ("impairment_scope",)),
        ]
        self.assertTrue(self.adapter.materially_distinct_options(options))
        fake_variants = [
            _option("C", "Strict", "x", ["strict source provenance required"], ("authority",)),
            _option("D", "Very strict", "y", ["very strict source provenance required"], ("authority",)),
        ]
        self.assertFalse(self.adapter.materially_distinct_options(fake_variants))

    def test_material_option_without_consequence_model_fails_closed(self):
        incomplete = m.DesignOption("A", "x", m.OriginClass.AI, "fake-key")
        with self.assertRaisesRegex(ValueError, "DECISION_DIMENSIONS_AND_EFFECTS"):
            self.adapter.materially_distinct_options([incomplete])

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
        self.assertIn(m.BOUND_CANONICAL_CONTEXT_ID, packet.provenance_refs[-1])
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
