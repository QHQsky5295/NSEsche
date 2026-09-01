from __future__ import annotations

import argparse
import gzip
import hashlib
import json
import math
import subprocess
from pathlib import Path
from typing import Any, Mapping, Sequence

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_concurrent2_queue8_cpu2_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v179 as v179,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_cpu_bounded_terminal_slack_short_work_pipeline_queue8_low_diagnostic_v168 as v168,
)
from scripts.reviewer_experiments.protocol import (
    nse_e1_homogeneous_v177_equivalence_complete_training_v181 as v181,
)
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.pairing import audit_manifest_pairing
from scripts.reviewer_experiments.protocol.schema import (
    load_and_validate_manifest,
    validate_manifest,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path(
    "tmp/nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_"
    "equivalence_complete_training_20260901_v182"
)
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_slack_short_work_"
    "pipeline_queue8_low_equivalence_complete_training_plan_v182.json"
)
PLAN_SHA256 = "027ed3bdbc2deb5b5d792991ad0eacbab6bddc5d4105ea58255b29c5801c9fed"
PLAN_COMMIT = "b26c6b889c3288b9ba9140f0347bc044e5b86b2b"
IMPLEMENTATION = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e1_homogeneous_concurrent2_queue8_cpu_bounded_terminal_slack_short_work_"
    "pipeline_queue8_low_equivalence_complete_training_implementation_v182.json"
)
IMPLEMENTATION_SHA256 = (
    "16e2ecb9ddc7fe453271e3b47600fcd9ad248b1bd02e83fa2f9fb54218035382"
)
IMPLEMENTATION_RECEIPT_HASH = (
    "cb8b4cb61243b8784278e083cdce621456cbc8e48508f9736af2f0cbd05fdee9"
)
IMPLEMENTATION_COMMIT = "95b3bd078355c7674244e7b2a79bd0433b47bb2c"
GOAL = v181.GOAL
GOAL_SHA256 = v181.GOAL_SHA256

SEEDS = ("E03", "E04", "E07", "E18")
V179_EQUIVALENT = ("E01", "E05", "E06", "E17")
V168_EQUIVALENT = ("E09",)
V177_EQUIVALENT = (
    "E02",
    "E08",
    "E10",
    "E11",
    "E12",
    "E13",
    "E14",
    "E15",
    "E16",
    "E19",
    "E20",
)
ARM_ID = "v182-low-queue8-lone-heavy-equivalence-complete-training"
PROFILE = (
    "srpt_slack_concurrent2_queue8_cpu_bounded_terminal_short5p5_pipeline_"
    "hiku2_ocs_queue8"
)
FRONTIER = (
    "parents_completed_or_concurrent2_queue8_cpu_bounded_terminal_or_slack_"
    "short_work_parents_scheduled"
)
PORT = v181.PORT
BINARY_PATH = Path("serverless_sim/target_e1_v182/release/serverless_sim.exe")
BINARY_SHA256 = "0e5f555d3709d530f3984c3a973443d3fd37192fc907d9a0122f21fd3c5cde8a"
BINARY_SOURCE_COMMIT = IMPLEMENTATION_COMMIT
QUEUE_THRESHOLD = 8.0
PREVIOUS_QUEUE_THRESHOLD = 32.0
HEAVY_PLAYER_THRESHOLD = 1
CPU_THRESHOLD = 1.0
RECORDS_ROOT = v181.RECORDS_ROOT


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "manifest": root / f"manifest.{ARM_ID}.unbound.json",
        "prepared": root / "prepared-v182.json",
        "schedule": root / "frozen-run-order-v182.json",
        "catalog": root / "references.catalog.json",
        "reference_workspace": root / "stages",
        "reference_execution": root / "reference-execution-receipt-v182.json",
        "ready": root / f"manifest.{ARM_ID}.ready.json",
        "workspace": root / "formal-runs",
        "execution": root / "execution-receipt-v182.json",
        "pairing": root / "pairing-audit-v182.json",
        "blind": root / "joint-blind-audit-v182.json",
        "result": root / "complete-training-result-v182.json",
    }


def _reread_goal() -> None:
    if hashlib.sha256(GOAL.read_bytes()).hexdigest() != GOAL_SHA256:
        raise RuntimeError("goal objective changed")


def _records_snapshot() -> dict[str, Any]:
    return v181._records_snapshot()


def _source_product_specs() -> list[tuple[str, Mapping[str, Any], Path]]:
    specs = []
    raw = (
        (
            "v177",
            v181.v177.paths()["ready"],
            v181.v177.paths()["workspace"] / "canonical",
        ),
        (
            "v176",
            v181.v176.paths()["ready"],
            v181.v176.paths()["workspace"] / "canonical",
        ),
        (
            "v170_first",
            v181.v175.v170.paths()["ready"],
            v181.v175.v170.paths()["workspace"] / "canonical",
        ),
        (
            "v170_remaining",
            v181.v175.v170remaining.paths()["ready"],
            v181.v175.v170remaining.paths()["workspace"] / "canonical",
        ),
        (
            "v181",
            v181.paths()["ready"],
            v181.paths()["workspace"] / "canonical",
        ),
        ("v179", v179.paths()["ready"], v179.paths()["workspace"] / "canonical"),
        ("v168", v168.paths()["ready"], v168.paths()["workspace"] / "canonical"),
    )
    for label, manifest_path, canonical_root in raw:
        specs.append((label, load_and_validate_manifest(manifest_path), canonical_root))
    return specs


def _entry_for_seed(
    specs: Sequence[tuple[str, Mapping[str, Any], Path]], label: str, seed: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Path]:
    matches = []
    for product_label, manifest, canonical_root in specs:
        if product_label != label:
            continue
        matches.extend(
            (manifest, run, canonical_root / run["run_id"])
            for run in manifest["runs"]
            if run["seed"] == seed
        )
    if len(matches) != 1:
        raise RuntimeError(f"V182 source product {label}/{seed} is not unique")
    return matches[0]


def _v177_equivalent_source(
    specs: Sequence[tuple[str, Mapping[str, Any], Path]], seed: str
) -> tuple[Mapping[str, Any], Mapping[str, Any], Path]:
    if seed in v181.SEEDS:
        return _entry_for_seed(specs, "v181", seed)
    if seed in v181.V177_EXISTING:
        return _entry_for_seed(specs, "v177", seed)
    if seed in v181.V176_EQUIVALENT:
        return _entry_for_seed(specs, "v176", seed)
    if seed not in v181.V170_EQUIVALENT:
        raise RuntimeError(f"seed is absent from the frozen V181 partition: {seed}")
    matches = []
    for label in ("v170_first", "v170_remaining"):
        try:
            matches.append(_entry_for_seed(specs, label, seed))
        except RuntimeError:
            pass
    if len(matches) != 1:
        raise RuntimeError(f"V170 source for {seed} is not unique")
    return matches[0]


