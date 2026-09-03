# G4 homogeneous-low latency analyzer audit

Date: 2026-09-04

## Decision

The G4 read-only latency analyzer is frozen at commit `99abf4e`. Exactly one
analysis of the unchanged 50-run homogeneous-low subset is authorized. No
simulator, source change, candidate, seed, formal experiment, or plot is
authorized.

## Frozen implementation

- Analyzer:
  `scripts/reviewer_experiments/analysis/g4_hom_low_latency.py`.
- Analyzer SHA-256:
  `733105bd641a5aa7cdd5742a3dafb28db17f011313bed33724ef8d3bb99c2656`.
- Directed tests:
  `scripts/reviewer_experiments/analysis/tests/test_g4_hom_low_latency.py`.
- Test SHA-256:
  `7c4f4919ef7bbb73b14bf86accbab2c6cb2b81a22b3167b6d27583395eeea6aa`.
- The parent selection file/document hashes remain hard-bound to
  `22e5cf35...f3f7` / `4cb006a3...6a34`.
- The analyzer revalidates the ready manifest and all selected canonical runs,
  requires exactly five C0 runs and 45 baseline runs, and retains all seeds.
- Request/function intersections are reported explicitly and cannot replace
  the full cohort.
- Output paths must be absent; existing products are not overwritten.

## Verification

- Python compilation and Black formatting: pass.
- New directed tests: 4/4 pass, covering simulator-boundary stages, early
  placement clamping, asymmetric common-completion sets, and expected-sign
  leave-one-seed-out gating.
- All G3/G4 analysis tests: 22/22 pass.
- Frozen G3-E0 protocol tests: 9/9 pass.
- `git diff --check`: pass before commit.

## Authorized invocation

Use the unchanged G3-E0 selection and canonical root. The output directory is
fixed as:

`runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/latency_diagnosis`.

The invocation may write only the frozen JSON report and four CSV tables. It
does not complete the required source inventory. After analysis, stop for
trace-result audit and source-symbol comparison.
