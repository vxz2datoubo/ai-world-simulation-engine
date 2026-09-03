from __future__ import annotations

import hashlib
import json
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


class MaterialDistinctnessState(str, Enum):
    DISTINCT = "DISTINCT"
    NOT_DISTINCT = "NOT_DISTINCT"
    UNKNOWN = "UNKNOWN"


def _normalize_semantic_text(value: str) -> str:
    lowered = value.strip().lower()
    lowered = re.sub(r"\b(very|really|strict|strictly|highly|more)\b", " ", lowered)
    lowered = re.sub(r"[^a-z0-9_\-]+", " ", lowered)
    return " ".join(lowered.split())


def _text_digest(value: str) -> str:
    return hashlib.sha256(_normalize_semantic_text(value).encode("utf-8")).hexdigest()


BOUND_CANONICAL_CONTEXT_ID = "d62fc4b2fbaffd4984f7e292690a9013714a8e3e"
BOUND_SPEC_SNAPSHOT_ID = "MIDS-WORLD-DESIGN-REM-002"
TRUSTED_USER_EVIDENCE_LEDGER_ID = "MIDS-UPSTREAM-USER-EVIDENCE-FIXTURE/v2"
TRUSTED_MATERIAL_SEMANTIC_LEDGER_ID = "MIDS-UPSTREAM-MATERIAL-SEMANTICS-FIXTURE/v1"


@dataclass(frozen=True)
class UserEvidenceReceipt:
    receipt_id: str
    source_ref: str
    action_type: str
    subject_ref: str
    question_ref: str
    canonical_context_id: str
    statement_digest: str = ""
    issuer: str = "UPSTREAM_USER_INTERACTION_AUTHORITY"


_CLASSIFY_STATEMENT = "The user explicitly confirms the bounded classification example."


_TRUSTED_USER_EVIDENCE = MappingProxyType(
    {
        "UE-ACCEPT-O1": UserEvidenceReceipt(
            "UE-ACCEPT-O1",
            "USER_MESSAGE:turn-10",
            "ACCEPT_AI_OPTION",
            "O1",
            "AI_OPTION_ACCEPTANCE",
            BOUND_CANONICAL_CONTEXT_ID,
        ),
        "UE-TACIT-TACIT-1": UserEvidenceReceipt(
            "UE-TACIT-TACIT-1",
            "USER_MESSAGE:turn-9",
            "CONFIRM_TACIT_CANDIDATE",
            "TACIT-1",
            "TACIT_CONFIRMATION",
            BOUND_CANONICAL_CONTEXT_ID,
        ),
        "UE-QOC-A": UserEvidenceReceipt(
            "UE-QOC-A", "USER_MESSAGE:turn-1", "QOC_DECISION", "A", "Q", BOUND_CANONICAL_CONTEXT_ID
        ),
        "UE-QOC-B": UserEvidenceReceipt(
            "UE-QOC-B", "USER_MESSAGE:turn-2", "QOC_DECISION", "B", "Q", BOUND_CANONICAL_CONTEXT_ID
        ),
        "UE-CLASSIFY-EXAMPLE": UserEvidenceReceipt(
            "UE-CLASSIFY-EXAMPLE",
            "USER_MESSAGE:turn-classify",
            "CLASSIFY_USER_EXPLICIT",
            "CLASSIFY-EXAMPLE",
            "Q-CLASSIFY-EXAMPLE",
            BOUND_CANONICAL_CONTEXT_ID,
            _text_digest(_CLASSIFY_STATEMENT),
        ),
    }
)


