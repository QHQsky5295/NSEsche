from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from scripts.reviewer_experiments.analysis.protocol_results import _nse_summary_metrics
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_causal_native_expert_closure_training_reveal_v149 import (
    _evaluate_load,
    _load_baselines,
    _metrics,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_cross_scenario_anchor_training_blind_audit_v151 import (
    OUTPUT_NAME as BLIND_AUDIT_NAME,
)
from scripts.reviewer_experiments.protocol.nse_e1_homogeneous_cross_scenario_anchor_training_prepare_v151 import (
    LOADS,
    PLAN_SHA256,
    PROFILES,
    ROOT,
    SEEDS,
    paths,
)
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


OUTPUT_NAME = "training-result-v151.json"


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
        summary = read_json(summary_path)
        values = _nse_summary_metrics(summary)
        load = run["workload"]["request_freq"]
        rows.append(
            {
                "load": load,
                "seed": run["seed"],
                "run_id": run["run_id"],
                "profile": PROFILES[load],
                **_metrics(
                    values.get("throughput"),
                    values.get("latency_mean_ms"),
                    values.get("cost"),
                    values.get("completed"),
                ),
            }
        )
    expected = {(load, seed) for load in LOADS for seed in SEEDS}
    if len(rows) != 60 or {(row["load"], row["seed"]) for row in rows} != expected:
        raise RuntimeError("V151 candidate result product changed")
    return rows


def execute_reveal(root: Path = ROOT) -> dict[str, Any]:
    output = root / OUTPUT_NAME
    if output.exists():
        raise RuntimeError(f"V151 training result already exists: {output}")
    blind_path = root / BLIND_AUDIT_NAME
    blind = read_json(blind_path)
    payload = dict(blind)
    blind_hash = payload.pop("blind_audit_hash", None)
    if not (
        isinstance(blind_hash, str)
        and object_hash(payload) == blind_hash
        and blind.get("status") == "pass"
        and blind.get("performance_reveal_authorized") is True
        and blind.get("throughput_completion_latency_cost_qpr_fields_parsed") == 0
        and blind.get("profile_map") == PROFILES
    ):
        raise RuntimeError(
            "V151 blind audit is absent, changed, or did not authorize reveal"
        )
    manifest = load_and_validate_manifest(paths(root)["ready"])
    candidate = _load_candidate(manifest, root)
    baselines = _load_baselines()
    loads = []
    for load in LOADS:
        result = _evaluate_load(load, candidate, baselines)
        result["profile"] = PROFILES[load]
        result["training_configuration_frozen_for_future_confirmation"] = result[
            "all_three_metric_gates_pass"
        ]
        loads.append(result)
    passed = all(item["all_three_metric_gates_pass"] for item in loads)
    document = {
        "schema_version": "NSE_E1_HOMOGENEOUS_CROSS_SCENARIO_ANCHOR_TRAINING_RESULT_V151_V1",
        "created_at": utc_now(),
        "training_only": True,
        "formal_results_eligible": False,
        "paper_superiority_claim_authorized": False,
        "performance_results_consulted_for_design": True,
        "plan_sha256": PLAN_SHA256,
        "blind_audit_path": str(blind_path),
        "blind_audit_file_sha256": file_hash(blind_path),
        "blind_audit_hash": blind_hash,
        "candidate_run_count": len(candidate),
        "reused_frozen_baseline_run_count": len(baselines),
        "baseline_rerun_count": 0,
        "profile_map": PROFILES,
        "loads": loads,
        "all_nine_training_gates_pass": passed,
        "disposition": (
            "training_pass_requires_separate_confirmation_plan_and_unopened_inputs"
            if passed
            else "retain_all_v151_runs_and_retire_failed_load_profiles_without_confirmation_inputs"
        ),
        "confirmation_inputs_generated": False,
        "valid_seed_deletion_replacement_relabeling_or_selective_rerun": False,
    }
    document["result_hash"] = object_hash(document)
    write_json_atomic(output, document)
    return document


def main() -> None:
    document = execute_reveal()
    print(
        json.dumps(
            {
                "result_hash": document["result_hash"],
                "all_nine_training_gates_pass": document[
                    "all_nine_training_gates_pass"
                ],
            }
        )
    )


if __name__ == "__main__":
    main()
