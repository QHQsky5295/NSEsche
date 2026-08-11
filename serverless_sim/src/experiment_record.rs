use std::{
    cell::RefCell,
    collections::BTreeMap,
    fs::{self, File},
    io::{self, BufWriter, Write},
    path::{Path, PathBuf},
};

use serde_json::{json, Value};

use crate::{
    config::Config,
    fn_dag::{EnvFnExt, FnContainerState},
    node::EnvNodeExt,
    request::Request,
    sim_env::SimEnv,
    with_env_sub::{WithEnvCore, WithEnvHelp},
};

struct JsonlFile {
    partial_path: PathBuf,
    final_path: PathBuf,
    writer: Option<BufWriter<File>>,
}

impl JsonlFile {
    fn create(directory: &Path, name: &str) -> io::Result<Self> {
        let final_path = directory.join(name);
        let partial_path = directory.join(format!("{name}.partial"));
        let writer = BufWriter::new(File::create(&partial_path)?);
        Ok(Self {
            partial_path,
            final_path,
            writer: Some(writer),
        })
    }

    fn write(&mut self, value: &Value) -> io::Result<()> {
        let writer = self.writer.as_mut().ok_or_else(|| {
            io::Error::new(io::ErrorKind::BrokenPipe, "experiment stream is finalized")
        })?;
        serde_json::to_writer(&mut *writer, value)?;
        writer.write_all(b"\n")
    }

    fn finalize(&mut self) -> io::Result<()> {
        let Some(mut writer) = self.writer.take() else {
            return Ok(());
        };
        writer.flush()?;
        drop(writer);
        if self.final_path.exists() {
            return Err(io::Error::new(
                io::ErrorKind::AlreadyExists,
                format!("refusing to overwrite {}", self.final_path.display()),
            ));
        }
        fs::rename(&self.partial_path, &self.final_path)
    }
}

#[derive(Default)]
struct WindowCounts {
    placements_accepted: u64,
    placements_rejected: u64,
    scale_up_commands: u64,
    scale_down_commands: u64,
}

struct ExperimentRecordState {
    directory: PathBuf,
    frames: Option<JsonlFile>,
    requests: Option<JsonlFile>,
    scheduler_windows: JsonlFile,
    written_done_requests: usize,
    finalized: bool,
    queue_peak: usize,
    queue_area: u64,
    node_sample_count: u64,
    cpu_sum: f64,
    mem_sum: f64,
    cpu_peak: f32,
    mem_peak: f32,
    cpu_utilization_samples: Vec<f64>,
    memory_utilization_samples: Vec<f64>,
    cpu_utilization_invalid_samples: u64,
    memory_utilization_invalid_samples: u64,
    scheduler_wall_ns: Vec<u64>,
    scheduler_cpu_ns: Vec<u64>,
    policy_wall_ns: Vec<u64>,
    policy_cpu_ns: Vec<u64>,
    welfare_evaluation_wall_ns: Vec<u64>,
    welfare_evaluation_cpu_ns: Vec<u64>,
    window_counts: WindowCounts,
    placement_rejections_total: u64,
    qos_function_arrivals: BTreeMap<String, u64>,
    qos_function_completions: BTreeMap<String, u64>,
    qos_internal_cost: BTreeMap<String, f64>,
}

/// Result-blind, streaming reviewer artifact writer. A crash leaves `.partial`
/// files in place; only normal completion atomically promotes them.
pub struct ExperimentRecorder {
    state: RefCell<Option<ExperimentRecordState>>,
}

impl ExperimentRecorder {
    pub fn new(config: &Config) -> Result<Self, String> {
        if !config.experiment.output.enabled {
            return Ok(Self {
                state: RefCell::new(None),
            });
        }
        if config.experiment.run_id.trim().is_empty() {
            return Err("experiment.output.enabled requires a non-empty run_id".to_string());
        }
        let directory = Path::new(&config.experiment.output.root).join(&config.experiment.run_id);
        fs::create_dir_all(&directory)
            .map_err(|error| format!("create {}: {error}", directory.display()))?;
        let frames = if config.experiment.output.window_events {
            Some(
                JsonlFile::create(&directory, "frames.jsonl").map_err(|error| {
                    format!("create frame stream in {}: {error}", directory.display())
                })?,
            )
        } else {
            None
        };
        let requests = if config.experiment.output.request_events {
            Some(
                JsonlFile::create(&directory, "requests.jsonl").map_err(|error| {
                    format!("create request stream in {}: {error}", directory.display())
                })?,
            )
        } else {
            None
        };
        let scheduler_windows =
            JsonlFile::create(&directory, "scheduler_windows.jsonl").map_err(|error| {
                format!(
                    "create scheduler stream in {}: {error}",
                    directory.display()
                )
            })?;
        Ok(Self {
            state: RefCell::new(Some(ExperimentRecordState {
                directory,
                frames,
                requests,
                scheduler_windows,
                written_done_requests: 0,
                finalized: false,
                queue_peak: 0,
                queue_area: 0,
                node_sample_count: 0,
                cpu_sum: 0.0,
                mem_sum: 0.0,
                cpu_peak: 0.0,
                mem_peak: 0.0,
                cpu_utilization_samples: Vec::new(),
                memory_utilization_samples: Vec::new(),
                cpu_utilization_invalid_samples: 0,
                memory_utilization_invalid_samples: 0,
                scheduler_wall_ns: Vec::new(),
                scheduler_cpu_ns: Vec::new(),
                policy_wall_ns: Vec::new(),
                policy_cpu_ns: Vec::new(),
                welfare_evaluation_wall_ns: Vec::new(),
                welfare_evaluation_cpu_ns: Vec::new(),
                window_counts: WindowCounts::default(),
                placement_rejections_total: 0,
                qos_function_arrivals: BTreeMap::new(),
                qos_function_completions: BTreeMap::new(),
                qos_internal_cost: BTreeMap::new(),
            })),
        })
    }

