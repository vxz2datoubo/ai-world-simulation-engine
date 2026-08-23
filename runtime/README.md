# Runtime

Status: `ACCEPTED REFERENCE FOUNDATION / NOT PRODUCTION READY`

The canonical AWRSE runtime now contains accepted bounded foundations from R001, R002, R003-I1A and R003-I1B.

Accepted reference foundation:

- R001: deterministic free-text -> typed Action DSL boundary, authoritative action resolution, append-preserved canonical events, deterministic replay, explicit knowledge-channel constraints, and renderer-neutral projection contracts
- R002: accepted spatial/possession/knowledge-provenance hardening and associated deterministic runtime invariants
- R003-I1A: deterministic SOLO persistence envelope plus exact restart/rehydration reference that returns through canonical replay rather than materialized-state authority
- R003-I1B: deterministic read-only replay inspection and differential evaluation over canonical replay-produced state

This runtime remains deliberately **bounded and not production ready**. It is a reference world-truth substrate, not the finished game, full physics engine, autonomous society, production persistence service, Capability system, Memory system, Narrative Opportunity runtime, World Echo runtime, AI Director adapter, H3/Matrix integration, or PARTY/PUBLIC implementation.

Implementation must preserve these invariants:

1. canonical simulation state is authoritative
2. renderers are projections only
3. raw player text is untrusted data
4. NPC internal state is not directly user-writable
5. physics/affordance validation precedes canonical outcome commit
6. hidden information does not leak across NPC knowledge boundaries
7. core world state remains replayable from event history and authorized deterministic projections
8. renderer mismatch cannot rewrite canonical truth

Any future bounded runtime change requires explicit Control Tower release, executable coverage appropriate to the authorized scope, full regression CI on the exact head, and fresh independent review. Accepted foundations do not implicitly authorize unresolved upper-layer implementation.
