"""Preregistered G3 diagnosis over retained G1/G2 run artifacts.

This module never mutates run directories and never drops a row based on a
scientific metric.  It emits one run-level table plus a deterministic JSON
report covering every diagnostic named in the G3 preregistration.
"""

from __future__ import annotations

import argparse
import csv
import gzip
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Sequence


FORMAL_METHODS = ("sche_nash", "sche_FaaSRank")
STAGES = ("schedule_wait_ms", "cold_start_wait_ms", "data_wait_ms", "execution_ms")
DIAGNOSTICS = (
    "waiting_share",
    "candidates_per_player",
    "selected_starting_share",
    "warm_bypass_share",
    "placement_dispersion",
    "co_location_conflict_ratio",
    "cross_node_placement_ratio",
    "assignment_moves_per_player",
    "outer_feedback_active_share",
    "mean_price_spread",
    "queue_area_per_arrival",
    "node_memory_utilization_mean",
)


def _finite(value: Any) -> float | None:
    try:
        result = float(value)
    except (TypeError, ValueError):
        return None
    return result if math.isfinite(result) else None


def _mean(values: Iterable[Any]) -> float | None:
    finite = [value for item in values if (value := _finite(item)) is not None]
    return statistics.fmean(finite) if finite else None


def _nested(data: Mapping[str, Any], *keys: str, default: Any = None) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, Mapping) or key not in current:
            return default
        current = current[key]
    return current


