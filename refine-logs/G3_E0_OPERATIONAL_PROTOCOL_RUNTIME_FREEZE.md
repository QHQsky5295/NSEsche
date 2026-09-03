# G3 E0 Operational Protocol and Runtime Freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: **PRE-SAMPLING GATES PASSED; ONLY COMPLETE D71--D75 TAPE CAPTURE IS
AUTHORIZED NEXT**.

## 1. Frozen source and protocol

The C0/C1/C2 implementation originated at commit
`47da450650f1f77a5449204c41fad2423fb4027c`. Protocol and analyzer commit
`9c8789f1a8a53e8cb16caeb0cbf230e3317bf096` freezes the exact 135-run
product, runtime-stream validation, global maximin ranking, dual-metric
control/baseline gates, and per-cell 9x active-window solve-time cap.

Commit `93b572d3258691e47ad1e6df2bf328447b641d3f` makes the already-existing
counterfactual incompatibility assertion directly testable and adds the
previously required incompatibility, fresh-scheduler determinism, and no-
eligible-outcome fallback tests. It does not change a formula, candidate,
selection rule, assignment, reference key, log schema, or timing path. The
final Rust source hashes are:

- `serverless_sim/src/sche/sche_nash.rs`:
  `35dcce5ea95da12800ff662d17cb69f125d752bbe1a3fb0b6e662b1ecd99aa46`;
- `serverless_sim/src/config.rs`:
  `b9dd5a318323746333769f46a8da7cac4598d21ea04a7d527a73a507c43b4405`.

The primary protocol implementation and validator hashes are:

- `scripts/reviewer_experiments/protocol/g3_e0_operational.py`:
  `9a60780e07357ccf94fce38c18aef90e893302d0f7b6198c6f557a69e0cddf9d`;
- `scripts/reviewer_experiments/protocol/schema.py`:
  `88d8eba1336a5e6ada1766202ce467a0784b0e51745d7dfaae44d82aa80e89cb`.

## 2. Verification closure

The final source and protocol passed:

- `cargo fmt --all -- --check`;
- 42/42 complete NSESche tests;
- 11/11 Rust tests selected by `cargo test config`;
- 6/6 new G3 operational protocol/analyzer tests;
- 12/12 combined G3 operational plus G2 regression tests;
- 66/66 cross-protocol G1/G2/G3/schema/adapter regression tests;
- Python compile-all and Black format checks;
- the complete Rust suite under the repository's Anaconda Python environment:
  120/121 passed in 111.32 seconds.

The sole full-suite failure remains the pre-existing wall-clock assertion in
`mechanism_thread::tests::test_algo_latency` (`begin_frame:2 current_frame:3
calltime:2`). The Rust/Python consistency test passed in the same complete
run. The wall-clock test does not execute the E0 solver and does not relax any
scientific or integrity gate.

## 3. Frozen release executable

All D71--D75 stages must use exactly:

- path:
  `serverless_sim/target_g3_e0_operational_93b572d/release/serverless_sim.exe`;
- source commit: `93b572d3258691e47ad1e6df2bf328447b641d3f`;
- bytes: `4,811,264`;
- SHA-256:
  `6f700b2b43da66ffdb4cf51ecdde9ea63b6441b69e0adb10af92eacb6ae7a0c3`.

The earlier `target_g3_e0_operational_9c8789f` executable was built before the
three explicit gate tests were committed. It is a retained technical artifact
only and is not authorized for capture, reference construction, or online
execution.

## 4. Immutable zero-data manifest

The only authorized run root is:

`runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903`

Its sole file at freeze is `g3_e0.unbound.json`:

- document `manifest_hash`:
  `c0bbfd2a2c3907ffdd053809f435cd955e51175aca05ee8bcbd96b11ed26a6d6`;
- file SHA-256:
  `a277e13086590109daed6022c0bc66591615b813e44c0ec39b0b8d60ad2a1d21`;
- bytes: `2,702,760`;
- run/cell/reference counts: `135 / 27 / 90`;
- candidate online runs/baseline online runs/tapes: `90 / 45 / 30`;
- formal-results eligible: false;
- FaaSRank model, tape hashes, reference hashes, and SLA bindings: unbound.

Recursive inventory found exactly that one unbound manifest and zero
materialized workload tapes, reference tables/receipts, run attempts,
canonical results, summaries, selection receipts, or derived metrics. CLI
schema and document-hash validation passed.

The earlier
`runs/tscv1_g3_e0_operational_d71_d75_9c8789f_20260903` root also contains
only one zero-data draft manifest. It is explicitly superseded and prohibited;
it must never be supplied to a capture, reference, run, or analysis command.

## 5. Stage authorization

Exactly the complete 30-tape D71--D75 capture declared by the authorized
manifest may now begin. Capture must finish and the catalog must bind all 30
tapes before any of the 90 candidate-specific offline references is built.
All references must then complete and bind before any online run begins.

At this freeze:

- D71--D75 tape capture: **authorized as the next atomic stage**;
- reference construction: blocked pending complete tape capture/binding;
- all 135 online runs: blocked pending complete reference/model binding;
- result inspection or candidate selection: blocked pending all 135 valid
  canonical runs;
- formal homogeneous-low/middle/high: not authorized;
- paper-ready experiment groups: zero.
