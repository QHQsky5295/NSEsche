# NSESche TSC 拒稿重投最佳实验计划 V2

日期：2026-09-03（Asia/Shanghai）

状态：已结合旧稿 PDF、审稿意见、历史 Excel/Git 溯源、G1 正式低负载结果和
G2 初始化开发结果重排；**P0/B0 已以 `legacy protocol unidentifiable` 闭合，
30-run calibration pilot 不授权**。当前进入 G3 的 decision-neutral mechanism
diagnosis；没有任何主论文实验组达到 `paper_ready_closed`

## 1. 结论与主线

旧实验必须重跑，但不能立即把全部旧图和新增实验一起跑完。当前最优顺序是：

1. 先解释为什么当前九个 baseline 全部不能同时复现旧 PDF 的 throughput、
   QPR、cost，而不是继续只改 NSESche；
2. 场景协议稳定后，才允许一个新的、至多三个候选的公式一致开发屏幕；
3. 候选通过独立资格后，从 **20 节点同构 low** 开始，按论文章节逐组正式
   重跑和闭口；前组失败时后组不开启；
4. 旧实验闭合后再完成 burst、QoS、welfare/PoA、特征相关性和收敛证据；
5. 旧柱只作为 provenance/alignment 锚点。正式结果以同协议、配对 tape、
   全部预注册 seeds 的新统计为准。

“最大化论文成功概率”的合法实现方式是开发集优化、独立确认和机制解释，
不是从正式结果中只留下有利 seeds。这样既能积极追求 NSESche 的吞吐量/QPR
优势，又不会让同一数据同时承担调参与验证两个角色。

## 2. Claim Map

| Claim | 审稿人为什么会质疑 | 最小可信证据 | 对应实验块 |
|---|---|---|---|
| C1：在统一 HPA/runtime 和共同可行集下，NSESche 的个体—系统协调能稳定提高 throughput 与 QPR | 原稿只有柱状图，baseline 边界和统计不足 | 六个 20-node 主 cell 的 20 个独立配对 runs；两项均值第一；CI、配对检验、成本/时延拆解；消融支持 | B1、B2 |
| C2：严格内层 best response、价格反馈和 offline social reference 具有可核验的理论/运行性质 | R1-1/R1-2/R1-3、R2-1/R2-2、R3-1/R3-4 质疑 PNE、外层固定点、reference 与 PoA | 条件性势函数证明；active-window 迭代/limit 分类；reference coverage/误差/开销；小规模 exact PoA；相邻 pricing/welfare baseline | B2、B5 |

需要排除的反解释：优势不是单位错误、不同 workload、不同 HPA、隐藏的
load-specific scheduler、baseline 弱化、挑 seed 或把 SA reference 写成 exact
global optimum 所造成。

论文不再声称：20 台物理机实测、外层无条件收敛、大规模 exact PoA、或完整
复现了同时包含 scaling/prewarming/container management 的 baseline 系统。

## 3. 不可变边界

- 冻结 Eqs. (1)--(20)、效用项、Eq. (19)/(20)、QPR 定义和严格 Eq. (15)。
- low 使用 `(r0=0.6,wq=0.5)`；middle/high 使用 `(0.5,0.6)`。E7 可以验证
  邻点，但不能把不同 NSESche 机制隐藏成负载调参。
- 一个候选 binary 跨 low/middle/high、homogeneous/heterogeneous 使用；只允许
  论文已披露的参数按负载变化。
- 所有方法共享 tape、HPA、cold start、container lifecycle、candidate filter、
  network、queue 和计时/成本口径。
- 开发阶段每个 unresolved 问题至多三个预注册候选；正式阶段固定 20 个配对
  seeds，全部 QC-valid 观测保留。
- 技术失败只按相同 seed/tape/config/binary 重试；低分、未收敛或旧柱偏差不
  构成技术失败。
- 原仓库只读；所有新代码、协议和数据只进入 revision worktree。

## 4. 已获得的证据与当前判定

### 4.1 已完成但不能写成最终主结果

- G0 已完成公共 cold-start transition 修复、论文—代码公式对齐和 Eq. (16)/
  (19)/(20) 日志重算门禁。
- G1 D61--D65 的 90-run strict-Eq.15 开发屏幕选定 `ready_order`。
- G1 Q61--Q80 同构低负载正式 cell 完成 200/200：NSESche 的 mean throughput
  `1.58150`、mean QPR `0.058107`，分别比 FaaSRank 低 `1.04%` 和 `9.26%`；
  因此该 cell 是必须保留的失败证据，不能闭口，也不能开启 formal middle。
