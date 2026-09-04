# G12 Global-Ready Admission Zero-Result Protocol and Manifest Audit

Date: 2026-09-04 (Asia/Shanghai)  
Protocol commit: `9b484155594e7cc03ab0b8591037c9165bbec55d`  
Runtime source commit: `c4e31a99b62012bf0fbdd48f7a6a0010d7484801`  
Status: `zero_result_protocol_frozen_d101_d105_tape_capture_authorized`

## 1. Exact development product

The frozen manifest is
`runs/tscv1_g12_global_ready_admission_d101_d105_c4e31a9_20260904/g12.unbound.json`.
It contains exactly the preregistered initial G12 product:

- C0 `ready_order` and candidate
  `ready_global_player_admission_n`, both under `sche_nash`;
- homogeneous 20-node low, middle, and high loads using the unchanged
  submission-v1 workload profiles;
- the five fresh fixed development seeds D101--D105;
- 30 unique online run specifications, 15 load/seed tape identities, and 30
  operational-mode-specific offline-reference dependencies.

Within every load/seed group, C0 and G12 share one workload specification hash
and one tape key. Their reference keys differ. No strong baseline,
confirmation seed, formal seed, other topology, other node count, or extra
candidate appears in the product.

## 2. Frozen mechanism and gates

G12 collects the complete global dependency-ready, not-yet-placed C0 sequence,
applies the unchanged individual feasibility filter, and admits the exact
first `min(feasible_ready_players, configured_node_count)` players in the
unchanged arrival/request/topological/function order. Deferred feasible
players remain unplaced for the next scheduling window. The manifest rejects
a request cohort, frontier/pre-ready player, remaining-work key, warm
override, utility-regret guard, load/seed/outcome branch, baseline expert, or
tunable multiplier.

The candidate is bound to operational schema 10, reference-key schema 11, and
reference tag 16; C0 retains tag 1. The displayed paper equations, strict Eq.
(15), Eq. (19), QPR, and offline-reference definitions remain unchanged on
the admitted finite player set.

All 30 first QC-valid rows must be retained. At each load, candidate mean
throughput and QPR must both exceed C0; throughput, QPR, and joint paired wins
must each be at least 3/5; no per-seed throughput or QPR ratio may be below
0.80; and every leave-one-seed-out mean difference must be positive for both
metrics. Mean completion ratio may not fall below C0, mean request latency
must be lower, and mean placement-policy wall time may not exceed 1.50x C0.

Admission must activate in at least 3/5 seeds per load and every activated run
must defer feasible players. Readiness, feasibility, legacy-order, prefix,
bound, and dispatch-set violations must all be zero. Strict-PNE,
offline-reference, runtime-identity, and dispatch checks remain mandatory.
Passing requires every gate; it authorizes only a separately preregistered
strong-baseline addendum. Failure closes G12 before confirmation. Gates cannot
be edited after outcome exposure.

## 3. Runtime and manifest receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g12_global_ready_impl/release/serverless_sim.exe` | 4,871,168 | `35e7e3d22b04baa232177394d487603ddc545ffcc461992ac1aa7c7ae2044f27` |
| `runs/tscv1_g12_global_ready_admission_d101_d105_c4e31a9_20260904/g12.unbound.json` | 731,469 | `cb14ab22755c878bdf4c93e856bbca8e884f9d856d4a64d4e021943ee500fc7d` |

The manifest's embedded canonical object hash is
`811f62e6d055883ae845467c0b8fcf590f3bc6f532faccbf9e03e82b935d6fee`.
At freeze time the run root contains exactly this one file and zero
subdirectories. Tape/reference hashes, event/line counts, completion markers,
and online artifacts are all absent or null. No request completion,
throughput, latency, cost, QPR, scheduler outcome, or candidate ranking exists.

## 4. Protocol source receipts

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 23,303 | `0150696c25dc176b559dfd21dc04f6eeca42cbfef54b24cc5165a0238762bf98` |
| `scripts/reviewer_experiments/protocol/g12_global_ready_admission.py` | 10,116 | `9c26e6330599c3fed0b7169f25a4d715361ab353626f71ec132e8e40e457b797` |
| `scripts/reviewer_experiments/protocol/schema.py` | 233,684 | `0d067aaf146adc35795e3ceef8cd8fe42425b2372bdb2ccccddbee006834011a` |
| `scripts/reviewer_experiments/protocol/manifest.schema.json` | 43,390 | `7f506a73e6ce58a4df89d9260725bc708fcba2e224f19a66ac404471508490f5` |
| `scripts/reviewer_experiments/protocol/tests/test_g12_global_ready_admission.py` | 8,617 | `dc86aedf546f506429f90ec058f366b7fd1f3e567d45abb588e1ae4009f3994e` |

Verification before this audit commit:

- G12 directed runtime/manifest tests: 8/8 pass;
- combined G9/G10/G12 directed protocol tests: 23/23 pass;
- complete reviewer-protocol regression: 232/232 pass in 902.800 seconds;
- Python compilation, Black formatting, and Git whitespace checks: pass;
- generic manifest validation and static JSON Schema validation: pass;
- independent product, pairing, unbound-input, file, runtime, and root-tree
  checks: pass.

## 5. Authorization boundary

After this audit and the sole unbound manifest are committed, exactly 15 base
tape captures are authorized: low/middle/high x D101--D105. Each capture must
use the bound workload specification and retain the first QC-valid tape.
Scientific content cannot trigger recapture, seed replacement, omission, or
down-weighting. C0 and G12 will later reuse the identical tape within each
load/seed pair.

Offline-reference construction remains blocked until all 15 tapes, hashes,
event counts, rates, pairings, and capture receipts are independently audited
and committed. Online execution, analyzer construction, strong baselines,
confirmation, formal replay, figures, and manuscript claims remain blocked.
