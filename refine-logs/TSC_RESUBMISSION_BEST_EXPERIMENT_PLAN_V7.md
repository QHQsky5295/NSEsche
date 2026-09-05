# NSESche TSC 拒稿重投最佳实验计划 V7

日期：2026-09-05（Asia/Shanghai）

状态：V7 在完整 P5 pilot 暴露公共排空和 player-eligibility 问题后取代 V6。
本计划保持论文 Eqs. (1)--(20)、Eq. (15)、QPR 公式和 P1 理论证据不变，先修复
所有方法共同的实验平台，再按论文实验章节逻辑从 20 节点同构 low 开始重跑。
当前只授权 P6 的只读推导和零结果预注册，不授权新的 simulator sampling。

## 1. 目标函数与不可越过的证据边界

本项目的优先目标是：在真实、固定、配对的测试数据上，使 NSESche 的 throughput
和 QPR 尽可能强，同时用最小但充分的新增证据回答原审稿人。实现层可以优化论文
未展示的公共协议、适配器、日志、计算效率和明确披露的运行机制；论文已经展示的
公式不能暗改。

以下做法不属于优化，且不得使用：按观察到的胜负挑 seed、删除有效低分结果、补跑
直到均值满意、只重跑 NSESche、跨 runtime/tape 拼接 baseline、把 development
结果冒充 confirmation，或用旧柱值作为 run 接受标准。参数调优和机制开发可以在
明确标记的 development 数据上做，但最终主张必须由完全隔离、一次冻结的 formal
population 验证。

## 2. 已闭口证据和 P5 决策

### 2.1 P1 直接复用

`closed-experiments/P1_convergence_offline_reference_exact_small_PoA/`
永久冻结，回答 R1/R2/R3 关于收敛、PNE、offline social reference 和 PoA 的核心
问题：300/300 exact-small states 存在 PNE，确定性轨迹均到达 PNE；worst-PNE
exact PoA median/p95/max 为 1.002848/1.010731/1.018114。旧在线证据中
19,509/19,509 active windows 内层稳定，外层 placement stability 为 97.396%，
9 个窗口达到 cap，未观察到 oscillation。P1 不因公共 runtime 改动而覆盖或重跑；
最终在线开销与迭代分布从新正式结果提取。

### 2.2 P5 完整但失败

P5 的 90/90 runs 和一个预声明 duplicate 全部保留。12 个门中 11 个通过，唯一
失败为 usable cohort：56/90 个 runs 的 terminal completion ratio 低于 0.95，
且十种方法全部受影响。P5 只作协议诊断，不能进入论文性能主图。

P5 还发现十种方法虽共享候选节点 hard-feasibility helper，却混用了 `All`、
`PreAllSched` 和 `PreAllDone` 三种 player eligibility。当前 NSESche `ready_order`
要求父函数完成，而多数组 baseline 在父函数已有 placement 后即可提前绑定后继。
这一差异会直接影响可调度 player 数、容器启动重叠、队列和固定窗口 throughput，
必须先统一，不能在修订稿中称当前结果为完全公平的 placement-policy comparison。

### 2.3 已关闭的单边机制路线

G2--G19、P2--P4 已关闭 warm/finish、order envelope、NSESche-only lookahead、
frontier、request backpressure、global-ready cap、deferral valves、fixed overflow
threshold、参数邻点、contribution tempering 和 startup-aware queue pressure 等路线。
P6 不得换名复跑这些候选。特别是 G6 的 NSESche-only `PreAllSched` 已失败；P6 的
新问题是为所有方法建立中央共同合约，而非给 NSESche 单独开放 lookahead。

## 3. P6：公共 eligibility、负载和排空协议修正

P6 是所有新正式性能实验的唯一前置阶段。

### 3.1 P6-A 只读推导与零结果预注册

先仅使用论文、源码、P5 workload descriptors、P5 gate/queue traces 和历史失败
审计，形成三个零结果文件：

