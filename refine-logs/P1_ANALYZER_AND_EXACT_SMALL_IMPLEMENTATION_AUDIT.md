# P1 Analyzer and Exact-Small Implementation Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: implementation frozen before any P1 retained-product analysis or 300-state output generation

Parent protocol: `P1_RETAINED_AND_EXACT_SMALL_PREREGISTRATION.md`

## 1. Frozen implementation identities

The following stored-content SHA-256 values were computed after formatting and
directed tests, while both registered output roots were absent.

| File | SHA-256 |
|---|---|
| `analysis/p1_retained_evidence.py` | `8a8ee9c3429a098e4ebc3ac13e9b134b040ffb1502b37b65cc90868ce0ab4156` |
| `analysis/tests/test_p1_retained_evidence.py` | `98e576df48d07c481bb2f2baf4f6b55a7e2657f8347fad9067d93b6ea0164e30` |
| `poa/generate_games_v2.py` | `36d663340a59f932c2c854cbab4efd4efff52246b72963fc2d9e3831918013cf` |
| `poa/exact_poa_v2.py` | `4437ee0a3fe66cdbdcfda7b93537ce038c38d05b0b02c39133b06c4af4e164c6` |
| `poa/verify_results_v2.py` | `5f062f2f6a84c81f11aa9dde7a0766932ff47c0e7b7420b217dd2185567646dd` |
| `poa/tests/test_exact_poa_v2.py` | `9157684b17356f4c2a972c463048697a39418d3798a5a78cf7292f4dd17d1d34` |
| `poa/tests/test_verify_results_v2.py` | `5c083e07cb5eac5b17a82bbe271599cdbe822edc43241e7f5ede0ab3589026ea` |

The implementation parent was Git commit
`6ddae92e9b45490cc2855ea163d5bc76bada1c4e`. The implementation will be
committed before execution, so the execution receipt can also bind a Git
identity.

## 2. P1-A retained analyzer contract

The analyzer fails before writing any scientific table unless it independently
establishes all of the following:

- exactly one canonical NSESche `ready_order` run for every Q61--Q80 seed and
  no result-conditioned inclusion;
- canonical QC, unique run-spec hashes, membership in the frozen ready
  manifest, exact ready-manifest document/file hashes, and exact anchor binary
  hash;
- reference dependency existence/hash and all four compressed stream hashes,
  decompressed hashes, byte counts, and line counts;
- one NSESche run configuration, 1,000 decision windows, one run summary,
  1,000 scheduler timing rows, a nonempty request stream, and the frozen strict
  Eq. (15)/`ready_order` runtime contract;
- structural Eq. (16)/(19)/(20) trace recomputation for active windows;
- all 120 reference catalog entries with exact 2 x 3 x 20 coverage, table,
  receipt, and process hashes, plus independent reference-value row counts.

The seed is the inferential unit. The analyzer retains all 20 seed points and
uses the preregistered metric-specific SHA-256 seed with 10,000 BCa resamples.
No comparator test or favorable convergence threshold exists. Zero thread-CPU
values remain observed zeros.

## 3. P1-B exact-small contract

The V1 generator, enumerator, and verifier remain unchanged and unauthorized.
The V2 path implements the frozen 3-node, 4/6/8-player, 100-state-per-size
population with the same V1 profile equations and Eq. (11) node pricing, but it
removes `existing_impact` and uses one state-shared quality weight. All function
containers are pre-provisioned, making all `3^p` assignments feasible.

The primary enumerator reports exact optimum, all PNE, worst/best PNE welfare,
worst-positive-PNE PoA, the separate `ready_order` selected state and explicit
stable/oscillation/limit termination, and exhaustive strict-improvement
weighted-potential identities. The frozen estimator ports the anchor search
structure: canonical social-greedy and Nash starts, unique canonical/reverse/
constrained/shuffled orders, sequential bounded social improvement, the anchor
64-bit LCG, 64 annealing proposals, 0.95 cooling, and final improvement.

The verifier imports neither the primary solver nor estimator. It separately
reimplements raw-dictionary feasibility, utility, welfare, PNE enumeration,
potential deltas, assignment hashes, and `ready_order`. It checks every exact
field and reference upper bound before emitting the registered CSV, summary,
and hash receipt. Estimator runtime is measured separately from exact
enumeration; the constructed double-precision port is not described as
bit-identical Rust.

## 4. Tests and pre-execution state

- Black formatting passed for all seven new files.
- The eight directed P1 tests passed after the final implementation change.
- The correctly rooted complete reviewer-experiment suite passed 304/304 in
  885.261 seconds. A preceding invocation without `-t .` passed 98 discovered
  tests but produced one collection error because it imported `protocol` as a
  top-level package; the corrected package-root invocation eliminated that
  harness error. The later termination-metadata-only change was rechecked by
  all eight directed P1 tests.
- `git diff --check` passed.
- `runs/tscv1_p1_retained_evidence_98f822c_20260904/` was absent.
- `runs/tscv1_p1_exact_small_v2_20260904/` was absent.
- No formal simulator run, retained-result analysis, exact game population, or
  exact optimum was generated while implementing or testing this contract.

## 5. Authorization

After this implementation and audit are committed, exactly one P1-A invocation
is authorized at the registered retained output root. It must be audited and
committed before the generator, primary enumerator, and independent verifier
are each invoked once at the registered P1-B root. Any hard failure stops P2;
no seed, state, or result may be replaced according to its observed value.
