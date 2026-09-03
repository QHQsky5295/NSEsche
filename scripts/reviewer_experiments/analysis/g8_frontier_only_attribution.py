"""Frozen read-only attribution for the possible G8 frontier-only candidate."""

from __future__ import annotations

import argparse
import csv
import json
import math
from collections import Counter
from pathlib import Path
from statistics import fmean, stdev
from typing import Any, Mapping, Sequence

from scipy import stats as scipy_stats

from ..protocol.g7_frontier_warm import _activation_metrics
from ..protocol.m1_qualification import _screen_metrics
from ..protocol.schema import ProtocolValidationError, load_and_validate_manifest
from ..protocol.util import file_hash, object_hash, read_json, utc_now
from .formal_inputs import validate_canonical_run
from .observability import RunArtifacts, load_run_artifacts


SCHEMA_VERSION = "NSE_G8_FRONTIER_ONLY_ATTRIBUTION_V1"
OUTPUT_NAMES = (
    "g8_frontier_only_attribution.json",
    "g8_frontier_only_runs.csv",
    "g8_frontier_only_pairs.csv",
)
INPUT_PRODUCTS: dict[str, dict[str, Any]] = {
    "g2_manifest": {
        "path": "runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.ready.json",
        "kind": "manifest",
        "document_sha256": "8173ab619744d7794106489c67e5ef017160c90e5bdcc4dd597be075f9bcd3f4",
        "file_sha256": "d49bc3865244f9b231b7dba312819f4c715059ca4ce7d7bb97b185add7481f18",
        "canonical_root": "runs/tscv1_g2_init_d66_d70_3ae7792_20260903/online/canonical",
    },
    "g2_analysis": {
        "path": "runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.analysis.json",
        "kind": "report",
        "document_sha256": "e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79",
        "file_sha256": "414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db",
        "status": "complete_g2_development_failed_baseline_gate",
        "run_count": 135,
    },
    "g3_manifest": {
        "path": "runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.ready.json",
        "kind": "manifest",
        "document_sha256": "c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657",
        "file_sha256": "a54f0fbbbe02d0b1559b1b094eeefe77f1860b522a6c26b9c69b03262ced02f4",
        "canonical_root": "runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/online/canonical",
    },
    "g3_selection": {
        "path": "runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json",
        "kind": "report",
        "document_sha256": "4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34",
        "file_sha256": "22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7",
        "status": "complete_g3_e0_development_gate_failed",
        "run_count": 135,
    },
    "g6_manifest": {
        "path": "runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904/g6.ready.json",
        "kind": "manifest",
        "document_sha256": "d5b7a2143688f618a9ef286466d0c7c7a6b92687bb5bf97dab6e28ce9ca4c1f3",
        "file_sha256": "69f34423d632fbdb1de286f9dc0ca27c1e3da24fbb629b4dc7e52614b2b96965",
        "canonical_root": "runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904/online/canonical",
    },
    "g6_selection": {
        "path": "runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904/g6.selection.json",
        "kind": "report",
        "document_sha256": "842a20e410c1f1a188b76d42b4398251171574241d39121b0e33630371d04592",
        "file_sha256": "6fa6446ef8a84432dee6607c8a58b3cbd02548e67aa0f22dbbbb787c2e60d3f6",
        "status": "complete_g6_development_gate_failed",
        "candidate_run_count": 5,
        "source_control_run_count": 50,
    },
    "g7_manifest": {
        "path": "runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/g7.ready.json",
        "kind": "manifest",
        "document_sha256": "37f26c48f6a78779d62d42acbedd440774d716ffc6818623a196925d97b6f4ae",
        "file_sha256": "4e285e025a1612480177ad1b2bcab52f4a0fe28886abca2186441cf75bd39567",
        "canonical_root": "runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/online/canonical",
    },
    "g7_selection": {
        "path": "runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/g7.selection.json",
        "kind": "report",
        "document_sha256": "549ce335172d0cbeae90e54951b772c097a5cc76bc02cdab56d3d47f7019a3ca",
        "file_sha256": "6e465ad1e7d3156b092d83f547cefd15f4959565bd7d3f74c99f5b864ae58806",
        "status": "complete_g7_development_gate_failed",
        "candidate_run_count": 5,
        "source_control_run_count": 50,
    },
}
SOURCE_CONTRACT = {
    "scripts/reviewer_experiments/analysis/formal_inputs.py": "5071aba9c4ca27ea61bc4eb233628d5526f30cf4e9485bde4bd3531e7e975458",
    "scripts/reviewer_experiments/analysis/observability.py": "5a2e14562ea1e229b606f7d705e1a2b1216f6941a80e111de5afbb1cd39d6407",
    "scripts/reviewer_experiments/analysis/g4_hom_low_latency.py": "733105bd641a5aa7cdd5742a3dafb28db17f011313bed33724ef8d3bb99c2656",
    "scripts/reviewer_experiments/protocol/m1_qualification.py": "100abd4837cbf6320b431f03afa041375ea7907ae7257f7c819173f555781a3d",
    "scripts/reviewer_experiments/protocol/g6_lookahead.py": "12110fd82815d771be3900895ae74b30b6e20f22eb043df6e4968c68f0902d77",
    "scripts/reviewer_experiments/protocol/g7_frontier_warm.py": "3b54bb50d7f4be80cb14dc8f27831cf1fe72227e563b803d1abec8df28139d43",
}
COHORTS = {
    "g2_c0": ("g2_manifest", "ready_order", tuple(f"D{i}" for i in range(66, 71))),
    "g2_warm": (
        "g2_manifest",
        "ready_warm_init",
        tuple(f"D{i}" for i in range(66, 71)),
    ),
    "g3_c0": ("g3_manifest", "ready_order", tuple(f"D{i}" for i in range(71, 76))),
    "g6": (
        "g6_manifest",
        "lookahead_preall_sched",
        tuple(f"D{i}" for i in range(71, 76)),
    ),
    "g7": (
        "g7_manifest",
        "lookahead_frontier1_warm_init",
        tuple(f"D{i}" for i in range(71, 76)),
    ),
}
PAIR_SPECS = (
    ("g2_warm_minus_g2_c0", "g2_warm", "g2_c0"),
    ("g6_minus_g3_c0", "g6", "g3_c0"),
    ("g7_minus_g3_c0", "g7", "g3_c0"),
    ("g7_minus_g6", "g7", "g6"),
)
OUTCOME_METRICS = (
    "throughput_kreq_per_s",
    "qpr",
    "latency_ms",
    "completion_ratio",
    "cost_per_completed_request",
)
PAIR_NUMERIC_METRICS = (
    *OUTCOME_METRICS,
    "active_window_count",
    "assigned_players",
    "complete_dispatch_windows",
    "assignment_moves",
    "inner_limit_hits",
    "outer_limit_hits",
    "oscillations",
    "inner_stable_share",
    "outer_stable_share",
    "queue_parent_blocked_mean",
    "queue_resident_mean",
    "queue_runnable_mean",
    "queue_starting_resident_mean",
    "queue_data_blocked_mean",
    "initialization_running_warm_choices",
    "initialization_refined_choices",
    "initialization_lower_utility_choices",
    "selected_running_warm_share",
    "selected_starting_container_share",
    "selected_cold_or_nonrunning_share",
    "offline_reference_hit_windows",
    "unreferenced_active_window_count",
    "completed_request_count",
    "completed_function_count",
    "pre_ready_bound_share",
    "startup_overlap_ms_sum",
    "mean_startup_overlap_ms",
    "maximum_executable_frontier_hops_ahead",
    "frontier_hop_violation_count",
)


