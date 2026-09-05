# P6 common eligibility、HPA liveness 与原子 batching 推导

日期：2026-09-05（Asia/Shanghai）
阶段：P6-A，只读推导
状态：零 P6 输入、零 P6 reference、零 P6 binary、零 P6 online result
源代码审计起点：`075fee8be96d732113d317da004d6f7b99277cb1`

本文件只使用旧稿、当前源码、P1 已闭口证据和 P5 全量保留的诊断证据。它不含
任何 P6 调度结果，也不授权根据 NSESche 的胜负修改公共协议。

## 1. 比较对象与适用边界

旧稿把每个 scheduling window 的待调度函数集合记为
`F={f1,...,f|F|}`，并说明每个 `fi` 是 “a request to be scheduled”；旧稿没有定义
“父函数仅已 placement”即可让子函数进入 `F`，同时又明确把研究范围限定为共同
scaling 下的 contention-aware scheduling。当前正式实现中，NSESche 和 FaaSRank
使用父函数完成语义 `PreAllDone`，OCS 使用 `PreAllSched`，其余多数方法调用
`All`，再由候选节点 helper 间接要求父函数已有 placement。P5 因此不是同一
placement-policy estimand。

需要冻结的反主张是：新的性能差异不能来自某方法获得更多 lookahead、私有
admission、私有 HPA、逐条命令可见状态或静默丢弃难调度 player。P6 的目标只是让
十种方法在同一 ready set、candidate map、snapshot 和 batch 边界内比较 node
selection；它不改变论文 Eqs. (1)--(20)、严格 Eq. (15) 或 QPR 公式。

## 2. 源码和 P5 证据

### 2.1 当前已有的正确公共路径

- `serverless_sim/src/mechanism.rs:473--518` 已让共同 HPA 与 placement policy 读取
  同一个 immutable `SimEnvObserve`，先收集两者命令，再统一提交。
- `mechanism.rs:525--607` 的 firewall 已禁止 placement policy 发出 scale command；
  `mechanism.rs:643--658` 已发送一个包含 scale-up、placement、scale-down 的原子
  command batch。
- `serverless_sim/src/sim_run.rs:87--123` 已提供共同 hard-feasibility helper：候选
  node 必须已有该函数的 starting/running container，父函数必须已有具体 node，
  跨 node 时链路必须 finite 且 positive，返回 node id 稳定排序。
- 执行层继续检查父函数完成、data transfer、container 状态和 task-memory hard
  capacity；placement 只把任务绑定到 HPA 所有的队列，不等于立即执行。

所以 P6 不重写 dispatcher，也不允许恢复 native mode。最小正确改动是把
dependency-ready eligibility、HPA pending floor、idle-to-zero 和 complete-batch
validation 提升为同一个中央合约。

### 2.2 P5 暴露的停滞证据

P5 保留 90/90 runs。56/90 terminal completion ratio `<0.95`，十种方法均受影响。
对这 56 个失败 run 的最后 100 frames 做只读核对：

- 52/56 在最后 100 frames 内 completed count 完全不变；
- 56/56 的 node pending task count 为 0，54/56 没有 starting container；
- terminal running-container count 的 min/median/p95/max 为
  `42/200.5/223/232`；
- terminal node CPU utilization mean 的中位数为 0，而 active requests 中位数为
  100、external FCFS queue 中位数为 2088.5；
- 44/56 仍有正的 dependency-ready unscheduled tasks。

该签名提示公共执行/HPA 路径可能停滞，但它没有直接证明永久死锁。
node.rs 的 running_task_cnt 统计 container 内全部 resident entries，包含等待任务，
不能据此声称它们正在消耗 CPU，也不能推导准确 idle-container 数。

### 2.3 HPA pending 语义与 `allow_scale_to_zero` 不一致

`serverless_sim/src/metric.rs:98--127` 同时维护两种计数：

1. `fn_unsche_req_cnt`：active DAG 中所有尚未 placement 的函数，包括父函数未完成的
   future descendants；
2. `fn_2_ready_sche_tasks`：父函数均已完成的 ready-unscheduled 函数。

