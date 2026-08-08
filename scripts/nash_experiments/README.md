# Nash调度器超参数实验套件

## 概述

完全自动化的Nash调度器超参数实验系统，支持两个关键超参数的实验：

1. **Price Feedback Rate (价格反馈调整系数)**：范围 0.05-0.35，控制价格对纳什-社会偏差的调整敏感度
2. **Quality Weight (质量敏感度权重)**：范围 5.0-35.0，影响函数的节点选择偏好

## 文件结构

```
scripts/nash_experiments/
├── run_nash_experiments.py          # 主控制脚本（菜单界面）
├── run_nash_price_feedback_experiment.py  # 价格反馈参数实验
├── run_nash_quality_weight_experiment.py  # 质量权重参数实验
├── analyze_nash_results.py          # 结果分析脚本
├── draw_nash_param_lines.py         # 折线图绘制脚本
├── NASH_EXPERIMENT_README.md        # 详细技术文档
└── README.md                        # 本文件
```

## 快速开始

### 1. 运行完整实验流程

```bash
cd scripts/nash_experiments
python run_nash_experiments.py
# 选择选项6：完整实验流程
```

### 2. 分步运行

```bash
# 运行价格反馈参数实验
python run_nash_price_feedback_experiment.py

# 运行质量权重参数实验  
python run_nash_quality_weight_experiment.py

# 分析结果
python analyze_nash_results.py

# 绘制图表
python draw_nash_param_lines.py
```

## 实验配置

- **参数值范围**：每个参数7个值，3种负载类型
- **重复次数**：每个配置运行3次取平均值
- **指标**：平均成本、平均延迟、吞吐量、性价比
- **图表格式**：IEEE双栏标准，PNG格式，300 DPI

## 结果输出

实验完成后将生成以下目录：

```
scripts/nash_experiments/
├── nash_experiment_results/    # 原始实验数据
├── nash_analysis_results/      # CSV分析结果
└── nash_figures/              # PNG图表文件
```

## 无影响保证

- ✅ 不运行实验时：Nash算法与原来完全一致
- ✅ 运行实验时：通过环境变量动态调整参数
- ✅ 实验前后：无需修改任何代码

## 技术细节

详细的技术文档和实验原理请参考：`NASH_EXPERIMENT_README.md` 