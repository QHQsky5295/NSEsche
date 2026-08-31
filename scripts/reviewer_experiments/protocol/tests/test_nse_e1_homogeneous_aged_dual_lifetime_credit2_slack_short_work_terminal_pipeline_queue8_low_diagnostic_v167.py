from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_aged_dual_lifetime_credit2_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v167 as v167,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


class V167ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v167.PLAN), v167.PLAN_SHA256)
        self.assertEqual(file_hash(v167.IMPLEMENTATION), v167.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v167.BINARY_PATH), v167.BINARY_SHA256)
        plan = read_json(v167.PLAN)
        implementation = read_json(v167.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v167.SEEDS))
        self.assertEqual(plan["candidate"]["profile"], v167.PROFILE)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["credit_cap_per_request_lifetime"], 2)
        self.assertEqual(change["second_credit_minimum_age_windows"], 2)
        self.assertEqual(change["second_credit_max_outstanding_before_admission"], 1)
        self.assertEqual(change["projected_outstanding_speculation_cap"], 2)
        manifest = v167._rewrite_candidate(v167._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v167.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        v167._validate_product(manifest, references_bound=False)
        self.assertTrue(
            all(
                run["metadata"]["v167_second_credit_minimum_age_windows"] == 2
                and run["metadata"][
                    "v167_second_credit_max_outstanding_before_admission"
                ]
                == 1
                and run["metadata"]["v167_operational_score"]
                == "exact_V163_router_for_every_player"
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(
        canonical: Path,
        run_id: str,
        *,
        omit_age_block: bool = False,
        corrupt_age: bool = False,
    ) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v167.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V167",
                    "player_frontier": v167.FRONTIER,
                    "single_change_from_v155": v167.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v167.TERMINAL_DEFINITION,
                    "lifetime_short_work_credit_definition": (
                        v167.LIFETIME_CREDIT_CONTRACT_DEFINITION
                    ),
                    "lifetime_short_work_credit_diagnostics": {
                        "credit_limit_per_request_lifetime": 2,
                        "second_credit_minimum_age_windows": 2,
                        "second_credit_max_outstanding_before_admission": 1,
                        "projected_outstanding_limit": 2,
                    },
                    "ready_antihotspot_required": False,
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            }
        ]
        for frame in range(1000):
            first = frame == 0
            second = frame == 2
            age_block = frame == 1 and not omit_age_block
            low = frame < 500
            credited_before = 0 if frame == 0 else 1
            credited_after = 1
            second_before = 0 if frame <= 2 else 1
            second_after = 1 if frame >= 2 else 0
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "player_frontier": v167.FRONTIER,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v167.FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": (
                                1 if first or second else 0
                            ),
                            "admitted_short_work_remaining_work_max": (
                                5.5 if first or second else None
                            ),
                            "rejected_nonterminal_remaining_work_min": 5.501,
                            "short_work_queue_gate": {
                                "admitted_short_work_queue_density_max": (
                                    7.0 if first or second else None
                                ),
                                "rejected_short_work_at_or_above_threshold": (
                                    0 if low else 2
                                ),
                                "rejected_short_work_queue_density_min": (
                                    None if low else 9.0
                                ),
                            },
                            "lifetime_short_work_credit": {
                                "enabled": True,
                                "definition": v167.LIFETIME_CREDIT_DEFINITION,
                                "credit_limit_per_request_lifetime": 2,
                                "selection_order": v167.SELECTION_ORDER,
                                "credit_reuse_after_parent_or_function_completion": False,
                                "second_credit_minimum_age_windows": 2,
                                "second_credit_max_outstanding_before_admission": 1,
                                "projected_outstanding_limit": 2,
                                "uses_completion_or_performance_outcomes": False,
                                "requests_observed": 4,
                                "credited_requests_before": credited_before,
                                "credited_requests_after": credited_after,
                                "retired_credited_requests": 0,
                                "first_admissions": 1 if first else 0,
                                "second_credited_requests_before": second_before,
                                "second_credited_requests_after": second_after,
                                "retired_second_credited_requests": 0,
                                "second_admissions": 1 if second else 0,
                                "second_rejected_below_minimum_age": (
                                    1 if age_block else 0
                                ),
                                "rejected_second_while_outstanding": 0,
                                "rejected_already_credited": 0,
                                "rejected_same_window_not_selected": 1,
                                "repeat_admission_violations": 0,
                                "second_admission_age_violations": (
                                    1 if corrupt_age and second else 0
                                ),
                                "second_admission_outstanding_violations": 0,
                                "projected_requests_over_limit": 0,
                                "first_admission_frame_requests_before": credited_before,
                                "first_admission_frame_requests_after": credited_after,
                                "retired_first_admission_frame_requests": 0,
                                "first_admission_frame_missing_requests": 0,
                                "first_admission_frame_orphan_requests": 0,
                                "second_admission_age_min": (
                                    (1 if corrupt_age else 2) if second else None
                                ),
                                "second_admission_age_max": (
                                    (1 if corrupt_age else 2) if second else None
                                ),
                                "selected_per_request_max": (
                                    1 if first or second else 0
                                ),
                                "projected_outstanding_max": (
                                    2 if second else (1 if first else 0)
                                ),
                            },
                            "uses_completion_or_performance_outcomes": False,
                        },
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density_threshold": 8.0,
                            "selected_expert": (
                                v167.LOW_EXPERT if low else v167.HIGH_EXPERT
                            ),
                            "player_frontier": v167.FRONTIER,
                            "uses_completion_outcomes": False,
                        },
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
        with gzip.open(
            record / "nash_metrics.jsonl.gz", "wt", encoding="utf-8", newline="\n"
        ) as stream:
            for event in events:
                stream.write(json.dumps(event, sort_keys=True) + "\n")

    def test_blind_log_requires_age_block_then_aged_second_admission(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v167")
            evidence = v167._audit_nash_log(
                canonical, {"run_id": "synthetic-v167", "seed": "E09"}
            )
            self.assertEqual(evidence["first_lifetime_credit_admissions"], 1)
            self.assertEqual(evidence["second_lifetime_credit_admissions"], 1)
            self.assertEqual(evidence["second_credit_rejected_below_minimum_age"], 1)
            self.assertEqual(evidence["second_admission_age_min"], 2)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)
            gate = v167._mechanism_falsification_gate([evidence])
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["failure_reasons"], [])

    def test_blind_gate_fails_without_age_block_and_log_rejects_young_second(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "missing-age-block", omit_age_block=True)
            evidence = v167._audit_nash_log(
                canonical, {"run_id": "missing-age-block", "seed": "E09"}
            )
            gate = v167._mechanism_falsification_gate([evidence])
            self.assertFalse(gate["passed"])
            self.assertIn(
                "unexercised_second_credit_blocked_below_minimum_age",
                gate["failure_reasons"],
            )
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "young-second", corrupt_age=True)
            with self.assertRaisesRegex(RuntimeError, "second admission age changed"):
                v167._audit_nash_log(
                    canonical, {"run_id": "young-second", "seed": "E09"}
                )

    def test_reveal_refuses_without_aged_dual_blind_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blind = {
                "status": "pass",
                "performance_reveal_authorized": True,
                "throughput_completion_latency_cost_qpr_fields_parsed": 0,
                "aged_dual_lifetime_credit_invariants_passed": False,
                "work_and_queue_threshold_invariants_passed": True,
                "both_routes_exercised": True,
                "ready_antihotspot_disabled": True,
            }
            blind["blind_audit_hash"] = object_hash(blind)
            write_json_atomic(v167.paths(root)["blind"], blind)
            with self.assertRaisesRegex(RuntimeError, "did not authorize reveal"):
                v167.reveal_v167(root)


if __name__ == "__main__":
    unittest.main()
