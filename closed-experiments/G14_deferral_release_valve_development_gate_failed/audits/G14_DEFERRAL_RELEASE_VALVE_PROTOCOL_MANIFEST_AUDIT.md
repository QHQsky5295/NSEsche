# G14 Deferral Release-Valve Zero-Result Protocol and Manifest Audit

Date: 2026-09-04 (Asia/Shanghai)
Protocol commit: `88e2bf9682a94a2e445ff87aa21151249981f13b`
Runtime source commit: `64d36b7b0fc6aa441283cb3b6c6115c8ba1d834b`
Status: `zero_result_protocol_frozen_d106_d110_tape_capture_authorized`

## 1. Exact development product

The frozen manifest is
`runs/tscv1_g14_deferral_release_valve_d106_d110_64d36b7_20260904/g14.manifest.json`.
It contains exactly the preregistered initial G14 product:

- C0 `ready_order` and candidate
  `ready_global_deferral_release_valve`, both under `sche_nash`;
- homogeneous 20-node low, middle, and high loads using the unchanged
  submission-v1 workload profiles;
- the five fresh fixed development seeds D106--D110, disjoint from G12's
  D101--D105 bank;
- 30 unique online run specifications, 15 load/seed tape identities, and 30
  operational-mode-specific offline-reference dependencies.

Within every load/seed group, C0 and G14 share one workload specification hash
and one tape key. Their reference keys differ. No strong baseline,
confirmation seed, formal seed, other topology, other node count, or extra
candidate appears in the product.

## 2. Frozen mechanism and gates

For the complete global feasible-ready legacy sequence `A_t`, G14 defines
`o_t = 1[|A_t| > N]`, starts with `v_0 = 0`, and updates
`v_(t+1) = o_t`. It admits the first `N` players only when `v_t = 0` and
`o_t = 1`; otherwise it admits all of `A_t`. Thus a first overflow window
equals G12, a later adjacent overflow window equals C0, and actual positive
deferral episodes cannot exceed one window. The rule contains no fitted
threshold, multiplier, request cohort, frontier/pre-ready player,
remaining-work key, warm override, utility guard, load/seed/outcome branch,
or baseline expert.

The candidate is bound to operational schema 11, reference-key schema 12, and
reference tag 17; C0 retains tag 1. The displayed paper Eqs. (1)--(20), strict
Eq. (15), Eq. (19), QPR, and offline-reference definitions remain unchanged
on the admitted finite player set.

All 30 first QC-valid rows must be retained. At each load, candidate mean
throughput and QPR must both exceed C0; throughput, QPR, and joint paired wins
must each be at least 3/5; no per-seed throughput or QPR ratio may be below
0.80; and every leave-one-seed-out mean difference must be positive for both
metrics. Mean completion ratio may not fall below C0, mean request latency
must be lower, and mean placement-policy wall time may not exceed 1.50x C0.

Activation additionally requires at least one first-overflow-bounded seed at
each load, at least three persistent-overflow release runs across at least two
loads, and a longest observed positive-deferral episode of at most one.
Readiness, feasibility, legacy-order, prefix, admission-rule,
state-transition, dispatch-set, strict-PNE reference, runtime-identity, and
dispatch checks remain mandatory. Passing requires every gate and authorizes
only a separately preregistered strong-baseline addendum. Failure closes G14
before confirmation. Gates cannot be edited after outcome exposure.

## 3. Runtime and manifest receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g14_deferral_release_valve_impl/release/serverless_sim.exe` | 4,885,504 | `ed885d50c9342a2a98f7a5a82662aef5c8415504111960d046569e5e66c873c7` |
| `runs/tscv1_g14_deferral_release_valve_d106_d110_64d36b7_20260904/g14.manifest.json` | 732,824 | `0d0d1983225a84cf7a2bebb05ff8f26fea42f2f71ed29ffa81b2622c102a3219` |

The manifest's embedded canonical object hash is
`7d0e6e294e04957810c87859fa92bac20e8d2346d97ec0dcc06d91a8e5d8b979`.
At freeze time the run root contains exactly this one file and zero
subdirectories. All 30 tape hashes/event counts and all 30 reference hashes,
line counts, and completion markers are null. No request completion,
throughput, latency, cost, QPR, scheduler outcome, or candidate ranking exists.

## 4. Protocol source receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 25,819 | `9a4b451d255f7d95e2ade99895ac1a2225e631ba14d1e7ba284ebf560729c1d8` |
| `scripts/reviewer_experiments/protocol/g14_deferral_release_valve.py` | 10,745 | `df685e5111ccbeb8a38f4b8430ee731ddf6ce7b929600ac35751e91b26ab2945` |
| `scripts/reviewer_experiments/protocol/schema.py` | 245,138 | `73e456d54351311fb6e0b9eebd83e7a3d32603354f1615eb9d42ed3223150163` |
| `scripts/reviewer_experiments/protocol/manifest.schema.json` | 43,468 | `e3506dcabb867c87bda6aa5fddfc9d3987689c16792d31d5ea730851445354c7` |
| `scripts/reviewer_experiments/protocol/tests/test_g14_deferral_release_valve.py` | 11,194 | `5837daa296a2a97519e26235e14b145fc32cadd8ccfebfb7dc8202efc33ee06b` |

Verification before this audit commit:

- G14 plus G12 directed runtime/manifest tests: 18/18 pass;
- complete reviewer-protocol regression: 242/242 pass in 952.70 seconds;
- Python compilation, Black formatting, JSON parsing, and Git whitespace
  checks: pass;
- generic manifest validation and static JSON Schema validation: pass;
- independent product, pairing, unbound-input, file, runtime, and root-tree
  checks: pass.

During zero-result construction, fail-closed tests first exposed that the new
G14 seed policy had not yet been added to the generic validator and then to
the static JSON Schema enum. Both omissions were corrected before manifest
creation; the final complete regression and sole manifest were produced only
after those corrections. No performance outcome existed during either fix.

## 5. Authorization boundary

After this audit and the sole unbound manifest are committed, exactly 15 base
tape captures are authorized: low/middle/high x D106--D110. Each capture must
use the bound workload specification and retain the first QC-valid tape.
Scientific content cannot trigger recapture, seed replacement, omission, or
down-weighting. C0 and G14 will later reuse the identical tape within each
load/seed pair.

Offline-reference construction remains blocked until all 15 tapes, hashes,
event counts, rates, pairings, and capture receipts are independently audited
and committed. Online execution, analyzer construction, strong baselines,
confirmation, formal replay, figures, and manuscript claims remain blocked.
