#!/usr/bin/env python3
"""
Export NSESche vs Advanced Algorithms Comparison to Excel
导出NSESche算法与先进算法对比数据到Excel表格
"""

import json
import pandas as pd
import numpy as np
from pathlib import Path
from collections import defaultdict

# Load type mapping
LOAD_MAPPING = {
    'rflow': 'Low Load',
    'rfmiddle': 'Middle Load', 
    'rfhigh': 'High Load'
}

# Algorithm name mapping
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

class NSEScheComparisonExporter:
    def __init__(self, cache_dir='../cache'):
        self.cache_dir = Path(cache_dir)
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
                
                self.data[load_type][algorithm] = {
                    'cost_per_req': metrics.get('cost_per_req', 0),
                    'rps': metrics.get('rps', 0),
                    'avg_latency': metrics.get('avg_latency', 0),
                    'total_cost': metrics.get('total_cost', 0)
                }
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
    
    def create_comparison_tables(self):
        """Create comparison tables for cost-effectiveness and throughput"""
        # Define advanced algorithms to compare against
        advanced_algorithms = {'FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion'}
        
        # Prepare data for Excel export
        cost_effectiveness_data = []
        throughput_data = []
        raw_metrics_data = []
        
        for load_type in self.data:
            if 'NSESche' not in self.data[load_type]:
                continue
                
            nsesche_data = self.data[load_type]['NSESche']
            load_label = LOAD_MAPPING[load_type]
            
            # Add raw metrics data
            raw_metrics_data.append({
                'Load Type': load_label,
                'Algorithm': 'NSESche',
                'Cost per Request': nsesche_data['cost_per_req'],
                'Requests per Second (RPS)': nsesche_data['rps'],
                'Average Latency': nsesche_data['avg_latency'],
                'Total Cost': nsesche_data['total_cost']
            })
            
            for algo, algo_data in self.data[load_type].items():
                if algo == 'NSESche' or algo not in advanced_algorithms:
                    continue
                
                # Add raw metrics for advanced algorithms
                raw_metrics_data.append({
                    'Load Type': load_label,
                    'Algorithm': algo,
                    'Cost per Request': algo_data['cost_per_req'],
                    'Requests per Second (RPS)': algo_data['rps'],
                    'Average Latency': algo_data['avg_latency'],
                    'Total Cost': algo_data['total_cost']
                })
                
                # Cost-effectiveness comparison
                if 'cost_per_req' in nsesche_data and 'cost_per_req' in algo_data:
                    nsesche_cost = nsesche_data['cost_per_req']
                    algo_cost = algo_data['cost_per_req']
                    
                    if algo_cost > 0:
                        improvement = ((algo_cost - nsesche_cost) / algo_cost) * 100
                        cost_effectiveness_data.append({
                            'Load Type': load_label,
                            'Compared Algorithm': algo,
                            'NSESche Cost per Request': round(nsesche_cost, 6),
                            'Compared Algorithm Cost per Request': round(algo_cost, 6),
                            'Cost Difference (Absolute)': round(algo_cost - nsesche_cost, 6),
                            'Cost Effectiveness Improvement (%)': round(improvement, 2),
                            'NSESche Total Cost': round(nsesche_data.get('total_cost', 0), 2),
                            'Compared Algorithm Total Cost': round(algo_data.get('total_cost', 0), 2),
                            'NSESche Avg Latency': round(nsesche_data.get('avg_latency', 0), 3),
                            'Compared Algorithm Avg Latency': round(algo_data.get('avg_latency', 0), 3),
                            'NSESche Better': 'Yes' if improvement > 0 else 'No'
                        })
                
                # Throughput comparison
                if 'rps' in nsesche_data and 'rps' in algo_data:
                    nsesche_rps = nsesche_data['rps']
                    algo_rps = algo_data['rps']
                    
                    if algo_rps > 0:
                        improvement = ((nsesche_rps - algo_rps) / algo_rps) * 100
                        throughput_data.append({
                            'Load Type': load_label,
                            'Compared Algorithm': algo,
                            'NSESche RPS': round(nsesche_rps, 2),
                            'Compared Algorithm RPS': round(algo_rps, 2),
                            'RPS Difference (Absolute)': round(nsesche_rps - algo_rps, 2),
                            'Throughput Improvement (%)': round(improvement, 2),
                            'NSESche Cost per Request': round(nsesche_data.get('cost_per_req', 0), 6),
                            'Compared Algorithm Cost per Request': round(algo_data.get('cost_per_req', 0), 6),
                            'NSESche Avg Latency': round(nsesche_data.get('avg_latency', 0), 3),
                            'Compared Algorithm Avg Latency': round(algo_data.get('avg_latency', 0), 3),
                            'NSESche Better': 'Yes' if improvement > 0 else 'No'
                        })
        
        return cost_effectiveness_data, throughput_data, raw_metrics_data
    
    def export_to_excel(self, output_file='nsesche_vs_advanced_algorithms_comparison.xlsx'):
        """Export comparison data to Excel file"""
        cost_data, throughput_data, raw_data = self.create_comparison_tables()
        
        # Create DataFrames
        cost_df = pd.DataFrame(cost_data)
        throughput_df = pd.DataFrame(throughput_data)
        raw_df = pd.DataFrame(raw_data)
        
        # Calculate summary statistics
        summary_data = []
        
        if not cost_df.empty:
            cost_improvements = cost_df['Cost Effectiveness Improvement (%)'].values
            summary_data.append({
                'Metric': 'Cost Effectiveness',
                'Average Improvement (%)': round(np.mean(cost_improvements), 2),
                'Min Improvement (%)': round(np.min(cost_improvements), 2),
                'Max Improvement (%)': round(np.max(cost_improvements), 2),
                'Positive Cases': len(cost_improvements[cost_improvements > 0]),
                'Total Cases': len(cost_improvements)
            })
        
        if not throughput_df.empty:
            throughput_improvements = throughput_df['Throughput Improvement (%)'].values
            summary_data.append({
                'Metric': 'Throughput',
                'Average Improvement (%)': round(np.mean(throughput_improvements), 2),
                'Min Improvement (%)': round(np.min(throughput_improvements), 2),
                'Max Improvement (%)': round(np.max(throughput_improvements), 2),
                'Positive Cases': len(throughput_improvements[throughput_improvements > 0]),
                'Total Cases': len(throughput_improvements)
            })
        
        summary_df = pd.DataFrame(summary_data)
        
        # Write to Excel with multiple sheets
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            # Summary sheet
            summary_df.to_excel(writer, sheet_name='Summary', index=False)
            
            # Raw metrics sheet
            raw_df.to_excel(writer, sheet_name='Raw Metrics', index=False)
            
            # Cost effectiveness comparison
            cost_df.to_excel(writer, sheet_name='Cost Effectiveness', index=False)
            
            # Throughput comparison
            throughput_df.to_excel(writer, sheet_name='Throughput', index=False)
            
            # Format the sheets
            for sheet_name in writer.sheets:
                worksheet = writer.sheets[sheet_name]
                
                # Auto-adjust column widths
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width
        
        print(f"✅ Excel文件已导出: {output_file}")
        print(f"📊 包含 {len(cost_data)} 个性价比对比和 {len(throughput_data)} 个吞吐量对比")
        
        return output_file

def main():
    print("正在导出NSESche算法与先进算法对比数据到Excel...")
    
    exporter = NSEScheComparisonExporter()
    exporter.load_data()
    
    if not exporter.data:
        print("❌ 未找到实验数据文件")
        return
    
    output_file = exporter.export_to_excel()
    print(f"\n🎉 导出完成! 文件保存为: {output_file}")
    print("\n📋 Excel文件包含以下工作表:")
    print("  • Summary: 总体统计摘要")
    print("  • Raw Metrics: 原始指标数据")
    print("  • Cost Effectiveness: 性价比对比详情")
    print("  • Throughput: 吞吐量对比详情")

if __name__ == '__main__':
    main()