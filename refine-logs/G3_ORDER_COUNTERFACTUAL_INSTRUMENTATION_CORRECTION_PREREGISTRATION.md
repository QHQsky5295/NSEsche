# G3 E0 Instrumentation Correction Preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: **FROZEN BEFORE SOURCE CORRECTION**; no candidate or D71--D75 run is
authorized.

## 1. Trigger and retained evidence

The V2 analyzer correction was committed before reanalysis as `09828ca`. The
corrected analysis was written to `analysis_corrected_v2/` without changing or
overwriting the first failed report. It recovered complete 300,000-row window
coverage and removed the 12 analyzer-induced errors, but three integrity errors
remain:

- homogeneous-high D67, window 578;
- homogeneous-high D70, window 845;
- heterogeneous-high D69, window 175.

In all three windows O0 is complete but capped and uncertified, while one or
more O1--O4 outcomes are stable, complete, certified, and within the frozen
welfare tolerance. The emitted `eligible_outcomes` is positive, but E0 still
selects the capped O0. This is a real observation-only instrumentation defect,
not an analyzer interpretation issue.

The V2 failed report has file SHA-256
`069eb5c12748a2bfebf88cc9f1b081059aeb65fd79605d5db5a011f67af6e92a`.
It remains invalid and cannot authorize or rank a candidate.

## 2. Frozen source correction

The correction is restricted to the E0 observation-only selector:

1. start with no eligible incumbent;
2. scan O0--O4 in the already frozen order;
3. the first complete, stable, certified, welfare-noninferior outcome becomes
   the incumbent;
4. subsequent eligible outcomes use the unchanged startup, projected-finish,
   welfare, and fixed-name tie break;
5. only when the eligible count is zero may the diagnostic record fall back
   to O0 for coverage.

No player order, candidate set, utility, welfare equation, price, iteration
cap, simulator command, scheduler state, reference path, throughput/QPR
calculation, or eligibility threshold may change. A unit test must construct a
capped O0 plus an eligible alternative and prove that the alternative is
selected. Existing read-only and welfare-guard tests must continue to pass.

## 3. Required repeat

Because Rust instrumentation changes, the correction requires:

- a new source commit and release binary;
- zero Rust-source drift from that commit;
- a new manifest that retains exactly the same 50 source run IDs, tapes,
  references, source artifacts, order, and seven strata while rebinding only
  the instrumentation commit/binary and derived run IDs;
- exactly those 50 new diagnostic replays, with every valid replay retained;
- fail-closed V2 analysis in a new directory.

The existing online workspace and both failed analysis directories remain
audit evidence. No D71 seed, formal homogeneous-middle run, or paper result is
authorized until the repeated integrity gate passes and the frozen eligibility
rule is applied.

At this freeze:

- source correction implemented: false;
- corrected binary exists: false;
- repeated replay exists: false;
- `D71_authorized=false`;
- paper-ready groups: zero.
