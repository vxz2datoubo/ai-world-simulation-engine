# AF-D-INSTANCE-ADMISSION-001

Status: `BOUNDED_REFERENCE_AUTHORITY_IMPLEMENTATION / ISSUE_66 / NOT_BROAD_I3_RUNTIME`

This slice implements the missing machine-verifiable trust boundary discovered while reviewing I3A-001 / PR #65.

Authority order:

`AF001 parent registry -> parent-registered AF-D reference manifest -> bounded admission issuer -> typed derived receipt -> downstream verifier`

The caller may request existing identities. The caller cannot provide an allowlist, admitted set, manifest, issuer identity, authority epoch, or canonical relationship graph.

The issuer and verifier both reload the canonical parent, binding, and manifest. Parent registration pins the binding and manifest by canonical JSON SHA-256 and a scoped authority epoch `AF001-AF-D-INSTANCE-ADMISSION-001@1`. A pre-extension parent with that field absent cannot authorize the new admission mechanism even though the broad AF001 contract version remains `1.9.0-candidate`.

The scoped epoch deliberately does not reinterpret the existing I2 authority graph or CapabilityDecisionReceipt epoch.

`evals/AF001-ASSET-SPATIAL-CONFORMANCE.json` remains historical conformance evidence only. Its earlier synthetic IDs acquire bounded reference authority only because the parent machine registry explicitly registers the new canonical manifest in this task; the eval artifact itself still has zero admission authority.

Receipts are deterministic derived evidence, not bearer capabilities and not cryptographic signatures. Verification re-derives every admitted View and MediaAsset/MediaVersion/Locator relationship from the canonical manifest. Copying a valid receipt cannot create a new identity; an invented or recombined identity fails during canonical re-derivation.

Explicitly not authorized:
- real renderer/provider integration;
- AI Film federation;
- production asset database/backend selection;
- broad I3 runtime;
- generated-pixel-to-world-truth flowback;
- presentation-state-to-asset-identity flowback;
- second spatial or asset registry.

PR #65 remains blocked until this slice is independently accepted and merged. After that, PR #65 must consume this typed receipt/verifier and remove its caller-constructible `identity_evidence` envelope.
