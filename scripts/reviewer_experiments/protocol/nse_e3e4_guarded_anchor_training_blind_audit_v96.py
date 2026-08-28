from __future__ import annotations

import json
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from scripts.reviewer_experiments.analysis.formal_inputs import validate_canonical_run
from scripts.reviewer_experiments.protocol.ledger import verify_ledger
from scripts.reviewer_experiments.protocol.reference import inspect_reference_table
from scripts.reviewer_experiments.protocol.schema import load_and_validate_manifest
from scripts.reviewer_experiments.protocol.tape import inspect_tape
from scripts.reviewer_experiments.protocol.util import (
    file_hash,
    object_hash,
    read_json,
    utc_now,
    write_json_atomic,
)


ROOT = Path("tmp/nse_e3e4_guarded_anchor_training_20260828_v96")
PLAN = Path(
    "scripts/reviewer_experiments/protocol/"
    "nse_e3e4_guarded_anchor_training_plan_v96.json"
)
PLAN_FILE_SHA256 = "5fc758ad2ce1a90aa26884d94d5338d4739277c9d75f12c0f37eaf07788747ab"
PREPARED = ROOT / "prepared-manifests-v96.json"
PREPARED_FILE_SHA256 = (
    "aa8d5ac27a281f2a9d6e9f1c43d7340211485200662be588e125548fff212765"
)
PREPARED_RECEIPT_HASH = (
    "ab157e6148595b49bf084f63865b442d14711ffb31d571008317ec476637a7d0"
)
TAPES = ROOT / "tapes.catalog.json"
TAPES_FILE_SHA256 = "7b552b71c6d76d4157d99c85a5036af0c83d6878bcef4b4dd122cfcef656464a"
TAPES_CATALOG_HASH = "361d986632fc1e8ea79dc67ecb1dfe80ee9badcf75c517f71bcfe10c673be371"
E4_TAPES = ROOT / "tapes.e4.catalog.json"
E4_TAPES_FILE_SHA256 = (
    "ba4142ed27ca53c96251b818af17effad56fe6768037fe0169e77e11a1d1461a"
)
E4_TAPES_CATALOG_HASH = (
    "750c34ed9f8e245f8eae2660f455bb1d3ef874e9335c64687285184a5d901d8e"
)
RENAME_RECEIPT = (
    ROOT / "stages/references/v96-e3-idle-warm-srpt/reference_builds/"
    "canonical_rename_receipt_v96.json"
)
RENAME_RECEIPT_FILE_SHA256 = (
    "786c7ba7dfb7a1daee975aa1bdf55609508a6bc726ef3351573ac89c2d747934"
)
RENAME_RECEIPT_HASH = "018d9b98a262718a4abae796f65a4391b4334c7c2e88b76282e13ce172ece4ae"
OUTPUT = ROOT / "joint-blind-audit-v96-training.json"
TRAINING_SEEDS = {"E746", "E747", "E748"}
CONFIRMATION_SEEDS = {f"E{index}" for index in range(766, 786)}
EXPECTED_RUNTIME = {
    "binary_sha256": (
        "9b97746f2785daccd086780c1203d0d3f823cb155350e4befa99b278201edf77"
    ),
    "git_commit": "018cb5d59e38822ba62a3a86f740fb96ffdc72b8",
    "python_executable_sha256": (
        "a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384"
    ),
    "cargo_lock_sha256": (
        "9f4a20c44510f7b4bc69629674d4b4a7425a4433701b3f03c63d24214ab23ccb"
    ),
}
EXPECTED_COMMON_HPA_SHA256 = (
    "c4c689eec0dd7814584f31d073cd9f1fb42ba1f1bcf5ed30fd42cc0ce04d6c9d"
)
ARMS = {
    "v96-e3-anchor": {
        "experiment_id": "E3",
        "role": "anchor",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "run_count": 9,
        "ready_file_sha256": (
            "583833d44ed19f471620fea3d7e09f61cfef40198b9195b861a303195bd1672a"
        ),
        "ready_manifest_hash": (
            "8b4a92f3cbc6d6acfc22ee43abe0dab204ecdbf981dbae7224958b35e19e5505"
        ),
        "reference_file_sha256": (
            "222ca7d9e1816e2de4657eb01c174269955e5bc0b88ba05345b9dad35eae6c45"
        ),
        "reference_catalog_hash": (
            "6e613414ee8e3bd4f3e8e377a99406ae569a7de7f4be418893a813a03b8d0442"
        ),
        "pairing_file_sha256": (
            "84e1afa21920a8d2b37e8fafe3e7e2e1a8f3d1f4cec710092c6b52f02884f80a"
        ),
    },
    "v96-e3-idle-warm-srpt": {
        "experiment_id": "E3",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "run_count": 9,
        "ready_file_sha256": (
            "5df97f92a1e90f3b1bb8885b438071065613cfdde62e0b06b1ab61d6b191965a"
        ),
        "ready_manifest_hash": (
            "515ac6007f58f2f6c4dbb4c3c4e4db275d683c0014d4d79a971d454dc40c9a36"
        ),
        "reference_file_sha256": (
            "1cae358aa4f7cb4e2220b5e8d5e80a31a21d89d0fcebc9a8b1467191da14ee7c"
        ),
        "reference_catalog_hash": (
            "b073c5e52618917da2cb8dd751b64dc08f478182055ac59280a98ffa80b72bc8"
        ),
        "pairing_file_sha256": (
            "0b30f0d96cf946ea866ddbab87065743eadff329ccb4b08748c6a4d0cf173076"
        ),
    },
    "v96-e3-idle-warm-no-srpt": {
        "experiment_id": "E3",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "dual_window_safe_pareto"
        ),
        "run_count": 9,
        "ready_file_sha256": (
            "237bc1d5d7fcddcf723fecb1b17da88029a2b4e2178fb96a4df5af3404f9a2fc"
        ),
        "ready_manifest_hash": (
            "94f89dd36125898debd8a430eccb938cb05a100b9ca05cd7db257a413959dc41"
        ),
        "reference_file_sha256": (
            "305b387810664a2e3cc6797ffa04d1a7082f5a482555e695684141eecaddfdf0"
        ),
        "reference_catalog_hash": (
            "7c6f88d355e80d52c566b16e58b9427d25ea23f277619780476e5876bfbfd030"
        ),
        "pairing_file_sha256": (
            "9db49740698182f44c973d1a154b6cb61c3bec9cc2357351dc9318e1dbcdee7a"
        ),
    },
    "v96-e4-anchor": {
        "experiment_id": "E4",
        "role": "anchor",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "srpt_ready_dual_window_safe_pareto"
        ),
        "run_count": 3,
        "ready_file_sha256": (
            "8d434beea2c1c1d89d1c3ee6eb81c18b7a41e9a1109d7daac6ec17f6764903d8"
        ),
        "ready_manifest_hash": (
            "bed0eba71dc04206cdf402fa41d7fb4a9fd3288b6009a41bf486d9a0f2ba15a4"
        ),
        "reference_file_sha256": (
            "c29a28e18641f2cc3a977a221b3b90c385ed257e16503f5b72dea9b217abd0a8"
        ),
        "reference_catalog_hash": (
            "2b4a831cc7d12ff2a8155077430f8357fb72b017a16dff2935a66b710224eaa9"
        ),
        "pairing_file_sha256": (
            "047f9fb38163de6e933f57eaeb638155ef3e1c35583507781c3dfff18cd09c83"
        ),
    },
    "v96-e4-idle-warm-no-srpt": {
        "experiment_id": "E4",
        "role": "candidate",
        "profile": (
            "faasrank_native_faithful_terminal_ocs_idle_warm_dominance_"
            "dual_window_safe_pareto"
        ),
        "run_count": 3,
        "ready_file_sha256": (
            "61e715ac95b007e8c4923c02d7ab89564b396cdb67c1fc1bb2728f301f9a8e4b"
        ),
        "ready_manifest_hash": (
            "66a050f9bc21b06626aef07858ca6c1e40236892afe6151d96f446eba108a88e"
        ),
        "reference_file_sha256": (
            "bc2da7e1e2232d4b560493b2a44e7b01bd71db5a23fe71fc9190073009c5b400"
        ),
        "reference_catalog_hash": (
            "0d40b43a5c11b8759824f17d2baffcb82affc0f9dc94300409aea169bfaacce9"
        ),
        "pairing_file_sha256": (
            "8c3577ba02fbea66efd03de13e4bbac769f18fb95137a2b8430e02011d99c886"
        ),
    },
}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise RuntimeError(message)


