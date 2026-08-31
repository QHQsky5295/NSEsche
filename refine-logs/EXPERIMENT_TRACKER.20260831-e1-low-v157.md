# Experiment Tracker: E1 Homogeneous-20 Low V157

| Milestone | Evidence | Status | Paper implication |
|---|---|---|---|
| V155 complete training | T=1.49915 > Orion; QPR=.0537231 < OCS | COMPLETE / NOT CLOSED | Retained unchanged |
| V156 three-seed diagnostic | blind audit pass; hybrid T=1.4772 and QPR=.0560685, but T wins=11/20 | COMPLETE / FAILED | All 3 valid rows retained as training evidence; unrestricted pipeline retired |
| V157 plan | terminal-only pipeline-ahead, E09/E18/E20, fixed gates | COMPLETE | Authorizes implementation only |
| V157 implementation | source `5cf1544`; 280/280 tests; release SHA `e80fdfe...1fb8` | COMPLETE | Authorizes exactly 3 references and 3 diagnostics |
| V157 references | exact 3 state-matched references | COMPLETE | E09/E18/E20; attempt-1; no baseline rebuild |
| V157 online diagnostic | exact 3 NSESche rows | COMPLETE | Blind audit passed before reveal; all valid rows retained |
| V157 decision | T=1.4948 and 12/20 wins pass; QPR=.0544338 < OCS .0555772 | COMPLETE / FAILED | V157 retired; remaining 17 and confirmation not authorized |
| Fresh confirmation | paired NSESche/Orion/OCS unopened seeds | NOT AUTHORIZED | Requires a complete E01-E20 training pass first |
| Low publication freeze | catalog/table/figure | NOT AUTHORIZED | Low remains the chapter blocker |

Middle/high historical evidence remains frozen. No later paper section is
authorized while homogeneous low is open.
