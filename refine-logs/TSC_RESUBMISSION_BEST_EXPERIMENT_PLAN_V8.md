# NSESche TSC 拒稿重投实验计划 V8

日期：2026-09-05（Asia/Shanghai）
状态：替代 V7；P6-A 定稿后进入共同平台的小场景验证与实现。
工作区：serverless_sim_game_revision；分支：agent/tsc-resubmit-final。
原仓库及永久冻结的 P1 材料保持只读。

## 1. 目标、依据与当前结论

目标是在论文现有行间公式下改进 NSESche 的 throughput/QPR，补齐审稿人明确要求
的实验，并复用所有来源一致的有效对照，控制重跑成本。论文未写明的实现细节可
优化；若改变 player 集合、可行域、信息可见性或机制，必须披露并重新检查相应
理论假设。公式字面未变并不自动意味着算法未变。

保留旧稿节点、函数分布、负载 profile、1000-ms 主指标窗口和图表顺序。旧柱偏差
用于来源解释，不用于选择实验结果。按结果删有效 seed、混画训练/测试或补到
第一会改变报告的统计对象，本计划不采用；开发参数可按负载调整，正式验证使用
未见的固定 paired seeds，所有有效观测保留。

当前已知：P1 的固定快照收敛、离线估计器和 exact-small PoA 材料已冻结；
P5 全部 90 runs 保留，但 56 runs terminal completion ratio <0.95，
NSESche throughput/QPR 均值排名分别为 low 10/8、middle 8/7、high 7/10。
这些是诊断结果，尚无新的同构/异构性能组达到本项目“双指标领先”的目标。

## 2. 两项论文主张和五组证据

| 主张 | 最小证据 | 不能用来替代的证据 |
|---|---|---|
| C1：固定快照的严格 best response 具有可解释稳定性，social feedback 有明确作用边界 | P1 条件证明、300 exact games；最终方法 online inner/outer/reference 开销；机制消融及近邻 welfare 比较 | 有界性不能证明完整双循环无条件收敛；小规模样本最大 PoA 不能称通用上界 |
| C2：NSESche 在声明的公共调度平台上取得较好的吞吐量–延迟–成本权衡 | 同构/异构配对主比较，资源/运行开销，比例扩展，controlled burst 和分类 QoS | 单个好 seed、旧柱接近、只有已完成请求的低 latency 都不能证明总体优势 |

五个 evidence blocks 为：主性能；参数与消融；资源/开销/扩展；突发与 QoS；
稳定性/reference/近邻福利。本文不提出新的 LLM/VLM/Diffusion 贡献，无需相关对照。
native-mode、故障注入、额外压力矩阵和长时间 soak 均不列入计划。

## 3. P6：一次共同平台验证，先解决同构主比较的前提

规范文件：
- P6_COMMON_ELIGIBILITY_AND_BATCHING_DERIVATION.md
- P6_WORKLOAD_STRATIFICATION_AND_DRAIN_DERIVATION.md
- P6_COMMON_PLATFORM_PROTOCOL_PREREGISTRATION.md
- P6_A_STATIC_REVIEW.md

### 3.1 从 V7 和未提交草案作出的修正

1. 共同 readiness 采用当前 NSESche 的 PreAllDone。论文未明确 readiness，因此
   这是公开的 placement-only 边界选择；不能将不同规则的 baseline 简单判为错误。
   方法内部 priority/scoring 保留，中央 validator 要求完整覆盖当窗可放置集合。
2. 复用已有共同 HPA 和 atomic dispatcher；补中央 ready index、完整 batch 检查、
   ready-pending/idle-to-zero、确定性 scale-down 和对应 telemetry。
3. HPA 基础 memory 导致 idle target 向上取整的源码风险已定位，但尚未证明它解释
   全部 P5 停滞。先写 deterministic fixtures，验证后才实施并运行 pilot。
4. 撤回输入工作量筛选。low/middle/high 代表到达率等级；随机 DAG 导致 rho_cpu
   交叠时完整报告。直接使用固定 P6P01--P6P03 三 seeds，不建候选池。
5. 主 QPR 回到 fixed 1000-ms throughput/cost/latency；cost 是全平台累计成本除以
   completed count。额外 drain 同一 arrival cohort 以报告尾延迟和删失，两个
   估计对象分别命名。DAG request completion 与 function-task completion 分开。
6. 缩减 pilot reference 工作：NSESche 需九份；baseline 现有 posthoc observer 必须
   先实现并验证显式关闭后，才可省去其 81 次参考构建。正式 welfare 单独启用。

### 3.2 执行顺序与判定

小场景验证 -> reviewer-v5 实现/回归 -> release 和零结果 manifest ->
九条固定 inputs -> 九份 NSESche references/模型绑定 ->
90-run pilot 和一个 duplicate。

