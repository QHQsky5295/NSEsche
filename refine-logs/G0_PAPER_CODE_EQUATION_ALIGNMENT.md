# G0 论文公式—代码—日志对齐审计

日期：2026-09-03（Asia/Shanghai）

结论：论文 Eqs. (1)--(14) 与 (16)--(20) 的数值计算路径已找到，主体效用、定价、社会福利和反馈表达式与代码一致或可由公开的模拟器定义实例化。唯一直接冲突是 5%/15% guarded 候选对 Eq. (15) 的 bounded-regret 放松；它们复用论文效用，却不执行严格 `arg max`，因此不能作为声称 pure Nash equilibrium 和有限严格改善性质的重投正式实现。正式候选必须限制为严格 best response 及等效用 tie-break。

## 1. 审计输入与边界

- 论文：`（5-12V2）TSC_NSESche_Complete_IEEE_.pdf`，12 页，SHA-256 `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`。
- 审计起点 source commit：`231bca38a043eb31dbc557fc47ca53fca9a0bddc`。
- 算法主文件：`serverless_sim/src/sche/sche_nash.rs`，审计起点 SHA-256 `75629c6de508f4be5ec92814c2a6c20ed5b7f1a806312b9a2c4d84c2d0177651`。
- 论文公式来自 PDF 第 5--6 页，Algorithm 1 来自第 7 页，QPR 定义来自第 8 页。
- 本审计不把旧 PDF 柱值当成数据，不授权新 seed，不把 D01--D60 提升为 corrected-runtime 结果。

状态标签：`EXACT` 表示直接或代数等价实现；`DEFINED` 表示论文符号由公开的模拟器量实例化；`CONDITIONAL` 表示估计或有效域有条件；`CONFLICT` 表示实现会改变公式语义。

## 2. Eqs. (1)--(20) 逐项映射

