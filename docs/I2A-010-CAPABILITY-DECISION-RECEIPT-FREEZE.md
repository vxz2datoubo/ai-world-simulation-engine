# I2A-010 Deterministic Capability Decision Receipt Freeze

Status: `CANDIDATE_REQUIRES_INDEPENDENT_EXACT_HEAD_REVIEW`

Governance: Issue #58 / Draft PR #59

## Scope

This slice freezes a deterministic, replay-verifiable `CapabilityDecisionReceipt`
contract gate around the already accepted I2A capability inputs and deterministic
resolver semantics. It does **not** implement a runtime receipt serializer/importer,
new persistence authority, probability, combat, progression, healing, or impairment
numeric penalties.

Authority locks remain:

- `I2_RUNTIME_AUTHORITY_NOT_GRANTED=true`
- `NO_I2_RUNTIME_IMPLEMENTED=true`
- `RUNTIME_SEMANTICS_UNCHANGED=true`

No `runtime/**/*.py` file is modified.

## Parent authority

The canonical parent remains:

- contract: `AWRSE-AF001-LIVING-STORY-CONTRACTS`
- version: `1.9.0-candidate`
- authority graph: `AF001-AUTHORITY-GRAPH-1.9-I2A008@1`

I2A-010 adds only the extension-scoped discriminator:

`capability_decision_receipt_authority_epoch=AF001-CAPABILITY-DECISION-RECEIPT-I2A010@1`

A pre-I2A010 same-version parent with that field absent cannot authorize the new
receipt extension. This avoids a parent-version cascade while still distinguishing
the authority state mechanically.

## Receipt identity

The receipt binds:

1. exact I2A-010 parent/epoch identity,
2. exact resolver id/version,
3. admitted ActorBaseProfile evidence,
4. admitted SkillLedger evidence,
5. admitted ActionDemand evidence,
6. optional FunctionalImpairment applicability evidence,
7. hard-prerequisite receipt reference,
8. difficulty source reference,
9. replay input reference,
10. deterministic recomputed result.

The input digest is SHA-256 over canonical UTF-8 JSON using sorted object keys,
compact separators, and no non-finite numeric values. The accepted R003-I1A
canonical-JSON pattern is reused only as a serialization pattern. R003-I1A remains
the sole accepted SOLO replay package authority.

## P1 remediation: upstream admission authority identity

Independent exact-head review of the first candidate correctly identified that the
initial evidence shapes preserved business/semantic fields but omitted authority
identity fields carried by the accepted upstream admission receipts.

The remediation therefore requires and digests the complete authority identity
needed to prove which accepted admission boundary produced each evidence object:

### ActorBaseProfileAdmissionReceipt

- `canonical_contract_id`
- `canonical_contract_version`

### SkillLedgerAdmissionReceipt

- `canonical_contract_id`
- `canonical_contract_version`

### ActionDemandAdmissionReceipt

- `canonical_contract_id`
- `canonical_contract_version`
- `binding_id`
- `binding_version`

### FunctionalImpairmentAdmissionReceipt when provided

- `canonical_contract_id`
- `canonical_contract_version`
- `authority_graph_version`
- `binding_id`
- `binding_version`

Reduced caller-shaped mappings cannot reconstitute admission authority. Any missing
or mismatched upstream authority identity fails closed before digest materialization.

This closes the collision class where identical business fields under a stale or
forged admission contract/binding identity could previously collapse to the same
decision-receipt input identity.

## Result semantics

The receipt does not invent new gameplay semantics. It freezes the current
deterministic resolver ordering:

1. hard feasibility,
2. demand-scoped attributes and skills,
3. deterministic additive `EffectiveCapability`,
4. `Margin = EffectiveCapability - DifficultyOrResistance`.

If a required attribute or skill is missing, `feasible=false` and both numeric
result fields are null.

A caller-supplied materialized result is never authority. It must exactly match the
recomputed result or fail closed.

FunctionalImpairment evidence remains structural only in this slice. It is bound
into receipt identity when supplied but has no numeric capability effect.

## Persistence boundary

`CapabilityDecisionReceipt` is derived decision evidence, not WorldState truth and
not a persistence backend.

R003-I1A remains unchanged. The future carrier relationship remains open as
`OD-I2A010-RECEIPT-CARRIER-001`.

No second Ledger, Gateway, Resolver, event store, or persistence authority is
created.

## Machine-verifiable regressions

The fixture/test layer covers:

- identical admitted evidence -> identical digest,
- feasible and infeasible deterministic result binding,
- actor/skill/demand/body-function/impairment changes -> identity change,
- non-semantic body-function ordering canonicalization,
- ordered provenance sensitivity,
- caller mutation isolation,
- supplied-result non-authority,
- orphan child and pre-I2A010 parent failure,
- schema/ruleset/resolver/epoch drift failure,
- Actor admission canonical contract identity drift failure,
- SkillLedger admission canonical contract identity drift failure,
- ActionDemand admission binding id/version drift failure,
- FunctionalImpairment authority graph/binding id/version drift failure,
- absent impairment vs provided-zero-applicability identity separation,
- exact unchanged runtime tree and R003-I1A evidence,
- all three I2 authority locks.

The candidate must receive a new exact-head CI pass and independent exact-head
`ACCEPT` before any merge or canonicalization.