    pub fn write_static_environment(&self, env: &SimEnv) -> Result<(), String> {
        let state = self.state.borrow();
        let Some(state) = state.as_ref() else {
            return Ok(());
        };
        let nodes = env
            .nodes()
            .iter()
            .map(|node| {
                json!({
                    "node_id": node.node_id(),
                    "cpu_capacity": node.rsc_limit.cpu,
                    "memory_capacity": node.rsc_limit.mem,
                })
            })
            .collect::<Vec<_>>();
        let functions = env
            .core()
            .fns()
            .iter()
            .map(|function| {
                json!({
                    "function_id": function.fn_id,
                    "dag_id": function.dag_id,
                    "cpu_work": function.cpu,
                    "memory": function.mem,
                    "output_mb": function.out_put_size,
                    "cold_start_frames": function.cold_start_time,
                    "container_memory": function.container_mem(),
                    "qos_class": &function.qos_class,
                    "quality_weight": function.quality_weight,
                    "parents": function.parent_fns(env),
                    "children": function.sub_fns(env),
                })
            })
            .collect::<Vec<_>>();
        let network = (0..env.node_cnt())
            .map(|from| {
                (0..env.node_cnt())
                    .map(|to| {
                        if from == to {
                            0.0
                        } else {
                            env.node_get_speed_btwn(from, to)
                        }
                    })
                    .collect::<Vec<_>>()
            })
            .collect::<Vec<_>>();
        let dag_arrival_model = env
            .help()
            .fn_call_frequency()
            .iter()
            .map(|(dag_id, (cdf_mean, cdf_cv))| {
                json!({
                    "dag_id": dag_id,
                    "cdf_mean_before_load_scale": cdf_mean,
                    "cdf_cv": cdf_cv,
                })
            })
            .collect::<Vec<_>>();
        let request_frequency_scale = if env.help().config().request_freq_low() {
            0.2
        } else if env.help().config().request_freq_middle() {
            0.6
        } else {
            1.4
        };
        let value = json!({
            "schema": "NSE_ENVIRONMENT_V1",
            "run_id": env.help().config().experiment.run_id,
            "config": env.help().config(),
            "runtime_constants": {
                "container_basic_memory": crate::CONTAINER_BASIC_MEM,
                "node_memory_reserve": crate::NODE_LEFT_MEM_THRESHOLD,
                "request_generation_period_frames": crate::REQUEST_GEN_FRAME_INTERVAL,
            },
            "nodes": nodes,
            "network_mb_per_second": network,
            "functions": functions,
            "arrival_generation": {
                "source": "Azure-trace-derived empirical IAT/CV CDF",
                "request_frequency_scale": request_frequency_scale,
                "generation_period_frames": crate::REQUEST_GEN_FRAME_INTERVAL,
                "formal_frequency_cache_policy": "disabled; derive once per explicit workload seed",
                "dag_parameters": dag_arrival_model,
            },
        });
        atomic_json(&state.directory.join("environment.json"), &value)
            .map_err(|error| format!("write static environment: {error}"))
    }

