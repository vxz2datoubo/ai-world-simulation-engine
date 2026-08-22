# AF-001 Traceability, Dependency, Authority and OPEN_DECISION Register

Status: `ARCHITECTURE_FREEZE_CANDIDATE / SINGLE_TRACEABILITY_ENTRYPOINT`

This is the single AF-001 traceability/dependency/open-decision registry. It does not compete with `ARCHITECTURE.md`, which remains the canonical architecture master. Machine-readable interface contracts are in `contracts/AF001-LIVING-STORY-CONTRACTS.json`; Golden Scenario executable specifications are in `evals/AF001-GOLDEN-SCENARIOS.json`.

## 1. Fresh source baseline

AF-001 branch base:

`ebd2ca2bad948b737f967ae09c000643ec2f9929`

That canonical `main` is the Control Tower merge of accepted R002 PR #4. AF-001 does not reopen R001/R002 semantics except to preserve them as mandatory foundations.

## 2. Authority matrix

| Plane / artifact | May create canonical world truth? | May mutate upstream truth? | May create recipient knowledge? | May choose presentation? | Notes |
|---|---:|---:|---:|---:|---|
| Player input | No | No | No | Intent only | Untrusted free text; controls only authorized attempted actions |
| World/rules/affordance authority | Yes, through authorized resolution/event path | N/A | No direct epistemic injection | No | Owns legality/world transition boundaries |
| Capability/state resolution | Yes, only through authorized resolution receipts/events | No | No | No | Interface frozen; runtime not implemented by AF-001 |
| Canonical event store | System of record | No rewrite-in-place | Evidence source only | No | Append-preserved causal evidence |
| Materialized world state | Projection only | No | No | No | Rebuildable from source evidence/rules |
| Player knowledge/chronicle | Player-local projection | No | Yes, only through valid paths | May constrain player-facing presentation | Never duplicates shared physical truth |
| NPC memory/belief/relationship | NPC-local projections | No | Yes, only from valid perception/information | May constrain NPC behavior/presentation later | Summary/reflection is derived cache |
| Story/Narrative design | No | No | No | Proposes dramatic structures | Hard anchors must revalidate real causes |
| Narrative Opportunity / World Echo | No | No | No direct injection | Proposes/ranks legal candidates | `NO_VALID_OPPORTUNITY` is valid |
| PX | No | No | No | Ranks/surfaces legal candidates | Cannot lower difficulty, invent facts or force action |
| AI Director | No | No | No | Yes, within packet | Downstream read-only staging/performance/editorial authority |
| Renderer | No | No | No | Generates pixels/audio | Contradiction => render failure |
| Publication/spectator projection | No | No | No flow-back | Yes, audience-specific | May expose only policy-authorized information |

Frozen order:

`WORLD/RULES > CAPABILITY/STATE > KNOWLEDGE/MEMORY > NARRATIVE OPPORTUNITY > PX > AI DIRECTOR > RENDERER/PUBLICATION`

## 3. Dependency graph

```text
R001/R002 accepted foundations
  |
  +--> AF-A Identity/Event/Authority
        |
        +--> AF-B Actor/Object/Spatial
        |      |
        |      +--> AF-C Capability/Injury
        |      +--> AF-D Appearance/Asset
        |
        +--> AF-E Perception/Memory/Knowledge/Relationship
        |
        +--> AF-F Story/Information
               |
               +--> AF-G Opportunity/World Echo/PX
                       |
                       +--> AF-H AI Director/Renderer/Publication

Cross-links:
AF-B -> AF-D (spatial/view/asset binding)
AF-C -> AF-D (functional injury vs visible treatment)
AF-E -> AF-F (information becomes recipient knowledge only through provenance)
AF-E -> AF-G (echo/response attribution and player speech boundary)
AF-F -> AF-G (story goals become legal opportunity candidates)
AF-D + AF-E + AF-G -> AF-H (presentation and knowledge-safe director packet)
```

No post-freeze runtime task may depend on an unresolved lower-layer `OPEN_DECISION` unless the task explicitly excludes that mechanism.

## 4. Design-source traceability

