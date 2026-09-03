# G3 Strict-PNE Scarcity/Order Counterfactual Preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: **FROZEN BEFORE IMPLEMENTATION AND REPLAY**; observation only; no
candidate and no D71--D75 run is authorized

## 1. Question and evidence boundary

The closed existing-log diagnosis found an objective/runtime mismatch:
NSESche has higher post-hoc paper welfare than FaaSRank but lower throughput
and QPR, with cold-start wait the largest positive stage difference. Direct
warm/finish initialization, bounded-regret finish guards, and larger
convergence budgets are already rejected. The only qualifying unexplored axis
is feasibility/concentration and deterministic player order.

This stage asks one falsifiable question:

> Holding the window snapshot, shared feasible candidate sets, Eqs. (1)--(20),
> strict Eq. (15), price vector, and iteration cap fixed, do deterministic
> scarcity orders expose a different certified PNE whose paper welfare is not
> lower and whose cold-path and projected-finish proxies are better?

This is not an online effect estimate. Throughput, QPR, cost, and request
latency from these diagnostic replays cannot select an order or appear as a
new paper result. They may be checked only for exact decision-neutral replay
parity. A qualifying counterfactual can only justify a separate candidate
preregistration on fresh D71--D75 tapes.

## 2. Frozen diagnostic state bank

Exactly 50 retained `ready_order` source runs are replayed with an instrumented
binary:

- all 20 Q61--Q80 NSESche homogeneous-low runs from
  `runs/tscv1_g1_formal_q61_q80_98f822c_20260903`;
- all 30 C0 D66--D70 runs (five seeds in each of six topology/load cells) from
  `runs/tscv1_g2_init_d66_d70_3ae7792_20260903`.

The seven reporting strata are the Q-bank homogeneous-low stratum and the six
G2 topology/load cells. Their frozen workload tapes, topology, configuration,
HPA, offline reference tables, and 1000-frame horizon are reused. No Q or D
source run is removed on the basis of any metric. The output must bind the
source run ID, tape hash, source observation hash, instrumented source commit,
executable hash, and counterfactual schema.

These are new diagnostic replays, not additional formal repetitions. They do
not alter or replace the 200 G1 formal observations or the 135 G2 development
observations.

## 3. Frozen counterfactual semantics

For every solver window, the live C0 path runs unchanged and is the only state
passed to dispatch, reference lookup, price feedback, or any simulator command.
After the live solve, a decision-neutral routine reconstructs the first
baseline-price inner solve from the same immutable snapshot. It uses the same:

- players and request-specific candidate sets;
- container states and available-memory snapshot;
- new-container limits;
- Eq. (15) utility and `EPSILON=1e-6` strict-improvement rule;
- sequential utility-best initialization;
- current-node preference on numerical ties;
- four-round cap and oscillation guard.

It changes only the order in which players initialize and perform strict best
responses. It cannot update scheduler caches, reference artifacts, prices,
commands, or simulator state. No alternative is permitted to prefer a
lower-utility node during a best response.

## 4. Preregistered orders

All keys end with the unchanged C0 order
`(arrival_frame, req_id, DAG_topological_rank, fn_id)` so ties are deterministic.
Candidate-node lists are canonicalized before computing counts.

- **O0 `ready_order`**: unchanged ascending C0 order; exact replay control.
- **O1 `reverse_ready_order`**: exact reverse of O0; a symmetric path-
  dependence falsification control.
- **O2 `service_scarcity_first`**: ascending count of running-warm candidate
  nodes, then ascending count of all existing-container candidate nodes, then
  ascending candidate count, descending cold-start frames, descending required
  container memory, then the C0 key.
- **O3 `capacity_scarcity_first`**: ascending count of candidates that can
  accept the player in the empty counterfactual assignment under current
  memory and new-container limits, then descending required container memory,
  descending resource intensity, descending cold-start frames, then the C0
  key.
- **O4 `resource_impact_first`**: descending heterogeneity impact, descending
  resource intensity, descending required container memory, descending
  cold-start frames, ascending feasible-candidate count, then the C0 key.

O2 uses container availability only to order players; it never directly
chooses a warm node. O3 and O4 test the feasibility/concentration branch. O1
guards against interpreting arbitrary order sensitivity as support for the
specific scarcity mechanism.

One derived observation-only envelope, **E0 `nonworse_welfare_cold_envelope`**,
is also reported. For each window it considers O0--O4 outcomes that are
complete, stable, and independently strict-PNE certified. It retains only
outcomes with welfare no lower than O0 by more than
`1e-6 * max(1, abs(O0 welfare))`, then ranks them by:

1. smaller assigned startup burden;
2. smaller projected-finish sum;
3. higher paper welfare;
4. fixed name order O0, O2, O3, O4, O1.

E0 is an upper-envelope diagnosis of whether PNE multiplicity contains a
formula-compatible operationally preferable state. It is not authorized as a
runtime mechanism by this document.

