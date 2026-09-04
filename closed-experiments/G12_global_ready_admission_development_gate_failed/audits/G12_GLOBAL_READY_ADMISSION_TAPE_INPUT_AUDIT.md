# G12 Global-Ready Admission Tape Capture and Input-Binding Audit

Date: 2026-09-04 (Asia/Shanghai)  
Parent freeze commit: `c73f4c95aa45aa47aea14f725b3693a95bcd2653`  
Status: `all_tapes_bound_exact_30_reference_builds_authorized_after_commit`

## 1. Result-blind tape capture

The 15 preregistered base tape identities were captured in the requested
paper-experiment order: low D101--D105, middle D101--D105, then high
D101--D105. All 15 canonicalized on attempt 1. The partial tree contains zero
files and no quarantine directory exists. Capture used the random scheduler
only to materialize arrival events and environment/provenance receipts; it did
not run or compare C0, G12, or any performance baseline.

Independent streaming inspection reopened every tape and verified its file
SHA-256, workload seed, event count, DAG-order hash, and first/last frame
against the catalog. Capture-receipt, process-observation, run-config, summary,
and arrival-count bindings were independently rechecked. The append-only
ledger has exactly 15 valid hash-chained canonicalization records in the same
low/middle/high order.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,899 | 1,983 | 9,679 |
| middle | 5 | 2,439 | 2,535 | 12,366 |
| high | 5 | 6,763 | 7,230 | 35,192 |
| total | 15 | 1,899 | 7,230 | 57,237 |

All 15 tape hashes are unique. The canonical capture tree contains 210 files
and 59,776,212 bytes. Its sorted inventory object hash is
`213406332905f2d260fed12395dc9b54f1b5415af650696c7c1cb191c73f8ec4`.
The ledger tip is
`bdcf1b2addcf1863157d8ff972d60f77d7e482afa138910d0f47df2964644c52`;
the ledger file SHA-256 is
`26013c2c28cad1d7ea395392291d9b43693445c7e8ee551df641800b013c6eb7`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g12.tape.catalog.json` | 89,530 | `cb36f08b64eb8e7db87723fdff1c356e7d788868de9395e2c096bcc97dce8825` | `021922d45485c521b9480f1af17ce7ef527cc397d678e04a8ea45b0325d42a1c` |
| `g12.tapes.json` | 784,097 | `2def7e2afc1f48a61ca2e52b52483a771a748a68fd3f583e6eba446d1859c58b` | `8357f14baac5c8f9c531732263e918268da6e12ee15eaa730eac7ef3f4d4496b` |

The bound manifest passes generic, G12-specific, and static JSON Schema
validation. It has `all_tapes_bound=true`, 30 unique run specifications, 15
distinct tape hashes, 15 exact load/seed groups with two arms each, and 30
distinct operational-mode reference dependencies. Within every group, C0 and
G12 bind the same tape hash and workload specification. Since this initial
stage has no FaaSRank or QoS-SLA arm, `all_faasrank_models_bound=false` and
`all_sla_targets_bound=false` are correct and inapplicable rather than missing
performance inputs.

## 3. Scientific status

No request-completion, throughput, latency, cost, QPR, scheduler, reference,
or candidate outcome was used to select, recapture, omit, or relabel a tape.
Seed-to-seed event-count variation is retained exactly. There is no
`stages/reference_builds` directory and no `online` directory, so C0/G12
performance and offline social-utility values remain unobserved.

## 4. Authorization boundary

After this audit, catalog, bound manifest, and append-only ledger are
committed, exactly the 30 declared offline-reference builds are authorized.
They must use the one frozen runtime, the 15 bound tapes, and the distinct C0
and G12 operational identities. Each first QC-valid reference build is
retained; reference value, solver behavior, or later performance cannot
trigger seed/mode replacement.

Online execution remains blocked until all 30 reference tables, catalogs,
hashes, row counts, state/assignment sequence hashes, process observations,
and mode identities are independently audited and committed. Analyzer
construction, strong baselines, confirmation, formal replay, figures, and
manuscript claims remain blocked.
