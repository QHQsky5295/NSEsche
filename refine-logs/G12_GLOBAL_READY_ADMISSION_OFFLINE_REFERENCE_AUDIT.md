# G12 Global-Ready Admission Offline-Reference Audit

Date: 2026-09-04 (Asia/Shanghai)  
Parent freeze commit: `62488dd84048c51b0fb3e547a3f9168f0c2693b3`  
Status: `all_references_bound_analyzer_freeze_authorized_after_commit`

## 1. Result-blind reference construction

Exactly the 30 operational-mode-specific offline social-utility references in
the frozen G12 tape-bound manifest were built in paper order: low, middle,
high; C0 then G12 within each load; D101--D105 within each arm. All 30 builds
canonicalized on attempt 1. The partial tree contains zero files and no
quarantine exists. No online candidate run has been executed, so throughput,
QPR, latency, cost, and candidate comparisons were unavailable during
construction.

Independent streaming verification reopened every table and recomputed its
file size, physical JSONL row count, SHA-256, state-key uniqueness,
hexadecimal/unsigned state-key equivalence, status/value consistency, and
state/assignment sequence hashes. It independently rehashed and reconciled
each build receipt, process observation, run configuration, Nash welfare
observation, summary, build-spec hash, workload-tape hash, seed, load, and
operational identity.

| Dimension | Count or value |
|---|---:|
| Reference entries / unique table hashes | 30 / 30 |
| Exact arm-load-seed cells | 30 |
| Table rows, total | 29,395 |
| Table rows, minimum / maximum | 931 / 998 |
| Positive / negative reference rows | 29,393 / 2 |
| Build-completed observations, total | 37,230 |
| Partial files | 0 |

Both negative-valued rows are retained as valid, hashed reference-table
observations. Neither was deleted or used to alter a seed, arm, gate, or
execution decision.

| Grouping | Reference-table rows |
|---|---:|
| C0 `ready_order` | 14,690 |
| G12 `ready_global_player_admission_n` | 14,705 |
| low | 9,712 |
| middle | 9,740 |
| high | 9,943 |

The canonical reference tree contains 420 files and 298,686,107 bytes. Its
sorted inventory object hash is
`28f2d35ed1a688afe63fff59451cd04d7b90658fc6eb03714fb782e1ea5e1539`.
The append-only 30-record build ledger has tip
`538839b045e94bf809aa9f243cca1fb6d871cdaf8c5b4c3c51a447eb0a5df099`
and file SHA-256
`1745e80dab2d83f2c6490b999c1f79b7e8cd3b8953a57a09cc3fd57863c96c92`.

## 2. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g12.reference.catalog.json` | 57,947 | `5d79292503a538e7b7f5f0ba699a6f5cd2b23859ca807fd36a6dd0828196ae2b` | `a4e9aba817eb6ace718e434b96d1eef615e3181188a940261e12e26701e390a2` |
| `g12.references.json` | 847,279 | `4c0140a0a9c92ebe0fe4afb8167b380e7a3a512560534694690d4439fa704209` | `ec5708cc4e7661d2efce1570bc6a2a6d617a82df8a34a5fb25dda5add4eabb96` |

The reference-bound manifest passes complete generic and G12-specific
validation with `all_tapes_bound=true` and `all_references_bound=true`. It
contains 30 exact run specifications, 15 distinct tape hashes, 30 distinct
reference-table hashes, and no online-result binding. Every reference path,
receipt path, and process-observation path was rehashed after binding and
agrees with the catalog and run artifact hashes.

## 3. Scientific status and authorization boundary

Reference construction is input generation, not a comparison of C0 and G12.
All reference observations, including the two negative rows, remain in the
frozen evidence. D101--D105 remain the complete fixed development seed bank.

After this audit is committed, only result-free implementation, testing, and
freezing of the G12 analyzer and exact 30-run selection are authorized. The
analyzer must retain zero-completion/null-QPR and adverse rows; validate the
candidate's exact run contract and six zero-violation counters; verify
activation, PNE/reference/runtime/dispatch integrity; report every paired
seed, ratio, sign, sample SD, descriptive interval, leave-one-seed-out mean,
completion/latency/cost/QPR factor, and policy overhead; and enforce the
preregistered gate without threshold edits.

Online execution, strong baselines, confirmation, formal replay, figures, and
manuscript performance claims remain blocked until that zero-result analyzer
and selection checkpoint is independently audited and committed.
