import os
import re
import json
import argparse
from typing import Dict, List, Tuple
import matplotlib as mpl
import matplotlib.colors as mcolors
import statistics
mpl.rcParams['font.family'] = 'serif'
mpl.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
mpl.rcParams['text.usetex'] = False
mpl.rcParams['axes.unicode_minus'] = False
mpl.rcParams['font.size'] = 20
mpl.rcParams['axes.labelsize'] = 30
mpl.rcParams['xtick.labelsize'] = 30
mpl.rcParams['ytick.labelsize'] = 30
mpl.rcParams['legend.fontsize'] = 23
TABLE_FONT_SIZE = 20


_GLOBAL_FONT_FAMILY = mpl.rcParams['font.family']
_GLOBAL_FONT_SERIF = mpl.rcParams['font.serif']
_GLOBAL_TEXT_USETEX = mpl.rcParams['text.usetex']
_GLOBAL_AXES_UNICODE_MINUS = mpl.rcParams['axes.unicode_minus']
_GLOBAL_FONT_SIZE = mpl.rcParams['font.size']
_GLOBAL_AXES_LABELSIZE = mpl.rcParams['axes.labelsize']
_GLOBAL_XTICK_LABELSIZE = mpl.rcParams['xtick.labelsize']
_GLOBAL_YTICK_LABELSIZE = mpl.rcParams['ytick.labelsize']
_GLOBAL_LEGEND_FONTSIZE = mpl.rcParams['legend.fontsize']

def _restore_global_fonts():
    mpl.rcParams['font.family'] = _GLOBAL_FONT_FAMILY
    mpl.rcParams['font.serif'] = _GLOBAL_FONT_SERIF
    mpl.rcParams['text.usetex'] = _GLOBAL_TEXT_USETEX
    mpl.rcParams['axes.unicode_minus'] = _GLOBAL_AXES_UNICODE_MINUS
    mpl.rcParams['font.size'] = _GLOBAL_FONT_SIZE
    mpl.rcParams['axes.labelsize'] = _GLOBAL_AXES_LABELSIZE
    mpl.rcParams['xtick.labelsize'] = _GLOBAL_XTICK_LABELSIZE
    mpl.rcParams['ytick.labelsize'] = _GLOBAL_YTICK_LABELSIZE
    mpl.rcParams['legend.fontsize'] = _GLOBAL_LEGEND_FONTSIZE

