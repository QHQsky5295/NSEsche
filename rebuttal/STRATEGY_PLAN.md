# Rebuttal Strategy Plan

## Response thesis

The strongest resubmission is not “the old claims were correct after more seeds.” It is: the revision formalizes the conditional equilibrium structure, binds the implementation to the equations, replaces unreproducible legacy bars with paired evidence, and adds only the controlled experiments explicitly needed to test burst, QoS, scalability, fairness, and welfare claims.

## Ordered response clusters

### 1. Inner equilibrium and outer fixed point

Address R1-1, R1-2, R2-1, and R3-1 together in the manuscript, while answering each reviewer separately. Add a formal game definition, fixed-snapshot assumptions, a weighted-potential proposition for positive-complexity players, the zero-complexity boundary, and a finite-improvement bound. Then explicitly separate this theorem from the budgeted implementation and from the outer loop. Use P1 logs for inner/outer rounds, stability, limit hits, oscillations, and non-fixed rates.

### 2. Price feedback and offline reference

Address R1-3 and R2-2 with properties that actually follow from Eqs. (19)–(20): common positive multiplication preserves baseline node-price ratios; `tanh(g)` is monotone and bounded; every round is re-anchored to baseline prices. State the valid domain and fallback for nonpositive references. Report the existing 120-table build cost and P1 coverage/lookup overhead. Use exact-small states to quantify SA reference error and exact PoA without calling large-state estimates exact optima.

### 3. Feature semantics and candidate feasibility

Address R2-3 and R3-2 without changing submitted equations. Correct the names and claims: `h_ri` is a normalized CPU–memory balance/coupling proxy, `h_nd` is a scheduler-visible communication-sensitivity proxy, and `h_pi` is deterministic differentiation rather than a physical measurement. Add an explicit candidate-set/admission paragraph. Validate contribution through preregistered correlations and the P2 ablation block; do not retrofit a physical interpretation.

### 4. Experimental methodology and units

Address R2-5 and R3-3 before presenting any result. Describe a trace-informed discrete-event simulator, not a physical OpenFaaS cluster. Report arrival rates in requests/s, throughput in requests/ms (or consistently convert both), latency in ms, and cost as simulator-internal normalized resource consumption per completion. Compute QPR within each run and then aggregate. Replace every legacy bar with paired 20-seed points, uncertainty intervals, and multiplicity-controlled tests.

### 5. Baseline boundary, overhead, and scalability

Address R2-6 and R3-3 by stating that the comparison isolates placement/node-selection under common HPA, cold-start, and container lifecycle. For Orion/Jiagu/OCS and similar systems, name which placement logic is retained and which native scaling/prewarming component is controlled; do not imply complete end-to-end reproduction. Reuse P1 overhead logs, then run workload-proportional 20/100/500-node scaling only after the main cells remain scientifically worthwhile.

### 6. Burst and heterogeneous QoS

Address R2-4 with the minimum controlled P3 design: three fixed burst patterns and a balanced three-class QoS/SLA experiment. Report queue peak/area, recovery time, drops, right-censoring, p95/p99, class throughput/latency/completion, violation rates, and fairness. “Burst-tolerant” remains conditional until this block closes.

### 7. Novelty, close comparators, fairness, and PoA

Address R3-4 by distinguishing the control role of NSESche prices from end-user fair pricing and distinguishing inner individual stability from direct centralized welfare maximization. Add exact-small PoA in P1 and two placement-compatible pricing/welfare comparators plus fairness in P3. Close-comparator names in V4 (`CP-BR`, `OnSocMax`) are protocol labels, not claims of reproducing a named external system; their definitions must be frozen before execution.

## Claim policy

- Delete the old high-load 55.4% QPR and 74.3% throughput numbers unless the exact same quantities are regenerated under the new frozen protocol.
- Replace universal “best/highest/outperforms” language with cell-specific ranks and intervals.
- Keep mechanism-description claims that are directly true by construction, but distinguish them from demonstrated performance effects.
- Keep “Nash–Social Equilibrium” only with a formal conditional definition; do not use it as shorthand for unconditional outer convergence.
- Keep the equations fixed for this resubmission path. Additional propositions, definitions, fallback cases, and observation-only metrics may clarify them but cannot silently alter scheduling decisions.

## Stage gates

1. P1 retained-log extraction and exact-small preregistration.
2. P1 result audit; stop if equation/exact enumerator/reference consistency fails.
3. P2 homogeneous middle/high, then ablation/parameter, heterogeneous cells, and proportional scaling, each with complete-cell stopping rules.
4. P3 burst, QoS/fairness, and pricing/welfare comparators only if P2 still supports a meaningful systems contribution.
5. Final response-letter drafting only after manuscript changes, figures, source tables, and venue formatting constraints are available.