def _nash_log(canonical: Path, run: Mapping[str, Any]) -> Path:
    return canonical / "reviewer_records" / run["run_id"] / "nash_metrics.jsonl.gz"


def _strict_count(value: Any, label: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeError(f"{label} is malformed")
    return value


def _finite(value: Any, label: str) -> float:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(float(value))
    ):
        raise RuntimeError(f"{label} is malformed")
    return float(value)


def _scan_branch_log(log: Path) -> dict[str, Any]:
    counts = {"run_config": 0, "window": 0, "run_summary": 0}
    assignments: list[int] = []
    exact_one_q_lt8 = 0
    exact_one_q_ge8 = 0
    exact_one_q8_lt32 = 0
    exact_one_q_ge8_cpu_gt2 = 0
    heavy_ge2 = 0
    first_q8_lt32 = None
    first_q8_lt32_detail = None
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind == "run_config":
                counts["run_config"] += 1
                continue
            if kind == "run_summary":
                counts["run_summary"] += 1
                continue
            if kind == "function_profile":
                continue
            if kind != "window":
                raise RuntimeError(f"unexpected Nash event kind: {kind}")
            frame = counts["window"]
            counts["window"] += 1
            if event.get("frame") != frame:
                raise RuntimeError("Nash window sequence changed")
            decision = event.get("decision", {})
            assignment = decision.get("assignment_hash")
            if isinstance(assignment, bool) or not isinstance(assignment, int):
                raise RuntimeError("assignment hash is malformed")
            assignments.append(assignment)
            frontier = decision.get("terminal_pipeline_frontier", {})
            guard = frontier.get("cpu_bounded_terminal_guard", {})
            activation = guard.get("capacity_overload_activation", {})
            if "heavy_incomplete_parent_terminal_players" in activation:
                heavy = _strict_count(
                    activation.get("heavy_incomplete_parent_terminal_players"),
                    "heavy player count",
                )
            else:
                # V168 predates capacity-overload telemetry. Its immutable-CPU
                # guard is always active and rejects every heavy player, so the
                # rejected-heavy count is the exact historical heavy count.
                heavy = _strict_count(
                    guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                    "legacy V168 heavy player count",
                )
            density = _finite(
                decision.get("srpt_hiku2_ocs_queue_router", {}).get("queue_density"),
                "operational queue density",
            )
            if heavy >= 2:
                heavy_ge2 += 1
            if heavy != 1:
                continue
            if density < QUEUE_THRESHOLD:
                exact_one_q_lt8 += 1
            else:
                exact_one_q_ge8 += 1
                lone_cpu = activation.get("lone_heavy_normalized_cpu")
                if lone_cpu is not None and _finite(lone_cpu, "lone-heavy CPU") > 2.0:
                    exact_one_q_ge8_cpu_gt2 += 1
            if QUEUE_THRESHOLD <= density < PREVIOUS_QUEUE_THRESHOLD:
                exact_one_q8_lt32 += 1
                if first_q8_lt32 is None:
                    first_q8_lt32 = frame
                    first_q8_lt32_detail = {
                        "frame": frame,
                        "heavy": heavy,
                        "density": density,
                    }
    if counts != {"run_config": 1, "window": 1000, "run_summary": 1}:
        raise RuntimeError(f"Nash observation cardinality changed: {counts}")
    return {
        "windows": 1000,
        "assignments": tuple(assignments),
        "assignment_sequence_sha256": v181.v177._assignment_sequence_sha256(
            assignments
        ),
        "exact_one_q_lt8": exact_one_q_lt8,
        "exact_one_q_ge8": exact_one_q_ge8,
        "exact_one_q8_lt32": exact_one_q8_lt32,
        "exact_one_q_ge8_cpu_gt2": exact_one_q_ge8_cpu_gt2,
        "heavy_ge2_windows": heavy_ge2,
        "first_q8_lt32_frame": first_q8_lt32,
        "first_q8_lt32_detail": first_q8_lt32_detail,
    }


def _validate_source_entry(
    manifest: Mapping[str, Any], run: Mapping[str, Any], canonical: Path
) -> dict[str, Any]:
    validate_canonical_run(
        run,
        canonical,
        expected_manifest_hash=manifest["manifest_hash"],
        result_relative_path="reviewer_records/{run_id}/summary.json",
    )
    return _scan_branch_log(_nash_log(canonical, run))


