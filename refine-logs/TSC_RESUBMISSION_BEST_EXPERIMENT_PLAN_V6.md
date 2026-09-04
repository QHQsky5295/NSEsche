# NSESche TSC 拒稿重投最佳实验计划 V6

日期：2026-09-05（Asia/Shanghai）

状态：本计划结合 P1、正式 homogeneous-low/middle、G2--G19、P2--P4 的
完整证据更新，取代 V5。V6 选择“论文公式忠实、先修正公共实验协议、按原章节
顺序整组重跑、用最小新增实验准确回应审稿人”的重投路线。本计划只授权下一步
的只读协议推导和零结果预注册，不直接授权 simulator sampling。

## 1. 当前事实与决策

### 1.1 已经闭口、可以直接用于写作的证据

- P1 收敛性、离线社会效用 reference 和 exact-small PoA 已永久冻结在
  `closed-experiments/P1_convergence_offline_reference_exact_small_PoA/`。
- 固定快照下严格顺序 best response 的有限改善性质已有条件性证明。
- 20 个 Q61--Q80 NSESche runs 中，19,509/19,509 个 active windows 达到内层
  稳定；外层 placement stability 为 97.396%，9 个窗口达到 outer cap，未观察到
  oscillation。该结果是运行行为，不外推为外层无条件收敛定理。
- 300/300 个 exact-small games 存在 PNE，确定性轨迹均到达 PNE；exact
  worst-PNE PoA 的 median/p95/max 为 1.002848/1.010731/1.018114。
- exact-small 离线估计器 normalized shortfall 的 median/p95/max 为
  0/0.0935%/0.2008%。大状态 reference 仍只称 empirical estimate。

P1 的数学证明、exact-small 结果和审稿回复材料不因后续公共 runtime 改动而重跑
或覆盖。最终论文中的在线迭代率和运行开销应从最终正式 runs 重新提取，以保持
runtime 身份一致。

### 1.2 已完成但不能作为最终主图的性能证据

- homogeneous-20 low 已完整保留 200/200：NSESche throughput 1.58150、QPR
  0.058107，分别排名第 3 和第 4；相对 FaaSRank 为 -1.04% 和 -9.26%。
- homogeneous-20 middle 已完整保留 200/200：NSESche throughput 排名第 5，
  applicable QPR 排名第 8；Q71 的 NSESche 和四个 baselines 为零完成，QPR
  按冻结定义不可计算。
- 旧 PDF 没有逐 seed 原始数据、完整配置或可识别 binary；legacy protocol 已经
  审计为不可唯一恢复。低/中场景相对旧柱的全方法漂移是场景级差异，不是只重跑
  NSESche 可以修复的问题。

这两个正式批次继续永久保留，作为协议诊断和重投 provenance；如果 V6 的公共
实验协议发生变化，它们不与 V6 新结果拼接，也不进入同一最终图或统计量。

### 1.3 已关闭的算法优化路线

G2--G19、P2--P4 已覆盖初始化、player order、warm/finish preference、lookahead、
request backpressure、global-ready admission、deferral valves、overflow thresholds、
参数邻点、贡献 tempering 和 startup-aware queue pressure。没有一个候选通过完整
预注册门槛。P4 虽使平均 throughput/QPR 提升 4.396%/2.243%，但只有 2/5 joint
wins，且删除 D127 的 leave-one-out 后两项平均差均为负，故已关闭。

因此 V6 不再把重投时间投入隐藏的局部机制搜索。最终 NSESche 决策语义回到论文
忠实的 `ready_order`、严格 Eq. (15)、Eqs. (1)--(20) 和现有 action set。P4 及
所有失败开发机制只能作为内部负面证据，不能进入最终方法或论文主结果。

### 1.4 当前真正需要修正的是公共实验协议

middle 的零完成不是 crash，而是大量请求同时进入系统后，CPU 被分给不断增长的
未完成 DAG；Q71 结束时 NSESche 仍有 43,677 个 function tasks，其中 10,307 个
正在运行。这个现象说明“无限在途请求 + 固定短观测期”没有形成可解释的稳态主
实验，也使 QPR 对零完成 run 不适用。直接继续 high、scaling 或 burst 会放大
这个问题。

