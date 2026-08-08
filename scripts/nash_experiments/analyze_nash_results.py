#!/usr/bin/env python3
"""
Nash 调度器超参数实验结果分析脚本
从JSON结果文件中提取关键指标，按负载类型和参数值分类
"""

import os
import sys
import json
import numpy as np
from pathlib import Path
from collections import defaultdict
import pandas as pd

# 添加records_read路径
sys.path.append(str(Path(__file__).parent.parent))
import records_read

# 设置工作目录
SCRIPT_DIR = Path(__file__).parent
RESULTS_DIR = SCRIPT_DIR / "nash_experiment_results"
ANALYSIS_DIR = SCRIPT_DIR / "nash_analysis_results"

# 关键指标定义
METRICS = {
    "cost": "平均成本",
    "latency": "平均延迟(ms)",
    "throughput": "吞吐量(req/s)",
    "cost_performance": "性价比"
}

LOAD_TYPES = ["low", "middle", "high"]
LOAD_NAMES = {"low": "低负载", "middle": "中负载", "high": "高负载"}

def extract_metrics_from_record(record):
    """从记录中提取关键指标"""
    metrics = {}
    
    # 平均成本
    metrics["cost"] = record.cost_per_req
    
    # 平均延迟(ms)
    metrics["latency"] = record.time_per_req
    
    # 吞吐量(req/s)
    metrics["throughput"] = record.rps
    
    # 性价比 = 吞吐量 / (成本 × 延迟)
    if record.cost_per_req > 0 and record.time_per_req > 0:
        metrics["cost_performance"] = record.rps / (record.cost_per_req * record.time_per_req)
    else:
        metrics["cost_performance"] = 0
    
    return metrics

def analyze_experiment_results(param_name, param_values):
    """分析特定参数的实验结果"""
    print(f"🔍 分析{param_name}实验结果...")
    
    results_dir = RESULTS_DIR / param_name
    if not results_dir.exists():
        print(f"❌ 找不到结果目录：{results_dir}")
        return None
    
    # 按负载类型和参数值组织数据
    data = {
        load_type: {
            "params": [],
            "cost": [],
            "latency": [],
            "throughput": [],
            "cost_performance": []
        }
        for load_type in LOAD_TYPES
    }
    
    # 遍历每个参数值
    for param_value in param_values:
        param_dir = results_dir / f"param_{param_value}"
        if not param_dir.exists():
            print(f"⚠️ 跳过缺失的参数值：{param_value}")
            continue
        
        # 遍历每个负载类型
        for load_type in LOAD_TYPES:
            load_dir = param_dir / load_type
            if not load_dir.exists():
                print(f"⚠️ 跳过缺失的负载类型：{param_value}/{load_type}")
                continue
            
            # 收集该参数值和负载类型下的所有记录
            records = []
            for result_file in load_dir.glob("*.UTC_*"):
                try:
                    record = records_read.load_record_from_file(result_file.name)
                    records.append(record)
                except Exception as e:
                    print(f"⚠️ 读取记录失败：{result_file.name}, {e}")
                    continue
            
            if not records:
                print(f"⚠️ 没有找到有效记录：{param_value}/{load_type}")
                continue
            
            # 计算平均指标
            avg_metrics = calculate_average_metrics(records)
            
            # 存储结果
            data[load_type]["params"].append(param_value)
            data[load_type]["cost"].append(avg_metrics["cost"])
            data[load_type]["latency"].append(avg_metrics["latency"])
            data[load_type]["throughput"].append(avg_metrics["throughput"])
            data[load_type]["cost_performance"].append(avg_metrics["cost_performance"])
            
            print(f"📊 处理完成：{param_value}/{load_type}, 记录数：{len(records)}")
    
    # 保存分析结果
    save_analysis_results(param_name, data)
    
    return data

def calculate_average_metrics(records):
    """计算多个记录的平均指标"""
    if not records:
        return {metric: 0 for metric in METRICS.keys()}
    
    metrics_list = [extract_metrics_from_record(record) for record in records]
    
    avg_metrics = {}
    for metric_name in METRICS.keys():
        values = [m[metric_name] for m in metrics_list if m[metric_name] > 0]
        if values:
            avg_metrics[metric_name] = np.mean(values)
        else:
            avg_metrics[metric_name] = 0
    
    return avg_metrics

def save_analysis_results(param_name, data):
    """保存分析结果到CSV文件"""
    ANALYSIS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 为每个负载类型保存一个CSV文件
    for load_type in LOAD_TYPES:
        if not data[load_type]["params"]:
            continue
        
        df = pd.DataFrame({
            "参数值": data[load_type]["params"],
            "平均成本": data[load_type]["cost"],
            "平均延迟(ms)": data[load_type]["latency"],
            "吞吐量(req/s)": data[load_type]["throughput"],
            "性价比": data[load_type]["cost_performance"]
        })
        
        csv_file = ANALYSIS_DIR / f"{param_name}_{load_type}.csv"
        df.to_csv(csv_file, index=False, encoding='utf-8')
        print(f"💾 保存分析结果：{csv_file}")

def print_analysis_summary(param_name, data):
    """打印分析结果摘要"""
    print(f"\n📊 {param_name}实验结果摘要：")
    print("=" * 80)
    
    for load_type in LOAD_TYPES:
        if not data[load_type]["params"]:
            continue
        
        print(f"\n🔸 {LOAD_NAMES[load_type]}:")
        print(f"   参数值范围：{min(data[load_type]['params']):.2f} - {max(data[load_type]['params']):.2f}")
        print(f"   平均成本范围：{min(data[load_type]['cost']):.4f} - {max(data[load_type]['cost']):.4f}")
        print(f"   平均延迟范围：{min(data[load_type]['latency']):.2f} - {max(data[load_type]['latency']):.2f} ms")
        print(f"   吞吐量范围：{min(data[load_type]['throughput']):.2f} - {max(data[load_type]['throughput']):.2f} req/s")
        print(f"   性价比范围：{min(data[load_type]['cost_performance']):.2f} - {max(data[load_type]['cost_performance']):.2f}")

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 Nash调度器超参数实验结果分析")
    print("=" * 60)
    
    # 分析Price Feedback Rate实验
    if (RESULTS_DIR / "price_feedback_rate").exists():
        print("\n📊 分析Price Feedback Rate实验...")
        price_feedback_values = [0.05, 0.10, 0.15, 0.20, 0.25, 0.30, 0.35]
        price_data = analyze_experiment_results("price_feedback_rate", price_feedback_values)
        
        if price_data:
            print_analysis_summary("Price Feedback Rate", price_data)
    else:
        print("⚠️ 找不到Price Feedback Rate实验结果")
    
    # 分析Quality Weight实验
    if (RESULTS_DIR / "quality_weight").exists():
        print("\n📊 分析Quality Weight实验...")
        quality_weight_values = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
        quality_data = analyze_experiment_results("quality_weight", quality_weight_values)
        
        if quality_data:
            print_analysis_summary("Quality Weight", quality_data)
    else:
        print("⚠️ 找不到Quality Weight实验结果")
    
    print(f"\n✅ 分析完成！结果保存在：{ANALYSIS_DIR}")
    print("下一步：运行 python draw_nash_param_lines.py 绘制折线图")

if __name__ == "__main__":
    main() 