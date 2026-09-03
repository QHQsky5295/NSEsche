# 旧稿实验数值来源与可复现性审计

日期：2026-09-03（Asia/Shanghai）

状态：只读溯源与 B0 全场景协议审计均已闭合；最终判定为
`legacy protocol unidentifiable`。旧柱可作历史锚点，但不能被认定为“20 次
独立运行均值”的可重放原始数据；不授权 30-run calibration pilot

## 1. 审计对象

- 旧稿 PDF：`（5-12V2）TSC_NSESche_Complete_IEEE_.pdf`，SHA-256
  `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`。
- 历史代码/数据提交：
  `54280eec20a3c3aebaadbd0c4cd39ed2b6be2b64`（2025-07-21）。
- 工作簿一：`scripts/experiment_results_20250721_105643.xlsx`，Git blob
  `90e45d056d372e165ea5d4741d1aaad848c490d3`，7,501 bytes。
- 工作簿二：`scripts/experiment_results_20250721_133125.xlsx`，Git blob
  `135f5dd89c7b49dffe5ad14ed30c51e15a099503`，36,671 bytes。
- 导出程序：`scripts/export_to_excel.py`，Git blob
  `3d8deb034cfea431dc864461baaf16ed101aef2a`。
- 历史 NSESche 代码线索：提交
  `e1904e7d7948cfe9820e57abf7f4885e9b3718fb` 及其祖先。

所有对象均从 Git object database 只读提取；没有签出或修改历史分支。

## 2. 找回的旧数值

两个工作簿包含相同的 NSESche/消融三负载聚合值，只是表格方向和方法名称
不同。与当前最关键的低负载锚点如下：

| Variant | Cost/request | Latency (ms) | Throughput (req/ms) | QPR |
|---|---:|---:|---:|---:|
| w/o Heterogeneity | 0.382372 | 64.6713 | 1.658 | 0.067048 |
| w/o Congestion Pricing | 0.827217 | 61.2506 | 0.874 | 0.017250 |
| w/o Social Awareness | 1.257079 | 53.2169 | 0.567 | 0.008476 |
| NSESche | 0.313890 | 34.0659 | 1.700 | 0.158983 |

工作簿中的低负载 NSESche `T=1.700`、`QPR=0.158983` 与旧 PDF 图中约
`1.7015`、`0.15907` 高度一致，因此该文件很可能是旧稿 Fig.5 以及相关
NSESche 柱值的直接数值来源之一。

## 3. 为什么它不是可重放的 20-seed 原始数据

1. 四个 sheet 均只有一个 `variant x load` 矩阵，没有 seed、run id、时间戳、
   配置哈希、binary 哈希、误差条或原始请求记录；全部单元格都是常量，不含
   统计公式。
2. 导出程序扫描 `scripts/cache/*.json` 后执行
   `self.data[load_type][algorithm] = data`。同一负载和算法若存在多个 JSON，
   后读文件覆盖先读文件；程序没有按 seed 建列表，也没有计算跨运行均值。
3. 性价比由被保留的单个 JSON 直接计算为
   `rps / (time_per_req * cost_per_req)`，随后写入 Excel。
4. 提交 `54280e...` 的 Git tree 中没有 `scripts/cache` 原始 JSON，也没有可将
   工作簿单元格反向绑定到一次运行的 records/manifest。
5. 历史 `batch_run.yml` 的 `run_time` 是“补足多少次运行”的循环计数，但现存
   工作簿既不保存这些运行，也不证明导出时曾对它们取平均。

因此，工作簿可以证明旧柱不是纯粹的 PDF 像素估读，却不能证明旧稿所写的
“20 independent runs average”，也无法重放旧置信区间。

## 4. 旧实现与当前论文公式实现并非同一方法版本

历史提交 `e1904e7...` 的 NSESche 使用另一套负载自适应策略对象、延迟权重、
成本权重、质量权重、收敛阈值和价格范围。例如其中的函数质量权重处于约
`10--20` 的量级，负载配置可使用单轮搜索和接近 1 的经验阈值，节点基础价格
还按负载分支。当前重投实现则按论文 Eqs. (1)--(20) 使用共享
`wq=0.5/0.6`、`r0=0.6/0.5`、严格 Eq. (15) best response 和已审计的
offline-reference 反馈语义。

从 `e1904e7...` 到重投协议冻结点，`sche_nash.rs`、`config.rs` 和 `score.rs`
经历了大规模重写。由于旧工作簿没有 source commit、binary、config、seed 和
raw record 绑定，不能断言哪一个历史二进制精确产生了每个旧柱；更不能要求
当前公式一致实现逐值复刻旧实现的输出。

## 5. 与 G1 正式低负载结果的合并判断

G1 Q61--Q80 同构低负载新结果中，九个 baseline 没有一个同时落在旧 PDF
throughput、QPR、cost 的冻结 `+/-15%` 诊断带内；Load Balance、Jiagu、Orion
等还出现远超 Monte Carlo 波动的排序/量级变化。现在的历史审计给出了与该
现象一致的来源解释：旧图没有可恢复的配对 run bank，且旧 NSESche 与当前
论文公式实现不属于同一可重放协议。

结论不是“放宽结果门槛”，而是把两个目标严格分开：

- **旧稿一致性目标**：保留旧工作簿/PDF 数值、实现差异和无法重放的原因，
  用作 provenance/alignment 附表；不通过调 seed 或改绘图贴柱。
- **重投有效性目标**：在同一冻结模拟器、tape、reference 和配对 seed 上重新
  生成 20-run 正式结果；该结果才是修订稿的统计证据。

## 6. 全场景审计闭合

以下公共场景核对已按结果盲态完成：

1. 已对旧 `54280e...`、稳定起点 `26fbe54` 和当前 corrected runtime 建立字段级
   差异表：运行帧数/是否 drain、到达率缩放、DAG 采样、节点容量、网络、HPA、
   cold-start、container cache、共同候选集、cost 累计和 throughput 分母。
2. 已把旧 Excel 的 12 个 variant/load 点（每点四项指标）与 PDF Fig.5 逐项核对，区分
   “已找回常量”“PDF 估读”和“完全缺失”。
3. 已检查历史 `export_to_excel.py`、绘图脚本和 `score.rs` 的指标口径，明确旧图
   中 `RPS` 实为 requests/frame = requests/ms 的命名问题。
4. 发现了多个耦合的公共 runtime/方法版本差异，而非一个唯一可验证的差异；
   因此 calibration pilot 的识别前提不成立。
5. 已冻结 `legacy protocol unidentifiable`，停止逐柱复刻，继续使用当前
   TSCv1 公共协议做独立重跑。

完整字段表、Fig.5 绑定、旧空 seed 重复、九个 baseline 版本差异以及 immutable
decision receipt 见 `B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md`。B0 闭合不自动
授权 D71 或 homogeneous-middle；下一步先做 decision-neutral mechanism
diagnosis，并且继续禁止重用 D61--D70 或 Q61--Q80 做候选效果估计。
