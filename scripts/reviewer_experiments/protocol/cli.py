from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

from .ledger import verify_ledger
from .faasrank_model import (
    create_faasrank_calibration_plan,
    freeze_faasrank_from_calibration,
    load_frozen_faasrank_model,
)
from .faasrank_calibration_stage import (
    capture_faasrank_training_tape,
    run_faasrank_calibration,
)
from .formal_e1_shard import (
    write_formal_e1_heterogeneous_shard,
    write_formal_e1_homogeneous_shard,
)
from .formal_e2_shard import write_formal_e2_weak_scaling_shard
from .formal_e3_e4_extension_shard import (
    write_formal_e3_e4_ci_extension_shard,
)
from .formal_e3_e4_shard import write_formal_e3_e4_initial_shard
from .formal_e5_e6_extension_shard import write_formal_e5_e6_ci_extension_shard
from .formal_e5_e6_e7_shard import write_formal_e5_e6_e7_initial_shard
from .matrix import (
    bind_faasrank_model,
    bind_sla_targets,
    bind_tape_catalog,
    dump_default_config,
    write_manifest,
)
from .qc import evaluate_attempt
from .reference import (
    bind_reference_catalog,
    inspect_reference_table,
    register_reference_build,
)
from .runner import ProtocolRunner
from .schema import ProtocolValidationError, load_and_validate_manifest
from .sla import freeze_sla_targets, load_frozen_sla_targets
from .sla_pilots import run_isolated_sla_pilots
from .smoke_shard import DEFAULT_SMOKE_PURPOSE, write_integration_smoke_shard
from .stages import build_references, capture_base_tapes
from .tape import (
    BURST_TRANSFORMS,
    derive_burst_tape,
    derive_required_tapes,
    derive_scaled_tape,
    inspect_tape,
    project_tape_catalog_for_manifest,
    register_base_tape,
    register_catalog_entry,
)
from .technical_timeout_recovery import (
    E2_ORIGINAL_RUNTIME_IDENTITY,
    TechnicalTimeoutRecoveryRunner,
    build_recovery_manifest,
    merge_timeout_recovery,
    plan_timeout_recovery,
    plan_timeout_recovery_tier2,
    validate_timeout_recovery_plan,
)
from .util import read_json, write_json_atomic


