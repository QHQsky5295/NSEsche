# G3 operational E0 analyzer convergence/fallback correction audit

Date: 2026-09-04  
Status: complete; one unchanged-product analyzer invocation is authorized

## 1. Implemented source-semantic validation

Commit `604a9158ae19bad4817b198216f17fd544055279` implements exactly the
preregistered correction:

- `outer_feedback_trace` must contain one row per completed stable outer
  round; only `inner_iteration_limit`, `infeasible_players`, or
  `oscillation_guard` may leave the final attempted round untraced;
- non-fallback selections still require a positive eligible count, complete
  assignment, stable inner result, independent strict-PNE certificate, and an
  equal corresponding feedback assignment hash;
- fallback selections require zero eligible outcomes, O0, and
  `selected_non_o0=false`;
- a stable fallback must have an equal feedback assignment hash;
- an unstable terminal fallback must be the final attempted round, have no
  feedback row, and have a selected assignment hash equal to the final
  decision/dispatch assignment hash;
- selection flags and certificate fields must remain correctly typed on both
  paths.

No permissive catch-all was added. Normal terminations with missing feedback,
non-fallback uncertified selections, and terminal fallbacks with mismatched
dispatch hashes fail closed.

## 2. Diff and immutable experiment boundary

Only the G3 operational analyzer and its unit-test module changed. The
simulator source, final `93b572d` executable, ready manifest, all 135 canonical
runs, tapes, references, receipts, and ledger are untouched. No metric,
candidate, seed, ranking rule, tie break, baseline gate, timing gate, or
threshold changed.

- corrected analyzer SHA-256:
  `93e532ea1babbc7e875a721da2f0f22a2ea80e979ad19a6f30feb748cf3a295a`;
- corrected test-module SHA-256:
  `ba81bc1304f9db54a232ea027256bf8b4bfc6624e1c08abf9236be719d8c553a`;
- immediately preceding analyzer SHA-256:
  `93a86896d633be89a0a26c21c237c4eceae7864b81808dcb695e17c445853821`.

## 3. Directed verification

- expanded G3 operational module: 9/9 tests passed;
- combined G2/G3 protocol regression: 15/15 tests passed;
- Python compile-all: passed;
- Black check on both changed files: passed;
- `git diff --check`: passed;
- production diff review: limited to the preregistered source-semantic
  feedback/fallback checks.

New tests explicitly accept both stable and terminal no-eligible O0 fallback
forms and reject a normal missing trace, a non-fallback uncertified selection,
and a terminal fallback/dispatch hash mismatch. The prior real-field negative
test remains active.

## 4. Authorization

Both prior analyzer attempts ended before performance aggregation and created
no `g3_e0.selection.json`. Exactly one further invocation is authorized on the
same `g3_e0.ready.json` and `online/canonical` product. Its complete output
must be retained whether gates pass or fail. No online rerun or D71--D75
extension is permitted. Formal execution and paper-ready claims remain
blocked pending the frozen analyzer outcome.

