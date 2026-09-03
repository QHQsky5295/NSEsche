# G3 E0 Operational-Selector Implementation Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: **SOURCE IMPLEMENTATION FROZEN; PROTOCOL/ANALYZER PENDING;
D71--D75 SAMPLING NOT AUTHORIZED**.

## 1. Source binding and scientific boundary

The operational implementation is frozen at source commit
`47da450650f1f77a5449204c41fad2423fb4027c` (`implement operational E0
equilibrium selectors`). The two changed source files are bound by SHA-256:

- `serverless_sim/src/config.rs`:
  `b9dd5a318323746333769f46a8da7cac4598d21ea04a7d527a73a507c43b4405`;
- `serverless_sim/src/sche/sche_nash.rs`:
  `8e2d2971514ef6d54113ca6a2cfd2eecc57e99af9f1b166d13d2eb781c0fbd1f`.

This commit implements only the three configurations frozen before source
work in `G3_E0_OPERATIONAL_CANDIDATE_PREREGISTRATION.md`: unchanged C0
`ready_order`, C1 `ready_pne_envelope_first`, and C2
`ready_pne_envelope_each`. It does not change Eqs. (1)--(20), the utility or
welfare formulas, strict Eq. (15), prices, limits, HPA, workload generation,
candidate feasibility, container lifecycle, dispatch, or metric definitions.
The new modes are equilibrium-selection frequencies outside the published
equations; every selected state is produced and independently certified under
the existing strict best-response semantics.

## 2. Operational behavior and observability

C1 evaluates the frozen O0--O4 family only at the first outer round and then
continues subsequent price rounds from the selected state using ready-order
strict best response. C2 evaluates and applies the same E0 rule at every outer
round. C0 follows the pre-existing path and schema.

The implementation reuses the corrected G3 E0 eligibility and ranking rule:
complete, stable, independently strict-PNE-certified outcomes within the
frozen O0 welfare tolerance are ranked by lower startup burden, lower
projected finish, higher paper welfare, and the fixed O0/O2/O3/O4/O1 tie
order. There is no direct warm-placement override and no proxy can replace a
best response.

The run configuration now exposes distinct reference-key tags, an operational
schema version, selection semantics, order list, eligibility/ranking rule,
welfare tolerance, and application frequency. Each active window separates
the selected dispatch path from total O0--O4 evaluation work. Logged fields
include selected order/state hash, strict-PNE certificate, fallback and
eligible counts, selected-path convergence work, evaluated-total work,
operational-envelope microseconds, total solve time, and outer-feedback state
hashes. Operational E0 and the observation-only order-counterfactual flag fail
closed when combined.

## 3. Directed verification

Formatting passed with `cargo fmt --all -- --check`.

- complete NSESche module: 39/39 passed;
- configuration module: 10/10 passed;
- focused operational/counterfactual/configuration tests: passed;
- Anaconda-backed Rust/Python consistency test: 1/1 passed in 111.72 seconds;
- full Rust suite: 116/118 passed.

The directed tests cover parser and reference-tag separation, schema and
frequency reporting, strict formula preservation, corrected E0 selection,
C1 first-round use, C2 every-round use, strict-PNE status, and equality between
the selected state hash and the corresponding outer-feedback/dispatch path.
The existing C0 counterfactual exactness test also remains green.

The two full-suite failures are pre-existing and outside this source path:
`mechanism_thread::tests::test_algo_latency` fails its wall-clock assertion,
and the default system-Python invocation of
`sim_env::tests::test_python_res_consistency` lacks NumPy. The latter passes
when run with the repository's existing `D:/Anaconda3/python.exe`; no package
or environment was modified. Neither failure authorizes weakening a gate.

## 4. Current authorization boundary

This source closure contains no D71--D75 workload tape, reference, online
result, selection receipt, or derived candidate metric. It does not establish
that C1 or C2 improves throughput or QPR.

Before any D71 capture, the exact 135-run protocol product, fail-closed
analyzer, affected Python regressions, release executable/source binding, and
unbound zero-data manifest must be separately frozen and committed. Therefore:

- protocol/analyzer construction and testing: authorized;
- release build and zero-data freeze: authorized only after protocol closure;
- D71--D75 capture/reference/online sampling: **not authorized**;
- formal homogeneous-low/middle/high execution: **not authorized**;
- paper-ready experiment groups: zero.

## 5. Post-audit directed-test closure

Commit `93b572d3258691e47ad1e6df2bf328447b641d3f` subsequently extracted the
already-enforced counterfactual incompatibility check into a directly testable
method and added three preregistered directed tests: counterfactual/E0 mutual
exclusion, deterministic results across fresh schedulers, and O0 fallback only
when no outcome is eligible. The operational computation and log contract are
unchanged. The final `sche_nash.rs` SHA-256 is
`35dcce5ea95da12800ff662d17cb69f125d752bbe1a3fb0b6e662b1ecd99aa46`;
the final release binding is recorded in
`G3_E0_OPERATIONAL_PROTOCOL_RUNTIME_FREEZE.md`.
