from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reviewer_experiments.analysis.p5_common_platform import (
    DETERMINISM_HASH_FIELDS,
    DETERMINISM_TARGET,
    DUPLICATE_SCHEMA,
    SELECTION_SCHEMA,
    _validate_selection,
    build_online_selection,
    evaluate_gate,
)
from scripts.reviewer_experiments.protocol.p5_common_platform import P5_LOADS
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_METHODS,
    P5_COMMON_PLATFORM_SEEDS,
    ProtocolValidationError,
)
from scripts.reviewer_experiments.protocol.util import object_hash


def _rows() -> list[dict]:
    rows = []
    for load_index, load in enumerate(P5_LOADS):
        for seed_index, seed in enumerate(P5_COMMON_PLATFORM_SEEDS):
            tape = f"{load_index * 3 + seed_index + 1:064x}"
            arrival = f"{load_index * 3 + seed_index + 101:064x}"
            for method_index, method in enumerate(FORMAL_E1_METHODS):
                rows.append(
                    {
                        "load": load,
                        "seed": seed,
                        "method": method,
                        "qc_valid": True,
                        "identity_pass": True,
                        "runtime_source_commit": "a" * 40,
                        "runtime_binary_sha256": "b" * 64,
                        "workload_tape_sha256": tape,
                        "offline_reference_sha256": (
                            f"{load_index * 30 + seed_index * 10 + method_index + 1:064x}"
                        ),
                        "arrival_event_sequence_sha256": arrival,
                        "arrivals": 2_000 + seed_index,
                        "tape_static_cpu_work": 20_000.0 + seed_index,
                        "cluster_cpu_per_frame": 100.0,
                        "static_path_allowance_frames": 50,
                        "max_drain_frames": 1_000,
                        "hard_end_frame": 2_000,
                        "conservation_pass": True,
                        "fcfs_pass": True,
                        "capacity_pass": True,
                        "timing_pass": True,
                        "metric_identity_pass": True,
                        "fixed_window_completed": 1,
                        "terminal_completion_ratio": 0.95,
                        "reference_integrity_pass": True,
                        "nash_integrity_pass": True,
                        "paper_throughput_requests_per_ms": 1.0 + method_index / 100.0,
                        "qpr": 0.01 + method_index / 1_000.0,
                    }
                )
    return rows


def _traffic() -> list[dict]:
    return [
        {
            "load": load,
            "seed": seed,
            "all_preregistered_tapes_reported": True,
            "measured_request_rate_rps": 2_000.0,
            "arrivals_per_frame_p50": 0.0,
            "arrivals_per_frame_p95": 10.0,
            "arrivals_per_frame_p99": 20.0,
            "arrivals_per_frame_max": 30.0,
            "static_cpu_work_rate_per_second": 20_000.0,
            "rho_ideal": 0.2,
        }
        for load in P5_LOADS
        for seed in P5_COMMON_PLATFORM_SEEDS
    ]


def _duplicate() -> dict:
    semantic_hashes = {
        field: f"{index + 1:064x}"
        for index, field in enumerate(DETERMINISM_HASH_FIELDS)
    }
    hashes = {"qc_valid": True, "run_spec_hash": "a" * 64, **semantic_hashes}
    evidence = {
        "schema_version": DUPLICATE_SCHEMA,
        "target": DETERMINISM_TARGET,
        "predeclared": True,
        "additional_observation": False,
        "canonical": hashes,
        "duplicate": copy.deepcopy(hashes),
    }
    evidence["document_sha256"] = object_hash(evidence)
    return evidence


def _ready_manifest() -> dict:
    runs = []
    ordinal = 0
    for load_index, load in enumerate(P5_LOADS):
        for seed_index, seed in enumerate(P5_COMMON_PLATFORM_SEEDS):
            tape_hash = f"{100 + load_index * 3 + seed_index:064x}"
            for method_index, method in enumerate(FORMAL_E1_METHODS):
                ordinal += 1
                runs.append(
                    {
                        "run_id": f"P5.{load}.{seed}.{method}",
                        "run_spec_hash": f"{ordinal:064x}",
                        "seed": seed,
                        "method": method,
                        "workload": {"request_freq": load},
                        "workload_tape": {"sha256": tape_hash},
                        "reference_dependency": {"sha256": f"{1000 + ordinal:064x}"},
                    }
                )
    return {"manifest_hash": "a" * 64, "runs": runs}


