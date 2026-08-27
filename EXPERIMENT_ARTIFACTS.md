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
  - formal execution remains deliberately blocked until a development-only
    NSESche profile closes every E3/E4 throughput-and-QPR gate.

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

## E2 status correction (2026-08-19)

The earlier “live E2” note is stale. E2 initial is now technically complete
through a result-blind composite: `tmp/formal_e2_reviewer_v3_20260817/` contains
the original 423 canonical runs plus preserved timeout evidence, tier-1 recovery
(6 canonical), tier-2 recovery (1 canonical), and `formal-runs-composite/` with
600/600 canonical runs and 60/60 pairing groups passed. The strict export is
`analysis/e2-runs-with-e1.csv` (900 rows: 600 physical E2 plus 300 sealed E1
20-node projections; coverage 1200/1200 `ok` across physical/source/projection
scopes), and Figure 10 is under
`analysis/figures/fig10_weak_scaling.pdf`. Recovery artifacts are technical,
result-blind retries; no new seeds were introduced and all timeout/quarantine
evidence remains preserved.

The precision gate requests E11--E20 for every E2 weak-scaling scenario. The sealed
extension shard has passed its 90-tape, frozen-model, and 60-reference gates; its
600-run ready manifest is
`tmp/formal_e2_extension_reviewer_v3_20260819/manifest.ready.json` (manifest hash
`fbf100bd759e7fff73685505a539c9d075f2ebb501713fc8c67b49118afaeb48`). The formal
extension batch started on 2026-08-19 and writes only QC-admitted results under
`tmp/formal_e2_extension_reviewer_v3_20260819/formal-runs/canonical/`. Do not treat
the initial E2 block as the final precision-complete estimate until this batch and
its pairing audit finish.
The E2 composite runtime identity is
anchored to Git `42bc59e...`; the sealed E1 all-stage reuse source uses Git
`f6c1d28...` while sharing the same binary, Python, Cargo-lock, HPA, and model
artifacts. This provenance difference is retained explicitly and must be disclosed
with any cross-workload comparison.

## V86 formal confirmation closure (2026-08-27)

The terminal OCS-dual Pareto candidate confirmation is closed and must not be
reopened or tuned on confirmation seeds E690--E709. Its formal workspace is
`tmp/nse_terminal_ocs_dual_pareto_confirmation_20260827_v86/`; all 20 runs passed
QC and pairing on attempt 1 with zero quarantine. The frozen result is
`scripts/reviewer_experiments/protocol/nse_terminal_ocs_dual_pareto_confirmation_result_v86.json`.
The outcome is `formal_confirmation_fail_close_v86`: mean throughput exceeded the
frozen floor, but its BCa interval did not establish the required margin, while
QPR was about 30.0% below the comparator and both QPR difference intervals were
strictly negative. These data are retained as a closed confirmation failure and
are not used as the resource-scaling configuration below.

## Frozen E1 publication-facing NSESche catalogs

The earlier generic E1 formal workspaces remain provenance sources, but the
publication-facing NSESche rows are the separately audited final catalogs below.
All listed groups are closed and `rerun_forbidden=true`; downstream experiments
with matching configurations must reuse them.

- homogeneous n20, low/middle/high (15 runs total):
  `scripts/reviewer_experiments/protocol/NSESche_E1_homogeneous_n20_final_v1.json`
  (catalog hash `97332fc3...2b36e0`). Low and middle were closed by V59;
  high is the unchanged V58 closure.
- heterogeneous n20, low/middle/high (15 runs total):
  `scripts/reviewer_experiments/protocol/NSESche_E1_heterogeneous_n20_final_v1.json`
  (catalog hash `07809e68...646d1`). The bundle status is `closed_complete`.

These catalogs are the evidence that both E1 topologies have NSESche groups
whose throughput and both QPR conventions exceed the corresponding frozen
baseline maxima. They supersede any statement that E1 is merely run-complete
but scientifically open.

## NSESche-only proportional-load resource scaling (2026-08-27)

The paper's same-load multi-node resource trend is NSESche-only; it does not make
a baseline-superiority claim. The frozen bundle reuses the exact E01--E20 formal
NSESche cohorts at 20, 100, and 500 homogeneous nodes (60 physical runs, 20 paired
environment seeds per node count, no new online runs, no baseline rows):

- frozen plan:
  `scripts/reviewer_experiments/protocol/nse_homogeneous_low_resource_scaling_reuse_plan_v1.json`
- result-free integrity audit:
  `scripts/reviewer_experiments/protocol/nse_homogeneous_low_resource_scaling_reuse_audit_v1.json`
- frozen result and exact per-run table:
  `scripts/reviewer_experiments/protocol/nse_homogeneous_low_resource_scaling_result_v1.json`
  and
  `scripts/reviewer_experiments/protocol/nse_homogeneous_low_resource_scaling_run_table_v1.csv`
- handoff:
  `scripts/reviewer_experiments/protocol/nse_homogeneous_low_resource_scaling_handoff_v1.md`
- reproducible figure source:
  `scripts/reviewer_experiments/figures/plot_nse_resource_scaling.py`
- generated figure bundle:
  `tmp/nse_homogeneous_low_resource_scaling_freeze_v1/` (`PDF`, `PNG`, `SVG`,
  `figure_manifest.json`, and `alt_text.md`).

The frozen scientific gate passed all four required components: throughput and QPR
increase from 20 to 100 nodes and from 100 to 500 nodes, with every paired BCa 95%
difference interval strictly above zero. Weak-scaling throughput efficiency is
reported descriptively (81.8% then 71.7%) without a post-hoc pass threshold. The
source E2 extension workspace is incomplete overall, but the selected low-load
NSESche n100/n500 E11--E20 cells are complete, QC-admitted, attempt-1 results; no
other incomplete E2 cell enters this bundle.

## E3/E4 NSESche operational development V87 (2026-08-27)

V87 is technically complete and scientifically failed closed. Its workspace is
`tmp/nse_e3e4_operational_dev_20260827_v87/`; 60 frozen advanced-baseline runs,
36 NSESche runs, and 36 candidate-specific reference builds all passed on attempt
1 with zero quarantine. The one-time result-blind reveal is retained at
`selection-result-v87.json`, and the tracked result receipt is
`scripts/reviewer_experiments/protocol/nse_e3e4_operational_dev_result_v87.json`.

No candidate simultaneously exceeded the maximum five-baseline mean for
throughput and both QPR conventions in all four scenarios. V87 B won throughput
for spike and sustained burst, while V87 B/C won QPR for E4; neither closed the
joint gates. The frozen baseline rows must be reused without rerun. Formal E3/E4
execution is still unauthorized; V88 is limited to an NSESche-only dependency
frontier and expert-history repair on untouched seeds E713--E715.
