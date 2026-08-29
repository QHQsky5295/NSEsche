from __future__ import annotations

import copy
import json
from collections import Counter
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.protocol.matrix import _assign_run_identity
from scripts.reviewer_experiments.protocol.schema import validate_manifest
from scripts.reviewer_experiments.protocol.smoke_shard import (
    _matrix_summary,
    _reference_build_dependencies,
    derive_integration_smoke_shard,
)
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3_all_baseline_closure_diagnostic_20260830_v136")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3_all_baseline_closure_diagnostic_plan_v136.json"
)
PLAN_SHA256 = "251146f551243a62579c68a4da89375769aeab450a75cb51375077a589378981"

SOURCE = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/"
    "manifest.v135-training-source-full.unbound.json"
)
SOURCE_FILE_SHA256 = "50741b73a3b1810193e635ec0dde53f3462d0c17b56a7de6f9cc02286c665a8c"
SOURCE_MANIFEST_HASH = (
    "07e48f4fa509f75c112a247b4151f5036f65729e1770028b8db275ab558dc9d3"
)
TAPES = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/" "tapes.catalog.json"
)
TAPES_FILE_SHA256 = "4a934319cbb19ec7d20eb3fe524f1f01715c2f90f2c66a8ed715003759ae45b8"
SLA = Path(
    "C:/Users/99349/Desktop/serverless_sim_game/tmp/"
    "formal_e3_e4_reviewer_v3_20260817/frozen-sla.json"
)
SLA_SHA256 = "4a8392bb4f087106716e7d9a801a1dab4377804eef5c3e66df06a5403b100496"
MODEL = Path(
    "C:/Users/99349/Desktop/serverless_sim_game/tmp/"
    "formal_e1_atomic_hpa_reviewer_v3_20260813/faasrank.frozen.json"
)
MODEL_SHA256 = "7e9e1e63c88a83762fe10af66f6a0fcc6fb457c8087cda848a7c17ddf9f56463"
BINARY = Path("tmp/nse_v135_build_702e5a4/release/serverless_sim.exe")
BINARY_SHA256 = "8eceb2f8066b083739740e6cf3b9c66ba88bb8fcff7d1f3bf8684a5793da35e8"

V135_RESULT = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/"
    "training-result-v135.json"
)
V135_RESULT_FILE_SHA256 = (
    "739115d659e95d2bbd9ec8d60c7c94c50b69198f2d17b519e8748c0f6dd4d104"
)
V135_BLIND_AUDIT = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/"
    "joint-blind-audit-v135-training.json"
)
V135_BLIND_AUDIT_FILE_SHA256 = (
    "219cf94f70a9bbfc38f6d5dbc64f6356020b0a59a7b657814c8c354161975230"
)
V135_ANCHOR_MANIFEST = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/"
    "manifest.v135-e3-anchor.ready.json"
)
V135_ANCHOR_MANIFEST_FILE_SHA256 = (
    "f5d035b410767b633d2a2bb91943f5b69e2a04a721dee653df56fa4cdc843bcc"
)
V135_ANCHOR_WORKSPACE = Path(
    "tmp/nse_e3_readiness_stratified_work_training_20260830_v135/" "runs/v135-e3-anchor"
)

SEED_LIST = ["E1448", "E1449", "E1450"]
SEEDS = set(SEED_LIST)
SCENARIOS = ["spike5x50ms", "sustained3x200ms", "pulse4x4x50ms"]
BASELINE_METHODS = [
    "greedy",
    "random",
    "hash",
    "load_least",
    "sche_FaaSRank",
    "sche_OCS",
    "sche_Hiku",
    "sche_jiagu",
    "sche_orion",
]
BASELINE_METHOD_SET = set(BASELINE_METHODS)
PORT = "3167"


def paths(root: Path = ROOT) -> dict[str, Path]:
    return {
        "unbound": root / "manifest.v136-baselines.unbound.json",
        "tapes": root / "manifest.v136-baselines.tapes.json",
        "sla": root / "manifest.v136-baselines.sla.json",
        "ready": root / "manifest.v136-baselines.ready.json",
        "prepared": root / "prepared-v136.json",
        "workspace": root / "runs/v136-baselines",
        "pairing": root / "pairing-audit-v136-baselines.json",
        "blind": root / "joint-blind-audit-v136.json",
        "result": root / "all-baseline-closure-result-v136.json",
    }


def scenario_id(run: dict[str, Any]) -> str:
    burst = run["workload"]["burst"]
    kind = burst["kind"]
    if kind == "spike":
        return "spike5x50ms"
    if kind == "sustained":
        return "sustained3x200ms"
    if kind == "pulse":
        return "pulse4x4x50ms"
    raise RuntimeError(f"unexpected E3 burst kind: {kind}")


