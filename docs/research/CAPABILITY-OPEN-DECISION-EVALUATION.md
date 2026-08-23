# CAP-EVAL-001 Capability OPEN_DECISION Evaluation

Status: `EVALUATION_EVIDENCE_ONLY / NON_CANONICAL_CANDIDATES / NO_I2_RUNTIME_AUTHORITY`

Release base: `15abb16b3892d69aeed14ee2327211d2af672500`

Source OPEN_DECISIONs under evaluation:
- `OD-CAPABILITY-ATTR-001`
- `OD-CAPABILITY-MATH-001`

This report accompanies the deterministic executable evaluator in `evals/capability_open_decision_eval.py` and the governed data in `evals/CAPABILITY-OPEN-DECISION-EVALS.json`.

It may recommend or narrow future research. It does **not** resolve either OPEN_DECISION, freeze an attribute vector, authorize I2, or change runtime semantics.

## 1. Architecture boundary

The evaluation preserves the AF-001 order:

`Intent -> Method Candidate -> Authority -> Physics/Affordance -> Capability Feasibility -> Difficulty/Resistance -> Outcome -> Hazard/Side Effects -> Canonical Events`

Hard properties retained by the evaluator:
- impossible/hard-prerequisite failure occurs before stochastic mapping;
- success and hazard remain separate axes;
- actor ID/name is not a capability bonus;
- tools contribute only when the fixture explicitly makes the tool available;
- local function impairment changes only dimensions tagged as relevant to that function;
- no candidate is labeled canonical, accepted, frozen or production;
- no runtime code is called or modified by this evaluation.

The executable result is shaped to remain compatible with the AF-001 boundary concepts `ActorBaseProfile`, `ActionDemandProfile`, and `ActionResolutionReceipt` without claiming their future runtime implementation.

## 2. Bounded corpus

The corpus is intentionally small enough for line-by-line review while spanning more than combat:

| Family | Fixture |
|---|---|
| restraint escape / force | `RESTRAINT_FORCE` |
| restraint escape / technique | `RESTRAINT_TECHNIQUE` |
| restraint escape / real tool | `RESTRAINT_TOOL` |
| lift/push/pull force | `LIFT_CRATE` |
| sustained effort | `SUSTAINED_CRANK` |
| precision/manual | `DISARM_TRAP` |
| coordination/balance | `BEAM_BALANCE` |
| perception/observation | `OBSERVE_TRACKS` |
| reasoning/problem-solving | `SOLVE_MECHANISM` |

`FIGHTER_A` and `SCHOLAR_B` face the same restraint challenge under force, technique and tool methods. Both have the fixture tool `PICK_SET_01`, so the tool route compares declared capability/skill inputs rather than ownership luck.

The intended directional checks are not actor-name rules. They arise from candidate inputs:
- fighter has a large force-route advantage;
- technique produces a smaller, representation-dependent gap;
- scholar has a tool-route advantage because manual/tool/reasoning inputs align with that method;
- changing the actor ID while preserving candidate inputs leaves the resolution signature unchanged.

## 3. Attribute representation ablation

All candidates below remain `EVALUATION_CANDIDATE_ONLY`.

| Candidate | Family | Durable/base dimensions in fixture | Method demand parameters across 9 tasks | Evidence strength | Strongest failure case |
|---|---|---:|---:|---|---|
| `DEMAND_PRIMITIVES_V1` | action-demand-only primitives | 9 primitive values | 22 | Excellent method expressiveness and direct locality; avoids pretending a genre-neutral actor vector is already frozen | Task-local primitives can become a hidden second character sheet unless every primitive is bound to durable evidence |
| `SMALL_CORE_V1` | small mundane core | 6 | 22 | Lowest base-vector burden; clean force/manual/perception/reasoning isolation; still distinguishes fighter/scholar by method | May collapse power/agility/balance distinctions that later prove materially important |
| `RICH_GENRE_NEUTRAL_V1` | richer genre-neutral vector | 10 | 29 | More explicit balance/power/agility distinctions and strong task expressiveness | Larger stat surface and more demand weights without current production evidence that the extra axes earn their tuning cost |

### Current interpretation

The bounded corpus does **not** justify freezing the richer vector. It also does not prove that action-demand primitives alone are sufficient durable actor state.

The strongest current research direction is therefore to keep comparing a **small durable mundane core plus explicit method-specific demand/skill/tool inputs** against the demand-primitives alternative, rather than treating the richer vector as the default merely because it is more descriptive.

That is a narrowing observation, not an OPEN_DECISION resolution.

## 4. Function-local injury probes

Two evaluation-only conditions are used:
- `HAND_ARM_IMPAIRMENT`: affects tags such as hand function and upper-limb force;
- `LEG_IMPAIRMENT`: affects balance/mobility tags.

Required executable properties:

| Probe | Required result |
|---|---|
| hand/arm impairment on force restraint | lower relevant margin |
| hand/arm impairment on manual/tool dimensions | lower relevant margin where used |
| leg impairment on beam balance | lower relevant margin |
| hand/arm impairment on `SOLVE_MECHANISM` | unchanged reasoning result |
| leg impairment on `SOLVE_MECHANISM` | unchanged reasoning result |
| all condition-adjusted outputs | finite and range-bounded |

These probes only evaluate locality. They are **not** a canonical injury taxonomy, medical model, healing system, fatigue system or I2 implementation.

## 5. Math-policy comparison

All math policies remain `EVALUATION_CANDIDATE_ONLY`.

