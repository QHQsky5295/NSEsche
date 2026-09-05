# P6 common-ready platform pilot 零结果预注册

日期：2026-09-05（Asia/Shanghai）
协议 ID：`TSCv1-P6-common-ready-batch-v1`
阶段：P6-A
状态：预注册完成前不授权实现、输入、reference、binary 或 online sampling

## 1. 两个有限主张和对应反主张

P6 本身不检验“NSESche 最优”。它只检验：

1. 十种 placement-only methods 是否在同一 dependency-ready eligibility、candidate、
   immutable snapshot、common HPA 和 atomic batch 合约下运行；
2. 固定的 low/middle/high 到达率输入下，共同 runtime 能否完整排空 cohort、产生
   与旧稿口径相同且同时报告删失情况的指标。

反主张是：任何表面增益来自 method-specific lookahead/scaling/admission、输入筛选、
逐命令状态泄漏、未完成 cohort 或 P6 结果后的 protocol 修改。P6 的所有相对性能
字段在 gate 决定前保持密封。

## 2. 冻结的处理和 population

Methods 与顺序固定为：

```text
greedy, random, hash, load_least, sche_FaaSRank,
sche_orion, sche_jiagu, sche_OCS, sche_Hiku, sche_nash
```

场景固定为 homogeneous 20 nodes、low→middle→high，每个 load 三条独立 pilot tape，
每条 tape 十种方法配对 replay：

```text
10 methods * 3 loads * 3 pilot tapes = 90 unique online runs
```

pilot seeds 固定 `P6P01/P6P02/P6P03`，不做结果或工作量筛选。
另预声明一个 determinism duplicate：`low/P6P01` tape 上
`sche_nash` canonical observation 完成后立即重复一次。duplicate 不进入性能汇总。

节点为 20 个 homogeneous nodes，CPU 150、memory 5000；网络范围 8000--10000
MB/s；DAG type `mix`、cold start `high`、function type `cpu`；arrival/primary metric
window 1000 ms。十种方法共享 HPA、FCFS admission、container lifecycle、network、
task-memory hard capacity、no-mechanism-latency 和随机输入。

## 3. 冻结的 protocol semantics

以下两个推导文件是本预注册的规范组成部分：

- `P6_COMMON_ELIGIBILITY_AND_BATCHING_DERIVATION.md`；
- `P6_WORKLOAD_STRATIFICATION_AND_DRAIN_DERIVATION.md`。

核心版本标签为：

```text
eligibility_rule      = dependency_complete_v1
canonical_order       = arrival_req_topo_fn_v1
candidate_rule        = existing_container_parent_path_v1
hpa_pending_rule      = dependency_ready_v1
hpa_idle_zero_rule    = no_ready_no_resident_v1
batch_rule            = exact_dispatchable_set_v1
atomic_commit_rule    = common_hpa_up_place_down_v1
primary_metric_rule   = fixed_1000ms_common_completed_denominator_v1
terminal_metric_rule  = full_arrival_cohort_v1
workload_rule         = fixed_seed_nominal_arrival_profiles_v1
drain_rule            = capped_work_network_cold_budget_v1
```

任何标签、函数实现、schema 或 hash 在 first online observation 后改变，都产生新
protocol ID，旧 P6 observation 只作保留的失败证据。

## 4. 分阶段授权；当前只到 P6-A

### P6-B1：共同实现

本预注册提交并完成静态审查后，继续既有执行授权：先写小场景测试验证 HPA
假设，再实现中央 ready index、HPA ready-pending/idle-to-zero、deterministic
scale-down、complete-batch validator 和所需 telemetry。历史协议保持可重放。
需要补全字段和依赖开关时在同一实现中完成，避免以文档逐项重新申请授权。
该阶段可运行 deterministic fixtures，不采集新的性能结果。

### P6-B2：零结果 release/manifest 审计

完整 Rust、protocol、analysis tests 全通过后，构建一次 release，冻结 source、
binary、config、schema、analyzer 和 figure/source-data contracts。生成的 90-run
manifest 必须仍未绑定 tape/reference/result，且不得含 metric/rank 字段。

### P6-B3：九条固定 pilot inputs

直接生成三个预注册 seed 的三负载 tapes，记录实测到达率和 offered-work descriptors。
不设置工作量区间、rate 容差筛选或 candidate pool。完成跨方法环境绑定、历史 seed
排重和输入结构验证后，冻结 exact hashes；DAG 和负载强弱的随机差异原样保留。

### P6-B4：最小依赖冻结

- 对九条 pilot tapes 构建 NSESche 运行所需的九个 offline social references。
  当前 baseline 存在 posthoc welfare observer，不能未经实现就声称不依赖 reference。
  P6-B1 应增加显式 pilot observer-disabled 模式，验证仅关闭只读评估，不改变 policy
  action、HPA 或模拟时间；由此节省 baseline 的 81 次 reference builds。正式 welfare
  比较再按状态建立所需 reference，独立计入评估时间。
- 复用或重建 FaaSRank model 前必须证明 training tape 与全部 pilot/development/formal
  tape hash 不相交；model/source/training receipt 在 online 前绑定。
- reference 的 state/assignment sequence、missing/nonpositive fallback、build cost 和
  lookup schema 全部审计。

### P6-B5：result-blind selection/analyzer freeze

