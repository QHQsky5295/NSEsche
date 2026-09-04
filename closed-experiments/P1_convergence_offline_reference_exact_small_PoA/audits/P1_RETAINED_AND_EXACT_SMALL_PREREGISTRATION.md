# P1 Retained-Log and Exact-Small Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Status: frozen before P1 analyzer implementation, exact-small V2 implementation, result generation, or exposure of any exact optimum

Parent decision: `P0_CLAIM_RUNTIME_AUDIT_RESULT.md` status `complete_p1_retained_log_and_exact_small_preregistration_authorized`

## 1. Claims and anti-claims

P1 tests only two claims:

1. **Conditional-equilibrium claim:** under a fixed snapshot, fixed feasible candidate sets, fixed adjusted prices, and strict utility-improving moves, the NSESche inner game has the stated weighted-potential structure; the budgeted implementation's actual stable/limit/oscillation behavior is measured rather than assumed.
2. **Reference claim:** the offline reference is a state/profile-specific deterministic heuristic estimate whose coverage, computation cost, online lookup cost, and error against exact optima on constructed small states can be quantified.

P1 explicitly rules out two anti-claims: finite/bounded state alone proves convergence of the entire double loop, and simulated annealing returns an exact large-state optimum.

## 2. Frozen inputs

| Input | SHA-256 / identity |
|---|---|
| P0 result audit | `bff6f684621fc4a75fb92284342114b9e449bbba965c14e4b998383692cad694` |
| P0 runtime/telemetry audit | `568bb1c395fcad2501827806b07123169f11603a8f892ef69a508a3a13c0fc04` |
| Claim map | `afa265744bf8b2fec0f3dccc3cf3e0fee8203a7b0ddd8dff8cd2fff3446c5399` |
| Reviewer-evidence matrix | `a792c500d5b2c525fc0448349557fba84f19f5c692f3f84e9c2fc814d71d273d` |
| Formal homogeneous-low result audit | `9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16` |
| Formal input/reference freeze | `fcebed1a0ca25d9be2eea3b41e73aab7ee7daf4af3d98f5dbf1745f3810787f3` |
| Q61–Q80 ready manifest | file `d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a`; document `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b` |
| Formal runtime | source `98f822cf2dcb878024a2ca39cc56533895ea692c`; binary `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4` |
| Formal run root | `runs/tscv1_g1_formal_q61_q80_98f822c_20260903` |
| Preregistration HEAD | `f4d3716418aa1661a2f18f7776b31d4c19d76579` |

The exact retained online population is every canonical run matching experiment E1, homogeneous topology, 20 nodes, low load, method `sche_nash`, variant `full`, refinement `ready_order`, and seeds exactly Q61–Q80. It must contain exactly 20 unique run IDs and one run per seed. No value-dependent inclusion is allowed.

The all-cell offline-reference population is the already frozen 120-entry reference catalog: 2 topologies × 3 loads × Q61–Q80. No reference is rebuilt in P1.

## 3. Block A — retained-log convergence, reference, and overhead

### 3.1 Structural gate

The analyzer must independently revalidate for all 20 runs:

- canonical QC, binary hash, run-spec uniqueness, exact seed coverage, and ready-manifest membership;
- gzip artifact SHA-256 against each audit manifest;
- exactly one run-config, 1,000 window records, one run-summary, 1,000 scheduler-window records, and one request stream;
- `strict_best_response=true`, `operational_refinement=ready_order`, `stream_contract_ready=true`, reference dependency existence/hash, and no malformed Eq. (16)/(19)/(20) trace;
- all 120 reference catalog rows and their table/process receipts match the frozen catalog.

Any structural failure stops the analysis without a partial scientific table.

### 3.2 Frozen definitions

- `active_window`: `decision.request_function_players > 0`.
- `no_player_window`: the same field equals zero; it is never counted as non-converged.
- `inner_stable`: logged `solver.inner_stable=true` on an active window.
- `outer_fixed`: logged `solver.outer_stable=true` on an active window.
- `nonconverged`: active and either inner not stable or outer not stable.
- `limit_hit`: active and either inner/outer limit flag is true.
- `oscillation`: active and logged oscillations greater than zero.
- `feedback_applied`: sum of `outer_feedback_trace[].feedback_applied=true` divided by eligible trace rounds; windows without eligible reference remain in the coverage denominator and are reported separately.
- online reference use is classified by source and by positive/zero/negative/missing/unavailable/below-current/search-suboptimal flags; none is discarded.
- policy/full/welfare timing follows `scheduler_windows.timing_scope`; solve/reference timing follows `nash_metrics.overhead`; process-tree CPU/RSS follows `process_observation.json`.

