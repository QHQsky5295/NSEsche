from __future__ import annotations

import copy
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.formal_e2_nsesche_overlay import (
    FORMAL_E2_NSESCHE_OVERLAY_MARKER,
    FORMAL_E2_NSESCHE_OVERLAY_SCHEMA,
    TARGET_VARIANT,
    _matrix_summary,
)
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_build_dependencies,
    _reference_dependency,
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_SHARD_MARKERS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import object_hash, read_json


HASH = "1" * 64
BASELINE_BINARY = "2" * 64
MODEL_SHA = "3" * 64
TRAINING_SHA = "4" * 64
PAYLOAD_SHA = "5" * 64


def _artifact_lineage(run: dict) -> dict:
    return {
        "source_stage": "initial" if int(run["seed"][1:]) <= 10 else "ci_extension",
        "source_manifest_path": "source.json",
        "source_manifest_hash": HASH,
        "source_manifest_file_sha256": HASH,
        "source_run_id": run["run_id"],
        "source_run_spec_hash": run["run_spec_hash"],
        "source_cell_id": run["cell_id"],
        "source_method": run["method"],
        "source_variant": run.get("variant", "full"),
        "source_seed": run["seed"],
        "source_workload_spec_hash": run["workload_spec_hash"],
        "source_workload_tape_key": run["workload_tape"]["key"],
        "source_workload_tape_sha256": HASH,
        "source_common_hpa_hash": run["common_hpa_hash"],
        "source_cluster_sha256": object_hash(run["cluster"]),
        "source_simulation_sha256": object_hash(run["simulation"]),
        "source_canonical_directory": "canonical/run",
        "source_audit_manifest_sha256": HASH,
        "source_qc_report_sha256": HASH,
        "source_summary_sha256": HASH,
        "source_runtime_identity": {
            "binary_sha256": BASELINE_BINARY,
            "python_sha256": HASH,
            "git_commit": "a" * 40,
            "cargo_lock_sha256": HASH,
        },
    }


