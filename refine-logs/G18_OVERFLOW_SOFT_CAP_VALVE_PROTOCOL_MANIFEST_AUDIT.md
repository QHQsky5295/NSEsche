# G18 Overflow Soft-Cap Valve Zero-Result Protocol and Manifest Audit

Date: 2026-09-05 (Asia/Shanghai)

Protocol commit: `5b224f45ff9becd2bee7d8037ddc3ad0cb740cd4`

Runtime source commit: `f3a1e0950c5a53a0ab614edacc2838703c2a9d81`

Status: `zero_result_protocol_frozen_d116_d120_tape_capture_authorized`

## 1. Exact development product

The frozen manifest is
`runs/tscv1_g18_overflow_soft_cap_valve_d116_d120_f3a1e09_20260905/g18.manifest.json`.
It contains exactly the preregistered initial G18 product:

- C0 `ready_order` and candidate
  `ready_global_overflow_soft_cap_release_valve`, both under `sche_nash`;
- homogeneous 20-node low, middle, and high loads using the unchanged
  submission-v1 workload profiles;
- the five fresh fixed development seeds D116--D120, disjoint from G12's
  D101--D105, G14's D106--D110, and G16's D111--D115 banks;
- 30 unique future online run specifications, 15 load/seed tape identities,
  and 30 operational-mode-specific offline-reference dependencies.

Within every load/seed group, C0 and G18 share one workload specification hash
and one tape key. Their reference keys differ. No strong baseline,
confirmation seed, formal seed, other topology, other node count, extra
candidate, or result-conditioned extension appears. The manifest is explicitly
non-formal.

## 2. Frozen mechanism and gates

For the complete global feasible-ready legacy sequence `A_t`, write
`F=|A_t|`, let `N>0` be configured physical-node count, and define the checked
integer cap `C=ceil(5N/4)=(5N+3)//4`. Starting with the previous-overflow valve
bit closed, G18 admits the first `C` players only when the current window is a
first overflow and `F>C`. At/below `C`, on every adjacent persistent-overflow
window, and on every non-overflow window it admits the complete feasible-ready
sequence. The only cross-window transition is `v_(t+1)=1[F>N]`.

The rule contains no cap search, fitted multiplier, fixed-threshold classifier,
request cohort, frontier/pre-ready player, remaining-work key, warm override,
utility guard, load/seed/outcome branch, or baseline expert. G18 binds
operational schema 13, reference-key schema 14, and reference tag 19; C0
retains tag 1. The displayed paper Eqs. (1)--(20), strict Eq. (15), Eq. (19),
QPR, and offline-reference definitions remain unchanged on the admitted finite
player set.

All 30 first QC-valid rows must be retained. At every load, candidate mean
throughput and mean QPR must strictly exceed C0. At least one pair must be a
joint strict win and at least four of five pairs must be joint nonlosses. No
per-seed throughput or QPR ratio may be below 0.80. Every leave-one-seed-out
mean difference must be nonnegative, with at least four of five strictly
positive values per metric and load. Mean completion may not fall below C0,
mean request-latency ratio may not exceed 1.05, and mean placement-policy wall
time may not exceed 1.50x C0.

Activation additionally requires at least one material soft-cap deferral seed
at each load, at least three at/below-cap first-overflow release runs across at
least two loads, at least three persistent-overflow release runs across at
least two loads, and a longest positive-deferral episode of at most one.
Readiness, feasibility, legacy-order, prefix, bound, soft-cap-arithmetic,
admission-rule, state-transition, and dispatch-set violations must all be zero.
Strict-PNE/reference/runtime-dispatch coverage remains mandatory. Passing every
condition authorizes only a separately audited strong-baseline addendum;
failure closes G18 before confirmation. Gates cannot be edited after outcome
exposure.

## 3. Runtime and manifest receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g18_overflow_soft_cap_impl/release/serverless_sim.exe` | 4,918,272 | `aaa0980cf451a88f7b3652f55c3e8c624af2a71b6312c40f4b19aa83bf6af713` |
| `runs/tscv1_g18_overflow_soft_cap_valve_d116_d120_f3a1e09_20260905/g18.manifest.json` | 735,302 | `b27d71567eda59a6e506834e750c2ad1e332b8e39bad879a1597cb39fcb1af42` |

The manifest's embedded canonical object hash is
`533447624b51750ae1a1186780080766c4836f9fdac5b05f1fd45520e17efcd2`.
At freeze time the run root contains exactly this one file and zero
subdirectories. All 30 tape hashes and event counts and all 30 reference
hashes, byte/line counts, completion markers, sequence hashes, receipts, and
process observations are null. No request completion, throughput, latency,
cost, QPR, scheduler outcome, or candidate ranking exists.

## 4. Protocol source receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 31,931 | `887c438679b48632dfc870e46f07206500831e213c0d19123196195b815a9d59` |
| `scripts/reviewer_experiments/protocol/g18_overflow_soft_cap_valve.py` | 11,569 | `56f97586c742ac3f9288f0dc098fcb7c0c01ee86166c5872a124d658d6c07d84` |
| `scripts/reviewer_experiments/protocol/schema.py` | 269,953 | `681d6b1c6f031d98d116fe46c40ebbbd6afd53893a55121f5fb1bb7f256dc750` |
| `scripts/reviewer_experiments/protocol/manifest.schema.json` | 43,627 | `54e4dc24d696d567614713c743bc8057724f7471162e5efc43ea7aebe45da0f7` |
| `scripts/reviewer_experiments/protocol/tests/test_g18_overflow_soft_cap_release_valve.py` | 12,229 | `9646ff5ef8c899ba65dab15ccb4b7de462075903d715ffc46ae759dec0e6fea0` |

Verification before this audit commit:

- focused G18 runtime/manifest tests: 9/9 passed;
- directed G18 plus legacy G16/G14/G12 tests: 36/36 passed;
- complete reviewer-protocol regression: 260/260 passed in 757.884 seconds;
- complete analysis regression: 181/181 passed in 83.912 seconds;
- Python compilation, Black formatting, JSON parsing, and Git whitespace
  checks passed;
- generic manifest validation, G18 exact validation, and static JSON Schema
  validation passed; and
- independent product, run-order, pairing, unbound-input, file, runtime, and
  root-tree checks passed.

The manifest was created exactly once, after protocol source commit `5b224f4`
and an independent recheck of the protected binary's size, SHA-256, and source
commit. Protocol construction did not execute the simulator.

## 5. Authorization boundary

After this audit and the sole unbound manifest are committed, exactly 15 base
tape captures are authorized: low/middle/high x D116--D120. Each capture must
use the bound workload specification and retain the first QC-valid tape.
Scientific content cannot trigger recapture, seed replacement, omission,
down-weighting, or a change to the fixed soft-cap rule.

Offline-reference construction remains blocked until all 15 tapes, hashes,
event counts, rates, pairings, and capture receipts are independently audited
and committed. Online execution, analyzer construction, strong baselines,
confirmation, formal replay, figures, and manuscript claims remain blocked.
