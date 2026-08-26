# I2A-010 Capability Decision Receipt Freeze

Status: `ARCHITECTURE_CONTRACT_EVALS_ONLY / CONTRACT_GATE_ONLY_NOT_RUNTIME_IMPLEMENTED`

Governance: Issue #58

## Purpose

I2A-010 freezes the smallest deterministic, provenance-bound `CapabilityDecisionReceipt` profile needed to reproduce and independently check one bounded I2A capability decision. The receipt is derived evidence only. It is not ActorBaseProfile truth, SkillLedger truth, ActionDemandProfile truth, InjuryState truth, WorldState truth, or persistence authority.

## Authority tuple

The canonical AF001 parent remains unchanged at:

- contract id: `AWRSE-AF001-LIVING-STORY-CONTRACTS`
- contract version: `1.9.0-candidate`
- authority graph version: `AF001-AUTHORITY-GRAPH-1.9-I2A008@1`

I2A-010 does **not** introduce a `1.10.0-candidate` parent-version cascade. Instead, the parent registers the receipt extension with one extension-scoped discriminator:

`capability_decision_receipt_authority_epoch = AF001-CAPABILITY-DECISION-RECEIPT-I2A010@1`

The exact authorization tuple is:

1. `contract_id`
2. `contract_version`
3. `authority_graph_version`
4. `capability_decision_receipt_authority_epoch`

A pre-I2A010 parent with the epoch absent cannot authorize the new child even if its AF001 contract version and authority graph version are otherwise identical.

Existing ActionDemand and FunctionalImpairment extension identities and versions remain unchanged.

## Resolver reference

The receipt binds the existing deterministic resolver semantics under:

`AWRSE-I2A-DETERMINISTIC-CAPABILITY-RESOLVER@1.0.0-candidate`

Implementation evidence remains `runtime/awrse/capability_resolution.py`; this task does not modify it.

Frozen semantics are only:

1. hard feasibility first;
2. demand-scoped admitted attributes and skills only;
3. deterministic additive EffectiveCapability;
4. `Margin = EffectiveCapability - DifficultyOrResistance`;
5. finite non-boolean numeric validation;
6. no probability;
7. no weighting;
8. no impairment numeric application.

If feasibility fails because a required admitted capability reference is missing, `effective_capability` and `margin` are both `null`.

## Bound admitted evidence

The logical receipt binds:

- actor identity and admitted ActorBaseProfile evidence;
- admitted SkillLedger evidence;
- admitted ActionDemand evidence;
- canonical `required_body_functions` preserved by I2A-009;
- optional FunctionalImpairment applicability evidence;
- hard-prerequisite receipt reference;
- difficulty source reference;
- replay input reference;
- exact parent authority tuple;
- exact resolver identity;
- recomputed deterministic result.

Functional impairment remains structural only. A provided impairment receipt changes receipt identity, including unrelated/zero-applicability evidence, but it cannot change `effective_capability` or `margin` in I2A-010.

`ABSENT` and `PROVIDED_ZERO_APPLICABILITY` are intentionally distinct evidence states.

## Canonical digest

I2A-010 reuses the accepted R003-I1A canonical JSON philosophy as a reference pattern only:

- UTF-8 JSON;
- sorted object keys;
- compact separators;
- non-finite numbers forbidden;
- SHA-256 tamper-evident digest.

The digest is over canonical admitted input material plus authority/resolver identity. Materialized result values are not allowed to become input authority. Replay/checking must recompute the result and reject a supplied result that disagrees.

Upstream ordering law is preserved rather than redefined:

- mapping keys are canonicalized by sorted JSON object keys;
- required attribute and skill refs are canonicalized lexicographically because they are derived from unique upstream mapping keys;
- `required_body_functions` are lexicographically ordered while preserving multiplicity exactly as admitted upstream;
- FunctionalImpairment applicability maps and their source-ref sets use the ordering already frozen by I2A-008/I2A-009;
- ActorBaseProfile source-event sequences remain order-sensitive;
- SkillLedger entry order and each entry's source-event sequence remain order-sensitive;
- hard-prerequisite order remains whatever was admitted upstream.

## Relationship to ActionResolutionReceipt

AF001 already exposes broader `ActionResolutionReceipt` v1.0 as a future interface. I2A-010 is a focused deterministic capability-decision child/profile only.

It does not authorize or claim runtime implementation of:

- outcome bands;
- hazard outcomes;
- randomness;
- combat;
- gameplay resolution.

## Persistence boundary

R003-I1A remains the sole accepted SOLO replay evidence package authority. I2A-010 does not modify:

- `runtime/awrse/persistence.py`;
- `evals/R003-I1A-RESTART-REFERENCE.json`;
- the accepted R003-I1A envelope;
- any persistence backend.

The future carrier relationship remains deliberately open:

`OD-I2A010-RECEIPT-CARRIER-001`

No decision is made here between an event-carried receipt, a sidecar/reference, or a future versioned envelope extension.

## Machine verification

`evals/AF001-CAPABILITY-DECISION-RECEIPT-FIXTURES.json` and `tests/test_i2a_capability_decision_receipt_contract.py` lock:

- identical-input deterministic identity;
- exact feasible and infeasible result semantics;
- upstream evidence tamper detection;
- required-body-function binding;
- FunctionalImpairment binding and zero numeric effect;
- canonical versus order-sensitive namespaces;
- schema/ruleset/resolver/authority drift rejection;
- mutation isolation;
- recomputation over caller-supplied result;
- parent registration and pre-I2A010 epoch rejection;
- exact unchanged runtime tree;
- exact unchanged R003-I1A persistence artifacts;
- all three I2 authority locks.

## Authority locks

The following remain true:

```text
I2_RUNTIME_AUTHORITY_NOT_GRANTED=true
NO_I2_RUNTIME_IMPLEMENTED=true
RUNTIME_SEMANTICS_UNCHANGED=true
```

No `runtime/**/*.py` change is authorized by this slice.
