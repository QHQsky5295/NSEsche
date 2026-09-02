# M1 Dynamic-Contention Guard Preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: preregistered after closing the D21--D25 result audit and before source
modification, D41--D60 tape capture, or execution

Phase: final non-formal M1 mechanism-development family

## Evidence-bound design question

The D21--D25 completion-guard screen retained the unchanged `ready_order`
control.  The static guard improved both throughput and QPR in homogeneous-low
and heterogeneous-low at radius 0.05, and in heterogeneous-high at radius
0.15, but collapsed homogeneous-middle and degraded other cells.  The closed
result audit traced the collapse to a specific mechanism mismatch:

- the paper utility evaluates the current joint-decision externality through
  `state_without_player.node_aggregates[node].impact_sum`;
- the guard's projected-finish score uses only the static window snapshot;
- a utility-regret allowance can therefore override the dynamic balancing
  signal and concentrate multiple same-window assignments on the same
  statically attractive node.

The final design question is whether adding the already-known same-window
assigned request count to the completion proxy removes that concentration
failure while retaining the cell-level gains of completion-aware selection.

## Frozen mechanism family

The paper utility, price signal, feasible set, common HPA, workload, reference,
and Eqs. 1--20 are unchanged.  Candidate utilities and the relative utility
floor remain exactly those used by the closed completion-guard family.

For a candidate node `j`, define only in implementation/prose the dynamic
completion proxy

`static_finish(j) + state_without_player.node_aggregates[j].request_count`,

where `static_finish` remains
`startup_remaining + runnable + starting_resident + pressure`.  The added term
has the same task-count interpretation as the runnable and resident terms and
uses only players already assigned earlier in the current deterministic solve.
It does not use future completions, baseline results, offline hindsight, load
labels, or seed identity.

The three and only three candidates are:

1. `ready_order` -- unchanged control, simplicity order 0;
2. `guarded_dynamic_finish_05` -- relative utility-regret radius 0.05,
   simplicity order 1;
3. `guarded_dynamic_finish_15` -- relative utility-regret radius 0.15,
   simplicity order 2.

The radii are deliberately unchanged from the rejected static family so this
screen tests the diagnosed missing dynamic-contention term rather than another
radius sweep.  Among candidates above
`U_max - rho * max(1, abs(U_max))`, minimize the dynamic completion proxy;
then prefer higher paper utility, the current node, and lower node ID.  Keep the
paper-utility-best node unless the dynamic proxy improves beyond `EPSILON`.

## Fresh bank and fixed screen

- D41--D60 are the only development/qualification seeds for this family.
- D01--D40 and E01--E20 are forbidden for selection.
- Screen seeds are D41--D45, frozen before capture.
- Cells are homogeneous/heterogeneous x low/middle/high at 20 nodes.
- Screen size is 90 runs = 3 candidates x 6 cells x 5 seeds.
- If authorized, qualification size is 1,200 runs = 10 methods x 6 cells x
  20 seeds.
- All candidates/methods in a cell share the exact tape.
- References are candidate-state matched and built before online inspection.
- Every valid fixed row is retained; retries are result-blind technical retries
  only.

## Selection, qualification, and terminal rule

Apply the same frozen global maximin rule:

1. maximize the minimum of the twelve candidate-relative cell means for
   throughput and run-level QPR;
2. maximize their mean;
3. maximize cells jointly first in both metrics;
4. use the declared simplicity order.

If `ready_order` wins, this family is rejected and no qualification is run.  If
a dynamic guard wins, freeze its source/binary and run the complete D41--D60
qualification.  Qualification requires strictly highest arithmetic-mean
throughput and QPR in every one of the six cells with 20/20 QPR applicability
for all ten methods.

This is the final local M1 development family authorized by the present
mechanism diagnosis.  A screen loss or qualification loss stops further local
candidate addition and requires explicit user-level redesign direction; it
does not authorize a fourth candidate, revised coefficient, load-specific
mechanism, D41--D60 reuse, or M2 execution.
