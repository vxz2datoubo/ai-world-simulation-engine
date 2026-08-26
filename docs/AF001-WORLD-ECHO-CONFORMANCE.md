# AF-001 World Echo / Epistemic Conformance Gate

Status: `EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY / NOT_AUTHORITY_EXTENSION`

Governance task: `WORLD-ECHO-CONFORMANCE-001` / Issue #62.

Canonical base at release: `9379e8d6e4cf085f9c157e59b4c02ae6a0d26d86`.

## 1. Purpose

This bounded slice turns already-frozen AF-001 perception, memory, belief, relationship, World Echo and player-expression authority laws into deterministic executable evidence.

It does **not** implement NPC cognition, dialogue generation, an LLM memory system, relationship scoring, a persistence backend, Narrative Gravity runtime, or a second world-truth source.

The canonical parent remains `contracts/AF001-LIVING-STORY-CONTRACTS.json`.

The executable evidence is limited to:

- `evals/AF001-WORLD-ECHO-CONFORMANCE.json`
- `tests/test_af001_world_echo_conformance.py`

The task deliberately leaves the parent contract and all runtime files untouched so it remains parallel-safe with I2A-010 / PR #59 and Asset-Spatial Conformance / PR #61.

## 2. Existing AF-001 interfaces reused

The evaluator binds the exact parent tuple:

- contract id: `AWRSE-AF001-LIVING-STORY-CONTRACTS`
- contract version: `1.9.0-candidate`
- authority graph: `AF001-AUTHORITY-GRAPH-1.9-I2A008@1`

It reuses, without redefining:

- `NPCPerceptionEvent`
- `NPCEpisodicMemory`
- `BeliefState`
- `NPCPlayerRelationshipState`
- `NPCContextBundle`
- `WorldEchoOpportunity`
- `ResponseConcept`
- `PlayerAutoExpressionPolicy`

The test binds each type's exact id, version and authority profile. Parent drift fails closed.

## 3. Frozen authority laws exercised

The gate focuses on three already-frozen laws:

1. `RECIPIENT_PROJECTION_CANNOT_CREATE_ACQUISITION_EVIDENCE`
2. `PX_CANNOT_INVENT_FACTS_OR_INJECT_KNOWLEDGE`
3. `COMMENTARY_REQUIRES_PROVENANCE_AND_ANTI_REPEAT_POLICY`

From these, the reference evaluator checks that memory remains recipient-local, knowledge claims remain evidence-bound, and World Echo remains a downstream non-authoritative opportunity.

## 4. Synthetic broken-door revisit

The tiny fixture models one canonical fact: a tavern door remains broken after an earlier event.

Three NPCs later encounter that same shared world state:

### Witness
`NPC-WITNESS` directly saw `PLAYER-A` break the door. Their episodic memory binds the direct perception and source event, so a direct attribution may be valid.

### Rumor hearer
`NPC-RUMOR` was told a rumor and later received documentary correction evidence. Their belief is now doubted. They may still remember the rumor, but cannot silently upgrade it into witnessed certainty or an unhedged canonical fact.

### Newcomer
`NPC-NEWCOMER` has no culprit evidence. They may observe the current broken state, but cannot name a culprit simply because the simulator knows one.

All three share one world truth. Their valid reactions differ because their epistemic histories differ. This is the intended result, not a fork of world truth.

## 5. Evaluation-only helper objects

The parent does not currently register every convenient evaluator structure required to express this synthetic proof. Therefore helper constructs such as:

- `CanonicalWorldHistoryFixture`
- `EnvironmentalDeltaFixture`
- `AttributionResolutionFixture`
- `ContextKnowledgeProjectionFixture`
- `EchoHistoryFixture`
- `CommentaryBudgetFixture`
- `RealizationProbeFixture`
- `GeneratedSummaryProbeFixture`
- `DownstreamPresentationProbeFixture`

are explicitly `NONCANONICAL_EVAL_ONLY`.

They are test scaffolding. They do not become AF-001 types, runtime authority, or persistence state through this PR.

## 6. Executable adversarial coverage

The gate covers at least these failure families:

- simulator omniscience leaking culprit knowledge to a newcomer;
- memory without a valid perception ref;
- memory owner / perception owner mismatch;
- one NPC importing another NPC's memory;
- rumor/told provenance being upgraded to witnessed cause;
- rumor being realized as an unhedged factual assertion;
- unknown speaker naming a culprit;
- belief support referencing nonexistent or foreign evidence;
- later correction erasing the original rumor/evidence audit trail;
- relationship projection minting memory or perception evidence;
- `forbidden_hidden_fact_refs` being disclosed in the context projection;
- WorldEchoOpportunity drifting away from its environmental delta;
- speaker/attribution mismatch;
- ResponseConcept requiring facts the speaker does not have;
- private player commentary becoming audible/world-causal;
- low-risk audible auto-bark without `PlayerAutoExpressionPolicy` authorization;
- high-risk confession/threat/contract-style speech auto-emitting without explicit player intent;
- repeated identical novelty key firing again;
- expired echo firing;
- commentary-budget-suppressed echo firing;
- downstream director/renderer inventing culprit/world facts;
- generated summary claiming memory authority;
- broken-door callback firing when no environmental delta exists.

Silence is explicitly a valid result when eligibility, novelty, expiry, budget or knowledge gates do not permit a callback.

## 7. Player agency boundary

The fixture distinguishes:

- `PRIVATE_INNER_COMMENTARY`
- authorized low-risk diegetic bark
- high-risk speech requiring explicit player intent

Private commentary is non-diegetic: it does not create an audible speech event and cannot produce NPC hearing, legal, social, contractual or relationship consequences.

An auto-expression policy can authorize bounded low-risk bark classes. It cannot convert high-impact confession, threat, alliance, consent, contract, trade commitment or quest acceptance into automatic flavor text.

## 8. What this task does not authorize

A passing gate does **not** authorize:

- an NPC memory database/backend;
- memory decay/retrieval weights;
- relationship mathematics;
- LLM reflection/summarization authority;
- automatic diegetic dialogue runtime;
- World Echo ranking/scoring runtime;
- Narrative Gravity or PX runtime;
- director or renderer fact creation;
- persistence schema selection;
- multiplayer/public scaling decisions.

Those require separately bounded tasks and parent/runtime authority where applicable.

## 9. Promotion rule

A passing result means only:

`THE_EXISTING_AF001_EPISTEMIC_AND_WORLD_ECHO_BOUNDARIES_SUPPORT_A_DETERMINISTIC_NON_COMPETING_REFERENCE_CONFORMANCE_MODEL`

It does not mean:

`NPC_MEMORY_RUNTIME_IMPLEMENTED`

or:

`WORLD_ECHO_RUNTIME_AUTHORITY_GRANTED`.

Engineering stops after exact-head full-repository CI and independent-review handoff. No self-review and no merge by the Engineering Worker.