def _json_lines(path: Path) -> Iterator[dict[str, Any]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                yield json.loads(line)


def _one(directory: Path, pattern: str) -> Path:
    matches = sorted(directory.rglob(pattern))
    if len(matches) != 1:
        raise ValueError(f"expected exactly one {pattern} below {directory}, found {len(matches)}")
    return matches[0]


def stage_breakdown(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    """Reproduce the simulator's completed-function stage boundaries."""

    totals = {stage: 0.0 for stage in STAGES}
    function_count = 0
    cold_events = 0
    request_count = 0
    for request in events:
        request_count += 1
        for function in request.get("functions", []):
            ready = int(function["ready_schedule_frame"])
            scheduled = int(function["scheduled_frame"])
            function_done = int(function["function_done_frame"])
            schedule_boundary = max(ready, scheduled)
            cold_raw = function.get("cold_start_done_frame")
            if cold_raw is None:
                cold_done = schedule_boundary
            else:
                cold_events += 1
                cold_done = max(int(cold_raw), schedule_boundary)
            data_raw = function.get("data_received_frame")
            data_done = cold_done if data_raw is None else max(int(data_raw), cold_done)

            values = {
                # A placement may be made before its DAG parents finish.  The
                # simulator therefore clamps scheduling wait at zero rather
                # than treating an early binding as negative latency.
                "schedule_wait_ms": max(scheduled - ready, 0),
                "cold_start_wait_ms": cold_done - schedule_boundary,
                "data_wait_ms": data_done - cold_done,
                "execution_ms": function_done - data_done,
            }
            if any(value < 0 for value in values.values()):
                raise ValueError(f"negative stage duration in request {request.get('request_id')}")
            for key, value in values.items():
                totals[key] += value
            function_count += 1

    result: dict[str, Any] = {
        "completed_request_events": request_count,
        "completed_function_events": function_count,
        "cold_start_events": cold_events,
        "cold_start_event_share": cold_events / function_count if function_count else None,
    }
    for stage in STAGES:
        result[stage] = totals[stage] / function_count if function_count else None
    return result


def _weighted_mean(total: float, weight: int) -> float | None:
    return total / weight if weight else None


def nash_diagnostics(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    totals: defaultdict[str, float] = defaultdict(float)
    active_windows = 0
    no_player_windows = 0
    inner_limit_windows = 0
    outer_limit_windows = 0
    oscillation_windows = 0
    stable_windows = 0
    feedback_windows = 0
    reference_below_current_windows = 0
    finite_gap_windows = 0

    for event in events:
        if event.get("kind") != "window":
            continue
        decision = event.get("decision", {})
        solver = event.get("solver", {})
        pricing = event.get("pricing", {})
        cluster = event.get("cluster", {})
        network = event.get("network", {})
        social = event.get("social", {})
        assigned = int(decision.get("assigned_players", 0))
        pending = int(decision.get("pending_request_function_pairs", 0))
        totals["pending"] += pending
        totals["waiting"] += int(decision.get("waiting_for_candidate_nodes", 0))
        if assigned <= 0:
            no_player_windows += 1
            continue

        active_windows += 1
        totals["assigned"] += assigned
        totals["candidate_evaluations"] += int(decision.get("candidate_evaluations", 0))
        totals["selected_starting"] += int(
            decision.get("selected_starting_container_players", 0)
        )
        totals["warm_available"] += int(decision.get("running_warm_available_players", 0))
        totals["warm_bypassed"] += int(decision.get("running_warm_bypassed_players", 0))
        totals["assigned_node_count"] += int(decision.get("assigned_node_count", 0))
        totals["dispersion_weighted"] += assigned * float(
            decision.get("placement_dispersion_normalized", 0.0)
        )
        totals["conflict_weighted"] += assigned * float(
            decision.get("co_location_conflict_pair_ratio_proxy", 0.0)
        )
        totals["cross_node_weighted"] += assigned * float(
            network.get("cross_node_placement_ratio", 0.0)
        )
        totals["moves"] += int(solver.get("assignment_moves", 0))
        totals["inner_rounds"] += int(solver.get("inner_rounds", 0))
        totals["outer_rounds"] += int(solver.get("outer_rounds", 0))
        totals["price_spread_weighted"] += assigned * (
            float(pricing.get("price_max", 0.0)) - float(pricing.get("price_min", 0.0))
        )
        totals["pressure_weighted"] += assigned * float(cluster.get("pressure_mean", 0.0))
        totals["queue_pressure_weighted"] += assigned * float(
            cluster.get("queue_pressure_ratio_max", 0.0)
        )

        if int(pricing.get("adjustments", 0)) > 0:
            feedback_windows += 1
        if bool(solver.get("inner_limit_hit")):
            inner_limit_windows += 1
        if bool(solver.get("outer_limit_hit")):
            outer_limit_windows += 1
        if int(solver.get("oscillations", 0)) > 0:
            oscillation_windows += 1
        if bool(solver.get("inner_stable")):
            stable_windows += 1
        if bool(social.get("reference_below_current")):
            reference_below_current_windows += 1
        gap = _finite(social.get("empirical_gap"))
        if gap is not None:
            totals["empirical_gap"] += gap
            finite_gap_windows += 1

        components = social.get("baseline_utility_components", {})
        for component in ("baseline_reward", "cost", "quality", "externality", "contribution"):
            totals[f"welfare_{component}"] += float(components.get(component, 0.0))
        totals["welfare"] += float(social.get("final_assignment_baseline_welfare", 0.0))

    assigned = int(totals["assigned"])
    pending = int(totals["pending"])
    warm_available = int(totals["warm_available"])
    result = {
        "active_windows": active_windows,
        "no_player_windows": no_player_windows,
        "assigned_players": assigned,
        "waiting_share": totals["waiting"] / pending if pending else 0.0,
        "candidates_per_player": totals["candidate_evaluations"] / assigned if assigned else None,
        "selected_starting_share": totals["selected_starting"] / assigned if assigned else None,
        "warm_available_share": warm_available / assigned if assigned else None,
        "warm_bypass_share": totals["warm_bypassed"] / warm_available if warm_available else 0.0,
        "mean_assigned_node_count": _weighted_mean(totals["assigned_node_count"], active_windows),
        "placement_dispersion": _weighted_mean(totals["dispersion_weighted"], assigned),
        "co_location_conflict_ratio": _weighted_mean(totals["conflict_weighted"], assigned),
        "cross_node_placement_ratio": _weighted_mean(totals["cross_node_weighted"], assigned),
        "assignment_moves_per_player": _weighted_mean(totals["moves"], assigned),
        "inner_rounds_per_active_window": _weighted_mean(totals["inner_rounds"], active_windows),
        "outer_rounds_per_active_window": _weighted_mean(totals["outer_rounds"], active_windows),
        "outer_feedback_active_share": feedback_windows / active_windows if active_windows else 0.0,
        "mean_price_spread": _weighted_mean(totals["price_spread_weighted"], assigned),
        "mean_pressure": _weighted_mean(totals["pressure_weighted"], assigned),
        "mean_queue_pressure_ratio_max": _weighted_mean(
            totals["queue_pressure_weighted"], assigned
        ),
        "inner_limit_active_share": inner_limit_windows / active_windows if active_windows else 0.0,
        "outer_limit_active_share": outer_limit_windows / active_windows if active_windows else 0.0,
        "oscillation_active_share": oscillation_windows / active_windows if active_windows else 0.0,
        "inner_stable_active_share": stable_windows / active_windows if active_windows else 0.0,
        "reference_below_current_active_share": (
            reference_below_current_windows / active_windows if active_windows else 0.0
        ),
        "mean_empirical_gap": totals["empirical_gap"] / finite_gap_windows
        if finite_gap_windows
        else None,
    }
    for component in ("baseline_reward", "cost", "quality", "externality", "contribution"):
        result[f"welfare_{component}_per_player"] = _weighted_mean(
            totals[f"welfare_{component}"], assigned
        )
    result["paper_welfare_per_player"] = _weighted_mean(totals["welfare"], assigned)
    return result


def welfare_diagnostics(events: Iterable[Mapping[str, Any]]) -> dict[str, Any]:
    assigned = 0
    active_windows = 0
    incomplete_windows = 0
    totals: defaultdict[str, float] = defaultdict(float)
    for event in events:
        if event.get("kind") != "welfare_window":
            continue
        decision = event.get("decision", {})
        count = int(decision.get("assigned_players", 0))
        if count <= 0:
            continue
        active_windows += 1
        assigned += count
        if not bool(decision.get("complete_assignment")):
            incomplete_windows += 1
        social = event.get("social", {})
        totals["welfare"] += float(social.get("final_assignment_baseline_welfare", 0.0))
        components = social.get("utility_components", {})
        for component in ("baseline_reward", "cost", "quality", "externality", "contribution"):
            totals[component] += float(components.get(component, 0.0))
    result = {
        "active_windows": active_windows,
        "assigned_players": assigned,
        "incomplete_active_share": incomplete_windows / active_windows if active_windows else 0.0,
        "paper_welfare_per_player": _weighted_mean(totals["welfare"], assigned),
    }
    for component in ("baseline_reward", "cost", "quality", "externality", "contribution"):
        result[f"welfare_{component}_per_player"] = _weighted_mean(totals[component], assigned)
    return result


def _rank(values: Sequence[float]) -> list[float]:
    ordered = sorted(enumerate(values), key=lambda pair: pair[1])
    ranks = [0.0] * len(values)
    start = 0
    while start < len(ordered):
        end = start + 1
        while end < len(ordered) and ordered[end][1] == ordered[start][1]:
            end += 1
        average_rank = (start + 1 + end) / 2.0
        for index in range(start, end):
            ranks[ordered[index][0]] = average_rank
        start = end
    return ranks


def spearman(first: Sequence[Any], second: Sequence[Any]) -> tuple[float | None, int]:
    pairs = [
        (x, y)
        for left, right in zip(first, second)
        if (x := _finite(left)) is not None and (y := _finite(right)) is not None
    ]
    if len(pairs) < 3:
        return None, len(pairs)
    x_rank = _rank([pair[0] for pair in pairs])
    y_rank = _rank([pair[1] for pair in pairs])
    x_mean = statistics.fmean(x_rank)
    y_mean = statistics.fmean(y_rank)
    numerator = sum((x - x_mean) * (y - y_mean) for x, y in zip(x_rank, y_rank))
    first_ss = sum((x - x_mean) ** 2 for x in x_rank)
    second_ss = sum((y - y_mean) ** 2 for y in y_rank)
    denominator = math.sqrt(first_ss * second_ss)
    return (numerator / denominator if denominator else None), len(pairs)


def load_run(config_path: Path, source_bank: str) -> dict[str, Any]:
    directory = config_path.parent
    config = json.loads(config_path.read_text(encoding="utf-8"))
    summary = json.loads(_one(directory, "summary.json").read_text(encoding="utf-8"))
    method = str(config["method"])
    simulator = config.get("simulator_experiment", {})
    operational_refinement = _nested(simulator, "nash", "operational_refinement")
    if operational_refinement is None:
        operational_refinement = config.get("environment", {}).get("NASH_OPERATIONAL_REFINEMENT")
    if method != "sche_nash":
        operational_refinement = "baseline"

    throughput = _finite(
        _nested(summary, "fixed_observation_window", "throughput_requests_per_second")
    )
    throughput = throughput / 1000.0 if throughput is not None else None
    latency = _finite(_nested(summary, "drained_arrival_cohort", "latency_ms", "mean"))
    cost = _finite(summary.get("simulator_internal_cost_per_completed_request"))
    qpr = (
        throughput / (cost * latency)
        if throughput is not None and cost and latency and cost > 0.0 and latency > 0.0
        else None
    )
    arrivals = int(_nested(summary, "fixed_observation_window", "arrivals", default=0))

    request_path = _one(directory, "requests.jsonl.gz")
    row: dict[str, Any] = {
        "source_bank": source_bank,
        "run_id": config["run_id"],
        "method": method,
        "operational_refinement": operational_refinement,
        "seed": str(config["seed"]),
        "topology": str(_nested(config, "workload", "topology")),
        "load": str(_nested(config, "workload", "request_freq")),
        "throughput": throughput,
        "completion_ratio": _finite(
            _nested(summary, "fixed_observation_window", "completion_ratio")
        ),
        "latency_mean_ms": latency,
        "latency_p95_ms": _finite(
            _nested(summary, "drained_arrival_cohort", "latency_ms", "p95")
        ),
        "latency_p99_ms": _finite(
            _nested(summary, "drained_arrival_cohort", "latency_ms", "p99")
        ),
        "cost": cost,
        "qpr": qpr,
        "queue_area_per_arrival": (
            float(summary.get("queue_area_request_frames", 0)) / arrivals if arrivals else None
        ),
        "queue_peak": int(summary.get("queue_peak", 0)),
        "node_cpu_utilization_mean": _finite(summary.get("node_cpu_utilization_mean")),
        "node_memory_utilization_mean": _finite(summary.get("node_memory_utilization_mean")),
        "qc_run_complete": bool(summary.get("run_complete")),
        "config_path": str(config_path),
    }
    row.update(stage_breakdown(_json_lines(request_path)))

    reviewer = request_path.parent
    if method == "sche_nash":
        metrics = _one(reviewer, "nash_metrics.jsonl.gz")
        row.update(nash_diagnostics(_json_lines(metrics)))
    else:
        metrics = _one(reviewer, "welfare_metrics.jsonl.gz")
        row.update(welfare_diagnostics(_json_lines(metrics)))
    return row


def scan_online(root: Path, source_bank: str) -> list[dict[str, Any]]:
    configs = sorted((root / "online").rglob("run_config.json"))
    rows = [load_run(path, source_bank) for path in configs]
    if len({row["run_id"] for row in rows}) != len(rows):
        raise ValueError(f"duplicate run IDs below {root}")
    return rows


def _group_mean(rows: Sequence[Mapping[str, Any]], fields: Sequence[str]) -> dict[str, Any]:
    return {field: _mean(row.get(field) for row in rows) for field in fields}


def build_report(g1_rows: list[dict[str, Any]], g2_rows: list[dict[str, Any]]) -> dict[str, Any]:
    formal = [row for row in g1_rows if row["method"] in FORMAL_METHODS]
    by_seed: defaultdict[str, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in formal:
        by_seed[row["seed"]][row["method"]] = row
    incomplete_pairs = {
        seed: sorted(set(FORMAL_METHODS) - set(methods))
        for seed, methods in by_seed.items()
        if set(methods) != set(FORMAL_METHODS)
    }
    if incomplete_pairs:
        raise ValueError(f"incomplete G1 pairs: {incomplete_pairs}")

    pairs = []
    for seed in sorted(by_seed):
        nash = by_seed[seed]["sche_nash"]
        baseline = by_seed[seed]["sche_FaaSRank"]
        pair: dict[str, Any] = {"seed": seed}
        for field in (
            "throughput",
            "completion_ratio",
            "latency_mean_ms",
            "latency_p95_ms",
            "latency_p99_ms",
            "cost",
            "qpr",
            *STAGES,
            "cold_start_event_share",
        ):
            left = _finite(nash.get(field))
            right = _finite(baseline.get(field))
            pair[f"nash_{field}"] = left
            pair[f"faasrank_{field}"] = right
            pair[f"delta_{field}"] = left - right if left is not None and right is not None else None
        for diagnostic in DIAGNOSTICS:
            pair[diagnostic] = nash.get(diagnostic)
        pairs.append(pair)

    outcome_gaps = ("delta_throughput", "delta_qpr")
    correlations = []
    for diagnostic in DIAGNOSTICS:
        for outcome in outcome_gaps:
            rho, count = spearman(
                [pair.get(diagnostic) for pair in pairs],
                [pair.get(outcome) for pair in pairs],
            )
            correlations.append(
                {"diagnostic": diagnostic, "outcome_gap": outcome, "spearman_rho": rho, "n": count}
            )

    stage_differences = {}
    for stage in STAGES:
        differences = [_finite(pair[f"delta_{stage}"]) for pair in pairs]
        finite = [value for value in differences if value is not None]
        stage_differences[stage] = {
            "mean_nash_minus_faasrank_ms": statistics.fmean(finite) if finite else None,
            "positive_seed_count": sum(value > 0.0 for value in finite),
            "negative_seed_count": sum(value < 0.0 for value in finite),
            "tie_seed_count": sum(value == 0.0 for value in finite),
            "n": len(finite),
        }
    positive_stages = [
        (stage, data["mean_nash_minus_faasrank_ms"])
        for stage, data in stage_differences.items()
        if data["mean_nash_minus_faasrank_ms"] is not None
        and data["mean_nash_minus_faasrank_ms"] > 0.0
    ]
    primary_stage = max(positive_stages, key=lambda item: item[1])[0] if positive_stages else None

    formal_fields = (
        "throughput",
        "completion_ratio",
        "latency_mean_ms",
        "latency_p95_ms",
        "latency_p99_ms",
        "cost",
        "qpr",
        *STAGES,
        "cold_start_event_share",
        "paper_welfare_per_player",
        "welfare_cost_per_player",
        "welfare_quality_per_player",
        "welfare_externality_per_player",
        "welfare_contribution_per_player",
    )
    formal_means = {
        method: _group_mean([row for row in formal if row["method"] == method], formal_fields)
        for method in FORMAL_METHODS
    }

    g2_nash = [row for row in g2_rows if row["method"] == "sche_nash"]
    grouped: defaultdict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in g2_nash:
        grouped[(row["operational_refinement"], row["topology"], row["load"])].append(row)
    g2_fields = (
        "throughput",
        "qpr",
        "latency_mean_ms",
        "cost",
        *DIAGNOSTICS,
        "inner_limit_active_share",
        "outer_limit_active_share",
        "oscillation_active_share",
        "inner_stable_active_share",
    )
    g2_cell_means = []
    for (candidate, topology, load), rows in sorted(grouped.items()):
        item = {
            "operational_refinement": candidate,
            "topology": topology,
            "load": load,
            "seed_count": len(rows),
        }
        item.update(_group_mean(rows, g2_fields))
        g2_cell_means.append(item)

    return {
        "schema": "NSE_G3_EXISTING_LOG_DIAGNOSIS_V1",
        "decision_boundary": {
            "candidate_effect_estimation": False,
            "d71_authorized": False,
            "homogeneous_middle_formal_authorized": False,
            "all_predeclared_correlations_reported": True,
        },
        "input_counts": {
            "g1_online_runs": len(g1_rows),
            "g1_formal_pair_runs": len(formal),
            "g1_pair_count": len(pairs),
            "g2_online_runs": len(g2_rows),
            "g2_nash_runs": len(g2_nash),
        },
        "formal_method_means": formal_means,
        "stage_differences": stage_differences,
        "primary_positive_stage": primary_stage,
        "formal_pairs": pairs,
        "predeclared_correlations": correlations,
        "g2_cell_means": g2_cell_means,
        "all_runs": g1_rows + g2_rows,
    }


def write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    fields = sorted({key for row in rows for key in row if not isinstance(row[key], (dict, list))})
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fields})


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--g1-root", type=Path, required=True)
    parser.add_argument("--g2-root", type=Path, required=True)
    parser.add_argument("--output-json", type=Path, required=True)
    parser.add_argument("--output-csv", type=Path, required=True)
    args = parser.parse_args(argv)

    g1_rows = scan_online(args.g1_root.resolve(), "G1_Q61_Q80")
    g2_rows = scan_online(args.g2_root.resolve(), "G2_D66_D70")
    report = build_report(g1_rows, g2_rows)
    args.output_json.parent.mkdir(parents=True, exist_ok=True)
    args.output_json.write_text(
        json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    write_csv(args.output_csv, report["all_runs"])
    print(json.dumps({key: report[key] for key in ("input_counts", "primary_positive_stage")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
