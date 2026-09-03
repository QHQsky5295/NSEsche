# P2 Homogeneous-Middle Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: `formal_complete_not_paper_ready_full_qpr_failed_high_blocked`

## 1. Stage decision

The one authorized homogeneous-middle invocation completed the exact frozen
selection: 200/200 runs were canonicalized, with no blocked run and no
result-conditioned replay, deletion, replacement, or extension. Result-blind
path reconciliation found all 200 runs at their exact canonical paths and
performed zero repairs or scientific re-executions. Pairing passed for all 20
Q61--Q80 seeds, and every run used one runtime identity.

This cell is **formal-complete but not paper-ready closed**. The reason is a
scientific full-QPR failure, not a missing artifact: five first QC-valid Q71
runs had zero throughput and zero completed requests, so their latency, cost
per completed request, and QPR are correctly undefined. The affected methods
are Greedy, Load Balance, OCS, Hiku, and NSESche. All five rows remain in the
200-row table.

Q71 is not an empty or corrupt workload. Its shared tape contains 2,459
arrival events, all ten methods use the same tape key and SHA-256, and five
other methods completed a small positive fraction. The NSESche Q71 run has
1,000 scheduler windows, valid strict-Eq.-(15) and reference streams, nonzero
CPU/memory activity, zero placement rejections, and passing QC. Therefore it
cannot be classified as a technical failure or retried.

Under the frozen V4 rule, homogeneous-high is blocked. The possible-stop
branch is not entered because NSESche ranks fifth, not 6--10, in throughput;
however, failure of the independent 20/20 QPR gate blocks progression in all
cases. No later online block is authorized by this audit.

## 2. Primary results

### Throughput

Mean throughput ranks (10^3 requests/s, numerically requests/ms) are:

| Rank | Method | Mean | 95% BCa CI | n |
|---:|---|---:|---:|---:|
| 1 | Load Balance | 0.67970 | [0.41768, 1.06359] | 20 |
| 2 | FaaSRank | 0.67465 | [0.39995, 1.07785] | 20 |
| 3 | Orion | 0.60905 | [0.38306, 0.95191] | 20 |
| 4 | Jiagu | 0.59945 | [0.36475, 0.98347] | 20 |
| 5 | NSESche | 0.59750 | [0.36804, 0.95229] | 20 |
| 6 | Hiku | 0.59575 | [0.35180, 0.97410] | 20 |
| 7 | Greedy | 0.58800 | [0.36099, 0.93313] | 20 |
| 8 | OCS | 0.54450 | [0.34572, 0.92602] | 20 |
| 9 | Hash | 0.43120 | [0.30057, 0.64386] | 20 |
| 10 | Random | 0.35265 | [0.23673, 0.49613] | 20 |

Against the throughput leader, Load Balance, NSESche's paired mean difference
is -0.08220 (about -12.1% of the baseline mean), with 95% paired-difference BCa
CI [-0.21673, 0.00720], raw two-sided sign-flip p=0.1642, Holm-adjusted p=1.0,
`dz=-0.330`, and 6 wins / 1 tie / 13 losses. NSESche is numerically close to
Jiagu and Hiku but is not the throughput leader.

### Run-level QPR

Applicable-run mean QPR ranks are:

| Rank | Method | Mean | 95% BCa CI | applicable n |
|---:|---|---:|---:|---:|
| 1 | Hiku | 0.012127 | [0.003667, 0.037651] | 19 |
| 2 | Load Balance | 0.010752 | [0.003379, 0.038144] | 19 |
| 3 | FaaSRank | 0.010459 | [0.003658, 0.031623] | 20 |
| 4 | OCS | 0.010212 | [0.003000, 0.033961] | 19 |
| 5 | Jiagu | 0.009672 | [0.002230, 0.042706] | 20 |
| 6 | Orion | 0.009371 | [0.003181, 0.030444] | 20 |
| 7 | Greedy | 0.007821 | [0.002329, 0.026915] | 19 |
| 8 | NSESche | 0.006368 | [0.002262, 0.015851] | 19 |
| 9 | Hash | 0.002356 | [0.001154, 0.006293] | 20 |
| 10 | Random | 0.001152 | [0.000558, 0.002417] | 20 |

Against Hiku on their 19 defined seed pairs, NSESche's mean difference is
-0.005759, with paired BCa CI [-0.022539, -0.000047], raw p=0.3010,
Holm-adjusted p=1.0, `dz=-0.290`, and 9 wins / 10 losses. The skew-sensitive
BCa interval and sign-flip p-value answer different questions and are both
reported; none of the 18 comparisons survives the frozen Holm family. Against
FaaSRank, the paired mean difference is -0.004636 with BCa CI
[-0.016789, -0.000825], raw p=0.1331, and Holm-adjusted p=1.0.