def _number(value: Any, label: str, *, nonnegative: bool = False) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProtocolValidationError(f"{label} is not numeric")
    result = float(value)
    if not math.isfinite(result) or (nonnegative and result < 0.0):
        raise ProtocolValidationError(f"{label} is outside its finite domain")
    return result


def _count(value: Any, label: str) -> int:
    result = _number(value, label, nonnegative=True)
    integer = int(result)
    if result != integer:
        raise ProtocolValidationError(f"{label} is not an integer count")
    return integer


def _flag(value: Any, label: str) -> bool:
    if not isinstance(value, bool):
        raise ProtocolValidationError(f"{label} is not boolean")
    return value


def _unique_file(root: Path, names: Sequence[str]) -> Path:
    matches = sorted(
        {path for name in names for path in root.rglob(name) if path.is_file()}
    )
    if len(matches) != 1:
        raise ProtocolValidationError(
            f"expected one of {tuple(names)} below {root}, found {len(matches)}"
        )
    return matches[0]


def _validate_report(path: Path, spec: Mapping[str, Any]) -> dict[str, Any]:
    report = read_json(path)
    if not isinstance(report, dict):
        raise ProtocolValidationError(f"frozen report is not an object: {path}")
    stored = report.get("document_sha256")
    payload = dict(report)
    payload.pop("document_sha256", None)
    if stored != spec["document_sha256"] or object_hash(payload) != stored:
        raise ProtocolValidationError(f"frozen report document hash mismatch: {path}")
    for field in (
        "status",
        "run_count",
        "candidate_run_count",
        "source_control_run_count",
    ):
        if field in spec and report.get(field) != spec[field]:
            raise ProtocolValidationError(f"frozen report {field} mismatch: {path}")
    return report


