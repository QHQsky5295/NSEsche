# M1 Decision-Neutral Mechanism Diagnosis Plan

Date: 2026-09-02 (Asia/Shanghai)

Status: preregistered before diagnostic source modification

Phase: development diagnosis only; never eligible for paper figures

## Source result and question

The complete `ready_order` qualification batch at commit `080a3da` retained
1,200/1,200 canonical rows but failed the throughput/QPR gate in all six E1
cells.  `M1_QUALIFICATION_RESULT_AUDIT.md` shows that solver convergence and
offline-reference availability are not the primary failure modes.

The unresolved question is whether NSESche selects a non-running placement
despite an available running-warm candidate because the paper utility is
strictly higher on that placement, or whether the common HPA/candidate set
usually supplies no running-warm alternative at decision time.

## Frozen diagnostic cohort

- Tapes: the already revealed, immutable M1 development tapes D01--D05.
- Cells: homogeneous and heterogeneous x low, middle, and high.
- Method: `sche_nash` with the globally selected `ready_order` mechanism.
- Runs: 30 = 5 fixed tapes x 6 cells.
- Runtime, topology, load, HPA, queue, network, QoS, reference, and random
  configuration: identical to the completed qualification protocol except for
  the new observation-only source/binary identity.
- Attempt policy: the existing technical-failure policy only; no replacement,
  relabeling, or result-conditioned rerun.
- Baseline runs: none.  The completed paired qualification batch already
  establishes the performance gap; this diagnostic tests mechanism state, not
  another superiority claim.

## Decision-neutral source change

The scheduler must retain the exact selected assignment and command stream.
Only `placement_diagnostics` and the emitted observation record may change.
For each completed proposed assignment, record:

1. selected running-warm, starting-container, and cold/nonrunning path counts;
2. players for which at least one running-warm feasible candidate exists;
3. players that bypass all running-warm candidates;
4. for a bypass, the selected paper-utility minus the best running-warm
   paper-utility;
5. for the same bypass, the selected projected-finish tie score minus the best
   running-warm alternative's projected-finish score.

The counterfactual must use the same common candidate set, immutable price
signal, player profile, and other-player impact used by the existing
decision.  It must not feed any diagnostic value back into candidate ranking,
best response, pricing, HPA, or dispatch.

Required unit tests:

- distinguish running, starting, and cold selected states;
- report a warm bypass and its utility/finish deltas on a controlled state;
- prove that calling the diagnostic leaves the assignment fingerprint and
  selected node unchanged;
- retain all existing NSESche scheduler tests.

## Preregistered interpretation

The diagnosis has no pass/fail performance threshold.  Interpret all 30 fixed
runs together:

- **Objective conflict supported:** running-warm alternatives are commonly
  available and commonly bypassed with a positive utility advantage for the
  selected nonwarm node, especially where the selected finish score is worse.
  This means equal-utility tie-breaking cannot address the performance gap.
- **Supply limitation supported:** running-warm alternatives are rarely
  available.  Diagnose common HPA/container placement and feasible-candidate
  formation before changing any NSESche ranking rule.
- **Implementation defect supported:** the selected assignment is lower in
  paper utility than an admissible running-warm alternative beyond numerical
  tolerance.  Correct the best-response implementation before defining a new
  mechanism family.

No interpretation authorizes a fourth local candidate under the current
frozen family.  If no implementation defect is found, a materially new
paper-compatible operational family requires its own preregistration and a
fresh development bank before qualification is repeated.

## Integrity boundary

- Paper Eqs. 1--20, Eq. 19/20, utility, QPR, and load-dependent published
  parameter centres remain unchanged.
- No baseline score, outcome, seed label, workload label, or future completion
  enters an online decision.
- The completed failed qualification artifacts remain immutable and are not
  reclassified after this diagnosis.
