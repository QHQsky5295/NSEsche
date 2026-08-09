#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Motivation实验脚本
使用OpenFaaS仿真平台运行motivation实验
"""

import os
import sys
import time
import warnings
warnings.filterwarnings('ignore')

# 设置英文字体
import matplotlib
matplotlib.use('Agg')  # 使用非交互式后端
import matplotlib.pyplot as plt
plt.rcParams['font.family'] = 'Times New Roman'
plt.rcParams['font.size'] = 14
plt.rcParams['axes.labelsize'] = 16
plt.rcParams['axes.titlesize'] = 18
plt.rcParams['xtick.labelsize'] = 14
plt.rcParams['ytick.labelsize'] = 14
plt.rcParams['legend.fontsize'] = 14
plt.rcParams['figure.titlesize'] = 20

# 导入OpenFaaS仿真器
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from openfaas_simulator import OpenFaaSMotivationExperiments

def main():
    """主函数"""
    print("Starting OpenFaaS Motivation Experiments...")
    print("This will generate 2 key figures proving the theoretical problems exist.")
    
    # 创建实验对象
    experiments = OpenFaaSMotivationExperiments()
    
    # 运行所有实验
    experiments.run_all_experiments()
    
    print("\n=== Summary ===")
    print("Generated figures:")
    print("1. experiment1_resource_competition.png - Negative externalities from resource competition")
    print("2. experiment2_preference_conflicts.png - Heterogeneous scheduling preference conflicts")
    print("\nAll figures use English labels and industry-standard performance metrics.")
    print("The experiments validate the theoretical problems using realistic cloud environment simulation.")

if __name__ == "__main__":
    main() 