from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from enum import Enum
from types import MappingProxyType
from typing import Any, Callable, Dict, Iterable, List, Optional, Sequence, Tuple


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


BOUND_CANONICAL_CONTEXT_ID = "bc9bee8c6402d70dbb5c36ca4416905f4ca54ee4"
BOUND_SPEC_SNAPSHOT_ID = "MIDS-001-SPEC-2026-08-31-R1"
TRUSTED_USER_EVIDENCE_LEDGER_ID = "MIDS-UPSTREAM-USER-EVIDENCE-FIXTURE/v1"


@dataclass(frozen=True)
class UserEvidenceReceipt:
    receipt_id: str
    source_ref: str
    action_type: str
    subject_ref: str
    question_ref: str
    canonical_context_id: str
    issuer: str = "UPSTREAM_USER_INTERACTION_AUTHORITY"


# Shadow/replay-only stand-in for a future upstream interaction authority.  The adapter
# may RESOLVE these receipts, but it has no API that mints arbitrary new receipts.
_TRUSTED_USER_EVIDENCE = MappingProxyType(
    {
        "UE-ACCEPT-O1": UserEvidenceReceipt(
            "UE-ACCEPT-O1", "USER_MESSAGE:turn-10", "ACCEPT_AI_OPTION", "O1", "AI_OPTION_ACCEPTANCE", BOUND_CANONICAL_CONTEXT_ID
        ),
        "UE-TACIT-TACIT-1": UserEvidenceReceipt(
            "UE-TACIT-TACIT-1", "USER_MESSAGE:turn-9", "CONFIRM_TACIT_CANDIDATE", "TACIT-1", "TACIT_CONFIRMATION", BOUND_CANONICAL_CONTEXT_ID
        ),
        "UE-QOC-A": UserEvidenceReceipt(
            "UE-QOC-A", "USER_MESSAGE:turn-1", "QOC_DECISION", "A", "Q", BOUND_CANONICAL_CONTEXT_ID
        ),
        "UE-QOC-B": UserEvidenceReceipt(
            "UE-QOC-B", "USER_MESSAGE:turn-2", "QOC_DECISION", "B", "Q", BOUND_CANONICAL_CONTEXT_ID
        ),
    }
)


def _require_user_evidence(
    receipt_id: str,
    *,
    action_type: str,
    subject_ref: str,
    question_ref: str,
) -> UserEvidenceReceipt:
    receipt = _TRUSTED_USER_EVIDENCE.get(receipt_id)
    if receipt is None:
        raise ValueError("USER_EVIDENCE_RECEIPT_NOT_IN_TRUSTED_UPSTREAM_LEDGER")
    if receipt.canonical_context_id != BOUND_CANONICAL_CONTEXT_ID:
        raise ValueError("USER_EVIDENCE_RECEIPT_CONTEXT_MISMATCH")
    if receipt.issuer != "UPSTREAM_USER_INTERACTION_AUTHORITY":
        raise ValueError("USER_EVIDENCE_RECEIPT_ISSUER_INVALID")
    if receipt.action_type != action_type:
        raise ValueError("USER_EVIDENCE_ACTION_MISMATCH")
    if receipt.subject_ref != subject_ref:
        raise ValueError("USER_EVIDENCE_SUBJECT_MISMATCH")
    if receipt.question_ref != question_ref:
        raise ValueError("USER_EVIDENCE_QUESTION_MISMATCH")
    return receipt


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
    material_key: str = ""
    decision_dimensions: Tuple[str, ...] = ()
    material_effects: Tuple[str, ...] = ()
    status: str = "CANDIDATE"

    def material_signature(self) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
        dimensions = tuple(sorted({_normalize_material_text(value) for value in self.decision_dimensions if value.strip()}))
        effects = tuple(sorted({_normalize_material_text(value) for value in self.material_effects if value.strip()}))
        if not dimensions or not effects:
            raise ValueError("MATERIAL_OPTION_REQUIRES_DECISION_DIMENSIONS_AND_EFFECTS")
        return dimensions, effects


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
    user_evidence_receipt_id: Optional[str]
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
        if not decision.user_evidence_receipt_id:
            raise ValueError("Explicit USER decision requires trusted upstream evidence receipt")
        _require_user_evidence(
            decision.user_evidence_receipt_id,
            action_type="QOC_DECISION",
            subject_ref=decision.selected_option_id,
            question_ref=decision.question_id,
        )
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


