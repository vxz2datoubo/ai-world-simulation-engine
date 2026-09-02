# AWRSE Canonical Architecture

Status: `AF001_ARCHITECTURE_FREEZE_ACCEPTED / MERGED_CANONICAL`

Authority role: `CANONICAL_ARCHITECTURE_MASTER`.

This file is the single current architecture master for AWRSE. `contracts/AF001-LIVING-STORY-CONTRACTS.json` is the machine contract registry, `evals/AF001-GOLDEN-SCENARIOS.json` is the Golden executable-spec registry, and `docs/AF001-TRACEABILITY.md` is the traceability/dependency/OPEN_DECISION registry. Supporting artifacts refine this master and do not compete with it.

AF-001 is the accepted canonical architecture/contracts/eval foundation. It does **not** itself authorize gameplay runtime expansion. Accepted R001/R002 runtime behavior plus the bounded R003-I1A persistence/restart-replay and R003-I1B replay-inspection foundations are canonical implementation truth; any further runtime expansion still requires a separately released bounded task.

## 1. Product law

**Maximum Valid Freedom** means a player may attempt broad natural-language actions while the world remains authoritative about what is physically, socially, causally and role-consistently possible.

`AUTHORIAL_INTENT -> LEGAL_OPPORTUNITY -> PLAYER_INTENT -> WORLD_RESOLUTION -> CANONICAL_EVENT -> PERSISTENT_PROJECTION -> PERCEPTION/KNOWLEDGE -> CALLBACK/OPPORTUNITY -> PRESENTATION`

No downstream stage may silently rewrite an upstream fact. Generated pixels, prose summaries, LLM plans, narrative candidates and caches are never canonical world truth merely because they are plausible.

## 2. Frozen authority order

`WORLD/RULES AUTHORITY > CAPABILITY/STATE RESOLUTION > KNOWLEDGE/MEMORY > NARRATIVE OPPORTUNITY > PX RANKING > AI DIRECTOR > RENDERER/PUBLICATION`

1. Player controls only authorized attempted actions for their actor(s).
2. World/rules/affordance/topology decide legality and possible transitions.
3. Capability/state resolution, when later implemented, resolves feasible uncertain outcomes and side effects.
4. Canonical events are append-preserved evidence of committed truth.
5. Materialized state, snapshots, summaries, relationship projections and indexes derive from evidence and remain rebuildable according to their contracts.
6. Player/NPC knowledge advances only through provenance-bearing acquisition/perception/information paths.
7. Narrative systems request/rank opportunities and may return `NO_VALID_OPPORTUNITY`; they cannot inject facts, knowledge, success or forced actions.
8. AI Director stages already-valid beats inside knowledge/privacy/presentation constraints.
9. Renderer/publication outputs are read-only projections; contradiction is output failure, never authority to edit canonical truth.

Hard invariant: `NARRATIVE_NEED != PERMISSION_TO_CHANGE_WORLD_TRUTH`.

## 3. AF-A — identity, event and compatibility law

### 3.1 Stable identity

Material aggregates/events/contracts use stable machine IDs. Human names, filenames, model labels and storage locators are metadata, not identity authority.

### 3.2 Canonical events are profile-versioned

AF-001 does **not** retroactively impose a new envelope on accepted R001/R002 history.

Two explicit profiles are frozen in the machine registry:

#### `LEGACY_R001_R002_EVENT_PROFILE`

This is the accepted runtime `runtime.awrse.model.Event` shape:
- `event_id`
- `event_type`
- `actor_id`
- `scene_id`
- `baseline_version`
- `payload`
- `caused_by_action_id`

Those events remain fully legal canonical evidence and replay/rebuild inputs. `baseline_version` is its accepted legacy meaning; it is **not** silently reinterpreted as a vNext `schema_version` or `ruleset_version`.

#### `AF001_VNEXT_EVENT_ENVELOPE`

Future newly emitted events, only after a separately authorized runtime migration task, are expected to carry the stronger envelope:
- `event_id`
- `event_type`
- `schema_version`
- `ruleset_version`
- `world_id`
- `authority_scope_ref`
- `ordering_or_version_cursor`
- `payload`

Compatibility fields may preserve actor/scene/action/baseline references.

### 3.3 Non-fabricating compatibility bridge

