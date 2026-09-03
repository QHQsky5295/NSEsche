# G3 operational E0 analyzer convergence/fallback correction preregistration

Date: 2026-09-04  
Status: correction frozen before implementation and before metric exposure

## 1. Trigger and preserved result boundary

After the separately preregistered run-config field-path correction, the
second analyzer invocation advanced past all three C0/C1/C2 configuration
contracts and stopped in runtime validation with:

`G3 E0 outer-feedback trace length mismatch`

It again emitted no throughput/QPR value and created no selection artifact.
The same immutable 135-run product remains untouched; no simulator rerun,
promotion, import, deletion, or replacement is authorized.

## 2. Root cause from source semantics

Rust increments `outer_rounds` when an outer round is attempted. It appends an
`outer_feedback_trace` row only after the selected inner path is stable. If an
attempt terminates at `inner_iteration_limit`, `infeasible_players`, or
`oscillation_guard`, the final attempted outer round correctly has no feedback
row. Therefore the exact source-semantic relation is:

- normal/no-player termination: `len(feedback) == outer_rounds`;
- terminal inner failure: `len(feedback) == outer_rounds - 1`.

The analyzer incorrectly required equality in every case.

The preregistered operational selector also explicitly requires O0 fallback
when all O0--O4 outcomes are ineligible. Such a fallback is not claimed to be
an eligible strict PNE; otherwise the eligible count could not be zero. The
analyzer nevertheless required every fallback's selected state to be complete,
stable, and certified and unconditionally indexed a corresponding feedback
row. This contradicts the frozen selector/fallback semantics and the explicit
Rust no-eligible-outcome test.

## 3. Complete result-blind structural census

A scan limited to runtime control fields across all 90 candidate runs found:

- 90,000 policy-window records in total;
- 15 attempted-but-untraced terminal rounds, all
  `inner_iteration_limit`: six C0, five C1, and four C2 windows across eight
  runs;
- ten C1/C2 fallback selections: nine unstable final-round fallbacks without
  a feedback row and one stable but uncertified fallback with a feedback row;
- every unstable no-feedback fallback has `eligible_outcomes=0`, selects O0,
  sets `selected_non_o0=false`, and has a selected assignment hash equal to
  the final decision/dispatch assignment hash;
- the stable fallback's feedback assignment hash equals its selected hash;
- every non-fallback selection has a positive eligible count, is complete,
  stable, independently certified, and has an equal corresponding feedback
  assignment hash;
- zero structural exceptions to these source-derived relations.

No throughput, QPR, latency, cost, completion, selection score, candidate
aggregate, or gate outcome was read or computed by this census.

## 4. Frozen correction

The only authorized analyzer changes are:

1. validate feedback length against termination semantics: exact equality for
   normal/no-player windows and exactly one missing final row for the three
   terminal inner-failure reasons;
2. reorder per-round checks so fallback identity is established before
   strict-PNE eligibility checks;
3. require complete/stable/certified state, positive eligible count, and a
   matching feedback hash for every non-fallback selection;
4. for fallback, require zero eligible outcomes, O0, and
   `selected_non_o0=false`; if feedback exists, require its hash to match; if
   feedback is absent, require it to be the final attempted inner-failure
   round, require `selected_stable=false`, and require the final decision hash
   to equal the selected hash;
5. require the certificate object and boolean `certified` field for both
   paths; do not silently omit malformed fallback data.

The test fixture may add the real decision assignment hash. Directed tests
must cover accepted stable fallback, accepted terminal unstable fallback,
rejection of a normal termination with a missing trace, rejection of a
non-fallback uncertified selection, and rejection of a terminal fallback whose
decision hash differs.

No other production or test change is authorized. In particular, this does
not relax the non-fallback strict-PNE contract, QPR completeness, global
maximin rule, twelve strict C0 ratios, nine-baseline dual-metric gate, or 9x
timing ceiling.

## 5. Verification and next gate

The corrected code must pass the expanded G3 module, combined G2/G3
regression, Python compilation, Black, and source-diff review. It must then be
committed and audited before exactly one further analysis of the unchanged
135-run product is authorized. Formal execution and paper-ready claims remain
blocked.

