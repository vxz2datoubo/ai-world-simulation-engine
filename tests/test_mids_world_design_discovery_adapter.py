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


class MIDSWorldDesignDiscoveryAdapterTests(unittest.TestCase):
    def setUp(self):
        self.adapter = m.MIDSWorldDesignDiscoveryAdapter("base", "base", question_budget=3)

    def test_tacit_candidate_requires_explicit_user_evidence(self):
        with self.assertRaises(ValueError):
            self.adapter.promote_tacit_candidate("TACIT-1", None)
        decision = self.adapter.promote_tacit_candidate("TACIT-1", "USER:turn-9")
        self.assertEqual(decision.origin, m.OriginClass.USER)

    def test_ai_option_requires_explicit_acceptance_and_preserves_ai_origin_on_option(self):
        option = m.DesignOption("O1", "candidate", m.OriginClass.AI, "candidate-a")
        with self.assertRaises(ValueError):
            self.adapter.accept_ai_option(option, None)
        decision = self.adapter.accept_ai_option(option, "USER:turn-10")
        self.assertEqual(option.origin, m.OriginClass.AI)
        self.assertEqual(decision.origin, m.OriginClass.USER)

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

    def test_fake_wording_variants_do_not_count_as_material_alternatives(self):
        options = [
            m.DesignOption("A", "Use strict provenance", m.OriginClass.AI, "strict-provenance"),
            m.DesignOption("B", "Use very strict provenance", m.OriginClass.AI, "strict-provenance"),
        ]
        self.assertFalse(self.adapter.materially_distinct_options(options))

    def test_superseded_decision_history_remains_queryable(self):
        q = m.DiscoveryQuestion("Q", "choice", 5, 5, 5, 5)
        record = m.QOCRecord(q)
        d1 = m.DiscoveryDecision("D1", "Q", "A", m.OriginClass.USER, "USER:1")
        d2 = m.DiscoveryDecision("D2", "Q", "B", m.OriginClass.USER, "USER:2")
        record.add_decision(d1)
        record.add_decision(d2)
        self.assertEqual(len(record.decisions), 2)
        self.assertFalse(record.decisions[0].effective)
        self.assertEqual(record.decisions[0].superseded_by, "D2")
        self.assertEqual(record.current_decision().decision_id, "D2")

    def test_candidate_packet_is_candidate_only_and_has_no_mutator_api(self):
        data = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        case = m.ReplayDiscoveryCase(**data["cases"][0])
        packet = self.adapter.compile_candidate_packet(case, ["world truth remains authoritative"], [], [])
        self.assertEqual(packet.authority, "CANDIDATE_ONLY / REQUIRES_ARCHITECTURE_RESOLUTION")
        forbidden = [
            name for name in dir(self.adapter)
            if name.startswith(("write_", "mutate_", "register_", "apply_canonical"))
        ]
        self.assertEqual(forbidden, [])

    def test_stale_context_fails_closed(self):
        stale = m.MIDSWorldDesignDiscoveryAdapter("expected", "stale")
        with self.assertRaises(m.ReconciliationRequired):
            stale.select_questions([m.DiscoveryQuestion("Q", "x", 1, 1, 1, 1)])

    def test_hidden_expected_data_not_in_discovery_input(self):
        raw = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        for case in raw["cases"]:
            discovery_keys = {"case_id", "family", "user_input", "allowed_context", "questions", "options"}
            projected = {k: case[k] for k in discovery_keys}
            self.assertNotIn("expected_discoveries", projected)
            self.assertNotIn("final_resolution", projected)

    def test_open_decision_refs_traceable_not_resolved(self):
        raw = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        case = m.ReplayDiscoveryCase(**raw["cases"][0])
        packet = self.adapter.compile_candidate_packet(case, case.expected_discoveries, [], [])
        self.assertEqual(packet.related_open_decision_refs, case.open_decision_refs)
        self.assertFalse(any("RESOLVED" in ref for ref in packet.related_open_decision_refs))

    def test_golden_output_never_claims_canonical_registration(self):
        raw = json.loads((ROOT / "evals" / "MIDS-WORLD-DESIGN-DISCOVERY-REPLAY-CASES.json").read_text())
        case = m.ReplayDiscoveryCase(**raw["cases"][0])
        packet = self.adapter.compile_candidate_packet(case, case.expected_discoveries, [], [])
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
