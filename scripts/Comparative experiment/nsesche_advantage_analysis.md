# NSESche算法优势分析报告
## 📊 图表保留建议
### ✅ 请求失败率分析 - **推荐保留**
**相关图表:** failure_rate_heatmap.png, detailed_failure_analysis.png
**NSESche优势:**
- High Load: 优于 9/9 个算法 (100.0%)
  - 比Random提升 53.1%
  - 比Greedy提升 52.8%
  - 比Hash提升 52.7%
- Low Load: 优于 6/9 个算法 (66.7%)
  - 比Orion提升 86.6%
  - 比Random提升 84.8%
  - 比Jiagu提升 84.2%
- Middle Load: 优于 6/9 个算法 (66.7%)
  - 比Hash提升 39.3%
  - 比Load Balance提升 38.2%
  - 比Random提升 33.7%
- High Load: 优于 9/9 个算法 (100.0%)
  - 比Greedy提升 2156.1%
  - 比Jiagu提升 1011.1%
  - 比Orion提升 718.9%
- Low Load: 优于 6/9 个算法 (66.7%)
  - 比Orion提升 553.8%
  - 比Random提升 273.6%
  - 比Jiagu提升 232.7%
- Middle Load: 优于 6/9 个算法 (66.7%)
  - 比Hash提升 883.8%
  - 比Load Balance提升 513.5%
  - 比Random提升 216.5%

### ✅ 成本效率分析 - **推荐保留**
**相关图表:** cost_efficiency_boxplots.png, cost_efficiency_by_load.png, cost_distribution_analysis.png
**NSESche优势:**
- High Load: 优于 9/9 个算法 (100.0%)
  - 比Greedy提升 96.8%
  - 比Orion提升 89.4%
  - 比Jiagu提升 82.3%
- Low Load: 优于 7/9 个算法 (77.8%)
  - 比Load Balance提升 77.3%
  - 比Random提升 73.3%
  - 比Orion提升 71.4%
- Middle Load: 优于 8/9 个算法 (88.9%)
  - 比Load Balance提升 91.1%
  - 比Hash提升 89.4%
  - 比OCS提升 69.4%
- Low Load: 优于 9/9 个算法 (100.0%)
  - 比Random提升 84.6%
  - 比FaasRank提升 79.0%
  - 比Greedy提升 77.6%
- High Load: 优于 9/9 个算法 (100.0%)
  - 比Greedy提升 2156.1%
  - 比Jiagu提升 1011.1%
  - 比Orion提升 718.9%
- Low Load: 优于 6/9 个算法 (66.7%)
  - 比Orion提升 553.8%
  - 比Random提升 273.6%
  - 比Jiagu提升 232.7%
- Middle Load: 优于 6/9 个算法 (66.7%)
  - 比Hash提升 883.8%
  - 比Load Balance提升 513.5%
  - 比Random提升 216.5%

### ✅ 容器利用率分析 - **推荐保留**
**相关图表:** container_utilization_heatmap.png, resource_utilization_heatmap.png, overhead_analysis_heatmap.png, container_count_heatmap.png
**NSESche优势:**
- Middle Load: 优于 5/9 个算法 (55.6%)
  - 比OCS提升 37.8%
  - 比Hiku提升 21.5%
  - 比Greedy提升 19.2%
- Low Load: 优于 7/9 个算法 (77.8%)
  - 比Random提升 82.2%
  - 比Greedy提升 62.9%
  - 比Jiagu提升 36.2%
- Middle Load: 优于 8/9 个算法 (88.9%)
  - 比Orion提升 70.7%
  - 比Random提升 69.2%
  - 比Load Balance提升 63.5%
- High Load: 优于 6/9 个算法 (66.7%)
  - 比Random提升 86.0%
  - 比FaasRank提升 76.9%
  - 比Load Balance提升 72.3%
- Low Load: 优于 8/9 个算法 (88.9%)
  - 比FaasRank提升 90.7%
  - 比Random提升 88.8%
  - 比Greedy提升 87.5%
- Middle Load: 优于 8/9 个算法 (88.9%)
  - 比OCS提升 96.0%
  - 比Random提升 95.7%
  - 比Load Balance提升 95.1%

## 📈 详细指标分析
### 延迟时间
**Low Load:**
- NSESche值: 34.066
- 优于算法数: 9/9
- 平均提升: 60.6%

### 成本
**High Load:**
- NSESche值: 0.306
- 优于算法数: 9/9
- 平均提升: 71.2%

**Low Load:**
- NSESche值: 0.314
- 优于算法数: 7/9
- 平均提升: 50.3%

**Middle Load:**
- NSESche值: 0.312
- 优于算法数: 8/9
- 平均提升: 58.2%

### 吞吐量
**High Load:**
- NSESche值: 2.211
- 优于算法数: 9/9
- 平均提升: 594.9%

**Low Load:**
- NSESche值: 1.700
- 优于算法数: 6/9
- 平均提升: 228.4%

**Middle Load:**
- NSESche值: 1.092
- 优于算法数: 6/9
- 平均提升: 311.8%

### 失败率
**High Load:**
- NSESche值: 25713.000
- 优于算法数: 9/9
- 平均提升: 26.4%

**Low Load:**
- NSESche值: 223.000
- 优于算法数: 6/9
- 平均提升: 78.5%

**Middle Load:**
- NSESche值: 1482.000
- 优于算法数: 6/9
- 平均提升: 29.6%

### 冷启动时间
**Low Load:**
- NSESche值: 20.006
- 优于算法数: 7/9
- 平均提升: 41.5%

**Middle Load:**
- NSESche值: 31.519
- 优于算法数: 8/9
- 平均提升: 44.6%

### 执行时间
**High Load:**
- NSESche值: 46.109
- 优于算法数: 6/9
- 平均提升: 65.1%

**Low Load:**
- NSESche值: 11.894
- 优于算法数: 8/9
- 平均提升: 82.4%

**Middle Load:**
- NSESche值: 11.281
- 优于算法数: 8/9
- 平均提升: 91.9%

### 容器数量
**Middle Load:**
- NSESche值: 116.384
- 优于算法数: 5/9
- 平均提升: 21.2%

## 🎯 总结建议
### 推荐保留的图表:
- failure_rate_heatmap.png
- detailed_failure_analysis.png
- cost_efficiency_boxplots.png
- cost_efficiency_by_load.png
- cost_distribution_analysis.png
- container_utilization_heatmap.png
- resource_utilization_heatmap.png
- overhead_analysis_heatmap.png
- container_count_heatmap.png

### 核心优势总结:
NSESche在以下指标上表现突出:
- 成本
- 吞吐量
- 失败率
- 冷启动时间
- 执行时间
