# G6 lookahead candidate implementation audit

Date: 2026-09-04

Implementation commit: `f554fd49904a7f003290ef2f261f74a5c51538bc`

Status: source implementation frozen; protocol construction authorized; no
reference or simulator sampling authorized

## Frozen change

The implementation adds the single preregistered operational refinement
`lookahead_preall_sched`.  It changes only NSESche player admission from
`CollectTaskConfig::PreAllDone` (all parents completed) to the existing shared
`CollectTaskConfig::PreAllSched` primitive (all parents already have a node
placement).  Collection remains one pass per scheduling call, so a descendant
is not recursively admitted merely because its parent receives a command in
that same call.

The candidate preserves stable ordering by arrival frame, request ID, DAG
topological rank, and function ID.  It also preserves feasible-node
construction, initialization, strict Eq. (15) argmax and incumbent/numeric tie
semantics, inner/outer convergence, Eqs. (16)--(20), offline social-reference
lookup, congestion-price feedback, dispatch, HPA, cache/container lifecycle,
workload generation, baselines, and metric definitions.  No warm-affinity,
finish guard, bounded regret, operational equilibrium envelope, or
method-specific scale/cache rule is introduced.

## Identity and observability

The new refinement has reference-key tag `11` and operational schema version
`6`; existing tags and schemas are unchanged.  Its run configuration reports
`player_collection=parents_scheduled`,
`player_order=arrival_frame_req_id_dag_topological_rank_fn_id`,
`formula_alignment=paper_Eqs_1_20_strict_argmax`, and
`strict_best_response=true`.  Rust and reviewer-protocol configuration
validation accept the new name explicitly and continue to reject other values.

Files and SHA-256 receipts at the implementation commit:

| File | SHA-256 |
|---|---|
| `serverless_sim/src/sche/sche_nash.rs` | `3f1c5c3a876c4dc63e553b79cd0afacbf1708e31c3c24a634ce3c468165adb43` |
| `serverless_sim/src/config.rs` | `a973967c8c378d23d0ec3b861b289e374a95e49559aacae1d245d268ea4fc1e8` |
| `scripts/reviewer_experiments/protocol/schema.py` | `e07682d5c51e2ad186f57c0299e7c1c4f6b09b97fd6168bf9b8d8070ac15c5b1` |
| `scripts/reviewer_experiments/protocol/tests/test_protocol.py` | `d580ddfb0dd09c87897d7bb657ec7868a178cf90a28e1c49594bea6fc4af8336` |

## Verification

- Rust formatting check: pass.
- Python Black formatting check: pass.
- Complete `sche::sche_nash::tests`: 42/42 pass.
- Complete `config::experiment_config_tests`: 10/10 pass.
- Complete reviewer-protocol tests: 40/40 pass in 258.481 seconds.
- Combined G3--G5 analysis regression tests: 27/27 pass.
- `git diff --check`: pass before the implementation commit.

Directed assertions cover parsing, strict paper-formula alignment, a unique
reference-key tag, the dedicated schema, parent-scheduled collection
semantics, stable player ordering, and protocol/config allow-list validation.
The shared `PreAllSched` implementation was source-inspected and requires every
parent to be present in `req.fn_node`.

## Authorization boundary

This is an implementation-only closure.  It contains no new workload tape,
offline reference, online run, exposed candidate outcome, seed decision,
figure, or paper claim.  The next authorized work is construction and testing
of a G6-specific fail-closed protocol/analyzer, followed by a release binary
and zero-data manifest that binds the five frozen D71--D75 tapes and existing
controls.  Candidate reference construction and online simulation remain
blocked until that protocol/runtime freeze is separately audited and
committed.  Q61--Q80 confirmation and every later formal cell remain blocked.
