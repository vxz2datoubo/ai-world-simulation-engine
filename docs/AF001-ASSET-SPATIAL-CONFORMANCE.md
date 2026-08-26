# AF-001 Asset / Spatial Conformance Gate

Status: `EXECUTABLE_CONFORMANCE_EVIDENCE_ONLY / NOT_AUTHORITY_EXTENSION`

Governance task: `ASSET-SPATIAL-CONFORMANCE-001` / Issue #60.

Canonical base at release: `9379e8d6e4cf085f9c157e59b4c02ae6a0d26d86`.

## 1. Purpose

This slice turns already-frozen AF-001 spatial and asset identity laws into deterministic executable evidence without creating a competing spatial graph, asset registry, renderer authority, storage system, or runtime implementation.

The canonical authority remains:

- `ARCHITECTURE.md`
- `contracts/AF001-LIVING-STORY-CONTRACTS.json`

The executable evidence is:

- `evals/AF001-ASSET-SPATIAL-CONFORMANCE.json`
- `tests/test_af001_asset_spatial_conformance.py`

This task intentionally does **not** modify the canonical parent contract. That keeps the work parallel-safe with I2A-010 / PR #59 and prevents a child file from pretending that self-declaration grants canonical authority.

## 2. Existing canonical interfaces reused

The evaluator binds the exact current parent tuple:

- contract: `AWRSE-AF001-LIVING-STORY-CONTRACTS`
- contract version: `1.9.0-candidate`
- authority graph: `AF001-AUTHORITY-GRAPH-1.9-I2A008@1`

It reuses, without redefining, these AF-001 types:

### AF-B world/spatial authority

- `WorldFrame`
- `Scene`
- `Zone`
- `Portal`

### AF-D spatial-view / asset authority

- `CameraAnchor`
- `View`
- `MediaAsset`
- `MediaVersion`
- `Locator`

The evaluator also asserts the exact parent authority-profile binding for each type. A parent type/version/profile drift fails the test rather than being silently accepted.

## 3. Authority boundary

Two classes are deliberately separated.

### 3.1 Parent-frozen law

These semantics already exist in AF-001 and the evaluator exercises them:

- stable machine identity is not a human name, filename, or locator;
- camera position is not camera facing;
- a View is a stable spatial-semantic view definition, not a media file;
- `MediaAsset != MediaVersion != Locator`;
- locator migration cannot change asset/version identity;
- generated pixels cannot create canonical world, topology, presentation, or damage truth;
- renderer/publication is downstream projection only.

### 3.2 Candidate evaluation-only policy

Some production-grade concepts from ASSET-DESIGN-001 are useful to test now but are **not** silently promoted into AF-001 canonical types or fields by this task:

- `CanonicalSpatialGraphFixture`
- `TextMapProjectionFixture`
- `ImageMapProjectionFixture`
- `ExplicitViewRelationFixture`
- `AssetSelectionProjectionFixture`
- `VersionSelectionProjectionFixture`
- `StoryAssetPackFixture`
- `ResolverProbeFixture`
- a current-version selection pointer/lifecycle projection

Every such object is marked `NONCANONICAL_EVAL_ONLY`.

If a future task wants any of these to become canonical runtime-facing authority, that task must explicitly change/register the parent machine contract, analyze migration/replay impact where applicable, pass exact-head CI, and receive independent review. This conformance gate is evidence for that future decision, not a shortcut around it.

## 4. Synthetic fixture

The fixture uses one world frame and a tiny three-scene topology: plaza, hall, and tower.

It contains:

- one cardinal portal from plaza to hall;
- one vertical portal from hall to tower;
- an east-side camera anchor whose perspective View faces west;
- a west-side reciprocal camera anchor;
- an overhead View with screen-top north;
- stable logical day/night media assets;
- immutable media versions;
- multiple locators for the same immutable version;
- two synthetic story packs that reuse one logical asset by ID reference.

No synthetic object becomes canonical world data. The entire graph exists only as deterministic evaluation material.

## 5. Executable cases

The gate includes more than the required twenty cases. It covers:

1. text/image map graph identity drift;
2. map north-orientation drift;
3. camera-position/facing conflation;
4. positive east-side camera + west-facing View resolution;
5. inferred shot/reverse-shot rejection;
6. duplicate default asset/context rejection;
7. multiple-current-version rejection;
8. locator migration changing version identity rejection;
9. same pixels minting a new version rejection;
10. changed pixels reusing an immutable version rejection;
11. time/weather/lighting-style variant modeled as ordinary revision rejection;
12. text/image map topology disagreement rejection;
13. unknown portal endpoint rejection;
14. vertical topology flattened into a false cardinal edge rejection;
15. renderer-invented topology rejection;
16. dynamic state contamination of logical asset identity rejection;
17. revisit minting a new stable asset without explicit identity-changing evidence rejection;
18. unverified version promoted as current rejection;
19. story pack embedding/duplicating shared asset identity rejection;
20. stale/unavailable target asset being replaced by a semantically similar asset rejection;
21. direction inferred from filename/opaque ID rejection;
22. View treated as a file/locator rejection;
23. generated media requesting canonical topology mutation rejection.

The positive base fixture must also pass as a whole.

## 6. AI-film pattern evidence

The following files were consulted as mature implementation-pattern evidence:

- `vxz2datoubo/eustia-ai-film/10_运行时/scene_asset_identity_schema.yaml`
- `vxz2datoubo/eustia-ai-film/10_运行时/scene_media_resolver_manifest.yaml`

Useful patterns include opaque stable IDs, separation of camera anchor and facing, separation of logical asset/version/locator, explicit relations, current-version verification, locator migration, and fail-closed media unavailability.

They are **not** AWRSE authority. No Eustia ID namespace, storage policy, ChatGPT Library locator policy, renderer policy, or production registry is imported into AWRSE.

## 7. Explicit non-goals

This task does not:

- modify `runtime/**/*.py`;
- implement a spatial graph runtime;
- implement a media resolver;
- implement renderer integration;
- generate or inspect production images;
- choose SQLite/Postgres/Redis/object storage;
- adopt OpenUSD/OpenAssetIO/Unreal/OTIO as runtime dependencies;
- add a second asset database;
- register `StoryAssetPack`, map projections, or explicit View relations as canonical AF-001 types;
- alter capability/I2A semantics;
- modify any I2A-010 file.

## 8. Promotion rule

A passing conformance gate means only:

`THE_CURRENT_AF001_TYPES_PLUS_THE_EXPLICIT_EVAL_ONLY_CANDIDATE_RULES_FORM_A_DETERMINISTIC_NON_COMPETING_REFERENCE_MODEL`

It does **not** mean:

`NEW_ASSET_OR_SPATIAL_RUNTIME_AUTHORITY_GRANTED`

It does **not** mean:

`EVAL_ONLY_FIXTURE_TYPES_ARE_CANONICAL`

It does **not** mean:

`RENDERER_OR_STORAGE_IMPLEMENTATION_AUTHORIZED`

Engineering stops at exact-head evidence + independent review. No self-review and no merge by the Engineering Worker.
