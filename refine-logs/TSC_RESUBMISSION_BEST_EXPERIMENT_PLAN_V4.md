# NSESche TSC 拒稿重投最佳实验计划 V4

日期：2026-09-04（Asia/Shanghai）

状态：结合 G1 正式 Q61--Q80、G2/G3/G6/G7、G8 归因和 post-G8
claim/scene 审计更新。不存在可进入确认的现有候选；lookahead 家族与局部机制
搜索关闭。V4 取代 V3，选择“论文公式/算法忠实 + 声明收缩 + 审稿证据优先”的
可信重投路线。本计划本身不授权新的 sampling。

## 1. 已证实的事实与不可再假设的前提

1. 旧论文图只有近似柱值和旧导出，没有逐 seed 原始结果、完整 config、binary
   或可识别 legacy protocol；旧实验必须按统一协议重建，旧柱不能作为目标值。
2. 完整正式 homogeneous-20 low、Q61--Q80、十方法 200/200 已经跑完。
   NSESche throughput 为 1.5815 req/ms、排名 3；QPR 为 0.058107、排名 4。
   相对 FaaSRank 分别为 -1.04% 与 -9.26%。QPR 配对 95% 描述性区间完全低于
   0，不能称为“统计上相当”或“最优”。
3. G2/G3 四个公式一致的非控制候选均未达到确认门。最强的
   `ready_warm_init` 也只在 4/6 cells 双指标改善，worst C0 ratio 为 0.8574，且
   homogeneous-low 不领先全部九个 baseline。
4. G6/G7 均为完整保留的失败开发结果。G8 未获预注册授权，不能继续做 G9、
   换 seed、放宽门槛或按场景切换 NSESche 机制。
5. 因而“通过继续重跑即可保证 QPR 和 throughput 都第一”已被现有证据否定。
   如果双指标普遍第一是不可退让的投稿条件，当前项目需要新的研究贡献与新的
   研究阶段，而不是实验工程或结果选择。

## 2. V4 的论文定位

### 2.1 冻结实现

- 最终论文方法回到最简单、论文忠实的 `ready_order`：严格执行 Eqs. (1)--(20)
  和 Eq. (15) best response，不使用 warm preference、finish override、lookahead、
  regret guard、seed/load 分支或额外效用项。
