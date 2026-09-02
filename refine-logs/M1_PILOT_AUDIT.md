# M1 Workload and SLA Pilot Audit

## Status

`M1-PILOT` is complete. This phase is non-formal calibration evidence only;
none of its observations may enter manuscript estimates, confidence intervals,
significance tests, or figures. No main-paper comparison group is closed by
this milestone.

## Runtime identity

- Low-load capture and SLA-run commit:
  `ec2c55a30da5c6ea469847ba8ebba7e647ebf9fc`.
- Middle/high capture commit:
  `2b287f79f0a29d17f183c26be43cf7522cec9b2f`.
- Three-seed SLA freezer commit: `2b287f79f0a29d17f183c26be43cf7522cec9b2f`.
- Release binary SHA-256:
  `1647ea8614d70deddc86abb7e01890daf6ab92bea047c56f99299ec785ff9c44`.
- Python executable: `D:\Anaconda3\python.exe`.
- Python executable SHA-256:
  `a1685ca0f56367b7ca3e8bf1bcbdd3a326f5e8e20c8743bf3108586f0aaff384`.
- Every pilot manifest is marked `formal_results_eligible: false`.

## Workload-rate calibration

All rates are measured arrivals in a 1000 ms arrival horizon. E01--E03 are
fixed before inspection; per-seed DAG and tape hashes differ, while every
method in a later paired cell must reuse the same bound tape hash.

| Load | E01 | E02 | E03 | Mean | Frozen interpretation |
|---|---:|---:|---:|---:|---|
| low | 1920 | 1907 | 1949 | 1925.33 | approximately 1.9k requests/s |
| middle | 2572 | 2560 | 2546 | 2559.33 | approximately 2.6k requests/s |
| high | 7084 | 7238 | 7086 | 7136.00 | approximately 7.0k requests/s |

Primary bindings:

- low tape catalog:
  `runs/tscv1_m1_pilot_ec2c55a_20260902/pilot-tapes.catalog.json`, SHA-256
  `af130444f105e31c96d45af419496a54b4305353be0f5fbd1584fef9826bcf12`;
- low tape-bound pilot manifest:
  `runs/tscv1_m1_pilot_ec2c55a_20260902/manifest.pilot3.tapes.json`, SHA-256
  `51b34b0d8226cdff06ec9e532dadad5b846f6bc480bcc4880c0acb42106e5682`;
- middle/high tape catalog:
  `runs/tscv1_m1_pilot_ec2c55a_20260902/middle-high-tapes.catalog.json`,
  SHA-256
  `4282b2b4af23118c15e3694fbbfbc78ee77f4ebfd12d648391e9c76e893772aa`;
- middle/high tape-bound pilot manifest:
  `runs/tscv1_m1_pilot_ec2c55a_20260902/manifest.pilot-middle-high.tapes.json`,
  SHA-256
  `6cb101365cfd2a0fa5c411b06d58f73bef3e7fd6aeb02096436646e29980f0e7`.

The revised manuscript must report these actual operating rates. The original
PDF's broad textual 1--5k/5--15k/15--70k ranges are not retained as measured
rates. Per-figure old-bar alignment remains a gate of each later formal figure;
this workload pilot does not substitute for `old_pdf_alignment.csv`.

## Offline-reference integration pilot

The real E01 low-load NSESche reference path completed capture, build, hash
binding, replay, and QC. It is pipeline evidence only and remains explicitly
ineligible for formal analysis.

- reference key:
  `nse-reference.E1.sche_nash.low.homogeneous.n20.E01.7b6e309ebcdb2911`;
- table SHA-256:
  `5b2221e97b7310e1cca253e8e7e49923c4a428a5ccb1d7ef723d228b85456b53`;
- table rows: 970;
- reference build completed requests: 1877;
- build/replay assignment sequence SHA-256:
  `daa423352fc2c3b5daf0fba34f92ef0e605bc09cfbe4b5121691766f7faebc73`;
- build receipt SHA-256:
  `7eaa571e7a99d21d0a4b263536fb740b438f80d8a0bf9b2103c2da300cbe774d`;
- reference catalog SHA-256:
  `c8eb6dbb68f75a0642f2c415107f7f37a043bb3f793e1b40deb5b1aa85977e67`;
- ready smoke manifest SHA-256:
  `600de384b94bf6c6280b593eaf6f87c091f331f6ba666d5d0c756627486ad6a5`.

