# Experiment Tracker: E1 Homogeneous-20 Low V160

| Milestone | Evidence | Status | Paper implication |
|---|---|---|---|
| Frozen baselines | 180 low-load rows, Orion T=1.4741, OCS QPR=.0555772 | COMPLETE | Reuse only; no rerun |
| V155 complete training | T=1.49915; QPR=.0537231 | COMPLETE / NOT CLOSED | 20 rows retained |
| V156--V159 diagnostics | complementary throughput/QPR failures | COMPLETE / FAILED | all valid rows retained; profiles retired |
| V160 causal plan | one-stage completion-proximal short-work preplacement | COMPLETE | Authorizes implementation only |
| V160 implementation | source `67926e6`; 283/283 tests; release `9f298bc7…84cd1` | COMPLETE | Independent binary; formulas unchanged |
| V160 protocol | source `d492d67`; 9/9 V159+V160 tests | COMPLETE | Exact-three result-blind contract sealed |
| V160 references | E09/E18/E20 state-matched tables | COMPLETE | 3/3 canonical, no quarantine |
| V160 diagnostic | exact three NSESche rows | COMPLETE / VALID | Blind audit passed before reveal; all rows retained |
| V160 decision | T=1.4947 and 12/20 pass; QPR=.0544235 below OCS | COMPLETE / FAILED | Retire V160; do not run remaining 17 |
| Fresh confirmation | unopened paired block | NOT AUTHORIZED | Requires complete V160 training pass |

Homogeneous low remains the only active paper section. V160's topology gate
restored throughput but removed V159's QPR gain, so the joint gate remains open.
Middle/high historical evidence stays frozen, and all later sections remain
blocked.
