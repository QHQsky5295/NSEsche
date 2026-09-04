# G14 deferral release-valve implementation audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `cdb440adb44c7d6886bd5520605d918e60b3e4e5`

Runtime source commit: `64d36b7b0fc6aa441283cb3b6c6115c8ba1d834b`

Status: `implementation_complete_zero_result_protocol_only_next`

## Implemented state machine

The source adds exactly one operational identity,
`ready_global_deferral_release_valve`. In each window it retains the complete
global C0 dependency-ready sequence after the existing individual feasibility
filter and in the unchanged legacy order. With node count `N`, current
overflow `o_t=1[|A_t|>N]`, and initial state `v_0=0`, it admits the first `N`
players only when `v_t=0` and `o_t=1`; otherwise it admits all of `A_t`. The
only cross-window update is `v_(t+1)=o_t`.

The pure selection tests establish the exact structural equivalences: below
the limit G14 equals C0 and G12; the first overflow window equals G12; and
every later adjacent overflow window equals C0. An eight-window boundary,
persistence, reset, and re-trigger sequence also verifies that actual positive
deferral cannot occur in adjacent windows.

The rule is load-blind, seed-blind, and parameter-free. It contains no fitted
multiplier, result branch, request cohort, remaining-work key, frontier,
lookahead, warm override, or baseline expert.

## Runtime checks and telemetry

The implementation retains G12's readiness, feasibility, legacy-order,
prefix, bound, solver-set, and prepared-dispatch checks and adds exact
admission-rule and state-transition checks. The runtime panics instead of
emitting a valid-looking result if any check is nonzero.

G14 window records expose the configured node count, current overflow,
valve state before and after the decision, mutually exclusive mode, effective
admission limit, admitted/deferred counts, ordered-set hashes, admitted arrival
range, and all violation counts. The modes are exactly `below_limit`,
`first_overflow_bounded`, `persistent_overflow_release`, and
`post_overflow_reset`.

The legacy G12 run and window JSON contracts retain their prior field sets and
schema string. Its protocol contract tests still pass. C0 and all other modes
remain outside the global-ready branch, and switching away from G14 resets the
one-bit state to closed.

## Formula and identity audit

Utility evaluation, price construction, strict Eq. (15) best response,
Eq. (19) feedback, social welfare, QPR, the offline-reference search, and
dispatch are unchanged. G14 reports `paper_Eqs_1_20_strict_argmax` and uses
the same sequential existing-candidate initialization. The finite-player
weighted-potential/finite-improvement argument therefore continues to apply to
the exact admitted set in every window.

Identity separation is explicit:

- operational schema version 11 binds
  `global_feasible_ready_first_overflow_prefix_then_persistent_full_release_v1`;
- reference-key schema advances from 11 to 12 for the new release binary; and
- G14 reference tag 17 is distinct from C0 tag 1 and G12 tag 16.

The shared runtime-contract validator recognizes G14 as strict Eq. (15) only
when every frozen state-machine declaration matches. Directed mutation tests
reject schema, collection, order, initial-state, transition, admission,
deferral, load-branch, and baseline-expert drift.

## Source and runtime receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/src/config.rs` | 48,437 | `dc9acb7b0880a41fdb8b403f9a90a9f7192318ffcc218f9857debcc7ee164c73` |
| `serverless_sim/src/sche/sche_nash.rs` | 406,465 | `f14ac68e5ceeac8e1f8506913214b72b1e6eacee7e30a5d9826a5bfde1d5788d` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 25,819 | `9a4b451d255f7d95e2ade99895ac1a2225e631ba14d1e7ba284ebf560729c1d8` |
| `scripts/reviewer_experiments/protocol/tests/test_g14_deferral_release_valve.py` | 4,874 | `086f76ed6d9bf3cf22017f8f80d07f28255eb983f0acca890526f1029c038b77` |
| `target_g14_deferral_release_valve_impl/release/serverless_sim.exe` | 4,885,504 | `ed885d50c9342a2a98f7a5a82662aef5c8415504111960d046569e5e66c873c7` |

The release binary was compiled only after source commit `64d36b7`. Its
dedicated untracked target directory is now protected from deletion, movement,
overwriting, or Git staging for the lifetime of G14.

## Verification

- G14 state-machine boundary and equivalence tests: 2/2 passed.
- Complete NSESche tests: 54/54 passed.
- Experiment configuration tests: 10/10 passed.
- G14 plus legacy G12 protocol-contract tests: 10/10 passed.
- Complete reviewer protocol regression: 234/234 passed in 980.840 seconds.
- Complete analysis regression: 135/135 passed in 106.140 seconds.
- `cargo check`, release compilation, Rustfmt, Black, Python compilation, and
  Git whitespace checks passed.
- The unfiltered Rust suite is 131/133. Its two failures are the same existing
  `mechanism_thread::tests::test_algo_latency` timing assertion and
  `sim_env::tests::test_python_res_consistency` use of a system Python without
  NumPy. Neither invokes the G14 admission identity; every G14, NSESche, and
  configuration test passes.

No G14 run root, D106--D110 tape, offline reference, online metric,
throughput, QPR, or candidate outcome exists at this checkpoint.

## Next authorization

After this audit is committed, only construction and validation of a
zero-result G14 protocol/manifest is authorized. It must bind source commit
`64d36b7`, the exact release-binary hash above, C0/G14 x three loads x fresh
D106--D110, operational schema 11, reference-key schema 12, and tags 1/17.
Tape capture, reference construction, online execution, strong baselines,
confirmation, formal replay, figures, and paper claims remain blocked until
their separate stage audits.

