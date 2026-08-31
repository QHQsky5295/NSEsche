import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_queue8_low_training_v155 import (
    AMENDMENT,
    AMENDMENT_SHA256,
    BINARY_PATH,
    BINARY_SHA256,
    COMMON_ENVIRONMENT,
    HIGH_EXPERT,
    LOW_EXPERT,
    PLAN,
    PLAN_SHA256,
    PROFILE,
    QUEUE_THRESHOLD,
    SEEDS,
    SOURCE_MANIFEST,
    MODULE_CONF_SEMANTIC_HASH,
    _audit_nash_log,
    _assert_json_semantic,
    _rewrite_candidate,
    _validate_product,
)
from scripts.reviewer_experiments.protocol.util import file_hash, object_hash, read_json


class V155ProtocolTests(unittest.TestCase):
    def test_plan_binary_and_candidate_contract_are_frozen(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        self.assertEqual(file_hash(AMENDMENT), AMENDMENT_SHA256)
        self.assertEqual(file_hash(BINARY_PATH), BINARY_SHA256)
        plan = read_json(PLAN)
        candidate = plan["frozen_candidate"]
        self.assertEqual(candidate["profile"], PROFILE)
        self.assertEqual(candidate["mechanism"]["threshold"], QUEUE_THRESHOLD)
        self.assertFalse(candidate["mechanism"]["uses_completion_metrics"])
        self.assertTrue(plan["training_design"]["strictly_serial"])
        self.assertTrue(
            plan["training_design"][
                "no_seed_deletion_replacement_relabeling_or_selective_rerun"
            ]
        )
        self.assertFalse(
            plan["fresh_confirmation_boundary"][
                "fresh_confirmation_inputs_exist_at_preregistration"
            ]
        )

    def test_module_conf_audit_is_order_insensitive_but_value_strict(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "module.json"
            path.write_text('{"b":{"y":2,"x":1},"a":0}', encoding="utf-8")
            expected = file_hash(path)
            semantic = _assert_json_semantic(
                path,
                object_hash({"a": 0, "b": {"x": 1, "y": 2}}),
                "synthetic module config",
            )
            self.assertEqual(semantic["observed_file_sha256"], expected)
            path.write_text('{"a":0,"b":{"x":1,"y":3}}', encoding="utf-8")
            with self.assertRaisesRegex(RuntimeError, "semantic content changed"):
                _assert_json_semantic(
                    path, semantic["semantic_hash"], "synthetic module config"
                )
        self.assertEqual(len(MODULE_CONF_SEMANTIC_HASH), 64)

    def test_candidate_rewrite_is_exact_low_e01_e20_and_result_blind(self) -> None:
        manifest = _rewrite_candidate(read_json(SOURCE_MANIFEST), "1" * 40)
        _validate_product(manifest, references_bound=False)
        self.assertEqual(len(manifest["runs"]), 20)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 20)
        self.assertFalse(manifest["formal_results_eligible"])
        self.assertFalse(manifest["all_references_bound"])
        self.assertEqual({run["seed"] for run in manifest["runs"]}, set(SEEDS))
        for run in manifest["runs"]:
            self.assertEqual(run["workload"]["request_freq"], "low")
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILE
            )
            for key, value in COMMON_ENVIRONMENT.items():
                self.assertEqual(run["environment"][key], value)
            self.assertEqual(run["metadata"]["v155_queue_density_threshold"], 8.0)
            self.assertEqual(
                run["metadata"][
                    "v155_candidate_performance_summaries_parsed_before_run"
                ],
                0,
            )

    @staticmethod
    def _write_log(canonical: Path, run_id: str, *, corrupt_route: bool) -> None:
        log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
        log.parent.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": PROFILE,
                "operational_direct_initialization": True,
                "operational_unrestricted_initialization": True,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V155",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": LOW_EXPERT,
                    "at_or_above_threshold_expert": HIGH_EXPERT,
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            }
        ]
        for frame in range(1000):
            density = 7.0 if frame < 500 else 8.0
            selected = LOW_EXPERT if density < 8.0 else HIGH_EXPERT
            if corrupt_route and frame == 700:
                selected = LOW_EXPERT
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {"assignment_hash": frame},
                    "social": {
                        "reference_state_key": None if frame == 0 else f"state-{frame}",
                        "reference_source": "not_requested"
                        if frame == 0
                        else "offline_table",
                    },
                    "srpt_hiku2_ocs_queue_router": {
                        "enabled": True,
                        "queue_density": density,
                        "queue_density_threshold": 8.0,
                        "selected_expert": selected,
                        "uses_completion_outcomes": False,
                    },
                }
            )
        events.append(
            {
                "kind": "run_summary",
                "scheduler": "sche_nash",
                "windows": 1000,
                "observation_writer_error": None,
            }
        )
        with gzip.open(log, "wt", encoding="utf-8") as stream:
            for event in events:
                stream.write(json.dumps(event) + "\n")

    def test_blind_log_audit_proves_both_exact_routes_without_outcomes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "synthetic-v155", corrupt_route=False)
            evidence = _audit_nash_log(
                canonical, {"run_id": "synthetic-v155", "seed": "E01"}
            )
            self.assertEqual(evidence["windows"], 1000)
            self.assertEqual(evidence["below_threshold_route_windows"], 500)
            self.assertEqual(evidence["at_or_above_threshold_route_windows"], 500)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)

    def test_blind_log_audit_rejects_route_inconsistent_with_density(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            self._write_log(canonical, "synthetic-v155-bad", corrupt_route=True)
            with self.assertRaisesRegex(
                RuntimeError, "route does not match current queue density"
            ):
                _audit_nash_log(
                    canonical, {"run_id": "synthetic-v155-bad", "seed": "E01"}
                )


if __name__ == "__main__":
    unittest.main()
