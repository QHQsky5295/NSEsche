from __future__ import annotations

import copy
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.analysis.e2_results import (
    _validate_merge_contract,
)
from scripts.reviewer_experiments.analysis.protocol_results import (
    materialize_analysis_reuse_rows,
)
from scripts.reviewer_experiments.protocol.formal_e1_shard import (
    derive_formal_e1_homogeneous_shard,
)
from scripts.reviewer_experiments.protocol.formal_e2_shard import (
    derive_formal_e2_weak_scaling_shard,
)
from scripts.reviewer_experiments.protocol.matrix import (
    build_manifest,
    load_protocol_config,
)
from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError
from scripts.reviewer_experiments.protocol.util import object_hash, write_json_atomic


def _source(root: Path) -> Path:
    path = root / "manifest.full.json"
    write_json_atomic(path, build_manifest(load_protocol_config(), "initial"))
    return path


class E2ReuseAuditTests(unittest.TestCase):
    def test_merge_contract_accepts_ready_e1_e2_and_detects_lineage_tampering(
        self,
    ) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = _source(root)
            e1 = derive_formal_e1_homogeneous_shard(source)
            e2 = derive_formal_e2_weak_scaling_shard(source)
            artifact = "a" * 64
            for manifest in (e1, e2):
                manifest["all_tapes_bound"] = True
                manifest["all_faasrank_models_bound"] = True
                manifest["all_references_bound"] = True
                for run in manifest["runs"]:
                    if run["method"] == "sche_FaaSRank":
                        run["baseline_model"] = {"artifact_sha256": artifact}
            # The merge contract intentionally inspects the stable fields and
            # does not require reconstructing the unavailable binary binding.
            contract = _validate_merge_contract(e2, e1)
            self.assertEqual(
                contract["reuse_rule_id"], "E2_FROM_E1_20NODE_HOMOGENEOUS_V1"
            )

            tampered = copy.deepcopy(e1)
            victim = next(
                run
                for run in tampered["runs"]
                if run["method"] == "greedy"
                and run["workload"]["request_freq"] == "low"
                and run["seed"] == "E01"
            )
            victim["workload_tape"]["key"] = "changed"
            with self.assertRaisesRegex(ProtocolValidationError, "differs"):
                _validate_merge_contract(e2, tampered)

    def test_e2_rule_materializes_only_sealed_e1_twenty_node_rows(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = _source(root)
            e1 = derive_formal_e1_homogeneous_shard(source)
            e2 = derive_formal_e2_weak_scaling_shard(source)
            source_rows = [
                {
                    "run_id": run["run_id"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "node_count": 20,
                    "throughput": 1.0,
                }
                for run in e1["runs"]
            ]
            reused, coverage = materialize_analysis_reuse_rows(
                e2,
                source_rows,
                source_runs=e1["runs"],
                target_experiment_ids={"E2"},
                source_manifest_hash=e1["manifest_hash"],
            )
            self.assertEqual(len(reused), 300)
            self.assertEqual(len(coverage), 300)
            self.assertTrue(all(row["node_count"] == 20 for row in reused))
            self.assertTrue(
                all(
                    row["analysis_record_kind"] == "materialized_reuse"
                    for row in reused
                )
            )
            self.assertTrue(all(item["status"] == "ok" for item in coverage))
            self.assertTrue(
                all(
                    row["reuse_contract_manifest_hash"] == e2["manifest_hash"]
                    and row["source_manifest_hash"] == e1["manifest_hash"]
                    for row in reused
                )
            )


if __name__ == "__main__":
    unittest.main()
