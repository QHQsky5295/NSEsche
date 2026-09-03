# G1 corrected-runtime strict-Eq.15 preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: authorized and protocol-frozen before D61--D65 capture; no G1 tape,
reference, or candidate result existed when this document was written

## 1. Paper claim and boundary

This non-formal block decides which existing equation-consistent NSESche
operational interpretation may enter the independent six-cell qualification.
It does not change paper Eqs. (1)--(20), utility, Eq. (19)/(20), QPR, common
HPA, workload profiles, or the cold-start correction. Its result cannot be
plotted as a formal paper result.

The G0 correction at commit `16c32c2` reserves memory for cold-start
transitions before admitting runnable task memory. Commits `cafb7c5` and
`6e5643e` expose and validate the actual Eq. (16)/(19)/(20) control path. The
runtime frozen after this preregistration must contain all three changes.

## 2. Authorization and historical-data exclusion

The user-authorized goal file is:

`C:\Users\99349\.codex\attachments\3d926a20-44a2-4b72-aa24-5a3d1e120f99\goal-objective.md`

The authorization permits the corrected-runtime technical replay and the
90-run D61--D65 screen. D01--D60 observations remain historical diagnostics.
Their tapes may be used only for a named technical check; their references,
performance rows, and seeds cannot select the G1 candidate.

## 3. D44 technical gate

- Source: the already captured D44 homogeneous/high `ready_order` tape.
- Frozen tape SHA-256:
  `70c4151f0ce12b1476554f1be051878499283bdf60da5a483ac99604eaab07aa`.
- Role: one technical-only run, not selection-eligible and not formal.
- Reference: rebuilt from the same final runtime and exact run state; the old
  D44 reference is forbidden.
- Admission requires canonical QC, exact build/replay state-pair and final
  assignment pairing, equal build/replay completion counters, the frozen
  runtime Git/binary identity, `strict_eq15_ready=true`,
  `stream_contract_ready=true`, at least one validated feedback-trace round,
  and zero analyzer-invalid feedback rows.
- D61 capture is forbidden until a hash-sealed
  `NSE_G1_CORRECTED_RUNTIME_TECHNICAL_GATE_V1` receipt exists.

## 4. Fresh D61--D65 screen

- Seeds: exactly `D61`, `D62`, `D63`, `D64`, `D65`.
- Topologies: homogeneous and heterogeneous, 20 nodes each.
- Loads: low, middle, and high frozen submission-era workload profiles.
- Candidates, in simplicity order:
  1. C0 `ready_order`;
  2. C1 `ready_finish_tie`;
  3. C2 `formula`.
- Matrix: `3 candidates x 2 topologies x 3 loads x 5 seeds = 90 runs`.
- Tape count: 30; all candidates in a `(topology, load, seed)` group replay
  the same byte-identical tape.
- Reference count: 90 state-matched offline tables, one dependency per
  candidate/cell/seed trajectory.
- Every candidate must declare `strict_best_response=true` and
  `utility_guard_relative_regret=0.0` in the manifest, and the real stream
  must pass the Eq. (14)/(16)/(19)/(20) canonical gate.

## 5. Frozen selection rule

For every candidate and each of the six `(load, topology)` cells, compute the
five-seed mean throughput and run-level QPR. For each of the twelve
cell/metric combinations, divide the candidate mean by the C0 `ready_order`
mean.

Rank candidates lexicographically by:

1. largest minimum of the twelve candidate/C0 ratios;
2. largest mean of the twelve ratios;
3. largest number of cells in which the candidate is jointly first in mean
   throughput and mean QPR;
4. C0--C1--C2 simplicity order.

All 90 QC-valid observations are retained. A nonpositive or nonfinite
throughput, latency, cost/completion, or derived QPR makes the family
unrankable and fails closed. Statistical disadvantage is not a technical
failure and never authorizes seed removal or replacement. Only one immutable
selection receipt may be written.

## 6. Post-selection diagnostics and stop/go rule

The receipt retains each seed-level throughput, QPR, latency,
cost/completion, completion ratio, queue peak/area, inner/outer limit rates,
nonconvergence rate, feedback round counts, QC hash, summary hash, and audit
hash. These fields are inspected for seed-level collapse, queue pathologies,
and convergence problems before any independent qualification protocol is
opened.

Completing this screen does not itself make an experiment chapter
`paper_ready_closed`. The selected candidate still requires an independently
preregistered Q61--Q80 ten-method, six-cell qualification. M2 and M3 remain
forbidden until that qualification passes the frozen dual-first gate.