The bridge `LEGACY_R001_R002_EVENT_PROFILE -> AF001_VNEXT_EVENT_ENVELOPE` is a **non-mutating compatibility view**, not a source-event migration.

Lossless direct mappings are allowed only where evidence exists: event ID/type, actor, scene, payload, caused action and legacy baseline. Missing `schema_version`, `ruleset_version`, `world_id`, `authority_scope_ref` or ordering provenance remain `UNKNOWN`, `NOT_APPLICABLE`, or externally supplied only when authentic replay context explicitly proves them.

Hard rules:
- never fabricate missing provenance;
- never treat `baseline_version` as schema/ruleset provenance;
- never renumber or rewrite old source events;
- old history continues replaying under the accepted legacy profile;
- the vNext envelope becomes mandatory only for **new** events after a later bounded implementation + independent review + Control Tower release.

### 3.4 Truth vs projection

- Event stream: authoritative causal evidence.
- Materialized state: current authorized projection.
- Snapshot/checkpoint: rebuildable performance optimization bound to source cursor/version.
- Summary/reflection: derived cache with source/model provenance.
- Renderer output: non-authoritative projection.

A newer projection never outranks the evidence it summarizes.

## 4. AF-B — world, actor, object and spatial state ownership

### 4.1 Minimal identity boundary

`WorldInstance` freezes the identity of a shared truth scope through `world_instance_id`, `world_id`, `instance_class`, `shared_truth_scope` and `state_version`. Multiple player-local projections may refer to one `WorldInstance`; they do not clone its shared physical truth.

`WorldFrame`, `Scene`, `Zone` and `Portal` define stable spatial identity/topology interfaces. Camera/DCC/engine axes are adapters and cannot redefine world-cardinal truth.

### 4.2 One canonical owner per material fact

The machine registry freezes owner, projection/index copies, authorized mutation source, consistency invariant and rebuild direction for every material relation below.

#### Legal/social ownership

Canonical truth: `ObjectAggregate.owner_ref` when that domain is modeled. It must arise from authorized ownership-transfer evidence. It is never inferred from possession.

Accepted R002 has **no lossless legal/social ownership field**. Therefore legacy legal ownership remains `UNKNOWN / NOT_MODELED` unless separate evidence exists.

#### Physical possession

Canonical truth: `ObjectAggregate.possessor_ref`.

`ActorAggregate.inventory_refs` is a derived/rebuildable index of objects whose `possessor_ref` is that actor. It is not a second possession authority.

Accepted R002 compatibility is explicit:

`ObjectState.owner_actor_id -> ObjectAggregate.possessor_ref`

Despite the legacy field name, accepted R002 semantics use `owner_actor_id` as the current physical holder/inventory actor. It must **not** be mapped to future `owner_ref`.

The accepted R002 invariant remains binding: one object has at most one possessor; the actor inventory index and object possession truth agree exactly; carried object scene/zone follows the possessor.

#### Inventory

`inventory_refs` is query/materialized index state rebuilt from possession truth. It changes only as part of an authorized possession transition. No Worker may mutate it as an independent ownership source.

#### Worn state

Canonical truth: `OutfitState.slot_bindings`. Possession does not imply worn state.

#### Mechanically equipped state

Canonical truth: `EquipmentLoadout.equipped_object_refs`. Equipment must be canonically available; inventory does not automatically imply equipped. Capability/presentation consumers are projections of this fact.

#### Location

Each actor/object aggregate owns its canonical `scene_id`/`zone_id`. Scene occupancy/render/query structures are indexes/projections. Movement/transfer transitions are the mutation source. Accepted R002 scene/zone fail-closed rules remain binding.

### 4.3 Shared world vs player-local state

Shared world facts exist once per `WorldInstance`. `PlayerChronicle`, knowledge, persona hypotheses and snapshots are recipient/player-local projections and cannot fork physical truth.

Concurrency hooks bind commands to expected world/aggregate versions and deterministic ordering evidence. The concrete arbitration algorithm remains `OD-CONCURRENCY-001`.

## 5. AF-C — capability, injury and status

These are frozen interfaces, not AF-001 runtime implementation:
- `ActorBaseProfile`
- `SkillLedger`
- `DerivedCapability`
- `ActionDemandProfile`
- `ActionResolutionReceipt`
- `InjuryState`
- `EquipmentLoadout`

