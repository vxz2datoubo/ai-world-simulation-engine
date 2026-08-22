# AWRSE Canonical Architecture

Status: `AF001_ARCHITECTURE_FREEZE_CANDIDATE / NOT_YET_INDEPENDENTLY_ACCEPTED`

Canonical authority: this file is the single current architecture master for AWRSE. Detailed machine-readable freeze contracts live in `contracts/AF001-LIVING-STORY-CONTRACTS.json`; executable-spec Golden Scenarios live in `evals/AF001-GOLDEN-SCENARIOS.json`; dependency, traceability and unresolved decisions live in `docs/AF001-TRACEABILITY.md`. Those files refine this master and must not create competing architecture authority.

AF-001 is architecture/contracts/eval work only. It does **not** authorize new gameplay runtime features. R001 and R002 merged runtime behavior remains canonical implementation truth until a later bounded task is explicitly released after Architecture Freeze acceptance.

## 1. Product law

**Maximum Valid Freedom** means a player may attempt broad natural-language actions while the world remains authoritative about what is physically, socially, causally and role-consistently possible.

The central composition law is:

`AUTHORIAL_INTENT -> LEGAL_OPPORTUNITY -> PLAYER_INTENT -> WORLD_RESOLUTION -> CANONICAL_EVENT -> PERSISTENT_PROJECTION -> PERCEPTION/KNOWLEDGE -> CALLBACK/OPPORTUNITY -> PRESENTATION`

No downstream stage may silently rewrite an upstream fact.

The system preserves four conceptual views without collapsing authority:

1. **Semantic World** — identities, ownership, roles, relationships, rules and meanings.
2. **Physical World** — symbolic/physical position, reachability, topology, affordances, capability, injury and constraints.
3. **Epistemic/Social World** — perception, knowledge, memory, belief, relationship, reputation and information propagation.
4. **Presentation World** — assets, appearance, camera, director packets, audio/video rendering and publication.

Generated pixels, prose summaries, LLM plans, narrative candidates and caches are never canonical world truth merely because they are plausible.

## 2. Frozen authority order

The candidate AF-001 invariant is:

`WORLD/RULES AUTHORITY > CAPABILITY/STATE RESOLUTION > KNOWLEDGE/MEMORY > NARRATIVE OPPORTUNITY > PX RANKING > AI DIRECTOR > RENDERER/PUBLICATION`

Expanded rules:

1. Player controls only authorized attempted actions for their actor(s).
2. World/rules/affordance/topology decide what is legal and possible.
3. Capability/state resolution decides feasible uncertain outcomes and side effects when such systems are later implemented.
4. Canonical events are the append-preserved evidence of committed truth.
5. Materialized state, snapshots, summaries, relationship projections and caches derive from evidence and are rebuildable unless explicitly classified otherwise.
6. NPC/player knowledge can advance only through provenance-bearing perception/information paths.
7. Narrative systems may request or rank opportunities; they may return `NO_VALID_OPPORTUNITY` and may not inject facts, knowledge, success or forced actions.
8. AI Director chooses staging/presentation of already-valid beats inside knowledge/privacy/presentation constraints.
9. Renderer/publication outputs are read-only projections. Contradictions are render/publication failures, never authority to edit canonical truth.

Hard invariant:

`NARRATIVE_NEED != PERMISSION_TO_CHANGE_WORLD_TRUTH`.

## 3. Canonical event and identity law — AF-A

### 3.1 Stable identity

Every material aggregate/event/contract entity uses a stable machine ID. Human display names, filenames, model-generated labels and storage locators are metadata, not identity authority.

Identity families are contract namespaces, not promises that every runtime family already exists. IDs must survive display-name localization, media relocation and projection rebuilds.

### 3.2 Canonical events

A canonical event must be immutable/append-preserved evidence and carry at least:
- `event_id`
- `event_type`
- `schema_version`
- `ruleset_version`
- `world_id`
- authoritative aggregate/scene scope
- causal/action provenance where applicable
- event/world version or ordering cursor
- actor/source identity where applicable
- payload constrained by a versioned event contract

Random resolution, when later authorized, must carry deterministic replay provenance rather than hidden nondeterminism.

### 3.3 Truth vs projection

