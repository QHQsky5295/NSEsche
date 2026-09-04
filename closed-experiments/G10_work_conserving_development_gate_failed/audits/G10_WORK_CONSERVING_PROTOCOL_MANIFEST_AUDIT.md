# G10 Work-Conserving Zero-Result Protocol and Manifest Audit

Date: 2026-09-04 (Asia/Shanghai)  
Protocol commit: `a3a31d5d7a08a573d245556a201089c0fc4885e7`  
Runtime source commit: `ab0ae94f0a8314db348078040a49dfe59281653e`  
Status: `zero_result_protocol_frozen_d96_d100_tape_capture_authorized`

## 1. Exact development product

The frozen manifest is
`runs/tscv1_g10_work_conserving_d96_d100_ab0ae94_20260904/g10.unbound.json`.
It contains exactly the initial G10 product:

- three NSESche operational identities: C0 `ready_order`, C1
  `ready_remaining_work`, and C2
  `ready_remaining_work_bounded_frontier`;
- three homogeneous 20-node loads: low, middle, and high;
- five fresh, fixed development seeds: D96, D97, D98, D99, and D100;
- 45 online run specifications, 15 load/seed tape identities, and 45 distinct
  candidate-specific offline-reference dependencies.

For every load/seed pair the three arms have the same workload specification
hash and tape key. Their reference keys are all different because C0/C1/C2
have distinct operational identities and reference-key tags 1/14/15. There is
no strong baseline, confirmation seed, Q61--Q80 seed, topology variant, node-
count variant, or extra run in this product.

## 2. Frozen gates and selection

Generic schema validation independently reconstructs the full
`3 modes x 3 loads x 5 seeds` Cartesian product and rejects any missing,
duplicate, substituted, or extra row. It also rejects cross-mode reference
reuse, tape mismatch, runtime drift, formula/strict-Eq.-(15) drift, a changed
candidate rule, any load-specific or baseline-expert branch, a weakened gate,
or early inclusion of a strong baseline.

For each candidate, all five QC-valid seeds must be used. At every load, mean
throughput and mean QPR ratios must both be strictly above 1.0; throughput,
QPR, and joint paired wins must each be at least 3/5; every per-seed metric
ratio must be at least 0.80; every leave-one-seed-out mean difference must be
positive; mean completion ratio cannot fall below C0; mean request latency
must fall below C0; and mean policy wall time is capped at 1.50x C0. C1 must
match C0's ready set. C2 must have zero ready omission, frontier-bound,
one-hop, and dispatch-class violations, plus positive frontier admission in at
least 3/5 seeds at each load. Strict-PNE, reference, runtime, and complete-
dispatch checks are mandatory.

If both candidates pass, the frozen order is maximum minimum of the six
primary ratios, then maximum mean of those ratios, then joint paired wins,
then simpler C1 on an exact tie. If neither passes, G10 closes as negative
development evidence. These rules cannot be edited after outcome exposure.

## 3. Runtime and manifest receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g10_work_conserving_impl/release/serverless_sim.exe` | 4,869,120 | `39d56c1bf332635a51962a061c3e001c04a5eab23ab2e54ffb27175c3adc12e8` |
| `runs/tscv1_g10_work_conserving_d96_d100_ab0ae94_20260904/g10.unbound.json` | 1,089,366 | `e1811128a22c376ed77e4853059f92b360d43629df4adeb7967082ce742e3e77` |

The manifest's embedded canonical object hash is
`4847961a95ec22283b142ce074ca3456fb689a1e28ea4c90e9f62ccb22574b04`.
At freeze time the run root contains exactly this one file. It has no
`stages/` or `online/` directory and therefore contains no tape, reference,
request completion, throughput, latency, cost, QPR, or scheduler outcome.

## 4. Protocol source receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/protocol/g10_work_conserving.py` | 10,301 | `58ad970b3d26e8790f86fd0b11cf6d1f01008ac9b89570a460e08e3fed05f6b6` |
| `scripts/reviewer_experiments/protocol/schema.py` | 223,346 | `532388a72ac5d242faf76391acedc42da6f1948d3396745689884be46fd5d717` |
| `scripts/reviewer_experiments/protocol/manifest.schema.json` | 43,312 | `1799cf31de1108e51c162ab51a817455a0ba0a5e5dd382258fbc5b459532e3b3` |
| `scripts/reviewer_experiments/protocol/tests/test_g10_work_conserving.py` | 9,067 | `3588c3ff953e9de57021432114fc1dd061d87ab59cb91309d2cf2bfcd4b4d373` |

The older structural seed regex accepted only two digits. It was extended to
two or three digits solely so the preregistered D100 label is representable.
G10-specific validation still requires the exact D96--D100 set. The static
JSON Schema now has a direct test proving that the real 45-run shape containing
D100 validates.

Verification before this audit commit:

- G10 runtime/manifest directed tests: 9/9 pass;
- combined G10/G9 directed protocol tests: 14/14 pass;
- complete reviewer-protocol regression: 224/224 pass in 962.683 seconds;
- Python compilation and Black formatting: pass;
- static JSON Schema validation of the G10 manifest shape: pass;
- actual manifest generic validation and independent file/runtime hashing:
  pass;
- `git diff --check`: pass.

## 5. Authorization boundary

After this audit and the single manifest are committed, exactly 15 base tape
captures are authorized: one for each low/middle/high x D96--D100 load/seed
pair. Capture must use the bound workload specification and retain the first
QC-valid tape; scientific content cannot trigger recapture or seed
replacement. All three NSESche arms will later reuse that same tape.

Offline-reference construction remains blocked until all 15 tape artifacts,
hashes, event counts, and pairings are independently audited and committed.
Online execution, analyzer selection, strong baselines, confirmation, formal
replay, figures, and manuscript performance claims remain blocked.

