from __future__ import annotations

import argparse
import gzip
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.matrix import (
    _assign_run_identity,
    _reference_dependency,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
    _metrics,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_container_affinity_diagnostic_v152 import (
    PYTHON_PATH,
    PYTHON_SHA256,
    SOURCE_MANIFEST,
    SOURCE_MANIFEST_HASH,
    SOURCE_MANIFEST_SHA256,
    SOURCE_PAIRING,
    SOURCE_PAIRING_SHA256,
    _assert_file,
    _assert_hashed,
    _validate_reference_catalog,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_legacy_profile_training_prepare_v150 import (
    COMMON_ENVIRONMENT,
)
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
    derive_integration_smoke_shard,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e1_homogeneous_queue8_low_training_20260831_v155")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_queue8_low_training_plan_v155.json"
)
PLAN_SHA256 = "82c77e90fce93bc824faf83222c1e4366ee390d548992fb1992d610812feb298"
AMENDMENT = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_queue8_low_training_amendment_v155a.json"
)
AMENDMENT_SHA256 = "29d922e207e5532c82905c3513bd738207484ca86b3d8aeea4b1ec2dd3f9c977"
AMENDMENT_B = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_queue8_low_training_amendment_v155b.json"
)
AMENDMENT_B_SHA256 = "81ecdf3f3b24b351683ec7a45305a9eb0e1d277ac4dd6a3850a104e1bcd4fa88"
AMENDMENT_C = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_queue8_low_training_amendment_v155c.json"
)
AMENDMENT_C_SHA256 = "89558b5aca14867a516dd17674d8f99693ea22cfa6b70c5604a9f94493326559"
V150_RESULT = Path(
    "tmp/nse_e1_homogeneous_legacy_profile_training_20260831_v150/"
    "training-result-v150.json"
)
V150_RESULT_SHA256 = "31094458481ed38b4faae961326f2b4900eb3252e3d07de88d1f3c2d6bc5839b"
V150_RESULT_HASH = "d7016463743d8136757d6f92ee42c4daf44349284eb91b1a809e14b64dba4342"

ARM_ID = "v155-low-srpt-ready-hiku2-ocs-queue8"
PROFILE = "srpt_ready_hiku2_ocs_queue8"
LOW_EXPERT = "srpt_ready_hiku2_ocs_borda"
HIGH_EXPERT = "srpt_ready_ocs_current_demand"
QUEUE_THRESHOLD = 8.0
SEEDS = tuple(f"E{index:02d}" for index in range(1, 21))
PORT = "3206"
BINARY_SOURCE_COMMIT = "cc4179f028d7af5a2a8adeb48aa14d11b05daa8f"
BINARY_PATH = Path("serverless_sim/target_e1_v155/release/serverless_sim.exe")
BINARY_SHA256 = "cd91cf1f36e8940027e9386cc0bf4188615479ba22ad057ae76edc554e3c7a23"
CARGO_LOCK_SHA256 = "17fe8bce08ba31f9edda8e6e331641cb7d981c1c9f1e21e7bf09178da6dd3205"
MODULE_CONF_SHA256 = "788a81b38e47b44b591953045565a835364a860f7ae071b69f30e2720631bd0e"
MODULE_CONF_SEMANTIC_HASH = (
    "752e521c15ec7a84d2e11a7f73ffd86241a9ad56638964210c30d2c709662877"
)


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v155.json",
        "schedule": root / "frozen-run-order-v155.json",
        "catalog": root / "references.catalog.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "reference_workspace": root / "stages",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v155.json",
        "pairing": root / "pairing-audit-v155.json",
        "blind": root / "joint-blind-audit-v155.json",
        "result": root / "training-result-v155.json",
    }


def _assert_json_semantic(
    path: Path, expected_semantic_hash: str, label: str
) -> dict[str, Any]:
    if not path.is_file():
        raise RuntimeError(f"{label} is missing: {path}")
    semantic_hash = object_hash(read_json(path))
    if semantic_hash != expected_semantic_hash:
        raise RuntimeError(f"{label} semantic content changed: {path}")
    observed_file_sha256 = file_hash(path)
    return {
        "path": str(path),
        "planned_file_sha256": MODULE_CONF_SHA256,
        "observed_file_sha256": observed_file_sha256,
        "byte_identity_preserved": observed_file_sha256 == MODULE_CONF_SHA256,
        "semantic_hash": semantic_hash,
        "semantic_identity_preserved": True,
        "known_serializer_effect": (
            None
            if observed_file_sha256 == MODULE_CONF_SHA256
            else "simulator_reserialized_the_same_JSON_object_with_HashMap_key_order_and_no_terminal_newline"
        ),
    }


