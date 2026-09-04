# P2 Low-Load Hyperparameter Recovery Screen Preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `preregistered_implementation_only_sampling_blocked`

## 1. Purpose

Test whether exactly one of the four axial neighbours already specified by the
paper's E7 sensitivity design provides a sufficiently large and robust
low-load improvement over the submitted centre. This is a development-only
screen. It does not alter the scheduling mechanism or any displayed formula,
and it cannot be used in a paper figure or baseline comparison.

The screen is motivated by the complete pre-existing Q61--Q80 formal result:
the centre is about 1.04% below the throughput leader and 9.26% below the QPR
leader. The screen's viability margins are frozen before any D121--D125 tape,
reference, or outcome is generated.

## 2. Immutable population

- topology: homogeneous;
- nodes: 20;
- load: low only;
- simulator method: NSESche only;
- scheduler mechanism: `ready_order`;
- binary: the already frozen G18 release binary, SHA-256
  `aaa0980cf451a88f7b3652f55c3e8c624af2a71b6312c40f4b19aa83bf6af713`,
  source commit `f3a1e0950c5a53a0ab614edacc2838703c2a9d81`;
- fixed seeds: D121, D122, D123, D124, D125;
- shared workload tapes: one per seed, reused across all five settings;
- settings, in fixed manifest order:
  1. `centre`: `r0=0.60`, `wq=0.50`;
  2. `r0_minus`: `r0=0.55`, `wq=0.50`;
  3. `r0_plus`: `r0=0.65`, `wq=0.50`;
  4. `wq_minus`: `r0=0.60`, `wq=0.40`;
  5. `wq_plus`: `r0=0.60`, `wq=0.60`.

The execution population is exactly 25 online runs: five settings by five
seeds. Offline social-utility references are parameter-specific, so exactly
25 reference builds are required. All five settings for D121 execute before
D122, and so on, preserving the declared seed-major/setting-minor order.

No result-conditioned seed extension, seed replacement, new setting, diagonal
point, refined step, baseline run, or post-outcome threshold change is
permitted. D121--D125 are exhausted when this screen completes.

## 3. Required result-free implementation and input audits

Before tape capture:

1. implement a dedicated protocol builder and fail-closed validator that admit
   only the exact 25-run population above;
2. implement a result-blind analyzer and directed tests;
3. bind source commit, binary hash/size, protocol hashes, config hashes, method
   identity, setting label, seed, tape hash, reference key/table hash, and
   manifest order;
4. prove the selected release binary still exposes `ready_order`, uses the
   declared `r0`/`wq`, and passes the existing runtime-contract tests; and
5. freeze a zero-result manifest whose reference fields are null and whose
   result directories do not exist.

Tape capture and each later stage require a separate audit. The analyzer and
selection list must be frozen before any online result exists.

## 4. Run validity and retained metrics

A run is QC-valid only if generic protocol QC and the dedicated screen
validator pass, including exact tape/config/binary/reference identity, finite
required fields, positive completed count, defined QPR, and complete NSESche
runtime streams. A loaded offline reference must be finite, strictly positive,
and keyed to the exact parameter-specific state.

For every run retain at minimum:

- throughput (req/ms);
- run-level QPR under frozen Eq. (19);
- completion ratio;
- drained mean latency;
- simulator cost per completion;
- active/stable/limit/oscillation/reference-hit window counts; and
- placement-policy wall/thread CPU and integrity violations.

Every first QC-valid canonical run is retained. Performance direction is never
a technical retry reason.

## 5. Fixed paired comparisons

Each neighbour is paired with `centre` within the same D121--D125 tape. For
throughput and QPR report all five raw differences and ratios, arithmetic mean,
sample SD, descriptive 95% t interval, signs, joint wins/nonlosses, and every
leave-one-seed-out mean difference. Completion, latency, cost, and policy time
are reported for safety and interpretation, not used to reconstruct QPR.

Numerical comparison tolerances are fixed as:

- equality/nonloss: candidate value >= centre value within absolute
  `1e-12` only;
- finite checks reject NaN and infinity;
- no rounding is applied before a gate comparison.

## 6. All-pass neighbour gate

A neighbour is eligible only if all conditions pass:

1. **Population and identity:** exactly five valid neighbour runs and their
   five same-tape centre runs exist; the complete screen contains all 25
   declared runs and no extra run.
2. **Viable dual mean effect:** neighbour/centre arithmetic-mean throughput
   ratio is at least `1.015`, and QPR ratio is at least `1.11`.
3. **Paired robustness:** at least three of five seeds are strict joint wins
   in throughput and QPR, and at least four of five are joint nonlosses.
4. **Per-seed safety:** every seed's throughput ratio and QPR ratio is at
   least `0.80`.
5. **Leave-one-out stability:** all five leave-one-out mean differences are
   nonnegative for each primary metric, with at least four strictly positive
   leave-one-out means for each metric.
6. **Completion and latency:** mean completion ratio is not below centre and
   mean drained-latency ratio is at most `1.05`.
7. **Runtime/reference integrity:** no structural/runtime-contract violation;
   every active strict-PNE window that requests a reference has an exact
   positive table hit; no oscillator; no unexplained missing terminal record.
8. **Overhead:** neighbour/centre mean placement-policy wall-time ratio is at
   most `1.50`.

Conditions are conjunctive. No condition may be waived because another metric
is strong.

## 7. Deterministic selection and stopping

If no neighbour passes all eight conditions, select none, retain the submitted
centre, close local low-load parameter recovery, and block the fresh formal
bank. The failed development evidence remains archived outside paper figures.

If one neighbour passes, select it. If several pass, rank only the passing set
by:

1. descending `min(mean_throughput_ratio, mean_QPR_ratio)`;
2. descending geometric mean of those two ratios; and
3. fixed label order `r0_minus`, `r0_plus`, `wq_minus`, `wq_plus`.

The selection rule is invoked exactly once on the frozen complete 25-run
product. A selected neighbour authorizes planning, but not automatic execution,
of a fresh Q81--Q100 all-ten-method formal low-load confirmation. Development
rows never replace or augment formal rows.

## 8. Current authorization

This preregistration authorizes only protocol/analyzer implementation,
directed tests, and a result-free source/binary/manifest audit. It does not yet
authorize D121--D125 tape capture, offline-reference construction, online
execution, formal confirmation, E7 figures, manuscript claims, or any baseline
run.

