# P5 common-platform protocol and manifest audit

Date: 2026-09-05 (Asia/Shanghai)

Implementation commit: `5bd817ebe5ab3173bc387f8ebfdb6ded444b3dc6`

Status: `zero_result_protocol_frozen_tape_capture_authorized`

## 1. Frozen implementation boundary

The implementation adds one method-neutral external FCFS admission queue,
derives the active-request limit from public memory headroom, continues every
scheduler through a result-blind bounded drain, and records complete arrival,
admission, active, completion, censoring, latency, cost, and metric identities.
At 20 homogeneous nodes the active limit is exactly 100. The arrival and fixed
throughput horizon is 1,000 ms; the maximum post-arrival drain is
`max(1000, ceil(4W/C) + L_static)` and may stop early only when both the
external FIFO and active cohort are empty.

Paper Eqs. (1)--(20), strict Eq. (15), the NSESche action set, `ready_order`,
the already frozen load-specific price/quality parameters, and run-level QPR
algebra are unchanged. The new protocol version is `reviewer-v4`; legacy
protocol behavior remains disabled by default.

The pre-result addendum also freezes two previously unserialized details:
FaaSRank must reuse the existing frozen model without retraining or reselection
after tape-disjointness verification, and the one duplicate audit compares
timing-free workload, policy-decision, terminal-count, and scientific-result
semantic hashes.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/p5_common_platform.py` | 12,595 | `dfc6f31fe0ea74d5d7fada825dd8bfdf7235015d3734fa73c70743cfad716144` |
| `analysis/p5_common_platform.py` | 30,667 | `fb80f6c4dbfd5849ac20e2df7c910299bac49375f916aab07843770cd028521f` |
| `protocol/schema.py` | 306,297 | `f104bbb7b0b5c5be0b5c4aee77446c27031eed4530eab80670ab2da24a7b2dcd` |
| `protocol/qc.py` | 169,785 | `aa7eb6eb15b5ddf3a996966adfd94df60e08a88816e350edbc76b6eabe3d2a3e` |
| `protocol/manifest.schema.json` | 43,945 | `0031c1ac12e221b8778839f3cdb5c69236c8cf96816183e3cc74b13e77c4d6a6` |
| `P5_COMMON_PLATFORM_PRERESULT_ADDENDUM.md` | 3,086 | `fa06c71a9c18043cdd81aec1bfbf506f80f835f306f380f41fb85ac1ad21c47b` |
| `serverless_sim/src/config.rs` | 55,307 | `31e03a82753d0f670e59097bb7212ddc9f325685668362aa77fd557f8d55f2fb` |
| `serverless_sim/src/request.rs` | 34,718 | `3f169028d00036d04a52db7ce11d5a32078256ee9498539f52c1ca08a0af6f03` |
| `serverless_sim/src/sim_env.rs` | 32,520 | `6a2439c70389defd50396f4d35c922760dc9da77059b10a25b5eab178a8aaf8e` |
| `serverless_sim/src/sim_loop.rs` | 15,573 | `1a76eb1cd161321041f4146f774ff6af9f340db899a9a3d0f7144c22d9f59af9` |
| `serverless_sim/src/experiment_record.rs` | 53,522 | `cbbba9552c614577e84f9b3dd67c88a9fedc842b84717283107af8341fdb0cf0` |
| `serverless_sim/src/workload.rs` | 7,953 | `0f7f7c95832c56f757aad0246575552d25c20b91166c80549d31e5cb398f4da0` |

The dedicated release runtime is frozen at:

- path:
  `serverless_sim/target_p5_common_platform_impl/release/serverless_sim.exe`;
- source commit: `5bd817ebe5ab3173bc387f8ebfdb6ded444b3dc6`;
- binary bytes: 5,013,504; and
- binary SHA-256:
  `d3fc580eaeab3f4220e088d039d04145ddae4ec440fd84122b06c1399b89c1d7`.

## 2. Verification evidence

- P5 Rust admission/cap/drain/metric tests: 9/9 pass;
- NSESche Rust tests: 61/61 pass;
- complete protocol suite: 282/282 pass in 774.876 s;
- complete analysis suite: 221/221 pass in 84.876 s;
- final directed P5 protocol/analyzer suite: 11/11 pass in 5.398 s;
- Rust formatting, Python formatting and compilation, static JSON Schema,
  generic manifest validation, and `git diff --check` pass; and
- the complete Rust suite retains 141 passing tests and two known historical,
  unrelated failures (`test_algo_latency` and the system-Python environment
  check); no P5 or NSESche directed test fails.

The tests cover same-frame and cross-frame FCFS order, next-frame refill,
active-cap derivation, weak-scaling drain arithmetic, exact early/hard stop,
dynamic summary identities, stream conservation, exact 90-run population,
same-pair tape identity, 90 distinct references, legal staged binding order,
immutable output, all twelve method-neutral gates, incomplete/duplicate
fail-closure, and an explicitly unfavorable NSESche ranking that cannot alter
gate status or authorize a retry.

## 3. Zero-result manifest

Path:
`runs/tscv1_p5_common_platform_p5p01_p5p03_5bd817e_20260905/p5_common_platform.manifest.json`

- bytes: 2,217,343;
- file SHA-256:
  `d242002f04c20deb1b61b53d3f47ae5da8e1f8877099b57f5222476d948ecbd2`;
- canonical manifest object hash:
  `8e69a03ae6cc0123a4220908842d12d240d44251e52f722dacdc30771d26c6ee`;
- 90 unique run IDs and 90 unique run-spec hashes;
- nine unique workload-tape keys, one shared by all ten methods within each
  load/seed pair;
- 90 unique method-state reference keys;
- `all_tapes_bound=false`, `all_faasrank_models_bound=false`, and
  `all_references_bound=false`;
- generic validation, dedicated P5 validation, and static JSON Schema
  validation pass; and
- the manifest directory contains only this manifest: no tape, reference,
  online, duplicate, analysis, selected-seed, or figure artifact exists.

Thus the manifest contains no metric, outcome, method rank, old-PDF match,
candidate decision, or paper-eligible row. Its analyzer hash is
`fb80f6c4...8521f`, and its result appendix is structurally sealed until
conditions 1--11 have been evaluated.

The pre-existing FaaSRank model intended for later binding is
`runs/tscv1_m1_qual_080a3da_20260902/faasrank.frozen.json` (20,795 bytes,
SHA-256 `4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`).
It is not yet bound, and no P5 evaluation tape currently exists.

## 4. Authorization boundary

After this audit is committed, exactly nine P5 tapes may be captured in the
fixed load-major, seed-major order. Tape capture is input generation only;
none of the ten online methods may run during capture.

After all nine tapes are independently validated and hash-bound, the existing
FaaSRank artifact may be bound only after proving training/evaluation tape
disjointness. Offline-reference construction, online execution, duplicate
replay, gate evaluation, final formal experiments, figures, and manuscript
claims remain blocked. A complete tape/model input-binding audit must
independently unlock the 90 reference builds.