| Source | Design role | AF destinations | Golden Scenario coverage | Freeze disposition |
|---|---|---|---|---|
| Issue #5 `PX-DESIGN-001` | consolidated product/authority/PX/world-topology candidate master | AF-A, AF-B, AF-G, AF-H | all, especially multiplayer/plot-breaking | consolidated; no direct implementation authority |
| Issue #6 `ASSET-DESIGN-001` | asset identity, spatial graph, camera/view/media separation | AF-B, AF-D, AF-H | `ASSET_APPEARANCE_REVISIT`, `BROKEN_DOOR_WORLD_ECHO` | interfaces frozen; storage/tool adapters not selected |
| Issue #7 `REACT-DESIGN-001` | World Echo, attribution, response concepts, player-expression risk | AF-E, AF-G, AF-H | `BROKEN_DOOR_WORLD_ECHO`, `PERSONA_SPEECH_BOUNDARY` | interfaces frozen; runtime/scoring not implemented |
| Issue #8 `NARRATIVE-DESIGN-001` | choice memory, persona hypothesis, promises, storylets | AF-E, AF-F, AF-G | `PROMISE_RETURN_CALLBACK`, `PERSONA_SPEECH_BOUNDARY`, `HOSTILE_PLAYER_BREAKS_PLOT` | authority/evidence boundaries frozen; model/scoring details open |
| Issue #9 `MEMORY-DESIGN-001` | NPC episodic memory, beliefs, relationships, rehydration | AF-E | `BROKEN_DOOR_WORLD_ECHO`, `PROMISE_RETURN_CALLBACK`, `MULTIPLAYER_DIFFERENT_KNOWLEDGE` | data ownership/provenance frozen; backend/decay math open |
| Issue #10 `GOV-DESIGN-001` | landing register / freeze governance | all | all | AF-001 becomes current freeze artifact set; no runtime release |
| Issue #11 `STORY-DESIGN-001` | StoryDNA, genre engines, narrative gravity, branch quality | AF-F, AF-G | `HOSTILE_PLAYER_BREAKS_PLOT`, `WILDERNESS_NEWS_TRAP` | narrative authority boundaries frozen; registry/scoring details open |
| Issue #12 `CAPABILITY-DESIGN-001` | attributes/skills/injury/action resolution | AF-C, AF-D | `FIGHTER_VS_SCHOLAR`, `WILDERNESS_NEWS_TRAP` | interfaces/order/provenance frozen; math/attributes open |
| Issue #13 `ENCOUNTER-STATE-DESIGN-001` | opportunity broker, information propagation, persistent actor presentation | AF-C, AF-D, AF-F, AF-G, AF-H | `WILDERNESS_NEWS_TRAP`, `ASSET_APPEARANCE_REVISIT` | candidate lifecycles/authority frozen; density/scoring open |
| Issue #14 `INTEGRATION-DESIGN-001` | integrated state planes / cross-module composition / Golden Scenarios | AF-A through AF-H | all eight | consolidated into canonical master + machine contracts |
| Issue #15 `AF-001` | active architecture-freeze authorization | AF-A through AF-H | all eight | current authorized task; architecture only |

## 5. Candidate-skill landing coverage

Issue #10 tracks candidate skill ranges. AF-001 does **not** promote them to formal skills. It freezes the interfaces/evals they must later satisfy.

| Candidate skill range | Design family | AF contract coverage | Promotion state |
|---|---|---|---|
| S13-S34 | player continuity / PX / world topology / concurrency / publication / director federation | AF-A, AF-B, AF-G, AF-H | `CANDIDATE / NOT_PROMOTED` |
| S35-S40 | story asset / spatial graph / view / media / continuity | AF-B, AF-D, AF-H | `CANDIDATE / NOT_PROMOTED` |
| S41-S46 | World Echo / attribution / response concept / player auto-expression | AF-E, AF-G, AF-H | `CANDIDATE / NOT_PROMOTED` |
| S47-S54 | choice memory / character arc / persona / storylets / branch guard | AF-E, AF-F, AF-G | `CANDIDATE / NOT_PROMOTED` |
| S55-S61 | NPC memory / belief / relationship / retrieval / integrity | AF-E | `CANDIDATE / NOT_PROMOTED` |

