# V82 result-blind dependency-pipeline handoff

Outcome: `result_blind_screen_fail`.
Screen gate passed: `false`.
Formal-confirmation preparation authorized: `false`.
Formal confirmation success: `false`.

| Metric | Candidate mean | Best baseline | Baseline mean | Relative margin | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 5.3527 | sche_FaaSRank | 5.6231 | -4.808735% | false |
| qpr_finite_only | 0.106873900686 | sche_OCS | 0.121067868174 | -11.723976% | false |
| qpr_zero_completed_as_zero | 0.106873900686 | sche_OCS | 0.121067868174 | -11.723976% | false |

- Prior-family values were not pooled into this decision.
- E540-E559 inputs remain absent at reveal time.
- E570-E589 confirmation inputs remain absent at reveal time.
- Pipeline players/incomplete-parent players/ready players: 379295/191426/187869.
- Guard evaluated/accepted/fallback windows: 0/0/0.
- A pass authorizes only preparation of a dedicated formal-results-eligible confirmation shard; it is not itself a formal confirmation.
- Paired BCa intervals and per-seed rows are retained in the JSON result.
