# CAP-EVAL-002 Held-out Capability Robustness Evaluation

Status: `EVALUATION_EVIDENCE_ONLY / NON_CANONICAL_CANDIDATES / NO_I2_RUNTIME_AUTHORITY`

Release base: `32e2a1a830f0685af207275da0ad4849e7637ea4`

Predecessor evidence: Issue #24 / merged PR #25 / accepted head `6e665ca3f02795564119383f52f7643190997eec`.

This report is bounded CAP-EVAL-002 evidence for `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001`. It does not resolve either OPEN_DECISION, does not implement Capability/Skill/Injury gameplay runtime, and does not authorize I2.

The executable source of truth is `evals/capability_robustness_eval.py` consuming the governed `evals/CAPABILITY-ROBUSTNESS-EVALS.json` plus the read-only CAP-EVAL-001 predecessor artifacts. Numeric evidence must come from a successful evaluator execution and exact-head CI, not from hand-maintained prose.

Governance locks:

- `RUNTIME_SEMANTICS_UNCHANGED=true`
- `OPEN_DECISION_STATUS_UNCHANGED=true`
- `NO_I2_RUNTIME_IMPLEMENTED=true`

## 1. What the suite is allowed to establish

Executable evidence may establish:

- held-out task distinctness from CAP-EVAL-001;
- hard-prerequisite feasibility ordering;
- representation collisions;
- bounded actor/difficulty/weight robustness;
- function-local impairment behavior;
- candidate/task/order/name independence;
- fresh-process determinism;
- explicit WUXIA / XIANXIA / SF extension isolation;
- parameter burden and auditability;
- whether a governed recommendation policy is actually satisfied.

It may not establish:

- player-facing fairness;
- final genre ontology;
- progression feel;
- probability calibration;
- medical realism;
- production tuning;
- I2 authority.

Those remain outside CAP-EVAL-002.

## 2. True held-out corpus

The governed spec declares eight held-out families, all with task IDs and normalized semantics mechanically checked against CAP-EVAL-001:

| Family | Fixture | Pressure |
|---|---|---|
| explosive / rapid force | `BREACH_DOOR_BURST` | burst power distinct from slow force |
| whole-body change of direction | `CROWD_DODGE_CUT` | agility distinct from static balance |
| precision under time pressure | `TIMED_NEEDLE_ALIGNMENT` | precision + control under time pressure |
| multi-stage tool manipulation | `VALVE_BYPASS_SEQUENCE` | hard prerequisite before resolution |
| noisy observation | `FOG_SIGNAL_DISCRIMINATION` | observation under ambiguous evidence |
| reasoning with irrelevant impairment | `LOGIC_GRID_WITH_WRIST_SPLINT` | locality / irrelevant-factor isolation |
| sustained coordinated physical work | `ROPE_BRIDGE_HAUL` | endurance + control |
| teamwork-shaped pressure | `TWO_PERSON_STRETCHER_SYNC` | representation pressure only, not PARTY runtime |

The evaluator does not inspect an `expected_winner` label. Actor, task, representation, and math-policy identifiers are excluded from semantic resolution identity where only semantics should matter.

## 3. B01 remediation: feasibility is not a fake numeric margin

`VALVE_BYPASS_SEQUENCE` requires `MULTITOOL_KIT`.

A fixture without that tool returns:

- `feasibility = HARD_FAIL_MISSING_REQUIRED_TOOL`
- `margin = null`
- no stochastic receipt
- no sampled outcome

CAP-EVAL-002 now treats qualitative comparison in two explicit domains:

1. `FEASIBILITY_DOMINANCE`
   - one side is feasible and the other fails a hard prerequisite;
   - the relation is evaluated by feasibility;
   - no margin subtraction is attempted.

2. `MARGIN_ORDER`
   - both sides are feasible;
   - margin ordering and bounded perturbation are evaluated numerically.

If both sides are infeasible, the evaluator reports `BOTH_INFEASIBLE_NO_MARGIN_ORDER` and does not invent a numeric ordering.

Robustness evidence separately reports:

- feasibility-dominance count;
- margin-comparison count;
- preservation fraction;
- margin-band stability only when a numeric margin comparison actually exists;
- reversal locations with the comparison basis that produced them.

This preserves the AF-001 law that hard prerequisites dominate later stochastic or graded resolution.

## 4. Representation-collision pressure

The collision probes deliberately pressure distinctions left unresolved by CAP-EVAL-001:

- explosive burst/power;
- rapid agility/change of direction.

