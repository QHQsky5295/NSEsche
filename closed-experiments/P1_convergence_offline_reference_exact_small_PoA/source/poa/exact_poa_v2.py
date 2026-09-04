#!/usr/bin/env python3
"""Exact PNE/PoA enumerator and frozen offline-reference estimator for P1-B."""

from __future__ import annotations

import argparse
import hashlib
import itertools
import json
import math
import os
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Sequence


SCHEMA = "NSE_EXACT_GAME_V2"
RESULT_SCHEMA = "NSE_EXACT_POA_REFERENCE_RESULT_V2"
EPSILON = 1.0e-6
IDENTITY_REL_TOL = 1.0e-8
LCG_MULTIPLIER = 6364136223846793005
LCG_ADDEND = 1442695040888963407
UINT64_MASK = (1 << 64) - 1


class ExactGameError(ValueError):
    pass


def _finite(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ExactGameError(f"{name} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise ExactGameError(f"{name} must be finite")
    return result


@dataclass(frozen=True)
class Node:
    node_id: int
    pressure: float
    utilization: float
    congestion_premium: float
    price: float
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
    epsilon: float
    inner_round_cap: int


@dataclass(frozen=True)
class Game:
    state_id: str
    nodes: tuple[Node, ...]
    players: tuple[Player, ...]
    settings: Settings


def load_game(raw: dict[str, Any]) -> Game:
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
        if "existing_impact" in item:
            raise ExactGameError("V2 prohibits nodes[].existing_impact")
        node_id = item.get("node_id")
        if isinstance(node_id, bool) or not isinstance(node_id, int) or node_id < 0:
            raise ExactGameError(f"nodes[{index}].node_id must be non-negative integer")
        if node_id in node_ids:
            raise ExactGameError(f"duplicate node_id {node_id}")
        node_ids.add(node_id)
        pressure = _finite(item.get("pressure"), f"nodes[{index}].pressure")
        utilization = _finite(item.get("utilization"), f"nodes[{index}].utilization")
        premium = _finite(
            item.get("congestion_premium"), f"nodes[{index}].congestion_premium"
        )
        price = _finite(item.get("price"), f"nodes[{index}].price")
        if pressure < 0 or not 0 <= utilization <= 1 or premium < 0 or price <= 0:
            raise ExactGameError(f"nodes[{index}] has an out-of-range state value")
        memory_value = item.get("available_container_memory")
        memory = (
            None
            if memory_value is None
            else _finite(memory_value, f"nodes[{index}].available_container_memory")
        )
        if memory is not None and memory < 0:
            raise ExactGameError("available_container_memory cannot be negative")
        existing = item.get("existing_functions", [])
        if not isinstance(existing, list) or any(
            isinstance(value, bool) or not isinstance(value, int) or value < 0
            for value in existing
        ):
            raise ExactGameError(f"nodes[{index}].existing_functions is invalid")
        nodes.append(
            Node(
                node_id,
                pressure,
                utilization,
                premium,
                price,
                memory,
                frozenset(existing),
            )
        )
    nodes.sort(key=lambda node: node.node_id)
    if [node.node_id for node in nodes] != list(range(len(nodes))):
        raise ExactGameError("node IDs must be contiguous from zero")

    shared_quality = _finite(raw_settings.get("quality_weight"), "quality_weight")
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
        if any(
            isinstance(candidate, bool)
            or not isinstance(candidate, int)
            or candidate not in node_ids
            for candidate in candidates
        ):
            raise ExactGameError(f"players[{index}] references an unknown candidate")
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
        for name in (
            "resource_intensity",
            "function_complexity",
            "network_dependency",
            "differentiation",
            "quality_weight",
        ):
            if not 0 <= values[name] <= 1:
                raise ExactGameError(f"players[{index}].{name} must be in [0,1]")
        if values["required_container_memory"] < 0:
            raise ExactGameError("required_container_memory cannot be negative")
        if abs(values["quality_weight"] - shared_quality) > 1.0e-12:
            raise ExactGameError(
                "all players must use the state's shared quality weight"
            )
        players.append(
            Player(
                player_id=player_id,
                function_id=function_id,
                candidates=tuple(sorted(set(candidates))),
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
        epsilon=_finite(raw_settings.get("epsilon", EPSILON), "epsilon"),
        inner_round_cap=int(raw_settings.get("inner_round_cap", 4)),
    )
    if settings.epsilon != EPSILON or settings.inner_round_cap != 4:
        raise ExactGameError("V2 requires epsilon=1e-6 and inner_round_cap=4")
    return Game(state_id, tuple(nodes), tuple(players), settings)


def is_feasible(game: Game, assignment: Sequence[int]) -> bool:
    for node in game.nodes:
        if node.available_container_memory is None:
            continue
        required: dict[int, float] = {}
        for player, assigned_node in zip(game.players, assignment):
            if assigned_node < 0 or assigned_node != node.node_id:
                continue
            if player.function_id in node.existing_functions:
                continue
            required[player.function_id] = max(
                required.get(player.function_id, 0.0), player.required_container_memory
            )
        if sum(required.values()) > node.available_container_memory + EPSILON:
            return False
    return True


def _non_pair_utility(game: Game, node_id: int, player_index: int) -> float:
    player = game.players[player_index]
    node = game.nodes[node_id]
    baseline = game.settings.base_utility * (
        player.resource_intensity + player.function_complexity
    )
    cost = node.price * (1.0 + player.resource_intensity)
    quality = (
        player.quality_weight
        * (player.function_complexity + player.network_dependency)
        / (1.0 + node.pressure)
    )
    contribution = (
        game.settings.contribution_coefficient
        * (1.0 + player.differentiation)
        * (1.0 - node.utilization)
        if game.settings.contribution_enabled
        else 0.0
    )
    return baseline - cost + quality + contribution


def player_utility(game: Game, assignment: Sequence[int], player_index: int) -> float:
    node_id = assignment[player_index]
    if node_id < 0:
        raise ExactGameError("cannot evaluate an unassigned player")
    player = game.players[player_index]
    externality = 0.0
    if game.settings.externality_enabled:
        other_impact = sum(
            other.impact
            for index, (other, assigned_node) in enumerate(
                zip(game.players, assignment)
            )
            if index != player_index and assigned_node == node_id
        )
        externality = (
            player.resource_intensity * game.nodes[node_id].pressure * other_impact
        )
    return _non_pair_utility(game, node_id, player_index) - externality


def welfare(game: Game, assignment: Sequence[int]) -> float:
    return sum(
        player_utility(game, assignment, index)
        for index, node_id in enumerate(assignment)
        if node_id >= 0
    )


def is_nash(game: Game, assignment: tuple[int, ...]) -> bool:
    for index, player in enumerate(game.players):
        current = player_utility(game, assignment, index)
        for candidate in player.candidates:
            if candidate == assignment[index]:
                continue
            deviated = assignment[:index] + (candidate,) + assignment[index + 1 :]
            if is_feasible(game, deviated) and (
                player_utility(game, deviated, index) > current + EPSILON
            ):
                return False
    return True


def potential(game: Game, assignment: Sequence[int]) -> float:
    value = sum(
        player.function_complexity * _non_pair_utility(game, node_id, index)
        for index, (player, node_id) in enumerate(zip(game.players, assignment))
        if node_id >= 0
    )
    if not game.settings.externality_enabled:
        return value
    for left in range(len(game.players)):
        left_node = assignment[left]
        if left_node < 0:
            continue
        for right in range(left + 1, len(game.players)):
            if assignment[right] != left_node:
                continue
            value -= (
                game.nodes[left_node].pressure
                * game.players[left].impact
                * game.players[right].impact
            )
    return value


def _potential_delta_for_move(
    game: Game,
    assignment: tuple[int, ...],
    player_index: int,
    new_node: int,
) -> float:
    old_node = assignment[player_index]
    player = game.players[player_index]
    delta = player.function_complexity * (
        _non_pair_utility(game, new_node, player_index)
        - _non_pair_utility(game, old_node, player_index)
    )
    if not game.settings.externality_enabled:
        return delta
    for other_index, other in enumerate(game.players):
        if other_index == player_index:
            continue
        other_node = assignment[other_index]
        if other_node == old_node:
            delta += game.nodes[old_node].pressure * player.impact * other.impact
        if other_node == new_node:
            delta -= game.nodes[new_node].pressure * player.impact * other.impact
    return delta


def _assignment_hash(game: Game, assignment: Sequence[int]) -> str:
    payload = "|".join(
        f"{player.player_id}:{node}" for player, node in zip(game.players, assignment)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ready_order_execution(
    game: Game,
) -> tuple[tuple[int, ...], dict[str, int | bool | str]]:
    assignment = [-1] * len(game.players)
    for index, player in enumerate(game.players):
        best_node: int | None = None
        best_utility = -math.inf
        for candidate in player.candidates:
            proposed = assignment.copy()
            proposed[index] = candidate
            if not is_feasible(game, proposed):
                continue
            utility = player_utility(game, proposed, index)
            if utility > best_utility + EPSILON or (
                abs(utility - best_utility) <= EPSILON
                and (best_node is None or candidate < best_node)
            ):
                best_node, best_utility = candidate, utility
        if best_node is None:
            raise ExactGameError(f"player {player.player_id} has no feasible node")
        assignment[index] = best_node

    current = tuple(assignment)
    best = current
    best_welfare = welfare(game, current)
    seen = {current}
    total_moves = 0
    for round_index in range(1, game.settings.inner_round_cap + 1):
        moved = False
        mutable = list(current)
        for index, player in enumerate(game.players):
            snapshot = tuple(mutable)
            old_node = mutable[index]
            old_utility = player_utility(game, snapshot, index)
            chosen_node = old_node
            chosen_utility = old_utility
            for candidate in player.candidates:
                if candidate == old_node:
                    continue
                proposed = mutable.copy()
                proposed[index] = candidate
                proposed_tuple = tuple(proposed)
                if not is_feasible(game, proposed_tuple):
                    continue
                utility = player_utility(game, proposed_tuple, index)
                if utility > chosen_utility + EPSILON or (
                    chosen_node != old_node
                    and abs(utility - chosen_utility) <= EPSILON
                    and candidate < chosen_node
                ):
                    chosen_node, chosen_utility = candidate, utility
            if chosen_node != old_node:
                mutable[index] = chosen_node
                moved = True
                total_moves += 1
        current = tuple(mutable)
        current_welfare = welfare(game, current)
        if current_welfare > best_welfare + EPSILON:
            best, best_welfare = current, current_welfare
        if not moved:
            return current, {
                "termination": "stable",
                "inner_stable": True,
                "inner_limit_hit": False,
                "oscillated": False,
                "inner_rounds": round_index,
                "assignment_moves": total_moves,
            }
        if current in seen:
            return best, {
                "termination": "oscillation_best_state",
                "inner_stable": False,
                "inner_limit_hit": False,
                "oscillated": True,
                "inner_rounds": round_index,
                "assignment_moves": total_moves,
            }
        seen.add(current)
    return best, {
        "termination": "inner_iteration_limit_best_state",
        "inner_stable": False,
        "inner_limit_hit": True,
        "oscillated": False,
        "inner_rounds": game.settings.inner_round_cap,
        "assignment_moves": total_moves,
    }


def _best_response_state(game: Game) -> tuple[int, ...]:
    return _ready_order_execution(game)[0]


def ready_order_result(game: Game) -> dict[str, Any]:
    selected, termination = _ready_order_execution(game)
    return {
        "assignment_sha256": _assignment_hash(game, selected),
        "welfare": welfare(game, selected),
        "is_pure_nash": is_nash(game, selected),
        **termination,
    }


def _social_greedy(game: Game, order: Sequence[int]) -> tuple[int, ...]:
    assignment = [-1] * len(game.players)
    for index in order:
        best_node: int | None = None
        best_welfare = -math.inf
        for candidate in game.players[index].candidates:
            proposed = assignment.copy()
            proposed[index] = candidate
            if not is_feasible(game, proposed):
                continue
            score = welfare(game, proposed)
            if score > best_welfare + EPSILON or (
                abs(score - best_welfare) <= EPSILON
                and (best_node is None or candidate < best_node)
            ):
                best_node, best_welfare = candidate, score
        if best_node is None:
            raise ExactGameError("social-greedy construction became infeasible")
        assignment[index] = best_node
    return tuple(assignment)


def _local_social_improvement(
    game: Game, start: tuple[int, ...], evaluation_budget: int
) -> tuple[int, ...]:
    current = start
    current_welfare = welfare(game, current)
    evaluations = 0
    while True:
        improved = False
        for index, player in enumerate(game.players):
            candidates = tuple(sorted(set(player.candidates)))
            if evaluations + len(candidates) > evaluation_budget:
                return current
            old_node = current[index]
            best_node = old_node
            best_welfare = current_welfare
            for candidate in candidates:
                evaluations += 1
                proposed = current[:index] + (candidate,) + current[index + 1 :]
                if not is_feasible(game, proposed):
                    continue
                score = welfare(game, proposed)
                if score > best_welfare + EPSILON or (
                    abs(score - best_welfare) <= EPSILON and candidate < best_node
                ):
                    best_node, best_welfare = candidate, score
            if best_welfare > current_welfare + EPSILON:
                proposed = current[:index] + (best_node,) + current[index + 1 :]
                exact_welfare = welfare(game, proposed)
                if exact_welfare > current_welfare + EPSILON:
                    current, current_welfare = proposed, exact_welfare
                    improved = True
        if not improved:
            return current


class _Lcg:
    def __init__(self, state: int):
        self.state = state & UINT64_MASK
        if self.state == 0:
            self.state = 1

    def next_u64(self) -> int:
        self.state = (self.state * LCG_MULTIPLIER + LCG_ADDEND) & UINT64_MASK
        return self.state

    def unit(self) -> float:
        return (self.next_u64() >> 11) / float(1 << 53)


def reference_seed(state_id: str) -> int:
    digest = hashlib.sha256(f"NSE-P1-REF-V2|{state_id}".encode("utf-8")).digest()
    for offset in range(0, len(digest), 8):
        seed = int.from_bytes(digest[offset : offset + 8], "big", signed=False)
        if seed != 0:
            return seed
    return 1


def estimate_reference(game: Game) -> dict[str, Any]:
    player_count = len(game.players)
    canonical = tuple(range(player_count))
    constrained = tuple(
        sorted(
            canonical,
            key=lambda index: (
                len(game.players[index].candidates),
                game.players[index].player_id,
            ),
        )
    )
    seed = reference_seed(game.state_id)
    shuffle_rng = _Lcg(seed)
    shuffled = list(canonical)
    for index in range(len(shuffled) - 1, 0, -1):
        other = shuffle_rng.next_u64() % (index + 1)
        shuffled[index], shuffled[other] = shuffled[other], shuffled[index]
    orders: list[tuple[int, ...]] = []
    for order in (canonical, tuple(reversed(canonical)), constrained, tuple(shuffled)):
        if order not in orders:
            orders.append(order)

    starts: list[tuple[int, ...]] = []
    for state in (
        _social_greedy(game, canonical),
        _best_response_state(game),
        *(_social_greedy(game, order) for order in orders),
    ):
        if state not in starts:
            starts.append(state)
    local_budget = 3 * player_count * max(player_count, 4)
    improved = [
        _local_social_improvement(game, start, local_budget) for start in starts
    ]
    current = improved[0]
    current_welfare = welfare(game, current)
    for candidate in improved[1:]:
        candidate_welfare = welfare(game, candidate)
        if candidate_welfare > current_welfare + EPSILON:
            current, current_welfare = candidate, candidate_welfare
    best = current
    best_welfare = current_welfare

    rng = _Lcg(seed)
    temperature = max(1.0, abs(current_welfare) / max(player_count, 1))
    for _ in range(64):
        index = rng.next_u64() % player_count
        candidates = tuple(sorted(set(game.players[index].candidates)))
        candidate = candidates[rng.next_u64() % len(candidates)]
        proposed = current[:index] + (candidate,) + current[index + 1 :]
        if not is_feasible(game, proposed):
            temperature *= 0.95
            continue
        proposed_welfare = welfare(game, proposed)
        delta = proposed_welfare - current_welfare
        if delta >= 0.0 or rng.unit() < math.exp(delta / max(temperature, 1.0e-12)):
            current, current_welfare = proposed, proposed_welfare
            if current_welfare > best_welfare + EPSILON:
                best, best_welfare = current, current_welfare
        temperature *= 0.95

    final = _local_social_improvement(game, best, local_budget)
    final_welfare = welfare(game, final)
    if final_welfare > best_welfare + EPSILON:
        best, best_welfare = final, final_welfare
    return {
        "welfare": best_welfare,
        "assignment_sha256": _assignment_hash(game, best),
        "seed_u64": reference_seed(game.state_id),
        "start_count": len(starts),
        "local_evaluation_budget_per_start": local_budget,
        "annealing_proposals": 64,
    }


def solve_exact(raw: dict[str, Any]) -> dict[str, Any]:
    game = load_game(raw)
    feasible_count = 0
    optimum_welfare = -math.inf
    optimum_assignment: tuple[int, ...] | None = None
    equilibria: list[tuple[float, tuple[int, ...]]] = []
    deviations_checked = 0
    strict_improvements = 0
    identity_violations = 0
    sign_violations = 0
    max_identity_residual = 0.0

    for assignment in itertools.product(
        *(player.candidates for player in game.players)
    ):
        if not is_feasible(game, assignment):
            continue
        feasible_count += 1
        state_welfare = welfare(game, assignment)
        if state_welfare > optimum_welfare + EPSILON or (
            abs(state_welfare - optimum_welfare) <= EPSILON
            and (optimum_assignment is None or assignment < optimum_assignment)
        ):
            optimum_welfare, optimum_assignment = state_welfare, assignment
        nash = True
        for index, player in enumerate(game.players):
            current_utility = player_utility(game, assignment, index)
            for candidate in player.candidates:
                if candidate == assignment[index]:
                    continue
                deviated = assignment[:index] + (candidate,) + assignment[index + 1 :]
                if not is_feasible(game, deviated):
                    continue
                deviations_checked += 1
                delta_utility = player_utility(game, deviated, index) - current_utility
                if delta_utility > EPSILON:
                    nash = False
                    strict_improvements += 1
                    delta_phi = _potential_delta_for_move(
                        game, assignment, index, candidate
                    )
                    weighted_delta = player.function_complexity * delta_utility
                    residual = abs(delta_phi - weighted_delta)
                    tolerance = IDENTITY_REL_TOL * max(
                        1.0, abs(delta_phi), abs(weighted_delta)
                    )
                    max_identity_residual = max(max_identity_residual, residual)
                    if residual > tolerance:
                        identity_violations += 1
                    if delta_phi <= 0.0 or weighted_delta <= 0.0:
                        sign_violations += 1
        if nash:
            equilibria.append((state_welfare, assignment))

    if feasible_count == 0 or optimum_assignment is None:
        raise ExactGameError(f"state {game.state_id} has no feasible assignment")
    equilibria.sort(key=lambda item: (item[0], item[1]))
    worst = equilibria[0] if equilibria else None
    best = min(equilibria, key=lambda item: (-item[0], item[1])) if equilibria else None
    exact_poa = (
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
        "worst_nash_assignment_sha256": (
            None if worst is None else _assignment_hash(game, worst[1])
        ),
        "best_nash_welfare": None if best is None else best[0],
        "best_nash_assignment_sha256": (
            None if best is None else _assignment_hash(game, best[1])
        ),
        "exact_poa": exact_poa,
        "relative_welfare_gap": relative_gap,
        "poa_applicable": exact_poa is not None,
        "ready_order": ready_order_result(game),
        "potential_verification": {
            "deviations_checked": deviations_checked,
            "strict_improvements": strict_improvements,
            "identity_violations": identity_violations,
            "sign_violations": sign_violations,
            "max_identity_residual": max_identity_residual,
            "passed": identity_violations == 0 and sign_violations == 0,
        },
        "poa_definition": "optimal_social_welfare/worst_positive_pure_nash_welfare",
        "formula_alignment": "NSESche Eq. (8) current-window utility and social welfare",
    }


def solve_with_reference(raw: dict[str, Any]) -> dict[str, Any]:
    exact_start = time.perf_counter_ns()
    result = solve_exact(raw)
    exact_ns = time.perf_counter_ns() - exact_start
    game = load_game(raw)
    reference_start = time.perf_counter_ns()
    reference = estimate_reference(game)
    reference_ns = time.perf_counter_ns() - reference_start
    optimum = float(result["optimal_welfare"])
    estimate = float(reference["welfare"])
    tolerance = IDENTITY_REL_TOL * max(1.0, abs(optimum))
    if estimate > optimum + tolerance:
        raise ExactGameError(
            f"reference estimate {estimate} exceeds exact optimum {optimum}"
        )
    absolute_shortfall = max(0.0, optimum - estimate)
    normalized_shortfall = absolute_shortfall / optimum if optimum > EPSILON else None
    result["reference"] = {
        **reference,
        "absolute_shortfall": absolute_shortfall,
        "normalized_shortfall": normalized_shortfall,
        "exact_hit": absolute_shortfall <= tolerance,
        "runtime_ns": reference_ns,
    }
    result["exact_enumeration_runtime_ns"] = exact_ns
    return result


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
    output_path.parent.mkdir(parents=True, exist_ok=True)
    if output_path.exists():
        raise ExactGameError(f"refusing to overwrite {output_path}")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{output_path.name}.", suffix=".partial", dir=output_path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for raw in _iter_jsonl(input_path):
                json.dump(
                    solve_with_reference(raw),
                    handle,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                )
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, output_path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path, help="NSE_EXACT_GAME_V2 JSONL")
    parser.add_argument("output", type=Path, help="atomic result JSONL")
    args = parser.parse_args(argv)
    try:
        solve_file(args.input, args.output)
    except (OSError, json.JSONDecodeError, ExactGameError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
