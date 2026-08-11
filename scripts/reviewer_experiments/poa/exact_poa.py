from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable


SCHEMA = "NSE_EXACT_GAME_V1"
RESULT_SCHEMA = "NSE_EXACT_POA_RESULT_V1"
EPSILON = 1.0e-6


class ExactGameError(ValueError):
    pass


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExactGameError(f"{name} must be numeric")
    value = float(value)
    if not math.isfinite(value):
        raise ExactGameError(f"{name} must be finite")
    return value


@dataclass(frozen=True)
class Node:
    node_id: int
    pressure: float
    utilization: float
    price: float
    existing_impact: float
    available_container_memory: float | None
    existing_functions: frozenset[int]


@dataclass(frozen=True)
class Player:
    player_id: str
    function_id: int
    candidates: tuple[int, ...]
    resource_intensity: float
    function_complexity: float
    network_dependency: float
    differentiation: float
    quality_weight: float
    required_container_memory: float

    @property
    def impact(self) -> float:
        return self.resource_intensity * self.function_complexity


@dataclass(frozen=True)
class Settings:
    base_utility: float
    contribution_coefficient: float
    externality_enabled: bool
    contribution_enabled: bool


@dataclass(frozen=True)
class Game:
    state_id: str
    nodes: tuple[Node, ...]
    players: tuple[Player, ...]
    settings: Settings


def _load_game(raw: dict[str, Any]) -> Game:
    if raw.get("schema") != SCHEMA:
        raise ExactGameError(f"game schema must be {SCHEMA}")
    state_id = str(raw.get("state_id", "")).strip()
    if not state_id:
        raise ExactGameError("state_id is required")
    raw_nodes = raw.get("nodes")
    raw_players = raw.get("players")
    raw_settings = raw.get("settings")
    if not isinstance(raw_nodes, list) or not raw_nodes:
        raise ExactGameError("nodes must be a non-empty array")
    if not isinstance(raw_players, list) or not raw_players:
        raise ExactGameError("players must be a non-empty array")
    if not isinstance(raw_settings, dict):
        raise ExactGameError("settings must be an object")

    nodes: list[Node] = []
    node_ids: set[int] = set()
    for index, item in enumerate(raw_nodes):
        if not isinstance(item, dict):
            raise ExactGameError(f"nodes[{index}] must be an object")
        node_id = item.get("node_id")
        if isinstance(node_id, bool) or not isinstance(node_id, int) or node_id < 0:
            raise ExactGameError(
                f"nodes[{index}].node_id must be a non-negative integer"
            )
        if node_id in node_ids:
            raise ExactGameError(f"duplicate node_id {node_id}")
        node_ids.add(node_id)
        pressure = _finite(item.get("pressure"), f"nodes[{index}].pressure")
        utilization = _finite(item.get("utilization"), f"nodes[{index}].utilization")
        price = _finite(item.get("price"), f"nodes[{index}].price")
        existing_impact = _finite(
            item.get("existing_impact", 0.0), f"nodes[{index}].existing_impact"
        )
        if (
            pressure < 0
            or not 0 <= utilization <= 1
            or price <= 0
            or existing_impact < 0
        ):
            raise ExactGameError(f"nodes[{index}] has an out-of-range state value")
        memory = item.get("available_container_memory")
        available_memory = (
            None
            if memory is None
            else _finite(memory, f"nodes[{index}].available_container_memory")
        )
        if available_memory is not None and available_memory < 0:
            raise ExactGameError("available_container_memory cannot be negative")
        existing = item.get("existing_functions", [])
        if not isinstance(existing, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in existing
        ):
            raise ExactGameError(f"nodes[{index}].existing_functions is invalid")
        nodes.append(
            Node(
                node_id=node_id,
                pressure=pressure,
                utilization=utilization,
                price=price,
                existing_impact=existing_impact,
                available_container_memory=available_memory,
                existing_functions=frozenset(existing),
            )
        )
    nodes.sort(key=lambda node: node.node_id)
    if [node.node_id for node in nodes] != list(range(len(nodes))):
        raise ExactGameError("node IDs must be contiguous from zero")

    players: list[Player] = []
    player_ids: set[str] = set()
    for index, item in enumerate(raw_players):
        if not isinstance(item, dict):
            raise ExactGameError(f"players[{index}] must be an object")
        player_id = str(item.get("player_id", "")).strip()
        if not player_id or player_id in player_ids:
            raise ExactGameError(f"players[{index}].player_id is empty or duplicated")
        player_ids.add(player_id)
        function_id = item.get("function_id")
        candidates = item.get("candidates")
        if (
            isinstance(function_id, bool)
            or not isinstance(function_id, int)
            or function_id < 0
        ):
            raise ExactGameError(f"players[{index}].function_id is invalid")
        if not isinstance(candidates, list) or not candidates:
            raise ExactGameError(f"players[{index}].candidates must be non-empty")
        if any(candidate not in node_ids for candidate in candidates):
            raise ExactGameError(
                f"players[{index}] references an unknown candidate node"
            )
        candidates = sorted(set(candidates))
        values = {
            name: _finite(item.get(name), f"players[{index}].{name}")
            for name in (
                "resource_intensity",
                "function_complexity",
                "network_dependency",
                "differentiation",
                "quality_weight",
                "required_container_memory",
            )
        }
        if any(
            not 0 <= values[name] <= 1
            for name in values
            if name != "required_container_memory"
        ):
            raise ExactGameError(f"players[{index}] feature values must be in [0,1]")
        if values["required_container_memory"] < 0:
            raise ExactGameError("required_container_memory cannot be negative")
        players.append(
            Player(
                player_id=player_id,
                function_id=function_id,
                candidates=tuple(candidates),
                **values,
            )
        )
    players.sort(key=lambda player: player.player_id)
    settings = Settings(
        base_utility=_finite(raw_settings.get("base_utility", 10.0), "base_utility"),
        contribution_coefficient=_finite(
            raw_settings.get("contribution_coefficient", 1.0),
            "contribution_coefficient",
        ),
        externality_enabled=bool(raw_settings.get("externality_enabled", True)),
        contribution_enabled=bool(raw_settings.get("contribution_enabled", True)),
    )
    return Game(state_id, tuple(nodes), tuple(players), settings)


