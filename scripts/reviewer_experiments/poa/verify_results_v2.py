#!/usr/bin/env python3
"""Independent raw-dictionary verifier and summarizer for P1-B V2 outputs.

This module deliberately does not import the primary enumerator or estimator.
"""

from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import itertools
import json
import math
import os
import statistics
import tempfile
from pathlib import Path
from typing import Any, Iterable, Sequence


GAME_SCHEMA = "NSE_EXACT_GAME_V2"
RESULT_SCHEMA = "NSE_EXACT_POA_REFERENCE_RESULT_V2"
EPSILON = 1.0e-6
REL_TOL = 1.0e-8


class VerificationError(ValueError):
    pass


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _load_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            value = json.loads(line)
            if not isinstance(value, dict):
                raise VerificationError(f"{path}:{line_number} is not an object")
            rows.append(value)
    return rows


def _normalized(
    raw: dict[str, Any]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if raw.get("schema") != GAME_SCHEMA:
        raise VerificationError("unexpected game schema")
    nodes = sorted(raw.get("nodes", []), key=lambda item: item["node_id"])
    players = sorted(raw.get("players", []), key=lambda item: item["player_id"])
    if not nodes or not players:
        raise VerificationError("empty node or player array")
    if any("existing_impact" in node for node in nodes):
        raise VerificationError("V2 game contains prohibited existing_impact")
    if [node["node_id"] for node in nodes] != list(range(len(nodes))):
        raise VerificationError("node IDs are not contiguous")
    shared_quality = float(raw["settings"]["quality_weight"])
    for player in players:
        if tuple(sorted(set(player["candidates"]))) != tuple(range(len(nodes))):
            raise VerificationError("every P1-B player must have all three candidates")
        if abs(float(player["quality_weight"]) - shared_quality) > 1.0e-12:
            raise VerificationError("quality weight is not shared within state")
    return nodes, players


def _feasible(
    nodes: list[dict[str, Any]],
    players: list[dict[str, Any]],
    assignment: Sequence[int],
) -> bool:
    for node in nodes:
        capacity = node.get("available_container_memory")
        if capacity is None:
            continue
        existing = set(node.get("existing_functions", []))
        required: dict[int, float] = {}
        for player, assigned in zip(players, assignment):
            if (
                assigned < 0
                or assigned != node["node_id"]
                or player["function_id"] in existing
            ):
                continue
            function_id = int(player["function_id"])
            required[function_id] = max(
                required.get(function_id, 0.0),
                float(player["required_container_memory"]),
            )
        if sum(required.values()) > float(capacity) + EPSILON:
            return False
    return True


def _non_pair(
    raw: dict[str, Any], node: dict[str, Any], player: dict[str, Any]
) -> float:
    settings = raw["settings"]
    h_ri = float(player["resource_intensity"])
    h_fc = float(player["function_complexity"])
    baseline = float(settings["base_utility"]) * (h_ri + h_fc)
    cost = float(node["price"]) * (1.0 + h_ri)
    quality = (
        float(player["quality_weight"])
        * (h_fc + float(player["network_dependency"]))
        / (1.0 + float(node["pressure"]))
    )
    contribution = 0.0
    if bool(settings.get("contribution_enabled", True)):
        contribution = (
            float(settings["contribution_coefficient"])
            * (1.0 + float(player["differentiation"]))
            * (1.0 - float(node["utilization"]))
        )
    return baseline - cost + quality + contribution


def _utility(
    raw: dict[str, Any],
    nodes: list[dict[str, Any]],
    players: list[dict[str, Any]],
    assignment: Sequence[int],
    index: int,
) -> float:
    node_id = assignment[index]
    player = players[index]
    value = _non_pair(raw, nodes[node_id], player)
    if bool(raw["settings"].get("externality_enabled", True)):
        other_impact = sum(
            float(other["resource_intensity"]) * float(other["function_complexity"])
            for other_index, (other, assigned) in enumerate(zip(players, assignment))
            if other_index != index and assigned == node_id
        )
        value -= (
            float(player["resource_intensity"])
            * float(nodes[node_id]["pressure"])
            * other_impact
        )
    return value


def _welfare(
    raw: dict[str, Any],
    nodes: list[dict[str, Any]],
    players: list[dict[str, Any]],
    assignment: Sequence[int],
) -> float:
    return sum(
        _utility(raw, nodes, players, assignment, index)
        for index, node_id in enumerate(assignment)
        if node_id >= 0
    )


def _is_nash(
    raw: dict[str, Any],
    nodes: list[dict[str, Any]],
    players: list[dict[str, Any]],
    assignment: tuple[int, ...],
) -> bool:
    for index, player in enumerate(players):
        current = _utility(raw, nodes, players, assignment, index)
        for candidate in player["candidates"]:
            if candidate == assignment[index]:
                continue
            deviated = assignment[:index] + (candidate,) + assignment[index + 1 :]
            if _feasible(nodes, players, deviated) and (
                _utility(raw, nodes, players, deviated, index) > current + EPSILON
            ):
                return False
    return True


def _potential_delta(
    raw: dict[str, Any],
    nodes: list[dict[str, Any]],
    players: list[dict[str, Any]],
    assignment: tuple[int, ...],
    index: int,
    candidate: int,
) -> float:
    player = players[index]
    old_node = assignment[index]
    h_fc = float(player["function_complexity"])
    player_impact = float(player["resource_intensity"]) * h_fc
    delta = h_fc * (
        _non_pair(raw, nodes[candidate], player)
        - _non_pair(raw, nodes[old_node], player)
    )
    if not bool(raw["settings"].get("externality_enabled", True)):
        return delta
    for other_index, other in enumerate(players):
        if other_index == index:
            continue
        other_impact = float(other["resource_intensity"]) * float(
            other["function_complexity"]
        )
        if assignment[other_index] == old_node:
            delta += float(nodes[old_node]["pressure"]) * player_impact * other_impact
        if assignment[other_index] == candidate:
            delta -= float(nodes[candidate]["pressure"]) * player_impact * other_impact
    return delta


def _assignment_hash(players: list[dict[str, Any]], assignment: Sequence[int]) -> str:
    payload = "|".join(
        f"{player['player_id']}:{node}" for player, node in zip(players, assignment)
    ).encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def _ready_order(
    raw: dict[str, Any], nodes: list[dict[str, Any]], players: list[dict[str, Any]]
) -> tuple[tuple[int, ...], dict[str, int | bool | str]]:
    assignment = [-1] * len(players)
    for index, player in enumerate(players):
        best_node: int | None = None
        best_value = -math.inf
        for candidate in player["candidates"]:
            proposed = assignment.copy()
            proposed[index] = candidate
            if not _feasible(nodes, players, proposed):
                continue
            value = _utility(raw, nodes, players, proposed, index)
            if value > best_value + EPSILON or (
                abs(value - best_value) <= EPSILON
                and (best_node is None or candidate < best_node)
            ):
                best_node, best_value = candidate, value
        if best_node is None:
            raise VerificationError("ready_order initialization has no feasible choice")
        assignment[index] = best_node
    current = tuple(assignment)
    best = current
    best_value = _welfare(raw, nodes, players, current)
    seen = {current}
    total_moves = 0
    for round_index in range(1, 5):
        mutable = list(current)
        moved = False
        for index, player in enumerate(players):
            snapshot = tuple(mutable)
            old_node = mutable[index]
            chosen = old_node
            chosen_value = _utility(raw, nodes, players, snapshot, index)
            for candidate in player["candidates"]:
                if candidate == old_node:
                    continue
                proposed = mutable.copy()
                proposed[index] = candidate
                proposed_tuple = tuple(proposed)
                if not _feasible(nodes, players, proposed_tuple):
                    continue
                value = _utility(raw, nodes, players, proposed_tuple, index)
                if value > chosen_value + EPSILON or (
                    chosen != old_node
                    and abs(value - chosen_value) <= EPSILON
                    and candidate < chosen
                ):
                    chosen, chosen_value = candidate, value
            if chosen != old_node:
                mutable[index] = chosen
                moved = True
                total_moves += 1
        current = tuple(mutable)
        value = _welfare(raw, nodes, players, current)
        if value > best_value + EPSILON:
            best, best_value = current, value
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
        "inner_rounds": 4,
        "assignment_moves": total_moves,
    }