def _assert_hashed_object(path: Path, field: str, expected: str) -> None:
    document = json.loads(path.read_text(encoding="utf-8"))
    payload = dict(document)
    claimed = payload.pop(field, None)
    if claimed != expected or object_hash(payload) != claimed:
        raise RuntimeError(f"frozen hashed object changed: {path}")


def _assert_frozen_inputs() -> dict[str, Any]:
    frozen = (
        (PLAN, PLAN_SHA256),
        (SOURCE, SOURCE_FILE_SHA256),
        (TAPES, TAPES_FILE_SHA256),
        (SLA, SLA_SHA256),
        (MODEL, MODEL_SHA256),
        (BINARY, BINARY_SHA256),
        (V135_RESULT, V135_RESULT_FILE_SHA256),
        (V135_BLIND_AUDIT, V135_BLIND_AUDIT_FILE_SHA256),
        (V135_ANCHOR_MANIFEST, V135_ANCHOR_MANIFEST_FILE_SHA256),
    )
    for path, expected in frozen:
        if not path.is_file() or file_hash(path) != expected:
            raise RuntimeError(f"frozen V136 input is missing or changed: {path}")
    _assert_hashed_object(
        V135_RESULT,
        "result_hash",
        "2103661167d58477fb9a6063618b8426c39a0afd71a0b51a177ed06583ac5f93",
    )
    _assert_hashed_object(
        V135_BLIND_AUDIT,
        "audit_hash",
        "f89d8936e293631310d553dd817ce145eb1387bae10357a8ac58fb0dadd333d0",
    )
    source = json.loads(SOURCE.read_text(encoding="utf-8"))
    if source.get("manifest_hash") != SOURCE_MANIFEST_HASH:
        raise RuntimeError("V136 source manifest hash changed")
    validate_manifest(source)
    return source


def _is_selected(run: dict[str, Any]) -> bool:
    return (
        run["experiment_id"] == "E3"
        and run["seed"] in SEEDS
        and run["method"] in BASELINE_METHOD_SET
        and run["workload"]["request_freq"] == "middle"
        and run["workload"]["topology"] == "heterogeneous"
        and run["workload"]["qos_profile"] == "balanced"
        and run["cluster"] == {"node_count": 20, "topology": "heterogeneous"}
        and scenario_id(run) in SCENARIOS
    )


def _validate_product(runs: list[dict[str, Any]]) -> None:
    expected = {
        (method, scenario, seed)
        for method in BASELINE_METHODS
        for scenario in SCENARIOS
        for seed in SEED_LIST
    }
    actual = {(run["method"], scenario_id(run), run["seed"]) for run in runs}
    if len(runs) != 81 or actual != expected:
        raise RuntimeError(
            "V136 baseline product changed: "
            f"count={len(runs)}, missing={sorted(expected-actual)}, "
            f"extra={sorted(actual-expected)}"
        )
    if any(run.get("reference_dependency") is not None for run in runs):
        raise RuntimeError(
            "V136 baseline product unexpectedly requires Nash references"
        )


