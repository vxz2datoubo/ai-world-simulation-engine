# AF-001 Traceability, Dependency, Authority and OPEN_DECISION Register

Status: `ARCHITECTURE_FREEZE_CANDIDATE / SINGLE_TRACEABILITY_ENTRYPOINT`

This is the single AF-001 traceability/dependency/open-decision registry. It does not compete with `ARCHITECTURE.md`, which is the canonical architecture master. Machine contracts live in `contracts/AF001-LIVING-STORY-CONTRACTS.json`; Golden executable specifications live in `evals/AF001-GOLDEN-SCENARIOS.json`.

## 1. Fresh source baseline

AF-001 base: `ebd2ca2bad948b737f967ae09c000643ec2f9929`.

That `main` is the Control Tower merge of accepted R002 PR #4. AF-001 preserves R001/R002 and does not reopen their runtime semantics.

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

No post-freeze runtime task may silently depend on an unresolved lower-layer `OPEN_DECISION`.

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
| Issue #12 `CAPABILITY-DESIGN-001` | AF-C/D | interface/order/provenance frozen; math open |
| Issue #13 `ENCOUNTER-STATE-DESIGN-001` | AF-C/D/F/G/H | opportunity/presentation interfaces frozen |
| Issue #14 `INTEGRATION-DESIGN-001` | AF-A..H | integrated into single master/registry |
| Issue #15 `AF-001` | AF-A..H | current authorized architecture-only task |

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

Human-readable scenario prose remains in the eval registry. Each scenario also has a machine `machine_spec` whose type refs and OPEN_DECISION dependencies must resolve.

## 10. Migration/versioning obligations

Breaking authority/identity/event/ownership/provenance changes require explicit migration spec, replay/rebuild impact analysis, affected Golden updates and fresh independent review. Source events never change in place. Snapshots/caches may be rebuilt from exact source cursor/version.

## 11. Historical R001/R002 non-regression map

- R001 authority: raw user text untrusted; player cannot control target internal state/world rules.
- R001 event sourcing: append-preserved evidence and replay for implemented domains.
- R001 live-state seal remains fail-closed.
- R001 renderer remains projection-only.
- R002 spatial zone/scene/adjacency/reachability integrity remains fail-closed.
- R002 possession graph remains bidirectionally consistent.
- R002 SAW/HEARD/WAS_TOLD provenance remains mode-specific; unsupported modes fail closed.
- R002 render projection remains contradiction-checked.

## 12. OPEN_DECISION registry

Each section below is independently bounded. Validator must inspect only the text between one `### OD-...` heading and the next `### OD-...` or next level-2 heading.

### OD-CONCURRENCY-001 — canonical concurrency/arbitration algorithm
- **Competing options:** per-aggregate optimistic versioning; deterministic tick resolver; ordered DecisionWindow scheduler; hybrid by WorldScope.
- **Evidence:** current contracts require deterministic ordering but R001/R002 do not exercise multiplayer conflict load.
- **Dependency:** shared-object conflicts and interruptible activities.
- **Risk:** wrong scheduler can bake latency assumptions into semantics or break replay determinism.
- **Required experiment/research:** two-player same-object conflict corpus plus deterministic replay benchmark.

### OD-CAPABILITY-ATTR-001 — final core attribute vector
- **Competing options:** small mundane core; richer genre-neutral vector; action-demand-only primitives.
- **Evidence:** Issue #12 proposes candidates but does not validate a final list.
- **Dependency:** ActionDemandProfile, progression and genre extensions.
- **Risk:** stat soup or hidden LLM judgment.
- **Required experiment/research:** cross-domain task corpus, ablation and designer usability study.

### OD-CAPABILITY-MATH-001 — modifier stacking and stochastic curve
- **Competing options:** additive/multiplicative stack; tagged priority; per-demand rules; deterministic margin for some actions.
- **Evidence:** Issue #12 equations are research candidates only.
- **Dependency:** DerivedCapability and ActionResolutionReceipt runtime.
- **Risk:** fake precision, non-monotonicity or replay mismatch.
- **Required experiment/research:** property/sensitivity tests and fighter-vs-scholar parameter sweeps.

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

Final Architecture Freeze requires **Independent Reviewer + Control Tower**. Worker may implement this architecture-only remediation and provide exact-head evidence, but may not self-review, ACCEPT, merge or release R003.
