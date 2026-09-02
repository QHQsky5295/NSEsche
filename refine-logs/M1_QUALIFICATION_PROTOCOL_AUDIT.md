# M1 Six-Cell Method Qualification Protocol Audit

Date: 2026-09-02

Status: protocol frozen; no M1 screen or qualification run executed yet

Paper eligibility: none (`formal_results_eligible=false`)

## Scientific boundary

M1 is a disjoint development gate before the E01--E20 paper experiments.  It
uses the same 20-node low/middle/high workload definitions, homogeneous and
heterogeneous topologies, common HPA/runtime, metrics, and QC rules that will
be used in E1.  Its D01--D20 seed bank has no overlap with the formal bank.

The paper equations and published load-dependent parameter centres are not
changed.  The only selectable implementation detail is the preregistered
deterministic operational refinement:

1. `formula`: formula-aligned all-player order and node-ID tie-break;
2. `ready_order`: dependency-ready players in arrival/request/topological/
   function order;
3. `ready_finish_tie`: the same ready order plus running-warm,
   starting-container, projected-finish, and node-ID tie-breaks for equal
   utility only.

All candidates use strict utility improvement.  No candidate calls another
baseline, changes the common feasible set, or selects a different mechanism
by load.

## Frozen products and gates

- Complete source: 1,440 specifications = (9 baselines + 3 NSESche
  candidates) x 3 loads x 2 topologies x 20 paired development seeds.
- Candidate screen: 90 runs = 3 candidates x 6 cells x D01--D05; all five
  paired runs are retained.
- Selection: global maximin over the twelve candidate-relative cell means
  (throughput and QPR in six cells), followed by mean ratio, joint dual-first
  cell count, and preregistered simplicity order.
- Qualification: 1,200 runs = selected NSESche + 9 baselines x 6 cells x
  D01--D20.
- Pass: NSESche has the highest complete-sample mean throughput and QPR in
  every one of the six cells, with all QC-valid paired observations retained.

The selection receipt binds the source manifest/file hashes and every screen
artifact/QC hash.  The qualification shard binds that receipt and source.  A
failed gate cannot be repaired by result-conditioned deletion or replacement
of a valid seed.

## Verification evidence before execution

- Python protocol suite: 148 tests passed.
- Rust NSESche scheduler suite: 25 tests passed.
- Generated 1,440-run development manifest passes both Python protocol and
  JSON Schema validation.
- Rust formatting, Python bytecode compilation, and Git whitespace checks
  passed before this audit update.

Runtime binary identity and the exact development workspace paths will be
added after the protocol commit and release build.  Until the complete 90-run
screen and 1,200-run qualification pass, M1 remains open and no paper
experiment group is started.