| Eq. | 论文角色 | 代码路径 | 可审计日志/测试 | 状态与结论 |
|---:|---|---|---|---|
| 1 | `U_ind-sys = U_ind + U_sys` | `utility()` 汇总 `baseline_reward - cost + quality - externality + contribution`；`node_social_welfare_from_aggregates()` 使用同一分解 | `social.utility_components`；`aggregate_social_welfare_matches_player_equations_after_move` | `EXACT` |
| 2 | `U_ind = B - C + Q` | `utility()` 的前三项 | 同上 | `EXACT` |
| 3 | `B_i = U_base(h_ri+h_fc)` | `base_utility * (resource_intensity + function_complexity)` | `run_config.base_utility`、`function_profile.heterogeneity` | `EXACT` |
| 4 | `C_i = p_n(t)(1+h_ri)` | `price * (1.0 + resource_intensity)`；内层使用 `adjusted_prices` | `pricing.price_*`、`social.utility_components.cost` | `EXACT`，Algorithm 1 对 `p`→`tilde p` 的替换已实现 |
| 5 | `Q_i = w_i^q(h_fc+h_nd)/(1+Pressure_n)` | `profile.quality_weight * (...) / (1.0 + node.pressure)` | `function_profile.quality_weight_w_i_q`；`utility_uses_function_level_quality_weight` | `EXACT` |
| 6 | `Pressure_n = u_cpu+u_mem+q_n/q_max` | `update_node_snapshots()`；`q_n` 为 pending+runnable，`q_max=max(1,max_n q_n)` | `cluster.cpu_*`、`memory_*`、`queue_pressure_*`；`queue_pressure_includes_only_pending_and_runnable_tasks` | `DEFINED`；blocked/starting resident 另行记录，不冒充 runnable queue |
| 7 | `U_sys = -E_ext + C_soc` | `-externality + contribution` | `social.utility_components` | `EXACT` |
| 8 | 同节点其他函数的负外部性 | `h_ri_i * Pressure_n * other_impact_sum`，`Impact_j=h_fc_j*h_ri_j`；聚合式扣除 self-pair | `co_location_*`、utility components；`window_externality_does_not_duplicate_runtime_pressure` | `EXACT`；求和域是当前 window 的其他 players，既有运行态已通过 pressure/premium 表示，避免重复计数 |
| 9 | `C_soc = mu(1+h_pi)(1-Util_n)` | `contribution_coefficient * (1+differentiation) * (1-node.utilization)` | `run_config.contribution_coefficient`、function profile、utility components | `DEFINED`；`Util_n` 实例化为归一化 CPU 与 memory 利用率均值 |
| 10 | `P(t)=({p_n},g,beta)` | `PriceSignal` | `pricing` 对象 | `EXACT` |
| 11 | `p_n=p_base(1+Pressure_n)(1+P_node-con,n)` | `build_price_signal()` | `pricing.price_*`、`run_config.base_node_price_internal_units` | `EXACT` |
| 12 | 节点共置拥塞 premium | `mean(h_ri on node) * node.utilization` | `pricing.node_premium_*` | `DEFINED`；在 `Util_n=u_total/u_max` 的实现定义下与论文式代数等价，空集合为 0 |
| 13 | `g=|N|^-1 sum_n(u_cpu+u_mem)` | `build_price_signal().global_load` | `pricing.global_load_g` | `EXACT`；注意这里不是再除以 2 的平均利用率 |
| 14 | 平均有向链路 latency 的归一化网络拥塞 | `update_dynamic_network_proxy()` 按 active transfer 的 `remaining_MB / MBps` 计算有向链路 delay | `network.active_link_delay_proxy_*`、`pricing.network_beta`、`physical_rtt_measured=false` | `DEFINED`；这是 trace-driven simulator 的在线 delay proxy，不是物理 RTT，修订稿必须如实表述 |
| 15 | `s_i*=arg max U_i(s_i,S_-i)` | `best_response()`；strict 分支以 utility 最大值选择，当前节点在数值等效用时优先 | `run_config.strict_best_response`、`eq15_selection_semantics`；候选语义测试 | strict `formula`/`ready_order`/`ready_finish_tie` 为 `EXACT`；四个 guarded 变体为 `CONFLICT`，可选择低于 argmax 的节点 |
| 16 | `Delta=(U*_social-U^Nash_social)/U*_social` | `social_gap()`；仅正 reference 且 current≤reference 时定义 | `social.reference`、`gap`、`feedback_eligible`、invalid/below-current flags；nonpositive tests | `CONDITIONAL`；0/负 reference fail closed，保留基础价格与内层分配 |
| 17 | `U^Nash_social=sum_i U_i(S_Nash)` | `social_welfare()` / node aggregate algebra | social welfare/component logs；aggregate-vs-direct test | `EXACT` |
| 18 | `U*_social=max_S sum_i U_i(S)` | offline builder 使用 canonical greedy、Nash start、deterministic multi-start local improvement 和 geometric-cooling SA | reference state key/source/compute/iterations；exact-small-state test | `CONDITIONAL`；论文已称“estimated offline”，不能把 SA estimate 写成精确全局 optimum |
| 19 | `tilde p_n^(k+1)=p_n(t)[1+gamma beta Delta]` | `apply_price_feedback()` 每轮从 immutable `baseline_prices` 重算，而非递归乘上轮价格 | `pricing.gamma/adjustments/price_*`；`price_feedback_uses_fixed_window_baseline` | `EXACT`；统一正乘子保持节点价格比 |
| 20 | `gamma=r0 tanh(g)` | `price_adjustment_factor * global_load.tanh()` | `run_config.r0`、`pricing.gamma`；price feedback test | `EXACT`；`0≤gamma<r0` 对非负有限 `g` 成立 |

## 3. 跨公式发现

### 3.1 Eq. (15) 是正式重投的硬边界

