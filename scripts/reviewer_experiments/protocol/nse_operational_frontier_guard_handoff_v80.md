# V80 result-blind frontier replication handoff

Outcome: `result_blind_replication_screen_fail`.
Replication gate passed: `false`.
Formal-confirmation preparation authorized: `false`.
Formal confirmation success: `false`.

| Metric | Candidate mean | Best baseline | Baseline mean | Relative margin | Pass |
|---|---:|---:|---:|---:|---:|
| throughput_requests_per_ms | 6.3006 | sche_FaaSRank | 6.4493 | -2.305677% | false |
| qpr_finite_only | 0.143550864755 | sche_Hiku | 0.149978135528 | -4.285472% | false |
| qpr_zero_completed_as_zero | 0.143550864755 | sche_Hiku | 0.149978135528 | -4.285472% | false |

- V79 values were not pooled into this decision.
- E480-E499 remain permanently unused after the V79 blindness incident.
- E510-E529 inputs remain absent at reveal time.
- A pass authorizes only preparation of a dedicated formal-results-eligible confirmation shard; it is not itself a formal confirmation.
- Paired BCa intervals and per-seed rows are retained in the JSON result.
