# G18 Overflow Soft-Cap Valve Offline Social-Utility Reference Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent tape freeze commit: `d7d41c41298b9b27c0033d9f555ffe9ad5302dcd`

Status: `all_30_references_bound_result_blind_analyzer_only_next`

## 1. Exact reference population

Exactly 30 declared reference builds were executed in fixed paper order:
low, middle, and high; within each load D116--D120; within each seed C0
`ready_order` then G18 `ready_global_overflow_soft_cap_release_valve`. All 30
canonicalized on attempt 1. The partial tree retains 30 empty per-key
directories and zero files, and no quarantine directory exists.

Each reference used the protected G18 runtime, its already bound workload tape,
and its operational-mode-specific reference key. C0 and G18 therefore share
arrivals within each load/seed pair while retaining distinct active-player
semantics and reference tables. No online throughput, latency, cost, QPR, or
candidate comparison existed during construction.

## 2. Table and process integrity

Independent inspection reopened every table and verified file SHA-256, bytes,
unique state keys, line count, finite reference values, initial-assignment
hashes, and state-pair sequence hash. It independently reconstructed the
window observation pair count, state sequence, and final-assignment sequence
from each `nash_metrics.jsonl` and matched them to the table and receipt.

Every build summary is complete, uses the bound arrival count, and agrees with
the receipt's completion count. Every run configuration binds the intended
load, seed, tape, and C0/G18 operational identity. All process observations
report exit code zero, no timeout, and no launch error. The 30-event ledger is
valid, hash chained, attempt-1 only, and follows the preregistered execution
order.

| Load | Method | Tables | State rows | Rows/table | Positive | Zero | Negative | Missing | Mean reference |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| low | C0 | 5 | 4,848 | 957--987 | 4,848 | 0 | 0 | 0 | 189.737101 |
| low | G18 | 5 | 4,847 | 957--987 | 4,847 | 0 | 0 | 0 | 189.946415 |
| middle | C0 | 5 | 4,858 | 955--985 | 4,858 | 0 | 0 | 0 | 220.372051 |
| middle | G18 | 5 | 4,858 | 955--985 | 4,858 | 0 | 0 | 0 | 220.294122 |
| high | C0 | 5 | 4,966 | 989--998 | 4,966 | 0 | 0 | 0 | 671.939757 |
| high | G18 | 5 | 4,968 | 989--998 | 4,968 | 0 | 0 | 0 | 675.926063 |

All 29,345 reference rows are finite and strictly positive. The full observed
range is positive: low minima start at 14.377034, middle at 26.656654, and high
at 23.667564. Consequently, G18 exposes no widespread negative-reference
pathology and no formula or policy change is justified by this stage.

The canonical reference tree contains 420 files and 314,388,832 bytes. Its
path-independent inventory hash is
`84ec09256ef77d12cd83942e6e56dc58f03230ed5b5cd75de1471a2632c5cfd7`.
The 29,823-byte ledger has file SHA-256
`5369f14b6e2dba3c178599983bee89b737f5deb553e51e4f983aa4a116f856ed`
and tip `fc34172c9c4842262f146f4cbd51c3df40e25d3ca13a191c45fab3c62acd0d97`.

## 3. Catalog and reference-bound manifest

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g18.reference.catalog.json` | 58,293 | `d69b4dc26e7ded0e5091a959a2c255a23af4f82cd742a3e47e081d4a7e27951b` | `81d4105eb33f3d99567f9f06b34ebb20df80a470fa2b385ca6bbe6d3b182ba93` |
| `g18.references.json` | 845,984 | `694e5ad1242f7bb6254aa614660d7ec30b687d0b5e42e84aa7d9e7b54afc4a8b` | `81859abdaa4ff48eaa484f82cf0e4089a341d12cce38ba30308b5dfaa75241c5` |

The reference-bound manifest passes generic, G18-specific, and static JSON
Schema validation plus independent disk reopening. It has 30 unique run-spec
hashes, 15 tape hashes, 30 distinct reference hashes, exact C0/G18 pairing,
`all_tapes_bound=true`, and `all_references_bound=true`. Each run's artifact
hashes match its tape and reference table. The tape-bound manifest and frozen
binary remain byte-identical at SHA-256 `64ac6653...d0e9` and
`aaa0980c...af713`, respectively.

## 4. Scientific interpretation

This stage supplies the per-state offline social-utility reference required to
evaluate empirical equilibrium quality without changing the paper's welfare
definition. The near-equal low/middle method averages are expected because C0
and G18 share the same payoff and solver and differ only in which feasible-ready
players enter a window. The higher high-load G18 average reflects a different
visited-state set, not an online performance claim.

No reference value, state count, completion count, or method difference caused
a retry, omission, key replacement, seed replacement, or rule adjustment. All
valid observations remain retained. There is still no `online` directory and
no G18 throughput/QPR result, so the 20-node homogeneous comparison is not yet
closed.

## 5. Authorization boundary

After this audit and all reference evidence are committed, only construction
and freezing of the result-blind G18 analyzer and exact 30-row online selection
are authorized. The analyzer must encode all nine preregistered all-pass gates,
runtime/telemetry reconstruction, retained-row inventory, and the fixed
manifest order before an online result directory exists.

Online execution remains blocked until that analyzer/selection audit is
committed. Strong baselines, confirmation, heterogeneous experiments,
scalability, burst tests, figures, and manuscript claims remain blocked by the
unfinished 20-node homogeneous main comparison.
