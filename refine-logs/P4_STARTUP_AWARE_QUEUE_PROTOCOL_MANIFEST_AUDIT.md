# P4 Startup-Aware Queue Protocol and Manifest Audit

Date: 2026-09-05 (Asia/Shanghai)

Implementation commit: `dc242339790e97ef6f472edd865265adb50c75ef`

Status: `zero_result_protocol_frozen_tape_capture_authorized`

## 1. Frozen implementation boundary

The P4 implementation changes only the operational observation used for Eq.
(6)'s node queue length. The unchanged control uses
`q_n=pending+runnable`; the sole candidate uses
`q_n=pending+runnable+starting_resident`. Parent-blocked and data-blocked work
remain excluded. Eqs. (1)--(20), strict Eq. (15), `ready_order`, the action
set, common HPA, price/quality parameters, workload, topology, and metrics are
unchanged.

The semantics are explicit in protocol configuration and fail closed outside
`execution_ready` and `startup_aware`. Reference-key schema version 15 binds
the semantic tag, preventing cross-semantic reuse. Per-window telemetry emits
both the execution-ready count and the configured pressure count, together
with resident-partition and pressure-semantics invariants.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/p4_startup_aware_queue.py` | 10,563 | `4e1f0c7422228ac2b80a07b652005c4dba2717e87b936cee1134f76c723901c1` |
| `analysis/p4_startup_aware_queue.py` | 39,996 | `dfde692cd303a2af4a6b30efd6a0516500aebe15178d748f1e91b447380e9aa5` |
| `protocol/schema.py` | 290,928 | `ec256720973880c6844e6c8e0b84863b583f7ba34ff3a9a471f7031355fbcdf5` |
| `protocol/manifest.schema.json` | 43,774 | `81550f11a7c4b9409b5f9a79511cca138257aaee57de3c752fb9a0491dffb73b` |
| `serverless_sim/src/config.rs` | 50,174 | `26db7a8db092069a9d7e7ee3872c907551051c17476a41bfa0ea67f605bd467b` |
| `serverless_sim/src/sche/sche_nash.rs` | 453,718 | `407adc4bda5bcb546c72aa97ffe213b8b0462a002e133bed3ea9f9569e1c2868` |

The dedicated release runtime is frozen at:

- path:
  `serverless_sim/target_p4_startup_aware_queue_impl/release/serverless_sim.exe`;
- source commit: `dc242339790e97ef6f472edd865265adb50c75ef`;
- binary bytes: 4,943,872; and
- binary SHA-256:
  `d59efe5d40a9ee1a565fa9d37e7533863af28e52eafc3f328d87af7ec433664a`.

## 2. Verification evidence

- P4 Rust queue-semantic/config/reference-key tests: 4/4 pass;
- P4 protocol plus analyzer directed tests: 13/13 pass in 0.605 s;
- complete protocol suite: 275/275 pass in 752.888 s;
- complete analysis suite: 217/217 pass in 81.776 s;
- Rust formatting, Python compilation, static JSON Schema validation, and
  `git diff --check` pass; and
- the complete Rust suite initially passed 139/141. The Python-consistency
  test passed in isolation (1/1 in 98.88 s) after binding `D:\Anaconda3` on
  `PATH`. The unrelated pre-existing
  `mechanism_thread::tests::test_algo_latency` frame-timing assertion still
  fails in isolation; none of the P4 paths or directed tests fail.

The directed tests cover exact category inclusion/exclusion, `[0,1]`
window-max pressure, reference-key separation, explicit configuration,
exact 2-by-5 population/order, same-seed tape pairing, distinct semantic
references, immutable output, mutation rejection, all ten gates, and
fail-closed incomplete/duplicate populations.

## 3. Zero-result manifest

Path:
`runs/tscv1_p4_startup_aware_queue_d126_d130_dc24233_20260905/p4_startup_aware_queue.manifest.json`

- bytes: 246,314;
- file SHA-256:
  `35d5d81323ae4b8741986d21da66daa5f329aab8d2aac3417ba319b559646833`;
- canonical manifest object hash:
  `3263a11a517161150464d6fad3c3b10126467c5f3fb1c0b070276bca935816e5`;
- 10 unique run IDs and 10 unique run-spec hashes;
- five unique workload-tape keys, one shared by both settings within seed;
- 10 unique queue-semantics-specific reference keys;
- all tape and reference SHA-256 fields remain null;
- generic validation, dedicated P4 validation, and static JSON Schema
  validation pass; and
- no capture, reference, online, selection, or analysis directory exists.

Thus the manifest contains no metric, outcome, selected seed, candidate
decision, baseline result, or paper-eligible row.

## 4. Authorization boundary

After this audit is committed, exactly five D126--D130 homogeneous-low base
tapes may be captured in fixed seed order. Tape capture is input generation,
not control/candidate execution; neither queue-pressure setting may run during
capture.

Offline-reference construction, online execution, gate evaluation, baseline
compatibility, formal confirmation, figures, and manuscript claims remain
blocked. A complete tape-input binding audit must independently unlock the
ten reference builds.
