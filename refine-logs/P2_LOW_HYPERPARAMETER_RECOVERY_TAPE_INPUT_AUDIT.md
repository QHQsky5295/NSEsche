# P2 Low-Load Hyperparameter Recovery Tape and Input Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent zero-result manifest commit: `93a5e8c2c8e01d627e0baccf14f39330c1b7cc09`

Status: `all_five_tapes_bound_exact_25_reference_builds_authorized_after_commit`

## 1. Complete fixed input population

The five preregistered D121--D125 homogeneous-low base tapes were captured in
seed order. All five canonicalized on attempt 1. There was no retry, seed
replacement, quarantine, or parameter-setting execution. Capture used the
random scheduler only to materialize arrivals and environment receipts; its
incidental summaries are not parameter-screen outcomes.

| Seed | Events |
|---|---:|
| D121 | 1,956 |
| D122 | 1,901 |
| D123 | 1,933 |
| D124 | 1,903 |
| D125 | 1,910 |
| **Total** | **9,603** |

The natural range is 1,901--1,956 events. Independent streaming inspection
reopened every tape and rechecked file SHA-256, workload seed, event count,
DAG-order hash, capture receipt, run configuration, and process observation.
All five tape hashes are distinct.

The canonical capture tree contains 70 files and 19,528,918 bytes. Its
path-independent sorted inventory hash is
`6c757b42f0aaa85100ae536f31320797c90a4de0303423246f8d6220324cb399`.
The append-only ledger has exactly five valid hash-chained events; its tip is
`b60347b5d2ba62b1accacb67ccb090d79def6e59505ef1fc96e50086e76606f2`.
The 4,515-byte ledger file has SHA-256
`b483e3efb105dab021717fd439035e312f28a9a172dcb586562f82ad420d67dd`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `p2-low.tape.catalog.json` | 28,120 | `d09f61b0059329d4b11139c4b21444c93a17a3bd7977877417271a234ffc5442` | `1ccc069f487395e4237d2b298b79a0e28965ac187b29a773ecd657571febf8df` |
| `p2-low.tapes.json` | 629,027 | `383306452515cf92bb327d5629203b871da74d7b583c2baa6d4758b490cc5bfe` | `6c181baee71a5fe3bbbcdd74ededab548c2b14b54429defcea5ad03993c93020` |

The original zero-result manifest remains byte-identical with SHA-256
`2a34025eb9a6a412cc76d9560f9df9906d00fc812553871d59eed57b625b1bc7`.
The tape-bound manifest passes generic, dedicated P2, and static JSON Schema
validation. It contains 25 unique specifications and exactly five distinct
tape hashes. Within every seed, all five parameter settings bind the same tape
hash and workload specification, while all 25 parameter-specific reference
keys remain distinct.

All 25 reference hashes are still null. Neither `reference_builds` nor
`online` existed at audit time. Thus no offline social-utility value,
throughput, latency, cost, QPR, completion, or selection has been observed.

## 3. Authorization boundary

After this audit is committed, exactly the 25 declared parameter-specific
offline-reference builds may run against the protected binary and the five
bound tapes, in manifest order. Each first structurally valid build is
retained. Reference value or later performance cannot trigger a parameter,
seed, or tape replacement.

Online execution remains blocked until all 25 tables and receipts are bound
and independently checked for row/key/config/process/sequence integrity.
Selection freezing, the 25 online runs, formal Q81--Q100, baselines, E7
figures, and manuscript claims remain blocked.

