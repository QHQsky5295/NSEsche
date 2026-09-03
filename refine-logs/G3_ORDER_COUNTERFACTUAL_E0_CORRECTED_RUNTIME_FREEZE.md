# G3 E0-Corrected Counterfactual Runtime Freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: **FROZEN BEFORE REPEATED REPLAY**; exactly 50 corrected diagnostic
replays are authorized; no D71--D75 or formal middle-load run is authorized.

## 1. Why this repeat exists

The original G3 replay and both retained analyses fail closed. Analyzer V2
proved that 50/50 live C0 source replays are exact and all 300,000 order/window
rows are present, but exposed three E0 records in which a capped O0 remained
selected despite a positive count of eligible alternatives. The correction
was preregistered in
`G3_ORDER_COUNTERFACTUAL_INSTRUMENTATION_CORRECTION_PREREGISTRATION.md`
before the Rust source changed.

The source correction changes only the observation-only E0 incumbent: the
first eligible outcome becomes the incumbent, and O0 is used as a coverage
fallback only when no eligible outcome exists. It cannot change live dispatch,
price feedback, references, workload execution, or online metrics.

## 2. Frozen source and binary

- source commit:
  `166689339c66f81c72ea90cbf1e8fbf532c37064`;
- Rust-source drift from that commit: zero files;
- release executable:
  `serverless_sim/target_g3_e0fix_1666893/release/serverless_sim.exe`;
- executable size: 4,770,816 bytes;
- executable SHA-256:
  `6a05e0b17ea6cad3aaeccf7fa257794e1e31c6f3c55d5b7b776fda8225db4ac3`.

Validation passed five focused Rust tests: three counterfactual determinism,
O0 reconstruction, and decision-neutrality tests; the independent profitable-
deviation certificate test; and the new capped-O0/eligible-alternative E0
regression. The G3 Python analysis/protocol set passes 13/13. `cargo fmt
--check` passes.

## 3. Frozen repeated manifest

The ready manifest is:

`runs/tscv1_g3_ordercf_e0fix_q61q80_d66d70_1666893_20260903/g3.order-counterfactual.ready.json`

- declared runs: 50;
- distinct source run IDs: 50;
- document hash:
  `df5d293d5f2e6eb500373943fa649f523cd582c29bbe417cff7ac258e0163bbb`;
- file SHA-256:
  `1082c38334a9b6fb2fa78b05aa5acd200303952678af2b47bf66425deb5ce2e7`;
- file size: 1,459,709 bytes;
- manifest schema validation: passed;
- `D71_authorized=false`.

A recursive old/new manifest comparison found exactly six scalar differences:
creation time, executable path, executable SHA-256, source commit, command-
template executable path, and manifest hash. After replacing those runtime
bindings, the manifests are byte-structure equal. The ordered 50 source IDs,
all seeds, tapes, references, source artifacts, topology/load cells,
configuration, HPA, equations, order definitions, thresholds, and reporting
strata are unchanged. Run IDs also remain unchanged because the scientific
run specifications are unchanged.

## 4. Execution boundary

The new workspace contains only the ready manifest at this freeze. Execute all
50 runs once in manifest order, retain every valid result, and reconcile paths
without using any metric. Analyze with the committed V2 analyzer in a new
output directory. The old online workspace and both failed analysis folders
remain immutable audit evidence.

At this freeze:

- corrected repeated replays complete: 0/50;
- candidate effect estimated: false;
- candidate authorized: false;
- `D71_authorized=false`;
- homogeneous-middle formal authorized: false;
- paper-ready groups: zero.