def _validate_inputs(repo_root: Path) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    products: dict[str, Any] = {}
    receipts: list[dict[str, Any]] = []
    for name, spec in INPUT_PRODUCTS.items():
        path = (repo_root / spec["path"]).resolve()
        actual_file_hash = file_hash(path)
        if actual_file_hash != spec["file_sha256"]:
            raise ProtocolValidationError(f"frozen input file hash mismatch: {name}")
        if spec["kind"] == "manifest":
            value = load_and_validate_manifest(path)
            if value.get("manifest_hash") != spec["document_sha256"]:
                raise ProtocolValidationError(f"manifest hash mismatch: {name}")
        else:
            value = _validate_report(path, spec)
        products[name] = value
        receipts.append(
            {
                "product": name,
                "path": spec["path"],
                "document_sha256": spec["document_sha256"],
                "file_sha256": actual_file_hash,
            }
        )
    return products, receipts


def _validate_sources(repo_root: Path) -> list[dict[str, str]]:
    receipts = []
    for relative, expected in SOURCE_CONTRACT.items():
        actual = file_hash(repo_root / relative)
        if actual != expected:
            raise ProtocolValidationError(f"source contract hash mismatch: {relative}")
        receipts.append({"path": relative, "file_sha256": actual})
    self_path = Path(__file__).resolve()
    receipts.append(
        {
            "path": self_path.relative_to(repo_root.resolve()).as_posix(),
            "file_sha256": file_hash(self_path),
        }
    )
    return receipts


def _is_homogeneous_low_nash(run: Mapping[str, Any]) -> bool:
    workload = run.get("workload")
    return bool(
        run.get("method") == "sche_nash"
        and run.get("variant") == "full"
        and isinstance(workload, Mapping)
        and workload.get("topology") == "homogeneous"
        and workload.get("request_freq") == "low"
    )


def _select_runs(products: Mapping[str, Any], repo_root: Path) -> list[dict[str, Any]]:
    selected: list[dict[str, Any]] = []
    for role, (product, candidate, seeds) in COHORTS.items():
        manifest = products[product]
        rows = [
            run
            for run in manifest["runs"]
            if _is_homogeneous_low_nash(run)
            and run.get("seed") in seeds
            and run.get("metadata", {}).get("m1_operational_candidate") == candidate
        ]
        if len(rows) != 5 or {row.get("seed") for row in rows} != set(seeds):
            raise ProtocolValidationError(
                f"frozen cohort is incomplete or ambiguous: {role}"
            )
        canonical_root = (
            repo_root / INPUT_PRODUCTS[product]["canonical_root"]
        ).resolve()
        template = manifest.get("execution", {}).get(
            "result_relative_path", "result.json"
        )
        for run in sorted(rows, key=lambda item: str(item["seed"])):
            run_dir = canonical_root / str(run["run_id"])
            qc = validate_canonical_run(
                run,
                run_dir,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path=template,
            )
            runtime = qc.get("observations", {}).get("nash_runtime_contract")
            if (
                not isinstance(runtime, Mapping)
                or runtime.get("stream_contract_ready") is not True
            ):
                raise ProtocolValidationError(
                    f"runtime stream contract failed: {run['run_id']}"
                )
            summary_path = _unique_file(run_dir, ("summary.json",))
            stream_path = _unique_file(
                run_dir, ("nash_metrics.jsonl", "nash_metrics.jsonl.gz")
            )
            selected.append(
                {
                    "role": role,
                    "product": product,
                    "manifest": manifest,
                    "run": run,
                    "canonical_root": canonical_root,
                    "result_relative_path": template,
                    "receipt": {
                        "role": role,
                        "run_id": run["run_id"],
                        "run_spec_hash": run["run_spec_hash"],
                        "workload_tape_sha256": run["workload_tape"]["sha256"],
                        "offline_reference_sha256": run["reference_dependency"][
                            "sha256"
                        ],
                        "qc_report_sha256": file_hash(run_dir / "qc_report.json"),
                        "audit_manifest_sha256": file_hash(run_dir / "manifest.json"),
                        "summary_sha256": file_hash(summary_path),
                        "nash_metrics_sha256": file_hash(stream_path),
                    },
                }
            )
    if len(selected) != 25 or len({item["run"]["run_id"] for item in selected}) != 25:
        raise ProtocolValidationError(
            "attribution run set is not exactly 25 unique runs"
        )
    return selected


