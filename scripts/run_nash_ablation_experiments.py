import os
import sys
import yaml
import time
import subprocess
import glob
from datetime import datetime

CUR_FPATH = os.path.abspath(__file__)
CUR_FDIR = os.path.dirname(CUR_FPATH)
os.chdir(CUR_FDIR)

def rename_result_files(ablation_type):
    """重命名实验结果文件"""
    # 消融实验类型映射
    ablation_name_mapping = {
        'no_social_awareness': 'no_social',
        'no_congestion_pricing': 'no_price', 
        'no_heterogeneity_modeling': 'no_heter_model',
        'full_version': 'full_version'
    }
    
    short_name = ablation_name_mapping.get(ablation_type, ablation_type)
    # 修正路径：records文件夹在serverless_sim中，不在scripts中
    records_dir = os.path.join(os.path.dirname(CUR_FDIR), 'serverless_sim', 'records')
    
    if not os.path.exists(records_dir):
        print(f"⚠️ records文件夹不存在: {records_dir}")
        return
    
    # 查找包含sche_nash的JSON文件
    pattern = os.path.join(records_dir, '*scd(sche_nash.)*')
    json_files = glob.glob(pattern)
    
    if not json_files:
        print(f"⚠️ 未找到包含scd(sche_nash.)的文件")
        return
    
    renamed_count = 0
    for file_path in json_files:
        try:
            # 获取文件名
            filename = os.path.basename(file_path)
            # 替换sche_nash为消融实验名称
            new_filename = filename.replace('sche_nash.', f'{short_name}.')
            new_file_path = os.path.join(records_dir, new_filename)
            
            # 重命名文件
            os.rename(file_path, new_file_path)
            print(f"✅ 重命名: {filename} -> {new_filename}")
            renamed_count += 1
            
        except Exception as e:
            print(f"❌ 重命名失败 {filename}: {e}")
    
    print(f"📁 共重命名 {renamed_count} 个文件")

def create_ablation_config(ablation_type, base_config_path="batch_run.yml"):
    """创建消融实验配置文件"""
    # 直接读取原始YAML文件内容
    with open(base_config_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 激活sche_nash配置项（取消注释）
    content = content.replace('    # - sche_nash:', '    - sche_nash:')
    
    # 注释掉其他调度器（如果已激活）
    content = content.replace('    - sche_orion:', '    # - sche_orion:')
    content = content.replace('    - greedy:', '    # - greedy:')
    content = content.replace('    - hash:', '    # - hash:')
    content = content.replace('    - random:', '    # - random:')
    content = content.replace('    - load_least:', '    # - load_least:')
    content = content.replace('    - faasflow:', '    # - faasflow:')
    content = content.replace('    - consistenthash:', '    # - consistenthash:')
    content = content.replace('    - bp_balance:', '    # - bp_balance:')
    content = content.replace('    - ensure_scheduler:', '    # - ensure_scheduler:')
    
    # 生成配置文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    config_filename = f"ablation_config_{ablation_type}_{timestamp}.yml"
    config_path = os.path.join(CUR_FDIR, config_filename)
    
    # 保存配置文件（直接写入修改后的文本内容）
    with open(config_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    return config_path, config_filename

def run_ablation_experiment(ablation_type):
    """运行消融实验"""
    print(f"\n=== 开始运行 {ablation_type} 消融实验 ===")
    
    # 创建配置文件
    config_path, config_filename = create_ablation_config(ablation_type)
    print(f"已创建配置文件: {config_filename}")
    
    # 设置环境变量
    env = os.environ.copy()
    env['NASH_ABLATION_TYPE'] = ablation_type
    
    try:
        # 运行实验
        print(f"正在执行消融实验: {ablation_type}")
        print("请确保后端已经启动 (cargo run)")
        
        # 修改batch_run.py以使用自定义配置文件
        result = subprocess.run([
            sys.executable, 'batch_run_ablation.py', config_path
        ], env=env, capture_output=True, text=True)
        
        if result.returncode == 0:
            print(f"✅ {ablation_type} 实验完成")
            print("实验数据已保存到 records 文件夹")
            
            # 重命名结果文件
            print(f"\n🔄 开始重命名结果文件...")
            rename_result_files(ablation_type)
            
        else:
            print(f"❌ {ablation_type} 实验失败")
            print(f"错误信息: {result.stderr}")
            
    except Exception as e:
        print(f"❌ 运行实验时出错: {e}")
    
    finally:
        # 清理临时配置文件
        if os.path.exists(config_path):
            os.remove(config_path)
            print(f"已清理临时配置文件: {config_filename}")

def main():
    print("=== Nash调度器消融实验系统 ===")
    print("请选择要运行的消融实验类型：")
    print("1. 无社会感知 (no_social_awareness)")
    print("2. 无拥塞定价 (no_congestion_pricing)")
    print("3. 无异质性建模 (no_heterogeneity_modeling)")
    print("4. 完整版本 (full_version) - 对照组")
    print("5. 运行所有消融实验")
    print("0. 退出")
    
    while True:
        try:
            choice = input("\n请输入选择 (0-5): ").strip()
            
            if choice == '0':
                print("退出消融实验系统")
                break
            elif choice == '1':
                run_ablation_experiment('no_social_awareness')
            elif choice == '2':
                run_ablation_experiment('no_congestion_pricing')
            elif choice == '3':
                run_ablation_experiment('no_heterogeneity_modeling')
            elif choice == '4':
                run_ablation_experiment('full_version')
            elif choice == '5':
                print("\n=== 运行所有消融实验 ===")
                experiments = [
                    'full_version',
                    'no_social_awareness', 
                    'no_congestion_pricing',
                    'no_heterogeneity_modeling'
                ]
                for exp in experiments:
                    run_ablation_experiment(exp)
                    time.sleep(2)  # 实验间隔
                print("\n🎉 所有消融实验完成！")
            else:
                print("❌ 无效选择，请重新输入")
                
        except KeyboardInterrupt:
            print("\n\n用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 发生错误: {e}")

if __name__ == "__main__":
    main()