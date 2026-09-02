# AF-001 Traceability, Dependency, Authority and OPEN_DECISION Register

Status: `ARCHITECTURE_FREEZE_ACCEPTED_CANONICAL / SINGLE_TRACEABILITY_ENTRYPOINT`

This is the single AF-001 traceability/dependency/open-decision registry. It does not compete with `ARCHITECTURE.md`, which is the canonical architecture master. Machine contracts live in `contracts/AF001-LIVING-STORY-CONTRACTS.json`; Golden executable specifications live in `evals/AF001-GOLDEN-SCENARIOS.json`.

AF-001 is independently accepted and merged canonical architecture. Subsequent accepted R003-I1A/I1B bounded runtime foundations do not, by themselves, resolve any `OPEN_DECISION` recorded here. `CAPABILITY-ARCH-RESOLUTION-001` is a later explicit Control Tower architecture/governance decision: it preserves the historical capability decision records while splitting resolved architectural substrate from still-deferred ruleset, player-balance and genre-extension policy.

## 1. Fresh source baseline

AF-001 base: `ebd2ca2bad948b737f967ae09c000643ec2f9929`.

That `main` is the Control Tower merge of accepted R002 PR #4. AF-001 preserves R001/R002 and does not reopen their runtime semantics.

Capability architecture resolution release base: `76a223f96dfb4e97400cc753d65d89b4e543cae6`, the governed CAP-EVAL-002 merge on canonical `main`.

## 2. Structured artifact authority roles

The machine contract is authoritative for this registry and must contain exactly this role allocation:

```json
{
  "ARCHITECTURE.md": "CANONICAL_ARCHITECTURE_MASTER",
  "contracts/AF001-LIVING-STORY-CONTRACTS.json": "MACHINE_CONTRACT_REGISTRY",
  "evals/AF001-GOLDEN-SCENARIOS.json": "GOLDEN_EXECUTABLE_SPEC_REGISTRY",
  "docs/AF001-TRACEABILITY.md": "TRACEABILITY_OPEN_DECISION_REGISTRY",
  "contracts/AF001-AF-D-INSTANCE-ADMISSION-BINDING.json": "CANONICAL_AF_D_REFERENCE_INSTANCE_ADMISSION_BINDING",
  "registries/AF001-AF-D-REFERENCE-INSTANCES.json": "CANONICAL_BOUNDED_AF_D_REFERENCE_INSTANCE_MANIFEST"
}
```

There must be exactly one `CANONICAL_ARCHITECTURE_MASTER` role. Textual claims do not establish authority by themselves.

## 3. Authority matrix

| Plane / artifact | May create canonical world truth? | May independently create knowledge evidence? | Projection role | Notes |
|---|---:|---:|---|---|
| Player input | No | No | intent/request only | raw text is untrusted |
| World/rules/affordance authority | Yes through authorized transitions/events | No | canonical resolution | owns legality/world transition boundary |
| Capability/state resolution | Yes through authorized receipts/events when implemented | No | current capability/state projections | AF-001 freezes interface only |
| Canonical event store | system of record | evidence carrier | none | append-preserved; no rewrite-in-place |
| Materialized world state | No independent truth | No | rebuildable current projection | derives from evidence/rules |
| Provenance-bearing acquisition/perception path | No new physical truth | **Yes, as acquisition evidence only after a valid channel** | feeds recipient-local projections | SAW/HEARD/WAS_TOLD etc. require mode-specific semantics |
| PlayerChronicle / PlayerSnapshot | No | **No** | recipient-local projection/cache | may materialize knowledge only from acquisition evidence |
| NPCPerceptionStream | No | No independent creation | recipient-local ordered index | references provenance-bearing perception events |
| NPCEpisodicMemory / BeliefState / relationship | No | **No** | recipient-local projections | cannot upgrade inference/summary into source evidence |
| Story/Narrative design | No | No | authored constraints/opportunities | not world truth |
| Narrative Opportunity / World Echo | No | No | proposes legal candidates | `NO_VALID_OPPORTUNITY` is valid |
| PX | No | No | ranks/surfaces legal candidates | cannot invent facts/knowledge/success |
| AI Director | No | No | staging/presentation | downstream read-only |
| Renderer | No | No | pixels/audio | contradiction is render failure |
| Publication/spectator | No | No | audience projection | no flow-back into player/NPC knowledge |

Frozen order:

`WORLD/RULES > CAPABILITY/STATE > KNOWLEDGE/MEMORY > NARRATIVE OPPORTUNITY > PX > AI DIRECTOR > RENDERER/PUBLICATION`