pilot 按 low 30 runs、middle 30、high 30 运行；每级先通过协议检查再进入下一级，
pilot 排名不作为通过条件。完整 pilot 要通过输入身份、共同 eligibility/candidate/
batch、FCFS/cap/dependency、atomic timing、metric identity、完整 drain、reference/
model/determinism 等十一项检查。任何失败保留，先在同一失败输入诊断/回归。

每 run 使用预先由输入计算、上限 200k drain frames 的预算和 30-minute wall cap；
超过预算的输入仍保留，不换 seed。stall counter 只报警，不凭部分计数提前认定死锁。
截至 P6-A，未编译 reviewer-v5、未生成 P6 tape、未运行 P6 pilot。

阶段审查和原有用户授权足以继续实现、测试及后续合格阶段；不逐项重复请求许可。
修改影响实验语义时先形成版本记录，technical regression 无需另开一份审批文档。

## 4. NSESche 开发、对照复用与性能判定

从 homogeneous-20 low 开始，固定 P6D01--P6D10 development bank。
九个 baselines 在每条 tape 上运行一次并冻结；NSESche 的参数/实现开发复用这些
对照，前提是 tape、common runtime、HPA、资源、指标口径和 baseline 版本均未变。
共享 runtime 改变会使旧对照不可直接合并；只改 NSESche 且共同代码身份一致时，
无需重跑 baseline。

已有 G2--G19/P2--P4 失败路线保留，不换名复跑。只有源码和已保留数据支持新的
机制假设时，先评估一个明确的新候选；记录三负载均值、paired effects、per-seed
最低表现、leave-one-out、completion/latency/cost 和运行开销。不能承诺每次优化
必定改善。候选失败时先解释失败原因，避免继续堆叠阈值。

low 参数中心 (r0=0.6,wq=0.5)，middle/high 中心 (0.5,0.6)，四个轴向邻点步长 0.1。
开发阶段选择参数；正式结果不能反向调参。各负载可有预先冻结的参数，一套
算法代码；新机制需披露，并检查 P1 证明的假设仍成立。

方法冻结后，在 P6F01--P6F20 的 20 个未见 paired seeds 上确认。
固定规模的 formal population 一次评估；若 NSESche 不领先，保留并明确报告。
性能“闭口”要求 throughput 和 QPR 均值都领先、完成率/副指标可解释、统计及图表
齐全；显著性不足不能写显著优越。没有达到目标时停在该组开发/诊断，不跳到
后续昂贵性能矩阵。

## 5. 原稿重跑的具体矩阵

当前目标文件优先要求先解决同构 low，再 middle/high。因此执行顺序以性能组为
单位；论文排图仍沿用 Fig.4 参数、Fig.5 消融、Fig.6--8 同构、Fig.9 异构、
Fig.10 扩展。同一 Full observation 只生成一次，按 hash 复用于所有对应图。

| 顺序 / 论文实验 | 配置与固定次数 | 新 online runs | 主要输出与通过解释 |
|---|---|---:|---|
| 1 同构主比较 / Fig.6 | 20 nodes，low -> middle -> high；10 methods ×20 seeds/load | 600 | throughput、QPR、cost、latency、completion、paired CI；逐负载完成后再推进 |
| 2 参数 / Fig.4 | 三负载各中心+四轴向邻点，20 seeds；中心复用 Full | 240 | 验证开发选出的中心及稳定区间；正式邻点不再反向选择最终参数 |
| 3 消融 / Fig.5 | w/o Heterogeneity、Externality、Pricing、Coordination；3 loads ×20 seeds | 240 | Full 复用；报告每项增益及不利结果，不改变公式来让消融好看 |
| 4 资源与开销 / Fig.7--8 | 同构同一批 observations | 0 | CPU/memory/container/network、policy wall/thread CPU、RSS、迭代与 timeout |
| 5 异构 / Fig.9 | 20 nodes；相同平均 CPU/memory，CV=30%/25%；10×3×20 | 600 | 同一最终算法，按 low -> middle -> high；不私自换异构专用机制 |
| 6 扩展 / Fig.10 | 仅 NSESche；100/500 nodes，5×/25×输入，3 loads ×20 seeds | 120 | 20-node Full 复用；总/per-node 吞吐、扩展效率、QPR、tail、wall/RSS/迭代/timeout |

旧稿声称 20 independent runs，因此以上旧实验保持 20 次，不沿用 V7 对参数和
消融降至 10 次的安排。扩展性按用户明确要求仅运行 NSESche，不额外跑九个
baselines；R2-6 要求的是容量同比负载和开销证据，不强制该图重复十方法。

