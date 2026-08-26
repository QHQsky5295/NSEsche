# V79 frontier-guard exploratory handoff

V79 completed 120/120 technically valid screen runs, but it is not a formal
result and it failed the strict joint-blindness gate because one candidate/seed
QC report was exposed after execution and before the joint audit.

Outcome: `at_least_one_candidate_passed_exploratory_gate`.

Automatic exploratory winner:
`v79a-native-faithful-hiku1-jiagu1-frontier`.

Confirmation authorized: `false`.

## Baseline thresholds

| Metric | Best baseline | Mean |
|---|---:|---:|
| throughput_requests_per_ms | sche_FaaSRank | 7.1166 |
| qpr_finite_only | sche_OCS | 0.165261024708 |
| qpr_zero_completed_as_zero | sche_OCS | 0.165261024708 |

## Candidate gates

| Candidate | Throughput mean | QPR finite mean | QPR zero mean | Minimum relative margin | Pass |
|---|---:|---:|---:|---:|---:|
| v79a-native-faithful-hiku1-jiagu1-frontier | 7.1357 | 0.167369793713 | 0.167369793713 | 0.268387% | true |
| v79b-native-faithful-hiku2-jiagu1-frontier | 7.1379 | 0.160679466949 | 0.160679466949 | -2.772316% | false |
| v79c-native-faithful-hiku1-jiagu2-frontier | 7.1194 | 0.161600717493 | 0.161600717493 | -2.214864% | false |

## Scientific boundary

- Retain all V79 artifacts and the blindness-incident receipt.
- Do not generate or use E480-E499 as a confirmation block.
- Any continuation requires a fresh preregistered screen on E500-E509; only a
  later untouched E510-E529 block may serve as confirmation.
- Paired BCa intervals and all per-seed rows are preserved in the JSON result;
  they do not alter the preregistered arithmetic-mean gates.