## 4. State ownership matrix

| Material fact | Canonical owner | Projection/index copy | Authorized mutation source | Rebuild direction / invariant |
|---|---|---|---|---|
| legal/social ownership | `ObjectAggregate.owner_ref` | social/UI views | future ownership-transfer event | ownership events -> `owner_ref`; never infer from possession |
| physical possession | `ObjectAggregate.possessor_ref` | `ActorAggregate.inventory_refs` | PICK/DROP/THROW or other authorized possession transition | object possession -> actor inventory; exactly one possessor |
| inventory | derived from possession truth | `ActorAggregate.inventory_refs` | no independent mutation | scan `possessor_ref`; inventory is not second truth |
| worn state | `OutfitState.slot_bindings` | presentation snapshot | wear/unwear/outfit event | possession does not imply worn |
| equipped state | `EquipmentLoadout.equipped_object_refs` | capability/presentation views | equip/unequip event | inventory does not imply equipped |
| actor/object location | each aggregate `scene_id/zone_id` | scene/query/render indexes | movement/transfer event | carried object location agrees with possessor |
| knowledge acquisition evidence | provenance-bearing acquisition/perception event path | PlayerChronicle/NPC memory/belief/relationship | valid mode-specific acquisition | evidence -> recipient-local projection, never reverse |

### R002 legacy possession compatibility

Accepted runtime uses `ObjectState.owner_actor_id` as the current physical holder/inventory actor. Therefore:

`ObjectState.owner_actor_id -> ObjectAggregate.possessor_ref`

It does **not** map to `ObjectAggregate.owner_ref`. R002 has no lossless legal/social ownership field, so legacy legal ownership is `UNKNOWN / NOT_MODELED` absent separate evidence. `ActorState.inventory_refs` is the accepted validated index side and rebuilds from physical possession truth in the AF-B model.

## 5. Event compatibility profile

Accepted source event profile:

`LEGACY_R001_R002_EVENT_PROFILE = {event_id, event_type, actor_id, scene_id, baseline_version, payload, caused_by_action_id}`

Future profile:

`AF001_VNEXT_EVENT_ENVELOPE = {event_id, event_type, schema_version, ruleset_version, world_id, authority_scope_ref, ordering_or_version_cursor, payload, ...optional compatibility fields}`

Only evidence-backed mappings are legal. `baseline_version` remains legacy baseline provenance and is not schema/ruleset provenance. Missing vNext fields remain `UNKNOWN/NOT_APPLICABLE` unless authentic external replay context proves them. Existing source events are never rewritten. Legacy history remains replayable under its accepted profile. vNext becomes mandatory only for new events after a later bounded runtime migration task + independent review + Control Tower release.

## 6. Cross-module type-reference inventory

The unified contract registry resolves the current Freeze surface. At minimum the following must exist with version, domain, authority owner and implementation state:

- AF-A coordination-only candidate interfaces: `WorldOrchestrationPlan`, `DomainChangeNotice`, `SimulationFidelityPolicy`, `DeferredConcretizationReceipt`, `TemporalCompressionPlan`, `DomainModuleManifest`. None owns canonical data or direct event-commit authority.
- AF-B: `WorldInstance`, `WorldFrame`, `Scene`, `Zone`, `Portal`, `ActorAggregate`, `ObjectAggregate`, `PlayerIdentity`, plus vNext candidate `InstitutionAggregate`, `EntityLifecycleReceipt`, `PlaceHistoryProjection`.
- AF-C: `ActorBaseProfile`, `SkillLedger`, `DerivedCapability`, `ActionDemandProfile`, `ActionResolutionReceipt`, `InjuryState`, `EquipmentLoadout`.
- AF-D: `ActorPresentationState`, `OutfitState`, `DressingState`, `ActorAppearanceSnapshot`, `View`, `MediaAsset`, `MediaVersion`.
- AF-E: `PlayerChronicle`, `PlayerSnapshot`, `IntentBelief`, `CharacterCore`, `EnactedPersonaHypothesis`, `NPCPerceptionEvent`, `NPCPerceptionStream`, `NPCEpisodicMemory`, `BeliefState`, `NPCPlayerRelationshipState`, plus vNext candidate `LegalProcessProjection`.
- AF-F: `StoryDNA`, `StoryBible`, `HardCausalAnchor`, `SoftDramaticAttractor`, `Storylet`, `EventDeckEntry`, `InformationPacket`, `NarrativePromise`.
- AF-G: `NarrativeOpportunityBroker`, `EncounterCandidate`, `WorldEchoOpportunity`, `ResponseConcept`, `PlayerAutoExpressionPolicy`, plus vNext candidate `NarrativeInfluenceReceipt`.
- AF-H: `DIRECTOR-BEAT-PACKET`, `PublicationProjection`, plus vNext candidate `DramaticPresentationIntent`, `AudienceExposurePolicy`.

