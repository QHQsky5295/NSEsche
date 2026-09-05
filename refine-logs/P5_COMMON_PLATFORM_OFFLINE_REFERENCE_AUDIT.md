# P5 common-platform offline reference audit

Date: 2026-09-05 (Asia/Shanghai)

Parent tape/model input audit commit: `3a66607`

Status: `all_ninety_references_bound_online_selection_freeze_authorized_after_commit`

## 1. Complete reference population

All 90 preregistered method-state references were built in manifest order:
low--middle--high, P5P01--P5P03 within load, and the frozen ten-method order
within seed. Every reference canonicalized on attempt 1. The first build was
independently inspected before the remaining 89 were launched. There was no
retry, replacement, quarantine, input change, model change, or online method
execution.

| Load | Tables | State-pair rows | Table bytes | Min--max rows/table |
|---|---:|---:|---:|---:|
| low | 30 | 27,645 | 7,098,007 | 18--2,461 |
| middle | 30 | 48,525 | 12,382,163 | 1--4,901 |
| high | 30 | 105,398 | 26,983,020 | 7--17,643 |
| **Total** | **90** | **181,568** | **46,463,190** | **1--17,643** |

Independent streaming inspection reopened all 90 tables and verified finite
offline-reference entries, unique state keys, initial-assignment identities,
table SHA-256, bytes, row count, and state-pair sequence hash. For every key,
the audit also recomputed the state-pair and final-assignment sequence hashes
from the retained build-window trace and matched them to the table, receipt,
and catalog.

All 90 receipts match their declared reference key, build specification,
workload tape, table, run config, process observation, summary, and assignment
sequence. Every process exited 0 without timeout or launch error; every
attempt is attempt 1/pass; every summary is complete and has the exact bound
tape arrival count.

The canonical reference tree contains 1,350 files and 3,788,381,881 bytes.
Its path-independent sorted inventory object hash is
`1bb69fea59dad60b43423866a5282382b88b2ac1420c7813ebdf2c6e2c72123c`.
No quarantine directory exists.

The append-only reference ledger has exactly 90 valid hash-chained events;
its tip is
`926d7fa811b32543dfae4de115216f46f5a264e67126469873cee87f3c5e8360`.
The 85,196-byte ledger has SHA-256
`d26d7bdddbcaeaa607abe014d58f49785c8d2d82d14754bfd6d62c038791efa0`.

## 2. Catalog and ready-manifest closure

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `reference_stage/reference_catalog.json` | 164,060 | `23872fa60abb159b73cecef376b0cb060e36bc6ac1a86176bc585190bac59199` | `7eb2e4152d6aecd538d8447a3ee014b2b5ce3a86fdd9ce673b451fa4e7d88067` |
| `p5_common_platform.ready.json` | 2,770,804 | `7f9720e9dc7aa8dfe00d96e00c4d8deee8df6863d0c914d2490f51d625353d19` | `0a02d480e583b1fba4eec97a9d1f974573406be5c8de48dae7181dd5e60de3ee` |

The catalog payload hash is
`ebbdc9ac8dc475eff08ea0a26304c8510975675ec7469e80a3d07146cd35a082`.
The ready manifest's embedded pre-self hash is
`92dd4e2501b69ce4d0ca561c6dcea76d49356a6edb94ee789dfe48563b6b0af3`.

The ready manifest passes generic, dedicated P5, and static JSON Schema
validation. It contains 90 unique run IDs/specifications, 90 unique reference
keys and hashes, and no remaining `build_required` reference. Its legal staged
state is tapes/model/references = true/true/true; SLA remains inapplicable and
false.

No `online`, selection, or analysis path exists. The audit does not aggregate,
rank, compare, or select any method by offline utility, and no P5 throughput,
latency, cost, QPR, completion, or method decision has been observed.

## 3. Authorization boundary

After this audit is committed, P5.4 may freeze exactly the ready manifest's 90
ordered run IDs and run-spec hashes together with the already implemented P5
analyzer source hash and its twelve-condition result-blind contract. That
selection construction must not read any reference utility value or online
result.

No online run is authorized until the selection and analyzer audit is itself
committed. Duplicate replay, result analysis, figures, paper claims, and the
formal rerun remain blocked.