V6 因而先引入一个对所有方法完全相同、与方法排名无关的公共平台协议：有限且
FCFS 的 request admission、明确的 arrival/measurement/drain phases、统一的
HPA/冷启动/容器生命周期和容量同比扩展。它属于实验平台控制变量，不改变
NSESche 的论文公式；但由于它改变所有方法收到的 active-request population，
最终性能比较必须从 homogeneous-20 low 开始整组重跑，不能复用旧 baseline 柱。

## 2. 不可变的科学与实现边界

### 2.1 NSESche 冻结边界

- 保持论文已显示的 Eqs. (1)--(20)、QPR 公式、效用项和 Eq. (15) strict
  best-response 条件不变。
- player 仍为依赖已满足的 `(ReqId, FnId)`；候选节点先经过统一 hard
  feasibility/admission 检查。
- 固定 `ready_order`；不加入 warm preference、finish override、lookahead、
  regret guard、额外效用项、seed 分支或结果触发分支。
- 只保留论文已经声明的负载参数：low `(r0=0.6,wq=0.5)`，middle/high
  `(0.5,0.6)`。最终使用一个 binary，不为不同负载切换隐藏机制。
- Eq. (19) 每轮重新锚定 CP-GEN 基础价格，不递归累乘；非正 reference 时保留
  inner Nash assignment 和基础价格，并显式记录原因。

允许的改动仅为：所有算法共同的平台协议、decision-neutral telemetry、配置/
receipt/QC、从现有公式推导的命题与边界说明，以及不改变调度命令的性能优化。

### 2.2 Baseline 公平边界

论文必须明确比较的是 placement/node-selection policy，而非各论文完整的
autoscaling product。所有方法共享 HPA、冷启动、容器管理、网络模型、request
admission、workload tape、随机源和观测期。逐方法列出保留部分，例如 FaaSRank
的 score-rank-select、Orion 的 DAG-aware placement、Jiagu 的 QoS-aware
pre-decision；其原生 sizing/prewarming 不在本次受控比较内。删除“完整复现其
端到端系统”的暗示，也不新增 native-mode 实验。

### 2.3 结果处理边界

- 正式 population 在结果暴露前冻结；同一 seed 的所有方法共享 tape 和公共
  runtime 配置。
- 每个第一次 QC-valid canonical observation 必须保留。性能差、未第一、与旧柱
  不同、达到迭代上限或零完成都不是删 seed/重跑理由。
- 技术重试只允许 crash、panic、OOM、I/O/截断、timeout、hash/config/tape 身份
  不符或结构不变量失败；必须使用相同 seed/tape/config/source/binary 并保留失败
  attempt。
- 不允许只保留有利种子、补跑到均值满意、混入 development 结果、只重跑
  NSESche、跨 tape 拼 baseline、修改 reference 或隐藏负面 cell。
- 旧 PDF 柱值只作 `old_pdf_alignment.csv` 的诊断锚点，不能成为 seed 接受标准。
  没有 legacy 原始数据时，不承诺逐柱复刻；对同一场景的系统偏差给出统一协议
  解释。

这些约束既保证数据可信，也降低同一批审稿人发现选择性报告、算法版本不一致或
baseline 不公平后再次拒稿的风险。

## 3. P5：最终公共平台协议修正与冻结

P5 是所有新正式性能实验的唯一前置阶段。

### 3.1 先做只读推导

使用现有 low/middle、高负载 pilot、source 和 Q71 traces，形成
`P5_COMMON_PLATFORM_PROTOCOL_DERIVATION.md`，回答：

1. arrival 进入等待队列、active DAG cohort、dependency-ready function 和节点
   runnable task 的精确定义；
2. 当前何处产生无限 active DAG 扩散，现有 queue/admission 字段是否真正执行
   hard constraint；
3. 怎样用总 CPU/memory capacity 与公开 function profile 构造 cluster-size
   proportional active-DAG cap，而不使用任何方法的 throughput/QPR 排名；
4. arrival、measurement 和 drain 应如何划分，哪些 arrival 进入分母，排队等待
   是否计入 end-to-end latency，以及未完成请求如何右删失；
5. low/middle/high offered-load strata 如何根据同一 capacity audit 冻结，避免
   “名义 70k”与实际平均 rate 混淆；
6. 20/100/500 节点时 admission 和 workload 如何同比扩展。

此步骤只能读取既有数据，不生成新 workload/reference/online result。

### 3.2 唯一允许的公共语义

在零结果预注册后实现并测试以下共同语义：

