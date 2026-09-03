from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)
from scripts.reviewer_experiments.protocol.g3_e0_operational import (
    G3_E0_OPERATIONAL_BASELINES,
    build_g3_e0_operational_manifest,
)
from scripts.reviewer_experiments.protocol.g6_lookahead import (
    G6_CANDIDATE,
    _activation_metrics,
    _candidate_runtime,
    _evaluate_gate,
    build_g6_lookahead_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    G6_LOOKAHEAD_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class G6LookaheadProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.binary = self.root / "serverless_sim.exe"
        self.binary.write_bytes(b"g6-lookahead-test-binary")
        source = build_g3_e0_operational_manifest(self.binary, "c" * 40)
        self.source_path = self.root / "g3.ready.json"
        write_json_atomic(self.source_path, source)
        selection = {
            "schema_version": "TEST_G3_SELECTION",
            "status": "complete_g3_e0_development_gate_failed",
            "run_count": 135,
            "formal_confirmation_authorized": False,
            "development_manifest": {
                "path": str(self.source_path.resolve()),
                "manifest_hash": source["manifest_hash"],
                "file_sha256": file_hash(self.source_path),
            },
            "baseline_low_aggregates": [
                {
                    "method": method,
                    "mean_throughput_requests_per_ms": (
                        1.1514 if method == "sche_Hiku" else 1.0
                    ),
                    "mean_qpr": (
                        0.040391614512590296 if method == "sche_jiagu" else 0.03
                    ),
                }
                for method in G3_E0_OPERATIONAL_BASELINES
            ],
        }
        selection["document_sha256"] = object_hash(selection)
        self.selection_path = self.root / "g3.selection.json"
        write_json_atomic(self.selection_path, selection)

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        from scripts.reviewer_experiments.protocol import g6_lookahead

        source = __import__("json").loads(self.source_path.read_text(encoding="utf-8"))
        selection = __import__("json").loads(
            self.selection_path.read_text(encoding="utf-8")
        )
        with mock.patch.multiple(
            g6_lookahead,
            EXPECTED_G3_READY_MANIFEST_HASH=source["manifest_hash"],
            EXPECTED_G3_READY_FILE_SHA256=file_hash(self.source_path),
            EXPECTED_G3_SELECTION_FILE_SHA256=file_hash(self.selection_path),
            EXPECTED_G3_SELECTION_DOCUMENT_SHA256=selection["document_sha256"],
        ):
            return build_g6_lookahead_manifest(
                self.binary,
                "d" * 40,
                self.source_path,
                self.selection_path,
                self.root / "g3-canonical",
            )

    def test_manifest_is_exact_candidate_only_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        self.assertEqual(len(manifest["runs"]), 5)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 5)
        self.assertEqual(
            {run["seed"] for run in manifest["runs"]}, set(G6_LOOKAHEAD_SEEDS)
        )
        self.assertEqual(len({run["cell_id"] for run in manifest["runs"]}), 1)
        self.assertTrue(
            all(
                run["metadata"]["m1_operational_candidate"] == G6_CANDIDATE
                and run["simulator_experiment"]["nash"]["operational_refinement"]
                == G6_CANDIDATE
                for run in manifest["runs"]
            )
        )
        source = manifest["g6_lookahead_development"]["source_g3_product"]
        self.assertEqual(source["reused_control_run_count"], 50)
        self.assertEqual(len(source["run_bindings"]), 50)

    def test_manifest_gate_seed_and_candidate_tampering_fail_closed(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        bad["g6_lookahead_development"]["performance_gate"][
            "mean_qpr_strictly_above"
        ] = 0.0
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["fixed_seed_bank"]["selected_seeds"] = ["D71"]
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["runs"][0]["environment"]["NASH_OPERATIONAL_REFINEMENT"] = "ready_order"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 6,
            "operational_refinement": G6_CANDIDATE,
            "player_collection": "parents_scheduled",
            "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
            "initialization_semantics": "sequential_existing_candidate_selection",
            "strict_best_response": True,
            "formula_alignment": "paper_Eqs_1_20_strict_argmax",
            "eq15_selection_semantics": (
                "strict_argmax_with_current_node_preferred_on_numerical_ties"
            ),
            "utility_guard_relative_regret": None,
            "outer_feedback_trace_schema": "eq16_eq19_control_path_v1",
            "reference_price_basis": "immutable_window_baseline_prices",
            "feedback_nash_welfare_price_basis": "current_outer_adjusted_prices",
            "empirical_gap_price_basis": "immutable_window_baseline_prices",
            "price_feedback_update_basis": (
                "immutable_window_baseline_prices_not_recursive"
            ),
            "network_beta_source": (
                "active_transfer_remaining_time_by_directed_link_proxy"
            ),
            "network_beta_effective_domain": (
                "finite_beta_ge_1_unclipped_no_global_upper_bound"
            ),
            "network_proxy_is_physical_rtt": False,
            "r0": 0.1,
            "operational_equilibrium_selection": {
                "schema": None,
                "semantics": "single_ready_order_path",
                "orders": None,
                "eligibility": None,
                "ranking": None,
                "welfare_tolerance": None,
                "dispatch_feedback": False,
            },
            "decision_neutral_diagnostics": {"order_counterfactual_enabled": False},
            "reference": {
                "mode": "offline_required",
                "offline_load_ok": True,
                "offline_entries": 7,
            },
        }

    def test_runtime_contract_and_dispatch_accounting_are_fail_closed(self) -> None:
        config = self._run_config()
        self.assertEqual(validate_runtime_contract_config(config, expected_r0=0.1), [])
        bad_config = copy.deepcopy(config)
        bad_config["player_collection"] = "dependency_ready_only"
        self.assertTrue(validate_runtime_contract_config(bad_config, expected_r0=0.1))

        window = {
            "kind": "window",
            "frame": 10,
            "decision": {
                "assigned_players": 2,
                "complete_assignment": True,
                "commands_prepared": 2,
                "commands_sent": 2,
                "invalid_assignments": 0,
                "dispatch_channel_failed": False,
            },
            "overhead": {"solve_us": 20},
            "social": {
                "reference_source": "offline_table",
                "reference_state_key": 1,
                "reference": 10.0,
            },
            "operational_equilibrium_selection": None,
            "order_counterfactual": None,
        }
        artifacts = SimpleNamespace(nse_events=[config, window])
        run = {"simulator_experiment": {"nash": {"price_feedback_rate": 0.1}}}
        result = _candidate_runtime(run, artifacts)
        self.assertEqual(result["assigned_players"], 2)
        self.assertEqual(result["aggregate_active_window_solve_us"], 20)
        bad = copy.deepcopy(artifacts)
        bad.nse_events[1]["decision"]["commands_sent"] = 1
        with self.assertRaises(ProtocolValidationError):
            _candidate_runtime(run, bad)

    def test_completed_function_activation_is_measured_per_seed(self) -> None:
        artifacts = SimpleNamespace(
            summary={"fixed_observation_window": {"completed": 1}},
            requests=[
                {
                    "request_id": "r1",
                    "functions": [
                        {
                            "function_id": "f1",
                            "ready_schedule_frame": 10,
                            "scheduled_frame": 5,
                            "cold_start_done_frame": 8,
                        },
                        {
                            "function_id": "f2",
                            "ready_schedule_frame": 12,
                            "scheduled_frame": 12,
                            "cold_start_done_frame": None,
                        },
                    ],
                }
            ],
        )
        metrics = _activation_metrics(artifacts)
        self.assertEqual(metrics["completed_function_count"], 2)
        self.assertEqual(metrics["pre_ready_bound_share"], 0.5)
        self.assertEqual(metrics["mean_startup_overlap_ms"], 1.5)

    @staticmethod
    def _row(seed: str, method: str, *, candidate: bool = False) -> dict:
        if candidate:
            return {
                "run_id": f"candidate.{seed}",
                "seed": seed,
                "method": "sche_nash",
                "throughput_requests_per_ms": 1.20,
                "qpr": 0.05,
                "latency_mean_ms": 50.0,
                "cost_per_completed_request": 0.40,
                "completion_ratio": 0.70,
                "aggregate_active_window_solve_us": 150.0,
                "pre_ready_bound_share": 0.20,
                "mean_startup_overlap_ms": 4.0,
            }
        if method == "sche_nash":
            return {
                "run_id": f"control.{seed}",
                "seed": seed,
                "method": method,
                "throughput_requests_per_ms": 1.00,
                "qpr": 0.03,
                "latency_mean_ms": 80.0,
                "cost_per_completed_request": 0.60,
                "completion_ratio": 0.65,
                "aggregate_active_window_solve_us": 100.0,
            }
        return {
            "run_id": f"{method}.{seed}",
            "seed": seed,
            "method": method,
            "throughput_requests_per_ms": 1.10,
            "qpr": 0.04,
            "latency_mean_ms": 60.0,
            "cost_per_completed_request": 0.50,
            "completion_ratio": 0.68,
        }

    def test_development_gate_reports_all_seeds_and_all_conditions(self) -> None:
        candidates = [
            self._row(seed, "sche_nash", candidate=True) for seed in G6_LOOKAHEAD_SEEDS
        ]
        controls = [self._row(seed, "sche_nash") for seed in G6_LOOKAHEAD_SEEDS]
        baselines = [
            self._row(seed, method)
            for method in G3_E0_OPERATIONAL_BASELINES
            for seed in G6_LOOKAHEAD_SEEDS
        ]
        result = _evaluate_gate(candidates, controls, baselines)
        self.assertTrue(result["candidate_development_qualified"])
        self.assertEqual(len(result["paired_rows"]), 5)
        self.assertEqual(
            len(
                result["paired_metric_summaries"]["qpr_difference"][
                    "leave_one_seed_out"
                ]
            ),
            5,
        )
        failed = copy.deepcopy(candidates)
        for row in failed[:2]:
            row["qpr"] = 0.02
        result = _evaluate_gate(failed, controls, baselines)
        self.assertFalse(result["candidate_development_qualified"])
        self.assertFalse(result["conditions"]["paired_qpr_wins_at_least_4"])
        self.assertEqual(len(result["paired_rows"]), 5)


if __name__ == "__main__":
    unittest.main()
