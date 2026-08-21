# Runtime

Status: `R001 IMPLEMENTATION CANDIDATE / NOT PRODUCTION READY`

The first authorized AWRSE runtime slice is being implemented on branch `gpt/r001-core-loop`.

Current R001 scope:

- deterministic free-text -> typed Action DSL compiler
- untrusted player-text boundary
- authoritative action resolution
- conservative physical impossibility rejection
- append-preserved canonical events
- deterministic state projection and replay
- NPC knowledge acquisition only through explicit channels
- renderer-neutral `WorldRenderPacket`
- render/canonical mismatch contract
- executable regression tests for the implemented invariants

This is deliberately a **small proof of authority**, not yet a game, full physics engine, autonomous society, H3 integration, or Matrix-Game integration.

Implementation must preserve these invariants:

1. canonical simulation state is authoritative
2. renderers are projections only
3. raw player text is untrusted data
4. NPC internal state is not directly user-writable
5. physics/affordance validation precedes canonical outcome commit
6. hidden information does not leak across NPC knowledge boundaries
7. core world state remains replayable from event history and authorized deterministic projections
8. renderer mismatch cannot rewrite canonical truth

Before implementation is considered acceptable, the core eval suite in `evals/AWRSE-CORE-EVALS.yaml` must have executable coverage appropriate to the implemented scope and CI must pass on the exact review head.