Required future chain remains:

`CONTRACT_FROZEN -> EVALS_DEFINED -> BOUNDED_TASK_RELEASED -> IMPLEMENTED -> INDEPENDENT_REVIEW -> MERGED -> RUNTIME_VALIDATED -> REAL_WORLD_VALIDATED(if applicable) -> FORMAL_SKILL_PROMOTED`.

## 6. Golden Scenario coverage matrix

| Scenario | A | B | C | D | E | F | G | H |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| `WILDERNESS_NEWS_TRAP` | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ | ✓ |
| `BROKEN_DOOR_WORLD_ECHO` | ✓ | ✓ |  | ✓ | ✓ | ✓ | ✓ | ✓ |
| `FIGHTER_VS_SCHOLAR` | ✓ | ✓ | ✓ | ✓ |  |  |  |  |
| `PROMISE_RETURN_CALLBACK` | ✓ |  |  |  | ✓ | ✓ | ✓ | ✓ |
| `PERSONA_SPEECH_BOUNDARY` |  |  |  |  | ✓ |  | ✓ | ✓ |
| `ASSET_APPEARANCE_REVISIT` |  | ✓ |  | ✓ |  |  |  | ✓ |
| `HOSTILE_PLAYER_BREAKS_PLOT` | ✓ | ✓ |  |  | ✓ | ✓ | ✓ | ✓ |
| `MULTIPLAYER_DIFFERENT_KNOWLEDGE` | ✓ | ✓ |  |  | ✓ | ✓ | ✓ | ✓ |

All AF domains are covered by at least one scenario; high-risk authority/knowledge planes are covered by multiple adversarial scenarios.

## 7. Migration/versioning obligations

Frozen obligations:

1. Every AF contract carries an explicit version.
2. Changes to authority order, identity semantics, canonical event meaning, canonical ownership, required provenance or fail-closed boundaries are breaking.
3. Breaking changes require:
   - explicit migration specification;
   - replay/rebuild impact analysis;
   - updated affected Golden Scenarios;
   - fresh independent review.
4. Snapshots/caches carry source cursor + schema/ruleset version and may be invalidated/rebuilt.
5. Source events are never edited merely to migrate a projection.
6. Model/provider upgrades create new derived output versions and cannot silently rewrite history.

## 8. Historical R001/R002 non-regression map

AF-001 must preserve these accepted foundation invariants:

| Foundation | Required preservation |
|---|---|
| R001 authority | raw user text untrusted; player cannot control target internal state/world rules |
| R001 event sourcing | canonical events append-preserved; current state is projection; replay remains authoritative for implemented domains |
| R001 live-state seal | public direct live mutation/deletion remains rejected |
| R001 renderer | render mismatch cannot mutate world truth |
| R002 spatial | zone/scene binding, adjacency, reachability and malformed spatial graphs fail closed |
| R002 possession | owner/inventory graph integrity, possession transitions and held-object movement stay consistent |
| R002 perception | SAW/HEARD/WAS_TOLD mode-specific provenance; unsupported modes fail closed until implemented |
| R002 render projection | persistent object state fields remain contradiction-checked |

Existing foundation contract/schema/eval files are referenced, not shadow-copied into AF-001.

## 9. OPEN_DECISION registry

### OD-CONCURRENCY-001 — canonical concurrency/arbitration algorithm
- **Competing options:** per-aggregate single-writer optimistic versioning; deterministic tick resolver; ordered DecisionWindow scheduler; hybrid by WorldScope.
- **Evidence:** Issue #5 requires deterministic ordering/conflict handling but current R001/R002 does not exercise multiplayer concurrency load.
- **Dependency:** future PARTY/PUBLIC shared-object conflicts and interruptible activities.
- **Risk:** freezing the wrong scheduler may bake platform latency assumptions into world semantics or permit nondeterministic replay.
- **Required experiment/research:** workload model + two-player same-object conflict Golden extension + replay determinism benchmark across asynchronous/live inputs.

