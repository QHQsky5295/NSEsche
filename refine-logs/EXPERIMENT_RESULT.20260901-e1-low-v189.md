# E1 Homogeneous-20 Low V189 Result

V189 is a complete, technically valid **training failure**. It was the final
preregistered adaptive NSESche-only test on the revealed E1610--E1629 tapes.
It ran 20 new NSESche samples, no control or baseline samples, captured no new
tapes, and built 20 state-matched references.

All 20 candidate runs completed on attempt 1 and passed QC. The result-blind
audit passed before the single reveal. There were no quarantines, missing
runs, seed replacements, selective reruns, or post-outcome deletions. All 40
candidate and frozen-control QPR values were finite.

## Preregistered gates

| Metric | V189 candidate | Frozen paper comparator | Same-tape V187 control | Paired candidate-control result | Gate |
| --- | ---: | ---: | ---: | --- | --- |
| Throughput (requests/ms) | 0.96265 | Orion 1.47410 | 1.45185 | mean -0.48920; 0 wins / 0 ties / 20 losses; BCa 95% CI [-0.63096, -0.35390] | Fail |
| QPR, finite-only | 0.02648 | OCS 0.05558 | 0.06355 | mean -0.03707; 3 wins / 0 ties / 17 losses; BCa 95% CI [-0.07192, -0.01823] | Fail |
| QPR, zero-completion-as-zero | 0.02648 | OCS 0.05558 | 0.06355 | mean -0.03707; 3 wins / 0 ties / 17 losses | Fail |

V189 is not near either acceptance boundary. It loses completion throughput to
the frozen same-tape control on every seed and loses QPR on 17 of 20 seeds.
The two-sided paired permutation values are report-only, not gates; their
values are approximately 0.000010 for throughput and 0.00161 for finite-only
QPR.

## Full-cohort post-reveal diagnostic

This diagnostic was not used as a gate. It includes every E1610--E1629 run,
with no seed filtering. Frame and scheduler-window quantities are run-equal
means; cold-start share is the aggregate share among every completed-function
record. All 20,000 V189 scheduler windows reported complete processor-sharing
and readiness-stratified work observations.

| Mechanism observation | V187 same-tape control | V188 clearance | V189 earliest finish |
| --- | ---: | ---: | ---: |
| Mean node CPU utilization | 0.3258 | 0.2369 | 0.2337 |
| Mean starting containers | 32.73 | 34.67 | 35.47 |
| Mean running containers | 128.20 | 133.90 | 135.95 |
| Active-window placement dispersion | 0.7461 | 0.7785 | 0.7709 |
| Mean resident queue | 799.92 | 1098.15 | 1092.33 |
| Mean resident remaining CPU work | 166,432.95 | 232,384.74 | 235,236.79 |
| Mean blocked resident CPU work | 44,007.72 | 71,931.82 | 65,802.66 |
| Mean runnable queue | 553.03 | 685.91 | 709.85 |
| Positive cold-start share | 12.13% | 23.92% | 19.45% |
| Completed-function records | 62,250 | 31,659 | 30,243 |

The V189 correction was locally real: relative to V188, blocked resident CPU
work fell 8.5%, positive cold-start share fell 18.7%, placement dispersion fell
1.0%, and the resident task count fell 0.5%. Those changes did not close the
completion mechanism. Runnable backlog rose 3.5%, resident remaining CPU work
rose 1.2%, starting containers rose 2.3%, CPU utilization fell another 1.3%,
and completed-function records fell 4.5%.

Against the unchanged V187 control, V189 still has 36.6% more resident tasks,
41.3% more resident CPU work, 28.4% more runnable tasks, 60.3% more positive
cold starts, and 28.3% lower CPU utilization. It completes 51.4% fewer function
records. Thus excluding blocked work fixed the specific V188 accounting error,
but a local, one-window earliest-finish order over the unchanged V182 frontier
is not a sufficient system-level controller for warm-container reuse,
placement concentration, runnable-work accumulation, and completion volume.
The evidence does not justify another coefficient or router adjustment on this
axis.

## Disposition

- Retain all 20 V189 candidate rows, all 20 V188 rows, and all frozen V187
  control rows.
- Close the native earliest-executable-finish axis.
- Stop adaptive low-load online search under the current objective pending a
  broader, separately preregistered review of the NSESche objective.
- Do not claim the homogeneous-20 low group is closed.
- Do not advance to middle or high load, or to later paper chapters.
- Do not select, delete, relabel, or replace unfavorable valid seeds.
- This result does not authorize another online experiment.

Evidence root:
`tmp/nse_e1_homogeneous_20node_low_earliest_executable_finish_training_20260901_v189`.
The single-reveal result hash is
`977a2f46279cc96ac83ed1419962f0906989c7e69d32077cae4d14e8fee96693`.
