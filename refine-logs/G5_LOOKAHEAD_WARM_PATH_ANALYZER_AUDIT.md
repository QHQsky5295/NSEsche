# G5 lookahead/warm-path analyzer audit

Date: 2026-09-04

Implementation commit: `18e911e`

Status: one read-only invocation authorized

## Frozen implementation

The G5 analyzer implements only the measurements and decision rules frozen in
`G5_LOOKAHEAD_WARM_PATH_DIAGNOSIS_PREREGISTRATION.md`.  It does not execute the
simulator, alter a run, change Eqs. (1)--(20), select seeds, implement a new
scheduler candidate, or authorize formal progression.

Files and SHA-256 receipts:

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/analysis/g5_lookahead_warm_path.py` | `34f310065541b6312a7deb61fb3c86cab966adbe99b63fed241ea91554d31acc` |
| `scripts/reviewer_experiments/analysis/tests/test_g5_lookahead_warm_path.py` | `0c4435c17a2a68a78def2cb926ef4aaf5e92ad661635ce8002e119b31f0e0f31` |

The analyzer hard-binds the closed G4 report file/document hashes, the failed
G3-E0 selection, the ready-manifest hash, and the exact 50-run G4 run set.  It
revalidates each canonical run and requires its manifest/QC receipts to equal
the receipts already stored by G4.

The source contract binds NSESche, FaaSRank-P, OCS, Hiku, Jiagu, Orion, and the
shared `CollectTaskConfig` definition.  Direct validation passed for all seven
files and maps collection modes to `PreAllDone`, `PreAllSched`, or `All` without
depending on filename capitalization.

## Fail-closed behavior

For every active C0 window the implementation requires exact assignment-state
partitioning, bounded warm availability/bypass counts, complete assignment,
prepared and sent command counts equal to assigned players, no invalid
assignment or failed channel, and zero selected-lower-utility-than-warm cases.
It also rejects a completed-function same-frame join that exceeds dispatched
players.  Output files are atomic, fixed-name, and non-overwriting.

The decision code cannot authorize implementation or sampling.  A passing
lookahead path returns only
`candidate_preregistration_authorized=pre_all_scheduled_strict_eq15`; a passing
warm-bypass path returns only `warm_bypass_family`.  Both leave
`source_change_authorized`, `new_sampling_authorized`, and
`formal_progression_authorized` false.

## Verification

- Python compilation: pass.
- Black formatting check: pass.
- New G5 directed tests: 5/5 pass.
- Combined G3--G5 analysis regression: 27/27 pass.
- Live seven-file source-contract validation: pass.
- `git diff --check`: pass before the implementation commit.

Directed tests cover early-binding overlap boundaries, full/common pair
orientation, full/common decision thresholds, warm/non-warm accounting and
fail-closed lower-utility rejection, and narrow authorization semantics.

## Authorization

Exactly one invocation is authorized against the unchanged 50-run
homogeneous-low D71--D75 product.  It must use the committed analyzer above and
write only the five preregistered products under a new `lookahead_warm_diagnosis`
directory below the existing G3-E0 run root.  No simulator run, overwrite,
source edit, new seed, candidate implementation, formal experiment, plot, or
paper claim is authorized before a committed G5 result audit.