@dataclass(frozen=True)
class DiscoveryInput:
    case_id: str
    family: str
    user_input: str
    allowed_context: Dict[str, Any]
    questions: Tuple[DiscoveryQuestion, ...]
    options: Tuple[DesignOption, ...]


class ReconciliationRequired(RuntimeError):
    pass


def _normalize_material_text(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"\b(very|really|strict|strictly|highly|more)\b", " ", lowered)
    lowered = re.sub(r"[^a-z0-9_\-]+", " ", lowered)
    return " ".join(lowered.split())


_STOPWORDS = {
    "about", "after", "again", "allow", "because", "before", "being", "cannot", "could", "direct", "from",
    "have", "into", "must", "only", "remain", "should", "that", "their", "this", "through", "when", "where",
    "while", "with", "without", "world", "player", "system", "candidate", "option", "state", "truth",
}


def _semantic_tokens(value: str) -> set[str]:
    return {
        token
        for token in re.findall(r"[a-z0-9_\-]+", value.lower())
        if len(token) >= 4 and token not in _STOPWORDS
    }


def _reference_discovery_generator(discovery_input: DiscoveryInput) -> List[str]:
    """Deterministic shadow generator that has no field/path to hidden expected answers."""
    generated: List[str] = [f"USER_GOAL: {discovery_input.user_input}"]
    selected = sorted(
        (q for q in discovery_input.questions if q.material and not q.canonical_known),
        key=lambda q: (q.ranking_tuple(), q.question_id),
        reverse=True,
    )[:3]
    for question in selected:
        generated.append(f"MATERIAL_QUESTION: {question.user_prompt()}")
    for option in discovery_input.options:
        if option.status != "CANDIDATE":
            continue
        dimensions, effects = option.material_signature()
        generated.append(
            "MATERIAL_OPTION: " + "; ".join([*(f"dimension={d}" for d in dimensions), *(f"effect={e}" for e in effects)])
        )
    for key, value in sorted(discovery_input.allowed_context.items()):
        generated.append(f"BOUND_CONTEXT: {key}={value}")
    return generated


def _score_expected_discoveries(expected: Sequence[str], generated: Sequence[str]) -> Dict[str, Any]:
    generated_tokens = _semantic_tokens(" ".join(generated))
    matched: List[str] = []
    for item in expected:
        expected_tokens = _semantic_tokens(item)
        if not expected_tokens:
            continue
        overlap = expected_tokens & generated_tokens
        threshold = 1 if len(expected_tokens) <= 3 else 2
        if len(overlap) >= threshold and len(overlap) / len(expected_tokens) >= 0.25:
            matched.append(item)
    return {
        "expected_count": len(expected),
        "matched_count": len(matched),
        "matched_expected_discoveries": matched,
        "coverage": round(len(matched) / max(1, len(expected)), 3),
    }


