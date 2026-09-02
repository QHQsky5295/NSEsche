from __future__ import annotations

import copy
import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from .schema import ProtocolValidationError
from .util import file_hash, object_hash, utc_now, write_json_atomic


SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
PILOT_SCHEMA = "NSE_ISOLATED_SLA_PILOT_V1"
SUMMARY_SCHEMA = "NSE_SUMMARY_V1"
TARGET_SCHEMA = "NSE_FROZEN_SLA_TARGETS_V1"
EXPECTED_CLASS_ASSIGNMENT = {
    "latency_p95_ms": "all_latency",
    "sustainable_throughput_rps": "all_throughput",
    "cost_per_request": "all_cost",
}
MULTI_SEED_PILOT_COUNT = 3


class SlaFreezeError(ProtocolValidationError):
    """Raised when an SLA pilot artifact cannot support a frozen target."""


@dataclass(frozen=True)
class PilotMetric:
    role: str
    value: float
    json_path: str
    artifact_path: str
    artifact_sha256: str
    artifact_bytes: int
    artifact_schema: str
    artifact_id: str
    class_assignment: str
    class_assignment_evidence: list[dict[str, Any]]
    artifact_provenance: dict[str, Any]

    def source_record(self) -> dict[str, Any]:
        provenance = copy.deepcopy(self.artifact_provenance)
        return {
            "role": self.role,
            "path": self.artifact_path,
            "sha256": self.artifact_sha256,
            "bytes": self.artifact_bytes,
            "schema": self.artifact_schema,
            "artifact_id": self.artifact_id,
            "class_assignment": self.class_assignment,
            "class_assignment_evidence": copy.deepcopy(self.class_assignment_evidence),
            "json_path": self.json_path,
            "observed_value": self.value,
            "provenance": provenance,
            "provenance_sha256": object_hash(provenance),
        }


@dataclass(frozen=True)
class FrozenSlaTargets:
    path: str
    artifact_sha256: str
    artifact_bytes: int
    document_sha256: str
    targets_sha256: str
    targets: dict[str, float]
    frozen_at: str
    source_bundle_sha256: str


def _read_artifact(path: Path) -> tuple[dict[str, Any], bytes, str]:
    resolved = path.resolve()
    try:
        raw = resolved.read_bytes()
    except OSError as exc:
        raise SlaFreezeError(
            f"cannot read SLA pilot artifact {resolved}: {exc}"
        ) from exc

    def reject_constant(value: str) -> Any:
        raise ValueError(f"non-standard/nonfinite JSON constant {value}")

    def reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
        result: dict[str, Any] = {}
        for key, value in pairs:
            if key in result:
                raise ValueError(f"duplicate JSON key {key!r}")
            result[key] = value
        return result

    try:
        value = json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise SlaFreezeError(
            f"SLA pilot artifact is not valid UTF-8 JSON: {resolved}: {exc}"
        ) from exc
    if not isinstance(value, dict):
        raise SlaFreezeError(f"SLA pilot artifact must be a JSON object: {resolved}")
    return value, raw, hashlib.sha256(raw).hexdigest()


def _nested(document: dict[str, Any], path: tuple[str, ...]) -> Any:
    value: Any = document
    for component in path:
        if not isinstance(value, dict) or component not in value:
            return None
        value = value[component]
    return value


def _positive_finite(value: Any, *, field: str, path: Path) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise SlaFreezeError(f"{field} in {path.resolve()} must be numeric")
    result = float(value)
    if not math.isfinite(result) or result <= 0.0:
        raise SlaFreezeError(
            f"{field} in {path.resolve()} must be finite and greater than zero"
        )
    return result


def _schema(document: dict[str, Any], path: Path) -> str:
    schema = document.get("schema_version", document.get("schema"))
    if schema not in {PILOT_SCHEMA, SUMMARY_SCHEMA}:
        raise SlaFreezeError(
            f"unsupported SLA pilot schema in {path.resolve()}: {schema!r}; "
            f"expected {PILOT_SCHEMA} or {SUMMARY_SCHEMA}"
        )
    return str(schema)


