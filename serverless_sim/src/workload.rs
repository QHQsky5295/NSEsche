use std::{
    cell::RefCell,
    collections::BTreeMap,
    fs,
    io::{BufReader, BufWriter, Write},
    path::{Path, PathBuf},
};

use serde::{Deserialize, Serialize};

use crate::{config::Config, fn_dag::DagId};

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq, Eq)]
pub struct WorkloadEvent {
    pub frame: usize,
    pub dag_id: DagId,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct WorkloadTapeFile {
    pub version: u32,
    pub workload_seed: String,
    pub events: Vec<WorkloadEvent>,
}

#[derive(Clone, Copy, Debug, PartialEq, Eq)]
enum TapeMode {
    Generated,
    Capture,
    Replay,
}

pub struct WorkloadTapeRuntime {
    mode: TapeMode,
    path: Option<PathBuf>,
    replay_by_frame: BTreeMap<usize, Vec<DagId>>,
    captured: RefCell<Vec<WorkloadEvent>>,
    workload_seed: String,
}

impl WorkloadTapeRuntime {
    pub fn new(config: &Config) -> Result<Self, String> {
        let raw_mode = config.experiment.workload.mode.trim().to_ascii_lowercase();
        let mode = match raw_mode.as_str() {
            "" | "generated" => TapeMode::Generated,
            "capture" => TapeMode::Capture,
            "replay" => TapeMode::Replay,
            other => return Err(format!("unsupported workload tape mode: {other}")),
        };
        let path = resolved_tape_path(config, mode);
        let mut replay_by_frame = BTreeMap::<usize, Vec<DagId>>::new();
        if mode == TapeMode::Replay {
            let path = path
                .as_ref()
                .ok_or_else(|| "replay mode requires workload.tape_path".to_string())?;
            let file = fs::File::open(path)
                .map_err(|error| format!("open workload tape {}: {error}", path.display()))?;
            let tape: WorkloadTapeFile = serde_json::from_reader(BufReader::new(file))
                .map_err(|error| format!("parse workload tape {}: {error}", path.display()))?;
            if tape.workload_seed != config.workload_seed() {
                return Err(format!(
                    "workload tape seed mismatch: tape={} config={}",
                    tape.workload_seed,
                    config.workload_seed()
                ));
            }
            for event in tape.events {
                replay_by_frame
                    .entry(event.frame)
                    .or_default()
                    .push(event.dag_id);
            }
        }
        Ok(Self {
            mode,
            path,
            replay_by_frame,
            captured: RefCell::new(Vec::new()),
            workload_seed: config.workload_seed().to_string(),
        })
    }

    pub fn is_replay(&self) -> bool {
        self.mode == TapeMode::Replay
    }

    pub fn replay_events(&self, frame: usize) -> Vec<DagId> {
        self.replay_by_frame
            .get(&frame)
            .cloned()
            .unwrap_or_default()
    }

    pub fn replay_event_count_before(&self, horizon: usize) -> usize {
        self.replay_by_frame
            .range(..horizon)
            .map(|(_, dag_ids)| dag_ids.len())
            .sum()
    }

    pub fn replay_dag_counts_before(&self, horizon: usize) -> BTreeMap<DagId, usize> {
        let mut counts = BTreeMap::new();
        for (_, dag_ids) in self.replay_by_frame.range(..horizon) {
            for dag_id in dag_ids {
                *counts.entry(*dag_id).or_default() += 1;
            }
        }
        counts
    }

    pub fn record(&self, frame: usize, dag_id: DagId) {
        if self.mode == TapeMode::Capture {
            self.captured
                .borrow_mut()
                .push(WorkloadEvent { frame, dag_id });
        }
    }

    pub fn flush(&self) -> Result<(), String> {
        if self.mode != TapeMode::Capture {
            return Ok(());
        }
        let path = self
            .path
            .as_ref()
            .ok_or_else(|| "capture mode has no workload tape path".to_string())?;
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)
                .map_err(|error| format!("create tape directory {}: {error}", parent.display()))?;
        }
        let partial = partial_path(path);
        let file = fs::File::create(&partial)
            .map_err(|error| format!("create workload tape {}: {error}", partial.display()))?;
        let tape = WorkloadTapeFile {
            version: 1,
            workload_seed: self.workload_seed.clone(),
            events: self.captured.borrow().clone(),
        };
        let mut writer = BufWriter::new(file);
        serde_json::to_writer(&mut writer, &tape)
            .map_err(|error| format!("serialize workload tape: {error}"))?;
        writer
            .write_all(b"\n")
            .map_err(|error| format!("finish workload tape: {error}"))?;
        writer
            .flush()
            .map_err(|error| format!("flush workload tape: {error}"))?;
        drop(writer);
        if path.exists() {
            fs::remove_file(path)
                .map_err(|error| format!("replace workload tape {}: {error}", path.display()))?;
        }
        fs::rename(&partial, path).map_err(|error| {
            format!(
                "finalize workload tape {} -> {}: {error}",
                partial.display(),
                path.display()
            )
        })
    }
}

fn resolved_tape_path(config: &Config, mode: TapeMode) -> Option<PathBuf> {
    if !config.experiment.workload.tape_path.trim().is_empty() {
        return Some(PathBuf::from(&config.experiment.workload.tape_path));
    }
    if mode != TapeMode::Capture || config.experiment.run_id.is_empty() {
        return None;
    }
    Some(
        Path::new(&config.experiment.output.root)
            .join(&config.experiment.run_id)
            .join("workload_tape.json"),
    )
}

fn partial_path(path: &Path) -> PathBuf {
    let mut value = path.as_os_str().to_os_string();
    value.push(".partial");
    PathBuf::from(value)
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn generated_mode_has_no_events() {
        let config = Config::new_test();
        let tape = WorkloadTapeRuntime::new(&config).expect("generated tape");
        assert!(!tape.is_replay());
        assert!(tape.replay_events(10).is_empty());
    }

    #[test]
    fn captured_tape_replays_exact_events() {
        let directory = std::env::temp_dir().join(format!(
            "serverless_sim_workload_test_{}",
            std::process::id()
        ));
        let path = directory.join("tape.json");
        let mut config = Config::new_test();
        config.experiment.workload_seed = "workload-E01".to_string();
        config.experiment.workload.mode = "capture".to_string();
        config.experiment.workload.tape_path = path.to_string_lossy().into_owned();
        let capture = WorkloadTapeRuntime::new(&config).expect("capture tape");
        capture.record(4, 2);
        capture.record(4, 1);
        capture.record(8, 3);
        capture.flush().expect("publish tape");
        assert!(path.exists());
        assert!(!partial_path(&path).exists());

        config.experiment.workload.mode = "replay".to_string();
        let replay = WorkloadTapeRuntime::new(&config).expect("replay tape");
        assert_eq!(replay.replay_events(4), vec![2, 1]);
        assert_eq!(replay.replay_events(8), vec![3]);
        assert!(replay.replay_events(9).is_empty());
        assert_eq!(replay.replay_event_count_before(8), 2);
        assert_eq!(replay.replay_event_count_before(9), 3);
        assert_eq!(
            replay.replay_dag_counts_before(9),
            BTreeMap::from([(1, 1), (2, 1), (3, 1)])
        );

        fs::remove_file(&path).expect("remove test tape");
        fs::remove_dir(&directory).expect("remove test directory");
    }
}
