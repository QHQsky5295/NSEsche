# P5 common-platform pre-result implementation addendum

Date: 2026-09-05 (Asia/Shanghai)

Status: frozen during implementation, before any P5 tape, P5 offline
reference, P5 online result, or P5 duplicate result exists.

## 1. Scope

This addendum closes two implementation details that the P5 preregistration
requires but did not serialize fully. It does not change the active-request
limit, FCFS discipline, arrival loads, seeds, methods, NSESche equations or
parameters, drain rule, metrics, or pass/fail thresholds.

## 2. FaaSRank model binding

P5 includes `sche_FaaSRank`, so its model must be immutable and
training/evaluation-disjoint before the 90 online runs. After the nine P5
tapes are captured and hash-bound, the existing frozen artifact
`runs/tscv1_m1_qual_080a3da_20260902/faasrank.frozen.json` is bound with the
standard `bind_faasrank_model` verifier. The verifier must prove that its
training-tape hash is absent from all nine P5 evaluation-tape hashes.

The model is reused without retraining, candidate reselection, or coefficient
change. Its binding is a prerequisite for reference construction and online
execution. This adds one input-integrity step between tape capture and the 90
method-state reference builds; it adds no online observation.

The only legal staged binding states are:

1. zero-result: tapes=false, FaaSRank=false, references=false;
2. tape-bound: tapes=true, FaaSRank=false, references=false;
3. model-bound: tapes=true, FaaSRank=true, references=false;
4. ready: tapes=true, FaaSRank=true, references=true.

Online execution and analysis require state 4.

## 3. Determinism semantic hashes

The preregistered `P5P01-low-sche_nash` duplicate uses the identical run spec,
tape, reference, source, binary, and configuration. Four timing-free semantic
hashes must match exactly:

- workload: ordered `(tape_sequence, arrival_frame, request_id, DAG_id)`;
- command: ordered per-window policy decision objects;
- terminal count: final frame and arrival/admission/waiting/active/completed/
  censored counts;
- scientific result: throughput, completion/censoring, end-to-end latency,
  simulator cost, QPR, and admission-queue measurements.

Wall-clock and thread-CPU scheduler timing are excluded because they measure
host execution overhead, not simulator determinism. The duplicate remains a
non-observational audit and cannot replace the canonical run.

## 4. QC and analyzer boundary

QC must recompute FCFS order, frame-by-frame conservation, next-frame refill,
capacity, dynamic terminal timing, throughput, clearance throughput, and QPR
before emitting the semantic hashes. The P5 analyzer evaluates conditions
1--11 before constructing its relative-method appendix. Relative throughput,
QPR, rank, and old-PDF drift are absent from every pass/fail condition.

## 5. Authorization

This addendum authorizes only the missing model-binding and semantic-hash
implementation within P5 stage 1. Tape capture remains blocked until the
source, tests, release binary, analyzer, this addendum, and zero-result
manifest are committed and hash-bound.