扩展 workload 使用预声明 tape transform：20-node 输入作为 parent，100/500
产生 5/25 份具有独立 request ids 的等分布 arrivals；变换方式、时间抖动、DAG mix、
网络模型必须在运行前固定。报告该方式的 burst correlation，不能声称新增独立
trace。相同负载、更多资源的旧曲线只在已有可用资料时作 overprovisioning 对照，
不新增大矩阵冒充 weak scaling。

## 6. 审稿人明确要求的最小新增矩阵

| 审稿问题 | 实验和配置 | 次数 / 新 runs | 关键证据 |
|---|---|---:|---|
| R2-4 controlled burst | hom-20 middle；5×/50ms、3×/200ms、4×四脉冲；十方法 | 10 paired seeds/pattern；300 | queue buildup、peak/area、恢复时间、drop/reject/timeout、p95/p99、SLA violation、cost |
| R2-4/R3-4 分类 QoS、公平性 | het-20 middle；latency/throughput/cost classes 各1/3 | 20 paired seeds；200 | 每类 T/L/cost/completion/violation；normalized satisfaction、Jain、worst-10% |
| R3-4 pricing/welfare 近邻 | het-20 middle/high，两个近邻 comparator | 2×2×20；80 | 与原十方法相同配置；福利差、fairness、throughput/QPR 和开销 |
| R1/R2/R3 收敛、参考、PoA | P1 复用；最终 online 日志补统计 | 0 新独立矩阵 | inner/outer 区分、cap/oscillation、reference build/update/lookup/非正回退 |
| R2-3/R3-2 特征验证 | 复用主比较、burst、QoS 日志 | 0 | hri/通信代理/区分因子与实际 contention、transfer、dispersion 的 association，CI及失败情形 |

burst 与稳态采用同总请求量的时间重排；在方法结果前验证请求数、DAG multiset 和
资源 work 相等，以分离 burstiness。恢复定义用配对稳态 queue 的独立校准阈值：
脉冲结束后连续 50 ms 回到阈值内；未回落保留右删失。不能因为尾延迟相差大而删
数据，需先看是否由相同工作量下排队/冷启动机制解释。

QoS 的 deadline、throughput target 和 cost budget 在独立校准输入上一次冻结，
按类报告归一化办法。共享参数与三类参数的含义需在论文中区分。

近邻 comparator 的实际来源、实现和删减边界在正式运行前核实。CP-BR/OnSocMax
若是自建机理对照，应明确命名为自建 reference comparator；不能冒充已发表
完整系统。目前该块尚未完成实现来源资格审核。

## 7. 统计、图表、存储和写作边界

全部主比较保留 paired run 数据。报告 mean、sample SD、95% CI、paired effect、
permutation 和 Holm、多重比较 family、win/tie/loss；QPR 逐 run 计算，p95/p99
先在 run 内算。10-seed 新 burst 与20-seed旧实验分别标出 n，不能沿用笼统“所有20次”。

图保留旧方法顺序、零轴、seed points 和 CI，使用矢量 PDF/SVG 与审阅 PNG；
同时保存 source CSV、脚本、单位变换和 manifest。未画图时不得声称图已完成。
正文将来源明确写为 trace-feature-driven simulation，不暗示真实20台服务器。

P1 永久冻结在 closed-experiments/P1_convergence_offline_reference_exact_small_PoA/。
其31文件 manifest维持不动；后续 online 数字用新日志另报，不能把旧 runtime
迭代结果当作新版实测。P1 README 列出 exact-small 和外层稳定性的适用范围。

有效/失败观察均按审计需要压缩归档。C盘保留当前组与小摘要，已完成的大日志经
E盘 hash/恢复验证后迁移；可再生 target/cache 按具体目录清理。不得以性能不佳
删除唯一原始证据。当前 C 盘约332 GB可用，无需为本轮文档删除任何材料。

## 8. 预算、下一步和阶段汇报

旧稿重跑上限1800 runs；新增 burst/QoS/近邻580 runs；合计2380 online runs。
另计 P6 pilot90+duplicate1，development基线最多270、NSESche中心30及候选30；
reference builds、SLA校准和技术 fixtures 单列，不能藏在 online 数中。
历史 P1 不再重复300个状态。实际时间用 P6 分阶段测量给出，不沿用旧36–48小时承诺。

下一步：完成 P6-A 静态审查，实施共同 HPA/readiness 的小场景验证与修正；验证成功
后开始 hom-20 low 的 pilot。main low 双指标目标未达到前，后续正式组不提前启动。

每个阶段按论文章节汇报：
- 已闭口：P1 的路径、可用 claim、数据/写作材料；若有图给实际路径；
- 当前：hom-20 low 性能前置验证，以及已有结果的 throughput/QPR 排名；
- 未完成：参数、消融、同构其余负载、异构、扩展、burst、QoS、近邻对照；
- 本轮新增证据是否改变下一步，以及哪些仍未验证。

本计划保留完整实验目标；P6-A 文档完成不代表论文实验完成。
