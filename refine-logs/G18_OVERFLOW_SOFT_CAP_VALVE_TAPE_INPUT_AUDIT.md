# G18 Overflow Soft-Cap Valve Tape Capture and Input-Binding Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent freeze commit: `f03835e7efc7bf1e4372df79afab266175954651`

Status: `all_tapes_bound_exact_30_reference_builds_authorized_after_commit`

## 1. Result-blind tape capture

The 15 preregistered base tape identities were captured in paper-experiment
order: low D116--D120, middle D116--D120, then high D116--D120. All 15
canonicalized on attempt 1. The partial tree retains 15 empty per-key
directories and zero files; no quarantine directory exists. Capture used the
random scheduler only to materialize arrival events and environment/provenance
receipts. It did not run or compare C0, G18, or any performance baseline.

Independent streaming inspection reopened every tape and verified its file
SHA-256, workload seed, event count, DAG-order hash, monotone first/last frame,
and catalog binding. Capture receipt, process observation, run configuration,
semantic environment bundle, summary completion, and arrival-count bindings
were independently rechecked. The append-only ledger has exactly 15 valid
hash-chained canonicalization records in the same low/middle/high order.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,919 | 1,941 | 9,657 |
| middle | 5 | 2,434 | 2,568 | 12,482 |
| high | 5 | 6,751 | 7,152 | 34,919 |
| total | 15 | 1,919 | 7,152 | 57,058 |

All 15 tape hashes are unique. The canonical capture tree contains 210 files
and 59,161,173 bytes. Its path-independent sorted inventory object hash is
`f1ba0ade39247cddac18a05268a40fa2a7e149997dac28387caef10fa15980c8`.
The ledger tip is
`d4e92653573e20f77c1939a20e94f376a457027fe62fb70ba53ca79971a9003d`;
the 13,246-byte ledger file has SHA-256
`be388462b56544ab007ce98b043a15e9ef2cb6d53071af523d4126fe865924b2`.

## 2. Catalog and bound-manifest receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g18.tape.catalog.json` | 88,720 | `a89fd0cb00bb4363db8f5e2c9d613f20685acd6884ce742b2a9a32e4aab162b6` | `898aea6b16e8615f7cba5ef752eddfc801a10d28af9fab8eeb9cb41b4974a3ac` |
| `g18.tapes.json` | 783,880 | `64ac6653df56fd4b1c86a12490e46f49fa8cd66f1d72705344fb06743707d0e9` | `79de5015444ea89647a248ab88605d13837bd933f147f4158f450fa30bfd590a` |

The bound manifest passes generic, G18-specific, and static JSON Schema
validation. It has `all_tapes_bound=true`, 30 unique run specifications, 15
distinct tape hashes, 15 exact load/seed groups with two arms each, and 30
distinct operational-mode reference dependencies. Within every group, C0 and
G18 bind the same tape hash and workload specification while their reference
keys remain distinct. Since this development stage has no FaaSRank or QoS-SLA
arm, `all_faasrank_models_bound=false` and `all_sla_targets_bound=false` are
correct and inapplicable rather than missing performance inputs.

The original unbound manifest remains byte-identical with SHA-256
`b27d71567eda59a6e506834e750c2ad1e332b8e39bad879a1597cb39fcb1af42`.
The protected runtime remains byte-identical with SHA-256
`aaa0980cf451a88f7b3652f55c3e8c624af2a71b6312c40f4b19aa83bf6af713`.

## 3. Scientific status

No request completion, throughput, latency, cost, QPR, scheduler reference, or
candidate outcome was used to select, recapture, omit, or relabel a tape. The
incidental random-scheduler capture summaries are input-generation receipts,
not C0/G18 observations or evidence for the development gate. Natural
seed-to-seed event-count variation is retained exactly. There is no
`reference_builds` directory and no `online` directory, and all 30 reference
hashes remain null. Thus C0/G18 performance and offline social-utility values
remain unobserved.

## 4. Authorization boundary

After this audit, catalog, bound manifest, capture tree, and append-only ledger
are committed, exactly the 30 declared offline-reference builds are
authorized. They must use the protected runtime, the 15 bound tapes, and the
distinct C0 and G18 operational identities. Each first QC-valid reference
build is retained; reference value, solver behavior, or later performance
cannot trigger seed/mode replacement, recapture, omission, or down-weighting.

Online execution remains blocked until all 30 reference tables, catalogs,
hashes, row counts, state/assignment sequence hashes, process observations,
and mode identities are independently audited and committed. Analyzer
construction, strong baselines, confirmation, formal replay, figures, and
manuscript claims remain blocked.
