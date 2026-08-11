use std::sync::mpsc;

use enum_as_inner::EnumAsInner;
#[cfg(target_os = "windows")]
use thread_priority::{set_current_thread_priority, ThreadPriority, WinAPIThreadPriority};
#[cfg(target_os = "windows")]
use windows::Win32::System::Threading::{GetCurrentThread, SetThreadPriority, THREAD_PRIORITY};

use crate::actions::ESActionWrapper;
use crate::mechanism::{DownCmd, Mechanism, MechanismImpl, ScheCmd, SimEnvObserve, UpCmd};

use std::thread::JoinHandle;
use std::time::Instant;

pub type MechCmdDistributor = mpsc::Sender<MechScheduleOnceRes>;

pub struct MechScheduleOnce {
    pub sim_env: SimEnvObserve,
    pub responser: MechCmdDistributor,
    pub action: ESActionWrapper,
}

#[derive(EnumAsInner)]
pub enum MechScheduleOnceRes {
    ScheCmd(ScheCmd),
    ScaleUpCmd(UpCmd),
    ScaleDownCmd(DownCmd),
    Cmds {
        sche_cmds: Vec<ScheCmd>,
        scale_up_cmds: Vec<UpCmd>,
        scale_down_cmds: Vec<DownCmd>,
    },
    End {
        mech_run_ms: u64,
        wall_time_ns: u64,
        thread_cpu_ns: u64,
        policy_wall_time_ns: u64,
        policy_thread_cpu_ns: u64,
        welfare_evaluation_wall_time_ns: u64,
        welfare_evaluation_thread_cpu_ns: u64,
    },
}

pub fn spawn(mech: MechanismImpl) -> mpsc::Sender<MechScheduleOnce> {
    spawn_joinable(mech).0
}

/// Start the mechanism worker and return its join handle.  Formal experiment
/// artifacts owned by a scheduler are finalized from the scheduler's `Drop`,
/// so the simulator must join this worker before an environment is considered
/// complete or the server process is terminated.
pub fn spawn_joinable(mech: MechanismImpl) -> (mpsc::Sender<MechScheduleOnce>, JoinHandle<()>) {
    let (tx, rx) = mpsc::channel();
    let worker = std::thread::spawn(move || {
        // 尝试设置当前线程的优先级
        // unsafe {
        //     SetThreadPriority(
        //         GetCurrentThread(),
        //         THREAD_PRIORITY(WinAPIThreadPriority::TimeCritical as i32)
        //     ).unwrap();
        // }

        #[cfg(target_os = "windows")]
        if let Err(e) = set_current_thread_priority(ThreadPriority::Max) {
            eprintln!("设置线程优先级失败: {:?}", e);
        }

        mechanism_loop(rx, mech);
    });
    (tx, worker)
}

fn mechanism_loop(rx: mpsc::Receiver<MechScheduleOnce>, mech: MechanismImpl) {
    loop {
        let res = match rx.recv() {
            Ok(res) => res,
            Err(_res) => {
                log::info!("mechanism_loop end");
                return;
            }
        };

        let wall_begin = Instant::now();
        let cpu_begin = cpu_time::ThreadTime::now();
        mech.step(&res.sim_env, res.action, &res.responser);
        let placement_timing = mech.placement_timing();
        let wall_elapsed = wall_begin.elapsed();
        let cpu_elapsed = cpu_begin.elapsed();
        let wall_time_ns = wall_elapsed.as_nanos().min(u64::MAX as u128) as u64;
        let thread_cpu_ns = cpu_elapsed.as_nanos().min(u64::MAX as u128) as u64;
        let mech_latency = if mech.config.no_mech_latency {
            0
        } else {
            wall_elapsed.as_millis().min(u64::MAX as u128) as u64
        };
        // 使用 match 进行错误处理，避免 panic
        match res.responser.send(MechScheduleOnceRes::End {
            mech_run_ms: mech_latency,
            wall_time_ns,
            thread_cpu_ns,
            policy_wall_time_ns: placement_timing.policy_wall_time_ns,
            policy_thread_cpu_ns: placement_timing.policy_thread_cpu_ns,
            welfare_evaluation_wall_time_ns: placement_timing.welfare_evaluation_wall_time_ns,
            welfare_evaluation_thread_cpu_ns: placement_timing.welfare_evaluation_thread_cpu_ns,
        }) {
            Ok(_) => {
                // 发送成功，继续处理
            }
            Err(e) => {
                // 发送失败，记录错误并退出循环
                log::warn!("Failed to send End message in mechanism_loop: {:?}", e);
                log::info!("mechanism_loop end due to send error");
                return;
            }
        }
    }
}

#[cfg(test)]
pub mod tests {
    use std::sync::mpsc;

    use crate::{actions::ESActionWrapper, mechanism_thread::MechScheduleOnceRes, sim_env::SimEnv};

    #[test]
    pub fn test_algo_latency() {
        use std::{
            cell::RefCell,
            rc::Rc,
            sync::{atomic::AtomicU64, Arc},
        };

        use crate::config::Config;
        let _ = env_logger::try_init();
        let mut conf = Config::new_test();
        conf.total_frame = 50;
        let mut env = SimEnv::new(conf);
        let (tx, rx) = mpsc::channel();
        env.mech_caller = tx;
        // let algo_latencys=vec![0, 10, 20, 30, 40, 50, 60, 70, 80, 90];
        let calltime = Arc::new(AtomicU64::new(1));
        {
            let calltime = calltime.clone();
            std::thread::spawn(move || {
                while let Ok(once) = rx.recv() {
                    once.responser
                        .send(MechScheduleOnceRes::End {
                            mech_run_ms: calltime.fetch_add(1, std::sync::atomic::Ordering::SeqCst),
                            wall_time_ns: 0,
                            thread_cpu_ns: 0,
                            policy_wall_time_ns: 0,
                            policy_thread_cpu_ns: 0,
                            welfare_evaluation_wall_time_ns: 0,
                            welfare_evaluation_thread_cpu_ns: 0,
                        })
                        .unwrap();
                }
            });
        }
        let mut calltime = 1;
        let begin_frame = Rc::new(RefCell::new(0));
        let begin_frame2 = begin_frame.clone();

        env.step_es(
            ESActionWrapper::Int(0),
            None,
            None,
            Some(Box::new(move |env: &SimEnv| {
                *begin_frame.borrow_mut() = env.current_frame();
            })),
            Some(Box::new(move |env: &SimEnv| {
                // calltime = env.current_frame() - begin_frame;
                assert!(
                    env.current_frame() - *begin_frame2.borrow() == calltime,
                    "begin_frame:{} current_frame:{} calltime:{}",
                    begin_frame2.borrow(),
                    env.current_frame(),
                    calltime
                );
                calltime += 1;
            })),
        );
    }
}
