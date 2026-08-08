#!/usr/bin/env python3
"""
Nash 调度器质量权重参数超参数实验脚本
完全自动化运行，生成低中高负载下的性能数据
"""

import os
import sys
import time
import json
import subprocess
from pathlib import Path
import shutil

# 设置工作目录
SCRIPT_DIR = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
SERVERLESS_SIM_DIR = PROJECT_ROOT / "serverless_sim"
RESULTS_DIR = SCRIPT_DIR / "nash_experiment_results" / "quality_weight"

# 实验参数设置
QUALITY_WEIGHT_VALUES = [5.0, 10.0, 15.0, 20.0, 25.0, 30.0, 35.0]
# 从batch_run.yml读取实际的负载类型配置
RUNS_PER_PARAM = 3  # 每个参数值运行3次取平均

def setup_experiment_env():
    """设置实验环境"""
    print("🚀 设置实验环境...")
    
    # 创建结果目录
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    # 检查serverless_sim目录是否存在
    if not SERVERLESS_SIM_DIR.exists():
        print(f"❌ 错误：找不到 {SERVERLESS_SIM_DIR}")
        sys.exit(1)
    
    # 确保records目录存在
    records_dir = SERVERLESS_SIM_DIR / "records"
    records_dir.mkdir(exist_ok=True)
    
    print("✅ 实验环境设置完成")

