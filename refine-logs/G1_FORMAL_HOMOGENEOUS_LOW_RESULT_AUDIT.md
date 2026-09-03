# G1 Formal Homogeneous-20 Low-Load Result Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: complete formal cell; dual-metric gate failed; old-PDF alignment gate
failed; homogeneous-middle execution is not authorized; no paper section is
closed

## 1. Frozen execution and retention

- Cell: E1, homogeneous 20-node cluster, low load.
- Methods: the frozen ten-method comparison.
- Seeds: exactly Q61--Q80, paired by workload tape.
- Online runs: 200/200 canonical, all on attempt 1.
- Every QC-valid observation is retained; no seed or method result was removed,
  replaced, or rerun because of its scientific value.
- Runtime source: `98f822cf2dcb878024a2ca39cc56533895ea692c`.
- Runtime binary SHA-256:
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Ready-manifest document hash:
  `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b`.
- Canonical reconciliation: 200 exact paths, zero reconciled paths, and zero
  simulator re-executions. Its document SHA-256 is
  `e0b6fd7f42962b2c07bf54699b32d7556bdb9347dd11f8c49a3fd07968fadd45`.
- Cell-report document SHA-256:
  `10dada54be25f19efa647d5c46bf5f7bf6528f12a6f55f33e02349d2ffa7f709`.
- Cell-report file SHA-256:
  `98558269dc6303f9245479f1a4aaa02d40ad0f727c3db491780558a0802f8073`.
- Ledger: 402 valid events; final hash
  `a9c880163187f2598fe60c5635f70da798bc592ceafa97dc480ce56c1a970cdc`.

The canonical result directory is
`runs/tscv1_g1_formal_q61_q80_98f822c_20260903/online/homogeneous-low`.
Its machine report records `complete_formal_cell_failed_gate`,
`next_cell_authorized=false`, and `paper_ready_closed=false`.

## 2. Complete 20-seed means

QPR is calculated within each run as throughput in requests/ms divided by
cost/completed-request and drained mean latency, and only then averaged across
the 20 seeds. Every method has 20/20 applicable QPR values.

| Method | Throughput (req/ms) | Completion ratio | Mean latency (ms) | Cost/completed | Mean QPR |
|---|---:|---:|---:|---:|---:|
| FaaSRank | **1.59810** | **0.830015** | 89.475 | 0.541000 | **0.064039** |
| Jiagu | 1.59220 | 0.826815 | 95.520 | 0.542319 | 0.059352 |
| NSESche | 1.58150 | 0.821267 | 97.943 | **0.533315** | 0.058107 |
| Greedy | 1.56480 | 0.812666 | 100.806 | 0.415887 | 0.056740 |
| Load Balance | 1.56180 | 0.810955 | 99.907 | 0.549198 | 0.057732 |
| Hiku | 1.55515 | 0.807611 | 94.513 | 0.544319 | 0.057551 |
| OCS | 1.55130 | 0.805738 | **88.412** | 0.550214 | 0.055985 |
| Orion | 1.54485 | 0.802231 | 99.445 | 0.551031 | 0.058375 |
| Hash | 1.02860 | 0.534712 | 182.820 | 0.695912 | 0.016115 |
| Random | 0.52730 | 0.273773 | 336.251 | 1.611822 | 0.002495 |

NSESche is not first in either frozen primary metric. Relative to FaaSRank,
its mean throughput margin is -0.01660 req/ms (-1.04%) and its mean QPR margin
is -0.005932 (-9.26%). It is also 0.01070 req/ms below Jiagu. Therefore the
strict cell gate fails and this cell cannot be used for a proposed-method
superiority claim.

## 3. Paired-seed diagnosis

Against FaaSRank, NSESche wins/ties/loses throughput on 9/1/10 seeds. The
paired median throughput difference is only -0.002 req/ms, but the mean is
pulled down by Q74 (-0.503) and Q69 (-0.253), partly offset by Q73 (+0.441).
This is a tail-sensitive throughput failure rather than uniform inferiority.

QPR is different: NSESche wins only 4/20 paired seeds and its median paired
difference is -0.002933. Relative to FaaSRank it has:

- mean completion-ratio difference -0.008747;
- mean latency difference +8.467 ms;
- mean cost/completed-request difference -0.007685.

NSESche's lower cost is insufficient to offset its higher latency and slightly
lower completion. Q72 and Q76 have nearly equal throughput to FaaSRank but QPR
deficits of -0.019117 and -0.029587 because their NSESche latencies are 102.3
versus 83.7 ms and 151.7 versus 100.0 ms, respectively.

## 4. NSESche mechanism evidence

The retained `nash_metrics.jsonl.gz` streams show, across Q61--Q80:

- 14.98% of choices with a running-warm candidate available bypass it;
- 24.29% of assigned players select a starting container;
- each warm bypass sacrifices 55.29 projected-finish-score units on average
  while gaining 1.664 units of the published paper utility;
