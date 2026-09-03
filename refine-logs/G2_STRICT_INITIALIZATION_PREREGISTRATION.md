# G2 Strict-Initialization Successor Preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: frozen before scheduler-source modification and before D66 capture

## 1. Motivation and evidence boundary

The independent Q61--Q80 homogeneous-low formal cell completed all 200 rows
but failed its frozen dual-metric gate. NSESche was 1.04% below FaaSRank in
mean throughput and 9.26% below it in mean QPR. Paired diagnostics showed that
the throughput mean is tail-sensitive, whereas the QPR loss is broad and is
associated with bypassing available running-warm containers and selecting
starting containers.

The earlier tie-order, static completion-guard, and dynamic completion-guard
families are closed. A bounded-regret guard cannot be used because it may
choose a lower-utility strategy and therefore conflicts with paper Eq. (15).
G2 is a new mechanism family following that completed diagnosis; it is not a
fourth candidate appended to a closed screen.

Q61--Q80 and every associated baseline/NSESche result remain immutable failed
formal evidence. They are used only to motivate this preregistration and are
not candidate-selection observations.

## 2. Frozen scientific invariants

G2 does not change:

- paper Eqs. (1)--(20), their signs, units, or coefficients;
- low `(r0=0.6,wq=0.5)` and middle/high `(r0=0.5,wq=0.6)` centres;
- dependency-ready player collection and deterministic base player order;
- feasible-node filtering, common HPA, cold-start/container lifecycle,
  workload generator/tape schema, network model, or metric definitions;
- run-level QPR, reference validation, fixed observation window, QC, or
  all-valid-row retention;
- inner/outer iteration limits of four/two.

For every candidate, every inner-loop update evaluates all feasible nodes and
selects an Eq. (15) utility argmax. A move is accepted only for a strict
published-utility improvement; equal utility retains the current node before
the deterministic node-ID tie-break. Only Algorithm 1 line 8's unpublished
construction of an initial feasible assignment may differ.

## 3. Exactly three candidates

The candidate set is closed before implementation:

1. `ready_order` (C0): unchanged corrected-runtime control. Initialization is
   the existing sequential strict-utility construction.
2. `ready_warm_init` (C1): during initialization only, if one or more feasible
   nodes already contain a running container for the function, select among
   those nodes by minimum dynamic finish score, then higher published utility,
   then NodeId. If no feasible running-warm node exists, use C0 initialization.
3. `ready_finish_init` (C2): during initialization only, select the feasible
   node with minimum dynamic finish score, then higher published utility, then
   NodeId.

The frozen dynamic finish score is

`startup_remaining + runnable + starting_resident + pressure +
state_so_far_assigned_request_count`.

It is used only to construct a feasible starting state. It is not a utility
term, does not filter any inner-loop action, and cannot override an Eq. (15)
best response after initialization. No load- or topology-specific candidate is
allowed.

Candidate-specific initialization counters and a semantic label must be
logged. Distinct reference-key tags are required because initialization can
change the deterministic search starting state.

## 4. Fresh development bank and exact matrix

- Development seeds: exactly D66, D67, D68, D69, and D70.
- Candidate cells: homogeneous/heterogeneous x low/middle/high x five seeds x
  three candidates = 90 NSESche runs.
- Candidate references: one state-matched offline table per candidate/cell/seed
  = 90 builds.
- Workload tapes: six cells x five seeds = 30 captures, shared across the three
  candidates for a given cell/seed.
- Low-load paired feasibility controls: the nine frozen baseline methods x
  homogeneous-low x D66--D70 = 45 additional online runs.
- Total online screen: 135 runs.

D66--D70 did not appear in the previous D01--D65 development screens or the
Q61--Q80 formal bank. No D66 tape, reference, or result may exist before the
protocol commit and source-bound manifest.

## 5. Frozen selection and fail-closed rules

Every expected row must be canonical and pass the pre-existing QC, formula,
reference, pairing, and complete-QPR gates. A technical failure may be retried
only with the identical run spec under the frozen retry policy. A QC-valid
scientific result is never deleted, replaced, or rerun because it is adverse.

Candidate ranking uses the same global rule as G1 across the twelve
candidate-cell quantities:

1. maximize the minimum Ck/C0 ratio over six mean throughputs and six mean
   run-level QPR values;
2. maximize the arithmetic mean of the twelve ratios;
3. maximize the number of cells jointly first in both metrics;
4. prefer simplicity C0, then C1, then C2.

The winning candidate is eligible for a new formal confirmation bank only if,
on the paired D66--D70 homogeneous-low feasibility check, its mean throughput
and mean QPR strictly exceed every one of the nine baselines with complete QPR
coverage. Otherwise the family is rejected and no formal run is authorized.

Development results, including baseline feasibility controls, are not paper
evidence and cannot be mixed with a later confirmation bank.

## 6. Formal boundary after a development pass

A G2 development pass does not repair or overwrite Q61--Q80. It authorizes a
new preregistered twenty-seed bank disjoint from D01--D70 and Q61--Q80. Formal
execution again starts with the complete ten-method homogeneous-low cell. The
middle cell remains blocked until that new low cell passes the dual-metric and
provenance gates.

The old-PDF +/-15% target remains a separate scene-level diagnostic. The G2
candidate may not weaken baselines, alter common runtime semantics, or select
seeds to manufacture numerical alignment.

