# G3 E0 operational development result audit

Date: 2026-09-04
Status: complete development gate failure; no formal or paper-ready result authorized

## Decision

The complete preregistered G3-E0 development product is a valid negative result.
All 135 online runs are retained. Neither operational E0 candidate satisfies the
global control-improvement gate, and neither the selected control nor either
counterfactual candidate satisfies the nine-baseline homogeneous-low gate.
Consequently, `ready_order` remains selected, formal confirmation is not
authorized, and homogeneous-middle formal execution remains blocked by the
earlier G1 homogeneous-low failure.

This result does not authorize seed replacement, post-hoc seed filtering, a
fourth order rule, repeated sampling until success, or a paper claim based on a
favorable cell. The next admissible activity is result-blind claim/scene and
mechanism diagnosis using the retained product.

## Frozen product and integrity

- Source/runtime commit: `93b572d`.
- Release binary: `target_g3_e0_operational_93b572d/release/serverless_sim.exe`.
- Release SHA-256: `6f700b2b...a0c3`; size: 4,811,264 bytes.
- Development bank: D71--D75, disjoint from earlier development/formal banks.
- Coverage: 3 candidates x 3 loads x 2 topologies x 5 seeds = 90 candidate
  runs, plus 9 homogeneous-low baselines x 5 seeds = 45 baseline runs.
- Total: 135/135 canonical attempt-1 runs, zero failed or quarantined runs.
- Input tapes: 30/30 canonical; 15 load/seed pairs share identical event
  streams across homogeneous and heterogeneous topology variants.
- Offline references: 90/90 canonical, zero missing/extra keys.
- Frozen FaaSRank model: SHA-256 `4853fffa...f17e`; its training tape is
  disjoint from D71--D75.
- Ready-manifest document/file hashes: `c7beed33...a657` /
  `a54f0fbb...02f4`.
- Final ledger: 272 events; last-event hash `fae46e...665e`; file SHA-256
  `42b35b...902e`.
