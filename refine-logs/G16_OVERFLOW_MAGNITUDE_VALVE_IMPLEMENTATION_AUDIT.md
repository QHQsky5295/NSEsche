# G16 Overflow-Magnitude-Gated Release-Valve Implementation Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `ca207ceac7e58d3257d2fdece3f9246de9d503a8`

Runtime source commit: `8da3dbdc9694e683889e5448bead908e288093fa`

Status: `implementation_complete_zero_result_protocol_only_next`

## 1. Implemented mechanism

The source adds exactly one operational identity,
`ready_global_overflow_magnitude_release_valve`. It collects the complete C0
dependency-ready sequence after the existing individual feasibility filter in
the unchanged legacy order. With feasible-ready count `F`, positive physical
node count `N`, current overflow `F>N`, and the previous-overflow bit initially
closed, it bounds the active set to the first `N` players only on a first-
overflow window satisfying the exact widened-integer comparison `4F>=5N`.
Every other window admits the complete feasible-ready sequence. The only
cross-window transition remains `v_(t+1)=1[F>N]`.

The pure selection tests verify the exact boundary: for `N=20`, `F=24`
releases all 24 players while `F=25` admits exactly 20. A non-divisible
boundary with `N=6` releases `F=7` and bounds `F=8`. Zero nodes fail closed.
A mild first overflow followed by a larger adjacent overflow never triggers a
late bound, because the second window is already a persistent-overflow window.
Reset and re-trigger behavior and the maximum one-window positive-deferral
streak are tested directly.

The four preregistered equivalences also hold: below the limit G16 equals C0;
on a mild first overflow it equals C0; on a material first overflow it equals
G14/G12; and on persistent overflow it equals G14/C0. No workload, load label,
seed, baseline result, realized metric, or future arrival is available to the
decision.

## 2. Runtime checks and telemetry

G16 reuses the fail-closed readiness, feasibility, legacy-order, prefix,
solver-set, prepared-dispatch, and state-transition checks and adds an
independently recomputed exact magnitude-comparison check. Its window record
includes `F`, `N`, the fixed 5/4 threshold, both integer comparison operands,
applicability and pass bits, entry/exit valve state, admitted/deferred counts,
ordered-set hashes, arrival range, and all nine violation counters.

The five mutually exclusive modes are `below_limit`,
`first_overflow_below_magnitude_release`,
`first_overflow_magnitude_bounded`, `persistent_overflow_release`, and
`post_overflow_reset`. The runtime independently reconstructs the expected
mode, active count, deferred count, threshold result, and next state and
panics before solving if any pre-dispatch check differs. It then requires the
solver assignment set and dispatched command set to equal the admitted set.

G14 retains its prior four modes and JSON field set; G12 retains its fixed-
prefix contract. C0 and every non-valve operational mode reset the internal
valve bit. Directed G16/G14/G12 contract tests all pass, and the complete
legacy protocol suite reports no regression.

## 3. Formula and identity audit

Utility evaluation, utility weights, action feasibility, price construction,
strict Eq. (15) best response, Eq. (19) feedback, social welfare, QPR, offline
reference search, and dispatch ranking are unchanged. G16 reports
`paper_Eqs_1_20_strict_argmax` and the unchanged sequential existing-candidate
initialization. The new rule selects only the finite active player sequence;
the weighted-potential/finite-improvement argument therefore continues to
apply without changing a displayed paper formula.

Identity separation is explicit:

- operational schema version 12 binds
  `global_feasible_ready_material_first_overflow_5_over_4_prefix_then_persistent_full_release_v1`;
- the future release binary uses reference-key schema version 13; and
- G16 reference tag 18 is distinct from C0 tag 1, G12 tag 16, and G14 tag 17.

The shared runtime validator accepts G16 as strict Eq. (15) only when the
complete identity, 5/4 threshold, integer comparison, state transition,
admission, no-load-branch, and no-baseline-expert declarations match exactly.
Directed mutations of each field fail closed.

## 4. Source and binary receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/src/config.rs` | 48,611 | `8bcfd17e3b86b85f75254d291b5a91f70aabc99a37bd78138e9fe3b09a362416` |
| `serverless_sim/src/sche/sche_nash.rs` | 427,183 | `f141210c4c205215b4d8defd80d5a8d1511a1e7db138f94a670c5e82822c5efc` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 28,903 | `31b0a5458fb48b6f2c58fb1bcd4e70e13d5387029de9ca57fa21d54c53fd073e` |
| `scripts/reviewer_experiments/protocol/tests/test_g16_overflow_magnitude_valve.py` | 5,749 | `2fbbe6c817b9bead195706632d0a22769755fe82f39201ecc0152da7b6f952ce` |
| `serverless_sim/target_g16_overflow_magnitude_valve_impl/release/serverless_sim.exe` | 4,901,888 | `652d1831f1e7ccb531b6ec462cb0a2d5963b49d0f0c7f6b35c0b6a8e92751cfd` |

The dedicated release binary was compiled only after the tracked worktree was
clean at source commit `8da3dbd`. Its 1,490-file target directory is now
protected from deletion, movement, overwriting, or Git staging for the
lifetime of G16.

## 5. Verification

- G16 exact-boundary/state/equivalence/zero-node Rust tests: 3/3 passed.
- Complete NSESche Rust tests: 57/57 passed.
- G16 plus legacy G14/G12 directed Python contract tests: 21/21 passed.
- Complete analysis regression: 157/157 passed in 101.706 seconds.
- Complete protocol regression: 245/245 passed in 811.954 seconds.
- `cargo check`, release compilation, Rustfmt, Black, Python compilation, and
  Git whitespace checks passed.

The repository contained no D111--D115 evidence, G16 manifest, G16 run root,
workload tape, offline reference, online metric, throughput, QPR, or candidate
outcome before the source commit or release build.

## 6. Next authorization

After this audit is committed, only construction and validation of a
zero-result G16 protocol/manifest is authorized. It must bind source commit
`8da3dbd`, the exact binary hash above, C0/G16 x three loads x fresh
D111--D115, operational schema 12, reference-key schema 13, tags 1/18, the
exact 5/4 threshold, and all nine frozen development conditions.

Tape capture, offline-reference construction, online execution, strong
baselines, confirmation, formal replay, figures, and paper claims remain
blocked until their separate stage audits.
