from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_srpt_ready_native_training_20260828_v93")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_srpt_ready_native_training_design_v93.json"
)
PLAN_SHA256 = "3795b9bc8ed6c4f5cb05607178b80c29a115ce6c7952591798917535366f1d09"
V92_RESULT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_strict_native_per_player_training_result_v92.json"
)
V92_RESULT_SHA256 = "b77dda8c53868dfdc9e0fbf6fbe818d47d5aea2fe5ed0ac3dc0377b3753c9aea"
SOURCE = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v88/"
    "manifest.v88-pipeline-terminal-ocs.sla.json"
)
SOURCE_SHA256 = "d6d39bbbee1edc9eebbd5c8a433f07d7a21942c98afc6e772e4b0644988ddb3e"
BINARY = Path("tmp/nse_v93_build_67a3c70/release/serverless_sim.exe")
BINARY_SHA256 = "5c3fc338eda895fd7fcb34bdc0c8056d8bb17e756a03c36437ac5b83ff188eab"
BINARY_SOURCE_COMMIT = "67a3c70134ecde84ee723b3f885cf3c77c5d1617"
OUTPUT = ROOT / "manifest.v93-srpt-ready-native-training.sla.json"
RECEIPT = ROOT / "prepared-training-v93.json"
TRAINING_SEEDS = {"E713", "E714", "E715"}
CONFIRMATION_SEEDS = ["E716", "E717", "E718"]
E3_PROFILE = "ocs_native_exact_srpt_ready_per_player_strict_pareto"
E4_PROFILE = "jiagu_native_exact_srpt_ready_per_player_strict_pareto"


def _assert_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (V92_RESULT, V92_RESULT_SHA256),
        (SOURCE, SOURCE_SHA256),
        (BINARY, BINARY_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(
                f"frozen V93 training input is missing or changed: {path}"
            )


def _rewrite_manifest(source: dict) -> dict:
    manifest = copy.deepcopy(source)
    if manifest.get("formal_results_eligible") is not False:
        raise RuntimeError("V93 training source must remain non-formal")
    if len(manifest.get("runs", [])) != 12:
        raise RuntimeError("V93 training source must contain exactly 12 runs")
    if {run.get("seed") for run in manifest["runs"]} != TRAINING_SEEDS:
        raise RuntimeError("V93 training source seed set changed")
    if {run.get("experiment_id") for run in manifest["runs"]} != {"E3", "E4"}:
        raise RuntimeError("V93 training source experiment set changed")
    if any(run.get("method") != "sche_nash" for run in manifest["runs"]):
        raise RuntimeError("V93 training source contains a non-NSESche run")

    source_reference_keys = {
        dependency["key"] for dependency in manifest["reference_build_dependencies"]
    }
    manifest["created_at"] = utc_now()
    manifest["execution"]["command_template"][-1] = str(BINARY.resolve())
    marker = manifest["integration_smoke_shard"]
    marker["purpose"] = (
        "V93 training-only exact native SRPT-ready initializer with the frozen "
        f"strict-player Pareto guard on revealed E713-E715; plan_sha256={PLAN_SHA256}"
    )
    marker["v93_training_plan_sha256"] = PLAN_SHA256
    marker["v93_training_only"] = True
    marker["v93_binary_source_commit"] = BINARY_SOURCE_COMMIT
    marker["v93_strict_player_improvement_required"] = True
    marker["v93_srpt_ready_frontier_required"] = True
    marker["v93_complete_v92_cohort_retained"] = True
    marker["formal_results_eligible"] = False
    marker["new_baseline_online_runs"] = 0

    for run in manifest["runs"]:
        profile = E3_PROFILE if run["experiment_id"] == "E3" else E4_PROFILE
        variant = (
            "v93-training-srpt-ready-exact-ocs"
            if run["experiment_id"] == "E3"
            else "v93-training-srpt-ready-exact-jiagu"
        )
        run["variant"] = variant
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        metadata = run.setdefault("metadata", {})
        metadata["v93_training_plan_sha256"] = PLAN_SHA256
        metadata["v93_training_only"] = True
        metadata["v93_training_seed_metrics_previously_revealed"] = True
        metadata["v93_candidate_profile"] = profile
        metadata["v93_candidate_variant"] = variant
        metadata["v93_binary_source_commit"] = BINARY_SOURCE_COMMIT
        metadata["v93_exact_native_initializer"] = True
        metadata["v93_every_player_expert_nonworsening_certificate"] = True
        metadata["v93_at_least_one_player_strict_expert_improvement"] = True
        metadata["v93_parent_complete_ready_frontier"] = True
        metadata["v93_srpt_player_order"] = True
        metadata["v93_native_expert_demand_context_retained"] = True
        metadata["v93_resource_scaling_excluded"] = True
        metadata["v93_complete_v92_cohort_retained"] = True
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"]["table_path"] = run[
            "reference_dependency"
        ]["path"]
        _assign_run_identity(run)

    manifest["reference_build_dependencies"] = _reference_build_dependencies(
        manifest["runs"]
    )
    candidate_reference_keys = {
        dependency["key"] for dependency in manifest["reference_build_dependencies"]
    }
    if len(candidate_reference_keys) != 12:
        raise RuntimeError("V93 must have exactly 12 candidate-specific references")
    if source_reference_keys & candidate_reference_keys:
        raise RuntimeError(
            "V93 environment-bound references unexpectedly reuse source keys"
        )
    manifest["matrix_summary"] = _matrix_summary(
        manifest["runs"], manifest["reuse_analyses"]
    )
    marker["selected_run_count"] = len(manifest["runs"])
    marker["selected_reference_build_count"] = len(
        manifest["reference_build_dependencies"]
    )
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def main() -> None:
    _assert_inputs()
    if ROOT.exists():
        raise RuntimeError(f"refusing to overwrite V93 training root: {ROOT}")
    ROOT.mkdir(parents=True)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifest = _rewrite_manifest(source)
    write_json_atomic(OUTPUT, manifest)
    receipt = {
        "schema_version": "NSE_E3E4_SRPT_READY_NATIVE_TRAINING_PREPARED_V93_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_metrics_previously_revealed": True,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "V92_result_path": str(V92_RESULT),
        "V92_result_sha256": V92_RESULT_SHA256,
        "source_manifest_path": str(SOURCE),
        "source_manifest_sha256": SOURCE_SHA256,
        "binary_path": str(BINARY),
        "binary_sha256": BINARY_SHA256,
        "binary_source_commit": BINARY_SOURCE_COMMIT,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "E3_profile": E3_PROFILE,
        "E4_profile": E4_PROFILE,
        "run_count": len(manifest["runs"]),
        "reference_build_count": len(manifest["reference_build_dependencies"]),
        "new_baseline_online_runs": 0,
        "output_manifest_path": str(OUTPUT),
        "output_manifest_sha256": file_hash(OUTPUT),
        "output_manifest_hash": manifest["manifest_hash"],
        "scientific_summary_files_opened_during_preparation": 0,
        "confirmation_seeds_opened": False,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "output": str(OUTPUT),
                "runs": len(manifest["runs"]),
                "references": len(manifest["reference_build_dependencies"]),
                "manifest_hash": manifest["manifest_hash"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