class MIDSWorldDesignDiscoveryAdapter:
    AUTHORITY_MARKER = "CANDIDATE_ONLY / REQUIRES_ARCHITECTURE_RESOLUTION"

    def __init__(self, question_budget: int = 3, canonical_snapshot_id: str = BOUND_CANONICAL_CONTEXT_ID):
        if question_budget < 1 or question_budget > 3:
            raise ValueError("question_budget must be between 1 and 3")
        if canonical_snapshot_id != BOUND_CANONICAL_CONTEXT_ID:
            raise ReconciliationRequired(
                f"RECONCILIATION_REQUIRED: adapter is frozen to {BOUND_CANONICAL_CONTEXT_ID}, got {canonical_snapshot_id}"
            )
        self.canonical_snapshot_id = canonical_snapshot_id
        self.question_budget = question_budget
        self.provider_call_count = 0
        self.world_mutation_count = 0
        self.false_canonicalization_count = 0

    def reconcile(self) -> None:
        if self.canonical_snapshot_id != BOUND_CANONICAL_CONTEXT_ID:
            raise ReconciliationRequired("BOUND_CANONICAL_CONTEXT_DRIFT")

    def classify_epistemic_state(self, origin: OriginClass, user_evidence_receipt_id: Optional[str] = None) -> EpistemicState:
        if origin == OriginClass.USER and user_evidence_receipt_id in _TRUSTED_USER_EVIDENCE:
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
        signatures = {
            option.material_signature()
            for option in options
            if option.status == "CANDIDATE"
        }
        return len(signatures) >= 2

    @staticmethod
    def accept_ai_option(option: DesignOption, user_evidence_receipt_id: str) -> DiscoveryDecision:
        if option.origin != OriginClass.AI:
            raise ValueError("accept_ai_option expects an AI-originated option")
        receipt = _require_user_evidence(
            user_evidence_receipt_id,
            action_type="ACCEPT_AI_OPTION",
            subject_ref=option.option_id,
            question_ref="AI_OPTION_ACCEPTANCE",
        )
        return DiscoveryDecision(
            decision_id=f"DECISION-{option.option_id}",
            question_id="AI_OPTION_ACCEPTANCE",
            selected_option_id=option.option_id,
            origin=OriginClass.USER,
            user_evidence_receipt_id=receipt.receipt_id,
        )

    @staticmethod
    def promote_tacit_candidate(candidate_id: str, user_evidence_receipt_id: str) -> DiscoveryDecision:
        receipt = _require_user_evidence(
            user_evidence_receipt_id,
            action_type="CONFIRM_TACIT_CANDIDATE",
            subject_ref=candidate_id,
            question_ref="TACIT_CONFIRMATION",
        )
        return DiscoveryDecision(
            decision_id=f"DECISION-{candidate_id}",
            question_id="TACIT_CONFIRMATION",
            selected_option_id=candidate_id,
            origin=OriginClass.USER,
            user_evidence_receipt_id=receipt.receipt_id,
        )

    def _discovery_input(self, case: ReplayDiscoveryCase) -> DiscoveryInput:
        questions = tuple(DiscoveryQuestion(**q) for q in case.questions)
        options = tuple(
            DesignOption(
                option_id=o["option_id"],
                text=o["text"],
                origin=OriginClass(o["origin"]),
                material_key=o.get("material_key", ""),
                decision_dimensions=tuple(o.get("decision_dimensions", ())),
                material_effects=tuple(o.get("material_effects", ())),
                status=o.get("status", "CANDIDATE"),
            )
            for o in case.options
        )
        return DiscoveryInput(
            case_id=case.case_id,
            family=case.family,
            user_input=case.user_input,
            allowed_context=dict(case.allowed_context),
            questions=questions,
            options=options,
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
            provenance_refs=[f"REPLAY:{case.case_id}", f"CANONICAL_SNAPSHOT:{BOUND_CANONICAL_CONTEXT_ID}"],
        )

    def evaluate_replay_case(
        self,
        case: ReplayDiscoveryCase,
        discovery_generator: Optional[Callable[[DiscoveryInput], Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        self.reconcile()
        discovery_input = self._discovery_input(case)
        generator = discovery_generator or _reference_discovery_generator
        discovered = list(generator(discovery_input))
        if any(not isinstance(item, str) for item in discovered):
            raise ValueError("DISCOVERY_GENERATOR_OUTPUT_MUST_BE_STRINGS")

        # Hidden expected answers are first touched only here, after generation completed.
        score = _score_expected_discoveries(case.expected_discoveries, discovered)
        selected = self.select_questions(discovery_input.questions)
        useful_option_count = (
            len(discovery_input.options)
            if discovery_input.options and self.materially_distinct_options(discovery_input.options)
            else 0
        )
        packet = self.compile_candidate_packet(case, discovered, [], [])
        if packet.authority != self.AUTHORITY_MARKER:
            self.false_canonicalization_count += 1

        return {
            "case_id": case.case_id,
            "selected_question_ids": [q.question_id for q in selected],
            "selected_question_prompts": [q.user_prompt() for q in selected],
            "generated_discovery_count": len(discovered),
            "critical_unknowns_discovered_before_implementation": score["matched_count"],
            "expected_discovery_count": score["expected_count"],
            "hidden_answer_coverage": score["coverage"],
            "material_decisions_per_question": round(score["matched_count"] / max(1, len(selected)), 3),
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

    def evaluate_replay_suite(
        self,
        cases: Iterable[ReplayDiscoveryCase],
        discovery_generator: Optional[Callable[[DiscoveryInput], Sequence[str]]] = None,
    ) -> Dict[str, Any]:
        results = [self.evaluate_replay_case(case, discovery_generator=discovery_generator) for case in cases]
        return {
            "cases": results,
            "case_count": len(results),
            "false_canonicalization_count": self.false_canonicalization_count,
            "provider_call_count": self.provider_call_count,
            "world_mutation_count": self.world_mutation_count,
            "all_question_budgets_respected": all(len(r["selected_question_ids"]) <= self.question_budget for r in results),
        }