- G2 D66--D70 的 135-run 初始化屏幕完整保留；全局规则仍选 C0
  `ready_order`。C1 虽在同构低负载 throughput 上领先九个 baseline，但 QPR
  不领先且 heterogeneous-middle 退化，不能事后替换 C0。
- 修正后的 active-window 审计表明内外层 explicit limit hits 很少；纯粹增加
  convergence budget 不可能解释或修复主要 QPR 差距。

### 4.2 找回的旧稿锚点

Git 历史中的两个 2025-07-21 Excel 找回了旧稿 NSESche/消融三负载的单点
聚合值。低负载 NSESche 为 `T=1.700`、`cost=0.313890`、`latency=34.0659`、
`QPR=0.158983`，与 PDF 柱高度一致。

但导出脚本对相同 `(load, algorithm)` 的多个 JSON 执行覆盖而非均值，工作簿
没有 seed/run/config/hash，Git 也没有原 cache JSON。因此旧柱不是可恢复的
20-seed 正式 bank。历史 NSESche 还使用与当前论文公式版本不同的效用权重、
负载分支和经验阈值。详见 `LEGACY_RESULT_PROVENANCE_AUDIT.md`。

## 5. 五个实验块

### B0：全场景 provenance/configuration audit（当前 MUST-RUN）

**状态：CLOSED。** 字段级审计发现空 seed 重复、覆盖式导出、未绑定 binary、
九个 baseline/NSESche 版本断层以及公共候选集、原子提交、确定性和 cold-start
语义变化。不存在可唯一验证的旧协议，因此冻结 `legacy protocol
unidentifiable`，不启动 30-run calibration pilot。详见
`B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md`。

- **检验问题**：新旧大偏差来自哪个公共协议/实现变化？
- **数据**：旧 PDF、历史 Excel、`54280e...`/`26fbe54`/current 三个代码点、
  G1 Q61--Q80 的十方法输出。
- **核对轴**：观察帧数与 drain、到达率、DAG 抽样、节点资源、网络、HPA、
  cold-start、container cache、可行集、baseline 版本、cost 累计、throughput
  分母、QPR 和绘图导出。
- **先做只读差异表**：不运行新模拟，不看某个新 candidate 的结果。
- **必要 pilot**：只有发现可证明的公共差异后，才用 3 个全新 calibration
  tapes 运行 homogeneous-20 low 的十方法，共 30 runs；所有方法同改同跑。
- **成功条件**：唯一的新公共协议被解释并冻结；旧值能复现则记录误差，不能
  唯一恢复则正式冻结 `legacy protocol unidentifiable`，不再无限贴柱。
- **失败解释**：不能把场景级偏差归因给 NSESche，也不能启动 NSESche-only
  补丁。
- **论文位置**：Experimental Setup、reproducibility appendix、old alignment
  supplement。

### B1：20-node 主性能比较（MUST-RUN）

- **检验 C1**：NSESche 是否在统一 runtime 下同时提供最高 throughput/QPR？
- **方法**：NSESche、Greedy、Random、Hash、Load Balance、FaaSRank、OCS、
  Hiku、Jiagu、Orion。
- **顺序**：homogeneous low → middle → high；随后 heterogeneous low →
  middle → high。
- **每 cell**：`10 methods x 20 paired formal seeds = 200 runs`。
- **闭口条件**：20/20 完整、QC/统计/图/CSV 完整，NSESche 两项均值均第一；
  负面 secondary metrics 不隐藏。
- **停止条件**：任一 cell 未通过，保存整组并停止后续正式 cell，回到新的
  development bank。
- **论文位置**：Fig.6、Fig.9 和主性能表。

### B2：参数、消融、机制与收敛（MUST-RUN）

- **E7 参数**：每负载为论文中心加四个轴向邻点；中心复用 B1，新增
  `12 x 20 = 240 runs`。中心须在 throughput--QPR Pareto 前沿。若不是，必须
  如实更新敏感性结论，不能只保留有利格点。
- **E5 消融**：w/o Heterogeneity、w/o Externality、w/o Congestion Pricing、
  w/o Nash--Social Coordination；Full 复用 B1，新增 `4 x 3 x 20 = 240`。
