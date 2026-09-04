# G10 Work-Conserving Remaining-Work Development Preregistration

Date: 2026-09-04 (Asia/Shanghai)  
Branch: `agent/tsc-resubmit-final`  
Base commit: `3a14077627487b8a0b43e633f13064d77702dc79`  
Status: zero-result mechanism/protocol boundary frozen; implementation only is authorized

## 1. Motivation and scientific boundary

G9 established a specific failure mechanism rather than an ambiguous bad
sample: limiting the oldest *live requests* to the node count was not work
conserving because dependency-blocked requests occupied the cohort while
ready function players outside it were excluded. The G9 candidate consequently
ranked last in throughput and QPR at every load. All 75 observations remain
frozen; D81--D85 cannot be reused to select or evaluate G10.

The retained G1--G8 evidence identifies two additional facts:

1. fixed-snapshot Nash convergence is not the performance bottleneck; and
2. the publication gap is driven by completed-request throughput and request
   latency, while unrestricted speculative DAG binding can reduce latency but
   can also accumulate parent-blocked work and reduce completion.

G10 therefore changes neither the paper utility nor any displayed equation.
It tests whether a deterministic remaining-work order, optionally combined
with a globally bounded one-hop frontier, can choose a better strict PNE and
overlap a small amount of successor startup without excluding any dependency-
ready player.

This is development research, not a formal paper result. No G10 outcome may
be mixed with formal Q61--Q80 observations. Every first QC-valid observation
is retained regardless of throughput or QPR. Result-conditioned seed/run
deletion, replacement, relabeling, or repeated sampling until a threshold is
met is prohibited.

## 2. Frozen candidates

The control and two candidates form one globally defined family; no load label
or topology label enters the decision rule.

### C0: `ready_order`

The current paper-faithful control. It collects every unplaced function whose
parents are complete and orders players by arrival frame, request ID, DAG
topological rank, and function ID.

### C1: `ready_remaining_work`

- Candidate set: exactly the same dependency-ready players and feasible nodes
  as C0.
- Request priority: ascending number of unfinished functions,
  `dag_function_count - completed_function_count`.
- Deterministic tie-break: arrival frame, request ID, DAG topological rank,
  function ID.
- Initialization: the existing strict-utility feasible initialization.
- Updates: unchanged strict Eq. (15) best responses until the existing stop
  rule/budget.

This is a shortest-remaining-DAG ordering of the same game. It changes only
the deterministic sequence in which the finite potential game is initialized
and updated; it does not change utilities, actions, prices, or the definition
of a PNE.

### C2: `ready_remaining_work_bounded_frontier`

C2 includes C1 and adds a bounded operational lookahead:

- all dependency-ready players collected by C1 are always admitted first;
- an additional candidate is eligible only when it is unplaced, not yet
  dependency-ready, and every incomplete direct parent is already placed and
  has all of its own parents complete (at most one unfinished ancestor hop);
- let `B(t)` be the number of already placed, unfinished functions that still
  have an incomplete parent at the start of the window;
- the new frontier budget is `max(0, |N| - B(t))`;
- admit at most that many frontier players, using the same remaining-work and
  deterministic tie-break as C1;
- ready players are never capped, displaced, or omitted, so C2 is work
  conserving with respect to immediately executable work;
- ready players precede frontier players in initialization and update order,
  so frontier assignments consume only residual feasible capacity;
- final node choices still use strict Eq. (15); the frontier changes timing of
  binding/startup, not the payoff equation.

The invariant `B(t) + newly_admitted_frontier(t) <= |N|` must hold in every
window. There is no warm-first, finish-score, bounded-regret, baseline-expert,
or load-specific branch in either C1 or C2.

## 3. Formula and proof contract

The implementation must record and tests must verify:

- Eqs. (1)--(20), Eq. (15) strict argmax, Eq. (19) price feedback, QPR, and
  offline social-reference definitions are behaviorally unchanged;
- C0 output is unchanged under the new binary for fixed synthetic states;
- C1 has the identical ready player/candidate-node set as C0, differing only
  in order;
- C2 contains every C0 ready player exactly once and only the bounded one-hop
  frontier beyond that set;
- every stable complete output is independently certified as a strict PNE for
  the exact G10 player set and price vector;
- the existing weighted-potential argument remains applicable because each
  accepted unilateral move is still a strict utility improvement. Player
  order and feasible initialization affect equilibrium selection but not the
  finite-improvement property.

The new operational schema and reference-key tags must be unique. Reference
tables cannot cross C0/C1/C2 boundaries.

