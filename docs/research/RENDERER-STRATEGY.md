# Renderer Strategy

Status: `PROVISIONAL / REQUIRES EMPIRICAL A/B VALIDATION`

## Decision summary

### Phase 1 primary renderer: MiniMax H3

Use H3 first for short, high-fidelity player-action feedback because the current product loop is expected to be discrete:

`player action -> canonical simulation resolution -> 4–15s reaction clip -> next player action`

Reasons to test H3 first:
- strong complex-action and character-performance orientation
- multimodal context / reference inputs
- commercial API access path
- short-form cinematic reaction output fits the MVP interaction loop
- easier engineering path than self-hosting a high-VRAM world model for the first vertical slice

### Strategic renderer: Matrix-Game 3.5

Keep Matrix-Game 3.5 as an R&D backend for:
- first-person / third-person navigation
- camera trajectory control
- long-horizon visual exploration
- scene revisit and persistent visual continuity

It is not the initial canonical simulation engine. Its Patch Memory and geometry-aware approach are strategically relevant to continuous world exploration but do not replace authoritative physical/social/world state.

## Product architecture implication

Do not hard-code the system to either renderer. Maintain a renderer-neutral `WorldRenderPacket` and model-specific adapters.

Candidate long-term routing policy:
- ordinary navigation / continuous exploration -> Matrix-Game-class world renderer
- complex interaction / dialogue / emotion / conflict / cinematic event -> H3-class high-fidelity renderer
- cheap routine feedback -> future lower-cost renderer or conventional engine

This routing policy is a hypothesis until measured.

## Required A/B evaluation

Evaluate the same canonical event/state package across candidate renderers on:
1. action fidelity
2. NPC reaction fidelity
3. character identity
4. scene persistence
5. physics appearance
6. camera control
7. audio alignment
8. latency
9. cost
10. long-horizon consistency
11. scene revisit quality
12. unauthorized hallucination rate

## Evidence anchors

Primary external sources to revalidate before implementation decisions:
- Matrix-Game 3.5 project / repository: https://matrix-game-v3-5.github.io/ and https://github.com/Riemann-Dynamics/Matrix-Game-3.5
- MiniMax official model/API documentation: https://www.minimax.io/ and https://platform.minimax.io/
- Google DeepMind Genie / SIMA research for world-model and agent reference architecture
- NVIDIA Cosmos research for world-foundation-model / physical-AI reference architecture
- OWASP GenAI guidance for prompt-injection and trust-boundary security

## Decision invalidation conditions

Reconsider H3 as Phase 1 primary renderer if any of the following is observed in controlled tests:
- unacceptable action/state mismatch rate
- character/scene identity drift that defeats continuity
- latency or cost makes the interaction loop unusable
- API constraints prevent required references or output control
- another renderer materially dominates on the weighted MVP evaluation matrix

Reconsider Matrix-Game as the strategic exploration renderer if:
- scene revisit gains are not reproducible
- camera/action control is insufficient for product interaction
- deployment cost or latency remains incompatible with intended scale
- a newer world model provides stronger persistent exploration under the same canonical contract
