# G16 Overflow-Magnitude-Gated Valve Tape Capture and Input-Binding Audit

Date: 2026-09-04 (Asia/Shanghai)

Parent freeze commit: `24215857594b8950094ebc9de3a6d0b1801fe15d`

Status: `all_tapes_bound_exact_30_reference_builds_authorized_after_commit`

## 1. Result-blind tape capture

The 15 preregistered base tape identities were captured in paper-experiment
order: low D111--D115, middle D111--D115, then high D111--D115. All 15
canonicalized on attempt 1. The partial tree retains 15 empty per-key
directories and zero files; no quarantine directory exists. Capture used the
random scheduler only to materialize arrival events and
environment/provenance receipts. It did not run or compare C0, G16, or any
performance baseline.

Independent streaming inspection reopened every tape and verified its file
SHA-256, workload seed, event count, DAG-order hash, and first/last frame
against the catalog. Capture receipt, process observation, run configuration,
environment semantic bundle, summary completion, and arrival-count bindings
were independently rechecked. The append-only ledger has exactly 15 valid
hash-chained canonicalization records in the same low/middle/high order.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,889 | 1,968 | 9,614 |
| middle | 5 | 2,432 | 2,572 | 12,588 |
| high | 5 | 6,831 | 7,048 | 34,680 |
| total | 15 | 1,889 | 7,048 | 56,882 |

All 15 tape hashes are unique. The canonical capture tree contains 210 files
and 59,073,907 bytes. Its sorted inventory object hash is
`2fbfece1b97895007b2f7dc44f58228a2cd10e0c168437ca25ec6f611e07453e`.
The ledger tip is
`01569b3c6f98d57e662fd829daa185476cdfd02853e952086d666b2e1cf6de4e`;
the 13,261-byte ledger file has SHA-256
`584be58566db109fc7b82e7986a8f4a4c90d060f091f051b7ba29c81a4b12de3`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g16.tape.catalog.json` | 88,750 | `6f39cf93ee3bba2bee0438b8e23073fa5fede2e4c452258aa4eab45f2ae291d9` | `06cce1476a22edb4eb246c347117a14ea8b65869e8e09f73be46fa7c972bd1ed` |
| `g16.tapes.json` | 784,171 | `42cd2b62b3b4afd55140d08c0ddb8730eab363e67f77474d01c42ec4784aac34` | `31bbdc62352fd0adff6f8cd50d4aff2bcd519d8d2fea76990c6ca509a246dbd7` |

The bound manifest passes generic, G16-specific, and static JSON Schema
validation. It has `all_tapes_bound=true`, 30 unique run specifications, 15
distinct tape hashes, 15 exact load/seed groups with two arms each, and 30
distinct operational-mode reference dependencies. Within every group, C0 and
G16 bind the same tape hash and workload specification while their reference
keys remain distinct. Since this development stage has no FaaSRank or QoS-SLA
arm, `all_faasrank_models_bound=false` and `all_sla_targets_bound=false` are
correct and inapplicable rather than missing performance inputs.

## 3. Scientific status

No request-completion, throughput, latency, cost, QPR, scheduler-reference, or
candidate outcome was used to select, recapture, omit, or relabel a tape. The
incidental random-scheduler capture summaries are input-generation receipts,
not C0/G16 observations or evidence for the development gate. Seed-to-seed
event-count variation is retained exactly. There is no
`stages/reference_builds` directory and no `online` directory, and all 30
reference hashes remain null. Thus C0/G16 performance and offline
social-utility values remain unobserved.

## 4. Authorization boundary

After this audit, catalog, bound manifest, capture tree, and append-only ledger
are committed, exactly the 30 declared offline-reference builds are
authorized. They must use the protected runtime, the 15 bound tapes, and the
distinct C0 and G16 operational identities. Each first QC-valid reference
build is retained; reference value, solver behavior, or later performance
cannot trigger seed/mode replacement, recapture, omission, or down-weighting.

Online execution remains blocked until all 30 reference tables, catalogs,
hashes, row counts, state/assignment sequence hashes, process observations,
and mode identities are independently audited and committed. Analyzer
construction, strong baselines, confirmation, formal replay, figures, and
manuscript claims remain blocked.
