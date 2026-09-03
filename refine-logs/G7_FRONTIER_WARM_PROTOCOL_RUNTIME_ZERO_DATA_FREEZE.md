# G7 bounded-frontier warm protocol/runtime zero-data freeze

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `9c16366dd820b824db12bb6c320e6afabd934ec8`  
Status: frozen before reference construction and online sampling

## Scope

This receipt freezes the sole G7 development product for
`lookahead_frontier1_warm_init` after the implementation/protocol audits and
before any new offline-reference or online candidate result exists.  It does
not authorize a confirmation sample, a formal experiment, a figure, or a paper
claim.

The run root is:

`runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904`

## Release runtime

`cargo build --release --manifest-path serverless_sim/Cargo.toml --bin serverless_sim`
completed successfully in the protected target directory
`serverless_sim/target_g7_frontier_warm_impl`.  The build emitted 94 existing
compiler warnings and no errors; no tracked source file changed during the
build.

| Field | Frozen value |
|---|---|
| executable | `serverless_sim/target_g7_frontier_warm_impl/release/serverless_sim.exe` |
| SHA-256 | `593f79671b7b8659b7df6ef2c2c240e74f409ed53c3956e4e2cfaca93e2918b7` |
| bytes | `4815872` |
| source commit | `9c16366dd820b824db12bb6c320e6afabd934ec8` |

## Frozen zero-data artifacts

The protocol generated one candidate-only homogeneous-low cell with exactly
five development seeds, D71--D75.  It projected only the five already captured
G3 workload tapes and derived no new workload.

| Artifact | Canonical document hash | File SHA-256 |
|---|---|---|
| `g7.unbound.json` | `241e5c24caf1ed2ef73a77c596d1c35e6b8694ca035d677993997487af061ead` | `735b03906482caf837d6b4c5a789c4cf99cac987d3e01ad194cb2a8a3de606f7` |
| `g7.tape.catalog.json` | `75a551472a5fef852793dca87e14f177057dcbc810847a898affe2158638b353` | `00fa4bc913f7deebc2934399ae9adca3b2f30e71e7899bf27f7fdd01f47fe3fc` |
| `g7.tapes.json` | `ce8b54b2eac1c24f11c673b9c2cb2f452fcb7ac11e748d1ab24c8089d3298e00` | `4e17729fd6f4851dc037b3e9ed419a848c82464a1daababf62bf9a36b3362708` |

The source G3 tape-catalog file SHA-256 is
`95b638e09d91444f6a78d6a09437a833dbd87449362639d1b168573422d675a4`.

## Frozen run identities

| Seed | Run ID | Run-spec SHA-256 | Tape events |
|---|---|---|---:|
| D71 | `TSCv1.E1.homogeneous.n20.low.sche_nash.FD71.2b94496e` | `3b04b4b2066512bcb8c2c7a3c7f51cbedfd0d9dcdb47ad39cbc06ac3c17de602` | 1908 |
| D72 | `TSCv1.E1.homogeneous.n20.low.sche_nash.FD72.4daaf7b5` | `218e603890731c6b79bddd577876863cba6fab7cd6f126a19c2338f526b191dc` | 1926 |
| D73 | `TSCv1.E1.homogeneous.n20.low.sche_nash.FD73.4a856fec` | `be9bc3900fb42704e46a55a457870f3f79d6ea9bce26b75bc79f19075409072b` | 1896 |
| D74 | `TSCv1.E1.homogeneous.n20.low.sche_nash.FD74.73602505` | `dc3226b7acaddba39034afc888fec37b96f240a614daa36ab3ee35416b6a4f38` | 1916 |
| D75 | `TSCv1.E1.homogeneous.n20.low.sche_nash.FD75.2316e603` | `527e299aeb1b90cf9e68cb9ee4e3e92fc43844f07d11f3112c0ca2b46d62ea36` | 1908 |

## Fail-closed checks

- `protocol validate g7.tapes.json` passed with five runs and one new cell.
- Every run is `sche_nash` with the G7 candidate, strict Eq. (15), zero
  relative-regret guard, bounded-frontier collection, registered warm
  initialization, stable player order, and `paper_equations_changed=false`.
- All five source tape paths exist; every live SHA-256 matches the manifest.
- The source binding contains 50 unique retained homogeneous-low controls:
  five G3 C0 runs plus 45 baseline runs.  No control is scheduled for rerun.
- The five candidate-specific reference keys are unique and have zero
  intersection with both the G3 homogeneous-low NSESche reference keys and the
  five G6 reference keys.
- All five reference hashes are null and all five dependencies retain
  `build_required=true`.
- The G7 root contains only the three frozen JSON documents.  Neither
  `stages/reference_builds` nor `online` exists, so no G7 reference result,
  candidate metric, or result-conditioned decision was available at freeze.
- The manifest fixes `all_valid_runs_retained=true`,
  `first_valid_canonical_result_retained=true`, and
  `result_conditioned_extension=false`.

## Authorization boundary

This freeze authorizes construction of exactly the five predeclared
candidate-specific offline social-utility references, once each in manifest
order.  Their tables, receipts, process outcomes, and ready manifest must be
audited and committed before online sampling.  Online candidate runs,
result analysis, confirmation, later formal cells, figures, and manuscript
claims remain blocked.
