# M1 Six-Cell Qualification Result Audit

Date: 2026-09-02 (Asia/Shanghai)

Status: complete nonformal qualification; gate failed; mechanism diagnosis
required

Paper eligibility: none (`formal_results_eligible=false`)

## Frozen execution identity

- Runtime Git commit: `080a3daebfdd76e5d4ba01337e4c726d7c759680`.
- Runtime binary SHA-256:
  `f37b3162588cc95303bdf2085f866c862706a1b2f2a9ee10ab60d7841a12a35f`.
- NSESche source SHA-256:
  `ce9dff7641afd253392b6ea560fec2a9d844a20c9306db57df37864705542f78`.
- Selected global candidate: `ready_order`.
- Candidate-selection file SHA-256:
  `40691397fa8764e133fad04f2922865c3a003f220147a44839f182e8b03625bf`.
- Bound qualification manifest SHA-256:
  `3591a322c66a60e924e36fcfd52a65d497ca3fadaba11f65534a53041695a868`.
- Canonical root:
  `runs/tscv1_m1_qual_080a3da_20260902/ledger-qc-v2/canonical`.

The candidate screen retained all 90 preregistered runs.  Its global maximin
rule selected `ready_order`; no load-specific candidate was selected.

## Recovery and completeness audit

The first qualification workspace contained 1,077 valid canonical artifacts
and three baseline attempts rejected only because binary floating-point
roundoff represented a mean utilization as
`0.20000000000000004 > 0.2`.  The QC invariant was corrected to accept only
machine-close equality while still rejecting a real mean-over-peak violation.
The original quarantine and attempt history were not rewritten.

A clean `ledger-qc-v2` workspace then performed an exact-manifest,
result-blind import.  Import validation used the run specification, manifest,
audit path, file hashes, and QC status; it did not read performance summaries
or choose artifacts by outcome.  It admitted all 1,077 matching qualification
artifacts and rejected 30 valid screen artifacts because they belonged to a
different manifest.  The remaining three baselines and all 120 selected
NSESche runs executed once and passed QC on attempt 1.

- Canonical runs: 1,200/1,200.
- Imported verified runs: 1,077.
- Newly executed attempts: 123; canonicalized: 123; quarantined: 0.
- Paired groups: 120; pairing failures: 0.
- Ledger events: 2,402; final hash:
  `c3038bc031ba3b9216d9978662291f2df858eef45830b86490d0067f2fa540cf`.
- Pairing report SHA-256:
  `e14a3fe85096be7bc1684521e3977a963175b03137a50caa75a1816e95427b30`.
- Qualification report file SHA-256:
  `ff9ef94f0463b8136dfdc083fc5a2f010c6314151f41ac62176796e6b71daf9d`.
- Qualification report internal document hash:
  `ff3b217d1334a40e1f581764ac98ac7e10fecf3362173d3d7be3ecc74bc757ab`.

Post-recovery verification passed:

- Protocol suite: 151 tests passed.
- Analysis suite: 45 tests passed.
- Python bytecode compilation: passed.
- Rust formatting check: passed.
- Git whitespace check: passed (only the expected Windows LF-to-CRLF
  notices).
- Ledger-chain verification: passed.

## Qualification result

The frozen gate requires NSESche to have a strictly higher 20-run sample mean
for both throughput and applicable QPR than every baseline in every cell, with
complete QPR coverage.  It passed neither the overall gate nor any cell's
joint gate.

| Topology | Load | NSESche throughput | Best baseline throughput | Margin | NSESche QPR (n) | Best baseline QPR | Cell result |
|---|---|---:|---:|---:|---:|---:|---|
| homogeneous | low | 1.43605 | Greedy 1.49705 | -0.06100 | 0.048471 (20) | FaaSRank 0.060196 | fail T/QPR |
| homogeneous | middle | 0.79025 | FaaSRank 0.85100 | -0.06075 | 0.015150 (20) | 0.014994 | fail T; QPR first |
| homogeneous | high | 0.44975 | Orion 0.71625 | -0.26650 | 0.003506 (18) | OCS 0.006168 | fail T/QPR/coverage |
| heterogeneous | low | 1.23395 | OCS 1.36685 | -0.13290 | 0.041335 (20) | Hiku 0.051337 | fail T/QPR |
| heterogeneous | middle | 0.55430 | Orion 0.55905 | -0.00475 | 0.009758 (20) | 0.009041 | fail T; QPR first |
| heterogeneous | high | 0.31785 | Orion 0.47545 | -0.15760 | 0.002798 (18) | OCS 0.005319 | fail T/QPR/coverage |

The complete result is retained.  No valid seed was deleted, replaced,
relabeled, or selectively rerun, and the failed development result is not
eligible for a paper figure.

## First-principles mechanism diagnosis

The failure is not explained by lack of Nash convergence or an unavailable
offline social reference:

- Across the six cells, solver-window outer stability is approximately
  96.5%--98.3%; outer-limit hits are approximately 0.05%--0.16%.
- Offline-required lookup had no missing, zero, negative, or unavailable
  reference in the inspected qualification logs.  Reference values below the
  current result were explicitly retained as search-suboptimal observations.
- High-load windows nevertheless accumulate thousands of runnable and
  starting-resident tasks while mean CPU utilization remains far below one in
  many runs, a cold-start/placement-flow signature rather than a solver-limit
  signature.
- The paper utility varies continuously with price, pressure, externality,
  utilization, and heterogeneity.  Consequently, the warm/starting/finish
  refinement is reached only on utility ties.  In the qualification logs the
  near-tie share ranges from about 0.0003% in heterogeneous high load to 3.9%
  in homogeneous low load; in the most problematic cells it is operationally
  negligible.

Thus the three allowed candidates do not span the mechanism needed to close
the result.  `ready_order` changes player order, while `ready_finish_tie`
cannot reliably prefer an already executable warm path when a different node
has even a small formula-utility advantage.  The formula-consistent binary
therefore behaves primarily as a pressure/price load balancer, whereas the
leading baselines explicitly exploit warm affinity, headroom, locality, or
completion-oriented ordering.

Historical V202 is useful only as diagnosis.  On its separate revealed
E1610--E1629 training cohort it obtained throughput 1.46195 and QPR 0.066387,
but it still failed its Orion throughput gate (1.47410).  More importantly,
it used SRPT/critical-path order, a physical-warm/Pareto admissibility filter,
terminal/nonterminal completion ordering, direct initialization, and a large
operational indifference band.  Those operations can explain its better
completion behavior, but they are not equal-utility tie-breaks and cannot be
silently transplanted into the currently frozen formula-consistent method.

## Disposition

1. Keep all screen and qualification evidence immutable; do not promote it to
   formal data.
2. Do not start M2 while M1 is failed.
3. Add decision-neutral observability that records, for every selected
   placement, the selected container state and the best warm alternative's
   utility delta.  Run this only as a fixed-seed diagnostic, not a fourth
   qualification candidate.
4. Use that diagnostic to distinguish an implementation defect from an
   intrinsic objective conflict.  A defect may be corrected without changing
   the paper equations.  If the conflict is intrinsic, any new operational
   mechanism family must be explicitly preregistered and justified as
   paper-compatible before a fresh development bank is opened.
5. Preserve the published equations, QPR definition, common HPA/runtime, and
   the rule that all valid observations are retained.
