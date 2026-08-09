#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSESche Algorithm Improvement Verification
NSESche算法提升验证

This script verifies the claimed improvements of NSESche algorithm
compared to popular algorithms (excluding baselines) in terms of
cost-effectiveness and throughput.
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
    'sche_nash': 'NSESche'
}

# Define baseline algorithms (to be excluded from comparison)
BASELINE_ALGORITHMS = {'Greedy', 'Random', 'Hash', 'Load Balance'}

# Define popular/advanced algorithms for comparison
ADVANCED_ALGORITHMS = {'FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion'}

class NSEScheImprovementVerifier:
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
                    
                    # Calculate cost-effectiveness (cost per unit time)
                    cost_per_req = metrics.get('cost_per_req', 0)
                    time_per_req = metrics.get('time_per_req', 0)
                    rps = metrics.get('rps', 0)
                    
                    cost_effectiveness = cost_per_req / time_per_req if time_per_req > 0 else 0
                    
                    # Store data
                    self.data.append({
                        'Load Type': load_type,
                        'Algorithm': algorithm,
                        'Cost per Request': cost_per_req,
                        'Average Latency (ms)': time_per_req,
                        'Throughput (RPS)': rps,
                        'Coldstart Latency (ms)': metrics.get('coldstart_time_per_req', 0),
                        'Cost Effectiveness': cost_effectiveness
                    })
                    
            except Exception as e:
                print(f"❌ 加载文件 {json_file} 失败: {e}")
                
        return len(self.data) > 0
    
    def calculate_improvements(self):
        """Calculate NSESche improvements compared to advanced algorithms"""
        df = pd.DataFrame(self.data)
        
        # Filter data for NSESche and advanced algorithms only
        target_algorithms = ADVANCED_ALGORITHMS | {'NSESche'}
        filtered_df = df[df['Algorithm'].isin(target_algorithms)]
        
        print(f"\n🔍 分析算法: {', '.join(sorted(target_algorithms))}")
        print(f"📊 数据点: {len(filtered_df)} 个")
        
        improvements = []
        
        # Calculate improvements for each load type
        for load_type in filtered_df['Load Type'].unique():
            load_data = filtered_df[filtered_df['Load Type'] == load_type]
            
            # Get NSESche data
            nsesche_data = load_data[load_data['Algorithm'] == 'NSESche']
            if nsesche_data.empty:
                print(f"⚠️ {load_type} 下未找到NSESche数据")
                continue
                
            nsesche_cost = nsesche_data['Cost per Request'].iloc[0]
            nsesche_throughput = nsesche_data['Throughput (RPS)'].iloc[0]
            nsesche_cost_eff = nsesche_data['Cost Effectiveness'].iloc[0]
            
            # Compare with other advanced algorithms
            other_algos = load_data[load_data['Algorithm'] != 'NSESche']
            
            cost_improvements = []
            throughput_improvements = []
            cost_eff_improvements = []
            
            for _, row in other_algos.iterrows():
                algo_name = row['Algorithm']
                
                # Cost improvement (lower is better, so negative improvement means NSESche is better)
                cost_improvement = (nsesche_cost - row['Cost per Request']) / row['Cost per Request'] * 100
                cost_improvements.append(cost_improvement)
                
                # Throughput improvement (higher is better)
                throughput_improvement = (nsesche_throughput - row['Throughput (RPS)']) / row['Throughput (RPS)'] * 100
                throughput_improvements.append(throughput_improvement)
                
                # Cost effectiveness improvement (lower is better for cost/time ratio)
                cost_eff_improvement = (nsesche_cost_eff - row['Cost Effectiveness']) / row['Cost Effectiveness'] * 100
                cost_eff_improvements.append(cost_eff_improvement)
                
                print(f"  {load_type} - {algo_name}:")
                print(f"    成本改善: {cost_improvement:+.1f}%")
                print(f"    吞吐量改善: {throughput_improvement:+.1f}%")
                print(f"    性价比改善: {cost_eff_improvement:+.1f}%")
            
            # Calculate average improvements for this load type
            avg_cost_improvement = np.mean(cost_improvements)
            avg_throughput_improvement = np.mean(throughput_improvements)
            avg_cost_eff_improvement = np.mean(cost_eff_improvements)
            
            improvements.append({
                'Load Type': load_type,
                'NSESche Cost': nsesche_cost,
                'NSESche Throughput': nsesche_throughput,
                'NSESche Cost Effectiveness': nsesche_cost_eff,
                'Avg Cost Improvement (%)': avg_cost_improvement,
                'Avg Throughput Improvement (%)': avg_throughput_improvement,
                'Avg Cost Effectiveness Improvement (%)': avg_cost_eff_improvement,
                'Compared Algorithms Count': len(other_algos)
            })
            
            print(f"\n📈 {load_type} 平均改善:")
            print(f"  成本: {avg_cost_improvement:+.1f}%")
            print(f"  吞吐量: {avg_throughput_improvement:+.1f}%")
            print(f"  性价比: {avg_cost_eff_improvement:+.1f}%")
        
        return improvements
    
    def calculate_overall_improvements(self, improvements):
        """Calculate overall average improvements across all load types"""
        if not improvements:
            return None
            
        df_improvements = pd.DataFrame(improvements)
        
        overall_cost_improvement = df_improvements['Avg Cost Improvement (%)'].mean()
        overall_throughput_improvement = df_improvements['Avg Throughput Improvement (%)'].mean()
        overall_cost_eff_improvement = df_improvements['Avg Cost Effectiveness Improvement (%)'].mean()
        
        return {
            'Overall Avg Cost Improvement (%)': overall_cost_improvement,
            'Overall Avg Throughput Improvement (%)': overall_throughput_improvement,
            'Overall Avg Cost Effectiveness Improvement (%)': overall_cost_eff_improvement,
            'Total Load Types': len(improvements)
        }
    
    def export_verification_results(self, improvements, overall):
        """Export verification results to Excel"""
        import datetime
        timestamp = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
        excel_filename = f'nsesche_improvement_verification_{timestamp}.xlsx'
        excel_path = self.script_dir / excel_filename
        
        with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
            # Detailed improvements by load type
            df_improvements = pd.DataFrame(improvements)
            df_improvements.to_excel(writer, sheet_name='Improvements by Load Type', index=False)
            
            # Overall summary
            if overall:
                df_overall = pd.DataFrame([overall])
                df_overall.to_excel(writer, sheet_name='Overall Summary', index=False)
            
            # Raw data for reference
            df_raw = pd.DataFrame(self.data)
            target_algorithms = ADVANCED_ALGORITHMS | {'NSESche'}
            df_filtered = df_raw[df_raw['Algorithm'].isin(target_algorithms)]
            df_filtered.to_excel(writer, sheet_name='Raw Data', index=False)
        
        print(f"\n✅ 验证结果已导出到: {excel_filename}")
        return excel_path
    
    def verify_claims(self):
        """Main verification function"""
        print("🔍 NSESche算法改善验证分析")
        print("="*60)
        
        # Load data
        if not self.load_data():
            print("❌ 数据加载失败")
            return False
        
        # Calculate improvements
        improvements = self.calculate_improvements()
        if not improvements:
            print("❌ 无法计算改善数据")
            return False
        
        # Calculate overall improvements
        overall = self.calculate_overall_improvements(improvements)
        
        # Print summary
        print("\n" + "="*60)
        print("📊 NSESche vs 先进算法 总体改善分析")
        print("="*60)
        
        if overall:
            print(f"🏆 总体平均改善 (相较于 {', '.join(ADVANCED_ALGORITHMS)}):")
            print(f"  💰 成本改善: {overall['Overall Avg Cost Improvement (%)']:+.1f}%")
            print(f"  🚀 吞吐量改善: {overall['Overall Avg Throughput Improvement (%)']:+.1f}%")
            print(f"  📈 性价比改善: {overall['Overall Avg Cost Effectiveness Improvement (%)']:+.1f}%")
            print(f"  📋 分析负载类型: {overall['Total Load Types']} 个")
            
            # Verification conclusion
            print("\n🎯 验证结论:")
            cost_claim_valid = overall['Overall Avg Cost Improvement (%)'] < -20  # At least 20% cost reduction
            throughput_claim_valid = overall['Overall Avg Throughput Improvement (%)'] > 10  # At least 10% throughput increase
            
            print(f"  成本优势声明: {'✅ 属实' if cost_claim_valid else '❌ 不符'}")
            print(f"  吞吐量优势声明: {'✅ 属实' if throughput_claim_valid else '❌ 不符'}")
            
            if cost_claim_valid and throughput_claim_valid:
                print("  🏆 总体结论: NSESche算法的性价比和吞吐量优势声明属实")
            else:
                print("  ⚠️ 总体结论: 部分声明需要进一步验证")
        
        # Export results
        self.export_verification_results(improvements, overall)
        
        return True

def main():
    """Main function"""
    verifier = NSEScheImprovementVerifier()
    verifier.verify_claims()

if __name__ == '__main__':
    main()