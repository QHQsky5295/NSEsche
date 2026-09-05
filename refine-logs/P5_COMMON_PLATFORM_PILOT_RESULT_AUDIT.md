# P5 common-platform pilot result audit

Date: 2026-09-05 (Asia/Shanghai)

Status: `complete_p5_common_platform_failed_formal_sampling_blocked`

## Complete retained population

All 90 preregistered online runs completed and were independently reopened
against the ready manifest: ten methods by three loads by `P5P01--P5P03`.
Low/P5P01/greedy retains two historical quarantined attempts caused solely by
the versioned QC-label mismatch and one audited canonical attempt 3. The other
89 rows canonicalized on attempt 1. No valid observation, seed, method, load,
or unfavorable result was deleted or replaced.

The predeclared low/P5P01/NSESche duplicate also completed. The reporting-only
action-semantic correction is separately audited in
`P5_POLICY_ACTION_SEMANTIC_HASH_CORRECTION_AUDIT.md`; it changes no simulator
output.

Evidence root:
`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905`.

Runtime source commit: `2cbeb9ac02da55d200a757c1ba8841087d677487`.
Runtime binary SHA-256:
`945e0deca86466f9ef322bba25c779f5240d45d7e376c740ed54d240688262d8`.

## Frozen gate outcome

Eleven of twelve conditions pass:

- population/identity, shared arrivals, conservation, FCFS, capacity, timing,
  metric identity, traffic interpretation, reference/NSESche integrity,
  corrected action determinism, and result-blindness pass;
- usable cohort fails.

The usable-cohort gate required at least one fixed-window completion and a
terminal completion ratio of at least 0.95 in every run. Fifty-six of 90 runs
fall below 0.95: 10 low, 26 middle, and 20 high. Every one of the ten methods
has four to six affected runs. This is a common protocol failure, not a
method-specific technical failure. Formal preregistration and formal sampling
remain blocked.

The nine workload tapes also show that request rate alone did not define
separated load strata:

| Load/seed | Measured req/s | Static CPU work rate/s | `rho_ideal` |
|---|---:|---:|---:|
| low/P5P01 | 1,948 | 1,889,768.9 | 0.6299 |
| low/P5P02 | 1,931 | 843,535.4 | 0.2812 |
| low/P5P03 | 1,880 | 859,601.7 | 0.2865 |
| middle/P5P01 | 2,543 | 1,549,223.2 | 0.5164 |
| middle/P5P02 | 2,532 | 7,485,853.5 | 2.4953 |
| middle/P5P03 | 2,481 | 1,912,310.8 | 0.6374 |
| high/P5P01 | 7,178 | 12,871,068.5 | 4.2904 |
| high/P5P02 | 6,996 | 11,687,102.3 | 3.8957 |
| high/P5P03 | 7,019 | 4,649,997.1 | 1.5500 |

The fixed four-times-static-work drain bound is therefore not a valid
method-neutral guarantee for these heterogeneous DAG mixes.

## Relative outcomes are diagnostic only

Relative outcomes were unsealed only after conditions 1--11 were decided and
were excluded from the P5 pass/fail decision. They nevertheless show that the
current NSESche runtime is not ready for formal comparison:

| Load | NSESche throughput (req/ms) | Rank | Best throughput | NSESche QPR | Rank | Best QPR |
|---|---:|---:|---:|---:|---:|---:|
| low | 0.432333 | 10 | OCS 1.514667 | 0.000792315 | 8 | Load Least 0.011212431 |
| middle | 0.360000 | 8 | Load Least 0.744000 | 0.000210658 | 7 | Load Least 0.002188122 |
| high | 0.186000 | 7 | FaaSRank 0.313667 | 0.000045824 | 10 | Load Least 0.000723568 |

These three-seed means are neither paper results nor a basis for deleting or
replacing P5 seeds.

## Source-level diagnosis

The inner/outer solver and dispatch path are not the immediate bottleneck.
There are no inner/outer-limit or oscillation signatures explaining the gap,
and selected players are dispatched completely with no invalid assignment or
failed channel. Instead, NSESche sees few feasible players per window, many
`waiting_for_candidate_nodes` events, low CPU utilization, and concentrated
co-location.

All policies use the shared `placement_candidate_ids` hard-feasibility helper,
but they do not use one common player-eligibility rule:

- current P5 NSESche `ready_order` and FaaSRank require every parent function
  to be complete (`PreAllDone`);
- OCS admits a child after every parent has a placement (`PreAllSched`); and
- Greedy, Random, Hash, Load Least, Hiku, Jiagu, and Orion call `All`, with the
  shared path-feasibility check effectively delaying a child until parent
  placement exists.

The paper defines `F` as the function requests to schedule in a window and
does not state that parents must finish before a child may receive a placement.
The execution layer still must prevent child execution before dependency
completion. Thus the present comparison contains a platform-level eligibility
difference that must be removed before R2-6 fairness can be claimed.

This finding does not revive G6. G6 gave only NSESche parent-scheduled
lookahead under the old mixed-policy platform and failed its five-seed gate.
The only scientifically distinct successor is a central, method-neutral
eligibility and batching contract applied to all policies, followed by fresh
protocol validation.

## Decision and authorization boundary

- P5 is complete, failed, immutable diagnostic evidence.
- P5 data cannot enter a final main figure or be mixed with a corrected
  platform.
- Homogeneous formal low/middle/high, parameter, ablation, heterogeneous,
  scaling, burst, QoS, pricing/welfare, and paper-result tasks remain blocked.
- The only permitted next stage is read-only P6 derivation and a zero-result
  preregistration for common eligibility, workload-load calibration, and a
  valid drain contract.
- No P6 tape, reference, binary, online run, or candidate selection is
  authorized by this audit.
