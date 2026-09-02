# G0 Eq. (16)--(20) 外层反馈可观测性审计

日期：2026-09-03（Asia/Shanghai）

状态：实现和静态/合成验证完成；等待 corrected-runtime binary 技术回放与新 reference 绑定，不含任何新实验 seed。

## 1. 目的

原窗口日志只保留最终 assignment 在 immutable baseline prices 下重新评价得到的 `empirical_gap`。该值适合跨方法比较，但不是每个 outer round 实际驱动 Eq. (19) 的 loop-local Eq. (16) gap。若直接用它绘制反馈或收敛曲线，会混淆控制量与报告量。

commit `cafb7c5` 增加只读 schema `eq16_eq19_control_path_v1`，不修改 utility、best response、price update、assignment 或 dispatch。commit `6e5643e` 又冻结 `eq14_eq16_eq19_semantics_v1` 运行语义契约，并把同一验证器同时接入分析器和 canonical 前协议 QC。

## 2. 每个稳定 outer round 的新证据

`solver.outer_feedback_trace[]` 按一基 round 编号记录：

- `assignment_hash`：该轮稳定 inner assignment；
- `nash_welfare_at_current_prices`：该轮 adjusted prices 下的 Eq. (17)；
- `reference_welfare_at_baseline_prices`：离线 baseline reference；
- `feedback_gap`：可用于 Eq. (19) 的 loop-local Eq. (16)；
- `gamma`：该轮 Eq. (20)；
- `price_multiplier_for_current_round`：本轮统一 adjusted/base ratio；
- `price_multiplier_for_next_round`：只有实际执行 Eq. (19) 时存在；
- `feedback_applied`：区分“计算了 gap”与“确实生成下一轮价格”。

`social.empirical_gap` 仍是最终 assignment 的 baseline-price 复评值。日志同时写明两种 welfare basis，二者不互相覆盖。

## 3. fail-closed 分析与 canonical 门禁

共享验证器 `analysis/feedback_trace.py` 对 trace 执行以下验证；`analysis/observability.py` 只有通过后才导出 E9 指标，`protocol/qc.py` 则在一次运行进入 canonical 前执行同一检查：

1. `run_config` 必须声明 strict Eq. (15)、immutable baseline reference/empirical-gap price basis、Eq. (19) 非递归 baseline update、Eq. (14) active-transfer proxy 与有限但无全局上界的 beta 域；
2. round 编号连续、assignment hash 和统一价格乘子有效，第一轮 multiplier 必须为 1；
3. 下一轮 current multiplier 必须等于上一轮 next multiplier；
4. 使用与 Rust 相同的 `EPSILON=10^-6` 重新计算 Eq. (16) control gap；
5. 使用窗口中的冻结 `r0` 与 `g(t)` 重新计算 Eq. (20) `gamma=r0*tanh(g)`；
6. `feedback_applied=true` 时核对 Eq. (19) `next_multiplier=1+gamma*beta*gap`；
7. 每个 scheduler window 都必须有且仅由一个合格 contract 覆盖；缺窗口、重复/迟到 `run_config`、错误 basis 或 malformed trace 均 fail closed。

新增 NSESche-only run-level 字段包括 control-gap mean/p95、gamma mean、最大价格乘子、反馈应用轮数和相邻 outer assignment change rate。它们导出到诊断表，但不与没有该外层机制的 baseline 强行做配对显著性检验。

## 4. 验证结果

- `cargo fmt -- --check`：通过。
- `cargo test sche_nash::tests`：31/31 通过。
- 新 Rust 测试证明：两轮 assignment 不变时，第一轮 control gap 触发价格更新，第二轮 control gap 与最终 baseline empirical gap 可不同；新增 trace 不改变最终 assignment。
- `python -m black --check`：通过。
- reviewer protocol tests：167/167 通过；新增门禁测试证明错误 Eq. (16) gap、错误 Eq. (20) gamma、非 strict Eq. (15) 配置和缺失窗口均不会进入 canonical。
- reviewer analysis tests：48/48 通过。
- 合成分析验证 7 个 outer traces、2 个实际反馈、0 malformed rows，并正确导出 control gap、gamma、price multiplier 与 assignment-change 指标。

## 5. 尚未证明的事项

当前验证证明日志计算和分析契约正确，但还没有 corrected-runtime 实际窗口记录。旧 D01--D60 日志不含新 schema，也不能回填。下一次获授权后必须：

1. 从包含 `16c32c2`、`cafb7c5` 和 `6e5643e` 的冻结后继构建新 binary 并记录 SHA-256；
2. 用匹配 binary 构建新的 state-keyed offline references；
3. 在 D61 前置技术回放中要求 `stream_contract_ready=true`、reference pairing、公式重算和 analyzer 均通过；
4. 只有此后才捕获 D61--D65 新 tapes。

没有主论文实验组因本次可观测性工作而闭口。
