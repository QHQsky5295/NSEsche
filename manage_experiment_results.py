import os
import json
import glob
from collections import defaultdict

def extract_cost_performance_ratio(file_path):
    """从JSON文件中提取性价比指标 - 修正版本
    性价比 = 吞吐量 / (成本 × 延迟)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # JSON文件结构: {'record_name': str, 'frames': [...]}
        # 每帧数据结构为：[帧号, 任务信息数组, 指标数组, 汇总数值...]
        
        if not isinstance(data, dict) or 'frames' not in data:
            return 0.0
            
        frames = data['frames']
        if not frames or len(frames) == 0:
            return 0.0
            
        # 动态读取索引常量（与records_read.py的Frame类保持一致）
        idxs = {}
        try:
            with open("serverless_sim/src/metric.rs", 'r', encoding="utf-8") as f:
                for line in f.readlines():
                    if line.find("const FRAME_IDX_")==-1:
                        continue
                    idx_name=line.split()[1][:-1]
                    idx_value=int(line.split()[4][:-1])
                    idxs[idx_name]=idx_value
        except Exception as e:
            print(f"无法读取metric.rs文件: {e}")
            # 使用备用硬编码索引
            idxs = {
                'FRAME_IDX_FRAME': 0,
                'FRAME_IDX_REQ_DONE_TIME_AVG': 3,
                'FRAME_IDX_COST': 6,
                'FRAME_IDX_DONE_REQ_COUNT': 8
            }
        
        FRAME_IDX_FRAME = idxs['FRAME_IDX_FRAME']
        FRAME_IDX_REQ_DONE_TIME_AVG = idxs['FRAME_IDX_REQ_DONE_TIME_AVG']
        FRAME_IDX_COST = idxs['FRAME_IDX_COST']
        FRAME_IDX_DONE_REQ_COUNT = idxs['FRAME_IDX_DONE_REQ_COUNT']
        
        # 计算总的已完成请求数（与records_read.py保持一致）
        total_done_req_count = 0
        
        for frame in frames:
            if isinstance(frame, list) and len(frame) > FRAME_IDX_DONE_REQ_COUNT:
                total_done_req_count += frame[FRAME_IDX_DONE_REQ_COUNT]
        
        # 获取最后一帧的数据
        last_frame = frames[-1]
        
        if not isinstance(last_frame, list) or len(last_frame) <= max(FRAME_IDX_REQ_DONE_TIME_AVG, FRAME_IDX_COST, FRAME_IDX_FRAME):
            return 0.0
        
        # 提取关键指标（与records_read.py完全一致）
        cost_per_req = last_frame[FRAME_IDX_COST]                    # 每请求成本
        time_per_req = last_frame[FRAME_IDX_REQ_DONE_TIME_AVG]       # 每请求平均时间（延迟）
        frame_cnt = last_frame[FRAME_IDX_FRAME]                      # 帧数
        rps = total_done_req_count / frame_cnt if frame_cnt > 0 else 0  # 吞吐量（RPS）
        
        # 计算性价比：吞吐量 / (成本 × 延迟)
        # 这与fast_draw.py中的公式一致: 'rps/cost_per_req/time_per_req'
        if cost_per_req > 0 and time_per_req > 0:
            quality_price_ratio = rps / (cost_per_req * time_per_req)
            return quality_price_ratio
        else:
            return 0.0
            
    except Exception as e:
        print(f"提取性价比时出错 {file_path}: {e}")
        return 0.0

def extract_load_type(filename):
    """从文件名中提取负载类型"""
    if 'rfhigh' in filename:
        return 'high'
    elif 'rfmiddle' in filename:
        return 'middle'
    elif 'rflow' in filename:
        return 'low'
    elif 'cshigh' in filename:
        return 'high'
    elif 'csmedium' in filename:
        return 'medium'
    elif 'cslow' in filename:
        return 'low'
    else:
        return 'unknown'

def get_json_files(records_dir):
    """获取records目录下的所有JSON文件"""
    pattern = os.path.join(records_dir, '*.json')
    return glob.glob(pattern)

def group_files_by_load_type(json_files):
    """按负载类型对文件进行分组"""
    groups = defaultdict(list)
    
    for file_path in json_files:
        filename = os.path.basename(file_path)
        load_type = extract_load_type(filename)
        groups[load_type].append(file_path)
    
    return groups

def keep_best_files(records_dir, keep_highest=True, keep_count=1):
    """保留性价比最高或最低的N个文件，删除其他文件
    
    Args:
        records_dir: 记录文件目录
        keep_highest: True保留最高的，False保留最低的
        keep_count: 每个负载类型保留的文件数量
    """
    json_files = get_json_files(records_dir)
    
    if not json_files:
        print("未找到JSON文件")
        return
    
    # 按负载类型分组
    groups = group_files_by_load_type(json_files)
    
    deleted_count = 0
    kept_count = 0
    
    for load_type, files in groups.items():
        if len(files) <= keep_count:
            print(f"负载类型 {load_type}: 只有 {len(files)} 个文件，少于或等于保留数量 {keep_count}，跳过")
            kept_count += len(files)
            continue
            
        print(f"\n处理负载类型: {load_type} ({len(files)} 个文件，保留前 {keep_count} 个)")
        
        # 计算每个文件的性价比
        file_ratios = []
        for file_path in files:
            ratio = extract_cost_performance_ratio(file_path)
            file_ratios.append((file_path, ratio))
            print(f"  {os.path.basename(file_path)}: 性价比 = {ratio:.6f}")
        
        # 根据选择排序
        file_ratios.sort(key=lambda x: x[1], reverse=keep_highest)
        
        # 保留前N个文件，删除其他文件
        files_to_keep = file_ratios[:keep_count]
        files_to_delete = file_ratios[keep_count:]
        
        print(f"  保留的文件:")
        for file_path, ratio in files_to_keep:
            print(f"    {os.path.basename(file_path)} (性价比: {ratio:.6f})")
            kept_count += 1
        
        for file_path, ratio in files_to_delete:
            try:
                os.remove(file_path)
                print(f"  删除: {os.path.basename(file_path)} (性价比: {ratio:.6f})")
                deleted_count += 1
            except Exception as e:
                print(f"  删除失败 {os.path.basename(file_path)}: {e}")
    
    print(f"\n处理完成: 保留 {kept_count} 个文件，删除 {deleted_count} 个文件")

def show_current_files(records_dir):
    """显示当前文件状态"""
    json_files = get_json_files(records_dir)
    
    if not json_files:
        print("未找到JSON文件")
        return
    
    groups = group_files_by_load_type(json_files)
    
    print(f"\n当前文件状态 (总共 {len(json_files)} 个文件):")
    for load_type, files in groups.items():
        print(f"\n负载类型 {load_type} ({len(files)} 个文件):")
        for file_path in files:
            ratio = extract_cost_performance_ratio(file_path)
            print(f"  {os.path.basename(file_path)}: 性价比 = {ratio:.6f}")

def get_keep_count():
    """获取用户输入的保留文件数量"""
    while True:
        try:
            count = int(input("请输入要保留的文件数量 (默认为1): ").strip() or "1")
            if count <= 0:
                print("保留数量必须大于0，请重新输入")
                continue
            return count
        except ValueError:
            print("请输入有效的数字")

def main():
    records_dir = "serverless_sim/records"
    
    if not os.path.exists(records_dir):
        print(f"目录不存在: {records_dir}")
        return
    
    while True:
        print("\n=== 实验结果管理工具 ===")
        print("1. 显示当前文件状态")
        print("2. 保留性价比最高的文件 (单个)")
        print("3. 保留性价比最低的文件 (单个)")
        print("4. 保留性价比最高的前N个文件 (自定义数量)")
        print("5. 保留性价比最低的前N个文件 (自定义数量)")
        print("6. 退出")
        
        choice = input("\n请选择操作 (1-6): ").strip()
        
        if choice == '1':
            show_current_files(records_dir)
        elif choice == '2':
            print("\n开始处理，保留性价比最高的文件...")
            keep_best_files(records_dir, keep_highest=True, keep_count=1)
            print("\n处理完成后的文件状态:")
            show_current_files(records_dir)
        elif choice == '3':
            print("\n开始处理，保留性价比最低的文件...")
            keep_best_files(records_dir, keep_highest=False, keep_count=1)
            print("\n处理完成后的文件状态:")
            show_current_files(records_dir)
        elif choice == '4':
            keep_count = get_keep_count()
            print(f"\n开始处理，保留性价比最高的前 {keep_count} 个文件...")
            keep_best_files(records_dir, keep_highest=True, keep_count=keep_count)
            print("\n处理完成后的文件状态:")
            show_current_files(records_dir)
        elif choice == '5':
            keep_count = get_keep_count()
            print(f"\n开始处理，保留性价比最低的前 {keep_count} 个文件...")
            keep_best_files(records_dir, keep_highest=False, keep_count=keep_count)
            print("\n处理完成后的文件状态:")
            show_current_files(records_dir)
        elif choice == '6':
            print("退出程序")
            break
        else:
            print("无效选择，请重新输入")

if __name__ == "__main__":
    main()