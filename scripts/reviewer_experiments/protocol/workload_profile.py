from __future__ import annotations

import hashlib
import math
import re
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .schema import ProtocolValidationError
from .util import file_hash, object_hash, read_json


PROFILE_SCHEMA = "NSE_WORKLOAD_FREQUENCY_PROFILE_V1"
PROFILE_SET_SCHEMA = "NSE_WORKLOAD_FREQUENCY_PROFILE_SET_V1"
FREQUENCY_MAP_HASH_DOMAIN = b"NSE_WORKLOAD_FREQUENCY_MAP_V2_F32\0"
PROFILE_LOADS = ("low", "middle", "high")
PROFILE_SCALES = {"low": 0.2, "middle": 0.6, "high": 1.4}
CANONICAL_PROFILE_SET_ID = "submission-era-azure-cdf-v1"
CANONICAL_PROFILES = {
    "low": {
        "sha256": "2dd3147eb8b807c39fb6bbf4a977f42f4db860cddfd1e07664c7dbb367b7e9a2",
        "profile_id": "submission-era-azure-cdf-low-v1",
        "dag_call_frequency_sha256": "323290747f6eb52db0002196e34091cc249610ee46480155335256bf47f0f7f7",
        "expected_arrival_rate_rps": 1934.66,
        "submission_actual_arrival_rate_rps": 1923.0,
    },
    "middle": {
        "sha256": "a810c95735845b25ecc9e0b59266e322fdf5eb83871903baa1128f757ea5a3aa",
        "profile_id": "submission-era-azure-cdf-middle-v1",
        "dag_call_frequency_sha256": "be66a5890b6b8d4594dcebb5d6b12ad827353add95ce2e511166e61684af1fdd",
        "expected_arrival_rate_rps": 2533.14,
        "submission_actual_arrival_rate_rps": 2574.0,
    },
    "high": {
        "sha256": "add8fc82517c826372ec2ff3a169f989cc79e60aa9171cd0ee452a73923e4a3b",
        "profile_id": "submission-era-azure-cdf-high-7k-v1",
        "dag_call_frequency_sha256": "10842c57245d684cbf42c69cfe78a0b3d1cd54cc534a8f517327d2001eb98a8c",
        "expected_arrival_rate_rps": 7000.0,
        "submission_actual_arrival_rate_rps": 27924.0,
    },
}
HASH_RE = re.compile(r"^[0-9a-f]{64}$")


@dataclass(frozen=True)
class FrozenWorkloadProfile:
    path: str
    sha256: str
    profile_set_id: str
    profile_id: str
    load: str
    dag_call_frequency_sha256: str
    dag_count: int
    expected_arrival_rate_rps: float
    submission_actual_arrival_rate_rps: float
    request_frequency_scale: float
    source: dict[str, Any]

    def to_binding(self) -> dict[str, Any]:
        return {
            "schema_version": PROFILE_SCHEMA,
            "profile_set_id": self.profile_set_id,
            "profile_id": self.profile_id,
            "load": self.load,
            "path": self.path,
            "sha256": self.sha256,
            "dag_call_frequency_sha256": self.dag_call_frequency_sha256,
            "dag_count": self.dag_count,
            "expected_arrival_rate_rps": self.expected_arrival_rate_rps,
            "submission_actual_arrival_rate_rps": (
                self.submission_actual_arrival_rate_rps
            ),
            "request_frequency_scale": self.request_frequency_scale,
            "source": self.source,
        }


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ProtocolValidationError(message)


def _positive_number(value: Any, field: str) -> float:
    _require(
        isinstance(value, (int, float))
        and not isinstance(value, bool)
        and math.isfinite(float(value))
        and float(value) > 0.0,
        f"{field} must be finite and positive",
    )
    return float(value)


def _positive_truncated_normal_mean(mean: float, cv: float) -> float:
    if cv == 0.0:
        return mean
    z = 1.0 / cv
    standard_normal_density = math.exp(-(z * z) / 2.0) / math.sqrt(2.0 * math.pi)
    positive_probability = 0.5 * (1.0 + math.erf(z / math.sqrt(2.0)))
    return mean + mean * cv * standard_normal_density / positive_probability


def _frequency_map_sha256(frequencies: dict[str, Any]) -> str:
    """Hash cross-language f32 semantics; the artifact SHA protects exact f64 text."""

    digest = hashlib.sha256()
    digest.update(FREQUENCY_MAP_HASH_DOMAIN)
    for dag_id in range(len(frequencies)):
        mean, cv = frequencies[str(dag_id)]
        digest.update(struct.pack(">Qff", dag_id, float(mean), float(cv)))
    return digest.hexdigest()