### 3.3 Outputs and statistics

Required products under `runs/tscv1_p1_retained_evidence_98f822c_20260904/`:

1. `p1_retained_seed_rows.csv`: one row per Q61–Q80 seed, including all numerators/denominators and summary metrics;
2. `p1_retained_window_counts.csv`: termination/reference-source counts by seed and active/no-player stratum;
3. `p1_reference_build_rows.csv`: exactly 120 build rows with load/topology/seed, state-row counts, positive/nonpositive counts, build wall/CPU/RSS, and table bytes;
4. `p1_retained_evidence.json`: definitions, integrity receipts, seed-level summaries, pooled fractions, and artifact hashes.

The seed is the inferential unit (`n=20`). For each continuous or per-seed rate metric report all 20 points, mean, sample SD, median, and deterministic BCa 95% confidence interval with 10,000 resamples and seed string `NSE-P1-BCA-V1|metric`. Pooled event fractions additionally report exact numerators and denominators. No comparator hypothesis test is performed in P1-A.

Timing metrics are reported in their observed clock scope. Zero thread-CPU readings remain zero and are labelled timer-resolution-limited; process-tree CPU is not substituted into a window-level field.

### 3.4 Interpretation gate

Convergence rates are descriptive and cannot trigger seed deletion or a rerun. A low fixed-point rate narrows the paper claim. P1-A passes the P2 integrity gate if and only if all 20 streams and all 120 references pass structural validation and the metric definitions can be reproduced from raw logs. No favorable convergence percentage is required for integrity.

## 4. Block B — 300 constructed exact-small games

### 4.1 Population frozen before optimum exposure

- Schema: `NSE_EXACT_GAME_V2` and `NSE_EXACT_POA_REFERENCE_RESULT_V2`.
- Generator seed: `NSE-P1-EXACT-V2`.
- Exactly 3 nodes.
- Player counts: exactly 4, 6, and 8.
- Exactly 100 states per player count, indexed 000–099; total 300.
- Each player has all three candidate nodes; all function containers are pre-provisioned, so every one of the `3^players` assignments is feasible. This isolates the finite placement game from HPA/admission effects.
- Function profiles: deterministic draws from the frozen seed; normalized CPU and memory independently uniform on `[0.05,1.0]`; `h_ri=2*sqrt(c*m)/(c+m)`; DAG nodes uniformly integer 2–10; `h_fc=tanh(log(N_DAG)/1.5)`; `h_nd=sqrt(h_ri*h_fc)`; `h_pi=((31c+37m) mod 100)/100`.
- Each state uses one shared quality weight: 0.5 for state indices 000–049 and 0.6 for 050–099. `U_base=10`, base node price 0.3, and contribution coefficient 1.0.
- Node pressure is uniform `[0.05,0.95]`; utilization `[0.05,0.90]`; congestion premium is `Uniform[0,0.5]*utilization`; price is Eq. (11). All are fixed within the game.
- Eq. (8) includes only other current-game players. The V1 field `existing_impact` is prohibited because the audited formal runtime uses an empty current-window aggregate and represents pre-existing runtime pressure through snapshot pressure/premium.

The current V1 scripts (hashes `068e85e...`, `92091769...`, `510773f...`) are unauthorised for result generation: they include a random nonzero `existing_impact`, do not compute the offline estimator error, and the verifier calls the same solver rather than an independent implementation.

### 4.2 Exact quantities

For every state, enumerate every assignment and every feasible unilateral deviation. Report:

- exact maximum social welfare and deterministic lexicographically smallest maximizing assignment;
- all pure-strategy Nash equilibria under improvement tolerance `1e-6`;
- worst and best PNE welfare;
- exact PoA `optimum/worst-positive-PNE` when both terms are positive;
- relative welfare gap when the exact optimum is positive;
- the deterministic `ready_order` selected PNE or capped/nonstable state, separately from worst-PNE PoA;
- exhaustive weighted-potential verification for every strict improving deviation with `h_fc>0`, requiring `Delta Phi = h_fc,i * Delta U_i` within `1e-8 * max(1, |terms|)` and the same positive sign.

