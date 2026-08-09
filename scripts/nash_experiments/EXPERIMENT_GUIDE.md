# Nash超参数实验指南

## 🚀 正确的实验流程

### 方法一：手动启动（推荐）

**步骤1：启动后端服务**
```bash
# 终端1：启动后端
cd serverless_sim
cargo run
```

**步骤2：运行实验脚本**
```bash
# 终端2：运行实验
cd scripts/nash_experiments
python run_nash_experiments.py
# 选择选项7或8进行完整实验
```

### 方法二：自动启动（已修复编码问题）

直接运行实验脚本，系统会自动：
1. 编译后端
2. 启动实验
3. 收集结果
4. 分析数据
5. 绘制图表

## 🔧 编码问题修复

已修复Windows系统的编码问题：
- 使用UTF-8编码写入配置文件
- 添加编码错误处理
- 支持中文路径和文件名

## 📋 实验参数配置

### 动态配置同步机制
实验脚本会**每次运行时动态读取**您当前的 `batch_run.yml` 配置：

✅ **完全同步**：每次运行都读取最新的配置
✅ **灵活适应**：支持您随时修改配置
✅ **错误处理**：配置文件读取失败时会提示错误
✅ **配置继承**：继承您的所有设置，只将调度器改为 `sche_nash`

**支持的配置模式**：
- `scale_sche_separated`：扩缩容与调度分离模式
- `scale_sche_joint`：扩缩容与调度联合模式  
- `no_scale`：无扩缩容模式

**动态读取的配置项**：
- **run_time**：实验次数
- **params**：所有参数配置（负载类型、DAG类型等）
- **mech_scale_sche**：扩缩容和调度配置
- **mech_other**：其他机制配置

### Price Feedback Rate实验
- **参数范围**：`[0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]`
- **负载类型**：动态读取您的 `batch_run.yml` 配置
- **实验次数**：动态读取您的 `batch_run.yml` 配置
- **总实验数**：根据您的配置动态计算

### Quality Weight实验
- **参数范围**：`[5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]`
- **负载类型**：动态读取您的 `batch_run.yml` 配置
- **实验次数**：动态读取您的 `batch_run.yml` 配置
- **总实验数**：根据您的配置动态计算

## 🎯 推荐使用方式

### 1. 单参数完整实验
```bash
# 运行Price Feedback Rate完整实验
python run_nash_experiments.py
# 选择选项7

# 运行Quality Weight完整实验
python run_nash_experiments.py
# 选择选项8
```

### 2. 分步实验
```bash
# 步骤1：运行实验
python run_nash_price_feedback_experiment.py

# 步骤2：分析结果
python analyze_nash_results.py

# 步骤3：绘制图表
python draw_nash_param_lines.py
```

## 📊 结果输出

实验完成后将生成：
- `nash_experiment_results/` - 原始实验数据
- `nash_analysis_results/` - CSV分析结果
- `nash_figures/` - PNG图表文件

## ⚠️ 注意事项

1. **确保后端稳定**：如果自动启动不稳定，建议使用手动启动方式
2. **检查环境变量**：确保Nash算法能正确读取环境变量
3. **监控系统资源**：长时间实验需要足够的系统资源
4. **备份重要数据**：实验前备份重要的配置文件

## 🛠️ 故障排除

### 编码错误
- 已修复UTF-8编码问题
- 如果仍有问题，检查系统区域设置

### 后端启动失败
- 检查Rust环境是否正确安装
- 确保在正确的目录下运行`cargo run`

### 实验超时
- 增加`timeout`参数值
- 检查系统资源使用情况 