- **E8 特征验证**：从 B1/B3 日志检验 resource coupling、network-dependency
  proxy 和 differentiation 与 contention/data-wait/placement dispersion 的
  Spearman 关系及 bootstrap CI。
- **E9 收敛/开销**：从正式日志统计 active-window inner/outer rounds、stable、
  oscillation、limit-hit、outer fixed-point、wall/thread CPU/RSS；不再使用把
  no-player window 混入的旧 `nonconvergence_rate`。
- **论文位置**：Fig.4、Fig.5、Fig.7、Fig.8、Fig.13。

### B3：受控 burst 与 QoS（MUST-RUN，回答 R2-4）

- **Burst**：homogeneous-20 middle，5x/50 ms 单峰、3x/200 ms 持续峰、四次
  4x/50 ms 脉冲；`10 x 3 x 20 = 600 runs`。报告 queue peak/area、恢复时间、
  p95/p99、completion/drop/reject/timeout；最长 drain 4,000 ms，未恢复右删失。
- **QoS**：heterogeneous-20 middle，三类函数各 1/3，`10 x 20 = 200 runs`；
  SLA 由独立 pilot 冻结，报告 class metrics、violation、Jain index 和最差
  10% satisfaction。
- **一致性门**：steady 与 burst 的到达总量、基础 scene、计时口径可追溯；
  异常差距先查 burst 定义而不是删 runs。
- **论文位置**：Fig.11、Fig.12。

### B4：工作负载同比扩展（MUST-RUN，回答 R2-6/R3-3）

- 20/100/500 nodes 分别使用 1x/5x/25x workload；20-node 点复用 B1。
- 100/500 节点对十方法、三负载、20 seeds，新增
  `10 x 3 x 2 x 20 = 1,200 runs`。
- 报告总吞吐、每节点吞吐、扩展效率、QPR、resource cost、scheduler
  wall/thread CPU/RSS、迭代数和 timeout/limit-hit。
- 若仅展示 NSESche 自身趋势，可作为补充诊断，不能替代 reviewer 要求的
  workload-proportional comparison。
- **论文位置**：Fig.10。

### B5：Pricing/Welfare/PoA（MUST-RUN，回答 R3-4）

- heterogeneous middle/high 增加 CP-BR 和 OnSocMax placement adaptation；
  原十方法复用 B1，新增 `2 x 2 x 20 = 80 runs`。
- 3 nodes、4/6/8 players 各 100 个确定性状态，计算 exact optimum/PNE 和
  exact PoA，共 300 states。
- 大规模只报告 empirical welfare gap、reference coverage 和误差/开销，
  不称 exact PoA。
- **论文位置**：pricing/welfare 主表、PoA appendix、Fig.13 reference panel。

## 6. P0 后的 G3 开发规则

G3 现在不预注册具体机制；必须先由 B0 给出可证伪的单一原因。候选规则为：

1. fresh bank 固定为新的 D71--D75 或后续未使用编号；D61--D70 与 Q61--Q80
   均不得再次参与候选选择；
2. C0 固定为 `ready_order`；C1/C2 只能改变一个被 B0/日志直接支持、且不改
   Eqs. (1)--(20) 的运行语义；
3. 不再重复已失败的 `ready_finish_tie`、`formula`、warm/finish initialization
   或纯 convergence-budget 家族；
4. 矩阵至少覆盖 `3 candidates x 2 topologies x 3 loads x 5 seeds = 90`，以
   六 cell 的十二个 throughput/QPR 相对 C0 比率做全局 maximin；
5. homogeneous-low 还必须在相同 fresh tapes 上与九个 baseline 比较，两项
   均值都第一才获得独立 formal 资格；
6. 若三个候选均失败，停止加规则，回到 claim/scene 诊断；不得追加第四个
   候选或从失败 bank 中抽取有利 runs。

只有 G3 通过，才冻结 source/protocol/binary/reference 并创建全新 Q-bank 做
B1 正式确认。若公共 runtime 有变化，十方法全部重跑；若只有 NSESche 代码
变化，正式比较仍需在同一个全新配对 bank 上获得 baseline 行，不能跨 seeds
拼接旧 baseline 均值。

## 7. 正式运行顺序与预算

