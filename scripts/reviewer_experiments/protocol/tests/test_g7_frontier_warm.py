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
from scripts.reviewer_experiments.protocol.g7_frontier_warm import (
    G7_CANDIDATE,
    G7_INITIALIZATION,
    G7_PLAYER_COLLECTION,
    _activation_metrics,
    _candidate_runtime,
    _evaluate_gate,
    build_g7_frontier_warm_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    G7_FRONTIER_WARM_SEEDS,
    ProtocolValidationError,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


class G7FrontierWarmProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.binary = self.root / "serverless_sim.exe"
        self.binary.write_bytes(b"g7-frontier-warm-test-binary")
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
        import json

        from scripts.reviewer_experiments.protocol import g6_lookahead

        source = json.loads(self.source_path.read_text(encoding="utf-8"))
        selection = json.loads(self.selection_path.read_text(encoding="utf-8"))
        with mock.patch.multiple(
            g6_lookahead,
            EXPECTED_G3_READY_MANIFEST_HASH=source["manifest_hash"],
            EXPECTED_G3_READY_FILE_SHA256=file_hash(self.source_path),
            EXPECTED_G3_SELECTION_FILE_SHA256=file_hash(self.selection_path),
            EXPECTED_G3_SELECTION_DOCUMENT_SHA256=selection["document_sha256"],
        ):
            return build_g7_frontier_warm_manifest(
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
            {run["seed"] for run in manifest["runs"]},
            set(G7_FRONTIER_WARM_SEEDS),
        )
        self.assertEqual(len({run["cell_id"] for run in manifest["runs"]}), 1)
        self.assertTrue(
            all(
                run["metadata"]["m1_operational_candidate"] == G7_CANDIDATE
                and run["simulator_experiment"]["nash"]["operational_refinement"]
                == G7_CANDIDATE
                and run["metadata"]["player_collection"] == G7_PLAYER_COLLECTION
                and run["metadata"]["initialization_semantics"] == G7_INITIALIZATION
                for run in manifest["runs"]
            )
        )
        source = manifest["g7_frontier_warm_development"]["source_g3_product"]
        self.assertEqual(source["reused_control_run_count"], 50)
        self.assertEqual(len(source["run_bindings"]), 50)

    def test_manifest_gate_seed_and_candidate_tampering_fail_closed(self) -> None:
        manifest = self._manifest()
        bad = copy.deepcopy(manifest)
        bad["g7_frontier_warm_development"]["activation_gate"][
            "per_seed_frontier_hop_violation_count_at_most"
        ] = 1
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["fixed_seed_bank"]["selected_seeds"] = ["D71"]
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["runs"][0]["environment"][
            "NASH_OPERATIONAL_REFINEMENT"
        ] = "lookahead_preall_sched"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    @staticmethod
    def _run_config() -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 7,
            "operational_refinement": G7_CANDIDATE,
            "player_collection": G7_PLAYER_COLLECTION,
            "player_order": "arrival_frame_req_id_dag_topological_rank_fn_id",
            "initialization_semantics": G7_INITIALIZATION,
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

    def test_runtime_contract_and_warm_accounting_are_fail_closed(self) -> None:
        config = self._run_config()
        self.assertEqual(validate_runtime_contract_config(config, expected_r0=0.1), [])
        bad_config = copy.deepcopy(config)
        bad_config[
            "initialization_semantics"
        ] = "sequential_existing_candidate_selection"
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
                "initialization_refined_choices": 1,
                "initialization_lower_utility_choices": 1,
                "initialization_running_warm_choices": 1,
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
        self.assertEqual(result["initialization_running_warm_choices"], 1)
        self.assertEqual(result["offline_reference_hit_windows"], 1)
        self.assertEqual(result["unreferenced_active_window_count"], 0)

        not_requested = copy.deepcopy(window)
        not_requested["frame"] = 11
        not_requested["social"] = {
            "reference_source": "not_requested",
            "reference_state_key": None,
            "reference": None,
            "reference_cache_hit": False,
            "feedback_eligible": False,
        }
        reported = _candidate_runtime(
            run, SimpleNamespace(nse_events=[config, window, not_requested])
        )
        self.assertEqual(reported["active_window_count"], 2)
        self.assertEqual(reported["offline_reference_hit_windows"], 1)
        self.assertEqual(reported["unreferenced_active_window_count"], 1)

        malformed = copy.deepcopy(not_requested)
        malformed["social"]["reference_state_key"] = 1
        with self.assertRaises(ProtocolValidationError):
            _candidate_runtime(
                run, SimpleNamespace(nse_events=[config, window, malformed])
            )

        malformed = copy.deepcopy(not_requested)
        malformed["social"]["reference_source"] = "offline_table_missing"
        with self.assertRaises(ProtocolValidationError):
            _candidate_runtime(
                run, SimpleNamespace(nse_events=[config, window, malformed])
            )

        bad = copy.deepcopy(artifacts)
        bad.nse_events[1]["decision"]["commands_sent"] = 1
        with self.assertRaises(ProtocolValidationError):
            _candidate_runtime(run, bad)

    @staticmethod
    def _activation_artifacts() -> SimpleNamespace:
        topology = [
            {"function_id": 1, "parents": []},
            {"function_id": 2, "parents": [1]},
            {"function_id": 3, "parents": [2]},
            {"function_id": 4, "parents": [3]},
        ]
        functions = [
            {
                "function_id": 1,
                "ready_schedule_frame": 0,
                "scheduled_frame": 0,
                "cold_start_done_frame": 3,
                "function_done_frame": 5,
            },
            {
                "function_id": 2,
                "ready_schedule_frame": 5,
                "scheduled_frame": 5,
                "cold_start_done_frame": 8,
                "function_done_frame": 10,
            },
            {
                "function_id": 3,
                "ready_schedule_frame": 10,
                "scheduled_frame": 5,
                "cold_start_done_frame": 8,
                "function_done_frame": 15,
            },
            {
                "function_id": 4,
                "ready_schedule_frame": 15,
                "scheduled_frame": 10,
                "cold_start_done_frame": 12,
                "function_done_frame": 20,
            },
        ]
        return SimpleNamespace(
            environment={"functions": topology},
            summary={"fixed_observation_window": {"completed": 1}},
            requests=[{"request_id": "r1", "functions": functions}],
        )

    def test_frontier_reconstruction_accepts_one_hop_and_rejects_two(self) -> None:
        artifacts = self._activation_artifacts()
        metrics = _activation_metrics(artifacts)
        self.assertEqual(metrics["pre_ready_bound_count"], 2)
        self.assertEqual(metrics["maximum_executable_frontier_hops_ahead"], 1)
        self.assertEqual(metrics["frontier_hop_violation_count"], 0)
        self.assertGreater(metrics["startup_overlap_ms_sum"], 0.0)

        artifacts.requests[0]["functions"][3]["scheduled_frame"] = 5
        metrics = _activation_metrics(artifacts)
        self.assertEqual(metrics["maximum_executable_frontier_hops_ahead"], 2)
        self.assertEqual(metrics["frontier_hop_violation_count"], 1)

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
                "active_window_count": 10,
                "offline_reference_hit_windows": 10,
                "unreferenced_active_window_count": 0,
                "pre_ready_bound_count": 2,
                "pre_ready_bound_share": 0.20,
                "startup_overlap_ms_sum": 20.0,
                "mean_startup_overlap_ms": 4.0,
                "initialization_refined_choices": 2,
                "initialization_running_warm_choices": 2,
                "maximum_executable_frontier_hops_ahead": 1,
                "frontier_hop_violation_count": 0,
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

    def test_development_gate_requires_warm_and_bounded_frontier_activation(
        self,
    ) -> None:
        candidates = [
            self._row(seed, "sche_nash", candidate=True)
            for seed in G7_FRONTIER_WARM_SEEDS
        ]
        controls = [self._row(seed, "sche_nash") for seed in G7_FRONTIER_WARM_SEEDS]
        baselines = [
            self._row(seed, method)
            for method in G3_E0_OPERATIONAL_BASELINES
            for seed in G7_FRONTIER_WARM_SEEDS
        ]
        result = _evaluate_gate(candidates, controls, baselines)
        self.assertTrue(result["candidate_development_qualified"])
        self.assertEqual(len(result["paired_rows"]), 5)
        self.assertEqual(len(result["activation_rows"]), 5)
        self.assertEqual(len(result["reference_coverage_rows"]), 5)
        self.assertTrue(result["conditions"]["offline_reference_all_active_windows"])

        failed = copy.deepcopy(candidates)
        failed[0]["offline_reference_hit_windows"] = 9
        failed[0]["unreferenced_active_window_count"] = 1
        result = _evaluate_gate(failed, controls, baselines)
        self.assertFalse(result["candidate_development_qualified"])
        self.assertFalse(result["conditions"]["offline_reference_all_active_windows"])
        self.assertFalse(result["reference_coverage_rows"][0]["passed"])

        failed = copy.deepcopy(candidates)
        failed[0]["initialization_running_warm_choices"] = 0
        result = _evaluate_gate(failed, controls, baselines)
        self.assertFalse(result["candidate_development_qualified"])
        self.assertFalse(result["conditions"]["activation_all_seeds"])

        failed = copy.deepcopy(candidates)
        failed[0]["frontier_hop_violation_count"] = 1
        result = _evaluate_gate(failed, controls, baselines)
        self.assertFalse(result["candidate_development_qualified"])
        self.assertFalse(result["conditions"]["activation_all_seeds"])


if __name__ == "__main__":
    unittest.main()
