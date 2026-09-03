# Post-G8 claim/scene analyzer audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Preregistration commit: `37d40d7`  
Status: implementation frozen; one retained-product invocation authorized

## Implemented contract

The analyzer validates four machine-readable reports by both file and canonical
document hash and four audit documents by file hash. It admits exactly 270
G2/G3 development rows plus the complete 200-run formal homogeneous-low
product. Each development family is checked for its exact three-candidate,
six-cell, five-seed matrix and nine homogeneous-low baselines; the families
remain separate.

For every candidate cell it reports the five raw values, mean, sample SD,
candidate-minus-own-C0 paired interval/signs, and all leave-one-seed-out means
for throughput, QPR, latency, completion, and cost. Homogeneous-low candidate
rows are paired with each of the nine same-bank baselines. The formal table
recomputes all ten 20-seed method summaries, primary ranks, and NSESche-to-
leader paired margins. Unopened scenes are explicitly labelled as not measured
against all baselines.

The existing-candidate decision is the exact six-condition conjunction in the
preregistration. Multiple passers use the frozen candidate score dimensions
and then a global simplicity order; no result-dependent tie rule is available.
Whatever the outcome, all implementation and sampling authorization flags are
false.

## Frozen implementation receipts

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/analysis/post_g8_claim_scene_feasibility.py` | `6a8fd315efa21a95e967c962969930e24f474f4df006b89485bf2350824a5b35` |
| `scripts/reviewer_experiments/analysis/tests/test_post_g8_claim_scene_feasibility.py` | `e6a07ba2f33a1eb89bb73c62af0df36c75caade20b2302d696f48b2f9cb05b3a` |

## Verification

- Black and Python compilation passed.
- Three directed synthetic tests passed, covering five-/twenty-seed summaries,
  exact conjunction failure, deterministic candidate selection, and formal
  rank/wording classification.
- Combined post-G8/G8/G2/G3 regression: 24/24 passed.
- `git diff --check` passed.
- The no-overwrite target directory
  `runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/claim_scene_feasibility`
  was absent at audit time.

## Authorization boundary

After this audit is committed, exactly one invocation may validate and analyze
the unchanged frozen inputs and atomically create the four preregistered
products. A structural failure must be retained and separately audited before
any retry. No scheduler edit, candidate implementation, tape/reference build,
simulator run, confirmation, formal continuation, figure, or manuscript claim
is authorized.
