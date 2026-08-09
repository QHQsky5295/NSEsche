# Nash 调度器超参数实验系统

## 📋 概述

这是一个完全自动化的Nash调度器超参数实验系统，支持两个关键超参数的实验：

1. **Price Feedback Rate** (价格反馈调整系数)
2. **Quality Weight** (质量敏感度权重)

## 🎯 系统特点

- **完全非侵入式**：只需添加6行代码支持环境变量
- **自动化实验**：一键运行N轮实验
- **多维度分析**：低中高负载 × 4个关键指标
- **学术标准**：符合IEEE双栏格式的图表输出
- **现有代码不受影响**：不运行实验脚本时系统正常工作

## 🚀 快速开始

### 1. 运行完整实验流程

```bash
cd scripts
python run_nash_experiments.py
```

选择选项6，运行完整实验流程（实验+分析+绘图）

### 2. 分别运行实验

```bash
# Price Feedback Rate实验
python run_nash_price_feedback_experiment.py

# Quality Weight实验  
python run_nash_quality_weight_experiment.py
```

### 3. 分析和绘图

```bash
# 分析结果
python analyze_nash_results.py

# 绘制折线图
python draw_nash_param_lines.py
```

## 📊 实验参数

### Price Feedback Rate
- **参数值**: [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
- **环境变量**: `NASH_PRICE_FEEDBACK_RATE`
- **作用**: 控制价格对纳什-社会偏差的调整敏感度

### Quality Weight
- **参数值**: [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
- **环境变量**: `NASH_QUALITY_WEIGHT`
- **作用**: 影响函数的节点选择偏好

## 📈 输出结果

### 实验数据
```
scripts/nash_experiment_results/
├── price_feedback_rate/
│   ├── param_0.05/
│   │   ├── low/
│   │   ├── middle/
│   │   └── high/
│   └── ...
└── quality_weight/
    └── ...
```

### 分析结果
```
scripts/nash_analysis_results/
├── price_feedback_rate_low.csv
├── price_feedback_rate_middle.csv
├── price_feedback_rate_high.csv
├── quality_weight_low.csv
├── quality_weight_middle.csv
└── quality_weight_high.csv
```

### 图表输出
```
scripts/nash_figures/
├── price_feedback_rate_low.png       # 低负载多指标折线图
├── price_feedback_rate_middle.png    # 中负载多指标折线图
├── price_feedback_rate_high.png      # 高负载多指标折线图
├── quality_weight_low.png            # 低负载多指标折线图
├── quality_weight_middle.png         # 中负载多指标折线图
├── quality_weight_high.png           # 高负载多指标折线图
└── ...
```

## 🔧 关键指标

每个图表包含4条折线：

1. **平均成本** (`cost_per_req`)
2. **平均延迟** (`time_per_req`) 
3. **吞吐量** (`rps`)
4. **性价比** (`rps/(cost_per_req*time_per_req)`)

## 🏗️ 系统架构

### 代码修改（最小化）
```rust
// 在 OptimizationConfig::default() 中添加
let price_feedback_rate = std::env::var("NASH_PRICE_FEEDBACK_RATE")
    .ok()
    .and_then(|s| s.parse::<f32>().ok())
    .unwrap_or(0.2); // 默认值

// 在 quality_weight 计算中添加
let quality_weight = std::env::var("NASH_QUALITY_WEIGHT")
    .ok()
    .and_then(|s| s.parse::<f32>().ok())
    .unwrap_or(10.0 + 10.0 * complexity_factor); // 默认值
```

### 实验脚本结构
```
scripts/
├── run_nash_experiments.py              # 主控制脚本
├── run_nash_price_feedback_experiment.py # 价格反馈实验
├── run_nash_quality_weight_experiment.py # 质量权重实验
├── analyze_nash_results.py              # 结果分析
├── draw_nash_param_lines.py             # 折线图绘制
└── NASH_EXPERIMENT_README.md            # 说明文档
```

## 🎨 图表特点

- **IEEE双栏格式**：3.5×2.5英寸尺寸
- **学术标准**：Times New Roman字体，300DPI
- **清晰标注**：不同线型、颜色、标记
- **专业布局**：网格、图例、标题完整

## 📋 使用流程

1. **环境准备**：确保serverless_sim可以正常编译
2. **运行实验**：使用主控制脚本选择实验类型
3. **自动编译**：脚本自动编译Rust后端
4. **批量实验**：自动运行所有参数值和负载组合
5. **结果收集**：自动收集和分类实验结果
6. **数据分析**：提取关键指标并计算平均值
7. **图表生成**：生成符合学术标准的折线图

## 🔍 故障排查

### 常见问题

1. **编译失败**
   - 检查Rust环境是否正确安装
   - 确保在serverless_sim目录可以运行`cargo build`

2. **实验运行失败**
   - 检查batch_run.py是否正常工作
   - 确认环境变量设置正确

3. **结果分析失败**
   - 检查records_read.py是否可以导入
   - 确认JSON结果文件格式正确

4. **图表生成失败**
   - 检查matplotlib是否正确安装
   - 确认pandas库可用

### 检查命令

```bash
# 检查实验状态
python run_nash_experiments.py
# 选择选项7查看实验状态

# 手动检查环境变量
export NASH_PRICE_FEEDBACK_RATE=0.15
cd ../serverless_sim
cargo build --release
```

## 🎯 下一步

1. **运行实验**：使用主控制脚本运行完整实验流程
2. **分析结果**：查看生成的CSV文件和图表
3. **论文写作**：使用图表进行学术论文写作
4. **参数调优**：根据结果调整算法参数

## 💡 注意事项

- 实验时间较长，建议在性能较好的机器上运行
- 确保硬盘空间充足，实验会产生大量数据文件
- 每次实验前可以先运行少量测试验证系统正常
- 实验结果会覆盖已有数据，注意备份重要结果

## 🔗 相关文档

- [Serverless Sim 使用文档](../README.md)
- [Nash调度器算法说明](../NASH_OPTIMIZATION_SUMMARY.md)
- [参数映射说明](../NASH_PARAMETER_MAPPING.md) 