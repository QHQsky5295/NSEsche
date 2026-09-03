# P0 Claim and Runtime Audit Result

Date: 2026-09-04 (Asia/Shanghai)

Preregistration: `P0_CLAIM_RUNTIME_AUDIT_PREREGISTRATION.md`

Status: `complete_p1_retained_log_and_exact_small_preregistration_authorized`

## Completion

All eight preregistered outputs exist:

1. `rebuttal/REVIEWS_RAW.md`
2. `rebuttal/REBUTTAL_STATE.md`
3. `rebuttal/ISSUE_BOARD.md`
4. `rebuttal/STRATEGY_PLAN.md`
5. `rebuttal/MANUSCRIPT_CLAIM_MAP.md`
6. `rebuttal/REVIEWER_EVIDENCE_MATRIX.md`
7. `refine-logs/P0_READY_ORDER_RUNTIME_TELEMETRY_AUDIT.md`
8. this result audit

The reviewer source was normalized into 13 atomic issues without overwriting the attachment. The submitted manuscript was mapped into 31 material claims. Every reviewer issue has a response mode and evidence block; no native, fault, stress, or soak experiment is needed.

## Principal decisions

1. The manuscript's universal throughput/QPR superiority narrative is removed. The old 55.4%/74.3% and related bars are not recoverable paired statistics; the formal low-load result contradicts low-load leadership.
2. “Burst-tolerant,” heterogeneous QoS coordination, scaling, and close-comparator/fairness claims remain conditional on their specific P2/P3 gates.
3. The inner PNE claim is restricted to fixed snapshot/candidates/prices and strict improvement; executed windows that hit a cap are not called PNE. Bounded prices do not prove outer convergence.
4. Large-state offline references remain SA estimates. Exact-small enumeration will validate the evaluator and quantify reference error/PoA, not certify large-state optimality.
5. The exact `98f822cf` executable exists and matches SHA-256. It remains the only authorized final `ready_order` runtime. Current HEAD is not source-equivalent and is not silently substituted.
6. All P1 convergence/reference/overhead fields already exist in the 20 retained NSESche logs. P1 requires no replay and no new online run.
7. The missing anchor `Cargo.lock` is recorded as a rebuild limitation; preservation of the exact executable avoids changing current formal results.

## Gate result

P0 passes its claim/evidence coverage gate. It does not close a paper section and does not authorize P2/P3 online sampling.

Exactly one next stage is authorized: **freeze and execute P1 as a combined retained-log convergence/reference/overhead analysis plus a separately frozen 300-state exact-small reference/PNE/PoA protocol**. The exact-small generator, state distribution, tie-break, utility equality tolerance, enumeration limits, output schema, and stopping rules must be committed before running it or exposing any optimum.