Future resolution order:

`Intent -> Method Candidate -> Authority -> Physics/Affordance -> Capability Feasibility -> Difficulty/Resistance -> Outcome -> Hazard/Side Effects -> Canonical Events`.

### 5.1 Post CAP-EVAL architectural resolution

Control Tower decision `CAPABILITY-ARCH-RESOLUTION-001` resolves the architectural substrate previously carried inside `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001`. The historical decision IDs and CAP-EVAL evidence remain traceable, while ruleset tuning, player balance and genre-extension policy remain explicitly deferred.

Current architectural status for both capability decisions is `RESOLVED_ARCHITECTURAL_SUBSTRATE`.

Capability truth and representation law:

1. `ActorBaseProfile` remains canonical persistent/versioned actor capability truth. Every AF-C v1.1 profile carries immutable `profile_schema_ref` and `ruleset_family_ref` alongside `profile_version`, `base_attribute_map` and source evidence; the map keys are not an eternal universal stat ontology. Legacy v1.0 profiles remain valid only for their accepted historical replay profile and may not be silently reinterpreted as v1.1 capability input.
2. `SkillLedger` remains separate persistent competence truth. Skill truth may influence resolution but is not folded into or substituted for base-profile truth.
3. `DerivedCapability` is a current derived projection and remains distinct from `ActorBaseProfile` and `SkillLedger`.
4. Action resolution remains method-specific through `ActionDemandProfile`; one universal combat or capability score may not replace method-specific demand semantics.
5. Task-local logic may consume declared profile/skill/demand inputs but may not invent undocumented actor capability truth or mint a hidden second character sheet.
6. Capability schema and `base_attribute_map` keys are versioned ruleset schema. Migration across incompatible schemas requires explicit version/migration handling rather than silent reinterpretation.
7. Genre-specific capability remains an explicit extension namespace, resource or skill surface. Genre extensions may not silently redefine mundane-core semantics.
8. Profile, demand and receipt provenance must bind sufficient profile/schema/ruleset identity and source inputs for deterministic replay and migration. The current AF-C v1.1 minimum surface is `ActorBaseProfile.profile_version`, `ActorBaseProfile.profile_schema_ref`, `ActorBaseProfile.ruleset_family_ref`, source refs, `ActionDemandProfile.ruleset_version`, `ActionResolutionReceipt.ruleset_version` and deterministic random provenance. A legacy-v1.0-to-v1.1 transformation requires explicit compatibility or transformation evidence and must fail closed when that evidence is missing or mismatched.

Minimum resolution law:

1. Hard feasibility precedes graded or stochastic resolution.
2. An infeasible action is a hard failure at the relevant prerequisite gate. It has no fabricated numeric margin and cannot become a lucky success.
3. `EffectiveCapability` derives deterministically from declared versioned inputs.
4. For feasible graded ordering, the minimum auditable deterministic substrate is `Margin = EffectiveCapability - DifficultyOrResistance`.
5. Relevant impairment effects remain function-local; unrelated impairments may not leak into unrelated capability dimensions merely through a global stack.
6. Success and hazard/injury remain separate axes.
7. Outcome-band thresholds are ruleset-versioned policy rather than universal architecture constants.
8. Randomness is optional and downstream of feasibility.
9. Any randomness must carry deterministic provenance sufficient for exact replay.

CAP-EVAL-002's stack-nonlocality failure is evidence against canonicalizing the challenged stacking policies. It is **not** evidence against the deterministic feasibility/margin substrate above.

### 5.2 Deferred ruleset and balance policy

The following remain `DEFERRED_RULESET_TUNING` or `DEFERRED_PLAYER_BALANCE`, not unresolved architectural substrate:
- exact mundane stat list and stat ranges;
- strength vs power split;
- agility vs balance split;
- task and skill weights;
- progression values;
- injury and condition coefficients;
- outcome-band thresholds and exact balance coefficients;
- player-facing stat/balance/probability presentation and calibration.

Genre-specific naming, extension-pack composition and adoption policy remain `DEFERRED_GENRE_EXTENSION_POLICY` while the explicit-extension boundary itself is architectural law.

