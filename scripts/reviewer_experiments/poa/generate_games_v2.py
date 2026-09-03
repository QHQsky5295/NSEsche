#!/usr/bin/env python3
"""Generate the preregistered P1-B exact-small game population.

The generator is intentionally independent of simulator runtime state.  Every
quantity is a deterministic function of ``(population_seed, player_count,
state_index)`` and
the output contains no legacy ``existing_impact`` term: Eq. (8) is evaluated
over the players in the enumerated decision window only.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import random
import tempfile
from pathlib import Path
from typing import Any


SCHEMA = "NSE_EXACT_GAME_V2"
DEFAULT_POPULATION_SEED = "NSE-P1-EXACT-V2"
PLAYER_COUNTS = (4, 6, 8)
STATES_PER_SIZE = 100
NODE_COUNT = 3


def _seed_for(population_seed: str, player_count: int, local_index: int) -> int:
    digest = hashlib.sha256(
        f"{population_seed}|{player_count}|{local_index}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest, "big", signed=False)


def _round(value: float) -> float:
    return round(float(value), 12)


def make_game(
    player_count: int, local_index: int, population_seed: str
) -> dict[str, Any]:
    if player_count not in PLAYER_COUNTS:
        raise ValueError(f"unsupported player count: {player_count}")
    if not 0 <= local_index < STATES_PER_SIZE:
        raise ValueError(f"local index must be in [0, {STATES_PER_SIZE})")

    state_id = f"p{player_count:02d}-s{local_index:03d}"
    rng = random.Random(_seed_for(population_seed, player_count, local_index))
    quality_weight = 0.5 if local_index < 50 else 0.6

    function_count = max(2, player_count // 2)
    function_ids = list(range(function_count))
    profiles: list[dict[str, Any]] = []
    for function_id in range(function_count):
        cpu = rng.uniform(0.05, 1.00)
        memory = rng.uniform(0.05, 1.00)
        dag_size = rng.randint(2, 10)
        h_ri = 2.0 * math.sqrt(cpu * memory) / (cpu + memory)
        h_fc = math.tanh(math.log(dag_size) / 1.5)
        h_nd = math.sqrt(h_ri * h_fc)
        h_pi = ((31.0 * cpu + 37.0 * memory) % 100.0) / 100.0
        profiles.append(
            {
                "function_id": function_id,
                "normalized_cpu": _round(cpu),
                "normalized_memory": _round(memory),
                "dag_nodes": dag_size,
                "resource_intensity": _round(h_ri),
                "function_complexity": _round(h_fc),
                "network_dependency": _round(h_nd),
                "differentiation": _round(h_pi),
                "required_container_memory": _round(rng.uniform(100.0, 500.0)),
            }
        )

    nodes: list[dict[str, Any]] = []
    for node_id in range(NODE_COUNT):
        pressure = rng.uniform(0.05, 0.95)
        utilization = rng.uniform(0.05, 0.90)
        congestion_premium = rng.uniform(0.0, 0.5) * utilization
        nodes.append(
            {
                "node_id": node_id,
                "pressure": _round(pressure),
                "utilization": _round(utilization),
                "congestion_premium": _round(congestion_premium),
                "price": _round(0.3 * (1.0 + pressure) * (1.0 + congestion_premium)),
                "available_container_memory": 5000.0,
                "existing_functions": list(function_ids),
            }
        )

    players: list[dict[str, Any]] = []
    for player_id in range(player_count):
        profile = profiles[player_id % function_count]
        players.append(
            {
                "player_id": f"r{local_index:03d}-p{player_id:02d}",
                **profile,
                "quality_weight": quality_weight,
                "candidates": list(range(NODE_COUNT)),
            }
        )

    return {
        "schema": SCHEMA,
        "state_id": state_id,
        "population_seed": population_seed,
        "local_index": local_index,
        "construction": {
            "kind": "pre_registered_small_exact_game_v2",
            "placement_only_common_hpa": True,
            "current_window_externality_only": True,
            "formula_constants": {
                "dag_complexity_normalizer": 1.5,
                "differentiation_p1": 31.0,
                "differentiation_p2": 37.0,
                "base_node_price": 0.3,
            },
        },
        "settings": {
            "quality_weight": quality_weight,
            "base_utility": 10.0,
            "contribution_coefficient": 1.0,
            "externality_enabled": True,
            "contribution_enabled": True,
            "epsilon": 1.0e-6,
            "inner_round_cap": 4,
        },
        "nodes": nodes,
        "players": players,
    }


def generate_population(
    population_seed: str = DEFAULT_POPULATION_SEED,
    states_per_size: int = STATES_PER_SIZE,
) -> list[dict[str, Any]]:
    if states_per_size < 1 or states_per_size > STATES_PER_SIZE:
        raise ValueError(f"states_per_size must be in [1, {STATES_PER_SIZE}]")
    return [
        make_game(player_count, local_index, population_seed)
        for player_count in PLAYER_COUNTS
        for local_index in range(states_per_size)
    ]


def _atomic_write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise FileExistsError(f"refusing to overwrite existing output: {path}")
    fd, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            for row in rows:
                json.dump(
                    row,
                    handle,
                    ensure_ascii=False,
                    allow_nan=False,
                    sort_keys=True,
                )
                handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
    except BaseException:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--population-seed", default=DEFAULT_POPULATION_SEED)
    parser.add_argument("--states-per-size", type=int, default=STATES_PER_SIZE)
    args = parser.parse_args()

    games = generate_population(args.population_seed, args.states_per_size)
    _atomic_write_jsonl(args.output, games)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