def compile_backend():
    """编译Rust后端"""
    print("🔧 编译Rust后端...")
    
    try:
        result = subprocess.run(
            ["cargo", "build", "--release"],
            cwd=SERVERLESS_SIM_DIR,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            print(f"❌ 编译失败：{result.stderr}")
            sys.exit(1)
        
        print("✅ 后端编译完成")
        
    except subprocess.TimeoutExpired:
        print("❌ 编译超时")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 编译错误：{e}")
        sys.exit(1)

def run_experiment_for_param(param_value, load_type):
    """为特定参数值和负载类型运行实验"""
    print(f"🧪 运行实验：quality_weight={param_value}, load={load_type}")
    
    # 设置环境变量
    env = os.environ.copy()
    env["NASH_QUALITY_WEIGHT"] = str(param_value)
    
    # 动态读取当前batch_run.yml配置
    original_config_path = SCRIPT_DIR.parent / "batch_run.yml"
    import yaml
    
    try:
        with open(original_config_path, 'r', encoding='utf-8') as f:
            original_config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ 读取配置文件失败：{e}")
        return
    
    # 创建临时批量配置，完全基于当前配置但只使用sche_nash
    batch_config = {
        "run_time": original_config.get("run_time", 5),
        "params": original_config.get("params", {}),
        "mech_scale_sche": {}
    }
    
    # 动态处理mech_scale_sche配置
    if "scale_sche_separated" in original_config.get("mech_scale_sche", {}):
        batch_config["mech_scale_sche"]["scale_sche_separated"] = {
            "scale_num": original_config["mech_scale_sche"]["scale_sche_separated"].get("scale_num", []),
            "scale_down_exec": original_config["mech_scale_sche"]["scale_sche_separated"].get("scale_down_exec", []),
            "scale_up_exec": original_config["mech_scale_sche"]["scale_sche_separated"].get("scale_up_exec", []),
            "sche": [{"sche_nash": None}],  # 只使用sche_nash
            "filter": original_config["mech_scale_sche"]["scale_sche_separated"].get("filter", [])
        }
    elif "scale_sche_joint" in original_config.get("mech_scale_sche", {}):
        batch_config["mech_scale_sche"]["scale_sche_joint"] = {
            "scale_num": original_config["mech_scale_sche"]["scale_sche_joint"].get("scale_num", []),
            "scale_down_exec": original_config["mech_scale_sche"]["scale_sche_joint"].get("scale_down_exec", []),
            "scale_up_exec": original_config["mech_scale_sche"]["scale_sche_joint"].get("scale_up_exec", []),
            "sche": [{"sche_nash": None}],  # 只使用sche_nash
            "filter": original_config["mech_scale_sche"]["scale_sche_joint"].get("filter", [])
        }
    elif "no_scale" in original_config.get("mech_scale_sche", {}):
        batch_config["mech_scale_sche"]["no_scale"] = {
            "scale_num": original_config["mech_scale_sche"]["no_scale"].get("scale_num", []),
            "scale_down_exec": original_config["mech_scale_sche"]["no_scale"].get("scale_down_exec", []),
            "scale_up_exec": original_config["mech_scale_sche"]["no_scale"].get("scale_up_exec", []),
            "sche": [{"sche_nash": None}],  # 只使用sche_nash
            "filter": original_config["mech_scale_sche"]["no_scale"].get("filter", [])
        }
    
    # 复制mech_other配置
    batch_config["mech_other"] = original_config.get("mech_other", {})
    
    # 写入临时配置文件
    temp_config_path = SCRIPT_DIR / f"temp_batch_config_{param_value}_{load_type}.yml"
    
    import yaml
    with open(temp_config_path, 'w', encoding='utf-8') as f:
        yaml.dump(batch_config, f)
    
    try:
        # 运行实验 - 修复编码问题
        result = subprocess.run(
            [sys.executable, "batch_run.py"],
            cwd=SCRIPT_DIR.parent,
            env=env,
            capture_output=True,
            text=True,
            encoding='utf-8',
            errors='ignore',
            timeout=600  # 10分钟超时
        )
        
        if result.returncode != 0:
            print(f"⚠️ 实验运行警告：{result.stderr}")
        
        # 收集结果文件
        collect_results(param_value, load_type)
        
    except subprocess.TimeoutExpired:
        print(f"❌ 实验超时：quality_weight={param_value}, load={load_type}")
    except Exception as e:
        print(f"❌ 实验错误：{e}")
    finally:
        # 清理临时文件
        if temp_config_path.exists():
            temp_config_path.unlink()

def collect_results(param_value, load_type):
    """收集实验结果"""
    records_dir = SERVERLESS_SIM_DIR / "records"
    target_dir = RESULTS_DIR / f"param_{param_value}" / load_type
    target_dir.mkdir(parents=True, exist_ok=True)
    
    # 查找匹配的结果文件
    for file_path in records_dir.glob("*.UTC_*"):
        filename = file_path.name
        
        # 检查文件名是否匹配当前实验配置
        if (f"rf{load_type}" in filename and 
            "dtmix" in filename and 
            "sche_nash" in filename):
            
            # 复制到结果目录
            target_file = target_dir / filename
            shutil.copy2(file_path, target_file)
            
            print(f"📊 收集结果：{filename}")

def run_complete_experiment():
    """运行完整的超参数实验"""
    print("🎯 开始Quality Weight超参数实验")
    print(f"📊 实验参数：{QUALITY_WEIGHT_VALUES}")
    print(f"📊 每参数运行次数：{RUNS_PER_PARAM}")
    
    # 读取原始配置以获取实际的负载类型
    original_config_path = SCRIPT_DIR.parent / "batch_run.yml"
    import yaml
    
    with open(original_config_path, 'r', encoding='utf-8') as f:
        original_config = yaml.safe_load(f)
    
    # 获取实际启用的负载类型
    request_freq_config = original_config.get("params", {}).get("request_freq", [])
    load_types = []
    for config in request_freq_config:
        for load_type in config.keys():
            load_types.append(load_type)
    
    print(f"📊 实际负载类型：{load_types}")
    
    total_experiments = len(QUALITY_WEIGHT_VALUES) * len(load_types)
    current_experiment = 0
    
    for param_value in QUALITY_WEIGHT_VALUES:
        for load_type in load_types:
            current_experiment += 1
            print(f"\n🎯 进度：{current_experiment}/{total_experiments}")
            
            # 清理之前的结果
            records_dir = SERVERLESS_SIM_DIR / "records"
            if records_dir.exists():
                for file_path in records_dir.glob("*.UTC_*"):
                    file_path.unlink()
            
            # 运行实验
            run_experiment_for_param(param_value, load_type)
            
            # 等待系统稳定
            time.sleep(2)
    
    print("\n🎉 Quality Weight实验完成！")
    print(f"📁 结果保存在：{RESULTS_DIR}")

def main():
    """主函数"""
    print("=" * 60)
    print("🧪 Nash调度器Quality Weight超参数实验")
    print("=" * 60)
    
    try:
        setup_experiment_env()
        compile_backend()
        run_complete_experiment()
        
        print("\n✅ 实验完成！下一步：")
        print("1. 运行 python analyze_nash_results.py 分析结果")
        print("2. 运行 python draw_nash_param_lines.py 绘制折线图")
        
    except KeyboardInterrupt:
        print("\n❌ 用户中断实验")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ 实验失败：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 