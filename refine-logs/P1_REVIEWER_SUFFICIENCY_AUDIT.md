# P1 Reviewer-Sufficiency Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: `p1_scope_closed_manuscript_material_ready`

## Decision

P1 is now closed for its declared scope: inner convergence/PNE, outer-loop
boundary and empirical stability, offline-reference construction/accuracy/
cost/fallback, and exact-small PoA. The result is reviewer-satisfactory only
with the corrected theorem and terminology in `PROOF_PACKAGE.md`; the raw
statement “300/300 states converged, maximum PoA 1.0181” is not sufficient by
itself and must not replace the proof.

The original unconditional double-loop convergence claim does not survive.
The proved result is a fixed-snapshot finite-improvement theorem over feasible
assignments, with a worst-case bound of $|\mathcal F|-1$. Under shared capacity
the terminal object is a constrained PNE/pure GNE. Outer convergence remains
an explicit non-claim; the measured quantity is placement stability.

## Reviewer-by-reviewer adequacy

| Issue | P1 disposition | Evidence and required wording | Residual risk |
|---|---|---|---|
| R1-1 | answered within scope | weighted/lexicographic potential proof, existence and finite improvement; 19,509 runtime windows and 300 exhaustive games | must keep fixed-snapshot assumptions visible |
| R1-2 | answered within scope | replaces boundedness argument with an exact potential identity and finite-state-change bound | cannot imply the outer loop shares the theorem |
| R1-3 | answered conservatively | proves bounded saturating gain, ratio invariance, and nonrecursive price bound | these are design properties, not unique optimality |
| R2-1 | answered within scope | defines inner constrained PNE, strong joint fixed point, and weaker implemented placement-stability condition | strong joint fixed-point existence remains unproved and unclaimed |
| R2-2 | answered | construction/update trigger, 120 tables, build/lookup/RSS/storage cost, nonpositive and below-current fallback, exact-small accuracy | large-state tables remain heuristic estimates |
| R3-1 | answered within scope | explicit assumptions, $|\mathcal F|-1$ bound, four-round implementation cap, 2.604% nonstable outer rate, zero oscillation | worst-case bound is exponential |
| R3-4 PoA part | answered | exact 300-state/737,100-assignment PoA distribution and independent verification | close comparators and QoS fairness remain P3, outside P1 |

## Why the evidence is strong enough

1. The proof does not rely on the 300 sampled games; it follows algebraically
   from the paper utility after the pairwise term is symmetrized.
2. The zero-complexity boundary is handled rather than excluded silently.
3. Joint memory feasibility is acknowledged, so the equilibrium is not
   mislabeled as an unconstrained Cartesian-product game.
4. The exact-small study enumerates every assignment and deviation and is
   independently reimplemented; it is a verification layer, not a visual
   example.
5. Runtime evidence reports failures and limits. In particular, 499
   below-current references and nine outer caps are retained.
6. The reference claim separates small-state exact accuracy from large-state
   heuristic behavior and reports both offline and online cost.

## Prohibited phrasings

- “Bounded utilities guarantee convergence of NSESche.”
- “The complete inner and outer algorithm always converges.”
- “The simulated-annealing reference is the exact social optimum.”
- “PoA is analytically bounded by 1.0181.”
- “Outer placement stability proves a price fixed point.”

## Approved concise claim

> For each fixed scheduling snapshot with a complete feasible assignment,
> strict sequential NSESche updates have the finite-improvement property and
> terminate at an epsilon-constrained resource-feasible pure equilibrium. This
> is supported by exhaustive 300-state validation and by 100% inner stability
> over 19,509 active runtime windows. The outer loop is reported empirically:
> 97.396% placement stability, 0.0461% cap hits, and zero observed oscillation.
> The offline estimator has 0.0935% p95 exact-small shortfall, while its
> large-state below-current incidence (2.558%) and fail-closed behavior are
> disclosed.

## Artifact set to freeze

- `PROOF_PACKAGE.md`
- `rebuttal/P1_THEORY_REFERENCE_RESPONSE.md`
- `refine-logs/P1_A_RETAINED_EVIDENCE_RESULT_AUDIT.md`
- `refine-logs/P1_B_EXACT_SMALL_RESULT_AUDIT.md`
- `runs/tscv1_p1_retained_evidence_98f822c_20260904/`
- `runs/tscv1_p1_exact_small_v2_20260904/`

The permanent root-level freeze directory and hash inventory are created only
after these texts pass consistency checks.