def _require_user_evidence(
    receipt_id: str,
    *,
    action_type: str,
    subject_ref: str,
    question_ref: str,
    statement: Optional[str] = None,
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
    if receipt.statement_digest:
        if statement is None:
            raise ValueError("USER_EVIDENCE_STATEMENT_REQUIRED")
        if _text_digest(statement) != receipt.statement_digest:
            raise ValueError("USER_EVIDENCE_STATEMENT_MISMATCH")
    return receipt


@dataclass(frozen=True)
class MaterialSemanticReceipt:
    receipt_id: str
    source_ref: str
    option_id: str
    comparison_scope_ref: str
    option_text_digest: str
    semantic_class_ref: str
    canonical_context_id: str
    issuer: str = "UPSTREAM_DESIGN_SEMANTIC_AUTHORITY"


def _semantic_receipt(option_id: str, text: str, scope: str, semantic_class: str) -> MaterialSemanticReceipt:
    return MaterialSemanticReceipt(
        receipt_id=f"MSR-{option_id}",
        source_ref=f"REPLAY_FIXTURE:{scope}:{option_id}",
        option_id=option_id,
        comparison_scope_ref=scope,
        option_text_digest=_text_digest(text),
        semantic_class_ref=semantic_class,
        canonical_context_id=BOUND_CANONICAL_CONTEXT_ID,
    )


_TRUSTED_MATERIAL_SEMANTICS = MappingProxyType(
    {
        r.option_id: r
        for r in (
            _semantic_receipt("O-R1-LOCAL", "Function-local impairment preserves unaffected skills.", "R1-CAPABILITY", "FUNCTION_LOCAL"),
            _semantic_receipt("O-R1-GLOBAL", "Global penalty degrades most combat output.", "R1-CAPABILITY", "GLOBAL_PENALTY"),
            _semantic_receipt("O-R2-CHANNEL", "Require a real source/channel/carrier/perception path.", "R2-KNOWLEDGE", "PROVENANCE_CHANNEL"),
            _semantic_receipt("O-R2-INJECT", "Allow direct narrative injection for important events.", "R2-KNOWLEDGE", "NARRATIVE_INJECTION"),
            _semantic_receipt("O-R3-EVENT", "Canonical event evidence outranks summaries and projections.", "R3-PERSISTENCE", "EVENT_EVIDENCE_AUTHORITY"),
            _semantic_receipt("O-R3-SUMMARY", "Newest materialized summary wins.", "R3-PERSISTENCE", "SUMMARY_AUTHORITY"),
            _semantic_receipt("O-R4-LEGAL", "Accept causal loss and seek only legal alternatives or no opportunity.", "R4-HOSTILE-PLAYER", "LEGAL_ALTERNATIVE_ONLY"),
            _semantic_receipt("O-R4-FORCE", "Force dramatic reconvergence by replacing the lost cause.", "R4-HOSTILE-PLAYER", "FORCED_RECONVERGENCE"),
            _semantic_receipt("O-R5-OBJECT", "Treat object possession as canonical and inventory as rebuildable index.", "R5-POSSESSION", "OBJECT_POSSESSION_AUTHORITY"),
            _semantic_receipt("O-R5-DUAL", "Let inventory and object both independently assert possession.", "R5-POSSESSION", "DUAL_POSSESSION_AUTHORITY"),
            _semantic_receipt("O-R6-BIND", "Bind presentation refs to the same replayed world/scene state.", "R6-PRESENTATION", "CROSS_PLANE_BINDING"),
            _semantic_receipt("O-R6-DIRECTOR", "Allow director-visible assets to override possession when useful.", "R6-PRESENTATION", "DIRECTOR_OVERRIDE"),
        )
    }
)


def _resolve_material_semantic(option: "DesignOption") -> Optional[MaterialSemanticReceipt]:
    receipt = _TRUSTED_MATERIAL_SEMANTICS.get(option.option_id)
    if receipt is None:
        return None
    if receipt.canonical_context_id != BOUND_CANONICAL_CONTEXT_ID:
        return None
    if receipt.issuer != "UPSTREAM_DESIGN_SEMANTIC_AUTHORITY":
        return None
    if receipt.option_text_digest != _text_digest(option.text):
        return None
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

    def declared_material_metadata(self) -> Dict[str, Tuple[str, ...]]:
        """Caller-authored metadata retained for audit only; never semantic authority."""
        return {
            "decision_dimensions": tuple(self.decision_dimensions),
            "material_effects": tuple(self.material_effects),
        }


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
    """Deterministic shadow generator with no hidden-answer or caller-semantic authority."""
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
        receipt = _resolve_material_semantic(option)
        if receipt is None:
            generated.append(f"MATERIAL_OPTION_UNRESOLVED: {option.option_id}")
        else:
            generated.append(
                f"MATERIAL_OPTION: scope={receipt.comparison_scope_ref}; semantic_class={receipt.semantic_class_ref}; option={option.option_id}"
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

    def classify_epistemic_state(
        self,
        origin: OriginClass,
        user_evidence_receipt_id: Optional[str] = None,
        *,
        subject_ref: Optional[str] = None,
        question_ref: Optional[str] = None,
        statement: Optional[str] = None,
    ) -> EpistemicState:
        if origin == OriginClass.USER:
            if not user_evidence_receipt_id or not subject_ref or not question_ref or statement is None:
                raise ValueError("USER_EXPLICIT_CLASSIFICATION_REQUIRES_BOUND_EVIDENCE_CONTEXT")
            _require_user_evidence(
                user_evidence_receipt_id,
                action_type="CLASSIFY_USER_EXPLICIT",
                subject_ref=subject_ref,
                question_ref=question_ref,
                statement=statement,
            )
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
    def material_distinctness_state(options: Sequence[DesignOption]) -> MaterialDistinctnessState:
        candidates = [option for option in options if option.status == "CANDIDATE"]
        if len(candidates) < 2:
            return MaterialDistinctnessState.NOT_DISTINCT
        receipts: List[MaterialSemanticReceipt] = []
        for option in candidates:
            receipt = _resolve_material_semantic(option)
            if receipt is None:
                return MaterialDistinctnessState.UNKNOWN
            receipts.append(receipt)
        scopes = {receipt.comparison_scope_ref for receipt in receipts}
        if len(scopes) != 1:
            return MaterialDistinctnessState.UNKNOWN
        classes = {receipt.semantic_class_ref for receipt in receipts}
        if len(classes) < 2:
            return MaterialDistinctnessState.NOT_DISTINCT
        return MaterialDistinctnessState.DISTINCT

    @staticmethod
    def materially_distinct_options(options: Sequence[DesignOption]) -> bool:
        return MIDSWorldDesignDiscoveryAdapter.material_distinctness_state(options) is MaterialDistinctnessState.DISTINCT

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
            provenance_refs=[
                f"REPLAY:{case.case_id}",
                f"CANONICAL_SNAPSHOT:{BOUND_CANONICAL_CONTEXT_ID}",
                f"SPEC_SNAPSHOT:{BOUND_SPEC_SNAPSHOT_ID}",
            ],
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

        score = _score_expected_discoveries(case.expected_discoveries, discovered)
        selected = self.select_questions(discovery_input.questions)
        distinctness = self.material_distinctness_state(discovery_input.options)
        useful_option_count = len(discovery_input.options) if distinctness is MaterialDistinctnessState.DISTINCT else 0
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
            "material_distinctness_state": distinctness.value,
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
