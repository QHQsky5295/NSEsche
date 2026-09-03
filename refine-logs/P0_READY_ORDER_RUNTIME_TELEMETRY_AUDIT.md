# P0 `ready_order` Runtime and Telemetry Audit

Date: 2026-09-04 (Asia/Shanghai)  
Status: anchor runtime recovered and verified; retained logs are sufficient for P1; current HEAD is not authorized as an equivalent formal runtime

## 1. Exact formal runtime

| Item | Frozen identity / observation |
|---|---|
| Source commit | `98f822cf2dcb878024a2ca39cc56533895ea692c` |
| `sche_nash.rs` Git blob | `56374147d84fcdf6b9dbc65e7a4918628de14d5f` |
| `sche_nash.rs` stored-content SHA-256 | `3c48651a0312b7bcb1f8ab5b90cbb062d1fac821a9dcb5e2f2f58b251f5f8ca3` |
| `config.rs` Git blob / SHA-256 | `033c63152b59c06f898c03d08fbeed5335cd45ec` / `bd37604953442edbbc33f1140046f3b6df559d63efce2588bba718aa6cb64e59` |
| `Cargo.toml` Git blob / SHA-256 | `43d94f2a67d3e1bc6054f35528c8f6026c78ecd7` / `13f4f108025bd243b60c0b6885953a1adabb19a00cca10bacb094dee2b6c541b` |
| Executable | `serverless_sim/target_g1_corrected_runtime_98f822c/release/serverless_sim.exe` |
| Executable size / SHA-256 | 4,707,328 bytes / `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4` |
| Formal protocol commit | `125a741b7cffec1973f8d6632c781f9ff83d38ac` |
| Formal ready-manifest document/file hash | `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b` / `d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a` |
| Python executable / version | SHA-256 `a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384`; Python 3.9.7 |

The executable exists at the audited path and independently recomputes to the recorded digest. The source commit exists in the local object database. This is sufficient to execute later frozen cells without rebuilding.

`serverless_sim/Cargo.lock` is ignored and was not present in the anchor commit. The current on-disk lockfile has SHA-256 `5351d1431bd0ff8f45f5ca30aef6ded8759795bb073144900964792a4bcf9e64`, but it is not evidence of the exact build-time lockfile. Therefore source-only byte-for-byte rebuilding is not claimed. The preserved executable digest is the authoritative runtime identity; any future rebuild requires a newly frozen lockfile/toolchain and decision-equivalence protocol.

## 2. Python protocol identities

The formal protocol commit contains the following stored-content SHA-256 values:

| File | SHA-256 |
|---|---|
| `protocol/g1_corrected_runtime.py` | `e0e795acd73f17959a4d7c0069d11fd51bec074a726e4d2593965b2f6f0b4f07` |
| `protocol/runner.py` | `f66e3c700343743b5e55761d37fda06e49990dbeee4ce7a685304c1a54c94835` |
| `protocol/qc.py` | `a1c1ca5771e86fa8cbd3fe118ea249feb18f3cfc087a905c7bcd6e56eb4efdf7` |
| `protocol/schema.py` | `8cc925104c358128ad17e357dc5f68f27dacc989f3d2c80dce9b0bc0b12b6ffd` |
| `protocol/reference.py` | `3fbdb8c5dabdd692365df4d0de9c5a47847c18d34e257419beedda828a8731b5` |
| `protocol/serverless_adapter.py` | `2c01aff12b60863eb24dc1810b37da9af4a82b07a82ef1b593eb9a7187dfa937` |
| `analysis/feedback_trace.py` | `759587ea13b359fb5f11918658c756dbbd5523fa43d49597d06a454a2b942c18` |
| `analysis/observability.py` | `06a6895e86c9ed1a89be9edfd9bcc055f04e7035031af50cb40e238c8fb86900` |

These hashes identify the generation/QC stack. P1 analysis code must receive its own preregistration and hash; it need not alter or rerun the simulator.

## 3. Current source is not the formal runtime

At P0 HEAD `285b576ae5c3ef751e935cc3933ca99716851e2f`, current file SHA-256 values are:

- `sche_nash.rs`: `82d7932b25185bf962724e5702b80c74628edc1db7c611b084db5c574b28b9f6`;
- `config.rs`: `64eddf43d04d034f45d87e1763b76ccc6153dd2d8a9a2093e07e5d33d5464182`;
- `Cargo.toml`: `e4b9251ee3582bdf6bfadc0c5c2896bb2c46ad7567f9502279064c519157a6d1`.

Relative to the anchor, `sche_nash.rs` has 1,867 added and 54 deleted lines; `config.rs` has 32 added and one deleted line. The changes add G2–G7 initialization, order-counterfactual, equilibrium-envelope, lookahead/frontier, and diagnostic paths. Many are guarded or default-off, but core collection, initialization, best-response, solve, and logging functions were refactored. Static inspection therefore cannot establish byte- or command-stream equivalence.

Decision: no executable built from current HEAD is authorized for final `ready_order` results. The exact anchor executable remains the default. A new binary is needed only if a future P3 field is genuinely absent; before use it must pass a separately preregistered deterministic replay comparing per-request placement/action sequence, assignment hashes, RNG order, and result metrics against the anchor.

## 4. Retained-log telemetry coverage

A read-only structural inventory covered exactly the 20 formal homogeneous-low NSESche Q61–Q80 canonical directories. All counts below are 20/20:

- canonical QC pass and exact anchor-binary digest;
- one gzip `nash_metrics` stream, 1,000 window records, one `run_config`, and one `run_summary`;
- presence in every window of inner/outer rounds, stability, limit hits, oscillations, termination, assignment moves, and outer feedback trace;
- presence of reference value/source/state key, lookup/compute/SA iterations/cache/fallback fields;
- presence of solve, scheduler wall/thread CPU, and reference-refresh timing fields;
- 1,000 scheduler timing records with full/policy/welfare wall and thread-CPU fields;
- process duration, process-tree CPU, peak RSS, timeout, and exit-code fields;
- one request stream suitable for reconstructing placement/completion sequences;
- on-disk reference dependency exists and its SHA-256 matches the run binding.

The structural audit had zero errors. Existing G1 QC additionally verified `strict_eq15_ready=true`, `stream_contract_ready=true`, state-pair/reference pairing, and Eq. (16)/(19)/(20) recomputation.

## 5. Decision-neutral conclusion

P1 convergence, reference, and overhead analysis can be completed solely by parsing existing canonical artifacts. No replay, source modification, new telemetry, or decision-equivalence experiment is needed for P1. Policy thread CPU may be zero or timer-limited on Windows; the analysis must report observed values and timing scope rather than invent resolution. Process-tree CPU and peak RSS provide the run-level fallback.

For P2 homogeneous middle/high, the existing anchor executable, already captured tapes, and already built state-matched references are technically available, but V4 requires a new claim-reframed P2 preregistration after P1; availability is not authorization.
