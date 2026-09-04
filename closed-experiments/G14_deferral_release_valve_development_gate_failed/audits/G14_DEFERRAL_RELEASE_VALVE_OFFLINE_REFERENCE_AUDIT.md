# G14 Deferral Release-Valve Offline-Reference Audit

Date: 2026-09-04 (Asia/Shanghai)
Parent freeze commit: `834dacdb4187b89636c33253a02f35c4ae4d36ed`
Status: `all_references_bound_analyzer_freeze_authorized_after_commit`

## 1. Result-blind reference construction

Exactly the 30 operational-mode-specific offline social-utility references in
the frozen G14 tape-bound manifest were built in paper order: low, middle,
high; C0 then G14 within each load; D106--D110 within each arm. All 30 builds
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
| Table rows, total | 29,414 |
| Table rows, minimum / maximum | 941 / 997 |
| Positive / negative / zero reference rows | 29,414 / 0 / 0 |
| Build-completed observations, total | 32,463 |
| Build-completed observations, minimum / maximum | 175 / 2,712 |
| Partial files | 0 |

All reference rows are retained. The absence of negative or zero rows is an
observed property of this fixed reference bank and was not used to alter a
seed, arm, gate, or execution decision.

| Grouping | Reference-table rows |
|---|---:|
| C0 `ready_order` | 14,704 |
| G14 `ready_global_deferral_release_valve` | 14,710 |
| low | 9,748 |
| middle | 9,738 |
| high | 9,928 |

The canonical reference tree contains 420 files and 303,952,789 bytes. Its
sorted inventory object hash is
`a8f912c01abf631b7ba02b4957c03e8114ef47d1ea94d04ba23b6111ef872d17`.
The append-only 30-record build ledger has tip
`c2539f3e6e5411a5ff93c0fb219f92204665188ae29c1157221f0add44bf5fcb`
and its 29,759-byte file has SHA-256
`f18ea5dd4d27549e398aadd91e86e110d5e59923e6b7d842e90793dfe3fca67d`.

## 2. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g14.reference.catalog.json` | 58,244 | `eb4d777b82ffe1b8e16c50b9c5eef231d1b52ec718a4f0ac823da21e3781ef21` | `160a52568ad0104f69ec7b822da05c1e5e4236fcf4760b8601ff3a858f1d93c0` |
| `g14.references.json` | 848,748 | `92eab2178b7a7a69023e8afa19768dcf9b717caed6a18660b64f94fb294dac26` | `6ac843330b50df77d6034de66175be17235ff10a56017cc4e2c9b592116b25f1` |

The reference-bound manifest passes complete generic, G14-specific, and
static JSON Schema validation with `all_tapes_bound=true` and
`all_references_bound=true`. It contains 30 exact run specifications, 15
distinct tape hashes, 30 distinct reference-table hashes, and no online-result
binding. Every reference path, receipt path, and process-observation path was
rehashed after binding and agrees with the catalog and run artifact hashes.

## 3. Scientific status and authorization boundary

Reference construction is input generation, not a comparison of C0 and G14.
All reference observations remain in the frozen evidence. D106--D110 remain
the complete fixed development seed bank.

After this audit is committed, only result-free implementation, testing, and
freezing of the G14 analyzer and exact 30-run selection are authorized. The
analyzer must retain zero-completion/null-QPR and adverse rows; validate the
candidate's exact runtime state machine and seven zero-violation counters;
verify activation, PNE/reference/runtime/dispatch integrity; report every
paired seed, ratio, sign, sample SD, descriptive interval, leave-one-seed-out
mean, completion/latency/cost/QPR factor, and policy overhead; and enforce the
preregistered gate without threshold edits.

Online execution, strong baselines, confirmation, formal replay, figures, and
manuscript performance claims remain blocked until that zero-result analyzer
and selection checkpoint is independently audited and committed.
