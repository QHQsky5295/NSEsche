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
    register_base_tape,
    register_catalog_entry,
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
    run_sla_pilots.add_argument("--total-frame", type=int, default=4000)
    run_sla_pilots.add_argument("--arrival-horizon-frames", type=int, default=1000)
    run_sla_pilots.add_argument("--minimum-completion-ratio", type=float, default=0.99)
    freeze_sla.add_argument("output", type=Path)
    freeze_sla.add_argument(
        "--latency-pilot",
        type=Path,
        required=True,
        help="completed isolated all_latency pilot artifact",
    )
    freeze_sla.add_argument(
        "--throughput-pilot",
        type=Path,
        required=True,
        help="completed isolated all_throughput capacity-pilot artifact",
    )
    freeze_sla.add_argument(
        "--cost-pilot",
        type=Path,
        required=True,
        help="completed isolated all_cost pilot artifact",
    )
    freeze_sla.add_argument(
        "--replace-existing-sha256",
        help="replace only if the current output file has this exact SHA-256",
    )

    bind_sla = subparsers.add_parser(
        "bind-sla",
        help="bind frozen three-pilot SLA targets into a manifest",
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
        "--command",
        nargs=argparse.REMAINDER,
        help="optional command override; supports {python}, {run_config}, {result_path}, {partial_dir}, {run_id}, {attempt}",
    )

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
        if args.subcommand == "run":
            command = args.command
            if command and command[0] == "--":
                command = command[1:]
            runner = ProtocolRunner(args.manifest, args.workspace)
            results = runner.run(
                run_ids=args.run_ids,
                experiment_ids=args.experiment_ids,
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
        if args.subcommand == "verify-ledger":
            sequence, last_hash = verify_ledger(args.ledger)
            _print_json({"status": "valid", "events": sequence, "last_hash": last_hash})
            return 0
    except (OSError, ProtocolValidationError, RuntimeError, ValueError) as exc:
        print(f"protocol error: {exc}", file=sys.stderr)
        return 2
    return 2
