# G3 post-failure diagnosis implementation audit

Date: 2026-09-04

## Decision

The read-only analyzer implementing
`G3_POSTFAIL_CLAIM_SCENE_DIAGNOSIS_PREREGISTRATION.md` is frozen at commit
`83c2a96`. Exactly one invocation against the unchanged canonical D71--D75
product is authorized. No simulator run, candidate implementation, seed
extension, formal experiment, or plot is authorized.

## Frozen implementation

- Analyzer:
  `scripts/reviewer_experiments/analysis/g3_postfail_diagnosis.py`.
- Analyzer SHA-256:
  `2a19a8a2bf87bec92d3f56a0a9c269f407b18acc8aedf2df50e631fd8b911f1d`.
- Directed tests:
  `scripts/reviewer_experiments/analysis/tests/test_g3_postfail_diagnosis.py`.
- Test SHA-256:
  `0b2e07fdfb3dc46be41d84b00eca8aebf62c8667e8311f0e8ef302637f7b3789`.
- Required selection file/document SHA-256 values are hard-coded as
  `22e5cf35...f3f7` and `4cb006a3...6a34`; unexpected products fail closed.
- The analyzer revalidates the ready manifest and all canonical run/QC/summary
  receipts before forming any result.
- The independent unit is one run/seed. Frames and scheduler windows are
  reduced within run and are never treated as independent repetitions.
- All output paths must be absent. The writer refuses to overwrite an existing
  diagnostic product and removes partial outputs if a CSV write fails.

## Verification

- Python compilation: pass.
- Black format check: pass.
- New directed tests: 4/4 pass. They cover the exact log-QPR identity, complete
  sign retention, run-level Spearman/leave-one-seed-out behavior, and inclusion
  of undefined tests in the Holm family.
- All G3 analysis tests: 17/17 pass.
- Frozen G3-E0 protocol tests: 9/9 pass.
- `git diff --check`: pass before the implementation commit.

## Authorized invocation

The only authorized command is the frozen analyzer with:

- selection:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json`;
- canonical root:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/online/canonical`;
- output directory:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/diagnosis`.

The invocation may read all 135 validated runs and write only the six
preregistered diagnostic artifacts. After it terminates, stop for result and
integrity audit. A positive statistical pattern does not itself authorize any
new experiment.
