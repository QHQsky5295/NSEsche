# NSESche TSC 拒稿重投最佳实验计划 V3

日期：2026-09-04（Asia/Shanghai）

状态：结合旧稿溯源、正式 Q61--Q80 失败、G2/G3/G6/G7 完整开发结果更新。
G7 已关闭且不得进入确认；当前唯一授权动作是预注册并执行一次只读的
G7/G6/G3-C0/G2-warm 归因。本文取代 V2 作为后续实验总路线，但不单独授权
新机制或采样。

## 1. 核心判断

旧论文图没有可恢复的逐 run 原始数据，旧导出又是同键覆盖而非多 seed 均值，
因此旧实验必须用统一协议重跑。旧柱仅能作为 provenance/alignment 锚点，不能
要求新数据“做成旧数值”。最安全的重投叙事是：

1. 固定论文 Eqs. (1)--(20)、QPR 定义与博弈主线；
2. 只在 development bank 中优化论文未写死的运行语义；
3. 用完全未参与开发的确认 bank 检验 NSESche 是否同时取得 throughput/QPR
   第一；
4. 方法冻结后，严格按论文实验章节从 20 节点同构低负载开始重跑；
5. 复用正式日志补收敛、reference、资源和特征证据，另外只运行审稿人明确
   要求且无法复用的数据块。

“目标结果最大化”通过机制诊断、开发集候选选择和独立确认实现。不能按结果
删除有效 seed、补跑到均值达标、替换离线 reference，或只展示有利子集；这些
做法会使拒稿重投的可信度风险远高于任何局部柱高收益。

## 2. 不可变边界

- 论文 Eqs. (1)--(20)、严格 Eq. (15)、Eq. (19)/(20)、效用项与 QPR 定义冻结。
- low 使用 `(r0=0.6,wq=0.5)`；middle/high 使用 `(0.5,0.6)`；一个最终 binary
  跨六个 20-node 主场景使用。
- 所有方法共享 tape、公共 HPA、冷启动、容器生命周期、候选集、网络、随机源、
  计时和成本口径；baseline 只负责 placement。
- 每个唯一候选/tape 使用新的离线 reference identity；build/replay 的表、收据、
  state-pair/assignment 序列与进程证据全部哈希绑定。
- 技术重试仅限 crash、timeout、OOM、I/O、截断、哈希或结构不变量失败；性能差、
  未收敛或偏离旧柱不是技术失败。
- 每个预注册 bank 保留全部 QC-valid 首次 canonical 结果。development、
  confirmation、formal 数据不可混用。
- 原仓库保持只读；revision worktree 保存代码、协议、审计和数据。

## 3. 当前证据与停止点

### 3.1 旧结果与正式失败

- 旧 PDF/Excel 找回了柱值，但没有 seed、run、config、binary 或原始 JSON；旧
  protocol 已冻结为 `legacy protocol unidentifiable`。
- 原正式 Q61--Q80 同构低负载 200/200 完成：NSESche throughput/QPR 均未超过
  FaaSRank，必须保留为历史失败；由于后续机制变化，它不能充当新候选确认。
- G2 warm-only 在 D66--D70 的同构低负载有局部正信号，但全局资格失败，只能
  用作探索性机制证据。
- G3 C0 和全部九 baseline 的 D71--D75 同构低负载结果是当前开发比较锚点。

### 3.2 G6/G7 给出的新约束

- G6 unrestricted lookahead 激活但失败：`T=1.0784`、`QPR=0.029572`，且产生
  multi-hop cascade、parent-blocked/resident backlog 与完成率损失。
- G7 bounded-frontier + warm initialization 的一跳约束正确生效，但结果更差：
  `T=1.0580`、`QPR=0.0211551`、latency `100.123 ms`、completion `0.553675`。
  对 C0 的 throughput/QPR/joint 胜数仅 2/5、1/5、1/5。