`EventDeckEntry` is explicitly an alias/wrapper of `Storylet` plus deck-selection metadata. It is not an independent world-truth type.

For the resolved AF-C substrate, the v1.1 contract makes `ActorBaseProfile.profile_schema_ref` and `ActorBaseProfile.ruleset_family_ref` immutable alongside `profile_version`, `base_attribute_map` and source evidence. `SkillLedger` remains a separate persistent ledger; `DerivedCapability` stays derived; `ActionDemandProfile.method_id` and `ruleset_version` bind method-specific demand policy; `ActionResolutionReceipt.ruleset_version` and deterministic random provenance bind replay policy. Legacy v1.0 profiles remain replayable only under their accepted historical profile and may not be silently read as v1.1 runtime input. The compatibility boundary is machine-defined in `versioning_and_migration.actor_base_profile_migration`: a v1.1 transformation needs explicit compatibility or transformation evidence in authorized source-event provenance, and unknown/mismatched schema fails closed. This governance change does not authorize I2.

## 7. Dependency graph

```text
R001/R002 accepted foundations
  -> AF-A Identity/Event/Authority
      -> AF-B Actor/Object/Spatial
          -> AF-C Capability/Injury
          -> AF-D Appearance/Asset
      -> AF-E Perception/Memory/Knowledge/Relationship
      -> AF-F Story/Information
          -> AF-G Opportunity/World Echo/PX
              -> AF-H AI Director/Renderer/Publication
```

Cross-links: AF-B->AF-D, AF-C->AF-D, AF-E->AF-F, AF-E->AF-G, AF-F->AF-G, AF-D+AF-E+AF-G->AF-H.

MIDS vNext adds coordination cross-links without changing authority order:

```text
AF-A WorldOrchestrationPlan (coordination only)
  -> typed request to owning AF domain
  <- owning domain receipt / canonical event ref
  -> DomainChangeNotice (derived causal hint)
  -> receiving domain independently validates

AF-A/B DeferredConcretizationReceipt -> owning-domain event (never prior-event edit)
AF-F/G NarrativeInfluenceReceipt -> already-legal candidate selection
AF-H AudienceExposurePolicy -> PublicationProjection (never AF-E acquisition)
AF-H DramaticPresentationIntent -> existing DIRECTOR-BEAT-PACKET extension
```

No post-freeze runtime task may silently depend on an unresolved lower-layer architectural decision. Deferred ruleset/balance policy must remain explicit and version-bound, but it does not by itself re-open an already resolved architectural substrate.

## 8. Design-source traceability

| Source | AF destinations | Freeze disposition |
|---|---|---|
| Issue #5 `PX-DESIGN-001` | AF-A/B/G/H | consolidated, no implementation authority |
| Issue #6 `ASSET-DESIGN-001` | AF-B/D/H | interfaces frozen |
| Issue #7 `REACT-DESIGN-001` | AF-E/G/H | interfaces frozen, runtime not implemented |
| Issue #8 `NARRATIVE-DESIGN-001` | AF-E/F/G | player continuity/persona/storylet boundaries frozen |
| Issue #9 `MEMORY-DESIGN-001` | AF-E | evidence/projection boundary frozen; backend/math open |
| Issue #10 `GOV-DESIGN-001` | all | governance/landing authority |
| Issue #11 `STORY-DESIGN-001` | AF-F/G | narrative authority boundary frozen |
| Issue #12 `CAPABILITY-DESIGN-001` | AF-C/D | original capability candidates and interface/order/provenance design; historical evidence preserved |
| Issue #13 `ENCOUNTER-STATE-DESIGN-001` | AF-C/D/F/G/H | opportunity/presentation interfaces frozen |
| Issue #14 `INTEGRATION-DESIGN-001` | AF-A..H | integrated into single master/registry |
| Issue #15 `AF-001` | AF-A..H | accepted + merged canonical architecture freeze |
| Issue #24 / PR #25 `CAP-EVAL-001` | AF-C | executable evaluation evidence only; candidates non-canonical; no I2 authority |
| Issue #26 / PR #27 `CAP-EVAL-002` | AF-C | held-out robustness evidence only; Independent Review `5004524795` accepted exact head `91a46c7c1ac8a5c7e13f389a81497a5307166ca0`; no I2 authority |
| Issue #28 `CAPABILITY-ARCH-RESOLUTION-001` | AF-C governance | Control Tower architectural substrate resolution; tuning/balance/genre policy deferred; no runtime release |
| Issue #102 `MIDS-WORLD-DESIGN-001` | research/governance | shadow discovery/replay tooling remains separate; its candidate output cannot write canonical architecture |
| Issue #103 `MIDS-ARCH-001` + snapshot `MIDS-ARCH-001-SPEC-2026-09-02-R1` | AF-A..H | user-confirmed design compiled into this architecture-only candidate; independent exact-head review required |
| Evidence head `f20c097de5d91ba580b807a2bf86e10b0fe5439d` | AF-A..H | three MIDS design files are immutable non-canonical evidence; classification recorded in `docs/research/AWRSE-MIDS-TO-AF-VNEXT-MAPPING-v0.1.md` |

