# P4 Startup-Aware Queue Tape and Input Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent zero-result audit commit: `881bf50667193ca81bdc45930631c723516d0b57`

Status: `all_five_tapes_bound_exact_ten_reference_builds_authorized_after_commit`

## 1. Complete fixed input population

The preregistered D126--D130 homogeneous-low base tapes were captured in seed
order. All five canonicalized on attempt 1. There was no retry, seed
replacement, quarantine, or queue-pressure-setting execution. Capture used
the random scheduler only to materialize arrivals and environment receipts;
its incidental summaries are not P4 outcomes.

| Seed | Events | Tape SHA-256 |
|---|---:|---|
| D126 | 1,905 | `5c69f8a1242f4589c448fda3891b620b319a57c71543efb9b090b6db3abe8c8b` |
| D127 | 1,920 | `792435f3b5ac60365088a6d074eadd9cdc3d878d3c016353cd6bc41991e9298c` |
| D128 | 1,952 | `25224a2d05a9e8d79ebcf67a6d73dbff6866cd6053ff90580dc92ccd2cf6f9c2` |
| D129 | 1,936 | `35ff6f632e1eef5b6f7311e7ea2ca55a52bc8e83526f7d5e2a56f69d83f56e49` |
| D130 | 1,909 | `0d0bd6f1ecc50090a2ee89a1f34f41956a41c5f6237675d317186975953c23ee` |
| **Total** | **9,622** | **five distinct hashes** |

Independent streaming inspection reopened every tape and rechecked the tape
SHA-256, workload seed, event count, DAG-order hash, first/last frame,
capture receipt, run configuration, process observation, attempt record, and
capture summary. Every process exited 0 without timeout or launch error, and
every attempt record is attempt 1/pass.

The canonical capture tree contains 70 files and 19,327,769 bytes. Its path-
independent sorted inventory object hash is
`8f27a0dc815905db3e7bdec3a07b4f1fd6e983677a393a981962d98e5db2a99a`.
The append-only ledger has exactly five valid hash-chained events; its tip is
`3914c4de40830bb3ebfae95f1e0a21a826a9bcac3ceceef2799ed5285b4e7d6d`.
The 4,375-byte ledger file has SHA-256
`e3659378342ee24de0633f03fd05a0bb002ed9cd9f5c8293789605b7da3fad5d`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `p4_startup_aware_queue.tape.catalog.json` | 27,840 | `ef40463ca582d57132d657efa54442b61920294b8327c2539fa3a950c3c65aac` | `21870ce152cd2bfde0fec24090aaff44dcf6810cca72d1cb481d2b3cd20bc911` |
| `p4_startup_aware_queue.tapes.json` | 262,322 | `519f9c5253d37693e5283fc0555e471bdfd28e95b762266b18d5733120887b42` | `e753350214dd2968686183159a219767702a08b333516e64c6d4bc704d935b05` |

The original zero-result manifest remains byte-identical with SHA-256
`35d5d81323ae4b8741986d21da66daa5f329aab8d2aac3417ba319b559646833`.
The tape-bound manifest passes generic, dedicated P4, and static JSON Schema
validation. It contains ten unique specifications and exactly five distinct
tape hashes. Within every seed, `execution_ready` and `startup_aware` bind the
same tape hash and workload specification, while all ten semantic-specific
reference keys remain distinct.

All ten reference hashes are still null. Neither `reference_builds` nor
`online` nor a selection file existed at audit time. Thus no offline social-
utility value, throughput, latency, cost, QPR, completion, or P4 decision has
been observed.

## 3. Authorization boundary

After this audit is committed, exactly the ten declared queue-semantics-
specific offline-reference builds may run against the frozen P4 binary and
the five bound tapes, in manifest order. Each first structurally valid build
is retained. Reference value or later performance cannot trigger a setting,
seed, or tape replacement.

Online execution remains blocked until all ten tables and receipts are bound
and independently checked for row/key/config/process/assignment-sequence
integrity. Selection freezing, the ten online runs, baseline compatibility,
formal confirmation, figures, and manuscript claims remain blocked.
