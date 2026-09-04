# G12 global-ready player admission preregistration

Date: 2026-09-04 (Asia/Shanghai)

Base closure commit: `62dbab4`

Status: `implementation_only_no_g12_input_or_sampling`

## 1. Why this is a new mechanism family

G9 and G10/G11 close request-cohort backpressure, remaining-work ordering,
bounded frontier, and ready-count switching. G12 does not reopen any of those
choices. Its source-derived target is the command-release boundary.

The current C0 path collects every dependency-ready, not-yet-placed player,
filters individual placement feasibility, solves one strict game over the
whole feasible set, and dispatches every final assignment in one command
batch. The simulator's request queue is explicitly unbounded. Once dispatched,
a function is bound in `request.fn_node` and is no longer eligible for a later
scheduler-window decision. Thus a transient ready burst can irrevocably place
far more new work than the configured node count before the next observation.

G9 controlled the wrong abstraction: it first retained at most `N` oldest live
requests and only then collected their dependency-ready functions. Its retained
evidence shows windows with roughly 0.24--3.24 schedulable players in the
cohort while thousands of ready players could exist outside it. G12 instead
starts from the complete global dependency-ready set and limits only the
number of newly released feasible players. It cannot create G9's request-level
dependency blocking.

The fixed candidate is named `ready_global_player_admission_n`. This is the
first candidate in a new command-admission family, not a fourth ordering,
frontier, warm-initialization, or request-cohort rule.

## 2. Frozen candidate semantics

For scheduling window `t`, let `A_t` be the exact C0 dependency-ready,
not-yet-placed player sequence after the existing per-player feasibility
filter, in the unchanged C0 order:

`(request arrival frame, request ID, topological rank, function ID)`.

Let `N` be the configured node count. G12 admits the exact prefix

`S_t = first min(|A_t|, N) players of A_t`.

Only `S_t` enters the existing Nash solver and dispatch batch. Every feasible
player in `A_t \ S_t` remains unplaced and is reconsidered in the next window.
Infeasible ready players retain the existing waiting behavior. Newer arrivals
cannot displace an older ready player because the order is unchanged and the
prefix is taken after global ready collection.

The rule is fixed and load-blind. It may inspect only dependency readiness,
existing placement feasibility, the legacy deterministic order, and configured
node count. It may not inspect workload/load labels, seed, baseline identity,
realized throughput/QPR/latency/cost, future arrivals, or offline outcomes. It
has no tunable multiplier or threshold.

The release layer must be work-conserving under its fixed service budget:

- if `A_t` is empty, `S_t` is empty;
- otherwise `1 <= |S_t| <= N`;
- `|S_t| = min(|A_t|, N)` exactly;
- every admitted player is dependency-ready and feasible;
- every dispatched player is admitted; and
- the admitted order and set equal the exact C0-prefix construction.

No frontier player, pre-ready player, request cohort, warm override,
remaining-work key, utility-regret guard, result-conditioned switch, or
cross-window hidden exception is allowed.

## 3. Formula and proof contract

The manuscript's displayed Eqs. (1)--(20), utility components and weights,
strict Eq. (15) best response, Eq. (19) feedback, social-welfare definition,
QPR definition, price signal, feasibility relation, and offline-reference
definition are unchanged.

G12 changes only the finite per-window active player set presented to the same
game. For any fixed finite `S_t`, the existing weighted-potential argument and
finite-improvement termination reasoning apply without alteration. Runtime
certification must evaluate strict-PNE status and the offline social-utility
reference on exactly `S_t`. A result is invalid if a dispatched assignment is
outside the certified set or if the solver/reference identity differs from the
candidate's registered operational tag.

This operational admission layer is not evidence that the paper's equations
were changed. It is also not allowed to weaken a formula check to obtain a
performance result.

## 4. Required implementation and telemetry

Implementation must add exactly one operational identity and a new reference
tag without changing C0 or any baseline. It must record per window:

