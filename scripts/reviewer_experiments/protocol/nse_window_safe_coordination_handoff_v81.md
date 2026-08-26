# V81 result-blind window-safe coordination handoff

Outcome: `result_blind_screen_fail`.
Screen gate passed: `false`.
Formal-confirmation preparation authorized: `false`.
Formal confirmation success: `false`.

| Metric | Candidate mean | Best baseline | Baseline mean | Relative margin | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.2385 | sche_FaaSRank | 6.2675 | -0.462704% | false |
| qpr_finite_only | 0.144903104996 | sche_OCS | 0.19710295057 | -26.483543% | false |
| qpr_zero_completed_as_zero | 0.144903104996 | sche_OCS | 0.19710295057 | -26.483543% | false |

- V80 values were not pooled into this decision.
- E510-E529 inputs remain absent at reveal time.
- E540-E559 inputs remain absent at reveal time.
- Guard evaluated/accepted/fallback windows: 9754/3219/6535.
- A pass authorizes only preparation of a dedicated formal-results-eligible confirmation shard; it is not itself a formal confirmation.
- Paired BCa intervals and per-seed rows are retained in the JSON result.
