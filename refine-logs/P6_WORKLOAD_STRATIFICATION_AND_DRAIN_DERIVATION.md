# P6 固定负载输入、排空与指标口径推导

日期：2026-09-05（Asia/Shanghai）
阶段：P6-A；定稿时没有 P6 tape、reference、binary 或 online observation。

## 1. 从 P5 得到的输入结论

P5 的九条输入带 request rate 接近既有 profile，但随机 DAG 的静态工作量不同：

| Load/seed | requests/s | 静态 CPU demand/capacity index |
|---|---:|---:|
| low/P5P01 | 1948 | 0.6299 |
| low/P5P02 | 1931 | 0.2812 |
| low/P5P03 | 1880 | 0.2865 |
| middle/P5P01 | 2543 | 0.5164 |
| middle/P5P02 | 2532 | 2.4953 |
| middle/P5P03 | 2481 | 0.6374 |
| high/P5P01 | 7178 | 4.2904 |
| high/P5P02 | 6996 | 3.8957 |
| high/P5P03 | 7019 | 1.5500 |

low/middle/high 应明确指名义到达率等级，不应宣称每个 seed 的实际资源压力都严格
递增。相同到达数对应不同 DAG 工作量是需要报告的随机性，不是无效样本。

本定稿撤回未提交草案中的静态工作量分层筛选、64-seed candidate pool、±5% rate
接受门和 200k-frame 输入排除门。它们并非审稿人要求，会改变原来的工作负载
分布并增加准备时间。没有任何 P6 输入按这些草案规则生成或筛选。

## 2. 固定 population，直接使用原有负载生成方式

保留既有 submission_v1 的三个 profile 及其 Azure-CDF-derived provenance：
low/middle/high 期望到达率分别为 1934.66、2533.14、7000 requests/s。高负载
已按历史计划从原 cache 统一缩放至 7k；不得将新实验描述为旧 27,924/s 的同场景
精确复现。函数配置和随机 DAG 生成方式保留，同一输入供全部方法 replay。

P6 pilot seed 固定为 P6P01、P6P02、P6P03，每个 seed 三个 load，共九条 tapes。
三类 RNG 使用分离标识：
- workload_seed = P6P01（依此到 P6P03）；
- topology_seed = P6T01（依此到 P6T03）；
- algorithm_seed = P6A01（依此到 P6A03）。

实现阶段必须核查三类 stream 的实际用途；若同名 seed 并不能固定 DAG/function
catalog，应显式保存并 replay catalog，不能仅凭 seed 相等断言输入一致。相同
seed 的三负载尽量共用 catalog，逐项验证；跨方法必须严格相同。

后续 development bank 固定 P6D01--P6D10，formal bank 固定 P6F01--P6F20，
按相同 domain separation 规则派生 topology/algorithm seed，且与历史全部 bank
做精确排重。正式 bank 只在方法冻结后生成/运行。每条 QC-valid tape 均保留；
不按工作量、预计 drain、NSESche 表现或旧柱接近程度换 seed。

每条 tape 仅计算描述性输入审计：
- event count、实测到达率、每 frame arrivals 的 p50/p95/p99/max；
- DAG size/depth/parallelism、unique function count、cold-start 分布；
- CPU work、memory demand、依赖边数据量、节点和链路容量；
- DAG 有向无环、id 有效、资源值 finite、必要网络路径存在。

结构错误是技术问题，修生成器后保留同 seed 的前后版本；低/高工作量和资源争用
本身不是技术失败。若正常生成器产生无法部署的函数，保留并单独标记，而不是筛掉。

## 3. Offered-work 指标

arrival horizon H=1000 frames，1 frame=1 ms。令 w_d 为 DAG 全部 function 的静态
CPU work 之和，C 为 cluster 每 frame CPU capacity 总和：

    W_cpu = sum_arrivals w_dag
    rho_cpu = W_cpu / (H * C)

rho_cpu 只描述理想全 cluster 并行下的需求/容量比，不等于真实 CPU utilization。
使用初始 environment 的 DAG/function/edge 信息计算，不读取任何 scheduler outcome。
按 seed 报告与实测 utilization、queue 和 completion 的关系；三个 nominal rate
等级的 rho_cpu 可以交叠。节点扩展时同时报告总工作量和 per-node 工作量。

## 4. 排空预算与停滞诊断

P5 的 4*W_cpu/C_cluster 加单条 critical path 只是启发式 deadline。
52/56 个低完成率 run 在最后 100 frames 没有新增 completion，提示必须检查
进展和 HPA；这些统计没有证明所有 run 永久死锁，也不能证明延长窗口一定无效。

