# G12 global-ready player admission implementation audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `68e886934675e323844be1bfbf93e56bf764fc81`

Runtime source commit: `c4e31a99b62012bf0fbdd48f7a6a0010d7484801`

Status: `implementation_complete_zero_result_protocol_only_next`

## Implemented boundary

The source implements exactly one new operational identity,
`ready_global_player_admission_n`. It retains the complete global C0
dependency-ready sequence, applies the existing individual placement-
feasibility filter without reordering, and admits the exact first
`min(feasible_ready_players, configured_node_count)` players. Deferred feasible
players remain unplaced and re-enter the next window's global ready pool.

The candidate uses the unchanged C0 key `(arrival frame, request ID,
topological rank, function ID)`. It has no request cohort, remaining-work key,
frontier, lookahead, warm-placement override, utility relaxation, tunable
multiplier, load branch, seed branch, result branch, or baseline expert. C0 and
all registered baseline paths are outside the new conditional branch.

The admission occurs after global dependency-ready collection and individual
feasibility filtering but before the Nash solve. The existing solver and
dispatcher operate on the same admitted vector. The implementation now checks
the pre-solve readiness, feasibility, legacy-order, prefix, and cardinality
invariants; verifies that the solver assignment has exactly the admitted
player set before dispatch; and verifies that the prepared command order and
count equal the admitted vector. A violation panics instead of producing a
valid-looking result.

## Formula and identity audit

The utility, social-welfare, pricing, strict best-response, feedback, QPR, and
offline-reference algorithms are unchanged. `ReadyGlobalPlayerAdmissionN`
reports `paper_Eqs_1_20_strict_argmax`. The weighted-potential/finite-
improvement argument continues to apply to the finite admitted player set in
each window.

To prevent cross-mode reference reuse:

- reference-key schema advances from 10 to 11;
- the new operational reference tag is 16, distinct from C0 tag 1 and G10
  tags 14/15; and
- operational schema 10 binds
  `global_feasible_ready_legacy_order_prefix_node_count_v1`.

Run configuration logs disclose the global scope, legacy order, node-count
limit, and next-window deferral. Window logs disclose dependency-ready and
feasible counts, admitted/deferred counts, limit, order-sensitive candidate
and admitted hashes, admitted arrival range, all six violation counts, and the
existing command/PNE/reference fields.

## Source and runtime receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/src/config.rs` | 48,293 | `5ec0fa9e949bc9946fbb6960abe158b8859867d516d27a801231ff07a5ba7bad` |
| `serverless_sim/src/sche/sche_nash.rs` | 391,103 | `152ab299060d2febf66c9ab4e70689021d368dda0f89e68d314f4c880d29f0a7` |
| `target_g12_global_ready_impl/release/serverless_sim.exe` | 4,871,168 | `35e7e3d22b04baa232177394d487603ddc545ffcc461992ac1aa7c7ae2044f27` |

The release binary was built only after source commit `c4e31a9` and is retained
in the dedicated untracked target directory. That directory is protected from
deletion, movement, or Git staging for the lifetime of the G12 protocol.

## Verification

- Core G12 boundary and order-hash tests: 2/2 passed.
- NSESche tests, including identity/schema/reference separation: 52/52 passed.
- Experiment configuration tests: 10/10 passed.
- Complete reviewer protocol regression: 224/224 passed in 998.484 seconds.
- `cargo check`, release compilation, `cargo fmt --check`, and Git whitespace
  checks passed.
- The unfiltered Rust suite is 129/131. The two failures are the same existing
  thread-timing assertion in `mechanism_thread::tests::test_algo_latency` and
  the system-default-Python NumPy dependency in
  `sim_env::tests::test_python_res_consistency`; neither invokes the G12
  admission path. Every NSESche and configuration test passes.

No G12 run directory, D101--D105 tape, offline reference, online metric,
throughput, QPR, or candidate outcome exists at this checkpoint.

## Next authorization

After this audit is committed, only construction and validation of a
zero-result G12 protocol/manifest is authorized. It must bind the exact source
commit and release-binary hash above and freeze C0/G12 x three loads x
D101--D105 before any tape capture. Tape capture, offline-reference building,
online execution, strong baselines, confirmation, formal replay, figures, and
claims remain blocked until their separate stage audits.
