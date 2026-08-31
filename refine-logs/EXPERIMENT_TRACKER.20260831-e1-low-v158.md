# Experiment Tracker: E1 Homogeneous-20 Low V158

| Milestone | Evidence | Status | Paper implication |
|---|---|---|---|
| V155 complete training | T=1.49915 > Orion; QPR=.0537231 < OCS | COMPLETE / NOT CLOSED | Retained unchanged |
| V156 broad pipeline diagnostic | QPR pass; throughput paired gate failed 11/20 | COMPLETE / FAILED | All 3 rows retained; profile retired |
| V157 terminal pipeline diagnostic | T=1.4948 and 12/20 pass; QPR=.0544338 fails | COMPLETE / FAILED | All 3 rows retained; profile retired |
| V158 plan | add only nonterminal pipeline requests with remaining work <=5.5 | COMPLETE | Authorizes implementation only |
| V158 implementation | source `bf08566`; 281/281 tests; release SHA `f50472e...c64ab` | COMPLETE | Authorizes exactly 3 references and 3 diagnostics |
| V158 references | exact 3 state-matched references | PENDING | No baseline rebuild |
| V158 online diagnostic | exact E09/E18/E20 NSESche rows | NOT AUTHORIZED | Requires references and blind gates |
| V158 decision | unchanged complete 20-seed hybrid gates | PENDING | Pass may open remaining 17; fail retires V158 |
| Fresh confirmation | paired NSESche/Orion/OCS unopened seeds | NOT AUTHORIZED | Requires a complete E01-E20 training pass |
| Low publication freeze | catalog/table/figure | NOT AUTHORIZED | Low remains the chapter blocker |

Middle/high historical evidence remains frozen. No later paper section is
authorized while homogeneous low is open.
