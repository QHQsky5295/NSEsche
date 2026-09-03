from __future__ import annotations

import copy
import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.protocol.p2_homogeneous import (
    P2_MIDDLE_RUN_COUNT,
    P2_MIDDLE_SELECTION_SCHEMA,
    P2_MIDDLE_WORKSPACE_NAME,
    build_middle_selection,
    validate_middle_selection,
)
from scripts.reviewer_experiments.protocol.schema import ProtocolValidationError


REPO_ROOT = Path(__file__).resolve().parents[4]
FORMAL_ROOT = REPO_ROOT / "runs" / "tscv1_g1_formal_q61_q80_98f822c_20260903"


def _paths(workspace: Path) -> dict[str, Path]:
    return {
        "source_manifest_path": FORMAL_ROOT / "q61-q80.formal.ready.json",
        "workspace": workspace,
        "plan_v4_path": REPO_ROOT
        / "refine-logs"
        / "TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V4.md",
        "p1a_path": REPO_ROOT
        / "refine-logs"
        / "P1_A_RETAINED_EVIDENCE_RESULT_AUDIT.md",
        "p1b_path": REPO_ROOT / "refine-logs" / "P1_B_EXACT_SMALL_RESULT_AUDIT.md",
        "low_audit_path": REPO_ROOT
        / "refine-logs"
        / "G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md",
        "low_report_path": FORMAL_ROOT
        / "online"
        / "homogeneous-low"
        / "homogeneous-low.cell-report.json",
    }


class P2HomogeneousSelectionTests(unittest.TestCase):
    def test_builds_exact_middle_allowlist_without_results(self) -> None:
        workspace = REPO_ROOT / "runs" / P2_MIDDLE_WORKSPACE_NAME
        self.assertFalse(workspace.exists())
        selection = build_middle_selection(**_paths(workspace))
        self.assertEqual(selection["schema_version"], P2_MIDDLE_SELECTION_SCHEMA)
        self.assertEqual(selection["selection"]["run_count"], P2_MIDDLE_RUN_COUNT)
        self.assertEqual(len(set(selection["selection"]["run_ids"])), 200)
        self.assertEqual(len(selection["input_receipts"]["tapes"]), 20)
        self.assertEqual(len(selection["input_receipts"]["references"]), 20)
        self.assertFalse(selection["scientific_metric_values_consulted"])
        self.assertFalse(selection["result_conditioned_seed_or_run_selection"])

    def test_validator_rejects_allowlist_tampering(self) -> None:
        workspace = REPO_ROOT / "runs" / P2_MIDDLE_WORKSPACE_NAME
        selection = build_middle_selection(**_paths(workspace))
        selection = copy.deepcopy(selection)
        selection["selection"]["run_ids"] = selection["selection"]["run_ids"][:-1]
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "tampered.json"
            path.write_text(json.dumps(selection), encoding="utf-8")
            with self.assertRaises(ProtocolValidationError):
                validate_middle_selection(path)


if __name__ == "__main__":
    unittest.main()
