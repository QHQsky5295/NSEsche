from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.sla_pilots import (
    PilotOutcome,
    SlaPilotError,
    _select_template,
    _is_sustainable,
    run_isolated_sla_pilots,
)
from scripts.reviewer_experiments.protocol.tape import (
    derive_capacity_tape,
    inspect_tape,
)
from scripts.reviewer_experiments.protocol.util import write_json_atomic


class SlaPilotTests(unittest.TestCase):
    @staticmethod
    def _e1_template_run(
        *, seed: str = "E01", topology: str = "homogeneous", node_count: int = 20
    ) -> dict:
        return {
            "experiment_id": "E1",
            "seed": seed,
            "method": "greedy",
            "cluster": {"topology": topology, "node_count": node_count},
            "workload": {"request_freq": "low"},
            "workload_tape": {"sha256": "a" * 64},
        }

    def test_template_selection_uses_bound_e1_cluster_node_count(self) -> None:
        # Expanded formal manifests do not carry the editable config's
        # matrix_defaults object.  Selection must still work from the bound
        # E1 run declarations.
        manifest = {
            "runs": [
                self._e1_template_run(),
                self._e1_template_run(topology="heterogeneous"),
            ]
        }
        selected = _select_template(
            manifest,
            seed="E01",
            method="greedy",
            load="low",
            topology="homogeneous",
        )
        self.assertEqual(selected["cluster"]["node_count"], 20)
        self.assertEqual(selected["cluster"]["topology"], "homogeneous")

    def test_template_selection_rejects_inconsistent_e1_node_counts(self) -> None:
        manifest = {
            "runs": [
                self._e1_template_run(node_count=20),
                self._e1_template_run(topology="heterogeneous", node_count=100),
            ]
        }
        with self.assertRaisesRegex(SlaPilotError, "not uniquely frozen"):
            _select_template(
                manifest,
                seed="E01",
                method="greedy",
                load="low",
                topology="homogeneous",
            )

    def test_capacity_tape_is_exact_same_frame_replication(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            parent = root / "parent.json"
            output = root / "capacity.json"
            write_json_atomic(
                parent,
                {
                    "version": 1,
                    "workload_seed": "E01",
                    "events": [
                        {"frame": 2, "dag_id": 7, "sequence": 0},
                        {"frame": 9, "dag_id": 8, "sequence": 1},
                    ],
                },
            )

            entry = derive_capacity_tape(parent, output, 3, horizon_frames=10)
            observed = inspect_tape(output)

            self.assertEqual(observed.event_count, 6)
            self.assertEqual(observed.first_frame, 2)
            self.assertEqual(observed.last_frame, 9)
            self.assertEqual(entry["transform"]["factor"], 3)
            self.assertEqual(entry["measured_arrival_rate_rps"], 600.0)

    def test_sustainable_requires_a_fully_drained_zero_loss_run(self) -> None:
        outcome = PilotOutcome(
            role="throughput_capacity",
            class_assignment="all_throughput",
            factor=2,
            run_id="pilot",
            directory=Path("."),
            summary={
                "completion_ratio": 0.999,
                "admission_drop": 0,
                "admission_reject": 0,
                "timeout": 0,
            },
            final_frame={
                "queue_total": 0,
                "active_requests": 0,
                "tasks_in_system": 0,
            },
            tape={"sha256": "0" * 64},
        )
        self.assertTrue(_is_sustainable(outcome, 0.99))
        outcome.final_frame["queue_total"] = 1
        self.assertFalse(_is_sustainable(outcome, 0.99))

    def test_capacity_grid_is_frozen_before_any_process_launch(self) -> None:
        with self.assertRaisesRegex(SlaPilotError, "capacity factors"):
            run_isolated_sla_pilots(
                Path("missing.json"),
                Path("missing-workspace"),
                capacity_factors=(1, 3, 2),
            )


if __name__ == "__main__":
    unittest.main()
