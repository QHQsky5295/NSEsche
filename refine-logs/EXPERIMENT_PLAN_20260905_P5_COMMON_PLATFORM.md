# P5 common-platform fixed execution plan

Date: 2026-09-05 (Asia/Shanghai)

Status: P5.1, all three pre-result integration corrections, P5.2 immutable
inputs, and P5.3 offline references are frozen. After the reference audit
commit, only the result-free P5.4 online-selection/analyzer freeze is
authorized.
This plan is subordinate to
`TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V6.md`,
`P5_COMMON_PLATFORM_PROTOCOL_DERIVATION.md`, and
`P5_COMMON_PLATFORM_PROTOCOL_PREREGISTRATION.md`.

## Frozen experiment card

| Field | Value |
|---|---|
| Purpose | Validate common FCFS request admission, capacity-proportional active-DAG bounds, and explicit arrival/drain accounting |
| Online pilot | 90 runs: 10 methods x 3 loads x `P5P01--P5P03` |
| Cluster | homogeneous 20 nodes |
| Active limit | 100, derived as `20 x floor((5000-3500)/300)` |
| Fixed horizon | 1,000 ms arrival and throughput observation |
| Drain | early empty stop; per-tape `max(1000,ceil(4W/C)+L_static)` hard post-arrival duration |
| Primary throughput | fixed-window completions / 1,000 ms, req/ms |
| Primary latency | external arrival through completion, including admission wait |
| Primary cost | full terminal resource cost / completed cohort request |
| QPR | unchanged `throughput/(latency x cost)`, computed per run |
| Retention | first QC-valid result for every frozen run; no outcome-based omission |

## Ordered stages

### P5.1 -- implementation and zero-result freeze

- add platform config and validation;
- add external FIFO and active-limit derivation;
- add early drain/hard deadline;
- extend environment, frame, request, summary, and QC telemetry;
- update matrix/reference identities and analyzer;
- run targeted Rust/Python tests and complete regression suites;
- compile one release binary in a new protected target directory;
- freeze a zero-result manifest with no tape/reference/result hash bound;
- write and commit the implementation audit.

P5.1 was completed and committed. Its first P5.2 launch exposed the
pre-result adapter-version omission recorded in
`P5_ADAPTER_VERSION_ALLOWLIST_CORRECTION_PREREGISTRATION.md`. The corrected
source then exposed the three inherited fields omitted when P5 replaced the
base simulation object, as recorded in
`P5_SIMULATION_FIELD_COMPLETENESS_CORRECTION_PREREGISTRATION.md`. Both
three-attempt instances remain exhausted. The complete-fields source then
reached Rust validation and exposed that the generic input-only clone retained
the reviewer-v4 admission/replay constraint while changing workload mode to
capture. The third three-attempt instance is also exhausted; the exact
reviewer-v3/admission-disabled capture normalization is frozen in
`P5_CAPTURE_MODE_NORMALIZATION_CORRECTION_PREREGISTRATION.md` and completed by
the source/release/zero-manifest audit in
`P5_CAPTURE_MODE_NORMALIZATION_CORRECTION_AUDIT.md`. Only that new instance may
capture inputs.

### P5.2 -- immutable inputs

Completed. All nine tapes were captured on attempt 1 in load-major,
seed-major order, independently validated, and hash-bound. The existing
frozen FaaSRank model was bound only after proving its training tape disjoint
from all nine P5 evaluation tapes. No online method execution occurred. See
`P5_COMMON_PLATFORM_TAPE_MODEL_INPUT_AUDIT.md`.

### P5.3 -- offline references

Completed. All 90 method-state references canonicalized on attempt 1, were
independently revalidated, and bind table/row/state/assignment/config/process
identities. No online result directory exists. See
`P5_COMMON_PLATFORM_OFFLINE_REFERENCE_AUDIT.md`.

### P5.4 -- online selection freeze

Authorized only after the P5.3 audit commit. Freeze the exact 90-run list and
complete analyzer hash before any online result exists.

### P5.5 -- pilot execution

Blocked until P5.4 audit commit. Execute seed-major, load-major, method-major;
retain all first QC-valid outcomes and the full attempt ledger. Run the one
predeclared duplicate determinism replay only after its canonical observation.

### P5.6 -- gate and transition

Recompute all twelve preregistered gates independently. Passing freezes the
final platform and authorizes a separate homogeneous-20-low formal
preregistration. Failure stops sampling and permits only a newly
preregistered common-protocol correction.

## Stop rules

- No P5 simulator invocation before a committed zero-result implementation
  audit.
- No stage may start before the preceding stage is complete and committed.
- Any population, hash, conservation, FCFS, cap, timing, metric, completion,
  reference, or determinism failure stops progression.
- Relative method performance never authorizes a retry or protocol change.
- No formal, high-load, scaling, burst, QoS, ablation, or figure task begins
  during P5.
