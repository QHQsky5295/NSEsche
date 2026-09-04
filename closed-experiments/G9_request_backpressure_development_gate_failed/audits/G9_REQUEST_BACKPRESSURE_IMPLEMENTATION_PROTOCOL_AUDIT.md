# G9 Request-Level Backpressure Implementation and Zero-Result Protocol Audit

Date: 2026-09-04 (Asia/Shanghai)

Implementation commit: `d5241f96cf1ad8384a359aeabb225a137827cdca`

Status: `implementation_runtime_protocol_frozen_d81_d85_sampling_authorized`

## 1. Frozen mechanism boundary

The implementation adds only the preregistered operational refinement
`ready_request_backpressure`. At every scheduling frame it deterministically
orders live incomplete requests by `(begin_frame, req_id)` and admits at most
the configured node count. Only dependency-ready, not-yet-placed function
players belonging to that cohort enter the NSESche game. Deferred requests
remain live; they are neither deleted nor rejected. A live admitted request
cannot be displaced by a younger request.

Within the admitted cohort, feasible-node construction, the `ready_order`
initialization, strict Eq. (15) best response, Eqs. (16)--(20), price feedback,
dispatch, HPA, cache/container lifecycle, and the offline social-reference
definition are unchanged. There is no load-specific parameter, learned model,
random tie break, or special treatment of prior Q61--Q80 observations. Because
the player population changes, the candidate has operational schema version 8
and reference-key tag 13. It is a new compound method, not a silent
reinterpretation of the submitted paper equations.

## 2. Runtime and source receipts

One release runtime was built from the clean implementation commit and is the
only runtime accepted by the G9 manifest:

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g9_request_backpressure_impl/release/serverless_sim.exe` | 4,820,992 | `5f41999cd5c193e9fd989d74a72752760d493d3baa04cf9ac40bd7fee1ac5330` |
| `serverless_sim/src/sche/sche_nash.rs` | 349,401 | `79313c8b1dc94e921d3dcaec3abad52cf0261913e0201695c1969fa52009da72` |
| `serverless_sim/src/config.rs` | 47,912 | `e65b71aa534cb455df8d58237b5ac2faa1d9499c7e018abcf92c4da0e052b2d4` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 17,546 | `f7f66d39e14eab2be4125652eabf07120b803905123aef606c98cc34d765fe5d` |

The scheduler emits the preregistered per-window live/admitted/deferred
request counts, cohort bounds, pre/post-filter ready-player counts, cumulative
admissions and completions, retention violations, and dispatch-membership
violations. Runtime-contract validation fails closed if these fields or the
candidate identity disagree.

## 3. Frozen development product

The zero-result manifest is
`runs/tscv1_g9_request_backpressure_d81_d85_d5241f9_20260904/g9.unbound.json`.
Its file SHA-256 is
`fad2a3bb314fd3402c429c85873c592a0c1d35998a3f7b8c68d08276aab15192`;
its embedded canonical object hash is
`9cba4724257a1dc3e6f8a43c45ea004ae73f78b6e79bab0b1ee69509e91334b2`.

The product is exactly:

- five methods: `ready_order`, `ready_request_backpressure`, Load Balance,
  FaaSRank, and Hiku;
- three homogeneous 20-node loads: low, middle, and high;
- five fixed development seeds: D81--D85;
- 75 online run specifications, 15 shared workload-tape identities, and 30
  distinct offline-reference identities for the two NSESche arms.

All five methods share one workload specification and tape identity within
each load/seed group. The manifest binds the single release binary and source
commit above. The single independently calibrated FaaSRank model and reference
artifacts are deliberately unbound until the preregistered tape and
offline-reference stages complete. G9 uses the mixed non-QoS profile, so no SLA
target binding is applicable and `all_sla_targets_bound` remains false. At
freeze time the run root contained only this manifest: no `online` or
`reference-builds` directory and no outcome file existed.

The protocol freezes all ten development conditions before exposure,
including complete positive QPR/throughput, first rank for both metrics at all
three loads, 4/5 paired wins over `ready_order`, positive paired means versus
each baseline, the per-seed 80% control floor, activation and cohort-integrity
checks, strict-Eq.-(15)/reference/runtime checks, and the 1.25x policy-time cap.
Every first QC-valid observation must be retained. Scientific failure is not
retryable and cannot trigger seed, run, or load replacement.

## 4. Protocol receipts and verification

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/protocol/schema.py` | 212,574 | `c25f71c9ddba6c82d5ebff7318a9a27941795e55c153b01a41d9c560bb7f725f` |
| `scripts/reviewer_experiments/protocol/g9_request_backpressure.py` | 9,207 | `c29e5431656d34363d5b448d9ac24d8527b2307dbd8960982ff1a6a84163d571` |
| `scripts/reviewer_experiments/protocol/tests/test_g9_request_backpressure.py` | 5,549 | `63815d0cca39c52964400475ace7c0b991cf4fcef61d553c246ce8a6713e044f` |

Verification before this audit commit:

- complete NSESche Rust tests: 45/45 pass;
- G9 manifest/runtime directed tests: 5/5 pass;
- complete reviewer-protocol regression: 214/214 pass in 795.176 seconds;
- complete reviewer-analysis regression after the implementation change:
  92/92 pass;
- Python compilation and Black formatting: pass;
- `git diff --check`: pass.

Directed tests construct the exact 5 x 3 x 5 product and reject gate or seed
tampering. Generic schema validation independently rechecks runtime identity,
candidate/control bindings, method/load/seed Cartesian completeness, tape
pairing, distinct candidate references, non-formal status, and zero-result
stage counts. The two earlier P2 test failures caused by treating the real
closed P2 workspace as an absence fixture were corrected to use temporary
directories; the real retained P2 workspace was never removed or modified.

## 5. Authorization boundary

This audit closes the G9 implementation, release runtime, and zero-result
development protocol. After this file and its manifest are committed, exactly
the D81--D85 staged product may proceed: capture the 15 tapes, bind the single
previously frozen FaaSRank model, build the 30 offline references, then execute
the 75 online runs once under result-blind canonical reconciliation. No outcome
may be inspected to alter those bindings.

D86--D95 confirmation, Q61--Q80 formal replay, homogeneous-high P2, later
topologies/scales, figures, and paper performance claims remain blocked. They
require a passing G9 development gate and separately committed protocols. A
failed development gate closes G9 as a negative result; it does not authorize
replacement seeds or selective reruns.
