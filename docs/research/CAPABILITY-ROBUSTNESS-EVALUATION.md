# CAP-EVAL-002 Held-out Capability Robustness Evaluation

Status: `EVALUATION_EVIDENCE_ONLY / NON_CANONICAL_CANDIDATES / NO_I2_RUNTIME_AUTHORITY`

Release base: `32e2a1a830f0685af207275da0ad4849e7637ea4`

Predecessor evidence: Issue #24 / merged PR #25 / accepted head `6e665ca3f02795564119383f52f7643190997eec`.

This report is bounded CAP-EVAL-002 evidence for `OD-CAPABILITY-ATTR-001` and `OD-CAPABILITY-MATH-001`. It does not modify either OPEN_DECISION, does not implement Capability/Skill/Injury gameplay runtime, and does not authorize I2.

## 1. What this evaluation can and cannot establish

The executable suite can establish structural properties of the candidate representations and math policies: held-out discrimination, declared qualitative ordering, locality, prerequisite dominance, perturbation behavior, deterministic replay, label/order independence, parameter burden, and whether explicit genre extensions can remain outside the mundane base representation.

It cannot establish player-facing fairness, genre desirability, progression feel, probability calibration, injury realism, or production tuning. Those claims require playtest or production evidence and are deliberately excluded from the recommendation authority here.

Governance locks remain:

- `RUNTIME_SEMANTICS_UNCHANGED=true`
- `OPEN_DECISION_STATUS_UNCHANGED=true`
- `NO_I2_RUNTIME_IMPLEMENTED=true`

## 2. True held-out corpus

CAP-EVAL-002 declares eight task families whose IDs and normalized task semantics are checked against the CAP-EVAL-001 predecessor corpus. A duplicate ID or duplicate normalized task definition fails closed.

| Held-out family | Fixture | Pressure being tested |
|---|---|---|
| explosive / rapid force | `BREACH_DOOR_BURST` | burst power distinct from slow force |
| whole-body change of direction | `CROWD_DODGE_CUT` | rapid agility distinct from static balance |
| precision under time pressure | `TIMED_NEEDLE_ALIGNMENT` | manual precision + control under pressure |
| multi-stage tool manipulation | `VALVE_BYPASS_SEQUENCE` | hard real-tool prerequisite before resolution |
| noisy/ambiguous observation | `FOG_SIGNAL_DISCRIMINATION` | perception + analysis under weak evidence |
| reasoning with irrelevant impairment | `LOGIC_GRID_WITH_WRIST_SPLINT` | physical-condition locality |
| sustained coordinated physical work | `ROPE_BRIDGE_HAUL` | endurance + control |
| assistance/teamwork-shaped pressure | `TWO_PERSON_STRETCHER_SYNC` | representation pressure only, not PARTY runtime |

The evaluator contains no actor fixture names, held-out task fixture names, or predecessor candidate IDs. Actor, task, representation, and math-policy renames preserve semantic receipts when their semantic inputs remain unchanged.

## 3. Representation-collision evidence

The collision probes intentionally ask whether the currently declared candidate surfaces can express two distinctions that CAP-EVAL-001 left unresolved. They do not contain an `expected_winner` label.

| Probe | `DEMAND_PRIMITIVES_V1` | `SMALL_CORE_V1` | `RICH_GENRE_NEUTRAL_V1` |
|---|---:|---:|---:|
| burst/power collision, margin delta | `0.0` | `0.0` | `19.95` |
| agility/change-of-direction collision, margin delta | `0.0` | `0.0` | `10.4625` |

This is real structural counterevidence against prematurely freezing the previous small-core/primitives narrowing: in the declared predecessor forms, neither `SMALL_CORE_V1` nor `DEMAND_PRIMITIVES_V1` can distinguish these actor pairs without adding some extra evidence-bearing semantic input. `RICH_GENRE_NEUTRAL_V1` can distinguish both because it already carries explicit `power` and `agility` axes.

However, that does **not** prove those axes belong in durable mundane actor truth. The probes were designed specifically to pressure those distinctions, and synthetic evidence cannot decide whether a future design should represent them as durable base attributes, derived capability, explicit technique/skill state, or another separately governed structure.

## 4. Parameter and weight robustness

For every declared qualitative relation, every representation candidate and every math-policy candidate, the evaluator independently perturbs:

- left-actor relevant capability: `-5 / 0 / +5`;
- right-actor relevant capability: `-5 / 0 / +5`;
- task difficulty: `-5 / 0 / +5`;
- task representation/skill weight tilt: `0.9 / 1.0 / 1.1`.

That produces **81 perturbation combinations per relation**. The four held-out qualitative relations preserve their declared ordering in **81/81 cases** for every representation/math combination. No small-perturbation reversal is observed, so `fragile_relation_count = 0` throughout this bounded grid.

The stricter margin-band metric is intentionally more sensitive: only `0.333333` of the perturbation combinations remain within the declared ±2 margin band of baseline for each relation under the deterministic audit baseline. This prevents “rank stable” from being misreported as “numerically insensitive”. Rank ordering is robust here; exact margin magnitude is tuning-sensitive.

### Representation parameter burden

| Candidate | durable/base dimensions | held-out representation weight entries |
|---|---:|---:|
| `SMALL_CORE_V1` | 6 | 17 |
| `DEMAND_PRIMITIVES_V1` | 9 | 17 |
| `RICH_GENRE_NEUTRAL_V1` | 10 | 25 |

`RICH_GENRE_NEUTRAL_V1` earns extra collision discrimination, but it also carries the largest durable surface and the largest held-out weight burden. That unresolved expressiveness-versus-burden tradeoff is why this evaluation does not recommend resolving the attribute OPEN_DECISION yet.

