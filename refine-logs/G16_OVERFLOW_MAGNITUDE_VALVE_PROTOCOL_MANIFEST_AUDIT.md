# G16 Overflow-Magnitude-Gated Valve Zero-Result Protocol and Manifest Audit

Date: 2026-09-04 (Asia/Shanghai)

Protocol commit: `7e7bdc59168d260156228603e6a95373267ff5ac`

Runtime source commit: `8da3dbdc9694e683889e5448bead908e288093fa`

Status: `zero_result_protocol_frozen_d111_d115_tape_capture_authorized`

## 1. Exact development product

The frozen manifest is
`runs/tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904/g16.manifest.json`.
It contains exactly the preregistered initial G16 product:

- C0 `ready_order` and candidate
  `ready_global_overflow_magnitude_release_valve`, both under `sche_nash`;
- homogeneous 20-node low, middle, and high loads using the unchanged
  submission-v1 workload profiles;
- the five fresh fixed development seeds D111--D115, disjoint from G12's
  D101--D105 and G14's D106--D110 banks;
- 30 unique online run specifications, 15 load/seed tape identities, and 30
  operational-mode-specific offline-reference dependencies.

Within every load/seed group, C0 and G16 share one workload specification hash
and one tape key. Their reference keys differ. No strong baseline,
confirmation seed, formal seed, other topology, other node count, or extra
candidate appears in the product. The manifest is explicitly non-formal.

## 2. Frozen mechanism and gates

For the complete global feasible-ready legacy sequence `A_t`, write
`F=|A_t|`, let `N` be the configured positive physical-node count, define
current overflow by `F>N`, and start the previous-overflow valve bit closed.
G16 admits the first `N` players only on a first-overflow window for which the
exact widened-integer comparison `4F>=5N` passes. A below-threshold first
overflow, every later adjacent overflow window, and every non-overflow window
admit the complete feasible-ready sequence. The only cross-window transition
remains `v_(t+1)=1[F>N]`.

Consequently, G16 equals C0 below the physical limit and on mild first
overflow, equals G14/G12 on material first overflow, and equals G14/C0 on
persistent overflow. Its longest possible actual positive-deferral episode is
one window. The rule contains no threshold search, fitted multiplier, request
cohort, frontier/pre-ready player, remaining-work key, warm override, utility
guard, load/seed/outcome branch, or baseline expert.

The candidate is bound to operational schema 12, reference-key schema 13, and
reference tag 18; C0 retains tag 1. The displayed paper Eqs. (1)--(20), strict
Eq. (15), Eq. (19), QPR, and offline-reference definitions remain unchanged
on the admitted finite player set.

All 30 first QC-valid rows must be retained. At every load, candidate mean
throughput and mean QPR must strictly exceed C0. At least one pair must be a
joint strict win and at least four of five pairs must be joint nonlosses. No
per-seed throughput or QPR ratio may be below 0.80. Every leave-one-seed-out
mean difference must be nonnegative, with at least four of five strictly
positive values per metric and load. Mean completion may not fall below C0,
mean request-latency ratio may not exceed 1.05, and mean placement-policy wall
time may not exceed 1.50x C0.

Activation additionally requires at least one material-first-overflow bounded
seed at each load, at least three below-threshold first-overflow release runs
across at least two loads, at least three persistent-overflow release runs
across at least two loads, and a longest actual positive-deferral episode of
at most one. Readiness, feasibility, legacy-order, prefix, bound,
magnitude-comparison, admission-rule, state-transition, and dispatch-set
violations must all be zero. Strict-PNE reference and runtime dispatch remain
mandatory. Passing every condition authorizes only a separately audited
strong-baseline addendum; failure closes G16 before confirmation. Gates cannot
be edited after outcome exposure.

## 3. Runtime and manifest receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g16_overflow_magnitude_valve_impl/release/serverless_sim.exe` | 4,901,888 | `652d1831f1e7ccb531b6ec462cb0a2d5963b49d0f0c7f6b35c0b6a8e92751cfd` |
| `runs/tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904/g16.manifest.json` | 735,443 | `6a1145c74f683ec720f124b10a7341d26e9067c58e9171c75c9e1b8ec4327dae` |

The manifest's embedded canonical object hash is
`23aa24bde803e4a8ac1adebd2fc69087a4100e01655fcb9602ad50036d7ccca7`.
At freeze time the run root contains exactly this one file and zero
subdirectories. All 30 tape hashes and event counts and all 30 reference
hashes, line counts, and completion markers are null. No request completion,
throughput, latency, cost, QPR, scheduler outcome, or candidate ranking exists.

## 4. Protocol source receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 28,903 | `31b0a5458fb48b6f2c58fb1bcd4e70e13d5387029de9ca57fa21d54c53fd073e` |
| `scripts/reviewer_experiments/protocol/g16_overflow_magnitude_valve.py` | 11,467 | `38772568cb71a7f8b5fb519948624f0f2e9dacb4383c2bfd7c14aac5deb6f619` |
| `scripts/reviewer_experiments/protocol/schema.py` | 257,517 | `2cbe191c0675c3b6b28c4bf22d20452c3c0728120e26aae2cce4b2fa96548967` |
| `scripts/reviewer_experiments/protocol/manifest.schema.json` | 43,548 | `1f43698741750babe0af53dbd02dfaeca5bc24430c097530ad4d9f785b412e8e` |
| `scripts/reviewer_experiments/protocol/tests/test_g16_overflow_magnitude_valve.py` | 11,442 | `a9cb4ebe327d9c862aa169c98930a64fa964757f3fee343d9b6fc233cfad5fe4` |

Verification before this audit commit:

- focused G16 runtime/manifest tests: 9/9 pass;
- directed G16 plus legacy G14/G12 tests: 27/27 pass;
- complete reviewer-protocol regression: 251/251 pass in 782.817 seconds;
- complete analysis regression: 157/157 pass in 84.827 seconds;
- Python compilation, Black formatting, JSON parsing, and Git whitespace
  checks: pass;
- generic manifest validation and static JSON Schema validation: pass;
- independent product, run-order, pairing, unbound-input, file, runtime, and
  root-tree checks: pass.

The manifest was created exactly once, after protocol source commit `7e7bdc5`
and an independent recheck of the protected binary's size, SHA-256, and source
commit. Protocol construction did not execute the simulator.

## 5. Authorization boundary

After this audit and the sole unbound manifest are committed, exactly 15 base
tape captures are authorized: low/middle/high x D111--D115. Each capture must
use the bound workload specification and retain the first QC-valid tape.
Scientific content cannot trigger recapture, seed replacement, omission,
down-weighting, or a change to the fixed 5/4 rule.

Offline-reference construction remains blocked until all 15 tapes, hashes,
event counts, rates, pairings, and capture receipts are independently audited
and committed. Online execution, analyzer construction, strong baselines,
confirmation, formal replay, figures, and manuscript claims remain blocked.