def _validate_isolated(
    document: dict[str, Any],
    path: Path,
    class_assignment_evidence: list[dict[str, Any]],
) -> None:
    markers = [
        document.get("pilot_scope"),
        _nested(document, ("pilot", "scope")),
        _nested(document, ("provenance", "pilot_scope")),
    ]
    present = [marker for marker in markers if marker is not None]
    if any(marker != "isolated" for marker in present):
        raise SlaFreezeError(
            f"{path.resolve()} has a conflicting pilot scope "
            '(every declared pilot_scope must be "isolated")'
        )
    if not present and not class_assignment_evidence:
        raise SlaFreezeError(
            f"{path.resolve()} has no evidence that it is a class-isolated pilot"
        )


def _validate_completed(document: dict[str, Any], schema: str, path: Path) -> None:
    field = "completed" if schema == PILOT_SCHEMA else "run_complete"
    if document.get(field) is not True:
        raise SlaFreezeError(
            f"SLA pilot artifact {path.resolve()} does not have {field}=true"
        )


def _artifact_id(document: dict[str, Any], path: Path) -> str:
    value = document.get("pilot_id", document.get("run_id"))
    if not isinstance(value, str) or not value.strip():
        raise SlaFreezeError(
            f"SLA pilot artifact {path.resolve()} has no non-empty pilot_id/run_id"
        )
    return value


def _artifact_provenance(document: dict[str, Any]) -> dict[str, Any]:
    provenance = document.get("provenance", {})
    if provenance is None:
        provenance = {}
    if not isinstance(provenance, dict):
        raise SlaFreezeError("SLA pilot provenance must be a JSON object when present")
    return provenance


def _class_assignment(
    document: dict[str, Any],
    path: Path,
    role: str,
    artifact_id: str,
) -> tuple[str, list[dict[str, Any]]]:
    embedded_paths = (
        ("class_assignment",),
        ("pilot", "class_assignment"),
        ("provenance", "class_assignment"),
        ("config", "experiment", "qos", "class_assignment"),
        ("experiment", "qos", "class_assignment"),
        ("simulator_experiment", "qos", "class_assignment"),
    )
    evidence: list[dict[str, Any]] = []
    present: list[Any] = []
    for marker_path in embedded_paths:
        marker = _nested(document, marker_path)
        if marker is not None:
            present.append(marker)
            evidence.append(
                {
                    "kind": "pilot_artifact",
                    "json_path": ".".join(marker_path),
                    "value": marker,
                }
            )

    environment_path = path.resolve().parent / "environment.json"
    if environment_path.is_file() and environment_path != path.resolve():
        environment, raw, digest = _read_artifact(environment_path)
        environment_schema = environment.get(
            "schema_version", environment.get("schema")
        )
        if environment_schema != "NSE_ENVIRONMENT_V1":
            raise SlaFreezeError(
                f"sibling environment artifact has invalid schema: {environment_path}"
            )
        environment_run_id = environment.get("run_id")
        if environment_run_id is not None and environment_run_id != artifact_id:
            raise SlaFreezeError(
                f"sibling environment run_id {environment_run_id!r} does not match "
                f"pilot artifact id {artifact_id!r}"
            )
        marker = _nested(
            environment, ("config", "experiment", "qos", "class_assignment")
        )
        if marker is not None:
            present.append(marker)
            evidence.append(
                {
                    "kind": "sibling_environment",
                    "path": str(environment_path),
                    "sha256": digest,
                    "bytes": len(raw),
                    "schema": environment_schema,
                    "run_id": environment_run_id,
                    "json_path": "config.experiment.qos.class_assignment",
                    "value": marker,
                }
            )

    expected = EXPECTED_CLASS_ASSIGNMENT[role]
    if not present:
        raise SlaFreezeError(
            f"{path.resolve()} has no QoS class_assignment provenance; {role} must come from {expected}"
        )
    if any(marker != expected for marker in present):
        raise SlaFreezeError(
            f"{path.resolve()} has class_assignment={present!r}; {role} must come from {expected}"
        )
    return expected, evidence