Candidate disposition is intentionally bounded:
- `RICH_GENRE_NEUTRAL_V1` is not selected as a universal canonical base vector.
- `DEMAND_PRIMITIVES_V1` may inform demand semantics but may not become free task-local actor truth.
- `SMALL_CORE_V1` is allowed only as a bounded initial/reference ruleset family, not as an eternal global ontology.
- `ADDITIVE_MULTIPLICATIVE_STACK_V1`, `TAGGED_PRIORITY_V1` and `BOUNDED_SEEDED_STOCHASTIC_V1` remain non-canonical ruleset/evaluation candidates and are not universal architecture.

### 5.3 I2 authority boundary

This architecture resolution establishes only:

`I2A_ARCHITECTURALLY_UNBLOCKED_PENDING_SEPARATE_CONTROL_TOWER_RELEASE`

It does **not** establish `I2_RUNTIME_IMPLEMENTATION_AUTHORIZED`. Capability, Skill, Injury, stochastic gameplay, progression, combat and healing runtime remain unimplemented and unauthorized by this architecture-only decision.

Governance locks:
- `RUNTIME_SEMANTICS_UNCHANGED=true`
- `NO_I2_RUNTIME_IMPLEMENTED=true`
- `I2_RUNTIME_AUTHORITY_NOT_GRANTED=true`

## 6. AF-D — appearance and asset state

`FunctionalInjury != VisibleTreatment`.

Canonical/frozen interfaces include `ActorPresentationState`, `OutfitState`, `DressingState`, `ActorAppearanceSnapshot`, `View`, `MediaAsset` and `MediaVersion`.

Rules:
- visual treatment is not functional injury truth;
- logical asset identity is separate from immutable media revision and mutable locator;
- inventory possession does not imply worn state;
- generated pixels cannot create damage, clothing, treatment or topology facts;
- renderer contradictions are failures, never state migration.

## 7. AF-E — player continuity, perception, memory, knowledge and relationship

Knowledge taxonomy remains `SAW / HEARD / WAS_TOLD / DOCUMENTED / RUMORED / INFERRED / UNKNOWN`. A mode name is not authority: every implemented mode requires executable mode-specific provenance or fails closed. R002 currently has strict runtime provenance for `SAW`, `HEARD`, `WAS_TOLD` and fails closed for unsupported modes.

### 7.1 Acquisition evidence vs recipient projection

Knowledge advancement authority belongs to a provenance-bearing acquisition/perception/information path. Recipient-local projections may materialize that evidence but **cannot create acquisition evidence themselves**.

- `NPCPerceptionEvent` represents a provenance-bearing recipient acquisition record.
- `NPCPerceptionStream` is an ordered recipient-local index/stream of those records.
- `NPCEpisodicMemory`, `BeliefState`, and `NPCPlayerRelationshipState` are evidence-backed projections/materialized views.
- `PlayerChronicle` is a player-local evidence-backed chronicle/knowledge projection.
- `PlayerSnapshot` is a rebuildable cache.

Thus neither Player Chronicle nor NPC memory/belief/relationship is allowed to invent knowledge merely because it owns its local projection.

### 7.2 Player continuity interfaces

- `PlayerIdentity`: stable player/principal/avatar/WorldInstance binding.
- `CharacterCore`: explicit player-authored role/voice/boundary settings.
- `EnactedPersonaHypothesis`: private, probabilistic, evidence-backed roleplay hypothesis.
- `IntentBelief`: private derived hypothesis, never a declared action.
- `PlayerAutoExpressionPolicy`: explicit opt-in policy for automatic expression.

Current explicit player intent outranks inferred persona. Private persona/intent models are not NPC knowledge.

Summaries/reflections remain derived caches. Model upgrades may recompute derived outputs but cannot rewrite source events/acquisition history. Backend, decay and relationship math remain `OPEN_DECISION`.

## 8. AF-F — story and information

Frozen interfaces include:
- `StoryDNA`
- `StoryBible`
- `CharacterDramaticCore`
- `HardCausalAnchor`
- `SoftDramaticAttractor`
- `Storylet`
- `EventDeckEntry`
- `InformationPacket`
- `NarrativePromise`

`EventDeckEntry` is an explicit **alias/wrapper around a `Storylet` for deck-selection metadata**. It is not a second narrative truth type and cannot create world facts independently of Storylet eligibility and world validation.

