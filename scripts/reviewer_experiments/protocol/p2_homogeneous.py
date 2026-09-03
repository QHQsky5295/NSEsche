"""Freeze and execute the V4 claim-reframed homogeneous-middle cell.

The source ready manifest already binds all Q61--Q80 tapes, references, method
configurations, and the preserved corrected-runtime executable.  This module
does not derive new scientific inputs.  It creates a hash-bound allowlist for
the one previously unexecuted 200-run cell and revalidates every dependency
before passing those exact run IDs to :class:`ProtocolRunner`.
"""

from __future__ import annotations

import argparse
import copy
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Mapping, Sequence

from .g1_corrected_runtime import (
    G1_FORMAL_QUALIFICATION_SEEDS,
    G1_FORMAL_QUALIFICATION_SCHEMA,
)
from .runner import ProtocolRunner
from .schema import (
    FORMAL_E1_METHODS,
    ProtocolValidationError,
    load_and_validate_manifest,
)
from .util import file_hash, object_hash, read_json, utc_now, write_json_atomic


P2_MIDDLE_SELECTION_SCHEMA = "NSE_P2_HOMOGENEOUS_MIDDLE_SELECTION_V1"
P2_MIDDLE_LOAD = "middle"
P2_MIDDLE_TOPOLOGY = "homogeneous"
P2_MIDDLE_NODE_COUNT = 20
P2_MIDDLE_RUN_COUNT = 200
P2_MIDDLE_WORKSPACE_NAME = "tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904"

EXPECTED_SOURCE_MANIFEST_HASH = (
    "5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b"
)
EXPECTED_SOURCE_MANIFEST_FILE_SHA256 = (
    "d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a"
)
EXPECTED_RUNTIME_SOURCE_COMMIT = "98f822cf2dcb878024a2ca39cc56533895ea692c"
EXPECTED_RUNTIME_SHA256 = (
    "7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4"
)
EXPECTED_RUNTIME_BYTES = 4_707_328
EXPECTED_FAASRANK_SHA256 = (
    "4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e"
)
EXPECTED_AUTHORIZATION_SHA256 = {
    "plan_v4": "68369bd695e56232fba76d7be6b91e11d899a2e6372c08234635ea53ec8295c0",
    "p1a": "16c221a2512b2afcc4923e690f9f3320154749359636a5ae1b87c1a8348425c4",
    "p1b": "33b8627a81560fd296508adebb5408c99ddacdd0541ff8a67d7d2074f45b093c",
    "low_audit": "9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16",
    "low_report": "98558269dc6303f9245479f1a4aaa02d40ad0f727c3db491780558a0802f8073",
}
EXPECTED_LOW_REPORT_DOCUMENT_SHA256 = (
    "10dada54be25f19efa647d5c46bf5f7bf6528f12a6f55f33e02349d2ffa7f709"
)


def _receipt(path: Path, expected_sha256: str) -> dict[str, Any]:
    resolved = path.resolve()
    if not resolved.is_file():
        raise ProtocolValidationError(
            f"required P2 authorization file is missing: {resolved}"
        )
    observed = file_hash(resolved)
    if observed != expected_sha256:
        raise ProtocolValidationError(
            f"P2 authorization file hash mismatch for {resolved}: {observed}"
        )
    return {
        "path": str(resolved),
        "bytes": resolved.stat().st_size,
        "sha256": observed,
    }


def _validate_low_report(path: Path) -> dict[str, Any]:
    report = read_json(path)
    if not isinstance(report, dict):
        raise ProtocolValidationError("retained low-load report is not a JSON object")
    payload = copy.deepcopy(report)
    document_sha256 = payload.pop("document_sha256", None)
    if (
        report.get("schema_version") != "NSE_G1_FORMAL_CELL_REPORT_V1"
        or document_sha256 != EXPECTED_LOW_REPORT_DOCUMENT_SHA256
        or document_sha256 != object_hash(payload)
        or report.get("topology") != "homogeneous"
        or report.get("load") != "low"
        or report.get("run_count") != 200
        or report.get("all_valid_rows_retained") is not True
        or report.get("next_cell_authorized") is not False
    ):
        raise ProtocolValidationError("retained low-load machine report is invalid")
    return report


