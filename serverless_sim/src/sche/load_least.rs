use std::{
    cmp::Ordering,
    collections::{HashMap, HashSet},
};

use crate::{
    fn_dag::{EnvFnExt, FnId},
    mechanism::{DownCmd, MechType, MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{self, EnvNodeExt, Node, NodeId},
    sche,
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::WithEnvCore,
};

pub struct LoadLeastScheduler {
    fn_nodes: HashMap<FnId, HashSet<NodeId>>,
    node_cpu_usage: HashMap<NodeId, usize>,
}

impl LoadLeastScheduler {
    pub fn new() -> Self {
        Self {
            fn_nodes: HashMap::new(),
            node_cpu_usage: HashMap::new(),
        }
    }

    fn select_best_node_to_fn(&self, nodes: &[NodeId]) -> Option<NodeId> {
        nodes.iter().copied().min_by_key(|node_id| {
            (
                self.node_cpu_usage
                    .get(node_id)
                    .copied()
                    .unwrap_or(usize::MAX),
                *node_id,
            )
        })
    }
}

impl Scheduler for LoadLeastScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        // 遍历每个节点，更新其资源使用情况
        for node in env.core().nodes().iter() {
            // 任务数量
            let all_task_cnt = node.all_task_cnt();
            self.node_cpu_usage.insert(node.node_id(), all_task_cnt);
        }

        for func in env.core().fns().iter() {
            let nodes = env
                .core()
                .fn_2_nodes()
                .get(&func.fn_id)
                .map(|v| v.clone())
                .unwrap_or(HashSet::new());

            // log::info!("fn {}, nodes.len() = {}", func.fn_id, nodes.len());
            self.fn_nodes.insert(func.fn_id, nodes.clone());
        }

        for (_req_id, req) in env.core().requests().iter() {
            let fns = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            );

            //迭代请求中的函数，选择最合适的节点进行调度
            for fnid in fns {
                let candidates = schedule_helper::placement_candidate_ids(req, fnid, env);
                let Some(sche_nodeid) = self.select_best_node_to_fn(&candidates) else {
                    log::warn!("No placement-feasible node found for function {}", fnid);
                    continue;
                };

                log::info!("schedule fn {} to node {}", fnid, sche_nodeid);

                {
                    // 使用 match 进行错误处理，避免 panic
                    match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                        nid: sche_nodeid,
                        reqid: req.req_id,
                        fnid,
                        memlimit: None,
                    })) {
                        Ok(_) => {
                            // 发送成功，更新节点任务数量
                            let tasks_cnt = self.node_cpu_usage.get(&sche_nodeid).unwrap();
                            self.node_cpu_usage.insert(sche_nodeid, tasks_cnt + 1);
                        }
                        Err(e) => {
                            // 发送失败，记录错误但不崩溃
                            log::warn!(
                                "Failed to send schedule command for fn {} to node {}: {:?}",
                                fnid,
                                sche_nodeid,
                                e
                            );
                            // 可以选择继续处理其他任务，或者采取其他恢复策略
                        }
                    }
                }
            }
        }
    }
}