### 8.1 Authored narrative definition is not dynamic lifecycle state

AF-F explicitly separates authorial definition fields from evidence-derived current state. A single interface may expose both classes only when the machine contract carries field-level lifecycle authority; the authored loader never gains authority over the derived fields merely because they share a type name.

#### Hard causal anchor

`HardCausalAnchor` is a composite interface with two authority classes:

Authored narrative definition:
- `cause_refs`
- `planned_event_or_process`
- `revalidation_predicates`
- narrative intent implied by the planned process

These are authored/noncanonical design constraints. They describe what should remain eligible **if its causes remain intact**.

Dynamic lifecycle:
- `status`

`status` is evidence-derived current validity, not authored truth. It must be produced by the dedicated causal-anchor revalidation/projector boundary from canonical cause/event evidence. It must support deterministic rebuild/rehydration from `cause_refs` plus canonical events/evidence.

Hard rules:
- an invalid, destroyed, missing or unresolved required cause fails closed and cannot yield a currently valid anchor;
- narrative design cannot set, advance or restore current-valid status by authorial desire;
- an `INVALID` anchor remains invalid until legitimate new canonical evidence changes the relevant cause state and the dedicated revalidator evaluates it;
- legitimate cause restoration/change may permit revalidation, but only through real evidence and the same deterministic rules;
- model wording, PX rank, Director preference or branch-quality desire cannot override the evidence-derived result.

This preserves the Golden laws `destroyed_cause_invalidates_dependent_anchor` and `anchor_status_rebuilds_from_causes_and_events` without implementing a narrative runtime in AF-001.

#### Soft dramatic attractor adjacent audit

`SoftDramaticAttractor.dramatic_function`, `eligibility_predicates` and `expiry_policy` are authored design metadata. Its `status` is **not** authored metadata: current eligibility/expired/invalidated state depends on canonical world/history/player events. Therefore `status` uses a separate evidence-derived attractor-status lifecycle authority and must rebuild from bound evidence. Authored narrative may define the desired dramatic function but cannot mark an ineligible attractor active merely because it wants the beat.

#### Character dramatic core adjacent audit

`CharacterDramaticCore` goals, needs, fears, desires, value conflicts, obligations and non-negotiable boundaries are authored dramatic definition. `arc_state` is **not** free authored current state: Issue #11 explicitly treats current arc state as history/choice-sensitive and player-influenceable. Therefore `arc_state` uses a separate evidence-derived character-arc projection lifecycle. Narrative design may define an intended arc envelope, but current arc state must derive/rebuild from recorded history/evidence and cannot be advanced solely to hit a planned beat.

These adjacent separations are architecture-only authority freezes, not runtime implementations.

### 8.2 Information and promise evidence lifecycles

Information lifecycle:

`WORLD_EVENT -> SOURCE/WITNESS -> INFORMATION_PACKET -> CARRIER/CHANNEL -> PERCEPTION/COMMUNICATION -> PLAYER/NPC KNOWLEDGE`.

`InformationPacket` is provenance-bearing and cannot be authored from narrative desire. `NarrativePromise` is source-event/evidence derived; authored narrative may schedule a legal callback/payoff opportunity but cannot invent the underlying promise/history.

No direct Chronicle injection because a story considers information important. Narrative quality cannot justify resurrection, retcon or forced branch welding.

## 9. AF-G — opportunity, World Echo and PX

Frozen candidate flow:

`NarrativeGoal/Attractor -> NarrativeOpportunityBroker -> PlausibilityGate -> EncounterCandidate|WorldEchoOpportunity|NO_VALID_OPPORTUNITY -> PX ranking -> world/action authority`.

`NarrativeOpportunityBroker`, `EncounterCandidate`, `WorldEchoOpportunity` and `ResponseConcept` are interfaces only and are **not runtime-implemented by AF-001**.

Player auto-expression:
- private inner commentary is non-diegetic and has no world/social effect;
- low-risk automatic bark requires `PlayerAutoExpressionPolicy` explicit opt-in;
- high-risk confession/threat/agreement/promise/material identity claim requires explicit player action.

PX may rank only legal candidates. It cannot invent facts, lower difficulty, inject knowledge or force action. Scoring, commentary budget and encounter density remain explicit OPEN_DECISION dependencies.