def _is_feasible(game: Game, assignment: tuple[int, ...]) -> bool:
    for node in game.nodes:
        if node.available_container_memory is None:
            continue
        required: dict[int, float] = {}
        for player, assigned_node in zip(game.players, assignment):
            if (
                assigned_node != node.node_id
                or player.function_id in node.existing_functions
            ):
                continue
            required[player.function_id] = max(
                required.get(player.function_id, 0.0), player.required_container_memory
            )
        if sum(required.values()) > node.available_container_memory + EPSILON:
            return False
    return True


def _player_utility(
    game: Game, assignment: tuple[int, ...], player_index: int
) -> float:
    player = game.players[player_index]
    node_id = assignment[player_index]
    node = game.nodes[node_id]
    other_impact = node.existing_impact + sum(
        other.impact
        for index, (other, assigned_node) in enumerate(zip(game.players, assignment))
        if index != player_index and assigned_node == node_id
    )
    baseline = game.settings.base_utility * (
        player.resource_intensity + player.function_complexity
    )
    cost = node.price * (1.0 + player.resource_intensity)
    quality = (
        player.quality_weight
        * (player.function_complexity + player.network_dependency)
        / (1.0 + node.pressure)
    )
    externality = (
        player.resource_intensity * node.pressure * max(other_impact, 0.0)
        if game.settings.externality_enabled
        else 0.0
    )
    contribution = (
        game.settings.contribution_coefficient
        * (1.0 + player.differentiation)
        * (1.0 - node.utilization)
        if game.settings.contribution_enabled
        else 0.0
    )
    return baseline - cost + quality - externality + contribution


def _welfare(game: Game, assignment: tuple[int, ...]) -> float:
    return sum(
        _player_utility(game, assignment, index) for index in range(len(game.players))
    )


