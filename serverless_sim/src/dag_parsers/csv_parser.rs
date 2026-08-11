use csv::ReaderBuilder;
use std::fs::File;
use std::io;
use std::path::Path;

use crate::sim_env::SimEnv;

#[derive(Debug)]
pub struct TaskInfo {
    pub task_name: String,
    pub job_name: String,
    pub dependencies: Vec<u32>,
    pub task_id: u32,
}

fn select_job_name(mut job_names: Vec<String>, rng: f32) -> Option<String> {
    // The simulator RNG is seeded, but HashSet iteration is intentionally
    // randomized per process. Canonicalize the CSV-derived population before
    // applying the workload-seeded index so capture and replay select the same
    // DAGs in separate processes.
    job_names.sort_unstable();
    job_names.dedup();
    if job_names.is_empty() {
        return None;
    }

    let selected_index = ((rng.clamp(0.0, 1.0 - f32::EPSILON)) * job_names.len() as f32) as usize;
    job_names.get(selected_index).cloned()
}

pub fn parse_dag_csv(sim_env: &SimEnv) -> io::Result<Vec<TaskInfo>> {
    let file_path =
        Path::new(env!("CARGO_MANIFEST_DIR")).join("src/dag_parsers/filtered_tasks.csv");
    let file = File::open(file_path.clone())?;
    let mut rdr = ReaderBuilder::new().has_headers(true).from_reader(file);

    // 第一次遍历：用随机种子随机选一个 job_name
    let rng = sim_env.env_rand_f(0.0, 1.0);

    // Build a canonical population before using the workload-seeded draw.
    // File order and process-random hash state must not affect DAG selection.
    let job_names = rdr
        .records()
        .filter_map(|result| result.ok()) // 跳过无效行
        .map(|record| record[1].to_string()) // 提取 job_name
        .collect::<Vec<_>>();

    let selected_job_name = select_job_name(job_names, rng).ok_or_else(|| {
        io::Error::new(
            io::ErrorKind::InvalidData,
            "DAG CSV does not contain any job_name values",
        )
    })?;

    println!("job_name:{}", selected_job_name);

    let file = File::open(file_path)?; // 重新打开文件以重置读取器
    let mut rdr = ReaderBuilder::new().has_headers(true).from_reader(file);

    let mut tasks = Vec::new();

    for result in rdr.records() {
        let record = result.map_err(|e| io::Error::new(io::ErrorKind::InvalidData, e))?;

        if record[1] == selected_job_name {
            let task_name = record[0].to_string();

            // 提取 task_id 和 dependencies
            let mut parts = task_name.split('_');
            let task_id = parts
                .next()
                .and_then(|num| {
                    num.chars()
                        .filter(|c| c.is_digit(10))
                        .collect::<String>()
                        .parse()
                        .ok()
                })
                .unwrap_or_else(|| {
                    panic!("Failed to parse task_id from task_name: {}", task_name);
                });

            let mut dependencies: Vec<u32> =
                parts.filter_map(|num| num.parse::<u32>().ok()).collect();
            dependencies.sort();

            tasks.push(TaskInfo {
                task_name,
                job_name: selected_job_name.clone(),
                dependencies,
                task_id,
            });
        }
    }

    tasks.sort_by_key(|task| task.task_id);

    Ok(tasks)
}

#[cfg(test)]
mod tests {
    use super::select_job_name;

    #[test]
    fn seeded_job_selection_is_independent_of_input_order_and_duplicates() {
        let forward = vec!["j_20", "j_3", "j_10", "j_3"]
            .into_iter()
            .map(str::to_string)
            .collect();
        let reverse = vec!["j_10", "j_3", "j_20"]
            .into_iter()
            .map(str::to_string)
            .collect();

        assert_eq!(select_job_name(forward, 0.5), Some("j_20".to_string()));
        assert_eq!(select_job_name(reverse, 0.5), Some("j_20".to_string()));
    }

    #[test]
    fn seeded_job_selection_handles_empty_and_upper_boundary() {
        assert_eq!(select_job_name(Vec::new(), 0.5), None);
        assert_eq!(
            select_job_name(vec!["j_2".to_string(), "j_1".to_string()], 1.0),
            Some("j_2".to_string())
        );
    }

    #[test]
    fn different_seeded_draws_can_select_different_jobs() {
        let jobs = vec!["j_1".to_string(), "j_2".to_string(), "j_3".to_string()];
        assert_eq!(select_job_name(jobs.clone(), 0.0), Some("j_1".to_string()));
        assert_eq!(select_job_name(jobs, 0.99), Some("j_3".to_string()));
    }
}

// #[cfg(test)]
// mod tests {
//     use super::*;
//     use std::path::Path;

//     #[test]
//     fn test_parse_dag_csv() {
//         // 调用 parse_dag_csv 来解析该文件
//         let tasks = parse_dag_csv().expect("Failed to parse the CSV file");

//         // 输出解析的结果到终端
//         println!("Parsed tasks: {:#?}", tasks); // 使用 {:#?} 可以更好地格式化输出

//     }
// }
