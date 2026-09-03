# Submitted-Manuscript Claim Map

Authority: submitted PDF SHA-256 `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`. Page numbers are PDF pages. `remove` applies to the submitted wording; it does not prohibit a new, narrower claim after a preregistered result.

| ID | Page/section | Submitted claim (faithful short form) | Class | Disposition | Evidence/action contract |
|---|---|---|---|---|---|
| C01 | p1 title/abstract | NSESche is burst-tolerant | system capability | pending-preregistered-evidence | retain in title only if P3 controlled-burst gates close; otherwise remove “Burst-Tolerant” |
| C02 | p1 abstract; p2 contribution | experiments on real-world traces | methodology | narrow | “trace-informed discrete-event simulation using distributions derived from public Azure/Alibaba traces,” not direct physical-trace execution |
| C03 | p1 abstract; p2 contribution | high-load QPR +55.4%, throughput +74.3% | quantitative superiority | remove | legacy protocol/20-run mean is unidentifiable; replace only with new cell-specific estimates |
| C04 | p1 abstract | reduces cold-start overhead | performance | pending-preregistered-evidence | report cold-start component under complete P2/P3 cells; no universal wording |
| C05 | p1–2 motivation/contribution | ISCUM explicitly models contention-induced negative externalities | mechanism | keep | formula/code mapping supports “models”; do not infer that the proxy is physically complete |
| C06 | p1–4 | coordinates latency-, throughput-, and cost-sensitive functions | mechanism + effect | narrow | keep mechanism intent; performance effect requires P3 per-class QoS/SLA results |
| C07 | p2, p4–6 | CP-GEN converts pressure/externality into placement price signals | mechanism | keep | Eqs. (10)–(14) and code mapping; disclose Eq. (14) is an active-transfer delay proxy |
| C08 | p4, p6 | inner loop yields a Nash equilibrium | theory | narrow | fixed snapshot/candidate/prices + strict improvements; only stable, non-limit implementation windows qualify |
| C09 | p2, p4, p6 | outer correction steers equilibria toward more efficient outcomes | mechanism effect | narrow | describe as design objective/control signal; empirical welfare movement must be reported, not assumed |
| C10 | p5 feature list | `h_ri` captures aggregate CPU/memory demand | construct validity | narrow | rename as normalized CPU–memory balance/coupling structure; it does not encode absolute magnitude |
| C11 | p5 feature list | `h_nd` quantifies network dependency | construct validity | narrow | communication-sensitivity proxy from `h_ri,h_fc`; not traffic volume or measured dependency |
| C12 | p5 feature list | modular `h_pi` avoids homogeneity and modulates contribution | mechanism | pending-preregistered-evidence | identify as deterministic differentiator; validate effect in P2 ablation/correlation |
| C13 | p6 Eq. (19) | common correction preserves relative price differences | mathematical property | keep | conditional on valid positive multiplier; direct algebra and implementation support it |
| C14 | p6 Eq. (20) | bounded adjustment preserves stability | theory | narrow | `gamma` is bounded; this does not prove outer convergence or performance stability |
| C15 | p6 Eq. (18) | exact optimization is NP-hard; offline SA estimates reference | reference | keep | preserve “estimated”; report profile/state key, cost, update trigger, coverage, and fallback |
| C16 | p6 closed-loop summary | unchanged successive equilibrium terminates and coordination progressively improves | convergence/effect | narrow | keep deterministic unchanged-placement stopping condition; remove monotone/progressive-improvement implication |
| C17 | p7 complexity | `K,T` stay small/few rounds and overhead is low at scale | efficiency | pending-preregistered-evidence | P1 distributions/limits/CPU/RSS; later cross-method/scaling overhead before generalization |
| C18 | p7 setup | experiments run on a 20-node cluster with 8–10 Gbps links measured online | platform | narrow | simulated 20-node topology; 8–10 GB/s configured bandwidth range and dynamic delay proxy, not physical RTT/cluster measurement |
| C19 | p7 workloads | Azure is replayed and Alibaba DAGs are sampled | provenance | narrow | disclose empirical-CDF/synthetic tape construction and DAG mapping; avoid “raw trace replay” |
| C20 | p7 workloads | low/middle/high are 1k–5k, 5k–15k, 15k–70k req/s | workload quantity | remove | frozen Q61–Q80 tapes measure about 1.925k/2.526k/6.970k req/s; publish measured distributions |
| C21 | p8 metrics | all metrics average 20 independent runs | statistics | remove | legacy figures do not retain 20 independent runs; revised cells use 20 paired seeds with run-level QPR and CIs |
| C22 | p8 hyperparameters | fixed centers are best and nearby values show low sensitivity | tuning/robustness | pending-preregistered-evidence | rerun P2 E7 with frozen grid and disclose selection boundary; no old single-value proof |
| C23 | p8 ablation | full NSESche generally best in all four metrics | causal/component effect | remove | legacy Fig. 5 is unreplayable single constants; replace with P2 E5 estimates, including externality and coordination distinctions |
| C24 | p9 comparison | low/high throughput is highest; average +92.2%, low +157.2%, high +74.3% | quantitative superiority | remove | formal low now ranks 3; middle/high unmeasured against all baselines |
| C25 | p9–10 comparison | lowest cost across all loads; average cost reduction 45.3% | quantitative superiority | remove | current evidence supports only low-cell cost value/rank; future wording must be cell-specific |
| C26 | p10 comparison | QPR highest low/high and +55.4% high | quantitative superiority | remove | formal low QPR ranks 4 and is -9.26% vs FaaSRank |
| C27 | p10 resources | high throughput is highest without higher resource use | causal performance | remove | requires complete paired high-load resource/performance evidence; do not infer causality from utilization bars |
| C28 | p10 decision latency | only +32/+7/+24% vs Random and lowest among strong schedulers | overhead superiority | pending-preregistered-evidence | legacy values lack reproducible run bank; regenerate from frozen timing logs/cells |
| C29 | p10 heterogeneous | higher throughput/QPR and more stable in heterogeneous cluster | scalability/robustness | pending-preregistered-evidence | P2 three heterogeneous cells, 20 paired seeds; one fixed seed is insufficient |
| C30 | p10–11 scaling | fixed-workload 20→500 nodes proves horizontal scalability | scalability | narrow | rename as fixed-workload capacity sensitivity; proportional scaling is the actual R2-6/R3-3 test |
| C31 | p11 conclusion | real-world traces and large-scale clusters show improved T/QPR, especially high | overall performance | remove | replace after P2/P3 with bounded scene-specific synthesis; the current study is simulation, not physical large-scale clusters |

## Mandatory global edits

1. Replace `RPS` labels around 0–2 with `requests/ms`, or convert both arrivals and throughput to requests/s.
2. Replace “physical/real cluster” implications with the trace-informed discrete-event simulator description.
3. Define cost as simulator-internal normalized resource consumption per completed request and state that it is not currency.
4. State that current complex baselines are placement-level adaptations under common HPA/lifecycle, not full-system reproductions.
5. Put all revised quantitative claims behind source CSVs, 20 paired seed points, and uncertainty intervals.