- G7 五个 seed 均有 warm/overlap 激活、最大前沿深度 1、零 hop 违规；14/4953
  active windows 缺少 required offline-table hit。性能失败并非 dormant mechanism
  或求解开销造成。

结论：G7 不进入 Q-bank。继续把 warm initialization 与 lookahead 捆绑调参没有
依据；下一步必须先分离两种机制。

## 4. P1：最后一轮受控方法救援

### P1.1 只读归因（当前唯一可执行项）

使用现有 G7、G6、G3 C0 和 G2 warm-only 数据，不运行模拟器：

1. 在 D71--D75 上配对比较 G7/G6/C0 的 throughput、QPR、latency、completion、
   cost、solve time、queue peak/area 和各阶段 wait；
2. 比较 inner/outer termination、assignment moves、limit/oscillation、reference
   hit/not-requested 与 warm-refined/lower-utility 初始选择；
3. 验证 G7 是否在至少 4/5 seeds 消除 G6 的 multi-hop 与 parent-blocked backlog，
   以及性能下降是否更一致地伴随 warm 路径而非一跳 admission；
4. G2 D66--D70 仅用于方向性验证，不能与 D71--D75 做伪配对或合并均值；
5. 所有诊断定义、输出列和候选授权规则在读取聚合结果前预注册。

只有同时满足以下条件，才允许 P1.2：一跳边界确实修复 G6 cascade；G7 的
退化与 warm-init/path dependence 或 inner-limit/reference gap 有直接日志证据；
没有证据显示一跳 admission 本身是主要退化源。

### P1.2 条件候选 G8（尚未授权）

若 P1.1 通过，唯一候选为 `lookahead_frontier1_utility_init`：保留 G7 的一跳
admission，恢复普通严格 paper-utility 初始可行分配，随后仍使用原严格 Eq. (15)
best response。禁止 warm preference、finish override、regret guard、负载/seed
分支或增加公式项。

G8 是 lookahead 家族的最后一个候选。其实现前必须冻结：新名称、runtime
schema、reference tag、单元/协议测试、binary hash 和零数据 manifest。

开发优先复用 D71--D75 作为**明确已适应的 optimization bank**，以便同 tape
隔离 frontier-only 与 G6/G7；全部五个结果仍保留。固定通过门：

- 五 seed 均无 >1-hop 违规、dispatch 完整、每个 active window 命中 reference；
- mean throughput `>1.1514`，mean QPR `>0.040391615`；
- 对 C0 throughput 至少 3/5 胜、QPR 至少 4/5 胜、joint 至少 3/5 胜；
- 任一 seed 的 T/QPR 不低于 C0 的 80%；mean completion 不低于 C0，mean
  latency 低于 C0，mean solve-time ratio `<=3`。

若 G8 未同时通过全部门，停止局部机制搜索，冻结“不支持原主性能优势”的负面
结论，并回到论文 claim 收缩/场景定义，而不是增加 G9 或挑 seed。

### P1.3 独立确认

G8 仅在开发门通过后进入完全未见的 Q81--Q100。该 bank 必须在同一 20-node
homogeneous-low tapes 上运行 NSESche 加九个 baseline，共 200 runs；不能复用
Q61--Q80 或跨 tape 拼接 baseline 均值。NSESche throughput/QPR 均值均第一且
20/20 QC/统计闭合后，才冻结最终 binary 并进入正式章节顺序。

## 5. P2：旧论文章节顺序重跑

只在 P1.3 通过后执行，且逐 cell 闭口：

1. **20-node homogeneous low**：Q81--Q100 确认直接成为首个正式 cell，
   `10 methods x 20 paired seeds = 200`；
2. **homogeneous middle**：200；双指标第一后才开 high；
3. **homogeneous high**：200；
4. **参数 E7 + 消融 E5**：中心点复用 homogeneous，新增 240+240；
5. **heterogeneous low → middle → high**：600；同一个 binary，不重新调机制；
6. **20/100/500-node workload-proportional scaling**：20-node 复用，100/500
   使用 5x/25x workload，新增 1200。

