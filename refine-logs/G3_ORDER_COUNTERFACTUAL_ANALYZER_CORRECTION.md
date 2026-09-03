# G3 Order-Counterfactual Analyzer Technical Correction

Date: 2026-09-03 (Asia/Shanghai)

Status: **FROZEN BEFORE CORRECTED REANALYSIS**; the first analysis is retained
as a failed technical audit; no candidate or D71--D75 run is authorized by
this correction.

## 1. Immutable evidence being corrected

The frozen 50-run manifest remains
`runs/tscv1_g3_ordercf_q61q80_d66d70_14a61d2_20260903/g3.order-counterfactual.ready.json`
with document hash `d3f7b18c...b0a91` and file SHA-256
`5b55a4d5...af22`. All 50 canonical replay directories remain unchanged. The
instrumented binary and Rust source are unchanged, and the first analysis is
preserved under `analysis/`.

The first analyzer execution returned
`invalid_diagnostic_integrity_gate_failed`. Its report has document SHA-256
`d2a6640d...c723`; it recorded 50/50 canonical replays, exact source/live C0
parity, 50,000 raw stream windows, zero parity errors, and 15 diagnostic
errors. No eligibility result from that failed report was used to authorize a
candidate.

## 2. Frozen technical corrections

Inspection was restricted to integrity fields and the already frozen G3
preregistration. Throughput, QPR, latency, cost, and mechanism ranking did not
select these corrections.

1. The preregistration requires O0/live first-inner hash equality only for a
   completed stable first-inner solve. Six capped O0 windows correctly have no
   `outer_feedback_trace` entry, but V1 incorrectly required a hash whenever
   `players > 0`. V2 checks hash equality for stable/complete first-inner
   outcomes and checks the complementary no-trace contract for capped ones.
2. The six capped O0 windows must remain in coverage but are excluded from the
   frozen comparable-window estimand. V1 skipped them before writing the
   window CSV and then expected all-window coverage, creating exactly 36
   self-induced missing rows. V2 emits all six O0--O4/E0 rows before applying
   the comparable-window filter.
3. When O0 is not comparable and no certified outcome passes the E0 guard,
   the emitted O0 fallback is a coverage record, not an eligible E0 choice.
   V2 verifies this explicit empty-fallback contract without treating the
   capped outcome as an envelope violation.
4. The frozen Rust implementation evaluates the welfare guard with IEEE-754
   `f32` addition. V1 converted the emitted exact binary32 values to Python
   `f64` before rechecking the boundary, producing four false violations. V2
   reproduces the binary32 addition exactly; it does not change the tolerance
   or any observed value.

The complete-raw gate now verifies both the 50,000 unfiltered stream windows
and six exported mechanism rows per window. Any genuinely missing order,
window, schema field, stable-O0 certificate, decision-neutral flag, or parity
record still fails closed.

## 3. Validation and execution boundary

Two regression tests were added for the capped/no-trace contract and the
observed binary32 boundary. Together with the existing G3 tests, the focused
analysis/protocol set passes 13/13.

Corrected analysis must write to a new directory (not overwrite `analysis/`)
and must consume the same immutable 50 canonical replay artifacts. A second
simulator execution would duplicate approximately 0.19 GiB without changing
the corrected component, so it is prohibited here: this is a pure analyzer
correction, not a scheduler or replay correction. The original failed report
and every online replay remain retained for audit.

At this freeze:

- corrected result inspected: false;
- candidate authorized: false;
- `D71_authorized=false`;
- homogeneous-middle formal authorized: false;
- paper-ready groups: zero.
