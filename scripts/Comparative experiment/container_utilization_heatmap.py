#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Container Utilization Heatmap Analysis
容器利用率热力图分析

This script creates heatmaps for container utilization analysis across different algorithms and load types.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib import rcParams
from pathlib import Path
import pandas as pd
from matplotlib.colors import LinearSegmentedColormap

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

class ContainerUtilizationAnalyzer:
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
                
                # Calculate container utilization metrics
                fn_container_cnt = metrics.get('fn_container_cnt', 0)
                rps = metrics['rps']
                time_per_req = metrics['time_per_req']
                exe_time_per_req = metrics.get('exe_time_per_req', 0)
                coldstart_time_per_req = metrics.get('coldstart_time_per_req', 0)
                waitsche_time_per_req = metrics.get('waitsche_time_per_req', 0)
                
                # Container efficiency = RPS / Container Count (higher is better)
                container_efficiency = rps / fn_container_cnt if fn_container_cnt > 0 else 0
                
                # Resource utilization = Execution time / Total time (higher is better)
                resource_utilization = exe_time_per_req / time_per_req if time_per_req > 0 else 0
                
                # Container density = Requests per container per second
                container_density = rps / fn_container_cnt if fn_container_cnt > 0 else 0
                
                # Idle time ratio = (Total time - Execution time) / Total time (lower is better)
                idle_time_ratio = (time_per_req - exe_time_per_req) / time_per_req if time_per_req > 0 else 0
                
                # Cold start overhead = Cold start time / Total time (lower is better)
                coldstart_overhead = coldstart_time_per_req / time_per_req if time_per_req > 0 else 0
                
                # Wait scheduling overhead = Wait scheduling time / Total time (lower is better)
                waitsche_overhead = waitsche_time_per_req / time_per_req if time_per_req > 0 else 0
                
                self.data[load_type][algorithm] = {
                    'fn_container_cnt': fn_container_cnt,
                    'rps': rps,
                    'time_per_req': time_per_req,
                    'exe_time_per_req': exe_time_per_req,
                    'coldstart_time_per_req': coldstart_time_per_req,
                    'waitsche_time_per_req': waitsche_time_per_req,
                    'container_efficiency': container_efficiency,
                    'resource_utilization': resource_utilization,
                    'container_density': container_density,
                    'idle_time_ratio': idle_time_ratio,
                    'coldstart_overhead': coldstart_overhead,
                    'waitsche_overhead': waitsche_overhead
                }
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
    
    def create_container_utilization_heatmap(self):
        """Create main container utilization heatmap"""
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Prepare data matrix for container efficiency
        efficiency_matrix = np.zeros((len(algorithms), len(load_types)))
        
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.data and algo in self.data[load_type]:
                    efficiency_matrix[i, j] = self.data[load_type][algo]['container_efficiency']
                else:
                    efficiency_matrix[i, j] = np.nan
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Custom colormap
        colors = ['#d73027', '#f46d43', '#fdae61', '#fee08b', '#e6f598', '#abdda4', '#66c2a5', '#3288bd']
        n_bins = 100
        cmap = LinearSegmentedColormap.from_list('custom', colors, N=n_bins)
        
        # Create heatmap
        im = ax.imshow(efficiency_matrix, cmap=cmap, aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(range(len(load_labels)))
        ax.set_yticks(range(len(algorithms)))
        ax.set_xticklabels(load_labels)
        ax.set_yticklabels(algorithms)
        
        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
        plt.setp(ax.get_yticklabels(), rotation=0, ha="right")
        
        # Add text annotations
        for i in range(len(algorithms)):
            for j in range(len(load_types)):
                if not np.isnan(efficiency_matrix[i, j]):
                    text = ax.text(j, i, f'{efficiency_matrix[i, j]:.3f}',
                                 ha="center", va="center", color="black", fontweight='bold')
        
        # Highlight NSESche row if present
        if 'NSESche' in algorithms:
            nsesche_idx = algorithms.index('NSESche')
            for j in range(len(load_types)):
                rect = plt.Rectangle((j-0.5, nsesche_idx-0.5), 1, 1, 
                                   fill=False, edgecolor='blue', linewidth=3)
                ax.add_patch(rect)
        
        ax.set_title('Container Efficiency Heatmap\n(RPS per Container)', fontweight='bold', fontsize=16)
        ax.set_xlabel('Load Type', fontweight='bold')
        ax.set_ylabel('Algorithm', fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Container Efficiency (RPS/Container)', rotation=270, labelpad=20, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'container_utilization_heatmap.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'container_utilization_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_resource_utilization_heatmap(self):
        """Create resource utilization heatmap"""
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Prepare data matrix for resource utilization
        utilization_matrix = np.zeros((len(algorithms), len(load_types)))
        
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.data and algo in self.data[load_type]:
                    utilization_matrix[i, j] = self.data[load_type][algo]['resource_utilization']
                else:
                    utilization_matrix[i, j] = np.nan
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Custom colormap for utilization (0-1 range)
        colors = ['#ffffcc', '#c7e9b4', '#7fcdbb', '#41b6c4', '#2c7fb8', '#253494']
        cmap = LinearSegmentedColormap.from_list('utilization', colors, N=100)
        
        # Create heatmap
        im = ax.imshow(utilization_matrix, cmap=cmap, aspect='auto', vmin=0, vmax=1)
        
        # Set ticks and labels
        ax.set_xticks(range(len(load_labels)))
        ax.set_yticks(range(len(algorithms)))
        ax.set_xticklabels(load_labels)
        ax.set_yticklabels(algorithms)
        
        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
        plt.setp(ax.get_yticklabels(), rotation=0, ha="right")
        
        # Add text annotations
        for i in range(len(algorithms)):
            for j in range(len(load_types)):
                if not np.isnan(utilization_matrix[i, j]):
                    text = ax.text(j, i, f'{utilization_matrix[i, j]:.3f}',
                                 ha="center", va="center", color="white", fontweight='bold')
        
        # Highlight NSESche row if present
        if 'NSESche' in algorithms:
            nsesche_idx = algorithms.index('NSESche')
            for j in range(len(load_types)):
                rect = plt.Rectangle((j-0.5, nsesche_idx-0.5), 1, 1, 
                                   fill=False, edgecolor='red', linewidth=3)
                ax.add_patch(rect)
        
        ax.set_title('Resource Utilization Heatmap\n(Execution Time / Total Time)', fontweight='bold', fontsize=16)
        ax.set_xlabel('Load Type', fontweight='bold')
        ax.set_ylabel('Algorithm', fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Resource Utilization Ratio', rotation=270, labelpad=20, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'resource_utilization_heatmap.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'resource_utilization_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_overhead_analysis_heatmap(self):
        """Create overhead analysis heatmap"""
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Create subplots for different overhead metrics
        fig, axes = plt.subplots(2, 2, figsize=(16, 12))
        
        overhead_metrics = ['idle_time_ratio', 'coldstart_overhead', 'waitsche_overhead', 'container_density']
        metric_labels = ['Idle Time Ratio', 'Cold Start Overhead', 'Wait Scheduling Overhead', 'Container Density']
        subplot_labels = ['(a) Idle Time Ratio', '(b) Cold Start Overhead', 
                         '(c) Wait Scheduling Overhead', '(d) Container Density']
        
        for idx, (metric, label, subplot_label) in enumerate(zip(overhead_metrics, metric_labels, subplot_labels)):
            ax = axes[idx // 2, idx % 2]
            
            # Prepare data matrix
            metric_matrix = np.zeros((len(algorithms), len(load_types)))
            
            for i, algo in enumerate(algorithms):
                for j, load_type in enumerate(load_types):
                    if load_type in self.data and algo in self.data[load_type]:
                        metric_matrix[i, j] = self.data[load_type][algo][metric]
                    else:
                        metric_matrix[i, j] = np.nan
            
            # Choose colormap based on metric (lower is better for overhead metrics)
            if 'overhead' in metric or 'idle' in metric:
                colors = ['#2c7bb6', '#abd9e9', '#ffffcc', '#fdae61', '#d7191c']
                cmap = LinearSegmentedColormap.from_list('overhead', colors, N=100)
            else:
                colors = ['#d7191c', '#fdae61', '#ffffcc', '#abd9e9', '#2c7bb6']
                cmap = LinearSegmentedColormap.from_list('density', colors, N=100)
            
            # Create heatmap
            im = ax.imshow(metric_matrix, cmap=cmap, aspect='auto')
            
            # Set ticks and labels
            ax.set_xticks(range(len(load_labels)))
            ax.set_yticks(range(len(algorithms)))
            ax.set_xticklabels(load_labels)
            ax.set_yticklabels(algorithms)
            
            # Add text annotations
            for i in range(len(algorithms)):
                for j in range(len(load_types)):
                    if not np.isnan(metric_matrix[i, j]):
                        text = ax.text(j, i, f'{metric_matrix[i, j]:.3f}',
                                     ha="center", va="center", color="black", fontweight='bold')
            
            # Highlight NSESche row if present
            if 'NSESche' in algorithms:
                nsesche_idx = algorithms.index('NSESche')
                for j in range(len(load_types)):
                    rect = plt.Rectangle((j-0.5, nsesche_idx-0.5), 1, 1, 
                                       fill=False, edgecolor='blue', linewidth=2)
                    ax.add_patch(rect)
            
            ax.set_title(subplot_label, fontweight='bold', fontsize=14)
            ax.set_xlabel('Load Type', fontweight='bold')
            ax.set_ylabel('Algorithm', fontweight='bold')
            
            # Add colorbar
            cbar = plt.colorbar(im, ax=ax)
            cbar.set_label(label, rotation=270, labelpad=15, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'overhead_analysis_heatmap.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'overhead_analysis_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def create_container_count_heatmap(self):
        """Create container count heatmap"""
        load_types = ['rflow', 'rfmiddle', 'rfhigh']
        load_labels = [LOAD_MAPPING[lt] for lt in load_types]
        algorithms = [algo for algo in ALGORITHM_ORDER if self._algorithm_has_data(algo)]
        
        # Prepare data matrix for container count
        container_matrix = np.zeros((len(algorithms), len(load_types)))
        
        for i, algo in enumerate(algorithms):
            for j, load_type in enumerate(load_types):
                if load_type in self.data and algo in self.data[load_type]:
                    container_matrix[i, j] = self.data[load_type][algo]['fn_container_cnt']
                else:
                    container_matrix[i, j] = np.nan
        
        # Create heatmap
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Custom colormap for container count
        colors = ['#ffffb2', '#fed976', '#feb24c', '#fd8d3c', '#f03b20', '#bd0026']
        cmap = LinearSegmentedColormap.from_list('container', colors, N=100)
        
        # Create heatmap
        im = ax.imshow(container_matrix, cmap=cmap, aspect='auto')
        
        # Set ticks and labels
        ax.set_xticks(range(len(load_labels)))
        ax.set_yticks(range(len(algorithms)))
        ax.set_xticklabels(load_labels)
        ax.set_yticklabels(algorithms)
        
        # Rotate the tick labels and set their alignment
        plt.setp(ax.get_xticklabels(), rotation=0, ha="center")
        plt.setp(ax.get_yticklabels(), rotation=0, ha="right")
        
        # Add text annotations
        for i in range(len(algorithms)):
            for j in range(len(load_types)):
                if not np.isnan(container_matrix[i, j]):
                    text = ax.text(j, i, f'{container_matrix[i, j]:.1f}',
                                 ha="center", va="center", color="black", fontweight='bold')
        
        # Highlight NSESche row if present
        if 'NSESche' in algorithms:
            nsesche_idx = algorithms.index('NSESche')
            for j in range(len(load_types)):
                rect = plt.Rectangle((j-0.5, nsesche_idx-0.5), 1, 1, 
                                   fill=False, edgecolor='blue', linewidth=3)
                ax.add_patch(rect)
        
        ax.set_title('Container Count Heatmap\n(Average Number of Containers)', fontweight='bold', fontsize=16)
        ax.set_xlabel('Load Type', fontweight='bold')
        ax.set_ylabel('Algorithm', fontweight='bold')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Container Count', rotation=270, labelpad=20, fontweight='bold')
        
        plt.tight_layout()
        plt.savefig(self.output_dir / 'container_count_heatmap.pdf', dpi=300, bbox_inches='tight')
        plt.savefig(self.output_dir / 'container_count_heatmap.png', dpi=300, bbox_inches='tight')
        plt.close()
    
    def _algorithm_has_data(self, algorithm):
        """Check if algorithm has data in any load type"""
        for load_type in self.data:
            if algorithm in self.data[load_type]:
                return True
        return False

def main():
    """Main function to generate container utilization analysis"""
    analyzer = ContainerUtilizationAnalyzer()
    analyzer.load_data()
    
    print("Generating container utilization analysis...")
    
    # Create main container utilization heatmap
    analyzer.create_container_utilization_heatmap()
    print("✓ Container utilization heatmap saved")
    
    # Create resource utilization heatmap
    analyzer.create_resource_utilization_heatmap()
    print("✓ Resource utilization heatmap saved")
    
    # Create overhead analysis heatmap
    analyzer.create_overhead_analysis_heatmap()
    print("✓ Overhead analysis heatmap saved")
    
    # Create container count heatmap
    analyzer.create_container_count_heatmap()
    print("✓ Container count heatmap saved")
    
    print("All container utilization analysis plots generated successfully!")

if __name__ == '__main__':
    main()