### OD-CAPABILITY-ATTR-001 — final core attribute vector
- **Competing options:** small mundane core from Issue #12; richer genre-neutral vector; minimal action-demand-only primitives.
- **Evidence:** Issue #12 proposes candidate attributes but explicitly says exact list requires eval.
- **Dependency:** ActionDemandProfile authoring, progression and genre extension packs.
- **Risk:** over-broad vector becomes arbitrary stat soup; under-broad vector pushes hidden judgment back into LLM prompts.
- **Required experiment/research:** task corpus across physical/technical/social actions; ablation for predictive/useful distinction; designer usability review.

### OD-CAPABILITY-MATH-001 — modifier stacking and stochastic curve
- **Competing options:** additive-then-multiplicative stack; tagged priority stack; bounded rules per demand profile; deterministic margin-only resolution for some classes.
- **Evidence:** Issue #12 gives candidate equations/IRT-style sigmoid only as research models.
- **Dependency:** DerivedCapability and ActionResolutionReceipt runtime.
- **Risk:** fake precision, balance instability, replay mismatch or hidden order-dependence.
- **Required experiment/research:** sensitivity tests, monotonicity/property tests, replay receipts and fighter-vs-scholar parameter sweeps before code release.

### OD-MEMORY-STORE-001 — persistent backend/event-store technology
- **Competing options:** embedded relational/SQLite for MVP; server relational store; append/event store + materialized projections; hybrid tiers.
- **Evidence:** Issue #9 freezes structured persistence requirements but explicitly selects no backend.
- **Dependency:** NPC memory, player continuity, long-running worlds, privacy/operations.
- **Risk:** premature vendor/schema coupling or inability to rebuild/audit history.
- **Required experiment/research:** expected data volume/query shapes, retention/privacy requirements, restart/rebuild benchmarks, backup/migration tests.

### OD-MEMORY-DECAY-001 — memory accessibility/forgetting model
- **Competing options:** rule-based decay bands; retrieval-strength model; salience/relationship-aware decay; no ordinary decay for MVP except explicit policy.
- **Evidence:** Issue #9 distinguishes durable evidence from accessibility but does not validate weights/equations.
- **Dependency:** NPC retrieval bundle and long-horizon callback quality.
- **Risk:** accidental forgetting becomes lore drift, or no decay floods context/retrieval.
- **Required experiment/research:** long-history synthetic replay + retrieval precision/recall + contradiction/callback human evaluation.

### OD-RELATIONSHIP-MATH-001 — relationship projection dimensions/weights
- **Competing options:** categorical state machine; bounded multidimensional numeric projection; event-rule deltas; hybrid qualitative+numeric.
- **Evidence:** Issue #9 rejects one morality score and proposes dimensions without final update math.
- **Dependency:** NPC behavior, social callbacks, memory retrieval.
- **Risk:** opaque numeric drift or oversimplified social behavior.
- **Required experiment/research:** adversarial social histories, rebuild equivalence, sensitivity tests and designer interpretability review.

### OD-GENRE-REGISTRY-001 — GenreEngine registry governance
- **Competing options:** fixed core registry with extensions; fully data-driven pack registry; hierarchical dramatic-engine ontology.
- **Evidence:** Issue #11 states genre is multi-axis and candidate list is extensible.
- **Dependency:** StoryDNA validation and story authoring tools.
- **Risk:** mutually-exclusive genre enum or uncontrolled synonym explosion.
- **Required experiment/research:** encode representative mystery/romance/wuxia/xianxia/crime/humanist hybrids and test query/validation ergonomics.

### OD-CLUE-QUALITY-001 — clue/reveal/branch-quality metrics
- **Competing options:** authored invariant checks; graph coverage/solvability metrics; player-model-informed evidence sufficiency; hybrid human+automated eval.
- **Evidence:** Issues #11/#14 require mystery/branch quality but no validated universal metric exists.
- **Dependency:** future Storylet/RevealScheduler implementation.
- **Risk:** optimizing a simplistic score can make stories predictable or falsely certify unsolvable branches.
- **Required experiment/research:** authored mystery corpus, hostile early-solve variants, clue graph solvability tests and human playtest comparison.