1. `P6_COMMON_ELIGIBILITY_AND_BATCHING_DERIVATION.md`；
2. `P6_WORKLOAD_STRATIFICATION_AND_DRAIN_DERIVATION.md`；
3. `P6_COMMON_PLATFORM_PROTOCOL_PREREGISTRATION.md`。

推导必须冻结以下定义，之后才能实现：

- 中央 orchestrator 在每个 frame 对所有方法应用完全相同的 player-eligibility
  规则和稳定排序；统一语义为父函数已有 placement 后可分配 (`PreAllSched`)，
  执行层仍严格等父函数完成后才运行子函数；不同方法形成不同历史后，其实际
  player 集合可以合理不同；
- 每种方法只决定其当期、由公共规则产生的 feasible set 内的 node selection，
  不自行扩大/缩小 player 集合；eligibility/candidate 规则、snapshot schema、
  player 顺序和 batch 边界全部 hash-bound；实际内生集合另存 hash 用于同一 run
  replay，不要求不同方法在轨迹分化后逐帧数值相同；
- 所有方法一次返回完整 batch，再由共同 dispatcher 发送；不得因逐命令可见状态
  更新而让后运行的方法获得不同窗口状态；
- 共享 HPA、冷启动、容器生命周期、CPU/memory/network hard feasibility、外部
  FCFS admission 和随机流；
- low/middle/high 不再只按 request count 命名，而由输入 tape 的 offered work、
  critical-path work、DAG size/depth/parallelism、memory/cold-start demand 与 cluster
  capacity 的预声明函数分层；三层区间不得交叠；
- 先生成一个固定、输入-only candidate tape pool，再按上述 workload-only 距离函数
  确定性选择最靠近各层中心的 tapes；所有未选 inputs 和原因保留。选择过程不得
  读取任何 scheduler completion、latency、cost、QPR 或 rank；
- arrival/measurement 固定 1,000 ms。arrival 停止后继续排空所有已到达请求，
  throughput 分母仍为固定 1,000 ms；latency 从外部 arrival 计到 completion；
- hard drain 上界同时包含 total work、critical path、最大 cold-start chain 和固定
  safety factor，并设一个公开 wall-clock/runtime cap。只有计数守恒、无新 arrival、
  且至少 95% 固定 cohort 完成时 run-level QPR 才进入主汇总；未完成仍原样报告；
- 旧稿 low/middle/high request-rate 区间和柱值只作为场景级对齐表，不决定 tape
  接受或算法结果。

P6-A 完成前，不生成新 tape/reference，不编译 P6 binary，也不运行任何方法。

### 3.2 P6-B 实现与无结果冻结

在已提交的 P6-A 预注册之后：

- 实现唯一中央 eligibility/batch adapter；
- 为十种方法增加“收到相同 player/candidate/snapshot”和“返回同一 admitted set”
  的不变量；
- 增加 dependency execution safety、FCFS、conservation、drain、metric identity、
  deterministic action hash 和 cross-method input identity 测试；
- 构建一个 release binary，冻结 source/binary/config/schema/analyzer/figure contract；
- 固定 P6 pilot seeds、input-only tape pool、确定性分层规则和 90-run manifest；
- 在任何 online result 前绑定所有 tape、FaaSRank model 和 semantic-specific offline
  references。

### 3.3 P6-C 三种负载的公共协议 pilot

使用全新且与 P5、历史 development、formal seeds 隔离的 3 个 pilot seeds：
`10 methods × 3 loads × 3 seeds = 90 runs`。按 load-major、seed-major、固定方法
顺序执行；每个第一次 QC-valid observation 保留。

P6 必须同时通过：90/90 身份完整；同 tape 的 arrival、初始环境和外生随机输入
hash 一致；所有方法的 eligibility/candidate rule tag、snapshot schema 和 batch
时序一致；依赖执行无违规；FCFS/cap/conservation/timing/metric identity 全通过；
每个 run 固定窗口有完成且 terminal completion ratio ≥0.95；重复运行的内生集合、
action 和 result semantic hash 一致；reference 完整；无方法专属 HPA/scaling；
P5 的三层 workload 交叠消失。