Consequently, the experiment does not support a claim that NSESche is best in
throughput or QPR under homogeneous middle load. The five undefined QPR values
also prevent a complete ten-method primary comparison from being paper-ready.

## 3. Submitted-figure alignment

The old-PDF diagnostic triggers in 34/40 method/metric cells: 8/10 latency,
9/10 cost, 9/10 throughput, and 8/10 QPR. This is broad scene-level drift,
not an isolated NSESche discrepancy.

For NSESche, the new mean latency is 253.424 ms versus the approximate old
267.802 ms (-5.37%); the new cost per completed request is 2.64686 versus
0.243902 (+985%); throughput is 0.59750 versus 1.084639 (-44.9%); applicable
QPR is 0.006368 versus 0.012199 (-47.8%). The corrected runtime, fixed paired
Q61--Q80 workload population, run-level QPR definition, and explicit
zero-completion retention differ materially from the submission-era evidence.
The old bars therefore remain provenance anchors and cannot justify selective
replacement of valid current observations.

## 4. Figure disposition

The preregistered figure entry point was invoked once. It correctly refused to
create the figure because QPR did not have ten complete ordered 20-run
summaries. Exit code was 1 and the registered figure directory remains absent.
This is the frozen fail-closed behavior: a visually complete primary figure
must not conceal five non-applicable QPR observations. Run rows, method
summaries, paired comparisons, and old-PDF alignment remain available for
audit, but there is no paper-ready P2 figure.

## 5. Immutable receipts

Registered workspace:
`runs/tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904/`

| Artifact | File SHA-256 | Document SHA-256, if applicable |
|---|---|---|
| append-only ledger | `35cfa1c8437592c7fd9b7f4024fa324e27f1ae1866df7b293f2d1e1eaee203e6` | final event `f75d3cc58df3c0d4c8cf0a2562892b36001a190dd5caf11caadbaa0ea5877708` |
| canonical reconciliation | `d4985d5e72361df825e929361f642b9ef20962ccaaddb2a4dcef6b143a25bf87` | `671dc2d52486e3277349a437d01a7421aafd14a0c5055fac86fa5f27b293a518` |
| G1 integrity report | `d82999c5eb75c467958ef220bdea7bc76bd5c9133acb5017a5bb750260093be0` | `9c7dea69f174604a6dae5862c6b514dae7fdf931df3a83b67756c0c46f3c9122` |
| P2 machine result | `6cb04bbaf6393653631bfdfd30512cdf4f87fb5887ddb857a72eef8b3bc81c88` | `aca00526ac25c9e33057cdc516069adf88f802a9e1174137f7048a1b3b9db4bb` |
| 200 run rows | `12933b62932a53c77b7754573491519f00aefaf6e7c10a0cae639824dc87cbce` | -- |
| 50 method/metric summaries | `a0ad6b988684014a99e57ec22d1a865b0df20ebe9fe1f9cf3be7704bb8cd6600` | -- |
| 18 paired comparisons | `a5ffc6325c2766eb1d59c82124bc494a5b0a72a018ff3d785757c39f267dc0db` | -- |
| 40 old-PDF alignment rows | `ad90022c9f3800c36cc92154a0ed44c8250d626af0f9384a1a6e9f04b3fe3ff7` | -- |

The ledger contains 402 hash-chained events and verifies through its final
hash. All three JSON document hashes and all four table receipts were
independently recomputed and match.

## 6. Storage and publication status

The complete workspace was copied to
`E:\NSEsche_experiment_archives\tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904`.
Source and archive independently contain 3,009 files and 285,034,689 bytes;
their ordered content inventories exactly match with tree SHA-256
`b20256c30646acd2e298129fb8f7a3b1e5748c0ae3a045cb3d24d0c005aded7f`.

Paper-section status after P2:

- P1 convergence/reference/exact-small evidence is closed and can support the
  reviewer response, with its previously recorded limitations.
- The 20-node homogeneous main comparison is not closed: low is retained but
  not dual-first, middle is now formal-complete but fails full QPR and both
  best-in-class objectives, and high is not run.
- Hyperparameter/ablation, heterogeneous main comparison, scaling, burst,
  QoS, and pricing/welfare online blocks remain unopened.
- The present evidence supports mechanism validation and a claim-reduced
  paper, not universal throughput/QPR leadership. Continuing toward a
  best-in-class claim requires a separately governed new-method research
  cycle rather than deleting Q71 or selectively replaying NSESche.