def _is_nash(game: Game, assignment: tuple[int, ...]) -> bool:
    for index, player in enumerate(game.players):
        current = _player_utility(game, assignment, index)
        for candidate in player.candidates:
            if candidate == assignment[index]:
                continue
            deviated = (*assignment[:index], candidate, *assignment[index + 1 :])
            if not _is_feasible(game, deviated):
                continue
            if _player_utility(game, deviated, index) > current + EPSILON:
                return False
    return True


def _assignment_hash(game: Game, assignment: tuple[int, ...]) -> str:
    payload = "|".join(
        f"{player.player_id}:{node}" for player, node in zip(game.players, assignment)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def solve_exact(raw: dict[str, Any]) -> dict[str, Any]:
    game = _load_game(raw)
    feasible_count = 0
    optimum_welfare = -math.inf
    optimum_assignment: tuple[int, ...] | None = None
    equilibria: list[tuple[float, tuple[int, ...]]] = []
    for assignment in itertools.product(
        *(player.candidates for player in game.players)
    ):
        if not _is_feasible(game, assignment):
            continue
        feasible_count += 1
        welfare = _welfare(game, assignment)
        if welfare > optimum_welfare + EPSILON:
            optimum_welfare = welfare
            optimum_assignment = assignment
        if _is_nash(game, assignment):
            equilibria.append((welfare, assignment))
    if feasible_count == 0 or optimum_assignment is None:
        raise ExactGameError(f"state {game.state_id} has no feasible assignment")
    equilibria.sort(key=lambda item: (item[0], item[1]))
    worst = equilibria[0] if equilibria else None
    best = equilibria[-1] if equilibria else None
    ratio = (
        optimum_welfare / worst[0]
        if worst is not None and optimum_welfare > EPSILON and worst[0] > EPSILON
        else None
    )
    relative_gap = (
        (optimum_welfare - worst[0]) / optimum_welfare
        if worst is not None and optimum_welfare > EPSILON
        else None
    )
    return {
        "schema": RESULT_SCHEMA,
        "state_id": game.state_id,
        "nodes": len(game.nodes),
        "players": len(game.players),
        "feasible_assignments": feasible_count,
        "pure_nash_equilibria": len(equilibria),
        "pure_nash_exists": bool(equilibria),
        "optimal_welfare": optimum_welfare,
        "optimal_assignment_sha256": _assignment_hash(game, optimum_assignment),
        "worst_nash_welfare": None if worst is None else worst[0],
        "worst_nash_assignment_sha256": None
        if worst is None
        else _assignment_hash(game, worst[1]),
        "best_nash_welfare": None if best is None else best[0],
        "exact_poa": ratio,
        "relative_welfare_gap": relative_gap,
        "poa_applicable": ratio is not None,
        "poa_definition": "optimal_social_welfare/worst_pure_nash_social_welfare",
        "formula_alignment": "NSESche individual utility and social-welfare aggregation",
    }


def _iter_jsonl(path: Path) -> Iterable[dict[str, Any]]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise ExactGameError(f"line {line_number} is not a JSON object")
            yield value


def solve_file(input_path: Path, output_path: Path) -> None:
    partial = output_path.with_suffix(output_path.suffix + ".partial")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists() or partial.exists():
        raise ExactGameError(f"refusing to overwrite {output_path}")
    with partial.open("x", encoding="utf-8", newline="\n") as handle:
        for raw in _iter_jsonl(input_path):
            json.dump(solve_exact(raw), handle, ensure_ascii=False, allow_nan=False)
            handle.write("\n")
        handle.flush()
    partial.replace(output_path)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Enumerate exact PoA for small NSESche games"
    )
    parser.add_argument("input", type=Path, help="NSE_EXACT_GAME_V1 JSONL")
    parser.add_argument("output", type=Path, help="atomic result JSONL")
    args = parser.parse_args(argv)
    try:
        solve_file(args.input, args.output)
    except (OSError, json.JSONDecodeError, ExactGameError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
