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
