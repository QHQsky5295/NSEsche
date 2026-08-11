from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Mapping

from .schema import ProtocolValidationError
from .tape import inspect_tape
from .util import file_hash, object_hash, utc_now, write_json_atomic


MODEL_SCHEMA = "NSE_FAASRANK_FROZEN_LINEAR_V1"
MODEL_FAMILY = "frozen_linear_score_rank_select"
MODEL_STATE = "frozen"
CALIBRATION_PLAN_SCHEMA = "NSE_FAASRANK_CALIBRATION_PLAN_V1"
CALIBRATION_RESULTS_SCHEMA = "NSE_FAASRANK_CALIBRATION_RESULTS_V1"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
WEIGHT_NAMES = (
    "cpu_headroom",
    "memory_headroom",
    "network_locality",
    "warm_affinity",
    "load_balance",
    "diversity_penalty",
)

_TOP_LEVEL_FIELDS = {
    "schema_version",
    "model_family",
    "state",
    "created_at",
    "training_tape",
    "parameters",
    "provenance",
}
_PARAMETER_FIELDS = {*WEIGHT_NAMES, "epsilon"}
_PROVENANCE_FIELDS = {"calibration", "selection"}
CALIBRATION_OBJECTIVE = {
    "name": "mean_qpr",
    "direction": "maximize",
    "per_run_formula": (
        "(throughput_requests_per_second/1000)/"
        "(simulator_internal_cost_per_completed_request*latency_ms.mean)"
    ),
    "aggregation": "arithmetic_mean_over_preregistered_training_seeds",
    "tie_break": "lowest_candidate_parameter_sha256",
}
_PLAN_FIELDS = {
    "schema_version",
    "preregistered_at",
    "training_tape_sha256",
    "objective",
    "training_seeds",
    "candidates",
}
_CANDIDATE_FIELDS = {"candidate_sha256", "weights", "epsilon"}
_RESULTS_FIELDS = {
    "schema_version",
    "completed_at",
    "plan_sha256",
    "training_tape_sha256",
    "runs",
}
_RESULT_RUN_FIELDS = {
    "candidate_sha256",
    "seed",
    "run_id",
    "run_config_path",
    "run_config_sha256",
    "summary_path",
    "summary_sha256",
}


class FaaSRankModelError(ProtocolValidationError):
    """Raised when a frozen FaaSRank placement model is invalid or unbound."""


@dataclass(frozen=True)
class FrozenFaaSRankModel:
    path: str
    artifact_sha256: str
    artifact_bytes: int
    training_tape_sha256: str
    weights: dict[str, float]
    epsilon: float
    created_at: str
    provenance: dict[str, Any]

    def rust_experiment_config(self) -> dict[str, Any]:
        """Return the exact payload consumed by experiment.faasrank_model."""

        return rust_faasrank_model_config(self)


@dataclass(frozen=True)
class FaaSRankCalibrationPlan:
    path: str
    artifact_sha256: str
    training_tape_sha256: str
    training_seeds: tuple[str, ...]
    candidates: tuple[dict[str, Any], ...]
    preregistered_at: str


def _exact_fields(value: Mapping[str, Any], expected: set[str], field: str) -> None:
    actual = set(value)
    missing = sorted(expected - actual)
    unknown = sorted(actual - expected)
    if missing or unknown:
        details: list[str] = []
        if missing:
            details.append(f"missing {missing}")
        if unknown:
            details.append(f"unknown {unknown}")
        raise FaaSRankModelError(f"{field} has invalid fields: {', '.join(details)}")


def _sha256(value: Any, field: str) -> str:
    if not isinstance(value, str) or SHA256_RE.fullmatch(value) is None:
        raise FaaSRankModelError(f"{field} must be a lowercase 64-character SHA-256")
    return value


