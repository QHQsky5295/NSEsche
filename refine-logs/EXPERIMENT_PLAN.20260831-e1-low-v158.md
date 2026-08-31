# Experiment Plan: E1 Homogeneous-20 Low Short-Work Pipeline Diagnostic V158

**Current paper section:** E1 homogeneous, 20 nodes, low load.
**State:** still open. V157 passed throughput but failed the preregistered QPR
mean and three-seed QPR-sum gates.

## Why one more bounded diagnostic is justified

V156 and V157 isolate a clean tradeoff. The unrestricted parents-scheduled
frontier raised complete-cohort QPR above OCS but lost one required throughput
pair. Restricting speculative placement to terminal functions restored
throughput (`1.4948`, `12/20` wins), but the complete QPR mean fell to
`0.0544338`, below OCS `0.0555772`.

Frozen DAG analysis provides a testable middle ground. The existing SRPT
remaining-work score is approximately `5.07` for E09's dominant chain, where
pipeline placement delivered the clearest gain, but `6.16` and `6.19` for the
dominant short chains in E18 and E20. V158 therefore freezes `5.5` before any
implementation or V158 result. This is disclosed adaptive training, not a
paper-wide universal constant.

## V158 single change

V158 retains every V157 player and additionally admits a nonterminal
parents-scheduled player only when its request's current remaining-work score
is at most `5.5`. Remaining work uses the exact V155 SRPT formula over
unfinished immutable DAG functions. It does not read the seed, load label,
tape, future arrivals or any performance result.

The threshold-8 Hiku2/OCS router, SRPT ordering, NSESche equations, common HPA,
tapes, metrics and offline-reference rules are unchanged.

## Fixed diagnostic and gate

- New work: three references and three NSESche runs, E09→E18→E20.
- Reuse: the other 17 V155 rows and all 180 frozen baseline rows.
- Before reveal: verify that all short-work nonterminal admissions are `<=5.5`,
  all corresponding rejections are `>5.5`, terminal pipeline players remain
  admitted, both queue routes occur, and no performance field was read.
- After reveal: apply the unchanged V157 complete-cohort gates: throughput mean
  `>1.4741`, sum `>4.042`, at least `12/20` and `2/3` wins; both QPR means
  `>0.055577160345697`, three-seed sum `>0.187264280342794`, at least `12/20`
  wins and finite `20/20` coverage.

A pass authorizes only a separately committed remaining-17 training block. A
failure retires V158 and preserves all three valid diagnostics. Neither branch
opens fresh confirmation yet.

Machine-readable plan:
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_short_work_terminal_pipeline_queue8_low_diagnostic_plan_v158.json`.
