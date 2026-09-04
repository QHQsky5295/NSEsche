# G10 Work-Conserving Development Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Analyzer/selection commit: `4283957`

Status: `complete_g10_development_gate_failed_strong_baselines_blocked`

## 1. Complete retained population

The one authorized result-blind invocation executed all 45 frozen C0/C1/C2 x
low/middle/high x D96--D100 specifications in manifest order. All 45 runs
canonicalized on attempt 1. There were no technical retries, seed replacements,
run omissions, or result-conditioned extensions. Reconciliation found all 45
paths exact and performed zero repairs.

Independent validation reopened every canonical directory against the bound
manifest. All 45 runs are QC-valid, have positive fixed-window completion, and
have defined run-level QPR. The 675-file canonical online tree contains
44,085,210 bytes and has sorted inventory hash
`ed066974a43d804fe492fa9180aaa4e238131d708cb380a6f4be28e216dd997e`.
The partial tree contains zero files.

The append-only online ledger contains 92 valid chained events, has final
event hash `f0627d4b73d7ac83dd3612a19802e2bb6216b7452fcf5bfca03203b5ddb112f6`,
and file SHA-256
`8743f14e29e34408ad050d4fa4988b2df00c1dc586e17d38ac7254e01298bf66`.
The reconciliation report has canonical document hash
`c6fa10d03a5a14f94cfe60fb56b7ef11c5df2103ab1e4124e785e0396cc43cda`
and file SHA-256
`c629b862f1d9de2ac397fdf94b8a4d15292a81afa4d4a46e3faba668a7d82a45`.

## 2. Frozen gate outcome

The frozen analyzer returned
`complete_g10_development_gate_failed` and selected no candidate. Its complete
3,080,309-byte report has canonical document hash
`68fbd5efe081dcbef7669e8fde2f4c5c7fa5ea2f662d39554be83e6261351579`
and file SHA-256
`e0581b60b64382d886e219ab4b73d8f36c33f1dce5723c1f27da8607ae3a0870`.
An independent second implementation recomputed throughput, latency, cost,
QPR, and all six candidate/control mean ratios directly from the 45 canonical
summary files and matched the frozen report.

### C1: `ready_remaining_work`

| Load | Throughput mean | C1/C0 | QPR mean | C1/C0 | Paired wins T/QPR/joint |
|---|---:|---:|---:|---:|---:|
| low | 1.6154 req/ms | 1.00087 | 0.0617523 | 0.97719 | 2/3/2 |
| middle | 1.1822 req/ms | 1.00613 | 0.0508908 | 1.00712 | 3/4/3 |
| high | 0.8520 req/ms | 1.02651 | 0.00811131 | 1.04501 | 2/2/1 |

C1 passes population, completion/latency, activation, and overhead conditions
(1, 6, 7, and 9). It fails the dual-mean, paired-win, 0.80 per-seed floor,
leave-one-seed-out, and frozen integrity conditions (2, 3, 4, 5, and 8).
The floor failure is middle D100: throughput/C0 is 0.77914 and QPR/C0 is
0.59147. Its minimum leave-one-seed-out primary mean difference is -0.0245.

Despite failing the gate, C1's directional completion/latency pattern is
retained: its mean completion ratio is above C0 and its mean request latency
is below C0 at all three loads. Placement-policy wall-time ratios are 0.9708,
1.0165, and 1.2353 at low, middle, and high, all below the frozen 1.50 cap.

### C2: `ready_remaining_work_bounded_frontier`

| Load | Throughput mean | C2/C0 | QPR mean | C2/C0 | Paired wins T/QPR/joint |
|---|---:|---:|---:|---:|---:|
| low | 1.5880 req/ms | 0.98389 | 0.0634785 | 1.00450 | 3/3/2 |
| middle | 1.1672 req/ms | 0.99336 | 0.0527735 | 1.04437 | 2/2/2 |
| high | 1.0242 req/ms | 1.23398 | 0.0123924 | 1.59656 | 3/3/3 |

