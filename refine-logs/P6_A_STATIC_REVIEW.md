# P6-A 静态审查与 V8 交接

日期：2026-09-05（Asia/Shanghai）
审查对象：三份 P6-A 文档、V8 总计划及当前计划指针。
结论：文档可进入 P6-B1 小场景验证/共同实现；不代表 pilot 或性能目标已通过。

## 1. 核验依据

源码起点 075fee8be96d732113d317da004d6f7b99277cb1。
本轮未运行 simulator、cargo 或 reference builder；检查时无 serverless/cargo/rustc
进程，也无 runs 下 P6 目录或 target_p6 目录。

P5 gate 实读 run_count=90，12 项中仅 usable_cohort=false，其余11项为true。
P1 FREEZE_MANIFEST.csv 的30条文件长度与SHA-256逐项通过；加manifest为31文件。
该核验确认包未改变，不重新扩大 P1 的理论或经验结论。

矩阵算术复核：
- 旧实验 600+240+240+600+120 = 1800；
- 新 burst/QoS/近邻 300+200+80 = 580；
- 正式 online 总计2380；
- P6 pilot90，duplicate1；九个NSESche references另计。

## 2. 审查中修正的实质问题

- 工作量分层挑选没有必要性依据，且会改变随机DAG分布。已撤回未提交草案中的
  pool/sub-band/rate接受门，改用P6P01--P6P03固定输入；rho_cpu只作描述。
- PreAllDone 是明确披露的研究边界，不是从论文空白推出的唯一正确规则。其他
  方法的adaptation删减仍需逐项核实，尤其不可把简化FaaSRank当完整DRL复现。
- HPA未来pending和基础memory使idle target难以归零的路径有源码依据；P5日志
  尚未证明它是全部停滞的唯一原因，实施前必须有针对性fixtures。
- running_task_cnt包含等待中的resident entries。已停止把它当成正在计算的任务数。
- D_drain 是有上限的执行预算，不是终止证明；超过预算仍保留输入/删失。
  stall诊断不提前终止，因为HPA history等状态可能尚在变化。
- fixed-window cost分子是全平台累计成本，含未完成工作消耗；文档改称共同
  completed denominator，避免错误宣称三个量只涉及同一批已完成请求的资源费用。
- 当前baseline确实创建posthoc welfare observer。省81次reference需先实现显式
 关闭并验证action不变，不能在未改实现时假定baseline不依赖reference。
- 旧实验20次保持；扩展仅NSESche且负载同比增长，符合目标文件与R2-6。
- 用户已有持续执行授权。测试、阶段审查和常规实现可继续，不凭本计划反复请求许可。

## 3. 被审文件内容哈希（工作区 UTF-8 文件）

| 文件 | SHA-256 |
|---|---|
| P6_COMMON_ELIGIBILITY_AND_BATCHING_DERIVATION.md | 03c9e26af3dccbf9845ae72e6b67a7e19834d0daaef91fc5bbbb4f47428b0038 |
| P6_WORKLOAD_STRATIFICATION_AND_DRAIN_DERIVATION.md | 3523e7670585cd6599bb7b89f39f269299c84048467586c6d5373ef82f127337 |
| P6_COMMON_PLATFORM_PROTOCOL_PREREGISTRATION.md | 800ae43050436d9e2d2b8a06522c0d4968a36a12158e404a4722d10c710b58f2 |
| TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V8.md | cb3436d7d5ea84339a7d5c29e37e094026e547b3b9fea03df64a0632a7556105 |

原工作区 sche_nash.rs SHA-256：
bd106e4646ff6d56ae8dceceb731945667034dc46eb87aaf58da368e19f75814。
原工作区（NSESche）PLAN.md SHA-256：
19ed3f8dc104b4ce26c81c4b0cfb651ad16ac7083b22262c2a7e0b81b238ce99。
本轮只编辑revision下列明的计划文档，原文件用于只读核验。

## 4. 下一步可验证的交付

1. fixture：一个空闲running container、无ready/resident、positive基础memory；
   当前HPA返回非零，新规则应满足allow_scale_to_zero和min_instances。
2. fixture：future descendant不触发ready floor；ready请求触发floor；resident/
   starting work不被误删；tolerance不能绕过min/max/floor。
3. fixture：多node idle scale-down稳定选取；batch遗漏/额外/重复非法node必须失败。
4. 在reviewer-v5启用修正，历史reviewer-v3/v4重放路径保留；之后实现共享index、
   observer开关、drain/recorder合约，完整回归后才构建pilot输入。

本阶段没有新的throughput/QPR。P1可用于其冻结版本的写作材料；同构性能尚未闭口，
异构、扩展和审稿补充性能矩阵仍待执行。先前目标轮次分类为progress：
产生P5停滞证据、三份草案并修正其统计/因果边界；不存在需要标记blocked的外部障碍。
