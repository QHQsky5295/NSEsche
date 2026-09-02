# M1 Completion-Guard Redesign Preregistration

Date: 2026-09-02 (Asia/Shanghai)

Status: preregistered before source modification, tape capture, or D21--D40 execution

Phase: non-formal mechanism development only

## Evidence boundary and design question

The retained D01--D20 `ready_order` qualification failed the strict
throughput/QPR gate in all six E1 cells.  The subsequently preregistered D01--D05
decision-neutral diagnosis established that:

- a running-warm alternative exists for 79.56% of 273,972 assigned players;
- 29.40% of those alternatives are bypassed;
- the bypass has positive paper-utility advantage in all six cells;
- five cells, including both high-load cells, have a worse projected finish
  score after the bypass;
- homogeneous middle load is the exception, where a starting path has a better
  projected finish score on average.

Therefore neither supply expansion nor an unconditional warm-first rule is the
appropriate next test.  The design question is whether completion-aware ranking
inside a bounded paper-utility loss envelope can improve both throughput and
run-level QPR while preserving the original utility as an explicit quality
floor.

## Frozen mechanism family

The paper utility, price signal, feasible set, HPA, workload, reference, and
Eqs. 1--20 are unchanged.  For every player, the current implementation first
evaluates the same dynamically admissible candidates (`can_add`) and their
published utility values.

Let `U_max` be the maximum candidate utility and define the operational
admissible set in implementation/prose as candidates whose utility is no lower
than `U_max - rho * max(1, abs(U_max))`.  This is a new operational guard, not a
replacement for the published utility formula.

For a guarded candidate:

1. identify the current utility-best candidate exactly as `ready_order` does;
2. retain only candidates inside the frozen utility guard;
3. select the smallest existing projected-finish score
   (`startup_remaining + runnable + starting_resident + pressure`);
4. if finish scores are equal within the existing numerical epsilon, prefer
   higher paper utility, then the current node, then lower node ID;
5. keep the utility-best candidate unless the guarded candidate has a strictly
   smaller projected-finish score beyond epsilon.

The three and only three screen candidates are:

1. `ready_order` -- unchanged control, simplicity order 0;
2. `guarded_finish_05` -- `rho = 0.05`, simplicity order 1;
3. `guarded_finish_15` -- `rho = 0.15`, simplicity order 2.

The two logarithmically separated guards test a conservative and a permissive
envelope without a parameter sweep.  No load-specific radius, seed-specific
radius, hidden fallback, online outcome, baseline score, future completion, or
offline hindsight may enter a decision.

## Fresh development bank

- All redesign selection uses D21--D40.  D01--D20 are diagnosis/failed-family
  evidence and are forbidden for redesign selection.
- Screen seeds: D21--D25 fixed before capture.
- Qualification seeds: D21--D40 fixed before capture.
- Cells: homogeneous and heterogeneous x low, middle, and high, 20 nodes.
- Screen: 90 runs = 3 candidates x 6 cells x 5 fixed seeds.
- Qualification, if authorized: 1,200 runs = 10 methods x 6 cells x 20 seeds.
- All candidates/methods in a cell reuse the exact same bound tape.
- Offline social references remain method-state matched and are built before
  online result inspection.
- The ordinary result-blind technical failure policy applies.  No replacement
  seed or outcome-conditioned rerun is allowed.

## Frozen screen selection and family-admission rule

Apply the existing global maximin rule to the complete 90-run screen:

1. maximize the minimum candidate-relative mean ratio across throughput and
   QPR over all six cells;
2. then maximize the mean of those twelve ratios;
3. then maximize the number of cells jointly first in both metrics;
4. then use the declared simplicity order.

If `ready_order` wins, the completion-guard family is rejected and no
qualification is authorized.  A guarded candidate must win the same global
rule; there is no per-load mechanism choice.

## Qualification gate

If a guarded candidate wins, freeze its source and binary before qualification.
On the complete D21--D40 ten-method batch, NSESche must have strictly highest
arithmetic-mean throughput and strictly highest arithmetic-mean applicable QPR
in each of the six cells, with 20/20 QPR applicability for every method.  All
1,200 rows are retained regardless of outcome.

Only a six-cell dual-first pass authorizes the existing M2 formal sequence.
This redesign screen and qualification remain non-formal and cannot appear as
paper superiority evidence.

## Termination and integrity safeguards

- The D05 diagnosis found six lower-utility assignments in one
  `inner_iteration_limit` window.  This edge remains separately observable and
  must not be relabeled as a guarded decision.
- Candidate ranking tests must cover the utility floor, finish improvement,
  current-node/node-ID determinism, and zero-radius equivalence where relevant.
- Baseline behavior must remain unchanged under the new binary.
- Paper Eqs. 1--20, load-dependent `(r0, wq)` centres, QPR definition, and old
  PDF alignment are frozen.
- No fourth candidate or revised radius is permitted after any D21--D25 result
  is observed.  Failure closes this family and requires a new diagnosis or
  explicit user decision.