- Event stream: authoritative causal evidence.
- Materialized state: current deterministic projection.
- Snapshot/checkpoint: performance optimization bound to an event cursor and schema/ruleset version.
- Summary/reflection: derived cache with source refs and model/version provenance.
- Renderer output: non-authoritative projection.

A snapshot, summary or render cannot silently become a new causal source merely because it is newer than the events it summarizes.

## 4. World / actor / object / spatial state — AF-B

### 4.1 Aggregate boundaries

Candidate aggregate families:
- `WorldAggregate`
- `SceneAggregate`
- `ActorAggregate`
- `ObjectAggregate`
- optional later `PlayerWorldAggregate`, `PartyAggregate`, `StoryInstanceAggregate`, `PublicationAggregate`

Aggregate ownership does not permit duplicate facts. A fact has one canonical owner and other planes store refs/projections.

### 4.2 Spatial vocabulary

- `WorldFrame` owns canonical world-cardinal orientation and optional unit basis.
- `Scene` is a stable spatial identity.
- `Zone` is a scene-bound symbolic interaction area.
- `Portal` / adjacency edge records explicit connectivity/traversal semantics.
- Camera/DCC/engine axes are adapters and cannot redefine world-cardinal truth.

Text maps and image maps are projections of the same canonical spatial graph. A generated map mismatch is `MAP_PROJECTION_MISMATCH`, not permission to rewrite topology.

### 4.3 Location / ownership / possession

Canonical semantics distinguish:
- world/scene/zone location
- legal/social ownership where modeled
- actor possession/inventory
- worn/equipped state

`OWNED != POSSESSED != WORN` unless an explicit transition proves equivalence for a specific domain.

R002 possession/inventory and symbolic zone invariants remain binding foundation behavior.

### 4.4 Shared truth vs player-local state

Shared world facts exist once per shared world/instance. Player Chronicle/knowledge/persona projections may differ per player but cannot fork shared physical truth.

Concurrency hooks must bind commands to expected world/scene/aggregate versions and a deterministic canonical ordering policy. Exact arbitration algorithm remains an `OPEN_DECISION` until workload/eval evidence exists.

## 5. Capability / injury / status — AF-C

Capability contracts are frozen as architecture interfaces, not implemented by AF-001.

Required separations:
- `ActorBaseProfile` — durable baseline traits.
- `SkillLedger` — event-backed trained proficiency.
- `DerivedCapability` — current computed capability/read model.
- `ActionDemandProfile` — versioned requirements for one action/method.
- `InjuryState`, `FatigueState`, `StatusEffect`, `EquipmentModifier` — current modifiers with source provenance.
- `ActionResolutionReceipt` — feasibility/method/ruleset/input evidence/outcome/side-effect provenance.

Resolution order for future work:

`Intent -> Method Candidate -> Authority -> Physics/Affordance -> Capability Feasibility -> Difficulty/Resistance -> Outcome -> Hazard/Side Effects -> Canonical Events`.

Rules:
- impossible actions fail before probability;
- success and injury/hazard are independent axes;
- repeated attempts may consume time/stamina/progress under explicit rules;
- equipment contributes only when canonical possession/equip/reachability permits;
- randomness must be deterministic-replayable from explicit seed/roll/ruleset provenance.

Exact attribute list, stacking formula and stochastic curve remain `OPEN_DECISION` pending targeted evals.

## 6. Appearance / asset / presentation state — AF-D

Functional state and visible treatment are different truths connected by events:

`FunctionalInjury != VisibleTreatment`.

Canonical presentation vocabulary:
- `ActorPresentationState`
- `OutfitState`
- `DressingState`
- `SurfaceState`
- `ActorAppearanceSnapshot` as rebuildable read model

Asset/spatial vocabulary:
- `Scene`
- `CameraAnchor`
- `View`
- `MediaAsset`
- `MediaVersion`
- `Locator`

Rules:
- camera position and camera facing are separate variables;
- logical asset identity is separate from immutable media revision and mutable locator;
- current media promotion requires verification, not generation success alone;
- inventory possession does not imply visual wear;
- renderers must preserve required visible state or fail contradiction validation;
- generated pixels cannot create damage, clothing, treatment or topology facts.

## 7. Perception / memory / knowledge / relationship — AF-E

Canonical knowledge-acquisition taxonomy remains:
- `SAW`
- `HEARD`
- `WAS_TOLD`
- `DOCUMENTED`
- `RUMORED`
- `INFERRED`
- `UNKNOWN`