Candidate skills S13-S61 remain `CANDIDATE / NOT_PROMOTED`.

## 9. Golden Scenario coverage matrix

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

The additive `mids_vnext_architecture_checks` registry covers architecture-only cross-domain cases without pretending to execute runtime:

| MIDS check | Main AF coverage | Critical prohibition |
|---|---|---|
| `PRICE_CONTROL_TO_BLACK_MARKET` | A/B/C/E/F/G | Orchestrator cannot mutate price, scarcity or social truth |
| `DEFERRED_TOWN_CONCRETIZATION` | A/B/F | Unknown cannot be invented or locked history re-rolled |
| `FALSE_ARREST_AND_PUBLIC_BELIEF` | A/B/E/F/H | Legal judgment and audience knowledge cannot rewrite truth/character knowledge |
| `LONG_HORIZON_BUTTERFLY_PAYOFF` | A/B/E/F/G/H | Payoff cannot retcon cause or lose causal provenance |
| `PLAYER_DEATH_SAME_WORLD_SUCCESSION` | A/B/E/F/H | Rebinding cannot erase death, fork world or transfer unsupported knowledge |
| `LONG_ABSENCE_AND_TEMPORAL_COMPRESSION` | A/B/E/H | Presentation compression cannot erase time or activate disabled modules |
| `PEACEFUL_ORDINARY_LIFE` | F/G/H | Narrative cannot force catastrophe or replace an empty set with illegality |

Human-readable scenario prose remains in the eval registry. Each scenario also has a machine `machine_spec` whose type refs and decision dependencies must resolve.

### FIGHTER_VS_SCHOLAR dependency disposition

The Golden file is revised in this governance-only slice so the Control Tower decision is executable at the contract boundary:
- it binds `ActorBaseProfile`, `SkillLedger`, `DerivedCapability`, `ActionDemandProfile` and `ActionResolutionReceipt` as separate type refs;
- it requires method/demand before outcome and feasibility before stochastic/graded resolution;
- it requires deterministic replay when randomness is used;
- it adds profile-schema/ruleset replay-admission fixtures for matching v1.1 provenance, missing provenance, mismatched provenance and an explicitly evidenced legacy-to-v1.1 transformation;
- it explicitly remains `CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED`.

Its retained references to `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001` now mean `HISTORICAL_TRACE_PLUS_DEFERRED_RULESET_BINDING_NOT_ARCHITECTURE_BLOCKER`.

For this scenario:
- architecture-blocking capability dependency: `NONE`;
- architectural substrate: `RESOLVED_ARCHITECTURAL_SUBSTRATE`;
- exact stat vector/weights/coefficients/thresholds: `DEFERRED_RULESET_TUNING`;
- player-facing tuning/calibration: `DEFERRED_PLAYER_BALANCE`;
- genre-extension pack policy: `DEFERRED_GENRE_EXTENSION_POLICY`;
- runtime authority: `I2A_ARCHITECTURALLY_UNBLOCKED_PENDING_SEPARATE_CONTROL_TOWER_RELEASE`.

The retained decision refs therefore preserve history and force future I2A implementation to select an explicit versioned ruleset; they no longer block architecture merely because tuned policy remains deferred.

## 10. Migration/versioning obligations

Breaking authority/identity/event/ownership/provenance changes require explicit migration spec, replay/rebuild impact analysis, affected Golden updates and fresh independent review. Source events never change in place. Snapshots/caches may be rebuilt from exact source cursor/version.

