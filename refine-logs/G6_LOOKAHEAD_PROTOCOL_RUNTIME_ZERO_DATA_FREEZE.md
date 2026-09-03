# G6 lookahead protocol/runtime zero-data freeze

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `b43b5c76522eb1e40962f780387226202ab38171`  
Status: frozen before reference construction and online sampling

## Scope

This receipt freezes the sole G6 development product for
`lookahead_preall_sched` after the protocol/analyzer audit and before any new
offline-reference or online candidate result exists.  It does not authorize a
formal-paper claim or the disjoint Q61--Q80 confirmation bank.

The run root is:

`runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904`

## Release runtime

`cargo build --release --manifest-path serverless_sim/Cargo.toml --bin serverless_sim`
completed successfully in the protected target directory
`serverless_sim/target_g6_lookahead_impl`.  The build emitted 94 compiler
warnings and no errors; no tracked source file changed during the build.

| Field | Frozen value |
|---|---|
| executable | `serverless_sim/target_g6_lookahead_impl/release/serverless_sim.exe` |
| SHA-256 | `90988e545679a04f46f680d6ac7e0e0a52d8e1335c2d0309e73d4383c3147611` |
| bytes | `4809728` |
| source commit | `b43b5c76522eb1e40962f780387226202ab38171` |

## Frozen zero-data artifacts

The protocol generated one candidate-only homogeneous-low cell with exactly
five development seeds, D71--D75.  It projected the five already captured G3
workload tapes without deriving a new tape and bound those tapes before any
reference build or online run.

| Artifact | Canonical document hash | File SHA-256 |
|---|---|---|
| `g6.unbound.json` | `d7d6d6f3b4ee0c5e735dadfd6fc19e343bea69138c2f6508c43af5785ebd2a69` | `bc9233dcece50e9ca8b31b4692fd2f902de4364cb6108995bf8b8509986f2633` |
| `g6.tape.catalog.json` | `522df06b71f56fc2749123f1a11bc1f75b5b15339d64febd1324c6b6563c37e8` | `fa53d9f3cadccdb04d9efe51572f8ec28e00265c758ce332429e973be1335e1a` |
| `g6.tapes.json` | `eea6c45ff52ba854c37fd2f51c534f58bbc7da6eff0c6a551d08a807682deea1` | `1ddeadde1a4b7e1d195e147978cc91bd2b6ffae47641e796ee3362593030745c` |

The source G3 tape catalog file SHA-256 is
`95b638e09d91444f6a78d6a09437a833dbd87449362639d1b168573422d675a4`.
The already frozen G3 ready-manifest and selection file SHA-256 values remain
`a54f0fbbbe02d0b1559b1b094eeefe77f1860b522a6c26b9c69b03262ced02f4`
and `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`,
respectively.

## Fail-closed checks

- `protocol validate g6.tapes.json` passed with five runs and one new cell.
- The only seeds are D71, D72, D73, D74, and D75; all five run IDs and full
  run-spec hashes are fixed in `g6.tapes.json`.
- Every run is `sche_nash` with `lookahead_preall_sched`, strict best response,
  zero relative-regret guard, `parents_scheduled` player collection, and
  `paper_equations_changed=false`.
- All five source tape paths exist and their live SHA-256 values match the
  manifest.  Their event counts, in seed order, are 1908, 1926, 1896, 1916,
  and 1908.
- The source-product binding contains 50 unique retained homogeneous-low
  controls: five G3 C0 runs plus 45 baseline runs.  No baseline is scheduled
  for re-execution.
- The five required G6 offline-reference keys are unique and have zero
  intersection with all homogeneous-low G3 NSESche reference keys.
- All reference hashes remain null and `build_required=true` at this boundary.
- Neither `stages/reference_builds` nor `online` exists under the G6 run root.
  Therefore no G6 reference result, candidate result, performance metric, or
  result-conditioned selection was available when this freeze was made.
- The manifest fixes `all_valid_runs_retained=true`,
  `first_valid_canonical_result_retained=true`, and
  `result_conditioned_extension=false`.

## Authorization boundary

This freeze authorizes construction of exactly the five predeclared
candidate-specific offline social-utility references.  The resulting catalog
and ready manifest must be audited and committed before the five online
D71--D75 candidate runs begin.  Online sampling, result analysis, Q61--Q80
confirmation, figures, and manuscript claims remain blocked at this point.