A mode name is not authority. Each implemented mode needs executable provenance semantics; unsupported modes fail closed in runtime. R002 currently implements strict provenance for `SAW`, `HEARD` and `WAS_TOLD` and fails closed for unimplemented modes.

Player knowledge and NPC knowledge are separate projections. Private player persona hypotheses are never NPC knowledge unless a legal observable/information path exists.

Future persistence contracts distinguish:
- canonical world event evidence
- NPC perception events/stream
- `NPCEpisodicMemory`
- `BeliefState` with support/refutation/confidence/status
- sparse NPC↔player relationship projection with source refs
- retrieval/index/cache layers

Summaries/reflections are derived caches only. Model upgrades may create new derived versions but may not silently rewrite source history. Restart/rehydration must bind to exact IDs, event cursors and schema/ruleset versions.

Exact storage backend, memory-decay equation and relationship weighting remain `OPEN_DECISION` pending scale/eval evidence.

## 8. Story / information architecture — AF-F

Authored narrative is a design plane, not event truth.

Frozen vocabulary:
- `StoryDNA` — multi-axis dramatic engine/setting/tone/theme/interaction profile.
- `StoryBible` — governed authored facts/constraints/roles for a story domain.
- `GenreEngine` — genre-aware craft/rules/eval pack, not runtime authority over facts.
- `CharacterDramaticCore` — authored goals, needs, fears, values, obligations, contradictions and arc constraints.
- `HardCausalAnchor` — planned event/process whose real causes exist and must be revalidated.
- `SoftDramaticAttractor` — desired dramatic function without fixed world fact.
- `Storylet` / `EventDeckEntry` — conditional opportunity definition.
- `NarrativePromise` — setup/callback/payoff lifecycle bound to evidence.
- `InformationPacket` — provenance-bearing information object distinct from canonical truth and recipient knowledge.

Information lifecycle:

`WORLD_EVENT -> SOURCE/WITNESS -> INFORMATION_PACKET -> CARRIER/CHANNEL -> PERCEPTION/COMMUNICATION -> PLAYER/NPC KNOWLEDGE`.

No direct Chronicle injection because a story considers information important.

Clue/reveal/branch quality contracts must distinguish canonical truth, available evidence, recipient knowledge and presentation. Narrative quality cannot justify resurrection, retcon or branch welding that contradicts committed events.

## 9. Opportunity / World Echo / PX — AF-G

Frozen candidate lifecycle:

`NarrativeGoal/Attractor -> NarrativeOpportunityBroker -> PlausibilityGate -> EncounterCandidate|WorldEchoOpportunity|NO_VALID_OPPORTUNITY -> PX ranking -> world/action authority`.

`PlausibilityGate` checks spatial, temporal, identity/history, motivation, information provenance, density/ecology, asset/object availability and anti-repeat constraints before a candidate may be surfaced.

`EncounterCandidate` is temporary and non-authoritative. It may expire or be rejected.

World Echo obeys:

`PERSISTENT_STATE + VALID_PERCEPTION + MEMORY/KNOWLEDGE + CONTEXT -> WORLD_ECHO_OPPORTUNITY`.

A `ResponseConcept` describes a permitted communicative function before language realization. Commentary requires budget/cooldown/anti-repeat controls.

Player auto-expression risk routing:
- `PLAYER_PRIVATE_INNER_COMMENTARY` — non-diegetic/private, cannot change world/social state.
- `PLAYER_AUTHORIZED_CHARACTER_BARK` — only inside explicit opt-in policy and low-risk envelope; becomes diegetic if actually spoken.
- high-risk confession/threat/agreement/commitment/identity claim or other material speech requires explicit player action/authorization.

PX may rank or surface **legal** opportunities and presentation emphasis. It cannot fabricate facts, lower difficulty secretly, grant success, inject knowledge or force a player action.

Exact PX scoring weights, commentary thresholds and encounter-density budgets remain `OPEN_DECISION` pending real-player evaluation.

## 10. AI Director / renderer / publication — AF-H

The frozen bridge object is `DIRECTOR-BEAT-PACKET`, a downstream, read-only presentation request containing only validated world/knowledge/presentation facts plus explicit dramatic/presentation intent.

