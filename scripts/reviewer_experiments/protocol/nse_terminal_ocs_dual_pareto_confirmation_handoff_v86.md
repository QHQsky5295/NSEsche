# V86 NSESche homogeneous 100-node low-load scale5 formal confirmation

Outcome: `formal_confirmation_fail_close_v86`.
Joint confirmation gate passed: `false`.
This is the fresh E690-E709 formal confirmation cohort; E680-E689 screen seeds are not pooled.

| Metric | NSESche mean | Frozen floor | Relative margin | BCa 95% CI (candidate-floor) | Mean gate | CI gate | Joint |
|---|---:|---:|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.80685 | 6.772 | 0.514619% | [-0.726531344249, 0.75730680263] | true | false | false |
| qpr_finite_only | 0.154045299299 | 0.220199798813 | -30.042943% | [-0.0980952004423, -0.0282365195453] | false | false | false |
| qpr_zero_completed_as_zero | 0.154045299299 | 0.220199798813 | -30.042943% | [-0.0978392698721, -0.0276073795661] | false | false | false |

- Baseline online reruns: 0; the compatible frozen 20-node NSESche point remains the comparison anchor.
- All 20 candidate runs and 20 clean-rebuilt references passed on attempt one; quarantine was empty.
- V83 initializer alternatives/substitutions: 0/0; the frozen anchor was preserved.
- Coordination evaluated/accepted/fallback windows: 19604/3909/15695.
- A pass freezes the homogeneous 100-node NSESche point. A failure closes V86 without further tuning on E680-E709.
