from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from scripts.reviewer_experiments.protocol import util


def _winerror(code: int) -> OSError:
    error = OSError(code, "synthetic replace failure")
    error.winerror = code  # type: ignore[attr-defined]
    return error


class AtomicReplaceTests(unittest.TestCase):
    def test_windows_sharing_violation_is_retried_with_bounded_backoff(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            source.write_text("new", encoding="utf-8")
            destination.write_text("old", encoding="utf-8")
            replace = os.replace
            calls = 0

            def flaky(source_path: Path, destination_path: Path) -> None:
                nonlocal calls
                calls += 1
                if calls <= 2:
                    raise _winerror(32)
                replace(source_path, destination_path)

            with patch.object(util.os, "name", "nt"), patch.object(
                util.os, "replace", side_effect=flaky
            ), patch.object(util.time, "sleep") as sleep:
                util.replace_atomic(source, destination)

            self.assertEqual(calls, 3)
            self.assertEqual(sleep.call_count, 2)
            self.assertEqual(destination.read_text(encoding="utf-8"), "new")
            self.assertFalse(source.exists())

    def test_permanent_error_fails_closed_without_retry(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            source.write_text("new", encoding="utf-8")
            destination.write_text("old", encoding="utf-8")
            with patch.object(util.os, "name", "nt"), patch.object(
                util.os, "replace", side_effect=_winerror(87)
            ) as replace, patch.object(util.time, "sleep") as sleep:
                with self.assertRaises(OSError):
                    util.replace_atomic(source, destination)

            replace.assert_called_once_with(source, destination)
            sleep.assert_not_called()
            self.assertEqual(destination.read_text(encoding="utf-8"), "old")
            self.assertTrue(source.exists())

    def test_exhausted_transient_retries_fail_closed(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            source = root / "source"
            destination = root / "destination"
            source.write_text("new", encoding="utf-8")
            with patch.object(util.os, "name", "nt"), patch.object(
                util.os, "replace", side_effect=_winerror(5)
            ) as replace, patch.object(util.time, "sleep") as sleep:
                with self.assertRaises(OSError):
                    util.replace_atomic(source, destination)

            self.assertEqual(
                replace.call_count, len(util._ATOMIC_REPLACE_BACKOFF_SECONDS) + 1
            )
            self.assertEqual(
                sleep.call_count, len(util._ATOMIC_REPLACE_BACKOFF_SECONDS)
            )
            self.assertTrue(source.exists())


if __name__ == "__main__":
    unittest.main()
