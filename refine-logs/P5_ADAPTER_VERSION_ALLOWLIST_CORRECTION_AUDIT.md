# P5 adapter version-allowlist correction audit

Date: 2026-09-05 (Asia/Shanghai)

Correction preregistration commit: `4e70fc3`

Correction implementation commit: `3de688cf79767716347760e552c1589d6fda24fc`

Status: `corrected_zero_result_protocol_frozen_tape_capture_authorized`

## 1. Failed source-bound instance retained

The prior `5bd817e` instance remains unchanged. Its first tape key has exactly
three quarantined pre-launch attempts and one terminal `capture_blocked`
ledger event. The retained 16-file failure tree contains 59,089 bytes. Its
3,285-byte ledger has SHA-256
`842493b17ef4034b74a226ab85e8d508670d4f995bfbe0454e5838694e0fde0d`
and tip
`bd905e58c495074c6b12bd6ae2f701604f91b9001e4ccd6ec6bf6538bdd0e1b5`.

All three processes exited 2 with the same stale reviewer-v3-only adapter
message before simulator launch. There is still no tape catalog, workload
tape, summary, canonical capture, online result, or metric in that instance.
It is exhausted and cannot be retried or promoted.

## 2. Exact correction

Commit `3de688c` changes only the workload-profile preflight allowlist in
`protocol/serverless_adapter.py` from reviewer-v3 alone to the exact set
`{reviewer-v3, reviewer-v4}` and updates its error text. All profile binding,
load, path, artifact hash, profile ID/set, and DAG-frequency checks remain
unchanged. Black made only formatting changes elsewhere in the same two
edited Python files; no runtime behavior outside the allowlist and its tests
changed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/serverless_adapter.py` | 21,909 | `62690ad7e1e16f534f3358633b634a6e9780ad6e2f4273b66b28353fb968f11d` |
| `protocol/tests/test_serverless_adapter.py` | 7,154 | `86c5b5ddd7598b9272efc61df19a2363457ccc3e77f7e4e8ce90045d74152f75` |
| correction preregistration | 2,718 | `d79e2a90795376ba51309d40329302e0e8f53c73d9238a52ca24b4ce239db826` |

The three new tests prove that valid reviewer-v4 is accepted, reviewer-v3
remains accepted, and every unknown version is rejected. Adapter-directed
tests pass 7/7 in 0.937 s. The full protocol suite passes 285/285 in 759.796
s. Python formatting/compilation and `git diff --check` pass. The Rust and
analysis implementation is byte-identical to the previously audited P5
source; its existing P5 9/9, NSESche 61/61, and analysis 221/221 evidence
therefore remains applicable.

## 3. Corrected release and zero-result manifest

The corrected source-bound release is:

- path:
  `serverless_sim/target_p5_common_platform_v4_adapter_impl/release/serverless_sim.exe`;
- source commit: `3de688cf79767716347760e552c1589d6fda24fc`;
- bytes: 5,013,504; and
- SHA-256:
  `0d802d6f7e13287bb72b42eed42d8ea19b4043238173d801668e9f2b83f61676`.

The corrected manifest is:

`runs/tscv1_p5_common_platform_p5p01_p5p03_3de688c_20260905/p5_common_platform.manifest.json`

- bytes: 2,217,365;
- file SHA-256:
  `068639a802ba1b4214ce4c092bd3b2ed499a0542244338f47d1a5eb10b5e3036`;
- canonical object hash:
  `259aa0b4b34647c3aff88a7d8a851caee258f71e2b9667ab85de04d77f50e9bb`;
- 90 unique run IDs/specs, nine unique tape keys, and 90 unique references;
- tape, FaaSRank, and reference bindings all remain false;
- generic, dedicated P5, and static JSON Schema validation pass; and
- its directory contains only the manifest.

No seed, load, method, order, P5 algorithm parameter, admission/drain rule,
metric, QC condition, analyzer gate, or result policy differs from the prior
manifest. Run identities differ because source commit and release identity are
intentionally part of each run spec.

## 4. Authorization boundary

After this audit commit, exactly nine input-only tapes may be captured from
the corrected manifest, one key at a time in fixed load-major then seed-major
order, in its new workspace. First QC-valid capture is canonical; technical
failures follow the unchanged bounded attempt policy. The old failure instance
must never be resumed.

After all nine tapes are independently validated and hash-bound, the existing
FaaSRank artifact may be bound only after proving training/evaluation tape
disjointness. References, online methods, duplicate replay, analysis, figures,
and claims remain blocked pending a committed input-binding audit.
