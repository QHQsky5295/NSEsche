# P5 common-platform tape and model input audit

Date: 2026-09-05 (Asia/Shanghai)

Parent capture-normalization audit commit: `e8ef4a9`

Status: `nine_tapes_and_faasrank_model_bound_ninety_references_authorized_after_commit`

## 1. Complete fixed tape population

The preregistered P5P01--P5P03 homogeneous-20 tapes were captured in fixed
low--middle--high, then seed order. All nine canonicalized on attempt 1. There
was no retry, seed replacement, quarantine, reference build, or online method
execution. Capture used the random scheduler only to materialize arrivals and
environment receipts; its incidental summaries are not P5 method outcomes.

| Load | Seed | Events | Tape SHA-256 |
|---|---|---:|---|
| low | P5P01 | 1,948 | `022d7a3484328932da24f771fa905fc3e5f1869231286a4dcfc499694720a07a` |
| low | P5P02 | 1,931 | `53faf38d65e3d1076d1b1a5b62a90c1d75f1592c86451e55bcd40baf53dd2e22` |
| low | P5P03 | 1,880 | `1f5a2a18c426209a5359869f59429c2f3edb99eedc10d0835edc56bc9f50340e` |
| middle | P5P01 | 2,543 | `e7c71047a15fe91ea1bf825a6a2c1d8f57226214f211da2ac2d3db22c28d6deb` |
| middle | P5P02 | 2,532 | `439cdb62ff87cb8a4c21f40fc952f25d77a771fdd065c37455b798cbcd705340` |
| middle | P5P03 | 2,481 | `42432ba1c99033079c6e2ffbab3c1ec56fd33f8a52f817f8c033a0e87b58d7e8` |
| high | P5P01 | 7,178 | `d1751455e073d5f61634281f0b1e80f5a4457d400e43d5ed5fb42dbafe47b5a9` |
| high | P5P02 | 6,996 | `605532b214f0135db9e74aeba3848de9094b9b749d8f98f8b44507738ca4f302` |
| high | P5P03 | 7,019 | `6bac286d7386578927e38c0b3cc07f3f3a76ba12af8d117ae8d952fa4f15d95e` |
| **Total** | **9 tapes** | **34,508** | **nine distinct hashes** |

Independent streaming inspection reopened every tape and rechecked tape
SHA-256, workload seed, event count, DAG-order hash, and first/last frame.
Every attempt record is attempt 1/pass; every process exited 0 without timeout
or launch error; every capture summary is complete and has the catalog event
count. Both the attempt and receipt bind
`reviewer-v4 -> reviewer-v3`, `admission=false`, and
`reviewer_v4_capture_normalized=true`. Every materialized run config agrees.

The canonical capture tree contains 126 files and 36,624,770 bytes. Its
path-independent sorted inventory object hash is
`34867d360472bbec747f1cd0bf05efb5f5317359edcfce618044cbf22f3b9d73`.
The append-only ledger has exactly nine valid hash-chained events; its tip is
`ab79340f1100a557942a324ae1c497458d151872d620a0cfda98512406ec13d9`.
The 8,016-byte ledger has SHA-256
`6de70c017c51c0551b694315726500dc5d0853f1ae4279d5ec7d6d6f01e20cc6`.

## 2. Tape binding and immutable model binding

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `input_stage/workload_tapes/catalog.json` | 53,474 | `d63f3cb90844c13d42df2cbc01608caa82f82f6c8e1db69e6cdb8d5512578871` | `541ab4a66ca0ce684fdb283a4dd01a439e13f9d1eb91cb28e6bbb4da5d1d563b` |
| `p5_common_platform.tapes.json` | 2,373,265 | `91b9955644f17c2c03068c9471d59d6e9795957a823820ec8d28f4e57eec6c47` | `565e1ba1ebb5ea00f8bf0d41e7c7c0b9ce347a72549cd3b0524eea4038d80baf` |
| `p5_common_platform.tapes.faasrank.json` | 2,583,639 | `89f42d26189f14e45ac122e7f8dea5692b1f8bfdaf38c5435d6405d4dc6b735d` | `9e82ce3eddf17d7ae92904cd3c2ded11c2f78d90cc6e83504de1d8b60b3676a7` |

The original zero-result manifest remains byte-identical at 2,225,005 bytes
with SHA-256
`5ea7c62f1543f0ca3c4ecef658b2605b688ca7c5d226eb4fae74894c133a6555`.
The tape-bound and model-bound manifests pass generic, dedicated P5, and
static JSON Schema validation. The final input state has 90 unique run IDs
and specifications, nine distinct evaluation tapes, 90 distinct method-state
reference keys, and exactly nine FaaSRank rows.

The reused frozen FaaSRank artifact is 20,795 bytes with SHA-256
`4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`.
Its calibration tape hash is
`28a48254c9a8589d708c305dc6c1a89be2714f8ab3df307058637c5f142325b9`,
which is absent from the nine P5 evaluation hashes. The standard model
verifier therefore proves training/evaluation disjointness before binding.
The model was not retrained, reselected, or changed.

The final legal staged state is `tapes=true`, `FaaSRank=true`,
`references=false`, and `SLA=false`. No `reference_builds`, `online`,
selection, or analysis path exists. Thus no P5 offline utility, throughput,
latency, cost, QPR, completion, rank, or method decision has been observed.

## 3. Authorization boundary

After this audit is committed, exactly the 90 declared method-state offline
reference builds may run against the frozen P5 binary and the model-bound
manifest, in manifest order. Each first structurally valid build is retained.
Reference utility value or later method performance cannot trigger a method,
seed, tape, model, or reference replacement.

Online selection freezing and all 90 online runs remain blocked until all 90
tables and receipts are bound and independently checked for row/key/config/
process/assignment-sequence integrity. Duplicate replay, analysis, figures,
paper claims, and the formal rerun remain blocked.
