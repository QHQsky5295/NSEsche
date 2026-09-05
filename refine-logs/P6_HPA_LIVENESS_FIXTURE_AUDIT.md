# P6-B1 HPA 与缩容定向验证

日期：2026-09-05。状态：HPA/缩容子步骤完成；P6-B1 整体未完成。

本轮先完成综合计划评审；用户随后更新目标文件并要求转入执行。当前目标文件为
C:\Users\99349\.codex\attachments\54c90cbd-dfd8-4c85-a12e-503ca5092d25\goal-objective.md。
主性能开发目标仍为各负载 throughput 和 QPR 双领先；本步骤没有性能结果，不宣布任何性能组闭口。

## 已实现

- HPA 以不可变 demand 输入分别执行 legacy 与 reviewer-v5 分支。
- legacy 分支保持旧 memory arithmetic、未来未放置请求 floor 和 tolerance 提前返回，
  以保留旧协议回放行为；本次没有更改 NSESche 效用或 best response。
- reviewer-v5 只对 dependency-ready 或已入 node queue 的任务施加 pending floor；
  空闲基础 memory 不再阻止 desired=0；启动/驻留任务的实例得到目标数量保护；
  tolerance 不绕过 demand/min/max。
- Node 提供 function-specific pending count，不把别的函数的任务计入。
- reviewer-v5 缩容另外保护具体有 node-queued 任务的容器；仅保住实例数量不能
  保证保护正确的 node。新协议在筛选后按 node/function 排序，旧协议保留旧顺序。

## 验证结果

1. cargo test --offline ... p6_ -- --test-threads=1：12/12通过。
   其中8项HPA决策测试、3项缩容选择测试、1项实际Node队列计数测试。
2. 相同构建的 scheduler 单元测试：84/84通过。
3. 原子scale/place冲突测试：2/2通过。
4. Node queue breakdown：3/3通过，其中一项与第1项重复。

合计100个不同测试通过。没有声称整个162项Rust测试套件已执行；
protocol/analysis全套及端到端fixture仍待P6-B1完整集成后验证。
编译保留102条既有风格/未使用项等warning，本轮未清理无关代码。

空闲fixture在相同memory输入下重现legacy desired=1、新规则desired=0；
future descendant不再独自pin空闲实例。此证据证明决策路径的具体差异，
不证明它是P5全部停滞的唯一原因，也不等于在线吞吐量/QPR有所提高。

## 激活与证据边界

新分支只对显式 reviewer-v5 生效。当前配置验证尚未开放完整reviewer-v5运行；
没有生成P6 tape/reference/release/online result。不允许现在拿新分支与旧baseline拼图。

仍需：中央唯一ready index与所有policy的一致消费、完整batch validator、
协议telemetry、posthoc observer显式开关、drain/主指标schema集成、全套回归、
之后的release/输入/reference/固定pilot。直接按既有授权继续，不逐项重新申请许可。

## 工作区源文件SHA-256（rustfmt后，Git换行转换前）

| 文件 | SHA-256 |
|---|---|
| serverless_sim/src/scale/num/hpa.rs | 195fc302af820c469bb197ec607466c95aedee7a444ce50a8610375029b20049 |
| serverless_sim/src/scale/down_exec/mod.rs | 03433510feab3eed658e81cb9b253ed5e2c168e90c27d4408e1ba82157bc5ecc |
| serverless_sim/src/node.rs | 64be9805983322023d7f87d391b5cf2abfde195047c393a8b01185756db8c67f |

原目录sche_nash.rs仍为bd106e46...e75814，原（NSESche）PLAN.md仍为19ed3f8d...8ce99。
P1永久包、所有历史baseline和失败观察未删除/覆盖。

## 论文阶段汇报

- 已有可写材料：P1固定快照/精确小状态材料，保持原适用范围。
- 当前：同构20节点low的共同执行前置验证，HPA/缩容子步骤已完成；
  新版本性能尚未测量，最新P5诊断不支持双领先。
- 尚未完成：同构正式结果及后续参数、消融、异构、扩展、突发、QoS/公平性、
  特征和近邻对照。计划评审文件不改变这些事实。