`CAPABILITY-ARCH-RESOLUTION-001` performs a compatible machine-contract migration from the legacy v1.0 `ActorBaseProfile` shape to the v1.1 profile-schema/ruleset provenance shape. Legacy profiles remain valid for accepted legacy replay only; transformation requires explicit authorized evidence, and missing or mismatched v1.1 provenance fails closed. The contract, Golden fixtures and replay-impact record are versioned together. Runtime semantics remain unchanged and this migration does not authorize I2.

## 11. Historical R001/R002 non-regression map

- R001 authority: raw user text untrusted; player cannot control target internal state/world rules.
- R001 event sourcing: append-preserved evidence and replay for implemented domains.
- R001 live-state seal remains fail-closed.
- R001 renderer remains projection-only.
- R002 spatial zone/scene/adjacency/reachability integrity remains fail-closed.
- R002 possession graph remains bidirectionally consistent.
- R002 SAW/HEARD/WAS_TOLD provenance remains mode-specific; unsupported modes fail closed.
- R002 render projection remains contradiction-checked.

## 12. OPEN_DECISION registry with resolved-decision status

Each section below is independently bounded. Validator must inspect only the text between one `### OD-...` heading and the next `### OD-...` or next level-2 heading.

A historical `OD-*` identifier is durable traceability. Its presence does not imply that every layer remains open forever. Where an explicit Control Tower decision resolves architecture but leaves tuning open, this section records both states instead of deleting the old evidence. The legacy five-field metadata remains present for backwards-compatible traceability validation even when its current architectural status is resolved.

### OD-CONCURRENCY-001 — canonical concurrency/arbitration algorithm
- **Current status:** `OPEN_DECISION`.
- **Competing options:** per-aggregate optimistic versioning; deterministic tick resolver; ordered DecisionWindow scheduler; hybrid by WorldScope.
- **Evidence:** current contracts require deterministic ordering but R001/R002 do not exercise multiplayer conflict load.
- **Dependency:** shared-object conflicts and interruptible activities.
- **Risk:** wrong scheduler can bake latency assumptions into semantics or break replay determinism.
- **Required experiment/research:** two-player same-object conflict corpus plus deterministic replay benchmark.

### OD-CAPABILITY-ATTR-001 — capability representation architecture and ruleset vector
- **Current architecture status:** `RESOLVED_ARCHITECTURAL_SUBSTRATE` by Control Tower `CAPABILITY-ARCH-RESOLUTION-001` / Issue #28.
- **Competing options:** historically small mundane core; richer genre-neutral vector; action-demand-only primitives. These remain evidence of the original monolithic decision, not equally open architecture alternatives after Issue #28.
- **Evidence:** Issue #12 candidate design, CAP-EVAL-001 executable evaluation, CAP-EVAL-002 held-out robustness evaluation, Independent Review `5004524795`, and the explicit Control Tower split in Issue #28.
- **Dependency:** `ActionDemandProfile`, progression and genre extensions. Architecture no longer waits on the exact vector; any future runtime still depends on an explicit versioned ruleset choice.
- **Risk:** stat soup, hidden LLM judgment, or silently freezing one evaluation vector as eternal ontology.
- **Required experiment/research:** architecture-resolution evidence is complete for this split; future ruleset tuning still requires bounded balance/usability/genre validation before its chosen values become runtime policy.
- **Historical OPEN_DECISION preserved:** yes. Original competing options were small mundane core, richer genre-neutral vector and action-demand-only primitives. Issue #12, CAP-EVAL-001 and CAP-EVAL-002 remain immutable evidence history rather than being rewritten to look retrospectively resolved.
- **Accepted evidence chain:** Issue #12 -> Issue #19 planning -> Issue #24 / merged PR #25 CAP-EVAL-001 -> Issue #26 / merged PR #27 CAP-EVAL-002 -> Independent Review `5004524795` `ACCEPT` on exact head `91a46c7c1ac8a5c7e13f389a81497a5307166ca0` -> Issue #28 Control Tower architecture decision.
- **Resolved architectural substrate:** `ActorBaseProfile` is persistent/versioned actor capability truth; `SkillLedger` is separate persistent competence truth; `DerivedCapability` is current derived state; `ActionDemandProfile` is method-specific; task-local logic cannot invent actor capability truth; `base_attribute_map` belongs to versioned ruleset/schema families rather than one eternal vector; genre capability must use explicit extension namespaces/resources/skills; profile/demand/receipt provenance must remain sufficient for replay/migration.
- **Candidate disposition:** `RICH_GENRE_NEUTRAL_V1` is not a universal canonical base vector; `DEMAND_PRIMITIVES_V1` may express demand semantics but cannot mint free task-local actor truth; `SMALL_CORE_V1` may be a bounded initial/reference ruleset family but is not an eternal global ontology.
- **Deferred ruleset track:** `DEFERRED_RULESET_TUNING` for exact mundane stat list/ranges, strength-vs-power split, agility-vs-balance split, task/skill weights, progression values and injury/condition coefficients.
- **Deferred player track:** `DEFERRED_PLAYER_BALANCE` for player-facing stat/balance presentation and calibration.
- **Deferred genre track:** `DEFERRED_GENRE_EXTENSION_POLICY` for exact genre pack naming/composition/adoption while the explicit-extension boundary itself is resolved architecture.
- **Architecture dependency effect:** no Golden scenario is architecture-blocked merely because the above tuning/presentation policy remains deferred. Any future runtime release must still select and bind an explicit versioned ruleset.
- **Evidence caution:** CAP-EVAL synthetic fixtures remain evidence, not authority to promote their numeric values or candidate vector into canonical gameplay tuning.

