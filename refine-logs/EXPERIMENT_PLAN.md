# Current NSESche TSC resubmission experiment plan

Execution resumed after the user's updated objective on 2026-09-05.
P6 HPA/scale-down fixtures and the reviewer-v5-only implementation pass 12
directed tests; 100 distinct focused/regression tests passed in total.
See P6_HPA_LIVENESS_FIXTURE_AUDIT.md. Central readiness/batch/telemetry and
remaining P6 integration are still pending; no new performance run exists.
The objective remains throughput/QPR leadership across loads, pursued through
implementation and development evaluation, with valid formal observations retained.

Planning-only review, 2026-09-05: see EXPERIMENT_PLAN_REVIEW.md.
It proposes preserving the original three ablation meanings, separately rerunning
fixed-load capacity scaling, and adding a focused differentiation ablation.
Its 2520-run proposal is not an executed or activated replacement for the V8
runtime protocol below. No simulator/source/data changes were made by this review.

Current normative plan: TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V8.md
Date: 2026-09-05

P6-A is documented; the static review is P6_A_STATIC_REVIEW.md.
Proceed under the user's existing execution authorization to deterministic HPA/
readiness fixtures and the scoped reviewer-v5 implementation. The full P6 pilot
requires the implementation, identity, input, reference and analyzer checks
specified in P6_COMMON_PLATFORM_PROTOCOL_PREREGISTRATION.md.

V8 supersedes V7's forced nonoverlapping workload strata and PreAllSched proposal.
Use fixed P6P01--P6P03 inputs without workload/outcome filtering, central
PreAllDone, common HPA ready demand, idle-to-zero and complete atomic batches.
The HPA diagnosis is a source-supported hypothesis pending targeted verification.

P1 remains permanently frozen in
closed-experiments/P1_convergence_offline_reference_exact_small_PoA/.
P5 is complete and retained: 90/90 runs, 11/12 gates, usable-cohort failure.
No new homogeneous/heterogeneous performance group meets the dual-leading goal.
No P6 performance results existed when this plan was finalized.

Follow homogeneous-20 low -> middle -> high; reuse baselines only under unchanged
common runtime/input/metric identities. Final data retain all valid paired seeds.
Old experiment blocks use 20 runs; scaling runs NSESche only as requested.
The V8 planned formal budget is 2380 online runs, excluding pilot, development,
references and technical fixtures.

Historical P4/P5 and earlier plan files remain evidence; their stage permissions
do not override the current plan. Routine validation and implementation do not
require repeating the user's permission request.