def _verify_equivalence_partition(plan: Mapping[str, Any]) -> dict[str, Any]:
    partition = plan["fixed_twenty_seed_partition"]
    if not (
        tuple(partition["v179_behavior_equivalent"]) == V179_EQUIVALENT
        and tuple(partition["v168_behavior_equivalent"]) == V168_EQUIVALENT
        and tuple(partition["v177_behavior_equivalent"]) == V177_EQUIVALENT
        and tuple(partition["new_v182_required"]) == SEEDS
        and tuple(partition["new_run_order"]) == SEEDS
        and len(set(V179_EQUIVALENT + V168_EQUIVALENT + V177_EQUIVALENT + SEEDS)) == 20
    ):
        raise RuntimeError("V182 fixed partition changed")
    specs = _source_product_specs()
    v177_scans: dict[str, dict[str, Any]] = {}
    for index in range(1, 21):
        seed = f"E{index:02d}"
        manifest, run, canonical = _v177_equivalent_source(specs, seed)
        v177_scans[seed] = _validate_source_entry(manifest, run, canonical)
    evidence = plan["result_blind_branch_evidence"]
    for seed, expected in evidence["v177_counterfactual_new_branch"].items():
        manifest, run, canonical = _v177_equivalent_source(specs, seed)
        if run["run_id"] != expected["run_id"]:
            raise RuntimeError(f"V182 {seed} frozen V177 run changed")
        v181._assert_file(_nash_log(canonical, run), expected["nash_sha256"], seed)
        scan = v177_scans[seed]
        if not (
            scan["exact_one_q8_lt32"] == expected["q8_lt32_windows"]
            and scan["first_q8_lt32_frame"] == expected["first_frame"]
        ):
            raise RuntimeError(f"V182 {seed} new-branch evidence changed")
    expected_v177 = evidence["v177_equivalent_rows_have_q8_lt32_windows"]
    if set(expected_v177) != set(V177_EQUIVALENT):
        raise RuntimeError("V182 V177-equivalent evidence keys changed")
    for seed, expected_count in expected_v177.items():
        if v177_scans[seed]["exact_one_q8_lt32"] != expected_count:
            raise RuntimeError(f"V182 {seed} V177 equivalence changed")
    for seed, expected in evidence["v179_equivalent_rows"].items():
        manifest, run, canonical = _entry_for_seed(specs, "v179", seed)
        if run["run_id"] != expected["run_id"]:
            raise RuntimeError(f"V179 source run changed for {seed}")
        v181._assert_file(_nash_log(canonical, run), expected["nash_sha256"], seed)
        scan = _validate_source_entry(manifest, run, canonical)
        if not (
            scan["exact_one_q_ge8"] == expected["exact_one_q_ge8"]
            and scan["exact_one_q_ge8_cpu_gt2"] == expected["unbounded_cpu_q_ge8"]
        ):
            raise RuntimeError(f"V179-to-V182 branch equivalence changed for {seed}")
    seed = V168_EQUIVALENT[0]
    expected = evidence["v168_equivalent_row"][seed]
    manifest, run, canonical = _entry_for_seed(specs, "v168", seed)
    if run["run_id"] != expected["run_id"]:
        raise RuntimeError("V168 E09 source run changed")
    v181._assert_file(_nash_log(canonical, run), expected["nash_sha256"], seed)
    scan = _validate_source_entry(manifest, run, canonical)
    if not (
        scan["exact_one_q_lt8"] == expected["exact_one_q_lt8"]
        and scan["exact_one_q_ge8"] == expected["exact_one_q_ge8"]
        and scan["heavy_ge2_windows"] == expected["heavy_ge2_windows"]
    ):
        raise RuntimeError("V168-to-V182 E09 branch equivalence changed")
    return {
        "source_window_count": 25000,
        "performance_fields_parsed": 0,
        "role_counts": {
            "v179_behavior_equivalent": len(V179_EQUIVALENT),
            "v168_behavior_equivalent": len(V168_EQUIVALENT),
            "v177_behavior_equivalent": len(V177_EQUIVALENT),
            "new_v182_required": len(SEEDS),
        },
        "partition_pass": True,
    }


def _assert_frozen_inputs() -> Mapping[str, Any]:
    source = v181._assert_frozen_inputs()
    for path, sha256, label in (
        (PLAN, PLAN_SHA256, "V182 plan"),
        (IMPLEMENTATION, IMPLEMENTATION_SHA256, "V182 implementation receipt"),
        (GOAL, GOAL_SHA256, "goal objective"),
        (BINARY_PATH, BINARY_SHA256, "V182 release binary"),
        (v181.PYTHON_PATH, v181.PYTHON_SHA256, "frozen Python"),
        (
            Path("serverless_sim/Cargo.lock"),
            v181.CARGO_LOCK_SHA256,
            "frozen Cargo.lock",
        ),
    ):
        v181._assert_file(path, sha256, label)
    implementation = read_json(IMPLEMENTATION)
    if not (
        v181._assert_hashed(
            implementation, "receipt_hash", "V182 implementation receipt"
        )
        == IMPLEMENTATION_RECEIPT_HASH
        and implementation["implementation_commit"] == IMPLEMENTATION_COMMIT
        and implementation["isolated_release"]["sha256"] == BINARY_SHA256
        and implementation["execution_state_at_seal"]
        == {
            "v182_reference_builds_started": 0,
            "v182_online_runs_started": 0,
            "v182_performance_summaries_parsed": 0,
        }
    ):
        raise RuntimeError("V182 implementation receipt changed")
    plan = read_json(PLAN)
    if not (
        plan["training_only"] is True
        and plan["formal_results_eligible"] is False
        and plan["scientific_status"]["performance_results_consulted_for_design"]
        is True
        and plan["scientific_status"]["no_gate_tolerance_or_comparator_changed"] is True
        and plan["candidate"]["profile"] == PROFILE
        and plan["candidate"]["player_frontier"] == FRONTIER
        and plan["candidate"]["queue_density_threshold"] == QUEUE_THRESHOLD
        and plan["candidate"]["normalized_cpu_upper_threshold"] is None
        and plan["execution_contract"]["new_online_runs"] == len(SEEDS)
        and plan["execution_contract"]["new_reference_builds"] == len(SEEDS)
        and plan["execution_contract"]["baseline_reruns"] == 0
        and plan["execution_contract"][
            "no_seed_deletion_replacement_relabeling_or_selective_rerun"
        ]
        is True
    ):
        raise RuntimeError("V182 plan contract changed")
    for expected in plan["frozen_failure_boundaries"].values():
        path = Path(expected["path"])
        v181._assert_file(path, expected["sha256"], "V182 frozen failure")
        if (
            v181._assert_hashed(read_json(path), "receipt_hash", "frozen failure")
            != expected["receipt_hash"]
        ):
            raise RuntimeError("V182 frozen failure receipt changed")
    for label, expected in plan["frozen_source_manifests"].items():
        if label == "other_v177_equivalent_sources":
            continue
        path = Path(expected["path"])
        v181._assert_file(path, expected["sha256"], label)
        manifest = load_and_validate_manifest(path)
        if manifest["manifest_hash"] != expected["manifest_hash"]:
            raise RuntimeError(f"V182 frozen source manifest changed: {label}")
    _verify_equivalence_partition(plan)
    v181._assert_json_semantic(
        Path("serverless_sim/module_conf_es.json"),
        v181.MODULE_CONF_SEMANTIC_HASH,
        "frozen module_conf_es.json",
    )
    snapshot = _records_snapshot()
    if not (
        snapshot["file_count"] == 6
        and snapshot["bytes"] == 254320
        and snapshot["manifest_hash"]
        == "2f9387fd8b80b60e16f7cda8cdd11e4abc64f3e080135aa09e28e944dca3ea0f"
    ):
        raise RuntimeError("shared serverless_sim/records changed")
    return source


