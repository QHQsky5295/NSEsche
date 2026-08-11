#![recursion_limit = "256"]

mod actions;
mod algos;
mod apis;
mod cache;
mod config;
mod dag_parsers;
mod env_gc;
mod experiment_record;
mod fn_dag;
mod mechanism;
mod mechanism_conf;
mod mechanism_thread;
mod metric;
mod network;
mod node;
mod output;
mod request;
mod rl_target;
mod scale;
mod sche;
mod score;
mod sim_env;
mod sim_events;
mod sim_loop;
mod sim_run;
mod sim_timer;
mod state;
mod util;
mod with_env_sub;
mod workload;

use env_logger::Builder;
use log::LevelFilter;
use mechanism_conf::ModuleMechConf;
use std::io::Write;
use std::time::Duration;

#[macro_use]
extern crate lazy_static;

#[tokio::main]
async fn main() {
    let keyword: Vec<&'static str> = vec![];
    let log_level = match std::env::var("SERVERLESS_SIM_LOG_LEVEL")
        .unwrap_or_else(|_| "info".to_string())
        .to_ascii_lowercase()
        .as_str()
    {
        "off" => LevelFilter::Off,
        "error" => LevelFilter::Error,
        "warn" | "warning" => LevelFilter::Warn,
        "debug" => LevelFilter::Debug,
        "trace" => LevelFilter::Trace,
        _ => LevelFilter::Info,
    };
    // vec!["::sche", "::mechanism ", "::scale"]; // no algo log
    Builder::new()
        .filter(None, log_level)
        .format(move |buf, record| {
            let message = format!(
                "{} {}",
                record.module_path().unwrap_or("no_mod"),
                record.args()
            );
            for k in &keyword {
                if message.contains(k) {
                    return Ok(());
                }
            }
            writeln!(buf, "{}: {}", record.level(), message)
        })
        .init();

    std::thread::sleep(Duration::from_secs(1));
    output::print_logo();
    // 启动垃圾回收（Garbage Collection, GC）机制
    env_gc::start_gc();
    ModuleMechConf::new().export_module_file();
    // parse_arg::parse_arg();
    network::start().await;
}

const REQUEST_GEN_FRAME_INTERVAL: usize = 1; //请求生成帧间隔
                                             // const REQUEST_GEN_FRAME_INTERVAL: usize = 10;
const NODE_SCORE_CPU_WEIGHT: f32 = 0.2;

const NODE_SCORE_MEM_WEIGHT: f32 = 0.8;

const CONTAINER_BASIC_MEM: f32 = 300.0; //内存压力
const NODE_LEFT_MEM_THRESHOLD: f32 = 3500.0; //内存限制
