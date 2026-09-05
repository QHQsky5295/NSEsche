# P5 online queue-semantics QC correction preregistration

Date: 2026-09-05 (Asia/Shanghai)

Parent selection audit commit: `66ece7a417fb1249e29eea8b7d40355f233e1630`

Status: `technical_qc_correction_preregistered_online_execution_blocked`

## 1. Trigger and retained evidence

The first selected row,
`TSCv1.E1.homogeneous.n20.low.greedy.FP5P01.1ce7b703`, completed the simulator
twice but was quarantined twice with the same sole QC issue:
`queue_semantics_mismatch`. The generic QC branch requires
`unbounded_wait_by_design`; the frozen reviewer-v4 simulator correctly emits
`external_fcfs_bounded_active_dag_plus_node_task_queue`, matching the P5
external FCFS waiting queue and 100-request active-cohort contract.

Both attempts and all ledger events remain immutable under the original P5
online workspace. No canonical result exists. The repeated attempt was caused
by the checker classifying this contract mismatch as a technical failure; it
does not authorize result selection or replacement.

## 2. Frozen correction

Change only `scripts/reviewer_experiments/protocol/qc.py` and its directed
tests so queue semantics are checked against the run contract:

- P5 reviewer-v4 dynamic-admission runs must declare
  `external_fcfs_bounded_active_dag_plus_node_task_queue`;
- all existing non-P5 runs must continue to require
  `unbounded_wait_by_design`;
- drops, rejections, and timeouts must remain zero in both branches; and
- a P5 result using the legacy queue-semantics label must fail closed.

The existing P5 manifest already declares
`scientific_zero_or_low_completion_is_qc_valid=true`; that rule is unchanged.
The correction must not add any completion, throughput, QPR, rank, or old-PDF
criterion to per-run QC.

## 3. Prohibited changes

Do not change the ready manifest, online selection, runtime binary, workload
tapes, offline references, FaaSRank model, seed bank, method order, algorithms,
paper equations, admission policy, active limit, arrival horizon, observation
horizon, or drain deadline. Do not inspect relative method performance or use
the quarantined metric values to choose the correction.

## 4. Validation and restart boundary

Before online execution resumes:

1. add directed tests for both semantic branches and fail-closed mismatches;
2. pass the complete protocol and analysis suites;
3. re-evaluate both retained quarantined summaries and require that the former
   sole issue disappears without modifying either artifact; and
4. commit a correction audit with source/test hashes and retained-attempt
   identities.

Only after that audit commit may the exact same first selected run consume its
remaining attempt 3. If it becomes the first QC-valid result, it is canonical;
otherwise P5 remains blocked. The remaining 89 rows stay unauthorized until
that canonical integration check succeeds.