The potential is frozen as the sum of each player's node-specific non-pair utility multiplied by `h_fc,i`, minus one symmetric pair term `Pressure_n*(h_ri,i*h_fc,i)*(h_ri,j*h_fc,j)` for each colocated unordered pair. Baseline constants may be included because they cancel in deviations.

Separate fixed unit fixtures, not counted among the 300 states, must test the `h_fc=0` boundary: zero-complexity players impose zero Eq. (8) impact, cannot change positive-complexity players' utilities, and can choose an individual best response after positive-complexity players stabilize.

### 4.3 Offline-reference estimator

Implement an equation-level, double-precision port of the anchor reference-search structure:

- canonical social-greedy start;
- strict individual best-response start with the anchor's four inner rounds;
- sorted, reverse, constrained-first, and one deterministic shuffled social-greedy order;
- deterministic unilateral social-welfare local improvement with budget `3*p*max(p,4)` evaluations;
- simulated annealing with initial temperature equal to per-player welfare scale, cooling 0.95, and `max(64,4p,3p)=64` proposals;
- final local improvement.

The estimator seed is the first nonzero unsigned 64-bit big-endian value from `SHA256("NSE-P1-REF-V2|state_id")`, and the LCG is the anchor multiplier/addend with modulo `2^64`. This reproduces the anchor search structure and budget but is not labelled bit-identical Rust because the constructed state schema and floating-point type differ.

Report estimate, exact optimum, absolute and normalized shortfall, exact-hit indicator, estimator runtime, and exact-enumeration runtime. The estimator must never exceed the exact optimum beyond `1e-8*max(1,|optimum|)`; violation is an implementation failure.

### 4.4 Independent verification and outputs

Required products under `runs/tscv1_p1_exact_small_v2_20260904/`:

1. `exact_games_v2.jsonl` — 300 immutable game documents;
2. `exact_results_v2.jsonl` — 300 primary enumerator/estimator results;
3. `exact_state_rows_v2.csv` — one analysis row per state;
4. `exact_summary_v2.json` — coverage and aggregate statistics;
5. `exact_verification_v2.json` — independent verifier receipt and all artifact hashes.

The verifier must implement a separate raw-dictionary utility/welfare/PNE enumeration path and must not call the primary `solve_exact` or estimator functions. It must reproduce every exact result within the frozen tolerance, recheck `3^p` assignment counts and 100/100/100 coverage, and recompute potential identities. Primary and verifier source hashes are recorded before the one authorized invocation.

### 4.5 Gates and failure interpretation

Hard integrity gates:

1. 300/300 states and exact 100/100/100 coverage;
2. independent verification passes;
3. every state has at least one PNE, as predicted for the positive-`h_fc` fixed-snapshot game;
4. all potential identities pass;
5. estimator never exceeds exact optimum beyond tolerance; no nonfinite field.

Reference-quality labels are frozen as:

- `accurate_small_state_reference`: median normalized shortfall at most 5% and p95 at most 20%;
- `usable_but_loose_small_state_reference`: median at most 10% and p95 at most 35%;
- `weak_small_state_reference`: otherwise.

Exact PoA has no favorable-value gate and is always reported when mathematically applicable. A `weak` reference label pauses P2 and requires a manuscript/method decision; it cannot be hidden or repaired by changing the state seed. Failure of any hard gate stops P2 and triggers formula/implementation correction before further online sampling.

## 5. Compute, storage, and execution order

P1 adds zero online simulator runs and does not modify the preserved formal run root.

Execution order is fixed:

1. implement/test P1-A analyzer and V2 exact-small generator/enumerator/independent verifier;
2. freeze source hashes and prove both output roots absent;
3. execute P1-A exactly once;
4. audit/commit P1-A outputs;
5. generate 300 V2 games exactly once, then enumerate and independently verify exactly once each;
6. audit/commit P1-B outputs and decide P2.

Expected exact enumeration space is 737,100 assignments across the 300 states before unilateral-deviation checks; the independent verifier repeats it. CPU-only turnaround is expected in minutes and storage well below 1 GiB.

## 6. Output-protocol note

The `experiment-plan` skill's referenced `output-versioning.md`, `output-manifest.md`, and `output-language.md` resources were absent from the installed skill package. This preregistration therefore follows the repository's stricter existing protocol: immutable run roots, `.partial` atomic writers, refusal to overwrite, SHA-256 receipts, `refine-logs/MANIFEST.md`, and tracker updates. All paper-facing prose remains English; audit explanations may remain bilingual where already established.