def _first_metric(
    document: dict[str, Any],
    candidates: tuple[tuple[str, ...], ...],
) -> tuple[Any, str] | None:
    for path in candidates:
        value = _nested(document, path)
        if value is not None:
            return value, ".".join(path)
    return None


def _throughput_is_sustainable(document: dict[str, Any]) -> bool:
    markers = [
        document.get("throughput_is_sustainable"),
        _nested(document, ("pilot", "throughput_is_sustainable")),
        _nested(document, ("provenance", "throughput_is_sustainable")),
    ]
    present = [marker for marker in markers if marker is not None]
    return bool(present) and all(marker is True for marker in present)


def inspect_pilot_metric(path: Path, role: str) -> PilotMetric:
    """Read and validate exactly one observed metric from an isolated pilot.

    No aggregation, interpolation, or rounding is performed.  A normal simulator
    throughput summary is accepted only when its provenance explicitly states
    that the observed rate is the pilot's sustainable throughput.
    """

    document, raw, digest = _read_artifact(path)
    schema = _schema(document, path)
    _validate_completed(document, schema, path)
    artifact_id = _artifact_id(document, path)
    provenance = _artifact_provenance(document)
    class_assignment, class_assignment_evidence = _class_assignment(
        document, path, role, artifact_id
    )
    _validate_isolated(document, path, class_assignment_evidence)

    if role == "latency_p95_ms":
        found = _first_metric(
            document,
            (
                ("metrics", "latency_p95_ms"),
                ("metrics", "latency_ms", "p95"),
                ("latency_ms", "p95"),
                ("latency_p95_ms",),
            ),
        )
    elif role == "sustainable_throughput_rps":
        found = _first_metric(
            document,
            (
                ("metrics", "sustainable_throughput_rps"),
                ("sustainable_throughput_rps",),
            ),
        )
        if found is None:
            found = _first_metric(
                document,
                (
                    ("metrics", "throughput_requests_per_second"),
                    ("metrics", "throughput_rps"),
                    ("throughput_requests_per_second",),
                ),
            )
            if found is not None and not _throughput_is_sustainable(document):
                raise SlaFreezeError(
                    f"throughput in {path.resolve()} is an ordinary completed rate; "
                    "set throughput_is_sustainable=true in pilot provenance only after "
                    "the isolated sustainable-load pilot has established that fact"
                )
    elif role == "cost_per_request":
        found = _first_metric(
            document,
            (
                ("metrics", "cost_per_request"),
                ("metrics", "simulator_internal_cost_per_completed_request"),
                ("simulator_internal_cost_per_completed_request",),
                ("cost_per_request",),
            ),
        )
    else:
        raise SlaFreezeError(f"unknown SLA pilot metric role: {role}")

    if found is None:
        raise SlaFreezeError(f"{path.resolve()} does not contain {role}")
    raw_value, json_path = found
    value = _positive_finite(raw_value, field=role, path=path)
    return PilotMetric(
        role=role,
        value=value,
        json_path=json_path,
        artifact_path=str(path.resolve()),
        artifact_sha256=digest,
        artifact_bytes=len(raw),
        artifact_schema=schema,
        artifact_id=artifact_id,
        class_assignment=class_assignment,
        class_assignment_evidence=class_assignment_evidence,
        artifact_provenance=provenance,
    )


