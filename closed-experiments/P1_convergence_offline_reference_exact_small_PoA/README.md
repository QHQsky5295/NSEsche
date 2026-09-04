# P1 Convergence, Offline Reference, and Exact-Small PoA — Permanent Freeze

Freeze date: 2026-09-04 (Asia/Shanghai)

Source writing/audit commit: `410af08`

Status: `closed_for_paper_writing_do_not_modify`

This directory is the permanent paper-writing package for the closed P1
experiment. Later NSESche algorithm changes, performance experiments, or
manuscript revisions must not modify, replace, or delete any file here. A
correction, if ever required, must be stored in a new sibling freeze directory
with an explicit supersession note; this directory remains as provenance.

## Closed claims

- Fixed-snapshot strict sequential NSESche updates have a proved finite-
  improvement property over resource-feasible assignments, subject to the
  assumptions in `writing/PROOF_PACKAGE.md`.
- Runtime inner stability is 19,509/19,509 active windows; mean inner rounds
  are 1.7054.
- Observed outer placement stability is 97.396%; nine windows hit the outer
  cap and zero oscillations were observed. No joint price-placement fixed-point
  theorem is claimed.
- All 300 exact-small games contain a pure equilibrium and the deterministic
  trajectory reaches one. Exact worst-PNE PoA median/p95/max is
  1.002848/1.010731/1.018114.
- The offline estimator's exact-small normalized shortfall median/p95/max is
  0/0.0935%/0.2008%. Large-state references remain heuristic estimates, with
  the observed below-current cases retained and disclosed.

## Contents

- `data/retained_evidence/`: the complete four-file P1-A derived product.
- `data/exact_small/`: the complete five-file P1-B games, exact results,
  summary, table, and independent verification receipt.
- `audits/`: preregistration, implementation/correction audits, result audits,
  equation alignment, and reviewer-sufficiency decision.
- `writing/`: the proof package, reviewer response material, issue board, and
  evidence matrix at freeze time.
- `source/`: the retained analyzer, exact-small generator/enumerator/verifier,
  and directed tests used by the closed product.
- `FREEZE_MANIFEST.csv`: relative path, byte count, and SHA-256 for every other
  file in this directory.

## Evidence boundaries

This package closes the P1 evidence scope only. It does not claim universal
outer convergence, exact optimality of large-state simulated annealing,
universal PoA at most 1.018114, throughput/QPR leadership, close-comparator
coverage, or QoS fairness. Those are either explicit non-claims or separate
experiment blocks.
