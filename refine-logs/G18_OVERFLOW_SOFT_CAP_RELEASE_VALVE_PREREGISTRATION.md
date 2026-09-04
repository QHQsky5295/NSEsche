# G18 Overflow Soft-Cap Release-Valve Preregistration

Date: 2026-09-05 (Asia/Shanghai)

Parent closure commits: G16 `c604515`, G17 `1335c32`

Status: `preregistered_implementation_only_no_input_or_sampling_authorized`

## 1. Mechanism question and rationale

G14 showed that a one-window overflow intervention can improve low/high mean
throughput and QPR, but its hard admission limit `N` slightly reduced middle
throughput. G16 attempted to make that intervention safer by applying the
same hard `N` limit only above a fixed first-overflow magnitude. The gate
remained discontinuous: an event immediately below the threshold admits all
`F` players, whereas an event immediately at the threshold admits only `N`.
G16 then produced a severe middle D112 loss. G17 closed further fixed-threshold
classification because magnitude did not identify safe runs.

G18 tests a distinct action-design hypothesis rather than another classifier:

> A load-blind soft capacity cap at 125% of physical node count can preserve
> one-window overload smoothing while reducing the placement starvation caused
> by the hard `N` cap.

The value 125% is not fitted to a G17 outcome. It is the already frozen G15/G16
capacity boundary, reinterpreted as admitted burst capacity. No alternative
cap, threshold, cooldown, dose budget, queue rule, or load-specific mechanism
will be screened in G18.

## 2. Exact operational rule

Let `F` be the number of dependency-ready, placement-feasible players in the
current scheduler window and let `N>0` be configured node count. Define the
integer soft cap

`C = ceil(5N/4) = (5N+3)//4`.

The scheduler retains one bit `overflow_open`, initialized false and reset on
every non-overflow window. For each window:

1. `current_overflow = F>N`;
2. `first_overflow = !overflow_open && current_overflow`;
3. if `first_overflow && F>C`, admit exactly the first `C` players from the
   unchanged feasible-ready order;
4. otherwise admit all `F` feasible-ready players; and
5. set `overflow_open = current_overflow`.

Thus positive deferral occurs only in a material first-overflow window and can
never persist in adjacent windows. `F=C` admits all players. Every admitted
set is a prefix of the legacy, dependency-ready, individually feasible order.
Deferred players remain unplaced and are reconsidered on the next scheduler
window.

The method name is
`ready_global_overflow_soft_cap_release_valve`. It must use operational schema
13, offline-reference schema 14, and reference-key tag 19. Eqs. (1)--(20),
strict Eq. (15), Eq. (19), QPR, the price/reference definitions, HPA, workload,
and the within-admitted-set equilibrium solver remain unchanged.

## 3. Result-free implementation freeze

Before creating D116 input artifacts:

- add only the named operational refinement and exact selector;
- add widened-integer soft-cap operands and checked arithmetic;
- log `soft_cap_numerator=5`, `soft_cap_denominator=4`, exact rounded cap,
  applicability, material-pass state, five admission modes, before/after bit,
  admitted/deferred counts, order fingerprints, and violations;
- add directed Rust and protocol tests for below limit, first overflow at/below
  cap, material first overflow, persistent overflow, reset, integer rounding,
  prefix/feasibility, and one-window deferral; and
- freeze one release binary and a complete source/binary audit.

The implementation commit and binary must precede every tape, reference, and
online result. The G16 binary and protected target remain immutable.

## 4. Fixed development population

After the implementation freeze, construct exactly:

- topology: homogeneous, 20 nodes;
- loads in paper order: low, middle, high;
- fresh fixed seeds: `D116`, `D117`, `D118`, `D119`, `D120`;
- methods: C0 `ready_order` and G18
  `ready_global_overflow_soft_cap_release_valve`;
- one base tape per load/seed, shared exactly by both methods;
- one method-specific offline reference per load/seed/method; and
- 30 online runs total.

Every first QC-valid outcome is retained. A technical retry may repeat only
the same seed/tape/config/binary and only for crash, panic, OOM, I/O failure,
truncation, hash mismatch, nonfinite required fields, discontinuous frames, or
count/inventory corruption. A valid unfavorable result, exact tie,
zero-completion result, inner/outer cap, or nonpositive reference is not a
retry. D111--D115 remain diagnosis-only and cannot validate G18.

## 5. Frozen development gate

Freeze the exact 30-row selection and analyzer before the online result
directory exists. G18 qualifies only if all nine conditions pass:

1. all 30 unique rows are first QC-valid, form 15 same-tape C0/G18 pairs, have
   positive defined throughput/QPR, and use one frozen runtime identity;
2. G18 arithmetic-mean throughput and QPR are each strictly above C0 at low,
   middle, and high;
3. every load has at least one strict joint win and at least four joint
   nonlosses among five paired seeds;
4. every per-seed G18/C0 throughput and QPR ratio is at least 0.80;
5. for each load and primary metric, all five leave-one-seed-out mean
   differences are nonnegative and at least four are strictly positive;
6. at every load, mean completion ratio is not below C0 and mean latency is at
   most 1.05 times C0;
7. exact soft-cap/state telemetry reconstructs; at least one seed per load has
   positive material soft-cap deferral; at least three runs spanning two loads
   exercise an at/below-cap first-overflow release; at least three runs
   spanning two loads exercise persistent-overflow release; longest positive
   deferral episode is at most one window; and all readiness, feasibility,
   legacy-order, prefix, bound, cap-arithmetic, admission-rule,
   state-transition, and dispatch-set violations are zero;
8. strict Eq. (15), PNE/reference/dispatch coverage, the complete retained
   runtime-exception table, and runtime binary identity pass the frozen G18
   analyzer; and
9. mean G18/C0 placement-policy wall-time ratio is at most 1.50 at each load.

QPR is fixed as throughput divided by drained mean latency and simulator
internal cost per completed request. All arithmetic means, paired rows,
descriptive intervals, and exact ties remain visible.

## 6. Staged authorization and stopping

This document authorizes only implementation, tests, release build, and an
implementation audit. After that audit is committed, a separately audited
manifest may authorize tape capture, followed by references, analyzer/selection
freeze, and one online batch in distinct stages. No result-bearing stage is
authorized early.

If any gate condition fails, G18 is permanently closed with all valid rows and
a compact evidence package. No cap adjustment or D116--D120 reuse follows. If
all nine pass, this development result authorizes only a separate preregistered
strong-baseline addendum on a fresh bank; it does not itself enter a paper
figure or authorize formal confirmation.

At this checkpoint:

- `g18_implementation_authorized=true`;
- `g18_input_construction_authorized=false`;
- `g18_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`; and
- `formal_progression_authorized=false`.
