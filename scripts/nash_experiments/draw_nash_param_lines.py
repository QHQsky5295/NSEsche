#!/usr/bin/env python3
"""
Nash 调度器超参数实验折线图绘制脚本
为每个参数生成3个负载类型的图表，每个图表包含4个指标的折线
符合学术论文标准和IEEE双栏格式要求
"""

import os
import sys
import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from pathlib import Path
import matplotlib.font_manager as fm

# 设置工作目录
SCRIPT_DIR = Path(__file__).parent
ANALYSIS_DIR = SCRIPT_DIR / "nash_analysis_results"
FIGURES_DIR = SCRIPT_DIR / "nash_figures"

# 图表配置
LOAD_TYPES = ["low", "middle", "high"]
LOAD_NAMES = {"low": "低负载", "middle": "中负载", "high": "高负载"}

# 指标配置
METRICS_CONFIG = {
    "平均成本": {
        "column": "平均成本",
        "color": "#2E86AB",
        "linestyle": "-",
        "marker": "o",
        "ylabel": "平均成本",
        "grid": True
    },
    "平均延迟(ms)": {
        "column": "平均延迟(ms)",
        "color": "#A23B72",
        "linestyle": "--",
        "marker": "s",
        "ylabel": "平均延迟 (ms)",
        "grid": True
    },
    "吞吐量(req/s)": {
        "column": "吞吐量(req/s)",
        "color": "#F18F01",
        "linestyle": "-.",
        "marker": "^",
        "ylabel": "吞吐量 (req/s)",
        "grid": True
    },
    "性价比": {
        "column": "性价比",
        "color": "#C73E1D",
        "linestyle": ":",
        "marker": "D",
        "ylabel": "性价比",
        "grid": True
    }
}

def setup_matplotlib():
    """设置matplotlib参数，符合学术论文标准"""
    # 设置字体
    plt.rcParams['font.size'] = 10
    plt.rcParams['font.family'] = 'serif'
    plt.rcParams['font.serif'] = ['Times New Roman']
    
    # 设置图表尺寸（IEEE双栏格式）
    plt.rcParams['figure.figsize'] = (3.5, 2.5)  # 单栏宽度
    plt.rcParams['figure.dpi'] = 300
    
    # 设置线条和标记
    plt.rcParams['lines.linewidth'] = 1.5
    plt.rcParams['lines.markersize'] = 4
    
    # 设置网格
    plt.rcParams['axes.grid'] = True
    plt.rcParams['grid.alpha'] = 0.3
    plt.rcParams['grid.linewidth'] = 0.5
    
    # 设置图例
    plt.rcParams['legend.fontsize'] = 8
    plt.rcParams['legend.frameon'] = True
    plt.rcParams['legend.fancybox'] = True
    plt.rcParams['legend.shadow'] = True
    
    # 设置坐标轴
    plt.rcParams['axes.linewidth'] = 1.0
    plt.rcParams['xtick.major.size'] = 3
    plt.rcParams['ytick.major.size'] = 3
    plt.rcParams['xtick.direction'] = 'in'
    plt.rcParams['ytick.direction'] = 'in'

def create_multi_metric_plot(param_name, param_display_name, load_type, data):
    """创建包含4个指标的多折线图"""
    if data.empty:
        print(f"⚠️ 跳过空数据：{param_name}/{load_type}")
        return
    
    fig, ax = plt.subplots(figsize=(3.5, 2.5))
    
    # 绘制每个指标的折线
    for metric_name, config in METRICS_CONFIG.items():
        if config["column"] in data.columns:
            ax.plot(
                data["参数值"],
                data[config["column"]],
                color=config["color"],
                linestyle=config["linestyle"],
                marker=config["marker"],
                label=metric_name,
                linewidth=1.5,
                markersize=4,
                markerfacecolor='white',
                markeredgewidth=1
            )
    
    # 设置标题和标签
    ax.set_title(f"{param_display_name} - {LOAD_NAMES[load_type]}", fontsize=11, fontweight='bold')
    ax.set_xlabel(param_display_name, fontsize=10)
    ax.set_ylabel("指标值", fontsize=10)
    
    # 设置网格
    ax.grid(True, alpha=0.3, linewidth=0.5)
    
    # 设置图例
    ax.legend(
        loc='upper right',
        bbox_to_anchor=(1.0, 1.0),
        fontsize=8,
        frameon=True,
        fancybox=True,
        shadow=True,
        ncol=2 if len(METRICS_CONFIG) > 2 else 1
    )
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    figure_file = FIGURES_DIR / f"{param_name}_{load_type}.png"
    plt.savefig(
        figure_file,
        dpi=300,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none'
    )
    plt.close()
    
    print(f"📈 生成图表：{figure_file}")

