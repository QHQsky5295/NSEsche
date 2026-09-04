# G17 Threshold-Safety Diagnosis Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Parent closure commit: `c604515eb41e9a1ebdd3257c4eb2be176c86f8db`

Status: `preregistered_read_only_no_implementation_or_sampling_authorized`

## 1. Question and boundary

G16 is closed negative development evidence. Its exact `4F>=5N` valve passes
the activation and overhead contracts and produces seed-robust high-load
gains, but it loses middle throughput/QPR and lacks low/middle paired
robustness. G17 asks one narrower question before any further scheduler edit:

> Do the already logged first-overflow magnitude distribution and accumulated
> deferral dose identify a stricter, load-blind and pre-decision safety rule
> that could retain useful G16 activations while reverting unsafe runs toward
> C0 strongly enough to justify one fresh successor preregistration?

G17 is exploratory, read-only mechanism training. It uses exactly the
retained 15 G16 candidate runs and their 15 same-load/same-seed C0 controls
from D111--D115. It creates no tape, reference, simulator run, seed extension,
baseline comparison, confirmation, figure, or paper claim. Every tie, loss,
negative reference, inner-limit observation, and favorable result remains
visible.

## 2. Fixed inputs

The analyzer must bind and revalidate:

- the complete G16 run root: 1,092 files, 395,532,897 bytes, sorted inventory
  hash `28a7d5a16592e928e4c63d11901f76629c75d8a5041d69955baec12e36f04c9f`;
- `g16.references.json` file/document hashes
  `bdda8e7b...eb65` / `fbea597e...b50e`;
- the frozen online selection file/document hashes
  `0c9eb944...bdd4` / `94fc4f53...1458`;
- the frozen gate report file/document hashes
  `7fdf5456...00e3` / `c1856ac8...ea37`;
- the 62-event online ledger file SHA-256 `9e36a4f1...4f2a`, ending at
  `5ef27a3a...57fa`;
- the frozen G16 analyzer source SHA-256 `0c372111...f8e4`; and
- every canonical manifest/QC artifact and same-tape candidate/control pair.

The root hash is checked before any output is written. The G16 analyzer,
selection, report, source, and D111--D115 population remain immutable.

## 3. Frozen run-level features

For every G16 candidate run, scheduler windows remain in recorded frame
order. An overflow episode is a maximal consecutive sequence with
`feasible_ready>N`. Its first window must be either
`first_overflow_below_magnitude_release` or
`first_overflow_magnitude_bounded`; subsequent windows, if any, must be
`persistent_overflow_release`.

The analyzer reports without filtering:

- counts of all five G16 modes, overflow episodes, persistent episodes,
  episode lengths, reset intervals, and material bounded-event intervals;
- complete first-overflow `F/N` values plus mean, median, p75, p90, p95, and
  maximum;
- for each fixed threshold in `{1.25, 1.5, 2.0, 4.0}`, first-overflow counts,
  fractions, and deferred-player mass that meet the exact widened-integer
  comparison;
- actual bounded-window count, deferred-player total, bounded-window density
  per active window, deferred-player mass per assigned player, and the same
  features by load;
- feasible-ready, admitted, pending-queue, resident-queue, and total-queue
  summaries for all, first-overflow, and material-bounded windows;
- all nine G16 telemetry violation totals, runtime identity, strict-PNE and
  offline-reference coverage, including all five retained runtime
  exceptions; and
- paired throughput, QPR, latency, cost, and completion effects from the
  frozen report.

The independent unit is the run/seed (`n=15`), never an individual window.
The fixed safety label is `joint_nonloss = throughput_ratio>=1 and
qpr_ratio>=1`; the stricter `joint_win` label remains `>1` in both metrics.
Exact ties are retained and explicitly distinguished.

## 4. Fixed threshold-safety screens

For each threshold `h` in `{1.25, 1.5, 2.0, 4.0}`, a run is predicted safe
only when it has at least one first-overflow window and at least half of its
first-overflow windows satisfy `F/N >= h`. The report retains the complete
joint-nonloss and joint-win confusion matrices, sensitivity, specificity,
balanced accuracy, group sizes and loads, mean log throughput/QPR ratios,
and every leave-one-run-out recomputation.

