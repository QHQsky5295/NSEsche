# NSESche TSC 拒稿重投最佳实验执行计划

日期：2026-09-03（Asia/Shanghai）

状态：G0 已定位并修复公共 cold-start 转换饥饿，完成 Eqs. (1)--(20) 对齐和 outer-feedback 控制链日志；等待授权进行 strict-Eq.15 corrected-runtime 重新冻结与新 bank 资格验证；M2 尚未启动

## 1. 先给结论

1. **旧实验必须重跑。** 最终 NSESche binary、统一 workload tape、离线社会效用参考、QPR 计算和审稿日志必须属于同一个冻结协议；缺少原始数据时，不能把旧 PDF 柱值当作新统计数据。
2. **论文 Eqs. 1--20、效用函数和 QPR 定义冻结。** 代码若与论文冲突，优先把代码修正到论文定义，而不是用新实验反向改论文公式。
3. **论文未写明的运行级机制可以优化，但必须公开。** 只能在新开发族预注册前修改；一旦选定，必须跨负载、跨拓扑、跨 baseline 比较使用同一实现，不得隐藏为“实现细节”。
4. **旧柱值是复现实验锚点，不是调参目标。** 用独立 pilot 排查单位、时间窗、负载映射、拓扑和 HPA 差异，目标为旧 PDF 的 ±15%；正式结果不得为了贴柱值而删 seed、换 seed 或改指标。
5. **QPR 与吞吐最优通过机制开发实现，不通过结果筛选实现。** 允许用开发 bank 比较预注册候选；正式 bank 必须独立、固定、全部保留。QC-valid 的不利结果也属于实验结果。

## 2. 不可变边界

以下项目在新的 M1 候选族开始前一次性冻结，并在全部正式实验中保持不变：

- 论文 Eqs. 1--20、符号、单位、效用项及 QPR 公式；
- `1 frame = 1 ms`、主比较 1,000 ms 固定观察窗及其 throughput estimand；
- low/middle/high 的公共 workload profile、同 tape 配对规则和 DAG 生成规则；
- homogeneous/heterogeneous 节点分布、网络模型、cold-start 模型和公共 HPA；
- 十种方法的版本、参数来源、候选集、tie-break 和超时策略；
- 每个正式 cell 的 20 个配对 seeds、统计方法、图表顺序和失败处理；
- 离线 reference 的状态键、构建算法、校验规则和不可用状态处理；
- 所有日志 schema、QC、canonical promotion、哈希账本和重试规则。

技术失败只允许用**完全相同的 run spec 和 seed**重试，并保留失败收据。QC-valid 的零完成、低吞吐或低 QPR 不得重跑、替换或删除。

## 3. G0：公式—代码—模拟器一致性审计

在新候选开发前完成以下阻断项：

1. 建立论文公式到 `sche_nash.rs` 代码路径、变量、单位和日志字段的逐项映射；所有差异分类为论文一致、纯实现 tie-break、运行保护或错误。
2. 对 task→container→node 的执行模型做一节点合成测试，验证 CPU work conservation、容器内并发分配、starting/running 状态转换和 completion 触发。
3. 判定当前数万 running tasks/百余 running containers 是预期过载还是公共模拟器缺陷：
   - 若是公共缺陷，修复后必须对**全部方法**生效，并重新做协议冻结；
   - 若是预期过载，只允许在 NSESche 中新增公开的服务可执行性/准入机制。
4. 固定旧 PDF 数字提取表：旧值、图号、单位、估读误差、对应新 cell 和可接受解释，不把旧值写进调度器。
5. 完成确定性、公式对齐、reference、QPR、零完成和日志完整性测试后，冻结 source commit、binary SHA-256 和 protocol commit。

G0 未通过时不捕获新开发 tapes。

G0 当前结论：高负载零完成的首要原因是公共执行器先填充 runnable-task
内存、后检查 starting→running 的额外容器内存，导致 cold start 长期停在
`left_frame == 1`。公共修复已在 commit `16c32c2` 实现并完成同 tape 技术
回归；详见 `G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md`。由于状态轨迹已经
改变，旧 reference 与 D01--D60 性能结果不能用于 corrected-runtime 正式统计。

