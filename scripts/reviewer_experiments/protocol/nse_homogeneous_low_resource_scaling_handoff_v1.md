# NSESche homogeneous low-load resource scaling (E01-E20)

Outcome: `formal_nse_resource_scaling_freeze_pass`.
Resource-scaling gate passed: `true`.
Baselines are intentionally out of scope; this section evaluates NSESche's own proportional-load scaling.

| Nodes | Load scale | Throughput (req/ms) | QPR | Mean latency (ms) | Cost/completed | Completion rate |
|---:|---:|---:|---:|---:|---:|---:|
| 20 | 1x | 1.43905 | 0.0409601 | 125.458 | 0.463852 | 0.749336 |
| 100 | 5x | 5.88715 | 0.126073 | 172.598 | 0.463748 | 0.613956 |
| 500 | 25x | 21.1137 | 0.353263 | 199.102 | 0.630253 | 0.44055 |

| Transition | Throughput efficiency | QPR scale factor | Throughput difference BCa 95% CI | QPR difference BCa 95% CI | Joint primary pass |
|---|---:|---:|---:|---:|---:|
| n20_to_n100 | 0.8182 | 3.0779 | [3.81896, 5.15921] | [0.0577025, 0.118686] | true |
| n100_to_n500 | 0.7173 | 2.8020 | [11.9349, 19.5056] | [0.131242, 0.355861] | true |

- Exact product: 20 seeds x 3 node counts = 60 formal NSESche runs.
- All 60 were attempt-1 QC passes; selected quarantine count is zero.
- Every scale5/scale25 tape is an exact same-frame replication of the paired n20 tape.
- No baseline run was re-executed or included in this scaling claim.
- Raw run table: `scripts\reviewer_experiments\protocol\nse_homogeneous_low_resource_scaling_run_table_v1.csv`.