| 里程碑 | 论文证据 | 新 online runs | Go/No-Go |
|---|---|---:|---|
| P0 | B0 只读溯源；必要时 3-seed 十方法 pilot | 0 或 30 | 公共 scene 唯一冻结 |
| P1 | G3 fresh development | 至少 90，另加同 tape baseline gate | 六 cell maximin + low 双第一 |
| M2.1 | homogeneous low | 200 | 双指标第一后才开 middle |
| M2.2 | homogeneous middle | 200 | 双指标第一后才开 high |
| M2.3 | homogeneous high | 200 | 同构主比较闭合 |
| M2.4 | E7 参数 + E5 消融 | 480 | 中心 Pareto、Full 优于消融 |
| M2.5 | heterogeneous low→middle→high | 600 | 每 cell 双指标第一 |
| M2.6 | 100/500-node weak scaling | 1,200 | 可解释同比扩展 |
| M3.1 | Burst | 600 | 恢复/尾延迟/SLA 证据完整 |
| M3.2 | QoS | 200 | 分类与公平性证据完整 |
| M3.3 | Pricing/Welfare | 80 | 相邻方法与 welfare 证据完整 |

在不重复复用 cell 的前提下，计划正式 online 总量仍为 3,760，另加 300 个
exact PoA states。开发和必要 pilot 不进入正式预算。任何前置门失败都停止
后续大矩阵，因此不会为了“跑完计划”制造大量不可用数据。

## 8. 指标、统计与图表

- 逐 run 计算 throughput、cost/completed request、latency 和 QPR；QPR 不对
  聚合均值再计算。
- 报告 mean、seed 点、BCa 95% CI、双侧 paired permutation、Holm 校正、
  paired effect size 和 relative-change CI。
- 延迟报告 mean/p50/p95/p99；同时报告 completion ratio、queue peak/area、
  cold-start/schedule/data wait、drop/reject/timeout。
- 收敛只以 active-window 为分母，分别报告 stable、oscillation、inner limit、
  outer limit 和 fixed-point；no-player 另列。
- 每个旧图生成 `old_pdf_alignment.csv`，标明来源是历史 Excel 常量、PDF
  像素估读或缺失，并给出新均值/CI/相对偏差和协议解释。
- 图保持旧算法顺序，但柱从零起、带 CI 与 seed 点，并保存 source CSV、脚本、
  SVG/PDF 和 900-dpi PNG。

## 9. 数据保留与磁盘规则

- 正式 QC-valid 原始数据永久保留并压缩；失败正式结果同样保留，不能删除。
- pilot/development 在形成 summary、analysis、manifest、哈希和必要压缩流后，
  可清理可再生 staging/partial/target，但不得删除结论所依赖的 canonical
  observations。
- 不自动删除未确认归属的目录；先列出绝对路径、大小、是否可重建、是否被
  receipt/hash 引用，再决定归档或清理。
- 一组正式数据只有在协议相同、配对 tape 相同且没有公共 runtime 变化时才能
  被后续图表复用；跨 bank 的均值不能拼成配对比较。

## 10. 当前三个动作

1. 使用完整保留的 Q61--Q80/G2 日志完成 decision-neutral mechanism diagnosis；
   B0 已证明旧协议不可唯一恢复，不能再把旧柱差异归因到单个 NSESche 参数。
2. 只根据一个可证伪的公式/运行语义原因写 G3 preregistration；至多三个候选，
   并继续排除已失败的 initialization、finish-guard 和 convergence-budget 家族。
3. preregistration 闭合前不采样 D71，不运行 homogeneous-middle formal，也不
   运行 burst/QoS/scaling。

## 11. 审稿意见覆盖

- R1-1/R1-2/R2-1/R3-1：条件性 PNE 证明 + active-window convergence/E9。
- R1-3：Eq. (19)/(20) 相对价格保持、非递归有界性 + E5/E6。
- R2-2：offline reference build/replay、exact-small-state error、coverage/开销。
- R2-3/R3-2：E5 删除实验 + E8 相关性；收窄特征物理语义。
- R2-4：B3 burst/QoS/SLA/fairness。
- R2-5/R3-3：B0/B1 的单位、平台、配置、CI/统计和 workload-proportional B4。
- R2-6：baseline placement-only 边界表、共同 HPA/runtime、B4 开销与扩展。
- R3-4：B5 的 CP-BR/OnSocMax、fairness、empirical gap 和 exact-small PoA。

该映射只补审稿人明确改变结论可信度的证据；native-mode、故障注入、额外
压力测试和长时间 soak 继续删除。
