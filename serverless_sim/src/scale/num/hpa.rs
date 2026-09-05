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

/// Immutable inputs to the HPA decision. Counts distinguish future DAG work
/// from invocations that can be placed now and containers that cannot be evicted.
#[derive(Clone, Copy, Debug, Default)]
struct HpaWindowDemand {
    containers: usize,
    node_memory_utilization_sum: f32,
    unscheduled_requests: usize,
    ready_requests: usize,
    queued_requests: usize,
    protected_instances: usize,
}

pub struct HpaScaleNum {
    target: Target,
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

    fn utilization_target(&self, demand: HpaWindowDemand) -> (usize, bool) {
        if demand.containers == 0 {
            return (0, false);
        }
        let Target::MemUseRate(target) = self.target;
        let ratio = demand.node_memory_utilization_sum / target;
        let in_tolerance = (1.0 > ratio && ratio >= 1.0 - self.target_tolerance)
            || (1.0 < ratio && ratio < 1.0 + self.target_tolerance)
            || ratio == 1.0;
        if in_tolerance {
            (demand.containers, true)
        } else {
            (ratio.ceil() as usize, false)
        }
    }

    fn bounded_target(&self, desired: usize, node_count: usize) -> usize {
        desired
            .max(self.min_instances)
            .min(self.max_instances.unwrap_or(node_count).min(node_count))
    }

    fn legacy_target(&self, demand: HpaWindowDemand, node_count: usize) -> usize {
        let (mut desired, in_tolerance) = self.utilization_target(demand);
        // Preserve the historical early return for reviewer-v3/v4 replay.
        if in_tolerance {
            return demand.containers;
        }
        if demand.unscheduled_requests > 0 {
            desired = desired.max(self.min_instances_when_pending);
        } else if !self.allow_scale_to_zero && desired == 0 {
            desired = 1;
        }
        self.bounded_target(desired, node_count)
    }

    fn ready_target(&self, demand: HpaWindowDemand, node_count: usize) -> usize {
        let pending = demand.ready_requests > 0 || demand.queued_requests > 0;
        if self.allow_scale_to_zero && !pending && demand.protected_instances == 0 {
            // Idle container base memory is not invocation demand.
            return self.bounded_target(0, node_count);
        }

        let (mut desired, _) = self.utilization_target(demand);
        if pending {
            desired = desired.max(self.min_instances_when_pending);
        }
        desired = desired.max(demand.protected_instances);
        if !self.allow_scale_to_zero {
            desired = desired.max(1);
        }
        // Unlike the old early return, tolerance cannot bypass demand/min/max.
        self.bounded_target(desired, node_count)
    }
}

impl ScaleNum for HpaScaleNum {
    fn scale_for_fn(
        &mut self,
        env: &SimEnvObserve,
        fnid: FnId,
        _action: &ESActionWrapper,
    ) -> usize {
        let common_ready = env.help().config().experiment.protocol_version == "reviewer-v5";
        let mech_metric = env.help().mech_metric();
        let mut demand = HpaWindowDemand {
            containers: env.fn_container_cnt(fnid),
            unscheduled_requests: mech_metric.fn_unsche_req_cnt(fnid),
            ready_requests: if common_ready {
                mech_metric
                    .fn_ready_sche_tasks(fnid)
                    .map_or(0, |tasks| tasks.len())
            } else {
                0
            },
            ..HpaWindowDemand::default()
        };
        env.fn_containers_for_each(fnid, |container| {
            let node = env.node(container.node_id);
            demand.node_memory_utilization_sum += node.last_frame_mem / node.rsc_limit.mem;
            if common_ready && (!container.is_idle() || node.pending_task_cnt_for_fn(fnid) > 0) {
                demand.protected_instances += 1;
            }
        });
        if common_ready {
            demand.queued_requests = env
                .nodes()
                .iter()
                .map(|node| node.pending_task_cnt_for_fn(fnid))
                .sum();
            self.ready_target(demand, env.node_cnt())
        } else {
            self.legacy_target(demand, env.node_cnt())
        }
    }
}