def _finite_number(value: Any, field: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise FaaSRankModelError(f"{field} must be numeric")
    result = float(value)
    if not math.isfinite(result):
        raise FaaSRankModelError(f"{field} must be finite")
    return result


def _validate_json_value(value: Any, field: str) -> None:
    if value is None or isinstance(value, (str, bool)):
        return
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if not math.isfinite(float(value)):
            raise FaaSRankModelError(f"{field} contains a nonfinite number")
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _validate_json_value(item, f"{field}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise FaaSRankModelError(f"{field} contains a non-string object key")
            _validate_json_value(item, f"{field}.{key}")
        return
    raise FaaSRankModelError(
        f"{field} contains a non-JSON value of type {type(value).__name__}"
    )


def _strict_json_document(path: Path, description: str) -> Any:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise FaaSRankModelError(f"cannot read {description} {path}: {exc}") from exc

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
        return json.loads(
            raw.decode("utf-8"),
            parse_constant=reject_constant,
            object_pairs_hook=reject_duplicate_keys,
        )
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
        raise FaaSRankModelError(
            f"{description} is not strict UTF-8 JSON: {path}: {exc}"
        ) from exc


def _validated_document(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise FaaSRankModelError("frozen FaaSRank artifact must be a JSON object")
    _exact_fields(document, _TOP_LEVEL_FIELDS, "artifact")
    if document["schema_version"] != MODEL_SCHEMA:
        raise FaaSRankModelError(
            f"artifact schema must be {MODEL_SCHEMA}, got {document['schema_version']!r}"
        )
    if document["model_family"] != MODEL_FAMILY:
        raise FaaSRankModelError(
            f"model_family must be {MODEL_FAMILY}, got {document['model_family']!r}"
        )
    if document["state"] != MODEL_STATE:
        raise FaaSRankModelError(f"state must be {MODEL_STATE!r}")
    if (
        not isinstance(document["created_at"], str)
        or not document["created_at"].strip()
    ):
        raise FaaSRankModelError("created_at must be a non-empty string")

    training_tape = document["training_tape"]
    if not isinstance(training_tape, dict):
        raise FaaSRankModelError("training_tape must be an object")
    _exact_fields(training_tape, {"sha256"}, "training_tape")
    _sha256(training_tape["sha256"], "training_tape.sha256")

    parameters = document["parameters"]
    if not isinstance(parameters, dict):
        raise FaaSRankModelError("parameters must be an object")
    _exact_fields(parameters, _PARAMETER_FIELDS, "parameters")
    for name in WEIGHT_NAMES:
        _finite_number(parameters[name], f"parameters.{name}")
    epsilon = _finite_number(parameters["epsilon"], "parameters.epsilon")
    if not 0.0 <= epsilon <= 1.0:
        raise FaaSRankModelError("parameters.epsilon must be in [0, 1]")

    provenance = document["provenance"]
    if not isinstance(provenance, dict):
        raise FaaSRankModelError("provenance must be an object")
    _exact_fields(provenance, _PROVENANCE_FIELDS, "provenance")
    for role in sorted(_PROVENANCE_FIELDS):
        value = provenance[role]
        if not isinstance(value, dict) or not value:
            raise FaaSRankModelError(f"provenance.{role} must be a non-empty object")
        _validate_json_value(value, f"provenance.{role}")
    return document


def _strict_json(path: Path) -> dict[str, Any]:
    document = _strict_json_document(path, "frozen FaaSRank artifact")
    return _validated_document(document)


def _model_info(path: Path, document: Mapping[str, Any]) -> FrozenFaaSRankModel:
    parameters = document["parameters"]
    return FrozenFaaSRankModel(
        path=str(path),
        artifact_sha256=file_hash(path),
        artifact_bytes=path.stat().st_size,
        training_tape_sha256=str(document["training_tape"]["sha256"]),
        weights={name: float(parameters[name]) for name in WEIGHT_NAMES},
        epsilon=float(parameters["epsilon"]),
        created_at=str(document["created_at"]),
        provenance={
            "calibration": dict(document["provenance"]["calibration"]),
            "selection": dict(document["provenance"]["selection"]),
        },
    )


def load_frozen_faasrank_model(path: Path) -> FrozenFaaSRankModel:
    """Load and strictly validate an immutable frozen linear model artifact."""

    resolved = path.resolve()
    document = _strict_json(resolved)
    return _model_info(resolved, document)


def verify_frozen_faasrank_model(
    path: Path,
    *,
    expected_artifact_sha256: str | None = None,
    expected_training_tape_sha256: str | None = None,
    test_tape_sha256: str | None = None,
    forbidden_test_tape_sha256: Iterable[str] = (),
) -> FrozenFaaSRankModel:
    """Verify artifact bindings and training/test tape separation."""

    model = load_frozen_faasrank_model(path)
    if expected_artifact_sha256 is not None:
        expected = _sha256(expected_artifact_sha256, "expected_artifact_sha256")
        if model.artifact_sha256 != expected:
            raise FaaSRankModelError(
                "frozen FaaSRank artifact SHA-256 does not match its binding"
            )
    if expected_training_tape_sha256 is not None:
        expected = _sha256(
            expected_training_tape_sha256,
            "expected_training_tape_sha256",
        )
        if model.training_tape_sha256 != expected:
            raise FaaSRankModelError(
                "FaaSRank training tape SHA-256 does not match its binding"
            )

    forbidden = list(forbidden_test_tape_sha256)
    if test_tape_sha256 is not None:
        forbidden.append(test_tape_sha256)
    for index, value in enumerate(forbidden):
        test_hash = _sha256(value, f"test_tape_sha256[{index}]")
        if model.training_tape_sha256 == test_hash:
            raise FaaSRankModelError(
                "FaaSRank training and evaluation tapes must be hash-disjoint"
            )
    return model


def _parameters(
    weights: Mapping[str, Any], epsilon: Any, field: str = "candidate"
) -> dict[str, Any]:
    if not isinstance(weights, Mapping):
        raise FaaSRankModelError(f"{field}.weights must be an object")
    _exact_fields(weights, set(WEIGHT_NAMES), f"{field}.weights")
    normalized = {
        name: _finite_number(weights[name], f"{field}.weights.{name}")
        for name in WEIGHT_NAMES
    }
    normalized_epsilon = _finite_number(epsilon, f"{field}.epsilon")
    if not 0.0 <= normalized_epsilon <= 1.0:
        raise FaaSRankModelError(f"{field}.epsilon must be in [0, 1]")
    return {"weights": normalized, "epsilon": normalized_epsilon}


def candidate_parameter_sha256(weights: Mapping[str, Any], epsilon: Any) -> str:
    """Return the canonical identity of one preregistered linear candidate."""

    return object_hash(_parameters(weights, epsilon))


def create_faasrank_calibration_plan(
    output_path: Path,
    *,
    training_tape_sha256: str,
    candidates: Iterable[Mapping[str, Any]],
    training_seeds: Iterable[str],
    preregistered_at: str | None = None,
) -> FaaSRankCalibrationPlan:
    """Atomically preregister candidates before any calibration result is read."""

    resolved = output_path.resolve()
    if resolved.exists():
        raise FaaSRankModelError(
            f"refusing to replace FaaSRank calibration plan {resolved}"
        )
    tape_hash = _sha256(training_tape_sha256, "training_tape_sha256")
    seeds = tuple(training_seeds)
    if not seeds or any(
        not isinstance(seed, str) or not seed.strip() for seed in seeds
    ):
        raise FaaSRankModelError("training_seeds must contain non-empty strings")
    if len(set(seeds)) != len(seeds):
        raise FaaSRankModelError("training_seeds must be unique")
    normalized_candidates: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, Mapping):
            raise FaaSRankModelError(f"candidates[{index}] must be an object")
        _exact_fields(candidate, {"weights", "epsilon"}, f"candidates[{index}]")
        parameters = _parameters(
            candidate["weights"], candidate["epsilon"], f"candidates[{index}]"
        )
        normalized_candidates.append(
            {
                "candidate_sha256": object_hash(parameters),
                **parameters,
            }
        )
    if len(normalized_candidates) < 2:
        raise FaaSRankModelError("at least two preregistered candidates are required")
    identities = [item["candidate_sha256"] for item in normalized_candidates]
    if len(set(identities)) != len(identities):
        raise FaaSRankModelError("preregistered candidates must be unique")
    normalized_candidates.sort(key=lambda item: item["candidate_sha256"])
    timestamp = preregistered_at if preregistered_at is not None else utc_now()
    if not isinstance(timestamp, str) or not timestamp.strip():
        raise FaaSRankModelError("preregistered_at must be a non-empty string")
    document = {
        "schema_version": CALIBRATION_PLAN_SCHEMA,
        "preregistered_at": timestamp,
        "training_tape_sha256": tape_hash,
        "objective": dict(CALIBRATION_OBJECTIVE),
        "training_seeds": list(seeds),
        "candidates": normalized_candidates,
    }
    _validated_calibration_plan(document)
    write_json_atomic(resolved, document)
    return load_faasrank_calibration_plan(resolved)


def _validated_calibration_plan(document: Any) -> dict[str, Any]:
    if not isinstance(document, dict):
        raise FaaSRankModelError("FaaSRank calibration plan must be an object")
    _exact_fields(document, _PLAN_FIELDS, "calibration_plan")
    if document["schema_version"] != CALIBRATION_PLAN_SCHEMA:
        raise FaaSRankModelError(
            f"calibration plan schema must be {CALIBRATION_PLAN_SCHEMA}"
        )
    if (
        not isinstance(document["preregistered_at"], str)
        or not document["preregistered_at"].strip()
    ):
        raise FaaSRankModelError("preregistered_at must be a non-empty string")
    _sha256(document["training_tape_sha256"], "training_tape_sha256")
    if document["objective"] != CALIBRATION_OBJECTIVE:
        raise FaaSRankModelError(
            "calibration objective/direction/aggregation/tie-break must equal the frozen protocol"
        )
    seeds = document["training_seeds"]
    if (
        not isinstance(seeds, list)
        or not seeds
        or any(not isinstance(seed, str) or not seed.strip() for seed in seeds)
        or len(set(seeds)) != len(seeds)
    ):
        raise FaaSRankModelError(
            "training_seeds must be a non-empty unique string list"
        )
    candidates = document["candidates"]
    if not isinstance(candidates, list) or len(candidates) < 2:
        raise FaaSRankModelError("calibration plan requires at least two candidates")
    identities: list[str] = []
    for index, candidate in enumerate(candidates):
        if not isinstance(candidate, dict):
            raise FaaSRankModelError(f"candidates[{index}] must be an object")
        _exact_fields(candidate, _CANDIDATE_FIELDS, f"candidates[{index}]")
        identity = _sha256(
            candidate["candidate_sha256"], f"candidates[{index}].candidate_sha256"
        )
        parameters = _parameters(
            candidate["weights"], candidate["epsilon"], f"candidates[{index}]"
        )
        if object_hash(parameters) != identity:
            raise FaaSRankModelError(
                f"candidates[{index}] parameter hash does not match its weights/epsilon"
            )
        identities.append(identity)
    if len(set(identities)) != len(identities):
        raise FaaSRankModelError("calibration candidate identities must be unique")
    if identities != sorted(identities):
        raise FaaSRankModelError("calibration candidates must use canonical hash order")
    return document


def load_faasrank_calibration_plan(path: Path) -> FaaSRankCalibrationPlan:
    resolved = path.resolve()
    document = _validated_calibration_plan(
        _strict_json_document(resolved, "FaaSRank calibration plan")
    )
    return FaaSRankCalibrationPlan(
        path=str(resolved),
        artifact_sha256=file_hash(resolved),
        training_tape_sha256=document["training_tape_sha256"],
        training_seeds=tuple(document["training_seeds"]),
        candidates=tuple(dict(candidate) for candidate in document["candidates"]),
        preregistered_at=document["preregistered_at"],
    )


def _resolve_input(owner: Path, value: Any, field: str) -> Path:
    if not isinstance(value, str) or not value.strip():
        raise FaaSRankModelError(f"{field} must be a non-empty path")
    path = Path(value)
    return path.resolve() if path.is_absolute() else (owner.parent / path).resolve()


def _qpr_from_summary(summary: Any, field: str) -> float:
    if not isinstance(summary, dict) or summary.get("schema") != "NSE_SUMMARY_V1":
        raise FaaSRankModelError(f"{field} must be an NSE_SUMMARY_V1 object")
    if summary.get("run_complete") is not True:
        raise FaaSRankModelError(f"{field} is not a completed training run")
    latency = summary.get("latency_ms")
    latency_mean = latency.get("mean") if isinstance(latency, dict) else None
    throughput_rps = _finite_number(
        summary.get("throughput_requests_per_second"),
        f"{field}.throughput_requests_per_second",
    )
    cost = _finite_number(
        summary.get("simulator_internal_cost_per_completed_request"),
        f"{field}.simulator_internal_cost_per_completed_request",
    )
    latency_value = _finite_number(latency_mean, f"{field}.latency_ms.mean")
    if throughput_rps <= 0 or cost <= 0 or latency_value <= 0:
        raise FaaSRankModelError(
            f"{field} cannot produce the preregistered QPR objective from non-positive values"
        )
    qpr = (throughput_rps / 1000.0) / (cost * latency_value)
    if not math.isfinite(qpr) or qpr <= 0:
        raise FaaSRankModelError(f"{field} produced an invalid QPR")
    return qpr


def _verify_training_run_config(
    config: Any,
    *,
    run_id: str,
    seed: str,
    training_tape_sha256: str,
    candidate: Mapping[str, Any],
    field: str,
) -> None:
    if not isinstance(config, dict):
        raise FaaSRankModelError(f"{field} must be an object")
    if config.get("run_id") != run_id or config.get("seed") != seed:
        raise FaaSRankModelError(f"{field} run_id/seed differs from its result record")
    if config.get("method") != "sche_FaaSRank":
        raise FaaSRankModelError(f"{field} must execute sche_FaaSRank")
    workload = config.get("workload_tape")
    if not isinstance(workload, dict) or workload.get("sha256") != training_tape_sha256:
        raise FaaSRankModelError(f"{field} does not bind the independent training tape")
    experiment = config.get("simulator_experiment")
    model = experiment.get("faasrank_model") if isinstance(experiment, dict) else None
    expected = {
        "state": "frozen",
        "model_sha256": candidate["candidate_sha256"],
        "training_tape_sha256": training_tape_sha256,
        **candidate["weights"],
        "epsilon": candidate["epsilon"],
    }
    if model != expected:
        raise FaaSRankModelError(
            f"{field} FaaSRank parameters differ from the preregistered candidate"
        )


def freeze_faasrank_from_calibration(
    output_path: Path,
    *,
    training_tape_path: Path,
    calibration_plan_path: Path,
    training_results_path: Path,
) -> FrozenFaaSRankModel:
    """Select and freeze a model from result-complete preregistered training runs.

    This stage never accepts weights on its command line and never inspects a
    formal evaluation result.  Every score is recomputed from a hash-bound
    training summary using the frozen QPR objective.
    """

    training_tape = inspect_tape(training_tape_path, "auto")
    plan = load_faasrank_calibration_plan(calibration_plan_path)
    if training_tape.sha256 != plan.training_tape_sha256:
        raise FaaSRankModelError(
            "training tape SHA-256 differs from the preregistered calibration plan"
        )
    results_path = training_results_path.resolve()
    results = _strict_json_document(results_path, "FaaSRank calibration results")
    if not isinstance(results, dict):
        raise FaaSRankModelError("FaaSRank calibration results must be an object")
    _exact_fields(results, _RESULTS_FIELDS, "calibration_results")
    if results["schema_version"] != CALIBRATION_RESULTS_SCHEMA:
        raise FaaSRankModelError(
            f"calibration results schema must be {CALIBRATION_RESULTS_SCHEMA}"
        )
    if (
        not isinstance(results["completed_at"], str)
        or not results["completed_at"].strip()
    ):
        raise FaaSRankModelError("calibration results completed_at must be non-empty")
    if results["plan_sha256"] != plan.artifact_sha256:
        raise FaaSRankModelError(
            "calibration results do not bind the preregistered plan"
        )
    if results["training_tape_sha256"] != training_tape.sha256:
        raise FaaSRankModelError("calibration results do not bind the training tape")
    run_records = results["runs"]
    if not isinstance(run_records, list):
        raise FaaSRankModelError("calibration_results.runs must be a list")

    candidates = {
        candidate["candidate_sha256"]: candidate for candidate in plan.candidates
    }
    expected_pairs = {
        (candidate_sha256, seed)
        for candidate_sha256 in candidates
        for seed in plan.training_seeds
    }
    seen_pairs: set[tuple[str, str]] = set()
    seen_run_ids: set[str] = set()
    run_audit: list[dict[str, Any]] = []
    scores: dict[str, list[float]] = {identity: [] for identity in candidates}
    for index, record in enumerate(run_records):
        field = f"calibration_results.runs[{index}]"
        if not isinstance(record, dict):
            raise FaaSRankModelError(f"{field} must be an object")
        _exact_fields(record, _RESULT_RUN_FIELDS, field)
        identity = _sha256(record["candidate_sha256"], f"{field}.candidate_sha256")
        seed = record["seed"]
        run_id = record["run_id"]
        if identity not in candidates or seed not in plan.training_seeds:
            raise FaaSRankModelError(f"{field} was not preregistered")
        if not isinstance(run_id, str) or not run_id.strip():
            raise FaaSRankModelError(f"{field}.run_id must be non-empty")
        pair = (identity, seed)
        if pair in seen_pairs or run_id in seen_run_ids:
            raise FaaSRankModelError(f"{field} duplicates a candidate/seed or run_id")
        seen_pairs.add(pair)
        seen_run_ids.add(run_id)
        config_path = _resolve_input(
            results_path, record["run_config_path"], f"{field}.run_config_path"
        )
        summary_path = _resolve_input(
            results_path, record["summary_path"], f"{field}.summary_path"
        )
        config_hash = _sha256(record["run_config_sha256"], f"{field}.run_config_sha256")
        summary_hash = _sha256(record["summary_sha256"], f"{field}.summary_sha256")
        if file_hash(config_path) != config_hash:
            raise FaaSRankModelError(f"{field} run config hash mismatch")
        if file_hash(summary_path) != summary_hash:
            raise FaaSRankModelError(f"{field} summary hash mismatch")
        config = _strict_json_document(config_path, f"{field} run config")
        _verify_training_run_config(
            config,
            run_id=run_id,
            seed=seed,
            training_tape_sha256=training_tape.sha256,
            candidate=candidates[identity],
            field=f"{field}.run_config",
        )
        summary = _strict_json_document(summary_path, f"{field} summary")
        if not isinstance(summary, dict) or summary.get("run_id") != run_id:
            raise FaaSRankModelError(f"{field} summary run_id mismatch")
        qpr = _qpr_from_summary(summary, f"{field}.summary")
        scores[identity].append(qpr)
        run_audit.append(
            {
                "candidate_sha256": identity,
                "seed": seed,
                "run_id": run_id,
                "run_config_sha256": config_hash,
                "summary_sha256": summary_hash,
                "qpr": qpr,
            }
        )
    missing = sorted(expected_pairs - seen_pairs)
    extra = sorted(seen_pairs - expected_pairs)
    if missing or extra:
        raise FaaSRankModelError(
            f"calibration result matrix must be complete and paired; missing={missing}, extra={extra}"
        )

    aggregate_scores = {
        identity: math.fsum(values) / len(values) for identity, values in scores.items()
    }
    best_score = max(aggregate_scores.values())
    selected_identity = min(
        identity for identity, score in aggregate_scores.items() if score == best_score
    )
    selected = candidates[selected_identity]
    ranked = sorted(
        (
            {"candidate_sha256": identity, "mean_qpr": score}
            for identity, score in aggregate_scores.items()
        ),
        key=lambda item: (-item["mean_qpr"], item["candidate_sha256"]),
    )
    results_hash = file_hash(results_path)
    run_audit.sort(key=lambda item: (item["candidate_sha256"], item["seed"]))
    return create_frozen_faasrank_model(
        output_path,
        training_tape_sha256=training_tape.sha256,
        weights=selected["weights"],
        epsilon=selected["epsilon"],
        calibration_provenance={
            "plan_schema": CALIBRATION_PLAN_SCHEMA,
            "plan_sha256": plan.artifact_sha256,
            "plan_path": plan.path,
            "preregistered_at": plan.preregistered_at,
            "training_tape_path": str(training_tape_path.resolve()),
            "training_tape_sha256": training_tape.sha256,
            "training_tape_event_count": training_tape.event_count,
            "results_schema": CALIBRATION_RESULTS_SCHEMA,
            "results_path": str(results_path),
            "results_sha256": results_hash,
            "training_seeds": list(plan.training_seeds),
            "candidate_count": len(candidates),
            "candidates": list(plan.candidates),
            "verified_runs": run_audit,
        },
        selection_provenance={
            "objective": dict(CALIBRATION_OBJECTIVE),
            "ranked_candidates": ranked,
            "selected_candidate_sha256": selected_identity,
            "selected_mean_qpr": best_score,
            "result_matrix_sha256": object_hash(run_audit),
            "selection_rule": (
                "maximize preregistered arithmetic mean QPR; exact ties choose "
                "lowest candidate parameter SHA-256"
            ),
            "formal_evaluation_results_used": False,
        },
    )


def create_frozen_faasrank_model(
    output_path: Path,
    *,
    training_tape_sha256: str,
    weights: Mapping[str, Any],
    epsilon: Any,
    calibration_provenance: Mapping[str, Any],
    selection_provenance: Mapping[str, Any],
    created_at: str | None = None,
) -> FrozenFaaSRankModel:
    """Atomically create a new frozen linear Score-Rank-Select model artifact."""

    resolved = output_path.resolve()
    if resolved.exists():
        raise FaaSRankModelError(
            f"refusing to replace frozen model artifact {resolved}"
        )
    if not isinstance(weights, Mapping):
        raise FaaSRankModelError("weights must be an object")
    _exact_fields(weights, set(WEIGHT_NAMES), "weights")
    document = {
        "schema_version": MODEL_SCHEMA,
        "model_family": MODEL_FAMILY,
        "state": MODEL_STATE,
        "created_at": created_at if created_at is not None else utc_now(),
        "training_tape": {"sha256": training_tape_sha256},
        "parameters": {
            **{name: weights[name] for name in WEIGHT_NAMES},
            "epsilon": epsilon,
        },
        "provenance": {
            "calibration": dict(calibration_provenance),
            "selection": dict(selection_provenance),
        },
    }
    _validated_document(document)
    write_json_atomic(resolved, document)
    return load_frozen_faasrank_model(resolved)


def rust_faasrank_model_config(model: FrozenFaaSRankModel) -> dict[str, Any]:
    """Pure mapping from a verified artifact to the Rust experiment payload."""

    if not isinstance(model, FrozenFaaSRankModel):
        raise FaaSRankModelError("model must be a verified FrozenFaaSRankModel")
    _sha256(model.artifact_sha256, "artifact_sha256")
    _sha256(model.training_tape_sha256, "training_tape_sha256")
    weights = {
        name: _finite_number(model.weights.get(name), name) for name in WEIGHT_NAMES
    }
    if set(model.weights) != set(WEIGHT_NAMES):
        raise FaaSRankModelError(
            "verified model weights do not contain exactly six fields"
        )
    epsilon = _finite_number(model.epsilon, "epsilon")
    if not 0.0 <= epsilon <= 1.0:
        raise FaaSRankModelError("epsilon must be in [0, 1]")
    return {
        "state": MODEL_STATE,
        "model_sha256": model.artifact_sha256,
        "training_tape_sha256": model.training_tape_sha256,
        **weights,
        "epsilon": epsilon,
    }


def artifact_sha256(path: Path) -> str:
    """Hash an artifact externally; the digest is deliberately not self-embedded."""

    resolved = path.resolve()
    try:
        return hashlib.sha256(resolved.read_bytes()).hexdigest()
    except OSError as exc:
        raise FaaSRankModelError(
            f"cannot hash frozen FaaSRank artifact {resolved}: {exc}"
        ) from exc
