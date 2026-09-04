# P4 startup-aware queue-pressure result audit

Date: 2026-09-05  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `dc242339790e97ef6f472edd865265adb50c75ef`  
Online-selection prerequisite: `16e5a772d07794e74f82fe0ce6d24babdd07d5f7`  
Status: complete P4 gate failed; startup-aware queue-pressure family closed

## Outcome

The frozen D126--D130 product executed exactly once in seed-major,
`execution_ready`-then-`startup_aware` order. All ten first attempts passed QC
and were retained. The preregistered analyzer returned
`complete_p4_startup_aware_failed_family_closed` with no selected candidate.

The candidate improved arithmetic-mean throughput by 4.396%, QPR by 2.243%,
completion ratio by 4.442%, and drained latency by 7.902%. It nevertheless
failed the fixed QPR mean threshold, the paired robustness condition, and both
leave-one-seed-out stability requirements. Only two of five seeds were joint
wins or joint nonlosses. Omitting D127 makes both primary mean differences
negative. The result therefore does not support a stable candidate effect.

No seed was removed, replaced, extended, or rerun; no threshold was relaxed;
and no result-conditioned configuration was evaluated. Under the frozen
stopping rule, `execution_ready` remains the default and this mechanism family
is closed.

## Frozen result product

Run root:
`runs/tscv1_p4_startup_aware_queue_d126_d130_dc24233_20260905`

| Artifact | Value |
|---|---|
| release binary SHA-256 | `d59efe5d40a9ee1a565fa9d37e7533863af28e52eafc3f328d87af7ec433664a` |
| ready-manifest file SHA-256 | `835625463b598fbd4fb24242d3779013c80505bd2fa5f17478a773924a5d676a` |
| ready-manifest canonical hash | `c3db56e4ad4cd891e02b809686575942f1f896bb07f32901b442f601ab700d08` |
| selection file SHA-256 | `f3358b0d1162b72aaf2bb89e355dab28d6cfb43437e4d1448c8c0f5556880e6c` |
| selection canonical hash | `7c32c41af9fcf909c044f699d725d7221900ea2a82daadcb56fb0fcb645d0483` |
| analyzer SHA-256 | `dfde692cd303a2af4a6b30efd6a0516500aebe15178d748f1e91b447380e9aa5` |
| gate-report file SHA-256 | `fbd288a040de4a52982068199419f59836b410d0aa60f5e7e89ed8146de48906` |
| gate-report canonical hash | `1354f63dc13186f966d6dfc127a40c8f84944ee173114647734a54161b44083b` |
| canonical online tree | 150 files; 9,478,722 bytes |
| canonical online inventory hash | `24c1213e99f7dba2fca7aeecf83c0dc6ec4cae4afff49d60a6b5906f98d9979` |
| online ledger | 22 events; 20,195 bytes |
| online ledger file SHA-256 | `0dd7930db02342ecda567c08f0e618aa8e37d3647990359248b5da773d0fe4f7` |
| online ledger tip | `8013ee3196c7987e1d2b6650bc7f679b5cfaa3b8ae5465be3e6b6e72277f40df` |
| retained attempts | 10/10 attempt 1 |
| partial/quarantine files | 0/0 |
| summed attempt duration | 114.078 s |

The 22-event ledger is exactly one batch start, ten ordered
attempt-start/canonicalization pairs, and one batch finish. Every canonical
directory passes `validate_canonical_run`; source, binary, configuration,
tape, reference, and seed identities match the frozen selection.

## Per-seed retained results

| Seed | Control T | Candidate T | T ratio | Control QPR | Candidate QPR | QPR ratio | Joint result |
|---|---:|---:|---:|---:|---:|---:|---|
| D126 | 1.829 | 1.829 | 1.000000 | 0.221091 | 0.215505 | 0.974736 | loss |
| D127 | 1.493 | 1.859 | 1.245144 | 0.039848 | 0.053405 | 1.340230 | win |
| D128 | 1.929 | 1.922 | 0.996371 | 0.143656 | 0.142898 | 0.994726 | loss |
| D129 | 1.846 | 1.677 | 0.908451 | 0.043341 | 0.041643 | 0.960836 | loss |
| D130 | 0.774 | 0.930 | 1.201550 | 0.006620 | 0.011300 | 1.707021 | win |