- Selection artifact:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json`.
- Selection document/file hashes: `4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34`
  / `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`.

The analyzer first stopped twice before metric exposure because of integration
validation defects. Both fixes were result-blind, preregistered before code
changes, covered by directed negative tests, and committed separately. They
changed neither simulator output nor any metric, candidate, seed, rule, or
gate. The final analyzer passed on the unchanged 135-run product.

## Preregistered selection result

The maximin score is the worst of the twelve cell/metric ratios relative to C0
(`ready_order`), with six cells and two primary metrics per cell.

| Candidate | Worst ratio | Mean of 12 ratios | Cells winning both means | All 12 ratios > 1 |
|---|---:|---:|---:|---:|
| C0 `ready_order` | 1.0000 | 1.0000 | 3 | no (control) |
| C1 `ready_pne_envelope_first` | 0.7624 | 1.0095 | 1 | no |
| C2 `ready_pne_envelope_each` | 0.7372 | 1.0006 | 0 | no |

The arithmetic mean of ratios is not an authorization criterion. C1's mean is
slightly above one only because gains in high heterogeneous QPR offset losses
elsewhere; its worst cell/metric ratio is 0.7624. C2 is still less robust.

## Primary cell results

Each entry below uses all five paired seeds. Standard deviations are across
seeds. Percentage changes compare each candidate mean with C0 in the same
load/topology cell; positive is favorable for throughput and QPR.

| Load | Topology | Candidate | Throughput mean +/- SD | Delta T | QPR mean +/- SD | Delta QPR | Paired wins T/QPR/both |
|---|---|---|---:|---:|---:|---:|---:|
| low | homogeneous | C0 | 1.1434 +/- 0.3513 | 0.00% | 0.024900 +/- 0.012161 | 0.00% | -- |
| low | homogeneous | C1 | 1.1222 +/- 0.4013 | -1.85% | 0.028898 +/- 0.016375 | +16.05% | 2/4/2 of 5 |
| low | homogeneous | C2 | 1.1088 +/- 0.4003 | -3.03% | 0.028317 +/- 0.016094 | +13.72% | 1/4/1 of 5 |
| low | heterogeneous | C0 | 0.9056 +/- 0.3202 | 0.00% | 0.019797 +/- 0.013625 | 0.00% | -- |
| low | heterogeneous | C1 | 0.8138 +/- 0.3876 | -10.14% | 0.017828 +/- 0.013664 | -9.95% | 3/2/2 of 5 |
| low | heterogeneous | C2 | 0.8190 +/- 0.3793 | -9.56% | 0.018482 +/- 0.014330 | -6.65% | 3/2/2 of 5 |
| middle | homogeneous | C0 | 0.9770 +/- 1.0009 | 0.00% | 0.057949 +/- 0.116327 | 0.00% | -- |
| middle | homogeneous | C1 | 0.9906 +/- 1.0040 | +1.39% | 0.051023 +/- 0.100257 | -11.95% | 2/4/2 of 5 |
| middle | homogeneous | C2 | 0.9736 +/- 0.9995 | -0.35% | 0.050653 +/- 0.100396 | -12.59% | 1/2/0 of 5 |
| middle | heterogeneous | C0 | 0.7984 +/- 0.9353 | 0.00% | 0.026459 +/- 0.055728 | 0.00% | -- |
| middle | heterogeneous | C1 | 0.7712 +/- 0.9548 | -3.41% | 0.026202 +/- 0.054911 | -0.97% | 3/1/1 of 5 |
| middle | heterogeneous | C2 | 0.7460 +/- 0.9646 | -6.56% | 0.026191 +/- 0.054902 | -1.01% | 2/2/0 of 5 |
| high | homogeneous | C0 | 0.6512 +/- 0.7924 | 0.00% | 0.003365 +/- 0.005054 | 0.00% | -- |
| high | homogeneous | C1 | 0.5906 +/- 0.5971 | -9.31% | 0.002566 +/- 0.003314 | -23.76% | 2/3/2 of 5 |
| high | homogeneous | C2 | 0.5876 +/- 0.5915 | -9.77% | 0.002481 +/- 0.003165 | -26.28% | 2/2/2 of 5 |
| high | heterogeneous | C0 | 0.7326 +/- 0.8624 | 0.00% | 0.005688 +/- 0.010769 | 0.00% | -- |
| high | heterogeneous | C1 | 0.7828 +/- 0.9218 | +6.85% | 0.009008 +/- 0.015938 | +58.38% | 3/3/3 of 5 |
| high | heterogeneous | C2 | 0.7808 +/- 0.9146 | +6.58% | 0.008886 +/- 0.015664 | +56.24% | 3/3/3 of 5 |

All 24 paired-difference 95% t intervals (two candidates x six cells x two
metrics) include zero. This is a five-seed development screen, not an
inferential confirmation. The direction is also heterogeneous: both E0
variants improve both means only in high heterogeneous, while both materially
reduce QPR in high homogeneous.

Seed-level ratios show the same instability and are retained rather than
treated as exclusions. Examples include C1 low-heterogeneous D75
(throughput ratio 0.4040; QPR ratio 0.2595), C1 middle-heterogeneous D74
(0.6118; 0.5437), and C1 high-heterogeneous D72 (1.2413; 2.7009).

The complete numerical table is retained in
`G3_E0_OPERATIONAL_CANDIDATE_CELL_STATS.csv`.

## Homogeneous-low baseline gate

C0 beats both throughput and QPR means for only Random and Hash (2/9). C1 and
C2 each do so for Greedy, Random, Hash, and LoadLeast (4/9). Thus no candidate
beats all nine baselines on both primary metrics.

For C0, throughput is below Hiku, while QPR is below Greedy, LoadLeast,
FaaSRank-P, OCS, Hiku, Jiagu, and Orion. For C1 and C2, throughput is below
Hiku and Jiagu, while QPR is below FaaSRank-P, OCS, Hiku, Jiagu, and Orion.
The complete means, standard deviations, margins, and paired wins are retained
in `G3_E0_OPERATIONAL_BASELINE_STATS.csv`.

## Runtime and path-activation gate

The implementation-cost gate passes. Relative to C0, aggregate active-window
`solve_us` ratios range from 3.89--4.42 for C1 and 5.88--7.33 for C2, all below
the preregistered 9x ceiling. E0 accounts for 82.63--85.82% of C1 solve time
and 88.97--92.61% of C2 solve time.

The negative result is not caused by an inert implementation. Non-O0 PNEs are
selected in 31.08--43.86% of C1 and 32.66--45.48% of C2 selection rounds.
Fallback is rare (at most 0.0615% for C1 and 0.0138% for C2 in the summarized
cells). The complete runtime table is retained in
`G3_E0_OPERATIONAL_RUNTIME_STATS.csv`.

## Evidence-bounded interpretation

**Observation.** E0 changes a substantial fraction of decisions and meets the
runtime cap, but its effects are cell-dependent. The sole dual-mean gain occurs
under high heterogeneous load; high homogeneous QPR has the largest loss. The
nine-baseline failure is concentrated in QPR against advanced baselines.

**Interpretation.** Choosing a locally favorable, same-snapshot strict PNE by
cold-start/startup/projected-finish ordering is not sufficient to improve
future global throughput and QPR in a dynamic queue/container process. C2 pays
more overhead without a consistent benefit over C1. This is an inference from
the observed intervention pattern, not a proof of causality.

**Implication.** Another unmotivated ordering candidate is unlikely to resolve
the reviewer-facing gap. The bottleneck is no longer solver cost or whether E0
is exercised; it is the alignment among the paper's social-utility mechanism,
the dynamic workload, the QPR construction, and advanced baseline behavior.

**Next step.** Perform a result-blind diagnostic on these retained runs before
new sampling: audit the QPR numerator and denominator; decompose completions,
resource cost, waiting, cold starts, and projected-finish error by cell and
algorithm; and test whether the high-heterogeneous gain is associated with a
specific preregisterable state regime. Only one mechanism-level cause, fixed
before looking at a fresh bank, may justify a new maximum-three-candidate
development protocol on fresh D76--D80 seeds with the same paired nine-baseline
gate. Formal, burst, scaling, convergence, and offline-social-utility groups
remain blocked until that gate passes.

## Closure

Analyzer status is `complete_g3_e0_development_gate_failed`; selected candidate
is `ready_order`; `control_improvement_pass=false`;
`baseline_gate_pass=false`; `solve_time_gate_pass=true`;
`formal_confirmation_authorized=false`; and
`formal_results_eligible=false`. No main-paper experiment group is closed by
this development result.
