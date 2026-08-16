"""Cross-method pairing audit for canonical formal experiment results.

This audit is deliberately independent from metric values.  It verifies that
the runs forming one paired comparison used the same immutable workload and
the same runtime semantics before those runs are admitted to statistical
analysis.
"""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Any, Union

from .schema import validate_manifest
from .util import object_hash, read_json, utc_now, write_json_atomic


REPORT_SCHEMA = "NSE_PAIRED_ENVIRONMENT_AUDIT_V1"
HASH_RE = re.compile(r"^[0-9a-f]{64}$")
COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
AUDITED_FIELDS = (
    "workload_tape_sha256",
    "function_dag_qos_sha256",
    "workload_function_dag_qos_sha256",
    "node_network_sha256",
    "common_hpa_sha256",
    "simulation_sha256",
    "seed_tuple_sha256",
)
RUNTIME_AUDITED_FIELDS = (
    "runtime_binary_sha256",
    "runtime_git_commit",
    "runtime_python_executable_sha256",
    "runtime_cargo_lock_sha256",
)

ExpectedMethods = Union[Sequence[str], Mapping[str, Sequence[str]], None]


def scenario_descriptor(run: Mapping[str, Any]) -> dict[str, Any]:
    """Return the method-independent semantics identifying a comparison cell.

    Cluster size is explicit, so E2's 100- and 500-node weak-scaling cells can
    never be merged.  HPA, simulation and runtime hashes are intentionally not
    part of this key: differences in those values must be reported as pairing
    failures, not hidden by splitting the comparison into separate groups.
    """

    workload = run.get("workload")
    cluster = run.get("cluster")
    return {
        "experiment_id": run.get("experiment_id"),
        "variant": run.get("variant", "full"),
        "workload": workload if isinstance(workload, Mapping) else workload,
        "cluster": {
            "node_count": cluster.get("node_count")
            if isinstance(cluster, Mapping)
            else None,
            "topology": cluster.get("topology")
            if isinstance(cluster, Mapping)
            else None,
        },
    }


def pairing_group_key(run: Mapping[str, Any]) -> str:
    """Stable key for one paired seed-level comparison group."""

    return object_hash({"scenario": scenario_descriptor(run), "seed": run.get("seed")})


def pairing_cohort_key(run: Mapping[str, Any]) -> str:
    """Stable key for a scenario across seeds, used to infer method coverage."""

    return object_hash(scenario_descriptor(run))


def _normalise_methods(methods: Sequence[str], context: str) -> list[str]:
    if isinstance(methods, (str, bytes)):
        raise ValueError(f"{context} must be a sequence of method names")
    normalised = [str(method).strip() for method in methods]
    if any(not method for method in normalised):
        raise ValueError(f"{context} contains an empty method name")
    if len(normalised) != len(set(normalised)):
        raise ValueError(f"{context} contains duplicate method names")
    return sorted(normalised)


def _expected_for_group(
    run: Mapping[str, Any],
    inferred: Mapping[str, set[str]],
    expected_methods: ExpectedMethods,
) -> list[str]:
    if expected_methods is None:
        return sorted(inferred[pairing_cohort_key(run)])
    if not isinstance(expected_methods, Mapping):
        return _normalise_methods(expected_methods, "expected_methods")

    experiment_id = str(run.get("experiment_id"))
    variant = str(run.get("variant", "full"))
    for key in (f"{experiment_id}:{variant}", experiment_id, "*"):
        if key in expected_methods:
            return _normalise_methods(
                expected_methods[key], f"expected_methods[{key!r}]"
            )
    return sorted(inferred[pairing_cohort_key(run)])


def _failure(code: str, message: str, **details: Any) -> dict[str, Any]:
    return {"code": code, "message": message, "details": details}


