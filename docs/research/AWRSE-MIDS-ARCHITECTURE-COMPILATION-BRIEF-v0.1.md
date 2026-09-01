# AWRSE MIDS -> vNext Architecture Compilation Brief v0.1

> Authority: `NON_CANONICAL_CONTROL_TOWER_INPUT`
>
> Goal: give Codex a bounded architecture-only job that compiles the user's MIDS-confirmed world design into the existing AWRSE canonical architecture model without creating a second system.
>
> Current canonical base at brief preparation: `bc9bee8c6402d70dbb5c36ca4416905f4ca54ee4`
>
> Canonical authority remains:
> - `ARCHITECTURE.md` = sole architecture master
> - `contracts/AF001-LIVING-STORY-CONTRACTS.json` = machine contract registry
> - `evals/AF001-GOLDEN-SCENARIOS.json` = Golden executable-spec registry
> - `docs/AF001-TRACEABILITY.md` = traceability / OPEN_DECISION registry

---

## 1. Existing canonical substrate that MUST be reused

Do not duplicate these accepted authorities/interfaces:

### AF-A
- stable machine identity
- canonical event evidence
- truth vs projection
- replay/provenance/versioning

### AF-B
- WorldInstance / Scene / Zone / Portal
- ActorAggregate / ObjectAggregate
- legal ownership vs physical possession
- inventory as projection
- worn state
- equipped state
- canonical location
- concurrency hook with `OD-CONCURRENCY-001`

### AF-C
- ActorBaseProfile
- SkillLedger
- DerivedCapability
- ActionDemandProfile
- hard feasibility before graded/stochastic outcome
- function-local impairment
- deterministic provenance
- no universal combat score

### AF-D
- appearance/presentation state
- OutfitState
- asset identity/version
- renderer cannot mint world truth

### AF-E
- acquisition evidence
- NPCPerception
- NPCEpisodicMemory
- BeliefState
- relationship projection
- CharacterCore / persona boundary
- summaries as derived caches

### AF-F/G
- StoryBible
- HardCausalAnchor
- SoftDramaticAttractor
- Storylet
- Narrative Opportunity / World Echo / PX
- `NO_VALID_OPPORTUNITY`
- narrative cannot change world truth

### AF-H
- AI Director / presentation downstream
- DirectorBeat/Publication boundary
- renderer/publication no flow-back

---

# 2. Architecture deltas to compile

Codex should classify every delta below as:
`ALREADY_CANONICAL / CLARIFICATION / EXTENSION / OPEN_DECISION / POLICY / LATER_PHASE`.

Do not assume every bullet needs a new type.

## Delta A: Orchestration plane

Need architecture semantics for a high-level Orchestrator that:
- sees dependency graph / scheduling needs;
- routes structured state changes to relevant domains;
- increases/decreases simulation fidelity;
- pauses temporal compression when a high-value decision is needed;
- aggregates already-resolved domain results;
- surfaces cross-domain contradictions;
- prepares structured input for Narrative/Presentation.

Invariant:
`ORCHESTRATION_AUTHORITY != DOMAIN_TRUTH_AUTHORITY`

Orchestrator must not:
- decide world truth on behalf of domain owners;
- change probabilities because outcome is more dramatic;
- bypass AF-A event/provenance;
- become second world store.

Candidate new architecture surface only if existing AF-A/G runtime coordination cannot express it.

## Delta B: Cross-domain causal propagation

Need explicit semantics for:
`DOMAIN_DECISION -> CANONICAL_EVENT/STATE_CHANGE -> DEPENDENCY_ROUTING -> DOWNSTREAM_DOMAIN_RESPONSE`

Requirements:
- selective propagation;
- no all-system broadcast requirement;
- causal source retained;
- feedback loops evolve in canonical world time;
- cross-domain conflicts are composed through actual authority boundaries rather than “winner AI”.

Golden candidate:
`PRICE_CONTROL_BLACK_MARKET_FEEDBACK`

## Delta C: Adaptive simulation fidelity

Need architecture boundary for:
- group/statistical state;
- low-fidelity individuals;
- high-fidelity persistent entities;
- promotion when entity enters important causal chain;
- no deletion/re-roll of already-established history;
- different domains can run at different update granularities;
- all map to one canonical timeline.

Avoid prescribing performance implementation.

Candidate name:
`AdaptiveSimulationFidelity`

## Delta D: Deferred Concretization

Need formal distinction:
- `UNKNOWN`
- constrained candidate space
- selected concrete fact
- lock conditions / observation / downstream dependency
- no-retcon rule

Narrative may rank legal candidates only within genuine unresolved space.

Must not create second history authority.

Potential Golden:
`DEFERRED_TOWN_HISTORY`

## Delta E: Narrative influence budget

Current SoftDramaticAttractor/Narrative Opportunity laws remain authority.

Add/clarify:
- Narrative may bias legal probability within bounded policy;
- never manufacture impossibility;
- cumulative interventions must be auditable;
- budget can be scoped by player/storyline/world-event class;
- world truth remains domain-resolved;
- exact weights/limits remain ruleset/policy, NOT architecture constants.

