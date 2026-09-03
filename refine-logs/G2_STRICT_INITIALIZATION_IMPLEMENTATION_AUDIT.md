# G2 Strict-Initialization Implementation Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: source implementation frozen; G2-specific protocol and source-bound
manifest remain pending; no D66--D70 artifact has been generated

## 1. Frozen implementation identity

- Source commit: `3ae7792782adcef60a254fa7c6bdb60a43d8171d`.
- Branch: `agent/tsc-resubmit-final`.
- Preregistration: `G2_STRICT_INITIALIZATION_PREREGISTRATION.md`, committed
  before scheduler modification and before any D66 capture.
- Modified scientific source: `serverless_sim/src/sche/sche_nash.rs`.
- Modified validation surfaces: `serverless_sim/src/config.rs` and
  `scripts/reviewer_experiments/protocol/schema.py`.
- No paper equation, low/middle/high parameter centre, common HPA rule,
  workload rule, lifecycle transition, feasibility rule, metric, QPR
  definition, or reference-validation rule was changed.

## 2. Candidate semantics implemented

The operational-refinement schema is incremented from 3 to 4 and assigns
distinct reference-key tags to both new candidates.

- C0 `ready_order` is unchanged.
- C1 `ready_warm_init` changes initialization only. If at least one feasible
  node contains a `Running` container for the player's function, it chooses
  the lowest dynamic finish score, then higher published utility, then NodeId.
  If none exists, it falls back to C0's strict-utility initialization.
- C2 `ready_finish_init` changes initialization only. It chooses the lowest
  dynamic finish score, then higher published utility, then NodeId.

The implemented dynamic finish score is the preregistered sum of projected
startup/runnable/starting-resident/pressure and the number of requests already
assigned to that node in the current sequential initialization. Inspection of
the state collector confirms that `warm_containers` is populated only for
`FnContainerState::Running`, so the C1 label and implementation agree.

Feasible-candidate evaluation is shared by initialization and best-response
selection. After the initial feasible state is constructed, both new
candidates call the unchanged strict-utility selector: all feasible actions
are evaluated, numerical ties retain the current node, and lower-utility moves
are not accepted. Both candidates therefore continue to report
`strict_best_response=true`, zero utility-regret radius, and
`paper_Eqs_1_20_strict_argmax`.

The observation stream now exposes the initialization semantic label and the
counts of refined choices, lower-utility initialization choices, and choices
placed on running-warm containers. These counters are diagnostic only and do
not feed back into scheduling.

## 3. Verification

- `cargo fmt --all -- --check`: passed.
- Directed NSESche tests: 32/32 passed, including the new proof-by-unit-test
  that the initialization candidates can choose a different feasible start
  while the subsequent best response remains the strict utility argmax.
- Rust configuration tests: 11/11 passed, including explicit acceptance of C1
  and C2 and fail-closed rejection of an unregistered initializer.
- Existing protocol regression subset covering frozen matrix/QC/runner,
  run-audit manifest, G1 corrected runtime, M1 completion guard, and M1
  development: 64/64 passed under `D:/Anaconda3/python.exe`.
- The new Python configuration-schema test: 1/1 passed.
- `git diff --check`: passed before commit; only line-ending conversion
  notices were emitted.

The system-default Python 3.14 installation lacks NumPy and cannot import the
protocol package; this is an environment limitation, not a scientific result.
No dependency was installed or changed. The project's existing Anaconda
environment was used for the auditable Python checks.

## 4. Fail-closed boundary

This commit freezes candidate behavior but does not authorize sampling. Before
D66 capture, a G2-specific generator, validator, analyzer, retry ledger, and
unbound manifest must be implemented, tested, committed, and bound to a new
release executable built from the frozen source. The expected product remains
exactly 30 tapes, 90 candidate-specific references, 90 candidate online runs,
and 45 homogeneous-low baseline controls. Development observations cannot be
reported as paper evidence or mixed with any later formal bank.

