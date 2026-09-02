# NSESche TSC Resubmission Experiment Plan

**Protocol:** `TSCv1`

**Target:** IEEE Transactions on Services Computing

**Method:** formula-consistent NSESche with disclosed deterministic operational
refinements

**Formal replication unit:** one complete paired run; 20 seeds per cell

## Frozen method boundary

- Player identity is `(ReqId, FnId)` and only dependency-ready functions are
  scheduled.
- Player order is deterministic: arrival frame, request id, DAG topological
  rank, function id.
- A move is accepted only for a strict increase under the paper utility.
- Equal utility keeps the current feasible node; an unassigned equal-utility
  tie uses running-warm, starting, predicted-finish, then node-id order.
- Eq. 19 is recalculated from the current round's base price and never
  recursively multiplied.
- Low uses `(r0=0.6,wq=0.5)`; middle/high use `(0.5,0.6)`.  The implementation
  and binary hash are otherwise global across loads.
- No baseline score, learned expert, SRPT proxy, hidden per-load router or
  result-conditioned dispatch is permitted in the final method.

## Workload and platform

- 20-node arrival-rate targets: low 1.9k, middle 2.6k and high 7.0k requests/s.
- Homogeneous nodes: CPU 150 and memory 5000 simulator units.
- Heterogeneous nodes retain those means with CPU SD 30% and memory SD 25%.
- One frame is 1 ms; link rates are 8000--10000 MB/s.
- Common HPA: target 0.5, tolerance 0.1, minimum one instance when requests are
  pending, scale-to-zero when idle, 100-observation careful-down, least-task
  scale-up placement.
- Each tape is immutable and shared by all algorithms in a paired cell.

## Run order and budget

| Milestone | Paper block | New online runs | Gate |
|---|---|---:|---|
| M0 | Workspace, protocol, storage, tests | 0 | Reproducible frozen method and protocol |
| M1 | Workload pilot and method qualification | development only | All six E1 cells pass the development gate |
| M2.1 | 20-node homogeneous low/middle/high | 600 | NSESche mean throughput and QPR highest in every cell |
| M2.2 | Hyperparameter validation | 240 | Published centres are Pareto-undominated |
| M2.3 | Four ablations | 240 | Full method exceeds each ablation |
| M2.4 | 20-node heterogeneous low/middle/high | 600 | NSESche mean throughput and QPR highest in every cell |
| M2.5 | 100/500-node proportional weak scaling | 1200 | Complete ten-method scaling comparison |
| M3.1 | Three controlled burst patterns | 600 | Complete recovery/tail/SLA evidence |
| M3.2 | Balanced QoS | 200 | Complete class and fairness evidence |
| M3.3 | CP-BR and OnSocMax welfare comparison | 80 | Complete pricing/welfare evidence |

Formal online total: 3760 runs.  Exact PoA adds 300 deterministic small states.
Feature validation, resource use, convergence and online overhead reuse the
formal logs rather than launching duplicate runs.

## Development and confirmation

1. Evaluate at most three formula-consistent candidate versions on five
   development tapes per E1 cell.
2. Evaluate the selected candidate on 20 development tapes across all six E1
   cells.
3. Freeze code, parameters, binary, reference tables and formal banks before
   unblinding formal outcomes.
4. Run formal cells in paper order, starting with homogeneous-20 low.
5. A changed method invalidates earlier NSESche formal rows for the main claim.
   Preserve the old bank, create a disjoint bank and rerun all methods needed
   for paired confirmation.

## Required evidence

Every run emits a manifest, summary, compressed window/request/convergence
logs, stdout/stderr and QC result.  Required metrics include throughput,
cost/request, run-level QPR, completion ratio, latency mean/p50/p95/p99, queue
peak/area, burst recovery, drop/reject/timeout, resource use, scheduler
wall/thread CPU/RSS, inner/outer rounds and all convergence statuses.

Offline reference uses build/replay keyed by protocol, topology, load, QoS,
tape and parameter cell.  Record build CPU/wall/RSS/iterations, table size,
load/lookup time, and missing/zero/negative counts.  A non-positive reference
falls back to the inner Nash result without division.

Statistics use seed-level BCa 95% confidence intervals, paired permutation
tests, Holm correction, paired effect sizes and relative-change intervals.
All valid formal seeds remain in every estimate.

## Figure outputs

Generate Fig.4--Fig.13 in manuscript order with source CSV and export
manifests.  Keep the original method order while adding 95% CI, seed points,
redundant marker/hatching encodings and explicit units.  Export vector PDF/SVG
at IEEE single/double-column width plus a 900-dpi PNG.  Each replacement for an
old figure includes an `old_pdf_alignment.csv`; baseline means should normally
remain within +/-15% of the original bars or trigger a whole-cell configuration
audit.
