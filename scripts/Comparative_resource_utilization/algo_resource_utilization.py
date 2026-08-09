import json
from pathlib import Path
import re
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# 全局字体缩放：设置为默认的 2 倍
FONT_SCALE = 2.0
# 使用 seaborn 统一放大标题、坐标轴标签、刻度、图例等字体
sns.set(context='notebook', style='whitegrid', font_scale=FONT_SCALE)
ANNOT_SIZE = int(10 * FONT_SCALE)  # 热力图数字标注字体大小

ALGORITHM_MAPPING = {
    # normalize to lowercase keys for robust matching
    'greedy': 'Greedy',
    'random': 'Random',
    'hash': 'Hash',
    'load_least': 'Load Balance',
    'sche_OCS': 'OCS',
    'sche_Hiku': 'Hiku',
    'sche_jiagu': 'Jiagu',
    'sche_orion': 'Orion',
    'sche_nash': 'NSESche',
    'sche_FaasRank': 'FaaSRank',
    'sche_ocs': 'OCS',
    'sche_hiku': 'Hiku',
    'sche_Jiagu': 'Jiagu',
    'sche_Orion': 'Orion',
    'sche_Nash': 'NSESche'
}
ALGORITHM_ORDER = [
    'Greedy', 'Random', 'Hash', 'Load Balance',
    'FaaSRank', 'OCS', 'Hiku', 'Jiagu', 'Orion',
    'NSESche'
]
LOAD_MAPPING = {
    'rflow': 'Low Load',
    'rfmiddle': 'Middle Load',
    'rfhigh': 'High Load'
}
LOAD_ORDER = ['rflow', 'rfmiddle', 'rfhigh']

def parse_load_and_algo_from_filename(filename: str):
    config_str = filename.split('.UTC_')[0]
    parts = config_str.split('.')
    load = None
    for p in parts:
        if p.startswith('rf'):
            load = p
            break
    algo = None
    scd_start = config_str.find('.scd(')
    if scd_start != -1:
        scd_end = config_str.find(').', scd_start)
        if scd_end != -1:
            raw = config_str[scd_start + 5: scd_end]
            # examples: 'sche_nash.' or 'random.' -> strip trailing dot, lowercase
            sanitized = raw.strip().rstrip('.').lower()
            algo = ALGORITHM_MAPPING.get(sanitized, sanitized if sanitized else None)
    return load, algo

def get_node_limits(node_rs_path: Path):
    """Read CPU/MEM limits from serverless_sim/src/node.rs to keep in sync.

    Falls back to (150.0, 5000.0) if parsing fails.
    """
    cpu_limit = 150.0
    mem_limit = 5000.0
    try:
        text = node_rs_path.read_text(encoding='utf-8')
        # Prefer the rsc_limit NodeRscLimit initializer inside Node::new
        # Example: rsc_limit: NodeRscLimit { cpu: 150.0, mem: 5000.0, }
        pattern = r"NodeRscLimit\s*\{[^}]*cpu\s*:\s*([0-9]+(?:\.[0-9]+)?),[^}]*mem\s*:\s*([0-9]+(?:\.[0-9]+)?)"
        matches = re.findall(pattern, text, flags=re.DOTALL)
        if matches:
            # Use the last occurrence to guard against multiple examples
            last = matches[-1]
            cpu_limit = float(last[0])
            mem_limit = float(last[1])
        else:
            # Fallback: capture the inner block of rsc_limit initializer then parse fields
            m = re.search(r"rsc_limit\s*:\s*NodeRscLimit\s*\{([^}]*)\}", text, flags=re.DOTALL)
            if m:
                inner = m.group(1)
                mcpu = re.search(r"cpu\s*:\s*([0-9]+(?:\.[0-9]+)?)", inner)
                mmem = re.search(r"mem\s*:\s*([0-9]+(?:\.[0-9]+)?)", inner)
                if mcpu:
                    cpu_limit = float(mcpu.group(1))
                if mmem:
                    mem_limit = float(mmem.group(1))
    except Exception:
        # Keep defaults if any error occurs
        pass
    return cpu_limit, mem_limit