def _source_and_runs(
    source_manifest_path: Path,
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    source_path = source_manifest_path.resolve()
    source = load_and_validate_manifest(source_path)
    marker = source.get("g1_formal_qualification")
    runtime = marker.get("runtime_binary") if isinstance(marker, Mapping) else None
    if (
        source.get("manifest_hash") != EXPECTED_SOURCE_MANIFEST_HASH
        or file_hash(source_path) != EXPECTED_SOURCE_MANIFEST_FILE_SHA256
        or not isinstance(marker, Mapping)
        or marker.get("schema_version") != G1_FORMAL_QUALIFICATION_SCHEMA
        or not isinstance(runtime, Mapping)
        or runtime.get("source_git_commit") != EXPECTED_RUNTIME_SOURCE_COMMIT
        or runtime.get("sha256") != EXPECTED_RUNTIME_SHA256
        or runtime.get("bytes") != EXPECTED_RUNTIME_BYTES
        or len(source.get("runs", [])) != 1_200
    ):
        raise ProtocolValidationError(
            "P2 source is not the frozen Q61--Q80 ready manifest"
        )

    binary_path = Path(str(runtime["path"])).resolve()
    if (
        not binary_path.is_file()
        or binary_path.stat().st_size != EXPECTED_RUNTIME_BYTES
        or file_hash(binary_path) != EXPECTED_RUNTIME_SHA256
    ):
        raise ProtocolValidationError(
            "preserved P2 runtime binary is missing or changed"
        )

    selected = [
        run
        for run in source["runs"]
        if run.get("experiment_id") == "E1"
        and run.get("cluster", {}).get("topology") == P2_MIDDLE_TOPOLOGY
        and run.get("cluster", {}).get("node_count") == P2_MIDDLE_NODE_COUNT
        and run.get("workload", {}).get("request_freq") == P2_MIDDLE_LOAD
    ]
    if len(selected) != P2_MIDDLE_RUN_COUNT:
        raise ProtocolValidationError(
            "P2 source does not contain exactly 200 middle runs"
        )
    expected_pairs = {
        (method, seed)
        for method in FORMAL_E1_METHODS
        for seed in G1_FORMAL_QUALIFICATION_SEEDS
    }
    observed_pairs = [(str(run["method"]), str(run["seed"])) for run in selected]
    if (
        len(observed_pairs) != len(set(observed_pairs))
        or set(observed_pairs) != expected_pairs
    ):
        raise ProtocolValidationError("P2 middle method/seed product is incomplete")
    if len({str(run["run_id"]) for run in selected}) != P2_MIDDLE_RUN_COUNT:
        raise ProtocolValidationError("P2 middle run IDs are not unique")
    if len({str(run["run_spec_hash"]) for run in selected}) != P2_MIDDLE_RUN_COUNT:
        raise ProtocolValidationError(
            "P2 middle run specification hashes are not unique"
        )
    return source, selected


def _input_receipts(
    source_path: Path, selected: Sequence[Mapping[str, Any]]
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], dict[str, Any]]:
    by_seed: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    for run in selected:
        by_seed[str(run["seed"])].append(run)

    tape_receipts: list[dict[str, Any]] = []
    reference_receipts: list[dict[str, Any]] = []
    for seed in G1_FORMAL_QUALIFICATION_SEEDS:
        runs = by_seed.get(seed, [])
        if len(runs) != len(FORMAL_E1_METHODS):
            raise ProtocolValidationError(f"P2 seed {seed} lacks ten paired methods")
        tapes = {
            (
                str(run["workload_tape"]["key"]),
                str(run["workload_tape"]["path"]),
                str(run["workload_tape"]["sha256"]),
                str(run["workload_tape"]["capture_receipt_path"]),
                str(run["workload_tape"]["capture_receipt_sha256"]),
            )
            for run in runs
        }
        if len(tapes) != 1:
            raise ProtocolValidationError(f"P2 seed {seed} does not share one tape")
        key, tape_name, tape_sha, capture_name, capture_sha = next(iter(tapes))
        tape_path = Path(tape_name).resolve()
        capture_path = Path(capture_name).resolve()
        if file_hash(tape_path) != tape_sha or file_hash(capture_path) != capture_sha:
            raise ProtocolValidationError(f"P2 tape evidence changed for seed {seed}")
        tape_receipts.append(
            {
                "seed": seed,
                "key": key,
                "path": str(tape_path),
                "bytes": tape_path.stat().st_size,
                "sha256": tape_sha,
                "capture_receipt_path": str(capture_path),
                "capture_receipt_sha256": capture_sha,
            }
        )

        nash_runs = [run for run in runs if run["method"] == "sche_nash"]
        if len(nash_runs) != 1:
            raise ProtocolValidationError(f"P2 seed {seed} lacks one NSESche run")
        nash_run = nash_runs[0]
        nash = nash_run.get("simulator_experiment", {}).get("nash", {})
        dependency = nash_run.get("reference_dependency")
        if (
            nash_run.get("metadata", {}).get("m1_operational_candidate")
            != "ready_order"
            or nash_run.get("metadata", {}).get("strict_best_response") is not True
            or nash.get("operational_refinement") != "ready_order"
            or nash.get("price_feedback_rate") != 0.5
            or nash.get("quality_weight") != 0.6
            or nash.get("max_inner_rounds") != 4
            or nash.get("max_outer_rounds") != 2
            or not isinstance(dependency, Mapping)
            or dependency.get("build_required") is not False
        ):
            raise ProtocolValidationError(
                f"P2 NSESche contract changed for seed {seed}"
            )
        reference_path = Path(str(dependency["path"])).resolve()
        receipt_path = Path(str(dependency["receipt_path"])).resolve()
        if file_hash(reference_path) != dependency.get("sha256") or file_hash(
            receipt_path
        ) != dependency.get("receipt_sha256"):
            raise ProtocolValidationError(
                f"P2 reference evidence changed for seed {seed}"
            )
        reference_receipts.append(
            {
                "seed": seed,
                "key": dependency["key"],
                "path": str(reference_path),
                "bytes": reference_path.stat().st_size,
                "sha256": dependency["sha256"],
                "receipt_path": str(receipt_path),
                "receipt_sha256": dependency["receipt_sha256"],
            }
        )

    faasrank_runs = [run for run in selected if run["method"] == "sche_FaaSRank"]
    model_hashes = {
        str(run.get("baseline_model", {}).get("artifact_sha256"))
        for run in faasrank_runs
    }
    model_names = {
        str(run.get("baseline_model", {}).get("artifact_path")) for run in faasrank_runs
    }
    if model_hashes != {EXPECTED_FAASRANK_SHA256} or len(model_names) != 1:
        raise ProtocolValidationError("P2 FaaSRank binding is inconsistent")
    model_path = (source_path.parent / next(iter(model_names))).resolve()
    if file_hash(model_path) != EXPECTED_FAASRANK_SHA256:
        raise ProtocolValidationError("P2 frozen FaaSRank artifact changed")
    model_receipt = {
        "path": str(model_path),
        "bytes": model_path.stat().st_size,
        "sha256": EXPECTED_FAASRANK_SHA256,
    }
    return tape_receipts, reference_receipts, model_receipt