- 新请求按 arrival sequence 进入 FCFS admission queue；
- 同时 active 的 DAG 数量存在一个容量推导的上限，随 cluster capacity 线性
  扩展，对十种方法完全相同；
- active cohort 有空位时立即接纳最早等待请求，不按 DAG 类型、seed、方法或
  预期完成时间筛选；
- admission 之前的等待属于端到端 request latency，不能通过延迟接纳人为删除；
- arrival phase 停止后进入有界 drain，继续执行已经到达的请求；未完成请求保留
  为 right-censored，并报告 completion ratio；
- throughput 的 numerator、observation duration、drain 是否计入 denominator
  在任何结果前固定；QPR 保持现有 run-level 公式，不用伪常数修复不可适用值；
- CPU/memory hard feasibility、network reachability、queue admission 和无可行
  节点 fallback 全部写入配置、日志和 Algorithm 1 说明。

上限数值、phase 时长和 load rate 只能由预注册的 capacity/traffic 规则产生，
不能根据 NSESche 与 baseline 的胜负选择。

### 3.3 Pilot 和冻结门

使用与 formal 完全分离的 3 个 pilot seeds，最多 `10 methods × 3 loads × 3 = 90`
runs。Pilot 只检查协议可解释性，不选择算法：

- 到达率、admission conservation、FCFS、容量缩放和计时不变量全部通过；
- low/middle/high 的实测平均与瞬时分位数分离报告；
- 不出现由观测期明显过短造成的整场系统性零完成；
- 每个方法的排队、active、completed、censored 数量可守恒；
- 同一设置重复运行的 workload、command/result hashes 可复现；
- 十种方法共享完全相同的公共 runtime identity，NSESche 公式审计通过；
- offline reference build/replay 与新 active-state identity 一致。

若 pilot 失败，只能修正公共协议并在新 pilot seeds 上重新验证；不能依据相对排名
调 admission/load。全部通过后冻结 source commit、binary hash、配置 schema、
workload generator、reference builder、analyzer、figure contract 和 formal seeds。

## 4. E1：按原论文章节顺序重跑 20 节点主比较

P5 通过后，新建一次 result-blind formal preregistration，固定 20 个配对 seeds。
每个场景均为 `10 methods × 20 seeds = 200 runs`，严格按下列顺序执行：

1. homogeneous-20 low；
2. homogeneous-20 middle；
3. homogeneous-20 high。

low 必须从全部十种方法开始，不能把旧 Q61--Q80 baseline 与新公共协议下的
NSESche 拼接。每个场景完成 200/200、独立 QC、reference/receipt、统计和图表
source closure 后才进入下一个。一个 cell 的数据闭口条件是 population 完整和
报告诚实，不是观察到 NSESche 第一。

每个 run 至少输出：throughput、run-level QPR、completion ratio、mean/p50/p95/
p99 latency、cost/completion、queue peak/area、admission wait、censored/drop/
reject/timeout、CPU/memory/network utilization、scheduler wall/thread CPU/RSS、
inner/outer rounds、stable/cap/oscillation/nonconvergence，以及 reference hit/
missing/nonpositive/lookup cost。

若任何正式 cell 再出现不可解释的系统性零完成、计数不守恒或方法间公共输入不
一致，该 cell 原样保留并停止后续 sampling，返回公共协议审计；不得单独替换一
个方法或 seed。

## 5. E7 与 E5：参数和消融

完成三个 homogeneous 主场景后，按原稿顺序执行：

### 5.1 E7 参数验证

- 每个负载验证冻结中心与四个轴向邻点；中心复用 E1。
- 邻点共 `12 cells × 10 paired seeds = 120` 新 runs。
- 报告 throughput-QPR Pareto、completion、latency、cost 和效应区间。
- 这是敏感性验证，不允许按负载从结果中另选一个未预注册的投稿中心。

### 5.2 E5 机制消融

- `w/o Heterogeneity`；
- `w/o Externality`；
- `w/o Congestion Pricing`；
- `w/o Nash--Social Coordination`；
- Full NSESche 复用 E1。

四个消融 × 三负载 ×10 paired seeds，共 120 新 runs。每个消融必须由一个
明确公式/代码开关实现，其他语义相同。消融用于估计组件贡献，不要求每一项都
产生有利方向；反常结果必须报告和解释。

## 6. E1 heterogeneous：20 节点异构主比较

