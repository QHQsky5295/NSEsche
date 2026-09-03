# G3 既有日志机制诊断预注册

日期：2026-09-03（Asia/Shanghai）

状态：**FROZEN BEFORE AGGREGATE DIAGNOSIS；不授权候选、不授权 D71**

## 1. 目的与既有知识

目标是在不改论文 Eqs. (1)--(20)、不重用旧数据估计新候选效果的前提下，从
完整保留的 G1 Q61--Q80 和 G2 D66--D70 日志中确定一个可证伪的运行机制问题。

冻结前已经知道、因此不能包装成新发现的事实是：

- G1 homogeneous-low 中 NSESche 相对 FaaSRank 的均值差为 throughput
  `-1.04%`、QPR `-9.26%`，但 cost 略低；
- running-warm bypass 与较差 QPR 有描述性关联；
- equal-utility finish tie、bounded-regret finish guard、dynamic finish guard、
  warm/finish initialization 和纯 convergence-budget 家族已经失败或不符合严格
  Eq. (15)，不得再次作为 G3 候选；
- G2 明确表明 warm/finish initialization 的变化几乎总是选择较低即时 paper
  utility，不能事后用个别 seed 的改善替换冻结选择。

## 2. 封存输入

- G1 formal root：
  `runs/tscv1_g1_formal_q61_q80_98f822c_20260903`
- G2 development root：
  `runs/tscv1_g2_init_d66_d70_3ae7792_20260903`
- G1 runtime commit：`98f822c`；所有 200 个 homogeneous-low 正式行保留。
- G2 candidate commit：`3ae7792`；所有 135 个 online 行保留。

输入选择不依赖结果。缺失或 QC-invalid 行只能按既有技术规则报告，不能因分数
低而排除；本次预期为零缺失、零 quarantine。

## 3. 固定分解

### D1：端到端差距分解

对 Q61--Q80 的 NSESche/FaaSRank 配对 run 计算：

- fixed-window throughput、completion ratio、cost/completed、mean/p95/p99 latency、
  per-run QPR；
- completed function 的 schedule wait、cold-start wait、data wait 和 execution
  duration；
- cold-start event share。

每个量先在 run 内聚合，再在 20 个配对 seed 上报告均值与 NSESche-minus-
FaaSRank 差；不以请求数把某个 seed 隐式加权为多次独立重复。

### D2：NSESche 决策与可行性

从全部 active windows 聚合以下预先声明字段：

- `waiting_for_candidate_nodes / pending_request_function_pairs`；
- `candidate_evaluations / assigned_players`；
- selected-starting share、running-warm availability 与 bypass share；
- assigned-node count、normalized dispersion、co-location conflict proxy；
- cross-node placement ratio；
- queue/pressure、node CPU/memory、queue area/peak。

### D3：solver 与 outer feedback

固定检查：assignment moves/player、inner/outer rounds、stable/oscillation/limit-hit、
price-adjustment active-window share、price spread、empirical social gap、reference-
below-current。no-player window 单列，不能计作不收敛。

### D4：paper utility / welfare 对照

用同一 shared post-hoc evaluator 比较 NSESche 与 FaaSRank 的 baseline-price
welfare 及五个 utility components，均按 assigned player 归一化。该对照只检查
“paper objective 是否与运行指标出现系统性错位”，不把 FaaSRank assignment
称为 Nash equilibrium，也不把跨策略演化后的 window 当成同一状态的因果实验。

### D5：G2 六 cell 外部一致性

对 C0 `ready_order` 的六个 topology/load cell 重复 D2--D3 聚合；C1/C2 只用于
确认已失败 initialization 家族的行为，不参与新候选选择。G2 low baseline 行
只复述冻结 gate，不再次搜索有利方法或 seed。

## 4. 固定关联分析

对 20 个 Q seed，以下 NSESche run-level 诊断量与两个配对 outcome gap
（throughput gap、QPR gap）计算 Spearman rho：

1. waiting share；
2. candidates/player；
3. selected-starting share；
4. warm-bypass share；
5. placement dispersion；
6. co-location conflict ratio；
7. cross-node placement ratio；
8. assignment moves/player；
9. outer-feedback active share；
10. mean price spread；
11. queue area/arrival；
12. mean node-memory utilization。

全部 24 个 rho 原样报告；不只展示最大值。它们是探索性机制证据，不报告经过
多重搜索伪装的 confirmatory p-value。

## 5. 预注册判定规则

1. D1 的“主差距阶段”是四个 stage 中 NSESche-minus-FaaSRank 的 20-seed
   平均差最大的正值；同时报告正差 seed 数，不能因不满足阈值换定义。
2. 某机制轴只有在方向与主差距阶段一致、相应 outcome-gap 的
   `|Spearman rho| >= 0.40`，并在 G2 C0 六 cell 聚合中不与机理解释明显矛盾时，
   才进入下一项 observation-only counterfactual diagnosis。
3. 若最大合格轴仍属于 warm/finish/initialization 或纯 iteration-budget 家族，
   只把它记为失败解释，不重新授权该家族。
4. 若 solver/path-dependence 轴合格，下一步只允许实现不反馈到命令的多起点
   strict-PNE 诊断：相同 utility、相同 strict best response，比较不同预声明
   player orders 的 PNE hash、paper welfare 和 projected-finish proxy。
5. 若 feasibility/concentration 轴合格，下一步只允许对共享候选集做
   observation-only scarcity/order counterfactual；不能缩窄 baseline 候选集或
   给 NSESche 私有扩容能力。
6. 若 feedback 轴合格，下一步只允许记录 fixed-baseline-price 与现有 feedback
   path 的 counterfactual assignment；不能根据 Q/D 结果直接修改 `r0`。
7. 若没有轴合格，则 G3 机制候选保持 blocked；不得用旧柱、单个 seed 或人工
   直觉补一个候选。

observation-only counterfactual 仍不等于候选。只有其在全部封存诊断状态上给出
一致的机制方向，才能另写 G3 candidate preregistration，并使用全新 D71--D75
估计效果。

## 6. 输出与停止条件

- 机器可读：`G3_EXISTING_LOG_DIAGNOSIS.json` 和 run-level CSV；
- 人类审计：`G3_EXISTING_LOG_DIAGNOSIS_AUDIT.md`；
- 本阶段 online runs：0；
- 本阶段正式结果：0；
- `D71_authorized=false`；
- `homogeneous_middle_formal_authorized=false`。

诊断文件必须列出全部输入 run、全部预声明字段和全部关联；完成审计后单独提交。