- 以正式 Q61--Q80 使用的 corrected-runtime commit
  `98f822cf2dcb878024a2ca39cc56533895ea692c` 和 binary SHA-256
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`
  为复现实锚点。后续若为增加 decision-neutral 日志而重编译，必须证明
  placement command stream 与该语义逐帧一致，并使用一个新冻结 binary 跨所有
  后续 cell；不得修改决策。
- 当前 revision 中 G2--G7 分支代码保留作负面/消融证据，但不进入最终方法。

### 2.2 冻结声明

删除或改写以下泛化表述：

- “NSESche achieves the best/highest throughput and QPR”；
- “outperforms all baselines under all workloads/topologies/scales”；
- 把大规模 offline/SA reference 称为 exact optimum；
- 把有限轮未变化直接写成无条件理论收敛。

允许的中心声明为：

1. 在论文假设和有限候选集下，NSESche 的严格 best-response 过程具有条件性
   PNE/固定点解释；
2. 实现与 Eqs. (1)--(20) 对齐，并报告 active-window 收敛、limit、oscillation、
   开销和离线 reference 覆盖；
3. 通过 exact-small states 校验 reference/PoA，在大状态只报告 empirical
   welfare gap；
4. 吞吐量、QPR、延迟、完成率、成本均作为共同主要结果透明报告；可描述具体
   场景排名和 trade-off，但不能预设普遍领先。

后续某个预注册 cell 若确实双第一，只能写“在该场景观察到第一”，不能外推为
普遍优越性。所有失败 cell 同样进入论文或补充材料。

## 3. 执行总原则

- 独立单位是完整 run；所有在线比较固定 20 个配对 seeds，同一 cell 十方法共享
  workload tape、公共 HPA、冷启动、容器生命周期、随机源、计时、成本和 QoS
  口径。
- 每个 run 的第一次 QC-valid canonical 结果永久保留。性能差、偏离旧柱、QPR
  不第一或未收敛不是技术重跑理由。
- 技术重试只允许 crash、timeout、OOM、I/O/截断、哈希不符或结构不变量失败，
  并保留全部 attempt 和原因。
- 禁止删 seed、补跑到均值满意、只重跑 NSESche、跨 tape 拼 baseline、替换
  reference、隐藏负面 cell 或事后改主要指标。
- 每一阶段先预注册输入、输出、统计和停止条件，再实现/审计，再执行一次。
- 原仓库继续只读；所有工作只在 revision worktree，且不 push。

## 4. P0：重投 claim contract 与最终 runtime 冻结

在任何新运行前先完成：

1. 建立逐段 claim map：原稿句子、审稿意见、保留/收缩/删除、所需证据、对应
   图表；
2. 建立 reviewer-to-experiment matrix，明确 R1/R2/R3 哪条意见由复用日志、
   exact-small、主矩阵或新增受控实验回答；
3. 冻结 `ready_order` 最终 runtime、source/binary/Cargo/Python hash、公式语义、
   reference schema 和公共配置；
4. 冻结统计分析脚本和图表数据契约。

P0 验收不是“指标第一”，而是所有主张均有可生成证据且没有超过数据范围。

## 5. P1：先解决审稿人最核心、成本最低的证据缺口

### 5.1 复用 Q61--Q80 的收敛与开销

不重跑现有 200 个 homogeneous-low runs。直接从 20 个 NSESche canonical logs
提取：

- active/no-player window 分层；
- inner/outer rounds、stable、termination、limit-hit、oscillation、assignment
  moves、固定点保持率；
- placement-policy wall/thread CPU、完整 scheduler wall/thread CPU、RSS；
- seed 级 mean/SD/BCa CI 与全部点。

这直接回答 R1-1/R1-2/R2-1/R3-1。若日志缺字段，只允许 decision-neutral 重放
且必须先证明 command-stream 等价；不能改变 placement。

### 5.2 离线社会效用 reference 与 exact PoA

先审计 Q61--Q80 reference build/replay：coverage、missing/null/negative、lookup/
build cost、state key、state-pair 和 assignment-sequence 一致性。大规模报告
empirical gap，不称 exact。

新增最小 exact-small 集合：3 nodes，4/6/8 players，各 100 个确定性状态，共
300 states。枚举 feasible assignments、exact social optimum 和全部/一个 PNE，
与 SA/offline reference 比较，报告 relative error、exact PoA 分布、运行时间和
失败状态。状态生成规则、枚举 tie-break 和误差阈值须在任何 optimum 暴露前冻结。

P1 停止门：若 exact 枚举/效用实现无法逐项对应论文公式，或 reference coverage
不能解释，暂停全部大矩阵并先修正论文方法/实现一致性；不得用性能结果掩盖。

## 6. P2：按原论文章节顺序补齐主实验

P1 通过后，为 claim-reframed continuation 单独预注册；旧
`next_cell_authorized=false` 不能被 V4 自动覆盖。

1. **20-node homogeneous low**：直接复用 Q61--Q80 的 200/200 正式结果，作为
   顺序起点；不重复运行、不覆盖。
2. **homogeneous middle**：十方法 ×20 = 200；完整闭口后才开 high。
3. **homogeneous high**：200。
4. **参数 E7 + 消融 E5**：按旧稿的参数/消融顺序，各 240，共 480；中心点复用
   主矩阵，不重复计数。
5. **heterogeneous low → middle → high**：逐 cell 200，共 600；同一 frozen
   binary，不按场景调算法。
6. **20/100/500-node workload-proportional scaling**：20-node 复用；100/500
   保持每节点 offered load，按 V3 冻结范围新增 1,200。

每个 cell 的闭口条件是 20/20 QC、完整配对、QPR 全覆盖、统计/图/receipt 闭合，
不是 NSESche 必须第一。若在 homogeneous middle 或 high 的任一场景，NSESche
同时在 throughput 和 QPR 排名后 50%，且对相应第五名的两项配对区间均完全为
负，则保留并报告该 cell，暂停后续昂贵矩阵，重新评估重投稿价值。

## 7. P3：审稿意见要求的最小新增在线实验

只在 P2 主实验仍支持论文的理论/系统价值后执行：

### 7.1 Burst（600 runs）

homogeneous-20 middle，固定三种：5x/50 ms、3x/200 ms、4 次 4x/50 ms；十方法
×3×20。报告 queue peak/area、恢复时间、p95/p99、完成率、右删失和成本。

### 7.2 QoS/SLA/fairness（200 runs）

heterogeneous-20 middle，三类函数各 1/3；SLA 在独立 pilot 中冻结，正式十方法
×20。报告 class throughput/latency/completion、violation、Jain、最差 10%
satisfaction 和总体 QPR。

### 7.3 Pricing/welfare comparators（80 runs）

heterogeneous middle/high 增加 CP-BR 与 OnSocMax，2 方法×2 cells×20；原十方法
复用 P2。统一从 post-hoc welfare evaluator 计算，不允许 baseline 读到 NSESche
私有状态。

### 7.4 不做项

native mode、故障注入、额外压力测试和长时间 soak 继续排除。它们不是审稿人
明确要求，且不能修复当前核心证据缺口。

## 8. 统计与图表标准

- 每 run 先计算 QPR，再跨 20 seeds 汇总；不能用均值吞吐量/均值延迟/均值成本
  重新拼 QPR。
- 所有主指标给出全部 seed 点、mean、sample SD、BCa 95% CI、双侧 paired
  permutation、Holm 校正、配对效应量和相对变化 CI；离散 failure/coverage 给出
  分子分母。
- 每张旧图生成 `old_pdf_alignment.csv`：旧 PDF/Excel 来源、新 mean/CI、相对
  偏差、共同场景诊断。±15% 只触发全方法场景审计，不允许方法特异重跑。
- 图保持旧方法顺序以便审稿人核对，y 轴从零开始，叠加 seed 点和 95% CI；保存
  source CSV、分析脚本、SVG/PDF 和 900-dpi PNG。
- development/diagnosis 数据只能解释机制和规划，不能混入正式主图。

## 9. 运行预算与逐阶段授权

已有且复用：200 online runs。若全部阶段都获后续独立授权，新 online 上限为：

| Block | New online runs |
|---|---:|
| Homogeneous middle/high | 400 |
| E7 parameter + E5 ablation | 480 |
| Heterogeneous low/middle/high | 600 |
| Proportional scaling | 1,200 |
| Burst | 600 |
| QoS | 200 |
| Pricing/welfare comparators | 80 |
| **Maximum** | **3,560** |

另有 300 个 exact-small states，不算在线 simulator runs。该数字是最大路线，不是
一次性授权。每个 block 必须由上一 block 的完整审计单独解锁。

## 10. 与用户目标的关系

V4 仍然最大化重投成功率和结果质量，但不承诺制造双第一或复刻旧柱。现有证据
表明，继续针对已有候选挑种子/补跑会增加可复现性和审稿风险，而不会可靠修复
QPR。最有价值的新增证据是审稿人明确要求且当前缺失的收敛、reference、exact
PoA、burst、QoS 和 scaling；性能结果按统一协议如实呈现。

如果用户坚持“只有 NSESche 在所有主场景 throughput/QPR 都第一才投稿”，则
V4 的结论是：**暂停实验执行**，另立一个与本重投数据隔离的新研究项目，允许
提出新的算法贡献、修改模型/公式并重新走 development/confirmation。不能把
该研究探索伪装成这次拒稿重投中的自适应补实验。

## 11. 下一条唯一授权建议

先预注册并完成 P0 的 manuscript claim map、reviewer-to-evidence matrix 和
`ready_order` final-runtime/telemetry 等价性审计；随后只执行 P1 的 retained-log
收敛/reference 提取和 exact-small 预注册。P2/P3 的任何新在线运行在 P1 结果
审计前均保持阻塞。