def _assert_pair_contract(selected: Sequence[Mapping[str, Any]]) -> None:
    by_role = {
        role: {item["run"]["seed"]: item for item in selected if item["role"] == role}
        for role in COHORTS
    }
    pair_count = 0
    for _, left_role, right_role in PAIR_SPECS:
        if set(by_role[left_role]) != set(by_role[right_role]):
            raise ProtocolValidationError(
                f"pair seeds differ: {left_role}/{right_role}"
            )
        for seed, left in by_role[left_role].items():
            right = by_role[right_role][seed]
            if (
                left["run"]["workload_tape"]["sha256"]
                != right["run"]["workload_tape"]["sha256"]
            ):
                raise ProtocolValidationError(f"pair tape mismatch: {left_role}/{seed}")
            pair_count += 1
    if pair_count != 20:
        raise ProtocolValidationError("attribution pair set is not exactly 20")


def validate_contract(repo_root: Path) -> dict[str, Any]:
    repo_root = repo_root.resolve()
    products, input_receipts = _validate_inputs(repo_root)
    source_receipts = _validate_sources(repo_root)
    selected = _select_runs(products, repo_root)
    _assert_pair_contract(selected)
    return {
        "products": products,
        "input_receipts": input_receipts,
        "source_receipts": source_receipts,
        "selected": selected,
        "run_count": len(selected),
        "pair_count": 20,
    }


def _reference_shape(social: Mapping[str, Any]) -> str:
    source = social.get("reference_source")
    if source == "offline_table":
        _count(social.get("reference_state_key"), "reference_state_key")
        _number(social.get("reference"), "offline reference")
        return source
    if source == "not_requested":
        null_fields = ("reference_state_key", "reference")
        false_fields = ("reference_cache_hit", "feedback_eligible")
        if (
            any(field not in social for field in (*null_fields, *false_fields))
            or any(social[field] is not None for field in null_fields)
            or any(social[field] is not False for field in false_fields)
        ):
            raise ProtocolValidationError(
                "not_requested reference shape is inconsistent"
            )
        return source
    raise ProtocolValidationError(
        f"unexpected active-window reference source: {source}"
    )


