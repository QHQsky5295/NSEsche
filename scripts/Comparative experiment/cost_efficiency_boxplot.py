#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cost Efficiency Boxplot Analysis
成本效率箱线图分析

This script creates boxplots for cost efficiency analysis across different algorithms and load types.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import rcParams
from pathlib import Path
import pandas as pd

# Configure matplotlib for academic publication
rcParams['font.family'] = 'serif'
rcParams['font.serif'] = ['Times New Roman']
rcParams['font.size'] = 12
rcParams['axes.labelsize'] = 14
rcParams['axes.titlesize'] = 16
rcParams['xtick.labelsize'] = 12
rcParams['ytick.labelsize'] = 12
rcParams['legend.fontsize'] = 12
rcParams['figure.titlesize'] = 18
rcParams['text.usetex'] = False

# Academic color palette
ACCENT_COLORS = {
    'baseline': ['#d62728', '#ff7f0e', '#2ca02c', '#1f77b4'],  # Red, Orange, Green, Blue
    'advanced': ['#9467bd', '#8c564b', '#e377c2', '#2f2f2f'],  # Purple, Brown, Pink, Dark Gray
    'proposed': '#17becf'  # Cyan for NSESche
}

# Load type mapping
LOAD_MAPPING = {
    'rflow': 'Low Load',
    'rfmiddle': 'Middle Load', 
    'rfhigh': 'High Load'
}

# Algorithm mapping and ordering
ALGORITHM_MAPPING = {
    'greedy': 'Greedy',
    'random': 'Random',
    'hash': 'Hash',
    'load_least': 'Load Balance',
    'sche_FaaSRank': 'FaasRank',
    'sche_OCS': 'OCS',
    'sche_Hiku': 'Hiku',
    'sche_jiagu': 'Jiagu',
    'sche_orion': 'Orion',
    'sche_nash': 'NSESche',
    'sche_faasrank': 'FaasRank',
    'sche_ocs': 'OCS',
    'sche_hiku': 'Hiku',
    'sche_Jiagu': 'Jiagu',
    'sche_Orion': 'Orion',
    'sche_Nash': 'NSESche'
}

# Algorithm ordering
ALGORITHM_ORDER = [
    'Greedy', 'Random', 'Hash', 'Load Balance',  # Baseline
    'FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion',  # Advanced
    'NSESche'  # Proposed
]

