# Reviewer-to-Evidence Matrix

| Reviewer issue | Existing reusable evidence | Smallest additional evidence | Planned manuscript change | Stage / gate |
|---|---|---|---|---|
| R1-1 | complete potential proof; 20 retained solver streams; 300 exhaustive states | none | insert assumptions, zero-complexity boundary and finite bound | P1 complete / writing ready |
| R1-2 | finite-improvement proof and explicit outer-loop non-claim | none | replace hand-wavy boundedness text | P1 complete / writing ready |
| R1-3 | proved common-price ratio invariance and bounded saturating gain | none | insert properties and limitations | writing ready |
| R2-1 | formal inner constrained-PNE definition; strong joint fixed-point definition; P1 rates | none | distinguish proved inner theorem from observed outer placement stability | P1 complete / writing ready |
| R2-2 | 120-table build/lookup/fallback audit; 300-state exact reference comparison | none | insert state key, rebuild trigger, costs, invalid cases and heuristic boundary | P1 complete / writing ready |
| R2-3 | formula map, function profiles, queue/candidate telemetry, shared feasible placement helper | feature correlations + revised four-part ablation using P2 logs | correct feature semantics and enumerate hard/soft admission constraints | P2 E5/E7 reuse |
| R2-4 | metric schema already records queue, tails, drops | 600 controlled-burst + 200 QoS/SLA runs | add controlled-pattern and per-class subsections | P3 |
| R2-5 | formal run-level T/cost/latency/QPR and paired low-cell statistics | remaining P2 cells with CIs/tests | correct units, cost meaning, QPR aggregation, and simulator status | writing + P2 |
| R2-6 | common HPA/lifecycle contract; placement-only baseline inventory; process/scheduler telemetry | P1 overhead + 1,200 proportional-scaling runs | disclose retained vs controlled baseline mechanisms; rename old fixed-workload scaling | P1/P2 |
| R3-1 | complete theorem/bound plus retained empirical termination distribution | none | insert theorem and non-convergence table | P1 complete / writing ready |
| R3-2 | feature telemetry and deterministic formulas | same feature correlation/ablation block as R2-3 | proxy language and limitations | P2 E5/E7 reuse |
| R3-3 | full frozen manifests/configs; actual tape arrival rates | remaining P2 statistics + proportional scaling | setup table; event-driven scheduling-cycle definition; remove 70k mismatch | writing + P2 |
| R3-4 | mechanism decomposition and ten-method placement comparison | exact-small PoA + 80 close-comparator runs + QoS fairness reuse | sharpen congestion-game/fair-pricing/welfare boundary | P1/P3 |

## Coverage decision

Every atomic issue has a named response and evidence source. The matrix deliberately reuses blocks across overlapping comments: one P1 convergence product serves four theory comments; one P2 feature block serves R2-3/R3-2; one P2 proportional-scaling block serves R2-6/R3-3; and one P3 QoS block supplies both R2-4 and the fairness part of R3-4. No native-mode, fault-injection, extra stress, or soak experiment is required by this coverage map.

## Evidence not interchangeable

- Formal Q61–Q80 low results answer only homogeneous-20 low performance and retained-log questions.
- The already-built middle/high references are inputs, not online method-comparison outcomes.
- Development D/D71–D75 evidence cannot fill a formal performance cell.
- Exact-small PoA validates constructed small games; it does not turn large-state SA estimates into exact optima.
