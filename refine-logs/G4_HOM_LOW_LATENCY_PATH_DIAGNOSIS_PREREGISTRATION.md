# G4 homogeneous-low latency-path diagnosis preregistration

Date: 2026-09-04

## Purpose

The G3 post-failure diagnosis shows that the 20-node homogeneous-low QPR gap is
primarily associated with advanced baselines' lower drained-cohort latency,
while the E0 order envelope does not provide a stable topology or state-regime
explanation. This G4 stage therefore compares the retained request/function
stage traces and scheduler source paths before any further NSESche change.

The analysis is read-only. It cannot close the main comparison, alter or select
seeds, authorize a plot, or start a simulator. It exists to identify at most
one latency-path mechanism that can be tested later without changing Eqs.
(1)--(20), common HPA, workload, topology, or any baseline.

## Frozen inputs and population

- Parent diagnostic document/file SHA-256:
  `003cf898...284d9` / `1dc51c9d...0716`.
- Ready manifest and canonical root are the same hash-bound G3-E0 product.
- Cell: exactly 20-node homogeneous low.
- Seeds: all D71--D75.
- Methods: NSESche C0 plus all nine paired baselines, for 50/50 runs.
- Primary latency comparators: FaaSRank-P, OCS, Hiku, Jiagu, and Orion.
- Greedy, Random, Hash, and LoadLeast are retained as declared negative/control
  comparators; none may be removed based on a result.
- NSESche C1/C2 are not inputs to the primary source comparison because their
  gate has already failed. Their prior results remain retained and unchanged.
- Authoritative streams: canonical `summary.json`, `requests.jsonl.gz`,
  `frames.jsonl.gz`, `scheduler_windows.jsonl.gz`, and for NSESche
  `nash_metrics.jsonl.gz`; all manifests and QC receipts must revalidate.

The analyzer must fail closed before output on any hash, schema, count,
completion-stream, pairing, or finite-value error.

## D1: completed-function stage decomposition

For every completed function record, reproduce the existing simulator-boundary
definitions:

- schedule wait: `max(scheduled_frame - ready_schedule_frame, 0)`;
- cold-start wait: `cold_start_done_frame - max(ready_schedule_frame,
  scheduled_frame)`, or zero when no cold-start boundary exists;
- data wait: `data_received_frame - cold_start_done_boundary`, or zero when no
  data-received boundary exists;
- execution: `function_done_frame - data_received_boundary`.

Negative durations fail closed. Reduce function records within each run to
count, mean, median, p95, p99, and sum for each stage, plus cold-start event
count/share. Also report each stage's fraction of the sum of the four mean
stage durations. These are completed-function diagnostics and are not relabeled
as a causal decomposition of request latency.

For each baseline and seed, compute NSESche-C0 minus baseline run-level
differences for all stage statistics. Across the five seeds, report mean,
sample standard deviation, 95% t interval, and positive/neutral/negative count.
Positive means NSESche spends more time in that stage.

## D2: common-completion request and function pairs

For each `(baseline, seed)` pair, match completed requests by `request_id` and
completed functions by `(request_id, function_id)`.

Report:

- NSESche-only, baseline-only, and intersection counts;
- intersection coverage relative to each method's completed stream;
- within-intersection request-latency and stage differences;
- the mean, median, p95, p99, and sign fraction of matched differences, reduced
  to one row per run pair before cross-seed summaries.

The common-completion analysis is a censoring diagnostic. It cannot replace the
full-cohort latency metric or treat requests/functions as independent seeds.
The full-cohort and common-completion mean latency signs must be reported side
by side.

## D3: prespecified NSESche path exposures

From NSESche C0 only, reduce each run to:

- waiting-for-candidate-nodes divided by pending request/function players;
- no-feasible players divided by request/function players;
- selected running-warm, starting-container, and cold/nonrunning shares;
- running-warm bypass share;
- candidates per assigned player and assignment moves per assigned player;
- complete-assignment share, inner/outer limit shares, and dispatch failures;
- cross-node placement, data-blocked queue, parent-blocked queue, runnable
  queue, resident queue, starting-resident queue, pressure, CPU utilization,
  and running/starting container exposure.

For each exposure, report its Spearman association across the five NSESche
seeds with NSESche's mean and p95 value for each of the four stage durations.
These five-point associations are descriptive only; no p-value is used as an
authorization gate.

## D4: source-path comparison

After the trace product is frozen, inspect only the scheduling source files for
NSESche and the five primary comparators. Record whether each implementation
explicitly uses the following prespecified dimensions in its task/order or node
choice path:

- DAG readiness/criticality or dependency depth;
- current running-warm and starting-container state;
- queue/backlog or predicted finish time;
- function execution demand and node capacity/load;
- data locality/network transfer;
- QoS/quality class;
- multi-function/request coupling versus independent function placement;
- deferral when no candidate is immediately available;
- per-window dispatch breadth/command count.

Each yes/no/partial classification must cite a source symbol and line. This is
a semantic inventory, not a performance ranking. A source difference can
support a cause only if it maps to the stage selected by D1/D2 and to a measured
NSESche exposure in D3.

## Single-cause decision rule

One stage/mechanism is `diagnostically_supported` only if all conditions hold:

1. its NSESche-minus-baseline mean-stage difference is positive in at least
   4/5 seeds for at least three of the five primary comparators;
2. it is the largest positive mean completed-function stage gap for at least
   three primary comparators;
3. the common-completion request-latency mean has the same adverse sign as the
   full-cohort latency gap in at least 4/5 seeds for those same comparators;
4. at least one prespecified NSESche exposure has the mechanistically expected
   association sign with that stage in at least 4/5 leave-one-seed-out
   estimates, with absolute full-sample `rho >= 0.50`;
5. source comparison identifies exactly one shared operational difference that
   maps to the stage/exposure and lies outside Eqs. (1)--(20).

Expected exposure directions are frozen as follows:

- schedule wait: higher waiting/no-feasible/blocked/runnable/resident queue is
  adverse;
- cold-start wait: higher starting/cold selection and starting-container
  exposure is adverse, while higher running-warm selection is favorable;
- data wait: higher cross-node placement or data-blocked queue is adverse;
- execution: higher pressure/CPU/co-location or lower capacity headroom is
  adverse.

If multiple stages pass, select the stage that is the largest gap for the most
primary comparators; then the one with the larger median standardized gap;
otherwise report an unresolved tie. If no unique stage passes, status is
`complete_no_single_latency_cause`, and no implementation/sampling is
authorized.

If one stage passes, status is `complete_single_latency_cause_supported`. That
status authorizes only an experiment-plan amendment and separate
preregistration. It does not authorize source changes or new runs by itself.

## Outputs and stopping point

The analysis may write one machine-readable JSON plus CSVs for run-level stage
metrics, method/seed pairs, matched request/function diagnostics, NSESche
exposures, and exposure/stage associations. After those files are frozen, stop
for a result audit and the D4 source inventory. No valid observation may be
deleted or replaced.
