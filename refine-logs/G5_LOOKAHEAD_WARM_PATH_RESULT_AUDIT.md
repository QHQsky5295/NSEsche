# G5 lookahead/warm-path result audit

Date: 2026-09-04

Status: `complete_lookahead_candidate_preregistration_authorized`

## Decision

The one authorized G5 invocation completed on all 50 frozen homogeneous-low
D71--D75 runs.  The lookahead path passes every preregistered condition.  The
warm-bypass-dominant path fails.  This audit therefore authorizes only a
separate preregistration for one `PreAllSched` NSESche candidate that retains
strict Eq. (15).  It does not authorize implementation, sampling, formal
progression, figures, or paper claims.

No simulator ran, no source changed, and no seed, request, or function was
discarded.  Full completed-function and common-completion views are both
retained.

## Product receipts

The report document SHA-256 is
`d99dbedf368c896c466dea41b5da87c6454c6a51fbb56d0550f2e995db3b911a`.

| Product | SHA-256 |
|---|---|
| `g5_lookahead_warm_path.json` | `6ffa0e4ea8d064eba625d3738c03ed2d934de0365fe5e844bb9d6937ae7c44ca` |
| `g5_function_timing_runs.csv` | `45f9e8988b0c184630cfaf8e669dc24945908dc7ecf877c3978dc7f888c883b3` |
| `g5_function_timing_pairs.csv` | `b92ee84cb8817d96388fc00011b4ce925109f425164c7ee5b8a308eadf43cec4` |
| `g5_function_timing_aggregates.csv` | `1c532536b7ca648f3e81d5660086717d9299114bd95def2ef12e013a30438cec` |
| `g5_nash_warm_accounting.csv` | `e1b3d58ccb281bc0c82ae781e0ef8c13150ab3b70721f81f2e38b6d7540e21c2` |

## Lookahead result

C0 never binds a completed function before its `ready_schedule_frame`: its
pre-ready-bound share, mean lead, and mean startup overlap are zero in all five
seeds.  The same-admission FaaSRank-P control is also exactly zero on all three
measures.  In contrast, all four source-declared lookahead comparators pass all
G5 conditions in both full and common-completion cohorts.

Five-seed unweighted run means are:

| Method | Pre-ready-bound share | Mean lead (ms) | Mean startup overlap (ms) | Post-ready cold wait (ms) |
|---|---:|---:|---:|---:|
| NSESche C0 | 0.0000 | 0.0000 | 0.0000 | 23.7249 |
| FaaSRank-P | 0.0000 | 0.0000 | 0.0000 | 17.3880 |
| OCS | 0.3077 | 22.8988 | 3.7291 | 9.7481 |
| Hiku | 0.3142 | 22.1861 | 4.2394 | 10.4029 |
| Jiagu | 0.3427 | 24.0962 | 6.1327 | 11.4011 |
| Orion | 0.3352 | 32.1097 | 7.8863 | 16.8480 |

For OCS, Hiku, Jiagu, and Orion, the baseline-minus-C0 pre-ready-bound, lead,
and overlap differences are positive in 5/5 seeds in the full cohort and again
in 5/5 seeds on common completed function keys.  Their full-cohort mean overlap
advantages are respectively 3.7291, 4.2394, 6.1327, and 7.8863 ms; every paired
95% t interval for overlap remains above zero.  Positive overlap advantage and
positive C0 post-ready-cold-wait disadvantage co-occur in 5/5 seeds for all
four comparators.

Common-completion post-ready cold-wait differences are also positive in 5/5
seeds for all four.  Their five-seed mean differences are +7.2928 ms (OCS),
+7.4652 ms (Hiku), +7.5629 ms (Jiagu), and +3.9414 ms (Orion).  The small-sample
95% t intervals for the first three still include zero; Orion's does not.  This
uncertainty is retained and is why the result supports a development candidate,
not a causal or publication claim.

FaaSRank-P has no lead or overlap advantage in any seed yet retains a +6.3369
ms full-cohort and +2.5316 ms common-completion cold-wait advantage.  This
negative control shows that lookahead is not a complete explanation of every
baseline gap; FaaSRank-P's explicit warm-affinity/resource scoring remains a
separate mechanism.  It also prevents claiming that `PreAllSched` alone must
make NSESche best.

## Warm-bypass result

All assignment and dispatch invariants pass.  Across the five C0 runs, selected
non-warm decisions are entirely starting-container selections; selected cold/
non-running decisions and selected-lower-utility-than-warm cases are zero.
Warm bypass exists and selected-minus-best-warm paper utility is positive in
every seed, as expected under strict Eq. (15).

However, warm bypass is not dominant under the frozen rule:

- bypass explains at least half of non-warm selections in only 3/5 seeds, not
  the required 4/5;
- the pooled `B/N` share is 0.5359, which passes only the pooled subcondition;
- completed-only command coverage is 0.8907, 0.0694, 0.1600, 0.5180, and
  0.2630 for D71--D75, so four seeds fail the 80% identifiability threshold;
- in 0/5 seeds is the same-frame completed-function cold-event rate higher in
  bypass-active than bypass-inactive non-warm windows.  The observed direction
  is the reverse in every seed.

The last comparison is explicitly completed-only and window-level.  It is not
used to infer that bypass prevents cold starts; it only rejects the proposed
dominant-bypass attribution.

## Mechanism implication

The supported intervention is narrow: change only when a request/function
becomes an active game player, from parents-completed (`PreAllDone`) to
parents-scheduled (`PreAllSched`).  Once admitted, feasible candidate
construction, Eqs. (1)--(20), strict Eq. (15) best responses, social reference,
price feedback, convergence checks, and dispatch validation must remain
unchanged.  This lets a descendant placement/container start overlap with
upstream execution while retaining its parent's known placement for subsequent
data-locality state.

The candidate must be treated as an explicit operational refinement in the
revised manuscript.  It cannot be silently substituted for the previously
evaluated C0 or described as if it were present in the rejected submission.

## Mainline state

The homogeneous-low main comparison remains open: the retained formal Q61--Q80
cell failed, G3-E0 failed, and G5 supplies only a new development hypothesis.
Homogeneous-middle/high, heterogeneous cells, scalability, convergence,
offline-social-utility reference, ablation, and any reviewer-facing figures
remain blocked by the ordered main gate.  The next permitted action is a
separate candidate/protocol preregistration; no run is authorized by this
audit.
