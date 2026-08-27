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


ROOT = Path("tmp/nse_e3e4_reuse_profiles_training_20260827_v90")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_reuse_profiles_training_plan_v90.json"
)
PLAN_SHA256 = "980452abb659e0c9c2cae0dc2e58ebdbe8516a061d325297d5e84380dff0ec9a"
SOURCE = Path(
    "tmp/nse_e3e4_operational_dev_20260827_v88/"
    "manifest.v88-pipeline-terminal-ocs.sla.json"
)
SOURCE_SHA256 = "d6d39bbbee1edc9eebbd5c8a433f07d7a21942c98afc6e772e4b0644988ddb3e"
BINARY = Path("tmp/nse_v89_build_6dcdf4e/release/serverless_sim.exe")
BINARY_SHA256 = "42d42a9587eecf80b5cb258a1645d032defed7e80a8fb3d29c3765cc1e1649d4"
REFERENCE_CATALOG = Path(
    "tmp/nse_e3e4_native_expert_training_20260827_v89/references.v89.catalog.json"
)
REFERENCE_CATALOG_SHA256 = (
    "ace5b0f2750d0d712083cd8814dce3371f6ef69f802cd4472909652e9b47a39f"
)
RECEIPT = ROOT / "prepared-training-v90.json"
TRAINING_SEEDS = {"E713", "E714", "E715"}
CONFIRMATION_SEEDS = ["E716", "E717", "E718"]
E3_CANDIDATES = (
    ("v90-e3-middle-transfer", "stable_faasrank_load_least_borda"),
    ("v90-e3-high-transfer", "stable_ocs"),
)
E4_CANDIDATE = (
    "v90-e4-middle-transfer",
    "stable_faasrank_load_least_borda",
)
OUTPUTS = {
    "v90-e3-middle-transfer": ROOT / "manifest.v90-e3-middle-transfer.sla.json",
    "v90-e3-high-transfer": ROOT / "manifest.v90-e3-high-transfer.sla.json",
    "v90-e4-middle-transfer": ROOT / "manifest.v90-e4-middle-transfer.sla.json",
}


def _assert_inputs() -> None:
    for path, expected in (
        (PLAN, PLAN_SHA256),
        (SOURCE, SOURCE_SHA256),
        (BINARY, BINARY_SHA256),
        (REFERENCE_CATALOG, REFERENCE_CATALOG_SHA256),
    ):
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(
                f"frozen V90 training input is missing or changed: {path}"
            )


