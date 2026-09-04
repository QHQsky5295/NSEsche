# Reviewer Issue Board

Status labels: `ready-writing` means the evidence/derivation already exists but manuscript text is not yet revised; `partial` means some evidence exists; `open-experiment` means a preregistered experiment is still required.

| ID | Core request | Response mode | Existing evidence | Missing evidence or manuscript action | Status |
|---|---|---|---|---|---|
| R1-1 | Explain why the method works; PNE convergence | proof + empirical convergence | complete fixed-snapshot weighted/lexicographic potential proof; 19,509-window and 300-game P1 evidence | insert proof and assumptions into revised manuscript | ready-writing |
| R1-2 | Replace hand-wavy boundedness with solid analysis | proof/claim correction | finite-improvement theorem and explicit exponential state-change bound; outer non-claim | replace submitted boundedness paragraph | ready-writing |
| R1-3 | Justify mathematical advantages of Eqs. (19)–(20) | derivation | bounded/monotone/saturating gain, relative-price invariance, nonrecursive bound and limitations proved | insert conservative derivation; make no uniqueness claim | ready-writing |
| R2-1 | Define Nash–Social Equilibrium; analyze both loops | definition + proof + empirical rate | inner constrained PNE and strong joint fixed point separated; 97.396% outer placement stability reported | reserve joint-equilibrium term for the strong definition | ready-writing |
| R2-2 | Explain reference generation/update/cost/nonpositive cases/common multiplier | disclosure + P1 exact-small | complete 120-table cost/lookup/fallback audit and exact-small reference error distribution | insert construction and update-trigger paragraph/table | ready-writing |
| R2-3 | Validate feature meanings and feasible candidate construction | semantic correction + ablation/validation | formula/code map; function-profile and candidate/queue logs; shared placement-feasibility path | rename `h_ri` as CPU–memory balance/coupling proxy; disclose `h_nd`/`h_pi` as proxies; document CPU/memory/container/network/queue admission; P2 feature ablation/correlation | open-experiment |
| R2-4 | Controlled burst, queue/recovery/drop/tails/SLA; per-class QoS | new experiment | queue peak/area, drops, p95/p99 fields already supported | P3 controlled burst 600 runs and QoS/SLA/fairness 200 runs | open-experiment |
| R2-5 | Clarify units, cost/QPR, statistics, simulator vs physical cluster | disclosure + complete statistics | canonical req/ms, latency ms, internal cost/request, run-level QPR; formal paired low-load data | rewrite platform as trace-informed discrete-event simulation; remove currency implication; P2 cell-wise CIs/tests | partial |
| R2-6 | Baseline fairness, proportional scaling, overhead | boundary disclosure + P1/P2 | common HPA/lifecycle/candidate set; placement-only baseline adaptations; scheduler/process telemetry | explicitly say this is not full end-to-end reproduction; P1 NSESche overhead; P2 workload-proportional 20/100/500 study and baseline overhead | open-experiment |
| R3-1 | Conditions, iteration bounds, empirical non-convergence | proof + P1 | assumptions, finite-improvement bound, four-round runtime boundary, 2.604% outer-nonstable and 0.0461% cap-hit rates | insert theorem and empirical termination table | ready-writing |
| R3-2 | Stronger justification and correlation studies for ad-hoc features | semantic correction + validation | exact formulas and function-profile telemetry | avoid physical interpretation beyond observables; preregister correlation targets and four-way ablation in P2 | open-experiment |
| R3-3 | Setup details, unit mismatch, error bars, proportional scaling | disclosure + P2 | frozen config/manifests; measured formal arrival rates; paired-run framework | publish config table; replace 70k label; CIs/tests; proportional scaling | open-experiment |
| R3-4 | Distinguish prior paradigms; close comparators, fairness, PoA | related-work revision + P1/P3 | mechanism decomposition; existing ten-method placement comparison | exact-small PoA; P3 CP-BR/OnSocMax comparators; QoS fairness; precise related-work boundary | open-experiment |

## Theory correctness constraints

The planned weighted-potential argument is defensible only for a fixed scheduling snapshot, fixed candidate sets, fixed adjusted prices, and strict utility-improving unilateral moves. Multiplying player `i`'s utility change by positive `h_fc,i` symmetrizes the pairwise externality term; `h_fc=0` players require a separate boundary argument because zero weights are not valid weighted-potential weights. The bound is finite but can be exponential: at most `prod_i |S_i| - 1` strict state changes before a repeat is impossible. The implemented four-round inner cap means only windows that actually satisfy the stability gate can be called PNE windows.

No corresponding proof currently establishes convergence or existence of a fixed point for the outer deterministic mapping. A bounded multiplier proves numerical boundedness, not outer convergence. The response must report observed fixed-point/limit/oscillation rates and define “Nash–Social Equilibrium” conditionally when both inner PNE and outer placement invariance hold.

## Evidence integrity constraints

- The old PDF's 55.4%/74.3% and other bar values are not recoverable 20-seed statistics.
- Q61–Q80 low-load results cannot be replaced, filtered, or relabelled as development results.
- G2–G7 may explain mechanism behavior but cannot support main-paper performance rankings.
- New claims become available only after their named preregistered gate passes.
