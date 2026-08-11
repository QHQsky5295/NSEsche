use super::ScaleUpExec;
use crate::mechanism_thread::{MechCmdDistributor, MechScheduleOnceRes};
use crate::node::EnvNodeExt;
use crate::with_env_sub::WithEnvHelp;
use crate::{
    fn_dag::{EnvFnExt, FnId},
    mechanism::{SimEnvObserve, UpCmd},
};

pub struct LeastTaskScaleUpExec;

fn scale_up_count(target: usize, actual: usize, eligible_missing: usize) -> usize {
    target.saturating_sub(actual).min(eligible_missing)
}

impl LeastTaskScaleUpExec {
    pub fn new() -> Self {
        LeastTaskScaleUpExec {}
    }
}

impl ScaleUpExec for LeastTaskScaleUpExec {
    fn exec_scale_up(
        &self,
        target_cnt: usize,
        fnid: FnId,
        env: &SimEnvObserve,
        cmd_distributor: &MechCmdDistributor,
    ) -> Vec<UpCmd> {
        let mech_metric = || env.help().mech_metric_mut();
        let mut up_cmds = vec![];

        let nodes = env.nodes();
        let nodes_with_container_cnt = nodes
            .iter()
            .filter(|node| node.container(fnid).is_some())
            .count();
        let mut nodes_no_container = nodes
            .iter()
            .filter(|node| {
                node.container(fnid).is_none() && node.mem_enough_for_container(&env.func(fnid))
            })
            .map(|n| n.node_id())
            .collect::<Vec<_>>();

        // log::info!("nodes_no_container.len(): {}", nodes_no_container.len());
        // MARK 修复了一个扩容bug
        let to_scale_up_cnt = scale_up_count(
            target_cnt,
            nodes_with_container_cnt,
            nodes_no_container.len(),
        );
        if to_scale_up_cnt > 0 {
            // 对不含容器的节点按照其所有任务数量进行降序排序
            nodes_no_container.sort_by(|&a, &b| {
                let acnt = mech_metric().node_task_new_cnt(a);
                let bcnt = mech_metric().node_task_new_cnt(b);
                acnt.cmp(&bcnt).then_with(|| a.cmp(&b))
            });
            // 反转，即优先选择任务数量最少的节点进行预加载
            nodes_no_container.reverse();
            for _ in 0..to_scale_up_cnt {
                let node_2_load_contaienr = nodes_no_container.pop().unwrap();
                if let Err(error) = cmd_distributor.send(MechScheduleOnceRes::ScaleUpCmd(UpCmd {
                    nid: node_2_load_contaienr,
                    fnid,
                })) {
                    log::warn!("failed to send common-HPA scale-up command: {error}");
                    break;
                }
                up_cmds.push(UpCmd {
                    nid: node_2_load_contaienr,
                    fnid,
                })
            }
        }

        up_cmds
    }
}

#[cfg(test)]
mod tests {
    use super::scale_up_count;

    #[test]
    fn ineligible_missing_nodes_are_not_counted_as_existing_instances() {
        // Five real instances, two eligible empty nodes, and thirteen
        // ineligible empty nodes must still produce two scale-up commands.
        assert_eq!(scale_up_count(8, 5, 2), 2);
        assert_eq!(scale_up_count(5, 5, 2), 0);
        assert_eq!(scale_up_count(4, 5, 2), 0);
    }
}