def _metadata(commit: str, source: Mapping[str, Any]) -> dict[str, Any]:
    return {
        "v182_training_only": True,
        "v182_role": "fixed_four_run_complement_for_complete_queue8_lone_heavy_profile",
        "v182_plan_sha256": PLAN_SHA256,
        "v182_plan_commit": PLAN_COMMIT,
        "v182_implementation_receipt_hash": IMPLEMENTATION_RECEIPT_HASH,
        "v182_protocol_source_commit": commit,
        "v182_binary_source_commit": BINARY_SOURCE_COMMIT,
        "v182_binary_sha256": BINARY_SHA256,
        "v182_profile": PROFILE,
        "v182_player_frontier": FRONTIER,
        "v182_source_e1_run_id": source.get("v155_source_e1_run_id"),
        "v182_source_e1_run_spec_hash": source.get("v155_source_e1_run_spec_hash"),
        "v182_performance_summaries_parsed_before_run": 0,
        "v182_seed_selection_uses_branch_telemetry_only": True,
        "v182_valid_seed_deletion_replacement_or_selective_rerun": False,
    }


def _rewrite_candidate(source: dict[str, Any], commit: str) -> dict[str, Any]:
    rewritten = v181.v155._rewrite_candidate(source, commit)
    by_seed = {run["seed"]: run for run in rewritten["runs"]}
    if set(by_seed) != {f"E{i:02d}" for i in range(1, 21)}:
        raise RuntimeError("V155 complete low source product changed")
    rewritten["runs"] = [by_seed[seed] for seed in SEEDS]
    rewritten["execution"]["command_template"][-1] = str(BINARY_PATH.resolve())
    marker = rewritten["integration_smoke_shard"]
    lineage = {item["source_seed"]: item for item in marker["selected_source_runs"]}
    marker["selected_source_runs"] = [lineage[seed] for seed in SEEDS]
    for key in list(marker):
        if key.startswith("v155_"):
            marker.pop(key)
    marker.update(
        {
            "purpose": "V182 fixed four-run complement for one complete queue8 lone-heavy training profile",
            "v182_role": "fixed_four_run_complement_for_complete_queue8_lone_heavy_profile",
            "v182_plan_sha256": PLAN_SHA256,
            "v182_plan_commit": PLAN_COMMIT,
            "v182_implementation_receipt_hash": IMPLEMENTATION_RECEIPT_HASH,
            "v182_protocol_source_commit": commit,
            "v182_binary_source_commit": BINARY_SOURCE_COMMIT,
            "v182_binary_sha256": BINARY_SHA256,
            "v182_profile": PROFILE,
            "v182_player_frontier": FRONTIER,
            "v182_expected_run_count": len(SEEDS),
            "v182_expected_reference_build_count": len(SEEDS),
            "v182_fixed_order": list(SEEDS),
            "v182_performance_summaries_parsed": 0,
            "v182_seed_selection_uses_branch_telemetry_only": True,
            "v182_environment": v181.COMMON_ENVIRONMENT,
        }
    )
    for run in rewritten["runs"]:
        run["variant"] = ARM_ID
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run["environment"]["NASH_OPERATIONAL_EXPERT_PROXY"] = PROFILE
        run["metadata"] = _metadata(commit, run.get("metadata", {}))
        run["reference_dependency"] = v181._reference_dependency(run)
        run["simulator_experiment"]["reference"] = {
            "mode": "offline_required",
            "table_path": run["reference_dependency"]["path"],
            "build_output_path": "",
        }
        v181._assign_run_identity(run)
    rewritten["reference_build_dependencies"] = v181._reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = v181._matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker["selected_run_count"] = len(SEEDS)
    marker["selected_reference_build_count"] = len(SEEDS)
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def _validate_product(manifest: Mapping[str, Any], *, bound: bool) -> None:
    if not (
        len(manifest.get("runs", [])) == len(SEEDS)
        and [run["seed"] for run in manifest["runs"]] == list(SEEDS)
        and {run["method"] for run in manifest["runs"]} == {"sche_nash"}
        and len(manifest.get("reference_build_dependencies", [])) == len(SEEDS)
        and manifest.get("all_references_bound") is bound
    ):
        raise RuntimeError("V182 exact four-run product changed")
    expected_env = {
        **v181.COMMON_ENVIRONMENT,
        "NASH_OPERATIONAL_EXPERT_PROXY": PROFILE,
    }
    for run in manifest["runs"]:
        metadata = run.get("metadata", {})
        if not (
            run["experiment_id"] == "E1"
            and run["workload"]["request_freq"] == "low"
            and run["cluster"] == {"node_count": 20, "topology": "homogeneous"}
            and all(run["environment"].get(k) == v for k, v in expected_env.items())
            and run["environment"].get("SERVERLESS_SIM_PORT") == PORT
            and metadata.get("v182_profile") == PROFILE
            and metadata.get("v182_player_frontier") == FRONTIER
            and metadata.get("v182_seed_selection_uses_branch_telemetry_only") is True
        ):
            raise RuntimeError(f"V182 run contract changed: {run.get('run_id')}")


def prepare_v182(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V182 root: {root}")
    root.mkdir(parents=True)
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    manifest = _rewrite_candidate(dict(source), commit)
    _validate_product(manifest, bound=False)
    output = paths(root)
    write_json_atomic(output["manifest"], manifest)
    schedule = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_SCHEDULE_V182_V1",
        "created_at": utc_now(),
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "run_ids": [run["run_id"] for run in manifest["runs"]],
    }
    schedule["schedule_hash"] = object_hash(schedule)
    write_json_atomic(output["schedule"], schedule)
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_PREPARED_V182_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "candidate_performance_summaries_parsed": 0,
        "goal_objective_sha256": GOAL_SHA256,
        "plan_sha256": PLAN_SHA256,
        "plan_commit": PLAN_COMMIT,
        "implementation_receipt_hash": IMPLEMENTATION_RECEIPT_HASH,
        "protocol_source_commit": commit,
        "binary_source_commit": BINARY_SOURCE_COMMIT,
        "binary_path": str(BINARY_PATH.resolve()),
        "binary_sha256": BINARY_SHA256,
        "python_sha256": v181.PYTHON_SHA256,
        "cargo_lock_sha256": v181.CARGO_LOCK_SHA256,
        "module_conf_semantic_hash": v181.MODULE_CONF_SEMANTIC_HASH,
        "new_online_runs": len(SEEDS),
        "new_reference_builds": len(SEEDS),
        "baseline_reruns": 0,
        "fixed_order": list(SEEDS),
        "manifest_path": str(output["manifest"]),
        "manifest_file_sha256": file_hash(output["manifest"]),
        "manifest_hash": manifest["manifest_hash"],
        "schedule_path": str(output["schedule"]),
        "schedule_file_sha256": file_hash(output["schedule"]),
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "branch_partition": _verify_equivalence_partition(read_json(PLAN)),
        "shared_records_snapshot": _records_snapshot(),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["prepared"], receipt)
    return receipt


