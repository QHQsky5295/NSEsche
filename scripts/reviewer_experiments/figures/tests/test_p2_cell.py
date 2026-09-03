from __future__ import annotations

import csv
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.analysis.p2_homogeneous import (
    METHOD_LABELS,
    OUTPUT_NAMES,
    P2_RESULT_SCHEMA,
)
from scripts.reviewer_experiments.figures.p2_cell import render_p2_figure
from scripts.reviewer_experiments.protocol.schema import (
    FORMAL_E1_METHODS,
    G1_FORMAL_QUALIFICATION_SEEDS,
    ProtocolValidationError,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    write_json_atomic,
)


def _write_csv(path: Path, rows: list[dict[str, object]]) -> None:
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


class P2CellFigureTests(unittest.TestCase):
    def test_renders_vector_and_opaque_raster_outputs_without_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            run_path = root / OUTPUT_NAMES["run_rows"]
            summary_path = root / OUTPUT_NAMES["method_summaries"]
            run_rows: list[dict[str, object]] = []
            summaries: list[dict[str, object]] = []
            for method_index, method in enumerate(FORMAL_E1_METHODS):
                throughput = 1.0 + method_index * 0.05
                qpr = 0.01 + method_index * 0.001
                for seed_index, seed in enumerate(G1_FORMAL_QUALIFICATION_SEEDS):
                    run_rows.append(
                        {
                            "run_id": f"{method}-{seed}",
                            "seed": seed,
                            "method": method,
                            "throughput_requests_per_ms": throughput
                            + seed_index * 0.0001,
                            "qpr": qpr + seed_index * 0.00001,
                        }
                    )
                for metric, mean in (
                    ("throughput_requests_per_ms", throughput + 0.00095),
                    ("qpr", qpr + 0.000095),
                ):
                    summaries.append(
                        {
                            "method": method,
                            "method_label": METHOD_LABELS[method],
                            "metric": metric,
                            "n_finite": 20,
                            "mean": mean,
                            "bca_low": mean - 0.0005,
                            "bca_high": mean + 0.0005,
                        }
                    )
            _write_csv(run_path, run_rows)
            _write_csv(summary_path, summaries)
            result: dict[str, object] = {
                "schema_version": P2_RESULT_SCHEMA,
                "status": "complete_claim_reframed_middle_cell",
                "all_first_qc_valid_rows_retained": True,
                "result_conditioned_seed_or_run_selection": False,
                "artifact_receipts": {
                    "run_rows": {
                        "path": str(run_path.resolve()),
                        "bytes": run_path.stat().st_size,
                        "sha256": file_hash(run_path),
                    },
                    "method_summaries": {
                        "path": str(summary_path.resolve()),
                        "bytes": summary_path.stat().st_size,
                        "sha256": file_hash(summary_path),
                    },
                },
            }
            result["document_sha256"] = object_hash(result)
            result_path = root / OUTPUT_NAMES["result"]
            write_json_atomic(result_path, result)
            output = root / "figure"
            manifest = render_p2_figure(result_path, output, dpi=100)
            self.assertEqual(
                manifest["status"], "complete_publication_diagnostic_figure"
            )
            self.assertEqual(manifest["figure_contract"]["png_dpi"], 100)
            for suffix in ("pdf", "svg", "png"):
                self.assertGreater(manifest["artifacts"][suffix]["bytes"], 0)
            with self.assertRaises(ProtocolValidationError):
                render_p2_figure(result_path, output, dpi=100)


if __name__ == "__main__":
    unittest.main()