def _assert_frozen_inputs() -> dict[str, Any]:
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V155 plan"),
        (AMENDMENT, AMENDMENT_SHA256, "V155A result-blind audit amendment"),
        (AMENDMENT_B, AMENDMENT_B_SHA256, "V155B result-blind audit amendment"),
        (AMENDMENT_C, AMENDMENT_C_SHA256, "V155C result-blind audit amendment"),
        (SOURCE_MANIFEST, SOURCE_MANIFEST_SHA256, "frozen E1 manifest"),
        (SOURCE_PAIRING, SOURCE_PAIRING_SHA256, "frozen E1 pairing"),
        (V150_RESULT, V150_RESULT_SHA256, "V150 result"),
        (BINARY_PATH, BINARY_SHA256, "V155 release binary"),
        (PYTHON_PATH, PYTHON_SHA256, "frozen Python"),
        (Path("serverless_sim/Cargo.lock"), CARGO_LOCK_SHA256, "frozen Cargo.lock"),
    ):
        _assert_file(path, sha256, label)
    _assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    source = read_json(SOURCE_MANIFEST)
    if not (
        source.get("manifest_hash") == SOURCE_MANIFEST_HASH
        and source.get("formal_results_eligible") is True
        and source.get("seed_stage") == "all"
        and len(source.get("runs", [])) == 600
    ):
        raise RuntimeError("frozen E1 source boundary changed")
    pairing = read_json(SOURCE_PAIRING)
    if pairing.get("passed") is not True or pairing.get("run_count") != 600:
        raise RuntimeError("frozen E1 pairing boundary changed")
    v150 = read_json(V150_RESULT)
    if not (
        _assert_hashed(v150, "result_hash", "V150 result") == V150_RESULT_HASH
        and v150.get("candidate_run_count") == 60
        and v150.get("all_nine_training_gates_pass") is False
        and v150.get("confirmation_inputs_generated") is False
        and v150.get("valid_seed_deletion_replacement_relabeling_or_selective_rerun")
        is False
    ):
        raise RuntimeError("V150 diagnostic boundary changed")
    return source