class P5CommonPlatformAnalysisTests(unittest.TestCase):
    def test_result_blind_online_selection_freezes_exact_manifest_order(self) -> None:
        manifest = _ready_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "ready.json"
            manifest_path.write_text("{}\n", encoding="utf-8")
            canonical_root = root / "online" / "canonical"
            with patch(
                "scripts.reviewer_experiments.analysis.p5_common_platform._validate_ready_manifest",
                return_value=manifest,
            ):
                selection = build_online_selection(manifest_path, canonical_root)

            self.assertEqual(selection["schema_version"], SELECTION_SCHEMA)
            self.assertEqual(selection["run_count"], 90)
            self.assertEqual(
                [row["run_id"] for row in selection["runs"]],
                [run["run_id"] for run in manifest["runs"]],
            )
            self.assertEqual(
                [row["ordinal"] for row in selection["runs"]],
                list(range(1, 91)),
            )
            self.assertFalse(selection["online_results_present_at_freeze"])
            self.assertFalse(
                selection["result_conditioned_seed_method_or_run_selection"]
            )
            self.assertTrue(selection["relative_performance_excluded_from_gate"])
            self.assertEqual(selection["analysis_contract"]["gate_condition_count"], 12)
            self.assertFalse(
                any(
                    field in row
                    for row in selection["runs"]
                    for field in ("qpr", "throughput", "rank", "result", "status")
                )
            )
            payload = copy.deepcopy(selection)
            stored = payload.pop("document_sha256")
            self.assertEqual(stored, object_hash(payload))

            selection_path = root / "selection.json"
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            validated = _validate_selection(
                selection_path,
                manifest_path.resolve(),
                canonical_root.resolve(),
                manifest,
            )
            self.assertEqual(validated, selection)

            selection["runs"][0], selection["runs"][1] = (
                selection["runs"][1],
                selection["runs"][0],
            )
            payload = copy.deepcopy(selection)
            payload.pop("document_sha256")
            selection["document_sha256"] = object_hash(payload)
            selection_path.write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaisesRegex(
                ProtocolValidationError, "selection no longer matches inputs"
            ):
                _validate_selection(
                    selection_path,
                    manifest_path.resolve(),
                    canonical_root.resolve(),
                    manifest,
                )

    def test_online_selection_rejects_existing_online_parent(self) -> None:
        manifest = _ready_manifest()
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            manifest_path = root / "ready.json"
            manifest_path.write_text("{}\n", encoding="utf-8")
            canonical_root = root / "online" / "canonical"
            canonical_root.parent.mkdir()
            with patch(
                "scripts.reviewer_experiments.analysis.p5_common_platform._validate_ready_manifest",
                return_value=manifest,
            ), self.assertRaisesRegex(
                ProtocolValidationError, "result parent must not exist"
            ):
                build_online_selection(manifest_path, canonical_root)

    def test_all_twelve_method_neutral_conditions_pass(self) -> None:
        result = evaluate_gate(_rows(), _traffic(), _duplicate())
        self.assertTrue(result["qualified"])
        self.assertEqual(len(result["conditions"]), 12)
        self.assertTrue(result["formal_preregistration_authorized"])
        self.assertFalse(result["formal_sampling_authorized"])
        self.assertTrue(result["relative_outcomes"]["sealed_after_conditions_1_to_11"])
        self.assertTrue(result["relative_outcomes"]["excluded_from_pass_fail"])

    def test_unfavorable_nsesche_metrics_cannot_fail_or_trigger_retry(self) -> None:
        rows = _rows()
        for row in rows:
            if row["method"] == "sche_nash":
                row["paper_throughput_requests_per_ms"] = 0.0001
                row["qpr"] = 0.000001
        result = evaluate_gate(rows, _traffic(), _duplicate())
        self.assertTrue(result["qualified"])
        nash = next(
            row
            for load in result["relative_outcomes"]["loads"]
            if load["load"] == "low"
            for row in load["methods"]
            if row["method"] == "sche_nash"
        )
        self.assertEqual(nash["throughput_mean_rank"], 10)
        self.assertEqual(nash["qpr_mean_rank"], 10)

    def test_one_protocol_violation_fails_conjunctive_gate(self) -> None:
        rows = _rows()
        rows[37]["fcfs_pass"] = False
        result = evaluate_gate(rows, _traffic(), _duplicate())
        self.assertFalse(result["conditions"]["condition_4_fcfs"])
        self.assertFalse(result["qualified"])
        self.assertFalse(result["formal_preregistration_authorized"])

    def test_incomplete_population_and_duplicate_determinism_fail_closed(self) -> None:
        result = evaluate_gate(_rows()[:-1], _traffic(), _duplicate())
        self.assertFalse(result["conditions"]["condition_1_population_and_identity"])
        duplicate = _duplicate()
        duplicate["duplicate"][DETERMINISM_HASH_FIELDS[-1]] = "f" * 64
        payload = copy.deepcopy(duplicate)
        payload.pop("document_sha256")
        duplicate["document_sha256"] = object_hash(payload)
        result = evaluate_gate(_rows(), _traffic(), duplicate)
        self.assertFalse(result["conditions"]["condition_11_determinism_duplicate"])
        self.assertFalse(result["qualified"])


if __name__ == "__main__":
    unittest.main()
