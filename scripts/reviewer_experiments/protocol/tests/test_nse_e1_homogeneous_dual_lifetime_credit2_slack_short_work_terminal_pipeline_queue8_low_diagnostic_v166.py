from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_dual_lifetime_credit2_slack_short_work_terminal_pipeline_queue8_low_diagnostic_v166 as v166,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    write_json_atomic,
)


class V166ProtocolTests(unittest.TestCase):
    def test_frozen_plan_implementation_and_exact_product(self) -> None:
        self.assertEqual(file_hash(v166.PLAN), v166.PLAN_SHA256)
        self.assertEqual(file_hash(v166.IMPLEMENTATION), v166.IMPLEMENTATION_SHA256)
        self.assertEqual(file_hash(v166.BINARY_PATH), v166.BINARY_SHA256)
        plan = read_json(v166.PLAN)
        implementation = read_json(v166.IMPLEMENTATION)
        self.assertEqual(plan["diagnostic_design"]["seeds"], list(v166.SEEDS))
        self.assertEqual(plan["candidate"]["profile"], v166.PROFILE)
        change = implementation["single_scientific_change"]
        self.assertEqual(change["credit_cap_per_request_lifetime"], 2)
        self.assertEqual(
            change["selected_credit_players_per_request_per_window_cap"], 1
        )
        self.assertEqual(change["second_credit_max_outstanding_before_admission"], 1)
        self.assertEqual(change["projected_outstanding_speculation_cap"], 2)
        self.assertTrue(change["v164_ready_antihotspot_disabled"])
        manifest = v166._rewrite_candidate(v166._assert_frozen_inputs(), "c" * 40)
        self.assertEqual([run["seed"] for run in manifest["runs"]], list(v166.SEEDS))
        self.assertEqual(len(manifest["reference_build_dependencies"]), 3)
        v166._validate_product(manifest, references_bound=False)
        self.assertTrue(
            all(
                run["metadata"]["v166_lifetime_credit_limit_per_request"] == 2
                and run["metadata"][
                    "v166_second_credit_requires_zero_outstanding_speculation"
                ]
                is False
                and run["metadata"][
                    "v166_second_credit_max_outstanding_before_admission"
                ]
                == 1
                and run["metadata"]["v166_projected_outstanding_speculation_cap"] == 2
                and run["metadata"]["v166_ready_antihotspot_enabled"] is False
                and run["metadata"]["v166_operational_score"]
                == "exact_V163_router_for_every_player"
                for run in manifest["runs"]
            )
        )

    @staticmethod
    def _write_log(
        canonical: Path,
        run_id: str,
        *,
        corrupt_outstanding_violation: bool = False,
        corrupt_projected_limit: bool = False,
    ) -> None:
        record = canonical / "reviewer_records" / run_id
        record.mkdir(parents=True)
        events = [
            {
                "kind": "run_config",
                "scheduler": "sche_nash",
                "operational_expert_proxy": v166.PROFILE,
                "reference": {"mode": "offline_required", "offline_load_ok": True},
                "operational_expert_proxy_contract": {
                    "version": "V166",
                    "queue_density_threshold": 8.0,
                    "below_threshold_expert": v166.LOW_EXPERT,
                    "at_or_above_threshold_expert": v166.HIGH_EXPERT,
                    "player_frontier": v166.FRONTIER,
                    "single_change_from_v155": v166.SINGLE_CHANGE,
                    "terminal_pipeline_definition": v166.TERMINAL_DEFINITION,
                    "short_work_pipeline_remaining_work_threshold": 5.5,
                    "short_work_pipeline_queue_density_threshold": 8.0,
                    "short_work_pipeline_queue_boundary": "below_is_strict",
                    "short_work_definition": v166.WORK_DEFINITION,
                    "jit_parent_tail_short_work_required": False,
                    "jit_parent_tail_definition": None,
                    "one_outstanding_short_work_credit_required": False,
                    "one_outstanding_short_work_credit_definition": None,
                    "lifetime_short_work_credit_required": True,
                    "lifetime_short_work_credit_definition": (
                        v166.LIFETIME_CREDIT_CONTRACT_DEFINITION
                    ),
                    "lifetime_short_work_credit_diagnostics": {
                        "credit_limit_per_request_lifetime": 2,
                        "second_credit_max_outstanding_before_admission": 1,
                        "projected_outstanding_limit": 2,
                    },
                    "ready_antihotspot_required": False,
                    "ready_antihotspot_definition": None,
                    "uses_completed_request_outcomes": False,
                    "reference_policy_independent": True,
                },
            }
        ]
        for frame in range(1000):
            first = frame == 0
            second = frame == 1
            admitted = first or second
            low = frame < 2
            events.append(
                {
                    "kind": "window",
                    "frame": frame,
                    "decision": {
                        "assignment_hash": frame,
                        "player_frontier": v166.FRONTIER,
                        "pipeline_players_with_incomplete_parents": 2
                        if admitted
                        else 1,
                        "pipeline_observation_fields_drive_future_windows": False,
                        "terminal_pipeline_frontier": {
                            "enabled": True,
                            "definition": v166.FRONTIER,
                            "admitted_terminal_players_with_incomplete_parents": 1,
                            "rejected_nonterminal_players_with_incomplete_parents": 5,
                            "short_work_remaining_work_threshold": 5.5,
                            "admitted_short_work_nonterminal_players_with_incomplete_parents": (
                                1 if admitted else 0
                            ),
                            "admitted_short_work_remaining_work_max": (
                                5.5 if admitted else None
                            ),
                            "rejected_nonterminal_remaining_work_min": 5.501,
                            "short_work_queue_gate": {
                                "enabled": True,
                                "threshold": 8.0,
                                "boundary": "below_is_strict",
                                "admitted_short_work_queue_density_max": (
                                    7.0 if admitted else None
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
                                "definition": v166.LIFETIME_CREDIT_DEFINITION,
                                "credit_limit_per_request_lifetime": 2,
                                "selection_order": v166.SELECTION_ORDER,
                                "terminal_players_consume_credit": False,
                                "ready_players_consume_credit": False,
                                "credit_reuse_after_parent_or_function_completion": False,
                                "second_credit_requires_zero_outstanding_speculation": False,
                                "second_credit_max_outstanding_before_admission": 1,
                                "projected_outstanding_limit": 2,
                                "uses_completion_or_performance_outcomes": False,
                                "requests_observed": 4,
                                "credited_requests_before": 0 if frame == 0 else 1,
                                "credited_requests_after": 1,
                                "retired_credited_requests": 0,
                                "first_admissions": 1 if first else 0,
                                "second_credited_requests_before": (
                                    0 if frame < 2 else 1
                                ),
                                "second_credited_requests_after": (
                                    0 if frame == 0 else 1
                                ),
                                "retired_second_credited_requests": 0,
                                "second_admissions": 1 if second else 0,
                                "rejected_already_credited": 0,
                                "rejected_second_while_outstanding": 1,
                                "rejected_same_window_not_selected": 1,
                                "repeat_admission_violations": 0,
                                "second_admission_outstanding_violations": (
                                    1
                                    if corrupt_outstanding_violation and frame == 700
                                    else 0
                                ),
                                "selected_per_request_max": 1 if admitted else 0,
                                "projected_outstanding_max": (
                                    3
                                    if corrupt_projected_limit and frame == 700
                                    else (2 if second else (1 if first else 0))
                                ),
                                "projected_requests_over_limit": (
                                    1 if corrupt_projected_limit and frame == 700 else 0
                                ),
                            },
                            "ready_antihotspot": {
                                "enabled": False,
                                "eligible_ready_players": 0,
                                "dispatched_ready_players": 0,
                                "dispatched_with_nonempty_history": 0,
                                "v163_anchor_substitutions": 0,
                                "history_length_max_before_update": 0,
                                "history_limit": 64,
                                "history_updates_after_successful_send": True,
                                "uses_completion_or_performance_outcomes": False,
                            },
                            "terminal_topology_source": (
                                "immutable_function_children_is_empty"
                            ),
                            "uses_completion_or_performance_outcomes": False,
                        },
                        "srpt_hiku2_ocs_queue_router": {
                            "enabled": True,
                            "queue_density": 7.0 if low else 9.0,
                            "queue_density_threshold": 8.0,
                            "selected_expert": (
                                v166.LOW_EXPERT if low else v166.HIGH_EXPERT
                            ),
                            "player_frontier": v166.FRONTIER,
                            "dependency_pipeline_frontier": True,
                            "uses_completion_outcomes": False,
                        },
                    },
                    "social": {
                        "reference_state_key": None,
                        "reference_source": "not_requested",
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

    def test_blind_log_proves_dual_credit_without_cap_exhaustion_breadth(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            canonical = Path(tmp)
            self._write_log(canonical, "synthetic-v166")
            evidence = v166._audit_nash_log(
                canonical, {"run_id": "synthetic-v166", "seed": "E09"}
            )
            self.assertEqual(evidence["first_lifetime_credit_admissions"], 1)
            self.assertEqual(evidence["second_lifetime_credit_admissions"], 1)
            self.assertEqual(evidence["second_admission_outstanding_violations"], 0)
            self.assertEqual(evidence["projected_requests_over_limit"], 0)
            self.assertEqual(evidence["performance_outcome_fields_parsed"], 0)
            gate = v166._mechanism_falsification_gate([evidence])
            self.assertTrue(gate["passed"])
            self.assertEqual(gate["failure_reasons"], [])

    def test_blind_log_rejects_outstanding_or_projected_limit_violation(self) -> None:
        for outstanding, projected in ((True, False), (False, True)):
            with self.subTest(outstanding=outstanding, projected=projected):
                with tempfile.TemporaryDirectory() as tmp:
                    canonical = Path(tmp)
                    self._write_log(
                        canonical,
                        "synthetic-v166-bad",
                        corrupt_outstanding_violation=outstanding,
                        corrupt_projected_limit=projected,
                    )
                    with self.assertRaisesRegex(
                        RuntimeError, "dual lifetime-credit2 evidence changed"
                    ):
                        v166._audit_nash_log(
                            canonical,
                            {"run_id": "synthetic-v166-bad", "seed": "E09"},
                        )

    def test_reveal_refuses_without_dual_blind_gate(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            blind = {
                "status": "pass",
                "performance_reveal_authorized": True,
                "throughput_completion_latency_cost_qpr_fields_parsed": 0,
                "required_lifetime_credit_terminal_congested_short_and_over_work_paths_exercised": True,
                "deterministic_selection_contract_verified": True,
                "same_window_choice_absence_is_not_a_failure": True,
                "dual_lifetime_credit_invariants_passed": False,
                "work_and_queue_threshold_invariants_passed": True,
                "both_routes_exercised": True,
                "ready_antihotspot_disabled": True,
            }
            blind["blind_audit_hash"] = object_hash(blind)
            write_json_atomic(v166.paths(root)["blind"], blind)
            with self.assertRaisesRegex(RuntimeError, "did not authorize reveal"):
                v166.reveal_v166(root)


if __name__ == "__main__":
    unittest.main()