    pub fn record_placement(&self, accepted: bool) {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return;
        };
        if accepted {
            state.window_counts.placements_accepted += 1;
        } else {
            state.window_counts.placements_rejected += 1;
            state.placement_rejections_total += 1;
        }
    }

    pub fn record_scale_up(&self) {
        if let Some(state) = self.state.borrow_mut().as_mut() {
            state.window_counts.scale_up_commands += 1;
        }
    }

    pub fn record_scale_down(&self) {
        if let Some(state) = self.state.borrow_mut().as_mut() {
            state.window_counts.scale_down_commands += 1;
        }
    }

    pub fn record_request_arrival(&self, env: &SimEnv, request: &Request) {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return;
        };
        for function_id in request.fn_metric.keys() {
            let class = env.func(*function_id).qos_class.clone();
            *state.qos_function_arrivals.entry(class).or_default() += 1;
        }
    }

    pub fn record_function_completion(&self, env: &SimEnv, function_id: usize) {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return;
        };
        let class = env.func(function_id).qos_class.clone();
        *state.qos_function_completions.entry(class).or_default() += 1;
    }

    pub fn record_scheduler_window(
        &self,
        begin_frame: usize,
        end_frame: usize,
        wall_time_ns: u64,
        thread_cpu_ns: u64,
        policy_wall_time_ns: u64,
        policy_thread_cpu_ns: u64,
        welfare_evaluation_wall_time_ns: u64,
        welfare_evaluation_thread_cpu_ns: u64,
    ) {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return;
        };
        let counts = std::mem::take(&mut state.window_counts);
        let value = json!({
            "schema": "NSE_SCHEDULER_WINDOW_V1",
            "begin_frame": begin_frame,
            "end_frame": end_frame,
            "wall_time_ns": wall_time_ns,
            "thread_cpu_ns": thread_cpu_ns,
            "timing_scope": {
                "wall_time_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                "thread_cpu_ns": "complete_common_HPA_mechanism_plus_policy_plus_observation",
                "policy_wall_time_ns": "placement_policy_call_exact_boundary",
                "policy_thread_cpu_ns": "placement_policy_call_exact_boundary",
                "welfare_evaluation_wall_time_ns": "read_only_posthoc_observer_exact_boundary",
                "welfare_evaluation_thread_cpu_ns": "read_only_posthoc_observer_exact_boundary",
                "policy_time_derived_by_subtraction": false,
            },
            "policy_wall_time_ns": policy_wall_time_ns,
            "policy_thread_cpu_ns": policy_thread_cpu_ns,
            "welfare_evaluation_wall_time_ns": welfare_evaluation_wall_time_ns,
            "welfare_evaluation_thread_cpu_ns": welfare_evaluation_thread_cpu_ns,
            "placements_accepted": counts.placements_accepted,
            "placements_rejected": counts.placements_rejected,
            "common_hpa_scale_up_commands": counts.scale_up_commands,
            "common_hpa_scale_down_commands": counts.scale_down_commands,
        });
        state
            .scheduler_windows
            .write(&value)
            .unwrap_or_else(|error| panic!("write scheduler window: {error}"));
        state.scheduler_wall_ns.push(wall_time_ns);
        state.scheduler_cpu_ns.push(thread_cpu_ns);
        state.policy_wall_ns.push(policy_wall_time_ns);
        state.policy_cpu_ns.push(policy_thread_cpu_ns);
        state
            .welfare_evaluation_wall_ns
            .push(welfare_evaluation_wall_time_ns);
        state
            .welfare_evaluation_cpu_ns
            .push(welfare_evaluation_thread_cpu_ns);
    }

    pub fn record_frame(&self, env: &SimEnv) {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return;
        };
        let frame = env.current_frame();
        let nodes = env.nodes();
        let pending_tasks = nodes
            .iter()
            .map(|node| node.pending_task_cnt())
            .sum::<usize>();
        let running_tasks = nodes
            .iter()
            .map(|node| node.running_task_cnt())
            .sum::<usize>();
        let (unscheduled_tasks, ready_unscheduled_tasks) = {
            let metric = env.help().mech_metric();
            let functions = env.core().fns();
            let unscheduled = functions
                .iter()
                .map(|function| metric.fn_unsche_req_cnt(function.fn_id))
                .sum::<usize>();
            let ready = functions
                .iter()
                .map(|function| {
                    metric
                        .fn_ready_sche_tasks(function.fn_id)
                        .map(|requests| requests.len())
                        .unwrap_or(0)
                })
                .sum::<usize>();
            (unscheduled, ready)
        };
        let queue = unscheduled_tasks + pending_tasks;
        let tasks_in_system = queue + running_tasks;
        let mut running_containers = 0usize;
        let mut starting_containers = 0usize;
        let mut cpu_sum = 0.0f64;
        let mut mem_sum = 0.0f64;
        let mut cpu_peak = 0.0f32;
        let mut mem_peak = 0.0f32;
        let mut cpu_utilization_sum = 0.0f64;
        let mut memory_utilization_sum = 0.0f64;
        let mut cpu_utilization_count = 0usize;
        let mut memory_utilization_count = 0usize;
        let mut cpu_utilization_peak = None::<f64>;
        let mut memory_utilization_peak = None::<f64>;
        let mut cpu_utilization_invalid_samples = 0u64;
        let mut memory_utilization_invalid_samples = 0u64;
        let mut qos_resources = BTreeMap::<String, (f64, f64)>::new();
        for node in nodes.iter() {
            let cpu = node.cpu;
            let mem = node.unready_mem();
            cpu_sum += cpu as f64;
            mem_sum += mem as f64;
            cpu_peak = cpu_peak.max(cpu);
            mem_peak = mem_peak.max(mem);
            if let Some(utilization) = normalized_utilization(cpu, node.rsc_limit.cpu) {
                cpu_utilization_sum += utilization;
                cpu_utilization_count += 1;
                cpu_utilization_peak =
                    Some(cpu_utilization_peak.map_or(utilization, |peak| peak.max(utilization)));
                state.cpu_utilization_samples.push(utilization);
            } else {
                cpu_utilization_invalid_samples += 1;
                state.cpu_utilization_invalid_samples += 1;
            }
            if let Some(utilization) = normalized_utilization(mem, node.rsc_limit.mem) {
                memory_utilization_sum += utilization;
                memory_utilization_count += 1;
                memory_utilization_peak =
                    Some(memory_utilization_peak.map_or(utilization, |peak| peak.max(utilization)));
                state.memory_utilization_samples.push(utilization);
            } else {
                memory_utilization_invalid_samples += 1;
                state.memory_utilization_invalid_samples += 1;
            }
            for (function_id, container) in node.fn_containers.borrow().iter() {
                match container.state() {
                    FnContainerState::Running => running_containers += 1,
                    FnContainerState::Starting { .. } => starting_containers += 1,
                }
                let qos_class = env.func(*function_id).qos_class.clone();
                let usage = qos_resources.entry(qos_class).or_default();
                usage.0 += container.last_frame_cpu_used as f64;
                usage.1 += container.mem_use as f64;
            }
        }
        for (class, (cpu, memory)) in &qos_resources {
            *state.qos_internal_cost.entry(class.clone()).or_default() += (cpu + memory) * 0.00001;
        }
        let qos_resources = qos_resources
            .into_iter()
            .map(|(class, (cpu, memory))| {
                (
                    class,
                    json!({
                        "cpu_work": cpu,
                        "memory": memory,
                        "simulator_internal_cost": (cpu + memory) * 0.00001,
                    }),
                )
            })
            .collect::<serde_json::Map<String, Value>>();
        let qos_function_tasks = qos_function_task_counts(
            &state.qos_function_arrivals,
            &state.qos_function_completions,
        );
        state.queue_peak = state.queue_peak.max(queue);
        state.queue_area += queue as u64;
        state.node_sample_count += nodes.len() as u64;
        state.cpu_sum += cpu_sum;
        state.mem_sum += mem_sum;
        state.cpu_peak = state.cpu_peak.max(cpu_peak);
        state.mem_peak = state.mem_peak.max(mem_peak);

        let arrivals_total = env.core().requests().len() + env.core().done_requests().len();
        if let Some(frames) = state.frames.as_mut() {
            frames
                .write(&json!({
                    "schema": "NSE_FRAME_V1",
                    "frame": frame,
                    "arrivals_total": arrivals_total,
                    "completed_total": env.core().done_requests().len(),
                    "active_requests": env.core().requests().len(),
                    "pending_tasks": pending_tasks,
                    "unscheduled_tasks": unscheduled_tasks,
                    "ready_unscheduled_tasks": ready_unscheduled_tasks,
                    "running_tasks": running_tasks,
                    "queue_total": queue,
                    "tasks_in_system": tasks_in_system,
                    "running_containers": running_containers,
                    "starting_containers": starting_containers,
                    "node_cpu_mean": divide(cpu_sum, nodes.len()),
                    "node_cpu_peak": cpu_peak,
                    "node_memory_mean": divide(mem_sum, nodes.len()),
                    "node_memory_peak": mem_peak,
                    "node_cpu_utilization_mean": divide(cpu_utilization_sum, cpu_utilization_count),
                    "node_cpu_utilization_peak": cpu_utilization_peak,
                    "node_cpu_utilization_valid_samples": cpu_utilization_count,
                    "node_cpu_utilization_invalid_samples": cpu_utilization_invalid_samples,
                    "node_memory_utilization_mean": divide(memory_utilization_sum, memory_utilization_count),
                    "node_memory_utilization_peak": memory_utilization_peak,
                    "node_memory_utilization_valid_samples": memory_utilization_count,
                    "node_memory_utilization_invalid_samples": memory_utilization_invalid_samples,
                    "simulator_cost_total": *env.help().cost(),
                    "drop_total": 0,
                    "reject_total": 0,
                    "timeout_total": 0,
                    "qos_resources": qos_resources,
                    "qos_function_tasks": qos_function_tasks,
                }))
                .unwrap_or_else(|error| panic!("write frame event: {error}"));
        }

        if let Some(requests) = state.requests.as_mut() {
            let done = env.core().done_requests();
            for request in done.iter().skip(state.written_done_requests) {
                requests
                    .write(&request_event(env, request))
                    .unwrap_or_else(|error| panic!("write request event: {error}"));
            }
            state.written_done_requests = done.len();
        }
    }

    pub fn finalize(&self, env: &SimEnv) -> Result<(), String> {
        let mut state = self.state.borrow_mut();
        let Some(state) = state.as_mut() else {
            return Ok(());
        };
        if state.finalized {
            return Ok(());
        }
        let done_requests = env.core().done_requests();
        let active_requests = env.core().requests();
        let completed = done_requests.len();
        let arrivals = active_requests.len() + completed;
        let mut latencies = done_requests
            .iter()
            .map(|request| request.end_frame.saturating_sub(request.begin_frame) as f64)
            .collect::<Vec<_>>();
        latencies.sort_by(f64::total_cmp);
        let fixed_observation_frames = env
            .help()
            .config()
            .experiment
            .workload
            .arrival_horizon_frames
            .max(1);
        let completed_timings = done_requests
            .iter()
            .map(|request| (request.begin_frame, request.end_frame))
            .collect::<Vec<_>>();
        let active_arrivals = active_requests
            .values()
            .map(|request| request.begin_frame)
            .collect::<Vec<_>>();
        let cohort = summarize_arrival_cohort(
            &completed_timings,
            &active_arrivals,
            fixed_observation_frames,
        );
        // `total_frame` is the protocol's observation horizon in milliseconds.
        // The legacy loop also records the boundary state at index
        // `total_frame`, hence `frames_recorded = total_frame + 1`; that
        // boundary sample must not silently add an extra millisecond to the
        // throughput denominator.
        let observation_ms = env.help().config().total_frame.max(1);
        let fixed_observation_ms = fixed_observation_frames;
        let drain_horizon_frames = env.help().config().total_frame;
        let cost_total = *env.help().cost() as f64;
        let (cpu_utilization_mean, cpu_utilization_p95, cpu_utilization_peak) =
            utilization_summary(&state.cpu_utilization_samples);
        let (memory_utilization_mean, memory_utilization_p95, memory_utilization_peak) =
            utilization_summary(&state.memory_utilization_samples);
        let scheduler_timing_definition = json!({
            "primary_policy_metric": "placement_policy_wall_ns",
            "mechanism_total_metric": "scheduler_wall_ns",
            "posthoc_welfare_excluded_from_policy_boundary": true,
            "policy_time_derived_by_subtraction": false,
        });
        let summary = json!({
            "schema": "NSE_SUMMARY_V1",
            "run_id": env.help().config().experiment.run_id,
            "protocol_version": env.help().config().experiment.protocol_version,
            "run_complete": true,
            "final_frame": env.current_frame().saturating_sub(1),
            "frames_recorded": env.current_frame(),
            "frame_duration_ms": 1,
            "observation_time_ms": observation_ms,
            "arrivals": arrivals,
            "completed": completed,
            "completion_ratio": ratio(completed, arrivals),
            "throughput_requests_per_second": completed as f64 * 1000.0 / observation_ms as f64,
            "latency_ms": {
                "mean": mean(&latencies),
                "p50": percentile(&latencies, 0.50),
                "p95": percentile(&latencies, 0.95),
                "p99": percentile(&latencies, 0.99),
            },
            "fixed_observation_window": {
                "start_frame": 0,
                "end_frame": fixed_observation_frames,
                "duration_ms": fixed_observation_ms,
                "arrivals": cohort.arrivals,
                "completed": cohort.completed_by_observation,
                "completion_ratio": ratio(cohort.completed_by_observation, cohort.arrivals),
                "throughput_requests_per_second": cohort.completed_by_observation as f64
                    * 1000.0 / fixed_observation_ms as f64,
            },
            "drained_arrival_cohort": {
                "arrival_start_frame": 0,
                "arrival_end_frame": fixed_observation_frames,
                "drain_end_frame": drain_horizon_frames,
                "drain_duration_after_arrivals_ms": drain_horizon_frames
                    .saturating_sub(fixed_observation_frames),
                "arrivals": cohort.arrivals,
                "completed": cohort.completed_by_drain,
                "completion_ratio": ratio(cohort.completed_by_drain, cohort.arrivals),
                "latency_ms": {
                    "mean": mean(&cohort.drained_latencies),
                    "p50": percentile(&cohort.drained_latencies, 0.50),
                    "p95": percentile(&cohort.drained_latencies, 0.95),
                    "p99": percentile(&cohort.drained_latencies, 0.99),
                },
            },
            "metric_definitions": {
                "frame_duration_ms": 1,
                "fixed_observation_window": {
                    "arrival_cohort": "request arrival_frame is in [0, end_frame)",
                    "completion_deadline": "request completion_frame is in [0, end_frame]",
                    "throughput": "completed requests at or before end_frame divided by duration_ms",
                    "throughput_unit": "requests/s",
                },
                "drained_arrival_cohort": {
                    "cohort": "the fixed-observation-window arrival cohort",
                    "completion_deadline": "request completion_frame is at or before drain_end_frame",
                    "latency_population": "completed requests from that cohort by drain_end_frame",
                    "latency_unit": "ms",
                },
                "legacy_top_level_fields": "preserved for compatibility; completed, completion_ratio, throughput_requests_per_second, and latency_ms retain final-run semantics with observation_time_ms as denominator",
            },
            "simulator_internal_cost_total": cost_total,
            "simulator_internal_cost_per_completed_request": if completed == 0 { Value::Null } else { json!(cost_total / completed as f64) },
            "queue_peak": state.queue_peak,
            "queue_area_request_frames": state.queue_area,
            "node_cpu_mean": divide(state.cpu_sum, state.node_sample_count as usize),
            "node_cpu_peak": state.cpu_peak,
            "node_memory_mean": divide(state.mem_sum, state.node_sample_count as usize),
            "node_memory_peak": state.mem_peak,
            "node_cpu_utilization_mean": cpu_utilization_mean,
            "node_cpu_utilization_p95": cpu_utilization_p95,
            "node_cpu_utilization_peak": cpu_utilization_peak,
            "node_memory_utilization_mean": memory_utilization_mean,
            "node_memory_utilization_p95": memory_utilization_p95,
            "node_memory_utilization_peak": memory_utilization_peak,
            "node_utilization_unit": "fraction_of_node_capacity",
            "node_utilization_definition": {
                "sampling": "one_sample_per_node_per_recorded_frame",
                "cpu_numerator": "node.cpu",
                "cpu_denominator": "node.rsc_limit.cpu",
                "memory_numerator": "node.unready_mem()",
                "memory_denominator": "node.rsc_limit.mem",
                "clipping": "none",
                "invalid_sample_policy": "exclude_non_finite_usage_or_capacity_negative_usage_or_non_positive_capacity",
                "cpu_valid_samples": state.cpu_utilization_samples.len(),
                "cpu_invalid_samples": state.cpu_utilization_invalid_samples,
                "memory_valid_samples": state.memory_utilization_samples.len(),
                "memory_invalid_samples": state.memory_utilization_invalid_samples,
            },
            "scheduler_window_count": state.scheduler_wall_ns.len(),
            "scheduler_wall_ns": distribution(&state.scheduler_wall_ns),
            "scheduler_thread_cpu_ns": distribution(&state.scheduler_cpu_ns),
            "placement_policy_wall_ns": distribution(&state.policy_wall_ns),
            "placement_policy_thread_cpu_ns": distribution(&state.policy_cpu_ns),
            "posthoc_welfare_evaluation_wall_ns": distribution(&state.welfare_evaluation_wall_ns),
            "posthoc_welfare_evaluation_thread_cpu_ns": distribution(&state.welfare_evaluation_cpu_ns),
            "scheduler_timing_definition": scheduler_timing_definition,
            "placement_rejections": state.placement_rejections_total,
            "qos_function_tasks": qos_function_task_counts(
                &state.qos_function_arrivals,
                &state.qos_function_completions,
            ),
            "qos_simulator_internal_cost": qos_cost_summary(
                &state.qos_internal_cost,
                &state.qos_function_arrivals,
                &state.qos_function_completions,
            ),
            "admission_drop": 0,
            "admission_reject": 0,
            "timeout": 0,
            "queue_semantics": "unbounded_wait_by_design",
        });
        atomic_json(&state.directory.join("summary.json"), &summary)
            .map_err(|error| format!("write experiment summary: {error}"))?;
        if let Some(frames) = state.frames.as_mut() {
            frames
                .finalize()
                .map_err(|error| format!("finalize frames: {error}"))?;
        }
        if let Some(requests) = state.requests.as_mut() {
            requests
                .finalize()
                .map_err(|error| format!("finalize requests: {error}"))?;
        }
        state
            .scheduler_windows
            .finalize()
            .map_err(|error| format!("finalize scheduler windows: {error}"))?;
        state.finalized = true;
        Ok(())
    }
}

