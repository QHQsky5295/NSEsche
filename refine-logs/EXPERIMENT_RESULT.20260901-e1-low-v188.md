# E1 Homogeneous-20 Low V188 Result

V188 is a complete, technically valid **training failure**. It tested one
baseline-independent NSESche intervention on the frozen V187 E1610--E1629
tapes. It ran 20 new NSESche samples, no control or baseline samples, captured
no new tapes, and built 20 state-matched references.

All 20 candidate runs completed on attempt 1 and passed QC. The result-blind
audit passed before the only reveal. There were no quarantines, missing runs,
seed replacements, selective reruns, or post-outcome deletions.

## Preregistered gates

| Metric | V188 candidate | Frozen paper comparator | Same-tape V187 control | Paired candidate-control result | Gate |
| --- | ---: | ---: | ---: | --- | --- |
| Throughput (requests/ms) | 0.99425 | Orion 1.47410 | 1.45185 | mean -0.45760; 0 wins / 0 ties / 20 losses; BCa 95% CI [-0.59710, -0.33509] | Fail |
| QPR, finite-only | 0.02650 | OCS 0.05558 | 0.06355 | mean -0.03705; 2 wins / 18 losses; BCa 95% CI [-0.07187, -0.01820] | Fail |
| QPR, zero-completion-as-zero | 0.02650 | OCS 0.05558 | 0.06355 | mean -0.03705; 2 wins / 18 losses | Fail |

The intervention is not close to the acceptance boundary. It loses completion
throughput to the frozen control on every seed and loses QPR on 18 of 20 seeds.
This is scientific evidence against the CPU-clearance-majority native service
ranking, not a simulator or protocol failure.

## Post-reveal mechanism diagnostic

This diagnostic was not used as a gate. Across all 20 same-tape pairs, V188
increased mean placement dispersion from 0.746 to 0.778 and mean starting
containers from 32.7 to 34.7. Among completed-function records, the share with
a positive cold-start interval increased from 12.1% to 23.9%. At the same time,
mean node CPU utilization fell from 0.326 to 0.237, while the mean resident
queue grew from 800 to 1,098 tasks and resident remaining CPU work grew from
166,433 to 232,385 simulator work units.

The cause is structural: V188's clearance proxy counted blocked resident work
as if it delayed the current runnable task. It therefore avoided warm nodes,
created more cold placements, and left CPU capacity less effectively utilized.
The next native hypothesis must model earliest executable finish: runnable work
only, plus the maximum (not the sum) of container-ready and parent-data-ready
delays. This is a result-aware hypothesis and requires a new sealed plan before
any online run.

## Disposition

- Retain all 20 V188 candidate rows and all 20 frozen V187 control rows.
- Close the native clearance/response axis.
- Do not claim the homogeneous-20 low group is closed.
- Do not advance to middle or high load.
- Do not use favorable-seed selection, deletion, relabeling, or replacement.
- Before another online run, diagnose the completion loss and preregister no
  more than one new NSESche-only intervention on the retained tapes.

Evidence root:
`tmp/nse_e1_homogeneous_20node_low_native_clearance_response_training_20260901_v188`.
The single reveal result hash is
`da82d8f581c082f9ddb7ab6b46161b486cf5aff2d754ef30ef8d586020f5bdcc`.