def _assert_file(path: Path, expected_sha256: str) -> None:
    _require(path.is_file(), f"missing frozen input: {path}")
    _require(file_hash(path) == expected_sha256, f"frozen input changed: {path}")


def _assert_hashed_object(
    value: dict[str, Any], hash_field: str, expected_hash: str, label: str
) -> None:
    claimed = value.get(hash_field)
    unhashed = dict(value)
    unhashed.pop(hash_field, None)
    _require(claimed == expected_hash, f"{label} claimed hash changed")
    _require(object_hash(unhashed) == expected_hash, f"{label} self-hash mismatch")


def _read_ledger(path: Path) -> tuple[list[dict[str, Any]], str]:
    count, last_hash = verify_ledger(path)
    rows = [
        json.loads(line)
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]
    _require(len(rows) == count, f"ledger line count changed: {path}")
    _require(
        rows and rows[-1].get("event_hash") == last_hash,
        f"ledger tail hash changed: {path}",
    )
    return rows, last_hash


def _assert_ledger_contract(
    rows: list[dict[str, Any]], expected_types: Counter[str], label: str
) -> None:
    observed = Counter(str(row.get("event_type")) for row in rows)
    _require(observed == expected_types, f"{label} event contract changed: {observed}")


def _arm_paths(arm_id: str) -> dict[str, Path]:
    return {
        "ready": ROOT / f"manifest.{arm_id}.ready.json",
        "references": ROOT / f"references.{arm_id}.catalog.json",
        "pairing": ROOT / f"pairing-audit.{arm_id}.json",
        "workspace": ROOT / "runs" / arm_id,
        "reference_workspace": ROOT / "stages" / "references" / arm_id,
    }


