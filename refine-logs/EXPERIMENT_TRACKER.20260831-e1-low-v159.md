# Experiment Tracker: E1 Homogeneous-20 Low V159

| Milestone | Evidence | Status | Paper implication |
|---|---|---|---|
| Frozen baselines | 180 low-load rows, Orion T=1.4741, OCS QPR=.0555772 | COMPLETE | Reuse only; no rerun |
| V155 complete training | T=1.49915; QPR=.0537231 | COMPLETE / NOT CLOSED | 20 rows retained |
| V156 diagnostic | QPR pass; throughput paired gate failed | COMPLETE / FAILED | 3 rows retained |
| V157 diagnostic | Throughput pass; QPR mean failed | COMPLETE / FAILED | 3 rows retained |
| V158 diagnostic | QPR pass; throughput paired gate failed 11/20 | COMPLETE / FAILED | 3 rows retained; profile retired |
| V159 plan | short-work pipeline only when queue density <8 | COMPLETE | Authorizes implementation only |
| V159 implementation | source `585801c`; 282/282 tests; release `2c23991a…4514` | COMPLETE | Independent binary; formulas unchanged |
| V159 protocol | exact three-run product and result-blind work/queue audit | COMPLETE | No performance reveal before audit seal |
| V159 references | exact E09/E18/E20 state-matched tables | PENDING | Authorized only after protocol receipt |
| V159 diagnostic | exact three NSESche rows | NOT AUTHORIZED | Requires references and blind audit |
| V159 decision | unchanged complete 20-seed joint gate | PENDING | Pass may open remaining 17 |
| Fresh confirmation | unopened paired block | NOT AUTHORIZED | Requires complete V159 training pass |

Homogeneous low remains the only active paper section. Middle/high historical
evidence stays frozen, and all later sections remain blocked.