依次运行 heterogeneous-20 low、middle、high，每 cell 200 runs，共 600。
异构节点 CPU/memory 均值与 homogeneous 保持一致，离散程度在预注册中一次
冻结。三个函数特征的文字解释与公式职责保持准确：

- resource-intensity 是 CPU--memory 联合需求结构，不称绝对资源强度；
- network-dependency 是 placement 前通信敏感性 proxy，实际 network 状态由
  measured transfer/latency telemetry 验证；
- differentiation 是确定性算法差异化量，不称物理量。

每个异构 cell 复用 E1 的统计和 closure 规则。

## 7. E2：workload-proportional scalability

只选代表性的 middle load，保留全部十种方法：

- 20 nodes、1× workload：复用 homogeneous-middle；
- 100 nodes、5× workload：`10 × 10 seeds = 100` 新 runs；
- 500 nodes、25× workload：`10 × 10 seeds = 100` 新 runs。

共 200 新 runs。报告总 throughput、per-node throughput、scaling efficiency、
QPR、completion、tail latency、cost、scheduler wall/thread CPU、peak RSS、
inner/outer iterations、cap/timeout rate。旧 fixed-workload 20/100/500 只能作为
capacity-overprovisioning observation 放补充材料；没有原始数据时不伪造或重建
旧柱。

## 8. 审稿人明确要求的最小新增在线实验

### 8.1 E3 controlled burst

homogeneous-20 middle，三种总请求量受控模式：5×/50 ms 单峰、3×/200 ms
持续峰、四次 4×/50 ms 脉冲。十方法 ×3 patterns ×10 paired seeds，共 300 runs。

报告 arrival/queue/completion time series、queue peak/area、恢复时间、p95/p99、
completion、drop/reject/timeout 和成本。恢复定义、100 ms 持续窗口、最大 drain
和 right-censor 规则在结果前冻结。

### 8.2 E4 heterogeneous QoS、SLA 与 fairness

heterogeneous-20 middle，latency-/throughput-/cost-sensitive functions 各 1/3，
十方法 ×20 paired seeds，共 200 runs。SLA 仅用独立 pilot 冻结，正式结果不能
反向改阈值。

分别报告三类函数的 throughput、latency、completion、cost、violation；总体
报告 Jain normalized-satisfaction index、最差 10% satisfaction 和 QPR。

### 8.3 E6 close pricing/welfare comparators

heterogeneous middle/high 增加两个近邻比较器：一个公开、可审计的 congestion-
pricing best-response comparator 和一个直接 social-welfare placement comparator。
正式名称和实现必须在文献/代码核查后冻结，不能用一个弱自造 baseline 冒充现有
SOTA。两个方法 ×2 cells ×20 paired seeds，共 80 新 runs；原十方法和 NSESche
复用 heterogeneous E1。

P1 的 300-state exact PoA 直接复用。大状态只报告 empirical welfare gap、
reference coverage 和 estimator cost，不称 exact optimum/PoA。

## 9. E8/E9：只复用日志的特征、收敛和开销分析

不单独新增在线矩阵：

- resource-intensity 对 contention/slowdown；
- network-dependency 对 transfer volume/data-wait；
- differentiation 对 placement dispersion、冲突和同分选择；
- inner/outer rounds、fixed placement、limit hit、oscillation、nonconvergence；
- scheduler wall/thread CPU/RSS；
- offline build、table size/load、online lookup、missing/zero/negative reference。

相关性使用 Spearman + bootstrap CI + Holm correction。相关性只证明 association，
不写成因果。最终在线收敛统计来自 V6 正式 runs；P1 potential proof、exact-small
PNE/reference/PoA 结果继续复用。

## 10. 统计、图表与旧稿对齐

- E1 主比较固定 20 paired seeds；E7/E5/burst/scaling 固定 10；QoS 和近邻比较
  固定 20。不能按排名或显著性追加样本。
- 先逐 run 计算 QPR，再跨 seed 汇总；不得用三项均值重新拼 QPR。
- 报告全部 seed 点、mean、sample SD、BCa 95% CI、双侧 paired permutation、
  Holm correction、paired effect size、relative-change CI 和 win/tie/loss。
- p95/p99 先在 run 内计算；censored、zero-completion 和 non-applicable QPR 给出
  明确分子/分母，不静默删除。
- 每张旧图建立 `old_pdf_alignment.csv`：旧图近似读数、V6 mean/CI、相对偏差、
  协议差异。±15% 只触发整场公共审计，不触发方法/seed 特异重跑。