## 10. AF-H — AI Director, renderer and publication

`DIRECTOR-BEAT-PACKET` is a downstream read-only presentation interface. It separates canonical state/event refs, player-visible knowledge, public/spectator-visible knowledge, private forbidden knowledge, presentation requirements and forbidden inventions.

AI Director can choose staging/camera/performance/edit/sound within the packet but cannot change event truth, capability result, knowledge provenance or current appearance. Renderer/publication remains downstream projection-only. Publication knowledge never flows backward into player/NPC knowledge.

Existing `contracts/WORLD-RENDER-PACKET.yaml` remains the accepted R001/R002 render foundation and is not replaced.

## 11. Cross-module type-resolution law

Every material concept directly used by this master or a Golden acceptance gate must resolve in `contracts/AF001-LIVING-STORY-CONTRACTS.json` as one of:
1. a versioned minimal type/interface with authority owner;
2. an explicit alias with semantics; or
3. a named `OPEN_DECISION / NOT_FROZEN / OUT_OF_CURRENT_FREEZE` dependency that prevents a scenario from pretending the mechanism is contract-bound.

AF-001 specifically resolves `PlayerIdentity`, `PlayerChronicle`, `PlayerSnapshot`, `IntentBelief`, `CharacterCore`, `EnactedPersonaHypothesis`, `PlayerAutoExpressionPolicy`, `WorldInstance`, `NPCPerceptionEvent`, `NPCPerceptionStream`, and the `EventDeckEntry -> Storylet` alias.

A later Worker must not invent owner/version/schema semantics for these names ad hoc.

## 12. Golden Scenario acceptance surface

The eight required scenarios remain:
1. `WILDERNESS_NEWS_TRAP`
2. `BROKEN_DOOR_WORLD_ECHO`
3. `FIGHTER_VS_SCHOLAR`
4. `PROMISE_RETURN_CALLBACK`
5. `PERSONA_SPEECH_BOUNDARY`
6. `ASSET_APPEARANCE_REVISIT`
7. `HOSTILE_PLAYER_BREAKS_PLOT`
8. `MULTIPLAYER_DIFFERENT_KNOWLEDGE`

Each keeps its human-readable scenario explanation and also contains a machine-checkable `machine_spec` with stable ID/version, actual type refs, structured initial/expected/forbidden predicates, provenance/authority assertions, ordering assertions, replay/restart assertions and explicit decision dependencies.

For `FIGHTER_VS_SCHOLAR`, the historical `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001` references now bind the preserved decision evidence and deferred ruleset/balance choices. They are no longer unresolved **architectural** dependencies. The scenario remains contract-gated and explicitly bound to versioned profile/ruleset/seed provenance; it does not claim a runtime implementation or a universal tuned stat vector.

For future-only subsystems, machine assertions state `CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED`; they do not pretend gameplay execution exists.

## 13. Versioning and migration law

Breaking changes to authority, identity, canonical event meaning, canonical ownership, required provenance or fail-closed boundaries require:
- explicit migration specification;
- replay/rebuild impact analysis;
- affected Golden Scenario updates;
- fresh independent review.

Source events are never rewritten to migrate projections. R001/R002 legacy events remain legal under their explicit profile. vNext event requirements activate only for newly emitted events after a later bounded migration task is accepted.

## 14. R001/R002 compatibility boundary

AF-001 preserves:
- raw player text as untrusted data;
- player/NPC/world authority separation;
- append-preserved event evidence;
- replay for implemented domains;
- live-state read-only seal;
- R002 symbolic spatial/possession fail-closed integrity;
- mode-specific knowledge provenance;
- renderer projection-only authority.

AF-001 future-plane contracts are interfaces and ownership laws, not runtime implementation claims.

## 15. Decision and deferred-policy discipline

Historical `OPEN_DECISION` evidence is never deleted merely because an architectural substrate is later resolved. A decision record may therefore carry both a resolved architectural substrate and explicit deferred policy tracks.

For `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001`, `docs/AF001-TRACEABILITY.md` is authoritative for the split between:
- `RESOLVED_ARCHITECTURAL_SUBSTRATE`;
- `DEFERRED_RULESET_TUNING`;
- `DEFERRED_PLAYER_BALANCE`;
- `DEFERRED_GENRE_EXTENSION_POLICY` where applicable.