## 5. Frozen window metrics and certificates

Every O0--O4 outcome is emitted, including infeasible, capped, or oscillating
outcomes. Each record contains:

- source run/window/frame, topology/load/seed, order name and order hash;
- player count, candidate-set hash, assignment hash, assigned count;
- initialization/inner rounds, moves, evaluations, stable, limit,
  oscillation, and termination;
- independent strict-PNE certificate: after removing each assigned player,
  no feasible candidate has utility greater than its current-node utility by
  more than `EPSILON`;
- Eq. (17) welfare and its five components at immutable baseline prices;
- assigned startup burden: zero for running-warm, remaining startup frames for
  starting containers, and full function cold-start frames otherwise;
- projected-finish sum using the already disclosed
  `startup_remaining + runnable + starting_resident + pressure` score;
- running-warm, starting, and cold/nonrunning selected shares;
- assigned-node count, normalized dispersion, co-location conflict ratio,
  assigned snapshot pressure, and projected reserved-memory utilization.

All sums are also reported per assigned player. No counterfactual metric is
substituted for observed throughput, QPR, latency, or cost.

## 6. Integrity gates

Aggregate interpretation stops unless every gate passes:

1. exactly 50 declared replays complete with no missing or extra source ID;
2. instrumented live C0 matches the retained source on every comparable
   window's frame, player counts, final assignment hash, termination, prepared/
   sent commands, scale-up counts, and baseline welfare within the frozen
   floating tolerance;
3. O0's reconstructed first-inner assignment hash equals the live solve's
   first `outer_feedback_trace` assignment hash in every complete first-inner
   window;
4. all O0 outcomes marked stable/complete pass the independent strict-PNE
   certificate;
5. source code tests prove that the counterfactual result is never accepted by
   `dispatch`, price feedback, reference lookup, or scheduler mutable state;
6. every order and every window is present in the raw output, regardless of
   its direction.

A gate failure authorizes only a technical correction followed by the same
50 source replays. It cannot authorize D71 or an order candidate.

## 7. Frozen direction and eligibility rules

Comparisons use windows where O0 is complete, stable, and certified. All other
windows remain in coverage tables. Per-player sums are first aggregated within
each source run and then equally averaged by run inside each of the seven
strata.

A raw global order O1--O4 is directionally eligible only if:

1. it introduces no additional incomplete, non-stable, oscillating, capped,
   or certificate-failing comparable window relative to O0;
2. its assignment differs from O0 in at least 1% of comparable windows overall
   and in at least four of seven strata;
3. mean paper welfare/player is nonnegative versus O0 overall, and no stratum
   is worse by more than 0.1%;
4. mean startup burden/player is lower overall, is nonworse in at least five
   of seven strata, and is not worse by more than 1% in any stratum;
5. mean projected finish/player satisfies the same overall, five-of-seven,
   and 1% maximum-regression rule.

E0 is directionally eligible only if it selects a non-O0 outcome in at least
1% of comparable windows overall and in at least four strata, lowers both
startup burden/player and projected finish/player overall, and is nonworse on
each proxy in at least five strata with no stratum worse by more than 1%.
Its window-level welfare noninferiority is guaranteed by construction and must
be rechecked from emitted records.

Placement dispersion, conflict, memory, and warm-path shares are all reported
but do not enter the gate because the existing associations point in mixed
directions and are not causal estimates.

Eligible mechanisms are ranked by the minimum across the seven strata of the
three ratios `welfare/O0`, `O0 startup/alternative startup`, and
`O0 projected-finish/alternative projected-finish`, followed by their mean
ratio and fixed simplicity order O2, O3, O4, O1, E0. At most the top two can
be named in a later, separately frozen G3 candidate preregistration. If none
is eligible, G3 is blocked; thresholds, strata, orders, or the state bank
cannot be changed after inspection.

## 8. Implementation and output plan

Before replay:

1. add unit tests for every deterministic key, order invariance of candidate
   sets, O0 exact reconstruction, strict-PNE certification, E0 selection, and
   zero decision feedback;
2. run formatting, directed Rust tests, configuration/protocol regression, and
   an analysis-schema test;
3. commit source, freeze one executable, prove Rust source drift is zero, and
   build an immutable 50-replay manifest;
4. run the 50 diagnostics in result-blind source order and retain every valid
   artifact.

Required outputs are a raw counterfactual JSONL stream, a window-level CSV, a
run/stratum summary JSON and CSV, parity report, immutable manifest/receipt,
and `G3_ORDER_COUNTERFACTUAL_RESULT_AUDIT.md`.

At preregistration:

- implementation exists: false;
- diagnostic replay exists: false;
- candidate effect estimated: false;
- `D71_authorized=false`;
- `homogeneous_middle_formal_authorized=false`;
- paper-ready groups: zero.
