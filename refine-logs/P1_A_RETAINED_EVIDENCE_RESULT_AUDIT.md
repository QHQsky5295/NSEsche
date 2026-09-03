# P1-A Retained Evidence Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: `complete_p1a_integrity_pass_p1b_authorized`

Input population: all 20 canonical homogeneous-low NSESche `ready_order`
Q61--Q80 runs and all 120 frozen offline-reference builds

Output root: `runs/tscv1_p1_retained_evidence_98f822c_20260904/`

## 1. Integrity result

The successful invocation retained every preregistered seed and passed all
structural gates. It verified 20 unique run-spec hashes, exact ready-manifest
membership/document/file hashes, the preserved `98f822cf` executable hash, all
compressed and decompressed online stream identities, reference dependencies,
the strict Eq. (15)/`ready_order` runtime contract, and Eq. (16)/(19)/(20)
feedback traces. It also verified the exact 2 topologies x 3 loads x 20 seeds
reference catalog with table, receipt, and process hashes.

The two preceding validator attempts are separately recorded as
fail-before-output implementation corrections. Neither created the registered
output root or exposed a scientific table. The successful evidence binds
analyzer SHA-256
`6d87a7148d1c70d6ab696986fae885aea75f148e8deaca47e5e71f0329345591`.

## 2. Raw result table

Seed is the inferential unit (`n=20`). Intervals below are the frozen 10,000-
resample BCa 95% intervals; pooled event fractions retain their exact
numerators and denominators.

| Quantity | Result |
|---|---:|
| active / no-player windows | 19,509 / 491 |
| inner stable | 19,509 / 19,509 (100.000%) |
| outer stable | 19,001 / 19,509 (97.396% pooled); seed mean 97.411%, BCa [95.947%, 98.498%] |
| nonconverged by frozen definition | 508 / 19,509 (2.604% pooled); seed mean 2.589%, BCa [1.526%, 4.051%] |
| inner/outer limit hit | 9 / 19,509 (0.0461% pooled); seed mean 0.0459%, BCa [0.0204%, 0.0817%] |
| oscillation windows | 0 / 19,509 |
| feedback-eligible reference windows | 19,010 / 19,509 (97.442% pooled) |
| applied / eligible feedback trace rounds | 8,913 / 27,923 (31.920% pooled); seed mean 31.284%, BCa [27.887%, 34.004%] |
| positive online references | 19,509 / 19,509 |
| missing / unavailable / zero / negative online references | 0 / 0 / 0 / 0 |
| reference below current / search-suboptimal | 499 / 19,509 (2.558% pooled); seed mean 2.543%, BCa approximately [1.46%, 4.00%] |
| active-window NSESche solve time | seed mean 27.435 us, BCa [24.484, 30.509] us |
| offline-table lookup time | seed mean 14.202 us, BCa [12.407, 16.103] us |
| policy wall time, all windows | seed mean 0.348 ms, BCa [0.265, 0.527] ms |
| complete scheduler wall time, all windows | seed mean 0.411 ms, BCa [0.326, 0.594] ms |
| process-tree CPU / duration | seed means 10.919 s / 12.313 s |
| peak process-tree RSS | seed mean 237.74 MB (decimal), BCa [235.78, 239.71] MB |

The exact active termination counts are 10,097 `social_gap_zero`, 8,904
`outer_assignment_unchanged`, 499
`social_reference_below_current_welfare`, and 9 `outer_iteration_limit`.
Thus the 508 nonconverged windows are completely accounted for by 499
below-current heuristic references and nine outer-round caps. All inner games
were stable and no logged oscillation occurred.

The 120 reference tables contain 117,138 state rows: 117,123 positive and 15
nonpositive. Their aggregate build wall time was 1,794.156 s, process-tree CPU
1,644.844 s, maximum peak RSS 269.009 MB, and total table size 30,694,465
bytes. Nonpositive rows remain retained and are not treated as an integrity
failure.

## 3. Findings and claim implications

1. **Observation:** the inner fixed-snapshot game stabilized in every active
   window and had no observed oscillation. **Interpretation:** this is strong
   empirical support for the strict best-response inner mechanism under the
   evaluated homogeneous-low workload. **Implication:** the manuscript may
   report empirical inner stability, conditional on the fixed snapshot and
   four-round implementation. It must not turn this into an unconditional
   proof of the whole double loop.
2. **Observation:** outer stability was 97.396%, not 100%, and nine windows hit
   the outer limit. **Interpretation:** bounded runtime and reference-feedback
   eligibility matter. **Implication:** report termination categories and the
   cap explicitly; do not claim universal convergence.
3. **Observation:** every active window found a positive offline-table value,
   but 499 values were below the policy's current welfare. **Interpretation:**
   the offline search is a deterministic heuristic estimate, not an exact
   large-state optimum. **Implication:** use `offline reference estimate` and
   report the 2.558% search-suboptimal incidence; exact error is deferred to
   the preregistered small-state comparison.
4. **Observation:** online solve and lookup costs are tens of microseconds,
   while one-time reference construction consumed about 29.9 wall minutes
   across 120 tables. **Interpretation:** online reuse is cheap relative to
   offline construction. **Implication:** separate offline build cost, online
   lookup, policy boundary, and process-level resources rather than presenting
   one ambiguous overhead number.

## 4. Artifact identities

| Artifact | SHA-256 |
|---|---|
| `p1_retained_seed_rows.csv` | `4512737454a06606fc0c20ae2f003e57e2d41373987a1048b09a07f84fb1ac6d` |
| `p1_retained_window_counts.csv` | `dbf255070d348e0dd9c14a7e437c4bb9d919d07d0d9ca8ac160c875519ed3b7d` |
| `p1_reference_build_rows.csv` | `67877924542034b2bc53b3ced4beb74563ca75d573a8baf12ca835bd282f0f07` |
| `p1_retained_evidence.json` | `aa7b1f415946cd7d703ae5d61e0892dadd6d4e411409443b97c7698f77312067` |

CSV row counts are exactly 20 seed rows, 126 stratum/dimension/count rows, and
120 reference-build rows. All three CSV hashes match the hashes embedded in
the evidence JSON.

## 5. Gate decision

P1-A passes its integrity gate; no favorable convergence rate was required.
P1-B generation, exact enumeration, and independent verification are now
authorized exactly once under their already frozen source hashes and output
root. P2 remains blocked until P1-B passes every hard gate and receives a
non-weak reference-quality label.