C2 passes population, activation, and overhead conditions (1, 7, and 9). It
fails the dual-mean, paired-win, 0.80 floor, leave-one-out, completion/latency,
and frozen integrity conditions (2--6 and 8). The floor failure is middle D96:
throughput/C0 is 0.70370 and QPR/C0 is 0.35592. Its minimum leave-one-seed-out
primary mean difference is -0.0350.

The frontier is genuinely exercised in 5/5 seeds at every load, and all
ready-omission, global-bound, one-hop, and dispatch-class violation counts are
zero. C2's benefit is therefore real but regime- and seed-sensitive: high-load
mean throughput and QPR rise strongly, while low/middle throughput means fall
and low/middle completion/latency safety does not pass. High D100 is an
especially favorable but retained observation (throughput/C0 2.2364,
QPR/C0 9.3763); the leave-one-out gate prevents that run from qualifying the
mechanism by dominating an arithmetic mean.

Placement-policy wall-time ratios are 1.2744, 1.3466, and 1.3890, all below
the 1.50 cap. The maximum numerical error in the per-run identity
`QPR ratio = throughput ratio / (latency ratio * cost ratio)` is
`2.22e-16`.

## 3. Runtime-integrity qualification

C1 records 14,685/14,685 strict-PNE and offline-reference active windows. C2
records 14,678/14,678. C0 records 14,681 strict-PNE windows and 14,680
offline-reference windows among 14,682 active windows. The two retained C0
exceptions are:

- low D100, frame 906: 26 assigned players, four inner rounds, nine moves,
  `inner_limit_hit=true`; no reference is requested for the unstable state;
- high D96, frame 997: a stable assignment whose bound offline reference is
  negative, producing the explicit `offline_table_nonpositive` state and
  `social_reference_invalid` termination.

The negative reference is the same valid row retained and disclosed in the
offline-reference audit. Neither exception is a technical retry condition.

The frozen analyzer also reports all 15 C0 runs as failed because it requires
`unfinished_functions_min/max` whenever ready players exist. Those two fields
are intentionally `null` for C0 because remaining-work ordering is disabled;
C0 nevertheless records exact ready candidate/admission counts, zero omission,
and a ready-set hash. This is a conservative non-applicable-field false
positive discovered only after exposure. The analyzer and its report remain
unchanged. Removing only that false positive would not change qualification:
the two genuine C0 exceptions still fail condition 8, and both candidates
independently fail multiple performance and robustness conditions.

## 4. Evidence-bounded interpretation

**Observation.** Remaining-work order alone gives small positive mean
throughput/QPR changes at middle and high load and improves mean completion and
latency at every load, but the paired signs and one middle-load tail are not
robust. The bounded frontier activates correctly and yields a large high-load
gain, but it trades away low/middle throughput and has one severe middle-load
tail.

**Interpretation.** The data support the intended work-conserving diagnosis of
G9, but they do not support either G10 rule as one global mechanism. The
frontier is useful only in a subset of high-pressure states, while applying it
unconditionally can create completion/cost/latency regressions. This is an
inference from a five-seed development bank, not a paper claim.

**Implication.** Neither C1 nor C2 may be compared with strong baselines,
confirmed, replayed on Q61--Q80, or used in a figure. D96--D100 are exhausted
development evidence and cannot be rerun, filtered, or reused to validate a
successor.

**Next step.** A read-only state-regime diagnosis may use all retained G10
traces to define at most one globally state-conditioned, work-conserving
successor before any fresh D101+ input exists. Any successor must use no load
label or seed branch, preserve C0 ready work, expose its switching/activation
telemetry, and be evaluated on a new preregistered seed bank. No new online
sampling is authorized by this result.

## 5. Immutable archive

The complete G10 run root was copied without deletion to:

`E:\NSEsche_experiment_archives\tscv1_g10_work_conserving_d96_d100_ab0ae94_20260904`

Source and archive inventories match exactly: 1,527 files, 566,678,494 bytes,
and sorted inventory hash
`aed84ef942171c77d6ed340b9f2cfabb062a0b57b09b8cf02111443499704ff9`.
The C-drive source remains intact.

## 6. Authorization boundary

- `g10_candidate_selected=false`;
- `g10_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_successor_diagnosis_authorized=true`.
