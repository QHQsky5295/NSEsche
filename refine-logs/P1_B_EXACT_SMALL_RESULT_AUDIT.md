# P1-B Exact-Small Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: `complete_integrity_pass_accurate_reference_p2_authorized`

Population: 300 preregistered constructed games; three nodes; 100 games at
each of 4, 6, and 8 players; deterministic seed `NSE-P1-EXACT-V2`

Output root: `runs/tscv1_p1_exact_small_v2_20260904/`

## 1. Execution and integrity result

The generator, primary exhaustive enumerator, and independent verifier were
each invoked exactly once after their source hashes and output root had been
frozen. The verifier passed every hard gate: exact 100/100/100 coverage,
finite results, independent exact-result agreement, the weighted-potential
identity, at least one pure-strategy Nash equilibrium (PNE) in every state,
and no offline-reference estimate above the exact optimum. It reimplemented
the raw-dictionary utility, welfare, PNE, and potential calculations and did
not import the primary solver.

The enumerated population contains 81, 729, and 6,561 feasible assignments
per state at 4, 6, and 8 players, respectively: 737,100 assignments in total
before unilateral-deviation checks. The primary and independent paths both
covered the complete population; no state, seed, or result was excluded.

Frozen source SHA-256 values recorded by the execution are:

| Component | SHA-256 |
|---|---|
| V2 generator | `36d663340a59f932c2c854cbab4efd4efff52246b72963fc2d9e3831918013cf` |
| primary enumerator | `4437ee0a3fe66cdbdcfda7b93537ce038c38d05b0b02c39133b06c4af4e164c6` |
| independent verifier | `5f062f2f6a84c81f11aa9dde7a0766932ff47c0e7b7420b217dd2185567646dd` |

## 2. Raw result table

All quantities below retain all 100 states in each player-count stratum.
Percentiles use the frozen linear-interpolation definition. Normalized
shortfall is `(exact optimum - estimate) / exact optimum`, clipped at zero
only within floating-point tolerance.

| Players | States | Assignments/state | PNE count, median [min, max] | Exact PoA, median / p95 / max | Reference exact hits | Reference shortfall, median / p95 / max |
|---:|---:|---:|---:|---:|---:|---:|
| 4 | 100 | 81 | 4 [1, 12] | 1.001397 / 1.008280 / 1.013022 | 97 | 0 / approximately 0 / 0.001517 |
| 6 | 100 | 729 | 12 [1, 90] | 1.002785 / 1.011619 / 1.018114 | 66 | 0 / 0.000813 / 0.001320 |
| 8 | 100 | 6,561 | 44 [1, 466] | 1.004296 / 1.010764 / 1.013954 | 29 | 0.000152 / 0.001482 / 0.002008 |
| **All** | **300** | — | **8 [1, 466]** | **1.002848 / 1.010731 / 1.018114** | **192** | **0 / 0.000935 / 0.002008** |

The exact PoA is mathematically applicable in all 300 states. Thirty-one
states have PoA 1 within `1e-12`. The maximum, 1.0181139000, occurs at
`p06-s006`; its exact optimum is 88.0546927327 and worst-PNE welfare is
86.4880567198.

The deterministic `ready_order` trajectory terminated as `stable` and at a
PNE in 300/300 states, with no inner cap or oscillation. Inner rounds have
median 1, p95 2, and maximum 3; assignment moves have median 0, p95 1, and
maximum 4. Its normalized shortfall from the exact social optimum has median
0.001504, p95 0.007560, and maximum 0.013309. It reaches an exact optimum in
53 states and the worst PNE in 120 states. These trajectory results are kept
separate from worst-equilibrium PoA.

The offline reference estimate exactly hits the optimum in 192/300 states
(64.0%). Its median shortfall is zero, p95 is 0.0009349635 (0.0935%), and
maximum is 0.0020076707 (0.2008%, at `p08-s034`). It therefore satisfies the
preregistered highest label, `accurate_small_state_reference`, by a wide
margin (required median at most 5% and p95 at most 20%). Primary exact
enumeration took 60.639 s in aggregate and reference estimation 0.681 s;
these CPU-path measurements are descriptive and exclude independent-verifier
wall time.

## 3. Findings and claim implications

1. **Observation:** every constructed fixed-snapshot game has at least one
   PNE, every potential-identity check passes (maximum floating-point residual
   below `4.0e-15`), and every `ready_order` trajectory reaches a PNE.
   **Interpretation:** this gives exact finite-state support for the proposed
   weighted-potential mechanism and strong empirical support for the
   deterministic update path on the preregistered small-state population.
   **Implication:** the revision may present the potential argument together
   with exhaustive 4/6/8-player validation, but must not claim that 300 samples
   prove unconditional convergence of the runtime's changing outer loop.
2. **Observation:** worst-PNE PoA is close to one in this population, with
   median 1.002848, p95 1.010731, and maximum 1.018114.
   **Interpretation:** equilibrium inefficiency is small for the frozen game
   generator. **Implication:** report the entire distribution and state-space
   definition; do not elevate the observed maximum into a universal analytic
   PoA bound.
3. **Observation:** the offline estimator has zero median error, 0.0935% p95
   error, and never exceeds the exact optimum.
   **Interpretation:** it is highly accurate on these exact-small games while
   P1-A still observes a 2.558% below-current incidence in large runtime
   states. **Implication:** call it an `offline reference estimate`, validate
   its small-state accuracy explicitly, and retain the large-state limitation;
   do not call all large-state table values exact optima.
4. **Observation:** `ready_order` is not always socially optimal and equals
   the worst PNE in 120 states.
   **Interpretation:** equilibrium existence and trajectory convergence are
   distinct from optimal equilibrium selection. **Implication:** keep
   `ready_order` welfare, worst-PNE PoA, and reference accuracy as separate
   reported quantities.

## 4. Artifact identities

| Artifact | Rows / bytes | SHA-256 |
|---|---:|---|
| `exact_games_v2.jsonl` | 300 / 1,046,420 | `740769520e566eccc6218c071135e156336130315bb1188c30d63e332515f36f` |
| `exact_results_v2.jsonl` | 300 / 527,017 | `5fa3ea977d0f7373c88a89772b1922dedca422c5a1ad0fb5f84b3d0d92a0004f` |
| `exact_state_rows_v2.csv` | 300 / 76,561 | `315948819e9d6ba6dda57bf0cfc718ee79ad0de357c7b9ca1592e106bb96e5f8` |
| `exact_summary_v2.json` | 771 bytes | `14841b9316fd35e1caec7605ca1ea421cba556a860e4933e9d553614413a0102` |
| `exact_verification_v2.json` | 982 bytes | `c05445e85ecc05a2598b27c7c7cb397abdfcfd6ee5ed747ec8b603cdcfeee90b` |

The recomputed hashes match the independent verification receipt for every
artifact covered by that receipt. The verification receipt itself reports
`status: pass`, `verified_state_count: 300`, and all six hard gates as true.

## 5. Gate decision

P1-B passes every hard integrity gate and receives the non-weak highest
reference-quality label. Together with the completed P1-A gate, P1 is closed.
P2 is authorized to proceed only in the V4 order and through a new frozen
protocol: homogeneous middle load first, followed by homogeneous high load.
This authorization does not permit value-conditioned seed selection,
post-result parameter tuning, or simultaneous execution of later blocks.

