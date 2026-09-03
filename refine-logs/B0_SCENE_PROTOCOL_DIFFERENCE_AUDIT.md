# B0 旧稿场景协议差异与可识别性审计

日期：2026-09-03（Asia/Shanghai）

状态：**B0 CLOSED — `legacy protocol unidentifiable`；不启动 30-run
calibration pilot；当前 TSCv1 公共协议继续作为独立重跑基准**

## 1. 判定问题与证据边界

B0 只回答一个问题：旧 PDF/Excel 的大幅数值差异能否归因到一个可证明、对全部
方法共同生效、并可唯一恢复的历史协议变化？审计比较三个只读代码点：

- 历史数值提交 `54280eec20a3c3aebaadbd0c4cd39ed2b6be2b64`；
- 重投稳定起点 `26fbe54`；
- G1 正式运行时 `98f822c`（binary SHA-256
  `7f1d1ad8...06a4`）及当前审计 HEAD。

旧 PDF SHA-256 为
`03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`。
两个历史工作簿及其 blob/hash 见 `LEGACY_RESULT_PROVENANCE_AUDIT.md`。

本审计不把旧柱高度当作参数选择目标，不删除或重跑低分 seed，也不把开发数据
混入正式统计。

## 2. 字段级差异表

| 轴 | `54280e...` 可见历史状态 | `26fbe54` / G1 corrected runtime | B0 判断 |
|---|---|---|---|
| 运行窗 | `ProxyEnv3.total_frame=1000`；记录最后一帧；无 drain | E1 到达窗、观察窗和总帧均为 1000；无 drain | 同构 low E1 的主要差异不是 drain |
| 负载倍率 | low/middle/high 分别 `0.2/0.6/1.4` | steady capture 保留相同比例；low profile 声明 `0.2` | 标称倍率一致 |
| DAG 组成 | mix 为 50 DAG：5 个 single + 45 个 CSV DAG | 同一生成结构；正式 config 明确 `dag_count=50` | 结构一致，但实例 seed 不同 |
| seed | `ProxyEnv3.rand_seed=""`；`batch_run.py` 重复 `reset()` 时不改变 seed | workload/topology/algorithm seed 显式分离；Q61--Q80 配对 replay | 统计对象不同；旧 `run_time` 不是独立 seed 证明 |
| workload cache | 从未跟踪的 `cache/<no_mech_str>` 读写 IAT/CV | submission-era profile 声明 legacy cache `sd.rflow.dtmix.cshigh.ftcpu`、SHA `632f2e...`，并冻结成 tape | 当前 profile 有来源；旧工作簿没有字段把柱值绑定到该 cache |
| 节点 | 20 homogeneous；CPU 150、memory 5000、保留阈值 3500 | 20 homogeneous；CPU 150、memory 5000、阈值 3500 | 数值一致 |
| 网络 | 每条链路从 8000--10000 采样 | 8000--10000 MB/s，topology seed/环境 hash 显式绑定 | 范围一致，具体图不一致且旧图不可恢复 |
| 函数资源 | CPU 2--400、memory 10--2000；cold memory 100、cold CPU 0.1--2、cold time 1--300 | 相同生成范围 | 范围一致，具体函数样本不一致且旧样本不可恢复 |
| cache policy | 历史 batch YAML 选择 `no_evict` | common HPA config 选择 `no_evict` | 可见配置一致；工作簿仍没有 config binding |
| HPA 参数 | target 0.5、tolerance 0.1、careful-down history 100；pending 时至少 1 个实例 | 同值，且显式声明 check period 1、min 0、pending min 1、allow zero | 标称控制值等价 |
| HPA 扩容 | `least_task` 把内存不合格的空节点计入“已有实例”，可能少发扩容命令 | 只把真实容器计为已有实例，并只对内存合格节点发命令 | 公共运行时实质改变；当前是已验证 bug fix，不能为贴柱回滚 |
| scale/place 提交 | scale 命令先发送，scheduler 再观察/发送；可能在同窗缩掉被选择容器 | HPA 与 scheduler 观察同一快照，过滤冲突 scale-down 后原子提交 | 公共运行时实质改变 |
| placement 可行集 | baseline 各自实现；old Hash 可选任意节点，其他方法的容器/路径检查不统一 | 全方法调用共享 `placement_candidate_ids`，只选 HPA 已创建的 starting/running 容器并验证父路径 | 比较边界发生实质改变，旧方法间不完全同协议 |
| 执行顺序 | 多个 HashMap 遍历和 `thread_rng`/全局随机源可决定资源优先级 | 稳定 key 顺序；Random/FaaSRank 等绑定 algorithm seed | 旧重复运行既非独立环境，也不保证算法确定性 |
| cold-start 转换 | 无本轮硬内存预留语义 | 稳定点先加入硬边界；G0 corrected runtime 又在 runnable task 前为即将完成的启动转换预留内存 | 公共运行时两次实质改变；G1 绑定 corrected semantics |
| 简单 baseline | Greedy/Random/Hash/Load Balance 各用自有候选逻辑；Random 使用进程随机源 | 使用共享可行集；Random 使用显式 Pcg64 seed；稳定 tie-break | 行为和方差来源改变 |
| 复杂 baseline | FaaSRank/Hiku/OCS/Jiagu/Orion 为早期实现，其中部分带学习、预热或扩缩容语义 | 全部重写为 placement-only adaptation，共享 HPA/lifecycle；FaaSRank 参数与训练来源显式冻结 | 五个实现均为数百行级差异，旧新柱不能视为同一方法版本 |
| NSESche | 负载自适应启发式配置、不同量级权重/阈值/价格分支；`54280e` 还加入环境变量消融 | 按论文 Eqs. (1)--(20) 的 utility、严格 Eq. (15)、offline reference 和显式 outer feedback | 不是同一可重放实现；公式一致版优先于复刻旧启发式 |
| throughput | `sum(frame completions) / final frame`，数值单位为 requests/frame = requests/ms | fixed 1000-ms observation window；输出 requests/s 后除 1000 绘图 | steady E1 数值口径等价；旧图 `RPS` 标签不精确 |
| latency | 最后一帧的已完成请求平均 end-to-end latency | steady E1 同一 1000-ms 完成 cohort；drained cohort 仅用于带 drain 的后续实验 | steady E1 口径等价 |
| cost | recorder 写 `cost_each_req = accumulated cost / completed` | `simulator_internal_cost_per_completed_request` | 主口径等价 |
| QPR | recovered exporter 用 `rps/(latency*cost)`；另一个旧 YAML 曾写成 `1/(cost*time)` | 每 run 先算 `throughput/(latency*cost)`，无效分母 fail closed | 工作簿公式正确，但旧脚本体系存在口径歧义 |
| 聚合 | exporter 对同一 `(load, algorithm)` 执行字典覆盖；工作簿单元格是常量、无公式、无 seed/run/config/hash | 20 个配对 seed 全保留；run-level QPR 后再报告均值/CI | 最大的不可恢复缺口；旧柱不能称为可重放 20-run mean |

