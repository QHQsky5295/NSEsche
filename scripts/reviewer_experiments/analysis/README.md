# Reviewer experiment analysis

This directory turns a raw CSV into a reproducible run-level table, BCa summaries,
paired tests, and a pre-declared `n=10 -> n=20` precision decision. It does not
delete or select runs based on performance, significance, method ranking, or
agreement with the submitted PDF.

## Prerequisites and canonical input

Analysis starts only after the adjacent protocol has completed the following
chain: manifest expansion; base-tape capture and E2/E3 derivation; tape binding;
measured class-isolated SLA pilots via `run-sla-pilots` and SLA freeze/binding;
the executable FaaSRank-P sequence
`capture-faasrank-training-tape -> preregister-faasrank-calibration ->
run-faasrank-calibration -> freeze-faasrank-model -> bind-faasrank-model`;
offline-reference build/binding; formal execution; and the cross-method pairing
audit. The supplied FaaSRank candidate grid is
`protocol/faasrank_candidates.json`, and `FTR01`--`FTR05` are the recommended
paired calibration seeds. Calibration and SLA-pilot artifacts remain outside
the formal E1--E9 run count, but both stages are implemented and hash-audited by
the protocol.

Run the protocol and analysis with the validated interpreter:

```powershell
$ReviewerPython = 'D:\Anaconda3\python.exe'
```

Before export, require a passing machine-readable pairing report:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol.pairing `
  path\to\manifest.ready.json path\to\run-ledger `
  --output path\to\run-ledger\pairing-audit.json
```

It verifies method coverage and equality of workload-tape,
function/DAG/QoS, node/network, common-HPA, simulation, and seed hashes within
each paired comparison. E2's node count is part of the scenario, so 100- and
500-node runs cannot be compared as pairs.

The preferred input has one row per independent run. Required comparison fields
are `algorithm`, `seed` (or `pair_id`), and the experimental context such as
`scenario`, `load`, and `node_count`. Metric aliases from the old scripts are
accepted, including:

- `cost_per_req -> cost`
- `time_per_req -> latency`
- `rps -> throughput` for legacy CSVs (an alias only; no implicit unit conversion)
- `coldstart_time_per_req -> cold_start_latency`
- `waitsche_time_per_req -> queue_latency`
- `exe_time_per_req -> execution_latency`
- `algo_exec_time -> scheduler_latency`

The workload identity is the hash-bound package declared by the protocol: an
ordered same-seed `{frame, dag_id}` event tape plus its event count, DAG-order
hash, derivation/capture receipt, measured arrival rate, and captured
function/DAG/QoS semantic hash. E2 5x/25x tapes duplicate parent events within
the same frames; E3 tapes remap arrival frames but retain event count and DAG
order. The provenance is Azure-trace-derived empirical-CDF generation, not a
claim that every tape event is a direct raw-trace event.

If multiple rows have the same run keys, count-like columns are summed, peak-like
columns take the maximum, and other numeric observations take the arithmetic mean.
The output records `source_rows` and any conflicting text-field warning.

Formal simulator summaries use `schema: "NSE_SUMMARY_V1"`. A technically
complete run with `completed == 0` remains valid: throughput is zero and
completed-request latency/cost are null. Coverage and undefined-metric counts
retain that run; it must not be deleted or rerun because its performance is
unfavorable.

QPR is never calculated from already-averaged bars. For every run `i`:

```text
QPR_i = throughput_i[requests/ms] /
        (cost_i[simulator internal cost/completed request] * latency_i[ms])
```

Only then are `QPR_i` values summarized across seeds. Missing, non-finite, zero,
and negative values receive explicit counts/status fields. A non-positive cost or
latency makes that run's QPR undefined and is reported as such.

## Statistical contract

- Point estimate: arithmetic mean of finite independent run-level values.
- Uncertainty: two-sided 95% BCa bootstrap CI (10,000 resamples by default).
- Comparison: seed-paired permutation test. It is exact through 16 pairs and uses
  reproducible Monte Carlo sign flips with a `+1` correction above that size.
- Multiplicity: Holm correction within each experimental-cell/metric family.
- Effect sizes: paired Cohen's `dz` and matched-pairs rank-biserial correlation.
- Effect direction: positive `oriented_improvement` always favors the reference;
  cost/latency/overhead metrics are automatically treated as lower-is-better.
- Repetition rule: evaluate the fixed first ten seeds. Throughput, cost, and QPR
  trigger extension when their relative CI half-width exceeds 5%; p95/p99 and
  scheduler-overhead metrics trigger when it exceeds 10%. If any predeclared
  trigger fails, extend the **entire scenario**: every method advances together
  to E11-E20. E7 stays at five seeds. The decision never
  examines ranking, effect direction, agreement with the old PDF, or whether a
  p-value crosses 0.05.

## Usage

When experiments were executed by the adjacent frozen protocol, first export only
QC-passed canonical `NSE_SUMMARY_V1` results. The exporter also retains backward
compatibility with the synthetic `summary_json_v1` test schema. Formal export is
strict by default: any missing run produces an error after writing the coverage
audit.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.analysis.protocol_results `
  --manifest path\to\manifest.json `
  --canonical-root path\to\run-ledger\canonical `
  --output path\to\runs.csv `
  --coverage path\to\coverage.csv
```