P6 先做确定性小场景测试，检查 idle-to-zero、ready pending、resident pinning、
starting transition 和 HPA 历史保护。若这些测试不能解释/消除已知停滞路径，
不启动 90-run pilot；先保存针对性的失败状态。

预注册每条输入共同使用的 simulated deadline budget：

    D_cpu  = ceil(W_cpu / min_positive_node_cpu)
    D_net  = ceil(1000 * total_invoked_edge_MB / min_positive_link_MBps)
    D_cold = sum(cold_start_frames over invoked unique function types)
    D_adm  = number_of_arrivals
    D_path = longest DAG path using cold start, min-node CPU and min-link transfer
    D_raw  = max(5000, ceil(1.25*(D_cpu + D_net + D_cold + D_adm)), 4*D_path)
    D_drain = min(200000, D_raw)
    hard_end_frame = 1000 + D_drain

所有方法对同一输入使用同一个 deadline。此式是资源预算，不是终止定理：
unique-function cold budget 没有覆盖任意 container churn，串行工作量也没有证明
任意策略的 liveness。超过 200k 的 tape 仍然运行并保留，记录 budget_capped=true；
不得以预算大为由替换输入。边数据量必须与 simulator 真实 transfer payload 一致，
不能仅凭 environment 字段名称推断；缺字段时先补输入导出和恒等式测试。

20-node pilot 每 run 共同 wall cap 为 30 minutes。提前完成固定 arrival cohort 时
停止；否则达到 simulated/wall cap 后保留 timeout/censoring。连续 1000 frames 没有
admission、placement、completion、remaining CPU、transfer 或 cold-start 变化时
记录 stalled_window；该计数只是诊断，不能越过 deadline 提前判永久死锁，因为
HPA history 等内部状态仍可能变化。

## 5. 原论文指标与完整 cohort 的并列报告

主图在 frame 1000 冻结与旧稿相同的 fixed-window 口径：

    C_fix          = requests completed at or before frame 1000
    throughput_fix = |C_fix| / 1000 ms
    cost_fix       = whole-platform accumulated cost at frame 1000 / |C_fix|
    latency_fix    = mean(external arrival -> completion latency for C_fix)
    QPR_fix        = throughput_fix / (cost_fix * latency_fix)

三项使用同一个 completed-count 分母；cost 的分子包括窗口内服务尚未完成请求
所消耗的资源，不能说成只对已完成请求逐项计费。完成单位也要准确称为 simulator
request（当前为 DAG/application request），不能与 function-task completion 混用。

保留原 QPR 算式，逐 run 计算后求均值。零 completion 时 throughput=0、cost/latency/
QPR undefined，完整报告，不从组均值中静默删除。正分母时用绝对容差重算恒等式。
吞吐量同时保存 requests/s 和 requests/ms，绘图转换明确；成本为 simulator internal
unit，不能称真实云账单。QPR 单位随这些基本单位确定，不是无量纲指标。

已完成请求 latency 存在 survivor bias，因此每张主性能图同时配固定窗口完成比例，
并从同一 run 的 drain 提取全 arrival cohort 的 completion、end-to-end mean/p95/p99、
cost、queue peak/area、drain duration 和未完成数量。截止时未完成请求保留右删失信息。
完全排空时可另报 clearance throughput=N_arrivals/实际总时长，以及相同 terminal
成本/latency 所算的 clearance QPR；明确它与主 QPR 的估计对象不同，不能混合。

不再沿用 P5 将 fixed-window throughput 与 terminal cost/latency 组合后称作旧稿 QPR
的做法。所有 source fields、窗口端点（含 frame 1000 completion）、统计单位和
分母变换在 recorder/analyzer 中做同一个可检查合约。

## 6. 完成、失败和旧图对齐

P6 pilot 用完整排空作为进入正式阶段的要求；失败时保留全部观测并诊断。正式实验
里的 timeout/未完成是科学结果，不能当技术错误补种子；若某方法有 undefined QPR，
不能仅在其成功子集上宣称总体 QPR 第一。

旧柱值只用于 old_pdf_alignment.csv：旧值/来源、新 mean/CI、相对差异、负载和代码
口径变化。±15% 是解释差异的提示，不是接受/拒绝 run 的门。保持原场景和窗口可减少
不必要偏差，但旧代码、随机种子及聚合来源缺失时不能承诺还原柱高。

本定稿完成后，先按共同 eligibility 推导实施确定性小场景测试及最小公共修正，再
冻结九条 pilot 输入。全程保持 low -> middle -> high 的顺序。
