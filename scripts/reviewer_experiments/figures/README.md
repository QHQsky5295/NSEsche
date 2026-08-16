# Reviewer figure templates

`plot_figures.py` consumes `summary.csv` and, optionally, `comparisons.csv` from
the analysis pipeline. Every bar shows the run-level mean with an asymmetric 95%
BCa error bar. A `*`, `**`, or `***` above a comparator denotes a Holm-adjusted
paired comparison against NSESche at 0.05, 0.01, or 0.001.

All baseline names in these figures denote placement-only adaptations under the
single common HPA, cold-start model, container lifecycle, queue, and runtime.
They are not a second native-control track. Run the templates with the same
validated interpreter used by the experiment protocol:

```powershell
$ReviewerPython = 'D:\Anaconda3\python.exe'
```

The templates preserve the submitted visual structure:

- Fig. 5: `1 x 4` ablation panels with the submitted Set3 colors. The fourth
  component is labeled `w/o Nash–Social Coordination`, matching the frozen E5
  mechanism boundary.
- Fig. 6: `2 x 2` homogeneous performance panels and algorithm colors.
- Fig. 7: paired CPU/memory `10 x 3` heatmaps (ten frozen methods by
  low/middle/high load). The companion `fig7_resource_heatmap_ci.csv` retains
  every cell's run-level mean, 95% BCa interval, sample count, and explicit
  `ok`/`partial`/`unavailable` coverage; absent cells are printed as `NA`.
- Fig. 8: direct placement-policy-overhead bars across low/middle/high
  workloads. The plotted source is `placement_policy_wall_ns` per scheduling
  window, not the broader common-mechanism `scheduler_wall_ns`; common-mechanism
  and post-hoc welfare-evaluation timings remain separate E9 diagnostics.
- Fig. 9: the same `2 x 2` layout for heterogeneous workloads.
- Fig. 10: `2 x 3` scale panels for cost, latency, throughput, QPR, CPU, and memory.

The submission-era fixed-load Fig. 10 is retained only as a clearly labelled
fixed-load resource-provisioning observation in supplementary material. It is
not merged with the paired weak-scaling cells or used for formal confidence
intervals.

Performance-figure throughput is plotted as `10^3 requests/s`, numerically equal
to requests/ms. This is the same per-run throughput quantity used in QPR; burst
time-series plots continue to show physical requests/s.

Latency is stacked when the three component metrics are available; its error bar
is the BCa interval of total per-run latency, not a sum of component intervals.
Both PNG (300 dpi) and vector PDF are written.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.figures.plot_figures `
  --summary path\to\analysis\summary.csv `
  --comparisons path\to\analysis\comparisons.csv `
  --output-dir path\to\figures `
  --figure all
```

Default scenario names are `ablation`, `homogeneous`, `heterogeneous`, and
`weak_scaling`; each can be changed with the corresponding `--fig*-scenario`
option. Fig. 10 defaults to the predeclared high-pressure weak-scaling series;
choose another with `--fig10-load`. A plot deliberately fails on duplicate summary
cells rather than silently averaging across an unspecified QoS class, burst type,
or workload.

## Fig. 11--13

`plot_observability.py` consumes the E3/E4/E8/E9 CSVs produced by
`analysis.observability`:

- Fig. 11: a `2 x 2` aligned time series of request arrivals, queue backlog,
  completions, and rolling p99 latency. Gray bands are the frozen burst windows;
  lines are run means and shaded intervals are pointwise 95% run-bootstrap bands.
- Fig. 12a: one `2 x 4` figure per frozen burst pattern, covering peak queue,
  restricted joint queue+p95 recovery/censor time, recovery fraction,
  drop/reject/timeout, and request p95/p99. Fig. 12b is a `2 x 3` QoS figure
  covering class p95 latency, throughput, simulator cost, completion ratio,
  SLA violation rate, Jain index, and worst-10% satisfaction.
- Fig. 13: a `3 x 4` validation/diagnostic figure. It contains run-level
  Spearman effects (including active differentiation versus dispersion,
  co-location conflict, near ties, and changed top choice), convergence and
  stability, scheduler time, online/offline peak RSS, offline build wall/CPU
  time, exact table bytes, table load/lookup time, missing/zero/negative
  reference status (including unavailable, persistence failures, and
  `offline_required_ok`), welfare/reference coverage, and optional constructed-game
  exact PoA panels.

Every Fig. 12/13 bar uses a run-level 95% BCa interval. Stars are read only from
the corresponding seed-paired permutation/Holm table. CLI rendering fails
closed when those comparison inputs are missing; unavailable values remain
`NA` and retain separate coverage CSVs.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.figures.plot_observability `
  --figure all `
  --output-dir path\to\figures `
  --e3-timeseries-summary path\to\e3_timeseries_summary.csv `
  --e3-run-metrics path\to\e3_run_metrics.csv `
  --e3-run-summary path\to\e3_run_summary.csv `
  --e3-comparisons path\to\e3_comparisons.csv `
  --e4-qos-summary path\to\e4_qos_summary.csv `
  --e4-fairness-summary path\to\e4_fairness_summary.csv `
  --e4-qos-comparisons path\to\e4_qos_comparisons.csv `
  --e4-fairness-comparisons path\to\e4_fairness_comparisons.csv `
  --e8-feature-summary path\to\e8_correlations_summary.csv `
  --e8-differentiation-summary path\to\e8_differentiation_correlations_summary.csv `
  --e9-diagnostic-summary path\to\e9_diagnostics_summary.csv `
  --e9-comparisons path\to\e9_comparisons.csv
```

Fig. 11 accepts only one burst pattern per output. Fig. 12 automatically writes
one burst-resilience figure for each available frozen pattern plus the QoS
figure. Fig. 13 accepts one fully specified diagnostic context; its defaults
are E1/high/20 nodes/heterogeneous. These checks
prevent accidental averaging across different workloads or cluster sizes.
Fig. 11 annotates recovered/right-censored/NA run counts when E3 run metrics are
provided. Fig. 12 prints `NA` for unavailable cells; neither template converts a
censored or unavailable value to zero.