The exporter verifies result provenance, expands `{run_id}` in the result path,
converts physical Rust throughput from requests/s to requests/ms (the plotted
`10^3 requests/s` scale), maps simulator internal cost per completed request,
converts the direct `placement_policy_wall_ns` measurement to the Fig. 8
placement-decision milliseconds, and maps measured peak process-tree RSS to
MiB. The broader `scheduler_wall_ns` common-mechanism total and read-only
post-hoc evaluation time remain separately named diagnostics; no policy timing
is obtained by subtraction. One frame is 1 ms. E1, E2, and E4--E7 retain the
1000 ms submission horizon; E3 accepts the frozen request cohort for 1000 ms
and drains through frame 4000. The exporter uses
`fixed_observation_window.throughput_requests_per_second`, whose denominator
remains 1000 ms, together with the explicitly defined cohort completion ratio
and latency. Legacy summaries without these objects retain the old top-level
fallback and remain visibly distinguishable in exported audit columns.
CPU/memory normalized utilization is dimensionless; the underlying capacities
150 and 5000 are simulator internal units. The exporter explicitly
materializes the sealed identity-reuse rules in `reuse_analyses`: E2 receives
E1's 20-node homogeneous points, E5 receives Full NSESche, E6 receives the
original ten E1 methods at heterogeneous middle/high load, and E7 receives its
load-specific centre points (E01--E05 only). It first verifies the complete
source selector, identity workload/cluster contract, per-load Nash centre where
applicable, and source run/workload/HPA hashes. An unavailable or incompatible
source is written to coverage and is never copied.

Each materialized CSV row has a new analysis `run_id` and preserves
`source_run_id`, `source_run_spec_hash`, `source_workload_spec_hash`,
`source_common_hpa_hash`, source result path, sealed reuse-rule hash, and a
materialization hash. Thus a reused bar remains traceable to one physical run;
it is never presented as a second simulator execution.

All legend names denote placement-only adaptations under the common HPA,
cold-start model, container lifecycle, queue and runtime. The analysis therefore
compares `Scheduling Policy + Common HPA/Runtime`; it must not describe the bars
as complete native end-to-end baseline systems.

Main algorithms:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.analysis.summarize_runs `
  --input path\to\runs.csv `
  --output-dir path\to\analysis `
  --group-by scenario,load,node_count,algorithm `
  --metrics cost,latency,throughput,qpr,scheduler_latency `
  --treatment-column algorithm `
  --reference NSESche
```

Ablation variants should be analyzed as a separate family:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.analysis.summarize_runs `
  --input path\to\ablation_runs.csv `
  --output-dir path\to\ablation_analysis `
  --group-by scenario,load,variant `
  --metrics cost,latency,throughput,qpr `
  --treatment-column variant `
  --reference NSESche
```

Outputs are `run_level.csv`, `summary.csv`, `comparisons.csv`, `precision.csv`, and
`analysis_manifest.json`. The manifest contains the source SHA-256, parameters,
random seed, and QPR definition.

Run the synthetic regression suite with an environment that already contains
NumPy and Matplotlib:

```powershell
& $ReviewerPython -m unittest scripts.reviewer_experiments.analysis.tests.test_synthetic -v
```

## E3/E4/E8/E9 observability

`observability.py` consumes the canonical recorder artifacts (`frames.jsonl.gz`,
`requests.jsonl.gz`, `scheduler_windows.jsonl.gz`, `environment.json`) and the
dedicated authoritative `nash_metrics.jsonl(.gz)` or
`welfare_metrics.jsonl(.gz)` stream. `NSE_METRIC_V2` events retained in stdout or
stderr are only a compatibility fallback for legacy runs without the dedicated
stream; logs never override an available stream. Frames, requests, functions, and
scheduler windows are used only to construct a statistic *within* a run. All
confidence intervals, permutation tests, and Holm families use the run/seed as
the independent unit.

The frozen primary E3 recovery definition is joint queue-and-latency recovery.
Take the median queue and median rolling-p95 request latency in the 100 ms before
the first burst. After the final burst interval, recovery is the first point at
which both values are no greater than 110% of their respective baselines and
remain so continuously for 100 ms. Rolling p95 uses the preceding 100 ms;
arrival and throughput series use a 20 ms rolling window. A run that ends first
is right-censored. The table preserves censoring and
`restricted_recovery_time_ms`; it never silently deletes the run. Queue-only and
queue-plus-rolling-p99 recovery are auxiliary diagnostics and never replace the
primary endpoint.

