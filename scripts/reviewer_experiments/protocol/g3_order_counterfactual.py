"""Frozen 50-replay G3 strict-PNE order-counterfactual diagnostic.

The replay keeps the live ``ready_order`` scheduler path unchanged.  The
instrumented Rust binary emits five read-only first-inner strict-best-response
outcomes plus a non-worse-welfare envelope for every scheduler window.
"""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
from typing import Any, Iterable, Mapping, Sequence

from .g1_corrected_runtime import _runtime_execution
from .m1_completion_guard import _runtime_receipt
from .m1_development import _matrix_summary
from .matrix import _assign_run_identity, _reference_build_dependencies
from .schema import (
    G3_ORDER_COUNTERFACTUAL_MARKER,
    G3_ORDER_COUNTERFACTUAL_SAMPLE_POLICY,
    G3_ORDER_COUNTERFACTUAL_SEEDS,
    ProtocolValidationError,
    load_and_validate_manifest,
    validate_manifest,
)
from .util import file_hash, object_hash, utc_now, write_json_atomic


G3_ORDER_COUNTERFACTUAL_SCHEMA = "NSE_G3_ORDER_COUNTERFACTUAL_DIAGNOSTIC_V1"
G3_COUNTERFACTUAL_STREAM_SCHEMA = "strict_pne_scarcity_order_v1"
G3_ORDERS = (
    "ready_order",
    "reverse_ready_order",
    "service_scarcity_first",
    "capacity_scarcity_first",
    "resource_impact_first",
)
G3_ENVELOPE = "nonworse_welfare_cold_envelope"
G3_STRATA = (
    "g1_q_homogeneous_low",
    "g2_homogeneous_low",
    "g2_homogeneous_middle",
    "g2_homogeneous_high",
    "g2_heterogeneous_low",
    "g2_heterogeneous_middle",
    "g2_heterogeneous_high",
)


def _source_manifest_receipt(
    path: Path, manifest: Mapping[str, Any], selected_source_runs: int
) -> dict[str, Any]:
    return {
        "path": str(path.resolve()),
        "manifest_hash": manifest["manifest_hash"],
        "file_sha256": file_hash(path),
        "run_count": len(manifest["runs"]),
        "selected_source_runs": selected_source_runs,
    }


def _source_artifact(canonical_dir: Path, relative_path: Path) -> dict[str, Any]:
    path = canonical_dir / relative_path
    if not path.is_file():
        raise ProtocolValidationError(f"missing G3 source artifact: {path}")
    return {
        "path": str(path.resolve()),
        "sha256": file_hash(path),
        "bytes": path.stat().st_size,
    }


def _source_bindings(canonical_root: Path, source_run_id: str) -> dict[str, Any]:
    canonical_dir = canonical_root.resolve() / source_run_id
    if not canonical_dir.is_dir():
        raise ProtocolValidationError(
            f"missing G3 source canonical directory: {canonical_dir}"
        )
    records = Path("reviewer_records") / source_run_id
    return {
        "canonical_directory": str(canonical_dir),
        "run_config": _source_artifact(canonical_dir, Path("run_config.json")),
        "summary": _source_artifact(canonical_dir, records / "summary.json"),
        "nash_metrics": _source_artifact(
            canonical_dir, records / "nash_metrics.jsonl.gz"
        ),
    }


