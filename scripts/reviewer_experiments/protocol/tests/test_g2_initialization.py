from __future__ import annotations

import copy
import tempfile
import unittest
from itertools import product
from pathlib import Path

from scripts.reviewer_experiments.analysis.feedback_trace import (
    validate_runtime_contract_config,
)
from scripts.reviewer_experiments.protocol.g2_initialization import (
    G2_INITIALIZATION_BASELINES,
    G2_INITIALIZATION_CANDIDATES,
    G2_INITIALIZATION_LOADS,
    G2_INITIALIZATION_SEEDS,
    G2_INITIALIZATION_SEMANTICS,
    G2_INITIALIZATION_TOPOLOGIES,
    _choose_g2_candidate,
    _evaluate_baseline_gate,
    build_g2_initialization_manifest,
)
from scripts.reviewer_experiments.protocol.schema import (
    ProtocolValidationError,
    validate_manifest,
)


class G2InitializationProtocolTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.binary = self.root / "serverless_sim.exe"
        self.binary.write_bytes(b"g2-strict-initialization-test-binary")
        self.source_commit = "b" * 40

    def tearDown(self) -> None:
        self.temporary.cleanup()

    def _manifest(self) -> dict:
        return build_g2_initialization_manifest(self.binary, self.source_commit)

    @staticmethod
    def _runtime_event(candidate: str) -> dict:
        return {
            "v": 2,
            "kind": "run_config",
            "scheduler": "sche_nash",
            "g0_semantics_contract_schema": "eq14_eq16_eq19_semantics_v1",
            "operational_refinement_schema_version": 4,
            "operational_refinement": candidate,
            "initialization_semantics": G2_INITIALIZATION_SEMANTICS[candidate],
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
            "r0": 0.6,
        }

    def test_manifest_is_exact_135_run_fresh_product(self) -> None:
        manifest = self._manifest()
        validate_manifest(manifest)
        marker = manifest["g2_strict_initialization_development"]
        self.assertEqual(len(manifest["runs"]), 135)
        self.assertEqual(len({run["cell_id"] for run in manifest["runs"]}), 27)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 90)
        self.assertEqual(marker["candidate_run_count"], 90)
        self.assertEqual(marker["baseline_run_count"], 45)
        self.assertEqual(marker["workload_tape_count"], 30)
        self.assertFalse(manifest["formal_results_eligible"])
        self.assertEqual(
            manifest["fixed_seed_bank"]["all_seeds"], list(G2_INITIALIZATION_SEEDS)
        )

        candidate_runs = [
            run for run in manifest["runs"] if run["method"] == "sche_nash"
        ]
        baseline_runs = [
            run for run in manifest["runs"] if run["method"] != "sche_nash"
        ]
        self.assertEqual(len(candidate_runs), 90)
        self.assertEqual(len(baseline_runs), 45)
        self.assertEqual(
            {
                (
                    run["metadata"]["m1_operational_candidate"],
                    run["workload"]["request_freq"],
                    run["cluster"]["topology"],
                    run["seed"],
                )
                for run in candidate_runs
            },
            set(
                product(
                    G2_INITIALIZATION_CANDIDATES,
                    G2_INITIALIZATION_LOADS,
                    G2_INITIALIZATION_TOPOLOGIES,
                    G2_INITIALIZATION_SEEDS,
                )
            ),
        )
        self.assertEqual(
            {
                (
                    run["method"],
                    run["workload"]["request_freq"],
                    run["cluster"]["topology"],
                    run["seed"],
                )
                for run in baseline_runs
            },
            set(
                product(
                    G2_INITIALIZATION_BASELINES,
                    ("low",),
                    ("homogeneous",),
                    G2_INITIALIZATION_SEEDS,
                )
            ),
        )
        self.assertEqual(
            len(
                {
                    (
                        run["seed"],
                        run["workload"]["request_freq"],
                        run["cluster"]["topology"],
                    )
                    for run in manifest["runs"]
                }
            ),
            30,
        )

    def test_candidate_changes_reference_and_run_identity(self) -> None:
        manifest = self._manifest()
        runs = [
            run
            for run in manifest["runs"]
            if run["method"] == "sche_nash"
            and run["seed"] == "D66"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"]["topology"] == "homogeneous"
        ]
        self.assertEqual(len(runs), 3)
        self.assertEqual(len({run["run_id"] for run in runs}), 3)
        self.assertEqual(len({run["reference_dependency"]["path"] for run in runs}), 3)

    def test_candidate_or_baseline_product_tampering_fails_closed(self) -> None:
        manifest = self._manifest()
        candidate = next(
            run for run in manifest["runs"] if run["method"] == "sche_nash"
        )
        candidate["metadata"]["m1_operational_candidate"] = "ready_finish_tie"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(manifest, check_hash=False)

        manifest = self._manifest()
        baseline = next(run for run in manifest["runs"] if run["method"] != "sche_nash")
        baseline["cluster"]["topology"] = "heterogeneous"
        with self.assertRaises(ProtocolValidationError):
            validate_manifest(manifest, check_hash=False)

    def test_global_maximin_then_baseline_gate_are_frozen(self) -> None:
        aggregates = []
        for candidate, load, topology in product(
            G2_INITIALIZATION_CANDIDATES,
            G2_INITIALIZATION_LOADS,
            G2_INITIALIZATION_TOPOLOGIES,
        ):
            value = {
                "ready_order": 1.0,
                "ready_warm_init": 1.1,
                "ready_finish_init": 1.05,
            }[candidate]
            aggregates.append(
                {
                    "candidate": candidate,
                    "load": load,
                    "topology": topology,
                    "mean_throughput_requests_per_ms": value,
                    "mean_qpr": value,
                }
            )
        selected, scores = _choose_g2_candidate(aggregates)
        self.assertEqual(selected, "ready_warm_init")
        self.assertEqual(scores[0]["candidate"], selected)

        baselines = [
            {
                "method": method,
                "mean_throughput_requests_per_ms": 1.0,
                "mean_qpr": 1.0,
            }
            for method in G2_INITIALIZATION_BASELINES
        ]
        passed, rows = _evaluate_baseline_gate(selected, aggregates, baselines)
        self.assertTrue(passed)
        self.assertTrue(all(row["passed"] for row in rows))
        baselines[-1]["mean_qpr"] = 1.2
        passed, rows = _evaluate_baseline_gate(selected, aggregates, baselines)
        self.assertFalse(passed)
        self.assertFalse(rows[-1]["passed"])

    def test_simplicity_breaks_an_exact_global_tie(self) -> None:
        aggregates = [
            {
                "candidate": candidate,
                "load": load,
                "topology": topology,
                "mean_throughput_requests_per_ms": 1.0,
                "mean_qpr": 1.0,
            }
            for candidate, load, topology in product(
                G2_INITIALIZATION_CANDIDATES,
                G2_INITIALIZATION_LOADS,
                G2_INITIALIZATION_TOPOLOGIES,
            )
        ]
        selected, _ = _choose_g2_candidate(aggregates)
        self.assertEqual(selected, "ready_order")

    def test_runtime_contract_accepts_only_exact_new_semantics(self) -> None:
        for candidate in ("ready_warm_init", "ready_finish_init"):
            with self.subTest(candidate=candidate):
                event = self._runtime_event(candidate)
                self.assertEqual(
                    validate_runtime_contract_config(
                        event, expected_candidate=candidate, expected_r0=0.6
                    ),
                    [],
                )
                wrong = copy.deepcopy(event)
                wrong["initialization_semantics"] = "wrong"
                self.assertIn(
                    "strict initialization candidate has the wrong semantics",
                    validate_runtime_contract_config(
                        wrong, expected_candidate=candidate, expected_r0=0.6
                    ),
                )
                wrong = copy.deepcopy(event)
                wrong["operational_refinement_schema_version"] = 3
                self.assertIn(
                    "strict initialization candidate has the wrong schema version",
                    validate_runtime_contract_config(
                        wrong, expected_candidate=candidate, expected_r0=0.6
                    ),
                )


if __name__ == "__main__":
    unittest.main()
