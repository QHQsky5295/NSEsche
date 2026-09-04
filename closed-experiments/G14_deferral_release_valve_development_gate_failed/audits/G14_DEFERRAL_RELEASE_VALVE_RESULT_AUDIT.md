# G14 Deferral Release-Valve Development Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Analyzer/selection commits: `4da9b196cd11be443db239931ac15a721ad5ab8a`,
`728b15d11db34371cb3526e2d9f555f042b89714`

Status: `complete_g14_development_gate_failed_strong_baselines_blocked`

## 1. Complete retained population

The one authorized result-blind invocation executed all 30 frozen C0/G14 x
low/middle/high x D106--D110 specifications in manifest order. All 30 runs
canonicalized on attempt 1. There were no technical retries, seed
replacements, run omissions, result-conditioned extensions, or quarantined
attempts. Reconciliation found all 30 paths exact and performed zero repairs.

Independent validation reopened every canonical directory against the bound
manifest. All 30 runs are QC-valid, have positive fixed-window completion, and
have defined run-level QPR. The 450-file canonical online tree contains
29,091,644 bytes and has sorted inventory hash
`c3d12f92420e2b5bd9b1aa96ebbfa9045dd4003f87fab21178cb0b4c282d3fb1`.
The partial and quarantine trees contain zero files.

The append-only online ledger contains 62 valid chained events, has final
event hash
`0fd4fe2ddbb84bcb7dd9e548ec3b104be09137e2609158b2730af24b36facf5b`,
and its 58,977-byte file has SHA-256
`57098080c5b2df294720c9ac1082d3b62fa182af3816dcc88b5ad73668e82d44`.
The reconciliation report has canonical document hash
`d2fe20ac1e8157d8f0625599255e189e31944e72a9d139e2dfc77561a79e92fb`
and file SHA-256
`1a9e70ec0bd0c40805c271d1806d49dd036039985ddc798c1578981ba0f744b1`.

## 2. Frozen gate outcome

The frozen analyzer returned `complete_g14_development_gate_failed` and
selected no candidate. Its complete 389,275-byte report has canonical
document hash
`737fec07a20b42d1d2a20ee5044643bd717ccaf838d922f0a9779d4a61ab2ea0`
and file SHA-256
`aa318b727ab7fb89a5bcee271e0b36200a9235aceaadb8969b739a769c038ebc`.
An independent second implementation recomputed throughput, latency, cost,
QPR, completion, all 30 run contributions, method means, ratios, and paired
wins directly from canonical summaries. It matched every reported run metric
exactly (maximum absolute difference 0).

| Load | G14 throughput mean | G14/C0 | G14 QPR mean | G14/C0 | Paired wins T/QPR/joint |
|---|---:|---:|---:|---:|---:|
| low | 1.2544 req/ms | 1.01934 | 0.0313815 | 1.01790 | 2/2/2 |
| middle | 0.6556 req/ms | 0.99514 | 0.00388810 | 1.02701 | 0/3/0 |
| high | 1.4412 req/ms | 1.15112 | 0.0131728 | 1.27120 | 4/4/3 |

G14 passes population integrity, the 0.80 per-seed floors, its complete
state-machine activation gate, and the policy-overhead cap (conditions 1, 4,
7, and 9). It fails the all-load dual-mean, 3/5 paired-win,
leave-one-seed-out, completion/latency, and strict runtime-integrity
conditions (2, 3, 5, 6, and 8).

The low-load arithmetic means improve in both primary metrics, but only D108
and D110 are strict paired joint wins; D106 and D107 are exact ties, while
D109 has equal throughput and a slightly lower QPR. Middle-load throughput is
lower for four seeds and tied for one. Its candidate/control mean throughput
ratio is 0.99514, and all five leave-one-seed-out throughput differences stay
negative (-0.00400 to -0.00225 req/ms). The middle-load QPR increase therefore
cannot qualify the mechanism.