def _window_metrics(artifacts: RunArtifacts) -> dict[str, Any]:
    windows = [event for event in artifacts.nse_events if event.get("kind") == "window"]
    if not windows:
        raise ProtocolValidationError("run has no NSE policy windows")
    totals = Counter()
    terminations: Counter[str] = Counter()
    queue_fields = (
        "queue_parent_blocked_total",
        "queue_resident_total",
        "queue_runnable_total",
        "queue_starting_resident_total",
        "queue_data_blocked_total",
    )
    for window in windows:
        decision = window.get("decision")
        solver = window.get("solver")
        cluster = window.get("cluster")
        social = window.get("social")
        if not all(
            isinstance(item, Mapping) for item in (decision, solver, cluster, social)
        ):
            raise ProtocolValidationError("NSE policy window is incomplete")
        assigned = _count(decision.get("assigned_players"), "assigned_players")
        if assigned == 0:
            continue
        totals["active_window_count"] += 1
        totals["assigned_players"] += assigned
        if (
            decision.get("complete_assignment") is not True
            or _count(decision.get("commands_prepared"), "commands_prepared")
            != assigned
            or _count(decision.get("commands_sent"), "commands_sent") != assigned
            or _count(decision.get("invalid_assignments"), "invalid_assignments") != 0
            or decision.get("dispatch_channel_failed") is not False
        ):
            raise ProtocolValidationError("active-window dispatch accounting failed")
        totals["complete_dispatch_windows"] += 1
        for field in (
            "initialization_running_warm_choices",
            "initialization_refined_choices",
            "initialization_lower_utility_choices",
            "selected_running_warm_players",
            "selected_starting_container_players",
            "selected_cold_or_nonrunning_players",
        ):
            totals[field] += _count(decision.get(field), field)
        selected_this_window = sum(
            _count(decision.get(field), field)
            for field in (
                "selected_running_warm_players",
                "selected_starting_container_players",
                "selected_cold_or_nonrunning_players",
            )
        )
        if selected_this_window != assigned:
            raise ProtocolValidationError(
                "selected placement classes do not partition assignments"
            )
        totals["assignment_moves"] += _count(
            solver.get("assignment_moves"), "assignment_moves"
        )
        totals["inner_limit_hits"] += int(
            _flag(solver.get("inner_limit_hit"), "inner_limit_hit")
        )
        totals["outer_limit_hits"] += int(
            _flag(solver.get("outer_limit_hit"), "outer_limit_hit")
        )
        totals["oscillations"] += _count(solver.get("oscillations"), "oscillations")
        totals["inner_stable_windows"] += int(
            _flag(solver.get("inner_stable"), "inner_stable")
        )
        totals["outer_stable_windows"] += int(
            _flag(solver.get("outer_stable"), "outer_stable")
        )
        termination = solver.get("termination")
        if not isinstance(termination, str) or not termination:
            raise ProtocolValidationError("active window lacks a solver termination")
        terminations[termination] += 1
        for field in queue_fields:
            totals[field] += _count(cluster.get(field), field)
        reference_source = _reference_shape(social)
        totals[
            "offline_reference_hit_windows"
            if reference_source == "offline_table"
            else "unreferenced_active_window_count"
        ] += 1
    active = totals["active_window_count"]
    assigned = totals["assigned_players"]
    if active == 0 or assigned == 0 or sum(terminations.values()) != active:
        raise ProtocolValidationError("run has no coherent active-window population")
    if (
        totals["offline_reference_hit_windows"]
        + totals["unreferenced_active_window_count"]
        != active
    ):
        raise ProtocolValidationError(
            "reference coverage does not partition active windows"
        )
    result: dict[str, Any] = {
        "active_window_count": active,
        "assigned_players": assigned,
        "complete_dispatch_windows": totals["complete_dispatch_windows"],
        "assignment_moves": totals["assignment_moves"],
        "inner_limit_hits": totals["inner_limit_hits"],
        "outer_limit_hits": totals["outer_limit_hits"],
        "oscillations": totals["oscillations"],
        "inner_stable_share": totals["inner_stable_windows"] / active,
        "outer_stable_share": totals["outer_stable_windows"] / active,
        "termination_counts": dict(sorted(terminations.items())),
        "initialization_running_warm_choices": totals[
            "initialization_running_warm_choices"
        ],
        "initialization_refined_choices": totals["initialization_refined_choices"],
        "initialization_lower_utility_choices": totals[
            "initialization_lower_utility_choices"
        ],
        "selected_running_warm_share": totals["selected_running_warm_players"]
        / assigned,
        "selected_starting_container_share": totals[
            "selected_starting_container_players"
        ]
        / assigned,
        "selected_cold_or_nonrunning_share": totals[
            "selected_cold_or_nonrunning_players"
        ]
        / assigned,
        "offline_reference_hit_windows": totals["offline_reference_hit_windows"],
        "unreferenced_active_window_count": totals["unreferenced_active_window_count"],
    }
    for field in queue_fields:
        result[field.removesuffix("_total") + "_mean"] = totals[field] / active
    return result


def _raw_row(item: Mapping[str, Any]) -> dict[str, Any]:
    run = item["run"]
    artifacts = load_run_artifacts(
        run,
        item["canonical_root"],
        expected_manifest_hash=item["manifest"]["manifest_hash"],
        result_relative_path=item["result_relative_path"],
    )
    throughput, qpr, latency, cost = _screen_metrics(dict(artifacts.summary))
    fixed = artifacts.summary.get("fixed_observation_window")
    if not isinstance(fixed, Mapping):
        raise ProtocolValidationError("summary lacks fixed observation window")
    row: dict[str, Any] = {
        "product": item["product"],
        "role": item["role"],
        "seed": run["seed"],
        "run_id": run["run_id"],
        "run_spec_hash": run["run_spec_hash"],
        "workload_tape_sha256": run["workload_tape"]["sha256"],
        "offline_reference_sha256": run["reference_dependency"]["sha256"],
        "throughput_kreq_per_s": throughput,
        "qpr": qpr,
        "latency_ms": latency,
        "completion_ratio": _number(
            fixed.get("completion_ratio"), "completion_ratio", nonnegative=True
        ),
        "cost_per_completed_request": cost,
        "qc_report_sha256": item["receipt"]["qc_report_sha256"],
        "audit_manifest_sha256": item["receipt"]["audit_manifest_sha256"],
        "summary_sha256": item["receipt"]["summary_sha256"],
        "nash_metrics_sha256": item["receipt"]["nash_metrics_sha256"],
    }
    row.update(_window_metrics(artifacts))
    row.update(_activation_metrics(artifacts))
    return row


