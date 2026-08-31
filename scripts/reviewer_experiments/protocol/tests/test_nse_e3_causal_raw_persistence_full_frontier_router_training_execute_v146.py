from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_execute_v146 import (
    _assert_hashed,
    materialize_ready_schedule,
)
from scripts.reviewer_experiments.protocol.nse_e3_causal_raw_persistence_full_frontier_router_training_prepare_v146 import (
    ARM_ID,
    V142_TEMPLATE,
    _frozen_schedule,
    _rewrite_candidate,
)
from scripts.reviewer_experiments.protocol.util import (
    object_hash,
    read_json,
    write_json_atomic,
)


class V146FullFrontierExecuteTests(unittest.TestCase):
    def test_ready_schedule_maps_all_nine_bound_run_ids_once(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
            source = _frozen_schedule(manifest)
            write_json_atomic(root / "frozen-run-order-v146.json", source)
            write_json_atomic(root / f"manifest.{ARM_ID}.ready.json", manifest)
            ready = materialize_ready_schedule(root)
            self.assertEqual(len(ready["schedule"]), 9)
            self.assertEqual(len({item["run_id"] for item in ready["schedule"]}), 9)
            self.assertEqual(
                {item["source_unbound_run_id"] for item in ready["schedule"]},
                {run["run_id"] for run in manifest["runs"]},
            )
            _assert_hashed(ready, "schedule_hash", "test V146 ready schedule")

    def test_changed_existing_ready_schedule_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            manifest = _rewrite_candidate(read_json(V142_TEMPLATE))
            write_json_atomic(
                root / "frozen-run-order-v146.json", _frozen_schedule(manifest)
            )
            write_json_atomic(root / f"manifest.{ARM_ID}.ready.json", manifest)
            ready = materialize_ready_schedule(root)
            ready["schedule"][0]["seed"] = "tampered"
            ready.pop("schedule_hash")
            ready["schedule_hash"] = object_hash(ready)
            write_json_atomic(root / "frozen-ready-run-order-v146.json", ready)
            with self.assertRaisesRegex(RuntimeError, "refusing to replace"):
                materialize_ready_schedule(root)


if __name__ == "__main__":
    unittest.main()
