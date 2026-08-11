use std::{collections::BTreeMap, fs, path::Path};

use serde::Deserialize;
use sha2::{Digest, Sha256};

use crate::{config::WorkloadFrequencyProfileConfig, fn_dag::DagId};

const FREQUENCY_MAP_HASH_DOMAIN: &[u8] = b"NSE_WORKLOAD_FREQUENCY_MAP_V2_F32\0";

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct WorkloadFrequencyProfileArtifact {
    schema_version: String,
    profile_set_id: String,
    profile_id: String,
    load: String,
    source: serde_json::Value,
    rate_audit: RateAudit,
    dag_call_frequency: BTreeMap<String, [f64; 2]>,
}

#[derive(Debug, Deserialize)]
#[serde(deny_unknown_fields)]
struct RateAudit {
    model: String,
    request_frequency_scale: f64,
    expected_arrival_rate_rps: f64,
    submission_actual_arrival_rate_rps: f64,
}

fn sha256_hex(bytes: &[u8]) -> String {
    format!("{:x}", Sha256::digest(bytes))
}

fn validate_and_hash_frequency_map(
    frequencies: &BTreeMap<String, [f64; 2]>,
    expected_count: usize,
) -> Result<(BTreeMap<DagId, (f64, f64)>, String), String> {
    if frequencies.len() != expected_count {
        return Err(format!(
            "workload profile DAG count mismatch: expected={expected_count} observed={}",
            frequencies.len()
        ));
    }

    // The full artifact SHA binds exact f64 text. This secondary hash uses f32
    // bits so Python and serde_json cannot disagree by one f64 parsing ULP.
    let mut loaded = BTreeMap::new();
    let mut digest = Sha256::new();
    digest.update(FREQUENCY_MAP_HASH_DOMAIN);
    for expected_dag_id in 0..expected_count {
        let key = expected_dag_id.to_string();
        let [mean, cv] = frequencies
            .get(&key)
            .copied()
            .ok_or_else(|| format!("workload profile is missing DAG {expected_dag_id}"))?;
        if !mean.is_finite() || mean <= 0.0 || !cv.is_finite() || cv < 0.0 {
            return Err(format!(
                "workload profile DAG {expected_dag_id} has invalid mean/CV"
            ));
        }
        digest.update((expected_dag_id as u64).to_be_bytes());
        digest.update((mean as f32).to_bits().to_be_bytes());
        digest.update((cv as f32).to_bits().to_be_bytes());
        loaded.insert(expected_dag_id, (mean, cv));
    }
    Ok((loaded, format!("{:x}", digest.finalize())))
}

pub fn load_frozen_frequency_profile(
    config: &WorkloadFrequencyProfileConfig,
    request_freq: &str,
) -> Result<BTreeMap<DagId, (f64, f64)>, String> {
    let path = Path::new(&config.path);
    let bytes = fs::read(path)
        .map_err(|error| format!("read workload profile {}: {error}", path.display()))?;
    let observed_sha256 = sha256_hex(&bytes);
    if observed_sha256 != config.sha256 {
        return Err(format!(
            "workload profile SHA-256 mismatch: expected={} observed={observed_sha256}",
            config.sha256
        ));
    }
    let artifact: WorkloadFrequencyProfileArtifact = serde_json::from_slice(&bytes)
        .map_err(|error| format!("parse workload profile {}: {error}", path.display()))?;
    if artifact.schema_version != config.schema_version
        || artifact.profile_set_id != config.profile_set_id
        || artifact.profile_id != config.profile_id
        || artifact.load != config.load
        || artifact.load != request_freq
        || artifact.source != config.source
    {
        return Err("workload profile identity/provenance differs from config".to_string());
    }
    if !artifact.rate_audit.model.contains("truncated-normal")
        || artifact.rate_audit.request_frequency_scale != config.request_frequency_scale
        || artifact.rate_audit.expected_arrival_rate_rps != config.expected_arrival_rate_rps
        || artifact.rate_audit.submission_actual_arrival_rate_rps
            != config.submission_actual_arrival_rate_rps
    {
        return Err("workload profile rate audit differs from config".to_string());
    }
    let (loaded, frequency_sha256) =
        validate_and_hash_frequency_map(&artifact.dag_call_frequency, config.dag_count)?;
    if frequency_sha256 != config.dag_call_frequency_sha256 {
        return Err(format!(
            "workload frequency-map SHA-256 mismatch: expected={} observed={frequency_sha256}",
            config.dag_call_frequency_sha256
        ));
    }

    Ok(loaded)
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::path::PathBuf;

    fn tracked_profile(load: &str) -> (WorkloadFrequencyProfileConfig, PathBuf) {
        let path = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .join("..")
            .join("scripts")
            .join("reviewer_experiments")
            .join("protocol")
            .join("workload_profiles")
            .join("submission_v1")
            .join(format!("{load}.json"));
        let bytes = fs::read(&path).expect("read tracked profile");
        let document: serde_json::Value =
            serde_json::from_slice(&bytes).expect("parse tracked profile");
        let rate = &document["rate_audit"];
        let frequencies: BTreeMap<String, [f64; 2]> =
            serde_json::from_value(document["dag_call_frequency"].clone())
                .expect("parse frequencies");
        let (_, frequency_sha256) =
            validate_and_hash_frequency_map(&frequencies, 50).expect("hash frequencies");
        (
            WorkloadFrequencyProfileConfig {
                schema_version: document["schema_version"]
                    .as_str()
                    .expect("schema")
                    .to_string(),
                profile_set_id: document["profile_set_id"]
                    .as_str()
                    .expect("profile set")
                    .to_string(),
                profile_id: document["profile_id"]
                    .as_str()
                    .expect("profile id")
                    .to_string(),
                load: load.to_string(),
                path: path.to_string_lossy().into_owned(),
                sha256: sha256_hex(&bytes),
                dag_call_frequency_sha256: frequency_sha256,
                dag_count: 50,
                expected_arrival_rate_rps: rate["expected_arrival_rate_rps"]
                    .as_f64()
                    .expect("expected rate"),
                submission_actual_arrival_rate_rps: rate["submission_actual_arrival_rate_rps"]
                    .as_f64()
                    .expect("actual rate"),
                request_frequency_scale: rate["request_frequency_scale"].as_f64().expect("scale"),
                source: document["source"].clone(),
            },
            path,
        )
    }

    #[test]
    fn tracked_profiles_load_with_exact_identity() {
        for (load, expected_hash) in [
            (
                "low",
                "323290747f6eb52db0002196e34091cc249610ee46480155335256bf47f0f7f7",
            ),
            (
                "middle",
                "be66a5890b6b8d4594dcebb5d6b12ad827353add95ce2e511166e61684af1fdd",
            ),
            (
                "high",
                "10842c57245d684cbf42c69cfe78a0b3d1cd54cc534a8f517327d2001eb98a8c",
            ),
        ] {
            let (config, _) = tracked_profile(load);
            assert_eq!(config.dag_call_frequency_sha256, expected_hash);
            let profile = load_frozen_frequency_profile(&config, load).expect("load profile");
            assert_eq!(profile.len(), 50);
        }
    }

    #[test]
    fn profile_hash_mismatch_fails_closed() {
        let (mut config, _) = tracked_profile("low");
        config.sha256 = "0".repeat(64);
        let error = load_frozen_frequency_profile(&config, "low")
            .expect_err("changed artifact hash must fail");
        assert!(error.contains("SHA-256 mismatch"));
    }
}
