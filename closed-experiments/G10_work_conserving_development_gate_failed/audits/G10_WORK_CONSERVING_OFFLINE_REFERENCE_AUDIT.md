# G10 Work-Conserving Offline-Reference Audit

Date: 2026-09-04 (Asia/Shanghai)  
Parent freeze commit: `762754f`  
Status: `all_references_bound_analyzer_freeze_authorized_after_commit`

## 1. Result-blind reference construction

Exactly the 45 mode-specific offline social-utility references declared by the
frozen G10 tape-bound manifest were built in sorted reference-key order. They
cover C0/C1/C2 x low/middle/high x D96--D100 exactly once. All 45 builds
canonicalized on attempt 1; the partial tree contains zero files. No online
candidate run has been executed and no throughput, QPR, latency, cost, or
candidate comparison was available during construction.

Independent streaming verification reopened every table and recomputed its
file size, physical JSONL row count, SHA-256, state-key uniqueness, hexadecimal
and unsigned state-key equivalence, and status counts. It also independently
rehashed each build receipt, process observation, run configuration, welfare
observation, and summary. The run configuration in every directory matches
the catalog key, fixed workload tape, seed, load, reference build-spec hash,
and its declared operational candidate.

| Dimension | Count or value |
|---|---:|
| Reference entries / unique table hashes | 45 / 45 |
| Exact candidate-load-seed cells | 45 |
| Table rows, total | 44,044 |
| Table rows, minimum / maximum | 946 / 997 |
| Positive / negative reference rows | 44,043 / 1 |
| Build-completed observations, total | 55,240 |
| Partial files | 0 |

The single negative-valued row is retained as a valid, hashed reference-table
observation; it was neither deleted nor used to alter any seed, mode, or gate.

| Grouping | Reference-table rows |
|---|---:|
| C0 `ready_order` | 14,681 |
| C1 `ready_remaining_work` | 14,685 |
| C2 `ready_remaining_work_bounded_frontier` | 14,678 |
| low | 14,569 |
| middle | 14,550 |
| high | 14,925 |

The canonical reference tree contains 630 files and 455,388,235 bytes. Its
sorted inventory object hash is
`e455ec573f38585f5c6bee03261c3bcc3840780b999c45746fb6c82a5cb5ad18`.
The append-only 45-line build ledger is 44,184 bytes with SHA-256
`9c8584918cdbe97af4aa3c25e443ea9055f3376201029ebf0e5d00bbcdf6037d`.

## 2. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g10.reference.catalog.json` | 85,907 | `9af4338c07b419a34f61af563bf5b8b71fa6ee0a4ac838281b39cf9746c86c2f` | `2a05a02b75f3108d28fda382c564642b96714fee1bf60978d0935498405b8e3a` |
| `g10.references.json` | 1,258,673 | `804cf98c604ac2b2c6bb3457d143c2ab73e7ad57c9e3483b74b2576e99648921` | `6dd4f045ee144d186bb2bc3ea28f873c94d3e14c331aed9c95f03c5851d05ce5` |

The reference-bound manifest passes the complete schema validator and has
`all_tapes_bound=true` and `all_references_bound=true`. It contains 45 exact
run specifications, 15 distinct tape hashes, 45 distinct reference-table
hashes, and no online-result binding. Every reference path and receipt path was
rehashed after binding and agrees with both the catalog and run artifact hash.

## 3. Scientific status and authorization boundary

Reference construction is an input-generation stage, not an evaluation of the
three candidates. No QC-valid reference was omitted or replaced, including the
negative-valued table row. D96--D100 remain the complete fixed development
seed set.

After this audit is committed, only result-free implementation, testing, and
freezing of the G10 analyzer and exact 45-run selection are authorized. That
analyzer must preserve null QPR for zero completions; verify C0/C1/C2 runtime
identities and activation invariants; retain all QC-valid runs; report all
paired differences, wins, ratios, safety metrics, and leave-one-seed-out
means; and enforce the preregistered gate without threshold weakening.

Online execution, strong-baseline expansion, confirmation seeds, formal replay,
figures, and manuscript performance claims remain blocked until that
zero-result analyzer/selection checkpoint is independently audited and
committed.
