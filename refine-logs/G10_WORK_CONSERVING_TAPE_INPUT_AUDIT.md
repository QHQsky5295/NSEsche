# G10 Work-Conserving Tape Capture and Input-Binding Audit

Date: 2026-09-04 (Asia/Shanghai)  
Parent freeze commit: `613740b`  
Status: `all_tapes_bound_exact_45_reference_builds_authorized_after_commit`

## 1. Result-blind tape capture

The 15 base tape identities frozen before sampling were captured in sorted
tape-key order. All 15 canonicalized on attempt 1. The partial and quarantine
trees contain zero files. Capture used the random scheduler only to materialize
arrival events and environment/provenance receipts; it did not run or compare
C0, C1, C2, or any performance baseline.

Independent streaming inspection reopened every tape and verified its file
SHA-256, workload seed, event count, DAG-order hash, and first/last frame
against the catalog. Capture-receipt, process-observation, and run-config file
hashes were also independently rechecked.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,890 | 1,961 | 9,589 |
| middle | 5 | 2,465 | 2,545 | 12,532 |
| high | 5 | 6,688 | 7,319 | 34,854 |
| total | 15 | 1,890 | 7,319 | 56,975 |

All 15 tape hashes are unique. The canonical capture tree contains 210 files
and 60,211,642 bytes. Its sorted inventory object hash is
`6152feb550b9ed9db295e7e86cd210a802726492868d2b3393de9ff542258ce6`.
The append-only capture ledger has SHA-256
`f012217d842b63a43d2138990f8b2917ca0bae8acffa208436c2926510d91c65`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g10.tape.catalog.json` | 89,242 | `c78d18aab8a102f17fe2eab98ad7beae087d364a0e69f56ded8bdab0bf9fba50` | `a7d152e30c12c76ef930414abcc876d0b033ab3658aea1dd44e38613e29040ef` |
| `g10.tapes.json` | 1,166,413 | `4861a5b8f2f93493d3188c751e0fd152e0949a4fa269307fdcea7cdcbb39607d` | `6f5d4516b51cee27328e2cde8af79e6233c430e7f069360393a920f55cf8d7fd` |

The bound manifest passes the complete generic and G10-specific validators.
It has `all_tapes_bound=true`, 45 run specifications, 15 distinct tape hashes,
15 exact load/seed groups with three arms each, and 45 distinct operational-
mode reference dependencies. Within every group, C0/C1/C2 bind the same tape
hash and workload specification. Because the initial G10 stage has no
FaaSRank or QoS-SLA arm, `all_faasrank_models_bound=false` and
`all_sla_targets_bound=false` are correct and inapplicable rather than missing
performance inputs.

## 3. Scientific status

No request-completion, throughput, latency, cost, QPR, scheduler, or candidate
outcome was used to select, recapture, omit, or relabel a tape. Event-count
variation is retained exactly as produced by the five preregistered seeds.
There is still no `stages/reference_builds` directory and no `online`
directory. Consequently C0/C1/C2 performance remains unobserved.

## 4. Authorization boundary

After this audit, the tape catalog, tape-bound manifest, and append-only ledger
are committed, exactly the 45 declared offline-reference builds are
authorized. They must use the single frozen runtime, the 15 bound tapes, and
the three distinct C0/C1/C2 operational identities. Each first QC-valid
reference build is retained; reference content cannot trigger a seed or mode
replacement.

Online execution remains blocked until all 45 reference tables, catalogs,
hashes, row counts, and mode identities are independently audited and
committed. Analyzer selection, strong baselines, confirmation, formal replay,
figures, and manuscript performance claims remain blocked.

