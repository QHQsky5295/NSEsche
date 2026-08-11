from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.reviewer_experiments.poa.exact_poa import ExactGameError, solve_exact
from scripts.reviewer_experiments.poa.generate_games import generate_game
from scripts.reviewer_experiments.poa.verify_results import verify_files


class ExactPoaVerificationTests(unittest.TestCase):
    def _write_design(self, directory: Path) -> tuple[Path, Path]:
        games_path = directory / "games.jsonl"
        results_path = directory / "results.jsonl"
        games = [generate_game("verify-test", players, 0) for players in (4, 6, 8)]
        games_path.write_text(
            "".join(json.dumps(game) + "\n" for game in games), encoding="utf-8"
        )
        results_path.write_text(
            "".join(json.dumps(solve_exact(game)) + "\n" for game in games),
            encoding="utf-8",
        )
        return games_path, results_path

    def test_full_recomputation_verifies_small_frozen_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            games, results = self._write_design(Path(temporary))
            receipt = verify_files(games, results, states_per_size=1)
        self.assertEqual(receipt["status"], "verified")
        self.assertEqual(receipt["coverage"], {"4": 1, "6": 1, "8": 1})
        self.assertEqual(receipt["total_states"], 3)

    def test_tampered_result_is_rejected(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            games, results = self._write_design(Path(temporary))
            rows = [json.loads(line) for line in results.read_text().splitlines()]
            rows[0]["optimal_welfare"] += 1.0
            results.write_text(
                "".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8"
            )
            with self.assertRaises(ExactGameError):
                verify_files(games, results, states_per_size=1)


if __name__ == "__main__":
    unittest.main()
