# P4 Startup-Aware Queue Offline Social-Utility Reference Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent tape-input audit commit: `0d57fef45732c4de5cfd60d13c8844470750c8b6`

Status: `all_ten_references_bound_result_blind_selection_only_next`

## 1. Exact reference population

Exactly the ten declared semantic-specific reference builds were executed:
five `execution_ready` and five `startup_aware` tables over D126--D130. All
ten canonicalized on attempt 1. There was no retry, omission, key replacement,
seed replacement, quarantine, or online queue-pressure run. Both semantics
share the already bound tape within seed but have separate schema-15 reference
keys and tables.

## 2. Table and process integrity

Independent inspection reopened every table and verified file SHA-256, bytes,
unique state keys, line count, finite reference values, initial-assignment
hashes, and state-pair sequence hash. It independently reconstructed the
window observation pair count, state sequence, and final-assignment sequence
from each `nash_metrics.jsonl` and matched them to the table, receipt, catalog,
and ready manifest.

Every build summary is complete, uses the bound arrival count, and agrees with
the receipt's completion count. Every run configuration binds the intended
seed, tape, and queue-pressure semantics. All process observations report exit
code zero, no timeout, and no launch error. All attempt records are attempt
1/pass.

| Queue semantics | Tables | State rows | Rows/table | Positive | Zero | Negative | Missing | Mean reference |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| execution_ready | 5 | 4,900 | 965--989 | 4,900 | 0 | 0 | 0 | 196.520475 |
| startup_aware | 5 | 4,903 | 968--988 | 4,903 | 0 | 0 | 0 | 191.605546 |

All 9,803 rows are finite and strictly positive. The complete range is
6.404343--974.263489. The semantic means describe different visited-state
sets and are not an online throughput, latency, cost, QPR, or superiority
claim.

The canonical reference tree contains 140 files and 104,561,510 bytes. Its
path-independent inventory hash is
`24c5757bda0c030ce7c7ca6d474b7959701a0d795406d4faa47b8299be133546`.
The 9,729-byte ledger has ten valid attempt-1 hash-chained events, file SHA-256
`74bcf419dc3b3b0d7023b34062b02a9dc75fce460b601febf374a0ec100256ca`,
and tip
`a7b3ff4ebab11af3055b79260cba94d308119fce6a3b55953bebae9f431b89ce`.
The partial tree contains zero files and no quarantine directory exists.

The first independent read-only audit invocation reported only two audit-
script assumption mismatches: it looked for `workload_tape_sha256` inside the
bound dependency rather than the parent run, and filtered the wrong ledger
event name. All table, receipt, state/assignment sequence, configuration,
process, and value checks had already passed. The checker was corrected to the
protocol schema and rerun on the same immutable files; no reference was rerun
or modified.

## 3. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `p4_startup_aware_queue.reference.catalog.json` | 19,058 | `a3842b484c132a281f5d480b1ddbafc6b7e058a0517f60186c2a86ad9efa4517` | `baa0c0ef997afc2b33a398ae51f20465ae6d65fe6d20f376b4c173f0a0c7175d` |
| `p4_startup_aware_queue.ready.json` | 282,606 | `835625463b598fbd4fb24242d3779013c80505bd2fa5f17478a773924a5d676a` | `c3db56e4ad4cd891e02b809686575942f1f896bb07f32901b442f601ab700d08` |

The ready manifest passes generic, dedicated P4, and static JSON Schema
validation. It has ten unique run specs, five paired tape hashes, ten distinct
reference hashes, `all_tapes_bound=true`, and `all_references_bound=true`.
Every run's table, receipt, process, state-pair, assignment-sequence, and tape
identities match independently reopened artifacts. The tape-bound manifest
and frozen runtime remain byte-identical at SHA-256
`519f9c5253d37693e5283fc0555e471bdfd28e95b762266b18d5733120887b42`
and `d59efe5d40a9ee1a565fa9d37e7533863af28e52eafc3f328d87af7ec433664a`.

No reference value, row count, completion count, or semantic difference
caused a retry, omission, replacement, or gate adjustment. There is still no
`online` directory and no selection artifact.

## 4. Authorization boundary

After this audit is committed, only construction and freezing of the result-
blind P4 analyzer selection for the exact ten ready-manifest rows is
authorized. The already committed analyzer must remain byte-identical and
must encode all ten preregistered conjunctive conditions.

Online execution remains blocked until that analyzer/selection audit is
committed. Baseline compatibility, formal confirmation, later loads, figures,
and manuscript claims remain blocked.