def _select_g1_runs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    runs = [
        copy.deepcopy(run)
        for run in manifest["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in {f"Q{index:02d}" for index in range(61, 81)}
        and run.get("cluster", {}).get("node_count") == 20
        and run.get("cluster", {}).get("topology") == "homogeneous"
        and run.get("workload", {}).get("request_freq") == "low"
        and run.get("metadata", {}).get("m1_operational_candidate") == "ready_order"
    ]
    runs.sort(key=lambda run: run["seed"])
    if len(runs) != 20 or [run["seed"] for run in runs] != [
        f"Q{index:02d}" for index in range(61, 81)
    ]:
        raise ProtocolValidationError(
            "G3 requires exactly the Q61--Q80 G1 NSESche homogeneous-low source runs"
        )
    return runs


def _select_g2_runs(manifest: Mapping[str, Any]) -> list[dict[str, Any]]:
    runs = [
        copy.deepcopy(run)
        for run in manifest["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in {f"D{index:02d}" for index in range(66, 71)}
        and run.get("cluster", {}).get("node_count") == 20
        and run.get("cluster", {}).get("topology") in {"homogeneous", "heterogeneous"}
        and run.get("workload", {}).get("request_freq") in {"low", "middle", "high"}
        and run.get("metadata", {}).get("m1_operational_candidate") == "ready_order"
    ]
    topology_rank = {"homogeneous": 0, "heterogeneous": 1}
    load_rank = {"low": 0, "middle": 1, "high": 2}
    runs.sort(
        key=lambda run: (
            topology_rank[run["cluster"]["topology"]],
            load_rank[run["workload"]["request_freq"]],
            run["seed"],
        )
    )
    expected = {
        (topology, load, f"D{index:02d}")
        for topology in ("homogeneous", "heterogeneous")
        for load in ("low", "middle", "high")
        for index in range(66, 71)
    }
    actual = {
        (
            run["cluster"]["topology"],
            run["workload"]["request_freq"],
            run["seed"],
        )
        for run in runs
    }
    if len(runs) != 30 or actual != expected:
        raise ProtocolValidationError(
            "G3 requires exactly the 30 D66--D70 G2 C0 source runs"
        )
    return runs


def _assert_shared_protocol(g1: Mapping[str, Any], g2: Mapping[str, Any]) -> None:
    for field in (
        "protocol_id",
        "method_versions",
        "old_pdf_alignment",
        "runtime_identity_policy",
        "common_hpa",
        "common_hpa_hash",
        "workload_profile_set",
        "workload_profile_set_hash",
        "simulation",
        "qc",
    ):
        if g1.get(field) != g2.get(field):
            raise ProtocolValidationError(
                f"G3 source manifests differ in frozen shared field {field}"
            )


def _stratum(source_bank: str, run: Mapping[str, Any]) -> str:
    if source_bank == "g1_q61_q80":
        return "g1_q_homogeneous_low"
    return "g2_{}_{}".format(
        run["cluster"]["topology"], run["workload"]["request_freq"]
    )


def _counterfactual_run(
    source_run: Mapping[str, Any],
    *,
    source_bank: str,
    source_manifest: Mapping[str, Any],
    canonical_root: Path,
) -> dict[str, Any]:
    run = copy.deepcopy(dict(source_run))
    source_run_id = str(run["run_id"])
    stratum = _stratum(source_bank, run)
    run["cell_id"] = f"G3ORDERCF.{stratum}.n20"
    metadata = copy.deepcopy(run.get("metadata", {}))
    metadata.update(
        {
            "g3_order_counterfactual_role": "decision_neutral_source_replay",
            "g3_reporting_stratum": stratum,
            "source_bank": source_bank,
            "source_manifest_hash": source_manifest["manifest_hash"],
            "source_run_id": source_run_id,
            "source_run_spec_hash": run["run_spec_hash"],
            "source_artifacts": _source_bindings(canonical_root, source_run_id),
            "m1_operational_candidate": "ready_order",
            "paper_equations_changed": False,
            "strict_best_response": True,
            "utility_guard_relative_regret": 0.0,
            "decision_neutral_observation": G3_COUNTERFACTUAL_STREAM_SCHEMA,
            "counterfactual_dispatch_feedback": False,
            "formal_results_eligible": False,
        }
    )
    run["metadata"] = metadata
    run["environment"] = copy.deepcopy(run["environment"])
    run["environment"]["NASH_OPERATIONAL_REFINEMENT"] = "ready_order"
    run["environment"]["NASH_ORDER_COUNTERFACTUAL"] = "1"
    if (
        run["simulator_experiment"]["nash"].get("operational_refinement")
        != "ready_order"
    ):
        raise ProtocolValidationError(
            f"G3 source run is not live ready_order: {source_run_id}"
        )
    _assign_run_identity(run)
    return run


def build_g3_order_counterfactual_manifest(
    g1_manifest_path: Path,
    g1_canonical_root: Path,
    g2_manifest_path: Path,
    g2_canonical_root: Path,
    simulator_exe: Path,
    source_git_commit: str,
    preregistration_path: Path,
) -> dict[str, Any]:
    """Build and validate the immutable 50-source diagnostic replay manifest."""

    g1_manifest_path = g1_manifest_path.resolve()
    g2_manifest_path = g2_manifest_path.resolve()
    preregistration_path = preregistration_path.resolve()
    g1 = load_and_validate_manifest(g1_manifest_path)
    g2 = load_and_validate_manifest(g2_manifest_path)
    _assert_shared_protocol(g1, g2)
    if not preregistration_path.is_file():
        raise ProtocolValidationError(
            f"G3 preregistration artifact does not exist: {preregistration_path}"
        )
    runtime = _runtime_receipt(simulator_exe, source_git_commit)
    selected_g1 = _select_g1_runs(g1)
    selected_g2 = _select_g2_runs(g2)
    runs = [
        *(
            _counterfactual_run(
                run,
                source_bank="g1_q61_q80",
                source_manifest=g1,
                canonical_root=g1_canonical_root,
            )
            for run in selected_g1
        ),
        *(
            _counterfactual_run(
                run,
                source_bank="g2_d66_d70",
                source_manifest=g2,
                canonical_root=g2_canonical_root,
            )
            for run in selected_g2
        ),
    ]
    marker = {
        "schema_version": G3_ORDER_COUNTERFACTUAL_SCHEMA,
        "purpose": "decision-neutral strict-PNE scarcity-order diagnosis",
        "paper_equations_changed": False,
        "strict_eq15_required": True,
        "decision_feedback": False,
        "counterfactual_schema": G3_COUNTERFACTUAL_STREAM_SCHEMA,
        "orders": list(G3_ORDERS),
        "envelope": G3_ENVELOPE,
        "strata": list(G3_STRATA),
        "source_manifests": {
            "g1_q61_q80": _source_manifest_receipt(
                g1_manifest_path, g1, len(selected_g1)
            ),
            "g2_d66_d70": _source_manifest_receipt(
                g2_manifest_path, g2, len(selected_g2)
            ),
        },
        "preregistration": {
            "path": str(preregistration_path),
            "sha256": file_hash(preregistration_path),
            "bytes": preregistration_path.stat().st_size,
        },
        "runtime_binary": runtime,
        "integrity_gates": {
            "exact_replay_count": 50,
            "live_c0_source_parity_required": True,
            "o0_first_inner_hash_parity_required": True,
            "strict_pne_certificate_required": True,
            "decision_feedback_must_be_false": True,
            "complete_raw_output_required": True,
        },
        "eligibility": {
            "different_assignment_overall_min_fraction": 0.01,
            "different_assignment_min_strata": 4,
            "welfare_overall_nonnegative": True,
            "welfare_max_stratum_regression_fraction": 0.001,
            "startup_overall_strictly_lower": True,
            "startup_nonworse_min_strata": 5,
            "startup_max_stratum_regression_fraction": 0.01,
            "projected_finish_overall_strictly_lower": True,
            "projected_finish_nonworse_min_strata": 5,
            "projected_finish_max_stratum_regression_fraction": 0.01,
            "selection_uses_throughput_or_qpr": False,
            "maximum_later_candidates": 2,
        },
        "run_count": 50,
        "cell_count": 7,
        "reference_build_count": len(_reference_build_dependencies(runs)),
        "D71_authorized": False,
    }
    manifest: dict[str, Any] = {
        "schema_version": "1.0",
        "protocol_id": g1["protocol_id"],
        "created_at": utc_now(),
        "phase": "development",
        "bank_id": "TSCv1.diagnostic.G3.order-counterfactual.Q61-Q80.D66-D70",
        "formal_results_eligible": False,
        "fixed_seed_bank": {
            "policy": G3_ORDER_COUNTERFACTUAL_SAMPLE_POLICY,
            "all_seeds": list(G3_ORDER_COUNTERFACTUAL_SEEDS),
            "selected_seeds": list(G3_ORDER_COUNTERFACTUAL_SEEDS),
            "paired_across_methods": False,
            "result_conditioned_extension": False,
        },
        "method_versions": copy.deepcopy(g1["method_versions"]),
        "old_pdf_alignment": copy.deepcopy(g1["old_pdf_alignment"]),
        "runtime_identity_policy": copy.deepcopy(g1["runtime_identity_policy"]),
        "seed_stage": "development",
        "ci_extension_requires_trigger": False,
        "common_hpa": copy.deepcopy(g1["common_hpa"]),
        "common_hpa_hash": g1["common_hpa_hash"],
        "workload_profile_set": copy.deepcopy(g1["workload_profile_set"]),
        "workload_profile_set_hash": g1["workload_profile_set_hash"],
        "simulation": copy.deepcopy(g1["simulation"]),
        "execution": _runtime_execution(g1["execution"], runtime),
        "qc": copy.deepcopy(g1["qc"]),
        "matrix_summary": _matrix_summary(runs),
        "runs": runs,
        "reference_build_dependencies": _reference_build_dependencies(runs),
        "all_tapes_bound": True,
        "all_references_bound": True,
        "all_faasrank_models_bound": False,
        "all_sla_targets_bound": False,
        "reuse_analyses": [],
        G3_ORDER_COUNTERFACTUAL_MARKER: marker,
    }
    manifest["manifest_hash"] = object_hash(manifest)
    validate_manifest(manifest)
    return manifest


def write_g3_order_counterfactual_manifest(
    output_path: Path,
    g1_manifest_path: Path,
    g1_canonical_root: Path,
    g2_manifest_path: Path,
    g2_canonical_root: Path,
    simulator_exe: Path,
    source_git_commit: str,
    preregistration_path: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError(
            "refusing to overwrite G3 order-counterfactual manifest"
        )
    manifest = build_g3_order_counterfactual_manifest(
        g1_manifest_path,
        g1_canonical_root,
        g2_manifest_path,
        g2_canonical_root,
        simulator_exe,
        source_git_commit,
        preregistration_path,
    )
    write_json_atomic(output_path, manifest)
    return manifest


def source_run_ids(manifest: Mapping[str, Any]) -> Iterable[str]:
    """Expose the frozen result-blind source order for tests and receipts."""

    return (str(run["metadata"]["source_run_id"]) for run in manifest["runs"])


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("--g1-manifest", type=Path, required=True)
    parser.add_argument("--g1-canonical-root", type=Path, required=True)
    parser.add_argument("--g2-manifest", type=Path, required=True)
    parser.add_argument("--g2-canonical-root", type=Path, required=True)
    parser.add_argument("--simulator-exe", type=Path, required=True)
    parser.add_argument("--runtime-source-commit", required=True)
    parser.add_argument("--preregistration", type=Path, required=True)
    args = parser.parse_args(argv)
    manifest = write_g3_order_counterfactual_manifest(
        args.output,
        args.g1_manifest,
        args.g1_canonical_root,
        args.g2_manifest,
        args.g2_canonical_root,
        args.simulator_exe,
        args.runtime_source_commit,
        args.preregistration,
    )
    print(
        json.dumps(
            {
                "status": "written_g3_order_counterfactual_diagnostic",
                "manifest_hash": manifest["manifest_hash"],
                "run_count": len(manifest["runs"]),
                "D71_authorized": False,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