Potential type candidate:
`NarrativeInfluenceReceipt` or extension of existing opportunity receipt, only if current registry has no adequate provenance surface.

Do not create second Narrative Authority.

## Delta F: Player Narrative Exposure Preference

Need separate recipient/player experience preference:
- repeated explicit/tacit opt-out can reduce proactive narrative exposure;
- does not suppress true world consequences;
- not a permanent personality label;
- can recover when player seeks intensity again.

Should likely map to player/PX policy, not World Truth.

## Delta G: Presentation intent between AWRSE and AI Director

AWRSE should be able to communicate:
- why an event is worth showing;
- causal precursor;
- causal payoff;
- foreshadowing opportunity;
- what may be shown to audience;
- what must remain unknown to character;
- presentation importance vs playable importance.

AI Director remains responsible for:
- shots;
- edit;
- performance;
- pacing;
- concrete screenplay realization.

Candidate:
`DramaticPresentationIntent`
or extension of current DIRECTOR-BEAT-PACKET.

First reconcile I9 / presentation work before adding a competing packet.

Potential Goldens:
- `POLICE_SURVEILLANCE_FORESHADOW`
- `BUTTERFLY_CAUSAL_PAYOFF`

## Delta H: Game vs Film audience policy

Same World Truth supports:
- game mode: do not expose off-character knowledge as ordinary presentation;
- film mode: may show off-character world events to audience;
- audience knowledge never writes into character knowledge.

Likely AF-H/Publication policy, not new truth plane.

## Delta I: World initialization and authorial future attractors

World creation:
- author/script provides broad direction/anchors;
- world details generated under world constraints;
- unresolved areas can concretize later.

Future story direction:
- authored desired future acts as attractor, not guaranteed event;
- player/world can invalidate conditions and prevent it;
- reuse `SoftDramaticAttractor` / HardCausalAnchor semantics.

Do not invent “future truth store”.

## Delta J: Open natural-language plan execution

Need architectural law:
- player intent may be goal-level or detailed;
- role AI may fill unspecified method only within Character capability/knowledge;
- AI model intelligence cannot leak into character intelligence;
- each step re-resolves against current world;
- novel plans need not be pre-authored actions if existing world mechanisms can express them.

Likely clarification/extension across R001 intent + AF-C method resolution.

## Delta K: Player agency vs NPC autonomy

- player has final control over currently controlled actor action intent;
- personality can affect expression, not veto;
- player cannot directly control other NPCs;
- NPCs can receive goals/orders but execute according to own capability/knowledge/loyalty/state;
- subordinate AI can adapt small details and challenge bad plans.

Preserve R001 law that player cannot author target NPC internal state.

## Delta L: Institutions

Architecture should permit real institutions:
- resource state;
- goals;
- policy;
- internal factions;
- multi-role decision formation;
- independent evolution;
- failure/dissolution;
- emergence of new institutions.

Do not over-specify politics/economy runtime yet.

Need determine whether institution is AF-B world aggregate extension or separate future domain module.

## Delta M: Resource conservation with resolution scaling

Major entities/events need credible resource sources.
Remote simulation may be coarse but not causally free.

Do not turn every small consumable into high-fidelity accounting.

Potential invariant:
`LOW_FIDELITY != SOURCELESS`

## Delta N: Law, evidence and institutional judgment

Need high-level architecture distinction:
- World Fact
- Evidence
- Investigator Knowledge/Belief
- Legal Action/Status
- Court/Institutional Judgment
- Social Belief

Rules:
- legal judgment does not rewrite World Truth;
- investigators can be wrong;
- ability/bias/corruption/fatigue affect inference;
- evidence can be hidden, destroyed, forged;
- AI cannot fabricate evidence for plot convenience.

Keep courtroom procedure/ruleset detail out of this slice.

Potential Golden:
`FALSE_ARREST_LOW_SKILL_INVESTIGATOR`

## Delta O: Entity lifecycle / provenance

Existing stable IDs and object authority must be extended/clarified for:
- destroyed entity retains historical identity;
- split components get new IDs;
- composed objects get new IDs;
- same appearance != same entity;
- possession/ownership/permission/equipment remain separate;
- hidden object has actual location;
- object history can affect social meaning/value.

Do NOT silently require atom-level provenance.

Open:
exact parent/child provenance requirements for melted/split materials.

## Delta P: World spatial/history evolution

Architecture should support:
- location state persists after player leaves;
- buildings can be destroyed/rebuilt;
- settlements may emerge from population/resource history;
- environment changes propagate;
- location social identity evolves;
- World Spatial Truth != Character Known Map.

Keep geomorphology/economy detail modular.

## Delta Q: Long-history retention

Need explicit history retention philosophy:
- important canonical events retained;
- small events may be compacted;
- compaction cannot destroy causally necessary evidence;
- important entities/places/objects may retain finer history;
- current world should remain explainable from retained causal evidence.

