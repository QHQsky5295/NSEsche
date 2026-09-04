# G14 deferral release-valve preregistration

Date: 2026-09-04 (Asia/Shanghai)

Parent diagnosis closure commit: `19c033a0cccf83f1c8680788c26a28fa0634b8a7`

Status: `implementation_only_no_g14_input_or_sampling`

## 1. Evidence boundary and mechanism question

G12 is closed negative development evidence. Its fixed per-window `N` prefix
preserved the intended order and all structural contracts, but could defer a
feasible global-ready backlog for adjacent windows. G13 then retained every
G12/C0 pair and found that isolated-only deferral had 3/3 joint wins, whereas
persistent deferral had 1/8. The isolated-minus-persistent mean log-throughput
and log-QPR contrasts were +0.024614 and +0.100563 and remained positive in
all 15 leave-one-run-out recomputations.

G14 asks one prospectively fixed question: can the first window of a ready-set
overflow retain G12's bounded release, while a one-bit state opens a valve on
subsequent adjacent overflow windows so feasible work cannot accumulate under
repeated bounding?

G13 is diagnostic and non-causal. It does not validate G14. D101--D105 cannot
be used to score, select, or revise G14, and no G12 outcome may be relabeled as
G14 evidence.

## 2. Exact candidate state machine

The only candidate is `ready_global_deferral_release_valve`. For scheduler
window `t`, let `A_t` be the exact C0 sequence of dependency-ready,
not-yet-placed players after the existing individual placement-feasibility
filter, in the unchanged deterministic order

`(request arrival frame, request ID, topological rank, function ID)`.

Let `N` be the configured node count and define the current counterfactual
overflow bit

`o_t = 1[|A_t| > N]`.

Let `v_t` be the valve state at entry to the window, initialized once per run
as `v_0 = 0`. G14 fixes the admitted sequence as

`S_t = first N players of A_t`, if `v_t = 0` and `o_t = 1`; otherwise
`S_t = A_t`.

After the admission decision, the next state is exactly

`v_(t+1) = o_t`.

Thus `v_t` is precisely the previous window's overflow bit. While consecutive
counterfactual overflows continue, only the first is bounded and every later
window releases the complete feasible-ready sequence. The first window with
`|A_t| <= N` admits all players and closes the valve for the next window.
The state update uses current pre-outcome readiness only; actual throughput,
QPR, latency, cost, completion, queue outcomes, solver outcomes, and future
arrivals are unavailable to it.

This is a one-bit, load-blind, seed-blind, parameter-free rule. `N` is the
system's physical node count, not a fitted threshold. No multiplier,
ready-count search, request cohort, remaining-work key, frontier, lookahead,
warm override, baseline expert, outcome label, or hidden exception is allowed.

## 3. Fixed invariants and proof obligations

For every window, the implementation must fail closed unless all of the
following hold:

1. every element of `A_t` is dependency-ready and individually feasible;
2. `A_t` preserves the exact legacy C0 order;
3. `S_t` is an exact prefix of `A_t`;
4. if `v_t=0` and `|A_t|>N`, then `|S_t|=N` and
   `|A_t|-|S_t|>0`;
5. otherwise `S_t=A_t` and no feasible player is deferred;
6. `v_(t+1)=1[|A_t|>N]` exactly;
7. the solver assignment set equals `S_t`; and
8. the prepared dispatch sequence and count equal `S_t`.

These rules imply three exact equivalences useful for audit:

- with no current overflow, G14 equals both C0 and G12 on the active set;
- on the first window of an overflow episode, G14 equals G12; and
- on every later adjacent overflow window, G14 equals C0.

They also imply that actual positive-deferral windows cannot be adjacent:
after any bounded overflow, the next state is open, and an open window defers
zero feasible players. Therefore the longest actual positive-deferral episode
must be at most one window. This is a structural invariant, not a performance
gate or empirical expectation.

## 4. Formula-preservation contract

The manuscript's displayed Eqs. (1)--(20), utility components and weights,
strict Eq. (15) best response, Eq. (19) feedback, social-welfare definition,
QPR definition, price signal, feasibility relation, and offline-reference
definition remain unchanged.

G14 changes only the finite active player sequence presented to the existing
game in each scheduling window. Conditional on `S_t`, the same action sets,
utilities, strict best-response solver, dispatch, and offline social-utility
reference apply. The existing weighted-potential and finite-improvement
termination reasoning therefore applies without modification to every fixed
finite `S_t`. Runtime certification must evaluate strict-PNE status and the
offline reference on exactly that admitted set. A dispatched assignment
outside the certified set, an absent admitted assignment, or a mismatched
operational/reference identity invalidates the run.

The release valve is an operational admission layer that may be described in
new prose only if it later passes every gate. It is not permission to alter a
displayed formula or weaken a formula check.

## 5. Implementation and telemetry contract

