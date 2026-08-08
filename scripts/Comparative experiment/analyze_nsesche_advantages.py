#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NSESche Algorithm Advantage Analysis
NSESche算法优势分析

This script analyzes all generated charts to identify where NSESche algorithm shows advantages.
"""

import json
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.image as mpimg
from pathlib import Path
import pandas as pd
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

class NSEScheAdvantageAnalyzer:
    def __init__(self, cache_dir='../cache', output_dir='.'):
        self.cache_dir = Path(cache_dir)
        self.output_dir = Path(output_dir)
        self.data = {}
        self.analysis_results = {}
        
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
    
    def analyze_performance_metrics(self):
        """Analyze key performance metrics where NSESche shows advantages"""
        metrics_analysis = {
            'latency': {'metric': 'time_per_req', 'better': 'lower', 'advantages': []},
            'cost': {'metric': 'cost_per_req', 'better': 'lower', 'advantages': []},
            'throughput': {'metric': 'rps', 'better': 'higher', 'advantages': []},
            'failure_rate': {'metric': 'undone_req_cnt', 'better': 'lower', 'advantages': []},
            'coldstart_time': {'metric': 'coldstart_time_per_req', 'better': 'lower', 'advantages': []},
            'wait_scheduling_time': {'metric': 'waitsche_time_per_req', 'better': 'lower', 'advantages': []},
            'execution_time': {'metric': 'exe_time_per_req', 'better': 'lower', 'advantages': []},
            'container_count': {'metric': 'fn_container_cnt', 'better': 'lower', 'advantages': []}
        }
        
        for load_type in self.data:
            if 'NSESche' not in self.data[load_type]:
                continue
                
            nsesche_data = self.data[load_type]['NSESche']
            load_label = LOAD_MAPPING[load_type]
            
            for metric_name, metric_info in metrics_analysis.items():
                metric_key = metric_info['metric']
                if metric_key not in nsesche_data:
                    continue
                    
                nsesche_value = nsesche_data[metric_key]
                better_than_count = 0
                total_algorithms = 0
                
                comparisons = []
                
                for algo, algo_data in self.data[load_type].items():
                    if algo == 'NSESche' or metric_key not in algo_data:
                        continue
                        
                    total_algorithms += 1
                    algo_value = algo_data[metric_key]
                    
                    if metric_info['better'] == 'lower':
                        is_better = nsesche_value < algo_value
                        improvement = ((algo_value - nsesche_value) / algo_value * 100) if algo_value > 0 else 0
                    else:
                        is_better = nsesche_value > algo_value
                        improvement = ((nsesche_value - algo_value) / algo_value * 100) if algo_value > 0 else 0
                    
                    if is_better:
                        better_than_count += 1
                        comparisons.append({
                            'algorithm': algo,
                            'nsesche_value': nsesche_value,
                            'algo_value': algo_value,
                            'improvement': improvement
                        })
                
                if total_algorithms > 0:
                    advantage_ratio = better_than_count / total_algorithms
                    if advantage_ratio >= 0.5:  # NSESche is better than at least 50% of algorithms
                        metrics_analysis[metric_name]['advantages'].append({
                            'load_type': load_label,
                            'advantage_ratio': advantage_ratio,
                            'better_than_count': better_than_count,
                            'total_algorithms': total_algorithms,
                            'nsesche_value': nsesche_value,
                            'comparisons': comparisons
                        })
        
        return metrics_analysis
    
    def analyze_chart_advantages(self):
        """Analyze which charts show NSESche advantages"""
        chart_advantages = {
            'failure_rate_analysis': {
                'charts': ['failure_rate_heatmap.png', 'detailed_failure_analysis.png'],
                'advantages': [],
                'recommendation': 'unknown'
            },
            'cost_efficiency_analysis': {
                'charts': ['cost_efficiency_boxplots.png', 'cost_efficiency_by_load.png', 'cost_distribution_analysis.png'],
                'advantages': [],
                'recommendation': 'unknown'
            },
            'container_utilization_analysis': {
                'charts': ['container_utilization_heatmap.png', 'resource_utilization_heatmap.png', 
                          'overhead_analysis_heatmap.png', 'container_count_heatmap.png'],
                'advantages': [],
                'recommendation': 'unknown'
            }
        }
        
        metrics_analysis = self.analyze_performance_metrics()
        
        # Analyze failure rate advantages
        failure_metrics = ['failure_rate', 'throughput']
        failure_advantages = []
        for metric in failure_metrics:
            if metrics_analysis[metric]['advantages']:
                failure_advantages.extend(metrics_analysis[metric]['advantages'])
        
        if failure_advantages:
            chart_advantages['failure_rate_analysis']['advantages'] = failure_advantages
            chart_advantages['failure_rate_analysis']['recommendation'] = 'keep'
        else:
            chart_advantages['failure_rate_analysis']['recommendation'] = 'consider_removing'
        
        # Analyze cost efficiency advantages
        cost_metrics = ['cost', 'latency', 'throughput']
        cost_advantages = []
        for metric in cost_metrics:
            if metrics_analysis[metric]['advantages']:
                cost_advantages.extend(metrics_analysis[metric]['advantages'])
        
        if cost_advantages:
            chart_advantages['cost_efficiency_analysis']['advantages'] = cost_advantages
            chart_advantages['cost_efficiency_analysis']['recommendation'] = 'keep'
        else:
            chart_advantages['cost_efficiency_analysis']['recommendation'] = 'consider_removing'
        
        # Analyze container utilization advantages
        container_metrics = ['container_count', 'coldstart_time', 'wait_scheduling_time', 'execution_time']
        container_advantages = []
        for metric in container_metrics:
            if metrics_analysis[metric]['advantages']:
                container_advantages.extend(metrics_analysis[metric]['advantages'])
        
        if container_advantages:
            chart_advantages['container_utilization_analysis']['advantages'] = container_advantages
            chart_advantages['container_utilization_analysis']['recommendation'] = 'keep'
        else:
            chart_advantages['container_utilization_analysis']['recommendation'] = 'consider_removing'
        
        return chart_advantages, metrics_analysis
    
    def generate_advantage_report(self):
        """Generate comprehensive advantage analysis report"""
        chart_advantages, metrics_analysis = self.analyze_chart_advantages()
        
        report = []
        report.append("# NSESche算法优势分析报告\n")
        report.append("## 📊 图表保留建议\n")
        
        # Chart recommendations
        for category, info in chart_advantages.items():
            category_name = {
                'failure_rate_analysis': '请求失败率分析',
                'cost_efficiency_analysis': '成本效率分析', 
                'container_utilization_analysis': '容器利用率分析'
            }[category]
            
            if info['recommendation'] == 'keep':
                report.append(f"### ✅ {category_name} - **推荐保留**\n")
                report.append(f"**相关图表:** {', '.join(info['charts'])}\n")
                report.append("**NSESche优势:**\n")
                
                for advantage in info['advantages']:
                    load_type = advantage['load_type']
                    ratio = advantage['advantage_ratio']
                    better_count = advantage['better_than_count']
                    total_count = advantage['total_algorithms']
                    report.append(f"- {load_type}: 优于 {better_count}/{total_count} 个算法 ({ratio:.1%})\n")
                    
                    # Show top improvements
                    if 'comparisons' in advantage:
                        top_improvements = sorted(advantage['comparisons'], 
                                                key=lambda x: x['improvement'], reverse=True)[:3]
                        for comp in top_improvements:
                            report.append(f"  - 比{comp['algorithm']}提升 {comp['improvement']:.1f}%\n")
                report.append("\n")
            else:
                report.append(f"### ⚠️ {category_name} - **考虑移除**\n")
                report.append(f"**相关图表:** {', '.join(info['charts'])}\n")
                report.append("**原因:** NSESche在此类指标上未显示明显优势\n\n")
        
        # Detailed metric analysis
        report.append("## 📈 详细指标分析\n")
        
        for metric_name, metric_info in metrics_analysis.items():
            if metric_info['advantages']:
                metric_display = {
                    'latency': '延迟时间',
                    'cost': '成本',
                    'throughput': '吞吐量',
                    'failure_rate': '失败率',
                    'coldstart_time': '冷启动时间',
                    'wait_scheduling_time': '调度等待时间',
                    'execution_time': '执行时间',
                    'container_count': '容器数量'
                }[metric_name]
                
                report.append(f"### {metric_display}\n")
                
                for advantage in metric_info['advantages']:
                    report.append(f"**{advantage['load_type']}:**\n")
                    report.append(f"- NSESche值: {advantage['nsesche_value']:.3f}\n")
                    report.append(f"- 优于算法数: {advantage['better_than_count']}/{advantage['total_algorithms']}\n")
                    
                    if 'comparisons' in advantage and advantage['comparisons']:
                        avg_improvement = np.mean([c['improvement'] for c in advantage['comparisons']])
                        report.append(f"- 平均提升: {avg_improvement:.1f}%\n")
                    report.append("\n")
        
        # Summary recommendations
        report.append("## 🎯 总结建议\n")
        
        keep_charts = []
        remove_charts = []
        
        for category, info in chart_advantages.items():
            if info['recommendation'] == 'keep':
                keep_charts.extend(info['charts'])
            else:
                remove_charts.extend(info['charts'])
        
        if keep_charts:
            report.append("### 推荐保留的图表:\n")
            for chart in keep_charts:
                report.append(f"- {chart}\n")
            report.append("\n")
        
        if remove_charts:
            report.append("### 可考虑移除的图表:\n")
            for chart in remove_charts:
                report.append(f"- {chart}\n")
            report.append("\n")
        
        report.append("### 核心优势总结:\n")
        strong_metrics = [name for name, info in metrics_analysis.items() if len(info['advantages']) >= 2]
        if strong_metrics:
            report.append("NSESche在以下指标上表现突出:\n")
            for metric in strong_metrics:
                metric_display = {
                    'latency': '延迟时间',
                    'cost': '成本',
                    'throughput': '吞吐量',
                    'failure_rate': '失败率',
                    'coldstart_time': '冷启动时间',
                    'wait_scheduling_time': '调度等待时间',
                    'execution_time': '执行时间',
                    'container_count': '容器数量'
                }[metric]
                report.append(f"- {metric_display}\n")
        
        return ''.join(report)
    
    def save_analysis_report(self):
        """Save the analysis report to file"""
        report = self.generate_advantage_report()
        
        # Save as markdown
        with open(self.output_dir / 'nsesche_advantage_analysis.md', 'w', encoding='utf-8') as f:
            f.write(report)
        
        # Also print to console
        print(report)
        
        return report

def main():
    """Main function to analyze NSESche advantages"""
    analyzer = NSEScheAdvantageAnalyzer()
    analyzer.load_data()
    
    print("正在分析NSESche算法优势...\n")
    
    # Generate and save analysis report
    report = analyzer.save_analysis_report()
    
    print("\n✓ 分析报告已保存为 'nsesche_advantage_analysis.md'")
    print("\n" + "="*60)
    print("分析完成！请查看上述报告了解NSESche算法的优势表现。")

if __name__ == '__main__':
    main()