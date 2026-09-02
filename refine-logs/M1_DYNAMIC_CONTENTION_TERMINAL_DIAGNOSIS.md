# M1 Dynamic-Contention Terminal Diagnosis

Date: 2026-09-03 (Asia/Shanghai)

Status: post-screen descriptive diagnosis only; no candidate selection, protocol
change, seed replacement, or qualification authorization

## Evidence boundary

This note reuses the complete, frozen D41--D45 screen described in
`M1_DYNAMIC_CONTENTION_GUARD_RESULT_AUDIT.md`.  All 90 fixed rows completed on
attempt 1 and remain in the analysis.  The diagnosis was performed only after
the preregistered analyzer had failed closed because three QC-valid high-load
rows had zero completed requests and undefined run-level QPR.  It does not
replace the frozen selection rule and cannot make this family rankable.

## Zero completion is not zero scheduling

The three zero-completion rows still performed substantial scheduling work:

| Candidate | Topology | Seed | Placements / assigned players | Final running containers | Final running tasks | Final queue | No-feasible players |
|---|---|---|---:|---:|---:|---:|---:|
| ready_order | homogeneous | D44 | 36,539 | 103 | 31,134 | 23,045 | 0 |
| ready_order | heterogeneous | D42 | 19,209 | 205 | 13,953 | 42,604 | 0 |
| guarded_dynamic_finish_15 | heterogeneous | D44 | 37,143 | 90 | 32,151 | 22,441 | 0 |

The terminal frames therefore exclude both a no-dispatch explanation and a
candidate-feasibility explanation.  The runs accumulated approximately
13.9k--32.2k running tasks on only 90--205 running containers while the fixed
1,000 ms observation window ended.  The request-completion stream is empty in
the three rows even though the frame and Nash streams are complete.

On the same D44 homogeneous tape, the 5% and 15% dynamic guards changed zero
control completions into 30 and 11 completions respectively.  On the D42
heterogeneous tape, the 5% and 15% guards produced 90 and 1 completions.  On
the D44 heterogeneous tape, the control and 5% guard produced 23 and 5
completions while the 15% guard produced zero.  Thus the assignment-count term
can alter in-window service, but its sign and magnitude are not stable across
topologies or seeds.

## Complete-screen descriptive relations

Across the 30 fixed high-load runs, the Spearman relations with throughput
were:

| Terminal or decision diagnostic | Spearman rho |
|---|---:|
| Final queue | -0.6958 |
| Running containers | -0.5396 |
| Placement dispersion | -0.2469 |
| Node memory utilization | -0.1442 |
| Starting containers | -0.1103 |
| Running tasks per running container | -0.0472 |
| Co-location conflict proxy | +0.1689 |
| Node CPU utilization | +0.2733 |

These are univariate descriptive associations, not causal estimates.  The
strongest observed relation is the accumulated service queue, not the Nash
feasibility counter or either placement-only proxy.  Within candidates, the
throughput-versus-final-queue rho is -0.8571 for `ready_order`, -0.5593 for the
5% guard, and -0.6727 for the 15% guard.

The fully QPR-applicable 5% guard improved mean throughput in only two of six
cells:

| Topology | Load | Control throughput | 5% throughput | Delta | Control terminal tasks/container | 5% terminal tasks/container | Delta |
|---|---|---:|---:|---:|---:|---:|---:|
| homogeneous | low | 1.2778 | 1.2344 | -0.0434 | 5.320 | 5.154 | -0.166 |
| homogeneous | middle | 0.6874 | 0.6928 | +0.0054 | 20.871 | 20.052 | -0.819 |
| homogeneous | high | 0.1622 | 0.1424 | -0.0198 | 107.531 | 94.552 | -12.979 |
| heterogeneous | low | 1.0912 | 1.2268 | +0.1356 | 7.747 | 7.158 | -0.590 |
| heterogeneous | middle | 0.2992 | 0.2878 | -0.0114 | 31.059 | 32.044 | +0.986 |
| heterogeneous | high | 0.2236 | 0.2016 | -0.0220 | 110.057 | 128.696 | +18.639 |

In two losing cells the guard reduced terminal tasks per container, whereas in
the other two it increased them.  A single revised regret radius or a further
coefficient on the same projected-finish score therefore lacks a consistent
cross-cell mechanism supported by these observations.

## Mechanism conclusion

The dynamic guard changes node choice inside a solve, but it does not bound
how much newly ready work can be admitted to a running/starting container or
node.  Under high offered load, placement continues while useful service
completion can be starved inside the fixed observation window.  The current
family is consequently a placement-ranking intervention applied to a
serviceability/admission bottleneck.

The fixed 1,000 ms observation window and zero drain are part of the frozen
main comparison.  Adding drain after seeing these rows, redefining throughput,
or mapping undefined QPR to zero would change the estimand and is not an
acceptable repair.

## Successor design boundary (not authorized here)

If the user explicitly authorizes another mechanism family, the supported
direction is an operational serviceability/admission safeguard, not another
load-specific score coefficient.  A successor should:

1. keep the paper utility, Eqs. 1--20, QPR definition, common HPA, workload
   profiles, and fixed observation window unchanged;
2. use only current observable state and never the load label, future
   completion, seed identity, or baseline result;
3. limit or defer additional ready-player fan-in when normalized runnable work
   would make the estimated per-task service share non-serviceable;
4. apply the same deterministic rule to all loads and topologies, with a
   documented fallback when every candidate reaches its serviceability budget;
5. log budget hits, deferred players, terminal work per running container,
   queue accumulation, and the counterfactual unguarded choice;
6. be preregistered before code or fresh-tape execution and evaluated on a new
   development bank, followed by an independent formal seed bank.

No such source change or experiment has been started.  D41--D60 remain closed,
and M2 remains unauthorized.
