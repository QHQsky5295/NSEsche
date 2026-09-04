# G18 Overflow Soft-Cap Release-Valve Implementation Audit

Date: 2026-09-05 (Asia/Shanghai)

Preregistration commit: `0375d3f08897f80f5d6dedb66c1f77ca1dc8c288`

Runtime source commit: `f3a1e0950c5a53a0ab614edacc2838703c2a9d81`

Status: `implementation_complete_zero_result_protocol_only_next`

## 1. Implemented mechanism

The source adds exactly one operational identity,
`ready_global_overflow_soft_cap_release_valve`. It collects the complete C0
dependency-ready sequence after the existing individual feasibility filter in
the unchanged legacy order. For feasible-ready count `F` and positive physical
node count `N`, it computes the fixed integer cap
`C=ceil(5N/4)=(5N+3)//4` with widened checked integer arithmetic. On a material
first-overflow window (`F>N`, previous-overflow bit closed, and `F>C`) it admits
exactly the first `C` feasible-ready players. At or below `C`, during adjacent
persistent overflow, and outside overflow it admits all feasible-ready players.
The only transition is `v_(t+1)=1[F>N]`.

The selector tests exercise below-limit, at/below-cap first overflow, material
first overflow, persistent release, reset and retrigger, exact `N=20 -> C=25`
and `N=6 -> C=8` ceiling arithmetic, prefix identity, and the impossibility of
adjacent positive-deferral windows. Zero configured nodes fail closed. No load
label, workload seed, baseline result, realized metric, future arrival, or
alternative cap is available to the decision.

## 2. Runtime checks and telemetry

G18 reuses the fail-closed readiness, feasibility, legacy-order, prefix,
solver-set, prepared-dispatch, and state-transition checks. An independent
runtime path recomputes the widened `5N` operand, exact ceiling cap,
applicability, material-pass bit, admission count, deferred count, mode, and
next valve state before solving. Any mismatch panics before dispatch.

The five mutually exclusive modes are `below_limit`,
`first_overflow_at_or_below_soft_cap_release`,
`first_overflow_soft_cap_bounded`, `persistent_overflow_release`, and
`post_overflow_reset`. Each enabled window records `F`, `N`, numerator 5,
denominator 4, scaled and rounded operands, applicability and material-pass
bits, entry/exit valve state, admitted/deferred counts, ordered-set hashes,
arrival range, and all structural violation counters. Solver assignments and
prepared dispatch commands must equal the admitted set.

The shared runtime validator accepts G18 only when this complete contract is
present. Directed mutations of the soft-cap fraction, rounding declaration,
strict comparison, state, admission/deferred behavior, formula identity,
load-specific branch, and baseline-expert declaration all fail closed.

## 3. Formula and identity audit

Utility evaluation, utility weights, action feasibility, price construction,
strict Eq. (15) best response, Eq. (19) feedback, social welfare, QPR, offline
reference search, and dispatch ranking are unchanged. G18 changes only the
finite active-player admission sequence passed to the unchanged equilibrium
solver; it does not alter any displayed Eq. (1)--(20).

Identity separation is explicit:

- operational schema version 13 binds
  `global_feasible_ready_material_first_overflow_ceil_5n_over_4_prefix_then_persistent_full_release_v1`;
- offline-reference key schema version is 14; and
- G18 reference-key tag 19 is distinct from C0 tag 1 and all prior tags.

The run contract declares the unchanged sequential existing-candidate
initialization, strict paper Eq. (15), no utility guard, no load-specific
branch, and no baseline expert.

## 4. Source and binary receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/src/config.rs` | 48,782 | `84e221244d70f152b3572f68691bcdc911c231c5e7296d354791fe263a317755` |
| `serverless_sim/src/sche/sche_nash.rs` | 445,999 | `8423e3bdffbe18aaf72faa39926e099cc99fc7eda3b7b3759a45c3e26f0aa949` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 31,931 | `887c438679b48632dfc870e46f07206500831e213c0d19123196195b815a9d59` |
| `scripts/reviewer_experiments/protocol/tests/test_g18_overflow_soft_cap_release_valve.py` | 5,869 | `10f342080bb6f6cc48633a418ca54404902a115cf7cf942c0348eb768f8a66b7` |
| `serverless_sim/Cargo.lock` | 49,409 | `5351d1431bd0ff8f45f5ca30aef6ded8759795bb073144900964792a4bcf9e64` |
| `serverless_sim/target_g18_overflow_soft_cap_impl/release/serverless_sim.exe` | 4,918,272 | `aaa0980cf451a88f7b3652f55c3e8c624af2a71b6312c40f4b19aa83bf6af713` |

The release executable did not exist before compilation. It was built once
with `cargo build --release --locked` only after the tracked worktree was clean
at source commit `f3a1e09`. The dedicated target contains 4,065 files and is
now protected from deletion, movement, overwriting, rebuilding, or Git staging
for the lifetime of G18. All earlier frozen targets and binaries remain
untouched.

## 5. Verification

- G18 exact-cap/state/rounding/zero-node Rust tests: 2/2 passed.
- Complete NSESche Rust module tests: 59/59 passed.
- Experiment-config Rust tests: 10/10 passed.
- G18 directed Python runtime-contract tests: 3/3 passed.
- Complete analysis regression: 181/181 passed in 86.475 seconds.
- Complete protocol regression: 254/254 passed in 737.619 seconds.
- Python-backed simulator consistency: 1/1 passed in 107.03 seconds with the
  preregistered Anaconda interpreter explicitly pinned.
- `cargo check`, release compilation, Rustfmt, Black, Python compilation, and
  Git whitespace checks passed.

For completeness, a broader all-module Rust diagnostic produced 136 passes and
two failures outside the G18 paths. The Python consistency failure disappeared
when `SERVERLESS_SIM_PYTHON=D:\\Anaconda3\\python.exe` was pinned. The remaining
`mechanism_thread::tests::test_algo_latency` timing assertion is unchanged from
the parent source and reproduces in isolation; none of the four G18 source
files touches that module or its default test configuration. It is therefore
recorded as a pre-existing unrelated harness failure, not silently omitted or
reclassified as a pass.

No D116--D120 tape, G18 manifest, offline reference, online run, throughput,
QPR, candidate outcome, or result-bearing artifact existed before the source
commit or release build.

## 6. Next authorization

After this audit is committed, only construction and validation of a
zero-result G18 protocol and manifest are authorized. They must bind source
commit `f3a1e09`, the exact binary hash above, C0/G18 x low/middle/high x fresh
D116--D120, operational schema 13, reference-key schema 14, tags 1/19, the
exact `ceil(5N/4)` rule, and all nine frozen development conditions.

Tape capture, offline-reference construction, online execution, strong
baselines, confirmation, formal replay, figures, and paper claims remain
blocked until their separate stage audits.