E4 reports stage-latency p95/p99, offered rate, completed throughput, and
completion ratio separately for latency-, throughput-, and cost-sensitive
functions. `requests.jsonl` contains only fully completed requests, so it is
never used as the completion denominator. The primary arrived/completed counts
come from the final frame's cumulative `qos_function_tasks` counters (incremented
at request creation and every function completion). They must exactly match the
hash-bound replay tape after mapping each tape DAG to the functions/QoS classes
in `environment.json`. Old runs without these counters, missing tapes, mapping
gaps, or mismatches are `coverage_unavailable` and block formal completion-ratio
analysis; the code never infers 100% from the completed-request log.

The completed-request stream remains useful for latency samples. Its sample
count and coverage relative to the recorder's completed-function count are
reported explicitly; partial coverage is not relabeled as a full distribution.

SLA satisfaction is a directional target ratio clipped to `[0,1]` and is
evaluated once per QoS class within each run:

```text
lower-is-better:  s_c = min(1, target_c / observed_c)
higher-is-better: s_c = min(1, observed_c / target_c)
Jain:              J = (sum_c s_c)^2 / (C * sum_c s_c^2)
worst 10%:         mean of the bottom ceil(0.1*C) class satisfactions
```

Formal balanced-QoS run specifications carry the SLA thresholds frozen by the
pilot/binding stage. Analysis reads those manifest-bound values first and, when
an optional target JSON is supplied, requires exact equality. Missing or
mismatched thresholds remain `target_missing`/an analysis error; they are never
inferred from winners or from the submitted bars. Example:

```json
{
  "latency": {"metric": "stage_latency_p95_ms", "direction": "lower", "target": 50},
  "throughput": {"metric": "throughput_rps", "direction": "higher", "target": 5},
  "cost": {"metric": "direct_cost_mean", "direction": "lower", "target": 1.0}
}
```

`direct_cost_mean` is read from the recorder's cumulative per-QoS simulator
internal-cost summary and is explicitly not currency. `resource_cost_proxy_mean`
is also exported from completed-request samples, but it is a CPU/memory-time
proxy rather than the simulator's cost; it is used for an SLA only when that
metric is deliberately named in the target file.

E8 has two explicitly nested analyses. The original feature validation computes
Spearman rho across functions within each run. The differentiation audit reads
`active_differentiation_mean`, normalized placement dispersion, co-location
conflict ratio, near-tie ratio, and differentiation-changed-choice ratio from
each NSESche scheduler-window decision. It computes the four Spearman rhos
across windows *within a run*, then forms BCa intervals and sign-flip tests
across independent seeds; Holm correction covers the four outcomes within each
frozen experimental cell. Scheduler windows are never treated as independent
replicates. Missing/constant fields remain `NA` with per-window, per-run, and
cross-seed coverage/status outputs.

E9 reports inner/outer round distributions, limit-hit/oscillation/nonconvergence
rates, direct `placement_policy_wall_ns` / `placement_policy_thread_cpu_ns`
wall/thread-CPU time, measured process-tree peak RSS, offline build
wall/CPU/peak RSS, exact reference-table bytes, table load and per-window lookup
time, missing/zero/negative/unavailable reference ratios, persistence failures,
the recorded `offline_required_ok` indicator, positive-reference-only
`reference_below_current`, all-sign `reference_search_suboptimal`, and the
empirical gap `(W_ref-W)/W_ref`. The broader common-mechanism time and the
read-only post-hoc welfare-evaluator wall/thread-CPU time are retained as
separate fields; neither is folded into or arithmetically removed from the
direct policy measurement. Welfare rows may come from NSESche's solver event
or from the common `NSE_POSTHOC_WELFARE_WINDOW_V1` event used for other
schedulers. In both cases the gap uses the final proposed assignment evaluated
at the immutable baseline-price vector. Gap applicability is the fraction of
evaluation windows with a finite positive state-matched reference and a
formula-consistent gap. Zero and negative reference counts are applicability
observations, not technical/QC failures and never a reason to delete or rerun a
seed; measured unavailable/persistence/offline-required states are also retained
as observations rather than being recoded as missing. All E3, E4, and E9 bar families have seed-paired
permutation tests and Holm correction; `e9_metric_coverage.csv` preserves
not-applicable versus missing observations.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.analysis.observability `
  --manifest path\to\manifest.json `
  --canonical-root path\to\run-ledger\canonical `
  --output-dir path\to\observability `
  --sla-targets path\to\preregistered_sla_targets.json
```

The second synthetic suite covers censoring, per-class SLA/fairness, Spearman
aggregation, solver diagnostics, welfare applicability, and Fig. 11--13:

```powershell
& $ReviewerPython -m unittest scripts.reviewer_experiments.analysis.tests.test_observability -v
```
