from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.g1_corrected_runtime import (
    G1_SELECTION_SCHEMA,
    G1_STRICT_CANDIDATES,
    G1_TECHNICAL_GATE_SCHEMA,
    _choose_g1_candidate,
    build_g1_corrected_runtime_screen_manifest,
    build_g1_formal_qualification_manifest,
)
from scripts.reviewer_experiments.protocol.m1_completion_guard import _runtime_receipt
from scripts.reviewer_experiments.protocol.schema import (
    G1_CORRECTED_SCREEN_SEEDS,
    G1_FORMAL_QUALIFICATION_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import object_hash, write_json_atomic


class G1CorrectedRuntimeProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.binary = self.root / "serverless_sim.exe"
        self.binary.write_bytes(b"g1-corrected-runtime-test-binary")
        self.commit = "c" * 40
        self.runtime = _runtime_receipt(self.binary, self.commit)
        self.gate_path = self.root / "g1.technical-gate.json"
        gate = {
            "schema_version": G1_TECHNICAL_GATE_SCHEMA,
            "status": "technical_gate_passed",
            "technical_only": True,
            "selection_eligible": False,
            "formal_results_eligible": False,
            "technical_manifest": {"manifest_hash": "a" * 64},
            "runtime_binary": self.runtime,
            "nash_runtime_contract": {"stream_contract_ready": True},
        }
        gate["document_sha256"] = object_hash(gate)
        write_json_atomic(self.gate_path, gate)
        self.selection_path = self.root / "g1.selection.json"
        selection = {
            "schema_version": G1_SELECTION_SCHEMA,
            "formal_results_eligible": False,
            "selected_candidate": "ready_order",
            "qualification_authorized_by_screen": True,
            "runtime_binary": self.runtime,
            "screen_manifest": {"manifest_hash": "b" * 64},
        }
        selection["document_sha256"] = object_hash(selection)
        write_json_atomic(self.selection_path, selection)
        self.model_path = self.root / "faasrank.frozen.json"
        model = {
            "schema_version": "NSE_FAASRANK_FROZEN_LINEAR_V1",
            "model_family": "frozen_linear_score_rank_select",
            "state": "frozen",
            "created_at": "2026-09-03T00:00:00+00:00",
            "training_tape": {"sha256": "d" * 64},
            "parameters": {
                "cpu_headroom": 1.0,
                "memory_headroom": 1.0,
                "network_locality": 1.0,
                "warm_affinity": 1.0,
                "load_balance": 1.0,
                "diversity_penalty": 1.0,
                "epsilon": 0.0,
            },
            "provenance": {
                "calibration": {"plan_sha256": "e" * 64},
                "selection": {"candidate_sha256": "f" * 64},
            },
        }
        write_json_atomic(self.model_path, model)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict[str, object]:
        return build_g1_corrected_runtime_screen_manifest(
            self.binary, self.commit, self.gate_path
        )

    def test_screen_is_exact_strict_three_by_six_by_five_product(self) -> None:
        manifest = self._manifest()
        self.assertEqual(len(manifest["runs"]), 90)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 90)
        self.assertEqual(
            manifest["fixed_seed_bank"]["selected_seeds"],
            list(G1_CORRECTED_SCREEN_SEEDS),
        )
        self.assertEqual(
            {run["metadata"]["m1_operational_candidate"] for run in manifest["runs"]},
            set(G1_STRICT_CANDIDATES),
        )
        self.assertEqual(
            len({run["workload_tape"]["key"] for run in manifest["runs"]}),
            30,
        )
        self.assertTrue(
            all(
                run["metadata"]["strict_best_response"] is True
                and run["metadata"]["utility_guard_relative_regret"] == 0.0
                for run in manifest["runs"]
            )
        )
        self.assertEqual(
            manifest["execution"]["command_template"][-2:],
            ["--simulator-exe", str(self.binary.resolve())],
        )

    def test_gate_is_bound_by_file_and_document_hash(self) -> None:
        manifest = self._manifest()
        gate = manifest["g1_corrected_runtime_screen"]["technical_gate"]
        self.assertEqual(
            gate["document_sha256"],
            object_hash(
                {
                    key: value
                    for key, value in __import__("json")
                    .loads(self.gate_path.read_text(encoding="utf-8"))
                    .items()
                    if key != "document_sha256"
                }
            ),
        )
        self.assertEqual(gate["technical_manifest_hash"], "a" * 64)

    def test_wrong_runtime_gate_fails_closed(self) -> None:
        changed = __import__("json").loads(self.gate_path.read_text(encoding="utf-8"))
        changed["runtime_binary"]["sha256"] = "d" * 64
        changed["document_sha256"] = object_hash(
            {key: value for key, value in changed.items() if key != "document_sha256"}
        )
        write_json_atomic(self.gate_path, changed)
        with self.assertRaises(ProtocolValidationError):
            self._manifest()

    def test_nonzero_utility_guard_fails_schema(self) -> None:
        manifest = copy.deepcopy(self._manifest())
        run = manifest["runs"][0]
        run["metadata"]["utility_guard_relative_regret"] = 0.05
        run["run_spec_hash"] = object_hash(
            {key: value for key, value in run.items() if key != "run_spec_hash"}
        )
        manifest["manifest_hash"] = object_hash(
            {key: value for key, value in manifest.items() if key != "manifest_hash"}
        )
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(manifest)

    def test_control_relative_global_maximin_is_frozen(self) -> None:
        aggregates = []
        for load in ("low", "middle", "high"):
            for topology in ("homogeneous", "heterogeneous"):
                for candidate, throughput, qpr in (
                    ("ready_order", 1.0, 1.0),
                    ("ready_finish_tie", 1.1, 0.9),
                    ("formula", 1.05, 1.05),
                ):
                    aggregates.append(
                        {
                            "candidate": candidate,
                            "load": load,
                            "topology": topology,
                            "mean_throughput_requests_per_ms": throughput,
                            "mean_qpr": qpr,
                        }
                    )
        selected, scores = _choose_g1_candidate(aggregates)
        self.assertEqual(selected, "formula")
        self.assertEqual(scores[0]["candidate"], "formula")
        self.assertGreater(scores[0]["worst_control_relative_ratio"], 1.0)

    def test_formal_qualification_is_exact_ten_by_six_by_twenty_product(self) -> None:
        manifest = build_g1_formal_qualification_manifest(
            self.selection_path,
            self.binary,
            self.commit,
            self.model_path,
        )
        self.assertEqual(manifest["phase"], "formal")
        self.assertTrue(manifest["formal_results_eligible"])
        self.assertEqual(len(manifest["runs"]), 1200)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 120)
        self.assertEqual(
            manifest["fixed_seed_bank"]["selected_seeds"],
            list(G1_FORMAL_QUALIFICATION_SEEDS),
        )
        self.assertEqual(
            len({run["workload_tape"]["key"] for run in manifest["runs"]}),
            120,
        )
        self.assertEqual(
            {
                experiment_id: summary["reuse_entries"]
                for experiment_id, summary in manifest["matrix_summary"][
                    "by_experiment"
                ].items()
                if experiment_id in {"E2", "E5", "E6", "E7", "E8", "E9"}
            },
            {
                experiment_id: 1
                for experiment_id in ("E2", "E5", "E6", "E7", "E8", "E9")
            },
        )
        nash = [run for run in manifest["runs"] if run["method"] == "sche_nash"]
        self.assertEqual(len(nash), 120)
        self.assertTrue(
            all(
                run["metadata"]["m1_operational_candidate"] == "ready_order"
                and run["metadata"]["strict_best_response"] is True
                and run["simulator_experiment"]["nash"]["operational_refinement"]
                == "ready_order"
                for run in nash
            )
        )
        low = next(run for run in nash if run["workload"]["request_freq"] == "low")
        middle = next(
            run for run in nash if run["workload"]["request_freq"] == "middle"
        )
        self.assertEqual(
            (
                low["simulator_experiment"]["nash"]["price_feedback_rate"],
                low["simulator_experiment"]["nash"]["quality_weight"],
            ),
            (0.6, 0.5),
        )
        self.assertEqual(
            (
                middle["simulator_experiment"]["nash"]["price_feedback_rate"],
                middle["simulator_experiment"]["nash"]["quality_weight"],
            ),
            (0.5, 0.6),
        )
        marker = manifest["g1_formal_qualification"]
        self.assertEqual(marker["online_execution_order"][0]["load"], "low")
        self.assertEqual(marker["faasrank_model"]["training_tape_sha256"], "d" * 64)

    def test_formal_qualification_rejects_a_different_selected_candidate(self) -> None:
        selection = __import__("json").loads(
            self.selection_path.read_text(encoding="utf-8")
        )
        selection["selected_candidate"] = "formula"
        selection["document_sha256"] = object_hash(
            {key: value for key, value in selection.items() if key != "document_sha256"}
        )
        write_json_atomic(self.selection_path, selection)
        with self.assertRaises(ProtocolValidationError):
            build_g1_formal_qualification_manifest(
                self.selection_path,
                self.binary,
                self.commit,
                self.model_path,
            )


if __name__ == "__main__":
    unittest.main()