相对性能只能在协议门决定后解封。若门失败，只能修公共协议并使用新 pilot seeds；
不得用 NSESche 是否第一决定 admission、load 或 drain。P6 通过后才允许正式实验
预注册。

## 4. NSESche 性能开发与冻结规则

P6 通过不等于 NSESche 已经适合投稿。先在完全独立的每负载十个、共三十个
development tapes 上运行九个 baselines 一次并永久冻结，再评估冻结的
paper-center NSESche。只有源码
诊断能提出一个没有被 G2--G19/P2--P4 覆盖、且不改 Eqs. (1)--(20)/strict
Eq. (15) 的新机制时，才允许预注册至多一个新机制；不能无限搜索。

开发选择采用预先冻结的 robust multi-objective 规则：三种负载 throughput 和 QPR
均值、每-seed floor、paired wins、leave-one-seed-out、completion/latency/cost 和
overhead 必须共同通过。baseline 不因候选迭代而重跑。开发胜者随后冻结 source、
binary、参数和所有机制开关；正式测试使用完全未见的 20 个 paired seeds，同时
一次运行并冻结全部十种方法。

不能承诺 NSESche 必然第一。如果共同平台修正后仍被同一 baseline 在三种负载中
稳定支配，应停止高成本矩阵并修改论文主张；不得再通过 seed/场景筛选制造第一。

## 5. 按原论文章节逻辑执行正式实验

平台与 NSESche 冻结后，所有矩阵均从 homogeneous-20 low 开始，按
low→middle→high 闭口。每个 cell 完成、QC、统计、旧柱对齐和 source-data closure
后才进入下一个。

### 5.1 RQ1 / Fig. 4 参数验证

先在 development tapes 上验证原稿中心：low `(r0=0.6,wq=0.5)`，middle/high
`(0.5,0.6)`，以及四个轴向邻点。中心复用上述三十个 development runs；四个
邻点新增 `4 × 3 × 10 = 120` runs；中心最终用 E1 formal seeds 复核。选择规则
优先保留落在最优 QPR 置信平台
内的原稿中心，只有预声明规则显示稳定劣化时才更改，并在修订稿解释。不得根据
正式 test 结果反向调参。

### 5.2 RQ2 / Fig. 5 消融

按 low→middle→high 运行 Full、w/o Heterogeneity、w/o Externality、w/o
Congestion Pricing、w/o Nash-Social Coordination。Full 可复用同身份正式结果；
其余 `4 × 3 × 10 = 120` 新 runs。报告 throughput、QPR、completion、latency、
cost 和 paired effect；不要求每个消融方向都“好看”。

### 5.3 RQ3 / Fig. 6--8 同构主比较

`10 methods × 3 loads × 20 paired formal seeds = 600 runs`。首先完整执行
homogeneous-20 low 的 200 runs，再 middle 200，再 high 200。每个 baseline 在
每个 formal tape 上只运行一次并冻结；不能复用 P5 或旧 runtime 柱。

Fig. 6 throughput/QPR、Fig. 7 CPU/memory/container/network utilization、Fig. 8
scheduler wall/thread CPU/RSS/iterations 均从同一 600-run 产品提取，不新增在线
运行。

### 5.4 RQ4 / Fig. 9--10 异构与可扩展性

异构 20 节点按 low→middle→high 执行 600 runs；CPU/memory 均值与同构场景一致，
离散系数在结果前冻结。扩展性使用 middle load，20 nodes/1× 复用，100 nodes/5×
和 500 nodes/25× 各十种方法 ×10 seeds，共 200 新 runs。报告总吞吐、per-node
吞吐、scaling efficiency、QPR、tail latency、completion、cost、policy wall time、
RSS 和 iteration 分布。workload 随容量同比扩展，不能沿用旧 fixed-workload
过度供给口径作为主结论。

## 6. 审稿人明确要求的最小新增实验

### 6.1 Controlled burst（R2-4）