当前 `serverless_sim/src/scale/num/hpa.rs:98--100` 用第一种计数强制
`min_instances_when_pending=1`。这会为 active DAG 的未来阶段提前固定 container，
而 placement-only NSESche 又只消费第二种集合。与此同时，已有 container 的基础
memory utilization 会让 HPA 的 `ceil(current/target)` 至少为 1；即使
`allow_scale_to_zero=true` 且没有 ready work，idle container 也通常不会得到 target
0。这条源码路径是具体的 liveness 风险；其是否解释 P5 全部停滞，仍需确定性
状态重建和小场景测试。不能在测试前宣称它是唯一根因或修复已生效。

## 3. 三个 eligibility 方案的第一性原则选择

| 方案 | 含义 | 判断 |
|---|---|---|
| 各方法保留 `All/PreAllSched/PreAllDone` | 比较完整但边界不同的系统 | 拒绝；无法把差异归因于 node selection |
| 中央 `PreAllSched` | 父函数一旦 placement 就允许子函数预放置 | 本协议不采用；它是可行的另一种调度边界，但偏离当前 ready-only 实现；G6 的失败不证明对所有方法采用它无效 |
| 中央 `PreAllDone` | 只有父函数全部完成的 invocation 才进入共同集合 | 采用；与当前 NSESche/FaaSRank 和执行语义一致，最清楚地隔离 placement 决策 |

论文未规定 readiness 的空白不能证明其他 readiness 规则错误。本协议采用
`PreAllDone` 是沿用当前 ready-only 研究对象的设计决定，在任何 P6 结果前固定。Orion、Jiagu、Hiku 等仍可保留各自的 node scoring、priority、
bundling signal 和 deterministic tie-break，但本文只能称其为共同平台上的
placement-only adaptations，不能声称复现了其私有 scaling/prewarming 系统。

## 4. 冻结的中央合约

令 `A_t` 为 frame `t` 已由共同 FCFS admission 接纳且尚未完成的 requests。中央
orchestrator 从唯一 immutable snapshot 构造：

```text
E_t = {(r,f): r in A_t,
                f 尚未 placement,
                f 的每个 parent 在 snapshot_t 中已标记完成}

C_t(r,f) = placement_candidate_ids(r,f,snapshot_t)
D_t = {(r,f) in E_t: C_t(r,f) 非空}
W_t = E_t \ D_t
```

其中 `E_t` 是 dependency-ready set，`D_t` 是当窗必须完整返回的 dispatchable
set，`W_t` 是需由共同 HPA 解除 container scarcity 的 waiting set。canonical
identity/order 固定为：

```text
(arrival_frame, request_id, DAG topological_rank, function_id)
```

canonical order 用于身份、hash、审计和共同 deterministic tie-break；方法可以在
`D_t` 内部使用自己的预注册 priority/order 更新 projected state，但不能扩大、
缩小或延迟 `D_t`。

### 4.1 共同 HPA liveness 规则

- `min_instances_when_pending` 只读取按 function 聚合的 `E_t`，不读取所有 future
  unscheduled descendants。
- `W_t` 中某 function 没有 container 时，HPA 在同一 snapshot 上请求至少一个
  instance；该 frame 不伪造 placement，下一 frame 再由共同 candidate map 纳入。
- 当某 function 的 ready count、resident pending/runnable/data-transfer task 均为 0，
  且 `allow_scale_to_zero=true`、`min_instances=0` 时，HPA desired count 必须为 0；container basic
  memory 不得把 idle target 向上取整为 1。
- resident work 永远 pin 住其 container；`careful_down` 继续提供共同的历史保护；
  scale-up/down placement 仍由共同 `least_task/default` executor 完成。
- 每窗记录 `ready_by_function`、`waiting_by_function`、`resident_by_function`、desired/
  actual instances、scale failure reason 和 idle-to-zero decisions 的 semantic hash。

这是一项共同 runtime 修正，不进入 NSESche 消融。新规则只在显式 reviewer-v5
协议启用；历史 reviewer-v3/v4 仍可重放。HPA tolerance 分支不得提前返回而绕过
ready/resident/min/max 规则。已有 starting container 和所有 resident entries 都要
防误删；默认 down executor 的候选按 (node_id,function_id) 排序后再截取，避免
HashMap 迭代改变被删除的实例。先以小场景验证这些行为，再启动 pilot。