def build_middle_selection(
    source_manifest_path: Path,
    workspace: Path,
    *,
    plan_v4_path: Path,
    p1a_path: Path,
    p1b_path: Path,
    low_audit_path: Path,
    low_report_path: Path,
) -> dict[str, Any]:
    workspace = workspace.resolve()
    if workspace.exists():
        raise ProtocolValidationError(
            "P2 middle workspace must be absent at selection freeze"
        )
    if workspace.name != P2_MIDDLE_WORKSPACE_NAME:
        raise ProtocolValidationError(
            "P2 middle workspace name differs from preregistration"
        )

    source_path = source_manifest_path.resolve()
    source, selected = _source_and_runs(source_path)
    authorization = {
        "plan_v4": _receipt(plan_v4_path, EXPECTED_AUTHORIZATION_SHA256["plan_v4"]),
        "p1a": _receipt(p1a_path, EXPECTED_AUTHORIZATION_SHA256["p1a"]),
        "p1b": _receipt(p1b_path, EXPECTED_AUTHORIZATION_SHA256["p1b"]),
        "low_audit": _receipt(
            low_audit_path, EXPECTED_AUTHORIZATION_SHA256["low_audit"]
        ),
        "low_report": _receipt(
            low_report_path, EXPECTED_AUTHORIZATION_SHA256["low_report"]
        ),
    }
    _validate_low_report(low_report_path)
    tapes, references, faasrank = _input_receipts(source_path, selected)
    runtime = source["g1_formal_qualification"]["runtime_binary"]

    document: dict[str, Any] = {
        "schema_version": P2_MIDDLE_SELECTION_SCHEMA,
        "created_at": utc_now(),
        "status": "frozen_zero_result_selection",
        "scientific_metric_values_consulted": False,
        "result_conditioned_seed_or_run_selection": False,
        "source_manifest": {
            "path": str(source_path),
            "manifest_hash": source["manifest_hash"],
            "file_sha256": file_hash(source_path),
            "run_count": len(source["runs"]),
        },
        "authorization": authorization,
        "workspace": str(workspace),
        "selection": {
            "experiment_id": "E1",
            "topology": P2_MIDDLE_TOPOLOGY,
            "load": P2_MIDDLE_LOAD,
            "node_count": P2_MIDDLE_NODE_COUNT,
            "methods": list(FORMAL_E1_METHODS),
            "seeds": list(G1_FORMAL_QUALIFICATION_SEEDS),
            "run_count": len(selected),
            "run_ids": [str(run["run_id"]) for run in selected],
            "runs": [
                {
                    "run_id": str(run["run_id"]),
                    "run_spec_hash": str(run["run_spec_hash"]),
                    "method": str(run["method"]),
                    "seed": str(run["seed"]),
                    "workload_tape_key": str(run["workload_tape"]["key"]),
                    "workload_tape_sha256": str(run["workload_tape"]["sha256"]),
                }
                for run in selected
            ],
        },
        "runtime_binary": copy.deepcopy(runtime),
        "input_receipts": {
            "tapes": tapes,
            "references": references,
            "faasrank_model": faasrank,
        },
        "analysis_contract": {
            "all_first_qc_valid_rows_retained": True,
            "fixed_seed_count": 20,
            "full_qpr_coverage_required_for_progression": True,
            "bca_resamples": 10_000,
            "paired_permutation_resamples": 100_000,
            "holm_family_size": 18,
            "nash_must_rank_first": False,
            "possible_stop_rank_minimum": 6,
            "stop_requires_both_fifth_place_paired_bca_high_below_zero": True,
        },
    }
    document["document_sha256"] = object_hash(document)
    return document


