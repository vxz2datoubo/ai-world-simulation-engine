# I8D Stage B0 — BranchQualityEvidence interface freeze

Status: `INTERFACE_FREEZE_CANDIDATE_NOT_CANONICAL`

Governance: Issue #93

Canonical release base: `a06e739dfa329889a0110028ca8f7fe2f343e65b`

## 1. Why this freeze exists

Stage A, the Stage A R1 semantic repair, and Stage A2 now provide enough evidence to freeze a **minimal candidate evidence interface**. They do not justify a universal quality score, PX objective, hidden narrative judge, or direct canonical registration without a separate migration review.

B0 therefore freezes shape and authority boundaries only. The candidate remains non-canonical because the parent machine registry does not register it. Child self-declaration confers no authority.

B1 is a separate future task. B1 must independently advance the parent machine-contract and Golden suite versions, register the extension from both parents, prove that the historical parent version tuple cannot authorize the new extension, and preserve all B0 authority boundaries.

## 2. Evidence-derived split

### 2.1 Portable integrity assessments

Only three assessments are frozen as cross-source portable candidates:

- `causal_world_integrity`
- `agency_legibility`
- `knowledge_provenance_integrity`

The portability invariant is deliberately narrow:

`ASSESSMENT_LEVEL_PORTABILITY_ONLY_NOT_BYTE_IDENTICAL_EVIDENCE_MATERIAL`

Stage A2 showed that the same integrity assessment can remain stable while the concrete evidence material differs by mechanism and source. A later production contract must not turn assessment-level stability into a requirement that source-evidence blobs be identical.

### 2.2 Opportunity scarcity is not quality

`legal_dead_end_opportunity_scarcity_risk` is represented separately as `opportunity_scarcity_evidence`.

It may change when a legal opportunity appears, disappears, or becomes suppressed. That change does not imply world corruption, player-agency failure, or knowledge-provenance failure. `NO_VALID_OPPORTUNITY` and `NO_VALID_STORYLET` remain legitimate outcomes.

### 2.3 Mechanism-local optional evidence

The following evidence remains source-scoped and optional:

- `character_relationship_continuity`
- `meaningful_state_information_relationship_delta`
- `setup_promise_anchor_continuity`
- `contrivance_repetition_risk`

`NOT_APPLICABLE` is a first-class state. Missing mechanism evidence is not automatically bad quality.

### 2.4 Authored metadata remains outside V1 evidence

The B0 candidate excludes:

- `genre_theme_design_fit`
- `recoverable_thread_availability`

Those may remain useful authored-design metadata for later narrative craft tooling, but they cannot mint world truth, legality, knowledge, integrity, PX authority, or BranchQualityEvidence.

## 3. Authority profile candidate

The candidate profile is:

- canonical data authority: `NONE`
- schema steward: `AWRSE_AF_F_CONTRACT_STEWARD`
- assembler: `AWRSE_NARRATIVE_COMPOSITE_VIEW_ASSEMBLER`
- downstream readers: `NARRATIVE_OPPORTUNITY`, `PX_RANKING`, `AI_DIRECTOR`
- staging authority: `NONE`

Assembly may describe already-validated evidence only. It cannot legalize invalid candidates, create or rewrite world facts or knowledge, lower capability difficulty, create player intent, force Storylet/encounter realization, retcon, resurrect, or force reconvergence.

PX remains downstream and non-canonical. It may eventually consume BranchQualityEvidence only after legality gates. It cannot use evidence to legalize an invalid candidate.

## 4. Candidate payload

The candidate payload contains only:

### Identity and exact provenance
- `evidence_id`
- `evaluated_subject_ref`
- `source_kind`
- `source_package_sha256`
- `source_i1_sha256`
- `evidence_version`
- `authority_class`

### Portable integrity
- `causal_world_integrity`
- `agency_legibility`
- `knowledge_provenance_integrity`

### Dynamic opportunity state
- `opportunity_scarcity_evidence`

### Mechanism-local evidence
- `mechanism_evidence`

No scalar score, weight, rank, selection, legality result, mutation command, realization command, engagement/retention objective, hidden truth, or player-intent field exists.

The initial source-kind envelope is intentionally limited to the mechanisms actually tested by Stage A2: I5A information opportunity, I7A World Echo, and I8C Storylet. Adding a new source kind is a new evidence claim and requires later governed evaluation.

The B0 fixture suite is explicitly `SYNTHETIC_INTERFACE_SHAPE_FIXTURE_ONLY_NOT_SOURCE_PROOF`. Its SHA-256-shaped values validate the interface form and fail-closed rules; they are **not** claims that those exact hashes are canonical source packages or I1 replay digests. B1 must bind real replay-valid provenance before canonical promotion.

## 5. Fail-closed fixture semantics

The B0 validator rejects:

- unknown top-level fields;
- numeric scalar values anywhere in the payload;
- unvalidated source kinds;
- malformed source/I1 digests;
- authority-class escalation;
- authored metadata injection;
- score/rank/legality/player-intent/realization fields;
- unknown mechanism axes;
- `NOT_APPLICABLE` mechanism evidence carrying refs;
- non-`NOT_APPLICABLE` mechanism evidence without refs;
- malformed scarcity states;
- stale parent/Golden version context;
- premature parent registration.

The governance regression additionally reads the canonical `docs/AF001-TRACEABILITY.md` registry directly. B0 remains valid only while `OD-CLUE-QUALITY-001` and `OD-PX-SCORING-001` continue to expose unresolved competing options, risks, and required research. B0's own child declaration cannot close those decisions.

Negative fixtures assert exact failure codes so future relaxations cannot silently broaden authority.

## 6. B1 migration gate

B0 explicitly does **not** authorize B1.

After independent B0 ACCEPT, B1 must at minimum:

1. fresh-reconcile current canonical main;
2. advance `AWRSE-AF001-LIVING-STORY-CONTRACTS` from the historical B0 parent version;
3. advance `AWRSE-AF001-GOLDEN-SCENARIOS` and its required parent-contract version;
4. add inverse parent registration for the binding;
5. add inverse Golden fixture registration;
6. prove the old parent contract / Golden suite tuple cannot authorize the new extension;
7. preserve `canonical_data_authority = NONE`;
8. preserve assessment-level portability rather than evidence-material identity;
9. fresh-reconcile `OD-CLUE-QUALITY-001` and `OD-PX-SCORING-001` from canonical traceability and keep unresolved metric/PX policy outside this interface;
10. replace B0 synthetic shape-only hash fixtures with real replay-valid source-package and I1 provenance evidence before any canonical promotion;
11. keep runtime and PX scoring separately unauthorized.

## 7. Explicit non-goals

B0 does not:

- implement runtime BranchQuality assembly;
- define a universal quality/fun/drama score;
- implement PX ranking, objective, weights, or policy;
- change legality;
- mutate world or knowledge;
- realize a Storylet or encounter;
- resurrect/retcon/reconverge;
- create player intent;
- grant LLM, Director, renderer, or provider authority;
- define engagement or retention optimization;
- implement PARTY or PUBLIC scope.

The purpose is a narrow contract freeze, not a narrative optimizer.