def _independent_exact(raw: dict[str, Any]) -> dict[str, Any]:
    nodes, players = _normalized(raw)
    optimum = -math.inf
    optimum_assignment: tuple[int, ...] | None = None
    equilibria: list[tuple[float, tuple[int, ...]]] = []
    feasible_count = 0
    deviations = 0
    strict = 0
    identity_violations = 0
    sign_violations = 0
    max_residual = 0.0
    choices = [tuple(sorted(set(player["candidates"]))) for player in players]
    for assignment in itertools.product(*choices):
        if not _feasible(nodes, players, assignment):
            continue
        feasible_count += 1
        state_welfare = _welfare(raw, nodes, players, assignment)
        if state_welfare > optimum + EPSILON or (
            abs(state_welfare - optimum) <= EPSILON
            and (optimum_assignment is None or assignment < optimum_assignment)
        ):
            optimum, optimum_assignment = state_welfare, assignment
        nash = True
        for index, player in enumerate(players):
            current = _utility(raw, nodes, players, assignment, index)
            for candidate in choices[index]:
                if candidate == assignment[index]:
                    continue
                deviated = assignment[:index] + (candidate,) + assignment[index + 1 :]
                if not _feasible(nodes, players, deviated):
                    continue
                deviations += 1
                delta_u = _utility(raw, nodes, players, deviated, index) - current
                if delta_u > EPSILON:
                    nash = False
                    strict += 1
                    delta_phi = _potential_delta(
                        raw, nodes, players, assignment, index, candidate
                    )
                    weighted_delta = float(player["function_complexity"]) * delta_u
                    residual = abs(delta_phi - weighted_delta)
                    max_residual = max(max_residual, residual)
                    tolerance = REL_TOL * max(1.0, abs(delta_phi), abs(weighted_delta))
                    if residual > tolerance:
                        identity_violations += 1
                    if delta_phi <= 0.0 or weighted_delta <= 0.0:
                        sign_violations += 1
        if nash:
            equilibria.append((state_welfare, assignment))
    if optimum_assignment is None:
        raise VerificationError("game has no feasible assignment")
    equilibria.sort(key=lambda item: (item[0], item[1]))
    worst = equilibria[0] if equilibria else None
    best = min(equilibria, key=lambda item: (-item[0], item[1])) if equilibria else None
    selected, ready_termination = _ready_order(raw, nodes, players)
    return {
        "state_id": raw["state_id"],
        "nodes": len(nodes),
        "players": len(players),
        "feasible_assignments": feasible_count,
        "pure_nash_equilibria": len(equilibria),
        "pure_nash_exists": bool(equilibria),
        "optimal_welfare": optimum,
        "optimal_assignment_sha256": _assignment_hash(players, optimum_assignment),
        "worst_nash_welfare": None if worst is None else worst[0],
        "worst_nash_assignment_sha256": (
            None if worst is None else _assignment_hash(players, worst[1])
        ),
        "best_nash_welfare": None if best is None else best[0],
        "best_nash_assignment_sha256": (
            None if best is None else _assignment_hash(players, best[1])
        ),
        "exact_poa": (
            optimum / worst[0]
            if worst is not None and optimum > EPSILON and worst[0] > EPSILON
            else None
        ),
        "relative_welfare_gap": (
            (optimum - worst[0]) / optimum
            if worst is not None and optimum > EPSILON
            else None
        ),
        "ready_order": {
            "assignment_sha256": _assignment_hash(players, selected),
            "welfare": _welfare(raw, nodes, players, selected),
            "is_pure_nash": _is_nash(raw, nodes, players, selected),
            **ready_termination,
        },
        "potential_verification": {
            "deviations_checked": deviations,
            "strict_improvements": strict,
            "identity_violations": identity_violations,
            "sign_violations": sign_violations,
            "max_identity_residual": max_residual,
            "passed": identity_violations == 0 and sign_violations == 0,
        },
    }


