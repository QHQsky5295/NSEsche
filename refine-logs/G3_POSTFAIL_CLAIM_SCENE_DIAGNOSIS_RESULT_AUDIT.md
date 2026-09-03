# G3 post-failure claim/scene diagnosis result audit

Date: 2026-09-04
Status: complete; no single actionable cause; no new candidate or sample authorized

## Decision

The preregistered read-only diagnosis completed on all 135 retained D71--D75
runs. Its status is `complete_no_single_actionable_cause`. None of the five
joint root-cause conditions passed, so the result does not authorize another
ordering rule, a state-specific E0 gate, fresh development seeds, formal
homogeneous-middle, or any later paper experiment.

The useful result is narrower: the homogeneous-low publication gap is primarily
a latency gap, whereas the tested E0 ordering intervention produces unstable,
seed-dependent tradeoffs among throughput, latency, and unit completion cost.
The next admissible action is read-only source/trace comparison of the latency
path against the strongest baselines. It is not new sampling.

## Product integrity

- Machine-readable report:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/diagnosis/g3_postfail_diagnosis.json`.
- Report document SHA-256:
  `003cf898a60208e28133b8c4c7d20cd7bb28c1977f8237b861bcd84c4c4284d9`.
- Report file SHA-256:
  `1dc51c9d98c86bdc79e91e086368968343e1261742d40b305e284e63d4870716`;
  size: 1,678,224 bytes.
- Coverage: 135 run rows, 60 exact candidate-to-C0 pairs, and 45 exact
  baseline-to-C0 pairs; all D71--D75 observations retained.
- Additional output hashes:
  - QPR pairs: `67f5d8b4...74ee`;
  - run/scene metrics: `f0d6a239...a3c1`;
  - intervention/state contrasts: `ea97207a...3f85`;
  - associations: `6b09f8ab...7cea`;
  - topology differences: `6b8c6bfe...630f`.
- The first invocation failure and its source-faithful correction are retained
  in their separate preregistration/audit records. The successful retry used
  the unchanged canonical product and did not invoke the simulator.

## QPR factorization

For every pair, the identity
`delta log QPR = delta log throughput - delta log latency - delta log cost`
holds within `1e-12`. Positive component values favor the treatment.

| Candidate/cell | Throughput contribution | Latency contribution | Cost contribution | Total log-QPR change |
|---|---:|---:|---:|---:|
| C1 low homogeneous | -0.0329 | +0.1423 | -0.0376 | +0.0718 |
| C2 low homogeneous | -0.0462 | +0.1385 | -0.0489 | +0.0434 |
| C1 low heterogeneous | -0.1497 | +0.0892 | -0.1422 | -0.2028 |
| C2 low heterogeneous | -0.1354 | +0.1157 | -0.1283 | -0.1480 |
| C1 middle homogeneous | -0.0034 | +0.0559 | -0.0330 | +0.0194 |
| C2 middle homogeneous | -0.0194 | +0.0536 | -0.0492 | -0.0151 |
| C1 middle heterogeneous | -0.0348 | -0.0820 | -0.0407 | -0.1575 |
| C2 middle heterogeneous | -0.1134 | +0.1629 | -0.1203 | -0.0708 |
| C1 high homogeneous | +0.0561 | +0.0481 | +0.0698 | +0.1740 |
| C2 high homogeneous | +0.0560 | +0.0120 | +0.0699 | +0.1379 |
| C1 high heterogeneous | +0.0282 | +0.2010 | +0.0269 | +0.2561 |
| C2 high heterogeneous | +0.0335 | +0.2044 | +0.0316 | +0.2696 |

These are means of paired log changes and therefore describe geometric rather
than arithmetic behavior. They do not replace the frozen arithmetic-mean gate.
The distinction is material: high homogeneous arithmetic-mean QPR falls by
23.76% for C1 and 26.28% for C2, even though 3/5 and 2/5 seed-level log changes
are positive and their mean log changes are positive. The large absolute loss
on D74 dominates the arithmetic QPR mean. This is retained tail sensitivity,
not an exclusion criterion.

## Why the high-topology contrast did not qualify

For C1, heterogeneous-minus-homogeneous high-load difference-in-differences
has mean log-QPR `+0.0821`, but only 2/5 seeds are positive and its 95% t
interval is `[-0.9485, +1.1127]`. C2 is similar: mean `+0.1317`, 2/5 positive,
and interval `[-0.8723, +1.1356]`.

Both candidates' high-load throughput and cost topology contributions are
positive for only 2/5 seeds; latency is positive for 3/5. Thus the apparent
high-heterogeneous arithmetic-mean gains of 58.38% and 56.24% do not identify
a stable topology regime. D72 and D74 provide the large favorable outcomes,
while D71, D73, and D75 have adverse high-load topology contrasts.

## State associations

The only very strong preregistered associations are between throughput log
change and completion-ratio change: C1 `rho=0.9083`, C2 `rho=0.9457`, both
Holm-adjusted `p<0.001` with stable leave-one-seed-out signs. This is expected
from the fixed observation window, shared arrivals, and completion-based
throughput, and does not identify an independent scheduling mechanism.

C1's cost contribution versus running-container change is suggestive
(`rho=-0.4643`, Holm `p=0.0877`) but fails the frozen `abs(rho)>=0.50` rule;
C2 is weaker (`rho=-0.4216`, Holm `p=0.1828`). All other root-cause
associations fail the effect/multiplicity/stability combination. In particular,
intervention share versus log-QPR change is weak for C1 (`rho=0.1199`) and C2
(`rho=0.0687`), both Holm-adjusted `p=1.0`.

Within candidate runs, intervention windows are high-pressure windows rather
than a random subset. Relative to non-intervention windows, C1/C2 intervention
windows have roughly 270/238 more queued tasks, pressure-mean increases of
0.186/0.180, and 139/136 requests/s higher instantaneous throughput. They shift
about 12.4/12.3 percentage points of assigned players from starting containers
to already-running warm containers. The selected-cold-or-nonrunning share is
zero throughout. These descriptive contrasts show that E0 is active and favors
warm running placements when the system is pressured, but they cannot explain
the inconsistent run-level QPR effect.

## Homogeneous-low publication gap

The advanced baselines' dominant advantage over C0 is latency in every case.

| Method | Throughput | QPR | Mean latency (ms) | Unit completion cost |
|---|---:|---:|---:|---:|
| NSESche C0 | 1.1434 | 0.024900 | 84.46 | 0.6444 |
| NSESche C1 | 1.1222 | 0.028898 | 79.68 | 0.6792 |
| NSESche C2 | 1.1088 | 0.028317 | 79.81 | 0.6891 |
| FaaSRank-P | 1.0924 | 0.032705 | 58.20 | 0.7187 |
| OCS | 1.0878 | 0.038957 | 64.30 | 0.6519 |
| Hiku | 1.1514 | 0.039986 | 54.47 | 0.6151 |
| Jiagu | 1.1376 | 0.040392 | 63.10 | 0.6749 |
| Orion | 1.0646 | 0.030033 | 66.57 | 0.6954 |

C0 throughput is only 0.70% below Hiku and exceeds the other advanced
baselines except Hiku; its cost is also close to Hiku/OCS and lower than
FaaSRank-P/Jiagu/Orion. Its QPR deficit is therefore not primarily a throughput
or cost problem. C1 improves mean latency by 5.66% relative to C0 but loses
1.85% throughput and increases unit completion cost by 5.39%. That raises QPR
by 16.05% relative to C0, yet remains 28.45% below Jiagu's mean QPR.

This narrows the next source diagnosis: NSESche needs a material reduction in
end-to-end drained-cohort latency without sacrificing fixed-window completion
or unit completion cost. Re-ranking same-snapshot non-worse-welfare strict PNEs
by cold/startup/projected-finish summaries is insufficient.

## Observation, interpretation, implication, next step

**Observation.** E0 is exercised in roughly one third to nearly one half of
active windows and changes warm/starting placement mix, but its primary effects
are seed- and cell-dependent. The low-homogeneous QPR gap against advanced
baselines is consistently associated with their substantially lower latency.

**Interpretation.** The current locally evaluated operational envelope is not
aligned with the full request/DAG critical-path latency realized after
dispatch. Its same-snapshot welfare guard and aggregate startup/finish ranking
do not reliably predict future queue evolution. The data do not support a
topology-only or intervention-frequency explanation.

**Implication.** Further tuning of E0 order frequency or choosing favorable
high-heterogeneous seeds would not provide a defensible solution. A viable
mechanism must target the request/DAG latency path while preserving completion
and cost, and it must be derived from source/trace evidence rather than from a
new seed search.

**Next step.** Compare NSESche with Hiku, Jiagu, OCS, Orion, and FaaSRank-P at
homogeneous low using the retained paired traces and source paths. Decompose
drained request latency into DAG scheduling/ready wait, data communication,
execution, and cold-start boundaries where the records support them; audit
player collection, per-window dispatch, and critical-path prioritization. This
read-only analysis must be preregistered before detailed trace outcomes are
examined. No new online run is yet authorized.

## Experiment-section status

- 20-node homogeneous low main comparison: not closed; NSESche is not first in
  throughput or QPR.
- Homogeneous middle/high: blocked by the low-load gate.
- Heterogeneous low/middle/high: not closed and blocked by the ordered protocol.
- Scaling, burst, QoS, convergence, offline social-utility, pricing/welfare,
  and ablation groups: not started as paper-ready groups; still blocked.
- Paper-ready figures: none authorized from G1/G2/G3 development products.
