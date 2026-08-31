# Experiment Tracker: E1 Homogeneous-20 Low V161

| Milestone | Evidence | Status | Paper implication |
|---|---|---|---|
| Frozen baselines | 180 low-load rows; Orion T=1.4741; OCS QPR=.0555772 | COMPLETE | Reuse only; no rerun |
| V155 complete training | T=1.49915; QPR=.0537231 | COMPLETE / NOT CLOSED | 20 rows retained |
| V156--V160 diagnostics | complementary throughput/QPR failures | COMPLETE / FAILED | all valid rows retained; profiles retired |
| V161 causal plan | consecutive-frame realized-service parent-tail gate | COMPLETE | exact E09/E18/E20 only |
| V161 implementation | source `8e2ce69`; 286/286 Nash tests; release `426a3a53…b279d` | COMPLETE | formulas, HPA and metrics unchanged |
| V161 protocol | source `689945f`; V160+V161 tests 9/9 | COMPLETE | result-blind exact-three contract sealed |
| V161 references | E09/E18/E20 state-matched tables | COMPLETE | 3/3 attempt-1 canonical |
| V161 diagnostic | exact three NSESche rows | COMPLETE / VALID | QC pass; blind audit sealed before reveal |
| V161 decision | T=1.4948 and 12/20 pass; QPR=.0544279 below OCS | COMPLETE / FAILED | retire V161; do not run remaining 17 |
| Next low-load mechanism | first-principles analysis of earlier bounded prewarm | IN PROGRESS | requires a new committed plan before any run |
| Fresh confirmation | unopened paired block | NOT AUTHORIZED | requires a complete low-load training pass |

Homogeneous low remains the only active paper section. V161 preserved
throughput but its parent-tail trigger was still too late to raise QPR. The
middle/high historical groups stay frozen, and every later paper section stays
blocked.

