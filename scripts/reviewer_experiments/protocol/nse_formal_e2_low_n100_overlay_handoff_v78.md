# Formal E2 NSESche overlay V78 handoff

## Outcome

The frozen V76 NSESche profile completed the preregistered E2
low/homogeneous/n100/scale5 E01--E20 overlay with 20/20 attempt-one QC passes,
zero quarantine, a valid 42-event ledger, and 20/20 passing pairing groups.
The result-blind audit revalidated all 20 candidate artifacts, all 180 frozen
baseline artifacts, and all 180 cross-version seed/method pair equalities before
any metric was parsed.

The strict three-mean gate **failed**. No seed was deleted or replaced, no
baseline was rerun, and no gate was relaxed.

| Rank by throughput | Method | Throughput (requests/ms) | Rank by QPR | QPR |
|---:|---|---:|---:|---:|
| 1 | Jiagu | 6.579350 | 3 | 0.176454 |
| 2 | **NSESche V76** | **6.560500** | **4** | **0.174297** |
| 3 | FaaSRank | 6.490650 | 8 | 0.165886 |
| 4 | Orion | 6.405350 | 5 | 0.167976 |
| 5 | LoadLeast | 6.349000 | 6 | 0.167155 |
| 6 | Greedy | 6.272600 | 7 | 0.167004 |
| 7 | Hiku | 6.266850 | 1 | 0.186536 |
| 8 | OCS | 6.196150 | 2 | 0.176485 |
| 9 | Hash | 2.822400 | 9 | 0.021500 |
| 10 | Random | 0.747100 | 10 | 0.001710 |

All methods had 20 finite QPR observations, so finite-only and
zero-completed-as-zero QPR are identical in this cell.

## Gate margins and paired uncertainty

- Throughput: NSESche was 0.01885 requests/ms (0.2865%) below Jiagu. The
  paired BCa 95% interval for NSESche minus Jiagu was
  [-0.33471, 0.38483] requests/ms.
- QPR: NSESche was 0.012239 (6.561%) below Hiku. The paired BCa 95% interval
  for NSESche minus Hiku was [-0.032838, 0.011209].
- Relative to FaaSRank, NSESche was 1.076% higher in throughput
  (paired difference 0.06985, BCa 95% interval [-0.06680, 0.22260]) and 5.070%
  higher in QPR (paired difference 0.008411, BCa 95% interval
  [0.000156, 0.019143]). This confirms the narrower V76 comparator result but
  does not establish superiority over all nine baselines.

## First-principles interpretation

NSESche is already near the throughput frontier and has favorable arithmetic
mean latency/cost components (140.01 ms and 0.46335 cost units/completed
request), but the preregistered QPR is computed per run before averaging. Hiku's
much lower mean latency (109.12 ms) yields the best QPR despite lower throughput;
Jiagu retains a small throughput lead. The result therefore exposes two distinct
frontiers rather than a runtime or provenance failure.

The legitimate next step is a new development cohort that explicitly studies
the latency/throughput frontier, followed by a fresh untouched confirmation
cohort. These revealed E01--E20 results cannot be reused for tuning or selective
reruns.

## Immutable evidence

- Ready manifest hash:
  `ccf6a6d708518effe5d190532f228e6764b026074749563d1a44903c8b976050`
- Formal ledger last hash:
  `5986190d50132c8cdb968c7a62d37a1ab7649a281bc77888dd94645bd315c8c9`
- Passing blind-audit file SHA-256:
  `76144f5cb04d2e4b04b0ba1e859f3d0014f2d60006ba614275e3fb171dfe1bbf`
- Result file SHA-256:
  `6000994bd110ef2b00eba4e62742318f77cde7292d9005fd6eabca594446ac88`
- Candidate binary SHA-256:
  `c6de355055a134b117e54abb973c6d732a43ac725b21a2f08ff96d0e100668ea`
- Frozen baseline binary SHA-256:
  `ee07c609f50906acdb89c805cf5ff9204d3120da11c37ca45fac404659c8e0d5`

The machine-readable result contains the complete 200-run raw table, method
summaries, rankings, strict gates, and NSESche-vs-each-baseline paired BCa
intervals in `nse_formal_e2_low_n100_overlay_result_v78.json`.
