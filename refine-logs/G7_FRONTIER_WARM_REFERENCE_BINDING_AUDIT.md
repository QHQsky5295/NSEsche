# G7 frontier-warm offline-reference binding audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `9c16366d820b824db12bb6c320e6afabd934ec8`  
Prerequisite zero-data freeze commit: `df7a56eb1f51b28c51f64de2251b09b246d48613`  
Status: five references complete and bound; online sampling not started

## Scope

This receipt audits the five predeclared, candidate-specific offline social-
utility reference builds for G7 `lookahead_frontier1_warm_init`. These are
reference constructions, not online performance samples. The build used the
exact D71--D75 workload tapes and release binary frozen before reference
generation.

Run root:
`runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904`

## Bound artifacts

| Artifact | Canonical document hash | File SHA-256 |
|---|---|---|
| `g7.reference.catalog.json` | `432242880788e0fe88fd07b278e3dca6aa3bc74ffd33606395982a423d2b476b` | `112308d19b2e8ca552861fe25539ebfcabd015dd1af8b0581f8bf06dbc8d9557` |
| `g7.ready.json` | `37f26c48f6a78779d62d42acbedd440774d716ffc6818623a196925d97b6f4ae` | `4e285e025a1612480177ad1b2bcab52f4a0fe28886abca2186441cf75bd39567` |

`protocol validate g7.ready.json` passed with exactly five runs in one
development cell. The manifest retains `formal_results_eligible=false`.

## Per-seed reference receipts

`completed` below is the completed-request count recorded by the reference
builder, not a Boolean flag.

| Seed | Reference table SHA-256 | Bytes | Lines | Completed |
|---|---|---:|---:|---:|
| D71 | `b56196a08f797f00484fc1eeccac9acd3751b535c28d5852b9ca45b2ad801d0f` | 259269 | 992 | 1835 |
| D72 | `fe8dfb76b342191a75befd6f662614f9e676abf37ab5a93967ec7cdc2d95deca` | 257315 | 981 | 853 |
| D73 | `77972a11c64b58faae75fe23b7e4433907a64931ebdc2b1b4c1e3063de2f3be3` | 257835 | 984 | 669 |
| D74 | `fd6b66f16c2e6947dd09953337f32922676911d7dc3a69434b02691200c221a2` | 259317 | 991 | 1007 |
| D75 | `9ca9bef78fca20be54556bcc26d216d1505ebde925cd9ecbde0543613a90763b` | 259459 | 991 | 926 |

The five tables total 1,293,195 bytes and 4,939 JSONL records.

## Fail-closed checks

- All five reference keys are present exactly once, in D71--D75 manifest
  order, and bind to the same five dependencies frozen in `g7.tapes.json`.
- Each reference completed on attempt 1 with attempt status `pass`, process
  exit code 0, `timed_out=false`, no launch error, and adapter status
  `completed`; no technical retry was used.
- Every adapter receipt reports release-binary SHA-256
  `593f79671b7b8659b7df6ef2c2c240e74f409ed53c3956e4e2cfaca93e2918b7`.
- Every table, reference-build receipt, and process-observation file exists and
  matches the SHA-256 bound into `g7.ready.json`. Table byte counts, line
  counts, state-pair sequence hashes, and assignment-sequence hashes agree
  across the tables, catalog, and receipts.
- Each reference build-spec hash equals its frozen unbound dependency, and
  every workload-tape hash equals the corresponding projected tape binding.
- Each run's `artifact_hashes.offline_reference_sha256` equals its bound
  reference-table SHA-256, and `build_required=false` for all dependencies.
- The simulator module inventory was restored exactly after every build, with
  equal pre-run and post-restore hashes.
- The reference runner retains exactly five canonical products; partial and
  quarantine contain no attempt directories after promotion. No alternate or
  result-conditioned reference was substituted.
- The G7 `online` directory did not exist when this audit was made, so no
  throughput, QPR, latency, completion, solve-time, or frontier result could
  influence reference construction or binding.

## Authorization boundary

This audit authorizes exactly the five predeclared online candidate runs in
`g7.ready.json`, once each and in fixed manifest order D71--D75. All valid
first canonical products must be retained. The analyzer may be run only after
all five pass protocol QC. Additional seeds, Q61--Q80 confirmation, later
formal cells, figures, and paper claims remain blocked until the frozen G7
development gates are applied.
