# P5 common-platform protocol preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: frozen before implementation and before any P5 tape, offline
reference, or online result exists.

## 1. Objective

Validate one final method-neutral experiment platform before restarting the
paper's ten-method comparison at homogeneous-20 low. P5 is a protocol pilot,
not an NSESche selection experiment. Relative throughput, QPR, or rank cannot
change its pass/fail decision or any frozen capacity/timing value.

The derivation in `P5_COMMON_PLATFORM_PROTOCOL_DERIVATION.md` is normative.
P5 leaves the paper equations and all placement methods unchanged.

## 2. Frozen pilot population

| Dimension | Frozen value |
|---|---|
| Pilot seeds | `P5P01`, `P5P02`, `P5P03` |
| Cluster | homogeneous, 20 nodes |
| Loads | low, middle, high |
| Methods | greedy, random, hash, load_least, sche_FaaSRank, sche_OCS, sche_Hiku, sche_jiagu, sche_orion, sche_nash |
| Online population | `3 seeds x 3 loads x 10 methods = 90` |
| Arrival/observation | 1,000 frames, 1 ms/frame |
| Active request rule | `max(1,sum floor(max(0,node_mem-3500)/300))`; expected 100 |
| Queue discipline | strict FCFS `(arrival_frame,tape_sequence)` |
| Drain | early stop when waiting and active are empty; hard bound derived per tape by the frozen `4W/C + L_static` rule |
| HPA | one common frozen HPA for all methods |
| NSESche | `ready_order`; low `(r0=0.6,wq=0.5)`, middle/high `(0.5,0.6)` |

The three strings are new and disjoint from Q61--Q80, D01--D130, E01--E20,
and every prior formal/development bank. No alternative pilot seed may be
added if a valid outcome is unfavorable.

Each `(load,seed)` has one captured tape shared byte-for-byte by all methods.
Same-frame event order is part of the tape identity. The 90 method-state
offline references are built and hash-bound before any online run so reference
build/replay covers the new active-state semantics. Reference builds and nine
tape captures are input-construction stages and are not online pilot outcomes.

## 3. Frozen implementation contract

1. Every tape event creates exactly one external request with immutable
   arrival frame, tape sequence, request id, and DAG id.
2. New external requests append to one FIFO; only its head may be admitted.
3. Admission repeats until the FIFO is empty or the active count equals the
   derived limit. No per-method callback participates.
4. Active count never exceeds the limit. Completion is the only way a slot
   becomes free; a released slot is reusable on the next frame.
5. Admission wait is `admission_frame-arrival_frame` and is included in
   request latency. Waiting requests are included in arrival conservation,
   final censoring, and queue telemetry.
6. No arrival is dropped, rejected, timed out, reordered, or converted to a
   different DAG. The hard drain deadline censors unfinished requests.
7. The fixed observation throughput, drained latency/cost, clearance
   throughput, and QPR fields follow the derivation exactly.
8. Early stop cannot occur before the 1,000-frame arrival phase. All methods
   sharing a tape record the same hard deadline even if they stop earlier.
9. `environment.json`, run config, manifest, QC, and summary expose all rule
   inputs, derived values, terminal reason, and conservation counts.
10. Formal validation rejects admission-enabled generated/capture performance
    runs; online performance and reference replay require an immutable replay
    tape.

## 4. Pre-result verification

Before any P5 tape capture, the implementation stage must freeze a source
commit, one release binary hash, schema, matrix builder, QC, analyzer, and
zero-result 90-run manifest. Required tests include:

- FIFO ordering under same-frame and cross-frame arrivals;
- fill-to-cap, no-over-cap, and next-frame refill after completion;
- exact 20/100/500 homogeneous limits of 100/500/2,500;
- heterogeneous capacity summation and nonpositive usable-memory handling;
- arrival/admission/active/completed/censored conservation at every frame;
- admission wait included exactly once in latency;
- early drained termination and hard-deadline censoring;
- static tape work, path allowance, and drain-bound recomputation;
- weak-scaling invariance of both active limit and `W_tape/C`;
- QPR identity and undefined-value fail-closed behavior;
- unchanged outputs with admission disabled for historical unit fixtures;
- NSESche equation/strict-response/reference/determinism regression tests;
- common HPA and one-binary identity across all ten methods.

No test may assert a favorable NSESche performance value.

## 5. Staged authorization