def _scenario(run: dict[str, Any]) -> str:
    if run["experiment_id"] == "E4":
        return "E4.steady"
    return f"E3.{run['workload']['burst_name']}"


def _verify_tape_catalog() -> list[dict[str, Any]]:
    _assert_file(TAPES, TAPES_FILE_SHA256)
    catalog = read_json(TAPES)
    _assert_hashed_object(catalog, "catalog_hash", TAPES_CATALOG_HASH, "V96 tapes")
    entries = catalog.get("entries")
    _require(isinstance(entries, dict) and len(entries) == 12, "V96 tape count changed")
    evidence = []
    for key, entry in sorted(entries.items()):
        info = inspect_tape(Path(entry["path"]))
        _require(info.sha256 == entry["sha256"], f"tape hash changed: {key}")
        _require(info.workload_seed in TRAINING_SEEDS, f"unexpected tape seed: {key}")
        evidence.append(
            {
                "key": key,
                "sha256": info.sha256,
                "event_count": info.event_count,
                "dag_order_sha256": info.dag_order_sha256,
                "kind": entry["kind"],
            }
        )
    _require(
        Counter(item["kind"] for item in evidence)
        == Counter({"base_steady": 3, "derived_burst": 9}),
        "V96 tape kind boundary changed",
    )

    _assert_file(E4_TAPES, E4_TAPES_FILE_SHA256)
    projection = read_json(E4_TAPES)
    _assert_hashed_object(
        projection, "catalog_hash", E4_TAPES_CATALOG_HASH, "V96 E4 tape projection"
    )
    projected = projection.get("entries")
    _require(
        isinstance(projected, dict) and len(projected) == 3, "E4 tape count changed"
    )
    for key, entry in projected.items():
        _require(key in entries and entry == entries[key], "E4 tape projection changed")
        _require(entry.get("kind") == "base_steady", "E4 projection contains burst")

    capture_ledger = ROOT / "stages/tape_capture/capture_base_tapes/ledger.jsonl"
    rows, _ = _read_ledger(capture_ledger)
    _assert_ledger_contract(
        rows, Counter({"capture_canonicalized": 3}), "V96 tape capture"
    )
    _require(
        not list(
            (ROOT / "stages/tape_capture/capture_base_tapes/quarantine").glob(
                "**/attempt-*"
            )
        ),
        "V96 tape capture has quarantined attempts",
    )
    return evidence


