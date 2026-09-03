# G7 bounded-frontier warm candidate implementation audit

Date: 2026-09-04

Implementation commit: `e5f8802342dc60ae31972386b3236c3e5c940bbc`

Status: source implementation frozen; protocol/analyzer construction authorized;
release construction, reference building, and simulation sampling blocked

## Frozen change

The implementation adds exactly the preregistered operational refinement
`lookahead_frontier1_warm_init`.  The common scheduler and every baseline path
are unchanged.  NSESche first uses the existing parent-placement collector and
then applies a fail-closed candidate-only predicate:

1. every direct parent must have a placement;
2. a completed direct parent needs no further condition;
3. every unfinished direct parent must have all of its own direct parents
   completed; and
4. missing parent metadata rejects admission.

Roots and dependency-ready functions remain admissible.  A child whose
unfinished parent is on the executable dependency frontier is admissible, but
that early placement cannot recursively admit the grandchild while the parent
is still dependency-blocked.  Stable ordering remains arrival frame, request
ID, DAG topological rank, and function ID.

The new candidate reuses the existing `ready_warm_init` rule only for the
initial feasible assignment: among feasible running-warm nodes it minimizes
dynamic projected finish, then maximizes paper utility, then minimizes NodeId.
If no running-warm node is feasible, the existing strict utility initialization
is used.  All subsequent moves use the unchanged strict Eq. (15) best-response
path.  No regret radius, finish-time best-response override, new utility term,
price rule, HPA rule, cache rule, or baseline exception was introduced.

## Identity and observability

The refinement has unique reference-key tag `12` and dedicated operational
schema version `7`.  Runtime configuration reports:

- `operational_refinement=lookahead_frontier1_warm_init`;
- `player_collection=ready_plus_one_executable_frontier_hop`;
- `player_order=arrival_frame_req_id_dag_topological_rank_fn_id`;
- `initialization_semantics=running_warm_if_available_min_dynamic_finish_then_higher_utility_then_node_id_else_strict_utility`;
- `formula_alignment=paper_Eqs_1_20_strict_argmax`; and
- `strict_best_response=true`.

Rust configuration validation accepts this exact name and continues to reject
unregistered names.

Files and SHA-256 receipts at the implementation commit:

| File | SHA-256 |
|---|---|
| `serverless_sim/src/sche/sche_nash.rs` | `82d7932b25185bf962724e5702b80c74628edc1db7c611b084db5c574b28b9f6` |
| `serverless_sim/src/config.rs` | `64eddf43d04d034f45d87e1763b76ccc6153dd2d8a9a2093e07e5d33d5464182` |
| `serverless_sim/src/sim_run.rs` | `8226f8c66a7f26c641a07a3802f4440e51bd26c61ea02d2e6e46296fdeda3cb7` |

The `sim_run.rs` receipt is identical to the G7 preregistration receipt,
confirming that the shared runtime was not modified.

## Verification

- Rust formatting: pass.
- Complete `sche::sche_nash::tests`: 43/43 pass.
- Complete `config::experiment_config_tests`: 10/10 pass.
- Directed frontier test covers roots, ready functions, exactly one early
  frontier hop, rejection of recursive early binding, missing direct-parent
  placement, and missing topology metadata.
- Directed initialization assertions confirm that the warm rule may choose a
  lower-utility feasible start while the subsequent best response still
  selects the strict utility maximizer.
- Parsing, strict formula alignment, unique reference tag, schema, collection
  semantics, player order, initialization semantics, and allow-list validation
  are asserted.
- `git diff --check`: pass before the implementation commit.

The full 122-test repository sweep produced 120 passes and two failures outside
the changed paths.  `sim_env::tests::test_python_res_consistency` failed under
the system Python because NumPy was absent and passed when rerun with the
project interpreter at `D:\Anaconda3`.  The pre-existing wall-clock-sensitive
`mechanism_thread::tests::test_algo_latency` still fails its timing assertion
(`begin_frame=2`, `current_frame=3`, `calltime=2`) when run alone.  Neither test
executes the G7 refinement; these outcomes are disclosed rather than counted as
a complete repository pass.

## Authorization boundary

This closes source implementation only.  It contains no release binary,
workload tape, offline reference, online run, candidate outcome, seed decision,
figure, or paper claim.  The next authorized work is construction and testing
of a G7-specific fail-closed protocol and analyzer, followed by a separate
implementation/protocol audit.  Release construction and zero-data freezing
remain blocked until that audit is committed; reference construction and
online simulation remain blocked until their later staged freezes.