def _rewrite(shard: dict[str, Any]) -> dict[str, Any]:
    rewritten = copy.deepcopy(shard)
    rewritten["created_at"] = utc_now()
    rewritten["formal_results_eligible"] = False
    source_lineage = {
        item["source_run_id"]: item
        for item in rewritten["integration_smoke_shard"]["selected_source_runs"]
    }
    run_lineage = []
    for run in rewritten["runs"]:
        source_run_id = run["run_id"]
        source_run_spec_hash = run["run_spec_hash"]
        run["variant"] = "v136-all-baseline-closure-diagnostic"
        run["environment"]["SERVERLESS_SIM_PORT"] = PORT
        run.setdefault("metadata", {}).update(
            {
                "v136_plan_sha256": PLAN_SHA256,
                "v136_diagnostic_only": True,
                "v136_role": "paper_baseline",
                "v136_complete_method_seed_scenario_product": True,
                "v136_baseline_performance_consulted_before_execution": False,
                "v136_NSESche_reused_not_rerun": True,
                "v136_confirmation_inputs_opened": False,
                "v136_seed_or_scenario_label_used_by_policy": False,
                "v136_outcome_fields_used_by_policy": False,
                "v136_source_run_id": source_run_id,
                "v136_source_run_spec_hash": source_run_spec_hash,
            }
        )
        _assign_run_identity(run)
        lineage = source_lineage[source_run_id]
        run_lineage.append(
            {
                **lineage,
                "v136_run_id": run["run_id"],
                "v136_run_spec_hash": run["run_spec_hash"],
                "scenario": scenario_id(run),
            }
        )
    _validate_product(rewritten["runs"])
    rewritten["reference_build_dependencies"] = _reference_build_dependencies(
        rewritten["runs"]
    )
    rewritten["matrix_summary"] = _matrix_summary(
        rewritten["runs"], rewritten["reuse_analyses"]
    )
    marker = rewritten["integration_smoke_shard"]
    marker.update(
        {
            "purpose": "V136 all-paper-baseline closure diagnostic on the frozen V135 E1448-E1450 tapes",
            "v136_plan_sha256": PLAN_SHA256,
            "v136_diagnostic_only": True,
            "operational_group_closure_eligible": False,
            "performance_results_consulted": False,
            "selected_seeds": SEED_LIST,
            "selected_scenarios": SCENARIOS,
            "selected_baseline_methods": BASELINE_METHODS,
            "new_baseline_run_count": 81,
            "reused_NSESche_run_count": 9,
            "NSESche_rerun_count": 0,
            "new_reference_build_count": 0,
            "confirmation_inputs_generated": False,
            "v136_run_lineage": run_lineage,
            "selected_run_count": 81,
            "selected_reference_build_count": 0,
        }
    )
    rewritten.pop("manifest_hash", None)
    rewritten["manifest_hash"] = object_hash(rewritten)
    validate_manifest(rewritten)
    return rewritten


def prepare_v136(root: Path = ROOT) -> dict[str, Any]:
    source = _assert_frozen_inputs()
    if root.exists():
        raise RuntimeError(f"refusing to overwrite V136 diagnostic root: {root}")
    selected_ids = [run["run_id"] for run in source["runs"] if _is_selected(run)]
    if len(selected_ids) != 81:
        raise RuntimeError(
            f"V136 sealed source selected {len(selected_ids)} runs, not 81"
        )
    shard = derive_integration_smoke_shard(
        SOURCE,
        selected_ids,
        purpose=f"V136 all-baseline closure diagnostic {PLAN_SHA256}",
    )
    manifest = _rewrite(shard)
    root.mkdir(parents=True)
    output_paths = paths(root)
    write_json_atomic(output_paths["unbound"], manifest)
    counts = Counter(run["method"] for run in manifest["runs"])
    receipt = {
        "schema_version": "NSE_E3_ALL_BASELINE_CLOSURE_PREPARED_V136_V1",
        "created_at": utc_now(),
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_results_consulted": False,
        "baseline_performance_summaries_parsed": 0,
        "plan_path": str(PLAN),
        "plan_sha256": PLAN_SHA256,
        "source_manifest_path": str(SOURCE),
        "source_manifest_file_sha256": SOURCE_FILE_SHA256,
        "source_manifest_hash": SOURCE_MANIFEST_HASH,
        "source_run_count": len(source["runs"]),
        "tape_catalog_path": str(TAPES),
        "tape_catalog_file_sha256": TAPES_FILE_SHA256,
        "sla_artifact_path": str(SLA),
        "sla_artifact_sha256": SLA_SHA256,
        "faasrank_model_path": str(MODEL),
        "faasrank_model_sha256": MODEL_SHA256,
        "binary_path": str(BINARY),
        "binary_sha256": BINARY_SHA256,
        "v135_anchor_manifest_path": str(V135_ANCHOR_MANIFEST),
        "v135_anchor_manifest_file_sha256": V135_ANCHOR_MANIFEST_FILE_SHA256,
        "v135_anchor_workspace": str(V135_ANCHOR_WORKSPACE),
        "seeds": SEED_LIST,
        "scenarios": SCENARIOS,
        "baseline_methods": BASELINE_METHODS,
        "baseline_runs_by_method": dict(sorted(counts.items())),
        "new_baseline_run_count": 81,
        "reused_NSESche_run_count": 9,
        "combined_run_count": 90,
        "new_reference_build_count": 0,
        "NSESche_rerun_count": 0,
        "confirmation_inputs_generated": False,
        "manifest": {
            "path": str(output_paths["unbound"]),
            "file_sha256": file_hash(output_paths["unbound"]),
            "manifest_hash": manifest["manifest_hash"],
            "run_count": len(manifest["runs"]),
            "reference_build_count": len(manifest["reference_build_dependencies"]),
        },
    }
    receipt["receipt_hash"] = object_hash(receipt)
    write_json_atomic(output_paths["prepared"], receipt)
    return receipt


def main() -> None:
    prepare_v136()


if __name__ == "__main__":
    main()
