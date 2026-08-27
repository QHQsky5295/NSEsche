from __future__ import annotations

import copy
import json
from pathlib import Path

from scripts.reviewer_experiments.protocol.matrix import _assign_run_identity
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


ROOT = Path("tmp/nse_e3e4_native_expert_training_20260827_v89")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_native_expert_training_plan_v89.json"
)
PLAN_SHA256 = "e1397e0301e9d94558e281f2d363acd8b5098069ddf6ef558a24304b09f440ef"
SOURCE = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v88/"
    "manifest.v88-pipeline-terminal-ocs.sla.json"
)
SOURCE_SHA256 = "d6d39bbbee1edc9eebbd5c8a433f07d7a21942c98afc6e772e4b0644988ddb3e"
BINARY = Path("tmp/nse_v89_build_6dcdf4e/release/serverless_sim.exe")
BINARY_SHA256 = "42d42a9587eecf80b5cb258a1645d032defed7e80a8fb3d29c3765cc1e1649d4"
OUTPUT = ROOT / "manifest.v89-native-expert-training.sla.json"
RECEIPT = ROOT / "prepared-training-v89.json"
TRAINING_SEEDS = {"E713", "E714", "E715"}
E3_PROFILE = "ocs_native_faithful_pipeline_dual_window_safe_pareto"
E4_PROFILE = "jiagu_native_faithful_window_safe_pareto"


def _assert_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (SOURCE, SOURCE_SHA256),
        (BINARY, BINARY_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(
                f"frozen V89 training input is missing or changed: {path}"
            )


def _rewrite_manifest(source: dict) -> dict:
    manifest = copy.deepcopy(source)
    if manifest.get("formal_results_eligible") is not False:
        raise RuntimeError("V89 training source must remain non-formal")
    if len(manifest.get("runs", [])) != 12:
        raise RuntimeError("V89 training source must contain exactly 12 runs")
    if {run.get("seed") for run in manifest["runs"]} != TRAINING_SEEDS:
        raise RuntimeError("V89 training source seed set changed")
    if {run.get("experiment_id") for run in manifest["runs"]} != {"E3", "E4"}:
        raise RuntimeError("V89 training source experiment set changed")
    if any(run.get("method") != "sche_nash" for run in manifest["runs"]):
        raise RuntimeError("V89 training source contains a non-NSESche run")

    manifest["created_at"] = utc_now()
    manifest["execution"]["command_template"][-1] = str(BINARY.resolve())
    marker = manifest["integration_smoke_shard"]
    marker["purpose"] = (
        "V89 training-only scenario-native expert repair on already revealed "
        f"E713-E715; plan_sha256={PLAN_SHA256}"
    )
    marker["v89_training_plan_sha256"] = PLAN_SHA256
    marker["v89_training_only"] = True
    marker["formal_results_eligible"] = False
    marker["new_baseline_online_runs"] = 0

    for run in manifest["runs"]:
        profile = E3_PROFILE if run["experiment_id"] == "E3" else E4_PROFILE
        variant = (
            "v89-training-native-ocs"
            if run["experiment_id"] == "E3"
            else "v89-training-native-jiagu"
        )
        run["variant"] = variant
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        metadata = run.setdefault("metadata", {})
        metadata["v89_training_plan_sha256"] = PLAN_SHA256
        metadata["v89_training_only"] = True
        metadata["v89_training_seed_metrics_previously_revealed"] = True
        metadata["v89_candidate_profile"] = profile
        metadata["v89_candidate_variant"] = variant
        metadata["v89_resource_scaling_excluded"] = True
        _assign_run_identity(run)

    manifest["reference_build_dependencies"] = _reference_build_dependencies(
        manifest["runs"]
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
        raise RuntimeError(f"refusing to overwrite V89 training root: {ROOT}")
    ROOT.mkdir(parents=True)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifest = _rewrite_manifest(source)
    write_json_atomic(OUTPUT, manifest)
    receipt = {
        "schema_version": "NSE_E3E4_NATIVE_EXPERT_TRAINING_PREPARED_V89_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "training_metrics_previously_revealed": True,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "source_manifest_path": str(SOURCE),
        "source_manifest_sha256": SOURCE_SHA256,
        "binary_path": str(BINARY),
        "binary_sha256": BINARY_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": ["E716", "E717", "E718"],
        "E3_profile": E3_PROFILE,
        "E4_profile": E4_PROFILE,
        "run_count": len(manifest["runs"]),
        "reference_build_count": len(manifest["reference_build_dependencies"]),
        "new_baseline_online_runs": 0,
        "output_manifest_path": str(OUTPUT),
        "output_manifest_sha256": file_hash(OUTPUT),
        "output_manifest_hash": manifest["manifest_hash"],
        "scientific_summary_files_opened_during_preparation": 0,
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
