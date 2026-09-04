# G9 Request-Backpressure Development Experiment (Closed)

Status: `complete_g9_development_gate_failed_confirmation_blocked`

This directory is the permanent root-level evidence package for the closed G9
development experiment. It retains the result-free protocol lineage, bound
75-run selection, reconciliation and analysis reports, append-only ledgers,
audits, and the exact source files used to define and evaluate the mechanism.

The fixed oldest-first 20-live-request cohort activated correctly but was not
work-conserving for DAG workloads. It ranked 5/5 in both throughput and QPR at
low, middle, and high load, so it is not eligible for confirmation or paper
performance claims. See `audits/G9_REQUEST_BACKPRESSURE_RESULT_AUDIT.md` for
the complete result and authorization boundary.

The full immutable raw workspace is stored at:

`E:\NSEsche_experiment_archives\tscv1_g9_request_backpressure_d81_d85_d5241f9_20260904`

It contains 1,768 files and 461,180,190 bytes. Its canonical inventory SHA-256
is `f5892e6e33b52d9ac24a5374d1a3dff9da44333383e407b5cf20f9ced440cb1c`,
which exactly matches the source run root at closure.

Key commits:

- mechanism source: `d5241f96cf1ad8384a359aeabb225a137827cdca`;
- final bound inputs: `c12411aaa6309246a492e7cd1bc3dde963519b07`;
- frozen analyzer: `1cebbd3fd3d9530c3041d58afa904ce4298fdb2b`; and
- zero-result selection: `5137da7bb1311ab8a8a5107512ff271990e4aea6`.

Do not reuse D81--D85 for tuning, seed selection, or confirmation. A future
replacement mechanism requires a distinct name, a fresh development seed bank,
and a committed result-free protocol.
