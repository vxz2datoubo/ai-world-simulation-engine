# Runtime

Status: `NOT IMPLEMENTED`

This directory is reserved for authorized implementation of the AWRSE runtime.

No production runtime exists yet. The current repository stage is architecture, contracts, schemas, skills and evaluation design.

Implementation must preserve these invariants:

1. canonical simulation state is authoritative
2. renderers are projections only
3. raw player text is untrusted data
4. NPC internal state is not directly user-writable
5. physics/affordance validation precedes canonical outcome commit
6. hidden information does not leak across NPC knowledge boundaries
7. core world state remains replayable from event history and authorized deterministic projections
8. renderer mismatch cannot rewrite canonical truth

Before implementation is considered acceptable, the core eval suite in `evals/AWRSE-CORE-EVALS.yaml` must have executable coverage appropriate to the implemented scope.
