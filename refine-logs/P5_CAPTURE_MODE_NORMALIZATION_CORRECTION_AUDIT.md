# P5 capture-mode normalization correction audit

Date: 2026-09-05 (Asia/Shanghai)

Correction preregistration commit: `57d87ee`

Correction implementation commit: `2cbeb9ac02da55d200a757c1ba8841087d677487`

Status: `capture_normalized_zero_result_protocol_frozen_tape_capture_authorized`

## 1. All three failed instances remain closed

The `5bd817e`, `3de688c`, and `11e682f` source-bound instances each retain
exactly three quarantined attempts and a terminal `capture_blocked` event.
None contains a workload tape, tape catalog, summary, canonical capture,
online result, rank, or metric. None may be resumed, promoted, or used as
input.

The third instance's retained input tree has 19 files, 66,013 bytes, and
inventory hash
`8753d9f4c6552d74ef7ea86bf9a6b6d0a029102a25920b470c78d8170a32c2e2`.
Its four-event ledger has SHA-256
`3e45c5abec94219631430a2315a7082f8847248e3e8c9b624a051f76b7e79fcf`
and tip
`174bcb94b2b3e7cbf7e9505f7e9b6666bdf53b01131ec6baae5f2cb272fed1b3`.
All three attempts reached Rust reset validation but stopped before simulation
on the same contradictory capture/admission payload.

## 2. Exact correction and verification

Commit `2cbeb9a` introduces one capture-run materializer. It deep-copies the
source run and, only when the source protocol is reviewer-v4, changes the
input-only clone to reviewer-v3 and the exact disabled-admission defaults:

- `enabled=false` and `policy="disabled"`;
- `drain_cpu_work_multiplier=4.0`;
- `minimum_drain_frames=1000`; and
- `stop_when_drained=true`.

The helper records source protocol, capture protocol, capture admission state,
and normalization status in both attempt metadata and successful capture
receipts. Existing reviewer-v3 capture behavior is unchanged. The source run
is never mutated. Every P5 manifest, reference, duplicate, and online run
remains reviewer-v4 with the frozen FCFS admission/drain contract.

No Rust source, NSESche source, paper equation/parameter, P5 run field, seed,
method, workload profile, topology, HPA, reference identity, metric, gate, or
retention policy changed.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/stages.py` | 33,022 | `889ce3a829b55710fae5c785f6c341b1456958ac751d1224d344666ca872c838` |
| `protocol/tests/test_stage_promotion.py` | 5,319 | `d3490ffa6a183dd12e4350a1f0446bad9625239a554ebeae62691f28777f524e` |
| correction preregistration | 3,435 | `1308b35a51aa0b06cd8836267823c86ca70d560f358f9e6b273c8e0a6aa779a9` |

Directed stage/P5/adapter tests pass 18/18 in 7.314 s. The full protocol suite
passes 288/288 in 755.825 s. Python formatting/compilation and
`git diff --check` pass. The tests prove exact reviewer-v4 clone
normalization, unchanged reviewer-v3 behavior, source-object immutability, and
unchanged reviewer-v4/admission-enabled P5 manifest rows.

## 3. Capture-normalized release and zero-result manifest

The source-bound release is:

- path:
  `serverless_sim/target_p5_common_platform_capture_normalization_impl/release/serverless_sim.exe`;
- source commit: `2cbeb9ac02da55d200a757c1ba8841087d677487`;
- bytes: 5,013,504; and
- SHA-256:
  `945e0deca86466f9ef322bba25c779f5240d45d7e376c740ed54d240688262d8`.

The fourth zero-result manifest is:

`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/p5_common_platform.manifest.json`

- bytes: 2,225,005;
- file SHA-256:
  `5ea7c62f1543f0ca3c4ecef658b2605b688ca7c5d226eb4fae74894c133a6555`;
- canonical object hash:
  `ebeaa6c79c5f04599bf5b29b5658dbf1cd3eb83d06007ac566a586a5ca1cf5ee`;
- embedded pre-self manifest hash:
  `0cb21659a9e75f1502f0c56ea1c40644c290130d030bd4ac9aa1516b0360de8c`;
- 90 unique run IDs/specs, nine unique tape keys, and 90 unique references;
- every formal run remains reviewer-v4, admission-enabled, and
  `mix/high/cpu`;
- tape, FaaSRank, and reference bindings all remain false;
- generic, dedicated P5, and static JSON Schema validation pass; and
- its directory contains only the manifest.

The manifest has no tape, reference, result, rank, selection, metric, or
paper-eligible row.

## 4. Authorization boundary

After this audit commit, exactly nine input-only tapes may be captured from
the `2cbeb9a` manifest in a new workspace, one key at a time in fixed
low--middle--high, then P5P01--P5P03 order. The first QC-valid capture for each
key is canonical. All three prior workspaces remain closed.

After all nine tapes are independently validated and hash-bound, the existing
FaaSRank artifact may be bound only after proving training/evaluation tape
disjointness. Reference construction, online methods, duplicate replay,
analysis, figures, and claims remain blocked pending a committed input audit.
