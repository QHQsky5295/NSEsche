# P4 Startup-Aware Queue-Pressure Experiment Plan

Plan version: `P4-0`

Date: 2026-09-05 (Asia/Shanghai)

Protocol: `TSCv1-P4-startup-aware-queue`

Status: `fixed_zero_result_implementation_only`

## Decision objective

Determine whether the only P4 candidate, `startup_aware`, is sufficiently
active, safe, robust, and beneficial in homogeneous-20 low load to justify a
separate baseline-compatibility experiment. The estimands are the paired
candidate-minus-control effects and candidate/control ratios for throughput
and frozen run-level QPR.

The candidate changes only Eq. (6)'s queue observation from
`pending+runnable` to `pending+runnable+starting_resident`. It does not change
displayed Eqs. (1)--(20), strict Eq. (15), the action set, player order, common
HPA, workload, or metric definitions.

## Experimental design

| Item | Fixed value |
|---|---|
| Topology/load | homogeneous, 20 nodes, low |
| Method | NSESche `ready_order` only |
| Parameters | `r0=0.60`, `wq=0.50`, all other TSCv1 defaults |
| Control | `execution_ready`: `pending+runnable` |
| Candidate | `startup_aware`: `pending+runnable+starting_resident` |
| Seeds | D126, D127, D128, D129, D130 |
| Pairing | one immutable tape shared by both settings within seed |
| Online runs | exactly 10 |
| Offline references | exactly 10, semantics-specific |
| Execution order | seed-major; control then candidate |
| Primary metrics | throughput in req/ms; frozen run-level QPR |
| Safety metrics | completion, drained latency, cost/completion, runtime integrity, overhead |
| Statistical unit | one complete paired seed run |

This five-pair screen is a bounded development decision, not confirmatory
inference. It reports raw pairs, mean, sample SD, descriptive 95% t interval,
signs, joint wins/nonlosses, and all leave-one-seed-out means. No development
row is paper-eligible.

## Fixed stage order and stopping points

| Stage | Work | New simulator outputs | Exit requirement |
|---|---|---:|---|
| P4.0 | Derivation, preregistration, plan | 0 | Documents committed before code/result |
| P4.1 | Queue-semantics implementation and tests | 0 | Source boundary and default compatibility pass |
| P4.2 | Protocol, validator, analyzer, frozen binary and result-free manifest | 0 | Hash-bound zero-result audit committed |
| P4.3 | Capture D126--D130 tapes | 5 tapes | Exact input audit committed |
| P4.4 | Build semantics-specific references | 10 builds | Reference identity/coverage audit committed |
| P4.5 | Freeze result-blind ten-run selection | 0 | Analyzer/selection audit committed |
| P4.6 | Execute the fixed online population once | 10 runs | All first QC-valid rows retained |
| P4.7 | Invoke the frozen gate once | 0 | Pass selects candidate; any failure closes family |

No stage may begin before the preceding audit commit. A technical failure may
retry only the identical spec and must be disclosed. A valid unfavorable
observation is never retried, omitted, or replaced.

## Frozen success gate

`startup_aware` passes only when all ten preregistered conditions pass:
complete identity, formula/method boundary, mechanism activation, throughput
ratio `>=1.015`, QPR ratio `>=1.11`, paired joint robustness, per-seed primary
floors `>=0.80`, nonnegative leave-one-out stability with four strict positive
values per metric, noninferior completion with latency ratio `<=1.05`, complete
runtime/reference integrity, and policy wall-time ratio `<=1.50`.

Activation additionally requires positive startup backlog in at least 10% of
active candidate windows in at least four seeds and at least one aligned
assignment-hash change in at least four seeds.

## Reproducibility and retention

- work only on branch `agent/tsc-resubmit-final` in the revision worktree;
- compile to a new P4-specific target directory and never overwrite a frozen
  historical binary;
- bind source commit, binary SHA-256/size, Python source hashes, protocol and
  config object hashes, seed, tape, reference key/table, execution order, and
  ledger chain;
- keep compressed window/request/convergence logs plus manifest, summary,
  stdout/stderr, process observation, adapter observation, and QC report;
- keep all valid rows and all mechanism counters, including zeroes; and
- use `D:\Anaconda3\python.exe` and `git -c core.longpaths=true`.

## Exclusions and downstream decision

P4 contains no baseline run, heterogeneous/middle/high load, scaling, burst,
SLA, ablation, failure injection, native mode, soak, figure generation, or
paper claim. It does not reopen initialization, order, lookahead, warm bonus,
backpressure, remaining-work, ready-cap, release-valve, `r0`, `wq`, or `mu`
families.

A pass authorizes planning—not automatic execution—of a fresh low-load bank
that includes all strong baselines. Only that bank can decide whether the
candidate restores the paper's low-load leading narrative. A P4 failure ends
this family and returns the manuscript plan to transparent claim reduction.

## Current authorization

Only P4.1 and P4.2 are authorized after the P4.0 commit. P4.3--P4.7 and every
downstream experiment remain blocked pending the required committed audits.
