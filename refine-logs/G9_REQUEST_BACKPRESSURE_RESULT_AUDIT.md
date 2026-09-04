# G9 Request-Level Backpressure Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Zero-result selection commit: `5137da7bb1311ab8a8a5107512ff271990e4aea6`

Status: `complete_g9_development_gate_failed_confirmation_blocked`

## 1. Execution and retention

The one authorized result-blind invocation completed all 75 selected runs on
attempt 1. All 75 canonical directories are exact manifest paths; reconciliation
made zero repairs and did not re-execute the simulator. There is no quarantine
directory. The report retains 75/75 run metrics and 75/75 artifact receipts.

All runs passed QC and had positive completion and defined run-level QPR. Thus,
unlike P2's Q71 edge case, G9 has no undefined result and no technical or
scientific basis for a retry.

| Product | Files | Bytes | Inventory/document SHA-256 |
|---|---:|---:|---|
| canonical online tree | 1,125 | 129,588,496 | `c89f9827cfed258032192acecf91dfaeb3023002eaa4a33cbda756ec16ce0cde` |
| reconciliation report | 1 | 58,789 | `1962b1f5d801493ef8a483c1da1bae86be310c1da9810c5d8066b06b19a607f8` |
| G9 analysis report | 1 | 351,095 | `7b2afe603a528edc096e43f149888f10b85c27cdcff6326b62d25ef58447bd10` |

The analysis file SHA-256 is
`7b76f319cf4c42c76a69878348f15d4d2f40b592a4c6b2be2982de01e2377db0`.
The reconciliation file SHA-256 is
`7a3d3eadd149b421108ff3cc8c94d35e132e9873ebdfaab3b20b09f54ce98e71`.

## 2. Frozen gate result

Four of ten conditions pass: complete QC-valid paired coverage, positive
completion/defined QPR, request-backpressure activation/integrity, and policy
wall-time overhead. Six fail: throughput rank, QPR rank, paired control wins,
positive paired means against every baseline, the 0.80 per-seed control floors,
and the combined strict-PNE/reference/runtime condition.

| Load | Candidate throughput (kreq/s) | Control | Change | Candidate rank | Candidate QPR | Control QPR | Change | QPR rank |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| low | 0.1544 | 1.6320 | -90.54% | 5/5 | 0.00018648 | 0.06130837 | -99.70% | 5/5 |
| middle | 0.3628 | 1.3376 | -72.88% | 5/5 | 0.00131359 | 0.06162593 | -97.87% | 5/5 |
| high | 0.0678 | 0.5738 | -88.18% | 5/5 | 0.00004267 | 0.00217677 | -98.04% | 5/5 |

Against `ready_order`, throughput wins are 0/5, 1/5, and 0/5 for low,
middle, and high; QPR wins are 0/5 at every load. All 18 load x baseline x
metric paired means are negative. Every one of the 15 candidate/control pairs
fails the joint 0.80 floor. The smallest throughput and QPR ratios are 0.00877
and 0.0000918, respectively. These margins are decisive and are not plausibly
explained by the three separate control-integrity exceptions below.

All leave-one-seed-out candidate means remain far below the corresponding
control and baseline means. No seed is removed or promoted.

## 3. Mechanism diagnosis

The mechanism did exactly what was preregistered but imposed the wrong
operational bottleneck. In every candidate run, `live_requests > 20` and a
positive deferred population were observed in 986--997 of the 1,000 windows.
The admitted cohort therefore remained essentially fixed at 20 requests while
the mean live population ranged from roughly 830 to 3,530 requests.

Because admitted requests contain dependency-blocked DAG descendants, twenty
live requests do not imply twenty ready function players. Mean schedulable
players per window fell to 0.24--3.24 in individual candidate runs, compared
with 4.03--32.60 for `ready_order`. At the load-level, the candidate/control
mean assigned-player counts per window are approximately 0.52/4.77,
1.48/10.77, and 0.43/19.74 for low, middle, and high. The mechanism is thus
not work-conserving: it protects request age while starving the scheduler of
ready work. The throughput/QPR collapse is a direct, telemetry-supported
consequence of this mismatch, not excess placement-policy computation.

The policy wall-time ratios are 1.161, 0.729, and 0.541, all below the frozen
1.25 ceiling. Backpressure activation passes in 15/15 candidate runs, and all
15 candidate runs pass their strict dispatch/reference/runtime checks. The
failure is therefore attributed to the fixed request-count admission rule,
not to nonactivation or candidate corruption.

## 4. Separate integrity exceptions

The combined condition 9 passes in 27/30 NSESche runs: 15/15 candidate runs
and 12/15 controls. One middle-control window hit the four-round inner limit,
so it correctly had no requested reference. Three high-control active windows
used hash-matched but nonpositive offline reference values, which the frozen
analyzer rejects as usable reference evidence. Runtime binary identity and the
common execution-time Git identity agree in all 75 runs. These four exceptional
windows are reported without repair and do not rescue any failed performance
condition.

## 5. Immutable archives and authorization boundary

The complete 1,768-file, 461,180,190-byte G9 run root was copied without
modification to
`E:\NSEsche_experiment_archives\tscv1_g9_request_backpressure_d81_d85_d5241f9_20260904`.
Source and archive independently have tree SHA-256
`f5892e6e33b52d9ac24a5374d1a3dff9da44333383e407b5cf20f9ced440cb1c`.

G9 is closed as a negative development result. D86--D95 confirmation, formal
replay, figures, and paper performance claims are not authorized. Reusing
D81--D85 to tune or select a replacement is also prohibited.

The only scientifically legitimate next mechanism route is a separately
named, separately preregistered development candidate on a fresh seed bank.
The retained G9 telemetry may motivate a work-conserving design that limits
ready players rather than live requests, but it cannot supply confirmation
evidence for that design. Until such a protocol is frozen, `ready_order`
remains the paper-faithful NSESche implementation and G9 remains diagnostic
negative evidence only.
