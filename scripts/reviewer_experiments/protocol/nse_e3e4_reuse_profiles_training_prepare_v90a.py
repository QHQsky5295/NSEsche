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


ROOT = Path("tmp/nse_e3e4_reuse_profiles_training_20260828_v90a")
PARENT_PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_training_plan_v90.json"
)
PARENT_PLAN_SHA256 = "980452abb659e0c9c2cae0dc2e58ebdbe8516a061d325297d5e84380dff0ec9a"
AMENDMENT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_training_amendment_v90a.json"
)
AMENDMENT_SHA256 = "ac7e9a292b0545c8d5e435461c07cb4d5632875df431e62257537453264b79b7"
FAILURE_RECEIPT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_technical_failure_v90.json"
)
FAILURE_RECEIPT_SHA256 = (
    "e08e0d8c6082ce8e7bdb492f7decacb4a8ff8a3076b3913823a5c9743c35dd9a"
)
SOURCE = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v88/"
    "manifest.v88-pipeline-terminal-ocs.sla.json"
)
SOURCE_SHA256 = "d6d39bbbee1edc9eebbd5c8a433f07d7a21942c98afc6e772e4b0644988ddb3e"
BINARY = Path("tmp/nse_v89_build_6dcdf4e/release/serverless_sim.exe")
BINARY_SHA256 = "42d42a9587eecf80b5cb258a1645d032defed7e80a8fb3d29c3765cc1e1649d4"
RECEIPT = ROOT / "prepared-training-v90a.json"
TRAINING_SEEDS = {"E713", "E714", "E715"}
CANDIDATES = (
    (
        "v90-e3-middle-transfer",
        "stable_faasrank_load_least_borda",
        "E3",
    ),
    ("v90-e3-high-transfer", "stable_ocs", "E3"),
    (
        "v90-e4-middle-transfer",
        "stable_faasrank_load_least_borda",
        "E4",
    ),
)


def _output(candidate_id: str) -> Path:
    return ROOT / f"manifest.{candidate_id}.sla.json"


def _assert_inputs() -> None:
    for path, expected in (
        (PARENT_PLAN, PARENT_PLAN_SHA256),
        (AMENDMENT, AMENDMENT_SHA256),
        (FAILURE_RECEIPT, FAILURE_RECEIPT_SHA256),
        (SOURCE, SOURCE_SHA256),
        (BINARY, BINARY_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V90A input is missing or changed: {path}")


def _rewrite_manifest(
    source: dict, *, candidate_id: str, profile: str, experiment_id: str
) -> dict:
    manifest = copy.deepcopy(source)
    if manifest.get("formal_results_eligible") is not False:
        raise RuntimeError("V90A source must remain non-formal")
    if len(manifest.get("runs", [])) != 12:
        raise RuntimeError("V90A source must contain exactly 12 runs")
    if {run.get("seed") for run in manifest["runs"]} != TRAINING_SEEDS:
        raise RuntimeError("V90A source seed set changed")
    source_runs = [
        run for run in manifest["runs"] if run["experiment_id"] == experiment_id
    ]
    manifest["runs"] = []
    for source_run in source_runs:
        run = copy.deepcopy(source_run)
        run["variant"] = candidate_id
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        metadata = run.setdefault("metadata", {})
        metadata["v90_parent_plan_sha256"] = PARENT_PLAN_SHA256
        metadata["v90a_amendment_sha256"] = AMENDMENT_SHA256
        metadata["v90a_technical_correction_only"] = True
        metadata["v90a_training_only"] = True
        metadata["v90a_candidate_id"] = candidate_id
        metadata["v90a_candidate_profile"] = profile
        metadata["v90a_failed_v90_attempts_retained"] = True
        metadata["v90a_confirmation_seeds_untouched"] = True
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"]["table_path"] = run[
            "reference_dependency"
        ]["path"]
        _assign_run_identity(run)
        manifest["runs"].append(run)

    manifest["created_at"] = utc_now()
    manifest["execution"]["command_template"][-1] = str(BINARY.resolve())
    marker = manifest["integration_smoke_shard"]
    marker["purpose"] = (
        f"V90A technical correction for {candidate_id}; candidate set and "
        f"training seeds unchanged; amendment_sha256={AMENDMENT_SHA256}"
    )
    marker["v90_parent_plan_sha256"] = PARENT_PLAN_SHA256
    marker["v90a_amendment_sha256"] = AMENDMENT_SHA256
    marker["v90a_technical_correction_only"] = True
    marker["v90a_candidate_id"] = candidate_id
    marker["v90a_candidate_profile"] = profile
    marker["formal_results_eligible"] = False
    marker["new_baseline_online_runs"] = 0
    marker["selected_source_runs"] = [
        entry
        for entry in marker["selected_source_runs"]
        if entry["source_cell_id"].startswith(f"{experiment_id}.")
    ]
    manifest["reference_build_dependencies"] = _reference_build_dependencies(
        manifest["runs"]
    )
    expected = 9 if experiment_id == "E3" else 3
    if len(manifest["runs"]) != expected:
        raise RuntimeError(f"V90A {candidate_id} run count must be {expected}")
    if len(manifest["reference_build_dependencies"]) != expected:
        raise RuntimeError(f"V90A {candidate_id} reference count must be {expected}")
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
        raise RuntimeError(f"refusing to overwrite V90A root: {ROOT}")
    ROOT.mkdir(parents=True)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    manifests = {}
    all_keys = set()
    for candidate_id, profile, experiment_id in CANDIDATES:
        manifest = _rewrite_manifest(
            source,
            candidate_id=candidate_id,
            profile=profile,
            experiment_id=experiment_id,
        )
        output = _output(candidate_id)
        write_json_atomic(output, manifest)
        manifests[candidate_id] = manifest
        keys = {
            dependency["key"] for dependency in manifest["reference_build_dependencies"]
        }
        if all_keys.intersection(keys):
            raise RuntimeError("V90A candidate reference key sets must be disjoint")
        all_keys.update(keys)
    if len(all_keys) != 21:
        raise RuntimeError("V90A must bind 21 candidate-specific reference keys")

    receipt = {
        "schema_version": "NSE_E3E4_REUSE_PROFILES_TRAINING_PREPARED_V90A_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "parent_plan_sha256": PARENT_PLAN_SHA256,
        "amendment_sha256": AMENDMENT_SHA256,
        "technical_failure_receipt_sha256": FAILURE_RECEIPT_SHA256,
        "source_manifest_sha256": SOURCE_SHA256,
        "binary_sha256": BINARY_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": ["E716", "E717", "E718"],
        "candidate_set_changed": False,
        "run_count": sum(len(manifest["runs"]) for manifest in manifests.values()),
        "candidate_specific_reference_build_count": len(all_keys),
        "new_baseline_online_runs": 0,
        "output_manifests": {
            candidate_id: {
                "path": str(_output(candidate_id)),
                "file_sha256": file_hash(_output(candidate_id)),
                "manifest_hash": manifests[candidate_id]["manifest_hash"],
                "run_count": len(manifests[candidate_id]["runs"]),
                "reference_dependency_count": len(
                    manifests[candidate_id]["reference_build_dependencies"]
                ),
            }
            for candidate_id, _, _ in CANDIDATES
        },
        "scientific_summary_files_opened_during_preparation": 0,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "root": str(ROOT),
                "runs": receipt["run_count"],
                "references": receipt["candidate_specific_reference_build_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
