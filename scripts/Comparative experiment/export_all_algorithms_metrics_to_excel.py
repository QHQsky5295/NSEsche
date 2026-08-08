#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
All Algorithms Metrics Export to Excel
所有算法指标导出到Excel

This script exports all algorithms' key metrics (cost-effectiveness, throughput, cost, coldstart latency)
to Excel for comprehensive comparison analysis.
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict
import re

# Load type mapping
LOAD_MAPPING = {
    'rflow': 'Low Load',
    'rfmiddle': 'Middle Load', 
    'rfhigh': 'High Load'
}

# Algorithm mapping
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

class AllAlgorithmsMetricsExporter:
    def __init__(self):
        self.data = []
        self.script_dir = Path(__file__).parent
        
    def parse_filename(self, filename):
        """Parse filename to extract load type and algorithm"""
        # Extract load type
        load_type = None
        for key in LOAD_MAPPING.keys():
            if key in filename:
                load_type = LOAD_MAPPING[key]
                break
        
        # Extract algorithm name from .scd() part
        scd_pattern = r'\.scd\(([^)]+)\)\.'
        match = re.search(scd_pattern, filename)
        if match:
            algo_key = match.group(1).rstrip('.')
            algorithm = ALGORITHM_MAPPING.get(algo_key, algo_key)
        else:
            algorithm = None
            
        return load_type, algorithm
        
    def load_data(self):
        """Load experiment data from JSON files"""
        # Try multiple possible locations for data files
        possible_dirs = [
            self.script_dir,  # Current directory
            self.script_dir / '..' / 'cache',  # Parent cache directory
            self.script_dir.parent / 'cache',  # Parent cache directory (alternative)
            Path('../cache'),  # Relative cache directory
        ]
        
        json_files = []
        for data_dir in possible_dirs:
            if data_dir.exists():
                files = list(data_dir.glob('*.json'))
                if files:
                    json_files = files
                    print(f"📁 在 {data_dir} 找到 {len(files)} 个JSON文件")
                    break
        
        if not json_files:
            print("❌ 未找到JSON数据文件")
            print("尝试查找的目录:")
            for data_dir in possible_dirs:
                print(f"  - {data_dir} (存在: {data_dir.exists()})")
            return False
            
        print(f"📁 找到 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            try:
                # Parse filename to get load type and algorithm
                load_type, algorithm = self.parse_filename(json_file.name)
                
                if load_type and algorithm:
                    # Load JSON data
                    with open(json_file, 'r', encoding='utf-8') as f:
                        metrics = json.load(f)
                    
                    # Calculate cost-effectiveness
                    cost_per_req = metrics.get('cost_per_req', 0)
                    time_per_req = metrics.get('time_per_req', 0)
                    rps = metrics.get('rps', 0)
                    
                    cost_effectiveness = cost_per_req / time_per_req if time_per_req > 0 else 0
                    
                    # Store data
                    self.data.append({
                        'Load Type': load_type,
                        'Algorithm': algorithm,
                        'Cost per Request': round(cost_per_req, 6),
                        'Average Latency (ms)': round(time_per_req, 3),
                        'Throughput (RPS)': round(rps, 2),
                        'Coldstart Latency (ms)': round(metrics.get('coldstart_time_per_req', 0), 3),
                        'Wait Schedule Time (ms)': round(metrics.get('waitsche_time_per_req', 0), 3),
                        'Execution Time (ms)': round(metrics.get('exe_time_per_req', 0), 3),
                        'Data Receive Time (ms)': round(metrics.get('datarecv_time_per_req', 0), 3),
                        'Container Count': round(metrics.get('fn_container_cnt', 0), 1),
                        'Failed Requests': metrics.get('undone_req_cnt', 0),
                        'Cost Effectiveness': round(cost_effectiveness, 8),
                        'Score': round(metrics.get('score', 0), 3)
                    })
                    
                    print(f"✓ 加载: {load_type} - {algorithm}")
                else:
                    print(f"⚠️ 无法解析文件名: {json_file.name}")
                    
            except Exception as e:
                print(f"❌ 加载文件 {json_file} 失败: {e}")
                
        return len(self.data) > 0
    
    def create_summary_statistics(self):
        """Create summary statistics for each algorithm"""
        df = pd.DataFrame(self.data)
        
        summary_stats = []
        
        for algorithm in df['Algorithm'].unique():
            algo_data = df[df['Algorithm'] == algorithm]
            
            summary_stats.append({
                'Algorithm': algorithm,
                'Avg Cost per Request': round(algo_data['Cost per Request'].mean(), 6),
                'Avg Latency (ms)': round(algo_data['Average Latency (ms)'].mean(), 3),
                'Avg Throughput (RPS)': round(algo_data['Throughput (RPS)'].mean(), 2),
                'Avg Coldstart Latency (ms)': round(algo_data['Coldstart Latency (ms)'].mean(), 3),
                'Avg Wait Schedule Time (ms)': round(algo_data['Wait Schedule Time (ms)'].mean(), 3),
                'Avg Execution Time (ms)': round(algo_data['Execution Time (ms)'].mean(), 3),
                'Avg Container Count': round(algo_data['Container Count'].mean(), 1),
                'Total Failed Requests': algo_data['Failed Requests'].sum(),
                'Avg Cost Effectiveness': round(algo_data['Cost Effectiveness'].mean(), 8),
                'Data Points': len(algo_data)
            })
        
        return summary_stats
    
    def create_load_type_analysis(self):
        """Create analysis by load type"""
        df = pd.DataFrame(self.data)
        
        load_analysis = []
        
        for load_type in df['Load Type'].unique():
            load_data = df[df['Load Type'] == load_type]
            
            # Find best performing algorithm for each metric
            best_cost = load_data.loc[load_data['Cost per Request'].idxmin()]
            best_latency = load_data.loc[load_data['Average Latency (ms)'].idxmin()]
            best_throughput = load_data.loc[load_data['Throughput (RPS)'].idxmax()]
            best_coldstart = load_data.loc[load_data['Coldstart Latency (ms)'].idxmin()]
            best_cost_eff = load_data.loc[load_data['Cost Effectiveness'].idxmin()]  # Lower is better for cost effectiveness
            
            load_analysis.append({
                'Load Type': load_type,
                'Best Cost Algorithm': best_cost['Algorithm'],
                'Best Cost Value': round(best_cost['Cost per Request'], 6),
                'Best Latency Algorithm': best_latency['Algorithm'],
                'Best Latency Value (ms)': round(best_latency['Average Latency (ms)'], 3),
                'Best Throughput Algorithm': best_throughput['Algorithm'],
                'Best Throughput Value (RPS)': round(best_throughput['Throughput (RPS)'], 2),
                'Best Coldstart Algorithm': best_coldstart['Algorithm'],
                'Best Coldstart Value (ms)': round(best_coldstart['Coldstart Latency (ms)'], 3),
                'Best Cost Effectiveness Algorithm': best_cost_eff['Algorithm'],
                'Best Cost Effectiveness Value': round(best_cost_eff['Cost Effectiveness'], 8),
                'Algorithm Count': len(load_data)
            })
        
        return load_analysis
    
    def export_to_excel(self):
        """Export all metrics to Excel file"""
        if not self.data:
            print("❌ 没有数据可导出")
            return False
        
        # Create DataFrames
        df_metrics = pd.DataFrame(self.data)
        summary_stats = self.create_summary_statistics()
        load_analysis = self.create_load_type_analysis()
        
        # Create Excel file with timestamp to avoid permission issues
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'all_algorithms_comprehensive_metrics_{timestamp}.xlsx'
        excel_path = self.script_dir / excel_filename
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # All metrics data
            df_metrics.to_excel(writer, sheet_name='All Metrics', index=False)
            
            # Summary statistics
            df_summary = pd.DataFrame(summary_stats)
            df_summary.to_excel(writer, sheet_name='Summary Statistics', index=False)
            
            # Load type analysis
            df_load_analysis = pd.DataFrame(load_analysis)
            df_load_analysis.to_excel(writer, sheet_name='Best by Load Type', index=False)
            
            # Pivot tables for easier analysis (using mean for duplicate entries)
            # Cost per Request by Load Type and Algorithm
            pivot_cost = df_metrics.groupby(['Algorithm', 'Load Type'])['Cost per Request'].mean().unstack(fill_value=0)
            pivot_cost.to_excel(writer, sheet_name='Cost by Load Type')
            
            # Throughput by Load Type and Algorithm
            pivot_throughput = df_metrics.groupby(['Algorithm', 'Load Type'])['Throughput (RPS)'].mean().unstack(fill_value=0)
            pivot_throughput.to_excel(writer, sheet_name='Throughput by Load Type')
            
            # Latency by Load Type and Algorithm
            pivot_latency = df_metrics.groupby(['Algorithm', 'Load Type'])['Average Latency (ms)'].mean().unstack(fill_value=0)
            pivot_latency.to_excel(writer, sheet_name='Latency by Load Type')
            
            # Coldstart by Load Type and Algorithm
            pivot_coldstart = df_metrics.groupby(['Algorithm', 'Load Type'])['Coldstart Latency (ms)'].mean().unstack(fill_value=0)
            pivot_coldstart.to_excel(writer, sheet_name='Coldstart by Load Type')
            
            # Cost Effectiveness by Load Type and Algorithm
            pivot_cost_eff = df_metrics.groupby(['Algorithm', 'Load Type'])['Cost Effectiveness'].mean().unstack(fill_value=0)
            pivot_cost_eff.to_excel(writer, sheet_name='Cost Effectiveness by Load Type')
        
        print(f"✅ 数据已导出到: {excel_filename}")
        print(f"📊 包含数据点: {len(self.data)} 个")
        print(f"🔍 包含算法: {len(df_summary)} 个")
        print(f"📈 包含负载类型: {len(load_analysis)} 个")
        
        # Print summary
        print("\n📋 数据概览:")
        print("-" * 80)
        print(f"{'算法':12} | {'成本':8} | {'延迟(ms)':8} | {'吞吐量':8} | {'冷启动(ms)':10} | {'数据点':6}")
        print("-" * 80)
        for stat in summary_stats:
            print(f"{stat['Algorithm']:12} | {stat['Avg Cost per Request']:.6f} | "
                  f"{stat['Avg Latency (ms)']:8.1f} | "
                  f"{stat['Avg Throughput (RPS)']:8.1f} | "
                  f"{stat['Avg Coldstart Latency (ms)']:10.1f} | "
                  f"{stat['Data Points']:6d}")
        
        return True

def main():
    """Main function to export all algorithms metrics"""
    exporter = AllAlgorithmsMetricsExporter()
    
    print("🚀 开始导出所有算法的关键指标...")
    print("="*60)
    
    # Load data
    if not exporter.load_data():
        print("❌ 数据加载失败")
        return
    
    # Export to Excel
    if exporter.export_to_excel():
        print("\n✅ 所有算法指标导出完成!")
        print("📁 Excel文件包含以下工作表:")
        print("   • All Metrics - 所有原始指标数据")
        print("   • Summary Statistics - 算法平均性能统计")
        print("   • Best by Load Type - 各负载下最佳算法")
        print("   • Cost by Load Type - 成本透视表")
        print("   • Throughput by Load Type - 吞吐量透视表")
        print("   • Latency by Load Type - 延迟透视表")
        print("   • Coldstart by Load Type - 冷启动透视表")
        print("   • Cost Effectiveness by Load Type - 性价比透视表")
    else:
        print("❌ 导出失败")

if __name__ == '__main__':
    main()