def compute_utilization_for_file(json_path: Path, cpu_limit: float, mem_limit: float):
    # 某些记录文件可能不完整或写入中，需容错跳过
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except Exception:
        return None
    frames = data.get('frames', [])
    if not frames:
        return None

    cpu_utils = []
    mem_utils = []

    for frame in frames:
        # FRAME_IDX_NODES == 2
        nodes = frame[2]
        if not nodes:
            continue
        # 平均每帧各节点利用率（先按节点平均，再按帧平均）
        frame_cpu = np.mean([n['c'] / cpu_limit for n in nodes])
        frame_mem = np.mean([n['m'] / mem_limit for n in nodes])

        cpu_utils.append(frame_cpu)
        mem_utils.append(frame_mem)

    if not cpu_utils or not mem_utils:
        return None

    return float(np.mean(cpu_utils)), float(np.mean(mem_utils))

def main():
    # Repo root: .../serverless_sim_game
    repo_root = Path(__file__).resolve().parents[2]
    # Keep in sync with serverless_sim limits
    node_rs_path = repo_root / 'serverless_sim' / 'src' / 'node.rs'
    cpu_limit, mem_limit = get_node_limits(node_rs_path)

    # Records are created under serverless_sim/records when running the Rust server
    records_dir = repo_root / 'serverless_sim' / 'records'
    if not records_dir.exists():
        print(f'No records directory found: {records_dir}')
        return

    rows = []
    for jf in records_dir.glob('*.json'):
        load, algo = parse_load_and_algo_from_filename(jf.name)
        if not load or not algo:
            continue
        res = compute_utilization_for_file(jf, cpu_limit, mem_limit)
        if not res:
            continue
        cpu_avg, mem_avg = res
        rows.append({
            'algorithm': algo,
            'load': load,
            'cpu_util': cpu_avg,
            'mem_util': mem_avg,
            'file': jf.name
        })

    if not rows:
        print('No usable records found.')
        return

    df = pd.DataFrame(rows)
    # 对同一算法+负载的多次运行做平均
    agg = df.groupby(['algorithm', 'load'], as_index=False)[['cpu_util', 'mem_util']].mean()

    # 保存CSV
    out_csv = Path(__file__).parent / 'algo_resource_utilization.csv'
    agg.to_csv(out_csv, index=False)
    print(f'Wrote: {out_csv}')
    print(agg.sort_values(['algorithm', 'load']))

    # 画热力图：CPU
    cpu_pivot = agg.pivot(index='algorithm', columns='load', values='cpu_util')
    cpu_pivot = cpu_pivot.reindex(index=[a for a in ALGORITHM_ORDER if a in cpu_pivot.index],
                                  columns=[l for l in LOAD_ORDER if l in cpu_pivot.columns])
    plt.figure(figsize=(10, 7))
    sns.heatmap(cpu_pivot.rename(columns=LOAD_MAPPING), annot=True, fmt='.3f',
                cmap='YlGnBu', vmin=0, vmax=1, annot_kws={'size': ANNOT_SIZE})
    plt.ylabel('Algorithm'); plt.xlabel('Load')
    cpu_png = Path(__file__).parent / 'algo_cpu_utilization_heatmap.png'
    plt.tight_layout(); plt.savefig(cpu_png, dpi=300)
    print(f'Wrote: {cpu_png}')
    plt.close()

    # 画热力图：内存
    mem_pivot = agg.pivot(index='algorithm', columns='load', values='mem_util')
    mem_pivot = mem_pivot.reindex(index=[a for a in ALGORITHM_ORDER if a in mem_pivot.index],
                                  columns=[l for l in LOAD_ORDER if l in mem_pivot.columns])
    plt.figure(figsize=(10, 7))
    sns.heatmap(mem_pivot.rename(columns=LOAD_MAPPING), annot=True, fmt='.3f',
                cmap='OrRd', vmin=0, vmax=1, annot_kws={'size': ANNOT_SIZE})
    plt.ylabel('Algorithm'); plt.xlabel('Load')
    mem_png = Path(__file__).parent / 'algo_mem_utilization_heatmap.png'
    plt.tight_layout(); plt.savefig(mem_png, dpi=300)
    print(f'Wrote: {mem_png}')
    plt.close()

if __name__ == '__main__':
    main()