def _pilot_paths(value: Path | Iterable[Path], *, role: str) -> tuple[Path, ...]:
    if isinstance(value, Path):
        paths = (value,)
    else:
        paths = tuple(value)
    if not paths or any(not isinstance(path, Path) for path in paths):
        raise SlaFreezeError(f"{role} pilot paths must contain Path values")
    resolved = tuple(path.resolve() for path in paths)
    if len(set(resolved)) != len(resolved):
        raise SlaFreezeError(f"{role} pilot paths must be unique")
    return paths


def _pilot_seed(metric: PilotMetric) -> str:
    seed = metric.artifact_provenance.get("seed")
    if not isinstance(seed, str) or not seed.strip():
        raise SlaFreezeError(
            "multi-seed pilot artifact has no non-empty provenance.seed: "
            f"{metric.artifact_path}"
        )
    return seed


def _multi_seed_sources(
    metrics: dict[str, tuple[PilotMetric, ...]],
) -> tuple[dict[str, float], dict[str, Any], dict[str, Any]]:
    counts = {role: len(values) for role, values in metrics.items()}
    if set(counts.values()) != {MULTI_SEED_PILOT_COUNT}:
        raise SlaFreezeError(
            "multi-seed SLA freezing requires exactly three artifacts for each "
            f"role; observed counts={counts}"
        )
    by_role: dict[str, dict[str, PilotMetric]] = {}
    for role, values in metrics.items():
        indexed: dict[str, PilotMetric] = {}
        for metric in values:
            seed = _pilot_seed(metric)
            if seed in indexed:
                raise SlaFreezeError(f"duplicate {role} pilot seed: {seed}")
            indexed[seed] = metric
        by_role[role] = indexed
    seed_sets = {role: set(indexed) for role, indexed in by_role.items()}
    if len({tuple(sorted(seeds)) for seeds in seed_sets.values()}) != 1:
        raise SlaFreezeError(
            f"multi-seed SLA roles must use the same fixed seeds: {seed_sets}"
        )
    seeds = sorted(next(iter(seed_sets.values())))
    aggregations = {
        "latency_p95_ms": (max, "maximum_across_three_fixed_pilot_seeds"),
        "sustainable_throughput_rps": (
            min,
            "minimum_across_three_fixed_pilot_seeds",
        ),
        "cost_per_request": (max, "maximum_across_three_fixed_pilot_seeds"),
    }
    measurements: dict[str, float] = {}
    sources: dict[str, Any] = {}
    source_binding: dict[str, Any] = {}
    for role, (aggregate, policy) in aggregations.items():
        ordered = [by_role[role][seed] for seed in seeds]
        value = float(aggregate(metric.value for metric in ordered))
        records = [metric.source_record() for metric in ordered]
        measurements[role] = value
        sources[role] = {
            "aggregation": policy,
            "aggregated_value": value,
            "seed_count": len(seeds),
            "seeds": seeds,
            "inputs": records,
        }
        source_binding[role] = {
            "aggregation": policy,
            "aggregated_value": value,
            "inputs": [
                {
                    "seed": seed,
                    "sha256": record["sha256"],
                    "json_path": record["json_path"],
                    "observed_value": record["observed_value"],
                    "class_assignment": record["class_assignment"],
                    "class_assignment_evidence": record[
                        "class_assignment_evidence"
                    ],
                }
                for seed, record in zip(seeds, records)
            ],
        }
    return measurements, sources, source_binding


