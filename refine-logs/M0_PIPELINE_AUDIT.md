# M0 Manifest, Metrics, and QC Audit

Date: 2026-09-02 (Asia/Shanghai)

## Frozen boundary

- Protocol commit: `a35b955949c838501aafa0158b5602311a16c69e`.
- Protocol ID: `tsc-reviewer-common-hpa-v4-tscv1-fixed20`.
- Method commit: `e2de863` (`formula-consistent-operational-v1-reference-key-v9`).
- Old manuscript: `（5-12V2）TSC_NSESche_Complete_IEEE_.pdf`.
- Old manuscript SHA-256: `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18` (recomputed from the source PDF).
- `default_protocol.json` SHA-256: `45ce20f4201d9661e7cb27f2d400952108e6ce7fa184ae219cf2ecb34b37e535`.
- `manifest.schema.json` SHA-256: `95ec32ea854cd0993c0b9ff2ec5a6d5dfde4cbe1a430d9b6180ab9b303ac9448`.
- `matrix.py` SHA-256: `33118a95137df2d2fdce5ee0fc9489bae4b5a6ca3d89a5209e49ec8f182d71f8`.
- `schema.py` SHA-256: `a35d2823ab1abc98e592673e4b51351e60aad34a154aea8eb8d6e535a19c742e`.

## Fixed formal matrix

The formal sample size is not adaptive. Bank A is E01--E10 and bank B is E11--E20; both are mandatory and every method uses the same paired seed within a cell.

| Experiment | Bank A | Bank B | E01--E20 |
|---|---:|---:|---:|
| E1 | 600 | 600 | 1,200 |
| E2 | 600 | 600 | 1,200 |
| E3 | 300 | 300 | 600 |
| E4 | 100 | 100 | 200 |
| E5 | 120 | 120 | 240 |
| E6 | 40 | 40 | 80 |
| E7 | 120 | 120 | 240 |
| Total | 1,880 | 1,880 | 3,760 |

- Offline-reference dependencies: 410 in each bank and 820 in the combined manifest.
- Bank-A and bank-B run IDs are disjoint; their union equals the exact `seed_stage=all` run-ID and run-spec set.
- Example run ID: `TSCv1.E1.homogeneous.n20.low.greedy.FE01.ce00a105`.
- E7 now follows the same fixed 20-seed policy as E1--E6; the legacy `ci_extension` identifier is only the bank-B compatibility name.

## Provenance and admission rules

- Manifests bind `phase`, `bank_id`, the workload/topology/algorithm seed triplet, method version, workload-tape/config/reference hashes, and the old-PDF version/hash.
- Only `phase=formal` plus `formal_results_eligible=true` can enter the formal analysis exporter. Integration smoke is forcibly `phase=pilot` and ineligible.
- Every run audit records the Git commit and verified simulator binary, Python executable, Cargo.lock, method version, phase, bank, PDF alignment, and frozen run specification.
- Pairing first checks immutable workload/HPA/environment hashes within each paired group, then requires one global Git commit, binary hash, Python hash, and Cargo.lock hash across the entire audited formal artifact. The final E01--E20 artifact must pass this global audit.
- Result-conditioned sample extension is forbidden in the protocol config, manifest, custom validator, and JSON Schema. CI widths are descriptive diagnostics only.
- Zero-throughput/completion outcomes remain valid scientific observations. Formal retries are technical and bounded; deleting a canonical result does not authorize a selective rerun.

## Metrics and reference contract

- Run-level export covers throughput, simulator cost per completed request, QPR, mean/p50/p95/p99 latency, fixed-window and drained completion ratios, queue peak/area, drop/reject/timeout, CPU/memory utilization, placement/common-mechanism wall and thread CPU, and process-tree peak RSS.
- Burst recovery is derived from the preregistered queue-plus-p95 endpoint and retains right-censoring rather than replacing it with a synthetic value.
- NSESche observability retains inner/outer rounds, stability, oscillation, limit-hit, and non-convergence classifications at window and run level.
- Offline references use build/replay with hash-bound unique keys and retain build wall/CPU/RSS, SA iterations, table bytes, load/lookup time, and missing/zero/negative rates.
- QPR is computed per run before aggregation; no metric gate accepts or rejects a run because its value is favorable or unfavorable.

## Verification

- Full protocol suite: 140 passed, 0 failed (`590.884 s`).
- Full analysis suite under `D:\Anaconda3\python.exe`: 45 passed, 0 failed (`84.769 s`).
- NSESche method suite from the method freeze: 24 passed, 0 failed.
- Python custom validation: bank A, bank B, and combined manifests pass.
- Draft 2020-12 JSON Schema: bank A, bank B, and combined manifests pass.
- `git diff --check`: pass; Windows checkout reports only expected LF-to-CRLF notices.
- JSON parse and Python compile checks: pass.

No paper experiment result is closed by this audit. It freezes the execution and analysis boundary for the following M1 pilot and qualification stages.
