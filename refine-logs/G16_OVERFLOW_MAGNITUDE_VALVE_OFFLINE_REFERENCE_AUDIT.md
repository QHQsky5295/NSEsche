# G16 Overflow-Magnitude-Gated Valve Offline-Reference Audit

Date: 2026-09-04 (Asia/Shanghai)

Parent freeze commit: `89da7ff3acbce2e2c555abaf15eec7e7d3db9628`

Status: `all_references_bound_analyzer_freeze_authorized_after_commit`

## 1. Result-blind reference construction

Exactly the 30 operational-mode-specific offline social-utility references in
the frozen G16 tape-bound manifest were built in paper order: low, middle,
high; C0 then G16 within each load; D111--D115 within each arm. All 30 builds
canonicalized on attempt 1. The partial tree retains 30 empty per-key
directories and zero files; no quarantine exists. No online candidate run has
been executed, so C0/G16 throughput, QPR, latency, cost, and candidate
comparisons were unavailable during construction.

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
| Table rows, total | 29,467 |
| Table rows, minimum / maximum | 968 / 995 |
| Positive / negative / zero reference rows | 29,464 / 3 / 0 |
| Build-completed observations, total | 25,937 |
| Build-completed observations, minimum / maximum | 100 / 1,860 |
| Partial files | 0 |

All reference rows are retained. The three negative rows occur only in the
fixed high-load D111 pair: one C0 row and two G16 rows, with a minimum value of
`-490.8881530761719`. Every table's total reference remains positive; the
minimum table total is `150872.6326417923`. The sign distribution was observed
only after the complete bank had been built and did not alter a seed, arm,
threshold, gate, or execution decision. Downstream analysis must report the
nonpositive-reference count rather than delete or silently replace these
states.

| Grouping | Reference-table rows |
|---|---:|
| C0 `ready_order` | 14,728 |
| G16 `ready_global_overflow_magnitude_release_valve` | 14,739 |
| low | 9,758 |
| middle | 9,765 |
| high | 9,944 |

The canonical reference tree contains 420 files and 303,921,953 bytes. Its
sorted inventory object hash is
`f730839424481e14fff400a358b71f10b8b2c4b8f092d1a6cad783a56a5acf55`.
The append-only 30-record build ledger has tip
`48e5222770b23779229868544f7a261c1e20fe97278c82de28a3b7164f72e7cc`;
the 29,878-byte ledger file has SHA-256
`bca1d31567cdd4316513ed9ae01da442e93a840b7fd71f0e240226f158fe91e1`.

## 2. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g16.reference.catalog.json` | 58,454 | `9e2bb4d074eb238ea66c36bcdc08305f342db98cbb3582ac62fb65c2fff6ca23` | `c8e6dcedffbfa169d5154febdea149a3dabc87e0f8bce6baf7e87b54646b6a2b` |
| `g16.references.json` | 846,507 | `bdda8e7b8f790c692760e1eb5eb7369d0e4f078bb3140883e6db514fae63eb65` | `fbea597e13a10d032b5c9483c2b754d061d6d19062389e41ae02ffd7588cb50e` |

The reference-bound manifest passes complete generic, G16-specific, and
static JSON Schema validation with `all_tapes_bound=true` and
`all_references_bound=true`. It contains 30 exact run specifications, 15
distinct tape hashes, 30 distinct reference-table hashes, and no online-result
binding. Every reference path, receipt path, process-observation path, and
runtime identity was rehashed after binding and agrees with the catalog and
run artifact hashes.

## 3. Scientific status and authorization boundary

Reference construction is input generation, not a comparison of C0 and G16.
All positive and negative reference observations remain in the frozen
evidence, and D111--D115 remain the complete fixed development seed bank.

After this audit is committed, only result-free implementation, testing, and
freezing of the G16 analyzer and exact 30-run selection are authorized. The
analyzer must retain zero-completion/null-QPR and adverse rows; report
nonpositive-reference observations; validate the exact 5/4 magnitude gate,
one-bit state machine, five modes, and nine zero-violation counters; verify
activation, PNE/reference/runtime/dispatch integrity; report every paired
seed, ratio, sign, sample SD, descriptive interval, leave-one-seed-out mean,
completion/latency/cost/QPR factor, and policy overhead; and enforce the
preregistered gate without threshold edits.

Online execution, strong baselines, confirmation, formal replay, figures, and
manuscript performance claims remain blocked until that zero-result analyzer
and selection checkpoint is independently audited and committed.