### 4.2 完整 batch 与 fail-closed validation

每个 policy 一次返回一个完整 placement batch。中央 validator 必须同时证明：

1. batch key 集合与 `D_t` 精确相等；
2. 每个 `(request_id,function_id)` 恰好出现一次；
3. 所选 node 属于该 player 的 `C_t`；
4. policy 没有 scale/admission/lifecycle command；
5. batch 在 policy 返回后才一次提交，policy 不观察本窗任何 HPA 或其他 placement
   command 的应用结果。

重复、遗漏、额外 player、invalid node、channel failure 或 non-placement command
均为 protocol violation；不得静默忽略、补默认 node 或只重跑该方法。

### 4.3 原子提交时序

保留现有共同路径和以下顺序：

```text
snapshot_t
  -> common HPA decision(snapshot_t)
  -> placement policy complete batch(snapshot_t, E_t, C_t)
  -> validator
  -> atomic envelope {scale-up, placement, non-conflicting scale-down}
  -> runtime applies envelope
```

所有 policy 均不能在 `snapshot_t` 中使用本窗新 scale-up 的 container；若 scale-up
成功，该 container 最早在下一 snapshot 成为 candidate。这一拍延迟对十种方法
完全相同。

## 5. 必须 hash-bound 的 schema

P6 实现审计前必须冻结并写入每个 run manifest：

- `eligibility_rule = dependency_complete_v1`；
- `canonical_order = arrival_req_topo_fn_v1`；
- `candidate_rule = existing_container_parent_path_v1`；
- `hpa_pending_rule = dependency_ready_v1`；
- `hpa_idle_zero_rule = no_ready_no_resident_v1`；
- immutable snapshot schema hash；
- `E_t/C_t/D_t/W_t` semantic hash；
- policy action semantic hash；
- atomic envelope semantic hash；
- common HPA config/source hash、policy adapter source hash、release binary hash。

跨方法同 tape 的外生 input 和规则 hash 必须相同。轨迹分化后 `E_t/C_t` 的数值可
合理不同，因此不要求不同方法逐帧集合 hash 相等；要求同一 run replay 完全相等，
并要求所有方法由同一中央函数生成而非私有复制。

## 6. P6-B 实现与测试清单

在本推导和 P6 零结果预注册提交后，才允许：

1. 将 ready-set builder 提升为中央唯一实现，删除十个 adapter 的私有
   `CollectTaskConfig` 选择；
2. 让 HPA pending floor 复用同一 ready index，并实现真实 idle-to-zero；
3. 在现有 atomic dispatcher 前增加 complete-batch validator；
4. 增加 `All/PreAllSched` 无法越过中央边界、internal reorder 仍完整覆盖、zero-
   candidate 驱动共同 HPA、idle eviction、resident pinning、dependency execution
   safety、invalid batch fail-closed、duplicate replay 等 directed tests；
5. 运行完整 Rust/protocol/analysis tests，构建一次 release，并在零 online result
   条件下审计 source/binary/schema hash。并审计 adapters 在中央边界内保留的机制，
   特别是 FaaSRank 的训练实现和 Orion/Jiagu/Hiku 的删减范围，不将简化打分器
   无说明地称为原论文完整实现。

截至本文件提交，不授权 P6 binary、input capture、reference build 或 online run。

## 7. 证据绑定

- P5 gate report：
  `runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/`
  `p5_common_platform.gate_report.action_semantic_v2.json`，SHA-256
  `149b2245c0a34467b66ad2348f153995f720f096d170366ffa5d8baf22d58053`。
- P5 result audit：`P5_COMMON_PLATFORM_PILOT_RESULT_AUDIT.md`，SHA-256
  `158ae7038f25fd2f7b6c7bb04e15e94f2d42dc112001216e6df00efb75cf6d78`。
- 被审源码哈希：`metric.rs` `9736f0e9...a289c`；`hpa.rs`
  `97b99afc...840bc`；`sim_run.rs` `8226f8c6...a3cb7`；`mechanism.rs`
  `2248a0c9...20a7`；`sim_env.rs` `6a2439c7...af8e`。
