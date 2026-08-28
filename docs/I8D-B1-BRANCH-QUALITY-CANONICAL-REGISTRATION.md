# I8D B1 BranchQualityEvidence canonical registration

Status: `CANONICAL_REGISTRATION_CANDIDATE / NO_RUNTIME / NO_PX_SCORING`.

B1 migrates the parent machine-contract registry from `1.9.0-candidate` to `1.10.0-candidate`, authority graph from `AF001-AUTHORITY-GRAPH-1.9-I2A008@1` to `AF001-AUTHORITY-GRAPH-1.10-I8DB1@1`, Golden suite from `1.7.0-candidate` to `1.8.0-candidate`, and decision-lifecycle bindings from `1.2.0-candidate` to `1.3.0-candidate`.

The B0 interface shape is preserved. Canonical registration grants schema/derived-view legitimacy only; `canonical_data_authority` remains `NONE`. The registered Golden provenance artifact contains replayable Stage A R1 packages for I5A, I7A and I8C and is mechanically replayed in tests. The B0 synthetic fixture suite remains non-source-proof evidence.

Historical tuple `1.9.0-candidate` + `AF001-AUTHORITY-GRAPH-1.9-I2A008@1` + `1.7.0-candidate` cannot authorize BranchQualityEvidence. Existing registered extensions are rebound to the new parent registry epoch without changing gameplay formulas or authority scope.

Hard locks: no BranchQuality runtime producer, no PX scoring/weights, no world or knowledge mutation, no automatic Storylet/encounter realization, no engagement/retention objective, no provider/renderer authority.
