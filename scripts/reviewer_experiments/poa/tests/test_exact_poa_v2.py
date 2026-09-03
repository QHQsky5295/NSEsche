from __future__ import annotations

import copy
import unittest

from scripts.reviewer_experiments.poa.exact_poa_v2 import (
    EPSILON,
    estimate_reference,
    is_nash,
    load_game,
    player_utility,
    solve_exact,
    solve_with_reference,
)
from scripts.reviewer_experiments.poa.generate_games_v2 import make_game


class ExactPoaV2Tests(unittest.TestCase):
    def test_generator_is_deterministic_and_matches_frozen_domain(self) -> None:
        first = make_game(4, 0, "NSE-P1-EXACT-V2")
        second = make_game(4, 0, "NSE-P1-EXACT-V2")
        self.assertEqual(first, second)
        self.assertEqual(first["schema"], "NSE_EXACT_GAME_V2")
        self.assertTrue(all("existing_impact" not in node for node in first["nodes"]))
        self.assertEqual(
            {player["quality_weight"] for player in first["players"]}, {0.5}
        )
        self.assertTrue(
            all(player["candidates"] == [0, 1, 2] for player in first["players"])
        )
        self.assertEqual(
            make_game(4, 50, "NSE-P1-EXACT-V2")["settings"]["quality_weight"],
            0.6,
        )

    def test_exact_enumeration_potential_and_reference_bound(self) -> None:
        raw = make_game(4, 7, "NSE-P1-EXACT-V2")
        result = solve_with_reference(raw)
        self.assertEqual(result["feasible_assignments"], 3**4)
        self.assertTrue(result["pure_nash_exists"])
        self.assertTrue(result["potential_verification"]["passed"])
        self.assertEqual(result["potential_verification"]["identity_violations"], 0)
        self.assertIn(
            result["ready_order"]["termination"],
            {"stable", "oscillation_best_state", "inner_iteration_limit_best_state"},
        )
        self.assertLessEqual(result["ready_order"]["inner_rounds"], 4)
        self.assertLessEqual(
            result["reference"]["welfare"],
            result["optimal_welfare"]
            + 1.0e-8 * max(1.0, abs(result["optimal_welfare"])),
        )
        self.assertEqual(
            estimate_reference(load_game(raw)), estimate_reference(load_game(raw))
        )

    def test_eight_player_state_has_complete_assignment_coverage(self) -> None:
        result = solve_exact(make_game(8, 3, "NSE-P1-EXACT-V2"))
        self.assertEqual(result["feasible_assignments"], 3**8)
        self.assertGreaterEqual(result["pure_nash_equilibria"], 1)
        self.assertTrue(result["potential_verification"]["passed"])

    def test_zero_complexity_boundary_has_zero_cross_player_impact(self) -> None:
        raw = copy.deepcopy(make_game(4, 11, "NSE-P1-EXACT-V2"))
        raw["players"][0]["function_complexity"] = 0.0
        raw["players"][0]["network_dependency"] = 0.0
        game = load_game(raw)
        colocated = (0, 0, 1, 2)
        moved = (2, 0, 1, 2)
        self.assertAlmostEqual(
            player_utility(game, colocated, 1),
            player_utility(game, moved, 1),
            places=12,
        )

        positive_players_fixed = list(solve_exact(raw)["ready_order"].values())
        self.assertTrue(positive_players_fixed)
        base = (0, 0, 1, 2)
        utilities = []
        for node in game.players[0].candidates:
            candidate = (node,) + base[1:]
            utilities.append((player_utility(game, candidate, 0), node, candidate))
        best_utility = max(value for value, _, _ in utilities)
        chosen = min(
            node for value, node, _ in utilities if abs(value - best_utility) <= EPSILON
        )
        selected = (chosen,) + base[1:]
        self.assertFalse(
            any(
                player_utility(game, (node,) + selected[1:], 0)
                > player_utility(game, selected, 0) + EPSILON
                for node in game.players[0].candidates
            )
        )
        self.assertIsInstance(is_nash(game, selected), bool)


if __name__ == "__main__":
    unittest.main()
