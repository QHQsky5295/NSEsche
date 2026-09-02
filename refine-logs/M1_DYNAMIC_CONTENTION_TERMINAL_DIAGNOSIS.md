# M1 Dynamic-Contention Terminal Diagnosis

Date: 2026-09-03 (Asia/Shanghai)

Status: post-screen descriptive diagnosis only; no candidate selection, protocol
change, seed replacement, or qualification authorization

Superseding G0 finding: the post-screen runtime audit in
`G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md` identified a common executor
cold-start transition starvation defect.  The placement associations below
remain a faithful description of the closed D41--D45 data, but they must not be
used to justify an NSESche-specific admission mechanism before corrected-runtime
requalification.

## Evidence boundary

This note reuses the complete, frozen D41--D45 screen described in
`M1_DYNAMIC_CONTENTION_GUARD_RESULT_AUDIT.md`.  All 90 fixed rows completed on
attempt 1 and remain in the analysis.  The diagnosis was performed only after
the preregistered analyzer had failed closed because three QC-valid high-load
rows had zero completed requests and undefined run-level QPR.  It does not
replace the frozen selection rule and cannot make this family rankable.

## Zero completion is not zero scheduling

The three zero-completion rows still performed substantial scheduling work:

| Candidate | Topology | Seed | Assigned players | Resident | Runnable | Starting-resident | Running / starting containers | No-feasible players |
|---|---|---|---:|---:|---:|---:|---:|---:|
| ready_order | homogeneous | D44 | 36,539 | 31,125 | 7,011 | 24,114 | 103 / 119 | 0 |
| ready_order | heterogeneous | D42 | 19,209 | 13,954 | 11,618 | 2,336 | 205 / 24 | 0 |
| guarded_dynamic_finish_15 | heterogeneous | D44 | 37,143 | 32,140 | 15,107 | 17,033 | 90 / 70 | 0 |

The terminal frames therefore exclude both a no-dispatch explanation and a
candidate-feasibility explanation.  They also show that the old
`running_tasks` label counts all resident tasks: 2.3k--24.1k tasks were bound to
containers that were still starting, and did not participate in CPU sharing.
The request-completion stream is empty in the three rows even though the frame
and Nash streams are complete.

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

These are univariate descriptive associations, not causal estimates.  In
particular, `running tasks per running container` used the resident-task count,
not the runnable-task count.  The
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

## Mechanism conclusion superseded by G0 runtime audit

The dynamic guard changes node choice inside a solve and therefore changes how
many tasks are bound to running versus starting containers.  The later G0 audit
proved that the common executor admitted runnable-task memory before reserving
the extra memory needed for finishing cold starts.  Sustained task admission
could hold containers at `left_frame == 1` hundreds of frames beyond the
maximum configured cold start.  This common transition starvation, rather than
an NSESche-specific fan-in rule, is the primary supported explanation for the
zero-completion rows.

The fixed 1,000 ms observation window and zero drain are part of the frozen
main comparison.  Adding drain after seeing these rows, redefining throughput,
or mapping undefined QPR to zero would change the estimand and is not an
acceptable repair.

## Corrected-runtime boundary (not authorized here)

No NSESche-specific successor should be added on the basis of the defective
runtime.  The supported next experiment is a fresh, preregistered screen of the
unchanged `ready_order`, `guarded_dynamic_finish_05`, and
`guarded_dynamic_finish_15` candidates after the common runtime and matching
offline references are refrozen.  Only a remaining defect observed on that
corrected runtime could motivate a new mechanism.

D41--D60 remain closed, their references cannot be reused with the corrected
runtime, and M2 remains unauthorized.