| Candidate | Useful evidence | Main concern |
|---|---|---|
| `DETERMINISTIC_MARGIN_V1` | simplest audit baseline; direct monotonic margin; easiest replay explanation | a single aggregate margin can hide a weak required function unless prerequisites/demand definitions are explicit |
| `ADDITIVE_MULTIPLICATIVE_STACK_V1` | explicit stack ordering and deterministic behavior | multiplying the whole stack can over-penalize skill/tool contributions when a condition should be function-local |
| `TAGGED_PRIORITY_V1` | makes a weak relevant dimension visible through a bottleneck term | bottleneck weighting can create cliffs and requires evidence for the chosen priority weight |
| `BOUNDED_SEEDED_STOCHASTIC_V1` | proves feasibility-before-randomness and exact deterministic receipt replay | coarse probability buckets are still uncalibrated game policy, not scientific probability |

The stochastic candidate intentionally exposes only coarse mapping bands plus a deterministic receipt. It does not print a false-precision success percentage as if experimentally validated.

There is no caller-provided reroll seed. Repeated identical candidate input/ruleset/task produces the same seed digest and roll receipt.

## 6. Sensitivity / parameter sweeps

The governed spec executes bounded grids for:
1. fighter restraint-force capability vs difficulty, with/without hand impairment;
2. scholar precision/manual trap handling vs difficulty, with/without hand impairment;
3. scholar reasoning vs difficulty, including unrelated hand and leg impairment.

Each sweep varies relevant capability and difficulty across five-by-three grids and condition variants. The evaluator fails closed if a stronger relevant capability produces a lower deterministic margin in the governed sweep.

The report keeps reversal/dead-zone signals explicit rather than collapsing them into one score.

## 7. Adversarial evidence

The executable suite explicitly challenges:

1. actor ID/name change with identical candidate inputs;
2. irrelevant attribute perturbation on an unrelated reasoning task;
3. missing tool under stochastic policy;
4. stronger relevant capability monotonicity;
5. local injury leakage into unrelated cognition;
6. unowned/nonexistent tool bonus;
7. evaluation order mutation;
8. candidate list order dependence;
9. canonical-serialization stability;
10. deterministic stochastic receipt reproduction;
11. malformed/unknown candidate references;
12. accidental authority-bearing candidate labels.

Any failure raises an evaluation error or fails CI rather than being converted into a favorable recommendation.

## 8. Evidence dimensions kept separate

The evaluator does not emit an opaque winner score. Review should compare:
- actor/method discrimination;
- monotonicity;
- locality and irrelevant-factor isolation;
- method expressiveness;
- base dimension count;
- demand-weight parameter count;
- fake-precision risk;
- genre-extension pressure;
- explainability/auditability;
- deterministic replayability;
- AF-001 `ActionDemandProfile` / `ActionResolutionReceipt` compatibility;
- strongest counterexample for each candidate.

This is deliberate. A candidate that is easy to tune but cannot distinguish methods should not hide behind a composite score, and a highly expressive candidate should not hide its parameter burden behind the same score.

## 9. Recommendation

Recommendation status:

`INSUFFICIENT_EVIDENCE_KEEP_OPEN`

Both OPEN_DECISIONs remain open.

### Why not freeze a winner now

The executable evidence is strong enough to reject several *failure modes*, but not strong enough to claim production calibration:
- fixture actor values and demand weights are synthetic evaluation values;
- no human playtest establishes whether outcome bands feel fair;
- no production telemetry calibrates probability or modifier scales;
- genre-extension friendliness is structural reasoning here, not an executable wuxia/xianxia/science-fiction corpus;
- injury tests establish functional locality only, not gameplay or medical validity.

### Useful narrowing signal

For the next governance decision, the strongest evidence currently favors **continued comparison of `SMALL_CORE_V1` with explicit method-specific demand inputs against `DEMAND_PRIMITIVES_V1`**, while demanding stronger justification before adopting `RICH_GENRE_NEUTRAL_V1`'s larger base surface.

For math, `DETERMINISTIC_MARGIN_V1` is the clearest audit baseline. `BOUNDED_SEEDED_STOCHASTIC_V1` demonstrates reproducible uncertainty only after feasibility, but its bands remain uncalibrated. `ADDITIVE_MULTIPLICATIVE_STACK_V1` and `TAGGED_PRIORITY_V1` remain useful counter-candidates because they expose stacking/bottleneck tradeoffs rather than silently disappearing from the evaluation.

None of those statements means `RECOMMEND_*`, `ACCEPTED`, `FROZEN`, `CANONICAL`, or production authority.

## 10. Strongest counterevidence against this evaluation itself

The most important reason **not** to over-trust this suite is that it is synthetic by design. A clean deterministic benchmark can prove invariants and expose leakage, but it can also reward the assumptions encoded in its fixtures.

An Independent Reviewer should therefore attack whether:
- task weights are secretly chosen to make one representation look better;
- the corpus under-represents tasks where richer axes matter;
- the small core is getting a tuning-burden advantage without paying an expressiveness cost;
- demand primitives are merely moving hidden attributes from the actor sheet into each task definition;
- the stochastic buckets encode arbitrary taste as mathematics.

That counterevidence is why the recommendation remains `INSUFFICIENT_EVIDENCE_KEEP_OPEN` rather than declaring a winner.

## 11. Governance stop statement

`RUNTIME_SEMANTICS_UNCHANGED=true`

`OPEN_DECISION_STATUS_UNCHANGED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`

CAP-EVAL-001 produces executable evidence only. Independent Review must judge the **trustworthiness of the evaluation**, not whether the Reviewer personally prefers the recommendation. Control Tower alone may later choose a separate governance step to narrow or resolve the OPEN_DECISIONs and separately decide whether I2 runtime can be released.
