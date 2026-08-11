from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from scripts.reviewer_experiments.protocol.faasrank_model import (
    CALIBRATION_OBJECTIVE,
    CALIBRATION_RESULTS_SCHEMA,
    MODEL_FAMILY,
    MODEL_SCHEMA,
    FaaSRankModelError,
    artifact_sha256,
    candidate_parameter_sha256,
    create_faasrank_calibration_plan,
    create_frozen_faasrank_model,
    freeze_faasrank_from_calibration,
    load_faasrank_calibration_plan,
    load_frozen_faasrank_model,
    rust_faasrank_model_config,
    verify_frozen_faasrank_model,
)
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import file_hash, write_json_atomic


WEIGHTS = {
    "cpu_headroom": 0.25,
    "memory_headroom": 0.20,
    "network_locality": 0.20,
    "warm_affinity": 0.15,
    "load_balance": 0.15,
    "diversity_penalty": -0.05,
}
TRAINING_HASH = "a" * 64
SECOND_WEIGHTS = {**WEIGHTS, "cpu_headroom": 0.35, "load_balance": 0.05}


def _create(path: Path):
    return create_frozen_faasrank_model(
        path,
        training_tape_sha256=TRAINING_HASH,
        weights=WEIGHTS,
        epsilon=0.1,
        calibration_provenance={
            "method": "separate_training_tape_grid_search",
            "protocol": "calibration-v1",
            "seed_count": 10,
        },
        selection_provenance={
            "criterion": "validation_score",
            "tie_break": "lowest_epsilon_then_lexicographic",
        },
        created_at="2026-08-10T00:00:00Z",
    )


