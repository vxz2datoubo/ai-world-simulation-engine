# MIDS Living World to AWRSE AF-A..H vNext Mapping

Status: `ARCHITECTURE_CANDIDATE / NON_RUNTIME / REQUIRES_INDEPENDENT_REVIEW`

Source snapshot: `MIDS-ARCH-001-SPEC-2026-09-02-R1` (Issue #103 comment `5497416414`).

Design evidence: exact commit `f20c097de5d91ba580b807a2bf86e10b0fe5439d` on `control/mids-architecture-discovery-v0-2`. The evidence remains non-canonical; this document records the compilation, not a replacement source of truth.

## Classification legend

- `ALREADY_CANONICAL`: the current AF contract already states the required law.
- `CANONICAL_CLARIFICATION`: no new authority or type is needed; the existing law needs a more explicit consequence.
- `ARCHITECTURE_EXTENSION_CANDIDATE`: an additive interface is needed inside an existing AF authority.
- `OPEN_DECISION`: architecture must name the unresolved mechanism and required evidence.
- `RULESET_OR_PRODUCT_POLICY`: architecture fixes the boundary, while a versioned product/ruleset chooses values.
- `LATER_PHASE`: deliberately excluded from this slice.

## Complete decision classification

| ID | Classification | AF destination | Compiled disposition |
|---|---|---|---|
| P001 | CANONICAL_CLARIFICATION | AF-A..H | First vertical slice is breadth-first: every enabled domain has a minimal connected contract, but no empty domain may claim authority. |
| P002 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A | `WorldOrchestrationPlan` coordinates typed domain requests and receipts; it owns no domain truth and cannot commit events. |
| P003 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/B/E/F/G | `DomainChangeNotice` carries source event/cursor and affected-domain hints; each receiving authority independently validates any consequence. |
| P004 | ALREADY_CANONICAL | AF-A/B/E/H | One `WorldInstance` truth; knowledge, belief, audience policy and presentation remain projections with no flow-back. |
| P005 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-F/G | `NarrativeInfluenceReceipt` records bounded ranking influence over already-legal candidates; it cannot create facts, candidates or outcomes. |
| P006 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-H | `DramaticPresentationIntent` extends the existing director handoff semantically; concrete shot/edit/performance authority remains outside AWRSE. |
| P007 | RULESET_OR_PRODUCT_POLICY | AF-H | `AudienceExposurePolicy` selects game/film visibility from legal knowledge refs; exact product defaults remain versioned policy. |
| P008 | CANONICAL_CLARIFICATION | AF-A/E/G | Player controls attempted intent for the bound actor; persona may shape low-risk expression, never veto intent or control NPCs. |
| P009 | CANONICAL_CLARIFICATION | AF-A/C | Natural language is untrusted intent; legal method, capability, resources, time and consequence precede commitment. |
| P010 | CANONICAL_CLARIFICATION | AF-E | Model inference cannot become character knowledge, capability, memory or plan evidence without an authorized source path. |
| P011 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/B | `SimulationFidelityPolicy` selects update granularity, never whether established truth continues to exist. |
| P012 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/B | `DeferredConcretizationReceipt` chooses only among constraint-compatible unresolved alternatives and binds prior evidence/cursor. |
| P013 | ALREADY_CANONICAL | AF-A/E | `UNKNOWN` is legal; missing evidence is not guessed and locked evidence is never re-rolled. |
| P014 | CANONICAL_CLARIFICATION | AF-A/B | One canonical timeline/cursor; enabled domains may advance at different declared granularities. Single-player is first product scope. |
| P015 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/H | `TemporalCompressionPlan` is presentation scheduling over real elapsed world time and has decision/interrupt boundaries. |
| P016 | RULESET_OR_PRODUCT_POLICY | AF-A/B | Default reopen freezes elapsed world time; optional absence advancement needs a later versioned policy and remains open. |
| P017 | CANONICAL_CLARIFICATION | AF-B/E | Actor death is permanent evidence; player continuity may rebind to another eligible actor in the same `WorldInstance`. |
| P018 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-B/F | World bootstrap combines approved authored constraints with evidence-bound unresolved slots; later detail uses deferred concretization. |
| P019 | ALREADY_CANONICAL | AF-F/G | Soft attractors and storylets are possibilities, never promised future facts. |
| P020 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A | `DomainModuleManifest` declares authority scope, dependencies and lifecycle; disabled modules cannot adjudicate or emit canonical events. |
| P021 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-B/C/E | `InstitutionAggregate` is a world actor with stable identity and referenced resources/goals/factions/policy; detailed mechanics are later rulesets. |
| P022 | CANONICAL_CLARIFICATION | AF-B/C | Resolution scaling may aggregate resources, but every material consequence retains conservation/source evidence. |
| P023 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/B/E | `LegalProcessProjection` separates objective fact/evidence from investigator belief, legal action/judgment and social belief. |
| P024 | CANONICAL_CLARIFICATION | AF-B/E/F | Evidence is a world-grounded entity/ref that may be hidden, moved, destroyed or forged; narrative cannot mint it. |
| P025 | ALREADY_CANONICAL | AF-A/B | Persistent IDs, not appearance, establish physical entity identity. |
| P026 | ALREADY_CANONICAL | AF-B/C/D | Ownership, possession, permission, worn, equipped and location remain distinct. |
| P027 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-A/B | `EntityLifecycleReceipt` preserves destroyed IDs and source provenance; split/composed outputs receive new IDs. |
| P028 | ARCHITECTURE_EXTENSION_CANDIDATE | AF-B | `PlaceHistoryProjection` derives settlement/land-use/social-identity evolution from canonical events without becoming a second truth store. |
| P029 | CANONICAL_CLARIFICATION | AF-A/E/F | Compaction may replace derived projections only; causally material event evidence and provenance remain reconstructible. |
| P030 | CANONICAL_CLARIFICATION | AF-F/G | `NO_VALID_OPPORTUNITY` and ordinary peaceful continuation are valid; narrative activity cannot force catastrophe. |

## Gap and contradiction report

### Gaps closed by this candidate

1. Cross-domain coordination previously had authority order but no typed non-authoritative coordination envelope.
2. Adaptive fidelity and deferred concretization lacked explicit evidence/cursor/no-retcon contracts.
3. Narrative was prohibited from rewriting truth but had no auditable receipt for bounded influence over legal candidates.
4. AF-H separated Director authority but did not explicitly separate dramatic intent from concrete shot construction or game/film exposure policy.
5. Module enablement, institution identity, entity destruction/composition provenance, and legal judgment separation were principles without minimal type surfaces.

### Contradictions resolved without a second authority

- “Multiple domain AIs” does not mean multiple World Truth stores: domain owners validate and commit through AF-A; the Orchestrator only coordinates.
- “Narrative bias” does not mean narrative probability changes world physics: it may rank legal opportunities under an audited budget, never alter feasibility or outcome probability.
- “Generated later detail” does not mean retcon: only unresolved slots may be concretized, and the receipt binds all locked constraints.
- “Film audience sees more” does not mean characters learn more: exposure is an AF-H projection and has no acquisition path back to AF-E.
- “Institution as actor” does not make it a human `ActorAggregate`: it is a stable aggregate that delegates actions to authorized roles and resources.
- “Time compression” compresses presentation, not elapsed canonical time.

## Remaining decisions and exclusions

| Item | Disposition | Required future evidence |
|---|---|---|
| Canonical concurrency arbitration | OPEN_DECISION | Same-object conflicts, interrupt ordering and deterministic replay benchmark. |
| Exact adaptive-fidelity thresholds | RULESET_OR_PRODUCT_POLICY | Cost/quality profiling across active, background and dormant domains. |
| Exact narrative influence weights/budgets | RULESET_OR_PRODUCT_POLICY | Transparent offline ranking evaluation and human agency review. |
| Long-absence advancement threshold/algorithm | OPEN_DECISION | Long-horizon replay, interruption and fairness tests. |
| Memory backend/decay and relationship math | OPEN_DECISION | Retrieval quality, rebuild equality and sensitivity studies. |
| Detailed economy, courtroom, law and politics | LATER_PHASE | Domain-specific rulesets and Golden corpora. |
| Full parent-child material provenance | OPEN_DECISION | Identity/lifecycle corpus covering split, merge, repair and destruction. |
| Multiplayer runtime, save/load UI and hardcore mode | LATER_PHASE | Separate product and runtime releases. |
| AI Director transport/provider implementation | OPEN_DECISION | Version-skew, serialization and failure-isolation prototype. |

## First Living World build order after acceptance

1. AF-A module manifests, orchestration receipts and one canonical time cursor.
2. One small AF-B world with people, objects, one institution and resource conservation.
3. AF-C legal natural-language action planning against existing capability truth.
4. AF-E evidence/knowledge separation including one false-belief/legal-misjudgment path.
5. AF-F/G legal storylet ranking with a narrative influence receipt and peaceful `NO_VALID_OPPORTUNITY` path.
6. AF-H game/film exposure projections and dramatic intent handed to the existing Director contract.
7. Replay all selected Golden checks before any provider, renderer or production integration.

This sequence is an implementation dependency map, not runtime authority.
