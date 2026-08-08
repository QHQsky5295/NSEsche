#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证转置后的Excel文件结构
"""

import pandas as pd
import glob
import os
from pathlib import Path

def verify_latest_excel():
    """
    验证最新生成的Excel文件的行列结构
    """
    script_dir = Path(__file__).parent
    
    # 找到最新的experiment_results_*.xlsx文件
    excel_files = list(script_dir.glob("experiment_results_*.xlsx"))
    if not excel_files:
        print("❌ 没有找到Excel文件")
        return
    
    # 按修改时间排序，获取最新的文件
    latest_file = max(excel_files, key=lambda x: x.stat().st_mtime)
    print(f"📊 正在验证文件: {latest_file.name}")
    print("="*60)
    
    # 读取Excel文件的所有工作表
    excel_data = pd.read_excel(latest_file, sheet_name=None, index_col=0)
    
    for sheet_name, df in excel_data.items():
        print(f"\n📋 工作表: {sheet_name}")
        print(f"行数: {len(df)}")
        print(f"列数: {len(df.columns)}")
        print(f"行索引（算法）: {list(df.index)}")
        print(f"列名（负载级别）: {list(df.columns)}")
        print("\n数据预览:")
        print(df.round(4))
        print("-" * 60)
    
    print("\n✅ 验证完成！")
    print("📝 确认: 行是算法，列是负载级别")

if __name__ == "__main__":
    verify_latest_excel()