fn request_event(env: &SimEnv, request: &Request) -> Value {
    let mut function_events = request
        .fn_metric
        .iter()
        .map(|(function_id, metric)| {
            let function = env.func(*function_id);
            json!({
                "function_id": function_id,
                "qos_class": &function.qos_class,
                "quality_weight": function.quality_weight,
                "node_id": request.get_fn_node(*function_id),
                "ready_schedule_frame": metric.ready_sche_time,
                "scheduled_frame": metric.sche_time,
                "data_received_frame": metric.data_recv_done_time,
                "cold_start_done_frame": metric.cold_start_done_time,
                "function_done_frame": metric.fn_done_time,
            })
        })
        .collect::<Vec<_>>();
    function_events.sort_by_key(|value| {
        value
            .get("function_id")
            .and_then(Value::as_u64)
            .unwrap_or(u64::MAX)
    });
    json!({
        "schema": "NSE_REQUEST_V1",
        "request_id": request.req_id,
        "dag_id": request.dag_i,
        "arrival_frame": request.begin_frame,
        "completion_frame": request.end_frame,
        "latency_ms": request.end_frame.saturating_sub(request.begin_frame),
        "functions": function_events,
    })
}

fn qos_function_task_counts(
    arrivals: &BTreeMap<String, u64>,
    completions: &BTreeMap<String, u64>,
) -> Value {
    let mut classes = arrivals
        .keys()
        .chain(completions.keys())
        .cloned()
        .collect::<Vec<_>>();
    classes.sort();
    classes.dedup();
    let values = classes
        .into_iter()
        .map(|class| {
            let arrived = arrivals.get(&class).copied().unwrap_or(0);
            let completed = completions.get(&class).copied().unwrap_or(0);
            (
                class,
                json!({
                    "arrived": arrived,
                    "completed": completed,
                    "active": arrived.saturating_sub(completed),
                    "completion_ratio": if arrived == 0 {
                        Value::Null
                    } else {
                        json!(completed as f64 / arrived as f64)
                    },
                }),
            )
        })
        .collect::<serde_json::Map<String, Value>>();
    Value::Object(values)
}

