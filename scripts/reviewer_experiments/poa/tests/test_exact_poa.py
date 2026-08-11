from __future__ import annotations

import unittest

from scripts.reviewer_experiments.poa.exact_poa import ExactGameError, solve_exact
from scripts.reviewer_experiments.poa.generate_games import generate_game


class ExactPoaTests(unittest.TestCase):
    def test_generated_eight_player_game_enumerates_all_assignments(self) -> None:
        result = solve_exact(generate_game("test", 8, 0))
        self.assertEqual(result["feasible_assignments"], 3**8)
        self.assertEqual(result["players"], 8)
        self.assertGreaterEqual(result["pure_nash_equilibria"], 1)
        self.assertTrue(result["poa_applicable"])

    def test_dominant_single_node_has_unit_poa(self) -> None:
        game = generate_game("dominant", 4, 0)
        for player in game["players"]:
            player["candidates"] = [0]
        result = solve_exact(game)
        self.assertEqual(result["feasible_assignments"], 1)
        self.assertEqual(result["pure_nash_equilibria"], 1)
        self.assertAlmostEqual(result["exact_poa"], 1.0)
        self.assertAlmostEqual(result["relative_welfare_gap"], 0.0)

    def test_unknown_candidate_is_rejected(self) -> None:
        game = generate_game("invalid", 4, 0)
        game["players"][0]["candidates"] = [99]
        with self.assertRaises(ExactGameError):
            solve_exact(game)


if __name__ == "__main__":
    unittest.main()
