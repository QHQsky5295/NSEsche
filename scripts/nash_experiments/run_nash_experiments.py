#!/usr/bin/env python3
"""
Nash 调度器超参数实验主控制脚本
提供菜单选择，运行不同的实验和分析步骤
"""

import os
import sys
import subprocess
from pathlib import Path

# 设置工作目录
SCRIPT_DIR = Path(__file__).parent

def print_banner():
    """打印欢迎横幅"""
    print("=" * 70)
    print("🧪 Nash调度器超参数实验套件")
    print("=" * 70)
    print("📊 完全自动化的超参数实验和分析系统")
    print("🎯 支持两个关键超参数：")
    print("   1. Price Feedback Rate (价格反馈调整系数)")
    print("   2. Quality Weight (质量敏感度权重)")
    print("=" * 70)

def print_menu():
    """打印菜单选项"""
    print("\n🎯 请选择操作：")
    print("1. 运行Price Feedback Rate实验")
    print("2. 运行Quality Weight实验")
    print("3. 运行所有实验")
    print("4. 分析实验结果")
    print("5. 绘制折线图")
    print("6. 完整实验流程（实验+分析+绘图）")
    print("7. 运行完整Price Feedback Rate实验（实验+分析+绘图）")
    print("8. 运行完整Quality Weight实验（实验+分析+绘图）")
    print("9. 查看实验状态")
    print("10. 清理实验数据")
    print("0. 退出")

def run_script(script_name, description):
    """运行指定的脚本"""
    print(f"\n🚀 {description}...")
    print("-" * 50)
    
    try:
        script_path = SCRIPT_DIR / script_name
        if not script_path.exists():
            print(f"❌ 脚本不存在：{script_path}")
            return False
        
        result = subprocess.run(
            [sys.executable, str(script_path)],
            cwd=SCRIPT_DIR,
            capture_output=False,
            text=True
        )
        
        if result.returncode == 0:
            print(f"✅ {description}完成")
            return True
        else:
            print(f"❌ {description}失败")
            return False
            
    except KeyboardInterrupt:
        print(f"\n❌ 用户中断{description}")
        return False
    except Exception as e:
        print(f"❌ 执行错误：{e}")
        return False

def check_experiment_status():
    """检查实验状态"""
    print("\n📊 实验状态检查：")
    print("-" * 50)
    
    results_dir = SCRIPT_DIR / "nash_experiment_results"
    analysis_dir = SCRIPT_DIR / "nash_analysis_results"
    figures_dir = SCRIPT_DIR / "nash_figures"
    
    # 检查实验结果
    price_feedback_dir = results_dir / "price_feedback_rate"
    quality_weight_dir = results_dir / "quality_weight"
    
    if price_feedback_dir.exists():
        param_count = len(list(price_feedback_dir.glob("param_*")))
        print(f"🔸 Price Feedback Rate实验：{param_count} 个参数值")
    else:
        print("🔸 Price Feedback Rate实验：未运行")
    
    if quality_weight_dir.exists():
        param_count = len(list(quality_weight_dir.glob("param_*")))
        print(f"🔸 Quality Weight实验：{param_count} 个参数值")
    else:
        print("🔸 Quality Weight实验：未运行")
    
    # 检查分析结果
    if analysis_dir.exists():
        csv_count = len(list(analysis_dir.glob("*.csv")))
        print(f"🔸 分析结果：{csv_count} 个CSV文件")
    else:
        print("🔸 分析结果：未生成")
    
    # 检查图表
    if figures_dir.exists():
        png_count = len(list(figures_dir.glob("*.png")))
        print(f"🔸 图表：{png_count} 个PNG文件")
    else:
        print("🔸 图表：未生成")

def clean_experiment_data():
    """清理实验数据"""
    print("\n🧹 清理实验数据...")
    print("-" * 50)
    
    import shutil
    
    dirs_to_clean = [
        SCRIPT_DIR / "nash_experiment_results",
        SCRIPT_DIR / "nash_analysis_results",
        SCRIPT_DIR / "nash_figures"
    ]
    
    for dir_path in dirs_to_clean:
        if dir_path.exists():
            shutil.rmtree(dir_path)
            print(f"🗑️ 已删除：{dir_path}")
        else:
            print(f"⚠️ 目录不存在：{dir_path}")
    
    print("✅ 清理完成")