def _verify_rename_receipt() -> dict[str, Any]:
    _assert_file(RENAME_RECEIPT, RENAME_RECEIPT_FILE_SHA256)
    receipt = read_json(RENAME_RECEIPT)
    _assert_hashed_object(
        receipt, "receipt_hash", RENAME_RECEIPT_HASH, "V96 reference rename receipt"
    )
    _require(
        receipt.get("performance_metrics_consulted") is False
        and receipt.get("operation") == "same_parent_os_replace_directory_only",
        "V96 reference rename boundary changed",
    )
    canonical = RENAME_RECEIPT.parent / "canonical"
    target = canonical / receipt["target_name"]
    source = canonical / receipt["source_name"]
    _require(
        target.is_dir() and not source.exists(), "V96 reference rename not applied"
    )
    files = [
        {
            "path": path.relative_to(target).as_posix(),
            "bytes": path.stat().st_size,
            "sha256": file_hash(path),
        }
        for path in sorted(item for item in target.rglob("*") if item.is_file())
    ]
    _require(files == receipt["files"], "V96 renamed reference tree changed")
    return receipt


def run_blind_audit(output: Path = OUTPUT) -> dict[str, Any]:
    _require(not output.exists(), f"V96 blind audit already exists: {output}")
    _require(
        not (ROOT / "training-result-v96.json").exists(),
        "V96 reveal exists before blind audit",
    )
    _assert_file(PLAN, PLAN_FILE_SHA256)
    plan = read_json(PLAN)
    _require(
        plan.get("formal_results_eligible") is False, "V96 plan eligibility changed"
    )
    _assert_file(PREPARED, PREPARED_FILE_SHA256)
    prepared = read_json(PREPARED)
    _assert_hashed_object(
        prepared, "receipt_hash", PREPARED_RECEIPT_HASH, "V96 prepared receipt"
    )
    _require(
        prepared.get("performance_results_consulted") is False
        and prepared.get("confirmation_inputs_generated") is False
        and set(prepared.get("training_seeds", [])) == TRAINING_SEEDS
        and set(prepared.get("untouched_confirmation_seeds", [])) == CONFIRMATION_SEEDS,
        "V96 prepared scientific boundary changed",
    )
    tape_evidence = _verify_tape_catalog()
    rename_receipt = _verify_rename_receipt()

    run_evidence: list[dict[str, Any]] = []
    reference_evidence: list[dict[str, Any]] = []
    pairing_evidence: list[dict[str, Any]] = []
    runtime_values: dict[str, set[str]] = defaultdict(set)
    paired_inputs: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)

    for arm_id, expected in ARMS.items():
        paths = _arm_paths(arm_id)
        _assert_file(paths["ready"], expected["ready_file_sha256"])
        manifest = load_and_validate_manifest(paths["ready"])
        _require(
            manifest["manifest_hash"] == expected["ready_manifest_hash"],
            f"V96 ready hash changed: {arm_id}",
        )
        _require(
            len(manifest["runs"]) == expected["run_count"],
            f"V96 run count changed: {arm_id}",
        )
        _require(
            manifest.get("all_tapes_bound") is True
            and manifest.get("all_sla_targets_bound") is True
            and manifest.get("all_references_bound") is True,
            f"V96 ready flags changed: {arm_id}",
        )

        _assert_file(paths["references"], expected["reference_file_sha256"])
        references = read_json(paths["references"])
        _assert_hashed_object(
            references,
            "catalog_hash",
            expected["reference_catalog_hash"],
            f"V96 references {arm_id}",
        )
        entries = references.get("entries")
        declared_keys = {
            item["key"] for item in manifest["reference_build_dependencies"]
        }
        _require(
            isinstance(entries, dict)
            and set(entries) == declared_keys
            and len(entries) == expected["run_count"],
            f"V96 reference key set changed: {arm_id}",
        )
        for key, entry in sorted(entries.items()):
            info = inspect_reference_table(Path(entry["path"]))
            for field in (
                "sha256",
                "bytes",
                "line_count",
                "state_pair_sequence_sha256",
            ):
                _require(
                    getattr(info, field) == entry[field],
                    f"V96 reference {field} changed: {key}",
                )
            _require(
                file_hash(Path(entry["receipt_path"])) == entry["receipt_sha256"],
                f"V96 reference receipt changed: {key}",
            )
            _require(
                file_hash(Path(entry["build_process_observation_path"]))
                == entry["build_process_observation_sha256"],
                f"V96 reference process changed: {key}",
            )
            reference_evidence.append(
                {
                    "arm_id": arm_id,
                    "key": key,
                    "sha256": entry["sha256"],
                    "receipt_sha256": entry["receipt_sha256"],
                    "build_spec_hash": entry["build_spec_hash"],
                    "workload_tape_sha256": entry["workload_tape_sha256"],
                }
            )
        reference_ledger = (
            paths["reference_workspace"] / "reference_builds/ledger.jsonl"
        )
        reference_rows, reference_last_hash = _read_ledger(reference_ledger)
        _assert_ledger_contract(
            reference_rows,
            Counter({"reference_build_canonicalized": expected["run_count"]}),
            f"V96 reference {arm_id}",
        )
        _require(
            not list(
                (paths["reference_workspace"] / "reference_builds/quarantine").glob(
                    "**/attempt-*"
                )
            ),
            f"V96 reference quarantine is nonempty: {arm_id}",
        )

        _assert_file(paths["pairing"], expected["pairing_file_sha256"])
        pairing = read_json(paths["pairing"])
        _require(
            pairing.get("passed") is True
            and pairing.get("failed_group_count") == 0
            and pairing.get("run_count") == expected["run_count"]
            and pairing.get("group_count") == expected["run_count"],
            f"V96 pairing changed: {arm_id}",
        )
        pairing_evidence.append(
            {
                "arm_id": arm_id,
                "file_sha256": expected["pairing_file_sha256"],
                "run_count": pairing["run_count"],
                "group_count": pairing["group_count"],
                "passed": True,
            }
        )

        workspace = paths["workspace"]
        expected_ids = {run["run_id"] for run in manifest["runs"]}
        actual_ids = {
            path.name for path in (workspace / "canonical").iterdir() if path.is_dir()
        }
        _require(actual_ids == expected_ids, f"V96 canonical set changed: {arm_id}")
        _require(
            not list((workspace / "quarantine").glob("**/attempt-*")),
            f"V96 online quarantine is nonempty: {arm_id}",
        )
        ledger_rows, ledger_last_hash = _read_ledger(workspace / "ledger.jsonl")
        _assert_ledger_contract(
            ledger_rows,
            Counter(
                {
                    "batch_started": 1,
                    "attempt_started": expected["run_count"],
                    "attempt_canonicalized": expected["run_count"],
                    "batch_finished": 1,
                }
            ),
            f"V96 online {arm_id}",
        )

        for run in manifest["runs"]:
            _require(
                run["experiment_id"] == expected["experiment_id"]
                and run["seed"] in TRAINING_SEEDS
                and run["metadata"].get("v96_arm_id") == arm_id
                and run["metadata"].get("v96_arm_role") == expected["role"]
                and run["metadata"].get("v96_candidate_profile") == expected["profile"]
                and run["metadata"].get("v96_training_seed_metrics_previously_revealed")
                is False
                and run["metadata"].get("v96_confirmation_seeds_opened") is False,
                f"V96 run boundary changed: {run['run_id']}",
            )
            canonical = workspace / "canonical" / run["run_id"]
            validate_canonical_run(
                run,
                canonical,
                expected_manifest_hash=manifest["manifest_hash"],
                result_relative_path="reviewer_records/{run_id}/summary.json",
            )
            attempt = read_json(canonical / "attempt.json")
            qc = read_json(canonical / "qc_report.json")
            audit_manifest = read_json(canonical / "manifest.json")
            _require(
                attempt.get("attempt") == 1
                and attempt.get("status") == "qc_pass"
                and attempt.get("classification") == "qc_pass"
                and attempt.get("timed_out") is False
                and attempt.get("exit_code") == 0
                and qc.get("passed") is True
                and qc.get("classification") == "qc_pass",
                f"V96 canonical status changed: {run['run_id']}",
            )
            runtime = {
                "binary_sha256": audit_manifest["adapter_binary"]["verified_sha256"],
                "git_commit": audit_manifest["software_environment"]["git"]["commit"],
                "python_executable_sha256": audit_manifest["software_environment"][
                    "python"
                ]["executable_sha256"],
                "cargo_lock_sha256": audit_manifest["software_environment"][
                    "cargo_lock"
                ]["sha256"],
            }
            for field in EXPECTED_RUNTIME:
                runtime_values[field].add(str(runtime[field]))
            scenario = _scenario(run)
            paired_inputs[(run["experiment_id"], scenario, run["seed"])].append(
                {
                    "arm_id": arm_id,
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "workload_tape_key": run["workload_tape"]["key"],
                    "workload_spec_hash": run["workload_spec_hash"],
                    "capture_environment_sha256": run["workload_tape"][
                        "capture_environment"
                    ]["capture_environment_sha256"],
                    "common_hpa_hash": run["common_hpa_hash"],
                    "sla_artifact_sha256": run["sla_targets"]["artifact_sha256"],
                    "simulation": run["simulation"],
                }
            )
            run_evidence.append(
                {
                    "arm_id": arm_id,
                    "run_id": run["run_id"],
                    "experiment_id": run["experiment_id"],
                    "scenario": scenario,
                    "seed": run["seed"],
                    "run_spec_hash": run["run_spec_hash"],
                    "workload_tape_sha256": run["workload_tape"]["sha256"],
                    "reference_key": run["reference_dependency"]["key"],
                    "result_sha256": attempt["result_sha256"],
                    "audit_manifest_sha256": file_hash(canonical / "manifest.json"),
                    "qc_report_sha256": file_hash(canonical / "qc_report.json"),
                    "attempt": 1,
                    "classification": "qc_pass",
                    "ledger_last_hash": ledger_last_hash,
                    "reference_ledger_last_hash": reference_last_hash,
                }
            )

    _require(len(run_evidence) == 33, "V96 run evidence count must be 33")
    _require(len(reference_evidence) == 33, "V96 reference evidence count must be 33")
    _require(len(tape_evidence) == 12, "V96 tape evidence count must be 12")
    _require(
        all(
            runtime_values[field] == {value}
            for field, value in EXPECTED_RUNTIME.items()
        ),
        f"V96 runtime identity changed: {dict(runtime_values)}",
    )
    for (experiment_id, scenario, seed), rows in paired_inputs.items():
        expected_arms = 3 if experiment_id == "E3" else 2
        _require(
            len(rows) == expected_arms,
            f"V96 paired arm count changed: {scenario}/{seed}",
        )
        for field in (
            "workload_tape_sha256",
            "workload_tape_key",
            "workload_spec_hash",
            "capture_environment_sha256",
            "common_hpa_hash",
            "sla_artifact_sha256",
            "simulation",
        ):
            values = {object_hash(row[field]) for row in rows}
            _require(len(values) == 1, f"V96 paired {field} changed: {scenario}/{seed}")
        _require(
            rows[0]["common_hpa_hash"] == EXPECTED_COMMON_HPA_SHA256,
            f"V96 common HPA changed: {scenario}/{seed}",
        )

    output_payload = {
        "schema_version": "NSE_E3E4_GUARDED_ANCHOR_TRAINING_BLIND_AUDIT_V96_V1",
        "created_at": utc_now(),
        "status": "pass",
        "formal_results_eligible": False,
        "operational_group_closure_eligible": False,
        "performance_summaries_parsed": 0,
        "performance_results_consulted": False,
        "reveal_authorized": True,
        "confirmation_inputs_opened": False,
        "plan_path": str(PLAN),
        "plan_file_sha256": PLAN_FILE_SHA256,
        "prepared_path": str(PREPARED),
        "prepared_file_sha256": PREPARED_FILE_SHA256,
        "prepared_receipt_hash": PREPARED_RECEIPT_HASH,
        "runtime_identity": EXPECTED_RUNTIME,
        "common_hpa_sha256": EXPECTED_COMMON_HPA_SHA256,
        "training_seeds": sorted(TRAINING_SEEDS),
        "untouched_confirmation_seeds": sorted(CONFIRMATION_SEEDS),
        "arm_count": len(ARMS),
        "run_count": len(run_evidence),
        "reference_count": len(reference_evidence),
        "tape_count": len(tape_evidence),
        "pairing_audits": pairing_evidence,
        "reference_rename_receipt": {
            "path": str(RENAME_RECEIPT),
            "file_sha256": RENAME_RECEIPT_FILE_SHA256,
            "receipt_hash": RENAME_RECEIPT_HASH,
            "content_tree_hash": rename_receipt["content_tree_hash"],
        },
        "tapes": tape_evidence,
        "references": reference_evidence,
        "runs": run_evidence,
    }
    output_payload["audit_hash"] = object_hash(output_payload)
    write_json_atomic(output, output_payload)
    return output_payload


def main() -> None:
    audit = run_blind_audit()
    print(OUTPUT)
    print(file_hash(OUTPUT))
    print(audit["audit_hash"])


if __name__ == "__main__":
    main()
