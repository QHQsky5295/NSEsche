# G6 lookahead offline-reference binding audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `b43b5c76522eb1e40962f780387226202ab38171`  
Prerequisite freeze commit: `ead6a4bf1ea7440c0a420715a0725e81d154c709`  
Status: five references complete and bound; online sampling not started

## Scope

This receipt audits the five predeclared, candidate-specific offline social-
utility reference builds for G6 `lookahead_preall_sched`.  These are reference
constructions, not online performance samples.  The build used the exact
D71--D75 workload tapes and release binary frozen before reference generation.

Run root:
`runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904`

## Bound artifacts

| Artifact | Canonical document hash | File SHA-256 |
|---|---|---|
| `g6.reference.catalog.json` | `c2058d94ba63ca2b3b1a3666d1bdcab9d9afcbdefd86612270d940954315e786` | `09d8018b98491eda2d94c3c06741797e4122994c4287bedd4bcd9ffb451763d7` |
| `g6.ready.json` | `d5b7a2143688f618a9ef286466d0c7c7a6b92687bb5bf97dab6e28ce9ca4c1f3` | `69f34423d632fbdb1de286f9dc0ca27c1e3da24fbb629b4dc7e52614b2b96965` |

`protocol validate g6.ready.json` passed with exactly five runs in one
development cell.

## Per-seed reference receipts

`completed` below is the completed-request count recorded by the reference
builder, not a Boolean flag.

| Seed | Reference table SHA-256 | Bytes | Lines | Completed |
|---|---|---:|---:|---:|
| D71 | `5295dc78c4e5366e2245d4284be520c5c27af514e68e2cbe4944cbda6e2a530a` | 260455 | 997 | 1636 |
| D72 | `79a50789fe0449bc08c3dc1b48549d00a0022bfd4a262d4a8e9c6d42a4a9e591` | 259132 | 988 | 956 |
| D73 | `521b646ae5743ce23713df51478725b119ab5509df73e1666999a6fd2399ac43` | 261691 | 996 | 588 |
| D74 | `f7e917a84e0f5931274cf0affd14598666c77dd7988c1a86711033e82b5db06a` | 261111 | 997 | 998 |
| D75 | `0aae10a08931b27cfc2a2be9718a3acbd5a6ed6243146e41332946010a9ea857` | 261376 | 997 | 1214 |

The five tables total 1,303,765 bytes and 4,975 JSONL records.

## Fail-closed checks

- All five reference keys are present exactly once in the catalog and bind to
  the same five run dependencies frozen in `g6.tapes.json`.
- Each reference completed on attempt 1 with attempt status `pass`, process
  exit code 0, `timed_out=false`, and adapter status `completed`.
- Every adapter receipt reports release-binary SHA-256
  `90988e545679a04f46f680d6ac7e0e0a52d8e1335c2d0309e73d4383c3147611`.
- Every table, reference-build receipt, and process-observation file exists and
  matches the SHA-256 bound into `g6.ready.json`.
- Each run's `artifact_hashes.offline_reference_sha256` equals its bound
  reference-table SHA-256.  State-pair and assignment-sequence hashes are
  non-null for every seed.
- The simulator module inventory was restored exactly after every build.
- The reference runner canonicalized one valid product for each key; the
  partial workspace contains zero files after promotion.
- `build_required=false` for all five bound dependencies.  No alternate or
  result-conditioned reference was substituted.
- The G6 `online` directory did not exist when this audit was made, so no
  throughput, QPR, latency, completion, or solve-time result could influence
  reference construction or binding.

## Authorization boundary

This audit authorizes exactly the five predeclared online candidate runs in
`g6.ready.json`, once each and in their fixed manifest order.  All valid first
canonical products must be retained.  The analyzer may be run only after all
five pass protocol QC.  Additional seeds, Q61--Q80 confirmation, figures, and
paper claims remain blocked until the frozen G6 development gates are applied.
