#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Academic Visualization Script for AAAI Conference
Generates publication-quality charts for serverless scheduling algorithms comparison
"""

import json
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib import rcParams
import seaborn as sns
from pathlib import Path

# Configure matplotlib for academic publication
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman']
rcParams['font.size'] = 12
rcParams['axes.labelsize'] = 15
rcParams['axes.titlesize'] = 17
rcParams['xtick.labelsize'] = 17
rcParams['ytick.labelsize'] = 19
rcParams['legend.fontsize'] = 17
rcParams['figure.titlesize'] = 19
rcParams['text.usetex'] = False  # Set to True if LaTeX is available

# Academic color palette (colorblind-friendly) - Soft academic colors
# Tableau 10 color palette - professional data visualization colors
TABLEAU_10_COLORS = [
"#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]

ACCENT_COLORS = {
    'baseline': TABLEAU_10_COLORS[:4],  # First 4 colors for baseline algorithms
    'advanced': TABLEAU_10_COLORS[4:9],  # Next 5 colors for advanced algorithms
    'proposed': TABLEAU_10_COLORS[2]  # Red for NSESche to make it stand out
}

# Load type mapping
LOAD_MAPPING = {
    'rflow': 'Low',
    'rfmiddle': 'Middle', 
    'rfhigh': 'High'
}

# Algorithm mapping and ordering
ALGORITHM_MAPPING = {
    'greedy': 'Greedy',
    'random': 'Random',
    'hash': 'Hash',
    'load_least': 'Load Balance',
    'sche_FaaSRank': 'FaaSRank',
    'sche_OCS': 'OCS',
    'sche_Hiku': 'Hiku',
    'sche_jiagu': 'Jiagu',
    'sche_orion': 'Orion',
    'sche_nash': 'NSESche',
    'sche_FaasRank': 'FaaSRank',
    'sche_ocs': 'OCS',
    'sche_hiku': 'Hiku',
    'sche_Jiagu': 'Jiagu',
    'sche_Orion': 'Orion',
    'sche_Nash': 'NSESche'
}

# Algorithm ordering (baseline first, then advanced, NSESche last)
ALGORITHM_ORDER = [
    'Greedy', 'Random', 'Hash', 'Load Balance',  # Baseline
    'FaaSRank', 'OCS', 'Hiku', 'Jiagu', 'Orion',  # Advanced
    'NSESche'  # Proposed
]

class AcademicVisualizer:
    def __init__(self, cache_dir='../../cache', output_dir='.'):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.data = {}
        
    def load_data(self):
        """Load experimental data from JSON files"""
        
        for json_file in self.cache_dir.glob('*.json'):
            try:
                # Parse filename to extract algorithm and load type
                filename = json_file.stem
                parts = filename.split('.')
                
                # Extract load type (rf*)
                load_type = None
                for part in parts:
                    if part.startswith('rf'):
                        load_type = part
                        break
                
                # Extract algorithm name using string search
                algorithm = None
                
                # Look for .scd( pattern in filename
                scd_start = filename.find('.scd(')
                if scd_start != -1:
                    scd_end = filename.find(').', scd_start)
                    if scd_end != -1:
                        algo_name = filename[scd_start + 5:scd_end]  # Extract between .scd( and ).
                        # Remove trailing dot if present
                        if algo_name.endswith('.'):
                            algo_name = algo_name[:-1]
                        if algo_name in ALGORITHM_MAPPING:
                            algorithm = ALGORITHM_MAPPING[algo_name]
                
                # Skip files that don't match our pattern
                if not (load_type and algorithm):
                    continue
                
                if load_type and algorithm:
                    # Load JSON data
                    with open(json_file, 'r') as f:
                        metrics = json.load(f)
                    
                    # Store data
                    if load_type not in self.data:
                        self.data[load_type] = {}
                    
                    self.data[load_type][algorithm] = {
                        'latency': metrics['time_per_req'],
                        'cost': metrics['cost_per_req'],
                        'throughput': metrics['rps'],
                        'cost_performance_ratio': metrics['rps'] / (metrics['cost_per_req'] * metrics['time_per_req']) if (metrics['cost_per_req'] > 0 and metrics['time_per_req'] > 0) else 0,
                        'coldstart_time': metrics['coldstart_time_per_req'],
                        'wait_time': metrics['waitsche_time_per_req'],
                        'execution_time': metrics['exe_time_per_req']
                    }
                    
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
        

    
    def get_algorithm_color(self, algorithm):
        """Get color for algorithm based on category"""
        if algorithm == 'NSESche':
            return ACCENT_COLORS['proposed']
        elif algorithm in ['Greedy', 'Random', 'Hash', 'Load Balance']:
            idx = ['Greedy', 'Random', 'Hash', 'Load Balance'].index(algorithm)
            return ACCENT_COLORS['baseline'][idx]
        else:
            advanced_algos = ['FaaSRank', 'OCS', 'Hiku', 'Jiagu', 'Orion']
            if algorithm in advanced_algos:
                idx = advanced_algos.index(algorithm) % len(ACCENT_COLORS['advanced'])
                return ACCENT_COLORS['advanced'][idx]
        return '#666666'  # Default gray
    
    def create_bar_charts(self):
        """Create bar charts for all metrics"""
        metrics = ['latency', 'cost', 'throughput', 'cost_performance_ratio']
        metric_labels = ['Average Latency (ms)', 'Average Cost', 'Throughput (RPS)', 'Quality-Price Ratio']
        subplot_labels = ['(a) Average Latency', '(b) Average Cost', '(c) Throughput', '(d) Quality-Price Ratio']
        
        fig, axes = plt.subplots(2, 2, figsize=(16, 10))
        axes = axes.flatten()
        
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        
        for i, (metric, label, subplot_label) in enumerate(zip(metrics, metric_labels, subplot_labels)):
            ax = axes[i]
            
            if metric == 'latency':
                # Stacked bar chart for latency breakdown
                self._create_stacked_latency_chart(ax, load_types, load_labels, subplot_label, True)
            else:
                # Regular grouped bar chart
                self._create_grouped_bar_chart(ax, metric, label, load_types, load_labels, subplot_label)
        
        plt.tight_layout(pad=2.5)
        # 调整子图间距，右边两个图略微向左移动
        plt.subplots_adjust(hspace=0.3, wspace=0.15, left=0.08, right=0.95)
        # plt.savefig(self.output_dir / 'performance_comparison.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'performance_comparison.png', dpi=300, bbox_inches='tight')
        plt.close()  # Close figure to free memory
    
    def _create_stacked_latency_chart(self, ax, load_types, load_labels, subplot_label, show_legend=False):
        """Create stacked bar chart for latency breakdown with load types as x-axis"""
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Number of load types and algorithms
        n_loads = len(load_types)
        n_algos = len(algorithms)
        
        # Calculate positions
        x = np.arange(n_loads)  # Load type positions
        width = 0.8 / n_algos  # Width of each bar
        
        # Soft academic color palette for latency components
        colors = {
            'coldstart': ['#e8c1a0', '#f7dc6f', '#abebc6'],  # Soft peach, yellow, mint
            'wait': ['#d7bde2', '#aed6f1', '#f9e79f'],       # Soft purple, blue, yellow
            'exec': ['#fadbd8', '#d5f4e6', '#fdeaa7']        # Soft pink, green, cream
        }
        
        # Get algorithm colors
        algo_colors = [self.get_algorithm_color(algo) for algo in algorithms]
        
        # Plot stacked bars for each algorithm
        for i, algo in enumerate(algorithms):
            coldstart_times = []
            wait_times = []
            exec_times = []
            
            for load_type in load_types:
                if load_type in self.data and algo in self.data[load_type]:
                    data = self.data[load_type][algo]
                    coldstart_times.append(data['coldstart_time'])
                    wait_times.append(data['wait_time'])
                    exec_times.append(data['execution_time'])
                else:
                    coldstart_times.append(0)
                    wait_times.append(0)
                    exec_times.append(0)
            
            # Calculate x positions for this algorithm
            x_pos = x + (i - n_algos/2 + 0.5) * width
            
            # Create stacked bars with proper color mapping
            base_color = algo_colors[i]
            # Generate color variations: coldstart (darker), wait (medium), execution (lightest)
            import matplotlib.colors as mcolors
            rgb = mcolors.to_rgb(base_color)
            # Coldstart: darker than base for all algorithms, with extra darkness for specific ones
            if i == 1:  # Second algorithm (index 1)
                coldstart_color = tuple(max(0.0, c - 0.3) for c in rgb)  # Extra darker
            elif i == 8:  # Ninth algorithm (index 8) - second to last
                coldstart_color = tuple(max(0.0, c - 0.27) for c in rgb)  # Darker
            else:
                coldstart_color = tuple(max(0.0, c - 0.2) for c in rgb)  # All deeper than before
            # Wait time: medium lightness (base color with slight adjustment)
            wait_color = tuple(min(1.0, c + 0.2) for c in rgb)
            # Execution: lightest
            exec_color = tuple(min(1.0, c + 0.4) for c in rgb)
            
            p1 = ax.bar(x_pos, coldstart_times, width, 
                       label=f'{algo} - Cold Start' if i == 0 else "",
                       color=coldstart_color, alpha=0.8)
            p2 = ax.bar(x_pos, wait_times, width, bottom=coldstart_times,
                       label=f'{algo} - Wait Time' if i == 0 else "",
                       color=wait_color, alpha=0.8)
            p3 = ax.bar(x_pos, exec_times, width,
                       bottom=np.array(coldstart_times) + np.array(wait_times),
                       label=f'{algo} - Execution' if i == 0 else "",
                       color=exec_color, alpha=0.8)
        
        ax.set_xlabel('Load Types', labelpad=8, fontweight='bold')
        ax.set_ylabel('Latency (ms)', fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(load_labels)
        
        # Algorithm legend (same as other subplots)
        if show_legend:
            # Create legend patches for each algorithm using their base colors
            legend_elements = []
            for i, algo in enumerate(algorithms):
                legend_elements.append(mpatches.Patch(color=algo_colors[i], alpha=0.9, label=algo))
            ax.legend(handles=legend_elements, loc='upper left', fontsize=11, ncol=2)
        
        ax.grid(True, alpha=0.3)
        
        # Add subplot label below x-axis label (slightly higher)
        ax.text(0.5, -0.20, subplot_label, transform=ax.transAxes, ha='center', va='top', 
                fontsize=14, fontweight='bold')
    
    def _create_grouped_bar_chart(self, ax, metric, label, load_types, load_labels, subplot_label):
        """Create grouped bar chart for a specific metric with load types as x-axis"""
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Number of load types and algorithms
        n_loads = len(load_types)
        n_algos = len(algorithms)
        
        # Calculate positions
        x = np.arange(n_loads)  # Load type positions
        width = 0.8 / n_algos  # Width of each bar
        
        # Get algorithm colors
        algo_colors = [self.get_algorithm_color(algo) for algo in algorithms]
        
        # Plot bars for each algorithm
        for i, algo in enumerate(algorithms):
            values = []
            
            for load_type in load_types:
                if load_type in self.data and algo in self.data[load_type]:
                    values.append(self.data[load_type][algo][metric])
                else:
                    values.append(0)
            
            # Calculate x positions for this algorithm
            x_pos = x + (i - n_algos/2 + 0.5) * width
            
            bars = ax.bar(x_pos, values, width, label=algo, 
                         color=algo_colors[i], alpha=0.9)
        
        ax.set_xlabel('Load Types', labelpad=8, fontweight='bold')
        ax.set_ylabel(label, fontweight='bold')
        ax.set_xticks(x)
        ax.set_xticklabels(load_labels)
        ax.legend(loc='upper right', fontsize=11, ncol=2)
        ax.grid(True, alpha=0.3)
        
        # Add subplot label below x-axis label (slightly higher)
        ax.text(0.5, -0.20, subplot_label, transform=ax.transAxes, ha='center', va='top', 
                fontsize=14, fontweight='bold')
    
    def create_radar_chart(self):
        """Create radar chart for throughput comparison"""
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        
        # Set up radar chart
        angles = np.linspace(0, 2 * np.pi, len(load_types), endpoint=False).tolist()
        angles += angles[:1]  # Complete the circle
        
        fig, ax = plt.subplots(figsize=(10, 10), subplot_kw=dict(projection='polar'))
        
        # Plot each algorithm
        for i, algo in enumerate(algorithms):
            values = []
            for load_type in load_types:
                if load_type in self.data and algo in self.data[load_type]:
                    values.append(self.data[load_type][algo]['throughput'])
                else:
                    values.append(0)
            
            values += values[:1]  # Complete the circle
            
            color = self.get_algorithm_color(algo)
            linewidth = 3 if algo == 'NSESche' else 2
            alpha = 0.9 if algo == 'NSESche' else 0.7
            
            ax.plot(angles, values, 'o-', linewidth=linewidth, label=algo, 
                   color=color, alpha=alpha)
            ax.fill(angles, values, alpha=0.1, color=color)
        
        # Customize radar chart
        ax.set_xticks(angles[:-1])
        ax.set_xticklabels(load_labels, fontsize=25)  # 增大负载标签字体
        ax.set_ylim(0, None)
        # ax.set_title('Throughput Comparison (RPS)', size=16, pad=20)  # 移除标题
        ax.legend(loc='upper right', bbox_to_anchor=(1.15, 1.1), fontsize=21)  # 增大图例字体
        ax.tick_params(axis='y', labelsize=21)  # 增大y轴数字标签字体
        ax.grid(True)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'throughput_radar.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'throughput_radar.png', dpi=300, bbox_inches='tight')
        plt.close()  # Close figure to free memory
    
    def _algorithm_has_data(self, algorithm):
        """Check if algorithm has data in any load type"""
        for load_type in self.data:
            if algorithm in self.data[load_type]:
                return True
        return False
    
    def generate_all_charts(self):
        """Generate all charts"""
        # Ensure output directory exists
        self.output_dir.mkdir(exist_ok=True)
        
        # Load data
        self.load_data()
        
        if not self.data:
            print("No data found. Please check the cache directory.")
            return
        
        # Generate charts
        self.create_bar_charts()
        self.create_radar_chart()
        self.create_html_viewer()
    
    def create_html_viewer(self):
        """Create HTML file to view all charts"""
        html_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Academic Visualization Results - AAAI Conference</title>
    <style>
        body {
            font-family: 'Times New Roman', serif;
            margin: 20px;
            background-color: #f8f9fa;
        }
        .container {
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 30px;
            border-radius: 10px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        h1 {
            color: #2c3e50;
            text-align: center;
            margin-bottom: 30px;
            font-size: 28px;
        }
        h2 {
            color: #34495e;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
            margin-top: 40px;
        }
        .chart-section {
            margin: 30px 0;
            text-align: center;
        }
        .chart-image {
            max-width: 100%;
            height: auto;
            border: 1px solid #ddd;
            border-radius: 8px;
            margin: 10px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }
        .description {
            margin: 15px 0;
            padding: 15px;
            background-color: #f8f9fa;
            border-left: 4px solid #3498db;
            font-style: italic;
        }
        .footer {
            text-align: center;
            margin-top: 50px;
            padding-top: 20px;
            border-top: 1px solid #ddd;
            color: #7f8c8d;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>Academic Visualization Results</h1>
        <p style="text-align: center; font-size: 18px; color: #7f8c8d;">AAAI Conference Submission - Serverless Scheduling Algorithms Comparison</p>
        
        <h2>Performance Comparison Charts</h2>
        <div class="chart-section">
            <div class="description">
                <strong>Figure 1:</strong> Comprehensive performance comparison across different load types (Low, Middle, High). 
                All charts use soft academic colors suitable for publication and group algorithms by load types for better comparison.
            </div>
            <img src="performance_comparison.png" alt="Performance Comparison" class="chart-image">
        </div>
        
        <h2>Throughput Radar Chart</h2>
        <div class="chart-section">
            <div class="description">
                <strong>Figure 2:</strong> Radar chart showing throughput performance across different load conditions. 
                NSESche (proposed algorithm) is highlighted for emphasis.
            </div>
            <img src="throughput_radar.png" alt="Throughput Radar Chart" class="chart-image">
        </div>
        
        <div class="footer">
            <p>Generated by Academic Visualization Script</p>
            <p>Optimized for AAAI Conference Submission</p>
        </div>
    </div>
</body>
</html>
        """
        
        html_file = self.output_dir / 'view_all_charts.html'
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"HTML viewer created: {html_file}")

def main():
    """Main function"""
    # Initialize visualizer
    visualizer = AcademicVisualizer(
        cache_dir='cache',
        output_dir='./scripts/Comparative experiment/'
    )
    
    # Generate all charts
    visualizer.generate_all_charts()

if __name__ == '__main__':
    main()