def _read_run_evidence(
    run: Mapping[str, Any],
    canonical_root: Path,
    *,
    require_runtime_identity: bool = False,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]]]:
    run_id = str(run.get("run_id", ""))
    directory = canonical_root / run_id
    report_path = directory / "qc_report.json"
    failures: list[dict[str, Any]] = []
    if not directory.is_dir():
        return None, [
            _failure(
                "missing_canonical_run",
                "canonical run directory is missing",
                run_id=run_id,
                path=str(directory),
            )
        ]
    if not report_path.is_file():
        return None, [
            _failure(
                "missing_qc_report",
                "canonical run has no qc_report.json",
                run_id=run_id,
                path=str(report_path),
            )
        ]
    try:
        report = read_json(report_path)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        return None, [
            _failure(
                "invalid_qc_report",
                "qc_report.json cannot be parsed",
                run_id=run_id,
                path=str(report_path),
                error=str(exc),
            )
        ]
    if not isinstance(report, Mapping):
        return None, [
            _failure(
                "invalid_qc_report",
                "qc_report.json root must be an object",
                run_id=run_id,
                path=str(report_path),
            )
        ]
    if report.get("passed") is not True or report.get("classification") != "qc_pass":
        failures.append(
            _failure(
                "canonical_qc_not_passed",
                "canonical result does not carry a passing QC report",
                run_id=run_id,
                passed=report.get("passed"),
                classification=report.get("classification"),
            )
        )

    runtime_identity: dict[str, Any] = {
        field: None for field in RUNTIME_AUDITED_FIELDS
    }
    audit_path = directory / "manifest.json"
    audit: Mapping[str, Any] | None = None
    if audit_path.is_file():
        try:
            candidate = read_json(audit_path)
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            failures.append(
                _failure(
                    "invalid_audit_manifest",
                    "canonical manifest.json cannot be parsed",
                    run_id=run_id,
                    error=str(exc),
                )
            )
        else:
            if isinstance(candidate, Mapping):
                stored_hash = candidate.get("audit_manifest_hash")
                payload = dict(candidate)
                payload.pop("audit_manifest_hash", None)
                if (
                    candidate.get("status") != "canonical"
                    or not isinstance(stored_hash, str)
                    or object_hash(payload) != stored_hash
                ):
                    failures.append(
                        _failure(
                            "invalid_audit_manifest",
                            "canonical manifest status or self-hash is invalid",
                            run_id=run_id,
                        )
                    )
                else:
                    audit = candidate
            else:
                failures.append(
                    _failure(
                        "invalid_audit_manifest",
                        "canonical manifest.json root must be an object",
                        run_id=run_id,
                    )
                )
    elif require_runtime_identity:
        failures.append(
            _failure(
                "missing_audit_manifest",
                "formal canonical run lacks manifest.json runtime provenance",
                run_id=run_id,
                path=str(audit_path),
            )
        )

    if audit is not None:
        software = audit.get("software_environment")
        git = software.get("git") if isinstance(software, Mapping) else None
        python = software.get("python") if isinstance(software, Mapping) else None
        cargo_lock = (
            software.get("cargo_lock") if isinstance(software, Mapping) else None
        )
        binary = audit.get("adapter_binary")
        runtime_identity = {
            "runtime_binary_sha256": (
                binary.get("verified_sha256")
                if isinstance(binary, Mapping)
                else None
            ),
            "runtime_git_commit": (
                git.get("commit") if isinstance(git, Mapping) else None
            ),
            "runtime_python_executable_sha256": (
                python.get("executable_sha256")
                if isinstance(python, Mapping)
                else None
            ),
            "runtime_cargo_lock_sha256": (
                cargo_lock.get("sha256")
                if isinstance(cargo_lock, Mapping)
                else None
            ),
        }
    if require_runtime_identity:
        for field, value in runtime_identity.items():
            pattern = COMMIT_RE if field == "runtime_git_commit" else HASH_RE
            if not isinstance(value, str) or pattern.fullmatch(value) is None:
                failures.append(
                    _failure(
                        "invalid_runtime_identity",
                        f"{field} is absent or malformed",
                        run_id=run_id,
                        field=field,
                        value=value,
                    )
                )

    observations = report.get("observations")
    hashes = (
        observations.get("environment_semantic_hashes")
        if isinstance(observations, Mapping)
        else None
    )
    if not isinstance(hashes, Mapping):
        failures.append(
            _failure(
                "missing_environment_semantic_hashes",
                "passing QC report lacks environment semantic hashes",
                run_id=run_id,
            )
        )
        hashes = {}

    tape = run.get("workload_tape")
    tape_hash = tape.get("sha256") if isinstance(tape, Mapping) else None
    function_hash = hashes.get("function_dag_qos_sha256")
    node_hash = hashes.get("node_network_sha256")
    for field, value in (
        ("workload_tape_sha256", tape_hash),
        ("function_dag_qos_sha256", function_hash),
        ("node_network_sha256", node_hash),
        ("common_hpa_sha256", run.get("common_hpa_hash")),
    ):
        if not isinstance(value, str) or HASH_RE.fullmatch(value) is None:
            failures.append(
                _failure(
                    "invalid_pairing_hash",
                    f"{field} is absent or is not a SHA-256 digest",
                    run_id=run_id,
                    field=field,
                    value=value,
                )
            )

    experiment = run.get("simulator_experiment")
    seed_tuple = {
        "workload_seed": experiment.get("workload_seed")
        if isinstance(experiment, Mapping)
        else None,
        "topology_seed": experiment.get("topology_seed")
        if isinstance(experiment, Mapping)
        else None,
        "algorithm_seed": experiment.get("algorithm_seed")
        if isinstance(experiment, Mapping)
        else None,
    }
    evidence = {
        "run_id": run_id,
        "method": run.get("method"),
        "qc_report_path": str(report_path),
        "workload_tape_sha256": tape_hash,
        "function_dag_qos_sha256": function_hash,
        "workload_function_dag_qos_sha256": object_hash(
            {
                "workload_tape_sha256": tape_hash,
                "function_dag_qos_sha256": function_hash,
            }
        ),
        "node_network_sha256": node_hash,
        "common_hpa_sha256": run.get("common_hpa_hash"),
        "simulation_sha256": object_hash(run.get("simulation")),
        "seed_tuple": seed_tuple,
        "seed_tuple_sha256": object_hash(seed_tuple),
        **runtime_identity,
    }
    return evidence, failures