#[cfg(test)]
mod tests {
    use super::{HpaScaleNum, HpaWindowDemand};
    use crate::config::HpaProtocolConfig;

    fn idle() -> HpaWindowDemand {
        HpaWindowDemand {
            containers: 1,
            node_memory_utilization_sum: 300.0 / 5000.0,
            ..HpaWindowDemand::default()
        }
    }

    #[test]
    fn p6_idle_base_memory_demonstrates_legacy_nonzero_target() {
        let hpa = HpaScaleNum::new();
        assert_eq!(hpa.legacy_target(idle(), 20), 1);
        assert_eq!(hpa.ready_target(idle(), 20), 0);
    }

    #[test]
    fn p6_future_descendants_do_not_pin_an_idle_instance() {
        let hpa = HpaScaleNum::new();
        let demand = HpaWindowDemand {
            unscheduled_requests: 100,
            ..idle()
        };
        assert_eq!(hpa.legacy_target(demand, 20), 1);
        assert_eq!(hpa.ready_target(demand, 20), 0);
    }

    #[test]
    fn p6_ready_and_already_queued_requests_each_require_capacity() {
        let hpa = HpaScaleNum::new();
        for demand in [
            HpaWindowDemand {
                ready_requests: 1,
                ..Default::default()
            },
            HpaWindowDemand {
                queued_requests: 1,
                ..Default::default()
            },
        ] {
            assert_eq!(hpa.ready_target(demand, 20), 1);
        }
    }

    #[test]
    fn p6_resident_or_starting_instances_remain_protected_without_ready_work() {
        let hpa = HpaScaleNum::new();
        let demand = HpaWindowDemand {
            containers: 3,
            protected_instances: 3,
            node_memory_utilization_sum: 0.06,
            ..Default::default()
        };
        assert_eq!(hpa.ready_target(demand, 20), 3);
    }

    #[test]
    fn p6_tolerance_does_not_skip_pending_floor() {
        let hpa = HpaScaleNum::from_config(&HpaProtocolConfig {
            min_instances_when_pending: 3,
            ..Default::default()
        });
        let demand = HpaWindowDemand {
            node_memory_utilization_sum: 0.5,
            ready_requests: 1,
            unscheduled_requests: 1,
            ..idle()
        };
        assert_eq!(hpa.legacy_target(demand, 20), 1);
        assert_eq!(hpa.ready_target(demand, 20), 3);
    }

    #[test]
    fn p6_tolerance_does_not_skip_maximum() {
        let hpa = HpaScaleNum::from_config(&HpaProtocolConfig {
            max_instances: Some(2),
            ..Default::default()
        });
        let demand = HpaWindowDemand {
            containers: 4,
            node_memory_utilization_sum: 0.5,
            ready_requests: 1,
            ..Default::default()
        };
        assert_eq!(hpa.legacy_target(demand, 20), 4);
        assert_eq!(hpa.ready_target(demand, 20), 2);
    }

    #[test]
    fn p6_idle_target_respects_explicit_minimum_and_scale_to_zero_switch() {
        let minimum = HpaScaleNum::from_config(&HpaProtocolConfig {
            min_instances: 2,
            ..Default::default()
        });
        assert_eq!(minimum.ready_target(idle(), 20), 2);
        let no_zero = HpaScaleNum::from_config(&HpaProtocolConfig {
            allow_scale_to_zero: false,
            ..Default::default()
        });
        assert_eq!(no_zero.ready_target(Default::default(), 20), 1);
    }

    #[test]
    fn p6_busy_utilization_signal_is_preserved_and_capacity_bounded() {
        let hpa = HpaScaleNum::new();
        for (utilization, expected) in [(0.1, 1), (0.6, 2), (1.2, 3), (20.0, 20)] {
            let demand = HpaWindowDemand {
                containers: 1,
                node_memory_utilization_sum: utilization,
                ready_requests: 1,
                unscheduled_requests: 1,
                ..Default::default()
            };
            assert_eq!(hpa.ready_target(demand, 20), expected);
            assert_eq!(hpa.legacy_target(demand, 20), expected);
        }
    }
}
