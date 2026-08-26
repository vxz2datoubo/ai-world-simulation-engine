# I2A-008 Functional Impairment Freeze

Governance: Issue #53.

Remediation tracking: Issue #55.

This note records only the bounded architecture disposition represented by the machine contracts and executable fixtures in this branch.

## Frozen structural boundary

- `ActorBaseProfile` remains durable base truth and is not rewritten by temporary functional impairment.
- `SkillLedger` remains separate competence truth and is not rewritten by injury.
- `InjuryState.functional_impairments` plus injury provenance is the only impairment evidence source in this slice.
- `ActionDemandProfile.required_body_functions` is an exact, version-bound function-namespace applicability filter.
- Structural applicability requires exact `function_ref` equality. No anatomy aliasing or inference is authorized.
- Unrelated function namespaces have zero effect.
- Dressing, presentation, narrative, PX, director and renderer state cannot author mechanical impairment.
- The projection is deterministic, provenance-bound and mutation-isolated.

## Explicit runtime blocker

The architecture does **not** yet define a versioned function-to-capability dependency registry or any numeric impairment formula. Therefore this slice does not authorize numeric current-capability modification.

Still deferred:

- impairment severity to numeric penalty
- coefficients and stacking
- recovery/healing
- pain/bleeding/HP/damage
- fatigue/status composition
- combat and probability
- persistence/migration runtime
- renderer appearance mechanics

`I2_RUNTIME_AUTHORITY_NOT_GRANTED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`

`RUNTIME_SEMANTICS_UNCHANGED=true`

## Additive parent-version remediation

I2A-008 is registered as an `ADDITIVE_NON_RUNTIME_CANDIDATE_EXTENSION` under canonical AF001 `1.9.0-candidate`; it is not a top-level parent-version migration. Existing ActionDemand authority and version lineage remain unchanged.

The Issue #55 remediation preserves the same PR/branch and restores incidental ActionDemand changes to canonical main. Exact-head Python 3.11/3.13 CI and independent review remain mandatory release gates.

## Authority-graph discriminator remediation

The AF001 semantic contract version remains `1.9.0-candidate`, while the post-I2A-008 extension-authority graph carries the separate machine-verifiable discriminator `AF001-AUTHORITY-GRAPH-1.9-I2A008@1`. The existing general ActionDemand extension authority rule is unchanged. Functional-impairment extension authority additionally requires an exact `(contract_id, contract_version, authority_graph_version)` match. A pre-I2A-008 AF001 1.9 document lacks that discriminator and cannot authorize this extension. This removes replay/provenance ambiguity without inventing a top-level AF001 semantic-version migration.

The discriminator is part of the canonical authorization identity for this extension, not a runtime capability grant. Missing or mismatched discriminator evidence fails closed.

Release evidence is the exact-head CI provenance of the candidate submitted for independent review.