def audit_pairing_runs(
    runs: Sequence[Mapping[str, Any]],
    canonical_root: Path,
    *,
    expected_methods: ExpectedMethods = None,
    require_runtime_identity: bool = False,
) -> dict[str, Any]:
    """Audit method coverage and immutable inputs for a sequence of frozen runs."""

    groups: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
    inferred: dict[str, set[str]] = defaultdict(set)
    for run in runs:
        groups[pairing_group_key(run)].append(run)
        inferred[pairing_cohort_key(run)].add(str(run.get("method")))

    group_reports: list[dict[str, Any]] = []
    all_failures: list[dict[str, Any]] = []
    for group_key in sorted(groups):
        members = sorted(
            groups[group_key],
            key=lambda item: (str(item.get("method")), str(item.get("run_id"))),
        )
        representative = members[0]
        expected = _expected_for_group(representative, inferred, expected_methods)
        by_method: dict[str, list[Mapping[str, Any]]] = defaultdict(list)
        for run in members:
            by_method[str(run.get("method"))].append(run)
        observed = sorted(by_method)
        failures: list[dict[str, Any]] = []
        missing = sorted(set(expected) - set(observed))
        unexpected = sorted(set(observed) - set(expected))
        if missing:
            failures.append(
                _failure(
                    "missing_methods",
                    "paired group lacks one or more expected methods",
                    missing=missing,
                )
            )
        if unexpected:
            failures.append(
                _failure(
                    "unexpected_methods",
                    "paired group contains methods outside the expected comparison set",
                    unexpected=unexpected,
                )
            )
        duplicates = {
            method: len(items) for method, items in by_method.items() if len(items) != 1
        }
        if duplicates:
            failures.append(
                _failure(
                    "duplicate_method_runs",
                    "paired group contains multiple runs for one method",
                    counts=duplicates,
                )
            )

        evidence_rows: list[dict[str, Any]] = []
        for run in members:
            evidence, run_failures = _read_run_evidence(
                run,
                canonical_root,
                require_runtime_identity=require_runtime_identity,
            )
            for failure in run_failures:
                failure["details"].setdefault("method", run.get("method"))
            failures.extend(run_failures)
            if evidence is not None:
                evidence_rows.append(evidence)

        consensus: dict[str, Any] = {}
        audited_fields = AUDITED_FIELDS + (
            RUNTIME_AUDITED_FIELDS if require_runtime_identity else ()
        )
        for field in audited_fields:
            values: dict[str, list[str]] = defaultdict(list)
            for evidence in evidence_rows:
                values[str(evidence.get(field))].append(str(evidence.get("method")))
            consensus[field] = (
                next(iter(values)) if len(values) == 1 and values else None
            )
            if len(values) > 1:
                failures.append(
                    _failure(
                        "pairing_hash_mismatch",
                        f"paired methods disagree on {field}",
                        field=field,
                        values={
                            value: sorted(methods)
                            for value, methods in sorted(values.items())
                        },
                    )
                )

        descriptor = scenario_descriptor(representative)
        group_report = {
            "group_key": group_key,
            "cohort_key": pairing_cohort_key(representative),
            "experiment_id": representative.get("experiment_id"),
            "seed": representative.get("seed"),
            "variant": representative.get("variant", "full"),
            "scenario": descriptor,
            "expected_methods": expected,
            "observed_methods": observed,
            "missing_methods": missing,
            "unexpected_methods": unexpected,
            "consensus": consensus,
            "runs": evidence_rows,
            "passed": not failures,
            "failures": failures,
        }
        group_reports.append(group_report)
        for failure in failures:
            all_failures.append({"group_key": group_key, **failure})

    return {
        "schema": REPORT_SCHEMA,
        "created_at": utc_now(),
        "canonical_root": str(canonical_root.resolve()),
        "run_count": len(runs),
        "group_count": len(group_reports),
        "passed_group_count": sum(group["passed"] for group in group_reports),
        "failed_group_count": sum(not group["passed"] for group in group_reports),
        "passed": not all_failures,
        "failures": all_failures,
        "groups": group_reports,
    }


