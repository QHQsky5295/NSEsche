# G3 E0 Operational-Candidate Preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: **PREREGISTERED BEFORE IMPLEMENTATION AND BEFORE D71--D75 DATA**.
Implementation, directed tests, protocol/analyzer construction, and a release
freeze are authorized. Workload capture, reference building, online execution,
candidate selection, and formal confirmation remain prohibited until all
pre-sampling gates in Section 8 are committed and verified.

## 1. Authorization and falsifiable question

The corrected G3 diagnosis at commit
`d90457467d4219915e2d1f35350994b9d76db83d` retained all 50 source replays,
passed every integrity gate, and named only E0 as a permissible later
preregistration option. Its analysis SHA-256 is
`ea43d53f0ef91a256b2f6d4f673ede3c1c4eeef8dce36e00d6012b7c97c4d07a`.
Selection used paper welfare, startup burden, and projected finish only; replay
throughput and QPR did not enter eligibility.

This stage asks:

> When the G3 E0 rule is allowed to choose the operational strict PNE at the
> first or every outer price round, does one fixed implementation improve both
> realized throughput and QPR over C0 in all six 20-node cells, while remaining
> computationally viable and leading all nine homogeneous-low baselines?

The null outcome is that C0 wins, any throughput/QPR cell fails, the low-load
baseline gate fails, or the selected variant exceeds the frozen solve-time
cap. Any null outcome is retained and closes this family without formal reuse.

## 2. Immutable scientific boundary

The implementation must not change:

- paper Eqs. (1)--(20), ISCUM terms, CP-GEN prices, Eq. (17) welfare, Eq. (19)
  feedback, Eq. (20) adjustment intensity, or the nonpositive-reference
  fallback;
- strict Eq. (15) unilateral-improvement semantics or `EPSILON`;
- the four-round inner and outer limits, load-specific published parameter
  centres, feasible candidate sets, HPA, cold-start/container lifecycle,
  dispatch, workload profiles, metric definitions, or common runtime;
- low `(r0=0.6,wq=0.5)` and middle/high `(r0=0.5,wq=0.6)` settings;
- the five G3 orders, order keys, welfare tolerance, eligibility predicate, or
  envelope tie order.

E0 is an equilibrium-selection rule outside the published utility equations.
Every state that reaches dispatch must be a state produced by the unchanged
strict best-response solver at the current price. No proxy score may override
an individual best response or directly assign a request to a node.

The old-PDF bars remain provenance anchors only. Their proximity is reported
but is not a candidate, seed, extension, or stopping criterion.

## 3. Complete candidate family

Exactly three configurations are admitted:

### C0 `ready_order`

The unchanged current implementation. It initializes and updates players in
ready order and then applies the existing outer Eq. (16)--(20) feedback. This
is the control and final simplicity winner on an exact tie.

### C1 `ready_pne_envelope_first`

At the baseline-price first outer round only, independently solve O0--O4 from
the same immutable pre-window aggregates and candidate sets. Select E0 as
defined in Section 4, and use that selected state as the round-one operational
PNE. Do not first execute and retain a separate live C0 solution. If outer
feedback continues, subsequent rounds start from the selected state and use
the unchanged ready-order strict best-response loop.

### C2 `ready_pne_envelope_each`

At every outer round, independently solve O0--O4 from the same immutable
pre-window aggregates and current round's price signal. Select E0 at that
price and use it as the operational PNE for the round. The unchanged outer
loop compares successive selected assignments, computes the social gap,
applies Eqs. (19)--(20), and respects the existing stopping/round limit.

C1 and C2 vary only the frequency with which the single G3-authorized E0 rule
is applied. No fourth candidate, tuned threshold, learned order predictor, or
new order may be added after D71 inspection. C1 precedes C2 in a non-control
simplicity tie because it changes only the first round and has lower expected
cost.

## 4. Exact E0 selection rule

At a given immutable snapshot and price, construct O0--O4 with these existing
orders:

1. O0 ready order;
2. O1 reverse ready order;
3. O2 service scarcity first;
4. O3 capacity scarcity first;
5. O4 resource impact first.

An outcome is eligible only when it is complete, stable, and independently
strict-PNE certified, and its paper welfare is no lower than O0 by more than

`EPSILON * max(1, abs(O0 welfare))`.

Eligible outcomes are ranked exactly by:

1. smaller assigned startup-burden sum;
2. smaller projected-finish sum;
3. higher paper welfare;
4. fixed tie order O0, O2, O3, O4, O1.

The first eligible outcome is the incumbent. O0 is used as fallback only if
the eligible count is zero. This is the corrected and already tested G3 rule;
all comparisons retain binary32 guard semantics. Startup burden and projected
finish choose among strict PNEs only and never enter Eq. (15).

## 5. Implementation and observability contract

Implementation must add two distinct operational-refinement values and two
distinct reference-key tags. The run configuration must expose a new schema
version and the exact equilibrium-selection semantics. Operational E0 and
`NASH_ORDER_COUNTERFACTUAL` may not be enabled together; the diagnostic flag
remains observation-only and default-off.

For every policy window, logging must separate:

- chosen-path initialization, inner rounds, moves, evaluations, stable/PNE
  status, outer rounds, price feedback, and termination;
- total O0--O4 evaluations used by operational selection;
- eligible outcome count, selected order/hash, selected-non-O0 flag, welfare
  tolerance, fallback use, and independent certificate;
