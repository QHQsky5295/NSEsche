# G15 Overflow-Magnitude Diagnosis Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Parent closure commit: `ae92665f0f71c0a84c0bb070fdb57c68fa566e48`

Status: `preregistered_read_only_no_implementation_or_sampling_authorized`

## 1. Question and boundary

G14 is closed negative development evidence. Its parameter-free one-bit valve
passes the exact state-machine and overhead contracts and improves both
primary means at low and high load, but fails middle-load throughput and the
low/middle paired-win requirements. G15 asks one narrower question before any
further scheduler change:

> Can the magnitude of the *current first-overflow state*, observed before the
> placement decision as `feasible_ready/N`, distinguish valve-favorable from
> valve-unfavorable runs robustly enough to justify one fresh validation of a
> load-blind magnitude-gated valve?

G15 is exploratory, read-only mechanism training. It uses exactly the retained
15 G14 candidate runs and their 15 same-load/same-seed C0 controls from
D106--D110. It creates no tape, reference, simulator run, seed extension,
baseline comparison, confirmation, figure, or paper claim. Every tie, loss,
runtime exception, and favorable result remains visible.

## 2. Fixed inputs

The analyzer must bind and revalidate:

- the complete G14 run root: 1,092 files, 396,182,667 bytes, sorted inventory
  hash `fdb9706343dd4871e49c75be0cd7a2f81f15e095b9ea7aacf65d4ba04de59b63`;
- `g14.references.json` file/document hashes
  `92eab217...dac26` / `6ac84333...25f1`;
- the frozen online selection file/document hashes
  `887fc413...68b4` / `3e750866...9169`;
- the frozen gate report file/document hashes
  `aa318b72...8ebc` / `737fec07...2ea0`;
- the 62-event online ledger file SHA-256 `57098080...2d44`, ending at
  `0fd4fe2d...cf5b`; and
- every canonical manifest/QC artifact and same-tape candidate/control pair.

The root hash is checked before any output is written. The G14 analyzer,
selection, gate report, and D106--D110 population remain immutable.

## 3. Frozen run-level features

For every G14 candidate run, scheduler windows remain in recorded frame order.
An overflow episode is a maximal consecutive sequence with
`feasible_ready>N`. Its first window must have
`admission_mode=first_overflow_bounded`; subsequent windows, if any, must have
`admission_mode=persistent_overflow_release`.

The analyzer reports without filtering:

- first-overflow, persistent-overflow, below-limit, and reset window counts;
- episode count, persistent-episode count/fraction, episode-length mean and
  maximum;
- for first-overflow windows, `feasible_ready/N` and `(feasible_ready-N)/N`
  mean, median, p90, p95, maximum, and complete ordered values;
- first-overflow fractions at or above each fixed ratio in
  `{1.25, 1.5, 2.0, 4.0}`;
- admitted, feasible-ready, deferred, pending-queue, resident-queue, and total-
  queue summaries for all and first-overflow windows;
- all eight G14 telemetry violation totals, runtime identity, strict-PNE and
  offline-reference coverage, including all five retained inner-limit
  exceptions; and
- paired throughput, QPR, latency, cost, and completion effects from the
  frozen report.

The independent unit is the run/seed (`n=15`), never an individual window.
The fixed outcome label is `joint_win = throughput_ratio>1 and qpr_ratio>1`;
exact ties are retained as nonwins.

## 4. Fixed classifiers and descriptive analyses

For each threshold `h` in `{1.25, 1.5, 2.0, 4.0}`, a run is predicted
valve-favorable only when it has at least one first-overflow window and at
least half of its first-overflow windows satisfy `feasible_ready/N >= h`.
The report retains the full confusion matrix, sensitivity, specificity,
balanced accuracy, predicted-positive/negative group sizes and loads, mean log
throughput/QPR ratios for both groups, and every leave-one-run-out
recomputation.

The diagnostic threshold is selected by maximum full-sample balanced accuracy,
then maximum minimum of sensitivity and specificity, then the smaller numeric
threshold. This is explicit development fitting, not validation. The report
also includes Spearman associations, with average ranks, between all fixed
overflow/queue features and log throughput ratio, log QPR ratio, negative log
latency ratio, negative log cost ratio, completion difference, and persistent-
episode fraction. Overall, per-load, and all leave-one-run-out values are
reported; no favorable subset is selected.

## 5. Frozen successor-admissibility rule

A single successor concept, `overflow_magnitude_gated_release_valve`, may be
eligible for a separate preregistration only if every condition below passes:

1. all 15 G14/C0 pairs validate; every candidate row passes G14 activation and
   runtime identity; and all eight telemetry violation totals are zero;
2. the selected fixed threshold has balanced accuracy at least 0.70,
   sensitivity at least 0.60, specificity at least 0.60, at least three
   predicted-positive and three predicted-negative runs, and both groups span
   at least two loads;
3. predicted-positive minus predicted-negative mean log-throughput and mean
   log-QPR ratios are both positive;
4. after leaving out any one run, both mean-log-ratio contrast signs remain
   positive and the selected threshold's balanced accuracy remains at least
   0.65 with sensitivity and specificity each at least 0.50; and
5. across the 15 retained runs, first-overflow ratio p90 has positive Spearman
   association with both persistent-episode fraction and log-throughput ratio,
   and both signs remain positive after every run omission for which the
   coefficient is defined.

This rule does not claim causality. Passing would authorize only a separate
implementation preregistration. The only admissible runtime concept would
retain C0's complete feasible-ready order unless a *current first-overflow*
window meets the frozen dimensionless magnitude threshold; such a qualifying
window may admit the first `N` players once, while all subsequent adjacent
overflow windows release the full feasible-ready set exactly as G14. It may
not inspect workload profile, load label, seed, realized outcome, baseline
method, or future arrivals. Eqs. (1)--(20), strict Eq. (15), Eq. (19), QPR,
and offline-reference definitions remain unchanged on the admitted set.

If any condition fails, no magnitude-gated implementation or new seed bank is
authorized from this path.

## 6. Integrity and stopping rule

- D106--D110 are diagnosis-only and cannot validate a successor.
- The five strict-PNE/reference exceptions are retained and reported; they do
  not authorize omission or retry.
- No feature, threshold, condition, tie-break, or successor definition may be
  edited after the first real analyzer invocation.
- G15 stops after one validated report. There is no result-conditioned retry.
- Strong baselines, fresh seeds, confirmation, formal replay, figures, and
  paper claims remain blocked throughout G15.

At this checkpoint:

- `g15_read_only_diagnosis_authorized=true`;
- `g15_implementation_authorized=false`;
- `g15_input_construction_authorized=false`;
- `g15_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`; and
- `formal_progression_authorized=false`.
