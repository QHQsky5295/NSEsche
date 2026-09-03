from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.poa.exact_poa_v2 import solve_with_reference
from scripts.reviewer_experiments.poa.generate_games_v2 import generate_population
from scripts.reviewer_experiments.poa.verify_results_v2 import (
    VerificationError,
    verify_files,
)


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            json.dump(row, handle, ensure_ascii=False, allow_nan=False, sort_keys=True)
            handle.write("\n")


class VerifyResultsV2Tests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.games = generate_population(states_per_size=1)
        cls.results = [solve_with_reference(game) for game in cls.games]

    def test_independent_verifier_writes_complete_receipt(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            games_path = root / "exact_games_v2.jsonl"
            results_path = root / "exact_results_v2.jsonl"
            _write_jsonl(games_path, self.games)
            _write_jsonl(results_path, self.results)
            verified = verify_files(
                games_path, results_path, root / "out", states_per_size=1
            )
            self.assertEqual(verified["summary"]["state_count"], 3)
            self.assertEqual(
                verified["summary"]["coverage_by_players"], {"4": 1, "6": 1, "8": 1}
            )
            self.assertEqual(verified["verification"]["status"], "pass")
            self.assertTrue((root / "out" / "exact_verification_v2.json").is_file())

    def test_independent_verifier_rejects_tampered_optimum(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            games_path = root / "games.jsonl"
            results_path = root / "results.jsonl"
            tampered = [dict(result) for result in self.results]
            tampered[0] = dict(tampered[0])
            tampered[0]["optimal_welfare"] += 1.0
            _write_jsonl(games_path, self.games)
            _write_jsonl(results_path, tampered)
            with self.assertRaises(VerificationError):
                verify_files(games_path, results_path, root / "out", states_per_size=1)


if __name__ == "__main__":
    unittest.main()
