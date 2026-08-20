# AI World Simulation Engine

**Internal architecture name:** AWRSE — Autonomous World & Role Simulation Engine

A persistent AI world simulation system built around **Maximum Valid Freedom**: players may attempt arbitrary actions, but outcomes are resolved by authoritative world state, physics, affordances, permissions, NPC autonomy, social rules, and causal history.

## Core rule

> **The simulator decides what happened. The renderer decides what it looks and sounds like.**

Generative video models are projection/rendering backends. They must never become the canonical source of world truth.

## Canonical responsibilities

This repository is the sole canonical authority for:

- authoritative world state
- free-text action compilation / Action DSL
- physics and affordance validation
- NPC autonomy and cognition runtime
- NPC knowledge boundaries
- social consequence simulation
- event-sourced world history
- persistent scenes and dynamic deltas
- renderer routing and renderer adapters
- prompt-injection / authority security
- simulation evals and regression cases

## Repository boundaries

- `second-brain-coordination`: knowledge, learning, research, coordination and cross-system evidence. It is **not** the runtime world-state authority.
- `eustia-ai-film`: AI-film/director canonical. Video-model knowledge may be reused by explicit contract/reference, not copied into a competing canonical rule set.

## Initial renderer strategy

- **Phase 1 primary renderer:** MiniMax H3 for short, high-fidelity reaction videos and complex character/action feedback.
- **Strategic R&D renderer:** Matrix-Game 3.5 for long-horizon camera-controllable exploration and persistent visual-world navigation.
- Both remain non-authoritative renderers.

## Initial layout

- `ARCHITECTURE.md` — current canonical architecture
- `contracts/` — stable cross-layer contracts
- `schemas/` — world/action/NPC schemas
- `skills/` — simulation skill-family registry
- `evals/` — validation and regression definitions
- `runtime/` — implementation code when authorized
- `docs/research/` — evidence and research notes

## Status

`BOOTSTRAP / DESIGN FOUNDATION`

Runtime implementation has not yet been authorized as production-ready. All major claims must remain traceable to tests, evidence, or explicit architecture decisions.
