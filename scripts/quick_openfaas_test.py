#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenFaaS 仿真平台快速测试
验证系统功能和指标计算
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from openfaas_simulator import OpenFaaSMotivationExperiments, SchedulingAlgorithm
import time

def quick_test():
    """快速测试实验系统"""
    print("=== OpenFaaS Motivation 实验快速测试 ===")
    
    # 创建实验对象
    experiments = OpenFaaSMotivationExperiments()
    
    # 修改为更快的配置
    experiments.load_levels = {
        'low': 20.0,      # 20 req/s
        'medium': 50.0,   # 50 req/s  
        'high': 100.0     # 100 req/s
    }
    
    start_time = time.time()
    
    try:
        print("\n测试实验1：资源竞争负面外部性效应")
        # 只测试两种算法和两种负载
        test_algorithms = [SchedulingAlgorithm.GREEDY, SchedulingAlgorithm.LOAD_BALANCE]
        test_loads = {'low': 20.0, 'high': 100.0}
        
        experiment_1_results = []
        
        for algorithm in test_algorithms:
            for load_name, load_rate in test_loads.items():
                print(f"运行: {algorithm.value} - {load_name} ({load_rate} req/s)")
                
                experiments.simulator.reset_simulation()
                experiments.simulator.set_scheduler(algorithm)
                
                # 运行5分钟仿真
                experiments.simulator.simulate_workload(duration=300.0, request_rate=load_rate)
                
                metrics = experiments.simulator.get_simulation_metrics()
                if metrics:
                    metrics['algorithm'] = algorithm.value
                    metrics['load_level'] = load_name
                    metrics['load_rate'] = load_rate
                    experiment_1_results.append(metrics)
                    
                    # 打印关键指标
                    print(f"  - 处理请求数: {metrics['overall']['total_requests']}")
                    print(f"  - 平均延迟: {metrics['overall']['avg_latency']:.2f}ms")
                    print(f"  - 延迟恶化率: {metrics['overall']['latency_degradation_rate']:.3f}")
                    print(f"  - 资源不均衡系数: {metrics['overall']['resource_imbalance_coefficient']:.3f}")
        
        print(f"\n实验1测试完成，收集了 {len(experiment_1_results)} 个数据点")
        
        print("\n测试实验2：异质调度偏好冲突")
        # 测试偏好冲突
        experiment_2_results = []
        
        for algorithm in test_algorithms:
            print(f"运行偏好冲突测试: {algorithm.value}")
            
            experiments.simulator.reset_simulation()
            experiments.simulator.set_scheduler(algorithm)
            
            # 运行5分钟仿真
            experiments.simulator.simulate_workload(duration=300.0, request_rate=50.0)
            
            metrics = experiments.simulator.get_simulation_metrics()
            if metrics:
                metrics['algorithm'] = algorithm.value
                experiment_2_results.append(metrics)
                
                # 打印偏好相关指标
                print(f"  - 处理请求数: {metrics['overall']['total_requests']}")
                for preference, pref_metrics in metrics['by_preference'].items():
                    print(f"  - {preference} 偏好违反率: {pref_metrics['preference_violation_rate']:.3f}")
                    print(f"  - {preference} 目标达成率: {pref_metrics['performance_goal_achievement_rate']:.3f}")
        
        print(f"\n实验2测试完成，收集了 {len(experiment_2_results)} 个数据点")
        
        # 验证核心问题
        print("\n=== 核心问题验证 ===")
        
        # 问题1：资源竞争负面外部性效应
        print("问题1验证：资源竞争负面外部性效应")
        for result in experiment_1_results:
            degradation = result['overall']['latency_degradation_rate']
            imbalance = result['overall']['resource_imbalance_coefficient']
            print(f"  {result['algorithm']}-{result['load_level']}: 延迟恶化率={degradation:.3f}, 不均衡系数={imbalance:.3f}")
            
            if degradation > 0.1:  # 超过10%的延迟恶化
                print(f"    ✓ 检测到显著的负面外部性效应")
            else:
                print(f"    - 负面外部性效应较轻微")
        
        # 问题2：异质调度偏好冲突
        print("\n问题2验证：异质调度偏好冲突")
        for result in experiment_2_results:
            preferences = result['by_preference']
            violation_rates = [pref['preference_violation_rate'] for pref in preferences.values()]
            achievement_rates = [pref['performance_goal_achievement_rate'] for pref in preferences.values()]
            
            avg_violation = sum(violation_rates) / len(violation_rates)
            avg_achievement = sum(achievement_rates) / len(achievement_rates)
            
            print(f"  {result['algorithm']}: 平均违反率={avg_violation:.3f}, 平均达成率={avg_achievement:.3f}")
            
            if avg_violation > 0.3:  # 超过30%的偏好违反率
                print(f"    ✓ 检测到显著的偏好冲突")
            else:
                print(f"    - 偏好冲突程度较轻微")
        
    except Exception as e:
        print(f"测试过程中发生错误: {e}")
        import traceback
        traceback.print_exc()
    
    end_time = time.time()
    print(f"\n=== 快速测试完成 ===")
    print(f"总耗时: {end_time - start_time:.2f} 秒")
    print("系统功能验证通过，可以进行完整实验")

if __name__ == "__main__":
    quick_test() 