def _overlay_fixture() -> dict:
    manifest = build_manifest(load_protocol_config(), "all")
    plan = read_json(
        Path(
            "scripts/reviewer_experiments/protocol/"
            "nse_formal_e2_low_n100_overlay_plan_v77.json"
        )
    )
    selected_environment = copy.deepcopy(plan["frozen_candidate"]["environment"])
    target = [
        run
        for run in manifest["runs"]
        if run["experiment_id"] == "E2"
        and run["workload"]["request_freq"] == "low"
        and run["cluster"]["node_count"] == 100
    ]
    candidate_sources = [run for run in target if run["method"] == "sche_nash"]
    baselines = [run for run in target if run["method"] != "sche_nash"]
    candidates = []
    source_lineage = []
    for source in candidate_sources:
        run = copy.deepcopy(source)
        run["variant"] = TARGET_VARIANT
        run["environment"].update(selected_environment)
        model = run["simulator_experiment"]["faasrank_model"]
        model.update(
            {
                "state": "frozen",
                "model_sha256": MODEL_SHA,
                "training_tape_sha256": TRAINING_SHA,
            }
        )
        run["workload_tape"]["sha256"] = HASH
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
        candidates.append(run)
        source_lineage.append(
            {
                "source_stage": (
                    "initial" if int(source["seed"][1:]) <= 10 else "ci_extension"
                ),
                "source_run_id": source["run_id"],
                "source_run_spec_hash": source["run_spec_hash"],
                "source_cell_id": source["cell_id"],
                "source_seed": source["seed"],
                "source_workload_spec_hash": source["workload_spec_hash"],
                "source_workload_tape_key": source["workload_tape"]["key"],
                "source_workload_tape_sha256": HASH,
                "source_common_hpa_hash": source["common_hpa_hash"],
                "source_cluster_sha256": object_hash(source["cluster"]),
                "source_simulation_sha256": object_hash(source["simulation"]),
                "derived_run_id": run["run_id"],
                "derived_run_spec_hash": run["run_spec_hash"],
            }
        )

    for marker in FORMAL_SHARD_MARKERS:
        manifest.pop(marker, None)
    manifest["runs"] = sorted(candidates, key=lambda run: run["seed"])
    manifest["formal_results_eligible"] = True
    manifest["reference_build_dependencies"] = _reference_build_dependencies(
        manifest["runs"]
    )
    manifest["matrix_summary"] = _matrix_summary(
        manifest["runs"], manifest["reuse_analyses"]
    )
    manifest["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        "serverless_sim.exe",
    ]
    manifest[FORMAL_E2_NSESCHE_OVERLAY_MARKER] = {
        "schema_version": FORMAL_E2_NSESCHE_OVERLAY_SCHEMA,
        "plan": {
            "path": "plan.json",
            "file_sha256": HASH,
            "schema_version": "NSE_FORMAL_E2_NSESCHE_OVERLAY_PLAN_V77",
        },
        "source_manifests": [
            {
                "path": "initial.json",
                "manifest_hash": HASH,
                "file_sha256": HASH,
                "seed_stage": "initial",
                "canonical_root": "initial/canonical",
            },
            {
                "path": "extension.json",
                "manifest_hash": HASH,
                "file_sha256": HASH,
                "seed_stage": "ci_extension",
                "canonical_root": "extension/canonical",
            },
        ],
        "selection": copy.deepcopy(plan["matrix"]),
        "selected_profile": {
            "path": "selected.json",
            "file_sha256": HASH,
            "profile_id": "faasrank_native_faithful_completion_pareto",
            "environment": selected_environment,
            "binary_path": "serverless_sim.exe",
            "binary_sha256": HASH,
            "faasrank_model_path": "faasrank.frozen.json",
            "faasrank_model_sha256": MODEL_SHA,
            "faasrank_rust_model_payload_hash": PAYLOAD_SHA,
            "faasrank_training_tape_sha256": TRAINING_SHA,
        },
        "selected_source_runs": source_lineage,
        "frozen_baseline_runs": [_artifact_lineage(run) for run in baselines],
        "historical_nsesche_runs": [
            _artifact_lineage(run) for run in candidate_sources
        ],
        "versioned_runtime_contract": {},
        "frozen_baseline_runtime": {
            "binary_sha256": BASELINE_BINARY,
            "python_sha256": HASH,
            "cargo_lock_sha256": HASH,
            "common_hpa_hash": manifest["common_hpa_hash"],
        },
        "selected_run_count": 20,
        "selected_cell_count": 1,
        "selected_reference_build_count": 20,
        "frozen_baseline_run_count": 180,
        "historical_nsesche_run_count": 20,
        "performance_results_consulted": False,
    }
    manifest.pop("manifest_hash", None)
    manifest["manifest_hash"] = object_hash(manifest)
    return manifest


class FormalE2NSEScheOverlayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.overlay = _overlay_fixture()

    def test_exact_overlay_product_validates(self) -> None:
        validate_manifest(copy.deepcopy(self.overlay))
        self.assertEqual(len(self.overlay["runs"]), 20)
        self.assertEqual(
            len(self.overlay[FORMAL_E2_NSESCHE_OVERLAY_MARKER]["frozen_baseline_runs"]),
            180,
        )

    def test_environment_and_baseline_tampering_fail_closed(self) -> None:
        changed_environment = copy.deepcopy(self.overlay)
        changed_environment["runs"][0]["environment"][
            "NASH_OPERATIONAL_SWITCH_THRESHOLD"
        ] = "1.0"
        _assign_run_identity(changed_environment["runs"][0])
        changed_environment.pop("manifest_hash")
        changed_environment["manifest_hash"] = object_hash(changed_environment)
        with self.assertRaisesRegex(ProtocolValidationError, "noncanonical V77"):
            validate_manifest(changed_environment)

        missing_baseline = copy.deepcopy(self.overlay)
        missing_baseline[FORMAL_E2_NSESCHE_OVERLAY_MARKER]["frozen_baseline_runs"].pop()
        missing_baseline.pop("manifest_hash")
        missing_baseline["manifest_hash"] = object_hash(missing_baseline)
        with self.assertRaisesRegex(ProtocolValidationError, "wrong count"):
            validate_manifest(missing_baseline)

        broken_command = copy.deepcopy(self.overlay)
        broken_command["execution"]["command_template"] = broken_command["execution"][
            "command_template"
        ][:-2]
        broken_command.pop("manifest_hash")
        broken_command["manifest_hash"] = object_hash(broken_command)
        with self.assertRaisesRegex(ProtocolValidationError, "seven-argument"):
            validate_manifest(broken_command)


if __name__ == "__main__":
    unittest.main()