High load passes its mean, paired-win, floor, and leave-one-seed-out primary
tests. D110 has the largest retained gain (throughput/QPR ratios
1.58351/2.37713), but the high-load effect is not solely sign-dependent on
that seed: after omitting D110, the mean paired throughput and QPR differences
remain positive at +0.02775 req/ms and +0.00034137, respectively.

Mean completion/latency are 0.65570/138.73 ms for G14 versus
0.64319/135.96 ms for C0 at low load, 0.25970/227.05 ms versus
0.26095/233.31 ms at middle load, and 0.20844/299.19 ms versus
0.18156/300.62 ms at high load. Thus low fails on latency and middle fails on
completion; only high satisfies the joint secondary condition. The
candidate/control placement-policy wall-time ratios are 1.0366, 0.9905, and
1.0529, all below the fixed 1.50 cap.

## 3. Mechanism activation and runtime integrity

The release valve is genuinely exercised. The numbers of seeds with at least
one bounded first-overflow window are 3/5, 4/5, and 5/5 at low, middle, and
high load. Six runs across middle and high record persistent-overflow full
release. Across all 15 candidate runs, 836 first-overflow windows defer 9,440
feasible players, while 1,069 adjacent persistent-overflow windows release
the full feasible-ready set. No positive-deferral episode exceeds one window.
All readiness, feasibility, legacy-order, prefix, admission-rule,
state-transition, dispatch-set, and auxiliary bound violation totals are
zero.

G14 records 14,710 strict-PNE/reference windows among 14,711 active windows.
High D108 frame 979 reaches the unchanged four-round inner-iteration limit for
40 admitted players, so no offline reference is requested for that unstable
state. C0 records 14,704 strict-PNE/reference windows among 14,708 active
windows: high D108 frame 418, high D109 frames 311 and 315, and high D110
frame 404 reach the same inner limit. All five windows explicitly terminate
with `inner_iteration_limit`, `inner_stable=false`, and
`reference_source=not_requested`.

These retained runtime exceptions make condition 8 fail. They do not drive
the negative decision: G14 separately fails four performance/robustness/
secondary conditions, including the frozen all-load throughput and paired-win
requirements.

## 4. Evidence-bounded interpretation

**Observation.** The one-bit valve exactly enforces isolated first-overflow
deferral, retains strict ordering and feasibility, and adds little scheduler
overhead. It yields strong high-load gains and modest low-load mean gains, but
does not improve middle-load throughput and does not produce enough strict
low-load paired wins.

**Interpretation.** Releasing all feasible-ready work after one bounded
overflow window corrects G12's persistent-backlog pathology under sustained
high pressure. At low pressure the mechanism is mostly inactive, producing
ties, while at middle pressure its occasional deferral trades a small amount
of throughput for lower latency/cost and higher QPR. A single parameter-free
binary rule therefore does not meet the preregistered across-load dual-metric
claim. This is development evidence, not a manuscript claim.

**Implication.** G14 may not be compared with strong baselines, confirmed,
replayed on Q61--Q80, or used in a figure. D106--D110 are exhausted
development evidence and cannot be rerun, filtered, or reused to validate a
successor.

**Next step.** Only a separately preregistered, read-only diagnosis over all
retained G14 traces may determine whether a genuinely new observable-state
mechanism is justified. This result audit alone authorizes no scheduler
change, successor sampling, load-specific binary, strong baseline, or formal
run.

## 5. Immutable archive

The complete G14 run root was copied without deletion to:

`E:\NSEsche_experiment_archives\tscv1_g14_deferral_release_valve_d106_d110_64d36b7_20260904`

Source and archive inventories match exactly: 1,092 files, 396,182,667 bytes,
and sorted inventory hash
`fdb9706343dd4871e49c75be0cd7a2f81f15e095b9ea7aacf65d4ba04de59b63`.
The C-drive source remains intact.

## 6. Authorization boundary

- `g14_candidate_selected=false`;
- `g14_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_successor_diagnosis_authorized=true`.