冻结 exact 90 rows、load-major/seed-major/method-order、one-attempt-first-valid
规则、duplicate、十一项 gate 和相对结果密封。online parent 必须在该提交时不存在。

### P6-C：一次完整 pilot

按 low、middle、high 顺序执行 90 rows；duplicate 紧接 low/P6P01/NSESche 的
canonical observation，不再在末尾额外执行。每个 load 的协议检查通过后进入下一
load，pilot 不按 NSESche 排名决定进度。QC-valid observation 不因数值重跑；technical
failure 沿用最多三次同 seed/tape/config 重试，所有 attempts/ledgers 保留。

## 5. 十一项全合取 gate

相对性能解封前按以下顺序一次决定：

1. **population/identity**：90/90 unique run specs；method/load/tape/binary/config/source/
   schema hashes 完整，无跨 runtime 拼接。
2. **fixed input population**：九条 tapes 精确对应 P6P01--P6P03 与三个既有 profile；
   seed 未因到达率、工作量、预算或结果替换；rho_cpu 等只用于描述，不设区间门。
3. **cross-method exogenous identity**：同 tape 的 arrivals、DAG/function/node/network、
   algorithm-independent RNG 和 initial snapshot hashes 完全相同。
4. **central eligibility/HPA identity**：所有方法绑定同一 `PreAllDone` ready builder；
   HPA pending floor 读取同一 ready index；future unscheduled 不 pin container；idle-zero
   与 resident pinning tests/telemetry 通过。
5. **candidate/batch integrity**：每窗 action keys 精确等于 `D_t`，node 均在 `C_t`；
   无重复、遗漏、额外 player、private scale/admission 或 silent rejection。
6. **atomic timing**：HPA 与 policy 读取同一 immutable snapshot；一次 envelope 提交；
   无 policy 观察本窗 applied command；up/place/down conflict rule 一致。
7. **FCFS/cap/conservation/dependency**：arrival=waiting+active+completed+declared terminal
   outcomes；FCFS prefix、active cap、task/container memory、parent-complete execution、
   network path和 frame timing 全通过。
8. **complete cohort/liveness**：90/90 runs 在共同 deadline 内
   `completed=arrivals`、waiting=active=0，无 drop/reject/timeout/censoring 和
   permanent-deadlock 证据；stalled_window 只作诊断，不自行早停；fixed window 每 run
   至少一个 completion。达预算上限属于 retained scientific timeout，不补 seed。
9. **metric identity**：fixed-window throughput/cost/latency/QPR 使用同一 completed
   denominator，cost 分子为窗口内全平台累计成本；terminal cohort 单独报告；
   request/task 区别、窗口端点、单位、重算容差、quantiles 和删失统计全通过。
10. **reference/model/determinism**：九个 NSESche references 和 FaaSRank model 绑定
    完整；duplicate 的 workload、eligibility/candidate、HPA、policy action、terminal
    和 scientific result semantic hashes 相同。
11. **result blindness**：1--10 的决定文件在任何 NSESche/baseline mean、QPR、rank、
    win/loss 解封前生成；old PDF bars 和 method outcomes 未参与 tape/gate acceptance。

十一项必须全真才允许 P6 通过，并仅授权下一份 formal/development protocol 的
零结果预注册；P6 pilot 永远不进入论文主图或 formal aggregate。

## 6. 失败、修正和停止规则

- 输入结构/生成器错误：保留原输入、修正生成器并冻结同 seed 的新版本；正常
  DAG 工作量极端、负载重叠或 budget_capped 不能作为换 seed 理由。
- implementation/identity/schema/QC gate 失败：停止，保留全部 evidence，只允许一个
  最小公共修正及新 protocol version；不得只修 NSESche 或只重跑低分方法。
- complete-cohort gate 失败：先区分公共 HPA liveness、deadline 实现和真正 method
  timeout。公共故障修复先在同一失败 tape 重放用于回归，保留前后两版，不把新
  seed 当成修复。只有进一步开发会使用其性能信息时，下一独立 pilot 才使用新
  bank，并在任何结果前完整冻结；不得消耗 development/formal seeds 作为替补。
- 无论 P6 相对结果如何，本阶段都不允许继续调 NSESche 参数或宣称其最优。

## 7. P6 之后的最短合规路线

P6 全通过后：

1. 从 homogeneous-20 low 开始，在 10 development tapes 上冻结九个 baselines 一次；
   后续 middle/high 同理按序执行。不同 runtime 的旧 baseline 不能直接拼接；
2. 只允许至多一个有独立源码假设、未被 G2--G19/P2--P4 覆盖的 NSESche 机制候选；
3. 冻结 NSESche source/binary/params；
4. 在 20 完全未见 paired formal tapes/load 上从 homogeneous-20 low 开始；先完成
   该组完整主比较和效果检查，再推进 middle/high；论文展示仍按 Fig. 4→5→6--8→9→10，
   reviewer-only burst/QoS/welfare 只补必要证据；
5. 保留所有 QC-valid formal observations，样本量不随胜负增长。

如果 NSESche 在共同平台上仍被同一 baseline 稳定支配，应缩减论文性能主张或停止
高成本矩阵；不能以 seed、load、deadline 或 baseline 重实现来制造第一。

本预注册与 V8、P6-A 静态审查一起保存。各阶段检查通过后按既有授权继续，
不需要再次询问用户同一执行许可。定稿时没有执行 P6 sampling。