The same paired smoke tape yielded 1760 requests/s for Greedy and 1877
requests/s for NSESche. Those values are useful only as an integration and
submission-scale sanity check; two observations cannot close a comparison.
The smoke also exposed that simulator startup reordered a tracked module
inventory file. Commit `ec2c55a` now preserves and atomically restores its
exact pre-run bytes, and a real NSESche regression verified identical before
and after hashes.

## SLA capacity bracket

The initial E01 grid at 1920/3840/5760/7680 requests/s was executed completely
before inspection. Its latency and cost class pilots both completed only
94.11% of requests at factor 1, so the immutable default workspace failed as
required. The acceptance threshold was not relaxed.

A new divisor-4 nested grid was then fixed for all three seeds. Candidate `k`
retains a deterministic nested `k/4` subset of the parent tape; candidate 4 is
the complete parent tape.

| Seed | Sustainable candidates | First failing candidate | Selected rate |
|---|---|---|---:|
| E01 | 480 (completion 1.000, final state zero) | 960 (completion 0.9844) | 480 |
| E02 | 477 (completion 1.000, final state zero) | 954 (completion 0.9864) | 477 |
| E03 | 488, 975 (completion 1.000, final state zero) | 1462 (completion 0.9535) | 975 |

Each passing point also has zero admission drop, rejection, timeout, final
queue, final active requests, and final tasks. The three seed-level source
measurements are:

| Seed | latency p95 (ms) | sustainable throughput (requests/s) | cost/request |
|---|---:|---:|---:|
| E01 | 222 | 480 | 1.1931596120198569 |
| E02 | 289 | 477 | 3.2414041515166403 |
| E03 | 236 | 975 | 1.6155377997726690 |

The frozen aggregation is a conservative, fixed three-seed envelope followed
by the preregistered multipliers: maximum latency times 1.5, minimum sustainable
throughput times 0.9, and maximum cost times 1.25. No rounding is applied.

| Frozen target | Value |
|---|---:|
| latency deadline | 433.5 ms |
| throughput target | 429.3 requests/s |
| cost budget | 4.0517551893958 simulator-internal units/request |

Frozen artifact:

- path:
  `runs/tscv1_m1_pilot_ec2c55a_20260902/frozen-sla-three-seed.json`;
- file SHA-256:
  `496f70535daeb121c100b2823821679a83a52fd382718c1782cc0c1a036cf3f2`;
- self-document SHA-256:
  `efc1649d98b96e317182d0b3f085ff587e257dbfbfc6b3402d59c476d4362bb3`;
- targets SHA-256:
  `0224d3737301bd0eb3612a17c775fbf4ec9b853a732a1f5030ad2b6d3b7c77e7`.

The seed reports are hash-bound as follows:

- E01: `686f4e50688ea9e5b741ba444e88b9ac06e79c0d070a8433347b82d8a56861b5`;
- E02: `00a01a4c863bdb50d9d2ca3cf590c80ffdf526883474e006abd5784cb326697d`;
- E03: `31ddbda20666a18e25e40152e7ed65a387c83c94c48c9b5b3cb7fe3cfaf5ea0f`.

## Storage disposition

Successful pilot tapes, source artifacts, reports, and the frozen SLA remain
under `runs/tscv1_m1_pilot_ec2c55a_20260902` because they are live inputs to
later manifest binding. Two diagnostic-only trees were moved byte-for-byte to
the recoverable E-drive archive after their hashes and conclusions were
recorded:

- default-bracket failure, 91,801,959 bytes:
  `E:\NSEsche_experiment_archives\m1_pilot_diagnostics_20260902\sla-pilots-E01-default-failed`;
- pre-commit integration smoke and old-PDF render diagnostics, 45,988,110
  bytes:
  `E:\NSEsche_experiment_archives\m1_pilot_diagnostics_20260902\precommit-integration-smoke`.

Both moves verified that the destination byte total matched the source before
the C-drive source path was considered released. The data remain recoverable.

## Gate decision and next paper block

The workload labels, paired-tape mechanism, and isolated three-seed SLA targets
are ready for later formal manifests. `M1-PILOT` is therefore complete.
`M1-QUAL` remains open: NSESche must next pass the frozen six-cell development
qualification for homogeneous/heterogeneous low, middle, and high loads before
the first paper comparison group (`M2-HOM-LOW`) may start.
