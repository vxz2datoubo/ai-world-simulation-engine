# MIDS World Design Discovery Adapter V0

Status: `SHADOW / REPLAY / CANDIDATE_ONLY`

Source: AWRSE Issue #102, snapshot `MIDS-001-SPEC-2026-08-31-R1`.

## Purpose

This V0 is an upstream design-discovery adapter for authorial world intent. It helps convert natural-language goals into traceable questions, materially distinct candidate options, QOC-style rationale and `DesignCandidatePacket` outputs without acquiring world, runtime, architecture, contract, Golden Scenario, OPEN_DECISION or publication authority.

Authority marker on every compiled packet:

`CANDIDATE_ONLY / REQUIRES_ARCHITECTURE_RESOLUTION`

The frozen AWRSE authority order remains:

`WORLD/RULES > CAPABILITY/STATE > KNOWLEDGE/MEMORY > NARRATIVE OPPORTUNITY > PX > AI DIRECTOR > RENDERER/PUBLICATION`

and:

`NARRATIVE_NEED != PERMISSION_TO_CHANGE_WORLD_TRUTH`

## Epistemic boundary

V0 mechanically distinguishes:

- `USER_EXPLICIT_CONFIRMED`: direct user confirmation with provenance;
- `USER_TACIT_CANDIDATE`: inferred candidate that cannot self-promote;
- `AI_DISCOVERABLE_OPTION`: AI-originated direction that remains a proposal until explicit user acceptance;
- `EXPERT_BLIND_ZONE`: technically material design issue translated into a concrete world/player scenario before asking the user.

No inference or AI proposal is rewritten as user fact.

## Question selection

The selector is deterministic and transparent. It uses a lexicographic tuple rather than a fake universal numeric truth score:

1. world-consistency / authority risk;
2. decision impact;
3. dependency centrality;
4. uncertainty reduction;
5. irreversibility;
6. novelty potential;
7. lower implementation cost;
8. lower cognitive load.

It suppresses non-material and canonical-known questions, validates Expert Blind Zone scenario translations before rendering, and enforces a hard `1..3` question budget.

## Mixed initiative and rationale

A valid design exploration may contain materially different AI options/counteroptions, but wording variants with the same material key do not satisfy the alternative requirement.

QOC records preserve:

`QUESTION -> OPTIONS -> CRITERIA -> ARGUMENTS/EVIDENCE -> USER DECISION -> DEFERRED/UNKNOWN -> SUPERSEDED`

User decisions require explicit user provenance. Supersession preserves prior decisions as historical evidence and marks only one current-effective decision.

## Candidate compilation

A `DesignCandidatePacket` may contain candidate requirements, behavioral contracts, invariant candidates, state implications, examples/counterexamples, Golden Scenario candidates, unresolved unknowns, contradictions, existing contract refs and OPEN_DECISION refs.

It never mutates:

- `ARCHITECTURE.md`;
- `contracts/**`;
- `registries/**`;
- `docs/AF001-TRACEABILITY.md`;
- `evals/AF001-GOLDEN-SCENARIOS.json`;
- `runtime/**`;
- workflows;
- world/player/NPC state.

There is intentionally no canonical writer/mutator API in V0.

## Replay corpus and anti-leakage

The six historical families are capability impairment, knowledge delivery, persistence/restart, hostile-player narrative, possession/inventory and presentation cross-plane integrity.

Fixtures separate discovery input from `expected_discoveries`. Expected discoveries are scoring metadata only. V0 must not present deterministic replay success as evidence that a fresh LLM independently discovered every answer. Hidden-answer agent-generation evaluation remains a later independent requirement.

## Metrics

V0 reports:

- critical unknowns discovered before implementation;
- material decisions per question;
- unnecessary technical question rate;
- useful AI design alternative count;
- architecture contradiction rate;
- OPEN_DECISION traceability rate;
- Golden Scenario candidate coverage;
- false canonicalization count;
- provider-call count;
- world-mutation count.

Hard acceptance remains `false_canonicalization_count == 0`, with provider and world mutation counts also zero.

## Scope boundary

This implementation is deterministic, local and dependency-light. It performs no provider/network calls and has no runtime integration. Promotion, canonical architecture edits, runtime activation, Ready, merge and acceptance remain outside this worker's authority.