A Golden machine spec may retain one of these historical decision IDs to preserve traceability and bind future ruleset choices. Such a reference is not automatically an architecture blocker. Whether it blocks architecture, runtime release or only tuned policy must be read from the decision's current status and dependency semantics.

Unresolved mechanisms outside this split remain recorded in `docs/AF001-TRACEABILITY.md` with their own bounded section containing competing options, evidence, dependency, risk and required experiment/research. No Worker may silently treat a deferred tuning choice as resolved, nor use a deferred choice to re-open an already resolved architecture boundary without a new Control Tower decision.

## 16. Governance / stop gate

- World Model / Control Tower defines scope, accepts architecture and later releases bounded implementation tasks.
- Engineering Worker edits architecture/contracts/evals/validator and supplies exact-head evidence. No self-review, ACCEPT or merge.
- Independent Reviewer fresh-reconciles and reviews exact head. No implementation/merge.

AF-001 is independently accepted and merged canonical architecture. `CAPABILITY-ARCH-RESOLUTION-001` may remove the architectural blocker for an eventual I2A release, but it does not itself release I2 runtime scope.

`RUNTIME_SEMANTICS_UNCHANGED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`

`I2_RUNTIME_AUTHORITY_NOT_GRANTED=true`

`AF001_ACCEPTED_CANONICAL / FURTHER_RUNTIME_EXPANSION_REQUIRES_EXPLICIT_RELEASE`

## 17. MIDS Living World vNext architecture candidate

Status: `MIDS_ARCHITECTURE_CANDIDATE / ARCHITECTURE_ONLY / NO_RUNTIME_AUTHORITY / REQUIRES_INDEPENDENT_REVIEW`.

This section compiles the user-confirmed MIDS Living World direction into AF-A..H. It is additive to the frozen authority graph and creates no new truth plane. The detailed classification, contradictions and deferred decisions are recorded in `docs/research/AWRSE-MIDS-TO-AF-VNEXT-MAPPING-v0.1.md`.

### 17.1 Breadth-first minimal living world

The first small-world vertical slice enables a minimal connected skeleton of each required domain rather than completing one domain in isolation. Every enabled module must declare its AF authority scope, dependencies, input event classes, output request/receipt classes, update granularity and lifecycle. A disabled or unavailable module cannot adjudicate, guess defaults or emit canonical events for its domain.

The only truth scope remains `WorldInstance` plus AF-A canonical event evidence. Domain authorities own their declared facts; a `WorldOrchestrationPlan` may schedule and correlate work but cannot mutate domain truth, mint evidence or commit events. Every accepted cross-domain consequence returns through the receiving authority's normal validation and canonical event path.

### 17.2 Selective causal propagation

An authoritative change may publish a `DomainChangeNotice` containing source event refs, exact world cursor, originating authority, potentially affected domains and causal relevance—not a pre-decided downstream outcome. Receiving authorities independently decide whether the notice is relevant and whether any legal consequence follows. Cycles are allowed only as ordered event-to-request-to-event chains with correlation and causation refs; direct recursive mutation and hidden shared state are forbidden.

This preserves one event ledger while allowing feedback such as regulation -> price pressure -> scarcity -> social response. Fidelity reduction may coarsen derived calculation or aggregate resource lots, but cannot remove source requirements, duplicate entities, change prior events or bypass conservation.

### 17.3 Adaptive fidelity and deferred concretization

`SimulationFidelityPolicy` selects declared update granularity by domain/entity relevance, causal risk and available budget. Fidelity controls computation detail, never existence or authority. Established entities, locations and history remain addressable when outside the player's view.

`UNKNOWN` and unresolved alternatives are legal states. `DeferredConcretizationReceipt` may select an alternative only when it binds the exact world cursor, unresolved slot, authorized constraint refs, candidate-set digest and selected candidate. It must fail closed if the slot was already resolved, evidence conflicts, the cursor is stale or the candidate was outside the admissible set. Concretization creates a new canonical event through the owning domain; it never edits prior evidence.

### 17.4 Intent, autonomy, institutions and time

Open natural-language input remains an untrusted attempted goal. AF-B/C translate it into an evidence-bound plan of methods, capability demands, resources, time, permissions and consequences before world resolution. Model intelligence cannot supply character knowledge, skill, resources or hidden plans as fact.

