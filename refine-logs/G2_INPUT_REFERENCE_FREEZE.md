# G2 Input and Reference Freeze

Date: 2026-09-03 (Asia/Shanghai)

Status: all frozen G2 development inputs and matching references complete;
the 135-run online development screen is authorized; no result is formal or
paper-eligible

## 1. Frozen boundary

This freeze keeps the source, protocol, executable, candidate family, seed
bank, workload parameters, and selection/gating rules recorded in
`G2_PROTOCOL_RUNTIME_FREEZE.md` unchanged. It adds only the artifacts required
to make the already-preregistered development manifest executable.

- Run root: `runs/tscv1_g2_init_d66_d70_3ae7792_20260903`.
- Candidate source commit:
  `3ae7792782adcef60a254fa7c6bdb60a43d8171d`.
- Protocol commit:
  `5926c99d35f7788140d40f6bbcb4f879033f88ad`.
- Executable SHA-256:
  `18f5f85ac6bd5276948709ed1c0abc42dfdb4c070fbd63af6cd0a00cb19c810d`.
- Development seeds remain exactly D66--D70.
- `formal_results_eligible=false`; this bank cannot provide manuscript
  evidence or replace an independent formal confirmation bank.

## 2. Input-only capture closure

All 30 preregistered workload tapes completed and canonicalized on attempt 1.
The exact-copy verifier accepted every canonical artifact; no tape was
deleted, replaced, or rerun based on a measured outcome.

- Tape catalog: `g2.tape.catalog.json`.
- Tape-catalog document hash embedded in the ready manifest:
  `bc42cd3d484faa3859a44662aa882f2ecaecfac8969bd1f54ec69eaaab37a30d`.
- Tape-catalog file SHA-256:
  `ca53e72b806771f3a5342ac9e692e3b7232a92f6407227e168ebaec3479b41fe`.
- Tape ledger: 30 events; final chain hash
  `df0b67d97d738a3db61a248cce5d544a68dcdb60003c3bb7b263f9643f4ad37f`.
- Canonical tape directories: 30; partial files: 0; quarantined artifacts: 0.

Measured request-rate diagnostics, averaged across the ten topology-seed
tapes at each load, are 1,916.00 req/s for low, 2,511.40 req/s for middle,
and 6,863.40 req/s for high. Their observed ranges are respectively
1,890--1,933, 2,440--2,562, and 6,781--6,936 req/s. These measurements do not
change the frozen workload labels or select seeds.

## 3. Reference closure

All 90 candidate-specific reference builds completed and canonicalized on
attempt 1. Each of C0 `ready_order`, C1 `ready_warm_init`, and C2
`ready_finish_init` has 30 references sharing the appropriate frozen tape.
The exact-copy verifier and reference binder accepted every artifact.

- Reference catalog: `g2.reference.catalog.json`.
- Reference-catalog document hash embedded in the ready manifest:
  `9a469d74b23eecc9aa2f5f7efaef4bdce7a5e16903cec98a94065c850270a904`.
- Reference-catalog file SHA-256:
  `9c0ccffd3a07f3a8d18126061081ba4c0d8d1a3bffcfc326e2d02ea66e13f4c8`.
- Reference ledger: 90 events; final chain hash
  `73e16974c61e6fae2ed21e867640c230d610172c23bed87f04c8be03ec378625`.
- Canonical reference directories: 90; partial files: 0; quarantined
  artifacts: 0.
- Reference state rows: 87,770 total, comprising 87,712 positive and 58
  negative values, with zero exactly-zero or unknown values.
- Completed requests per reference build range from 1 to 3,214; no reference
  build has zero completions.

All observations, including the 58 negative reference values, are retained
under the frozen nonpositive-reference fallback. No validity decision used a
candidate's throughput or QPR.

## 4. Binding chain and ready manifest

The binding sequence produced and preserved the following intermediate
manifests:

- tape-bound file SHA-256:
  `a9c5725ccaf89dc0d20505cca0a72b00bd0098c548391fad50167003321d611e`;
  embedded document hash
  `9f2e7790f775ea5dbfe5e6538de7df569ebfd2f6c23f9fc3a5287e4870c44911`;
- tape/model-bound file SHA-256:
  `c2be6ca2b363e2accc06fa03853919327d249e8cdc5c83e848ff6155c00792da`;
  embedded document hash
  `c6d811bbbb8110a43eceef915bc540d7cbe3f7e0ce317dea8d28476e250b6ff7`.

The FaaSRank rows bind the independent frozen model whose artifact SHA-256 is
`4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`.

Final ready manifest: `g2.initialization.ready.json`.

- Manifest document hash:
  `8173ab619744d7794106489c67e5ef017160c90e5bdcc4dd597be075f9bcd3f4`.
- Manifest file SHA-256:
  `d49bc3865244f9b231b7dba312819f4c715059ca4ce7d7bb97b185add7481f18`.
- Validated product: 135 runs, 27 method/cell combinations, and 90 reference
  dependencies.
- `all_tapes_bound=true`, `all_faasrank_models_bound=true`, and
  `all_references_bound=true`.
- `all_sla_targets_bound=false` is expected for this G2 development screen:
  it has no offline-SLA target product and its frozen decision metrics are
  throughput and QPR. It is not an incomplete dependency for these 135 runs.
- Independent CLI validation returned `status=valid` for the final manifest.

## 5. Authorization and fail-closed rule

The complete 135-run online development product is now authorized. It consists
of 90 candidate runs over all six topology/load cells plus 45 nine-baseline
controls in homogeneous-low. Execution may be staged for operational safety,
but every row must retain its ready-manifest identity and all 135 canonical
QC-valid rows are required before selection.

Analysis remains fail-closed. The global six-cell maximin rule must first
select a candidate. That winner must then strictly exceed every one of the nine
paired homogeneous-low baselines in both mean throughput and mean QPR. Failure
of either condition prohibits creation of a new formal seed bank. Development
rows cannot be reported as paper evidence, and no measured result may justify
seed deletion, replacement, or result-conditioned rerun.
