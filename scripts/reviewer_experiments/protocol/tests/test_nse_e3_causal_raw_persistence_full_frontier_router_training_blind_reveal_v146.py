from __future__ import annotations

import gzip
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_blind_audit_v146 import (
    _expected_route,
    _persistence_comparison,
    _validate_v146_native_diagnostics,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_prepare_v146 import (
    ARM_ID,
    NEW_CONFIRMATION_SEEDS,
    PLAN_SHA256,
    PLAYER_FRONTIER,
    PROFILE,
    RUNTIME_NATIVE_KINDS,
    SERVICE_CERTIFICATE_SCOPE,
    TRAINING_SEED_LIST,
    V145_RESULT_HASH,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_reveal_v146 import (
    _validate_blind_audit,
    _validate_blind_document,
    evaluate_training_rows,
)
from scripts.reviewer_experiments.protocol.nse_e3_random_prefix_training_prepare_v142 import (
    BASELINE_METHODS,
    SCENARIOS,
)
from scripts.reviewer_experiments.protocol.tests.test_nse_e3_causal_raw_persistence_router_training_blind_reveal_v145 import (
    _synthetic_window as _v145_synthetic_window,
)
from scripts.reviewer_experiments.protocol.util import object_hash


def _synthetic_window(
    frame: int,
    raw: int,
    shock_active: bool,
    episode_count: int,
    first_start: int | None,
    baseline: int | None,
    recent: int | None,
    evaluated: bool,
    sustained: bool,
    started: bool,
    window_count: int,
    *,
    tamper_comparison: bool = False,
    tamper_projection: bool = False,
) -> dict[str, object]:
    event = _v145_synthetic_window(
        frame,
        raw,
        shock_active,
        episode_count,
        first_start,
        baseline,
        recent,
        evaluated,
        sustained,
        started,
        window_count,
        tamper_comparison=tamper_comparison,
    )
    decision = event["decision"]
    players = decision["request_function_players"]
    decision["player_frontier"] = PLAYER_FRONTIER
    decision["native_shadow_anchor"][
        "service_certificate_scope"
    ] = SERVICE_CERTIFICATE_SCOPE
    portfolio = decision["native_portfolio"]
    if players:
        portfolio["rule"] = "causal_raw_persistence_full_frontier"
    candidates = portfolio["candidates"]
    selected = next((item for item in candidates if item["selected"]), None)
    source_counts = {
        kind: players + 1 if players else 0 for kind in RUNTIME_NATIVE_KINDS
    }
    projected_counts = {kind: players for kind in RUNTIME_NATIVE_KINDS}
    if tamper_projection and frame == 0:
        projected_counts["greedy"] += 1
    projected_hashes = {
        kind: next(
            (
                item["ordered_command_hash"]
                for item in candidates
                if item["kind"] == kind
            ),
            0,
        )
        for kind in RUNTIME_NATIVE_KINDS
    }
    portfolio["v146_causal_raw_persistence_full_frontier"] = {
        "enabled": True,
        "frame": frame,
        "player_frontier": PLAYER_FRONTIER,
        "collect_task_config": PLAYER_FRONTIER,
        "common_hpa_candidate_filter_only": True,
        "full_frontier_feasible_player_count": players,
        "all_three_projected_assignments_cover_exact_full_feasible_cohort": True,
        "selected_kind": portfolio["v145_causal_raw_persistence"]["selected_kind"],
        "selection_reason": portfolio["v145_causal_raw_persistence"][
            "selection_reason"
        ],
        "source_native_command_counts": source_counts,
        "source_native_ordered_command_hashes": {
            kind: 1000 + index
            for index, kind in enumerate(RUNTIME_NATIVE_KINDS, start=1)
        },
        "projected_command_counts": projected_counts,
        "projected_ordered_command_hashes": projected_hashes,
        "dropped_noncohort_command_counts": {
            kind: source_counts[kind] - players for kind in RUNTIME_NATIVE_KINDS
        },
        "selected_native_ordered_command_hash": (
            selected["ordered_command_hash"] if selected else None
        ),
        "selected_native_assignment_hash": (
            selected["assignment_hash"] if selected else None
        ),
        "final_assignment_hash": portfolio["v145_causal_raw_persistence"][
            "final_assignment_hash"
        ],
        "selected_initializer_dispatched_exactly": portfolio[
            "v145_causal_raw_persistence"
        ]["selected_initializer_dispatched_exactly"],
        "accepted_nash_proposal_dispatched_exactly": portfolio[
            "v145_causal_raw_persistence"
        ]["accepted_nash_proposal_dispatched_exactly"],
    }
    return event


def _write_synthetic_diagnostics(
    canonical: Path, *, tamper_projection: bool = False
) -> None:
    path = canonical / "reviewer_records" / "synthetic"
    path.mkdir(parents=True)
    with gzip.open(path / "nash_metrics.jsonl.gz", "wt", encoding="utf-8") as handle:
        handle.write(
            json.dumps(
                {
                    "kind": "run_config",
                    "scheduler": "sche_nash",
                    "operational_expert_proxy": PROFILE,
                    "operational_player_frontier": PLAYER_FRONTIER,
                    "operational_expert_proxy_contract": None,
                }
            )
            + "\n"
        )
        for frame in range(4000):
            raw = 30 if 100 <= frame <= 154 else 10
            shock_active = 100 <= frame <= 149 or 200 <= frame <= 249
            episode_count = int(frame >= 100) + int(frame >= 200)
            first_start = 100 if frame >= 100 else None
            evaluated = frame >= 154
            event = _synthetic_window(
                frame,
                raw,
                shock_active,
                episode_count,
                first_start,
                800 if frame >= 100 else None,
                150 if evaluated else None,
                evaluated,
                evaluated,
                frame in {100, 200},
                frame + 1,
                tamper_projection=tamper_projection,
            )
            handle.write(json.dumps(event, separators=(",", ":")) + "\n")


class V146FullFrontierBlindRevealTests(unittest.TestCase):
    def test_causal_route_and_integer_boundary_are_unchanged(self) -> None:
        self.assertEqual(
            _expected_route(True, 1, True, True),
            ("faasrank", "age55_raw_persistence_sustained_retained_faasrank"),
        )
        self.assertEqual(
            _expected_route(True, 2, True, True),
            ("load_least", "recurrent_episode_retained_load_least"),
        )
        boundary = _persistence_comparison(recent=75, baseline=800)
        self.assertEqual(boundary["recent_scaled"], 12_000)
        self.assertEqual(boundary["baseline_scaled"], 12_000)
        self.assertTrue(boundary["sustained"])

    def test_blind_diagnostics_require_exact_full_frontier_projection(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical)
            evidence = _validate_v146_native_diagnostics(
                {"run_id": "synthetic"}, canonical
            )
            self.assertEqual(evidence["window_count"], 4000)
            self.assertEqual(evidence["player_frontier"], PLAYER_FRONTIER)
            self.assertEqual(evidence["persistence_evaluation_count"], 1)
            self.assertGreater(
                evidence["source_native_command_totals"]["greedy"],
                evidence["projected_command_totals"]["greedy"],
            )
            self.assertFalse(evidence["performance_fields_consulted"])
        with tempfile.TemporaryDirectory() as directory:
            canonical = Path(directory)
            _write_synthetic_diagnostics(canonical, tamper_projection=True)
            with self.assertRaisesRegex(RuntimeError, "projection changed"):
                _validate_v146_native_diagnostics({"run_id": "synthetic"}, canonical)

    def test_reveal_is_fail_closed_until_v146_blind_hashes_are_frozen(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "has not been frozen"):
            _validate_blind_audit()

    def test_blind_document_requires_zero_reads_and_v145_lineage(self) -> None:
        blind = {
            "status": "pass",
            "plan_file_sha256": PLAN_SHA256,
            "performance_summaries_parsed": 0,
            "candidate_performance_results_consulted": False,
            "reveal_authorized": True,
            "confirmation_inputs_opened": False,
            "baseline_rerun_count": 0,
            "baseline_run_count": 81,
            "candidate_run_count": 9,
            "analyzed_run_count": 90,
            "reference_count": 9,
            "tape_count": 12,
            "block_count": 9,
            "training_seeds": TRAINING_SEED_LIST,
            "sealed_confirmation_seeds": NEW_CONFIRMATION_SEEDS,
            "player_frontier": PLAYER_FRONTIER,
            "single_factor_change": "parents_completed_to_all_unscheduled_functions",
            "source_and_projected_native_command_evidence_required": True,
            "v145_parent": {
                "result_hash": V145_RESULT_HASH,
                "disposition": "complete_training_falsified_zero_of_nine_gates_no_confirmation_inputs_generated",
            },
        }
        expected_hash = object_hash(blind)
        blind["audit_hash"] = expected_hash
        _validate_blind_document(blind, expected_hash)
        blind["performance_summaries_parsed"] = 1
        with self.assertRaisesRegex(RuntimeError, "does not authorize reveal"):
            _validate_blind_document(blind, expected_hash)

    def test_all_nine_gates_are_required(self) -> None:
        rows = []
        for method_index, method in enumerate([*BASELINE_METHODS, ARM_ID]):
            for scenario in SCENARIOS:
                for seed in TRAINING_SEED_LIST:
                    value = 20.0 if method == ARM_ID else 10.0 + method_index / 100.0
                    rows.append(
                        {
                            "method_label": method,
                            "scenario": scenario,
                            "seed": seed,
                            "run_id": f"{method}-{scenario}-{seed}",
                            "fixed_window_completed": 1,
                            "throughput_requests_per_ms": value,
                            "qpr_finite_only": value,
                            "qpr_zero_completed_as_zero": value,
                        }
                    )
        evaluation = evaluate_training_rows(rows)
        self.assertTrue(evaluation["family_training_gate_pass"])
        self.assertEqual(
            evaluation["candidate_result"]["score"]["passed_gate_count"], 9
        )
        for row in rows:
            if row["method_label"] == ARM_ID and row["scenario"] == SCENARIOS[-1]:
                row["throughput_requests_per_ms"] = 0.0
        self.assertFalse(evaluate_training_rows(rows)["family_training_gate_pass"])


if __name__ == "__main__":
    unittest.main()
