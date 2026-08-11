use std::{
    cmp::Ordering,
    collections::{BinaryHeap, HashMap, HashSet},
};

use crate::{
    fn_dag::{FnContainerState, FnId},
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes},
    node::{EnvNodeExt, NodeId},
    request::ReqId,
    sim_run::{schedule_helper, Scheduler},
    with_env_sub::WithEnvCore,
};

/// A warm worker advertised to Hiku's pull queue.  `Ord` is reversed so a
/// `BinaryHeap` pops the least-connected worker and then the smallest node id.
#[derive(Clone, Debug)]
struct WorkerState {
    node_id: NodeId,
    active_connections: usize,
}

impl PartialEq for WorkerState {
    fn eq(&self, other: &Self) -> bool {
        self.node_id == other.node_id && self.active_connections == other.active_connections
    }
}

impl Eq for WorkerState {}

impl PartialOrd for WorkerState {
    fn partial_cmp(&self, other: &Self) -> Option<Ordering> {
        Some(self.cmp(other))
    }
}

impl Ord for WorkerState {
    fn cmp(&self, other: &Self) -> Ordering {
        other
            .active_connections
            .cmp(&self.active_connections)
            .then_with(|| other.node_id.cmp(&self.node_id))
    }
}

/// Placement-only Hiku adaptation.
///
/// Idle running containers advertise themselves through per-function pull
/// queues.  Hiku emits placement commands only; HPA and the common container
/// manager create, start, and evict all instances.
pub struct HikuScheduler {
    idle_workers: HashMap<FnId, BinaryHeap<WorkerState>>,
    scheduled_pairs: HashSet<(ReqId, FnId)>,
}

impl HikuScheduler {
    pub fn new() -> Self {
        Self {
            idle_workers: HashMap::new(),
            scheduled_pairs: HashSet::new(),
        }
    }

    fn rebuild_idle_worker_queues(&mut self, env: &SimEnvObserve) {
        self.idle_workers.clear();
        for node in env.nodes().iter() {
            let node_id = node.node_id();
            for (fn_id, container) in node.fn_containers.borrow().iter() {
                if matches!(container.state(), FnContainerState::Running)
                    && container.req_fn_state.is_empty()
                {
                    self.idle_workers
                        .entry(*fn_id)
                        .or_default()
                        .push(WorkerState {
                            node_id,
                            active_connections: node.all_task_cnt(),
                        });
                }
            }
        }
    }

    fn pull_idle_worker(&mut self, fn_id: FnId, candidates: &HashSet<NodeId>) -> Option<NodeId> {
        let queue = self.idle_workers.get_mut(&fn_id)?;
        while let Some(worker) = queue.pop() {
            if candidates.contains(&worker.node_id) {
                // Do not return it to the idle queue during this decision pass:
                // a successfully sent task makes this worker non-idle.
                return Some(worker.node_id);
            }
        }
        None
    }

    fn least_connected_fallback(
        &self,
        fn_id: FnId,
        candidates: &HashSet<NodeId>,
        projected: &HashMap<NodeId, usize>,
        env: &SimEnvObserve,
    ) -> Option<NodeId> {
        candidates.iter().copied().min_by_key(|node_id| {
            let node = env.node(*node_id);
            let container_rank = node
                .fn_containers
                .borrow()
                .get(&fn_id)
                .map(|container| match container.state() {
                    FnContainerState::Running => 0,
                    FnContainerState::Starting { .. } => 1,
                })
                .unwrap_or(2);
            (
                container_rank,
                node.all_task_cnt() + projected.get(node_id).copied().unwrap_or(0),
                *node_id,
            )
        })
    }

    fn prune_request_state(&mut self, _env: &SimEnvObserve) {
        self.scheduled_pairs.clear();
    }
}

impl Scheduler for HikuScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        _mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        self.prune_request_state(env);
        self.rebuild_idle_worker_queues(env);
        let mut projected: HashMap<NodeId, usize> = HashMap::new();

        for (_, req) in env.core().requests().iter() {
            let functions = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            );
            for fn_id in functions {
                let key = (req.req_id, fn_id);
                if self.scheduled_pairs.contains(&key) {
                    continue;
                }

                let candidates: HashSet<NodeId> =
                    schedule_helper::placement_candidate_ids(req, fn_id, env)
                        .into_iter()
                        .collect();
                if candidates.is_empty() {
                    continue;
                }
                let pulled_idle_worker = self.pull_idle_worker(fn_id, &candidates);
                let node_id = pulled_idle_worker
                    .or_else(|| self.least_connected_fallback(fn_id, &candidates, &projected, env));
                let Some(node_id) = node_id else {
                    continue;
                };

                match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                    nid: node_id,
                    reqid: req.req_id,
                    fnid: fn_id,
                    memlimit: None,
                })) {
                    Ok(()) => {
                        self.scheduled_pairs.insert(key);
                        *projected.entry(node_id).or_default() += 1;
                    }
                    Err(error) => {
                        if pulled_idle_worker.is_some() {
                            self.idle_workers
                                .entry(fn_id)
                                .or_default()
                                .push(WorkerState {
                                    node_id,
                                    active_connections: env.node(node_id).all_task_cnt(),
                                });
                        }
                        log::warn!(
                            "Hiku-P failed to place request {} function {} on node {}: {:?}",
                            req.req_id,
                            fn_id,
                            node_id,
                            error
                        );
                    }
                }
            }
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn worker_queue_pulls_least_connected_then_smallest_id() {
        let mut queue = BinaryHeap::new();
        queue.push(WorkerState {
            node_id: 8,
            active_connections: 1,
        });
        queue.push(WorkerState {
            node_id: 3,
            active_connections: 1,
        });
        queue.push(WorkerState {
            node_id: 1,
            active_connections: 4,
        });
        assert_eq!(queue.pop().map(|worker| worker.node_id), Some(3));
        assert_eq!(queue.pop().map(|worker| worker.node_id), Some(8));
    }
}
