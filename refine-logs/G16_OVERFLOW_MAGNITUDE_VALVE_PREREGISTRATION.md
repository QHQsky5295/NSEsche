# G16 Overflow-Magnitude-Gated Release-Valve Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Parent diagnosis closure commit: `1e81036559567641c05cfc443ede24d9f3590e32`

Status: `implementation_only_no_g16_input_or_sampling`

## 1. Evidence boundary and prospective question

G14 is permanently closed negative development evidence. Its parameter-free
release valve improved mean throughput and QPR at low and high load, but its
unconditional first-overflow bound reduced middle-load throughput and failed
the frozen across-load gate. G15 then analyzed every retained G14/C0 pair and
selected `h=1.25` from the prospectively fixed set `{1.25, 1.5, 2, 4}`. At
that threshold, balanced accuracy, sensitivity, and specificity were all
0.80, both primary group-effect contrasts were positive in every leave-one-
run-out recomputation, and the positive and negative groups each contained all
three loads.

G16 asks one new prospective question: can the G14 bound be restricted to a
material *first* overflow, observed before the placement decision, while the
same one-bit release valve prevents adjacent bounded windows?

G15 is explicit development fitting and is not G16 validation. D106--D110
cannot score, tune, select, repair, or confirm G16. The threshold, state
machine, telemetry, population, analysis gate, and stopping rule below are
fixed before any D111--D115 workload, reference, or result exists.

## 2. Exact candidate state machine

The only candidate operational identity is
`ready_global_overflow_magnitude_release_valve`. For scheduler window `t`, let
`A_t` be the exact C0 sequence of dependency-ready, not-yet-placed players
after the existing individual placement-feasibility filter, in the unchanged
deterministic order

`(request arrival frame, request ID, topological rank, function ID)`.

Let `F_t=|A_t|`, let `N>0` be the configured physical node count, and define

- current overflow `o_t = 1[F_t>N]`;
- entry valve state `v_t`, initialized once per run as `v_0=0`; and
- material first overflow
  `b_t = 1[v_t=0 and o_t=1 and 4F_t>=5N]`.

G16 admits

`S_t = first N players of A_t` if `b_t=1`; otherwise `S_t=A_t`.

After admission, the only cross-window update is

`v_(t+1)=o_t`.

The integer comparison `4F_t>=5N` is the exact, floating-point-free form of
`F_t/N>=1.25`; it must be evaluated in a widened integer type. It is not a
tunable multiplier. A mild first overflow (`F_t>N` but `4F_t<5N`) releases
all feasible-ready work and still opens the valve for the next adjacent
overflow. Therefore a later window in the same overflow episode can never be
retrospectively reclassified as a first overflow.

The rule is load-blind, seed-blind, method-blind, and outcome-blind. It may
inspect only the current pre-decision feasible-ready count, fixed physical node
count, and one previous-overflow bit. Workload profile, arrival-rate label,
seed, queue outcome, throughput, QPR, latency, cost, completion, solver
outcome, baseline result, and future arrival information are forbidden.

## 3. Structural invariants and proof obligations

For every G16 scheduler window, the implementation must fail closed unless:

1. every member of `A_t` is dependency-ready and individually feasible;
2. `A_t` preserves the exact legacy C0 order;
3. `N>0`, and the logged widened-integer comparison equals `4F_t>=5N`;
4. `S_t` is an exact prefix of `A_t`;
5. if and only if `v_t=0`, `F_t>N`, and `4F_t>=5N`, then
   `|S_t|=N` and `F_t-|S_t|>0`;
6. otherwise `S_t=A_t` and no feasible player is deferred;
7. `v_(t+1)=1[F_t>N]` exactly;
8. the solver assignment set equals `S_t`; and
9. the prepared and sent dispatch sequences/counts equal `S_t`.

These obligations imply four exact equivalences:

- without current overflow, G16 equals C0;
- on a below-threshold first overflow, G16 equals C0;
- on a material first overflow, G16 equals G14 and G12; and
- on every subsequent adjacent overflow, G16 equals G14 and C0.

Actual positive-deferral windows cannot be adjacent, so the longest positive-
deferral streak is at most one window. This is a structural invariant, not an
empirical target.

## 4. Formula-preservation contract

The manuscript's displayed Eqs. (1)--(20), utility terms and weights, strict
Eq. (15) best response, Eq. (19) feedback, social-welfare definition, QPR
definition, price signal, feasibility relation, and offline-reference
definition remain byte-for-byte conceptually unchanged.

G16 changes only the finite active-player sequence presented to the existing
game in a scheduling window. Conditional on `S_t`, action sets, utility
evaluation, strict best-response updates, deterministic tie-breaking,
dispatch, and the offline social-utility reference are unchanged. Because
`S_t` is finite, the existing weighted-potential/finite-improvement argument
continues to establish finite termination at a strict Eq. (15) pure Nash
equilibrium for every stable inner solve. The operational gate creates no new
payoff term and requires no modification of a displayed formula.

Runtime certification and the offline reference must bind to exactly `S_t`.
Any dispatched assignment outside the certified admitted set, absent admitted
assignment, reference-key mismatch, non-strict best response, or operational
identity mismatch invalidates the run.

## 5. Implementation and telemetry contract

Implementation may add exactly one operational identity, operational schema
version 12, reference-key schema version 13, and reference tag 18. Existing
C0, G12, G14, all baselines, schemas, and tags must remain behaviorally
unchanged. A dedicated source-commit-bound release binary must be retained
outside Git in the new protected directory
`serverless_sim/target_g16_overflow_magnitude_valve_impl/`.

Each G16 scheduler-window record must include:

- dependency-ready count, feasible-ready numerator `F_t`, node-count
  denominator `N`, and current overflow;
