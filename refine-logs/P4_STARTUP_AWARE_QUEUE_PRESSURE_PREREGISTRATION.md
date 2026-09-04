# P4 Startup-Aware Queue-Pressure Preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `preregistered_implementation_only_sampling_blocked`

## 1. Purpose and claim boundary

Test one formula-compatible NSESche candidate that counts requests resident in
starting containers in Eq. (6)'s queue observation. The candidate must improve
both homogeneous-low throughput and QPR enough to cover the retained formal
shortfalls before any strong-baseline confirmation is considered.

P4 is a development screen, not a paper figure or final estimate. It does not
change displayed Eqs. (1)--(20), relax strict Eq. (15), alter the common HPA,
or authorize a performance claim.

## 2. Exact candidate and control

Both settings use homogeneous 20-node low load, NSESche `ready_order`, paper
low-load parameters `r0=0.60` and `wq=0.50`, window-max queue normalization,
and every other frozen TSCv1 setting.

1. `execution_ready` control:
   `q_n = pending + runnable`.
2. `startup_aware` candidate:
   `q_n = pending + runnable + starting_resident`.

For each mode, `q_max(t)=max(1,max_n q_n(t))`. Parent-blocked and data-blocked
resident tasks are excluded in both modes. There is no coefficient to tune,
no alternate candidate, and no fallback to a previously rejected family.

## 3. Immutable population

- fixed fresh seeds: D126, D127, D128, D129, D130;
- five base workload tapes, one per seed;
- the same tape is reused by control and candidate within a seed;
- exact online population: `5 seeds x 2 settings = 10` runs;
- exact offline-reference population: ten mode-specific builds;
- fixed order: seed-major, then `execution_ready`, then `startup_aware`;
- all first QC-valid canonical observations are retained; and
- a technical retry is allowed only for the same seed, setting, config, tape,
  source, and binary when a documented non-performance QC failure occurs.

D126--D130 have not been sampled. Their conditional mention in P3 did not
generate a tape or result and does not bind them to the rejected Eq. (9)
direction. Once P4 sampling begins, no seed extension, replacement, omission,
or result-conditioned rerun is permitted.

## 4. Required zero-result stages

Before any tape capture:

1. implement an explicit two-value queue-semantics setting with
   `execution_ready` as the unchanged default;
2. include the semantics in run configuration, observability, reference state
   identity, and all relevant receipts;
3. add directed Rust and Python tests proving category inclusion/exclusion,
   bounded normalization, strict Eq. (15), and default-control compatibility;
4. compile into a new P4 build directory and freeze source commit, binary
   size/hash, configuration schema, protocol builder, validator, and analyzer;
5. create a result-free manifest with null tape/reference/result bindings and
   prove no P4 result directory exists; and
6. commit a separate implementation/protocol audit.

Each later stage requires its own committed audit: tape/input binding, offline
reference binding, result-blind online selection, and final result closure.

## 5. Run validity and retained metrics

A run is valid only if generic QC and the dedicated P4 validator pass exact
source/binary/config/seed/tape/reference identity. Required values include
finite throughput, completion, latency, cost and placement-policy overhead;
positive completed count; defined frozen run-level QPR; complete 1,000-window
NSESche streams; strict Eq. (15); and exact positive reference hits whenever
an active stable window requests a reference.

Retain all five paired raw differences and ratios for throughput and QPR,
arithmetic means, sample SD, descriptive 95% t intervals, signs, joint
wins/nonlosses, and all five leave-one-seed-out mean differences. Also retain
completion ratio, drained latency, simulator cost per completion, inner/outer
convergence states, oscillations, reference coverage, and placement-policy
wall/thread CPU.

Mechanism observability must retain per window:

- execution-ready queue total/max;
- starting-resident queue total/max;
- active queue semantics and actual pressure count total/max;
- normalizer and maximum normalized ratio;
- assignment hash and assigned-player count; and
- queue-category partition invariants.

The comparison tolerance is absolute `1e-12`; no rounding precedes a gate.

## 6. Ten-condition all-pass gate

The candidate is eligible only if every condition passes:

1. **Population and identity:** exactly ten declared valid runs, five shared
   within-seed tapes, ten distinct matching references, and no extra run.
2. **Formula/method boundary:** only the declared `q_n` operational slice
   differs; the control reproduces the previous default semantics; displayed
   Eqs. (1)--(20), strict Eq. (15), candidates, order, and HPA are unchanged.
3. **Mechanism activation:** in at least four seeds, at least 10% of active
   candidate windows have positive starting-resident backlog; in at least four
   seeds, candidate and control differ in final assignment hash in at least
   one aligned active window; all queue invariants pass.
4. **Viable dual mean effect:** candidate/control arithmetic-mean throughput
   ratio is at least `1.015` and QPR ratio is at least `1.11`.
5. **Paired robustness:** at least three of five seeds are strict joint wins
   in both primary metrics and at least four are joint nonlosses.
6. **Per-seed safety:** every seed's throughput and QPR ratios are at least
   `0.80`.
7. **Leave-one-out stability:** all five leave-one-out mean differences are
   nonnegative for each primary metric and at least four are strictly positive
   for each metric.
8. **Completion and latency:** mean completion ratio is not below control and
   mean drained-latency ratio is at most `1.05`.
9. **Runtime/reference integrity:** no runtime-contract violation, oscillator,
   unexplained terminal omission, reference-key collision, or missing/nonpositive
   required reference hit.
10. **Overhead:** candidate/control mean placement-policy wall-time ratio is at
    most `1.50`.

These are conjunctive gates. A large improvement in one metric cannot waive a
failure elsewhere.

## 7. Decision and stopping rule

If all ten conditions pass, `startup_aware` is the sole selected P4 candidate.
This authorizes only a new, separately preregistered homogeneous-low
baseline-compatibility bank and then a fresh formal confirmation bank if the
baseline gate passes. It does not allow P4 development rows into the paper.

If any condition fails, select none, retain `execution_ready`, close the
startup-aware queue-pressure family, and do not tune a startup coefficient,
try partial categories, change thresholds, add seeds, or substitute a warm
preference. The complete negative product remains archived.

## 8. Current authorization

After this preregistration is committed, only implementation, directed tests,
binary freeze, protocol/analyzer construction, and a result-free audit are
authorized. Tape capture, reference construction, online execution, strong
baselines, formal experiments, manuscript figures, and claims remain blocked.