任何 cell 未达到 20/20 QC、NSESche throughput/QPR 均值双第一和完整统计/图表，
都标记 `formal_complete_not_closed` 并停止后续正式 cell。失败数据永久保留。

## 6. P3：审稿人实验的最小充分集合

### 6.1 收敛与离线社会效用 reference（最高优先级）

不需要为每张图再跑一套主矩阵。复用 P2 NSESche 正式日志报告 active-window
inner/outer rounds、stable/oscillation/limit-hit、outer fixed point、wall/thread
CPU/RSS；no-player window 单列。

离线 reference 报告 build/replay coverage、missing/zero/negative、lookup/build
开销、state-pair/assignment 一致性。另做 3 nodes、4/6/8 players、各 100 个
确定性小状态，共 300 states，枚举 exact optimum/PNE 并报告 exact PoA 和
SA-reference 误差。大规模只称 empirical welfare gap，绝不称 exact optimum。

### 6.2 Burst 与 QoS

- Burst：homogeneous-20 middle，5x/50 ms、3x/200 ms、4 次 4x/50 ms，十方法
  ×3×20=600；报告 queue peak/area、恢复、p95/p99、completion 和右删失。
- QoS：heterogeneous-20 middle，三类函数各 1/3，十方法×20=200；SLA 由独立
  pilot 冻结，报告 class metrics、violation、Jain 和最差 10% satisfaction。

### 6.3 Pricing/Welfare 与特征验证

- heterogeneous middle/high 增加 CP-BR 与 OnSocMax：2×2×20=80；原十方法复用
  P2。
- E8 相关性从 P2/Burst/QoS 日志复用，报告 Spearman 和 bootstrap CI，不新增
  在线矩阵。

native mode、故障注入、额外压力测试和长时间 soak 继续不做，因为审稿意见并
未要求，且不能改变主结论可信度。

## 7. 统计、旧柱对齐与论文验收

- 独立单位是完整 run；固定 20 个配对 seeds。
- 逐 run 计算 QPR；报告全部 seed 点、mean、sample SD、BCa 95% CI、双侧 paired
  permutation、Holm 校正、配对效应量和 relative-change CI。
- throughput/QPR 为主指标；同时报告 latency mean/p50/p95/p99、completion、
  queue、cold/schedule/data wait、cost、drop/reject/timeout 与调度开销。
- 每张旧图生成 `old_pdf_alignment.csv`：旧 Excel/PDF 来源、新 mean/CI、相对
  偏差和 protocol 解释。±15% 仅触发全方法场景审计，不允许单独重跑 NSESche。
- 图保持旧算法顺序和风格，但柱从零起，叠加 seed 点和 95% CI；保存 source
  CSV、脚本、SVG/PDF 与 900-dpi PNG。
- 只有 `formal`、完整 20 seeds、统一协议、双指标第一、统计和图表均闭合的数据
  才能进入重投稿。development 只支持机制选择，不进入论文主图。

## 8. 审稿意见覆盖

- R1-1/R1-2/R2-1/R3-1：条件性 PNE 论证 + active-window 收敛/固定点/开销。
- R1-3/R2-2：Eq. (19)/(20) 日志、reference build/replay、coverage、误差与开销。
- R2-3/R3-2：E5 消融 + E8 特征相关性，收窄物理含义。
- R2-4：受控 Burst + QoS/SLA/fairness。
- R2-5/R3-3：统一配置、配对统计与同比 workload scaling。
- R2-6：共同 HPA/runtime、baseline placement-only 边界和调度开销。
- R3-4：CP-BR/OnSocMax、empirical gap 与小状态 exact PoA。

## 9. 下一条指令

先创建并提交 P1.1 只读诊断预注册；在其分析器、测试和结果审计完成前，不实现
G8，不采样新 seed，不启动 Q81--Q100、homogeneous middle、burst、QoS、scaling
或论文图表。