### OD-CAPABILITY-MATH-001 — resolution substrate and ruleset mathematics
- **Current architecture status:** `RESOLVED_ARCHITECTURAL_SUBSTRATE` by Control Tower `CAPABILITY-ARCH-RESOLUTION-001` / Issue #28.
- **Competing options:** historically additive/multiplicative stack, tagged priority, per-demand rules, deterministic margin and bounded seeded stochastic variants. They remain evaluation/ruleset candidates rather than unresolved universal architecture choices.
- **Evidence:** Issue #12 candidate equations, CAP-EVAL-001 and CAP-EVAL-002 executable evidence, stack-nonlocality failure, Independent Review `5004524795`, and Issue #28's explicit architecture/tuning split.
- **Dependency:** `DerivedCapability` and `ActionResolutionReceipt` runtime. Architecture fixes feasibility and auditable ordering substrate while exact stacking/threshold/balance policy remains ruleset-versioned.
- **Risk:** fake precision, non-local impairment leakage, non-monotonicity, replay mismatch, or promoting an evaluation formula into universal gameplay law.
- **Required experiment/research:** architecture-resolution evidence is complete for the feasibility/margin split; future ruleset tuning still requires bounded balance/calibration tests for stacking, coefficients, thresholds and optional probability policy.
- **Historical OPEN_DECISION preserved:** yes. Original competing options included additive/multiplicative stack, tagged priority, per-demand rules and deterministic margin variants. CAP-EVAL artifacts remain evaluation evidence and are not rewritten.
- **Accepted evidence chain:** Issue #12 -> Issue #19 planning -> Issue #24 / merged PR #25 CAP-EVAL-001 -> Issue #26 / merged PR #27 CAP-EVAL-002 -> Independent Review `5004524795` `ACCEPT` -> Issue #28 Control Tower architecture decision.
- **Resolved architectural substrate:** hard feasibility precedes graded/stochastic resolution; infeasible actions have no fabricated numeric margin and cannot get lucky success; effective capability derives deterministically from declared versioned inputs; for feasible graded ordering the minimum auditable substrate is `Margin = EffectiveCapability - DifficultyOrResistance`; relevant impairment is function-local; success and hazard/injury are separate axes; outcome bands are ruleset-versioned; randomness is optional/downstream feasibility and must carry exact-replay provenance.
- **CAP-EVAL-002 interpretation:** the held-out stack-nonlocality failure is evidence against canonicalizing the challenged stacking policies, not evidence against the deterministic feasibility/margin substrate.
- **Non-canonical candidates:** `ADDITIVE_MULTIPLICATIVE_STACK_V1`, `TAGGED_PRIORITY_V1` and `BOUNDED_SEEDED_STOCHASTIC_V1` remain evaluation/ruleset candidates, not universal canonical architecture. CAP-EVAL's exact formulas, thresholds and coefficients are not promoted here.
- **Deferred ruleset track:** `DEFERRED_RULESET_TUNING` for exact stacking rules, task/skill weights, condition coefficients, outcome-band thresholds and other gameplay coefficients.
- **Deferred player track:** `DEFERRED_PLAYER_BALANCE` for player-facing probability calibration and balance presentation.
- **Architecture dependency effect:** deterministic feasibility/margin architecture is resolved; exact tuned policy remains a required versioned ruleset choice for any future runtime release, not a reason to reclassify the substrate as architecturally unresolved.