P5 must proceed in this order, with a committed audit between stages:

1. implementation, tests, release binary, analyzer, and zero-result manifest;
2. exactly nine `P5P01--P5P03 x low/middle/high` base-tape captures;
3. exactly 90 method-state offline-reference builds;
4. one result-blind freeze of the exact 90 online run list;
5. exactly 90 online runs, retaining the first QC-valid observation;
6. one complete protocol-pilot analysis and decision.

A technical retry is allowed only for crash, panic, OOM, I/O/truncation,
timeout, hash/config/tape/reference mismatch, or a structural invariant
failure. It must reuse the same seed, tape, config, source, and binary, and the
failed attempt remains in the ledger. Zero completion, low completion,
unfavorable rank, or old-PDF drift is not a technical retry reason.

## 6. Pilot gate

P5 passes only if all conditions below hold over the exact 90-run population:

1. **Population and identity**: 90 unique first-QC-valid runs, one source and
   binary, nine tapes, one tape shared within each `(load,seed)`, exact common
   HPA/admission/phase fields, and 90 matching reference identities.
2. **Arrival identity**: each summary arrival count and ordered arrival hash
   equals its tape; all ten methods in a pair have identical arrival frames,
   order, DAG ids, `W_tape`, `C`, `L_static`, and hard deadline.
3. **Conservation**: frame and final conservation identities hold exactly;
   `censored=waiting+active=arrivals-completed`; drop/reject/timeout remain zero.
4. **FCFS**: admitted sequence is a prefix of external arrival sequence at
   every frame; no later request is admitted while an earlier request waits.
5. **Capacity**: derived active limit is 100 and no frame exceeds it; whenever
   the FIFO is nonempty and active count is below 100 at the admission boundary,
   the next request is admitted.
6. **Timing**: no arrival occurs at or after frame 1,000; no early stop occurs
   before it; terminal reason is exactly `cohort_drained` or
   `hard_drain_deadline`; all reported durations recompute from frames.
7. **Metric identity**: paper throughput, clearance throughput, end-to-end
   latency, cost/completion, completion/censoring, and run-level QPR recompute
   from event streams with absolute error at most `1e-9` (or exact integer
   equality for counts).
8. **Usable cohort**: every run has at least one completion by the fixed
   observation horizon and at least 95% terminal cohort completion. This gate
   is method-agnostic and does not compare ranks.
9. **Traffic interpretation**: for each load, the nine tapes' measured request
   rate, per-frame p50/p95/p99/max arrivals, static work rate, and
   `rho_ideal` are reported separately; labels remain low/middle/high and no
   tape is selected or rejected by a method result.
10. **Reference and NSESche integrity**: reference hit/missing/nonpositive
    counts reconcile, state/assignment identities match build and replay, and
    all NSESche equation, strict Eq. (15), convergence, and determinism audits
    pass without changing scheduling commands for other methods.
11. **Reproducibility**: one predeclared duplicate replay for
    `P5P01-low-sche_nash` reproduces workload, command, terminal-count, and
    result hashes exactly. This duplicate is a determinism check, not an
    additional observation and cannot replace the canonical run.
12. **Result blindness**: the protocol analyzer reports relative method
    outcomes only in a sealed appendix after conditions 1--11 are decided;
    no pass condition mentions NSESche rank, throughput margin, QPR margin, or
    old-PDF alignment.

All conditions are conjunctive. Failure retains the complete pilot and stops
before formal sampling. A correction may change only a demonstrably invalid
common protocol field and must be separately preregistered on three new pilot
seeds; it cannot tune the cap, drain, load, or method based on relative results.

## 7. Formal transition if P5 passes

Passing P5 authorizes a separate final-runtime freeze and result-blind formal
preregistration. It does not itself authorize reuse of the pilot in paper
means. The paper comparison then restarts exactly as:

1. homogeneous-20 low, all ten methods, 20 paired formal seeds;
2. homogeneous-20 middle only after low closes;
3. homogeneous-20 high only after middle closes.

Old-protocol Q61--Q80 baseline and NSESche results remain diagnostic provenance
and cannot be mixed with P5 results. Old-PDF alignment is reported after each
complete new scene but never determines retention.

## 8. Current authorization

After this preregistration is committed, only stage 1 implementation and
pre-result verification are authorized. Tape capture, reference construction,
online pilot runs, formal runs, figures, and paper claims remain blocked.
