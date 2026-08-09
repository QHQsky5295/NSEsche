#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验数据可视化脚本
Experiment Data Visualization Script

功能：
1. 自动读取cache文件夹中的JSON实验数据
2. 生成多指标对比的柱状图
3. 支持多负载级别和多算法对比
4. 为未来实验预留扩展空间
"""

import os
import json
import re
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from collections import defaultdict
import seaborn as sns
from pathlib import Path

# 设置中文字体支持
plt.rcParams['font.sans-serif'] = ['DejaVu Sans', 'SimHei', 'Arial Unicode MS']
plt.rcParams['axes.unicode_minus'] = False

# 学术风格配置
try:
    plt.style.use('seaborn-v0_8-whitegrid')
except:
    try:
        plt.style.use('seaborn-whitegrid')
    except:
        plt.style.use('default')
        
try:
    sns.set_palette("husl")
except:
    pass

class ExperimentVisualizer:
    def __init__(self, cache_dir="cache"):
        """
        初始化实验数据可视化器
        
        Args:
            cache_dir (str): cache文件夹路径
        """
        self.cache_dir = cache_dir
        self.data = defaultdict(lambda: defaultdict(dict))
        self.metrics_info = {
            'time_per_req': '平均请求响应时间 (毫秒)',
            'score': '系统评分 (越高越好)',
            'rps': '每秒请求处理数 (RPS)',
            'cost_per_req': '每请求成本',
            'coldstart_time_per_req': '冷启动时间 (毫秒)',
            'waitsche_time_per_req': '调度等待时间 (毫秒)',
            'exe_time_per_req': '执行时间 (毫秒)',
            'datarecv_time_per_req': '数据接收时间 (毫秒)',
            'fn_container_cnt': '平均容器数量',
            'undone_req_cnt': '未完成请求数',
            'performance_ratio': '性价比指标 (RPS/(总时间×成本), 越高越好)',
            'latency_efficiency': '延迟效率 (总时间/RPS, 越低越好)',
            'cost_efficiency': '成本效率 (成本/RPS, 越低越好)'
        }
        
        # 时间相关指标分组（用于分段显示，不包括总时间）
        self.time_metrics = {
            'coldstart_time_per_req': {'name': 'Cold Start', 'color': '#FF6B6B', 'desc': '冷启动时间'},
            'waitsche_time_per_req': {'name': 'Wait Schedule', 'color': '#4ECDC4', 'desc': '调度等待时间'},
            'exe_time_per_req': {'name': 'Execution', 'color': '#45B7D1', 'desc': '执行时间'},
            'datarecv_time_per_req': {'name': 'Data Recv', 'color': '#96CEB4', 'desc': '数据接收时间'}
        }
        
        self.load_level_mapping = {
            'rflow': 'Low Load',
            'rfmiddle': 'Medium Load', 
            'rfhigh': 'High Load'
        }
        
        self.algorithm_mapping = {
            'sche_nash': 'Nash',
            'hash': 'Hash',
            'random': 'Random',
            'greedy': 'Greedy'
        }
        
        # 学术风格颜色配置
        self.colors = {
            'Nash': '#2E86AB',      # 深蓝色
            'Hash': '#A23B72',      # 深紫红
            'Random': '#F18F01',    # 橙色
            'Greedy': '#C73E1D'     # 深红色
        }
        
    def parse_filename(self, filename):
        """
        解析文件名提取实验参数
        
        Args:
            filename (str): JSON文件名
            
        Returns:
            tuple: (load_level, algorithm) 或 (None, None)
        """
        # 提取负载级别
        load_pattern = r'\.rf(low|middle|high)\.'
        load_match = re.search(load_pattern, filename)
        if not load_match:
            return None, None
            
        load_level = 'rf' + load_match.group(1)
        
        # 提取算法名称
        algo_pattern = r'\.scd\(([^)]+)\)\.'
        algo_match = re.search(algo_pattern, filename)
        if not algo_match:
            return None, None
            
        algorithm = algo_match.group(1).rstrip('.')
        
        return load_level, algorithm
    
    def _get_dynamic_color(self, algo):
        """为未知算法动态生成颜色"""
        colors_pool = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFEAA7', 
                      '#DDA0DD', '#98D8C8', '#F7DC6F', '#BB8FCE', '#85C1E9']
        # 基于算法名称生成一致的颜色
        hash_val = hash(algo) % len(colors_pool)
        return colors_pool[hash_val]
    
    def load_data(self):
        """加载cache文件夹中的所有JSON数据"""
        cache_path = Path(self.cache_dir)
        if not cache_path.exists():
            print(f"❌ Cache文件夹不存在: {cache_path}")
            return
            
        json_files = list(cache_path.glob("*.json"))
        if not json_files:
            print(f"❌ Cache文件夹中没有找到JSON文件: {cache_path}")
            return
            
        print(f"📁 找到 {len(json_files)} 个实验数据文件")
        
        for json_file in json_files:
            load_level, algorithm = self.parse_filename(json_file.name)
            if load_level and algorithm:
                try:
                    with open(json_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        # 计算性价比指标
                        data = self._calculate_performance_metrics(data)
                        self.data[load_level][algorithm] = data
                        print(f"✅ 加载: {load_level} - {algorithm}")
                except Exception as e:
                    print(f"❌ 加载失败 {json_file.name}: {e}")
            else:
                print(f"⚠️  无法解析文件名: {json_file.name}")
    
    def _calculate_performance_metrics(self, data):
        """计算额外的性能指标"""
        # 获取基础数据
        rps = data.get('rps', 0)
        time_per_req = data.get('time_per_req', 0)
        cost_per_req = data.get('cost_per_req', 0)
        
        # 计算各项时间之和
        time_components = [
            data.get('coldstart_time_per_req', 0),
            data.get('waitsche_time_per_req', 0),
            data.get('exe_time_per_req', 0),
            data.get('datarecv_time_per_req', 0)
        ]
        total_time = sum(time_components)
        
        # 如果没有时间分解数据，使用总时间
        if total_time == 0 and time_per_req > 0:
            total_time = time_per_req
        
        # 计算新的延迟指标：（各项时间之和）/吞吐量
        if total_time > 0 and rps > 0:
            data['latency_efficiency'] = total_time / rps  # 延迟效率指标
        else:
            data['latency_efficiency'] = 0
            
        # 计算新的成本指标：成本/吞吐量
        if cost_per_req > 0 and rps > 0:
            data['cost_efficiency'] = cost_per_req / rps  # 成本效率指标
        else:
            data['cost_efficiency'] = 0
        
        # 计算性价比指标：吞吐量/（延迟 × 成本）
        if total_time > 0 and cost_per_req > 0 and rps > 0:
            data['performance_ratio'] = rps / (total_time * cost_per_req)
        else:
            data['performance_ratio'] = 0
            
        return data
    
    def print_metrics_info(self):
        """打印指标的中文含义"""
        print("\n" + "="*60)
        print("📊 实验指标说明 (Metrics Description)")
        print("="*60)
        for metric, description in self.metrics_info.items():
            print(f"{metric:25} -> {description}")
        print("="*60)
    
    def print_current_metrics(self, all_metrics, time_metrics_available):
        """打印当前实验中发现的指标及其中文含义"""
        print("\n" + "="*80)
        print("📋 当前实验数据中的指标及中文含义")
        print("="*80)
        
        if time_metrics_available:
            print("🕒 时间相关指标 (将合并显示):")
            for metric in time_metrics_available:
                desc = self.time_metrics[metric]['desc']
                print(f"  {metric:25} -> {desc}")
            print()
        
        print("📊 其他性能指标:")
        for metric in sorted(all_metrics):
            if metric in self.metrics_info and metric not in self.time_metrics:
                print(f"  {metric:25} -> {self.metrics_info[metric]}")
            elif metric not in self.metrics_info and metric not in self.time_metrics:
                print(f"  {metric:25} -> 未知指标 (将自动处理)")
        print("="*80)
        print()
    
    def create_visualization(self, save_path="experiment_results.png", figsize=(24, 18)):
        """
        创建综合可视化图表
        
        Args:
            save_path (str): 保存路径
            figsize (tuple): 图片尺寸
        """
        if not self.data:
            print("❌ 没有数据可以可视化")
            return
            
        # 获取所有指标
        all_metrics = set()
        for load_data in self.data.values():
            for algo_data in load_data.values():
                all_metrics.update(algo_data.keys())
        
        # 自适应识别指标
        metrics_to_plot = []
        time_metrics_available = []
        
        # 检查时间相关指标
        for time_metric in self.time_metrics.keys():
            if time_metric in all_metrics:
                time_metrics_available.append(time_metric)
        
        # 添加时间分段图（如果有时间指标）
        if time_metrics_available:
            metrics_to_plot.append('time_breakdown')
            print(f"🕒 发现时间相关指标: {[self.time_metrics[m]['desc'] for m in time_metrics_available]}")
        
        # 添加其他指标
        for metric in all_metrics:
            if metric in self.metrics_info and metric not in self.time_metrics:
                metrics_to_plot.append(metric)
        
        if not metrics_to_plot:
            print("❌ 没有找到可绘制的指标")
            return
            
        # 打印所有指标的中文含义
        self.print_current_metrics(all_metrics, time_metrics_available)
            
        # 计算子图布局 - 自适应布局
        n_metrics = len(metrics_to_plot)
        if n_metrics <= 4:
            n_cols, n_rows = 2, 2
        elif n_metrics <= 6:
            n_cols, n_rows = 3, 2
        elif n_metrics <= 9:
            n_cols, n_rows = 3, 3
        else:
            n_cols = 4
            n_rows = (n_metrics + n_cols - 1) // n_cols
        
        # 创建图形
        fig, axes = plt.subplots(n_rows, n_cols, figsize=figsize)
        fig.suptitle('Serverless Scheduling Algorithm Performance Comparison', 
                    fontsize=24, fontweight='bold', y=0.96)
        
        # 确保axes是二维数组
        if n_rows == 1 and n_cols == 1:
            axes = np.array([[axes]])
        elif n_rows == 1:
            axes = axes.reshape(1, -1)
        elif n_cols == 1:
            axes = axes.reshape(-1, 1)
            
        # 获取负载级别和算法列表
        load_levels = sorted(self.data.keys())
        algorithms = set()
        for load_data in self.data.values():
            algorithms.update(load_data.keys())
        algorithms = sorted(list(algorithms))
        
        print(f"\n📈 生成 {n_metrics} 个指标的对比图表")
        print(f"📊 负载级别: {[self.load_level_mapping.get(l, l) for l in load_levels]}")
        print(f"🔧 算法: {[self.algorithm_mapping.get(a, a.title()) for a in algorithms]}")
        
        # 为每个指标创建子图
        for idx, metric in enumerate(metrics_to_plot):
            row = idx // n_cols
            col = idx % n_cols
            ax = axes[row, col]
            
            if metric == 'time_breakdown':
                self._plot_time_breakdown(ax, load_levels, algorithms, time_metrics_available)
            else:
                self._plot_metric(ax, metric, load_levels, algorithms)
            
        # 隐藏多余的子图
        for idx in range(n_metrics, n_rows * n_cols):
            row = idx // n_cols
            col = idx % n_cols
            axes[row, col].set_visible(False)
            
        # 创建全局图例 - 放在更显眼的位置
        legend_elements = []
        for algo in algorithms:
            algo_display = self.algorithm_mapping.get(algo, algo.title())
            color = self.colors.get(algo_display, self._get_dynamic_color(algo))
            legend_elements.append(mpatches.Patch(color=color, label=algo_display))
        
        fig.legend(handles=legend_elements, loc='upper center', 
                  bbox_to_anchor=(0.5, 0.92), ncol=len(legend_elements),
                  fontsize=16, frameon=True, fancybox=True, shadow=True)
        
        # 调整布局
        plt.tight_layout()
        plt.subplots_adjust(top=0.88, bottom=0.05, hspace=0.35, wspace=0.3)
        
        # 保存图片
        plt.savefig(save_path, dpi=300, bbox_inches='tight', 
                   facecolor='white', edgecolor='none')
        print(f"💾 图表已保存至: {save_path}")
        
        # 显示图片
        plt.show()
    
    def _plot_metric(self, ax, metric, load_levels, algorithms):
        """
        为单个指标创建柱状图
        
        Args:
            ax: matplotlib轴对象
            metric (str): 指标名称
            load_levels (list): 负载级别列表
            algorithms (list): 算法列表
        """
        # 准备数据
        data_matrix = []
        labels = []
        
        for load in load_levels:
            load_label = self.load_level_mapping.get(load, load)
            labels.append(load_label)
            
            row_data = []
            for algo in algorithms:
                if algo in self.data[load] and metric in self.data[load][algo]:
                    value = self.data[load][algo][metric]
                    # 对于score指标，转换为正值便于比较
                    if metric == 'score' and value < 0:
                        value = -value
                    row_data.append(value)
                else:
                    row_data.append(0)  # 缺失数据用0填充
            data_matrix.append(row_data)
        
        data_matrix = np.array(data_matrix)
        
        # 设置柱状图参数
        x = np.arange(len(labels))
        width = 0.18  # 固定宽度，更美观
        
        # 绘制柱状图
        for i, algo in enumerate(algorithms):
            algo_display = self.algorithm_mapping.get(algo, algo.title())
            color = self.colors.get(algo_display, self._get_dynamic_color(algo))
            
            # 计算每个柱子的位置
            pos = x + (i - len(algorithms)/2 + 0.5) * width
            
            bars = ax.bar(pos, data_matrix[:, i], width, 
                        label=algo_display, color=color, alpha=0.85,
                        edgecolor='white', linewidth=1.2)
            
            # 添加数值标签 - 智能格式化
            for j, bar in enumerate(bars):
                height = bar.get_height()
                if height > 0:
                    # 智能数值格式化
                    if height >= 10000:
                        label_text = f'{height/1000:.0f}k'
                    elif height >= 1000:
                        label_text = f'{height:.0f}'
                    elif height >= 100:
                        label_text = f'{height:.0f}'
                    elif height >= 10:
                        label_text = f'{height:.1f}'
                    else:
                        label_text = f'{height:.2f}'
                    
                    ax.text(bar.get_x() + bar.get_width()/2., height + height*0.01,
                           label_text, ha='center', va='bottom', 
                           fontsize=10, fontweight='bold', color='black')
        
        # 设置图表样式 - 增大字体
        ax.set_xlabel('Load Level', fontsize=14, fontweight='bold')
        ax.set_ylabel(metric.replace('_', ' ').title(), fontsize=14, fontweight='bold')
        ax.set_title(f'{metric.replace("_", " ").title()}', 
                    fontsize=16, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=12)
        
        # 设置y轴刻度字体
        ax.tick_params(axis='y', labelsize=11)
        
        # 美化网格
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.set_axisbelow(True)
        
        # 设置y轴范围，确保所有数据可见
        if data_matrix.max() > 0:
            ax.set_ylim(0, data_matrix.max() * 1.2)
            
        # 优化布局
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
    
    def _plot_time_breakdown(self, ax, load_levels, algorithms, time_metrics_available):
        """
        绘制时间分段柱状图（不包括总时间）
        
        Args:
            ax: matplotlib轴对象
            load_levels (list): 负载级别列表
            algorithms (list): 算法列表
            time_metrics_available (list): 可用的时间指标列表
        """
        # 准备数据
        labels = [self.load_level_mapping.get(load, load) for load in load_levels]
        x = np.arange(len(labels))
        width = 0.18
        
        # 为每个算法绘制堆叠柱状图
        for i, algo in enumerate(algorithms):
            algo_display = self.algorithm_mapping.get(algo, algo.title())
            pos = x + (i - len(algorithms)/2 + 0.5) * width
            
            # 收集该算法在各负载下的时间数据
            bottom_values = np.zeros(len(load_levels))
            
            for time_metric in time_metrics_available:
                values = []
                for load in load_levels:
                    if algo in self.data[load] and time_metric in self.data[load][algo]:
                        value = self.data[load][algo][time_metric]
                        values.append(max(0, value))  # 确保非负值
                    else:
                        values.append(0)
                
                values = np.array(values)
                
                # 绘制堆叠柱子的一段
                color = self.time_metrics[time_metric]['color']
                bars = ax.bar(pos, values, width, bottom=bottom_values,
                            color=color, alpha=0.8, edgecolor='white', linewidth=0.8,
                            label=self.time_metrics[time_metric]['name'] if i == 0 else "")
                
                # 添加数值标签（只在足够大的段上显示）
                for j, (bar, value) in enumerate(zip(bars, values)):
                    if value > 10:  # 只在足够大的段上显示标签
                        label_y = bottom_values[j] + value / 2
                        ax.text(bar.get_x() + bar.get_width()/2., label_y,
                               f'{value:.0f}', ha='center', va='center',
                               fontsize=8, fontweight='bold', color='white')
                
                bottom_values += values
            
            # 在柱子顶部显示总时间
            for j, total in enumerate(bottom_values):
                if total > 0:
                    ax.text(pos[j], total + total*0.02,
                           f'{total:.0f}', ha='center', va='bottom',
                           fontsize=10, fontweight='bold', color='black')
        
        # 设置图表样式
        ax.set_xlabel('Load Level', fontsize=14, fontweight='bold')
        ax.set_ylabel('Time (ms)', fontsize=14, fontweight='bold')
        ax.set_title('Time Breakdown Analysis', fontsize=16, fontweight='bold', pad=15)
        ax.set_xticks(x)
        ax.set_xticklabels(labels, fontsize=12)
        ax.tick_params(axis='y', labelsize=11)
        
        # 美化网格
        ax.grid(True, alpha=0.3, linestyle='--', axis='y')
        ax.set_axisbelow(True)
        
        # 设置y轴范围
        max_total = 0
        for i, algo in enumerate(algorithms):
            for j, load in enumerate(load_levels):
                total = sum(self.data[load][algo].get(metric, 0) 
                           for metric in time_metrics_available 
                           if algo in self.data[load])
                max_total = max(max_total, total)
        
        if max_total > 0:
            ax.set_ylim(0, max_total * 1.15)
        
        # 优化布局
        ax.spines['top'].set_visible(False)
        ax.spines['right'].set_visible(False)
        
        # 添加时间分段图例
        time_legend_elements = [mpatches.Patch(color=self.time_metrics[metric]['color'], 
                                             label=self.time_metrics[metric]['name'])
                              for metric in time_metrics_available if metric in self.time_metrics]
        
        ax.legend(handles=time_legend_elements, loc='upper left', fontsize=10)
    
    def generate_summary_report(self):
        """生成实验总结报告"""
        if not self.data:
            print("❌ 没有数据可以分析")
            return
            
        print("\n" + "="*100)
        print("📋 实验数据详细总结报告 (Detailed Experiment Summary Report)")
        print("="*100)
        
        for load_level in sorted(self.data.keys()):
            load_name = self.load_level_mapping.get(load_level, load_level)
            print(f"\n🔸 {load_name} ({load_level}):")
            print("-" * 80)
            
            # 详细指标表格
            algorithms = sorted(self.data[load_level].keys())
            
            # 打印表头
            print(f"{'算法':<12} | {'RPS':<8} | {'响应时间':<10} | {'成本':<8} | {'延迟效率':<10} | {'成本效率':<10} | {'性价比':<10} | {'未完成':<8}")
            print("-" * 80)
            
            # 打印每个算法的数据
            for algo in algorithms:
                algo_name = self.algorithm_mapping.get(algo, algo)
                data = self.data[load_level][algo]
                
                rps = data.get('rps', 0)
                time_per_req = data.get('time_per_req', 0)
                cost_per_req = data.get('cost_per_req', 0)
                latency_eff = data.get('latency_efficiency', 0)
                cost_eff = data.get('cost_efficiency', 0)
                perf_ratio = data.get('performance_ratio', 0)
                undone = data.get('undone_req_cnt', 0)
                
                print(f"{algo_name:<12} | {rps:<8.3f} | {time_per_req:<10.1f} | {cost_per_req:<8.4f} | {latency_eff:<10.6f} | {cost_eff:<10.2f} | {perf_ratio:<10.2f} | {undone:<8.0f}")
            
            # 打印时间分解详情
            print(f"\n⏰ 时间分解详情 (毫秒):")
            print(f"{'算法':<12} | {'冷启动':<8} | {'调度等待':<10} | {'执行时间':<8} | {'数据接收':<10} | {'总时间':<8}")
            print("-" * 70)
            
            for algo in algorithms:
                algo_name = self.algorithm_mapping.get(algo, algo)
                data = self.data[load_level][algo]
                
                coldstart = data.get('coldstart_time_per_req', 0)
                waitsche = data.get('waitsche_time_per_req', 0)
                exe_time = data.get('exe_time_per_req', 0)
                datarecv = data.get('datarecv_time_per_req', 0)
                total_components = coldstart + waitsche + exe_time + datarecv
                
                print(f"{algo_name:<12} | {coldstart:<8.1f} | {waitsche:<10.1f} | {exe_time:<8.1f} | {datarecv:<10.1f} | {total_components:<8.1f}")
            
            # 性能排名分析
            print(f"\n🏆 性能排名分析:")
            
            # 按延迟效率排名（越小越好）
            latency_ranking = sorted(algorithms, 
                                   key=lambda x: self.data[load_level][x].get('latency_efficiency', float('inf')), 
                                   reverse=False)
            print(f"  延迟效率排名: {' > '.join([self.algorithm_mapping.get(a, a) for a in latency_ranking])}")
            
            # 按成本效率排名（越小越好）
            cost_ranking = sorted(algorithms, 
                                key=lambda x: self.data[load_level][x].get('cost_efficiency', float('inf')), 
                                reverse=False)
            print(f"  成本效率排名: {' > '.join([self.algorithm_mapping.get(a, a) for a in cost_ranking])}")
            
            # 按吞吐量排名
            rps_ranking = sorted(algorithms, 
                               key=lambda x: self.data[load_level][x].get('rps', 0), 
                               reverse=True)
            print(f"  吞吐量排名:   {' > '.join([self.algorithm_mapping.get(a, a) for a in rps_ranking])}")
        
        print("\n" + "="*100)
        print("📊 指标说明:")
        print("  - 延迟效率 = 总时间 / RPS (越低越好，表示处理单个请求的平均时间)")
        print("  - 成本效率 = 成本 / RPS (越低越好，表示处理单个请求的平均成本)")
        print("  - 性价比 = RPS / (总时间 × 成本) (越高越好，综合延迟和成本的效率指标)")
        print("="*100)

def main():
    """主函数"""
    print("🚀 启动实验数据可视化脚本")
    print("="*60)
    
    # 创建可视化器
    visualizer = ExperimentVisualizer()
    
    # 打印指标说明
    visualizer.print_metrics_info()
    
    # 加载数据
    print("\n📂 正在加载实验数据...")
    visualizer.load_data()
    
    if not visualizer.data:
        print("❌ 没有找到有效的实验数据")
        return
    
    # 生成总结报告
    visualizer.generate_summary_report()
    
    # 创建可视化图表
    print("\n🎨 正在生成可视化图表...")
    visualizer.create_visualization()
    
    print("\n✅ 实验数据可视化完成！")

if __name__ == "__main__":
    main() 