fn qos_cost_summary(
    costs: &BTreeMap<String, f64>,
    arrivals: &BTreeMap<String, u64>,
    completions: &BTreeMap<String, u64>,
) -> Value {
    let mut classes = costs
        .keys()
        .chain(arrivals.keys())
        .chain(completions.keys())
        .cloned()
        .collect::<Vec<_>>();
    classes.sort();
    classes.dedup();
    let values = classes
        .into_iter()
        .map(|class| {
            let total = costs.get(&class).copied().unwrap_or(0.0);
            let completed = completions.get(&class).copied().unwrap_or(0);
            (
                class,
                json!({
                    "unit": "simulator_internal_units",
                    "total": total,
                    "per_completed_function": if completed == 0 {
                        Value::Null
                    } else {
                        json!(total / completed as f64)
                    },
                    "is_currency": false,
                }),
            )
        })
        .collect::<serde_json::Map<String, Value>>();
    Value::Object(values)
}

fn atomic_json(path: &Path, value: &Value) -> io::Result<()> {
    let partial = PathBuf::from(format!("{}.partial", path.display()));
    let mut writer = BufWriter::new(File::create(&partial)?);
    serde_json::to_writer_pretty(&mut writer, value)?;
    writer.write_all(b"\n")?;
    writer.flush()?;
    drop(writer);
    if path.exists() {
        return Err(io::Error::new(
            io::ErrorKind::AlreadyExists,
            format!("refusing to overwrite {}", path.display()),
        ));
    }
    fs::rename(partial, path)
}