def _pair_rows(raw_rows: Sequence[Mapping[str, Any]]) -> list[dict[str, Any]]:
    by_role = {
        role: {row["seed"]: row for row in raw_rows if row["role"] == role}
        for role in COHORTS
    }
    rows = []
    for contrast, left_role, right_role in PAIR_SPECS:
        for seed in sorted(by_role[left_role]):
            left = by_role[left_role][seed]
            right = by_role[right_role][seed]
            if left["workload_tape_sha256"] != right["workload_tape_sha256"]:
                raise ProtocolValidationError(
                    f"raw pair tape mismatch: {contrast}/{seed}"
                )
            row: dict[str, Any] = {
                "contrast": contrast,
                "seed": seed,
                "left_role": left_role,
                "right_role": right_role,
                "left_run_id": left["run_id"],
                "right_run_id": right["run_id"],
                "workload_tape_sha256": left["workload_tape_sha256"],
            }
            for metric in PAIR_NUMERIC_METRICS:
                left_value = _number(left[metric], f"left {metric}")
                right_value = _number(right[metric], f"right {metric}")
                row[f"delta_{metric}"] = left_value - right_value
                if metric in OUTCOME_METRICS:
                    if right_value <= 0.0:
                        raise ProtocolValidationError(
                            f"ratio denominator is not positive: {contrast}/{metric}"
                        )
                    row[f"ratio_{metric}"] = left_value / right_value
            rows.append(row)
    if len(rows) != 20:
        raise ProtocolValidationError("paired output does not contain exactly 20 rows")
    return rows


def summarize(values: Sequence[float]) -> dict[str, Any]:
    sample = [_number(value, "summary value") for value in values]
    if len(sample) != 5:
        raise ProtocolValidationError(
            "frozen paired summary requires exactly five values"
        )
    mean = fmean(sample)
    sd = stdev(sample)
    half_width = float(scipy_stats.t.ppf(0.975, 4)) * sd / math.sqrt(5)
    epsilon = 1e-15
    return {
        "n": 5,
        "mean": mean,
        "sample_sd": sd,
        "ci95_low": mean - half_width,
        "ci95_high": mean + half_width,
        "positive": sum(value > epsilon for value in sample),
        "zero": sum(abs(value) <= epsilon for value in sample),
        "negative": sum(value < -epsilon for value in sample),
        "values": sample,
        "leave_one_seed_out_means": [
            fmean(sample[:index] + sample[index + 1 :]) for index in range(5)
        ],
    }