For each threshold, a deliberately optimistic screening envelope is also
reported: predicted-safe runs retain their observed G16 metric, while
predicted-unsafe runs are replaced by their paired C0 metric. From these 15
fixed rows the analyzer computes, at every load, arithmetic-mean throughput
and QPR ratios versus C0, paired wins/nonlosses, 0.80 floors, and every
leave-one-seed-out mean difference. This envelope is diagnostic only: it is
not a causal estimate because changing a window changes downstream state.

Threshold selection maximizes, in order: the minimum of the six per-load
screening-envelope throughput/QPR ratios; joint-nonloss balanced accuracy;
the minimum of sensitivity and specificity; and then prefers the larger
threshold. All four threshold reports remain visible.

## 5. Fixed dose and association analyses

The report includes Spearman associations, with average ranks, between all
fixed magnitude/episode/queue/dose features and log throughput ratio, log QPR
ratio, negative log latency ratio, negative log cost ratio, and completion
difference. Overall, per-load, activated-run-only, and all leave-one-run-out
values are reported; undefined coefficients remain undefined.

Actual bounded-event budgets `{1, 4, 16, 64}` are evaluated descriptively by
reporting, for each run, how many observed bounded events and deferred players
would be retained by an online first-events-only budget. This is a trace
coverage calculation, not a performance counterfactual, and cannot by itself
authorize a successor.

## 6. Frozen successor-admissibility rule

One stricter-threshold successor concept may be eligible for a separate
preregistration only if every condition below passes:

1. all 15 G16/C0 pairs validate; every candidate row passes G16 activation
   and runtime identity; and all nine telemetry violation totals are zero;
2. the selected fixed threshold is strictly above 1.25 and has
   joint-nonloss balanced accuracy at least 0.70, sensitivity at least 0.60,
   specificity at least 0.60, at least three predicted-safe and three
   predicted-unsafe runs, with both groups spanning at least two loads;
3. predicted-safe minus predicted-unsafe mean log-throughput and mean log-QPR
   ratios are both positive;
4. the optimistic screening envelope has throughput and QPR arithmetic-mean
   ratios strictly above 1 at all three loads, at least one joint win and four
   joint nonlosses per load, and every per-seed primary ratio at least 0.80;
5. every screening-envelope leave-one-seed-out primary mean difference is
   nonnegative and at least four of five are strictly positive at every load;
   and
6. after leaving out any one run, the selected threshold's joint-nonloss
   balanced accuracy remains at least 0.65, sensitivity and specificity each
   remain at least 0.50, and both safe-minus-unsafe mean-log-primary contrasts
   remain positive.

Passing authorizes only a new preregistration for the exact selected current-
window magnitude threshold with the unchanged G16 one-bit release recurrence.
The runtime rule may inspect only current pre-decision `F`, fixed `N`, and the
previous-overflow bit. It may not inspect workload profile, load label, seed,
realized outcome, baseline method, future arrivals, or the run-level
diagnostic classifier. Eqs. (1)--(20), strict Eq. (15), Eq. (19), QPR, and
offline-reference definitions remain unchanged on the admitted set.

If any condition fails, the fixed-threshold valve family closes. Dose and
association results may explain failure but cannot authorize a cooldown,
budget, or another mechanism without a separate preregistration.

## 7. Integrity and stopping rule

- D111--D115 are diagnosis-only and cannot validate a successor.
- All retained runtime exceptions are reported and never omitted or retried.
- No feature, threshold, condition, tie-break, or successor definition may be
  edited after the first real analyzer invocation.
- G17 stops after one validated report. There is no result-conditioned retry.
- Strong baselines, fresh seeds, confirmation, formal replay, figures, and
  paper claims remain blocked throughout G17.

At this checkpoint:

- `g17_read_only_diagnosis_authorized=true`;
- `g17_implementation_authorized=false`;
- `g17_input_construction_authorized=false`;
- `g17_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`; and
- `formal_progression_authorized=false`.
