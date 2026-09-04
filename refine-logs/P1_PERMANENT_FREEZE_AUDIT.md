# P1 Permanent Freeze Audit

Date: 2026-09-04
Status: `CLOSED_FOR_PAPER_WRITING_DO_NOT_MODIFY`

## Scope

This audit closes and permanently freezes the reviewer-facing P1 package for:

- inner best-response convergence and bounded finite termination;
- measured outer placement stability, explicitly not an unconditional joint
  fixed-point theorem;
- offline-reference construction, cost, nonpositive-reference handling and
  exact-small accuracy;
- exact-small PNE and price-of-anarchy evidence;
- the corresponding proof, reviewer response and source/verifier snapshot.

The immutable root-level copy is:

`closed-experiments/P1_convergence_offline_reference_exact_small_PoA`

It is independent of later NSESche algorithm development.  Later source,
protocol or manuscript edits must not alter this directory.  If a future
scientific correction is necessary, it must be recorded as a new, separately
named version rather than silently changing this freeze.

## Verification receipt

- total files, including the manifest: **31**;
- files covered by the manifest: **30**;
- retained P1-A result files: **4**;
- exact-small P1-B result files: **5**;
- total bytes: **1,988,774**;
- files lacking the Windows read-only attribute: **0**;
- manifest SHA-256:
  `D1E1707239E48D23B2EDB0C8893F38A93551BEDF9126DBF6C948F3B24340B579`.

Every manifest row was independently rehashed and checked for byte length.
The nine copied result files were also rehashed against their source files in:

- `runs/tscv1_p1_retained_evidence_98f822c_20260904`;
- `runs/tscv1_p1_exact_small_v2_20260904`.

All checks passed with zero missing, unexpected, size-mismatched,
hash-mismatched or source-mismatched files.

## Claim boundary carried into the freeze

The accepted theoretical status is **provable after weakening / explicit
assumptions**.  The finite weighted/lexicographic potential argument establishes
termination of strict feasible inner best-response moves and a constrained PNE
(or a standard PNE under Cartesian feasibility).  It does not establish
unconditional convergence of the implementation's full reference-price outer
loop.  The outer-loop result is therefore reported as empirical placement
stability, with the nine cap hits and all 508 nonstable windows retained.

The frozen exact-small experiment supports a bounded empirical inefficiency
statement only for the constructed three-node game family.  It does not license
a universal analytical PoA bound.

## Paper readiness

P1 is closed and ready for manuscript/rebuttal drafting under the claim boundary
above.  This closure does not make the main comparative performance section
paper-ready and does not authorize deleting or filtering any P2 observation.