def write_middle_selection(
    source_manifest_path: Path,
    workspace: Path,
    output_path: Path,
    **authorization_paths: Path,
) -> dict[str, Any]:
    if output_path.exists():
        raise ProtocolValidationError("refusing to overwrite P2 middle selection")
    document = build_middle_selection(
        source_manifest_path,
        workspace,
        **authorization_paths,
    )
    write_json_atomic(output_path, document)
    return document


def validate_middle_selection(path: Path) -> dict[str, Any]:
    selection = read_json(path)
    if not isinstance(selection, dict):
        raise ProtocolValidationError("P2 middle selection is not a JSON object")
    payload = copy.deepcopy(selection)
    document_sha256 = payload.pop("document_sha256", None)
    if (
        selection.get("schema_version") != P2_MIDDLE_SELECTION_SCHEMA
        or document_sha256 != object_hash(payload)
        or selection.get("status") != "frozen_zero_result_selection"
        or selection.get("scientific_metric_values_consulted") is not False
        or selection.get("result_conditioned_seed_or_run_selection") is not False
    ):
        raise ProtocolValidationError("P2 middle selection receipt is invalid")

    source = selection.get("source_manifest", {})
    source_path = Path(str(source.get("path", ""))).resolve()
    source_doc, selected = _source_and_runs(source_path)
    if (
        source.get("manifest_hash") != source_doc["manifest_hash"]
        or source.get("file_sha256") != file_hash(source_path)
        or source.get("run_count") != 1_200
    ):
        raise ProtocolValidationError("P2 selection source receipt changed")
    expected_runs = [
        {
            "run_id": str(run["run_id"]),
            "run_spec_hash": str(run["run_spec_hash"]),
            "method": str(run["method"]),
            "seed": str(run["seed"]),
            "workload_tape_key": str(run["workload_tape"]["key"]),
            "workload_tape_sha256": str(run["workload_tape"]["sha256"]),
        }
        for run in selected
    ]
    declared = selection.get("selection", {})
    if (
        declared.get("run_count") != P2_MIDDLE_RUN_COUNT
        or declared.get("methods") != list(FORMAL_E1_METHODS)
        or declared.get("seeds") != list(G1_FORMAL_QUALIFICATION_SEEDS)
        or declared.get("run_ids") != [row["run_id"] for row in expected_runs]
        or declared.get("runs") != expected_runs
    ):
        raise ProtocolValidationError("P2 selected run allowlist changed")

    authorization = selection.get("authorization", {})
    for key, expected_sha in EXPECTED_AUTHORIZATION_SHA256.items():
        receipt = authorization.get(key, {})
        receipt_path = Path(str(receipt.get("path", ""))).resolve()
        if (
            receipt.get("sha256") != expected_sha
            or receipt.get("bytes") != receipt_path.stat().st_size
            or file_hash(receipt_path) != expected_sha
        ):
            raise ProtocolValidationError(f"P2 authorization receipt changed: {key}")
    _validate_low_report(Path(str(authorization["low_report"]["path"])))
    tapes, references, faasrank = _input_receipts(source_path, selected)
    if selection.get("input_receipts") != {
        "tapes": tapes,
        "references": references,
        "faasrank_model": faasrank,
    }:
        raise ProtocolValidationError("P2 input receipts changed")

    runtime = selection.get("runtime_binary", {})
    if (
        runtime.get("source_git_commit") != EXPECTED_RUNTIME_SOURCE_COMMIT
        or runtime.get("sha256") != EXPECTED_RUNTIME_SHA256
        or runtime.get("bytes") != EXPECTED_RUNTIME_BYTES
        or file_hash(Path(str(runtime.get("path", ""))).resolve())
        != EXPECTED_RUNTIME_SHA256
    ):
        raise ProtocolValidationError("P2 runtime receipt changed")
    return selection