def _contrast_summaries(pair_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for contrast, _, _ in PAIR_SPECS:
        rows = [row for row in pair_rows if row["contrast"] == contrast]
        if len(rows) != 5:
            raise ProtocolValidationError(f"contrast is incomplete: {contrast}")
        metrics = [key for key in rows[0] if key.startswith(("delta_", "ratio_"))]
        summaries[contrast] = {
            metric: summarize([_number(row[metric], metric) for row in rows])
            for metric in metrics
        }
    return summaries


def _cohort_summaries(raw_rows: Sequence[Mapping[str, Any]]) -> dict[str, Any]:
    summaries: dict[str, Any] = {}
    for role in COHORTS:
        rows = [row for row in raw_rows if row["role"] == role]
        if len(rows) != 5:
            raise ProtocolValidationError(f"raw cohort is incomplete: {role}")
        summaries[role] = {
            metric: summarize([_number(row[metric], metric) for row in rows])
            for metric in PAIR_NUMERIC_METRICS
        }
    return summaries


def evaluate_conditions(
    raw_rows: Sequence[Mapping[str, Any]], pair_rows: Sequence[Mapping[str, Any]]
) -> dict[str, Any]:
    roles = {role: [row for row in raw_rows if row["role"] == role] for role in COHORTS}
    g7_g6 = [row for row in pair_rows if row["contrast"] == "g7_minus_g6"]
    if any(len(rows) != 5 for rows in roles.values()) or len(g7_g6) != 5:
        raise ProtocolValidationError("authorization inputs are incomplete")
    a1_count = sum(
        row["maximum_executable_frontier_hops_ahead"] <= 1
        and row["frontier_hop_violation_count"] == 0
        for row in roles["g7"]
    )
    a2_count = sum(
        row["maximum_executable_frontier_hops_ahead"] > 1 for row in roles["g6"]
    )
    a3_count = sum(row["delta_queue_parent_blocked_mean"] < 0 for row in g7_g6)
    a4_count = sum(row["delta_queue_resident_mean"] < 0 for row in g7_g6)
    b1_g7_refined = sum(
        row["initialization_refined_choices"] > 0 for row in roles["g7"]
    )
    b1_g7_lower = sum(
        row["initialization_lower_utility_choices"] > 0 for row in roles["g7"]
    )
    b1_g6_zero = sum(
        row["initialization_lower_utility_choices"] == 0 for row in roles["g6"]
    )
    mean_t_delta = fmean(row["delta_throughput_kreq_per_s"] for row in g7_g6)
    mean_qpr_delta = fmean(row["delta_qpr"] for row in g7_g6)
    throughput_losses = sum(row["delta_throughput_kreq_per_s"] < 0 for row in g7_g6)
    qpr_losses = sum(row["delta_qpr"] < 0 for row in g7_g6)
    g7_unreferenced = sum(
        row["unreferenced_active_window_count"] for row in roles["g7"]
    )
    more_unreferenced = sum(
        row["delta_unreferenced_active_window_count"] > 0 for row in g7_g6
    )
    conditions = {
        "A1_g7_frontier_bound_all_seeds": {
            "passed": a1_count == 5,
            "passing_seed_count": a1_count,
            "required": 5,
        },
        "A2_g6_deeper_than_one_hop_at_least_four_seeds": {
            "passed": a2_count >= 4,
            "passing_seed_count": a2_count,
            "required": 4,
        },
        "A3_g7_parent_blocked_mean_below_g6_at_least_four_seeds": {
            "passed": a3_count >= 4,
            "passing_seed_count": a3_count,
            "required": 4,
        },
        "A4_g7_resident_mean_below_g6_at_least_four_seeds": {
            "passed": a4_count >= 4,
            "passing_seed_count": a4_count,
            "required": 4,
        },
        "B1_warm_perturbation_exposed_all_seeds": {
            "passed": b1_g7_refined == b1_g7_lower == b1_g6_zero == 5,
            "g7_refined_positive_seed_count": b1_g7_refined,
            "g7_lower_utility_positive_seed_count": b1_g7_lower,
            "g6_lower_utility_zero_seed_count": b1_g6_zero,
            "required_each": 5,
        },
        "B2_g7_mean_outcomes_lower_and_loses_at_least_three_seeds": {
            "passed": (
                mean_t_delta < 0
                and mean_qpr_delta < 0
                and throughput_losses >= 3
                and qpr_losses >= 3
            ),
            "mean_throughput_delta": mean_t_delta,
            "mean_qpr_delta": mean_qpr_delta,
            "throughput_loss_seed_count": throughput_losses,
            "qpr_loss_seed_count": qpr_losses,
            "required_losses_each": 3,
        },
        "B3_g7_exact_not_requested_exposed": {
            "passed": g7_unreferenced > 0 and more_unreferenced >= 1,
            "g7_unreferenced_active_window_total": g7_unreferenced,
            "g7_more_than_g6_seed_count": more_unreferenced,
            "required_more_seed_count": 1,
        },
    }
    authorized = all(condition["passed"] for condition in conditions.values())
    return {
        "conditions": conditions,
        "g8_candidate_preregistration_authorized": authorized,
        "status": (
            "complete_g8_frontier_only_preregistration_authorized"
            if authorized
            else "complete_no_g8_authorized"
        ),
    }


def analyze(repo_root: Path) -> dict[str, Any]:
    contract = validate_contract(repo_root)
    raw_rows = [_raw_row(item) for item in contract["selected"]]
    pair_rows = _pair_rows(raw_rows)
    cohort_summaries = _cohort_summaries(raw_rows)
    summaries = _contrast_summaries(pair_rows)
    decision = evaluate_conditions(raw_rows, pair_rows)
    return {
        "schema_version": SCHEMA_VERSION,
        "created_at": utc_now(),
        "status": decision["status"],
        "formal_results_eligible": False,
        "paper_equations_changed": False,
        "definitions": {
            "independent_unit": "run/seed",
            "development_bank": True,
            "all_valid_frozen_runs_retained": True,
            "active_window": "NSE window with assigned_players > 0",
            "queue_mean_denominator": "all active scheduling windows",
            "activation_population": "completed functions only",
            "pair_difference": "left minus right; positive means more raw quantity",
            "pair_ratio": "left divided by right for positive outcome metrics",
            "g2_cross_bank_policy": "directional context only; never paired or pooled with D71-D75",
            "interval_interpretation": "descriptive paired t interval at n=5; not a confirmatory p-value",
        },
        "input_receipts": contract["input_receipts"],
        "source_receipts": contract["source_receipts"],
        "canonical_run_receipts": [item["receipt"] for item in contract["selected"]],
        "raw_run_metrics": raw_rows,
        "paired_metrics": pair_rows,
        "cohort_summaries": cohort_summaries,
        "contrast_summaries": summaries,
        "authorization_conditions": decision["conditions"],
        "run_count": len(raw_rows),
        "pair_count": len(pair_rows),
        "g8_candidate_preregistration_authorized": decision[
            "g8_candidate_preregistration_authorized"
        ],
        "g8_implementation_authorized": False,
        "new_sampling_authorized": False,
        "confirmation_sampling_authorized": False,
        "formal_progression_authorized": False,
    }


def _csv_value(value: Any) -> Any:
    if isinstance(value, (dict, list, tuple)):
        return json.dumps(
            value, ensure_ascii=False, sort_keys=True, separators=(",", ":")
        )
    return value


def _write_csv(path: Path, rows: Sequence[Mapping[str, Any]]) -> None:
    if not rows:
        raise ProtocolValidationError(f"empty CSV product: {path.name}")
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("x", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, extrasaction="raise")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: _csv_value(value) for key, value in row.items()})


