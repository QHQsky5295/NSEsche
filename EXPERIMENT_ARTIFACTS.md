# Reviewer experiment artifacts

正式实验产物统一保存在仓库根目录的 `tmp/` 下；`serverless_sim/records/`
不是 reviewer-v3 的归档位置，因此不会在那边看到这些结果。每个 workspace
都包含自己的 manifest、tape/reference 依赖、attempt/canonical 目录、QC 报告、
ledger 和最终压缩 JSONL。不要移动或重命名 canonical 目录；路径和哈希被 manifest
绑定。

## 已完成并可审计

- E1 homogeneous, 600 runs (E01--E20):
  `tmp/formal_e1_atomic_hpa_reviewer_v3_20260813/`
  - ready manifest: `manifest.e1-homogeneous.ready.json`
  - pairing audit: `pairing-audit-runtime-v2.json`
  - canonical results: `formal-runs/canonical/`
  - strict exporter output: `analysis/strict-runtime-v3/runs.csv`
  - physical E1-only analysis table (排除封存的 E2 20-node reuse projection):
    `analysis/strict-runtime-v2/runs-physical-e1.csv`
  - E1 physical summary: `analysis/strict-runtime-v2/stats-e1-physical/summary.csv`
  - figures: `analysis/strict-runtime-v2/figures-e1-physical/`

- E1 heterogeneous, 600 runs (E01--E20):
  `tmp/formal_e1_heterogeneous_reviewer_v3_20260813/`
  - ready manifest: `manifest.e1-heterogeneous.ready.json`
  - canonical results: `formal-runs/canonical/`

- E5/E6/E7 initial ready workspace:
  `tmp/formal_e5_e6_e7_reviewer_v3_20260817/`

## 正在运行或等待运行

- E2 weak scaling initial (600 physical runs):
  `tmp/formal_e2_reviewer_v3_20260817/`
  - ready manifest: `manifest.ready.json`
  - live canonical results: `formal-runs/canonical/`
  - live ledger: `formal-runs/ledger.jsonl`
  - 当前批次由单一冻结 runner 串行执行；不要删除 `partial/` 或重启进程。

- E3/E4 initial shard (400 runs, 40 references; 尚未开始正式 run):
  `tmp/formal_e3_e4_reviewer_v3_20260817/`
  - unbound shard: `manifest.unbound.json`
  - continuation gate/script: `continue_e3_e4.ps1`, `e3_e4_gate.py`

- E5/E6 precision extension preparation:
  `tmp/formal_e5_e6_extension_reviewer_v3_20260817/`

## 图和源码

可复现的绘图源码在
`scripts/reviewer_experiments/figures/`；统计源码在
`scripts/reviewer_experiments/analysis/`。图的 PDF/PNG 只从通过 pairing/QC 的
CSV 生成。E1 physical Fig.6/7/8 的相对路径见上方 workspace；这些是当前可直接
打开的论文图，不是旧 PDF 的复制品。

## 口径与完整性

- `formal_run` 与 `materialized_reuse` 是两种不同的分析记录类型；不能把 reuse
  projection 当成新的独立 seed。
- 所有通过 QC 的结果（包括完成数为零、负福利或高队列）都保留；不会按性能方向
  删除或挑选。
- high workload 已按冻结 workload profile 约 7k requests/s 运行，和旧稿约 27.9k
  的 submission-era high 不是同一个实验总体；比较时必须同时报告该差异。