def _rewrite_candidate(
    source: dict[str, Any], protocol_source_commit: str
) -> dict[str, Any]:
    if len(protocol_source_commit) != 40:
        raise RuntimeError("V155 protocol source commit is invalid")
    selected = [
        run
        for run in source["runs"]
        if run.get("method") == "sche_nash"
        and run.get("seed") in SEEDS
        and run.get("workload", {}).get("request_freq") == "low"
        and run.get("cluster") == {"node_count": 20, "topology": "homogeneous"}
    ]
    if len(selected) != 20 or {run["seed"] for run in selected} != set(SEEDS):
        raise RuntimeError("frozen source no longer has the V155 low product")
    by_seed = {run["seed"]: run for run in selected}
    rewritten = derive_integration_smoke_shard(
        SOURCE_MANIFEST,
        [by_seed[seed]["run_id"] for seed in SEEDS],
        purpose=(
            "V155 adaptive complete low E01-E20 queue-gated training; never a "
            "formal result or paper superiority claim"
        ),
    )
    rewritten["created_at"] = utc_now()
    rewritten["execution"]["command_template"] = [
        "{python}",
        "-m",
        "scripts.reviewer_experiments.protocol.serverless_adapter",
        "--run-config",
        "{run_config}",
        "--simulator-exe",
        str(BINARY_PATH.resolve()),
    ]
    rewritten["all_references_bound"] = False
    rewritten.pop("reference_catalog_hash", None)
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": (
                "V155 adaptive complete low E01-E20 queue-gated training; never "
                "a formal result or paper superiority claim"
            ),
            "v155_role": "result_blind_complete_low_training",
            "v155_plan_sha256": PLAN_SHA256,
            "v155_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v155_protocol_source_commit": protocol_source_commit,
            "v155_binary_sha256": BINARY_SHA256,
            "v155_arm_id": ARM_ID,
            "v155_profile": PROFILE,
            "v155_queue_density_threshold": QUEUE_THRESHOLD,
            "v155_environment": COMMON_ENVIRONMENT,
            "v155_expected_run_count": 20,
            "v155_expected_reference_build_count": 20,
            "v155_fixed_order": list(SEEDS),
            "v155_candidate_performance_summaries_parsed": 0,
            "v155_confirmation_inputs_generated": False,
        }
    )
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"].update(COMMON_ENVIRONMENT)
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = {
            "v155_training_only": True,
            "v155_role": "result_blind_complete_low_training",
            "v155_plan_sha256": PLAN_SHA256,
            "v155_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v155_protocol_source_commit": protocol_source_commit,
            "v155_binary_sha256": BINARY_SHA256,
            "v155_arm_id": ARM_ID,
            "v155_profile": PROFILE,
            "v155_queue_density_threshold": QUEUE_THRESHOLD,
            "v155_source_e1_run_id": source_run_id,
            "v155_source_e1_run_spec_hash": source_run_spec_hash,
            "v155_candidate_performance_summaries_parsed_before_run": 0,
            "v155_confirmation_inputs_generated": False,
        }
        run["reference_dependency"] = _reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        _assign_run_identity(run)
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker["selected_run_count"] = 20
    marker["selected_reference_build_count"] = 20
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, references_bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == 20
        and {run["seed"] for run in manifest["runs"]} == set(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and {
            (run["workload"]["request_freq"], run["cluster"]["node_count"])
            for run in manifest["runs"]
        }
        == {("low", 20)}
        and len(manifest.get("reference_build_dependencies", [])) == 20
        and manifest.get("all_references_bound") is references_bound
    ):
        raise RuntimeError("V155 exact low E01-E20 product changed")
    expected = {**COMMON_ENVIRONMENT, "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE}
    for run in manifest["runs"]:
        if (
            run["experiment_id"] != "E1"
            or run["cluster"]["topology"] != "homogeneous"
            or any(
                run["environment"].get(key) != value for key, value in expected.items()
            )
            or run.get("metadata", {}).get("v155_profile") != PROFILE
            or run.get("metadata", {}).get("v155_queue_density_threshold")
            != QUEUE_THRESHOLD
        ):
            raise RuntimeError(f"V155 run contract changed: {run.get('run_id')}")


def prepare_v155(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V155 root: {root}")
    root.mkdir(parents=True)
    protocol_source_commit = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], text=True
    ).strip()
    manifest = _rewrite_candidate(source, protocol_source_commit)
    _validate_product(manifest, references_bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LOW_SCHEDULE_V155_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [
            next(run["run_id"] for run in manifest["runs"] if run["seed"] == seed)
            for seed in SEEDS
        ],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LOW_PREPARED_V155_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "training_only": True,
        "candidate_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "implementation_commit": BINARY_SOURCE_COMMIT,
        "protocol_source_commit": protocol_source_commit,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": PYTHON_SHA256,
        "cargo_lock_sha256": CARGO_LOCK_SHA256,
        "module_conf_sha256": MODULE_CONF_SHA256,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_manifest_file_sha256": SOURCE_MANIFEST_SHA256,
        "source_pairing_file_sha256": SOURCE_PAIRING_SHA256,
        "v150_result_file_sha256": V150_RESULT_SHA256,
        "v150_result_hash": V150_RESULT_HASH,
        "candidate_online_runs": 20,
        "candidate_reference_builds": 20,
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "schedule_hash": schedule["schedule_hash"],
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "profile": PROFILE,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "environment": COMMON_ENVIRONMENT,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def execute_v155(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V155 execution receipt already exists")
    prepared = read_json(output["prepared"])
    _assert_hashed(prepared, "receipt_hash", "V155 prepared receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    dispatches = []
    log_root = root / "execution-logs"
    log_root.mkdir(parents=True, exist_ok=True)
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = log_root / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = log_root / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(output["ready"]),
            str(output["workspace"]),
            "--run-id",
            run["run_id"],
        ]
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V155 dispatch {seed} failed: {completed.returncode}")
        canonical = output["workspace"] / "canonical" / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        attempt = read_json(canonical / "attempt.json")
        qc = read_json(canonical / "qc_report.json")
        if not (
            attempt.get("classification") == "qc_pass"
            and attempt.get("timed_out") is False
            and qc.get("passed") is True
            and qc.get("classification") == "qc_pass"
        ):
            raise RuntimeError(f"V155 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "exit_code": completed.returncode,
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_path": str(stdout_path),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_path": str(stderr_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LOW_EXECUTION_V155_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": 20,
        "dispatches": dispatches,
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _audit_nash_log(canonical: Path, run: Mapping[str, Any]) -> dict[str, Any]:
    run_id = run["run_id"]
    log = canonical / "reviewer_records" / run_id / "nash_metrics.jsonl.gz"
    if not log.is_file():
        raise RuntimeError(f"V155 Nash log is missing: {run_id}")
    run_config_count = 0
    window_count = 0
    summary_count = 0
    function_profile_count = 0
    low_route_count = 0
    high_route_count = 0
    reference_available = 0
    reference_not_requested = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind == "run_config":
                run_config_count += 1
                contract = event.get("operational_expert_proxy_contract", {})
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("operational_expert_proxy") == PROFILE
                    and event.get("operational_direct_initialization") is True
                    and event.get("operational_unrestricted_initialization") is True
                    and event.get("reference", {}).get("mode") == "offline_required"
                    and event.get("reference", {}).get("offline_load_ok") is True
                    and contract.get("version") == "V155"
                    and contract.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and contract.get("below_threshold_expert") == LOW_EXPERT
                    and contract.get("at_or_above_threshold_expert") == HIGH_EXPERT
                    and contract.get("uses_completed_request_outcomes") is False
                    and contract.get("reference_policy_independent") is True
                ):
                    raise RuntimeError("V155 run_config contract changed")
            elif kind == "window":
                if event.get("frame") != window_count:
                    raise RuntimeError("V155 scheduler window sequence changed")
                decision_hash = event.get("decision", {}).get("assignment_hash")
                if isinstance(decision_hash, bool) or not isinstance(
                    decision_hash, int
                ):
                    raise RuntimeError("V155 final assignment hash is invalid")
                route = event.get("decision", {}).get("srpt_hiku2_ocs_queue_router", {})
                density = route.get("queue_density")
                selected = route.get("selected_expert")
                if not (
                    route.get("enabled") is True
                    and isinstance(density, (int, float))
                    and not isinstance(density, bool)
                    and math.isfinite(float(density))
                    and float(density) >= 0.0
                    and route.get("queue_density_threshold") == QUEUE_THRESHOLD
                    and route.get("uses_completion_outcomes") is False
                ):
                    raise RuntimeError("V155 route telemetry is incomplete")
                expected = (
                    LOW_EXPERT if float(density) < QUEUE_THRESHOLD else HIGH_EXPERT
                )
                if selected != expected:
                    raise RuntimeError(
                        "V155 route does not match current queue density"
                    )
                low_route_count += selected == LOW_EXPERT
                high_route_count += selected == HIGH_EXPERT
                social = event.get("social", {})
                key = social.get("reference_state_key")
                source = social.get("reference_source")
                if key is None:
                    if source != "not_requested":
                        raise RuntimeError("V155 unrequested reference reason changed")
                    reference_not_requested += 1
                elif source in ("offline_table", "offline_table_nonpositive"):
                    reference_available += 1
                else:
                    raise RuntimeError("V155 bound reference source changed")
                window_count += 1
            elif kind == "run_summary":
                summary_count += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V155 Nash terminal marker changed")
            elif kind == "function_profile":
                # This established observation kind is metadata outside the
                # scheduler-window contract.  The blind audit deliberately
                # counts only its kind and never reads its payload.
                function_profile_count += 1
            else:
                raise RuntimeError(f"unexpected V155 Nash observation kind: {kind}")
    if run_config_count != 1 or window_count != 1000 or summary_count != 1:
        raise RuntimeError("V155 Nash log cardinality changed")
    if reference_available + reference_not_requested != window_count:
        raise RuntimeError("V155 reference replay coverage changed")
    return {
        "run_id": run_id,
        "seed": run["seed"],
        "windows": window_count,
        "below_threshold_route_windows": low_route_count,
        "at_or_above_threshold_route_windows": high_route_count,
        "offline_reference_windows": reference_available,
        "legitimate_not_requested_windows": reference_not_requested,
        "function_profile_records_seen_without_payload_access": function_profile_count,
        "performance_outcome_fields_parsed": 0,
    }


def blind_audit_v155(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V155 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = _assert_hashed(prepared, "receipt_hash", "V155 prepared receipt")
    execution = read_json(output["execution"])
    execution_hash = _assert_hashed(execution, "receipt_hash", "V155 execution receipt")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, references_bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed") is True
        and pairing.get("run_count") == 20
        and pairing.get("group_count") == 20
    ):
        raise RuntimeError("V155 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = _validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=20
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V155 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {path.name for path in canonical_root.iterdir() if path.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V155 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V155 has unexplained quarantined attempts")
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    audits = []
    identities = set()
    for seed in SEEDS:
        run = by_seed[seed]
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit = read_json(canonical / "manifest.json")
        software = audit.get("software_environment", {})
        identities.add(
            (
                audit.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        audits.append(_audit_nash_log(canonical, run))
    if len(identities) != 1:
        raise RuntimeError("V155 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == PYTHON_SHA256
        and cargo == CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V155 runtime identity changed")
    low_routes = sum(item["below_threshold_route_windows"] for item in audits)
    high_routes = sum(item["at_or_above_threshold_route_windows"] for item in audits)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LOW_BLIND_AUDIT_V155_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "aggregate_runtime_breadth_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "result_blind_audit_amendment_path": str(AMENDMENT),
        "result_blind_audit_amendment_file_sha256": AMENDMENT_SHA256,
        "result_blind_audit_schema_amendment_path": str(AMENDMENT_B),
        "result_blind_audit_schema_amendment_file_sha256": AMENDMENT_B_SHA256,
        "result_blind_audit_record_kind_amendment_path": str(AMENDMENT_C),
        "result_blind_audit_record_kind_amendment_file_sha256": AMENDMENT_C_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": 20,
        "window_count": sum(item["windows"] for item in audits),
        "below_threshold_route_windows": low_routes,
        "at_or_above_threshold_route_windows": high_routes,
        "function_profile_records_seen_without_payload_access": sum(
            item["function_profile_records_seen_without_payload_access"]
            for item in audits
        ),
        "both_routes_exercised": low_routes > 0 and high_routes > 0,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "module_conf_identity": _assert_json_semantic(
            Path("serverless_sim/module_conf_es.json"),
            MODULE_CONF_SEMANTIC_HASH,
            "frozen module_conf_es.json",
        ),
        "profile": PROFILE,
        "queue_density_threshold": QUEUE_THRESHOLD,
        "per_run_result_blind_audits": audits,
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _load_candidate(
    manifest: Mapping[str, Any], root: Path = ROOT
) -> list[dict[str, Any]]:
    rows = []
    for run in manifest["runs"]:
        summary_path = (
            paths(root)["workspace"]
            / "canonical"
            / run["run_id"]
            / "reviewer_records"
            / run["run_id"]
            / "summary.json"
        )
        values = _nse_summary_metrics(read_json(summary_path))
        rows.append(
            {
                "load": "low",
                "seed": run["seed"],
                "run_id": run["run_id"],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    if len(rows) != 20 or {row["seed"] for row in rows} != set(SEEDS):
        raise RuntimeError("V155 candidate result product changed")
    return rows


def reveal_v155(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V155 result already exists")
    blind = read_json(output["blind"])
    blind_hash = _assert_hashed(blind, "blind_audit_hash", "V155 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("aggregate_runtime_breadth_fields_parsed") == 0
    ):
        raise RuntimeError("V155 blind audit did not authorize reveal")
    manifest = load_and_validate_manifest(output["ready"])
    candidate = _load_candidate(manifest, root)
    baselines = _load_baselines()
    evaluation = _evaluate_load("low", candidate, baselines)
    mechanism_gate = {
        "below_threshold_route_windows": blind["below_threshold_route_windows"],
        "at_or_above_threshold_route_windows": blind[
            "at_or_above_threshold_route_windows"
        ],
        "both_routes_exercised": blind["both_routes_exercised"],
        "pass": blind["both_routes_exercised"],
    }
    passed = evaluation["all_three_metric_gates_pass"] and mechanism_gate["pass"]
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LOW_TRAINING_RESULT_V155_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "candidate_run_count": 20,
        "reused_frozen_baseline_run_count": 180,
        "baseline_rerun_count": 0,
        "profile": PROFILE,
        "low_evaluation": evaluation,
        "mechanism_gate": mechanism_gate,
        "joint_training_pass": passed,
        "disposition": (
            "training_pass_requires_separate_fresh_confirmation_plan_and_unopened_inputs"
            if passed
            else "retain_all_v155_runs_and_retire_profile_without_threshold_tuning_or_confirmation_inputs"
        ),
        "confirmation_inputs_generated": False,
        "fresh_confirmation_inputs_opened": False,
        "homogeneous_low_claim_closed": False,
        "middle_or_later_execution_authorized": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action", choices=("prepare", "execute", "blind-audit", "reveal")
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "prepare":
        document = prepare_v155()
        key = "receipt_hash"
    elif action == "execute":
        document = execute_v155()
        key = "receipt_hash"
    elif action == "blind-audit":
        document = blind_audit_v155()
        key = "blind_audit_hash"
    else:
        document = reveal_v155()
        key = "result_hash"
    print(json.dumps({key: document[key], "runs": 20}))


if __name__ == "__main__":
    main()