- E0-selection microseconds, total `solve_us`, scheduler wall/thread CPU time,
  process peak RSS where available, and dispatch time.

Existing convergence fields must describe the path used by dispatch, while
new `evaluated_total_*` fields describe computational work across rejected
orders. The selected state hash in the operational log must equal the state
hash used by dispatch and the first corresponding outer-feedback trace row.

The implementation must process candidate solutions without retaining more
state than necessary. It may refactor common solver code for exact state
return, but may not change the ordering definitions or arithmetic to improve a
candidate after seeing development results.

## 6. Fresh development product

The only development seeds are `D71`, `D72`, `D73`, `D74`, and `D75`. They
must be generated from the existing deterministic seed mapping before any
capture. They are paired across every applicable method and may never become
formal observations.

The complete product is:

- 30 workload tapes: `2 topologies x 3 loads x 5 seeds`;
- 90 candidate-specific offline references: `3 candidates x 30 tapes`;
- 90 candidate online runs: `3 candidates x 2 topologies x 3 loads x 5`;
- 45 homogeneous-low controls: the nine non-NSESche formal methods on the same
  five homogeneous-low tapes;
- total online runs: 135; total candidate/reference cells: 18; baseline cells:
  9.

The baseline list is exactly Greedy, Random, Hash, Load Balance, FaaSRank,
OCS, Hiku, Jiagu, and Orion, using the current frozen protocol implementations
and the frozen independent FaaSRank model. One release executable is used for
all methods, topologies, and loads.

All tapes are captured before any reference is built; all 90 references are
built and bound before any online run. Online order is fixed in the manifest
without reading outcomes. Every valid observation is retained. A technical
failure may be retried only with the identical seed, tape, configuration,
reference, binary, and run ID, with the failed attempt quarantined and logged.

## 7. Frozen analysis, ranking, and gates

Analysis is fail-closed unless the complete 135-run product, 30 tapes, 90
matching references, runtime identity, strict-Eq.15 contract, formula trace,
QPR coverage, candidate E0 contract, and artifact hashes validate.

For each candidate and each of the six cells, compute the equal-weighted mean
throughput in requests/ms and mean QPR across exactly D71--D75. Construct the
twelve ratios `candidate_mean / C0_mean`. Rank candidates by:

1. largest minimum of the twelve ratios;
2. largest mean of the twelve ratios;
3. most cells jointly first in throughput and QPR;
4. fixed simplicity order C0, C1, C2.

Formal confirmation is authorized only if every condition holds:

1. the selected candidate is C1 or C2, not C0;
2. its minimum twelve-ratio score is strictly greater than `1.0`, so both
   throughput and QPR means exceed C0 in every cell;
3. in homogeneous-low, its throughput mean and QPR mean are each strictly
   greater than every one of the nine paired baseline means;
4. all five QPR values exist in every candidate/cell and baseline group;
5. for every cell, the candidate's aggregate active-window `solve_us` divided
   by C0's aggregate active-window `solve_us` is at most `9.0`;
6. no runtime-contract violation, dispatch/state-hash mismatch, OOM, or
   candidate-specific invalid assignment occurs.

The timing denominator and numerator sum all active policy windows across the
five paired runs before taking the ratio. Scheduler wall time, thread CPU time,
peak RSS, selected-order fractions, outer rounds, limits, latency, completion,
and cost are mandatory secondary reports but cannot rescue a failed primary
gate. No confidence interval extension is allowed in development.

The 9x ceiling is frozen from pre-D71 G3 evidence: the five-order diagnostic
cost 3.02--3.76 times live `solve_us` by load; conservative no-reuse upper
estimates were 4.02--4.76 times for C1 and up to 8.27 times for C2. It is a
practicality guard, not a post-result performance adjustment.

If all gates pass, a new disjoint 20-seed formal bank may be separately
preregistered, beginning with the complete 200-run homogeneous-20 low cell.
If any gate fails, D71--D75 remain a complete negative development result, no
candidate from this family enters formal execution, and homogeneous-middle
remains blocked.

## 8. Pre-sampling gates and zero-data state

Before D71 capture, all of the following must be completed and committed:

1. directed Rust tests for C0 parity, C1 first-round use, C2 every-round use,
   exact E0 selection/fallback, selected-state dispatch identity, strict PNE,
   outer feedback, reference-key separation, diagnostic incompatibility, and
   deterministic replay;
2. formatting plus the affected Rust, configuration, protocol, and analysis
   regression suites;
3. a protocol/analyzer implementation that encodes the exact matrix, metrics,
   ordering, ranking, overhead calculation, and fail-closed gates above;
4. one release executable bound to a source commit with zero Rust-source drift;
5. an unbound immutable manifest whose run root contains no D71--D75 tape,
   reference, result, selection receipt, or derived metric.

At this preregistration, repository HEAD is
`d90457467d4219915e2d1f35350994b9d76db83d`. A recursive run-artifact path
check found zero D71--D75 paths. No operational E0 source value, D71--D75
protocol module, manifest, tape, reference, online run, or selection receipt
exists.

Current authorization is therefore:

- source implementation and tests: authorized;
- protocol/analyzer implementation: authorized;
- release build and zero-data manifest freeze: authorized;
- D71--D75 workload capture or later sampling: **not authorized**;
- formal homogeneous-low/middle/high: **not authorized**;
- paper-ready experiment groups: zero.
