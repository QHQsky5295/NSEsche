use crate::config::Config;
use crate::mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes};
use crate::with_env_sub::WithEnvCore;
use crate::{
    mechanism::{MechanismImpl, ScheCmd, SimEnvObserve},
    sim_run::{schedule_helper, Scheduler},
};
use rand::prelude::SliceRandom;
use rand_pcg::Pcg64;
use rand_seeder::Seeder;

pub struct RandomScheduler {
    rng: Pcg64,
}

impl RandomScheduler {
    pub fn new(config: &Config) -> Self {
        Self {
            rng: Seeder::from(&format!("random-placement:{}", config.algorithm_seed())).make_rng(),
        }
    }
}

impl Scheduler for RandomScheduler {
    fn schedule_some(
        &mut self,
        env: &SimEnvObserve,
        mech: &MechanismImpl,
        cmd_distributor: &MechCmdDistributor,
    ) {
        for (_req_id, req) in env.core().requests().iter() {
            let fns = schedule_helper::collect_task_to_sche(
                req,
                env,
                schedule_helper::CollectTaskConfig::All,
            );

            for fnid in fns {
                let nodesid = schedule_helper::placement_candidate_ids(req, fnid, env);

                let nodeid = if let Some(node) = nodesid.choose(&mut self.rng) {
                    node
                } else {
                    // 处理没有可用节点的情况，例如记录日志或返回错误
                    eprintln!("No available nodes for scheduling");
                    return;
                };

                // 创建调度命令，使用 match 进行错误处理
                match cmd_distributor.send(MechScheduleOnceRes::ScheCmd(ScheCmd {
                    nid: *nodeid,
                    reqid: req.req_id,
                    fnid,
                    memlimit: None,
                })) {
                    Ok(_) => {
                        // 发送成功，继续处理
                    }
                    Err(e) => {
                        // 发送失败，记录错误但不崩溃
                        log::warn!(
                            "Failed to send schedule command for fn {} to node {}: {:?}",
                            fnid,
                            nodeid,
                            e
                        );
                    }
                }
            }
        }
    }
}