- mean solver nonconvergence is 2.59%;
- no placement rejection, admission drop/reject, or timeout explains the gap.

Across the twenty fixed seeds, warm-bypass rate has a descriptive Spearman
association of -0.522 with the NSESche-minus-FaaSRank QPR difference; the
starting-container selection ratio has rho=-0.496, and the projected-finish
penalty per bypass has rho=-0.484. These are post-result descriptive
associations, not causal or selection statistics. They support the concrete
mechanism observed in Q72/Q76: strict paper utility frequently prefers an
under-utilized starting path over an available warm path, reducing end-to-end
latency efficiency.

Q74 is a separate tail case: it has a 7.22% nonconverged-solver-window rate and
71 `reference_below_current` observations. Q69 combines a 27.23% warm-bypass
rate, 37.59% starting-container selection, and queue area 1,204,193. A single
tie-break or result-filtering explanation cannot account for both failure
types.

The prior bounded-regret completion guards are not a valid remedy: they can
choose a lower-utility node and conflict with paper Eq. (15), and their closed
fresh-bank screens already showed cell-specific concentration failures. Any
successor must preserve strict best response and can only change an unpublished
equilibrium-selection detail such as feasible initialization or deterministic
update order, after separate preregistration on fresh development seeds.

## 5. Old-PDF numerical-alignment audit

The original PDF has SHA-256
`03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`.
Its page-9 Fig. 6 contains four raster subfigures. Because the original cache
JSON is absent from both rollback and revision repositories, the old values
below were reconstructed from the embedded 2,228-pixel-wide bars using the
printed axis grid coordinates. They are approximate figure-space readings,
not recovered raw observations.

| Method | Old T | New T | Delta | Old QPR | New QPR | Delta | Old cost | New cost | Delta |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Greedy | 1.8976 | 1.5648 | -17.5% | 0.04300 | 0.05674 | +31.9% | 0.3052 | 0.4159 | +36.3% |
| Random | 0.4601 | 0.5273 | +14.6% | 0.00209 | 0.00249 | +19.3% | 1.1878 | 1.6118 | +35.7% |
| Hash | 0.8933 | 1.0286 | +15.1% | 0.01325 | 0.01611 | +21.6% | 0.5869 | 0.6959 | +18.6% |
| Load Balance | 0.5679 | 1.5618 | +175.0% | 0.00426 | 0.05773 | +1254.8% | 1.3944 | 0.5492 | -60.6% |
| FaaSRank | 1.8567 | 1.5981 | -13.9% | 0.03277 | 0.06404 | +95.4% | 0.3615 | 0.5410 | +49.7% |
| OCS | 1.4558 | 1.5513 | +6.6% | 0.06516 | 0.05599 | -14.1% | 0.4554 | 0.5502 | +20.8% |
| Hiku | 1.8761 | 1.5552 | -17.1% | 0.15085 | 0.05755 | -61.8% | 0.3146 | 0.5443 | +73.0% |
| Jiagu | 0.5162 | 1.5922 | +208.5% | 0.00907 | 0.05935 | +554.7% | 0.5869 | 0.5423 | -7.6% |
| Orion | 0.2640 | 1.5449 | +485.2% | 0.00395 | 0.05838 | +1377.3% | 1.1033 | 0.5510 | -50.1% |
| NSESche | 1.7015 | 1.5815 | -7.1% | 0.15907 | 0.05811 | -63.5% | 0.3239 | 0.5333 | +64.6% |

None of the nine baselines is simultaneously inside the frozen +/-15% bands
for throughput, QPR, and cost. The reversal is especially large for Load
Balance, Jiagu, and Orion, so it cannot be explained as Monte Carlo noise. It
is also unsafe to declare the 180 baseline rows final-and-frozen solely because
their new-protocol QC passes. The affected low-load scene requires an explicit
whole-scene provenance/configuration audit; method-specific or seed-specific
replacement is forbidden.

The PDF text independently confirms that low load uses `(r0=0.6,wq=0.5)`.
The actual Q61 NSESche run config uses exactly those values, so the present
failure is not caused by a wrong low-load parameter centre.

## 6. Gate consequence and next scientific step

This formal batch remains immutable failed evidence. Homogeneous-middle,
homogeneous-high, heterogeneous comparisons, hyperparameters, ablations,
scalability, burst, QoS, welfare/PoA, feature validation, and convergence
figures remain unopened.

The next allowed work is result-blind diagnosis and preregistration of a new
strict-Eq.15 equilibrium-selection development family on fresh development
seeds, together with the whole-scene old-PDF provenance audit. A changed
NSESche implementation requires fresh independent confirmation seeds; Q61--Q80
must not be silently overwritten or reused as its formal confirmation bank.