fn ratio(numerator: usize, denominator: usize) -> Option<f64> {
    (denominator > 0).then(|| numerator as f64 / denominator as f64)
}

fn divide(total: f64, count: usize) -> Option<f64> {
    (count > 0).then(|| total / count as f64)
}

/// Returns an un-clipped fraction of the node's configured capacity.
///
/// Invalid samples are excluded rather than coerced to zero: usage and capacity
/// must be finite, usage must be non-negative, and capacity must be positive.
/// Keeping the ratio un-clipped makes overload (utilization above 1.0) visible.
fn normalized_utilization(usage: f32, capacity: f32) -> Option<f64> {
    if !usage.is_finite() || !capacity.is_finite() || usage < 0.0 || capacity <= 0.0 {
        return None;
    }
    let utilization = usage as f64 / capacity as f64;
    utilization.is_finite().then_some(utilization)
}

#[derive(Debug, PartialEq)]
struct ArrivalCohortSummary {
    arrivals: usize,
    completed_by_observation: usize,
    completed_by_drain: usize,
    drained_latencies: Vec<f64>,
}

fn summarize_arrival_cohort(
    completed_timings: &[(usize, usize)],
    active_arrivals: &[usize],
    observation_end_frame: usize,
) -> ArrivalCohortSummary {
    let mut drained_latencies = completed_timings
        .iter()
        .filter(|(arrival, _)| *arrival < observation_end_frame)
        .map(|(arrival, completion)| completion.saturating_sub(*arrival) as f64)
        .collect::<Vec<_>>();
    drained_latencies.sort_by(f64::total_cmp);
    let completed_by_observation = completed_timings
        .iter()
        .filter(|(arrival, completion)| {
            *arrival < observation_end_frame && *completion <= observation_end_frame
        })
        .count();
    let completed_by_drain = drained_latencies.len();
    let active_in_cohort = active_arrivals
        .iter()
        .filter(|arrival| **arrival < observation_end_frame)
        .count();
    ArrivalCohortSummary {
        arrivals: completed_by_drain + active_in_cohort,
        completed_by_observation,
        completed_by_drain,
        drained_latencies,
    }
}

