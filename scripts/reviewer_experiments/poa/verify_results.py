from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path
from typing import Any, Iterable

from .exact_poa import RESULT_SCHEMA, SCHEMA, ExactGameError, solve_exact


RECEIPT_SCHEMA = "NSE_EXACT_POA_VERIFICATION_V1"


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _read_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                raise ExactGameError(f"{path}:{line_number} is blank")
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ExactGameError(f"{path}:{line_number} is not an object")
            yield value


def verify_files(
    games_path: Path,
    results_path: Path,
    *,
    states_per_size: int = 100,
) -> dict[str, Any]:
    if states_per_size <= 0:
        raise ExactGameError("states_per_size must be positive")
    games = list(_read_jsonl(games_path))
    results = list(_read_jsonl(results_path))
    expected_total = states_per_size * 3
    if len(games) != expected_total or len(results) != expected_total:
        raise ExactGameError(
            f"frozen exact-PoA coverage must contain {expected_total} games/results"
        )

    game_ids: set[str] = set()
    result_ids: set[str] = set()
    coverage: Counter[int] = Counter()
    applicable = 0
    no_pure_nash = 0
    for index, (game, result) in enumerate(zip(games, results), start=1):
        if game.get("schema") != SCHEMA:
            raise ExactGameError(f"game {index} has an invalid schema")
        state_id = game.get("state_id")
        if not isinstance(state_id, str) or not state_id or state_id in game_ids:
            raise ExactGameError(f"game {index} has a duplicate/invalid state_id")
        game_ids.add(state_id)
        nodes = game.get("nodes")
        players = game.get("players")
        if not isinstance(nodes, list) or len(nodes) != 3:
            raise ExactGameError(f"state {state_id} is not a 3-node game")
        if not isinstance(players, list) or len(players) not in {4, 6, 8}:
            raise ExactGameError(f"state {state_id} has an invalid player count")
        coverage[len(players)] += 1

        if result.get("schema") != RESULT_SCHEMA:
            raise ExactGameError(f"result {index} has an invalid schema")
        result_id = result.get("state_id")
        if (
            not isinstance(result_id, str)
            or not result_id
            or result_id in result_ids
            or result_id != state_id
        ):
            raise ExactGameError(f"result {index} is duplicated or out of order")
        result_ids.add(result_id)

        # This is a verification pass, not a schema-only check: enumerate the
        # full assignment/deviation space again and require byte-model-equivalent
        # result fields from the independently loaded game document.
        recomputed = solve_exact(game)
        if recomputed != result:
            differing = sorted(
                key
                for key in set(recomputed) | set(result)
                if recomputed.get(key) != result.get(key)
            )
            raise ExactGameError(
                f"result {state_id} differs from exact recomputation: {differing}"
            )
        applicable += int(bool(result.get("poa_applicable")))
        no_pure_nash += int(not bool(result.get("pure_nash_exists")))

    expected_coverage = {players: states_per_size for players in (4, 6, 8)}
    if dict(sorted(coverage.items())) != expected_coverage:
        raise ExactGameError(
            f"frozen exact-PoA coverage mismatch: {dict(coverage)} != {expected_coverage}"
        )
    if game_ids != result_ids:
        raise ExactGameError("game/result state-id populations differ")
    return {
        "schema": RECEIPT_SCHEMA,
        "status": "verified",
        "scope": "constructed_small_exact_game_not_azure_trace_run",
        "nodes": 3,
        "player_counts": [4, 6, 8],
        "states_per_player_count": states_per_size,
        "total_states": expected_total,
        "coverage": {str(key): value for key, value in sorted(coverage.items())},
        "poa_applicable_states": applicable,
        "states_without_pure_nash": no_pure_nash,
        "games_sha256": _sha256(games_path),
        "results_sha256": _sha256(results_path),
        "verification": "full_exact_recomputation_of_every_assignment_and_unilateral_deviation",
        "poa_definition": "optimal_social_welfare/worst_pure_nash_social_welfare",
        "formula_alignment": "NSESche individual utility and social-welfare aggregation",
    }


def _write_receipt(path: Path, receipt: dict[str, Any]) -> None:
    partial = path.with_name(path.name + ".partial")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists() or partial.exists():
        raise ExactGameError(f"refusing to overwrite {path}")
    with partial.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(receipt, handle, ensure_ascii=False, sort_keys=True, allow_nan=False)
        handle.write("\n")
        handle.flush()
    partial.replace(path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Recompute and verify the frozen 3-node exact pure-PoA design"
    )
    parser.add_argument("games", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("receipt", type=Path)
    parser.add_argument("--states-per-size", type=int, default=100)
    args = parser.parse_args(argv)
    try:
        receipt = verify_files(
            args.games, args.results, states_per_size=args.states_per_size
        )
        _write_receipt(args.receipt, receipt)
    except (OSError, json.JSONDecodeError, ExactGameError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