### OD-MEMORY-STORE-001 — persistent backend/event-store technology
- **Competing options:** SQLite/embedded; server relational; event store + projections; hybrid tiers.
- **Evidence:** Issue #9 requires structured persistence but chooses no backend.
- **Dependency:** memory, player continuity, privacy and operations.
- **Risk:** premature coupling or inability to rebuild/audit.
- **Required experiment/research:** volume/query model, restart benchmarks, backup/migration tests.

### OD-MEMORY-DECAY-001 — memory accessibility/forgetting model
- **Competing options:** rule bands; retrieval strength; salience/relationship-aware decay; no ordinary MVP decay.
- **Evidence:** Issue #9 separates durable evidence from accessibility but has no validated weights.
- **Dependency:** NPC retrieval and long-horizon callback quality.
- **Risk:** lore drift or context flooding.
- **Required experiment/research:** long-history replay plus retrieval precision/recall and human callback evaluation.

### OD-RELATIONSHIP-MATH-001 — relationship projection dimensions/weights
- **Competing options:** categorical state machine; bounded multidimensional numeric; event-rule deltas; hybrid.
- **Evidence:** Issue #9 rejects a single morality score but does not finalize update math.
- **Dependency:** NPC behavior/social callbacks.
- **Risk:** opaque drift or oversimplification.
- **Required experiment/research:** adversarial social histories, rebuild equivalence and sensitivity review.

### OD-GENRE-REGISTRY-001 — GenreEngine registry governance
- **Competing options:** fixed core + extensions; data-driven packs; hierarchical ontology.
- **Evidence:** Issue #11 defines multi-axis extensible genres.
- **Dependency:** StoryDNA validation/authoring.
- **Risk:** rigid enum or synonym explosion.
- **Required experiment/research:** encode representative mixed-genre stories and test query/validation ergonomics.

### OD-CLUE-QUALITY-001 — clue/reveal/branch-quality metrics
- **Competing options:** authored invariants; graph solvability; evidence sufficiency; hybrid human+automated eval.
- **Evidence:** Issues #11/#14 require branch quality without a validated universal metric.
- **Dependency:** future Storylet/reveal scheduling.
- **Risk:** simplistic metrics falsely certify bad/unsolvable branches.
- **Required experiment/research:** mystery corpus, early-solve variants, graph tests and human playtests.

### OD-PX-SCORING-001 — PX ranking objective/weights
- **Competing options:** constrained multi-objective; context rule packs; learned opt-in ranking; hybrid.
- **Evidence:** Issue #5 rejects one universal fun score.
- **Dependency:** PXRankingReceipt/runtime.
- **Risk:** hidden manipulation or engagement optimization over agency.
- **Required experiment/research:** transparent dimensions, offline rankings, opt-in player study and guardrail review.

### OD-COMMENTARY-BUDGET-001 — World Echo thresholds/cooldowns
- **Competing options:** fixed scene/speaker budgets; salience adaptive; director paced; hybrid.
- **Evidence:** Issue #7 requires anti-repeat without validated thresholds.
- **Dependency:** World Echo runtime.
- **Risk:** chatter spam or silent world memory.
- **Required experiment/research:** repeated-revisit simulations and human evaluation across context types.

### OD-ENCOUNTER-DENSITY-001 — opportunity density/contrivance budget
- **Competing options:** region density rules; adaptive pacing budget; story-critical capped retries; hybrid.
- **Evidence:** Issue #13 requires plausibility and anti-pattern constraints but no production density is validated.
- **Dependency:** NarrativeOpportunityBroker/EncounterCandidate runtime.
- **Risk:** contrived encounters or a barren world.
- **Required experiment/research:** route/population simulations, encounter-pattern analysis and player plausibility study.

### OD-PUBLICATION-POLICY-001 — spectator/public audience knowledge policy
- **Competing options:** strict player-equivalent view; omniscient spectator classes; delayed reveal tiers; per-project policy.
- **Evidence:** Issues #5/#14 require player/public knowledge separation without final product policy.
- **Dependency:** PublicationProjection and spectator recap.
- **Risk:** spoilers/privacy leak or accidental flow-back into gameplay knowledge.
- **Required experiment/research:** audience-class threat model, spoiler/privacy tests and product-format evaluation.

### OD-DIRECTOR-ADAPTER-001 — AWRSE to AI Director transport/adapter
- **Competing options:** in-process typed call; versioned file/message packet; service API; queue/event bridge.
- **Evidence:** AF-H freezes semantic packet authority but no runtime integration is authorized.
- **Dependency:** future AI Director federation.
- **Risk:** transport-specific assumptions leak into canonical semantics.
- **Required experiment/research:** contract serialization round-trip, version skew tests and failure-isolation prototype after freeze acceptance.