def freeze_sla_targets(
    output_path: Path,
    *,
    latency_pilot_path: Path | Iterable[Path],
    throughput_pilot_path: Path | Iterable[Path],
    cost_pilot_path: Path | Iterable[Path],
    replace_existing_sha256: str | None = None,
) -> dict[str, Any]:
    """Freeze targets from one or three fixed-seed class-isolated pilot sets."""

    metrics = {
        "latency_p95_ms": tuple(
            inspect_pilot_metric(path, "latency_p95_ms")
            for path in _pilot_paths(latency_pilot_path, role="latency")
        ),
        "sustainable_throughput_rps": tuple(
            inspect_pilot_metric(path, "sustainable_throughput_rps")
            for path in _pilot_paths(throughput_pilot_path, role="throughput")
        ),
        "cost_per_request": tuple(
            inspect_pilot_metric(path, "cost_per_request")
            for path in _pilot_paths(cost_pilot_path, role="cost")
        ),
    }

    sources_by_path: dict[str, str] = {}
    for values in metrics.values():
        for metric in values:
            previous_hash = sources_by_path.setdefault(
                metric.artifact_path, metric.artifact_sha256
            )
            if previous_hash != metric.artifact_sha256:
                raise SlaFreezeError(
                    "pilot artifact changed while it was being inspected: "
                    f"{metric.artifact_path}"
                )

    counts = {len(values) for values in metrics.values()}
    if counts == {1}:
        latency = metrics["latency_p95_ms"][0]
        throughput = metrics["sustainable_throughput_rps"][0]
        cost = metrics["cost_per_request"][0]
        aggregated = {
            "latency_p95_ms": latency.value,
            "sustainable_throughput_rps": throughput.value,
            "cost_per_request": cost.value,
        }
        sources = {
            "latency_p95_ms": latency.source_record(),
            "sustainable_throughput_rps": throughput.source_record(),
            "cost_per_request": cost.source_record(),
        }
        source_binding = {
            role: {
                "sha256": source["sha256"],
                "json_path": source["json_path"],
                "observed_value": source["observed_value"],
                "class_assignment": source["class_assignment"],
                "class_assignment_evidence": source[
                    "class_assignment_evidence"
                ],
            }
            for role, source in sources.items()
        }
        derivation_policy = (
            "three_class_isolated_pilots_direct_no_aggregation_no_rounding"
        )
        formulas = {
            "latency_deadline_ms": "1.5 * isolated_latency_p95_ms",
            "throughput_target_rps": "0.9 * isolated_sustainable_throughput_rps",
            "cost_budget_per_request": "1.25 * isolated_cost_per_request",
        }
        seed_aggregation = None
    else:
        aggregated, sources, source_binding = _multi_seed_sources(metrics)
        derivation_policy = (
            "three_fixed_seed_class_isolated_pilots_conservative_envelope_no_rounding"
        )
        formulas = {
            "latency_deadline_ms": (
                "1.5 * max_seed(isolated_latency_p95_ms)"
            ),
            "throughput_target_rps": (
                "0.9 * min_seed(isolated_sustainable_throughput_rps)"
            ),
            "cost_budget_per_request": (
                "1.25 * max_seed(isolated_cost_per_request)"
            ),
        }
        seed_aggregation = {
            "pilot_seed_count": MULTI_SEED_PILOT_COUNT,
            "latency": "maximum",
            "throughput": "minimum",
            "cost": "maximum",
        }

    measurements = {
        "isolated_latency_p95_ms": aggregated["latency_p95_ms"],
        "isolated_sustainable_throughput_rps": aggregated[
            "sustainable_throughput_rps"
        ],
        "isolated_cost_per_request": aggregated["cost_per_request"],
    }
    multipliers = {
        "latency_deadline": 1.5,
        "throughput_target": 0.9,
        "cost_budget": 1.25,
    }
    targets = {
        "latency_deadline_ms": (
            aggregated["latency_p95_ms"] * multipliers["latency_deadline"]
        ),
        "throughput_target_rps": (
            aggregated["sustainable_throughput_rps"]
            * multipliers["throughput_target"]
        ),
        "cost_budget_per_request": (
            aggregated["cost_per_request"] * multipliers["cost_budget"]
        ),
    }
    for name, value in targets.items():
        if not math.isfinite(value) or value <= 0.0:
            raise SlaFreezeError(f"derived target {name} is nonfinite or non-positive")
    document: dict[str, Any] = {
        "schema_version": TARGET_SCHEMA,
        "status": "frozen",
        "frozen_at": utc_now(),
        "derivation_policy": derivation_policy,
        "measurements": measurements,
        "multipliers": multipliers,
        "formulas": formulas,
        "targets": targets,
        "targets_sha256": object_hash(targets),
        "sources": sources,
        "source_bundle_sha256": object_hash(source_binding),
    }
    if seed_aggregation is not None:
        document["seed_aggregation"] = seed_aggregation
    document["document_sha256"] = object_hash(document)

    output_path = output_path.resolve()
    if str(output_path) in sources_by_path:
        raise SlaFreezeError(
            "the frozen SLA output path must not overwrite a source pilot artifact"
        )
    if output_path.exists():
        if replace_existing_sha256 is None:
            raise SlaFreezeError(
                f"refusing to overwrite existing frozen SLA file {output_path}; "
                "supply --replace-existing-sha256 with its current SHA-256 to replace it deliberately"
            )
        expected = replace_existing_sha256.lower()
        if SHA256_RE.fullmatch(expected) is None:
            raise SlaFreezeError(
                "replace-existing-sha256 must be 64 lowercase hexadecimal characters"
            )
        observed = file_hash(output_path)
        if observed != expected:
            raise SlaFreezeError(
                f"existing frozen SLA file hash mismatch: expected {expected}, observed {observed}"
            )
    elif replace_existing_sha256 is not None:
        raise SlaFreezeError(
            "replace-existing-sha256 was supplied but the output file does not exist"
        )

    write_json_atomic(output_path, document)
    return document