class FrozenFaaSRankModelTests(unittest.TestCase):
    def test_create_load_verify_and_map_to_rust(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "faasrank-model.json"
            model = _create(path)
            raw = json.loads(path.read_text(encoding="utf-8"))
            self.assertEqual(raw["schema_version"], MODEL_SCHEMA)
            self.assertEqual(raw["model_family"], MODEL_FAMILY)
            self.assertEqual(raw["state"], "frozen")
            self.assertEqual(raw["training_tape"], {"sha256": TRAINING_HASH})
            self.assertNotIn("model_sha256", raw)
            self.assertNotIn("artifact_sha256", raw)
            self.assertEqual(model.artifact_sha256, artifact_sha256(path))
            self.assertEqual(load_frozen_faasrank_model(path), model)
            self.assertEqual(
                verify_frozen_faasrank_model(
                    path,
                    expected_artifact_sha256=model.artifact_sha256,
                    expected_training_tape_sha256=TRAINING_HASH,
                    test_tape_sha256="b" * 64,
                ),
                model,
            )
            self.assertEqual(
                rust_faasrank_model_config(model),
                {
                    "state": "frozen",
                    "model_sha256": model.artifact_sha256,
                    "training_tape_sha256": TRAINING_HASH,
                    **{key: float(value) for key, value in WEIGHTS.items()},
                    "epsilon": 0.1,
                },
            )

    def test_creation_is_immutable(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            original = _create(path)
            with self.assertRaisesRegex(FaaSRankModelError, "refusing to replace"):
                _create(path)
            self.assertEqual(artifact_sha256(path), original.artifact_sha256)

    def test_training_and_evaluation_tapes_must_be_disjoint(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            _create(path)
            with self.assertRaisesRegex(FaaSRankModelError, "hash-disjoint"):
                verify_frozen_faasrank_model(path, test_tape_sha256=TRAINING_HASH)
            with self.assertRaisesRegex(FaaSRankModelError, "hash-disjoint"):
                verify_frozen_faasrank_model(
                    path,
                    forbidden_test_tape_sha256=["b" * 64, TRAINING_HASH],
                )

    def test_binding_mismatches_are_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "model.json"
            _create(path)
            with self.assertRaisesRegex(FaaSRankModelError, "artifact SHA-256"):
                verify_frozen_faasrank_model(path, expected_artifact_sha256="c" * 64)
            with self.assertRaisesRegex(FaaSRankModelError, "training tape SHA-256"):
                verify_frozen_faasrank_model(
                    path,
                    expected_training_tape_sha256="d" * 64,
                )

    def test_strict_schema_rejects_unknown_missing_and_nested_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            valid_path = root / "valid.json"
            _create(valid_path)
            valid = json.loads(valid_path.read_text(encoding="utf-8"))
            cases = []
            unknown = dict(valid)
            unknown["unexpected"] = True
            cases.append(unknown)
            missing = dict(valid)
            missing.pop("state")
            cases.append(missing)
            nested = json.loads(json.dumps(valid))
            nested["parameters"]["extra_weight"] = 1.0
            cases.append(nested)
            training = json.loads(json.dumps(valid))
            training["training_tape"]["path"] = "not-recorded.jsonl"
            cases.append(training)
            provenance = json.loads(json.dumps(valid))
            provenance["provenance"]["extra"] = {}
            cases.append(provenance)
            for index, document in enumerate(cases):
                path = root / f"bad-{index}.json"
                path.write_text(json.dumps(document), encoding="utf-8")
                with self.subTest(index=index):
                    with self.assertRaises(FaaSRankModelError):
                        load_frozen_faasrank_model(path)

    def test_nonfinite_weights_and_epsilon_outside_unit_interval_are_rejected(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for label, weights, epsilon in (
                ("nan", {**WEIGHTS, "cpu_headroom": float("nan")}, 0.1),
                ("infinity", {**WEIGHTS, "cpu_headroom": float("inf")}, 0.1),
                ("bool", {**WEIGHTS, "cpu_headroom": True}, 0.1),
                ("negative-epsilon", WEIGHTS, -0.01),
                ("large-epsilon", WEIGHTS, 1.01),
            ):
                with self.subTest(label=label):
                    with self.assertRaises(FaaSRankModelError):
                        create_frozen_faasrank_model(
                            root / f"{label}.json",
                            training_tape_sha256=TRAINING_HASH,
                            weights=weights,
                            epsilon=epsilon,
                            calibration_provenance={"method": "held-out calibration"},
                            selection_provenance={"criterion": "validation score"},
                        )

    def test_loader_rejects_duplicate_keys_and_nonstandard_constants(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            duplicate = root / "duplicate.json"
            duplicate.write_text(
                '{"schema_version":"x","schema_version":"y"}', encoding="utf-8"
            )
            with self.assertRaisesRegex(FaaSRankModelError, "duplicate JSON key"):
                load_frozen_faasrank_model(duplicate)
            nonfinite = root / "nonfinite.json"
            nonfinite.write_text('{"value":NaN}', encoding="utf-8")
            with self.assertRaisesRegex(FaaSRankModelError, "non-standard/nonfinite"):
                load_frozen_faasrank_model(nonfinite)

    def test_provenance_is_required_and_must_be_json(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            with self.assertRaisesRegex(FaaSRankModelError, "non-empty"):
                create_frozen_faasrank_model(
                    root / "empty.json",
                    training_tape_sha256=TRAINING_HASH,
                    weights=WEIGHTS,
                    epsilon=0.0,
                    calibration_provenance={},
                    selection_provenance={"criterion": "validation score"},
                )
            with self.assertRaisesRegex(FaaSRankModelError, "non-JSON"):
                create_frozen_faasrank_model(
                    root / "bad-value.json",
                    training_tape_sha256=TRAINING_HASH,
                    weights=WEIGHTS,
                    epsilon=0.0,
                    calibration_provenance={"source": Path("training.jsonl")},
                    selection_provenance={"criterion": "validation score"},
                )

    def test_mapping_revalidates_tampered_dataclass(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            model = _create(Path(temporary) / "model.json")
            with self.assertRaises(FaaSRankModelError):
                rust_faasrank_model_config(replace(model, epsilon=2.0))
            with self.assertRaises(FaaSRankModelError):
                rust_faasrank_model_config(
                    replace(model, weights={**model.weights, "unexpected": 1.0})
                )

    def _calibration_fixture(self, root: Path) -> tuple[Path, Path, Path, str]:
        tape_path = root / "training-tape.json"
        write_json_atomic(
            tape_path,
            {
                "version": 1,
                "workload_seed": "TRAIN",
                "events": [{"frame": 0, "dag_id": 0}],
            },
        )
        tape_hash = inspect_tape(tape_path).sha256
        plan_path = root / "plan.json"
        plan = create_faasrank_calibration_plan(
            plan_path,
            training_tape_sha256=tape_hash,
            candidates=[
                {"weights": WEIGHTS, "epsilon": 0.1},
                {"weights": SECOND_WEIGHTS, "epsilon": 0.2},
            ],
            training_seeds=["T01", "T02"],
            preregistered_at="2026-08-10T00:00:00Z",
        )
        by_id = {
            candidate["candidate_sha256"]: candidate for candidate in plan.candidates
        }
        better_id = candidate_parameter_sha256(SECOND_WEIGHTS, 0.2)
        runs = []
        for candidate_id, candidate in by_id.items():
            for seed in plan.training_seeds:
                run_id = f"train.{candidate_id[:8]}.{seed}"
                directory = root / run_id
                config_path = directory / "run_config.json"
                summary_path = directory / "summary.json"
                write_json_atomic(
                    config_path,
                    {
                        "run_id": run_id,
                        "method": "sche_FaaSRank",
                        "seed": seed,
                        "workload_tape": {"sha256": tape_hash},
                        "simulator_experiment": {
                            "faasrank_model": {
                                "state": "frozen",
                                "model_sha256": candidate_id,
                                "training_tape_sha256": tape_hash,
                                **candidate["weights"],
                                "epsilon": candidate["epsilon"],
                            }
                        },
                    },
                )
                throughput = 2000.0 if candidate_id == better_id else 1000.0
                write_json_atomic(
                    summary_path,
                    {
                        "schema": "NSE_SUMMARY_V1",
                        "run_id": run_id,
                        "run_complete": True,
                        "arrivals": 1,
                        "completed": 1,
                        "throughput_requests_per_second": throughput,
                        "simulator_internal_cost_per_completed_request": 0.5,
                        "latency_ms": {"mean": 2.0},
                    },
                )
                runs.append(
                    {
                        "candidate_sha256": candidate_id,
                        "seed": seed,
                        "run_id": run_id,
                        "run_config_path": str(config_path.relative_to(root)),
                        "run_config_sha256": file_hash(config_path),
                        "summary_path": str(summary_path.relative_to(root)),
                        "summary_sha256": file_hash(summary_path),
                    }
                )
        results_path = root / "results.json"
        write_json_atomic(
            results_path,
            {
                "schema_version": CALIBRATION_RESULTS_SCHEMA,
                "completed_at": "2026-08-10T01:00:00Z",
                "plan_sha256": plan.artifact_sha256,
                "training_tape_sha256": tape_hash,
                "runs": runs,
            },
        )
        return tape_path, plan_path, results_path, better_id

    def test_preregister_and_freeze_from_complete_real_training_matrix(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tape, plan_path, results, better_id = self._calibration_fixture(root)
            plan = load_faasrank_calibration_plan(plan_path)
            self.assertEqual(len(plan.candidates), 2)
            self.assertEqual(
                json.loads(plan_path.read_text(encoding="utf-8"))["objective"],
                CALIBRATION_OBJECTIVE,
            )
            model = freeze_faasrank_from_calibration(
                root / "frozen.json",
                training_tape_path=tape,
                calibration_plan_path=plan_path,
                training_results_path=results,
            )
            self.assertEqual(
                model.weights,
                {key: float(value) for key, value in SECOND_WEIGHTS.items()},
            )
            self.assertEqual(model.epsilon, 0.2)
            self.assertEqual(
                model.provenance["selection"]["selected_candidate_sha256"],
                better_id,
            )
            self.assertFalse(
                model.provenance["selection"]["formal_evaluation_results_used"]
            )
            self.assertEqual(len(model.provenance["calibration"]["verified_runs"]), 4)

    def test_partial_candidate_ranks_below_every_fully_applicable_candidate(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tape, plan_path, results_path, partial_id = self._calibration_fixture(root)
            full_id = candidate_parameter_sha256(WEIGHTS, 0.1)
            results = json.loads(results_path.read_text(encoding="utf-8"))
            record = next(
                item
                for item in results["runs"]
                if item["candidate_sha256"] == partial_id and item["seed"] == "T02"
            )
            summary_path = results_path.parent / record["summary_path"]
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary.update(
                {
                    "completed": 0,
                    "throughput_requests_per_second": 0.0,
                    "simulator_internal_cost_per_completed_request": None,
                    "latency_ms": {"mean": None},
                }
            )
            write_json_atomic(summary_path, summary)
            record["summary_sha256"] = file_hash(summary_path)
            write_json_atomic(results_path, results)

            model = freeze_faasrank_from_calibration(
                root / "frozen-with-non-applicable.json",
                training_tape_path=tape,
                calibration_plan_path=plan_path,
                training_results_path=results_path,
            )

            selection = model.provenance["selection"]
            self.assertEqual(selection["selected_candidate_sha256"], full_id)
            self.assertTrue(selection["selected_fully_applicable"])
            ranked = {
                item["candidate_sha256"]: item
                for item in selection["ranked_candidates"]
            }
            self.assertTrue(ranked[full_id]["fully_applicable"])
            self.assertFalse(ranked[partial_id]["fully_applicable"])
            self.assertEqual(ranked[partial_id]["applicable_seed_count"], 1)
            self.assertEqual(ranked[partial_id]["non_applicable_seed_count"], 1)
            self.assertGreater(
                ranked[partial_id]["mean_applicable_qpr"],
                ranked[full_id]["mean_applicable_qpr"],
            )
            audit = model.provenance["calibration"]["verified_runs"]
            non_applicable = next(
                item
                for item in audit
                if item["candidate_sha256"] == partial_id and item["seed"] == "T02"
            )
            self.assertFalse(non_applicable["qpr_applicable"])
            self.assertIsNone(non_applicable["qpr"])
            self.assertEqual(
                non_applicable["qpr_non_applicability_reason"],
                "zero_completed_requests",
            )

    def test_calibration_rejects_incomplete_or_tampered_results(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            tape, plan_path, results_path, _ = self._calibration_fixture(root)
            results = json.loads(results_path.read_text(encoding="utf-8"))
            results["runs"].pop()
            write_json_atomic(results_path, results)
            with self.assertRaisesRegex(FaaSRankModelError, "complete and paired"):
                freeze_faasrank_from_calibration(
                    root / "incomplete.json",
                    training_tape_path=tape,
                    calibration_plan_path=plan_path,
                    training_results_path=results_path,
                )

            tape, plan_path, results_path, _ = self._calibration_fixture(
                root / "tamper"
            )
            results = json.loads(results_path.read_text(encoding="utf-8"))
            summary_path = results_path.parent / results["runs"][0]["summary_path"]
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
            summary["throughput_requests_per_second"] = 9999.0
            write_json_atomic(summary_path, summary)
            with self.assertRaisesRegex(FaaSRankModelError, "summary hash mismatch"):
                freeze_faasrank_from_calibration(
                    root / "tampered.json",
                    training_tape_path=tape,
                    calibration_plan_path=plan_path,
                    training_results_path=results_path,
                )


if __name__ == "__main__":
    unittest.main()
