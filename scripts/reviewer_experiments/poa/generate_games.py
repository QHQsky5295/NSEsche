from __future__ import annotations

import argparse
import hashlib
import json
import math
import random
from pathlib import Path

from .exact_poa import SCHEMA


def _rng(seed: str, players: int, state_index: int) -> random.Random:
    digest = hashlib.sha256(f"{seed}|{players}|{state_index}".encode("utf-8")).digest()
    return random.Random(int.from_bytes(digest, "big"))


def _profile(rng: random.Random, function_id: int) -> dict[str, float | int]:
    cpu = rng.uniform(0.05, 1.0)
    memory = rng.uniform(0.05, 1.0)
    resource_intensity = 2.0 * math.sqrt(cpu * memory) / (cpu + memory)
    dag_nodes = rng.randint(2, 10)
    function_complexity = math.tanh(math.log(dag_nodes) / 1.5)
    network_dependency = math.sqrt(resource_intensity * function_complexity)
    differentiation = ((cpu * 31.0 + memory * 37.0) % 100.0) / 100.0
    return {
        "function_id": function_id,
        "resource_intensity": resource_intensity,
        "function_complexity": function_complexity,
        "network_dependency": network_dependency,
        "differentiation": differentiation,
        "required_container_memory": rng.uniform(100.0, 500.0),
    }


def generate_game(seed: str, player_count: int, state_index: int) -> dict:
    rng = _rng(seed, player_count, state_index)
    function_count = max(2, player_count // 2)
    profiles = [_profile(rng, function_id) for function_id in range(function_count)]
    function_ids = list(range(function_count))
    nodes = []
    for node_id in range(3):
        pressure = rng.uniform(0.05, 0.95)
        utilization = rng.uniform(0.05, 0.90)
        congestion_premium = rng.uniform(0.0, 0.5) * utilization
        nodes.append(
            {
                "node_id": node_id,
                "pressure": pressure,
                "utilization": utilization,
                "price": 0.3 * (1.0 + pressure) * (1.0 + congestion_premium),
                "existing_impact": rng.uniform(0.0, 0.5),
                "available_container_memory": 5000.0,
                # Common HPA has already provisioned these containers; the
                # exact game isolates placement choices, as in the main study.
                "existing_functions": function_ids,
            }
        )
    weights = (0.9, 0.6, 0.2)
    players = []
    for player_index in range(player_count):
        function_id = player_index % function_count
        profile = profiles[function_id]
        players.append(
            {
                "player_id": f"r{state_index:03d}-p{player_index:02d}",
                **profile,
                "candidates": [0, 1, 2],
                "quality_weight": weights[player_index % len(weights)],
            }
        )
    return {
        "schema": SCHEMA,
        "state_id": f"{seed}.p{player_count}.s{state_index:03d}",
        "construction": {
            "kind": "pre_registered_small_exact_game",
            "seed": seed,
            "state_index": state_index,
            "placement_only_common_hpa": True,
            "formula_constants": {
                "dag_complexity_normalizer": 1.5,
                "differentiation_p1": 31.0,
                "differentiation_p2": 37.0,
                "base_node_price": 0.3,
            },
        },
        "nodes": nodes,
        "players": players,
        "settings": {
            "base_utility": 10.0,
            "contribution_coefficient": 1.0,
            "externality_enabled": True,
            "contribution_enabled": True,
        },
    }


def generate_file(output: Path, seed: str, states_per_size: int) -> None:
    partial = output.with_suffix(output.suffix + ".partial")
    output.parent.mkdir(parents=True, exist_ok=True)
    if output.exists() or partial.exists():
        raise ValueError(f"refusing to overwrite {output}")
    with partial.open("x", encoding="utf-8", newline="\n") as handle:
        for player_count in (4, 6, 8):
            for state_index in range(states_per_size):
                json.dump(
                    generate_game(seed, player_count, state_index),
                    handle,
                    ensure_ascii=False,
                    allow_nan=False,
                )
                handle.write("\n")
        handle.flush()
    partial.replace(output)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Generate the frozen 3-node exact-PoA games"
    )
    parser.add_argument("output", type=Path)
    parser.add_argument("--seed", default="NSE-EXACT-POA-V1")
    parser.add_argument("--states-per-size", type=int, default=100)
    args = parser.parse_args(argv)
    if args.states_per_size <= 0:
        parser.error("--states-per-size must be positive")
    try:
        generate_file(args.output, args.seed, args.states_per_size)
    except (OSError, ValueError) as error:
        parser.error(str(error))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