The executable evidence records, per candidate, whether the declared representation collides or distinguishes. The suite does not translate collision coverage directly into authority. A richer vector may distinguish more cases while also carrying a larger durable parameter surface.

Therefore collision coverage is one evidence dimension, not a winner score.

## 5. Genre-extension pressure without mundane-core pollution

Evaluation-only WUXIA, XIANXIA and SF fixtures use explicit extension namespaces.

For each representation candidate, the evaluator checks:

- extension values remain outside the mundane representation map;
- mutating extension values does not change the mundane receipt when no extension is selected;
- selecting an extension fixture changes only the explicit extension contribution;
- the mundane base representation snapshot remains unchanged.

This establishes an extension-boundary invariant only. It does not implement WUXIA, XIANXIA, SF, PARTY, or production genre runtime.

## 6. Parameter / weight robustness

The governed perturbation grid varies:

- left actor relevant capability;
- right actor relevant capability;
- task difficulty;
- representation / skill weight tilt.

The evaluator does not collapse the result into one score.

Each relation records:

- preservation fraction;
- feasibility-dominance versus margin-comparison counts;
- reversal locations;
- fragile / non-fragile classification;
- margin-band stability only when a margin baseline exists.

This distinction matters because a relation can be structurally stable due to a hard prerequisite while having no legitimate numeric margin comparison at all.

## 7. Math-policy diagnostics

All four CAP-EVAL-001 math-policy families remain evaluation-only:

- deterministic margin;
- additive/multiplicative stack;
- tagged priority;
- bounded seeded stochastic.

The held-out diagnostics separately report:

- monotonicity under relevant capability perturbation;
- reasoning isolation from unrelated physical impairment;
- local tool-route effect from relevant impairment;
- exact seeded replay when stochastic sampling is used;
- excess condition penalty relative to deterministic margin;
- no probability-calibration claim.

The current governed recommendation policy is explicit:

`math_resolution_requires_deterministic_baseline_monotonic_and_stack_nonlocality_absent=true`

The evaluator now consumes that policy as a real gate. It does not bypass it.

Current executable evidence satisfies the deterministic baseline checks, but the challenge stacking policies do not satisfy the strict “stack non-locality absent” condition under the held-out diagnostic. Therefore the governed math resolution gate is not satisfied.

That result is intentionally conservative. CAP-EVAL-002 may provide narrowing evidence without pretending the OPEN_DECISION has been resolved.

## 8. Candidate-overfit guards

The regression suite proves:

- held-out IDs and normalized semantics are distinct from CAP-EVAL-001;
- no `expected_winner` label is consumed;
- evaluator source contains no held-out actor fixture IDs or predecessor candidate IDs;
- all held-out tasks cover all representation candidates;
- candidate and task order do not alter structured evidence;
- actor/task/representation/math renames preserve semantic receipts;
- missing tools remain feasibility failures across every math candidate;
- robustness paths are non-vacuous;
- genre-extension inputs do not pollute mundane base semantics;
- input specs remain immutable;
- repeated evaluation is canonical-serialization stable;
- fresh Python processes emit byte-identical output;
- candidate status remains `EVALUATION_CANDIDATE_ONLY`.

Tests validate recommendation-policy consistency. They do not force the evaluator to emit one preferred governance answer.

## 9. Strongest counterargument

A bigger synthetic benchmark can still become a bigger synthetic mirror.

Executable invariants can legitimately establish:

- feasibility before uncertainty;
- determinism;
- label/order independence;
- locality;
- extension isolation;
- structural collision facts;
- policy/evidence consistency.

They cannot by themselves establish:

- final actor stat ontology;
- exact condition multipliers;
- exact task weights;
- exact difficulty scale;
- player-facing probability buckets;
- production balance.

Those later tuning questions should not be confused with architectural truth, but neither should they be silently promoted into architecture by a synthetic evaluator.

## 10. Governance recommendation

The attribute evidence remains two-sided. Extra axes can earn collision discrimination, but the durable-surface and tuning burden tradeoff is unresolved by synthetic evidence alone.

For math, the existing governed resolution gate explicitly requires deterministic-baseline validity **and** absence of stack non-locality. The baseline evidence is good, but the full gate is not satisfied. CAP-EVAL-002 therefore keeps the math OPEN_DECISION open rather than weakening or bypassing the preregistered gate after observing the results.

ATTR recommendation class: `KEEP_ATTR_OPEN`

MATH recommendation class: `KEEP_MATH_OPEN`

`RUNTIME_SEMANTICS_UNCHANGED=true`

`OPEN_DECISION_STATUS_UNCHANGED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`