The table reports the exact run-level values used by the gate report, rounded
only for display. Gate evaluation uses the unrounded retained values. The
independently recomputed mean values are:

| Metric | Control mean | Candidate mean | Candidate/control |
|---|---:|---:|---:|
| throughput (requests/ms) | 1.574200 | 1.643400 | 1.043958836 |
| QPR | 0.090911031 | 0.092950427 | 1.022432874 |
| completion ratio | 0.816977 | 0.853270 | 1.044423197 |
| drained latency (ms) | 81.733799 | 75.275589 | 0.920984824 |
| cost/completed request | 0.462509 | 0.434425 | 0.939280529 |
| placement-policy wall time | 306004.56 | 303310.50 | 0.991196014 |

## Ten-condition decision

| Condition | Result | Evidence |
|---|---|---|
| 1. population and identity | pass | exact frozen ten-run product; no extra/replacement run |
| 2. formula/method boundary | pass | only declared Eq. (6) operational queue slice differs |
| 3. mechanism activation | pass | positive startup backlog and assignment change in 5/5 seeds |
| 4. viable dual mean effect | **fail** | throughput ratio 1.04396 passes; QPR ratio 1.02243 is below 1.11 |
| 5. paired robustness | **fail** | 2/5 joint wins and 2/5 joint nonlosses, below 3/5 and 4/5 |
| 6. per-seed safety | pass | every per-seed throughput and QPR ratio is at least 0.80 |
| 7. leave-one-out stability | **fail** | 4/5 nonnegative and 4/5 positive for each metric; all five required nonnegative |
| 8. completion and latency | pass | completion improves; latency ratio 0.92098 is below 1.05 |
| 9. runtime/reference integrity | pass | all canonical validators and reference requirements pass |
| 10. overhead | pass | wall-time ratio 0.99120 is below 1.50 |

Candidate active-window startup shares were 0.3381, 0.8760, 0.4293,
0.3895, and 0.4904 for D126--D130. Candidate/control final-assignment hashes
differed in 963/989, 850/976, 902/978, 952/990, and 907/988 aligned active
windows. P4 therefore changed decisions strongly; dormancy cannot explain the
failed outcome.

Every leave-one-seed-out primary difference is recomputed in the gate report.
Four of five are nonnegative and positive for each metric. When D127 is
omitted, the throughput mean difference is -0.005 requests/ms and the QPR
mean difference is -0.000840. This is the decisive sensitivity that prevents
promotion despite favorable full-sample means.

## Independent result audit

A read-only independent checker reloaded all ten raw summaries and reproduced
the report values exactly for throughput, QPR, completion ratio, latency,
cost, and wall time. Calling the frozen `evaluate_gate` on the retained
`run_metrics` reproduced the stored gate object exactly. It also revalidated
all canonical runs, the full online-tree inventory, ledger chain and order,
selection, ready-manifest, runtime hash, and the absence of partial or
quarantine files.

Two preliminary read-only checker invocations failed before reaching a result:

1. the first treated `validate_canonical_run`'s dictionary return value as an
   object and raised an attribute error; and
2. the second had already reproduced raw metrics, gates, and tree inventory,
   but its wrapper looked for identity fields at the manifest root instead of
   under `manifest.run` and required an empty quarantine directory rather than
   accepting zero quarantine files.

The wrapper was corrected to the documented return and manifest shapes and to
the protocol's file-count invariant. The final invocation passed. None of
these read-only checker corrections changed, reran, selected, or deleted an
experiment observation.

## Interpretation and stopping boundary

Startup-aware queue pressure is active and often beneficial, especially for
completion and latency, but it is not robust enough across the fixed seed bank
and does not meet the preregistered QPR effect size. It cannot be described as
a validated improvement, used to replace the paper algorithm, or used to
justify a stronger performance claim.

Per the frozen stopping rule:

- select no P4 candidate and retain `execution_ready`;
- close the startup-aware queue-pressure family without coefficient tuning,
  partial-category variants, extra seeds, or substituted warm preferences;
- do not launch P4 baseline compatibility, formal confirmation, later-load,
  figure, or manuscript-claim stages; and
- retain the complete negative product as internal provenance.

The next legitimate action is a result-faithful resubmission-plan reassessment
using the already retained P1 reviewer evidence and formal homogeneous-low
comparison. It is not another adaptive use of D126--D130.
