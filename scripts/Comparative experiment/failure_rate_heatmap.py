#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Request Failure Rate Analysis Heatmap
请求失败率分析热力图

This script creates heatmaps for request failure rate analysis across different algorithms and load types.
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

class FailureRateAnalyzer:
    def __init__(self, cache_dir='../cache', output_dir='.'):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.data = {}
        self.failure_rates = {}
        
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
                
                self.data[load_type][algorithm] = {
                    'undone_req_cnt': metrics['undone_req_cnt'],
                    'rps': metrics['rps'],
                    'cost_per_req': metrics['cost_per_req'],
                    'time_per_req': metrics['time_per_req'],
                    'fn_container_cnt': metrics['fn_container_cnt']
                }
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
    
    def calculate_failure_rates(self):
        """Calculate failure rates for each algorithm and load type"""
        # Estimate total requests based on RPS and simulation time
        # Assuming simulation runs for a fixed duration, we can estimate from undone requests
        for load_type in self.data:
            if load_type not in self.failure_rates:
                self.failure_rates[load_type] = {}
            
            for algorithm in self.data[load_type]:
                undone_req = self.data[load_type][algorithm]['undone_req_cnt']
                rps = self.data[load_type][algorithm]['rps']
                
                # Estimate total requests (assuming 100 second simulation)
                # This is a rough estimation, adjust based on your simulation setup
                estimated_total_req = rps * 100 + undone_req
                
                # Calculate failure rate as percentage
                failure_rate = (undone_req / estimated_total_req) * 100 if estimated_total_req > 0 else 0
                
                self.failure_rates[load_type][algorithm] = failure_rate
    
    def create_failure_rate_heatmap(self):
        """Create heatmap for failure rate analysis"""
        # Prepare data for heatmap
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Create matrix for heatmap
        failure_matrix = np.zeros((len(algorithms), len(load_types)))
        
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.failure_rates and algo in self.failure_rates[load_type]:
                    failure_matrix[i, j] = self.failure_rates[load_type][algo]
                else:
                    failure_matrix[i, j] = np.nan
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Use a color map that highlights high failure rates (red) and low failure rates (green)
        cmap = plt.cm.RdYlGn_r  # Red-Yellow-Green reversed (red for high failure)
        
        # Create heatmap with seaborn for better aesthetics
        sns.heatmap(failure_matrix, 
                   xticklabels=load_labels,
                   yticklabels=algorithms,
                   annot=True, 
                   fmt='.2f',
                   cmap=cmap,
                   cbar_kws={'label': 'Failure Rate (%)'},
                   ax=ax,
                   square=False,
                   linewidths=0.5)
        
        ax.set_title('Request Failure Rate Analysis', fontsize=16, fontweight='bold', pad=20)
        ax.set_xlabel('Load Type', fontweight='bold')
        ax.set_ylabel('Scheduling Algorithm', fontweight='bold')
        
        # Rotate x-axis labels for better readability
        plt.xticks(rotation=0)
        plt.yticks(rotation=0)
        
        # Highlight NSESche algorithm if present
        if 'NSESche' in algorithms:
            nsesche_idx = algorithms.index('NSESche')
            # Add a border around NSESche row
            for j in range(len(load_types)):
                rect = plt.Rectangle((j, nsesche_idx), 1, 1, 
                                   fill=False, edgecolor='blue', linewidth=3)
                ax.add_patch(rect)
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'failure_rate_heatmap.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'failure_rate_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_detailed_failure_analysis(self):
        """Create detailed failure analysis with additional metrics"""
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # 1. Failure Rate Heatmap (top-left)
        ax1 = axes[0, 0]
        failure_matrix = np.zeros((len(algorithms), len(load_types)))
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.failure_rates and algo in self.failure_rates[load_type]:
                    failure_matrix[i, j] = self.failure_rates[load_type][algo]
        
        sns.heatmap(failure_matrix, xticklabels=load_labels, yticklabels=algorithms,
                   annot=True, fmt='.1f', cmap='RdYlGn_r', ax=ax1, cbar_kws={'label': 'Failure Rate (%)'})
        ax1.set_title('(a) Failure Rate (%)', fontweight='bold')
        ax1.set_xlabel('Load Type', fontweight='bold')
        ax1.set_ylabel('Algorithm', fontweight='bold')
        
        # 2. Absolute Undone Requests (top-right)
        ax2 = axes[0, 1]
        undone_matrix = np.zeros((len(algorithms), len(load_types)))
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.data and algo in self.data[load_type]:
                    undone_matrix[i, j] = self.data[load_type][algo]['undone_req_cnt']
        
        sns.heatmap(undone_matrix, xticklabels=load_labels, yticklabels=algorithms,
                   annot=True, fmt='.0f', cmap='Reds', ax=ax2, cbar_kws={'label': 'Undone Requests'})
        ax2.set_title('(b) Undone Requests Count', fontweight='bold')
        ax2.set_xlabel('Load Type', fontweight='bold')
        ax2.set_ylabel('Algorithm', fontweight='bold')
        
        # 3. Throughput vs Failure Rate Scatter (bottom-left)
        ax3 = axes[1, 0]
        colors = ['red', 'orange', 'green']
        for j, (load_type, color) in enumerate(zip(load_types, colors)):
            x_vals, y_vals = [], []
            for algo in algorithms:
                if (load_type in self.data and algo in self.data[load_type] and 
                    load_type in self.failure_rates and algo in self.failure_rates[load_type]):
                    x_vals.append(self.data[load_type][algo]['rps'])
                    y_vals.append(self.failure_rates[load_type][algo])
            
            ax3.scatter(x_vals, y_vals, c=color, label=load_labels[j], alpha=0.7, s=60)
        
        ax3.set_xlabel('Throughput (RPS)', fontweight='bold')
        ax3.set_ylabel('Failure Rate (%)', fontweight='bold')
        ax3.set_title('(c) Throughput vs Failure Rate', fontweight='bold')
        ax3.legend()
        ax3.grid(True, alpha=0.3)
        
        # 4. Reliability Score (bottom-right)
        ax4 = axes[1, 1]
        reliability_matrix = np.zeros((len(algorithms), len(load_types)))
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.failure_rates and algo in self.failure_rates[load_type]:
                    # Reliability score = 100 - failure_rate
                    reliability_matrix[i, j] = 100 - self.failure_rates[load_type][algo]
        
        sns.heatmap(reliability_matrix, xticklabels=load_labels, yticklabels=algorithms,
                   annot=True, fmt='.1f', cmap='RdYlGn', ax=ax4, cbar_kws={'label': 'Reliability Score (%)'})
        ax4.set_title('(d) Reliability Score (%)', fontweight='bold')
        ax4.set_xlabel('Load Type', fontweight='bold')
        ax4.set_ylabel('Algorithm', fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'detailed_failure_analysis.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'detailed_failure_analysis.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _algorithm_has_data(self, algorithm):
        """Check if algorithm has data in any load type"""
        for load_type in self.data:
            if algorithm in self.data[load_type]:
                return True
        return False

def main():
    """Main function to generate failure rate analysis"""
    analyzer = FailureRateAnalyzer()
    analyzer.load_data()
    analyzer.calculate_failure_rates()
    
    print("Generating failure rate analysis...")
    
    # Create main failure rate heatmap
    analyzer.create_failure_rate_heatmap()
    print("✓ Failure rate heatmap saved")
    
    # Create detailed failure analysis
    analyzer.create_detailed_failure_analysis()
    print("✓ Detailed failure analysis saved")
    
    print("All failure rate analysis plots generated successfully!")

if __name__ == '__main__':
    main()