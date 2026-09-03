# G3 post-failure analyzer correction preregistration

Date: 2026-09-04

## Failure boundary

The first authorized invocation of the frozen post-failure analyzer stopped
while reducing the first active operational-E0 run. It emitted no diagnostic
JSON or CSV, and the `diagnosis` output directory does not exist. No simulator
run occurred.

The exception was raised before cross-run pairs, aggregates, correlations,
root-cause criteria, or result artifacts were constructed. The analyzer tried
to validate `operational_equilibrium_selection.rounds` as a numeric count.

## Source-grounded cause

The Rust serialization at `serverless_sim/src/sche/sche_nash.rs:5523` emits:

- `rounds` as `stats.operational_envelope_trace`, a list of per-outer-round
  trace objects;
- `selected_non_o0_rounds` as a numeric count.

A structure-only inspection of one active canonical event confirms `rounds`
is a list and each element is an object with the frozen E0 trace fields. The
failure is therefore an analyzer integration defect, not a data or simulator
failure.

## Sole authorized correction

Replace numeric validation of `selection["rounds"]` with all of the following:

1. require `rounds` to be a list;
2. require every member to be an object;
3. use `len(rounds)` as the selection-round count;
4. retain numeric validation of `selected_non_o0_rounds`;
5. require `0 <= selected_non_o0_rounds <= len(rounds)`;
6. add directed tests that accept a valid trace list and reject a scalar,
   non-object member, or impossible selected count.

No formula, run, raw artifact, metric, factorization, field set, statistical
test, multiplicity family, threshold, root-cause rule, source mapping,
candidate, seed, baseline, or output name may change. No simulator rerun or
new sample is authorized. After code review, tests, and a committed correction
audit, exactly one retry on the unchanged 135-run product may be authorized.