fn mean(values: &[f64]) -> Option<f64> {
    (!values.is_empty()).then(|| values.iter().sum::<f64>() / values.len() as f64)
}

/// Summarizes all valid node-frame samples in a run, rather than first averaging
/// each frame. This gives every observed node the same weight, including in
/// heterogeneous clusters.
fn utilization_summary(values: &[f64]) -> (Option<f64>, Option<f64>, Option<f64>) {
    let mut sorted = values
        .iter()
        .copied()
        .filter(|value| value.is_finite())
        .collect::<Vec<_>>();
    sorted.sort_by(f64::total_cmp);
    (
        mean(&sorted),
        percentile(&sorted, 0.95),
        sorted.last().copied(),
    )
}

fn percentile(values: &[f64], probability: f64) -> Option<f64> {
    if values.is_empty() {
        return None;
    }
    let rank = (values.len() as f64 * probability).ceil().max(1.0) as usize;
    let index = rank.saturating_sub(1).min(values.len() - 1);
    values.get(index).copied()
}

fn distribution(values: &[u64]) -> Value {
    if values.is_empty() {
        return Value::Null;
    }
    let mut sorted = values.to_vec();
    sorted.sort_unstable();
    let as_f64 = sorted.iter().map(|value| *value as f64).collect::<Vec<_>>();
    json!({
        "mean": mean(&as_f64),
        "p50": percentile(&as_f64, 0.50),
        "p95": percentile(&as_f64, 0.95),
        "p99": percentile(&as_f64, 0.99),
        "max": sorted.last(),
    })
}

