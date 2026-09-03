from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reviewer_experiments.protocol.stages import _promote_attempt_directory


class StagePromotionTests(unittest.TestCase):
    def test_recovers_verified_windows_destination_placement_anomaly(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            key = "steady.low.homogeneous.mixed.D61.example"
            attempt = root / "partial" / key / "attempt-01"
            attempt.mkdir(parents=True)
            (attempt / "attempt.json").write_text(
                json.dumps({"key": key, "status": "pass"}), encoding="utf-8"
            )
            (attempt / "artifact.bin").write_bytes(b"immutable experiment data")
            canonical = root / "canonical" / key

            def misplaced_replace(source: Path, destination: Path) -> None:
                destination.parent.mkdir(parents=True, exist_ok=True)
                source.rename(destination.parent / source.name)

            with patch(
                "scripts.reviewer_experiments.protocol.stages.promote_directory_exact",
                side_effect=misplaced_replace,
            ):
                promotion = _promote_attempt_directory(
                    attempt, canonical, expected_key=key
                )

            self.assertEqual(Path(promotion["source_path"]).name, "attempt-01")
            self.assertEqual(promotion["mode"], "recovered_misplaced_directory")
            self.assertEqual(
                (canonical / "artifact.bin").read_bytes(),
                b"immutable experiment data",
            )
            self.assertTrue((canonical.parent / "attempt-01").is_dir())


if __name__ == "__main__":
    unittest.main()