- fixed threshold numerator/denominator `5/4`, widened comparison operands
  `4F_t` and `5N`, and the exact magnitude-gate result;
- valve state before and after the decision and the material-first-overflow
  decision bit;
- exactly one mode: `below_limit`,
  `first_overflow_below_magnitude_release`,
  `first_overflow_magnitude_bounded`, `persistent_overflow_release`, or
  `post_overflow_reset`;
- effective admission limit, admitted and deferred feasible counts,
  order-sensitive hashes of `A_t` and `S_t`, and admitted arrival range;
- readiness, feasibility, legacy-order, prefix, magnitude-comparison,
  admission-rule, state-transition, solver-set, and dispatch violation counts;
  and
- commands prepared/sent, scale-up commands, strict-PNE, reference, timing,
  and runtime-identity fields already required for G14.

Tests must cover zero-node rejection; initialization; empty, below-`N`,
equal-`N`, and above-`N` sets; exact integer boundaries immediately below, at,
and above `5N/4`, including non-divisible `N`; isolated and multi-window
overflow; a mild first overflow followed by a material persistent overflow;
reset and re-trigger; stable feasibility filtering; legacy order and prefix;
new-arrival non-displacement in a bounded window; full release while open; no
adjacent positive deferral; solver/dispatch containment; C0/G12/G14
noninterference; schema/tag separation; and unchanged strict-best-response and
formula alignment.

At this stage, source, tests, result-free protocol support, and a dedicated
binary are allowed. No G16 manifest, D111--D115 tape, offline reference,
online run, throughput, QPR, or candidate outcome may exist before a separate
implementation audit is committed.

## 6. Frozen development population

After the implementation audit and a separate zero-result protocol freeze,
G16 will use fresh paired development seeds D111--D115:

- topology: homogeneous;
- nodes: 20;
- load order: low, middle, high under the unchanged formal profiles;
- arms: C0 `ready_order` and G16
  `ready_global_overflow_magnitude_release_valve`;
- product: 2 arms x 3 loads x 5 paired seeds = 30 online runs;
- inputs: 15 new shared candidate/control tapes and 30 mode-specific offline
  references; and
- execution: exact manifest order, retaining the first QC-valid observation
  for every cell.

No D111--D115 experimental artifact existed at this preregistration. The sole
text occurrence was an old protocol mutation test that replaces a valid G14
seed with `D111` and expects rejection; it contains no workload or result.

The C0 control is rebuilt and rerun with the same future G16 binary and paired
tape. No historical C0 or candidate row may substitute. Every QC-valid tie,
loss, zero completion, undefined QPR, convergence limit, and reference issue
remains visible. Only crash, panic, OOM, I/O failure, timeout, truncation,
hash mismatch, non-finite required raw fields, frame discontinuity, or count-
invariant failure is technically retryable under the identical seed, tape,
configuration, and binary, up to the existing global three-attempt limit.
Performance is never a retry reason.

## 7. Frozen development gate

The analyzer and exact 30-row online selection must be frozen while the online
parent is absent. G16 qualifies only if all nine conditions pass:

1. exactly 30 unique paired QC-valid rows have one registered runtime identity,
   identical within-pair tape hashes, positive completion, and defined QPR;
2. G16 arithmetic-mean throughput and QPR are each strictly above C0 at low,
   middle, and high load;
3. at every load, at least one of five pairs is a strict joint throughput/QPR
   win and at least four of five pairs are joint non-losses (both ratios at
   least 1.0); exact ties are retained as non-losses, never relabeled as wins;
4. every per-seed G16/C0 throughput and QPR ratio is at least 0.80;
5. every leave-one-seed-out G16-minus-C0 arithmetic-mean difference is
   nonnegative for both primary metrics at every load, and at least four of
   five omissions per metric/load are strictly positive;
6. G16 mean completion ratio is not below C0 and G16/C0 mean latency is at
   most 1.05 at every load;
7. at least one seed per load contains a material-first-overflow bounded
   window; below-threshold first-overflow release and persistent-overflow full
   release each occur in at least three runs spanning at least two loads;
   every candidate run has longest positive-deferral streak at most one; and
   all nine implementation violation totals are zero;
8. every active G16 and C0 window satisfies the registered strict-Eq.-(15)
   PNE/reference/solver/dispatch/runtime identity contract, with every
   exception retained and causing failure; and
9. the G16/C0 arithmetic-mean placement-policy wall-time ratio is at most
   1.50 at every load.

Condition 3 prospectively treats exact no-op ties as non-losses because G16 is
designed to equal C0 outside material first-overflow windows; condition 2
still requires a strict aggregate improvement at every load, and condition 5
prevents that conclusion from reversing after any single-seed omission. No
tie contributes a win.

The report must retain every per-seed metric and ratio, win/tie/loss state,
sample SD, descriptive 95% interval, leave-one-seed-out value, QPR
factorization, activation mode/count, threshold comparison, runtime exception,
and overhead observation. No seed may be dropped, replaced, down-weighted,
extended, or rerun because of performance, and no gate may be weakened after
any G16 metric exists.

Passing all nine conditions would authorize only a separately preregistered
strong-baseline addendum. It would not establish paper-ready leadership. If
any condition fails, the complete D111--D115 product is archived, G16 cannot
enter confirmation or formal replay, and this magnitude-gated family closes
without threshold revision or result-conditioned seed extension.

## 8. Stage authorization at this checkpoint

- `g16_source_edit_authorized=true`;
- `g16_test_and_compile_authorized=true`;
- `g16_implementation_audit_authorized=true`;
- `g16_protocol_manifest_construction_authorized=false`;
- `g16_input_construction_authorized=false`;
- `g16_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`; and
- `paper_claim_authorized=false`.

Every later authorization transition requires a separate hash-bound audit
commit.