`guarded_finish_05/15` 与 `guarded_dynamic_finish_05/15` 先构造
`maximum_utility - radius*max(|maximum_utility|,1)`，再在该集合中优先最小化 projected-finish score。它们可能从严格 utility 最大节点移动到较低 utility 节点。这不是等效用 tie-break，而是 Eq. (15) 的 5%/15% bounded-regret relaxation。

审稿回复计划依赖“固定 snapshot、固定价格、每次只接受严格效用改善”的加权势函数论证。guarded 选择会同时破坏：

1. `arg max` 的论文算法语义；
2. “每次移动严格提升个体效用”的证明前提；
3. pure Nash equilibrium 的最终声称。

因此 D21--D60 的 guard 只能保留为历史开发诊断。corrected-runtime 新屏幕若继续沿用论文 Eqs. (1)--(20)，候选应改为既有的三个 strict 变体：`ready_order`、`ready_finish_tie`、`formula`。

### 3.2 reference 与 gap 有两个不同用途

- Eq. (19) 的 loop-local feedback gap：当前内层 equilibrium 按当前 adjusted prices 计算，reference 按该 window 的 immutable baseline state/profile 离线构建。此语义符合 Algorithm 1 “一次加载 reference、每轮使用 adjusted prices”的字面流程，但必须在修订稿明确 reference price basis。
- 跨方法报告的 empirical welfare gap：最终 assignment 重新用 immutable baseline prices 评价，保证不同方法/不同 outer round 可比较；该 re-evaluation 只用于观察，不反馈决策。

当前窗口日志把最终 `social.gap` 用于第二种口径，但没有单独保留每个 outer round 实际驱动 Eq. (19) 的 gap 序列。D61 前应新增 `feedback_gap_per_outer`、对应 assignment hash 和 gamma 序列，避免收敛实验把报告 gap 误当控制 gap。

### 3.3 Eq. (14) 与理论上界必须条件化

代码不把 `delay/l_max` 截断为 1；超过 normalization bound 的链路被计数并保留真实比例。因此 beta 对有限 simulation state 是有限的，但不能无条件声称 `beta≤2`。价格上界证明应显式使用有限 `beta_max` 或假设 `l_ij(t)≤l_max`，同时将实验平台写成 trace-informed discrete-event simulation，不再暗示物理 RTT 测量。

### 3.4 有限迭代预算不是无条件收敛证明

实现有 `max_inner_rounds`、`max_outer_rounds`、oscillation guard 和 infeasible 分支。只有 `inner_stable=true` 且没有 limit/oscillation/infeasible 时，窗口结果才能称为 Eq. (15) 下的 PNE。正式 E9 必须报告 inner/outer round 分布、limit-hit、oscillation、reference unavailable 和 outer fixed-point 达到率；不稳定窗口保留，不得删除或改 seed。

## 4. QPR 口径旁审计

论文第 8 页定义 `QPR=Throughput/(Cost×Latency)`。正式分析代码按 run 先计算：

`throughput[requests/ms] / (cost[simulator internal units/completed request] * latency[ms])`

然后才跨 20 seeds 求均值。零完成、非正 cost/latency 或非有限输入的 QPR 为 undefined 并带原因，不能记成 0 后参与均值。`serverless_sim/src/score.rs` 的 legacy helper 在零完成时返回 0，仅用于旧运行时接口，不是 reviewer pipeline 的 canonical QPR 来源。

## 5. 本次审计形成的冻结决策

1. 论文 Eqs. (1)--(20) 不改；代码日志不再把 guarded 变体标成 strict 全公式对齐。
2. corrected-runtime 正式候选只允许 strict Eq. (15)；guarded D21--D60 永久保留为开发诊断。
3. 公共 cold-start 修复改变全部方法状态轨迹，必须重建 matching offline references；旧 reference 不可跨 runtime 使用。
4. D61 前补齐 feedback-gap-per-outer 观测并冻结 reference price basis、Eq. (14) proxy 定义和 beta 有效域。
5. 用户未显式授权前不捕获 D61--D65 tapes，不启动 Q61--Q80 或 M2。
