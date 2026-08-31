# Experiment Plan: E1 Homogeneous-20 Low-Load Pipeline Diagnostic V156

**Current paper section**: E1 homogeneous, 20 nodes, low load.  
**Status before execution**: not closed. V155 is first in throughput but its
QPR mean is 3.34% below OCS.  
**Question**: Does parent-scheduled pipeline-ahead placement remove the three
dominant QPR tail losses without sacrificing the V155 throughput lead?  
**Date**: 2026-08-31

## Claim boundary

V156 is an adaptive, outcome-informed training diagnostic. It cannot become a
paper row, cannot open the fresh confirmation group, and cannot authorize any
middle/high or later-section run. Its only possible success is permission to
run the remaining seventeen low-load training seeds under a separately
committed plan.

All frozen non-NSESche baselines are reused. No baseline is rerun. All three
valid V156 diagnostic outcomes are retained regardless of performance.

## First-principles mechanism

V155 already establishes that queue-8 routing is useful: relative to V150 it
improves throughput, latency, cost, queue area, and QPR. The remaining QPR loss
is concentrated in E09, E18, and E20 and is driven primarily by latency. The
causal difference still separating V155 from native OCS is the dependency
frontier:

- V155 schedules a child only after every parent completes (`PreAllDone`).
- Native OCS may place a child after every parent has an assigned node
  (`PreAllSched`), allowing one-layer-ahead container preparation.

V156 changes only this frontier. It keeps threshold 8, the two exact V155
scoring branches, SRPT ordering, NSESche equations, feasibility, common HPA,
tapes, reference construction, and metrics unchanged. Earlier pipeline trials
sometimes increased congestion, so this is deliberately a three-seed
falsification test rather than a full speculative run.

## Fixed diagnostic block

| Item | Frozen value |
|---|---|
| Seeds and order | E09, E18, E20 |
| New work | 3 state-matched references + 3 NSESche online runs |
| Reused candidate rows | V155 E01-E08, E10-E17, E19 (17 rows) |
| Reused baselines | all 180 frozen non-NSESche E01-E20 rows |
| Candidate profile | `srpt_pipeline_hiku2_ocs_queue8` |
| Scientific change | parent-completed → parent-scheduled frontier only |
| Selection disclosure | three largest sealed V155 QPR deficits vs OCS |

The three seeds are not a publication sample. They are a diagnostic challenge
set chosen after V155 reveal. If the candidate advances, the final training
decision must use the complete E01-E20 cohort, with these three rows reused and
the remaining seventeen added exactly once.

## Result-blind gate

Before any throughput, latency, cost, completion, or QPR field is read, the
audit must prove:

- exact E09/E18/E20 coverage and order, one unanimous runtime identity, valid
  ledger/QC/archive inventory, and exact reference build/replay pairing;
- every selected player satisfies parents-scheduled eligibility, no player
  with an unassigned parent enters the cohort, and at least one pipeline-ahead
  player has scheduled-but-incomplete parents;
- the queue-8 route is exact in every window, both branches are exercised, and
  no outcome metric drives routing;
- zero placement rejection, reference mismatch, unexplained quarantine, or
  non-finite primary metric.

## Frozen reveal rule

Replace the three V155 rows by V156 E09/E18/E20 and recompute the unchanged
twenty-seed training gates.

- Throughput: hybrid mean > Orion `1.47410` req/ms; equivalently, the three
  V156 throughputs sum to > `4.042`; hybrid paired wins ≥ 12/20, so at least
  2/3 diagnostic seeds must beat Orion.
- QPR: both conventions' hybrid means > OCS `0.055577160345697`;
  with the current all-finite cohort, the three V156 QPR values sum to
  > `0.187264280342794`; hybrid paired wins ≥ 12/20; finite coverage 20/20.
- Mechanism: the result-blind audit passes unchanged.

Every gate must pass. A failure retires V156 immediately and avoids the other
seventeen runs. A pass authorizes only a new, separately committed plan for the
remaining seventeen low-load training seeds. Fresh E1530-E1549 confirmation
remains unopened until a complete E01-E20 V156 training block passes.

## Paper-section order

1. Low-load V156 diagnostic (current).
2. If diagnostic passes, complete low-load E01-E20 training without rerunning
   the three diagnostic rows.
3. If complete training passes, preregister and run fresh three-method low-load
   confirmation.
4. Freeze the low-load publication row and figure only after confirmation.
5. Only then revisit the already retained middle/high state and later sections.

## Data and storage

- Output root:
  `tmp/nse_e1_homogeneous_pipeline_queue8_low_diagnostic_20260831_v156`.
- Frozen V155/V149/baseline roots are read-only.
- Shared `serverless_sim/records` stays empty.
- Verbose logs are compressed after verification; no valid diagnostic row is
  deleted because of performance.

The full machine-readable contract is
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_pipeline_queue8_low_diagnostic_plan_v156.json`.