def audit_manifest_pairing(
    manifest: dict[str, Any],
    workspace: Path,
    *,
    expected_methods: ExpectedMethods = None,
) -> dict[str, Any]:
    """Validate a manifest, then audit its canonical results."""

    validate_manifest(manifest)
    canonical_root = (
        workspace if workspace.name == "canonical" else workspace / "canonical"
    )
    report = audit_pairing_runs(
        manifest["runs"],
        canonical_root,
        expected_methods=expected_methods,
        require_runtime_identity=manifest.get("formal_results_eligible") is True,
    )
    report["protocol_id"] = manifest["protocol_id"]
    report["protocol_manifest_sha256"] = manifest["manifest_hash"]
    return report


def _parse_expected(values: Sequence[str]) -> dict[str, list[str]] | None:
    parsed: dict[str, list[str]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError("--expected-methods requires KEY=method1,method2")
        key, raw_methods = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError("--expected-methods key cannot be empty")
        parsed[key] = _normalise_methods(
            raw_methods.split(","), f"expected_methods[{key!r}]"
        )
    return parsed or None


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("manifest", type=Path)
    parser.add_argument("workspace", type=Path)
    parser.add_argument("--output", type=Path)
    parser.add_argument(
        "--expected-methods",
        action="append",
        default=[],
        metavar="KEY=M1,M2",
        help="override methods for E6, E5:variant, or * (repeatable)",
    )
    args = parser.parse_args(argv)
    try:
        expected = _parse_expected(args.expected_methods)
        manifest = read_json(args.manifest)
        if not isinstance(manifest, dict):
            raise ValueError("manifest root must be an object")
        report = audit_manifest_pairing(
            manifest, args.workspace, expected_methods=expected
        )
    except (OSError, UnicodeError, json.JSONDecodeError, ValueError) as exc:
        parser.error(str(exc))
    if args.output is not None:
        write_json_atomic(args.output, report)
    print(json.dumps(report, ensure_ascii=False, sort_keys=True))
    return 0 if report["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