### OD-PX-SCORING-001 — PX ranking objective/weights
- **Competing options:** constrained multi-objective ranking; per-context rule packs; learned ranking from opted-in player feedback; hybrid.
- **Evidence:** Issue #5 explicitly rejects collapsing experience into one `fun_score`.
- **Dependency:** PXRankingReceipt/runtime.
- **Risk:** hidden manipulation, brittle personalization or optimizing engagement over meaningful agency.
- **Required experiment/research:** define transparent dimensions, offline scenario rankings, opt-in real-player study and guardrail review before learned scoring.

### OD-COMMENTARY-BUDGET-001 — World Echo commentary thresholds/cooldowns
- **Competing options:** per-scene/per-speaker fixed budgets; salience-adaptive budget; director-paced budget; hybrid.
- **Evidence:** Issue #7 mandates anti-repeat but no threshold has real-player evidence.
- **Dependency:** World Echo runtime and ResponseConcept realization.
- **Risk:** chatter spam or silent world memory.
- **Required experiment/research:** repeated-revisit simulations + semantic duplicate tests + player evaluation across combat/quiet/grief/humor contexts.

### OD-ENCOUNTER-DENSITY-001 — opportunity/encounter density and contrivance budget
- **Competing options:** region/world-rule density tables; narrative-pressure-adjusted caps; ecology/schedule-derived encounter rates; hybrid.
- **Evidence:** Issue #13 requires regional density plausibility and non-obviousness.
- **Dependency:** NarrativeOpportunityBroker.
- **Risk:** wilderness becomes theme park of plot carriers or important information becomes implausibly unavailable.
- **Required experiment/research:** world-route simulations, carrier travel models, anti-pattern frequency tests and player contrivance ratings.

### OD-PUBLICATION-POLICY-001 — audience knowledge/redaction policy
- **Competing options:** strict player-knowledge-only publication; spectator omniscient channel with explicit redaction classes; episode-specific policy profiles.
- **Evidence:** Issues #5/#14 require spectator/publication separation but do not freeze one audience product.
- **Dependency:** PublicationProjection and AI Director packet.
- **Risk:** spoilers/privacy leaks can flow into player-facing output or canonical knowledge.
- **Required experiment/research:** define audience classes, privacy threat model, spoiler test cases and multiplayer-different-knowledge publication variants.

### OD-DIRECTOR-ADAPTER-001 — AWRSE ↔ AI Film director integration protocol
- **Competing options:** repository-neutral JSON packet API; versioned file/queue bridge; service API; future plugin/connector.
- **Evidence:** design freezes `DIRECTOR-BEAT-PACKET` semantics but explicitly forbids H3/AI Film runtime integration in AF-001.
- **Dependency:** future cinematic presentation slice.
- **Risk:** implementation transport accidentally becomes authority or forks director knowledge.
- **Required experiment/research:** packet round-trip mock, forbidden-invention validation, version negotiation and failure isolation without renderer access.

## 10. OPEN_DECISION governance

`OPEN_DECISION` means the boundary/interface is known but the concrete mechanism lacks enough evidence to freeze safely.

Rules:
- no worker may silently choose one option in runtime code;
- any future task depending on an OPEN_DECISION must either resolve it through approved research/eval or explicitly exclude it from scope;
- resolution is additive history: record decision evidence and replacement, do not erase competing-option history;
- low-confidence options do not become formal skills or canonical runtime rules.

## 11. AF-001 acceptance checklist

A candidate exact head is ready for Independent Reviewer only when all are true:

- one canonical `ARCHITECTURE.md` master;
- one AF contract registry covering AF-A through AF-H;
- one Golden Scenario registry containing all eight required scenarios and all mandatory fields;
- one traceability/dependency/OPEN_DECISION entrypoint;
- no new gameplay runtime files/features;
- existing R001/R002 foundation files remain present and are not shadow-replaced;
- architecture consistency validator is non-vacuous and green;
- full historical pytest suite remains green;
- Python 3.11 and 3.13 exact-head CI binds `EXPECTED_HEAD == EXACT_HEAD`;
- Draft PR remains unmerged;
- Worker publishes Issue #15 + PR handoff and stops.

Final acceptance still belongs to Independent Reviewer + Control Tower.
