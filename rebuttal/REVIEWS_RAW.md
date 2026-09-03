# Raw Reviewer Comments

Source: `C:\Users\99349\.codex\attachments\d883ca48-4785-4e5c-8acf-2ca4a6f6b836\pasted-text.txt`

Source SHA-256: `ecb83fd9a6d874008c2c1684ff2bf866bd3fe8eac26609496bcfccd151ee8b31`

Normalization rule: only the English reviewer comments are copied below. Chinese translations, author analysis, proposed replies, and the unfinished-experiment list remain annotations in the source and are not represented as reviewer text.

## Reviewer 1

### R1-1 — source line 3

> It is not clear “why” the proposed algorithm works from the theoretical standpoint. The reviewer agrees that the algorithm is shown to work in experiments but no theoretical proof about the characteristics of the proposed method is presented. For example, can the authors show convergence to pure NE?

### R1-2 — source line 20

> Along the same line of the comment above, the hand wavy discussions provided in "Boundedness and Practical Stability Discussion." are not enough to show the strong performance of the method. The authors are highly encourages to prove the characteristics of their proposed algorithm mathematically with solid proofs.

### R1-3 — source line 34

> The choice of operations in (19) and (20) seem to be mostly hubristic, which is ok. However, do they lead to unique advantages of the proposed method when mathematical analysis is carried out? In other words, can the mathematical analysis show the advantages of using (19) and (20)?

## Reviewer 2

### R2-1 — source line 54

> The concept of “Nash–Social Equilibrium” is not formally defined. The manuscript combines best-response search with social-utility-based price adjustment, but does not prove the existence of a pure Nash equilibrium or the convergence of the inner and outer loops. A rigorous equilibrium definition and convergence analysis should be provided.

### R2-2 — source line 72

> The offline-estimated social-utility reference in Eqs. (16)–(18) requires clarification because the optimal utility depends on the current workload and system state. The authors should explain how this reference is generated and updated, report its offline computation cost and update frequency, and include any per-window recomputation overhead in the runtime evaluation. Cases where the reference utility is zero or negative should also be handled, and the effectiveness of applying the same multiplicative price correction to all nodes should be justified.

### R2-3 — source line 94

> Several heterogeneity features lack sufficient physical justification. In particular, the resource-intensity metric mainly measures the balance between CPU and memory demands rather than their absolute magnitude, while the network-dependency and differentiation features appear heuristic. The authors should validate or redesign these features and clarify how resource-feasible candidate sets are constructed and how CPU, memory, network, queue, and admission constraints are enforced.

### R2-4 — source line 123

> The current experiments only indirectly demonstrate the claimed burst tolerance and heterogeneous QoS coordination. The authors should evaluate controlled burst patterns and report queue buildup, recovery time, request drops, p95/p99 latency, and SLA violations. Latency-, throughput-, and cost-sensitive function classes should also be evaluated separately rather than using only a shared quality weight and system-wide averages.

### R2-5 — source line 127

> The experimental methodology and metric definitions need further clarification. The workload reaches tens of thousands of requests per second, whereas the plotted throughput is approximately 0–2 RPS, which appears inconsistent. The units and coefficients of cost and QPR should be clearly defined, confidence intervals or statistical tests should be added, and the paper should distinguish physical-cluster experiments from trace-driven simulation.

### R2-6 — source line 143

> The fairness of the baseline comparison and the scalability evaluation should be strengthened. Some baselines jointly optimize scaling, prewarming, or container management, and it is unclear whether their original mechanisms were retained under the common HPA setting. Moreover, increasing the cluster from 20 to 500 nodes while keeping the workload fixed mainly evaluates overprovisioning. The workload should scale with cluster capacity, and scheduler runtime, memory overhead, iteration counts, and timeout rates should be reported.

## Reviewer 3

### R3-1 — source line 161

> The paper assumes that sequential best-response updates converge to a Nash equilibrium, but finiteness and bounded utilities do not guarantee convergence or the existence of a pure-strategy equilibrium. Similarly, bounded price updates do not establish convergence of the outer loop. Formal convergence conditions, iteration bounds, and empirical non-convergence rates should be provided.

### R3-2 — source line 177

> Several components appear ad hoc. For example, the resource-intensity metric mainly reflects the balance between CPU and memory demand rather than their absolute magnitude, while network dependency is inferred without using actual communication volume. The differentiation identifier based on modular arithmetic also lacks a clear physical interpretation. Stronger justification and correlation studies are needed.

### R3-3 — source line 193

> Important implementation details are missing, including node specifications, function profiles, scheduling-window size, HPA configuration, and baseline tuning. The reported workload rates of up to 70,000 requests/s also appear inconsistent with the throughput values of roughly 0–2 RPS. Error bars, significance tests, and workload-proportional scalability experiments should be added.

### R3-4 — source line 209

> The proposed method largely combines handcrafted utilities, congestion pricing, best-response search, and a social-utility reference, but the distinction from existing congestion games, fair pricing, and social-welfare scheduling is not sufficiently established. Comparisons with closely related pricing- and welfare-based schedulers, together with fairness and price-of-anarchy metrics, are necessary.