## 4. Result-free implementation gate

Before any tape, reference, or online outcome exists:

1. implement the two named modes and fail-closed configuration parsing;
2. emit window telemetry for ready count, unfinished-work priority range,
   frontier candidate count, outstanding speculative count, budget, admitted
   frontier count, ready omissions, and dispatch-class violations;
3. add unit tests for exact order, deterministic ties, zero/partial/full
   frontier budgets, all-ready retention, one-hop eligibility, no duplicate
   players, and C0 non-regression;
4. pass Rust formatting/tests and the complete Python protocol suite;
5. compile one release executable in a new, protected target directory and
   bind its SHA-256, Git commit, operational schema, and source inventory;
6. commit an implementation audit before constructing D96--D100 inputs.

Implementation tests may use synthetic states only. They cannot generate a
workload tape or expose a throughput/QPR outcome.

## 5. Fresh development bank and staged budget

Fresh development seeds are exactly D96--D100. They were absent at freeze
time and are disjoint from D66--D85, Q61--Q80, and any future confirmation
bank. Topology is homogeneous, node count is 20, and loads are low, middle,
and high using the frozen submission-v1 workload profiles. Within a
load/seed, C0/C1/C2 must share the exact tape, simulator seed, mechanism seed,
configuration, and common runtime.

Stages are strictly ordered:

1. create and hash exactly 15 base tapes (`3 loads x 5 seeds`);
2. build and hash exactly 45 candidate-specific offline references
   (`3 modes x 3 loads x 5 seeds`);
3. freeze a result-blind 45-run online selection;
4. execute every selected run once in manifest order and retain every first
   QC-valid result;
5. analyze C1/C2 against paired C0;
6. only if one candidate passes the control gate may a separate, pre-outcome
   strong-baseline addendum authorize `load_least`, `sche_FaaSRank`, and
   `sche_Hiku` on the same 15 tapes (45 additional runs).

No strong baseline is run speculatively. No formal Q61--Q80 candidate replay,
figure, or manuscript performance claim is authorized by this document.

## 6. Frozen control gate and selection rule

For each candidate, compute six mean ratios: throughput/C0 and QPR/C0 for each
of the three loads. All metrics use all five fixed seeds; QPR is computed per
run before averaging. Zero completion remains zero throughput with undefined
QPR and causes the candidate gate to fail without deleting the row.

A candidate passes only if all conditions hold:

1. 45/45 selected rows are present, uniquely paired, QC-valid, and use one
   bound runtime; every run has positive completion and defined QPR;
2. mean throughput and mean QPR are both strictly greater than C0 at low,
   middle, and high load (all six ratios `>1`);
3. at each load, candidate wins at least 3/5 paired seeds in throughput, 3/5
   in QPR, and 3/5 jointly;
4. neither throughput nor QPR falls below 0.80 of paired C0 for any seed;
5. every leave-one-seed-out mean difference is positive for both metrics at
   every load;
6. completion-ratio mean is not below C0 and request-latency mean is below C0
   at every load;
7. C1 preserves exact ready-set identity; C2 has zero ready omissions, zero
   frontier-bound/one-hop/dispatch violations, and positive frontier admission
   in at least 3/5 seeds at each load;
8. strict-PNE, offline-reference, runtime-identity, and complete-dispatch
   checks pass in every active window; and
9. per-load mean policy wall time is at most 1.50 times C0.

If both candidates pass, select the candidate maximizing the minimum of its
six primary ratios, then the mean of the six ratios, then joint paired wins;
an exact tie selects simpler C1. If neither passes, G10 stops and all outcomes
are frozen as negative development evidence. The rule cannot be weakened
after exposure.

## 7. Reporting, storage, and authorization boundary

The analyzer must retain raw run rows, paired differences, signs, ratios,
sample means/SDs, descriptive paired 95% intervals, and all leave-one-seed-out
means. It must also factor QPR changes into throughput, latency, and cost and
report completion, p95/p99 latency, queue area, utilization, cold/startup wait,
solver convergence, social-reference coverage, and scheduler overhead.

At each completed stage, hash inventories and ledgers are written before the
next stage. Canonical development evidence is archived to E after analysis;
only reproducible build caches and failed partial technical attempts may be
removed from C. QC-valid scientific observations are never deleted.

Until the implementation audit is committed:

- `g10_implementation_authorized=true`;
- `g10_tape_construction_authorized=false`;
- `g10_reference_build_authorized=false`;
- `g10_online_execution_authorized=false`;
- `g10_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