It must separate:
- canonical confirmed events/state refs
- player-visible knowledge
- public/spectator-visible knowledge
- private/forbidden knowledge
- ActorPresentationRequirements
- scene/view/asset refs
- presentation goals
- forbidden inventions
- provenance/version refs

AI Director may choose camera, performance, editing, sound and emphasis within the packet. It cannot change action outcomes, actor identity, capability result, knowledge provenance, current appearance or canonical event history.

Renderer validation must detect material contradictions, including confirmed-event, scene, object, actor identity/appearance, knowledge/privacy and camera/view requirements where contractually observable.

Publication/spectator projection is distinct from player knowledge. A spectator recap may know facts the player avatar does not only if publication policy explicitly authorizes that audience view; it may never leak those facts back into player/NPC canonical knowledge.

Existing `contracts/WORLD-RENDER-PACKET.yaml` remains the R001/R002 foundation render contract and is not replaced by AF-001.

## 11. Golden Scenario acceptance surface

Architecture Freeze is evaluated through eight executable-spec scenarios in `evals/AF001-GOLDEN-SCENARIOS.json`:

1. `WILDERNESS_NEWS_TRAP`
2. `BROKEN_DOOR_WORLD_ECHO`
3. `FIGHTER_VS_SCHOLAR`
4. `PROMISE_RETURN_CALLBACK`
5. `PERSONA_SPEECH_BOUNDARY`
6. `ASSET_APPEARANCE_REVISIT`
7. `HOSTILE_PLAYER_BREAKS_PLOT`
8. `MULTIPLAYER_DIFFERENT_KNOWLEDGE`

Every scenario defines initial canonical state, allowed player intents, required contracts, expected canonical events, projection changes, knowledge consequences, narrative consequences, presentation requirements, forbidden outcomes, replay/restart expectations, adversarial variants and acceptance criteria.

These are executable specifications and future implementation gates, not claims that the corresponding runtime exists today.

## 12. Versioning and migration law

Every freeze contract declares `contract_version` and compatibility expectations.

Rules:
- additive optional fields may be backward-compatible only when old consumers fail safely;
- changing authority, identity, event meaning, required provenance or canonical ownership is a breaking contract change;
- breaking changes require explicit migration spec, replay/rebuild impact analysis and new Golden Scenario receipts;
- snapshots/caches declare source cursor + schema/ruleset version and may be invalidated/rebuilt;
- source events are never rewritten in place merely to migrate a projection;
- model-specific outputs remain derived artifacts and can be regenerated under a new model version.

Exact long-lived storage migration framework is `OPEN_DECISION`; AF-001 freezes the obligations, not a database vendor.

## 13. R001/R002 compatibility boundary

AF-001 must not weaken accepted foundations:
- raw player text remains untrusted data;
- player cannot directly control NPC mind/world rules;
- canonical mutations flow through authoritative event/projector paths;
- event history is append-preserved and replayable for implemented domains;
- live canonical state is read-only outside authorized transitions;
- symbolic R002 zone/reachability/affordance/possession invariants remain fail-closed;
- knowledge provenance remains mode-specific and fail-closed;
- renderer is projection-only and contradictions do not rewrite truth.

AF-001 contracts that describe future planes are **interfaces and ownership laws**, not runtime implementation claims.

## 14. OPEN_DECISION discipline

If evidence is insufficient to freeze a concrete mechanism, the architecture records `OPEN_DECISION` with competing options, evidence, dependency, risk and required research/experiment. Open decisions block implementation that depends on them but do not invalidate already-frozen upstream boundaries.

Current open-decision registry is maintained only in `docs/AF001-TRACEABILITY.md` to avoid duplicate decision ledgers.

## 15. Governance / stop gate

- **World Model / Control Tower** defines scope, accepts architecture and later releases bounded implementation tasks.
- **Engineering Worker** edits architecture/contracts/evals and supplies exact-head evidence. No self-review, ACCEPT or merge.
- **Independent Reviewer** fresh-reconciles and reviews exact head. No implementation/merge.

No post-R002 runtime task is automatically released by this Freeze candidate.

Promotion requires:
1. complete AF-001 artifact set;
2. non-vacuous architecture consistency/traceability checks;
3. exact-head CI;
4. fresh independent exact-head ACCEPT;
5. Control Tower architecture acceptance and expected-head merge.

Until then:

`RUNTIME_EXPANSION_BLOCKED_UNTIL_AF001_ACCEPTED`.
