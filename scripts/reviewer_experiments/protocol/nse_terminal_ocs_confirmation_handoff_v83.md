# V83 formal confirmation terminal-OCS handoff

Outcome: `formal_confirmation_fail`.
Mean gate passed: `false`.
Formal confirmation success: `false`.

| Metric | Candidate mean | Best baseline | Baseline mean | Relative margin | Paired BCa 95% CI | Mean pass | CI pass | Formal pass |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.8038 | sche_jiagu | 6.772 | 0.469581% | [-0.281545634396, 0.336676450292] | true | false | false |
| qpr_finite_only | 0.205949556496 | sche_OCS | 0.220199798813 | -6.471506% | [-0.0657340901498, 0.0125779098264] | false | false | false |
| qpr_zero_completed_as_zero | 0.205949556496 | sche_OCS | 0.220199798813 | -6.471506% | [-0.0669481420426, 0.0123717005799] | false | false | false |

- Screen E590-E599 values were not pooled into this confirmation.
- E600-E619 completed as the dedicated formal-results-eligible cohort.
- Request-function/terminal-OCS/nonterminal-FaaSRank players: 526055/156502/369553.
- Guard evaluated/accepted/fallback windows: 19587/5751/13836.
- Formal success requires both frozen mean dominance and positive paired BCa lower bounds for all three metrics.
- Paired BCa intervals and per-seed rows are retained in the JSON result.
