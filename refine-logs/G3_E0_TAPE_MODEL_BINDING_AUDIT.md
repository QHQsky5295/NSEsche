# G3 operational E0 tape and model binding audit

Date: 2026-09-03  
Status: complete; reference construction is the next authorized atomic stage

## 1. Scope and result blindness

This audit covers only the complete D71--D75 base-tape capture, immutable tape
binding, and reuse of the already frozen FaaSRank-P model for the preregistered
G3 operational E0 development bank. No candidate throughput, QPR, latency,
cost, completion, Nash timing, or selection result existed or was inspected.
All 135 online runs remain blocked.

The sole authorized root remains:

`runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903`

The earlier `..._9c8789f_20260903` root remains superseded and prohibited.

## 2. Complete base-tape capture

The frozen release executable captured all 30 declared catalog keys on the
first capture pass. The immutable catalog contains exactly:

- five seeds: D71--D75;
- three load strata: low, middle, and high, ten keys each;
- two topologies: homogeneous and heterogeneous, fifteen keys each;
- 30 distinct canonical paths and 30 distinct provenance receipts;
- only `base_steady` tapes, each with a positive event count;
- event-count / measured-arrival-rate range: 1,896--7,101 requests/s;
- 30 canonical directories, zero failed directories, and zero quarantine
  directories.

The 30 topology-specific keys intentionally reduce to 15 unique event-stream
hashes: for each `(load, seed)` pair, homogeneous and heterogeneous use the
same arrival tape while the topology is supplied by the separately hash-bound
environment inputs. Every tape hash occurs exactly twice and only in its
matching topology pair; no unexpected duplicate was found.

Catalog evidence:

- schema: `NSE_TAPE_CATALOG_V2`;
- catalog document hash:
  `890bac97b5e19cb2644404be03c8c17f610a5217603a8465fc2b52c991a027fb`;
- catalog file SHA-256:
  `95b638e09d91444f6a78d6a09437a833dbd87449362639d1b168573422d675a4`;
- catalog bytes: 176,925.

## 3. Fail-closed tape binding

The protocol binder accepted the catalog only after checking exact key-set
equality with the frozen manifest and re-reading every tape from disk. Its
checks cover content hash, tape version, seed, event count, DAG order, frame
bounds, positive measured rate, workload-profile equality, Azure-derived CDF
provenance, environment semantic hashes, and receipt existence/hash/content.

The generated tape-bound manifest contains all 135 preregistered runs:

- path: `g3_e0.tapes.json`;
- document `manifest_hash`:
  `025755fca9f0af242000f3c783fdf92f2268f4fa6c40d371f99925412a3d7210`;
- file SHA-256:
  `f6d5922090fc37419d252d6f8897844f144a03186eab0cdcb3bfe2c7db0d0182`;
- bytes: 2,904,913;
- `all_tapes_bound=true`.

The original zero-data manifest is retained unchanged with file SHA-256
`a277e13086590109daed6022c0bc66591615b813e44c0ec39b0b8d60ad2a1d21`.

## 4. Frozen FaaSRank-P model binding

The same independently calibrated model already used by G1 was bound without
refitting:

- source artifact:
  `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/faasrank.frozen.json`;
- model file SHA-256:
  `4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`;
- calibration training-tape SHA-256:
  `28a48254c9a8589d708c305dc6c1a89be2714f8ab3df307058637c5f142325b9`;
- evaluation seeds: D71--D75;
- the training-tape hash is absent from all G3 evaluation-tape hashes.

The binder's disjointness check passed and produced:

- path: `g3_e0.model.json`;
- document `manifest_hash`:
  `333a43942ccd6682f4cb08cf758d6bd3facdd1daa811b1786f01c63229589318`;
- file SHA-256:
  `e0a2ec45ea57b8b94aed63e0f3c44fa3e0406e158b44a490062511d452cd3bd1`;
- bytes: 3,021,837;
- `all_faasrank_models_bound=true`.

This G3 manifest has no balanced-QoS runs, so no SLA-target artifact is
required or permitted for this stage.

## 5. Next gate

Exactly the 90 reference dependencies already frozen in `g3_e0.model.json`
may now be constructed as one complete stage. All 90 must validate and bind
before any of the 135 online runs begins. Candidate/result inspection,
selection, extension, formal homogeneous-middle execution, and paper-ready
claims remain blocked.

