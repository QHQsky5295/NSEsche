#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSESche Performance Improvement Range Calculator
NSESche算法性价比和吞吐量提升区间计算器

This script calculates the specific improvement ranges of NSESche algorithm
compared to other algorithms in terms of cost-effectiveness and throughput.
"""

import json
import numpy as np
from pathlib import Path
from collections import defaultdict

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

class NSEScheImprovementCalculator:
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
                
                self.data[load_type][algorithm] = metrics
                
            except Exception as e:
                print(f"Error processing {json_file}: {e}")
                continue
    
    def calculate_cost_effectiveness_improvements(self):
        """Calculate cost-effectiveness improvement ranges (advanced algorithms only)"""
        cost_improvements = []
        
        # Define advanced algorithms to compare against
        advanced_algorithms = {'FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion'}
        
        for load_type in self.data:
            if 'NSESche' not in self.data[load_type]:
                continue
                
            nsesche_data = self.data[load_type]['NSESche']
            load_label = LOAD_MAPPING[load_type]
            
            # Cost per request metric
            if 'cost_per_req' in nsesche_data:
                nsesche_cost = nsesche_data['cost_per_req']
                
                for algo, algo_data in self.data[load_type].items():
                    if algo == 'NSESche' or 'cost_per_req' not in algo_data:
                        continue
                    
                    # Only compare with advanced algorithms
                    if algo not in advanced_algorithms:
                        continue
                        
                    algo_cost = algo_data['cost_per_req']
                    if algo_cost > 0:
                        improvement = ((algo_cost - nsesche_cost) / algo_cost) * 100
                        # Include all comparisons, even when NSESche performs worse
                        cost_improvements.append({
                            'load_type': load_label,
                            'algorithm': algo,
                            'improvement': improvement,
                            'nsesche_value': nsesche_cost,
                            'algo_value': algo_cost
                        })
        
        return cost_improvements
    
    def calculate_throughput_improvements(self):
        """Calculate throughput improvement ranges (advanced algorithms only)"""
        throughput_improvements = []
        
        # Define advanced algorithms to compare against
        advanced_algorithms = {'FaasRank', 'OCS', 'Hiku', 'Jiagu', 'Orion'}
        
        for load_type in self.data:
            if 'NSESche' not in self.data[load_type]:
                continue
                
            nsesche_data = self.data[load_type]['NSESche']
            load_label = LOAD_MAPPING[load_type]
            
            # Requests per second metric
            if 'rps' in nsesche_data:
                nsesche_rps = nsesche_data['rps']
                
                for algo, algo_data in self.data[load_type].items():
                    if algo == 'NSESche' or 'rps' not in algo_data:
                        continue
                    
                    # Only compare with advanced algorithms
                    if algo not in advanced_algorithms:
                        continue
                        
                    algo_rps = algo_data['rps']
                    if algo_rps > 0:
                        improvement = ((nsesche_rps - algo_rps) / algo_rps) * 100
                        # Include all comparisons, even when NSESche performs worse
                        throughput_improvements.append({
                            'load_type': load_label,
                            'algorithm': algo,
                            'improvement': improvement,
                            'nsesche_value': nsesche_rps,
                            'algo_value': algo_rps
                        })
        
        return throughput_improvements
    
    def analyze_improvement_ranges(self):
        """Analyze and summarize improvement ranges"""
        cost_improvements = self.calculate_cost_effectiveness_improvements()
        throughput_improvements = self.calculate_throughput_improvements()
        
        print("="*80)
        print("🚀 NSESche算法相较于先进算法的性价比和吞吐量提升区间分析")
        print("="*80)
        
        # Cost-effectiveness analysis
        if cost_improvements:
            print("\n💰 性价比提升分析 (相较于先进算法)")
            print("-"*60)
            
            cost_values = [item['improvement'] for item in cost_improvements]
            min_cost_improvement = min(cost_values)
            max_cost_improvement = max(cost_values)
            avg_cost_improvement = np.mean(cost_values)
            
            print(f"📊 总体提升区间: {min_cost_improvement:.1f}% - {max_cost_improvement:.1f}%")
            print(f"📈 平均提升幅度: {avg_cost_improvement:.1f}%")
            print(f"📋 有效对比数量: {len(cost_improvements)} 个算法对比")
            
            # By load type
            print("\n按负载类型分析:")
            for load_type in ['Low Load', 'Middle Load', 'High Load']:
                load_improvements = [item for item in cost_improvements if item['load_type'] == load_type]
                if load_improvements:
                    load_values = [item['improvement'] for item in load_improvements]
                    load_min = min(load_values)
                    load_max = max(load_values)
                    load_avg = np.mean(load_values)
                    print(f"  • {load_type}: {load_min:.1f}% - {load_max:.1f}% (平均: {load_avg:.1f}%)")
            
            # Top improvements
            print("\n🏆 最显著的性价比提升:")
            top_cost = sorted(cost_improvements, key=lambda x: x['improvement'], reverse=True)[:5]
            for i, item in enumerate(top_cost, 1):
                print(f"  {i}. {item['load_type']} vs {item['algorithm']}: {item['improvement']:.1f}%")
        
        # Throughput analysis
        if throughput_improvements:
            print("\n🚄 吞吐量提升分析 (相较于先进算法)")
            print("-"*60)
            
            throughput_values = [item['improvement'] for item in throughput_improvements]
            min_throughput_improvement = min(throughput_values)
            max_throughput_improvement = max(throughput_values)
            avg_throughput_improvement = np.mean(throughput_values)
            
            print(f"📊 总体提升区间: {min_throughput_improvement:.1f}% - {max_throughput_improvement:.1f}%")
            print(f"📈 平均提升幅度: {avg_throughput_improvement:.1f}%")
            print(f"📋 有效对比数量: {len(throughput_improvements)} 个算法对比")
            
            # By load type
            print("\n按负载类型分析:")
            for load_type in ['Low Load', 'Middle Load', 'High Load']:
                load_improvements = [item for item in throughput_improvements if item['load_type'] == load_type]
                if load_improvements:
                    load_values = [item['improvement'] for item in load_improvements]
                    load_min = min(load_values)
                    load_max = max(load_values)
                    load_avg = np.mean(load_values)
                    print(f"  • {load_type}: {load_min:.1f}% - {load_max:.1f}% (平均: {load_avg:.1f}%)")
            
            # Top improvements
            print("\n🏆 最显著的吞吐量提升:")
            top_throughput = sorted(throughput_improvements, key=lambda x: x['improvement'], reverse=True)[:5]
            for i, item in enumerate(top_throughput, 1):
                print(f"  {i}. {item['load_type']} vs {item['algorithm']}: {item['improvement']:.1f}%")
        
        # Summary
        print("\n" + "="*80)
        print("📋 总结")
        print("="*80)
        
        if cost_improvements and throughput_improvements:
            print(f"🎯 NSESche算法在性价比方面的提升区间: {min_cost_improvement:.1f}% - {max_cost_improvement:.1f}%")
            print(f"🎯 NSESche算法在吞吐量方面的提升区间: {min_throughput_improvement:.1f}% - {max_throughput_improvement:.1f}%")
            
            print(f"\n💡 关键发现:")
            print(f"   • 性价比平均提升: {avg_cost_improvement:.1f}%")
            print(f"   • 吞吐量平均提升: {avg_throughput_improvement:.1f}%")
            print(f"   • 总计有效对比: {len(cost_improvements) + len(throughput_improvements)} 项")
        
        return {
            'cost_effectiveness': {
                'range': (min_cost_improvement, max_cost_improvement) if cost_improvements else None,
                'average': avg_cost_improvement if cost_improvements else None,
                'count': len(cost_improvements)
            },
            'throughput': {
                'range': (min_throughput_improvement, max_throughput_improvement) if throughput_improvements else None,
                'average': avg_throughput_improvement if throughput_improvements else None,
                'count': len(throughput_improvements)
            }
        }

def main():
    """Main function to calculate improvement ranges"""
    calculator = NSEScheImprovementCalculator()
    calculator.load_data()
    
    print("正在计算NSESche算法的性价比和吞吐量提升区间...\n")
    
    # Calculate and display improvement ranges
    results = calculator.analyze_improvement_ranges()
    
    return results

if __name__ == '__main__':
    main()