def main():
    """主函数"""
    print_banner()
    
    while True:
        print_menu()
        
        try:
            choice = input("\n请输入选项 (0-10): ").strip()
            
            if choice == "0":
                print("\n👋 感谢使用Nash调度器超参数实验套件！")
                break
            
            elif choice == "1":
                run_script("run_nash_price_feedback_experiment.py", "Price Feedback Rate实验")
            
            elif choice == "2":
                run_script("run_nash_quality_weight_experiment.py", "Quality Weight实验")
            
            elif choice == "3":
                print("\n🎯 运行所有实验...")
                success1 = run_script("run_nash_price_feedback_experiment.py", "Price Feedback Rate实验")
                success2 = run_script("run_nash_quality_weight_experiment.py", "Quality Weight实验")
                
                if success1 and success2:
                    print("\n✅ 所有实验完成！")
                else:
                    print("\n⚠️ 部分实验失败，请检查日志")
            
            elif choice == "4":
                run_script("analyze_nash_results.py", "实验结果分析")
            
            elif choice == "5":
                run_script("draw_nash_param_lines.py", "折线图绘制")
            
            elif choice == "6":
                print("\n🎯 运行完整实验流程...")
                
                # 运行实验
                success1 = run_script("run_nash_price_feedback_experiment.py", "Price Feedback Rate实验")
                success2 = run_script("run_nash_quality_weight_experiment.py", "Quality Weight实验")
                
                if success1 or success2:
                    # 分析结果
                    analysis_success = run_script("analyze_nash_results.py", "实验结果分析")
                    
                    if analysis_success:
                        # 绘制图表
                        draw_success = run_script("draw_nash_param_lines.py", "折线图绘制")
                        
                        if draw_success:
                            print("\n🎉 完整实验流程完成！")
                            print("📁 查看结果：")
                            print("   - 实验数据：scripts/nash_experiment_results/")
                            print("   - 分析结果：scripts/nash_analysis_results/")
                            print("   - 图表：scripts/nash_figures/")
                        else:
                            print("\n⚠️ 图表绘制失败")
                    else:
                        print("\n⚠️ 结果分析失败")
                else:
                    print("\n❌ 实验运行失败")
            
            elif choice == "7":
                print("\n🎯 运行完整Price Feedback Rate实验流程...")
                
                # 运行Price Feedback Rate实验
                experiment_success = run_script("run_nash_price_feedback_experiment.py", "Price Feedback Rate实验")
                
                if experiment_success:
                    # 分析结果
                    analysis_success = run_script("analyze_nash_results.py", "Price Feedback Rate实验结果分析")
                    
                    if analysis_success:
                        # 绘制图表
                        draw_success = run_script("draw_nash_param_lines.py", "Price Feedback Rate折线图绘制")
                        
                        if draw_success:
                            print("\n🎉 Price Feedback Rate完整实验流程完成！")
                            print("📁 查看结果：")
                            print("   - 实验数据：scripts/nash_experiments/nash_experiment_results/price_feedback_rate/")
                            print("   - 分析结果：scripts/nash_experiments/nash_analysis_results/")
                            print("   - 图表：scripts/nash_experiments/nash_figures/")
                        else:
                            print("\n⚠️ Price Feedback Rate图表绘制失败")
                    else:
                        print("\n⚠️ Price Feedback Rate结果分析失败")
                else:
                    print("\n❌ Price Feedback Rate实验运行失败")
            
            elif choice == "8":
                print("\n🎯 运行完整Quality Weight实验流程...")
                
                # 运行Quality Weight实验
                experiment_success = run_script("run_nash_quality_weight_experiment.py", "Quality Weight实验")
                
                if experiment_success:
                    # 分析结果
                    analysis_success = run_script("analyze_nash_results.py", "Quality Weight实验结果分析")
                    
                    if analysis_success:
                        # 绘制图表
                        draw_success = run_script("draw_nash_param_lines.py", "Quality Weight折线图绘制")
                        
                        if draw_success:
                            print("\n🎉 Quality Weight完整实验流程完成！")
                            print("📁 查看结果：")
                            print("   - 实验数据：scripts/nash_experiments/nash_experiment_results/quality_weight/")
                            print("   - 分析结果：scripts/nash_experiments/nash_analysis_results/")
                            print("   - 图表：scripts/nash_experiments/nash_figures/")
                        else:
                            print("\n⚠️ Quality Weight图表绘制失败")
                    else:
                        print("\n⚠️ Quality Weight结果分析失败")
                else:
                    print("\n❌ Quality Weight实验运行失败")
            
            elif choice == "9":
                check_experiment_status()
            
            elif choice == "10":
                confirm = input("⚠️ 确定要清理所有实验数据吗？(y/N): ").strip().lower()
                if confirm == "y":
                    clean_experiment_data()
                else:
                    print("❌ 取消清理")
            
            else:
                print("❌ 无效选项，请重新输入")
        
        except KeyboardInterrupt:
            print("\n\n👋 用户中断，退出程序")
            break
        except Exception as e:
            print(f"❌ 程序错误：{e}")

if __name__ == "__main__":
    main() 