# V84 NSESche 100-node low-load candidate-screen handoff

Outcome: `result_blind_screen_fail`.
Screen gate passed: `false`.
Formal-confirmation preparation authorized: `false`.
Formal confirmation success: `false`.

| Metric | NSESche mean | Frozen best baseline | Threshold | Relative margin | BCa 95% CI of difference | Pass |
|---|---:|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.1541 | sche_jiagu | 6.772 | -9.124335% | [-2.4684140145, 0.681141380396] | false |
| qpr_finite_only | 0.120172017739 | sche_OCS | 0.220199798813 | -45.425918% | [-0.147374057977, -0.0559361465435] | false |
| qpr_zero_completed_as_zero | 0.120172017739 | sche_OCS | 0.220199798813 | -45.425918% | [-0.147800286348, -0.0557726631922] | false |

- Baseline online reruns: 0; thresholds were frozen before V84 implementation.
- All 10 candidate runs and 10 references passed on attempt one; quarantine was empty.
- Faithful/admissible/rejected players: 137628/115255/137628.
- Guard evaluated/accepted/fallback windows: 9808/877/8931.
- A pass authorizes only fresh E630-E649 formal preparation; it is not a formal success claim.
- A failure closes V84 and forbids tuning on E620-E629.