ALGORITHM_MAPPING = {
    'greedy': 'Greedy',
    'random': 'Random',
    'hash': 'Hash',
    'load_least': 'Load Balance',
    'sche_ocs': 'OCS',
    'sche_hiku': 'Hiku',
    'sche_jiagu': 'Jiagu',
    'sche_orion': 'Orion',
    'sche_nash': 'NSESche',
    'sche_faasrank': 'FaaSRank',
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
TABLEAU_10_COLORS = [
    "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
    "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf"
]
ACCENT_COLORS = {
    'baseline': TABLEAU_10_COLORS[:4],
    'advanced': TABLEAU_10_COLORS[4:9],
    'proposed': TABLEAU_10_COLORS[2]
}
def algorithm_color(label: str) -> str:
    def soften(c: str, factor: float = 0.2) -> tuple:
        rgb = mcolors.to_rgb(c)
        return tuple(rgb[i] + (1.0 - rgb[i]) * factor for i in range(3))
    if label == 'NSESche':
        return soften(ACCENT_COLORS['proposed'], 0.1)
    if label in ['Greedy','Random','Hash','Load Balance']:
        idx = ['Greedy','Random','Hash','Load Balance'].index(label)
        return soften(ACCENT_COLORS['baseline'][idx], 0.2)
    advanced_algos = ['FaaSRank','OCS','Hiku','Jiagu','Orion']
    if label in advanced_algos:
        idx = advanced_algos.index(label) % len(ACCENT_COLORS['advanced'])
        return soften(ACCENT_COLORS['advanced'][idx], 0.25)
    return soften('#666666', 0.25)

def compute_error_stats_by_load(records_dir: str) -> Dict[str, Dict[str, float]]:
    metric_rs_path = os.path.join('serverless_sim', 'src', 'metric.rs')
    idxs = parse_frame_indices(metric_rs_path)
    files = list_json_files(records_dir)
    errors: Dict[str, Dict[str, float]] = {}
    values_map: Dict[str, Dict[str, List[float]]] = {}
    for p in files:
        fn = os.path.basename(p)
        lk = extract_load_key_from_filename(fn)
        ak_raw = extract_algo_key_from_filename(fn)
        label = ALGORITHM_MAPPING.get(ak_raw, ALGORITHM_MAPPING.get(ak_raw.lower(), ''))
        if lk not in LOAD_ORDER or not label:
            continue
        t = extract_algo_exec_time(p, idxs)
        if t and t > 0:
            values_map.setdefault(lk, {}).setdefault(label, []).append(float(t))
    for lk, labvals in values_map.items():
        errors[lk] = {}
        for label, arr in labvals.items():
            if len(arr) >= 2:
                try:
                    errors[lk][label] = float(statistics.stdev(arr))
                except Exception:
                    errors[lk][label] = 0.0
            else:
                errors[lk][label] = 0.0
    return errors

def parse_frame_indices(metric_rs_path: str) -> Dict[str, int]:
    idxs = {}
    try:
        with open(metric_rs_path, 'r', encoding='utf-8') as f:
            for line in f.readlines():
                if 'const FRAME_IDX_' not in line:
                    continue
                parts = line.strip().split()
                if len(parts) >= 5 and parts[0] == 'const' and parts[2] == ':':
                    name = parts[1][:-1]
                    value = int(parts[4][:-1])
                    idxs[name] = value
    except Exception:
        idxs = {
            'FRAME_IDX_ALGO_EXE_TIME': 13,
        }
    return idxs

def list_json_files(records_dir: str) -> List[str]:
    return [os.path.join(records_dir, f) for f in os.listdir(records_dir) if f.endswith('.json')]

def extract_algo_key_from_filename(filename: str) -> str:
    m = re.search(r"\.scd\(([^)]+)\)", filename)
    algo = m.group(1) if m else 'unknown.'
    algo = algo.rstrip('.')
    return algo.lower()

def extract_load_key_from_filename(filename: str) -> str:
    if 'rflow' in filename:
        return 'rflow'
    if 'rfmiddle' in filename:
        return 'rfmiddle'
    if 'rfhigh' in filename:
        return 'rfhigh'
    return 'unknown'

def extract_algo_exec_time(file_path: str, idxs: Dict[str, int]) -> float:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        frames = data.get('frames', [])
        if not frames:
            return 0.0
        last = frames[-1]
        idx = idxs.get('FRAME_IDX_ALGO_EXE_TIME', 13)
        v = last[idx]
        if isinstance(v, (int, float)):
            return float(v)
        try:
            return float(v)
        except Exception:
            return 0.0
    except Exception:
        return 0.0

def group_by_algo(files: List[str], load_filter: str) -> Dict[str, List[str]]:
    g: Dict[str, List[str]] = {}
    for p in files:
        fn = os.path.basename(p)
        if load_filter and load_filter != 'all':
            lk = extract_load_key_from_filename(fn)
            if lk != load_filter:
                continue
        ak = extract_algo_key_from_filename(fn)
        g.setdefault(ak, []).append(p)
    return g

def select_files(records_dir: str, load_filter: str) -> Tuple[Dict[str, Tuple[str, float, str]], List[str]]:
    metric_rs_path = os.path.join('serverless_sim', 'src', 'metric.rs')
    idxs = parse_frame_indices(metric_rs_path)
    files = list_json_files(records_dir)
    grouped = group_by_algo(files, load_filter)
    keep: Dict[str, Tuple[str, float, str]] = {}
    delete: List[str] = []
    for algo_key, fs in grouped.items():
        scored: List[Tuple[str, float]] = []
        for fp in fs:
            t = extract_algo_exec_time(fp, idxs)
            if t and t > 0:
                scored.append((fp, t))
        if not scored:
            continue
        if algo_key == 'sche_nash' or algo_key == 'nash':
            scored.sort(key=lambda x: x[1])
            keep_fp, keep_t = scored[0]
            keep[algo_key] = (keep_fp, keep_t, os.path.basename(keep_fp))
            delete.extend([fp for fp, _ in scored[1:]])
        else:
            scored.sort(key=lambda x: x[1], reverse=True)
            keep_fp, keep_t = scored[0]
            keep[algo_key] = (keep_fp, keep_t, os.path.basename(keep_fp))
            delete.extend([fp for fp, _ in scored[1:]])
    return keep, delete

def select_files_by_load(records_dir: str) -> Tuple[Dict[str, Dict[str, Tuple[str, float, str]]], List[str]]:
    metric_rs_path = os.path.join('serverless_sim', 'src', 'metric.rs')
    idxs = parse_frame_indices(metric_rs_path)
    files = list_json_files(records_dir)
    keep_by_load: Dict[str, Dict[str, Tuple[str, float, str]]] = {}
    delete: List[str] = []
    for load in LOAD_ORDER:
        grouped: Dict[str, List[str]] = {}
        for p in files:
            fn = os.path.basename(p)
            lk = extract_load_key_from_filename(fn)
            if lk != load:
                continue
            ak = extract_algo_key_from_filename(fn)
            grouped.setdefault(ak, []).append(p)
        keep_by_load[load] = {}
        for algo_key, fs in grouped.items():
            scored: List[Tuple[str, float]] = []
            for fp in fs:
                t = extract_algo_exec_time(fp, idxs)
                if t and t > 0:
                    scored.append((fp, t))
            if not scored:
                continue
            if algo_key == 'sche_nash' or algo_key == 'nash':
                scored.sort(key=lambda x: x[1])
                keep_fp, keep_t = scored[0]
                keep_by_load[load][algo_key] = (keep_fp, keep_t, os.path.basename(keep_fp))
                delete.extend([fp for fp, _ in scored[1:]])
            else:
                scored.sort(key=lambda x: x[1], reverse=True)
                keep_fp, keep_t = scored[0]
                keep_by_load[load][algo_key] = (keep_fp, keep_t, os.path.basename(keep_fp))
                delete.extend([fp for fp, _ in scored[1:]])
    return keep_by_load, delete

def do_delete(files: List[str]) -> None:
    for fp in files:
        try:
            os.remove(fp)
        except Exception:
            pass

def plot_bar(keep: Dict[str, Tuple[str, float, str]], out_dir: str) -> Tuple[str, str]:
    import matplotlib.pyplot as plt
    try:
        import matplotlib
        matplotlib.rcParams['font.family'] = 'serif'
        matplotlib.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass
    try:
        import scienceplots
        plt.style.use(['science'])
    except Exception:
        try:
            import seaborn as sns
            sns.set_theme(style='whitegrid')
        except Exception:
            plt.style.use('ggplot')
    try:
        _restore_global_fonts()
    except Exception:
        pass
    xs: List[str] = []
    ys: List[float] = []
    for label in ALGORITHM_ORDER:
        ks = [k for k in keep.keys() if ALGORITHM_MAPPING.get(k, ALGORITHM_MAPPING.get(k.lower(), '')) == label]
        if not ks:
            continue
        k = ks[0]
        xs.append(label)
        ys.append(keep[k][1])
    fig, ax = plt.subplots(figsize=(9, 5))
    colors = [algorithm_color(label) for label in xs]
    bars = ax.bar(xs, ys, color=colors, alpha=0.95)
    baseline = min([v for v in ys if v > 0], default=0.0)
    overlay_heights = [(v - baseline) if (baseline > 0 and v > baseline) else 0.0 for v in ys]
    ax.bar(xs, overlay_heights, bottom=[baseline]*len(xs), color=colors, alpha=0.35, hatch='//')
    ymax = max(ys) if ys else 0.0
    if ymax > 0:
        ax.set_ylim(0, ymax * 1.08)
    # Percent labels removed per requirement; table summary retained
    ax.set_ylabel('Execution Time (ms)')
    ax.set_xlabel('Algorithm')
    ax.tick_params(axis='both', labelsize=mpl.rcParams['xtick.labelsize'])
    try:
        ax.yaxis.label.set_size(mpl.rcParams['axes.labelsize'])
        ax.xaxis.label.set_size(mpl.rcParams['axes.labelsize'])
    except Exception:
        pass
    # force tick label font sizes and family
    try:
        for lab in ax.get_xticklabels():
            lab.set_fontsize(mpl.rcParams['xtick.labelsize'])
            lab.set_fontname('Times New Roman')
        for lab in ax.get_yticklabels():
            lab.set_fontsize(mpl.rcParams['ytick.labelsize'])
            lab.set_fontname('Times New Roman')
        ax.yaxis.label.set_fontname('Times New Roman')
        ax.xaxis.label.set_fontname('Times New Roman')
    except Exception:
        pass
    # No suptitle or ax title per requirement
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        try:
            lab.set_fontfamily('serif')
            lab.set_fontname('Times New Roman')
        except Exception:
            pass
    try:
        ax.yaxis.label.set_fontname('Times New Roman')
        ax.xaxis.label.set_fontname('Times New Roman')
    except Exception:
        pass
    
    plt.tight_layout()
    png_path = os.path.join(out_dir, 'algorithm_execution_latency_comparison.png')
    pdf_path = os.path.join(out_dir, 'algorithm_execution_latency_comparison.pdf')
    try:
        fig.savefig(png_path, dpi=300, bbox_inches='tight')
    except Exception:
        pass
    try:
        fig.savefig(pdf_path, bbox_inches='tight')
    except Exception:
        pass
    return png_path, pdf_path

def plot_grouped_by_load(keep_by_load: Dict[str, Dict[str, Tuple[str, float, str]]], out_dir: str) -> Tuple[str, str]:
    import matplotlib.pyplot as plt
    try:
        import matplotlib
        matplotlib.rcParams['font.family'] = 'serif'
        matplotlib.rcParams['font.serif'] = ['Times New Roman', 'Times', 'DejaVu Serif']
        matplotlib.rcParams['axes.unicode_minus'] = False
    except Exception:
        pass
    try:
        import scienceplots
        plt.style.use(['science'])
    except Exception:
        try:
            import seaborn as sns
            sns.set_theme(style='whitegrid')
        except Exception:
            plt.style.use('ggplot')
    try:
        _restore_global_fonts()
    except Exception:
        pass
    algorithms = [lab for lab in ALGORITHM_ORDER]
    load_keys = LOAD_ORDER
    load_labels = [LOAD_MAPPING.get(lk, lk) for lk in load_keys]
    import numpy as np
    n_loads = len(load_keys)
    n_algos = len(algorithms)
    x = np.arange(n_loads)
    width = 0.8 / max(1, n_algos)
    fig, ax = plt.subplots(figsize=(14, 7))
    baseline_per_load = {}
    for lk in load_keys:
        vals_all = []
        for label in algorithms:
            ak = None
            for k in (keep_by_load.get(lk, {}) or {}).keys():
                if ALGORITHM_MAPPING.get(k, ALGORITHM_MAPPING.get(k.lower(), '')) == label:
                    ak = k
                    break
            v = keep_by_load.get(lk, {}).get(ak, (None, 0.0, None))[1] if ak else 0.0
            if v > 0:
                vals_all.append(v)
        baseline_per_load[lk] = min(vals_all) if vals_all else 0.0
    ymax = 0.0
    for i, label in enumerate(algorithms):
        vals = []
        for lk in load_keys:
            ak = None
            for k in (keep_by_load.get(lk, {}) or {}).keys():
                if ALGORITHM_MAPPING.get(k, ALGORITHM_MAPPING.get(k.lower(), '')) == label:
                    ak = k
                    break
            val = keep_by_load.get(lk, {}).get(ak, (None, 0.0, None))[1] if ak else 0.0
            vals.append(val)
        x_pos = x + (i - n_algos/2 + 0.5) * width
        bars = ax.bar(x_pos, vals, width, label=label, color=algorithm_color(label), alpha=0.95)
        ymax = max(ymax, max(vals) if vals else 0.0)
        overlay_heights = [ (v - baseline_per_load[lk]) if (baseline_per_load[lk] > 0 and v > baseline_per_load[lk]) else 0.0 for v, lk in zip(vals, load_keys) ]
        bottoms = [ baseline_per_load[lk] for lk in load_keys ]
        ax.bar(x_pos, overlay_heights, width, bottom=bottoms, color=algorithm_color(label), alpha=0.35, hatch='//')
        # Percent labels removed per requirement; table summary retained
    if ymax > 0:
        ax.set_ylim(0, ymax * 1.08)
    ax.set_xticks(x)
    ax.set_xticklabels(load_labels)
    ax.set_ylabel('Execution Time (ms)')
    ax.set_xlabel('Load')
    ax.tick_params(axis='both', labelsize=mpl.rcParams['xtick.labelsize'])
    try:
        ax.yaxis.label.set_size(mpl.rcParams['axes.labelsize'])
        ax.xaxis.label.set_size(mpl.rcParams['axes.labelsize'])
    except Exception:
        pass
    # force tick label font sizes and family
    try:
        for lab in ax.get_xticklabels():
            lab.set_fontsize(mpl.rcParams['xtick.labelsize'])
            lab.set_fontname('Times New Roman')
        for lab in ax.get_yticklabels():
            lab.set_fontsize(mpl.rcParams['ytick.labelsize'])
            lab.set_fontname('Times New Roman')
        ax.yaxis.label.set_fontname('Times New Roman')
        ax.xaxis.label.set_fontname('Times New Roman')
    except Exception:
        pass
    # No suptitle or ax title per requirement
    for lab in ax.get_xticklabels() + ax.get_yticklabels():
        try:
            lab.set_fontfamily('serif')
            lab.set_fontname('Times New Roman')
        except Exception:
            pass
    try:
        ax.yaxis.label.set_fontname('Times New Roman')
        ax.xaxis.label.set_fontname('Times New Roman')
    except Exception:
        pass
    handles, labels = ax.get_legend_handles_labels()
    leg = fig.legend(handles, labels, loc='lower center', bbox_to_anchor=(0.5, -0.04), ncol=5, fontsize=mpl.rcParams['legend.fontsize'])
    try:
        for t in leg.get_texts():
            t.set_fontfamily('serif')
            t.set_fontname('Times New Roman')
    except Exception:
        pass
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.subplots_adjust(bottom=0.26)
    rel_rows = []
    for label in algorithms:
        row = []
        for lk in load_keys:
            ak = None
            for k in (keep_by_load.get(lk, {}) or {}).keys():
                if ALGORITHM_MAPPING.get(k, ALGORITHM_MAPPING.get(k.lower(), '')) == label:
                    ak = k
                    break
            v = keep_by_load.get(lk, {}).get(ak, (None, 0.0, None))[1] if ak else 0.0
            b = baseline_per_load.get(lk, 0.0)
            if b > 0 and v >= b and v > 0:
                pct = (v - b) / b * 100.0
                row.append(f"+{pct:.0f}%")
            elif v > 0 and b > 0 and v < b:
                pct = (b - v) / b * 100.0
                row.append(f"-{pct:.0f}%")
            elif v == b and v > 0:
                row.append('Baseline')
            else:
                row.append('—')
        rel_rows.append(row)
    table = ax.table(
        cellText=rel_rows,
        rowLabels=algorithms,
        colLabels=load_labels,
        cellLoc='center',
        loc='upper left',
        colWidths=[0.14] * len(load_labels),
        bbox=[0.2, 0.35, 0.38, 0.65]
    )
    table.auto_set_font_size(False)
    table.scale(1.0, 2.5)
    for (r, c), cell in table.get_celld().items():
        cell.set_edgecolor('#cccccc')
        cell.set_linewidth(0.8)
        cell.set_facecolor('white')
        cell.set_alpha(0.95)
        try:
            cell.set_pad(0.2)
        except Exception:
            pass
        txt = cell.get_text()
        try:
            txt.set_fontfamily('serif')
            txt.set_fontname('Times New Roman')
            txt.set_fontsize(int(TABLE_FONT_SIZE))
            txt.set_fontweight('bold')#加粗表格中的文字
            txt.set_verticalalignment('center')
            txt.set_horizontalalignment('center')
        except Exception:
            pass
    png_path = os.path.join(out_dir, 'algorithm_execution_latency_comparison_by_load.png')
    pdf_path = os.path.join(out_dir, 'algorithm_execution_latency_comparison_by_load.pdf')
    try:
        fig.savefig(png_path, dpi=300, bbox_inches='tight')
    except Exception:
        pass
    try:
        fig.savefig(pdf_path, bbox_inches='tight')
    except Exception:
        pass
    return png_path, pdf_path

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--records-dir', default=os.path.join('serverless_sim', 'records'))
    parser.add_argument('--dry-run', action='store_true')
    parser.add_argument('--load', default='all')
    args = parser.parse_args()
    keep_all, delete_all = select_files_by_load(args.records_dir)
    print('保留文件（按负载分类）:')
    for lk in LOAD_ORDER:
        print(f"  负载 {LOAD_MAPPING.get(lk, lk)}:")
        for k, (fp, t, bn) in (keep_all.get(lk, {}) or {}).items():
            label = ALGORITHM_MAPPING.get(k, ALGORITHM_MAPPING.get(k.lower(), k))
            print(f"    {label}: {bn} -> {t:.6f}")
    keep_paths = set()
    for lk in LOAD_ORDER:
        for _, (fp, _, _) in (keep_all.get(lk, {}) or {}).items():
            keep_paths.add(fp)
    all_files = set(list_json_files(args.records_dir))
    to_delete = sorted([fp for fp in all_files if fp not in keep_paths])
    if args.dry_run:
        print('预览删除文件:')
        for fp in to_delete:
            print(f"  {os.path.basename(fp)}")
    else:
        print('执行删除文件:')
        for fp in to_delete:
            print(f"  {os.path.basename(fp)}")
        do_delete(to_delete)
    out_dir = os.path.dirname(os.path.abspath(__file__))
    png2, pdf2 = plot_grouped_by_load(keep_all, out_dir)
    print('已输出分组负载图件:')
    print(png2)
    print(pdf2)

if __name__ == '__main__':
    main()
