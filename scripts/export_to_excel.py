#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
实验数据Excel导出脚本
基于manage_experiment_results.py的数据解析方法，将cache文件夹中的实验数据导出到Excel文件
每个指标生成一张数据表，横坐标为算法名，纵坐标为负载级别
"""

import os
import json
import pandas as pd
from pathlib import Path
import re
from typing import Dict, List, Tuple

class ExperimentDataExporter:
    def __init__(self, cache_dir: str = "cache"):
        """
        初始化导出器
        
        Args:
            cache_dir: cache文件夹路径
        """
        self.cache_dir = Path(cache_dir)
        self.data = {}
        
        # 负载级别映射
        self.load_level_mapping = {
            'rflow': 'low',
            'rfmiddle': 'middle', 
            'rfhigh': 'high'
        }
        
        # 算法名称映射
        self.algorithm_mapping = {
            'sche_nash': 'NSESche',
            'sche_nash.': 'NSESche',
            'no_social': 'no_Social Awareness',
            'no_price': 'no_Congestion Pricing',
            'no_price.': 'no_Congestion Pricing',
            'no_heter_model': 'no_Heterogeneity Modeling',
            'no_heter_model.': 'no_Heterogeneity Modeling'
        }
        
        # 指标定义
        self.metrics = {
            'cost_per_req': '成本',
            'time_per_req': '延迟(ms)',
            'rps': '吞吐量(RPS)',
            'performance_ratio': '性价比'
        }
    
    def extract_cost_efficiency_ratio(self, data: Dict) -> float:
        """
        从JSON数据中提取性价比指标
        参考manage_experiment_results.py中的计算方法
        
        Args:
            data: JSON数据字典
            
        Returns:
            性价比值
        """
        try:
            rps = data.get('rps', 0)
            time_per_req = data.get('time_per_req', 0)
            cost_per_req = data.get('cost_per_req', 0)
            
            if time_per_req > 0 and cost_per_req > 0:
                # 性价比 = RPS / (时间 × 成本)
                performance_ratio = rps / (time_per_req * cost_per_req)
                return performance_ratio
            else:
                return 0.0
        except (KeyError, ZeroDivisionError, TypeError):
            return 0.0
    
    def extract_load_type_from_filename(self, filename: str) -> str:
        """
        从文件名中提取负载类型
        参考manage_experiment_results.py第67行的功能
        
        Args:
            filename: 文件名
            
        Returns:
            负载类型 (rflow, rfmiddle, rfhigh)
        """
        # 使用正则表达式匹配负载类型
        pattern = r'sd\.(rf\w+)\.'
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
        return 'unknown'
    
    def extract_algorithm_from_filename(self, filename: str) -> str:
        """
        从文件名中提取算法名称
        提取scd(XXX)中的XXX部分
        
        Args:
            filename: 文件名
            
        Returns:
            算法名称
        """
        # 使用正则表达式匹配scd(XXX)中的XXX部分
        pattern = r'scd\(([^)]+)\)'
        match = re.search(pattern, filename)
        if match:
            return match.group(1)
        return 'unknown'
    
    def load_data(self):
        """
        加载cache文件夹中的所有JSON数据文件
        """
        if not self.cache_dir.exists():
            print(f"❌ Cache目录不存在: {self.cache_dir}")
            return
        
        json_files = list(self.cache_dir.glob("*.json"))
        if not json_files:
            print(f"❌ 在{self.cache_dir}中没有找到JSON文件")
            return
        
        print(f"📂 找到 {len(json_files)} 个JSON文件")
        
        for json_file in json_files:
            try:
                # 从文件名提取负载类型和算法名称
                load_type = self.extract_load_type_from_filename(json_file.name)
                algorithm = self.extract_algorithm_from_filename(json_file.name)
                
                if load_type == 'unknown' or algorithm == 'unknown':
                    print(f"⚠️  跳过文件 {json_file.name}: 无法解析负载类型或算法名称")
                    continue
                
                # 读取JSON数据
                with open(json_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 计算性价比
                data['performance_ratio'] = self.extract_cost_efficiency_ratio(data)
                
                # 组织数据结构
                if load_type not in self.data:
                    self.data[load_type] = {}
                
                self.data[load_type][algorithm] = data
                
                print(f"✅ 加载: {load_type} - {algorithm}")
                
            except Exception as e:
                print(f"❌ 加载文件 {json_file.name} 时出错: {e}")
        
        print(f"\n📊 总共加载了 {sum(len(algos) for algos in self.data.values())} 条数据")
    
    def create_excel_report(self, output_file: str = "experiment_results.xlsx"):
        """
        创建Excel报告，每个指标一个工作表
        
        Args:
            output_file: 输出Excel文件名
        """
        if not self.data:
            print("❌ 没有数据可以导出")
            return
        
        # 获取所有负载级别和算法
        # 按照 low -> middle -> high 的顺序排序
        load_order = ['rflow', 'rfmiddle', 'rfhigh']
        load_levels = [load for load in load_order if load in self.data]
        all_algorithms = set()
        for load_data in self.data.values():
            all_algorithms.update(load_data.keys())
        algorithms = sorted(all_algorithms)
        
        print(f"📋 负载级别: {load_levels}")
        print(f"📋 算法: {algorithms}")
        
        # 创建Excel写入器
        with pd.ExcelWriter(output_file, engine='openpyxl') as writer:
            
            for metric_key, metric_name in self.metrics.items():
                print(f"\n📊 正在创建 {metric_name} 数据表...")
                
                # 创建数据矩阵（行列互换：算法作为行，负载级别作为列）
                data_matrix = []
                row_labels = []
                
                for algo in algorithms:
                    algo_display = self.algorithm_mapping.get(algo, algo)
                    row_labels.append(algo_display)
                    
                    row_data = []
                    for load in load_levels:
                        if load in self.data and algo in self.data[load]:
                            value = self.data[load][algo].get(metric_key, 0)
                            row_data.append(value)
                        else:
                            row_data.append(0)  # 缺失数据用0填充
                    
                    data_matrix.append(row_data)
                
                # 创建DataFrame
                col_labels = [self.load_level_mapping.get(load, load) for load in load_levels]
                df = pd.DataFrame(data_matrix, index=row_labels, columns=col_labels)
                
                # 写入Excel工作表
                sheet_name = metric_name.replace('/', '_')  # Excel工作表名不能包含特殊字符
                df.to_excel(writer, sheet_name=sheet_name, index=True)
                
                print(f"✅ {metric_name} 数据表已创建")
                
                # 打印数据预览
                print(f"📋 {metric_name} 数据预览:")
                print(df.round(4))
                print("-" * 60)
        
        print(f"\n🎉 Excel报告已生成: {output_file}")
        print(f"📁 文件路径: {os.path.abspath(output_file)}")
    
    def print_data_summary(self):
        """
        打印数据摘要
        """
        if not self.data:
            print("❌ 没有数据可以显示")
            return
        
        print("\n" + "="*80)
        print("📋 实验数据摘要")
        print("="*80)
        
        for load_level in sorted(self.data.keys()):
            load_name = self.load_level_mapping.get(load_level, load_level)
            print(f"\n🔸 {load_name} ({load_level}):")
            print("-" * 60)
            
            algorithms = sorted(self.data[load_level].keys())
            
            # 打印表头
            print(f"{'算法':<15} | {'成本':<10} | {'延迟(ms)':<10} | {'吞吐量':<10} | {'性价比':<12}")
            print("-" * 60)
            
            # 打印每个算法的数据
            for algo in algorithms:
                algo_name = self.algorithm_mapping.get(algo, algo)
                data = self.data[load_level][algo]
                
                cost = data.get('cost_per_req', 0)
                time_req = data.get('time_per_req', 0)
                rps = data.get('rps', 0)
                perf_ratio = data.get('performance_ratio', 0)
                
                print(f"{algo_name:<15} | {cost:<10.4f} | {time_req:<10.1f} | {rps:<10.3f} | {perf_ratio:<12.6f}")
        
        print("\n" + "="*80)

def main():
    """
    主函数
    """
    print("🚀 启动实验数据Excel导出脚本")
    print("="*60)
    
    # 获取脚本所在目录
    script_dir = Path(__file__).parent
    cache_dir = script_dir / "cache"
    
    # 创建导出器
    exporter = ExperimentDataExporter(cache_dir)
    
    # 加载数据
    print("\n📂 正在加载实验数据...")
    exporter.load_data()
    
    if not exporter.data:
        print("❌ 没有找到有效的实验数据")
        return
    
    # 打印数据摘要
    exporter.print_data_summary()
    
    # 生成Excel报告
    import datetime
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    output_file = script_dir / f"experiment_results_{timestamp}.xlsx"
    print(f"\n📊 正在生成Excel报告: {output_file}")
    exporter.create_excel_report(str(output_file))
    
    print("\n✅ Excel导出完成！")

if __name__ == "__main__":
    main()