def execute_middle_selection(path: Path) -> dict[str, Any]:
    selection = validate_middle_selection(path)
    source_path = Path(selection["source_manifest"]["path"])
    workspace = Path(selection["workspace"])
    run_ids = list(selection["selection"]["run_ids"])
    runner = ProtocolRunner(source_path, workspace)
    results = runner.run(run_ids=run_ids)
    counts = Counter(str(result["status"]) for result in results)
    return {
        "schema_version": "NSE_P2_HOMOGENEOUS_MIDDLE_EXECUTION_SUMMARY_V1",
        "selection_document_sha256": selection["document_sha256"],
        "selected_run_count": len(run_ids),
        "status_counts": dict(sorted(counts.items())),
        "blocked": any(
            result["status"] in {"blocked", "preflight_blocked"} for result in results
        ),
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)
    freeze = subparsers.add_parser("freeze", help="write the zero-result run allowlist")
    freeze.add_argument("source_manifest", type=Path)
    freeze.add_argument("workspace", type=Path)
    freeze.add_argument("output", type=Path)
    freeze.add_argument("--plan-v4", type=Path, required=True)
    freeze.add_argument("--p1a", type=Path, required=True)
    freeze.add_argument("--p1b", type=Path, required=True)
    freeze.add_argument("--low-audit", type=Path, required=True)
    freeze.add_argument("--low-report", type=Path, required=True)
    run = subparsers.add_parser("run", help="execute the exact frozen allowlist")
    run.add_argument("selection", type=Path)
    validate = subparsers.add_parser("validate", help="revalidate a selection receipt")
    validate.add_argument("selection", type=Path)
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    if args.command == "freeze":
        result = write_middle_selection(
            args.source_manifest,
            args.workspace,
            args.output,
            plan_v4_path=args.plan_v4,
            p1a_path=args.p1a,
            p1b_path=args.p1b,
            low_audit_path=args.low_audit,
            low_report_path=args.low_report,
        )
    elif args.command == "validate":
        selection = validate_middle_selection(args.selection)
        result = {
            "status": "valid",
            "document_sha256": selection["document_sha256"],
            "run_count": selection["selection"]["run_count"],
        }
    else:
        result = execute_middle_selection(args.selection)
    import json

    print(json.dumps(result, indent=2, sort_keys=True))
    return 2 if result.get("blocked") is True else 0


if __name__ == "__main__":
    raise SystemExit(main())