def load_frozen_workload_profile(
    path: Path,
    *,
    expected_sha256: str | None = None,
    expected_load: str | None = None,
    expected_profile_id: str | None = None,
    expected_profile_set_id: str | None = None,
    expected_frequency_sha256: str | None = None,
) -> FrozenWorkloadProfile:
    resolved = path.resolve()
    _require(resolved.is_file(), f"workload profile is missing: {resolved}")
    artifact_sha256 = file_hash(resolved)
    if expected_sha256 is not None:
        _require(
            HASH_RE.fullmatch(expected_sha256) is not None,
            "workload profile expected_sha256 is invalid",
        )
        _require(
            artifact_sha256 == expected_sha256,
            f"workload profile SHA-256 mismatch: {resolved}",
        )
    document = read_json(resolved)
    _require(isinstance(document, dict), "workload profile root must be an object")
    _require(
        set(document)
        == {
            "schema_version",
            "profile_set_id",
            "profile_id",
            "load",
            "source",
            "rate_audit",
            "dag_call_frequency",
        },
        "workload profile has unexpected or missing fields",
    )
    _require(
        document["schema_version"] == PROFILE_SCHEMA,
        "unsupported workload profile schema",
    )
    profile_set_id = document["profile_set_id"]
    profile_id = document["profile_id"]
    load = document["load"]
    _require(
        isinstance(profile_set_id, str) and bool(profile_set_id),
        "workload profile_set_id must be non-empty",
    )
    _require(
        isinstance(profile_id, str) and bool(profile_id),
        "workload profile_id must be non-empty",
    )
    _require(load in PROFILE_LOADS, "workload profile load is invalid")
    if expected_load is not None:
        _require(load == expected_load, "workload profile load does not match config")
    if expected_profile_id is not None:
        _require(
            profile_id == expected_profile_id,
            "workload profile_id does not match config",
        )
    if expected_profile_set_id is not None:
        _require(
            profile_set_id == expected_profile_set_id,
            "workload profile_set_id does not match config",
        )

    source = document["source"]
    _require(isinstance(source, dict), "workload profile source must be an object")
    _require(
        source.get("kind") == "submission-era-frequency-cache-freeze",
        "workload profile source kind is invalid",
    )
    _require(
        isinstance(source.get("legacy_cache_filename"), str)
        and bool(source["legacy_cache_filename"]),
        "workload profile legacy cache filename is missing",
    )
    _require(
        isinstance(source.get("legacy_cache_sha256"), str)
        and HASH_RE.fullmatch(source["legacy_cache_sha256"]) is not None,
        "workload profile legacy cache SHA-256 is invalid",
    )
    _require(
        isinstance(source.get("source_statement"), str)
        and "does not read that untracked cache" in source["source_statement"],
        "workload profile source statement is incomplete",
    )

    rate = document["rate_audit"]
    _require(isinstance(rate, dict), "workload profile rate_audit must be an object")
    _require(
        isinstance(rate.get("model"), str) and "truncated-normal" in rate["model"],
        "workload profile rate model is invalid",
    )
    scale = _positive_number(
        rate.get("request_frequency_scale"), "request_frequency_scale"
    )
    _require(
        scale == PROFILE_SCALES[load],
        "workload profile request-frequency scale does not match load",
    )
    expected_rate = _positive_number(
        rate.get("expected_arrival_rate_rps"), "expected_arrival_rate_rps"
    )
    actual_rate = _positive_number(
        rate.get("submission_actual_arrival_rate_rps"),
        "submission_actual_arrival_rate_rps",
    )

    frequencies = document["dag_call_frequency"]
    _require(
        isinstance(frequencies, dict) and len(frequencies) == 50,
        "workload profile must contain exactly 50 DAG frequency entries",
    )
    _require(
        set(frequencies) == {str(index) for index in range(50)},
        "workload profile DAG ids must be exactly 0..49",
    )
    for dag_id, pair in frequencies.items():
        _require(
            isinstance(pair, list) and len(pair) == 2,
            f"workload profile DAG {dag_id} must contain [mean, cv]",
        )
        mean, cv = pair
        _require(
            isinstance(mean, (int, float))
            and not isinstance(mean, bool)
            and math.isfinite(float(mean))
            and float(mean) > 0.0,
            f"workload profile DAG {dag_id} mean is invalid",
        )
        _require(
            isinstance(cv, (int, float))
            and not isinstance(cv, bool)
            and math.isfinite(float(cv))
            and float(cv) >= 0.0,
            f"workload profile DAG {dag_id} CV is invalid",
        )
    calculated_rate = (
        sum(
            _positive_truncated_normal_mean(float(pair[0]), float(pair[1]))
            for pair in frequencies.values()
        )
        * scale
        * 1000.0
    )
    _require(
        math.isclose(calculated_rate, expected_rate, rel_tol=0.0, abs_tol=0.01),
        "workload profile expected arrival rate does not match its truncated-normal parameters",
    )
    frequency_sha256 = _frequency_map_sha256(frequencies)
    if expected_frequency_sha256 is not None:
        _require(
            frequency_sha256 == expected_frequency_sha256,
            "workload profile DAG-frequency content hash differs from config",
        )

    if load == "high":
        multiplier = _positive_number(
            source.get("uniform_mean_multiplier"), "uniform_mean_multiplier"
        )
        pre_expected = _positive_number(
            source.get("pre_normalization_expected_arrival_rate_rps"),
            "pre_normalization_expected_arrival_rate_rps",
        )
        target = _positive_number(
            source.get("formal_target_arrival_rate_rps"),
            "formal_target_arrival_rate_rps",
        )
        _require(
            math.isclose(pre_expected * multiplier, target, rel_tol=0.0, abs_tol=1e-3)
            and target == expected_rate,
            "high workload profile normalization does not produce its formal target",
        )
        _require(
            source.get("submission_actual_arrival_rate_rps") == actual_rate,
            "high workload profile submission actual rate is inconsistent",
        )
        pre_hash = source.get("pre_normalization_dag_call_frequency_sha256")
        _require(
            isinstance(pre_hash, str) and HASH_RE.fullmatch(pre_hash) is not None,
            "high workload profile pre-normalization map hash is invalid",
        )
        reconstructed = {
            dag_id: [float(pair[0]) / multiplier, float(pair[1])]
            for dag_id, pair in frequencies.items()
        }
        _require(
            object_hash(reconstructed) == pre_hash,
            "high workload profile is not a uniform mean-only normalization",
        )
        _require(
            isinstance(source.get("normalization_statement"), str)
            and "all CV values are unchanged" in source["normalization_statement"],
            "high workload profile normalization statement is incomplete",
        )

    return FrozenWorkloadProfile(
        path=str(resolved),
        sha256=artifact_sha256,
        profile_set_id=profile_set_id,
        profile_id=profile_id,
        load=load,
        dag_call_frequency_sha256=frequency_sha256,
        dag_count=len(frequencies),
        expected_arrival_rate_rps=expected_rate,
        submission_actual_arrival_rate_rps=actual_rate,
        request_frequency_scale=scale,
        source=dict(source),
    )