def write_outputs(report: Mapping[str, Any], output_dir: Path) -> list[Path]:
    output_dir = output_dir.resolve()
    paths = [output_dir / name for name in OUTPUT_NAMES]
    if output_dir.exists() or any(path.exists() for path in paths):
        raise FileExistsError("G8 attribution output directory already exists")
    output_dir.mkdir(parents=True, exist_ok=False)
    temporary = [path.with_suffix(path.suffix + ".tmp") for path in paths]
    try:
        _write_csv(temporary[1], report["raw_run_metrics"])
        _write_csv(temporary[2], report["paired_metrics"])
        temporary[1].replace(paths[1])
        temporary[2].replace(paths[2])
        final_report = dict(report)
        final_report["output_receipts"] = {
            paths[1].name: {
                "row_count": len(report["raw_run_metrics"]),
                "file_sha256": file_hash(paths[1]),
            },
            paths[2].name: {
                "row_count": len(report["paired_metrics"]),
                "file_sha256": file_hash(paths[2]),
            },
        }
        final_report["document_sha256"] = object_hash(final_report)
        with temporary[0].open("x", encoding="utf-8") as handle:
            json.dump(
                final_report,
                handle,
                ensure_ascii=False,
                sort_keys=True,
                indent=2,
                allow_nan=False,
            )
            handle.write("\n")
        temporary[0].replace(paths[0])
    except Exception:
        for path in (*temporary, *paths):
            if path.exists():
                path.unlink()
        if output_dir.exists():
            output_dir.rmdir()
        raise
    return paths


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args(argv)
    if args.validate_only:
        contract = validate_contract(args.repo_root)
        print(
            json.dumps(
                {
                    "status": "source_contract_validated",
                    "run_count": contract["run_count"],
                    "pair_count": contract["pair_count"],
                    "input_receipt_count": len(contract["input_receipts"]),
                    "source_receipt_count": len(contract["source_receipts"]),
                },
                sort_keys=True,
            )
        )
        return 0
    if args.output_dir is None:
        parser.error("--output-dir is required unless --validate-only is used")
    report = analyze(args.repo_root)
    paths = write_outputs(report, args.output_dir)
    print(
        json.dumps(
            {
                "status": report["status"],
                "g8_candidate_preregistration_authorized": report[
                    "g8_candidate_preregistration_authorized"
                ],
                "run_count": report["run_count"],
                "pair_count": report["pair_count"],
                "outputs": [str(path) for path in paths],
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