- global dependency-ready count before feasibility;
- feasible ready count `|A_t|`;
- admission limit `N`, admitted count, and deferred feasible count;
- exact ordered-set hashes before and after admission;
- minimum/maximum admitted arrival frame when nonempty;
- readiness, feasibility, prefix, bound, and dispatch-set violations;
- commands prepared/sent and scale-up commands for the admitted set; and
- strict-PNE/reference/runtime fields already required by G10.

The runtime must fail closed on any nonzero readiness, feasibility, prefix,
bound, or dispatch-set violation. Tests must cover zero, below-limit,
exact-limit, and above-limit sets; stable filtering; preservation of C0 order;
new-arrival non-displacement; dispatch containment; C0 noninterference; schema
identity; reference-tag separation; and unchanged strict-best-response mode.

The implementation stage may edit source, tests, and result-free protocol
code and may compile a dedicated release binary. It may not create a G12
workload tape, offline reference, online run directory, or metric result.

## 5. Frozen development product

After a separate implementation audit and a separate zero-result protocol
freeze, development will use fresh paired seeds D101--D105:

- topology: homogeneous;
- nodes: 20;
- loads: low, middle, high using the unchanged formal load profiles;
- arms: C0 `ready_order` and G12 `ready_global_player_admission_n`;
- product: 2 arms x 3 loads x 5 paired seeds = 30 online runs;
- tapes: 15 shared candidate/control workload tapes;
- references: 30 mode-specific offline-reference dependencies; and
- execution: exact manifest order, one retained QC-valid observation per cell.

D101--D105 have not been used by G1--G11. The control must be rerun under the
same future binary and tape; no earlier C0 observation may substitute for it.
All valid rows, including zero completion or adverse candidate results, remain
in the product. Only crash, panic, OOM, I/O failure, timeout, truncation, hash
mismatch, non-finite required metrics, frame discontinuity, or count-invariant
failure is retryable under the unchanged seed/tape/config/binary, up to the
global three-attempt technical limit.

## 6. Development gate fixed before implementation

The analyzer must be frozen before the online parent exists. G12 qualifies only
if all conditions pass:

1. exactly 30 unique paired, QC-valid rows have positive completion, defined
   QPR, identical tape pairing, and one registered runtime identity;
2. candidate arithmetic-mean throughput and QPR are each strictly above C0 at
   low, middle, and high;
3. candidate wins throughput and QPR jointly in at least 3/5 seeds at each
   load, and wins QPR alone in at least 3/5 at each load;
4. every candidate/control throughput and QPR ratio is at least 0.80;
5. every leave-one-seed-out candidate-minus-C0 mean is positive for throughput
   and QPR at each load;
6. candidate mean completion ratio is not below C0 and mean latency is below
   C0 at each load;
7. admission activates in at least 3/5 seeds at each load, every activated run
   has deferred feasible players, and all six implementation violation counts
   are zero in all candidate runs;
8. every active candidate window is strict-PNE certified with its exact
   offline reference, apart from already frozen universal runtime exceptions
   that must be retained and cannot be candidate-specific; and
9. candidate/C0 mean placement-policy wall-time ratio is at most 1.50 at each
   load.

The analyzer reports all per-seed metrics, ratios, paired signs, sample SDs,
95% descriptive intervals, and leave-one-seed-out means. No seed may be
dropped, replaced, down-weighted, or rerun because of performance. No gate may
be weakened after metrics exist.

If the gate passes, a separate strong-baseline addendum is required before any
confirmation design. Passing against C0 alone does not establish paper-ready
leadership. If it fails, the complete D101--D105 product is archived and G12
cannot enter confirmation or formal replay.

## 7. Stage authorization at this checkpoint

- `g12_source_edit_authorized=true`;
- `g12_test_and_compile_authorized=true`;
- `g12_implementation_audit_authorized=true`;
- `g12_protocol_manifest_construction_authorized=false`;
- `g12_input_construction_authorized=false`;
- `g12_online_execution_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`; and
- `paper_claim_authorized=false`.

Each later transition requires a separate hash-bound audit commit. No output
from G9--G11 may be relabeled as G12 validation.