The player has final control of attempted intent for the currently bound actor. Persona policy may alter opted-in low-risk expression, not veto intent or choose a materially different action. NPCs and institutions remain autonomous: an `InstitutionAggregate` has stable identity and references goals, resources, factions, policies and authorized acting roles; detailed institutional mechanics require later versioned rulesets.

There is one canonical world timeline. Domains may update at different declared granularities. Repetitive activity consumes real world time; `TemporalCompressionPlan` only compresses presentation and must expose interruption points for materially new decisions. Closing and reopening defaults to no elapsed-world advance; optional long-absence advancement remains an explicit open product/ruleset decision.

Player-actor death remains permanent canonical evidence. Continuing play may rebind `PlayerIdentity.actor_id` through an authorized continuity event to an eligible heir, partner, companion or other actor in the same `WorldInstance`; it does not reload or fork away the death.

### 17.5 Narrative influence without narrative truth

AF-F/G may propose and rank only currently legal opportunities. `NarrativeInfluenceReceipt` binds the candidate-set digest, policy revision, declared dimensions, bounded budget consumption, selected candidate and rejected alternatives. Narrative influence cannot:

- create an otherwise unavailable candidate;
- change feasibility, capability, resource or outcome probability;
- fabricate evidence or character knowledge;
- force disaster when peaceful ordinary continuation is legal;
- resurrect invalidated anchors or rewrite history.

Exact weights, budgets, thresholds and learned ranking remain versioned ruleset/product policy, not architecture constants. `NO_VALID_OPPORTUNITY` and ordinary life remain valid outputs.

### 17.6 Law, evidence, entities and place history

Objective world fact, physical/documentary evidence, investigator belief, legal action, legal judgment and social belief are separate. A `LegalProcessProjection` may be wrong and may drive lawful institutional action, but it cannot rewrite the event/evidence history it interprets. Evidence can be hidden, moved, destroyed or forged only through world-authorized events; narrative importance cannot create it.

Physical entity IDs persist through movement and history. Destroyed IDs are never reused. `EntityLifecycleReceipt` records destruction, split or composition provenance; independently addressable outputs receive new IDs. Ownership, possession, permission, worn, equipped and location remain separate AF-B/C/D relations. `PlaceHistoryProjection` summarizes settlement, land-use and social-identity change from canonical events and is rebuildable rather than a second spatial authority.

Causally material history and provenance remain explainable. Compaction may replace derived indexes, summaries and low-value presentation caches, never the evidence required to reproduce important causal claims.

### 17.7 AWRSE-to-Director boundary and audience modes

AWRSE may add `DramaticPresentationIntent` only as a mechanically bound extension of the existing `DIRECTOR-BEAT-PACKET`: causal emphasis, emotional objective, reveal timing bounds, continuity refs, permitted audience information and forbidden inventions. The parent packet carries exactly one `dramatic_presentation_intent_ref`; the extension carries the matching `parent_director_beat_packet_ref`. Both sides must bind the same `world_instance_id`, world-state version/cursor and exact confirmed-event set, causal emphasis must be a subset of those events, and allowed information cannot exceed the parent packet's player/public visibility envelope. An orphan, duplicate, wrong-world, stale-cursor, event-mismatched or information-expanding intent fails closed. The parent packet remains the single AWRSE Director handoff boundary.

`DramaticPresentationIntent` does not specify or compete for concrete shot, lens, edit, performance or sound authority; those remain with the separate AI Director inside the validated envelope. It cannot be submitted independently as a second handoff object and has no world, event, knowledge, Director or render authority of its own.

`AudienceExposurePolicy` is an AF-H projection policy. Game mode normally limits output to player-visible information; film mode may expose audience-only events when policy permits. Neither audience knowledge nor rendered information is an AF-E acquisition event, and neither may flow back into player/NPC knowledge.

### 17.8 Candidate activation boundary

The interfaces in this section are `INTERFACE_ONLY_NOT_RUNTIME_IMPLEMENTED`. Acceptance of the architecture candidate does not authorize MIDS adapter work, domain runtime, providers, multiplayer, save/load, hardcore mode, external Director integration or production deployment. Each later slice requires a separate bounded release, exact contract/eval bindings and independent review.
