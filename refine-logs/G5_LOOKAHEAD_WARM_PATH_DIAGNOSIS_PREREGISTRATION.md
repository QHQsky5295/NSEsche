# G5 lookahead/warm-path diagnosis preregistration

Date: 2026-09-04

Parent decision: `complete_trace_no_unique_latency_stage`

## Purpose

G4 found a strong but non-unique cold-start-wait gap.  Before proposing another
operational refinement, G5 will distinguish two source-grounded explanations:

1. **lookahead/capacity path** -- NSESche C0 admits a function only after all
   parents finish, while some advanced baselines bind descendants before they
   become execution-ready and can overlap container startup with upstream work;
2. **warm-bypass path** -- a running warm candidate is available, but C0's
   strict Eq. (15) utility argmax selects a starting or non-running container.

The analysis is descriptive and diagnostic.  It cannot turn a window-level
proxy into per-invocation causality and cannot make the G4 result paper-ready.

## Frozen inputs

- G4 JSON:
  `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/latency_diagnosis/g4_hom_low_latency.json`
- G4 document SHA-256:
  `d65feedbd8894df12a38f583b23ee319f008507188671985c9ad8621b3e1749e`
- G4 file SHA-256:
  `1f58e404f39f3aa03cd4c2e03865800caa95e0a687f3a00c335bd0d8798556c5`
- G3-E0 selection document/file SHA-256:
  `4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34` /
  `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`
- Ready-manifest hash:
  `c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657`
- Cohort: exactly the retained 50 homogeneous-low D71--D75 runs used by G4;
  five NSESche C0 and 45 nine-baseline runs.
- Primary source comparators for lookahead: OCS (`PreAllSched`), Hiku, Jiagu,
  and Orion (`All`).
- Same-admission negative/control comparator: FaaSRank-P (`PreAllDone`).
- Independent unit: run/seed.  No run, seed, completed request, or completed
  function may be removed after inspection.

The canonical run products and simulator binary are immutable.  No new online
run is authorized in G5.

## Frozen definitions

For each completed request/function record:

- `ready = ready_schedule_frame`;
- `scheduled = scheduled_frame`;
- **pre-ready lead** = `max(ready - scheduled, 0)` ms;
- **pre-ready-bound indicator** = `scheduled < ready`;
- for a non-null `cold_start_done_frame = cold_done`, **startup overlap** =
  `max(min(cold_done, ready) - scheduled, 0)` ms;
- **post-ready cold wait** =
  `max(cold_done - max(ready, scheduled), 0)` ms, or zero when the cold boundary
  is null.

Startup overlap is reported only as temporal overlap observed in a completed
function record.  It is not called saved latency.  Full completed-function and
common-completion comparisons are both mandatory.

For every active C0 decision window:

- `A = assigned_players`;
- `R = selected_running_warm_players`;
- `S = selected_starting_container_players`;
- `C = selected_cold_or_nonrunning_players`;
- `W = running_warm_available_players`;
- `B = running_warm_bypassed_players`;
- **selected non-warm** `N = S + C`;
- **capacity-absence non-warm decisions** `U = N - B`;
- **conditional warm-bypass share** = `B / W` when `W > 0`;
- **non-warm bypass contribution** = `B / N` when `N > 0`.

The analyzer must fail closed unless `A = R + S + C`, `0 <= B <= W <= A`,
`B <= N`, every active window is a complete assignment, prepared/sent commands
equal `A`, invalid assignments and channel failures are zero, and
`selected_lower_utility_than_warm_players` is zero under strict Eq. (15).
Utility-advantage and finish-delta sums/means are retained, with null means
allowed only when `B = 0`.

Completed functions will also be grouped by `scheduled_frame` and joined to the
C0 window with the same emitted `frame`.  This is an audit of temporal alignment
only: functions from incomplete requests are unavailable, so joined counts may
not be represented as all dispatched functions.

## Frozen summaries

For every method and seed, report count, mean, median, p95, p99, sum, and
positive share of lead, overlap, and post-ready cold wait, plus the pre-ready-
bound share.  Report mean +/- sample SD and paired 95% t intervals across five
seeds without treating functions as independent replicates.

For every NSESche/baseline seed pair, report full-completed-function differences
and the same differences over request/function keys completed by both methods.
Also report sign counts and leave-one-seed-out means.  Extreme seeds remain in
the tables and are discussed rather than removed.

For C0, report the exact run-level totals and shares for `A,R,S,C,W,B,N,U`,
weighted totals across runs, unweighted seed means, and same-frame completed-
function cold-event alignment.  The report must disclose the completed-only
coverage ratio relative to emitted commands.

## Decision rules

### L: lookahead path supported

`lookahead_supported=true` only if all conditions hold:

1. C0 pre-ready-bound share is at most 1% in every seed.
2. At least three of OCS/Hiku/Jiagu/Orion have a higher pre-ready-bound share
   and positive mean lead difference versus C0 in at least 4/5 full-cohort seed
   pairs and at least 3/5 common-completion seed pairs.
3. The same at-least-three comparators have greater startup overlap in at least
   4/5 full-cohort pairs and at least 3/5 common-completion pairs.
4. For those same comparators, positive overlap advantage and positive C0
   post-ready-cold-wait disadvantage co-occur in at least 3/5 full-cohort pairs.
5. FaaSRank-P does not satisfy Conditions 2 and 3, preserving its role as the
   same-admission control, and source inspection confirms the frozen collection
   modes.

These thresholds identify an operational timing mechanism; they do not prove
that all request-latency or QPR differences are caused by lookahead.

### W: warm bypass dominant

`warm_bypass_dominant=true` only if all conditions hold:

1. non-warm selections and warm bypasses are nonzero in every seed;
2. `B/N >= 0.50` in at least 4/5 seeds and in the five-run weighted total;
3. mean selected-minus-best-warm paper utility is strictly positive for bypass
   windows, with zero lower-utility-than-warm selections;
4. same-frame completed-only cold-event rate is higher in bypass-active than
   bypass-inactive non-warm windows in at least 4/5 seeds.

If completed-only frame coverage is below 80% in any seed, Condition 4 is
unidentifiable and W fails rather than being imputed.

### Authorization

- If L passes and W fails, the result audit may authorize only a separate,
  fresh-development-bank preregistration of one strict-Eq.-(15)
  `PreAllSched` lookahead candidate against C0.  It may not implement or run it.
- If W passes and L fails, the audit may authorize only a separately
  preregistered warm-bypass candidate family, subject to the fixed-equation
  boundary and prior E0 negative result.
- If both or neither pass, no candidate is authorized without a new explicit
  first-principles adjudication.

Under every outcome, formal progression, figures, paper claims, new seeds, and
source changes remain blocked until a result audit is committed.

## Output contract

One successful invocation may write, without overwrite, only:

- `g5_lookahead_warm_path.json`;
- `g5_function_timing_runs.csv`;
- `g5_function_timing_pairs.csv`;
- `g5_function_timing_aggregates.csv`;
- `g5_nash_warm_accounting.csv`.

The analyzer must bind all parent hashes, revalidate every canonical receipt,
and write atomically.  Analyzer implementation, directed tests, hashes, and the
one-invocation authorization require a separate audit before execution.