def _rewrite_manifest(
    source: dict, *, candidate_id: str, profile: str, experiment_id: str
) -> dict:
    manifest = copy.deepcopy(source)
    if manifest.get("formal_results_eligible") is not False:
        raise RuntimeError("V90 training source must remain non-formal")
    if len(manifest.get("runs", [])) != 12:
        raise RuntimeError("V90 training source must contain exactly 12 source runs")
    if {run.get("seed") for run in manifest["runs"]} != TRAINING_SEEDS:
        raise RuntimeError("V90 training source seed set changed")
    if {run.get("experiment_id") for run in manifest["runs"]} != {"E3", "E4"}:
        raise RuntimeError("V90 training source experiment set changed")
    if any(run.get("method") != "sche_nash" for run in manifest["runs"]):
        raise RuntimeError("V90 training source contains a non-NSESche run")

    source_runs = [
        run for run in manifest["runs"] if run["experiment_id"] == experiment_id
    ]
    manifest["runs"] = []
    for source_run in source_runs:
        candidate = copy.deepcopy(source_run)
        candidate["variant"] = candidate_id
        candidate["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = profile
        metadata = candidate.setdefault("metadata", {})
        metadata["v90_training_plan_sha256"] = PLAN_SHA256
        metadata["v90_training_only"] = True
        metadata["v90_training_seed_metrics_previously_revealed"] = True
        metadata["v90_candidate_id"] = candidate_id
        metadata["v90_candidate_profile"] = profile
        metadata["v90_profile_origin"] = (
            "frozen-heterogeneous-E1-middle"
            if profile == "stable_faasrank_load_least_borda"
            else "frozen-heterogeneous-E1-high"
        )
        metadata["v90_resource_scaling_excluded"] = True
        metadata["v90_reference_catalog_sha256"] = REFERENCE_CATALOG_SHA256
        _assign_run_identity(candidate)
        manifest["runs"].append(candidate)

    manifest["created_at"] = utc_now()
    manifest["execution"]["command_template"][-1] = str(BINARY.resolve())
    marker = manifest["integration_smoke_shard"]
    marker["purpose"] = (
        f"V90 training-only {candidate_id} transfer on already revealed "
        f"E713-E715; plan_sha256={PLAN_SHA256}"
    )
    marker["v90_training_plan_sha256"] = PLAN_SHA256
    marker["v90_training_only"] = True
    marker["v90_candidate_selection_preregistered"] = True
    marker["v90_candidate_id"] = candidate_id
    marker["v90_candidate_profile"] = profile
    marker["v90_reference_catalog_sha256"] = REFERENCE_CATALOG_SHA256
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
    expected_runs = 9 if experiment_id == "E3" else 3
    if len(manifest["runs"]) != expected_runs:
        raise RuntimeError(f"V90 {candidate_id} run count must be {expected_runs}")
    if len(manifest["reference_build_dependencies"]) != expected_runs:
        raise RuntimeError(
            f"V90 {candidate_id} reference dependency count must be {expected_runs}"
        )
    catalog = json.loads(REFERENCE_CATALOG.read_text(encoding="utf-8"))
    if not {item["key"] for item in manifest["reference_build_dependencies"]}.issubset(
        set(catalog.get("entries", {}))
    ):
        raise RuntimeError("V89 reference catalog does not cover V90 dependencies")

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
        raise RuntimeError(f"refusing to overwrite V90 training root: {ROOT}")
    ROOT.mkdir(parents=True)
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    candidates = (*E3_CANDIDATES, E4_CANDIDATE)
    manifests = {}
    for candidate_id, profile in candidates:
        experiment_id = "E4" if candidate_id.startswith("v90-e4-") else "E3"
        manifest = _rewrite_manifest(
            source,
            candidate_id=candidate_id,
            profile=profile,
            experiment_id=experiment_id,
        )
        output = OUTPUTS[candidate_id]
        write_json_atomic(output, manifest)
        manifests[candidate_id] = manifest

    receipt = {
        "schema_version": "NSE_E3E4_REUSE_PROFILES_TRAINING_PREPARED_V90_V1",
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
        "reference_catalog_path": str(REFERENCE_CATALOG),
        "reference_catalog_sha256": REFERENCE_CATALOG_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": CONFIRMATION_SEEDS,
        "E3_candidates": [
            {"candidate_id": candidate_id, "profile": profile}
            for candidate_id, profile in E3_CANDIDATES
        ],
        "E4_candidate": {
            "candidate_id": E4_CANDIDATE[0],
            "profile": E4_CANDIDATE[1],
        },
        "run_count": sum(len(manifest["runs"]) for manifest in manifests.values()),
        "unique_reference_dependency_count": len(
            {
                dependency["key"]
                for manifest in manifests.values()
                for dependency in manifest["reference_build_dependencies"]
            }
        ),
        "new_reference_build_count": 0,
        "new_baseline_online_runs": 0,
        "output_manifests": {
            candidate_id: {
                "path": str(OUTPUTS[candidate_id]),
                "file_sha256": file_hash(OUTPUTS[candidate_id]),
                "manifest_hash": manifests[candidate_id]["manifest_hash"],
                "run_count": len(manifests[candidate_id]["runs"]),
                "reference_dependency_count": len(
                    manifests[candidate_id]["reference_build_dependencies"]
                ),
            }
            for candidate_id, _ in candidates
        },
        "scientific_summary_files_opened_during_preparation": 0,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(RECEIPT, receipt)
    print(
        json.dumps(
            {
                "outputs": {
                    candidate_id: str(OUTPUTS[candidate_id])
                    for candidate_id, _ in candidates
                },
                "runs": receipt["run_count"],
                "references": receipt["unique_reference_dependency_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
