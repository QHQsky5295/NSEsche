# G11 State-Regime Successor Diagnosis Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Base closure commit: `3751c73`

Status: `read_only_g10_diagnosis_only_no_g11_implementation_or_sampling`

## 1. Fixed evidence and purpose

This diagnosis uses only the complete closed G10 D96--D100 evidence. Its raw
run-root inventory is fixed at 1,527 files, 566,678,494 bytes, and hash
`aed84ef942171c77d6ed340b9f2cfabb062a0b57b09b8cf02111443499704ff9`.
The frozen G10 gate report SHA-256 is
`e0581b60b64382d886e219ab4b73d8f36c33f1dce5723c1f27da8607ae3a0870`.

The purpose is narrow: determine whether the bounded frontier's high-load gain
and low/middle harm are associated with one observable pre-decision state
regime that can motivate at most one globally defined successor. This is
mechanism training/diagnosis, not validation, formal evidence, or a paper
result. No G10 observation may be removed, relabeled, or rerun.

## 2. Independent unit and retained outcomes

The independent unit is the run/seed (`n=15` per G10 arm), never an individual
scheduler window. Windows are aggregated within run before any association is
computed. For each candidate versus paired C0, retain:

- log and ordinary ratios for throughput, QPR, latency, and unit completion
  cost;
- completion-ratio difference;
- joint favorable sign, defined as throughput ratio above 1, QPR ratio above
  1, completion ratio not below C0, and latency below C0; and
- every unfavorable or extreme seed, including C1 middle D100 and C2 middle
  D96/high D100.

## 3. Frozen pre-decision state features

For every G10 run, aggregate the following from all recorded policy windows:

- dependency-ready players divided by node count: mean, median, p90, p95,
  maximum, and fractions at or above 1x, 2x, 4x, and 8x node count;
- pending request-function pairs divided by node count using the same
  summaries and thresholds;
- waiting-for-candidate-node pairs divided by node count;
- zero-ready-window and nonzero-ready-window fractions;
- for C2 only, frontier candidates, outstanding frontier, frontier budget,
  frontier admitted, positive-admission-window fraction, and admissions per
  active window; and
- run-level queue area per arrival, CPU/memory utilization, cold-start wait,
  scheduling wait, completion, latency, cost, and policy wall time already
  retained by the frozen analyzer.

All features must exist before the window's placement outcome. No realized
throughput, QPR, load label, seed, or comparator result may enter a future
runtime switching decision.

## 4. Frozen descriptive analyses

1. Recompute all G10 paired outcome ratios directly from canonical summaries
   and reproduce the frozen report.
2. Produce complete run-level state-feature and paired-outcome tables.
3. For C2, compute Spearman correlations between each fixed state feature and
   paired log-throughput, log-QPR, negative log-latency, negative log-cost, and
   completion difference. Report all correlations; do not select only favorable
   coefficients or treat windows as independent samples.
4. Report each feature by low/middle/high as a descriptive check, but a load
   label cannot be used by a successor.
5. Evaluate the four fixed saturation thresholds R/N in `{1, 2, 4, 8}` only
   as diagnostic classifiers. A run is predicted frontier-favorable when at
   least half of its active windows meet the threshold. Report the complete
   confusion table against the joint favorable sign and balanced accuracy for
   every threshold. Ties prefer the smaller threshold. This is training only.
6. Independently audit that every C2 run has zero ready omission, frontier-
   bound, one-hop, and dispatch-class violations.

No p-value or post-hoc threshold can authorize a successor. Correlations and
classification scores are descriptive mechanism evidence.

## 5. Successor admission rule

At most one G11 successor may be preregistered only if all of the following
hold:

1. all 45 G10 runs and all fixed features are present and reproducible;
2. C2 activation/integrity remains valid in all 15 C2 runs;
3. at least one fixed, load-blind threshold has balanced accuracy at least
   0.70 for the joint favorable sign, with both sensitivity and specificity at
   least 0.60; and
4. the direction is mechanistically coherent: greater pre-decision saturation
   must predict greater frontier benefit in both throughput and QPR, and the
   chosen threshold cannot rely on one seed alone under leave-one-seed-out
   recomputation.

If admitted, the only allowed design is a state-conditioned work-conserving
hybrid:

- every dependency-ready player is always admitted;
- below the frozen saturation threshold, use the C0 ready order and no
  frontier;
- at or above the threshold, use remaining-work order and the existing global
  node-count-bounded one-hop frontier;
- the rule may use only the current ready count and configured node count;
- it may not inspect workload profile, load label, seed, realized outcome,
  baseline method, or future arrival data; and
- Eqs. (1)--(20), strict Eq. (15), Eq. (19), QPR, and offline-reference
  definitions remain unchanged.

If the admission conditions fail, no G11 implementation or new seed bank is
authorized from this path.

## 6. Future validation boundary

Even if admitted, implementation, tests, runtime freezing, protocol creation,
and a fresh seed bank require a separate committed G11 preregistration. The
future bank must be disjoint from D96--D100 and all earlier development/formal
banks. G10 estimates cannot be reported as G11 validation.

At this checkpoint:

- `g11_read_only_diagnosis_authorized=true`;
- `g11_implementation_authorized=false`;
- `g11_input_construction_authorized=false`;
- `g11_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`; and
- `formal_progression_authorized=false`.