## 5. WUXIA / XIANXIA / SF extension pressure

Three explicit extension envelopes are exercised:

- WUXIA: qinggong / internal-force-control style inputs;
- XIANXIA: qi-control / formation style inputs;
- SF: hacking / piloting / cybernetic-assist style inputs.

For all three predecessor representation candidates:

1. genre inputs live in an explicit extension-input namespace, not in the mundane base representation;
2. mutating those extension inputs does not change the mundane receipt when no extension fixture is selected;
3. selecting the extension fixture changes only the evaluation-only extension contribution;
4. the base-representation snapshot digest remains unchanged.

This supports a structural rule that genre extension can be explicit without silently redefining mundane core attributes. It does not implement WUXIA, XIANXIA, SF, PARTY, or any production genre runtime.

## 6. Math-policy held-out comparison

All four CAP-EVAL-001 math-policy candidates are exercised on held-out monotonicity and locality probes.

| Math family | bounded monotonicity | unrelated wrist impairment changes reasoning? | relevant wrist impairment changes tool route? | tool-condition penalty | excess vs deterministic |
|---|---|---|---|---:|---:|
| deterministic margin | pass | no | yes | `11.2875` | `0.0` |
| bounded seeded stochastic | pass | no | yes | `11.2875` | `0.0` |
| tagged priority | pass | no | yes | `11.8975` | `0.61` |
| additive/multiplicative stack | pass | no | yes | `16.561393` | `5.273893` |

The additive/multiplicative candidate shows the strongest held-out concern in this diagnostic: its global multiplicative condition factor also scales contributions that are not themselves the impaired function, producing a materially larger penalty than the deterministic local audit baseline. The tagged-priority candidate remains monotonic here but introduces a smaller extra bottleneck penalty and still requires a separately justified bottleneck weight.

The seeded stochastic candidate reproduces the exact same semantic seed, roll and sampled outcome in fresh evaluations. Feasibility remains before sampling. Its probability buckets are still explicitly uncalibrated, so replayability is evidence for determinism, not evidence that the probability curve is valid player-facing law.

## 7. Candidate-overfit and label-dependence guards

The regression suite proves:

- held-out task IDs and normalized definitions are distinct from CAP-EVAL-001;
- the evaluator source has no actor fixture names and no representation/math candidate IDs;
- there is no `expected_winner` branch;
- every held-out task covers every representation candidate;
- candidate order and task order do not change structured evidence;
- actor/task/representation/math renames do not change semantic resolution;
- collision paths and actor/difficulty/weight perturbation paths are non-vacuous;
- missing required tool fails before stochastic mapping;
- WUXIA/XIANXIA/SF inputs do not pollute mundane base semantics;
- repeated execution is canonical-serialization stable;
- separate fresh Python interpreter processes emit byte-identical canonical JSON;
- evaluation does not mutate its input specs;
- no candidate output receives authority-bearing status.

## 8. Strongest counterargument against the suite

A larger synthetic suite can still be a more elaborate mirror of its author's assumptions. In particular, the burst and agility collision probes deliberately test distinctions represented explicitly only by the current rich-vector candidate. They prove a **representation fact** about the three declared candidate shapes, not a **game-design fact** that power and agility must be durable base stats.

Similarly, 81/81 qualitative ordering preservation proves bounded structural robustness under this declared grid. It does not prove that ±5 actor perturbations, ±5 difficulty, or 0.9–1.1 weight tilts are the correct production calibration envelope.

Therefore the legitimate architectural evidence is:

- hard prerequisites before uncertainty;
- deterministic semantic replay;
- local impairment should remain local;
- labels/order must not alter outcomes;
- genre-specific inputs can stay outside mundane core;
- the current small-core/primitives shapes lose burst/agility distinctions in the declared collision pairs;
- global multiplicative condition stacking creates a non-local penalty in the held-out tool diagnostic.

The claims that still require later tuning/playtest evidence are the final base-stat ontology, exact demand weights, exact condition multipliers, difficulty scale, outcome bands, and stochastic probability calibration.

This distinction avoids an endless evaluation treadmill: architectural substrate can be governed before player telemetry, while tuning values need not block architecture indefinitely.

## 9. Governance recommendation

The attribute evidence is now genuinely two-sided. The rich vector earns held-out discrimination that the other two declared candidates do not, but it pays 10 durable dimensions and 25 held-out representation weights versus 6/17 for the smallest candidate. Synthetic collision probes cannot decide whether those extra axes belong in durable actor truth or should be represented by explicit derived/skill/technique semantics. The attribute decision should therefore remain open rather than pretending this suite resolved that ontology question.

For math, the held-out evidence supports splitting architecture from later tuning. `DETERMINISTIC_MARGIN` is monotonic, auditable, local in the tested condition path, and sufficient to carry an authoritative ordering/margin substrate. Seeded stochastic replayability can remain a separately governed optional presentation/uncertainty layer whose buckets require later calibration. This is a recommendation to Control Tower, not an enacted split and not I2 authorization.

ATTR recommendation class: `KEEP_ATTR_OPEN`

MATH recommendation class: `RECOMMEND_RESOLVE_MATH_DETERMINISTIC_MARGIN_SUBSTRATE_WITH_SEPARATE_STOCHASTIC_TUNING`

`RUNTIME_SEMANTICS_UNCHANGED=true`

`OPEN_DECISION_STATUS_UNCHANGED=true`

`NO_I2_RUNTIME_IMPLEMENTED=true`
