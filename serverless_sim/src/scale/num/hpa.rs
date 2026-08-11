use std::collections::HashMap;

use crate::fn_dag::EnvFnExt;
use crate::mechanism::SimEnvObserve;
use crate::node::EnvNodeExt;

use crate::with_env_sub::WithEnvHelp;
use crate::{actions::ESActionWrapper, config::HpaProtocolConfig, fn_dag::FnId};

use super::{
    down_filter::{CarefulScaleDownFilter, ScaleFilter},
    ScaleNum,
};

pub enum Target {
    MemUseRate(f32),
}

pub struct HpaScaleNum {
    target: Target,
    // target_tolerance: determines how close the target/current
    //   resource ratio must be to 1.0 to skip scaling
    target_tolerance: f32,
    pub scale_down_policy: Box<dyn ScaleFilter + Send>,
    fn_sche_container_count: HashMap<FnId, usize>,
    min_instances_when_pending: usize,
    allow_scale_to_zero: bool,
    min_instances: usize,
    max_instances: Option<usize>,
}

impl HpaScaleNum {
    pub fn new() -> Self {
        Self::from_config(&HpaProtocolConfig::default())
    }

    pub fn from_config(config: &HpaProtocolConfig) -> Self {
        Self {
            target: Target::MemUseRate(config.target_mem_use_rate),
            target_tolerance: config.tolerance,
            scale_down_policy: Box::new(CarefulScaleDownFilter::with_history(
                config.careful_down_history,
            )),
            fn_sche_container_count: HashMap::new(),
            min_instances_when_pending: config.min_instances_when_pending,
            allow_scale_to_zero: config.allow_scale_to_zero,
            min_instances: config.min_instances,
            max_instances: config.max_instances,
        }
    }

    pub fn set_target(&mut self, tar: Target) {
        self.target = tar;
    }
}

impl ScaleNum for HpaScaleNum {
    fn scale_for_fn(
        &mut self,
        env: &SimEnvObserve,
        fnid: FnId,
        _action: &ESActionWrapper,
    ) -> usize {
        let mech_metric = env.help().mech_metric();
        let desired_container_cnt = match self.target {
            Target::MemUseRate(cpu_target_use_rate) => {
                let container_cnt = env.fn_container_cnt(fnid);

                let mut desired_container_cnt = if container_cnt != 0 {
                    let mut avg_mem_use_rate = 0.0;
                    env.fn_containers_for_each(fnid, |c| {
                        // avg_cpu_use_rate +=
                        // env.node(c.node_id).last_frame_cpu / env.node(c.node_id).rsc_limit.cpu;
                        avg_mem_use_rate +=
                            env.node(c.node_id).last_frame_mem / env.node(c.node_id).rsc_limit.mem;
                    });
                    // avg_mem_use_rate /= container_cnt as f32;

                    {
                        // current divide target
                        let ratio = avg_mem_use_rate / cpu_target_use_rate;
                        if (1.0 > ratio && ratio >= 1.0 - self.target_tolerance)
                            || (1.0 < ratio && ratio < 1.0 + self.target_tolerance)
                            || ratio == 1.0
                        {
                            // # ratio is sufficiently close to 1.0

                            // log::info!("hpa skip {fnid} at frame {}", env.current_frame());
                            return container_cnt;
                        }
                    }
                    // log::info!("avg mem use rate {}", avg_mem_use_rate);
                    (avg_mem_use_rate / cpu_target_use_rate).ceil() as usize
                } else {
                    0
                };

                if mech_metric.fn_unsche_req_cnt(fnid) > 0 {
                    desired_container_cnt =
                        desired_container_cnt.max(self.min_instances_when_pending);
                } else if !self.allow_scale_to_zero && desired_container_cnt == 0 {
                    desired_container_cnt = 1;
                }

                desired_container_cnt
            }
        };
        let maximum = self.max_instances.unwrap_or_else(|| env.node_cnt());
        desired_container_cnt
            .max(self.min_instances)
            .min(maximum.min(env.node_cnt()))
    }
}
