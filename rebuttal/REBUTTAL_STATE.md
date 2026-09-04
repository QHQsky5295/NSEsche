# Rebuttal State

## Submission state

- Venue/workflow: IEEE Transactions on Services Computing reject-and-resubmit.
- Submitted manuscript authority: `（5-12V2）TSC_NSESche_Complete_IEEE_.pdf`, SHA-256 `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`.
- Reviewer authority: `REVIEWS_RAW.md`, 13 atomic issues, source SHA-256 `ecb83fd9a6d874008c2c1684ff2bf866bd3fe8eac26609496bcfccd151ee8b31`.
- Governing experiment plan: `refine-logs/TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V4.md`, SHA-256 `68369bd695e56232fba76d7be6b91e11d899a2e6372c08234635ea53ec8295c0`.
- Working branch: `agent/tsc-resubmit-final`; original workspace remains read-only.
- Venue response length/template/deadline: not supplied. This does not block experiment planning, but a final rebuttal letter must not be finalized until these constraints are known.

## Current phase

P0 source normalization, claim contract, reviewer-evidence mapping, and runtime audit are complete. No revised manuscript source was found in the repository, so statements in the supplied attachment saying “we added” or “the revised manuscript now” are treated as proposed wording, not completed manuscript edits.

P1 execution and its reviewer-facing theory/reference synthesis are complete. A final response letter is still blocked on the venue response length/template/deadline and on the experiment blocks assigned to non-P1 issues.

## Evidence state

- Formal online evidence: homogeneous-20 low, ten methods, paired Q61–Q80, 200/200 QC-valid runs.
- Formal result: NSESche throughput rank 3 and QPR rank 4; the universal dual-metric leadership claim is unsupported.
- Formal runtime: `ready_order`, source commit `98f822cf2dcb878024a2ca39cc56533895ea692c`, binary SHA-256 `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- P1 retained convergence/reference telemetry: analyzed for all 20 formal NSESche low-load runs and 19,509 active windows; inner stability 100%, outer placement stability 97.396%, nine outer caps, zero oscillations.
- P1 exact-small evidence: 300/300 constructed games have a PNE and deterministic convergence; exact PoA median/p95/max 1.002848/1.010731/1.018114; reference shortfall median/p95/max 0/0.0935%/0.2008%.
- Offline references: 120/120 built and bound across the six 20-node cells; 15/117,138 rows are negative and none are zero; nonpositive fallback is explicit.
- Legacy figures: provenance anchors only. The historical protocol and claimed 20-run means are not reconstructible.
- Tested successor families G2–G7: development evidence only; none passed its confirmation gate.

## Issue clusters

| Cluster | Reviewer IDs | State |
|---|---|---|
| Inner PNE and outer fixed point | R1-1, R1-2, R2-1, R3-1 | P1 scope closed; proof and insertion text ready; outer joint fixed point explicitly not claimed |
| Eqs. (16)–(20) and offline reference | R1-3, R2-2 | P1 scope closed; derivation, costs, fallback, and exact-small validation ready |
| Feature semantics and feasibility | R2-3, R3-2 | wording correction + validation/ablation pending |
| Controlled burst and QoS | R2-4 | P3 experiment pending |
| Units, platform, statistics | R2-5, R3-3 | mandatory disclosure correction + staged results pending |
| Baseline fairness, scaling, overhead | R2-6, R3-3 | boundary disclosure + P1/P2 evidence pending |
| Novelty, close comparators, fairness, PoA | R3-4 | theory positioning + P1/P3 evidence pending |

## Commitment ledger

The project has committed only to auditable work blocks in V4. It has not committed that NSESche will rank first, that the outer loop converges unconditionally, that the SA reference is exact, or that legacy values will be reproduced. Every future response sentence must distinguish `completed`, `planned`, and `conditional on gate`.

## Next authorized decision

Freeze the complete P1 writing/data package under the root-level closed-experiment directory. Performance and non-P1 reviewer issues remain governed by the tracker; P1 evidence must not be modified to accommodate later algorithm changes.