Implementation may add exactly one operational identity, operational schema
version 11, reference-key schema version 12, and reference tag 17. C0, G12,
all baselines, and all existing tags must remain behaviorally unchanged. The
dedicated release binary must be source-commit-bound and retained outside Git
in a new protected target directory.

Each G14 scheduler-window record must include:

- dependency-ready and feasible-ready counts;
- configured node count and current overflow bit;
- valve state before the decision and the exact next state;
- one mutually exclusive mode: `below_limit`, `first_overflow_bounded`,
  `persistent_overflow_release`, or `post_overflow_reset`;
- effective admission limit, admitted count, and deferred feasible count;
- order-sensitive hashes of `A_t` and `S_t` and the admitted arrival range;
- readiness, feasibility, legacy-order, prefix, admission-rule,
  state-transition, and dispatch-set violation counts; and
- commands prepared/sent, scale-up commands, strict-PNE, reference, and
  runtime fields already required by G12.

Tests must cover initialization; empty, below-`N`, equal-`N`, and above-`N`
sets; isolated and multi-window overflow sequences; reset and re-trigger;
stable feasibility filtering; order and prefix preservation; new-arrival
non-displacement in a bounded window; full release while open; no adjacent
positive deferral; dispatch containment; C0/G12 noninterference; schema and
tag separation; and unchanged strict-best-response/formula alignment.

At this stage source, tests, result-free protocol code, and a dedicated release
build are allowed. No G14 tape, offline reference, online run directory,
metric, or candidate outcome may be created before the implementation audit is
committed.

## 6. Frozen development population

After a separate implementation audit and zero-result protocol freeze, G14
will use fresh paired seeds D106--D110:

- topology: homogeneous;
- nodes: 20;
- load order: low, middle, high under the unchanged formal profiles;
- arms: C0 `ready_order` and G14
  `ready_global_deferral_release_valve`;
- product: 2 arms x 3 loads x 5 paired seeds = 30 online runs;
- inputs: 15 new shared candidate/control tapes and 30 mode-specific offline
  references; and
- execution: exact manifest order, retaining one QC-valid observation per
  cell.

The C0 control is rerun with the same future binary and same tape. No prior
control or candidate observation may substitute. All QC-valid outcomes,
including ties, losses, zero completion, undefined QPR, convergence limits,
and nonpositive references, remain visible. Only crash, panic, OOM, I/O
failure, timeout, truncation, hash mismatch, non-finite required raw fields,
frame discontinuity, or count-invariant failure is technically retryable under
the identical seed, tape, configuration, and binary, up to the existing global
three-attempt limit. Performance is never a retry reason.

## 7. Frozen development gate

The analyzer and exact 30-row selection must be frozen while the online parent
is absent. G14 qualifies only if all nine conditions pass:

1. exactly 30 unique paired QC-valid rows have one registered runtime identity,
   identical within-pair tape hashes, positive completion, and defined QPR;
2. G14 arithmetic-mean throughput and QPR are each strictly above C0 at low,
   middle, and high load;
3. G14 wins throughput and QPR jointly in at least 3/5 paired seeds at every
   load, and wins QPR alone in at least 3/5 at every load;
4. every per-seed G14/C0 throughput and QPR ratio is at least 0.80;
5. every leave-one-seed-out G14-minus-C0 arithmetic-mean difference is positive
   for throughput and QPR at every load;
6. G14 mean completion ratio is not below C0 and mean latency is below C0 at
   every load;
7. at least one seed per load contains a bounded first-overflow window; at
   least three of 15 runs across at least two loads contain a persistent-
   overflow release window; every candidate run has longest actual deferral
   episode at most one; and all seven implementation violation totals are zero;
8. every active G14 and C0 window satisfies the registered strict-Eq.-(15)
   PNE/reference/dispatch/runtime identity contract, with every exception
   retained and causing failure; and
9. G14/C0 arithmetic-mean placement-policy wall-time ratio is at most 1.50 at
   every load.

The report must retain every per-seed metric, paired ratio/sign, sample SD,
95% descriptive interval, leave-one-seed-out value, QPR factorization,
activation count, exception, and overhead observation. No seed may be dropped,
replaced, down-weighted, extended, or rerun because of performance. No gate or
candidate rule may be weakened after any G14 metric exists.

If all nine conditions pass, only a separately preregistered strong-baseline
addendum is authorized. C0 superiority alone is not paper-ready leadership.
If any condition fails, the complete D106--D110 product is archived; G14
cannot enter confirmation or formal replay, and no result-conditioned
release-valve variant or seed extension is allowed.

## 8. Stage authorization at this checkpoint

- `g14_source_edit_authorized=true`;
- `g14_test_and_compile_authorized=true`;
- `g14_implementation_audit_authorized=true`;
- `g14_protocol_manifest_construction_authorized=false`;
- `g14_input_construction_authorized=false`;
- `g14_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`; and
- `paper_claim_authorized=false`.

Every later transition requires a separate hash-bound audit commit.