公式审计进一步确认，四个 5%/15% guarded 变体会在 bounded-regret 集合内
选择低于最大论文效用的节点，因此不满足 Eq. (15) 的严格 `arg max`，也不满足
审稿回复所需“每次移动严格改善效用”的势函数证明前提。它们只能保留为历史
开发诊断，不能进入重投正式候选；详见
`G0_PAPER_CODE_EQUATION_ALIGNMENT.md`。

## 4. G1：corrected-runtime 重新冻结与资格验证（需用户显式授权）

### 4.1 机制方向

在确认公共模拟器缺陷后，不应立即增加 NSESche-specific
serviceability/admission 机制。先保持论文公式不变，并只使用现有的三个
strict-Eq.15 候选：

- C0：冻结的 `ready_order` 控制；
- C1：`ready_finish_tie`，只在数值等效用时使用 readiness/finish tie-break；
- C2：`formula`，原始 request-function 收集/排序语义。

三个候选都必须记录 `strict_best_response=true`；任何非零
`utility_guard_relative_regret` 的 binary 不得进入 corrected-runtime screen。

公共 cold-start 修复对十种方法统一生效。只有 corrected-runtime 新 bank
仍提供独立证据时，才能另行预注册新的机制；不得从旧 D41--D45 结果直接
推出 NSESche-specific 补丁。

### 4.2 开发屏幕

- 新 bank：D61--D65，只用于候选选择；不进入正式论文统计。
- 矩阵：`3 candidates × 2 topologies × 3 loads × 5 paired seeds = 90 runs`。
- 先为 corrected runtime 构建逐候选、逐状态匹配的全新 offline reference；所有候选共享逐字节相同 tape 和公共配置。
- 冻结 commit `cafb7c5` 已补齐的 `solver.outer_feedback_trace`；技术回放必须证明 control gap、outer assignment hash、gamma 与价格乘子可由日志重算，报告用 empirical gap 与 Eq. (19) 控制 gap 不得混列。
- 先决条件：每个固定 row 均有可定义的 throughput、latency、cost/completion 和 QPR；若出现 QC-valid 的不可定义 QPR，候选族 fail closed。
- 冻结选择：六 cell 的 throughput 与 QPR 相对 C0 改善做全局 maximin；随后检查六 cell 双指标方向、seed-level collapse、queue、fan-in 和非收敛。
- 只生成一个 immutable selection receipt；失败不解释为“再补几个好 seed”。

### 4.3 独立正式资格验证

- 正式 bank：Q61--Q80，与 D61--D65 独立。
- 按论文旧章节顺序执行十种方法的六个 E1 cell，共 `10 × 6 × 20 = 1,200 runs`。
- 通过门槛：最终 NSESche 在六个 cell 的 mean throughput 和 mean QPR 均为第一，全部 row QC 完整，且没有协议例外。
- 这 1,200 runs 若通过即直接成为 E1 正式主结果，**不再重复运行同一矩阵**；若失败则停止，不启动后续 M2/M3。

## 5. G2：旧论文实验按章节主线重跑

执行依赖允许 reference 先构建，但在线运行与论文闭口严格按以下顺序：

1. **20 节点 homogeneous low**：`10 methods × 20 paired seeds = 200`。
2. **20 节点 homogeneous middle**：200。
3. **20 节点 homogeneous high**：200。
4. **超参数 E7**：中心加四个轴向邻点，中心复用主比较，新增 240；投稿中心须在 throughput--QPR Pareto 前沿。
5. **消融 E5**：四个消融 × 三负载 × 20，新增 240；Full 复用主比较。
6. **资源、开销与初步收敛**：直接复用以上日志生成 Fig.7/8，不重复在线运行。
7. **20 节点 heterogeneous low→middle→high**：`10 × 3 × 20 = 600`；不得为异构场景重新换机制。
8. **100/500 节点同比负载扩展**：5×/25× workload，`10 × 3 × 2 × 20 = 1,200`。

每个旧图均生成 `old_pdf_alignment.csv`，包含旧 PDF 值、新均值、95% CI、相对偏差、单位/协议差异和解释。±15% 仅作为复现诊断线：超过时回查公共协议，不能把正式 seed 或方法参数调到贴合旧柱。

## 6. G3：审稿人明确要求的新证据