def load_profile_set(
    config: dict[str, Any], *, repository: Path
) -> dict[str, FrozenWorkloadProfile]:
    _require(isinstance(config, dict), "workload_profiles must be an object")
    _require(
        config.get("schema_version") == PROFILE_SET_SCHEMA,
        "unsupported workload profile-set schema",
    )
    profile_set_id = config.get("profile_set_id")
    _require(
        isinstance(profile_set_id, str) and bool(profile_set_id),
        "workload profile-set id must be non-empty",
    )
    _require(
        profile_set_id == CANONICAL_PROFILE_SET_ID,
        "formal workload profile-set id is not the frozen canonical set",
    )
    _require(
        config.get("formal_required") is True,
        "formal workload profiles must be required",
    )
    entries = config.get("profiles")
    _require(
        isinstance(entries, dict) and set(entries) == set(PROFILE_LOADS),
        "workload profile set must define low/middle/high exactly",
    )
    loaded: dict[str, FrozenWorkloadProfile] = {}
    for load in PROFILE_LOADS:
        entry = entries[load]
        _require(isinstance(entry, dict), f"workload profile {load} is invalid")
        _require(
            set(entry) == {"path", "sha256", "profile_id", "dag_call_frequency_sha256"},
            f"workload profile {load} config fields are invalid",
        )
        path = Path(entry["path"])
        if not path.is_absolute():
            path = repository / path
        loaded[load] = load_frozen_workload_profile(
            path,
            expected_sha256=entry["sha256"],
            expected_load=load,
            expected_profile_id=entry["profile_id"],
            expected_profile_set_id=profile_set_id,
            expected_frequency_sha256=entry["dag_call_frequency_sha256"],
        )
        canonical = CANONICAL_PROFILES[load]
        _require(
            entry["sha256"] == canonical["sha256"]
            and entry["profile_id"] == canonical["profile_id"]
            and entry["dag_call_frequency_sha256"]
            == canonical["dag_call_frequency_sha256"]
            and loaded[load].expected_arrival_rate_rps
            == canonical["expected_arrival_rate_rps"]
            and loaded[load].submission_actual_arrival_rate_rps
            == canonical["submission_actual_arrival_rate_rps"],
            f"workload profile {load} is not the frozen canonical artifact",
        )
    return loaded