def load_frozen_sla_targets(path: Path) -> FrozenSlaTargets:
    """Strictly load and hash-bind one frozen three-pilot SLA artifact."""

    document, raw, artifact_digest = _read_artifact(path)
    if document.get("schema_version") != TARGET_SCHEMA:
        raise SlaFreezeError(
            f"frozen SLA schema must be {TARGET_SCHEMA}: {path.resolve()}"
        )
    if document.get("status") != "frozen":
        raise SlaFreezeError("frozen SLA artifact must have status=frozen")
    self_digest = document.get("document_sha256")
    if not isinstance(self_digest, str) or SHA256_RE.fullmatch(self_digest) is None:
        raise SlaFreezeError("frozen SLA document_sha256 is invalid")
    without_digest = copy.deepcopy(document)
    without_digest.pop("document_sha256", None)
    if object_hash(without_digest) != self_digest:
        raise SlaFreezeError("frozen SLA document_sha256 does not match its content")
    targets = document.get("targets")
    if not isinstance(targets, dict) or set(targets) != {
        "latency_deadline_ms",
        "throughput_target_rps",
        "cost_budget_per_request",
    }:
        raise SlaFreezeError("frozen SLA artifact has an invalid targets object")
    normalized = {
        name: _positive_finite(value, field=f"targets.{name}", path=path)
        for name, value in targets.items()
    }
    targets_digest = document.get("targets_sha256")
    if (
        not isinstance(targets_digest, str)
        or SHA256_RE.fullmatch(targets_digest) is None
        or object_hash(targets) != targets_digest
    ):
        raise SlaFreezeError("frozen SLA targets_sha256 does not match its content")
    source_digest = document.get("source_bundle_sha256")
    if not isinstance(source_digest, str) or SHA256_RE.fullmatch(source_digest) is None:
        raise SlaFreezeError("frozen SLA source_bundle_sha256 is invalid")
    frozen_at = document.get("frozen_at")
    if not isinstance(frozen_at, str) or not frozen_at.strip():
        raise SlaFreezeError("frozen SLA frozen_at is missing")
    return FrozenSlaTargets(
        path=str(path.resolve()),
        artifact_sha256=artifact_digest,
        artifact_bytes=len(raw),
        document_sha256=self_digest,
        targets_sha256=targets_digest,
        targets=normalized,
        frozen_at=frozen_at,
        source_bundle_sha256=source_digest,
    )
