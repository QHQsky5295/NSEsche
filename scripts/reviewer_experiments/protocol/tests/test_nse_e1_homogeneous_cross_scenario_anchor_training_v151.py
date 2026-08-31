import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_cross_scenario_anchor_training_blind_audit_v151 import (
    _audit_nash_log,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_cross_scenario_anchor_training_prepare_v151 import (
    COMMON_ENVIRONMENT,
    LOADS,
    PLAN,
    PLAN_SHA256,
    PROFILES,
    SEEDS,
    SOURCE_MANIFEST,
    _frozen_schedule,
    _rewrite_candidate,
    _validate_product,
)
from scripts.reviewer_experiments.protocol.util import file_hash, read_json


class V151ProtocolTests(unittest.TestCase):
    def test_plan_hash_and_profile_map_are_frozen(self) -> None:
        self.assertEqual(file_hash(PLAN), PLAN_SHA256)
        plan = read_json(PLAN)
        self.assertEqual(plan["frozen_candidate"]["load_profile_map"], PROFILES)
        self.assertEqual(plan["frozen_candidate"]["environment"], COMMON_ENVIRONMENT)
        self.assertFalse(
            plan["confirmation_boundary"][
                "fresh_confirmation_inputs_exist_at_preregistration"
            ]
        )
        self.assertTrue(
            plan["training_design"][
                "no_training_seed_deletion_replacement_relabeling_or_selective_rerun"
            ]
        )

    def test_candidate_rewrite_is_exact_and_result_blind(self) -> None:
        source = read_json(SOURCE_MANIFEST)
        manifest = _rewrite_candidate(source, "1" * 40)
        _validate_product(manifest)
        self.assertEqual(len(manifest["runs"]), 60)
        self.assertEqual(len(manifest["reference_build_dependencies"]), 60)
        self.assertFalse(manifest["formal_results_eligible"])
        self.assertFalse(manifest["all_references_bound"])
        self.assertEqual(
            {
                (run["workload"]["request_freq"], run["seed"])
                for run in manifest["runs"]
            },
            {(load, seed) for load in LOADS for seed in SEEDS},
        )
        for run in manifest["runs"]:
            load = run["workload"]["request_freq"]
            self.assertEqual(
                run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"], PROFILES[load]
            )
            for key, value in COMMON_ENVIRONMENT.items():
                self.assertEqual(run["environment"][key], value)
            self.assertEqual(run["metadata"]["v151_profile"], PROFILES[load])
            self.assertEqual(
                run["metadata"][
                    "v151_candidate_performance_summaries_parsed_before_run"
                ],
                0,
            )
        schedule_a = _frozen_schedule(manifest)
        schedule_b = _frozen_schedule(manifest)
        left = [
            (item["load"], item["seed"], item["profile"])
            for item in schedule_a["schedule"]
        ]
        right = [
            (item["load"], item["seed"], item["profile"])
            for item in schedule_b["schedule"]
        ]
        self.assertEqual(left, right)
        self.assertEqual(len(left), len(set(left)), 60)

    def test_blind_log_audit_requires_profile_direct_init_and_offline_reference(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            run_id = "synthetic-v151"
            log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
            log.parent.mkdir(parents=True)
            events = [
                {
                    "kind": "run_config",
                    "scheduler": "sche_nash",
                    "operational_expert_proxy": PROFILES["low"],
                    "operational_direct_initialization": True,
                    "operational_unrestricted_initialization": True,
                    "reference": {
                        "mode": "offline_required",
                        "offline_load_ok": True,
                    },
                }
            ]
            events.extend(
                {
                    "kind": "window",
                    "frame": frame,
                    "solver": {
                        "termination": "no_players" if frame == 0 else "converged"
                    },
                    "decision": {
                        "assignment_hash": frame,
                        "window_safe_guard": {
                            "evaluated": frame > 0,
                            "accepted": False,
                            "fallback_applied": frame > 0,
                            "certificate_uses_completion_outcomes": False,
                        },
                        "initializer_dominance_gate": {
                            "evaluated": frame > 0,
                            "accepted": False,
                            "certificate_uses_completion_outcomes": False,
                        },
                        "load_least_dominance_gate": {
                            "evaluated": frame > 0,
                            "accepted": False,
                            "certificate_uses_completion_outcomes": False,
                        },
                    },
                    "social": {
                        "reference_state_key": (
                            None if frame == 0 else f"state-{frame}"
                        ),
                        "reference_source": (
                            "not_requested"
                            if frame == 0
                            else (
                                "offline_table_nonpositive"
                                if frame == 1
                                else "offline_table"
                            )
                        ),
                    },
                }
                for frame in range(1000)
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
            evidence = _audit_nash_log(
                canonical,
                {
                    "run_id": run_id,
                    "seed": "E01",
                    "workload": {"request_freq": "low"},
                },
            )
            self.assertEqual(evidence["windows"], 1000)
            self.assertEqual(evidence["offline_reference_windows"], 999)
            self.assertEqual(evidence["offline_nonpositive_reference_windows"], 1)
            self.assertEqual(evidence["legitimate_not_requested_windows"], 1)
            self.assertEqual(evidence["profile"], PROFILES["low"])
            self.assertEqual(evidence["window_safe_guard_evaluated_windows"], 999)
            self.assertEqual(evidence["window_safe_guard_fallback_windows"], 999)


if __name__ == "__main__":
    unittest.main()