### OD-FIDELITY-POLICY-001 — adaptive simulation fidelity thresholds and budgets
- **Current status:** `OPEN_DECISION / ARCHITECTURE_BOUNDARY_RESOLVED_POLICY_VALUES_DEFERRED`.
- **Competing options:** fixed domain tiers; causal-risk adaptive tiers; attention/resource-budget scheduler; hybrid with per-domain minimums.
- **Evidence:** MIDS P011/P020 require adaptive fidelity and modular domains while preserving established history and conservation.
- **Dependency:** `SimulationFidelityPolicy`, domain update scheduling, background-world cost and reproducibility.
- **Risk:** hidden truth loss, inconsistent updates, resource creation or nondeterministic replay if fidelity becomes an authority switch.
- **Required experiment/research:** active/background/dormant world corpus measuring cost, causal divergence, conservation and replay stability.

### OD-NARRATIVE-INFLUENCE-POLICY-001 — narrative influence dimensions, weights and budget
- **Current status:** `OPEN_DECISION / ARCHITECTURE_BOUNDARY_RESOLVED_POLICY_VALUES_DEFERRED`.
- **Competing options:** fixed transparent dimensions; genre-scoped rule packs; bounded learned ranking; hybrid with hard human-authored caps.
- **Evidence:** MIDS P005 permits bounded audited influence over legal opportunities, while AF-F/G forbid fact/outcome authority.
- **Dependency:** `NarrativeInfluenceReceipt`, `PXRankingReceipt`, storylet selection and player-facing narrative exposure preference.
- **Risk:** covert railroading, engagement optimization over agency, or accidental mutation of feasibility/outcome probability.
- **Required experiment/research:** offline legal-candidate ranking corpus, counterfactual agency audit, budget exhaustion behavior and human review.

### OD-LONG-ABSENCE-001 — optional world advancement while player is absent
- **Current status:** `OPEN_DECISION / DEFAULT_FREEZE_RESOLVED_OPTIONAL_ADVANCE_DEFERRED`.
- **Competing options:** always freeze; opt-in elapsed-time cap; authored safe windows; causal-risk bounded catch-up simulation.
- **Evidence:** MIDS P016 confirms default close/reopen freeze and allows a later optional long-absence policy without choosing threshold or algorithm.
- **Dependency:** canonical time cursor, `SimulationFidelityPolicy`, `TemporalCompressionPlan`, interruption and player fairness.
- **Risk:** irreversible surprise, excessive catch-up cost, missed decisions, or divergent replay.
- **Required experiment/research:** long-absence scenario matrix with caps, critical interrupts, deterministic catch-up and user-consent evaluation.

### OD-ENTITY-PROVENANCE-001 — split/composition and material provenance depth
- **Current status:** `OPEN_DECISION / PERSISTENT_ID_AND_NO_REUSE_RESOLVED_PROVENANCE_DEPTH_DEFERRED`.
- **Competing options:** direct parent refs only; material-lot provenance graph; domain-specific composition receipts; tiered provenance by causal importance.
- **Evidence:** MIDS P025-P027 require persistent identity, destroyed-ID retention and new IDs for split/composed outputs, but defer atom-level provenance.
- **Dependency:** `EntityLifecycleReceipt`, resource conservation, repair/crafting and forensic evidence.
- **Risk:** identity laundering, duplication, storage explosion or inability to explain material origin.
- **Required experiment/research:** destruction/split/merge/repair/crafting corpus measuring identity correctness, conservation and provenance cost.

## 13. Governance

AF-001 Architecture Freeze is independently accepted and merged through the Independent Reviewer + Control Tower gate. This file remains the canonical traceability/dependency/decision entrypoint.

`OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001` are now durable historical decision records with `RESOLVED_ARCHITECTURAL_SUBSTRATE` plus explicit deferred policy tracks. All other unresolved ODs remain open until separately authorized, accepted decisions resolve them.

Capability runtime authority after this governance slice is exactly:

`I2A_ARCHITECTURALLY_UNBLOCKED_PENDING_SEPARATE_CONTROL_TOWER_RELEASE`

It is not `I2_RUNTIME_IMPLEMENTATION_AUTHORIZED`.

`RUNTIME_SEMANTICS_UNCHANGED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`

`I2_RUNTIME_AUTHORITY_NOT_GRANTED=true`

Future Workers may not infer implementation authority from this registry and may not self-review, ACCEPT, merge, or release follow-on runtime scope.
