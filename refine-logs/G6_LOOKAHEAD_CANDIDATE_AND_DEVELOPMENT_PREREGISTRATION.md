# G6 lookahead candidate and development preregistration

Date: 2026-09-04

Candidate: `lookahead_preall_sched`

Parent decision: `complete_lookahead_candidate_preregistration_authorized`

## Research question

Can parent-scheduled lookahead hide container startup behind upstream DAG
execution and improve homogeneous-low throughput and QPR, while leaving the
paper's Eqs. (1)--(20) and strict Eq. (15) node selection unchanged?

G6 is a development experiment.  D71--D75 informed the mechanism diagnosis and
cannot become final confirmation data.  A passing development result only
permits a disjoint Q61--Q80 confirmation that reuses already frozen paired
baseline products; it is not itself paper-ready.

## Sole implementation change

Add one explicit operational refinement named `lookahead_preall_sched`.

- C0 `ready_order` admits an unplaced request/function only when every parent
  is complete (`CollectTaskConfig::PreAllDone`).
- The new candidate admits it when every parent already has a placement
  (`CollectTaskConfig::PreAllSched`).
- The scheduler still collects the player set once per frame.  A descendant
  whose parent receives a command in the current call is not recursively added
  during that same call.
- Stable player order remains arrival frame, request ID, DAG topological rank,
  and function ID.
- Feasible nodes, resource/memory constraints, initialization, Eq. (15) strict
  argmax, incumbent/numeric tie behavior, inner and outer convergence, Eqs.
  (16)--(20), offline social reference, congestion-price feedback, and dispatch
  are unchanged.
- No warm-affinity term, finish guard, bounded regret, E0 order envelope,
  method-specific scaler, cache rule, prewarming rule, or baseline change is
  allowed.

The new refinement receives a unique reference-key tag and a dedicated
operational schema version.  The run-config record must state
`player_collection=parents_scheduled`,
`formula_alignment=paper_Eqs_1_20_strict_argmax`, and
`strict_best_response=true`.  Existing candidate schema values and hashes are
not reinterpreted.

## Implementation gate

Before protocol construction or data creation:

1. add parser/config/protocol-schema support for only the new named value;
2. add tests for parse/serialization, unique reference-key tag, collection
   semantics, stable order, strict Eq. (15), and rejection of invalid values;
3. run Rust formatting, focused Rust tests, reviewer-protocol tests affected by
   the allowed-value change, and the existing G3--G5 analysis regressions;
4. record source/test hashes and commit an implementation audit.

No simulator execution is authorized by this implementation section.

## Frozen development cohort

Only the homogeneous 20-node low-load cell is admitted initially.

- Seeds/workload tapes: D71, D72, D73, D74, D75 from the frozen G3-E0 product.
- Candidate runs: exactly five, one per tape.
- Controls: reuse the existing five C0 and 45 nine-baseline canonical runs from
  G3-E0; do not rerun them.
- FaaSRank model: reuse the already frozen disjoint model binding.
- Mechanism, HPA, cache, function/DAG generation, total frames, drain rules,
  cost units, QoS definition, and output metrics remain identical to G3-E0.

Because player admission and state keys change, the candidate must build and
freeze its own five offline social-reference tables before online execution.
No C0 or baseline reference may be relabeled for the candidate.

## Ordered execution

1. Freeze a zero-data manifest binding source commit, release binary, exact five
   input tapes, model, environment, output paths, and attempt policy.
2. Build all five candidate-specific offline reference tables.  Any missing,
   duplicate, non-finite, or policy-dependent reference blocks online runs.
3. Freeze reference file/document hashes into the ready manifest.
4. Run the five candidate cells once each.  Infrastructure failure may be
   retried only under the existing fail-closed attempt policy; the first valid
   canonical result is retained regardless of metric values.
5. Analyze exactly the five candidate runs against the frozen C0/baseline
   products.  No outcome-based retry, deletion, substitution, or extension is
   permitted.

The stage stops on failure; later stages are not started speculatively.

## Integrity and activation gates

All five candidate runs must satisfy:

- canonical run/QC/manifest/tape/reference hashes match the ready manifest;
- `operational_refinement=lookahead_preall_sched` with its dedicated schema;
- fixed Eq. (1)--(20) formula alignment and strict Eq. (15);
- offline-required reference hit with no missing/unavailable reference;
- complete dispatch accounting, zero invalid assignment, zero failed channel,
  and no forbidden fallback;
- no non-finite primary metric and a valid drained-arrival cohort;
- pre-ready-bound share at least 0.10 and mean startup overlap greater than zero
  among completed functions in every seed.

Failure of activation is an implementation/mechanism failure, not a performance
result.

## Development performance gate

The five-seed candidate is development-qualified only if every condition holds:

1. mean throughput is strictly greater than the frozen best baseline mean,
   Hiku's 1.1514 requests/ms;
2. mean QPR is strictly greater than the frozen best baseline mean, Jiagu's
   0.040391615;
3. versus paired C0, candidate throughput improves in at least 3/5 seeds, QPR
   improves in at least 4/5, and both improve jointly in at least 3/5;
4. neither throughput nor QPR is below 80% of paired C0 in any seed;
5. mean completion ratio is not below C0 and mean request latency is below C0;
6. mean scheduler solve-time ratio versus C0 is at most 3.0;
7. all five seeds, mean +/- sample SD, paired differences, paired 95% t
   intervals, and leave-one-seed-out means are reported even when intervals
   include zero.

These are development gates, not significance claims.  Old-PDF proximity is a
secondary descriptive check only and cannot replace any gate or justify seed
selection.

## Confirmation rule after a pass

A complete G6 pass may authorize a separate preregistration to run only the new
candidate on the already frozen, development-disjoint Q61--Q80 homogeneous-low
tapes and candidate-specific offline references.  The existing paired baseline
results are reused without rerun.  Final closure would require the new
candidate to pass a prospectively frozen 20-seed gate against all baselines;
the failed C0 Q61--Q80 result remains retained in provenance.

If G6 fails, Q61--Q80 candidate execution and every later main-plan cell remain
blocked.  Any further mechanism must start from a result audit and a new
preregistration; it may not extend D71--D75 until favorable seeds accumulate.

## Storage and reporting

Reference and online products are stored under a uniquely named G6 run root,
never in the original rollback workspace.  Partial failed attempts follow the
existing bounded quarantine/receipt policy; canonical valid results and all
audits are retained.  No protected target directory or prior canonical product
may be deleted.  No figure is authorized during development.
