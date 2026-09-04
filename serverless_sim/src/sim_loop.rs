#[cfg(target_os = "windows")]
use thread_priority::{set_current_thread_priority, ThreadPriority};

use crate::{
    actions::ESActionWrapper,
    mechanism::SimEnvObserve,
    mechanism_thread::{MechScheduleOnce, MechScheduleOnceRes},
    node::EnvNodeExt,
    rl_target::RL_TARGET,
    sim_env::SimEnv,
    with_env_sub::WithEnvHelp,
};

use std::{
    sync::mpsc::{self, Receiver},
    thread::sleep,
    time::Duration,
};

fn p5_should_stop(
    final_frame: usize,
    arrival_horizon: usize,
    cohort_drained: bool,
    hard_end_frame: usize,
) -> bool {
    final_frame >= hard_end_frame || (final_frame >= arrival_horizon && cohort_drained)
}

fn scheduler_may_run(
    current_frame: usize,
    configured_total_frame: usize,
    admission_enabled: bool,
    hard_end_frame: usize,
) -> bool {
    current_frame
        < if admission_enabled {
            hard_end_frame
        } else {
            configured_total_frame
        }
}

impl SimEnv {
    fn one_frame(
        &mut self,
        hook_frame_begin: &mut Option<Box<dyn FnMut(&SimEnv) + 'static>>,
        hook_req_gen: &mut Option<Box<dyn FnMut(&SimEnv) + 'static>>,
    ) -> bool {
        // 进行帧开始时处理
        self.on_frame_begin();
        if let Some(f) = hook_frame_begin.as_mut() {
            f(self);
        }
        // 生成新的请求，并添加到环境对象的请求映射中
        self.req_sim_gen_requests();
        if let Some(f) = hook_req_gen.as_mut() {
            f(self);
        }

        // 新请求生成之后将系统中请求和节点更新到最新状态
        self.help.mech_metric_mut().on_new_req_generated(self);

        // // 获得 扩容、缩容、调度 的指令
        // let (ups, downs, sches) = self.new_mech.step(self, raw_action.clone());

        self.sim_run();

        self.on_frame_end();

        let final_frame = self.current_frame().saturating_sub(1);
        let admission_enabled = self.admission_runtime.enabled;
        let arrival_horizon = self
            .help()
            .config()
            .experiment
            .workload
            .arrival_horizon_frames;
        let hard_stop = if admission_enabled {
            p5_should_stop(
                final_frame,
                arrival_horizon,
                self.help().config().experiment.admission.stop_when_drained
                    && self.cohort_is_drained(),
                self.admission_runtime.hard_end_frame,
            )
        } else {
            self.current_frame() > self.help().config().total_frame
        };
        if hard_stop {
            self.help.metric_record_mut().as_ref().unwrap().flush(self);
            if let Err(error) = self.workload_tape.flush() {
                panic!("failed to finalize workload tape: {error}");
            }
            if let Err(error) = self.experiment_recorder.finalize(self) {
                panic!("failed to finalize reviewer artifacts: {error}");
            }
            RL_TARGET.as_ref().map(|v| v.set_stop());
            // self.reset();
            false
        } else {
            true
        }
    }
    /// raw_action[0] container count
    pub fn step_es(
        &mut self,
        raw_action: ESActionWrapper,
        mut hook_frame_begin: Option<Box<dyn FnMut(&SimEnv) + 'static>>,
        mut hook_req_gen: Option<Box<dyn FnMut(&SimEnv) + 'static>>,
        mut hook_algo_begin: Option<Box<dyn FnMut(&SimEnv) + 'static>>,
        mut hook_algo_end: Option<Box<dyn FnMut(&SimEnv) + 'static>>,
    ) -> (f32, String) {
        // 尝试设置当前线程的优先级
        #[cfg(target_os = "windows")]
        if let Err(e) = set_current_thread_priority(ThreadPriority::Min) {
            eprintln!("设置线程优先级失败: {:?}", e);
        }

        self.avoid_gc();
        let mut master_mech_resp_rx: Option<Receiver<MechScheduleOnceRes>> = None;
        let mut frame_when_master_mech_begin = 0;
        // In no-mechanism-latency mode, a simulation frame must not advance
        // while the scheduler is still evaluating its snapshot.  Otherwise
        // placement commands are applied against a state that has already
        // changed underneath the scheduler.
        let mut run_frame_after_mech = false;
        'outer: loop {
            let mut clear_master_mech_rx = false;
            if let Some(rx) = &master_mech_resp_rx {
                let mut end_recv_algo_loop = false;
                while !end_recv_algo_loop {
                    let res = if self.help.config().no_mech_latency {
                        // wait until algo done;
                        let res = rx.recv().unwrap();
                        if res.is_end() {
                            end_recv_algo_loop = true;
                        }
                        res
                    } else {
                        // don't wait algo, run algo async
                        let Ok(res) = rx.try_recv() else {
                            break;
                        };
                        res
                    };
                    match res {
                        MechScheduleOnceRes::Cmds {
                            sche_cmds,
                            scale_up_cmds,
                            scale_down_cmds,
                        } => {
                            // 2. handle_master's commands
                            {
                                // HPA is the sole owner of container creation
                                // in the shared-HPA protocol. Apply its
                                // scale-up commands before placement so a
                                // placement decision from this window can
                                // observe the containers it requested.
                                for up in scale_up_cmds.iter() {
                                    self.experiment_recorder.record_scale_up();
                                    self.node_mut(up.nid).try_load_container(up.fnid, self);
                                }
                                // FIXME: Should transfer the cmds for a while.
                                // FIXME: should remove conflict cmds
                                // TODO: ScheCmd has memlimit
                                for sche in sche_cmds.iter() {
                                    let result = self.schedule_reqfn_on_node(
                                        &mut self.request_mut(sche.reqid),
                                        sche.fnid,
                                        sche.nid,
                                    );
                                    self.experiment_recorder.record_placement(result.is_ok());
                                    if let Err(error) = result {
                                        log::warn!(
                                            "rejected placement req={} fn={} node={}: {}",
                                            sche.reqid,
                                            sche.fnid,
                                            sche.nid,
                                            error
                                        );
                                    }
                                }
                                for down in scale_down_cmds.iter() {
                                    self.experiment_recorder.record_scale_down();
                                    //更新cache
                                    self.node_mut(down.nid)
                                        .try_unload_container(down.fnid, self, true);
                                }
                            }
                        }
                        MechScheduleOnceRes::ScheCmd(sche) => {
                            let result = self.schedule_reqfn_on_node(
                                &mut self.request_mut(sche.reqid),
                                sche.fnid,
                                sche.nid,
                            );
                            self.experiment_recorder.record_placement(result.is_ok());
                            if let Err(error) = result {
                                log::warn!(
                                    "rejected placement req={} fn={} node={}: {}",
                                    sche.reqid,
                                    sche.fnid,
                                    sche.nid,
                                    error
                                );
                            }
                        }
                        MechScheduleOnceRes::ScaleDownCmd(down) => {
                            self.experiment_recorder.record_scale_down();
                            //更新cache
                            self.node_mut(down.nid)
                                .try_unload_container(down.fnid, self, true);
                        }
                        MechScheduleOnceRes::ScaleUpCmd(up) => {
                            self.experiment_recorder.record_scale_up();
                            self.node_mut(up.nid).try_load_container(up.fnid, self);
                        }
                        MechScheduleOnceRes::End {
                            mech_run_ms,
                            wall_time_ns,
                            thread_cpu_ns,
                            policy_wall_time_ns,
                            policy_thread_cpu_ns,
                            welfare_evaluation_wall_time_ns,
                            welfare_evaluation_thread_cpu_ns,
                        } => {
                            clear_master_mech_rx = true;
                            self.experiment_recorder.record_scheduler_window(
                                frame_when_master_mech_begin,
                                self.current_frame(),
                                wall_time_ns,
                                thread_cpu_ns,
                                policy_wall_time_ns,
                                policy_thread_cpu_ns,
                                welfare_evaluation_wall_time_ns,
                                welfare_evaluation_thread_cpu_ns,
                            );
                            // 1. need to handle the gap between
                            //    master_mech time and simulation time
                            //    just simulate some if mech is longer
                            {
                                // one frame reflect to 1ms
                                let master_mech_frame = mech_run_ms as usize;
                                let frame_ran = self.current_frame() - frame_when_master_mech_begin;
                                let gap = if master_mech_frame > frame_ran {
                                    master_mech_frame - frame_ran
                                } else {
                                    0
                                };
                                for _ in 0..gap {
                                    if !self.one_frame(&mut hook_frame_begin, &mut hook_req_gen) {
                                        break 'outer;
                                    }
                                }
                                log::info!(
                                    "master mech ran in {} ms (mechanism wall={} ns cpu={} ns; policy wall={} ns cpu={} ns; posthoc welfare wall={} ns cpu={} ns), catch up {} gap frames, cur frame: {}",
                                    mech_run_ms,
                                    wall_time_ns,
                                    thread_cpu_ns,
                                    policy_wall_time_ns,
                                    policy_thread_cpu_ns,
                                    welfare_evaluation_wall_time_ns,
                                    welfare_evaluation_thread_cpu_ns,
                                    gap,
                                    self.current_frame()
                                );
                                self.help
                                    .algo_exc_time_mut()
                                    .insert(self.current_frame(), mech_run_ms as usize);
                            }

                            self.master_mech_not_running = true;
                            run_frame_after_mech = self.help().config().no_mech_latency;
                            frame_when_master_mech_begin = self.current_frame();
                            hook_algo_end.as_mut().map(|f| f(self));
                        }
                    }
                }
            }
            if clear_master_mech_rx {
                master_mech_resp_rx = None;
            }
            // A 0..T simulation records T+1 frame snapshots but has exactly T
            // scheduling windows (snapshots 0..T-1).  Do not launch a policy
            // evaluation at frame T: its commands can never be consumed because
            // the following frame finalizes the run, and doing so would create an
            // unmatched post-hoc welfare event.
            if run_frame_after_mech {
                run_frame_after_mech = false;
            } else if self.master_mech_not_running
                && scheduler_may_run(
                    self.current_frame(),
                    self.help().config().total_frame,
                    self.admission_runtime.enabled,
                    self.admission_runtime.hard_end_frame,
                )
            {
                self.master_mech_not_running = false;
                // just copy the algorithm needed metrics and continue run
                let (tx, rx) = mpsc::channel();
                master_mech_resp_rx = Some(rx);
                self.mech_caller
                    .send(MechScheduleOnce {
                        sim_env: SimEnvObserve::new(self.core.clone(), self.help.clone()),
                        responser: tx,
                        action: raw_action.clone(),
                    })
                    .unwrap();
                hook_algo_begin.as_mut().map(|f| f(self));

                // The next loop iteration receives the scheduler result. In
                // this mode that result must be applied before advancing the
                // simulation frame, so defer `one_frame` until then.
                if self.help().config().no_mech_latency {
                    continue 'outer;
                }
            }
            if !self.one_frame(&mut hook_frame_begin, &mut hook_req_gen) {
                log::info!("simulation end");
                break;
            }

            // 每帧跑完休息50ms
            // sleep(Duration::from_millis(20));
        }

        // state should has prompt info for next action
        (0.0, "no action".to_string())
    }
}

#[cfg(test)]
mod tests {
    use super::{p5_should_stop, scheduler_may_run};

    #[test]
    fn p5_early_stop_waits_for_arrival_horizon_and_hard_deadline_is_exact() {
        assert!(!p5_should_stop(999, 1_000, true, 4_000));
        assert!(p5_should_stop(1_000, 1_000, true, 4_000));
        assert!(!p5_should_stop(3_999, 1_000, false, 4_000));
        assert!(p5_should_stop(4_000, 1_000, false, 4_000));
    }

    #[test]
    fn p5_scheduler_continues_through_drain_but_not_past_hard_end() {
        assert!(scheduler_may_run(999, 1_000, false, 4_000));
        assert!(!scheduler_may_run(1_000, 1_000, false, 4_000));
        assert!(scheduler_may_run(1_000, 1_000, true, 4_000));
        assert!(scheduler_may_run(3_999, 1_000, true, 4_000));
        assert!(!scheduler_may_run(4_000, 1_000, true, 4_000));
    }
}
