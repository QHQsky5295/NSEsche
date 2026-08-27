# V86 NSESche homogeneous 100-node low-load scale5 screen

Outcome: `result_blind_screen_pass`.
Screen gate passed: `true`.
This is a candidate-only development screen, not yet the frozen publication point.

| Metric | NSESche mean | Frozen floor | Relative margin | BCa 95% CI of difference | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 7.4914 | 6.772 | 10.623154% | [-0.508828286664, 1.65320841569] | true |
| qpr_finite_only | 0.236888377101 | 0.220199798813 | 7.578834% | [-0.0680135157261, 0.219544477738] | true |
| qpr_zero_completed_as_zero | 0.236888377101 | 0.220199798813 | 7.578834% | [-0.0700382660084, 0.221969006029] | true |

- Baseline online reruns: 0; this paper section evaluates the NSESche resource-scaling trend.
- All 10 candidate runs and 10 references passed on attempt one; quarantine was empty.
- V83 initializer alternatives/substitutions: 0/0; the frozen anchor was preserved.
- Coordination evaluated/accepted/fallback windows: 9843/1937/7906.
- A pass authorizes only a separately committed, unchanged-candidate E690-E709 confirmation.
- A failure closes V86 and forbids tuning on E680-E689.
