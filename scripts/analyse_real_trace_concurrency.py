import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os
from matplotlib import rcParams

# 设置全局字体为Times New Roman
rcParams['font.family'] = 'Times New Roman'

# 数据集路径（根据实际情况调整）
trace_file = '../azurefunctions-dataset2019/invocations_per_function_md.anon.d01.csv'

# 只读取前几列和全部分钟列，避免内存压力
# 先读取表头
with open(trace_file, 'r') as f:
    header = f.readline().strip().split(',')

minute_cols = header[4:]  # 1440列，对应一天每分钟
usecols = header[:4] + minute_cols

print('Loading large file, please wait...')
df = pd.read_csv(trace_file, usecols=usecols)

# 1. Total requests per minute (platform-wide)
minute_matrix = df[minute_cols].values  # shape: (num_functions, 1440)
total_req_per_min = minute_matrix.sum(axis=0)  # shape: (1440,)

plt.figure(figsize=(8,3))
plt.hist(total_req_per_min, bins=100, color='royalblue', edgecolor='k', alpha=0.8)
plt.xlabel('Total Requests per Minute', fontsize=13)
plt.ylabel('Frequency (Minutes)', fontsize=13)
plt.title('Distribution of Total Requests per Minute (Azure Functions Trace)', fontsize=14)
plt.tight_layout()
plt.savefig('real_trace_total_req_per_min_hist.png', dpi=300)
plt.close()

# 2. Concurrent functions per minute (number of functions with requests)
concurrent_func_per_min = (minute_matrix > 0).sum(axis=0)

plt.figure(figsize=(8,3))
plt.hist(concurrent_func_per_min, bins=100, color='tomato', edgecolor='k', alpha=0.8)
plt.xlabel('Concurrent Function Types per Minute', fontsize=13)
plt.ylabel('Frequency (Minutes)', fontsize=13)
plt.title('Distribution of Concurrent Function Types per Minute (Azure Functions Trace)', fontsize=14)
plt.tight_layout()
plt.savefig('real_trace_concurrent_func_per_min_hist.png', dpi=300)
plt.close()

print('Analysis complete. Images saved as real_trace_total_req_per_min_hist.png and real_trace_concurrent_func_per_min_hist.png.') 