class CostEfficiencyAnalyzer:
    def __init__(self, cache_dir='../cache', output_dir='.'):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.data = {}
        
    def load_data(self):
        """Load experimental data from JSON files"""
        for json_file in self.cache_dir.glob('*.json'):
            try:
                filename = json_file.stem
                parts = filename.split('.')
                
                # Extract load type
                load_type = None
                for part in parts:
                    if part.startswith('rf'):
                        load_type = part
                        break
                
                # Extract algorithm name
                algorithm = None
                scd_start = filename.find('.scd(')
                if scd_start != -1:
                    scd_end = filename.find(').', scd_start)
                    if scd_end != -1:
                        algo_name = filename[scd_start + 5:scd_end]
                        if algo_name.endswith('.'):
                            algo_name = algo_name[:-1]
                        if algo_name in ALGORITHM_MAPPING:
                            algorithm = ALGORITHM_MAPPING[algo_name]
                
                if not (load_type and algorithm):
                    continue
                
                # Load JSON data
                with open(json_file, 'r') as f:
                    metrics = json.load(f)
                
                # Store data
                if load_type not in self.data:
                    self.data[load_type] = {}
                
                # Calculate cost efficiency metrics
                cost_per_req = metrics['cost_per_req']
                rps = metrics['rps']
                time_per_req = metrics['time_per_req']
                
                # Cost efficiency = Throughput / Cost (higher is better)
                cost_efficiency = rps / cost_per_req if cost_per_req > 0 else 0
                
                # Performance per dollar = 1 / (cost * latency) (higher is better)
                perf_per_dollar = 1 / (cost_per_req * time_per_req) if (cost_per_req * time_per_req) > 0 else 0
                
                # Quality-Price Ratio
                quality_price_ratio = rps / cost_per_req if cost_per_req > 0 else 0
                
                self.data[load_type][algorithm] = {
                    'cost_per_req': cost_per_req,
                    'rps': rps,
                    'time_per_req': time_per_req,
                    'cost_efficiency': cost_efficiency,
                    'perf_per_dollar': perf_per_dollar,
                    'quality_price_ratio': quality_price_ratio,
                    'fn_container_cnt': metrics['fn_container_cnt']
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
            advanced_algos = ['FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion']
            if algorithm in advanced_algos:
                idx = advanced_algos.index(algorithm) % len(ACCENT_COLORS['advanced'])
                return ACCENT_COLORS['advanced'][idx]
        return '#666666'
    
    def create_cost_efficiency_boxplots(self):
        """Create boxplots for cost efficiency analysis"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        metrics = ['cost_per_req', 'cost_efficiency', 'perf_per_dollar', 'quality_price_ratio']
        metric_labels = ['Cost per Request', 'Cost Efficiency (RPS/Cost)', 
                        'Performance per Dollar', 'Quality-Price Ratio']
        subplot_labels = ['(a) Cost per Request', '(b) Cost Efficiency', 
                         '(c) Performance per Dollar', '(d) Quality-Price Ratio']
        
        for idx, (metric, label, subplot_label) in enumerate(zip(metrics, metric_labels, subplot_labels)):
            ax = axes[idx // 2, idx % 2]
            
            # Prepare data for boxplot
            data_for_plot = []
            labels_for_plot = []
            colors_for_plot = []
            
            for algo in algorithms:
                algo_data = []
                for load_type in load_types:
                    if load_type in self.data and algo in self.data[load_type]:
                        algo_data.append(self.data[load_type][algo][metric])
                
                if algo_data:  # Only add if we have data
                    data_for_plot.append(algo_data)
                    labels_for_plot.append(algo)
                    colors_for_plot.append(self.get_algorithm_color(algo))
            
            # Create boxplot
            if data_for_plot:
                bp = ax.boxplot(data_for_plot, labels=labels_for_plot, patch_artist=True,
                               showmeans=True, meanline=True)
                
                # Color the boxes
                for patch, color in zip(bp['boxes'], colors_for_plot):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                # Highlight NSESche if present
                if 'NSESche' in labels_for_plot:
                    nsesche_idx = labels_for_plot.index('NSESche')
                    bp['boxes'][nsesche_idx].set_linewidth(3)
                    bp['boxes'][nsesche_idx].set_edgecolor('blue')
            
            ax.set_title(subplot_label, fontweight='bold', fontsize=14)
            ax.set_ylabel(label, fontweight='bold')
            ax.set_xlabel('Algorithm', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels for better readability
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'cost_efficiency_boxplots.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'cost_efficiency_boxplots.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_load_specific_boxplots(self):
        """Create separate boxplots for each load type"""
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        
        fig, axes = plt.subplots(1, 3, figsize=(18, 6))
        
        for i, (load_type, load_label) in enumerate(zip(load_types, load_labels)):
            ax = axes[i]
            
            if load_type not in self.data:
                continue
            
            algorithms = [algo for algo in ALGORITHM_ORDER if algo in self.data[load_type]]
            
            # Prepare data for cost efficiency
            cost_eff_data = []
            labels = []
            colors = []
            
            for algo in algorithms:
                cost_eff_data.append([self.data[load_type][algo]['cost_efficiency']])
                labels.append(algo)
                colors.append(self.get_algorithm_color(algo))
            
            # Create boxplot (will be single points since we have one value per algorithm)
            if cost_eff_data:
                bp = ax.boxplot(cost_eff_data, labels=labels, patch_artist=True)
                
                # Color the boxes
                for patch, color in zip(bp['boxes'], colors):
                    patch.set_facecolor(color)
                    patch.set_alpha(0.7)
                
                # Highlight NSESche if present
                if 'NSESche' in labels:
                    nsesche_idx = labels.index('NSESche')
                    bp['boxes'][nsesche_idx].set_linewidth(3)
                    bp['boxes'][nsesche_idx].set_edgecolor('blue')
            
            ax.set_title(f'{load_label}', fontweight='bold', fontsize=14)
            ax.set_ylabel('Cost Efficiency (RPS/Cost)', fontweight='bold')
            ax.set_xlabel('Algorithm', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
        
        plt.suptitle('Cost Efficiency by Load Type', fontsize=16, fontweight='bold')
        plt.tight_layout()
        plt.savefig(self.output_dir / 'cost_efficiency_by_load.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'cost_efficiency_by_load.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_cost_distribution_analysis(self):
        """Create violin plots for cost distribution analysis"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Prepare data for violin plots
        df_list = []
        for load_type in load_types:
            if load_type in self.data:
                for algo in algorithms:
                    if algo in self.data[load_type]:
                        df_list.append({
                            'Algorithm': algo,
                            'Load Type': LOAD_MAPPING[load_type],
                            'Cost per Request': self.data[load_type][algo]['cost_per_req'],
                            'Cost Efficiency': self.data[load_type][algo]['cost_efficiency'],
                            'Performance per Dollar': self.data[load_type][algo]['perf_per_dollar'],
                            'Quality-Price Ratio': self.data[load_type][algo]['quality_price_ratio']
                        })
        
        if not df_list:
            print("No data available for cost distribution analysis")
            return
        
        df = pd.DataFrame(df_list)
        
        metrics = ['Cost per Request', 'Cost Efficiency', 'Performance per Dollar', 'Quality-Price Ratio']
        subplot_labels = ['(a) Cost per Request', '(b) Cost Efficiency', 
                         '(c) Performance per Dollar', '(d) Quality-Price Ratio']
        
        for idx, (metric, subplot_label) in enumerate(zip(metrics, subplot_labels)):
            ax = axes[idx // 2, idx % 2]
            
            # Create violin plot
            sns.violinplot(data=df, x='Algorithm', y=metric, hue='Load Type', 
                          ax=ax, palette=['red', 'orange', 'green'])
            
            ax.set_title(subplot_label, fontweight='bold', fontsize=14)
            ax.set_ylabel(metric, fontweight='bold')
            ax.set_xlabel('Algorithm', fontweight='bold')
            ax.grid(True, alpha=0.3)
            
            # Rotate x-axis labels
            plt.setp(ax.get_xticklabels(), rotation=45, ha='right')
            
            # Move legend to avoid overlap
            if idx == 0:
                ax.legend(bbox_to_anchor=(1.05, 1), loc='upper left')
            else:
                ax.legend().set_visible(False)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'cost_distribution_analysis.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'cost_distribution_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _algorithm_has_data(self, algorithm):
        """Check if algorithm has data in any load type"""
        for load_type in self.data:
            if algorithm in self.data[load_type]:
                return True
        return False

def main():
    """Main function to generate cost efficiency analysis"""
    analyzer = CostEfficiencyAnalyzer()
    analyzer.load_data()
    
    print("Generating cost efficiency analysis...")
    
    # Create main cost efficiency boxplots
    analyzer.create_cost_efficiency_boxplots()
    print("✓ Cost efficiency boxplots saved")
    
    # Create load-specific boxplots
    analyzer.create_load_specific_boxplots()
    print("✓ Load-specific cost efficiency plots saved")
    
    # Create cost distribution analysis
    analyzer.create_cost_distribution_analysis()
    print("✓ Cost distribution analysis saved")
    
    print("All cost efficiency analysis plots generated successfully!")

if __name__ == '__main__':
    main()