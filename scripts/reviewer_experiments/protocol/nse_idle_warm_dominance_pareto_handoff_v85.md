# V85 NSESche homogeneous 100-node low-load scale5 screen

Outcome: `result_blind_screen_fail`.
Screen gate passed: `false`.
Candidate-only E660–E679 confirmation authorized: `false`.
This was a result-blind development screen, so it is not the frozen publication point.

| Metric | NSESche mean | Frozen floor | Relative margin | BCa 95% CI of difference | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.5172 | 6.772 | -3.762552% | [-1.43750336044, 0.926552507588] | false |
| qpr_finite_only | 0.14718267036 | 0.220199798813 | -33.159489% | [-0.114962901293, -0.0108495791595] | false |
| qpr_zero_completed_as_zero | 0.14718267036 | 0.220199798813 | -33.159489% | [-0.115537418919, -0.010354800989] | false |

- Baseline online reruns: 0; this paper section evaluates the NSESche resource-scaling trend.
- All 10 candidate runs and 10 references passed on attempt one; quarantine was empty.
- Initializer gate evaluated/accepted windows: 9794/859.
- Accepted idle-warm substitutions: 1060.
- Coordination guard evaluated/accepted/fallback windows: 9794/2439/7355.
- V85 improved over the failed V84 aggregate in both throughput and QPR, but it remained below every frozen quality floor.
- E660–E679 must not be generated. V85 is closed and E650–E659 may not be used to tune another candidate.
- Frozen result: `scripts/reviewer_experiments/protocol/nse_idle_warm_dominance_pareto_result_v85.json`.
- Full audit artifacts: `tmp/nse_idle_warm_dominance_pareto_20260827_v85`.
