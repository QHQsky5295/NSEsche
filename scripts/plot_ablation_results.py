import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
from matplotlib import rcParams
import matplotlib.font_manager as fm

# 设置字体为Times New Roman
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
rcParams['font.size'] = 20
rcParams['axes.labelsize'] = 20
rcParams['axes.titlesize'] = 20
rcParams['xtick.labelsize'] = 18
rcParams['ytick.labelsize'] = 18
rcParams['legend.fontsize'] = 20
rcParams['axes.unicode_minus'] = False

# AAAI顶会风格的配色方案
colors = ['#2E86AB', '#A23B72', '#F18F01', '#C73E1D']

def read_excel_data(file_path):
    """读取Excel文件的所有工作表"""
    try:
        # 读取所有工作表
        excel_data = pd.read_excel(file_path, sheet_name=None)
        return excel_data
    except Exception as e:
        print(f"读取Excel文件时出错: {e}")
        return None

def create_bar_chart(data, title, ax, color, subplot_label, all_algorithm_cols):
    """创建单个柱状图"""
    if data is None or data.empty:
        ax.text(0.5, 0.5, 'No Data', ha='center', va='center', transform=ax.transAxes)
        return
    
    # 数据格式：第一列是场景(low/middle/high)，其他列是不同算法的结果
    if len(data.columns) >= 2:
        scenarios = data.iloc[:, 0].astype(str)  # low, middle, high
        
        # 获取算法列（除第一列外的所有列）
        algorithm_cols = data.columns[1:]
        n_algorithms = len(algorithm_cols)
        n_scenarios = len(scenarios)
        
        # 设置y轴标签（英文）
        title_map = {
            '成本': 'Cost',
            '延迟(ms)': 'Latency (ms)',
            '吞吐量(RPS)': 'Throughput (RPS)',
            '性价比': 'Quality-Price Ratio'
        }
        ylabel = title_map.get(title, title)
        
        # 设置柱状图的位置
        x = np.arange(n_scenarios)
        width = 0.7 / n_algorithms  # 柱子宽度，减少宽度避免重叠
        
        # 为每个算法创建柱子
        for i, col in enumerate(algorithm_cols):
            values = pd.to_numeric(data[col], errors='coerce')
            offset = (i - n_algorithms/2 + 0.5) * width
            
            # 处理算法名称
            label_name = col.replace('no_', 'w/o ').replace('_', ' ')
            if col == 'Nash Equilibrium Algorithm':
                label_name = 'NSESche'
            
            # 只在第一个子图中添加图例标签
            legend_label = label_name if subplot_label == '(a)' else None
            
            bars = ax.bar(x + offset, values, width, 
                         color=plt.cm.Set3(i/n_algorithms), alpha=0.8,
                         edgecolor='black', linewidth=0.5,
                         label=legend_label)
        
        # 设置x轴
        ax.set_xticks(x)
        ax.set_xticklabels(scenarios)
        ax.set_xlabel('Workload Intensity', fontweight='bold')
        
        ax.set_ylabel(ylabel, fontweight='bold')
        
        # 设置y轴范围
        all_values = data.iloc[:, 1:].values.flatten()
        all_values = all_values[~pd.isna(all_values)]
        if len(all_values) > 0:
            ax.set_ylim(0, max(all_values) * 1.1)  # 减少上方空白
        
        ax.grid(True, alpha=0.3, axis='y')
        
    else:
        ax.text(0.5, 0.5, 'Invalid Data Format', ha='center', va='center', transform=ax.transAxes)
    
    # 添加子图标识
    ax.text(0.5, -0.22, subplot_label, transform=ax.transAxes, 
            fontsize=16, fontweight='bold', ha='center')
    
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

def plot_ablation_results(file_path):
    """绘制消融实验结果"""
    # 读取Excel数据
    excel_data = read_excel_data(file_path)
    
    if excel_data is None:
        print("无法读取Excel文件")
        return
    
    # 获取工作表名称
    sheet_names = list(excel_data.keys())
    print(f"发现 {len(sheet_names)} 个工作表: {sheet_names}")
    
    # 定义子图标识
    subplot_labels = ['(a)', '(b)', '(c)', '(d)']
    
    # 创建图形，四个子图排成一行，减少留白
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    
    # 获取所有算法列名（用于统一图例）
    all_algorithm_cols = set()
    for data in excel_data.values():
        if len(data.columns) >= 2:
            all_algorithm_cols.update(data.columns[1:])
    all_algorithm_cols = list(all_algorithm_cols)
    
    # 为每个工作表创建柱状图
    for i, (sheet_name, data) in enumerate(excel_data.items()):
        if i >= 4:  # 只处理前4个工作表
            break
            
        print(f"\n处理工作表: {sheet_name}")
        print(f"数据形状: {data.shape}")
        print(f"列名: {data.columns.tolist()}")
        print(f"前几行数据:\n{data.head()}")
        
        # 创建柱状图
        create_bar_chart(data, sheet_name, axes[i], colors[i % len(colors)], subplot_labels[i], all_algorithm_cols)
    
    # 如果工作表少于4个，隐藏多余的子图
    for i in range(len(excel_data), 4):
        axes[i].set_visible(False)
    
    # 在图片底部添加统一图例
    handles, labels = axes[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, -0.02), 
               ncol=len(labels), fontsize=14, frameon=False)
    
    # 调整布局，减少留白
    plt.tight_layout()
    plt.subplots_adjust(top=0.95, bottom=0.26, left=0.05, right=0.98, wspace=0.3)
    
    # 保存图片
    output_path = file_path.replace('.xlsx', '_ablation_charts.png')
    plt.savefig(output_path, dpi=300, bbox_inches='tight', facecolor='white')
    print(f"\n图表已保存到: {output_path}")
    
    # 显示图片
    plt.show()

if __name__ == "__main__":
    # Excel文件路径
    excel_file = r"c:\Users\99349\Desktop\serverless_sim_game\scripts\experiment_results_20250721_105643.xlsx"
    
    # 绘制消融实验结果
    plot_ablation_results(excel_file)