# G3 operational E0 offline-reference binding audit

Date: 2026-09-03  
Status: complete; the frozen 135-run online development stage is next

## 1. Scope and result blindness

This audit closes only the preregistered 90-dependency offline social-utility
reference stage for C0/C1/C2 on D71--D75. Reference construction was performed
from the already tape/model-bound manifest and the final `93b572d` release.
No online candidate or baseline run existed, and no throughput, QPR, latency,
cost, completion, or Nash-efficiency comparison was inspected.

## 2. Complete reference product

The atomic build command completed with exit code zero. All 90 dependencies
were canonicalized from attempt 1 through `verified_exact_copy`; the stage has
90 canonical directories, zero failed directories, and zero quarantine
directories. Exact factor coverage is:

- candidates: 30 `ready_order`, 30 `ready_pne_envelope_first`, and 30
  `ready_pne_envelope_each` references;
- loads: 30 low, 30 middle, and 30 high references;
- topologies: 45 homogeneous and 45 heterogeneous references;
- seeds: 18 references for each of D71, D72, D73, D74, and D75.

The observed catalog key set equals the 90-key dependency set in
`g3_e0.model.json`: zero missing and zero extra keys. Every dependency has a
unique build-spec hash, table path/hash, receipt path/hash, process-observation
path/hash, state-pair-sequence hash, and assignment-sequence hash. Reference
tables contain 938--997 state-pair rows and 245,394--261,991 bytes. All
`build_completed` counts are positive (52--2,460).

The builder itself verified, for every dependency, successful process exit,
absence of a retained partial table, complete simulation output, arrival-count
equality with the frozen tape, and exact equality between the reference table
and the build-time state-pair/assignment sequences. An independent metadata
reconciliation found zero mismatches between all 90 catalog entries and their
90 build receipts.

## 3. Immutable catalog and ready manifest

Reference catalog:

- schema: `NSE_REFERENCE_CATALOG_V1`;
- document `catalog_hash`:
  `97b916f1dbbc4f02bae436d393620041d376e9306394aed408e9edfe20e0e34f`;
- file SHA-256:
  `2ed0cb2c4b0d4f1593081b52765d35958dd0512f4d3b2ffeaa6d4fb1eb44118c`;
- bytes: 170,037.

The fail-closed binder then re-read and hash-checked every table, receipt, and
process observation and checked each build-spec and workload-tape hash against
its run dependency. It produced:

- path: `g3_e0.ready.json`;
- run/reference counts: 135 / 90;
- document `manifest_hash`:
  `c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657`;
- file SHA-256:
  `a54f0fbbbe02d0b1559b1b094eeefe77f1860b522a6c26b9c69b03262ced02f4`;
- bytes: 3,204,009;
- flags: `all_tapes_bound=true`, `all_faasrank_models_bound=true`, and
  `all_references_bound=true`.

`all_sla_targets_bound=false` is expected because the G3 manifest contains no
balanced-QoS run and therefore has no SLA artifact dependency.

## 4. Next gate

Exactly the 135 online runs declared by `g3_e0.ready.json` may now execute as
one complete development stage: 90 C0/C1/C2 candidate runs across all six
cells and 45 paired homogeneous-low baseline runs. Every valid run must be
retained. Candidate selection and all admission gates remain blocked until the
complete 135-run product passes runtime/provenance/QPR validation. No seed or
cell extension is authorized. Formal homogeneous-middle execution and every
paper-ready result group remain blocked.