def create_separated_metric_plots(param_name, param_display_name, load_type, data):
    """创建分离的单指标图表（备选方案）"""
    if data.empty:
        print(f"⚠️ 跳过空数据：{param_name}/{load_type}")
        return
    
    # 创建2x2子图布局
    fig, axes = plt.subplots(2, 2, figsize=(7, 5))
    axes = axes.flatten()
    
    for i, (metric_name, config) in enumerate(METRICS_CONFIG.items()):
        if config["column"] in data.columns:
            ax = axes[i]
            
            ax.plot(
                data["参数值"],
                data[config["column"]],
                color=config["color"],
                linestyle=config["linestyle"],
                marker=config["marker"],
                linewidth=2,
                markersize=5,
                markerfacecolor='white',
                markeredgewidth=1.5
            )
            
            ax.set_title(f"{metric_name}", fontsize=10, fontweight='bold')
            ax.set_xlabel(param_display_name, fontsize=9)
            ax.set_ylabel(config["ylabel"], fontsize=9)
            ax.grid(True, alpha=0.3, linewidth=0.5)
            
            # 设置坐标轴刻度
            ax.tick_params(axis='both', which='major', labelsize=8)
    
    # 总标题
    fig.suptitle(f"{param_display_name} - {LOAD_NAMES[load_type]}", fontsize=12, fontweight='bold')
    
    # 调整布局
    plt.tight_layout()
    
    # 保存图表
    figure_file = FIGURES_DIR / f"{param_name}_{load_type}_separated.png"
    plt.savefig(
        figure_file,
        dpi=300,
        bbox_inches='tight',
        facecolor='white',
        edgecolor='none'
    )
    plt.close()
    
    print(f"📈 生成分离图表：{figure_file}")

def draw_parameter_charts(param_name, param_display_name):
    """绘制特定参数的所有图表"""
    print(f"📊 绘制{param_display_name}图表...")
    
    # 为每个负载类型创建图表
    for load_type in LOAD_TYPES:
        csv_file = ANALYSIS_DIR / f"{param_name}_{load_type}.csv"
        
        if not csv_file.exists():
            print(f"⚠️ 找不到数据文件：{csv_file}")
            continue
        
        # 读取数据
        try:
            data = pd.read_csv(csv_file)
            
            # 按参数值排序
            data = data.sort_values("参数值")
            
            # 创建多指标折线图
            create_multi_metric_plot(param_name, param_display_name, load_type, data)
            
            # 创建分离的单指标图表（备选）
            create_separated_metric_plots(param_name, param_display_name, load_type, data)
            
        except Exception as e:
            print(f"❌ 绘制图表失败：{csv_file}, {e}")

def create_comparison_charts():
    """创建参数比较图表"""
    print("📊 创建参数比较图表...")
    
    # 这里可以添加参数间的比较图表
    # 例如：在同一图表中展示两个参数的最佳值比较
    pass

def main():
    """主函数"""
    print("=" * 60)
    print("📈 Nash调度器超参数实验折线图绘制")
    print("=" * 60)
    
    # 设置matplotlib
    setup_matplotlib()
    
    # 创建图表目录
    FIGURES_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查分析结果是否存在
    if not ANALYSIS_DIR.exists():
        print("❌ 找不到分析结果目录！")
        print("请先运行：python analyze_nash_results.py")
        sys.exit(1)
    
    # 绘制Price Feedback Rate图表
    if any(ANALYSIS_DIR.glob("price_feedback_rate_*.csv")):
        draw_parameter_charts("price_feedback_rate", "Price Feedback Rate")
    else:
        print("⚠️ 找不到Price Feedback Rate分析结果")
    
    # 绘制Quality Weight图表
    if any(ANALYSIS_DIR.glob("quality_weight_*.csv")):
        draw_parameter_charts("quality_weight", "Quality Weight")
    else:
        print("⚠️ 找不到Quality Weight分析结果")
    
    # 创建比较图表
    create_comparison_charts()
    
    print(f"\n✅ 图表生成完成！")
    print(f"📁 图表保存在：{FIGURES_DIR}")
    print("\n🎯 生成的图表：")
    for fig_file in FIGURES_DIR.glob("*.png"):
        print(f"   📈 {fig_file.name}")

if __name__ == "__main__":
    main() 