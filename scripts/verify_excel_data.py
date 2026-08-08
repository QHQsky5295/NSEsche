#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证Excel数据的准确性
"""

import pandas as pd
import json
from pathlib import Path

def main():
    # 找到最新的Excel文件
    excel_files = list(Path('.').glob('experiment_results_*.xlsx'))
    if not excel_files:
        print("未找到Excel文件")
        return
    
    latest_excel = max(excel_files, key=lambda x: x.stat().st_mtime)
    print(f"检查文件: {latest_excel}")
    print("=" * 80)
    
    # 读取Excel文件
    with pd.ExcelFile(latest_excel) as xls:
        for sheet_name in xls.sheet_names:
            print(f"\n📊 {sheet_name} 工作表数据:")
            df = pd.read_excel(xls, sheet_name=sheet_name, index_col=0)
            print(df)
            print("-" * 60)
    
    # 同时检查原始JSON数据
    print("\n🔍 原始JSON数据验证:")
    print("=" * 80)
    
    cache_dir = Path("cache")
    if cache_dir.exists():
        json_files = list(cache_dir.glob("*.json"))
        
        # 按负载类型和算法分组显示
        data_by_load = {}
        
        for json_file in json_files:
            # 提取负载类型和算法
            filename = json_file.name
            
            # 提取负载类型
            if 'rflow' in filename:
                load_type = 'rflow (低负载)'
            elif 'rfmiddle' in filename:
                load_type = 'rfmiddle (中负载)'
            elif 'rfhigh' in filename:
                load_type = 'rfhigh (高负载)'
            else:
                continue
            
            # 提取算法
            if 'sche_nash.' in filename:
                algo = 'Nash Equilibrium Algorithm'
            elif 'no_social' in filename:
                algo = 'no_Social Awareness'
            elif 'no_price.' in filename:
                algo = 'no_Congestion Pricing'
            elif 'no_heter_model.' in filename:
                algo = 'no_Heterogeneity Modeling'
            else:
                continue
            
            # 读取数据
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            if load_type not in data_by_load:
                data_by_load[load_type] = {}
            
            data_by_load[load_type][algo] = {
                'cost_per_req': data.get('cost_per_req', 0),
                'time_per_req': data.get('time_per_req', 0),
                'rps': data.get('rps', 0),
                'performance_ratio': data.get('rps', 0) / (data.get('time_per_req', 1) * data.get('cost_per_req', 1)) if data.get('time_per_req', 0) > 0 and data.get('cost_per_req', 0) > 0 else 0
            }
        
        # 按顺序显示数据
        load_order = ['rflow (低负载)', 'rfmiddle (中负载)', 'rfhigh (高负载)']
        for load_type in load_order:
            if load_type in data_by_load:
                print(f"\n{load_type}:")
                for algo, metrics in data_by_load[load_type].items():
                    print(f"  {algo}:")
                    print(f"    成本: {metrics['cost_per_req']:.6f}")
                    print(f"    延迟: {metrics['time_per_req']:.4f}")
                    print(f"    吞吐量: {metrics['rps']:.3f}")
                    print(f"    性价比: {metrics['performance_ratio']:.6f}")

if __name__ == "__main__":
    main()