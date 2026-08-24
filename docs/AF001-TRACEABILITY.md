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
  "docs/AF001-TRACEABILITY.md": "TRACEABILITY_OPEN_DECISION_REGISTRY"
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

- AF-B: `WorldInstance`, `WorldFrame`, `Scene`, `Zone`, `Portal`, `ActorAggregate`, `ObjectAggregate`, `PlayerIdentity`.
- AF-C: `ActorBaseProfile`, `SkillLedger`, `DerivedCapability`, `ActionDemandProfile`, `ActionResolutionReceipt`, `InjuryState`, `EquipmentLoadout`.
- AF-D: `ActorPresentationState`, `OutfitState`, `DressingState`, `ActorAppearanceSnapshot`, `View`, `MediaAsset`, `MediaVersion`.
- AF-E: `PlayerChronicle`, `PlayerSnapshot`, `IntentBelief`, `CharacterCore`, `EnactedPersonaHypothesis`, `NPCPerceptionEvent`, `NPCPerceptionStream`, `NPCEpisodicMemory`, `BeliefState`, `NPCPlayerRelationshipState`.
- AF-F: `StoryDNA`, `StoryBible`, `HardCausalAnchor`, `SoftDramaticAttractor`, `Storylet`, `EventDeckEntry`, `InformationPacket`, `NarrativePromise`.
- AF-G: `NarrativeOpportunityBroker`, `EncounterCandidate`, `WorldEchoOpportunity`, `ResponseConcept`, `PlayerAutoExpressionPolicy`.
- AF-H: `DIRECTOR-BEAT-PACKET`, `PublicationProjection`.

`EventDeckEntry` is explicitly an alias/wrapper of `Storylet` plus deck-selection metadata. It is not an independent world-truth type.

For the resolved AF-C substrate, the current contract surface is intentionally retained rather than migrated in this governance-only slice. `ActorBaseProfile.profile_version` plus source evidence identifies the versioned profile/schema family; `SkillLedger` remains a separate persistent ledger; `DerivedCapability` stays derived; `ActionDemandProfile.method_id` and `ruleset_version` bind method-specific demand policy; `ActionResolutionReceipt.ruleset_version` and deterministic random provenance bind replay policy. Any later need for stronger explicit schema fields is a separate compatible contract/migration task, not authority to implement I2 here.

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

Human-readable scenario prose remains in the eval registry. Each scenario also has a machine `machine_spec` whose type refs and decision dependencies must resolve.

### FIGHTER_VS_SCHOLAR dependency disposition

The Golden file is not rewritten in this governance-only slice because its current machine contract is already compatible with the Control Tower decision:
- it already binds `ActorBaseProfile`, `SkillLedger`, `DerivedCapability`, `ActionDemandProfile` and `ActionResolutionReceipt` as separate type refs;
- it already requires method/demand before outcome and feasibility before stochastic/graded resolution;
- it already requires deterministic replay when randomness is used;
- its human replay expectation already binds same ruleset/seed provenance;
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

`CAPABILITY-ARCH-RESOLUTION-001` deliberately performs no machine-contract schema migration. It changes governance meaning while preserving the existing compatible AF-C interface surface. Runtime semantics remain unchanged.

## 11. Historical R001/R002 non-regression map

- R001 authority: raw user text untrusted; player cannot control target internal state/world rules.
- R001 event sourcing: append-preserved evidence and replay for implemented domains.
- R001 live-state seal remains fail-closed.
- R001 renderer remains projection-only.
- R002 spatial zone/scene/adjacency/reachability integrity remains fail-closed.
- R002 possession graph remains bidirectionally consistent.
- R002 SAW/HEARD/WAS_TOLD provenance remains mode-specific; unsupported modes fail closed.
- R002 render projection remains contradiction-checked.

## 12. OPEN_DECISION and resolved-decision registry

Each section below is independently bounded. Validator must inspect only the text between one `### OD-...` heading and the next `### OD-...` or next level-2 heading.

A historical `OD-*` identifier is durable traceability. Its presence does not imply that every layer remains open forever. Where an explicit Control Tower decision resolves architecture but leaves tuning open, this section records both states instead of deleting the old evidence.

### OD-CONCURRENCY-001 — canonical concurrency/arbitration algorithm
- **Current status:** `OPEN_DECISION`.
- **Competing options:** per-aggregate optimistic versioning; deterministic tick resolver; ordered DecisionWindow scheduler; hybrid by WorldScope.
- **Evidence:** current contracts require deterministic ordering but R001/R002 do not exercise multiplayer conflict load.
- **Dependency:** shared-object conflicts and interruptible activities.
- **Risk:** wrong scheduler can bake latency assumptions into semantics or break replay determinism.
- **Required experiment/research:** two-player same-object conflict corpus plus deterministic replay benchmark.

### OD-CAPABILITY-ATTR-001 — capability representation architecture and ruleset vector
- **Current architecture status:** `RESOLVED_ARCHITECTURAL_SUBSTRATE` by Control Tower `CAPABILITY-ARCH-RESOLUTION-001` / Issue #28.
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
