# G14 Deferral Release-Valve Tape Capture and Input-Binding Audit

Date: 2026-09-04 (Asia/Shanghai)
Parent freeze commit: `22e4fef155fe0742b33226c93fafce7b07230f65`
Status: `all_tapes_bound_exact_30_reference_builds_authorized_after_commit`

## 1. Result-blind tape capture

The 15 preregistered base tape identities were captured in paper-experiment
order: low D106--D110, middle D106--D110, then high D106--D110. All 15
canonicalized on attempt 1. The partial tree contains zero files and no
quarantine directory exists. Capture used the random scheduler only to
materialize arrival events and environment/provenance receipts; it did not run
or compare C0, G14, or any performance baseline.

Independent streaming inspection reopened every tape and verified its file
SHA-256, workload seed, event count, DAG-order hash, and first/last frame
against the catalog. Capture-receipt, process-observation, run-config,
environment-semantic, measured-rate, and source-provenance bindings were
independently rechecked. The append-only ledger has exactly 15 valid
hash-chained canonicalization records in the same low/middle/high order.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,903 | 1,924 | 9,557 |
| middle | 5 | 2,476 | 2,625 | 12,806 |
| high | 5 | 6,783 | 7,070 | 34,632 |
| total | 15 | 1,903 | 7,070 | 56,995 |

All 15 tape hashes are unique. The canonical capture tree contains 210 files
and 60,077,953 bytes. Its sorted inventory object hash is
`69808c45b00a24b6cf18dfa9aea659d073fc1c244e2438cd9f884d6f31e9fd66`.
The ledger tip is
`3989ada965741d124da493606fb93ceab76ec6c8205258a9bbc867dc75db6270`;
the 13,651-byte ledger file has SHA-256
`838574e9ad7b9e542e4ab5769f01d3e30cc2b8ddd1a0fe15fa3ce42dd1056ee6`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g14.tape.catalog.json` | 89,530 | `5f3a7c6092f65667e80b170249b33d0c28c0daec5a81afe0f05e2e46fb81e369` | `32081786777fc0ac6e6dc06bb80d53843df1baebb846b488445e0a1e2d8addda` |
| `g14.tapes.json` | 785,452 | `1f5aa34ef729cbaadd989d94a090dbad5e432530254dfc362054afd5d6f123a8` | `5ea2fa02cee0c292f99362e327420a4d023aab4eb3be81701d392be32d5edfeb` |

The bound manifest passes generic, G14-specific, and static JSON Schema
validation. It has `all_tapes_bound=true`, 30 unique run specifications, 15
distinct tape hashes, 15 exact load/seed groups with two arms each, and 30
distinct operational-mode reference dependencies. Within every group, C0 and
G14 bind the same tape hash and workload specification. Since this initial
stage has no FaaSRank or QoS-SLA arm, `all_faasrank_models_bound=false` and
`all_sla_targets_bound=false` are correct and inapplicable rather than missing
performance inputs.

## 3. Scientific status

No request-completion, throughput, latency, cost, QPR, scheduler, reference,
or candidate outcome was used to select, recapture, omit, or relabel a tape.
Seed-to-seed event-count variation is retained exactly. There is no
`stages/reference_builds` directory and no `online` directory, so C0/G14
performance and offline social-utility values remain unobserved.

## 4. Authorization boundary

After this audit, catalog, bound manifest, capture tree, and append-only ledger
are committed, exactly the 30 declared offline-reference builds are
authorized. They must use the one frozen runtime, the 15 bound tapes, and the
distinct C0 and G14 operational identities. Each first QC-valid reference
build is retained; reference value, solver behavior, or later performance
cannot trigger seed/mode replacement.

Online execution remains blocked until all 30 reference tables, catalogs,
hashes, row counts, state/assignment sequence hashes, process observations,
and mode identities are independently audited and committed. Analyzer
construction, strong baselines, confirmation, formal replay, figures, and
manuscript claims remain blocked.