- 主图 y 轴从零开始，保留旧方法顺序，叠加 seed 点和 95% CI；保存 source CSV、
  analysis source/hash、SVG/PDF 和 900-dpi PNG。
- development/diagnosis/P4 数据不得进入正式主图。

## 11. 论文主张和停止规则

### 11.1 默认重投路线

主叙事改为“可分析的 Nash-stable placement 与 social-reference price feedback”，
证据中心是 potential/PNE、reference accuracy/cost、PoA、统一平台下的性能 trade-
off、QoS/fairness 和 scalability，不再预设所有场景双指标第一。

某个预注册场景若 NSESche 的 throughput 和 QPR 均第一，可以准确写“在该场景
观察到第一”；其他场景报告真实排名和 trade-off。不得写 universal best、全部
负载优于所有 baselines 或把近似 reference 称 exact optimum。

若连续两个 E1 场景中，NSESche 在 throughput 和 QPR 上均被同一方法支配，且
两项 paired relative-change 95% CI 均完全低于零，则完成并保留当前 cell 后暂停
后续高成本矩阵，先做一次投稿价值/claim review。这个门不删除结果，也不自动
授权新算法。

### 11.2 如果“双指标全部第一”仍是不可退让条件

当前 resubmission 路线应停止，并另立一个与本稿 formal 数据隔离的新算法研究
项目。该项目可以公开增加 end-to-end completion/admission objective 或修改公式，
但必须重新经过 development、disjoint confirmation 和全部 baseline 重跑，并在
稿件方法中明确呈现。不能把新方法伪装成原论文未变的实现细节，也不能通过筛选
种子把现有方法变成第一。

## 12. 最大运行预算

| Block | New online runs |
|---|---:|
| P5 common-protocol pilot（非正式） | <=90 |
| E1 homogeneous low/middle/high | 600 |
| E7 parameter validation | 120 |
| E5 ablation | 120 |
| E1 heterogeneous low/middle/high | 600 |
| E2 proportional scaling | 200 |
| E3 controlled burst | 300 |
| E4 QoS/SLA/fairness | 200 |
| E6 close comparators | 80 |
| **正式新增上限** | **2,220** |

预计最多约 450 个 semantic-specific offline reference builds；具体数量在 P5
reference-key schema 冻结时精确计算。P1 的 300 exact-small states 直接复用，不
计入新 runs。删除 native mode、故障注入、额外压力测试和长时间 soak。

## 13. 审稿意见到证据的最小映射

| Reviewer item | 必须提供的证据 | V6 来源 |
|---|---|---|
| R1-1/R1-2/R2-1/R3-1 | PNE 定义、条件性证明、迭代界与实测未稳定率 | P1 proof + V6 E9 |
| R1-3 | ratio preservation、monotone saturation、price bound | 现有公式推导，无新 run |
| R2-2 | profile/state reference、build/update/lookup cost、非正 fallback | P1 + V6 reference audit |
| R2-3/R3-2 | feature 语义、可行集/admission、相关性/消融 | P5 + E5 + E8 |
| R2-4 | controlled burst、queue/recovery/tail/drop、三类 QoS/SLA | E3 + E4 |
| R2-5/R3-3 | req/ms 单位、cost/QPR、simulation、CI/test、实现细节 | E1 + statistics contract |
| R2-6 | baseline 控制边界、同比 workload、runtime/memory/iterations | fairness table + E2/E9 |
| R3-4 | 近邻 pricing/welfare、fairness、PoA | E6 + E4 + P1 exact-small |

## 14. 数据命名、冻结和当前唯一下一步

- 正式 run ID 使用
  `TSCv2.<section>.<topology>.n<nodes>.<load>.<method>.F<seed>.<spec8>`。
- 场景闭口后复制完整 canonical/raw、derived CSV、figure、source、audits 和 receipt
  到清晰目录，例如
  `closed-experiments/E1_homogeneous_20node_low/`，生成逐文件 SHA-256 manifest
  后永久只读。
- 失败开发数据不能删除；从工作区移出后压缩到 E 盘 evidence archive，并保留
  root audit/manifest。可再生 build cache 才允许清理，且不触碰受保护目录。

当前唯一授权动作是完成 P5 的只读公共协议推导、source-level 可行性审计和零结果
预注册。P5 preregistration 提交前，不执行新 pilot、reference、baseline、NSESche、
high-load、scaling、burst 或 QoS run。
