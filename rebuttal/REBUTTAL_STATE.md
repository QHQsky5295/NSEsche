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

`AUTO_EXPERIMENT=false`: this state does not authorize a simulator run, reference build, workload capture, or exact-small enumeration.

## Evidence state

- Formal online evidence: homogeneous-20 low, ten methods, paired Q61–Q80, 200/200 QC-valid runs.
- Formal result: NSESche throughput rank 3 and QPR rank 4; the universal dual-metric leadership claim is unsupported.
- Formal runtime: `ready_order`, source commit `98f822cf2dcb878024a2ca39cc56533895ea692c`, binary SHA-256 `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Existing convergence/reference telemetry: structurally complete for all 20 formal NSESche low-load runs; P1 statistical extraction is not yet executed.
- Offline references: 120/120 built and bound across the six 20-node cells; 15/117,138 rows are negative and none are zero; nonpositive fallback is explicit.
- Legacy figures: provenance anchors only. The historical protocol and claimed 20-run means are not reconstructible.
- Tested successor families G2–G7: development evidence only; none passed its confirmation gate.

## Issue clusters

| Cluster | Reviewer IDs | State |
|---|---|---|
| Inner PNE and outer fixed point | R1-1, R1-2, R2-1, R3-1 | theory revision + P1 evidence required |
| Eqs. (16)–(20) and offline reference | R1-3, R2-2 | partial evidence exists; exact-small validation pending |
| Feature semantics and feasibility | R2-3, R3-2 | wording correction + validation/ablation pending |
| Controlled burst and QoS | R2-4 | P3 experiment pending |
| Units, platform, statistics | R2-5, R3-3 | mandatory disclosure correction + staged results pending |
| Baseline fairness, scaling, overhead | R2-6, R3-3 | boundary disclosure + P1/P2 evidence pending |
| Novelty, close comparators, fairness, PoA | R3-4 | theory positioning + P1/P3 evidence pending |

## Commitment ledger

The project has committed only to auditable work blocks in V4. It has not committed that NSESche will rank first, that the outer loop converges unconditionally, that the SA reference is exact, or that legacy values will be reproduced. Every future response sentence must distinguish `completed`, `planned`, and `conditional on gate`.

## Next authorized decision

The next unique scientific stage is a P1 preregistration for two read-only/offline products:

1. retained-log convergence/reference/overhead extraction from the 20 formal NSESche Q61–Q80 runs; and
2. a 300-state exact-small reference/PNE/PoA protocol, frozen before any optimum is exposed.

P2 and P3 online sampling remain blocked until P1 closes.
