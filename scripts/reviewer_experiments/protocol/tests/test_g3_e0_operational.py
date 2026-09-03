from __future__ import annotations

import copy
import tempfile
import unittest
from itertools import product
from pathlib import Path
from types import SimpleNamespace

from scripts.reviewer_experiments.protocol.g3_e0_operational import (
    G3_E0_OPERATIONAL_BASELINES,
    G3_E0_OPERATIONAL_CANDIDATES,
    G3_E0_OPERATIONAL_LOADS,
    G3_E0_OPERATIONAL_SEEDS,
    G3_E0_OPERATIONAL_TOPOLOGIES,
    G3_E0_ELIGIBILITY,
    G3_E0_ORDERS,
    G3_E0_SCHEMA,
    G3_E0_SEMANTICS,
    G3_E0_TIE_ORDER,
    _choose_candidate,
    _evaluate_baseline_gate,
    _evaluate_timing_gate,
    _validate_runtime_stream,
    build_g3_e0_operational_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
)


class G3E0OperationalProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.binary = self.root / "serverless_sim.exe"
        self.binary.write_bytes(b"g3-e0-operational-test-binary")

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_g3_e0_operational_manifest(self.binary, "c" * 40)

    def test_manifest_is_exact_fresh_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        marker = manifest["g3_e0_operational_development"]
        self.assertEqual(len(manifest["runs"]), 135)
        self.assertEqual(len({run["cell_id"] for run in manifest["runs"]}), 27)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 90)
        self.assertEqual(marker["workload_tape_count"], 30)
        self.assertEqual(marker["candidate_run_count"], 90)
        self.assertEqual(marker["baseline_run_count"], 45)
        self.assertEqual(
            manifest["fixed_seed_bank"]["all_seeds"],
            list(G3_E0_OPERATIONAL_SEEDS),
        )
        candidates = [run for run in manifest["runs"] if run["method"] == "sche_nash"]
        baselines = [run for run in manifest["runs"] if run["method"] != "sche_nash"]
        self.assertEqual(
            {
                (
                    run["metadata"]["m1_operational_candidate"],
                    run["workload"]["request_freq"],
                    run["cluster"]["topology"],
                    run["seed"],
                )
                for run in candidates
            },
            set(
                product(
                    G3_E0_OPERATIONAL_CANDIDATES,
                    G3_E0_OPERATIONAL_LOADS,
                    G3_E0_OPERATIONAL_TOPOLOGIES,
                    G3_E0_OPERATIONAL_SEEDS,
                )
            ),
        )
        self.assertEqual(
            {(run["method"], run["seed"]) for run in baselines},
            set(product(G3_E0_OPERATIONAL_BASELINES, G3_E0_OPERATIONAL_SEEDS)),
        )

    def test_candidate_identity_and_tampering_fail_closed(self) -> None:
        manifest = self._manifest()
        runs = [
            run
            for run in manifest["runs"]
            if run["method"] == "sche_nash"
            and run["seed"] == "D71"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"]["topology"] == "homogeneous"
        ]
        self.assertEqual(len({run["run_id"] for run in runs}), 3)
        self.assertEqual(len({run["reference_dependency"]["path"] for run in runs}), 3)
        bad = copy.deepcopy(manifest)
        target = next(run for run in bad["runs"] if run["method"] == "sche_nash")
        target["environment"]["NASH_ORDER_COUNTERFACTUAL"] = "1"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["fixed_seed_bank"]["selected_seeds"] = ["D71"]
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

        bad = copy.deepcopy(manifest)
        bad["g3_e0_operational_development"]["admission_gate"][
            "old_pdf_alignment_is_selection_criterion"
        ] = True
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(bad, check_hash=False)

    @staticmethod
    def _aggregates() -> list[dict]:
        rows = []
        for candidate, load, topology in product(
            G3_E0_OPERATIONAL_CANDIDATES,
            G3_E0_OPERATIONAL_LOADS,
            G3_E0_OPERATIONAL_TOPOLOGIES,
        ):
            value = {
                "ready_order": 1.0,
                "ready_pne_envelope_first": 1.1,
                "ready_pne_envelope_each": 1.05,
            }[candidate]
            rows.append(
                {
                    "candidate": candidate,
                    "load": load,
                    "topology": topology,
                    "mean_throughput_requests_per_ms": value,
                    "mean_qpr": value,
                    "aggregate_active_window_solve_us": {
                        "ready_order": 100,
                        "ready_pne_envelope_first": 450,
                        "ready_pne_envelope_each": 800,
                    }[candidate],
                }
            )
        return rows

    def test_maximin_and_all_admission_gates_are_frozen(self) -> None:
        aggregates = self._aggregates()
        selected, scores = _choose_candidate(aggregates)
        self.assertEqual(selected, "ready_pne_envelope_first")
        self.assertTrue(scores[0]["all_twelve_ratios_strictly_above_one"])
        baselines = [
            {
                "method": method,
                "mean_throughput_requests_per_ms": 1.0,
                "mean_qpr": 1.0,
            }
            for method in G3_E0_OPERATIONAL_BASELINES
        ]
        baseline_passed, _ = _evaluate_baseline_gate(selected, aggregates, baselines)
        timing_passed, timing_rows = _evaluate_timing_gate(selected, aggregates)
        self.assertTrue(baseline_passed)
        self.assertTrue(timing_passed)
        self.assertTrue(all(row["ratio"] == 4.5 for row in timing_rows))
        for row in aggregates:
            if row["candidate"] == selected and row["load"] == "high":
                row["aggregate_active_window_solve_us"] = 901
        timing_passed, timing_rows = _evaluate_timing_gate(selected, aggregates)
        self.assertFalse(timing_passed)
        self.assertTrue(any(not row["passed"] for row in timing_rows))

    def test_simplicity_breaks_exact_tie(self) -> None:
        aggregates = self._aggregates()
        for row in aggregates:
            row["mean_throughput_requests_per_ms"] = 1.0
            row["mean_qpr"] = 1.0
        selected, _ = _choose_candidate(aggregates)
        self.assertEqual(selected, "ready_order")

    @staticmethod
    def _run_config(candidate: str, r0: float) -> dict:
        operational = candidate != "ready_order"
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 5 if operational else 4,
            "operational_refinement": candidate,
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
            "r0": r0,
            "player_order": (
                "preregistered_O0_O4_order_set"
                if operational
                else "arrival_frame_req_id_dag_topological_rank_fn_id"
            ),
            "operational_equilibrium_selection": {
                "schema": G3_E0_SCHEMA if operational else None,
                "semantics": G3_E0_SEMANTICS[candidate],
                "orders": list(G3_E0_ORDERS) if operational else None,
                "eligibility": G3_E0_ELIGIBILITY if operational else None,
                "ranking": G3_E0_TIE_ORDER if operational else None,
                "welfare_tolerance": (
                    "EPSILON*max(1,abs(O0_welfare))" if operational else None
                ),
                "dispatch_feedback": operational,
            },
            "decision_neutral_diagnostics": {"order_counterfactual_enabled": False},
        }

    @staticmethod
    def _selection_round(outer_round: int, assignment_hash: int) -> dict:
        return {
            "outer_round": outer_round,
            "evaluated_orders": 5,
            "eligible_outcomes": 3,
            "selected_order": "service_scarcity_first",
            "selected_assignment_hash": assignment_hash,
            "selected_non_o0": True,
            "fallback_to_o0": False,
            "welfare_tolerance": 0.0001,
            "selected_complete": True,
            "selected_stable": True,
            "selected_strict_pne": {"certified": True},
            "selected_welfare": 20.0,
            "selected_startup_burden_sum": 10.0,
            "selected_projected_finish_sum": 30.0,
            "evaluation_us": 25,
        }

    def _runtime_fixture(self, candidate: str) -> tuple[dict, SimpleNamespace]:
        manifest = self._manifest()
        run = next(
            item
            for item in manifest["runs"]
            if item["method"] == "sche_nash"
            and item["metadata"]["m1_operational_candidate"] == candidate
            and item["seed"] == "D71"
            and item["workload"]["request_freq"] == "low"
            and item["cluster"]["topology"] == "homogeneous"
        )
        r0 = float(run["simulator_experiment"]["nash"]["price_feedback_rate"])
        hashes = [101, 202]
        selection_rounds = (
            []
            if candidate == "ready_order"
            else [self._selection_round(1, hashes[0])]
            if candidate == "ready_pne_envelope_first"
            else [
                self._selection_round(1, hashes[0]),
                self._selection_round(2, hashes[1]),
            ]
        )
        selection = None
        if candidate != "ready_order":
            selection = {
                "schema": G3_E0_SCHEMA,
                "decision_feedback": True,
                "rounds": selection_rounds,
                "evaluated_orders": len(selection_rounds) * 5,
                "eligible_outcomes": len(selection_rounds) * 3,
                "selected_non_o0_rounds": len(selection_rounds),
                "fallback_rounds": 0,
                "selected_path_inner_rounds": 4,
                "evaluated_total_inner_rounds": len(selection_rounds) * 10,
                "evaluated_total_assignment_moves": len(selection_rounds) * 4,
                "evaluated_total_candidate_evaluations": len(selection_rounds) * 50,
                "evaluated_total_initialization_evaluations": len(selection_rounds)
                * 20,
            }
        event = {
            "kind": "window",
            "decision": {"assigned_players": 2},
            "solver": {
                "outer_rounds": 2,
                "inner_rounds": 4,
                "inner_limit_hit": False,
                "outer_limit_hit": False,
                "outer_feedback_trace": [
                    {"assignment_hash": hashes[0]},
                    {"assignment_hash": hashes[1]},
                ],
            },
            "overhead": {
                "solve_us": 200,
                "operational_envelope_us": len(selection_rounds) * 25,
                "scheduler_wall_us": 250,
                "scheduler_thread_cpu_us": 180,
            },
            "operational_equilibrium_selection": selection,
            "order_counterfactual": None,
        }
        artifacts = SimpleNamespace(
            nse_events=[self._run_config(candidate, r0), event],
            process_observation={"peak_process_tree_rss_bytes": 1024},
        )
        return run, artifacts

    def test_runtime_stream_accepts_exact_c0_c1_c2_contracts(self) -> None:
        for candidate, expected_rounds in (
            ("ready_order", 0),
            ("ready_pne_envelope_first", 1),
            ("ready_pne_envelope_each", 2),
        ):
            with self.subTest(candidate=candidate):
                run, artifacts = self._runtime_fixture(candidate)
                result = _validate_runtime_stream(run, artifacts)
                self.assertEqual(result["selection_rounds"], expected_rounds)
                self.assertEqual(result["aggregate_active_window_solve_us"], 200)

    def test_runtime_stream_rejects_hash_timing_and_schema_drift(self) -> None:
        run, artifacts = self._runtime_fixture("ready_pne_envelope_each")
        bad = copy.deepcopy(artifacts)
        bad.nse_events[1]["solver"]["outer_feedback_trace"][1]["assignment_hash"] = 999
        with self.assertRaises(ProtocolValidationError):
            _validate_runtime_stream(run, bad)

        bad = copy.deepcopy(artifacts)
        bad.nse_events[1]["overhead"]["operational_envelope_us"] = 49
        with self.assertRaises(ProtocolValidationError):
            _validate_runtime_stream(run, bad)

        bad = copy.deepcopy(artifacts)
        bad.nse_events[0]["operational_refinement_schema_version"] = 4
        with self.assertRaises(ProtocolValidationError):
            _validate_runtime_stream(run, bad)

    def test_runtime_stream_uses_emitted_counterfactual_field(self) -> None:
        run, artifacts = self._runtime_fixture("ready_pne_envelope_each")
        artifacts.nse_events[0]["decision_neutral_diagnostics"][
            "order_counterfactual_enabled"
        ] = True
        artifacts.nse_events[0]["observation"] = {"order_counterfactual_enabled": False}
        with self.assertRaises(ProtocolValidationError):
            _validate_runtime_stream(run, artifacts)


if __name__ == "__main__":
    unittest.main()