1. **Burst E3**：homogeneous-20、middle 基准，三种固定 burst；`10 × 3 × 20 = 600`。到达结束后最多 drain 4,000 ms；恢复失败按右删失保留。
2. **QoS E4**：heterogeneous-20、middle，三 QoS 类各 1/3；`10 × 20 = 200`。报告 class throughput、latency、cost、completion、SLA violation、Jain index 和最差 10% satisfaction。
3. **Pricing/Welfare E6**：heterogeneous middle/high，新增 CP-BR 与 OnSocMax，80 runs；其余方法复用 E1。
4. **Exact PoA**：3 节点、4/6/8 players，各 100 状态，共 300 个 exact 状态；大规模只称 empirical welfare gap。
5. **Feature E8**：复用 E1/E3/E4，检验 resource intensity、network dependency、differentiation 与 contention/data-wait/placement dispersion 的 Spearman 关系。
6. **Reference/Convergence E9**：reference table 是所有 NSESche run 的前置依赖；收敛曲线、inner/outer rounds、limit-hit、offline-reference coverage/误差和开销直接复用正式日志，再补小规模 exact-reference 对照，不重复完整在线矩阵。

这样既回答审稿人关于“为什么有效、是否收敛、社会效用参考是否可信”的问题，又避免为了每条意见无边界扩展实验。

## 7. 旧数值一致性策略

旧稿没有原始数据时，最稳妥的做法是“协议复现”，不是“柱值复刻”：

1. 用 3 个独立 calibration seeds 校准公共单位、负载、时间窗、拓扑、网络和 HPA；calibration 数据不进入正式 CI。
2. 先看 baseline 整体形状是否复现，再看 NSESche；若所有方法同向偏移，优先检查公共协议。
3. 只允许修正可证实的协议/代码错误，修正必须对受影响方法一致，并产生新冻结提交。
4. 正式 bank 启动后，不再因柱值偏差修改参数；新版数值是权威结果，旧值只作为对照并解释。
5. 论文保留旧图算法顺序和视觉结构，但柱从零开始，叠加 seed 点和 95% CI，避免只展示均值造成“人为贴柱”的印象。

## 8. 统计与结果闭口

- 实验单位是完整 run；20 个固定配对 seeds，不按显著性追加样本。
- 逐 run 计算 throughput、QPR、latency、completion 和 cost；报告 mean、BCa 95% CI、双侧 paired permutation、Holm 校正、配对效应量及相对变化 CI。
- 零完成运行原样保留；预注册前必须明确每个指标的适用性与不可定义规则。
- 每个 run 保存 config、tape/reference SHA、binary SHA、stdout/stderr、frame/request/Nash streams、summary、QC receipt 和 ledger event。
- 只有在矩阵完整、统计/图/CSV 可重建、旧值对照完成、审稿意见映射完成后，实验组才标记 `paper_ready_closed`。

## 9. 预算与停止规则

- corrected-runtime 候选开发屏幕：90 online runs（非正式）。
- 独立 E1 正式资格/主结果：1,200 online runs。
- 后续旧实验与审稿补充：在 E1 复用前提下，总正式在线预算维持 3,760 runs，另加 300 exact PoA states 和按唯一状态键构建的 references。
- 任一门槛失败立即停止后续大矩阵，先形成机制诊断；不得用更多 seed 掩盖失败。
- 只有技术故障可同 spec 重试；统计不利不是故障。

## 10. 当前唯一下一步

当前 `M1-DYNAMIC` 已按预注册终止，公共执行器修复已完成技术回归，但旧
offline reference 与性能结果不能提升为 corrected-runtime 结果。尚无任何主
论文实验组 `paper_ready_closed`。下一步需要用户明确授权：

> 允许冻结公共 cold-start 转换修复和 outer-feedback gap 观测，重建匹配的
> offline references，并在不新增 NSESche 机制的前提下，用 `ready_order`、
> `ready_finish_tie`、`formula` 三个 strict-Eq.15 候选预注册 D61--D65
> corrected-runtime 开发屏幕；胜出后使用独立 Q61--Q80 正式资格 bank。

该授权只开放公共 runtime/reference 重新冻结、上述三个既有候选和新 seed
bank，不授权删选结果、修改论文公式/指标或直接启动 M2。