def _close(left: Any, right: Any) -> bool:
    if left is None or right is None:
        return left is right
    if isinstance(left, bool) or isinstance(right, bool):
        return left is right
    if isinstance(left, (int, float)) and isinstance(right, (int, float)):
        return abs(float(left) - float(right)) <= REL_TOL * max(
            1.0, abs(float(left)), abs(float(right))
        )
    return left == right


def _compare(
    primary: dict[str, Any], independent: dict[str, Any], prefix: str = ""
) -> None:
    for key, expected in independent.items():
        name = f"{prefix}.{key}" if prefix else key
        if key not in primary:
            raise VerificationError(f"missing primary field {name}")
        observed = primary[key]
        if isinstance(expected, dict):
            if not isinstance(observed, dict):
                raise VerificationError(f"primary field {name} is not an object")
            _compare(observed, expected, name)
        elif not _close(observed, expected):
            raise VerificationError(
                f"primary mismatch {name}: observed={observed!r}, expected={expected!r}"
            )


def _assert_finite(value: Any, name: str = "result") -> None:
    if isinstance(value, dict):
        for key, child in value.items():
            _assert_finite(child, f"{name}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _assert_finite(child, f"{name}[{index}]")
    elif isinstance(value, float) and not math.isfinite(value):
        raise VerificationError(f"nonfinite value at {name}")


def _quantile(values: Sequence[float], probability: float) -> float:
    if not values:
        raise VerificationError("cannot compute quantile of empty values")
    ordered = sorted(values)
    position = (len(ordered) - 1) * probability
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    weight = position - lower
    return ordered[lower] * (1.0 - weight) + ordered[upper] * weight


def _atomic_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise VerificationError(f"refusing to overwrite {path}")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".partial", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def verify_files(
    games_path: Path,
    results_path: Path,
    output_dir: Path,
    states_per_size: int = 100,
    primary_source: Path | None = None,
    verifier_source: Path | None = None,
) -> dict[str, Any]:
    games = _load_jsonl(games_path)
    results = _load_jsonl(results_path)
    expected_total = 3 * states_per_size
    if len(games) != expected_total or len(results) != expected_total:
        raise VerificationError(
            f"expected {expected_total} games/results, got {len(games)}/{len(results)}"
        )
    game_by_id = {str(game.get("state_id")): game for game in games}
    result_by_id = {str(result.get("state_id")): result for result in results}
    if len(game_by_id) != expected_total or len(result_by_id) != expected_total:
        raise VerificationError("duplicate state_id in games or results")
    if set(game_by_id) != set(result_by_id):
        raise VerificationError("game/result state coverage differs")

    state_rows: list[dict[str, Any]] = []
    coverage = {4: 0, 6: 0, 8: 0}
    for state_id in sorted(game_by_id):
        game = game_by_id[state_id]
        primary = result_by_id[state_id]
        if primary.get("schema") != RESULT_SCHEMA:
            raise VerificationError(f"{state_id}: unexpected result schema")
        _assert_finite(primary, state_id)
        independent = _independent_exact(game)
        _compare(primary, independent)
        players = int(independent["players"])
        if players not in coverage:
            raise VerificationError(f"{state_id}: unsupported player count {players}")
        coverage[players] += 1
        if independent["feasible_assignments"] != 3**players:
            raise VerificationError(f"{state_id}: not all assignments are feasible")
        if not independent["pure_nash_exists"]:
            raise VerificationError(f"{state_id}: no pure Nash equilibrium")
        if not independent["potential_verification"]["passed"]:
            raise VerificationError(f"{state_id}: potential verification failed")
        reference = primary.get("reference")
        if not isinstance(reference, dict):
            raise VerificationError(f"{state_id}: missing reference result")
        optimum = float(independent["optimal_welfare"])
        estimate = float(reference["welfare"])
        if estimate > optimum + REL_TOL * max(1.0, abs(optimum)):
            raise VerificationError(f"{state_id}: reference exceeds exact optimum")
        state_rows.append(
            {
                "state_id": state_id,
                "players": players,
                "nodes": independent["nodes"],
                "feasible_assignments": independent["feasible_assignments"],
                "pure_nash_equilibria": independent["pure_nash_equilibria"],
                "optimal_welfare": optimum,
                "worst_nash_welfare": independent["worst_nash_welfare"],
                "best_nash_welfare": independent["best_nash_welfare"],
                "exact_poa": independent["exact_poa"],
                "relative_welfare_gap": independent["relative_welfare_gap"],
                "ready_order_welfare": independent["ready_order"]["welfare"],
                "ready_order_is_pure_nash": independent["ready_order"]["is_pure_nash"],
                "ready_order_termination": independent["ready_order"]["termination"],
                "ready_order_inner_stable": independent["ready_order"]["inner_stable"],
                "ready_order_inner_limit_hit": independent["ready_order"][
                    "inner_limit_hit"
                ],
                "ready_order_oscillated": independent["ready_order"]["oscillated"],
                "ready_order_inner_rounds": independent["ready_order"]["inner_rounds"],
                "ready_order_assignment_moves": independent["ready_order"][
                    "assignment_moves"
                ],
                "reference_welfare": estimate,
                "reference_absolute_shortfall": reference["absolute_shortfall"],
                "reference_normalized_shortfall": reference["normalized_shortfall"],
                "reference_exact_hit": reference["exact_hit"],
                "reference_runtime_ns": reference["runtime_ns"],
                "exact_enumeration_runtime_ns": primary["exact_enumeration_runtime_ns"],
                "potential_strict_improvements": independent["potential_verification"][
                    "strict_improvements"
                ],
                "potential_max_identity_residual": independent[
                    "potential_verification"
                ]["max_identity_residual"],
            }
        )
    if any(count != states_per_size for count in coverage.values()):
        raise VerificationError(f"incorrect player-count coverage: {coverage}")

    shortfalls = [
        float(row["reference_normalized_shortfall"])
        for row in state_rows
        if row["reference_normalized_shortfall"] is not None
    ]
    median_shortfall = statistics.median(shortfalls)
    p95_shortfall = _quantile(shortfalls, 0.95)
    if median_shortfall <= 0.05 and p95_shortfall <= 0.20:
        quality_label = "accurate_small_state_reference"
    elif median_shortfall <= 0.10 and p95_shortfall <= 0.35:
        quality_label = "usable_but_loose_small_state_reference"
    else:
        quality_label = "weak_small_state_reference"
    poa_values = [
        float(row["exact_poa"]) for row in state_rows if row["exact_poa"] is not None
    ]
    summary = {
        "schema": "NSE_EXACT_SMALL_SUMMARY_V2",
        "state_count": len(state_rows),
        "coverage_by_players": {str(key): value for key, value in coverage.items()},
        "all_states_have_pure_nash": all(
            int(row["pure_nash_equilibria"]) > 0 for row in state_rows
        ),
        "all_potential_checks_pass": True,
        "ready_order_pure_nash_fraction": sum(
            bool(row["ready_order_is_pure_nash"]) for row in state_rows
        )
        / len(state_rows),
        "ready_order_termination_counts": dict(
            sorted(
                collections.Counter(
                    str(row["ready_order_termination"]) for row in state_rows
                ).items()
            )
        ),
        "reference": {
            "median_normalized_shortfall": median_shortfall,
            "p95_normalized_shortfall": p95_shortfall,
            "exact_hit_count": sum(
                bool(row["reference_exact_hit"]) for row in state_rows
            ),
            "quality_label": quality_label,
        },
        "exact_poa": {
            "applicable_count": len(poa_values),
            "median": statistics.median(poa_values) if poa_values else None,
            "p95": _quantile(poa_values, 0.95) if poa_values else None,
            "minimum": min(poa_values) if poa_values else None,
            "maximum": max(poa_values) if poa_values else None,
        },
        "timing_ns": {
            "exact_total": sum(
                int(row["exact_enumeration_runtime_ns"]) for row in state_rows
            ),
            "reference_total": sum(
                int(row["reference_runtime_ns"]) for row in state_rows
            ),
        },
    }

    output_dir.mkdir(parents=True, exist_ok=True)
    csv_path = output_dir / "exact_state_rows_v2.csv"
    summary_path = output_dir / "exact_summary_v2.json"
    verification_path = output_dir / "exact_verification_v2.json"
    for path in (csv_path, summary_path, verification_path):
        if path.exists():
            raise VerificationError(f"refusing to overwrite {path}")
    fieldnames = list(state_rows[0])
    lines: list[str] = []
    import io

    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fieldnames, lineterminator="\n")
    writer.writeheader()
    writer.writerows(state_rows)
    _atomic_text(csv_path, buffer.getvalue())
    _atomic_text(
        summary_path,
        json.dumps(
            summary, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True
        )
        + "\n",
    )
    verification = {
        "schema": "NSE_EXACT_SMALL_VERIFICATION_V2",
        "status": "pass",
        "independent_solver": True,
        "primary_solver_imported": False,
        "verified_state_count": len(state_rows),
        "hard_gates": {
            "coverage": True,
            "independent_exact_match": True,
            "pure_nash_exists": True,
            "potential_identity": True,
            "reference_upper_bound": True,
            "finite_results": True,
        },
        "artifact_sha256": {
            games_path.name: _sha256(games_path),
            results_path.name: _sha256(results_path),
            csv_path.name: _sha256(csv_path),
            summary_path.name: _sha256(summary_path),
        },
        "source_sha256": {
            "primary": None if primary_source is None else _sha256(primary_source),
            "verifier": None if verifier_source is None else _sha256(verifier_source),
        },
    }
    _atomic_text(
        verification_path,
        json.dumps(
            verification, ensure_ascii=False, allow_nan=False, indent=2, sort_keys=True
        )
        + "\n",
    )
    return {"summary": summary, "verification": verification, "rows": state_rows}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("games", type=Path)
    parser.add_argument("results", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--states-per-size", type=int, default=100)
    parser.add_argument("--primary-source", type=Path)
    parser.add_argument("--verifier-source", type=Path)
    args = parser.parse_args(argv)
    try:
        verify_files(
            args.games,
            args.results,
            args.output_dir,
            args.states_per_size,
            args.primary_source,
            args.verifier_source,
        )
    except (OSError, json.JSONDecodeError, VerificationError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
