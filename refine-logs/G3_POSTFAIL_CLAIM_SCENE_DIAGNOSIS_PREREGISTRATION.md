# G3 post-failure claim/scene diagnosis preregistration

Date: 2026-09-04

## Purpose and boundary

The complete G3-E0 D71--D75 development bank failed its frozen control and
nine-baseline gates. In accordance with Section 6 of
`TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V2.md`, this stage stops adding order
rules and returns to claim/scene diagnosis.

This is a read-only diagnostic of the retained product. It cannot create a
paper-ready result, select a seed, change a metric, change Eqs. (1)--(20), or
authorize a new online run. Its purpose is to determine whether one specific,
falsifiable mechanism/scene mismatch explains both (a) the E0 cell-dependent
effect and (b) NSESche's homogeneous-low QPR deficit against the advanced
baselines.

## Frozen inputs

- Selection artifact:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json`.
- Selection document SHA-256:
  `4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34`.
- Selection file SHA-256:
  `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`.
- Ready manifest document/file SHA-256:
  `c7beed33...a657` / `a54f0fbb...02f4`.
- Canonical product: 135/135 attempt-1 runs, comprising 90 C0/C1/C2 runs in
  all six load/topology cells and 45 homogeneous-low baseline runs.
- Seeds: D71--D75. All five seeds remain in every applicable comparison.
- Pairing unit: exact `(seed, load, topology)` for C1/C2 versus C0 and exact
  seed for the homogeneous-low baselines versus C0.
- Raw sources: validated `summary.json`, `frames.jsonl.gz`,
  `nash_metrics.jsonl.gz`, and their canonical manifests/QC receipts. No
  simulator output may be rewritten.

The analyzer must fail closed on a missing run, hash mismatch, non-finite
required value, broken pair, malformed compressed stream, or unexpected
schema. It must emit no result artifact on failure.

## D1: exact QPR factorization

For every paired run, use the already frozen definition

`QPR = throughput_requests_per_ms / (drained_mean_latency_ms * simulator_internal_cost_per_completed_request)`.

For candidate `k` relative to C0, compute the exact log decomposition:

`delta_log_QPR = delta_log_T - delta_log_L - delta_log_C`.

Report all four paired log differences per seed and, for each candidate/cell,
their arithmetic mean, sample standard deviation, two-sided 95% t interval,
and favorable/neutral/adverse sign count. The three QPR contributions are:

- throughput contribution: `delta_log_T`;
- latency contribution: `-delta_log_L`;
- cost contribution: `-delta_log_C`.

The identity residual must be at most `1e-12` per pair. The most adverse
component is the component with the smallest mean contribution; ties within
`1e-12` are retained as ties. The same decomposition is applied to each of the
nine homogeneous-low baselines relative to C0. Because the gate uses arithmetic
means of run-level QPR, this log analysis is explanatory only and cannot replace
the frozen gate.

## D2: completion, queue, resource, and cold-path proxies

For every run, retain the following prespecified values:

- fixed-window arrivals, completions, throughput, and completion ratio;
- drained-cohort arrivals, completions, completion ratio, mean/p95/p99 latency,
  and drain duration;
- total simulator cost and cost per completed request;
- placement rejections, admission rejects/drops, timeouts;
- queue peak and queue-area per arrival;
- frame means and maxima for active requests, tasks in system, queue total,
  unscheduled tasks, ready-unscheduled tasks, pending tasks, running tasks,
  running containers, starting containers, CPU utilization, and memory
  utilization.

`starting_container_frames / arrivals` is reported only as a starting-container
occupancy proxy. It must not be called measured cold-start latency or a cold-
start count. Likewise, queue-area per arrival is a queue-exposure proxy, not
request-level waiting time.

For C1/C2 versus C0 and every homogeneous-low baseline versus C0, report paired
differences and ratios using all five seeds. No outlier rule is permitted.

## D3: E0 intervention and state-regime association

This analysis applies only to the 60 C1/C2 runs. A scheduler window is active
when `decision.assigned_players > 0`. It is an E0-intervention window when
`operational_equilibrium_selection.selected_non_o0_rounds > 0`.

Per run, report active-window means and intervention-window versus
non-intervention-window means for the following prespecified fields:

- `cluster.queue_total`, `queue_resident_total`, `queue_runnable_total`,
  `queue_starting_resident_total`, `containers_running`,
  `containers_starting`, `pressure_mean`, and `pressure_max`;
- `traffic.arrival_rps` and `throughput_rps`;
- `decision.assigned_players`, `near_tie_player_ratio`,
  `running_warm_available_players / assigned_players`,
  `selected_running_warm_players / assigned_players`,
  `selected_starting_container_players / assigned_players`, and
  `selected_cold_or_nonrunning_players / assigned_players`;
- `network.cross_node_placement_ratio`;
- `social.final_welfare`, `empirical_gap`, and `reference_below_current`;
- selection intensity, selected-path inner rounds, solver inner/outer rounds,
  and limit indicators.

Undefined denominators remain null; they are not replaced by zero. Within-run
intervention/non-intervention contrasts are descriptive because successive
windows are dependent and the state may already reflect earlier decisions.

Across the 30 exact C1-to-C0 and 30 exact C2-to-C0 run pairs, compute Spearman
associations between intervention share and each of the paired changes in
throughput, QPR, latency, cost, completion ratio, queue-area per arrival, and
starting-container occupancy per arrival. Report nominal p-values, Holm-adjusted
p-values within each candidate family, and five leave-one-seed-out coefficients.
These are diagnostic associations, not causal estimates.

## D4: topology contrast on paired event streams

For every `(candidate, load, seed)`, form the paired difference-in-differences

`[(candidate - C0)_heterogeneous - (candidate - C0)_homogeneous]`

for log throughput, the three log-QPR contributions, log QPR, completion ratio,
queue-area per arrival, starting-container occupancy per arrival, and cross-node
placement ratio. Report the five seed values, mean, sample standard deviation,
95% t interval, and sign count. The high-load contrast is the prespecified focal
contrast because G3-E0 improved both primary means only in high heterogeneous
and lost both in high homogeneous; low and middle are reported as negative
controls, not discarded.

## Root-cause decision rule

A single mechanism-level cause is `diagnostically_supported` only if all of the
following are true:

1. one prespecified QPR component is the most adverse component in both C1 and
   C2 for high homogeneous and has the opposite sign in high heterogeneous;
2. the corresponding high-load topology contrast has the same favorable sign
   in at least 4/5 seeds for both C1 and C2;
3. at least one prespecified state exposure linked to that component has
   `abs(Spearman rho) >= 0.50`, retains the same sign in all five
   leave-one-seed-out estimates, and has Holm-adjusted `p < 0.10` in at least
   one candidate family;
4. the homogeneous-low C0-to-advanced-baseline decomposition identifies the
   same component for at least three of FaaSRank-P, OCS, Hiku, Jiagu, and Orion;
5. source inspection can map the exposure to exactly one operational mechanism
   outside Eqs. (1)--(20), without method-specific workload/HPA changes.

If several causes qualify, select the one with the largest absolute high-load
topology-contrast mean after standardizing by its five-seed sample standard
deviation; exact ties are reported unresolved. If none qualifies, status is
`complete_no_single_actionable_cause`, and no new candidate or sampling is
authorized.

If exactly one cause qualifies, status is
`complete_single_actionable_cause_supported`. This still does not authorize a
new candidate. It permits only a documented amendment to the experiment plan
and a separate result-blind preregistration containing C0 plus at most two
mechanistically derived alternatives on a fresh, disjoint bank. Baseline rows
must remain paired on that bank, and all valid runs must be retained.

## Outputs and stop rule

The one authorized analyzer invocation may create:

- `g3_postfail_diagnosis.json` with hashes, all run-level values, all pair-level
  values, aggregates, multiplicity corrections, decision status, and receipts;
- CSV tables for QPR decomposition, run-level scene metrics, intervention-state
  contrasts, associations, and topology differences;
- a human-readable result audit after the machine-readable product is frozen.

No plot, paper paragraph, online run, candidate implementation, or deletion of
valid observations is authorized by this preregistration. After the one
analysis, stop and audit the outcome before deciding whether the experiment
plan can be amended.
