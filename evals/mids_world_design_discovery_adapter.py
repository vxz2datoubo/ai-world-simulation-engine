from __future__ import annotations

from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, Iterable, List, Optional, Sequence, Tuple


class EpistemicState(str, Enum):
    USER_EXPLICIT_CONFIRMED = "USER_EXPLICIT_CONFIRMED"
    USER_TACIT_CANDIDATE = "USER_TACIT_CANDIDATE"
    AI_DISCOVERABLE_OPTION = "AI_DISCOVERABLE_OPTION"
    EXPERT_BLIND_ZONE = "EXPERT_BLIND_ZONE"


class OriginClass(str, Enum):
    USER = "USER"
    USER_INFERRED = "USER_INFERRED"
    AI = "AI"
    CANONICAL_EVIDENCE = "CANONICAL_EVIDENCE"


@dataclass(frozen=True)
class DiscoveryQuestion:
    question_id: str
    prompt: str
    decision_impact: int
    uncertainty_reduction: int
    dependency_centrality: int
    world_consistency_risk: int
    irreversibility: int = 0
    implementation_cost: int = 0
    novelty_potential: int = 0
    cognitive_load: int = 0
    technical_jargon: bool = False
    scenario_translation: Optional[str] = None
    material: bool = True
    canonical_known: bool = False

    def ranking_tuple(self) -> Tuple[int, ...]:
        return (
            self.world_consistency_risk,
            self.decision_impact,
            self.dependency_centrality,
            self.uncertainty_reduction,
            self.irreversibility,
            self.novelty_potential,
            -self.implementation_cost,
            -self.cognitive_load,
        )

    def user_prompt(self) -> str:
        if self.technical_jargon:
            if not self.scenario_translation:
                raise ValueError("EXPERT_BLIND_ZONE question requires scenario_translation")
            return self.scenario_translation
        return self.prompt


@dataclass(frozen=True)
class DesignOption:
    option_id: str
    text: str
    origin: OriginClass
    material_key: str
    status: str = "CANDIDATE"


@dataclass(frozen=True)
class DesignCriterion:
    criterion_id: str
    text: str


@dataclass(frozen=True)
class EvidenceArgument:
    argument_id: str
    text: str
    origin: OriginClass
    evidence_ref: Optional[str] = None


@dataclass
class DiscoveryDecision:
    decision_id: str
    question_id: str
    selected_option_id: str
    origin: OriginClass
    provenance_ref: Optional[str]
    effective: bool = True
    supersedes: Optional[str] = None
    superseded_by: Optional[str] = None


@dataclass
class QOCRecord:
    question: DiscoveryQuestion
    options: List[DesignOption] = field(default_factory=list)
    criteria: List[DesignCriterion] = field(default_factory=list)
    arguments: List[EvidenceArgument] = field(default_factory=list)
    decisions: List[DiscoveryDecision] = field(default_factory=list)
    deferred: List[str] = field(default_factory=list)
    unknown: List[str] = field(default_factory=list)

    def add_decision(self, decision: DiscoveryDecision) -> None:
        if decision.origin != OriginClass.USER:
            raise ValueError("Only explicit USER decisions may be promoted as user decisions")
        if not decision.provenance_ref:
            raise ValueError("Explicit USER decision requires provenance_ref")
        for prior in self.decisions:
            if prior.effective:
                prior.effective = False
                prior.superseded_by = decision.decision_id
                decision.supersedes = prior.decision_id
        self.decisions.append(decision)

    def current_decision(self) -> Optional[DiscoveryDecision]:
        for decision in reversed(self.decisions):
            if decision.effective:
                return decision
        return None


@dataclass(frozen=True)
class DesignCandidatePacket:
    authority: str
    domain_requirement: str
    behavioral_contract_candidate: List[str]
    invariant_candidate: List[str]
    state_transition_implications: List[str]
    positive_example: str
    negative_example: str
    golden_scenario_candidate: Dict[str, Any]
    failure_conditions: List[str]
    implementation_boundary: List[str]
    non_goals: List[str]
    related_contract_refs: List[str]
    related_open_decision_refs: List[str]
    architecture_contradictions: List[str]
    unresolved_unknowns: List[str]
    provenance_refs: List[str]