Must reconcile with AF-A truth-vs-projection / replay law.
Never delete source events in a way that violates accepted event authority.

If “compaction” means summaries/indexes only, say so explicitly.

## Delta R: Player death continuity

Player-controlled actor can die permanently.

Experience may continue:
1. preferably through heir/partner/companion with real world relationship;
2. otherwise new/selected character in same world.

Death does not delete/restart world history.

Treat succession selection as product policy; architecture should only ensure WorldInstance and player identity can rebind without rewriting history.

## Delta S: Single-player offline time policy

Initial product is single-player.

Default close/reopen may freeze world time.
Long absence may optionally advance world time.

Exact threshold/advance algorithm is policy/open decision, not architecture law.

Need architecture to permit a controlled time-advance/reconciliation operation without pretending real wall-clock time was already canonical world time.

## Delta T: Modular Living-World Kernel

Need architecture ability to support:
- common Meta-Law core;
- optional domain modules by world;
- legal module registration/activation;
- disabled modules cannot adjudicate;
- runtime addition only through governed/authorized module lifecycle;
- all modules obey World Truth / event / provenance / authority laws.

Do not build every module now.

---

# 3. Proposed architecture compilation outputs

Codex should produce an architecture-only Draft PR whose candidate diff is limited to the smallest necessary set among:

1. `ARCHITECTURE.md`
   - add/clarify architecture laws and module boundaries.
2. `contracts/AF001-LIVING-STORY-CONTRACTS.json`
   - only new/extended interfaces genuinely needed to make the architecture machine-addressable.
3. `docs/AF001-TRACEABILITY.md`
   - new decisions / explicitly deferred policies / mapping from MIDS evidence.
4. `evals/AF001-GOLDEN-SCENARIOS.json`
   - candidate architecture-bound Golden scenarios only where needed to prevent ambiguity.

Optional supporting research doc:
- a concise mapping document from MIDS decisions to AF-A..H.

No runtime code in this architecture slice.

---

# 4. Mandatory non-goals

- no `runtime/**`
- no `.github/workflows/**`
- no provider/LLM integration
- no AI Film repository edits
- no MIDS V0 implementation duplication of Issue #102
- no exact balance numbers
- no exact Narrative weights
- no full economy/law/politics simulation
- no multiplayer runtime
- no traditional save/load runtime
- no hardcore mode
- no self-review
- no self-ACCEPT
- no Ready transition
- no merge

---

# 5. Architecture success criteria

The Draft PR must make it possible for a later worker to answer, without inventing a second authority:

1. Who owns truth for a cross-domain state?
2. How does a canonical change wake related domains?
3. How can remote/low-fidelity world state become concrete without retcon?
4. How can Narrative lightly bias legal possibilities without owning outcomes?
5. How does AWRSE tell the AI Director what is worth showing without telling it how to shoot?
6. How are audience knowledge and character knowledge separated?
7. How can an NPC/institution act autonomously without player or Orchestrator directly controlling internal truth?
8. How can an entity persist, be destroyed, split/composed, owned, possessed, worn, hidden and historically recognized without ID confusion?
9. How can legal judgment be wrong while World Truth remains stable?
10. How can optional world modules join the system without becoming ungoverned truth sources?
11. How can player death or long absence continue the same WorldInstance without rewriting history?
12. How does all of the above remain compatible with accepted R001/R002/R003 and AF-A..H?

---

# 6. Golden scenario candidates for architecture review

Use only as candidate architecture checks unless formally registered:

- `MIDS-CONTESTED-KEY`
- `MIDS-UNDERGROUND-ORG-POLICE`
- `MIDS-PRICE-CONTROL-BLACK-MARKET`
- `MIDS-DEFERRED-TOWN`
- `MIDS-PERSISTENT-SWORD`
- `MIDS-FOREST-CAUSAL-PROPAGATION`
- `MIDS-BUTTERFLY-PAYOFF`
- `MIDS-WAR-TAVERN-EXPOSURE`
- `MIDS-PLAYER-DEATH-SUCCESSION`
- `MIDS-LONG-ABSENCE`
- `MIDS-FALSE-ARREST`

Each should include:
- positive path;
- negative/counterexample;
- authority owner;
- no-retcon constraint;
- knowledge/presentation boundary where relevant.

---

# 7. Codex execution posture

Role: `CODEX_ENGINEERING_WORKER / ARCHITECTURE_ONLY`

First action:
- fresh reconcile current main;
- read Issue #102 for MIDS epistemic/governance law;
- read the user-confirmed discovery document;
- read canonical architecture/contracts/Golden/Traceability;
- classify delta before writing.

If current main or binding architecture changed materially from the brief base:
- do not blindly apply this brief;
- reconcile and document drift;
- preserve user design intent while mapping it to the new canonical state.

Stop after:
- architecture-only branch pushed;
- Draft PR opened;
- exact-head tests/validators run;
- engineering handoff posted;
- independent review requested.

Do not merge.