def _print_json(value: Any) -> None:
    print(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Result-blind TSC reviewer experiment protocol"
    )
    subparsers = parser.add_subparsers(dest="subcommand", required=True)

    init = subparsers.add_parser(
        "init-config", help="write an editable copy of the frozen protocol defaults"
    )
    init.add_argument("output", type=Path)

    expand = subparsers.add_parser(
        "expand", help="expand the E1-E9 declaration into a run manifest"
    )
    expand.add_argument("output", type=Path)
    expand.add_argument("--config", type=Path)
    expand.add_argument(
        "--seed-stage", choices=("initial", "ci_extension", "all"), default="initial"
    )

    shard_smoke = subparsers.add_parser(
        "shard-smoke",
        help="derive a selected, explicitly non-formal integration-smoke manifest",
    )
    shard_smoke.add_argument("source", type=Path)
    shard_smoke.add_argument("output", type=Path)
    shard_smoke.add_argument(
        "--run-id",
        action="append",
        dest="run_ids",
        required=True,
        help="exact source run ID to include; repeat to select multiple runs",
    )
    shard_smoke.add_argument("--purpose", default=DEFAULT_SMOKE_PURPOSE)

    shard_e1 = subparsers.add_parser(
        "shard-e1-homogeneous",
        help=(
            "derive the complete formal E1 homogeneous block fixed by the "
            "source manifest's seed stage"
        ),
    )
    shard_e1.add_argument("source", type=Path)
    shard_e1.add_argument("output", type=Path)

    shard_e1_heterogeneous = subparsers.add_parser(
        "shard-e1-heterogeneous",
        help=(
            "derive the complete formal E1 heterogeneous block fixed by the "
            "source manifest's seed stage"
        ),
    )
    shard_e1_heterogeneous.add_argument("source", type=Path)
    shard_e1_heterogeneous.add_argument("output", type=Path)

    shard_e2 = subparsers.add_parser(
        "shard-e2",
        help=(
            "derive the complete formal E2 100/500-node weak-scaling block "
            "and seal its E1 20-node reuse source"
        ),
    )
    shard_e2.add_argument("source", type=Path)
    shard_e2.add_argument("output", type=Path)

    shard_e3_e4 = subparsers.add_parser(
        "shard-e3-e4",
        help=(
            "derive the complete bank-A E3 burst and E4 steady balanced-QoS "
            "formal block"
        ),
    )
    shard_e3_e4.add_argument("source", type=Path)
    shard_e3_e4.add_argument("output", type=Path)

    shard_e3_e4_extension = subparsers.add_parser(
        "shard-e3-e4-ci-extension",
        help=(
            "derive the complete E11-E20 E3 burst and E4 steady "
            "balanced-QoS bank-B block"
        ),
    )
    shard_e3_e4_extension.add_argument("source", type=Path)
    shard_e3_e4_extension.add_argument("output", type=Path)

    shard_e5_e6_e7 = subparsers.add_parser(
        "shard-e5-e6-e7",
        help=(
            "derive the complete bank-A physical E5/E6/E7 block and seal "
            "its heterogeneous E1 reuse lineage"
        ),
    )
    shard_e5_e6_e7.add_argument("source", type=Path)
    shard_e5_e6_e7.add_argument("output", type=Path)

    shard_e5_e6_extension = subparsers.add_parser(
        "shard-e5-e6-ci-extension",
        help=(
            "derive the complete E11-E20 E5/E6/E7 bank-B block "
            "and seal its heterogeneous E1 reuse lineage"
        ),
    )
    shard_e5_e6_extension.add_argument("source", type=Path)
    shard_e5_e6_extension.add_argument("output", type=Path)

    validate = subparsers.add_parser(
        "validate", help="validate a run manifest and its hashes"
    )
    validate.add_argument("manifest", type=Path)

    inspect = subparsers.add_parser(
        "inspect-tape", help="stream-validate and hash one workload tape"
    )
    inspect.add_argument("tape", type=Path)
    inspect.add_argument("--mode", choices=("auto", "small", "stream"), default="auto")

    register = subparsers.add_parser(
        "register-tape", help="register an immutable captured base tape"
    )
    register.add_argument("catalog", type=Path)
    register.add_argument("key")
    register.add_argument("tape", type=Path)
    register.add_argument("--mode", choices=("auto", "small", "stream"), default="auto")

    burst = subparsers.add_parser(
        "derive-burst", help="CDF-remap a steady tape without changing its event count"
    )
    burst.add_argument("catalog", type=Path)
    burst.add_argument("key")
    burst.add_argument("parent", type=Path)
    burst.add_argument("output", type=Path)
    burst.add_argument("scenario", choices=tuple(BURST_TRANSFORMS))
    burst.add_argument("--horizon-frames", type=int, default=1000)
    burst.add_argument("--mode", choices=("auto", "small", "stream"), default="auto")

    scale = subparsers.add_parser(
        "derive-scale", help="derive an exact same-frame 5x or 25x workload tape"
    )
    scale.add_argument("catalog", type=Path)
    scale.add_argument("key")
    scale.add_argument("parent", type=Path)
    scale.add_argument("output", type=Path)
    scale.add_argument("factor", type=int, choices=(5, 25))
    scale.add_argument("--mode", choices=("auto", "small", "stream"), default="auto")

    derive_required = subparsers.add_parser(
        "derive-required-tapes",
        help="derive all missing E2/E3 tapes declared by a manifest",
    )
    derive_required.add_argument("manifest", type=Path)
    derive_required.add_argument("catalog", type=Path)
    derive_required.add_argument("--output-root", type=Path, default=Path("."))
    derive_required.add_argument(
        "--mode", choices=("auto", "small", "stream"), default="auto"
    )

    project_catalog = subparsers.add_parser(
        "project-tape-catalog",
        help=(
            "project an audited source catalog to the exact keys required by a "
            "target manifest and deterministically derive missing E2/E3 tapes"
        ),
    )
    project_catalog.add_argument("manifest", type=Path)
    project_catalog.add_argument("source_catalog", type=Path)
    project_catalog.add_argument("output_catalog", type=Path)
    project_catalog.add_argument("--output-root", type=Path, default=Path("."))
    project_catalog.add_argument(
        "--mode", choices=("auto", "small", "stream"), default="auto"
    )

    export_e2 = subparsers.add_parser(
        "export-e2-with-e1-reuse",
        help=(
            "strictly audit formal E1/E2 canonical products and export the "
            "sealed 20/100/500-node weak-scaling table"
        ),
    )
    export_e2.add_argument("--e2-manifest", type=Path, required=True)
    export_e2.add_argument("--e2-workspace", type=Path, required=True)
    export_e2.add_argument("--e1-manifest", type=Path, required=True)
    export_e2.add_argument("--e1-workspace", type=Path, required=True)
    export_e2.add_argument("--output", type=Path, required=True)
    export_e2.add_argument("--coverage", type=Path, required=True)
    export_e2.add_argument("--audit", type=Path, required=True)

    bind = subparsers.add_parser(
        "bind-tapes", help="hash-bind a complete tape catalog into a new manifest"
    )
    bind.add_argument("manifest", type=Path)
    bind.add_argument("catalog", type=Path)
    bind.add_argument("output", type=Path)

    inspect_model = subparsers.add_parser(
        "inspect-faasrank-model",
        help="strictly inspect a frozen linear FaaSRank placement model",
    )
    inspect_model.add_argument("artifact", type=Path)

    preregister_model = subparsers.add_parser(
        "preregister-faasrank-calibration",
        help=(
            "immutably preregister frozen-objective FaaSRank candidates and "
            "training seeds before calibration runs"
        ),
    )
    preregister_model.add_argument("output", type=Path)
    preregister_model.add_argument("--training-tape", type=Path, required=True)
    preregister_model.add_argument(
        "--candidates",
        type=Path,
        required=True,
        help="JSON list of candidate objects containing exactly weights and epsilon",
    )
    preregister_model.add_argument(
        "--seed",
        action="append",
        dest="training_seeds",
        required=True,
        help="preregistered training seed; repeat for every paired seed",
    )

    capture_training_tape = subparsers.add_parser(
        "capture-faasrank-training-tape",
        help=(
            "capture one measured FaaSRank calibration tape whose workload seed "
            "and hash are disjoint from every formal evaluation tape"
        ),
    )
    capture_training_tape.add_argument("manifest", type=Path)
    capture_training_tape.add_argument("workspace", type=Path)
    capture_training_tape.add_argument("--workload-seed", default="FAASRANK-TRAIN-W01")
    capture_training_tape.add_argument("--template-seed", default="E01")
    capture_training_tape.add_argument(
        "--load", choices=("low", "middle", "high"), default="low"
    )

    run_model_calibration = subparsers.add_parser(
        "run-faasrank-calibration",
        help=(
            "execute every preregistered FaaSRank candidate-by-seed cell on the "
            "independent training tape before model selection"
        ),
    )
    run_model_calibration.add_argument("manifest", type=Path)
    run_model_calibration.add_argument("workspace", type=Path)
    run_model_calibration.add_argument("--training-tape", type=Path, required=True)
    run_model_calibration.add_argument("--plan", type=Path, required=True)
    run_model_calibration.add_argument("--template-seed", default="E01")
    run_model_calibration.add_argument(
        "--load", choices=("low", "middle", "high"), default="low"
    )

    freeze_model = subparsers.add_parser(
        "freeze-faasrank-model",
        help=(
            "freeze the uniquely selected linear Score-Rank-Select model from "
            "a preregistered plan and hash-bound real training results"
        ),
    )
    freeze_model.add_argument("output", type=Path)
    freeze_model.add_argument("--training-tape", type=Path, required=True)
    freeze_model.add_argument("--plan", type=Path, required=True)
    freeze_model.add_argument("--training-results", type=Path, required=True)

    bind_model = subparsers.add_parser(
        "bind-faasrank-model",
        help="bind a frozen model to an already tape-bound manifest",
    )
    bind_model.add_argument("manifest", type=Path)
    bind_model.add_argument("artifact", type=Path)
    bind_model.add_argument("output", type=Path)

    inspect_reference = subparsers.add_parser(
        "inspect-reference", help="stream-validate an offline social-reference JSONL"
    )
    inspect_reference.add_argument("table", type=Path)

    register_reference = subparsers.add_parser(
        "register-reference", help="register a table plus its immutable build receipt"
    )
    register_reference.add_argument("catalog", type=Path)
    register_reference.add_argument("key")
    register_reference.add_argument("table", type=Path)
    register_reference.add_argument("receipt", type=Path)

    bind_references = subparsers.add_parser(
        "bind-references",
        help="hash-bind all offline reference builds into a new manifest",
    )
    bind_references.add_argument("manifest", type=Path)
    bind_references.add_argument("catalog", type=Path)
    bind_references.add_argument("output", type=Path)

    capture = subparsers.add_parser(
        "capture-base-tapes",
        help="run measured same-seed captures for unique base-tape keys",
    )
    capture.add_argument("manifest", type=Path)
    capture.add_argument("workspace", type=Path)
    capture.add_argument("catalog", type=Path)
    capture.add_argument("--key", action="append", dest="keys")

    build_reference = subparsers.add_parser(
        "build-references", help="execute measured offline-reference build dependencies"
    )
    build_reference.add_argument("manifest", type=Path)
    build_reference.add_argument("workspace", type=Path)
    build_reference.add_argument("catalog", type=Path)
    build_reference.add_argument("--key", action="append", dest="keys")
    build_reference.add_argument("--run-id", action="append", dest="run_ids")

    freeze_sla = subparsers.add_parser(
        "freeze-sla",
        help="freeze SLA targets from completed, explicitly isolated pilot summaries",
    )

    run_sla_pilots = subparsers.add_parser(
        "run-sla-pilots",
        help="run the three isolated QoS pilots and a predeclared capacity bracket",
    )
    run_sla_pilots.add_argument("manifest", type=Path)
    run_sla_pilots.add_argument("workspace", type=Path)
    run_sla_pilots.add_argument("--seed", default="E01")
    run_sla_pilots.add_argument(
        "--load", choices=("low", "middle", "high"), default="low"
    )
    run_sla_pilots.add_argument(
        "--topology", choices=("homogeneous", "heterogeneous"), default="homogeneous"
    )
    run_sla_pilots.add_argument(
        "--capacity-factor",
        type=int,
        action="append",
        dest="capacity_factors",
        help="predeclared integer capacity candidate; repeat (default: 1,2,3,4)",
    )
    run_sla_pilots.add_argument(
        "--capacity-base-divisor",
        type=int,
        default=1,
        help=(
            "derive a nested lower-base grid k/divisor for k=1..divisor; "
            "default 1 preserves same-frame replication"
        ),
    )
    run_sla_pilots.add_argument("--total-frame", type=int, default=4000)
    run_sla_pilots.add_argument("--arrival-horizon-frames", type=int, default=1000)
    run_sla_pilots.add_argument("--minimum-completion-ratio", type=float, default=0.99)
    freeze_sla.add_argument("output", type=Path)
    freeze_sla.add_argument(
        "--latency-pilot",
        type=Path,
        action="append",
        required=True,
        help="completed isolated all_latency pilot artifact; repeat for three seeds",
    )
    freeze_sla.add_argument(
        "--throughput-pilot",
        type=Path,
        action="append",
        required=True,
        help=(
            "completed isolated all_throughput capacity-pilot artifact; "
            "repeat for three seeds"
        ),
    )
    freeze_sla.add_argument(
        "--cost-pilot",
        type=Path,
        action="append",
        required=True,
        help="completed isolated all_cost pilot artifact; repeat for three seeds",
    )
    freeze_sla.add_argument(
        "--replace-existing-sha256",
        help="replace only if the current output file has this exact SHA-256",
    )

    bind_sla = subparsers.add_parser(
        "bind-sla",
        help="bind frozen isolated-pilot SLA targets into a manifest",
    )
    bind_sla.add_argument("manifest", type=Path)
    bind_sla.add_argument("artifact", type=Path)
    bind_sla.add_argument("output", type=Path)

    qc = subparsers.add_parser(
        "qc", help="apply result-blind QC to one declared result"
    )
    qc.add_argument("manifest", type=Path)
    qc.add_argument("run_id")
    qc.add_argument("result", type=Path)
    qc.add_argument("--exit-code", type=int, default=0)
    qc.add_argument("--timed-out", action="store_true")
    qc.add_argument("--stdout", type=Path)
    qc.add_argument("--stderr", type=Path)
    qc.add_argument("--artifact-root", type=Path)
    qc.add_argument("--output", type=Path)

    run = subparsers.add_parser(
        "run",
        help="run selected manifest entries with at most three same-seed attempts",
    )
    run.add_argument("manifest", type=Path)
    run.add_argument("workspace", type=Path)
    run.add_argument("--run-id", action="append", dest="run_ids")
    run.add_argument(
        "--experiment",
        action="append",
        dest="experiment_ids",
        choices=[f"E{i}" for i in range(1, 8)],
    )
    run.add_argument(
        "--method",
        action="append",
        dest="methods",
        help="run only this declared method; repeat for a frozen method set",
    )
    run.add_argument(
        "--command",
        nargs=argparse.REMAINDER,
        help="optional command override; supports {python}, {run_config}, {result_path}, {partial_dir}, {run_id}, {attempt}",
    )

    promote = subparsers.add_parser(
        "promote-completed-partial",
        help=(
            "promote one fully verified completed partial attempt without "
            "re-executing the simulator"
        ),
    )
    promote.add_argument("manifest", type=Path)
    promote.add_argument("workspace", type=Path)
    promote.add_argument("run_id")
    promote.add_argument("--attempt", type=int, required=True)

    timeout_plan = subparsers.add_parser(
        "plan-timeout-recovery",
        help=(
            "derive a sealed, result-blind 3600/3590 technical timeout "
            "recovery plan from repeated timeout blocks"
        ),
    )
    timeout_plan.add_argument("manifest", type=Path)
    timeout_plan.add_argument("base_workspace", type=Path)
    timeout_plan.add_argument("plan", type=Path)

    timeout_plan_tier2 = subparsers.add_parser(
        "plan-timeout-recovery-tier2",
        help=(
            "derive the fixed 7200/7190 tier-2 recovery plan from one completed "
            "tier-1 technical recovery workspace"
        ),
    )
    timeout_plan_tier2.add_argument("previous_plan", type=Path)
    timeout_plan_tier2.add_argument("previous_recovery_workspace", type=Path)
    timeout_plan_tier2.add_argument("plan", type=Path)

    timeout_run = subparsers.add_parser(
        "run-timeout-recovery",
        help="run the complete sealed technical timeout recovery plan",
    )
    timeout_run.add_argument("plan", type=Path)

    timeout_merge = subparsers.add_parser(
        "merge-timeout-recovery",
        help="strictly merge original and independent timeout-recovery canonical runs",
    )
    timeout_merge.add_argument("manifest", type=Path)
    timeout_merge.add_argument("base_workspace", type=Path)
    timeout_merge.add_argument("plan", type=Path)
    timeout_merge.add_argument("recovery_workspace", type=Path)
    timeout_merge.add_argument("composite_workspace", type=Path)

    ledger = subparsers.add_parser(
        "verify-ledger", help="verify the append-only ledger hash chain"
    )
    ledger.add_argument("ledger", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        if args.subcommand == "init-config":
            dump_default_config(args.output)
            _print_json({"status": "written", "path": str(args.output)})
            return 0
        if args.subcommand == "expand":
            manifest = write_manifest(args.output, args.config, args.seed_stage)
            _print_json(
                {
                    "status": "written",
                    "path": str(args.output),
                    **manifest["matrix_summary"],
                }
            )
            return 0
        if args.subcommand == "shard-smoke":
            manifest = write_integration_smoke_shard(
                args.source,
                args.output,
                args.run_ids,
                purpose=args.purpose,
            )
            _print_json(
                {
                    "status": "written_nonformal_smoke_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "formal_results_eligible": False,
                }
            )
            return 0
        if args.subcommand == "shard-e1-homogeneous":
            manifest = write_formal_e1_homogeneous_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e1_homogeneous_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e1-heterogeneous":
            manifest = write_formal_e1_heterogeneous_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e1_heterogeneous_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e2":
            manifest = write_formal_e2_weak_scaling_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e2_weak_scaling_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "e1_reuse_source_run_count": manifest[
                        "formal_e2_weak_scaling_shard"
                    ]["e1_reuse_source_run_count"],
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e3-e4":
            manifest = write_formal_e3_e4_initial_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e3_e4_initial_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "balanced_qos_run_count": manifest["formal_e3_e4_initial_shard"][
                        "selected_balanced_qos_run_count"
                    ],
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e3-e4-ci-extension":
            manifest = write_formal_e3_e4_ci_extension_shard(
                args.source,
                args.output,
            )
            marker = manifest["formal_e3_e4_ci_extension_shard"]
            _print_json(
                {
                    "status": "written_formal_e3_e4_ci_extension_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "balanced_qos_run_count": marker["selected_balanced_qos_run_count"],
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e5-e6-e7":
            manifest = write_formal_e5_e6_e7_initial_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e5_e6_e7_initial_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "e1_reuse_projection_count": manifest[
                        "formal_e5_e6_e7_initial_shard"
                    ]["e1_reuse_projection_count"],
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "shard-e5-e6-ci-extension":
            manifest = write_formal_e5_e6_ci_extension_shard(
                args.source,
                args.output,
            )
            _print_json(
                {
                    "status": "written_formal_e5_e6_ci_extension_shard",
                    "path": str(args.output.resolve()),
                    "manifest_hash": manifest["manifest_hash"],
                    "seed_stage": manifest["seed_stage"],
                    "run_count": len(manifest["runs"]),
                    "reference_build_count": len(
                        manifest["reference_build_dependencies"]
                    ),
                    "e1_reuse_projection_count": manifest[
                        "formal_e5_e6_ci_extension_shard"
                    ]["e1_reuse_projection_count"],
                    "formal_results_eligible": True,
                }
            )
            return 0
        if args.subcommand == "validate":
            manifest = load_and_validate_manifest(args.manifest)
            _print_json(
                {
                    "status": "valid",
                    "manifest_hash": manifest["manifest_hash"],
                    "run_count": len(manifest["runs"]),
                    "matrix_summary": manifest.get("matrix_summary"),
                }
            )
            return 0
        if args.subcommand == "inspect-tape":
            _print_json(inspect_tape(args.tape, args.mode).to_dict())
            return 0
        if args.subcommand == "register-tape":
            entry = register_base_tape(args.catalog, args.key, args.tape, args.mode)
            _print_json({"status": "registered", "key": args.key, **entry})
            return 0
        if args.subcommand == "derive-burst":
            entry = derive_burst_tape(
                args.parent,
                args.output,
                args.scenario,
                horizon_frames=args.horizon_frames,
                mode=args.mode,
            )
            register_catalog_entry(args.catalog, args.key, entry)
            _print_json({"status": "derived_and_registered", "key": args.key, **entry})
            return 0
        if args.subcommand == "derive-scale":
            entry = derive_scaled_tape(
                args.parent, args.output, args.factor, mode=args.mode
            )
            register_catalog_entry(args.catalog, args.key, entry)
            _print_json({"status": "derived_and_registered", "key": args.key, **entry})
            return 0
        if args.subcommand == "derive-required-tapes":
            manifest = load_and_validate_manifest(args.manifest)
            created = derive_required_tapes(
                manifest, args.catalog, args.output_root, mode=args.mode
            )
            _print_json(
                {"status": "derived", "created_count": len(created), "created": created}
            )
            return 0
        if args.subcommand == "project-tape-catalog":
            manifest = load_and_validate_manifest(args.manifest)
            catalog = project_tape_catalog_for_manifest(
                manifest,
                args.source_catalog,
                args.output_catalog,
                args.output_root,
                mode=args.mode,
            )
            _print_json(
                {
                    "status": "projected_tape_catalog",
                    "path": str(args.output_catalog.resolve()),
                    "catalog_hash": catalog["catalog_hash"],
                    "entry_count": len(catalog["entries"]),
                    "projected_source_count": len(
                        catalog["projection"]["projected_source_keys"]
                    ),
                    "derived_count": len(
                        catalog["projection"]["derived_after_projection_keys"]
                    ),
                }
            )
            return 0
        if args.subcommand == "export-e2-with-e1-reuse":
            from scripts.reviewer_experiments.analysis.e2_results import (
                export_e2_with_e1_reuse,
            )

            audit = export_e2_with_e1_reuse(
                e2_manifest_path=args.e2_manifest,
                e2_workspace=args.e2_workspace,
                e1_manifest_path=args.e1_manifest,
                e1_workspace=args.e1_workspace,
                output_csv=args.output,
                coverage_csv=args.coverage,
                audit_json=args.audit,
            )
            _print_json(
                {
                    "status": "exported_e2_with_e1_reuse",
                    "output": str(args.output.resolve()),
                    "coverage": str(args.coverage.resolve()),
                    "audit": str(args.audit.resolve()),
                    "combined_row_count": audit["combined_row_count"],
                    "audit_sha256": audit["audit_sha256"],
                }
            )
            return 0
        if args.subcommand == "bind-tapes":
            manifest = load_and_validate_manifest(args.manifest)
            catalog = read_json(args.catalog)
            bound = bind_tape_catalog(manifest, catalog)
            write_json_atomic(args.output, bound)
            _print_json(
                {
                    "status": "bound",
                    "path": str(args.output),
                    "manifest_hash": bound["manifest_hash"],
                    "run_count": len(bound["runs"]),
                }
            )
            return 0
        if args.subcommand == "inspect-faasrank-model":
            model = load_frozen_faasrank_model(args.artifact)
            _print_json(
                {
                    "status": "valid",
                    "path": model.path,
                    "artifact_sha256": model.artifact_sha256,
                    "artifact_bytes": model.artifact_bytes,
                    "training_tape_sha256": model.training_tape_sha256,
                    "weights": model.weights,
                    "epsilon": model.epsilon,
                    "created_at": model.created_at,
                    "provenance": model.provenance,
                }
            )
            return 0
        if args.subcommand == "preregister-faasrank-calibration":
            training = inspect_tape(args.training_tape, "auto")
            candidates = read_json(args.candidates)
            if not isinstance(candidates, list):
                raise ProtocolValidationError(
                    "FaaSRank candidates file must be a JSON list"
                )
            plan = create_faasrank_calibration_plan(
                args.output,
                training_tape_sha256=training.sha256,
                candidates=candidates,
                training_seeds=args.training_seeds,
            )
            _print_json(
                {
                    "status": "preregistered",
                    "path": plan.path,
                    "plan_sha256": plan.artifact_sha256,
                    "training_tape_sha256": plan.training_tape_sha256,
                    "candidate_count": len(plan.candidates),
                    "training_seeds": list(plan.training_seeds),
                }
            )
            return 0
        if args.subcommand == "capture-faasrank-training-tape":
            receipt = capture_faasrank_training_tape(
                args.manifest,
                args.workspace,
                training_workload_seed=args.workload_seed,
                template_seed=args.template_seed,
                load=args.load,
            )
            _print_json(receipt)
            return 0
        if args.subcommand == "run-faasrank-calibration":
            results = run_faasrank_calibration(
                args.manifest,
                args.workspace,
                training_tape_path=args.training_tape,
                calibration_plan_path=args.plan,
                template_seed=args.template_seed,
                load=args.load,
            )
            _print_json(results)
            return 0
        if args.subcommand == "freeze-faasrank-model":
            model = freeze_faasrank_from_calibration(
                args.output,
                training_tape_path=args.training_tape,
                calibration_plan_path=args.plan,
                training_results_path=args.training_results,
            )
            _print_json(
                {
                    "status": "frozen",
                    "path": model.path,
                    "artifact_sha256": model.artifact_sha256,
                    "training_tape_sha256": model.training_tape_sha256,
                    "selected_candidate_sha256": model.provenance["selection"][
                        "selected_candidate_sha256"
                    ],
                }
            )
            return 0
        if args.subcommand == "bind-faasrank-model":
            manifest = load_and_validate_manifest(args.manifest)
            try:
                stored_path = os.path.relpath(
                    args.artifact.resolve(), args.output.resolve().parent
                )
            except ValueError:
                stored_path = str(args.artifact.resolve())
            bound = bind_faasrank_model(
                manifest,
                args.artifact,
                manifest_artifact_path=Path(stored_path).as_posix(),
            )
            write_json_atomic(args.output, bound)
            _print_json(
                {
                    "status": "bound",
                    "path": str(args.output.resolve()),
                    "manifest_hash": bound["manifest_hash"],
                    "artifact_sha256": load_frozen_faasrank_model(
                        args.artifact
                    ).artifact_sha256,
                }
            )
            return 0
        if args.subcommand == "inspect-reference":
            _print_json(inspect_reference_table(args.table).to_dict())
            return 0
        if args.subcommand == "register-reference":
            entry = register_reference_build(
                args.catalog, args.key, args.table, args.receipt
            )
            _print_json({"status": "registered", **entry})
            return 0
        if args.subcommand == "bind-references":
            manifest = load_and_validate_manifest(args.manifest)
            catalog = read_json(args.catalog)
            bound = bind_reference_catalog(manifest, catalog)
            write_json_atomic(args.output, bound)
            _print_json(
                {
                    "status": "bound",
                    "path": str(args.output),
                    "manifest_hash": bound["manifest_hash"],
                    "run_count": len(bound["runs"]),
                }
            )
            return 0
        if args.subcommand == "capture-base-tapes":
            results = capture_base_tapes(
                args.manifest, args.workspace, args.catalog, keys=args.keys
            )
            _print_json(results)
            return 2 if any(result["status"] == "blocked" for result in results) else 0
        if args.subcommand == "build-references":
            results = build_references(
                args.manifest,
                args.workspace,
                args.catalog,
                keys=args.keys,
                run_ids=args.run_ids,
            )
            _print_json(results)
            return (
                2
                if any(
                    result["status"] in {"blocked", "preflight_blocked"}
                    for result in results
                )
                else 0
            )
        if args.subcommand == "freeze-sla":
            frozen = freeze_sla_targets(
                args.output,
                latency_pilot_path=args.latency_pilot,
                throughput_pilot_path=args.throughput_pilot,
                cost_pilot_path=args.cost_pilot,
                replace_existing_sha256=args.replace_existing_sha256,
            )
            _print_json(
                {
                    "status": "frozen",
                    "path": str(args.output.resolve()),
                    "document_sha256": frozen["document_sha256"],
                    "targets": frozen["targets"],
                }
            )
            return 0
        if args.subcommand == "run-sla-pilots":
            report = run_isolated_sla_pilots(
                args.manifest,
                args.workspace,
                seed=args.seed,
                load=args.load,
                topology=args.topology,
                capacity_factors=args.capacity_factors or (1, 2, 3, 4),
                capacity_base_divisor=args.capacity_base_divisor,
                total_frame=args.total_frame,
                arrival_horizon_frames=args.arrival_horizon_frames,
                minimum_completion_ratio=args.minimum_completion_ratio,
            )
            _print_json(report)
            return 0
        if args.subcommand == "bind-sla":
            manifest = load_and_validate_manifest(args.manifest)
            try:
                stored_path = os.path.relpath(
                    args.artifact.resolve(), args.output.resolve().parent
                )
            except ValueError:
                stored_path = str(args.artifact.resolve())
            bound = bind_sla_targets(
                manifest,
                args.artifact,
                manifest_artifact_path=Path(stored_path).as_posix(),
            )
            write_json_atomic(args.output, bound)
            frozen = load_frozen_sla_targets(args.artifact)
            _print_json(
                {
                    "status": "bound",
                    "path": str(args.output.resolve()),
                    "manifest_hash": bound["manifest_hash"],
                    "artifact_sha256": frozen.artifact_sha256,
                    "targets": frozen.targets,
                }
            )
            return 0
        if args.subcommand == "qc":
            manifest = load_and_validate_manifest(args.manifest)
            matches = [run for run in manifest["runs"] if run["run_id"] == args.run_id]
            if len(matches) != 1:
                raise ProtocolValidationError(
                    f"manifest does not contain exactly one run {args.run_id!r}"
                )
            report = evaluate_attempt(
                matches[0],
                manifest["qc"],
                args.result,
                exit_code=args.exit_code,
                timed_out=args.timed_out,
                stdout_path=args.stdout,
                stderr_path=args.stderr,
                artifact_root=args.artifact_root,
            )
            if args.output:
                write_json_atomic(args.output, report.to_dict())
            _print_json(report.to_dict())
            return 0 if report.passed else 2
        if args.subcommand == "plan-timeout-recovery":
            plan = plan_timeout_recovery(
                args.manifest,
                args.base_workspace,
                args.plan,
                expected_runtime_identity=E2_ORIGINAL_RUNTIME_IDENTITY,
            )
            _print_json(
                {
                    "status": "planned",
                    "path": str(args.plan.resolve()),
                    "plan_sha256": plan["plan_sha256"],
                    "source_manifest_hash": plan["source"]["manifest_hash"],
                    "source_ledger_sequence": plan["source"]["ledger_sequence"],
                    "run_ids": plan["selection"]["run_ids"],
                    "timeout_seconds": plan["execution_override"]["timeout_seconds"],
                    "adapter_request_timeout_seconds": plan["execution_override"][
                        "adapter_request_timeout_seconds"
                    ],
                    "metrics_consulted": False,
                }
            )
            return 0
        if args.subcommand == "plan-timeout-recovery-tier2":
            plan = plan_timeout_recovery_tier2(
                args.previous_plan,
                args.previous_recovery_workspace,
                args.plan,
            )
            _print_json(
                {
                    "status": "planned",
                    "path": str(args.plan.resolve()),
                    "plan_sha256": plan["plan_sha256"],
                    "source_manifest_hash": plan["source"]["manifest_hash"],
                    "source_ledger_sequence": plan["source"]["ledger_sequence"],
                    "run_ids": plan["selection"]["run_ids"],
                    "timeout_seconds": plan["execution_override"]["timeout_seconds"],
                    "adapter_request_timeout_seconds": plan["execution_override"][
                        "adapter_request_timeout_seconds"
                    ],
                    "metrics_consulted": False,
                }
            )
            return 0
        if args.subcommand == "run-timeout-recovery":
            plan = validate_timeout_recovery_plan(args.plan)
            workspace = Path(plan["recovery"]["workspace"]).resolve()
            manifest_path = Path(plan["recovery"]["manifest_path"]).resolve()
            if not manifest_path.exists():
                source_manifest_path = Path(plan["source"]["manifest_path"])
                build_recovery_manifest(
                    source_manifest_path,
                    plan,
                    manifest_path=manifest_path,
                )
            runner = TechnicalTimeoutRecoveryRunner(
                manifest_path,
                workspace,
                args.plan,
            )
            results = runner.run()
            _print_json(
                {
                    "status": "completed",
                    "plan_sha256": plan["plan_sha256"],
                    "workspace": str(workspace),
                    "results": results,
                    "metrics_consulted": False,
                }
            )
            return (
                2
                if any(
                    result.get("status") in {"blocked", "preflight_blocked"}
                    for result in results
                )
                else 0
            )
        if args.subcommand == "merge-timeout-recovery":
            merged = merge_timeout_recovery(
                args.manifest,
                args.base_workspace,
                args.plan,
                args.recovery_workspace,
                args.composite_workspace,
            )
            _print_json(merged)
            return 0
        if args.subcommand == "run":
            command = args.command
            if command and command[0] == "--":
                command = command[1:]
            runner = ProtocolRunner(args.manifest, args.workspace)
            results = runner.run(
                run_ids=args.run_ids,
                experiment_ids=args.experiment_ids,
                methods=args.methods,
                command_override=command or None,
            )
            _print_json(results)
            return (
                2
                if any(
                    result["status"] in {"blocked", "preflight_blocked"}
                    for result in results
                )
                else 0
            )
        if args.subcommand == "promote-completed-partial":
            runner = ProtocolRunner(args.manifest, args.workspace)
            result = runner.promote_completed_partial(args.run_id, args.attempt)
            _print_json(result)
            return 0
        if args.subcommand == "verify-ledger":
            sequence, last_hash = verify_ledger(args.ledger)
            _print_json({"status": "valid", "events": sequence, "last_hash": last_hash})
            return 0
    except (OSError, ProtocolValidationError, RuntimeError, ValueError) as exc:
        print(f"protocol error: {exc}", file=sys.stderr)
        return 2
    return 2