#[cfg(test)]
mod tests {
    use std::collections::BTreeMap;

    use super::{
        normalized_utilization, percentile, qos_cost_summary, qos_function_task_counts, ratio,
        summarize_arrival_cohort, utilization_summary,
    };

    #[test]
    fn request_percentiles_use_nearest_rank_ceiling() {
        let values = (1..=100).map(|value| value as f64).collect::<Vec<_>>();
        assert_eq!(percentile(&values, 0.50), Some(50.0));
        assert_eq!(percentile(&values, 0.95), Some(95.0));
        assert_eq!(percentile(&values, 0.99), Some(99.0));
    }

    #[test]
    fn cohort_metrics_use_one_fixed_arrival_population_across_observe_and_drain() {
        let summary = summarize_arrival_cohort(
            &[(0, 10), (900, 1000), (900, 1200), (1000, 1001)],
            &[999, 1000],
            1000,
        );
        assert_eq!(summary.arrivals, 4);
        assert_eq!(summary.completed_by_observation, 2);
        assert_eq!(summary.completed_by_drain, 3);
        assert_eq!(summary.drained_latencies, vec![10.0, 100.0, 300.0]);
    }

    #[test]
    fn undefined_ratios_are_null_capable() {
        assert_eq!(ratio(0, 0), None);
        assert_eq!(ratio(5, 10), Some(0.5));
    }

    #[test]
    fn normalized_utilization_uses_capacity_without_clipping() {
        assert_eq!(normalized_utilization(75.0, 150.0), Some(0.5));
        assert_eq!(normalized_utilization(180.0, 150.0), Some(1.2));
    }

    #[test]
    fn normalized_utilization_rejects_invalid_samples() {
        assert_eq!(normalized_utilization(-1.0, 150.0), None);
        assert_eq!(normalized_utilization(1.0, 0.0), None);
        assert_eq!(normalized_utilization(1.0, f32::INFINITY), None);
        assert_eq!(normalized_utilization(f32::NAN, 150.0), None);
    }

    #[test]
    fn utilization_summary_is_over_node_frame_samples() {
        let values = (1..=100)
            .map(|value| value as f64 / 100.0)
            .collect::<Vec<_>>();
        let (mean, p95, peak) = utilization_summary(&values);
        assert_eq!(mean, Some(0.505));
        assert_eq!(p95, Some(0.95));
        assert_eq!(peak, Some(1.0));
    }

    #[test]
    fn utilization_summary_excludes_non_finite_values() {
        let (mean, p95, peak) = utilization_summary(&[0.5, f64::NAN, f64::INFINITY, 1.5]);
        assert_eq!(mean, Some(1.0));
        assert_eq!(p95, Some(1.5));
        assert_eq!(peak, Some(1.5));
        assert_eq!(utilization_summary(&[f64::NAN]), (None, None, None));
    }

    #[test]
    fn qos_function_counts_retain_incomplete_work() {
        let arrivals = BTreeMap::from([
            ("latency_sensitive".to_string(), 10),
            ("cost_sensitive".to_string(), 8),
        ]);
        let completions = BTreeMap::from([
            ("latency_sensitive".to_string(), 7),
            ("cost_sensitive".to_string(), 8),
        ]);
        let value = qos_function_task_counts(&arrivals, &completions);
        assert_eq!(value["latency_sensitive"]["active"], 3);
        assert_eq!(value["latency_sensitive"]["completion_ratio"], 0.7);
        assert_eq!(value["cost_sensitive"]["active"], 0);
    }

    #[test]
    fn qos_cost_uses_completed_function_denominator() {
        let costs = BTreeMap::from([("latency_sensitive".to_string(), 2.5)]);
        let arrivals = BTreeMap::from([("latency_sensitive".to_string(), 8)]);
        let completions = BTreeMap::from([("latency_sensitive".to_string(), 5)]);
        let value = qos_cost_summary(&costs, &arrivals, &completions);
        assert_eq!(value["latency_sensitive"]["per_completed_function"], 0.5);
        assert_eq!(value["latency_sensitive"]["is_currency"], false);
    }
}