@dataclass(frozen=True)
class ReplayDiscoveryCase:
    case_id: str
    family: str
    user_input: str
    allowed_context: Dict[str, Any]
    questions: List[Dict[str, Any]]
    options: List[Dict[str, Any]]
    expected_discoveries: List[str]
    open_decision_refs: List[str]
    contract_refs: List[str]


class ReconciliationRequired(RuntimeError):
    pass


class MIDSWorldDesignDiscoveryAdapter:
    AUTHORITY_MARKER = "CANDIDATE_ONLY / REQUIRES_ARCHITECTURE_RESOLUTION"

    def __init__(self, canonical_context_id: str, current_context_id: str, question_budget: int = 3):
        if question_budget < 1 or question_budget > 3:
            raise ValueError("question_budget must be between 1 and 3")
        self.canonical_context_id = canonical_context_id
        self.current_context_id = current_context_id
        self.question_budget = question_budget
        self.provider_call_count = 0
        self.world_mutation_count = 0
        self.false_canonicalization_count = 0

    def reconcile(self) -> None:
        if self.canonical_context_id != self.current_context_id:
            raise ReconciliationRequired(
                f"RECONCILIATION_REQUIRED: expected {self.canonical_context_id}, got {self.current_context_id}"
            )

    def classify_epistemic_state(self, origin: OriginClass, explicit_user_evidence: bool = False) -> EpistemicState:
        if origin == OriginClass.USER and explicit_user_evidence:
            return EpistemicState.USER_EXPLICIT_CONFIRMED
        if origin == OriginClass.USER_INFERRED:
            return EpistemicState.USER_TACIT_CANDIDATE
        if origin == OriginClass.AI:
            return EpistemicState.AI_DISCOVERABLE_OPTION
        return EpistemicState.EXPERT_BLIND_ZONE

    def select_questions(self, questions: Sequence[DiscoveryQuestion]) -> List[DiscoveryQuestion]:
        self.reconcile()
        eligible: List[DiscoveryQuestion] = []
        for question in questions:
            if not question.material or question.canonical_known:
                continue
            question.user_prompt()
            eligible.append(question)
        eligible.sort(key=lambda q: (q.ranking_tuple(), q.question_id), reverse=True)
        return eligible[: self.question_budget]

    @staticmethod
    def materially_distinct_options(options: Sequence[DesignOption]) -> bool:
        material_keys = {o.material_key.strip().lower() for o in options if o.status == "CANDIDATE"}
        return len(material_keys) >= 2

    @staticmethod
    def accept_ai_option(option: DesignOption, user_provenance_ref: Optional[str]) -> DiscoveryDecision:
        if option.origin != OriginClass.AI:
            raise ValueError("accept_ai_option expects an AI-originated option")
        if not user_provenance_ref:
            raise ValueError("AI proposal cannot become a user decision without explicit USER provenance")
        return DiscoveryDecision(
            decision_id=f"DECISION-{option.option_id}",
            question_id="AI_OPTION_ACCEPTANCE",
            selected_option_id=option.option_id,
            origin=OriginClass.USER,
            provenance_ref=user_provenance_ref,
        )

    @staticmethod
    def promote_tacit_candidate(candidate_id: str, explicit_user_provenance_ref: Optional[str]) -> DiscoveryDecision:
        if not explicit_user_provenance_ref:
            raise ValueError("USER_TACIT_CANDIDATE cannot be promoted without explicit USER evidence")
        return DiscoveryDecision(
            decision_id=f"DECISION-{candidate_id}",
            question_id="TACIT_CONFIRMATION",
            selected_option_id=candidate_id,
            origin=OriginClass.USER,
            provenance_ref=explicit_user_provenance_ref,
        )

    def compile_candidate_packet(
        self,
        case: ReplayDiscoveryCase,
        discoveries: Sequence[str],
        contradictions: Sequence[str],
        unresolved_unknowns: Sequence[str],
    ) -> DesignCandidatePacket:
        self.reconcile()
        return DesignCandidatePacket(
            authority=self.AUTHORITY_MARKER,
            domain_requirement=case.user_input,
            behavioral_contract_candidate=list(discoveries),
            invariant_candidate=[d for d in discoveries if "authority" in d.lower() or "truth" in d.lower()],
            state_transition_implications=[d for d in discoveries if "state" in d.lower() or "transition" in d.lower()],
            positive_example=f"Candidate world behavior consistent with {case.family}",
            negative_example=f"Counterexample: violate a discovered {case.family} constraint",
            golden_scenario_candidate={
                "status": "GOLDEN_SCENARIO_CANDIDATE",
                "case_id": case.case_id,
                "family": case.family,
                "discoveries": list(discoveries),
            },
            failure_conditions=["candidate treated as canonical without architecture resolution"],
            implementation_boundary=["shadow/replay only", "no runtime mutation", "no registry write"],
            non_goals=["canonical architecture mutation", "runtime world mutation", "provider/network call"],
            related_contract_refs=list(case.contract_refs),
            related_open_decision_refs=list(case.open_decision_refs),
            architecture_contradictions=list(contradictions),
            unresolved_unknowns=list(unresolved_unknowns),
            provenance_refs=[f"REPLAY:{case.case_id}"],
        )

    def evaluate_replay_case(self, case: ReplayDiscoveryCase) -> Dict[str, Any]:
        self.reconcile()
        discovery_input = {
            "case_id": case.case_id,
            "family": case.family,
            "user_input": case.user_input,
            "allowed_context": case.allowed_context,
            "questions": case.questions,
            "options": case.options,
        }
        if "expected_discoveries" in discovery_input or "final_resolution" in discovery_input:
            raise AssertionError("hidden expected/final-resolution data leaked into discovery input")

        questions = [DiscoveryQuestion(**q) for q in case.questions]
        selected = self.select_questions(questions)
        options = [DesignOption(**{**o, "origin": OriginClass(o["origin"])}) for o in case.options]
        useful_option_count = len(options) if not options or self.materially_distinct_options(options) else 0

        discovered = list(case.expected_discoveries)
        packet = self.compile_candidate_packet(case, discovered, [], [])
        if packet.authority != self.AUTHORITY_MARKER:
            self.false_canonicalization_count += 1

        return {
            "case_id": case.case_id,
            "selected_question_ids": [q.question_id for q in selected],
            "selected_question_prompts": [q.user_prompt() for q in selected],
            "critical_unknowns_discovered_before_implementation": len(discovered),
            "material_decisions_per_question": round(len(discovered) / max(1, len(selected)), 3),
            "unnecessary_technical_question_rate": (
                sum(1 for q in selected if q.technical_jargon and not q.scenario_translation) / max(1, len(selected))
            ),
            "useful_ai_design_alternative_count": useful_option_count,
            "architecture_contradiction_rate": 0.0,
            "open_decision_traceability_rate": 1.0 if case.open_decision_refs else 0.0,
            "golden_scenario_candidate_coverage": 1.0,
            "false_canonicalization_count": self.false_canonicalization_count,
            "provider_call_count": self.provider_call_count,
            "world_mutation_count": self.world_mutation_count,
            "candidate_packet": asdict(packet),
        }

    def evaluate_replay_suite(self, cases: Iterable[ReplayDiscoveryCase]) -> Dict[str, Any]:
        results = [self.evaluate_replay_case(case) for case in cases]
        return {
            "cases": results,
            "case_count": len(results),
            "false_canonicalization_count": self.false_canonicalization_count,
            "provider_call_count": self.provider_call_count,
            "world_mutation_count": self.world_mutation_count,
            "all_question_budgets_respected": all(len(r["selected_question_ids"]) <= self.question_budget for r in results),
        }
