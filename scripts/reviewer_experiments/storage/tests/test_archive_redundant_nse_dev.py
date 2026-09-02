from __future__ import annotations

import importlib.util
import json
import tempfile
import unittest
from pathlib import Path


SCRIPT = (
    Path(__file__).resolve().parents[1] / "archive_redundant_nse_dev.py"
)


def load_module():
    spec = importlib.util.spec_from_file_location("archive_redundant_nse_dev", SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError("cannot load archive helper")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class ArchiveRedundantNseDevTests(unittest.TestCase):
    def test_archive_round_trip_excludes_only_regenerable_directories(self) -> None:
        module = load_module()
        with tempfile.TemporaryDirectory() as source_temp, tempfile.TemporaryDirectory() as archive_temp:
            source = Path(source_temp)
            archive_dir = Path(archive_temp) / "archive"
            (source / "tmp" / "formal").mkdir(parents=True)
            (source / "tmp" / "formal" / "result.json").write_text(
                '{"throughput": 1.5}\n', encoding="utf-8"
            )
            (source / "serverless_sim" / "src").mkdir(parents=True)
            (source / "serverless_sim" / "src" / "sche_nash.rs").write_text(
                "fn main() {}\n", encoding="utf-8"
            )
            (source / "serverless_sim" / "target_e1_v206").mkdir(parents=True)
            (source / "serverless_sim" / "target_e1_v206" / "cache.bin").write_bytes(
                b"regenerable"
            )
            goal = source / "goal.md"
            plan = source / "plan.md"
            goal.write_text("goal\n", encoding="utf-8")
            plan.write_text("plan\n", encoding="utf-8")

            module.SOURCE_ROOT = source
            module.ARCHIVE_DIR = archive_dir
            module.ARCHIVE_PATH = archive_dir / "snapshot.zip"
            module.PARTIAL_PATH = archive_dir / "snapshot.zip.partial"
            module.RECEIPT_PATH = archive_dir / "snapshot.receipt.json"
            module.MIN_SOURCE_FILES = 1
            module.assert_frozen_paths = lambda: None

            receipt = module.create_archive(goal, plan)
            verification = module.verify_archive(module.ARCHIVE_PATH)
            entries = {
                item["relative_path"]
                for item in verification["manifest"]["entries"]
            }

            self.assertTrue(receipt["zip_crc_verified"])
            self.assertTrue(receipt["all_restored_file_sha256_verified"])
            self.assertIn("tmp/formal/result.json", entries)
            self.assertIn("serverless_sim/src/sche_nash.rs", entries)
            self.assertNotIn("serverless_sim/target_e1_v206/cache.bin", entries)
            self.assertIn(
                "serverless_sim/target_e1_v206",
                verification["manifest"]["excluded_directories"],
            )
            stored_receipt = json.loads(
                module.RECEIPT_PATH.read_text(encoding="utf-8")
            )
            self.assertEqual(receipt["receipt_hash"], stored_receipt["receipt_hash"])


if __name__ == "__main__":
    unittest.main()