homogeneous-20 middle，预注册单峰 5×/50 ms、持续峰 3×/200 ms、四次
4×/50 ms 脉冲：十方法 ×3 patterns ×10 paired seeds = 300 runs。报告 arrival、
queue、completion time series、queue peak/area、恢复时间、p95/p99、completion、
drop/reject/timeout 与 cost。恢复阈值和 right-censor 规则在结果前冻结。

### 6.2 QoS/SLA/fairness（R2-4、R3-4）

heterogeneous-20 middle，将 latency-/throughput-/cost-sensitive functions 各设
1/3：十方法 ×20 paired seeds = 200 runs。SLA 只用独立 pilot 冻结。分类型报告
throughput、latency、completion、cost、violation；总体报告 Jain normalized-
satisfaction、worst-10% satisfaction 和 QPR。

### 6.3 Pricing/welfare 近邻比较器（R3-4）

在 heterogeneous middle/high 增加一个可审计 congestion-pricing best-response
和一个直接 social-welfare placement comparator；正式名称与实现须先完成文献/
代码核查。两个 comparator ×2 cells ×20 seeds = 80 新 runs；原十方法复用异构
E1。P1 exact-small PoA 直接复用，大状态只称 empirical welfare gap。

## 7. 只复用日志的审稿证据

不新增在线矩阵即可回答：最终 inner/outer rounds、stable/cap/oscillation；offline
reference build/update/lookup/table size/missing/nonpositive fallback；resource-
intensity、network-dependency、differentiation 与实际 contention/transfer/
dispersion 的 Spearman + bootstrap CI + Holm 分析；scheduler runtime/RSS；QPR
单位与代数恒等式。相关性只写 association，不写 causal validation。

## 8. 统计、旧稿对齐与闭口规则

- 主比较固定 20 paired seeds；参数/消融/burst/scaling 固定 10；QoS/近邻比较固定
  20。样本量不因胜负追加。
- QPR 逐 run 计算，再跨 seed 汇总；p95/p99 先在 run 内计算。零完成、censored 和
  undefined QPR 不静默置零或删除。
- 报告所有 seed 点、mean、sample SD、BCa 95% CI、paired permutation、Holm、
  paired effect、relative-change CI 和 win/tie/loss。
- 每张旧图生成 `old_pdf_alignment.csv`：旧图近似值、新 mean/CI、相对偏差、协议
  差异。±15% 仅触发整个场景的公共审计，不触发 seed/method 特异重跑。
- 图从零轴开始，保留旧方法顺序，叠加 seed 点与 95% CI；保存 CSV、analysis
  source/hash、SVG/PDF 和 900-dpi PNG。
- P5、development、历史失败候选不得进入 formal aggregate 或主图。

## 9. 运行预算与停止门

| Block | 新 online runs 上限 |
|---|---:|
| P6 common-platform pilot（非正式） | 90 |
| 参数验证 | 120 |
| 消融 | 120 |
| 同构主比较 | 600 |
| 异构主比较 | 600 |
| 同比扩展 | 200 |
| Controlled burst | 300 |
| QoS/SLA/fairness | 200 |
| Pricing/welfare 近邻比较 | 80 |
| **正式新增上限** | **2,220** |

NSESche 的十-seed-per-load development gate 如被单独授权，另计九个 baseline
270 runs、paper-center NSESche 30 runs 和最多一个已预注册新候选的 30 runs。
删除 native mode、故障注入、
额外压力测试和长时间 soak。

任何阶段出现身份不一致、计数不守恒、公共 eligibility/batch 不一致、系统性不可
用 cohort 或 reference 错配，保留结果并立即停止后续阶段。连续两个正式场景中若
NSESche 被同一方法在 throughput 与 QPR 上以 paired 95% CI 完全低于零的方式
支配，则先做投稿价值/claim review，不继续烧完整矩阵。

## 10. 当前唯一授权动作

当前只允许：P6 只读源码/证据推导，以及在没有任何 P6 tape、reference、binary、
online result 或 rank 的前提下提交零结果预注册。P6 实现、输入生成、reference、
pilot 和所有正式实验均等待该预注册的独立审计与后续明确授权。