代码量核对进一步支持上述判断：从 `54280e` 到 `26fbe54`，九个 G1 baseline
文件全部变化；FaaSRank、Hiku、OCS、Jiagu、Orion 分别发生数百行增删。相同九个
文件从 `26fbe54` 到当前 HEAD 没有再变化，所以 G1 的 baseline 差异不是本轮
NSESche 调参造成，而是历史论文柱与重投公共实现之间的版本断层。

## 3. 旧 Fig. 5 与 Excel 的绑定程度

两个工作簿包含同一组 `4 variants x 3 loads x 4 metrics` 常量，只是矩阵方向
不同。PDF 第 8 页 Fig. 5 的全部柱高与这些常量一致；例如 Full NSESche 为：

| Load | Cost | Latency (ms) | Throughput (requests/ms) | QPR |
|---|---:|---:|---:|---:|
| low | 0.313890 | 34.0659 | 1.700 | 0.158983 |
| middle | 0.398824 | 295.1468 | 1.117 | 0.009489 |
| high | 0.306416 | 413.8584 | 2.211 | 0.017435 |

因此 Fig. 5 可标记为 **historical Excel constant**，而非纯像素估读。然而，
工作簿创建于提交 `54280e` 之前，且没有 source commit、binary、输入 cache、
seed 或 records 路径；“柱来自工作簿”不等于“运行协议可恢复”。Fig. 6 baseline
目前只有 PDF 估读值，没有找到对应 run-level 数据。

## 4. 为什么不运行 30-run calibration pilot

预注册规则只允许在发现一个可证明、唯一、对所有方法共同生效的差异时运行
`3 tapes x 10 methods` pilot。这里发现的是多个耦合且不可逆向辨识的差异：

1. 旧柱没有 binary/config/seed 绑定；
2. 历史批处理重复空 seed，导出又覆盖重复 JSON；
3. 公共 runtime、候选集、确定性和 cold-start 语义均发生变化；
4. 九个 baseline 以及 NSESche 本身都跨越了实现版本。

任取一个历史 commit、空 seed 或旧 scheduler 组合进行 30 runs，只能评价人为
猜出的协议，无法验证它就是 Fig. 5/6 的生成协议。因此 pilot 的识别条件失败；
不运行是预注册的 fail-closed 结果，而不是节省负结果。

## 5. B0 immutable decision receipt

- `decision`: `legacy protocol unidentifiable`
- `legacy_bar_role`: provenance/alignment anchor only
- `calibration_pilot_authorized`: `false`
- `reason`: multiple coupled implementation/protocol changes plus missing
  run-level binding; no unique historical estimand
- `authoritative_rerun_protocol`: corrected-runtime TSCv1, fixed public scene,
  paired workload tapes, disjoint workload/topology/algorithm seeds, all
  QC-valid rows retained
- `old_pdf_tolerance_role`: diagnostic only; never a seed/candidate filter
- `paper_ready_closed`: `false`
- `formal_middle_authorized`: `false`
- `D71_authorized_by_B0_alone`: `false`

修订稿应如实把新结果描述为在可复现的统一协议下从头重跑，而不能声称逐值复现
旧 20-run mean。旧柱与新均值之间的偏差放入 alignment supplement，并逐项标记
`historical Excel constant`、`PDF estimate` 或 `missing`。

## 6. 下一步

B0 只排除了场景误归因，并未自动给出新的 NSESche 机制。G3 进入
**decision-neutral mechanism diagnosis**：仅使用完整保留的 Q61--Q80/G2 日志，
按预先声明的分解检查 completion、latency、cost、候选集与公式项之间的关系，
选出一个可证伪的单一原因后再预注册至多三个公式一致候选。D61--D70 和
Q61--Q80 不得再次承担候选效果估计；D71--D75 只能在 preregistration 完成后
生成。
