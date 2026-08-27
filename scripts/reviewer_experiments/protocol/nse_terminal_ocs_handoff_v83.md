# V83 result-blind terminal-OCS handoff

Outcome: `result_blind_screen_pass`.
Screen gate passed: `true`.
Formal-confirmation preparation authorized: `true`.
Formal confirmation success: `false`.

| Metric | Candidate mean | Best baseline | Baseline mean | Relative margin | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.999 | sche_FaaSRank | 6.6838 | 4.715880% | true |
| qpr_finite_only | 0.223533882058 | sche_OCS | 0.211184236957 | 5.847806% | true |
| qpr_zero_completed_as_zero | 0.223533882058 | sche_OCS | 0.211184236957 | 5.847806% | true |

- Prior-family values were not pooled into this decision.
- E570-E589 inputs remain absent at reveal time.
- E600-E619 confirmation inputs remain absent at reveal time.
- Request-function/terminal-OCS/nonterminal-FaaSRank players: 255081/83967/171114.
- Guard evaluated/accepted/fallback windows: 9787/3051/6736.
- A pass authorizes only preparation of a dedicated formal-results-eligible confirmation shard; it is not itself a formal confirmation.
- Paired BCa intervals and per-seed rows are retained in the JSON result.