def build_references_v182(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["reference_execution"].exists() or output["ready"].exists():
        raise RuntimeError("V182 reference execution already finalized")
    prepared = read_json(output["prepared"])
    prepared_hash = v181._assert_hashed(
        prepared, "receipt_hash", "V182 prepared receipt"
    )
    manifest = load_and_validate_manifest(output["manifest"])
    _validate_product(manifest, bound=False)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "reference-execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(v181.PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "build-references",
            str(output["manifest"]),
            str(output["reference_workspace"]),
            str(output["catalog"]),
            "--run-id",
            run["run_id"],
        ]
        _reread_goal()
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(
                f"V182 reference dispatch {seed} failed: {completed.returncode}"
            )
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "stdout_sha256": file_hash(stdout_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    reference = v181._validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    bind_stdout = logs / "bind.stdout.log"
    bind_stderr = logs / "bind.stderr.log"
    command = [
        str(v181.PYTHON_PATH),
        "-m",
        "scripts.reviewer_experiments.protocol",
        "bind-references",
        str(output["manifest"]),
        str(output["catalog"]),
        str(output["ready"]),
    ]
    with bind_stdout.open("w", encoding="utf-8") as stdout, bind_stderr.open(
        "w", encoding="utf-8"
    ) as stderr:
        completed = subprocess.run(
            command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
        )
    if completed.returncode != 0:
        raise RuntimeError(f"V182 reference binding failed: {completed.returncode}")
    ready = load_and_validate_manifest(output["ready"])
    _validate_product(ready, bound=True)
    ledger_count, ledger_hash = verify_ledger(
        output["reference_workspace"] / "reference_builds" / "ledger.jsonl"
    )
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_REFERENCE_EXECUTION_V182_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "goal_reread_before_every_reference_dispatch": True,
        "prepared_receipt_hash": prepared_hash,
        "plan_sha256": PLAN_SHA256,
        "fixed_order": list(SEEDS),
        "dispatch_count": len(dispatches),
        "dispatches": dispatches,
        "reference_catalog": reference,
        "reference_catalog_file_sha256": file_hash(output["catalog"]),
        "reference_ledger_event_count": ledger_count,
        "reference_ledger_last_hash": ledger_hash,
        "ready_manifest_hash": ready["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "bind_stdout_sha256": file_hash(bind_stdout),
        "bind_stderr_sha256": file_hash(bind_stderr),
        "shared_records_snapshot": _records_snapshot(),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["reference_execution"], receipt)
    return receipt


def execute_v182(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["execution"].exists():
        raise RuntimeError("V182 execution receipt already exists")
    prepared = read_json(output["prepared"])
    v181._assert_hashed(prepared, "receipt_hash", "V182 prepared receipt")
    reference = read_json(output["reference_execution"])
    reference_hash = v181._assert_hashed(
        reference, "receipt_hash", "V182 reference execution receipt"
    )
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed before V182 execution")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, bound=True)
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    logs = root / "execution-logs"
    logs.mkdir(parents=True, exist_ok=True)
    dispatches = []
    for ordinal, seed in enumerate(SEEDS, start=1):
        run = by_seed[seed]
        stdout_path = logs / f"{ordinal:02d}-{seed}.stdout.log"
        stderr_path = logs / f"{ordinal:02d}-{seed}.stderr.log"
        command = [
            str(v181.PYTHON_PATH),
            "-m",
            "scripts.reviewer_experiments.protocol",
            "run",
            str(output["ready"]),
            str(output["workspace"]),
            "--run-id",
            run["run_id"],
        ]
        _reread_goal()
        with stdout_path.open("w", encoding="utf-8") as stdout, stderr_path.open(
            "w", encoding="utf-8"
        ) as stderr:
            completed = subprocess.run(
                command, cwd=Path.cwd(), stdout=stdout, stderr=stderr, check=False
            )
        if completed.returncode != 0:
            raise RuntimeError(f"V182 dispatch {seed} failed: {completed.returncode}")
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
            raise RuntimeError(f"V182 canonical is not a QC pass: {run['run_id']}")
        dispatches.append(
            {
                "ordinal": ordinal,
                "seed": seed,
                "run_id": run["run_id"],
                "attempt": attempt.get("attempt"),
                "attempt_file_sha256": file_hash(canonical / "attempt.json"),
                "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                "stdout_sha256": file_hash(stdout_path),
                "stderr_sha256": file_hash(stderr_path),
            }
        )
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed during V182 execution")
    receipt = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_EXECUTION_V182_V1",
        "created_at": utc_now(),
        "candidate_performance_summaries_parsed": 0,
        "goal_reread_before_every_dispatch": True,
        "plan_sha256": PLAN_SHA256,
        "reference_execution_receipt_hash": reference_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "ready_manifest_file_sha256": file_hash(output["ready"]),
        "fixed_order": list(SEEDS),
        "dispatch_count": len(SEEDS),
        "dispatches": dispatches,
        "shared_records_snapshot": _records_snapshot(),
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output["execution"], receipt)
    return receipt


def _audit_v182_log(
    canonical: Path,
    run: Mapping[str, Any],
    frozen_assignments: Sequence[int],
    expected_first_branch: int,
) -> dict[str, Any]:
    log = _nash_log(canonical, run)
    counts = {"run_config": 0, "window": 0, "run_summary": 0}
    assignments: list[int] = []
    first_new_branch = None
    active_lone_windows = 0
    active_lone_rejections = 0
    new_branch_windows = 0
    new_branch_rejections = 0
    reference_windows = 0
    with gzip.open(log, "rt", encoding="utf-8") as stream:
        for line in stream:
            event = json.loads(line)
            kind = event.get("kind")
            if kind == "run_config":
                counts["run_config"] += 1
                contract = event.get("operational_expert_proxy_contract", {})
                activation = contract.get("cpu_bounded_terminal_guard", {}).get(
                    "capacity_overload_activation", {}
                )
                checks = (
                    event.get("scheduler") == "sche_nash",
                    event.get("operational_expert_proxy") == PROFILE,
                    event.get("reference", {}).get("mode") == "offline_required",
                    event.get("reference", {}).get("offline_load_ok") is True,
                    contract.get("version") == "V182",
                    contract.get("player_frontier") == FRONTIER,
                    activation.get("capacity_threshold")
                    == "fixed_one_current_heavy_player",
                    activation.get("fixed_heavy_player_count_threshold") == 1,
                    activation.get("minimum_active_heavy_player_count") == 1,
                    activation.get("activation_boundary")
                    == "heavy_player_count_strictly_above_one_or_exactly_one_with_operational_queue_density_at_least_8",
                    activation.get("severe_single_queue_density_threshold")
                    == QUEUE_THRESHOLD,
                    activation.get("severe_single_queue_density_source")
                    == "current_pending_plus_runnable_tasks_per_node",
                    activation.get("severe_single_queue_boundary")
                    == "at_or_above_activates",
                    activation.get("bounded_single_normalized_cpu_upper_threshold")
                    is None,
                    activation.get("active_heavy_admission_policy") is None,
                    activation.get("active_heavy_admission_quota") is None,
                    activation.get("uses_seed_load_dag_function_or_performance_labels")
                    is False,
                )
                if not all(checks):
                    raise RuntimeError("V182 run_config contract changed")
                continue
            if kind == "run_summary":
                counts["run_summary"] += 1
                if not (
                    event.get("scheduler") == "sche_nash"
                    and event.get("windows") == 1000
                    and event.get("observation_writer_error") is None
                ):
                    raise RuntimeError("V182 run summary changed")
                continue
            if kind == "function_profile":
                continue
            if kind != "window":
                raise RuntimeError(f"unexpected V182 Nash event: {kind}")
            frame = counts["window"]
            counts["window"] += 1
            if event.get("frame") != frame:
                raise RuntimeError("V182 window sequence changed")
            decision = event.get("decision", {})
            assignment = decision.get("assignment_hash")
            if (
                isinstance(assignment, bool)
                or not isinstance(assignment, int)
                or decision.get("player_frontier") != FRONTIER
            ):
                raise RuntimeError("V182 assignment/frontier changed")
            assignments.append(assignment)
            frontier = decision.get("terminal_pipeline_frontier", {})
            guard = frontier.get("cpu_bounded_terminal_guard", {})
            activation = guard.get("capacity_overload_activation", {})
            heavy = _strict_count(
                activation.get("heavy_incomplete_parent_terminal_players"),
                "V182 heavy count",
            )
            density = _finite(
                activation.get("operational_queue_density"), "V182 queue density"
            )
            primary = heavy > HEAVY_PLAYER_THRESHOLD
            lone = heavy == 1 and density >= QUEUE_THRESHOLD
            active = primary or lone
            rejected = _strict_count(
                guard.get("rejected_heavy_incomplete_parent_terminal_players"),
                "V182 rejected heavy players",
            )
            inactive_admitted = _strict_count(
                activation.get("guard_inactive_heavy_terminal_admissions"),
                "V182 inactive heavy admissions",
            )
            if not (
                activation.get("enabled") is True
                and activation.get("heavy_player_count_threshold") == 1
                and activation.get("minimum_active_heavy_player_count") == 1
                and activation.get("threshold_kind") == "fixed_one_current_heavy_player"
                and activation.get("activation_boundary")
                == "heavy_count_strictly_above_one_or_exactly_one_with_queue_density_at_or_above_8_activates"
                and activation.get("operational_queue_density_source")
                == "current_pending_plus_runnable_tasks_per_node"
                and activation.get("severe_single_queue_density_threshold")
                == QUEUE_THRESHOLD
                and activation.get("severe_single_queue_boundary")
                == "at_or_above_activates"
                and activation.get("primary_heavy_count_activation") is primary
                and activation.get("severe_single_activation") is lone
                and activation.get("bounded_single_activation") is False
                and activation.get("guard_active") is active
                and activation.get("guard_inactive") is (not active)
                and rejected == (heavy if active else 0)
                and inactive_admitted == (0 if active else heavy)
                and activation.get("active_heavy_admission_policy") is None
                and activation.get("active_heavy_admission_quota") is None
                and activation.get("uses_seed_load_dag_function_or_performance_labels")
                is False
            ):
                raise RuntimeError("V182 window guard contract changed")
            route = decision.get("srpt_hiku2_ocs_queue_router", {})
            route_density = _finite(route.get("queue_density"), "V182 route density")
            if not (
                route.get("queue_density_threshold") == QUEUE_THRESHOLD
                and route.get("queue_fields")
                == "current_pending_plus_runnable_tasks_per_node"
                and route.get("player_frontier") == FRONTIER
                and route.get("selected_expert")
                == (
                    v181.v177.LOW_EXPERT
                    if route_density < QUEUE_THRESHOLD
                    else v181.v177.HIGH_EXPERT
                )
                and route.get("uses_completion_outcomes") is False
            ):
                raise RuntimeError("V182 queue router contract changed")
            social = event.get("social", {})
            if social.get("reference_state_key") is None:
                if social.get("reference_source") != "not_requested":
                    raise RuntimeError("V182 unrequested reference reason changed")
            elif social.get("reference_source") not in (
                "offline_table",
                "offline_table_nonpositive",
            ):
                raise RuntimeError("V182 offline reference source changed")
            reference_windows += 1
            if lone:
                active_lone_windows += 1
                active_lone_rejections += rejected
                if density < PREVIOUS_QUEUE_THRESHOLD:
                    new_branch_windows += 1
                    new_branch_rejections += rejected
                    if first_new_branch is None:
                        first_new_branch = frame
    if counts != {"run_config": 1, "window": 1000, "run_summary": 1}:
        raise RuntimeError(f"V182 Nash observation cardinality changed: {counts}")
    if len(frozen_assignments) != 1000 or reference_windows != 1000:
        raise RuntimeError("V182 frozen/replay window count changed")
    mismatch = [
        frame
        for frame, (candidate, frozen) in enumerate(
            zip(assignments, frozen_assignments)
        )
        if candidate != frozen
    ]
    first_mismatch = mismatch[0] if mismatch else None
    prefix_matches = tuple(assignments[:expected_first_branch]) == tuple(
        frozen_assignments[:expected_first_branch]
    )
    branch_event = first_new_branch == expected_first_branch
    first_differs = (
        assignments[expected_first_branch] != frozen_assignments[expected_first_branch]
    )
    return {
        "run_id": run["run_id"],
        "seed": run["seed"],
        "windows": 1000,
        "assignment_sequence_sha256": v181.v177._assignment_sequence_sha256(
            assignments
        ),
        "frozen_v177_equivalent_assignment_sequence_sha256": v181.v177._assignment_sequence_sha256(
            frozen_assignments
        ),
        "first_q8_lt32_lone_heavy_frame": first_new_branch,
        "expected_first_q8_lt32_frame": expected_first_branch,
        "first_assignment_mismatch_frame_vs_v177_equivalent": first_mismatch,
        "pre_first_branch_assignment_prefix_matches_v177_equivalent": prefix_matches,
        "first_branch_assignment_differs_from_v177_equivalent": first_differs,
        "first_divergence_is_first_q8_lt32_branch": first_mismatch
        == expected_first_branch
        and branch_event
        and first_differs,
        "active_lone_heavy_windows": active_lone_windows,
        "active_lone_heavy_rejections": active_lone_rejections,
        "new_q8_lt32_branch_windows": new_branch_windows,
        "new_q8_lt32_branch_rejections": new_branch_rejections,
        "new_branch_rejects_exactly_one_heavy_player": active_lone_rejections
        >= new_branch_rejections
        and new_branch_rejections == new_branch_windows
        and new_branch_windows > 0,
        "performance_outcome_fields_parsed": 0,
        "nash_metrics_sha256": file_hash(log),
    }


def blind_audit_v182(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["blind"].exists():
        raise RuntimeError("V182 blind audit already exists")
    _assert_frozen_inputs()
    prepared = read_json(output["prepared"])
    prepared_hash = v181._assert_hashed(
        prepared, "receipt_hash", "V182 prepared receipt"
    )
    reference_execution = read_json(output["reference_execution"])
    reference_hash = v181._assert_hashed(
        reference_execution, "receipt_hash", "V182 reference execution receipt"
    )
    execution = read_json(output["execution"])
    execution_hash = v181._assert_hashed(
        execution, "receipt_hash", "V182 execution receipt"
    )
    if _records_snapshot() != prepared["shared_records_snapshot"]:
        raise RuntimeError("shared records changed before V182 blind audit")
    manifest = load_and_validate_manifest(output["ready"])
    _validate_product(manifest, bound=True)
    pairing = audit_manifest_pairing(
        manifest, output["workspace"], expected_methods={"*": ["sche_nash"]}
    )
    if not (
        pairing.get("passed")
        and pairing.get("run_count") == len(SEEDS)
        and pairing.get("group_count") == len(SEEDS)
    ):
        raise RuntimeError("V182 exact pairing failed")
    write_json_atomic(output["pairing"], pairing)
    ledger_count, ledger_hash = verify_ledger(output["workspace"] / "ledger.jsonl")
    reference = v181._validate_reference_catalog(
        manifest, output["catalog"], expected_entry_count=len(SEEDS)
    )
    if [item["seed"] for item in execution["dispatches"]] != list(SEEDS):
        raise RuntimeError("V182 execution order changed")
    canonical_root = output["workspace"] / "canonical"
    if {item.name for item in canonical_root.iterdir() if item.is_dir()} != {
        run["run_id"] for run in manifest["runs"]
    }:
        raise RuntimeError("V182 canonical product changed")
    quarantine = output["workspace"] / "quarantine"
    if quarantine.exists() and any(quarantine.rglob("attempt-*")):
        raise RuntimeError("V182 has quarantined attempts")
    plan = read_json(PLAN)
    expected_frames = {
        seed: item["first_frame"]
        for seed, item in plan["result_blind_branch_evidence"][
            "v177_counterfactual_new_branch"
        ].items()
    }
    source_specs = _source_product_specs()
    audits = []
    identities = set()
    by_seed = {run["seed"]: run for run in manifest["runs"]}
    for seed in SEEDS:
        run = by_seed[seed]
        canonical = canonical_root / run["run_id"]
        validate_canonical_run(
            run,
            canonical,
            expected_manifest_hash=manifest["manifest_hash"],
            result_relative_path="reviewer_records/{run_id}/summary.json",
        )
        audit_manifest = read_json(canonical / "manifest.json")
        software = audit_manifest.get("software_environment", {})
        identities.add(
            (
                audit_manifest.get("adapter_binary", {}).get("verified_sha256"),
                software.get("git", {}).get("commit"),
                software.get("python", {}).get("executable_sha256"),
                software.get("cargo_lock", {}).get("sha256"),
            )
        )
        source_manifest, source_run, source_canonical = _v177_equivalent_source(
            source_specs, seed
        )
        source_scan = _validate_source_entry(
            source_manifest, source_run, source_canonical
        )
        audits.append(
            _audit_v182_log(
                canonical,
                run,
                source_scan["assignments"],
                int(expected_frames[seed]),
            )
        )
    if len(identities) != 1:
        raise RuntimeError("V182 runtime identity is not unanimous")
    binary, git_commit, python, cargo = next(iter(identities))
    if not (
        binary == BINARY_SHA256
        and git_commit == prepared["protocol_source_commit"]
        and python == v181.PYTHON_SHA256
        and cargo == v181.CARGO_LOCK_SHA256
    ):
        raise RuntimeError("V182 runtime identity changed")
    mechanism_pass = all(
        item["first_divergence_is_first_q8_lt32_branch"]
        and item["new_branch_rejects_exactly_one_heavy_player"]
        and item["performance_outcome_fields_parsed"] == 0
        for item in audits
    )
    if not mechanism_pass:
        raise RuntimeError("V182 pre-unblinding mechanism gate failed")
    partition = _verify_equivalence_partition(plan)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_BLIND_AUDIT_V182_V1",
        "created_at": utc_now(),
        "status": "pass",
        "performance_reveal_authorized": True,
        "throughput_completion_latency_cost_qpr_fields_parsed": 0,
        "candidate_performance_summaries_parsed": 0,
        "plan_sha256": PLAN_SHA256,
        "prepared_receipt_hash": prepared_hash,
        "reference_execution_receipt_hash": reference_hash,
        "execution_receipt_hash": execution_hash,
        "ready_manifest_hash": manifest["manifest_hash"],
        "reference_catalog": reference,
        "ledger_event_count": ledger_count,
        "ledger_last_hash": ledger_hash,
        "pairing_audit_path": str(output["pairing"]),
        "pairing_audit_file_sha256": file_hash(output["pairing"]),
        "run_count": len(SEEDS),
        "window_count": sum(item["windows"] for item in audits),
        "source_branch_audit": partition,
        "all_four_first_diverge_at_first_q8_lt32_branch": True,
        "all_four_new_branch_contracts_reject_one_heavy_player": True,
        "mechanism_gate_pass": mechanism_pass,
        "runtime_identity": {
            "runtime_binary_sha256": binary,
            "runtime_git_commit": git_commit,
            "runtime_python_executable_sha256": python,
            "runtime_cargo_lock_sha256": cargo,
        },
        "profile": PROFILE,
        "player_frontier": FRONTIER,
        "per_run_result_blind_audits": audits,
        "shared_records_snapshot": _records_snapshot(),
    }
    document["blind_audit_hash"] = object_hash(document)
    write_json_atomic(output["blind"], document)
    return document


def _compose_complete_profile(
    v179_rows: Sequence[Mapping[str, Any]],
    v168_rows: Sequence[Mapping[str, Any]],
    v181_complete_rows: Sequence[Mapping[str, Any]],
    v182_rows: Sequence[Mapping[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    sources = {
        "v179_behavior_equivalent": {row["seed"]: dict(row) for row in v179_rows},
        "v168_behavior_equivalent": {row["seed"]: dict(row) for row in v168_rows},
        "v177_behavior_equivalent": {
            row["seed"]: dict(row)
            for row in v181_complete_rows
            if row["seed"] in V177_EQUIVALENT
        },
        "new_v182_required": {row["seed"]: dict(row) for row in v182_rows},
    }
    partition = {
        "v179_behavior_equivalent": V179_EQUIVALENT,
        "v168_behavior_equivalent": V168_EQUIVALENT,
        "v177_behavior_equivalent": V177_EQUIVALENT,
        "new_v182_required": SEEDS,
    }
    rows = []
    lineage = []
    for seed in (f"E{i:02d}" for i in range(1, 21)):
        roles = [role for role, seeds in partition.items() if seed in seeds]
        if len(roles) != 1 or seed not in sources[roles[0]]:
            raise RuntimeError(f"V182 complete profile lineage changed: {seed}")
        role = roles[0]
        row = dict(sources[role][seed])
        rows.append(row)
        lineage.append({"seed": seed, "source_role": role, "run_id": row["run_id"]})
    return rows, lineage


def reveal_v182(root: Path = ROOT) -> dict[str, Any]:
    output = paths(root)
    if output["result"].exists():
        raise RuntimeError("V182 result already exists")
    blind = read_json(output["blind"])
    blind_hash = v181._assert_hashed(blind, "blind_audit_hash", "V182 blind audit")
    if not (
        blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("all_four_first_diverge_at_first_q8_lt32_branch") is True
        and blind.get("all_four_new_branch_contracts_reject_one_heavy_player") is True
        and blind.get("mechanism_gate_pass") is True
    ):
        raise RuntimeError("V182 blind audit did not authorize reveal")
    _reread_goal()
    manifest = load_and_validate_manifest(output["ready"])
    v182_rows = v181._load_rows(manifest, root, SEEDS)
    v179_manifest = load_and_validate_manifest(v179.paths()["ready"])
    v179_rows = v181._load_rows(v179_manifest, v179.ROOT, V179_EQUIVALENT)
    v168_manifest = load_and_validate_manifest(v168.paths()["ready"])
    v168_rows = v181._load_rows(v168_manifest, v168.ROOT, V168_EQUIVALENT)
    v181_failure = read_json(
        Path(
            "scripts/reviewer_experiments/protocol/"
            "nse_e1_homogeneous_v177_equivalence_complete_training_failure_v181.json"
        )
    )
    v181._assert_hashed(v181_failure, "receipt_hash", "V181 failure receipt")
    v181_result_seal = v181_failure["single_authorized_reveal"]
    if not (
        Path(v181_result_seal["path"]) == v181.paths()["result"]
        and file_hash(v181.paths()["result"]) == v181_result_seal["file_sha256"]
    ):
        raise RuntimeError("V181 sealed complete result file changed")
    v181_result = read_json(v181.paths()["result"])
    if (
        v181._assert_hashed(v181_result, "result_hash", "V181 complete result")
        != v181_result_seal["result_hash"]
    ):
        raise RuntimeError("V181 sealed complete result hash changed")
    v181_rows = v181_result["complete_profile_rows"]
    if [row["seed"] for row in v181_rows] != [f"E{i:02d}" for i in range(1, 21)]:
        raise RuntimeError("V181 complete result seed product changed")
    complete, lineage = _compose_complete_profile(
        v179_rows, v168_rows, v181_rows, v182_rows
    )
    evaluation = v181._evaluate_load("low", complete, v181._load_baselines())
    throughput = evaluation["gates"]["throughput"]
    qpr_finite = evaluation["gates"]["qpr_finite_only"]
    qpr_zero = evaluation["gates"]["qpr_zero_completed_as_zero"]
    if not (
        throughput["ceiling_algorithm"] == "Orion"
        and throughput["ceiling_mean"] == 1.4741
        and qpr_finite["ceiling_algorithm"] == "OCS"
        and qpr_finite["ceiling_mean"] == 0.055577160345697
        and qpr_zero["ceiling_algorithm"] == "OCS"
        and qpr_zero["ceiling_mean"] == 0.055577160345697
    ):
        raise RuntimeError("V182 frozen baseline ceilings changed")
    passed = bool(evaluation["all_three_metric_gates_pass"])
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_QUEUE8_LONE_HEAVY_EQUIVALENCE_COMPLETE_TRAINING_RESULT_V182_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(output["blind"]),
        "blind_audit_file_sha256": file_hash(output["blind"]),
        "blind_audit_hash": blind_hash,
        "new_online_run_count": len(SEEDS),
        "new_reference_build_count": len(SEEDS),
        "baseline_rerun_count": 0,
        "complete_profile_run_count": len(complete),
        "all_twenty_seeds_included": True,
        "profile": PROFILE,
        "complete_profile_lineage": lineage,
        "complete_profile_rows": complete,
        "hybrid_low_evaluation": evaluation,
        "joint_training_pass": passed,
        "homogeneous_low_training_closed": passed,
        "homogeneous_low_paper_claim_closed": False,
        "confirmation_inputs_generated": False,
        "disposition": (
            "freeze_complete_twenty_seed_V182_equivalent_training_result_and_require_a_separately_committed_fresh_seed_confirmation_plan"
            if passed
            else "retain_all_four_valid_V182_runs_and_retire_V182_without_subset_reporting"
        ),
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
        "middle_high_or_later_section_authorized": False,
        "shared_records_snapshot": _records_snapshot(),
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output["result"], document)
    return document


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "action",
        choices=("prepare", "build-references", "execute", "blind-audit", "reveal"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    action = build_parser().parse_args(argv).action
    if action == "prepare":
        document, key = prepare_v182(), "receipt_hash"
    elif action == "build-references":
        document, key = build_references_v182(), "receipt_hash"
    elif action == "execute":
        document, key = execute_v182(), "receipt_hash"
    elif action == "blind-audit":
        document, key = blind_audit_v182(), "blind_audit_hash"
    else:
        document, key = reveal_v182(), "result_hash"
    print(json.dumps({key: document[key], "runs": len(SEEDS)}))


if __name__ == "__main__":
    main()
