# P2 Low-Load Hyperparameter Recovery Protocol and Manifest Audit

Date: 2026-09-05 (Asia/Shanghai)

Implementation commit: `fab5df83b8040c9e4a875b1581d46aed84ae4aa7`

Status: `zero_result_protocol_frozen_tape_capture_authorized`

## 1. Frozen implementation

The dedicated protocol constructs only the preregistered homogeneous-20 low-
load product: five fixed settings by D121--D125 under `ready_order`, in seed-
major then setting-ordinal order. The analyzer binds the complete population,
same-seed tapes, parameter-specific references, runtime/config identities,
all eight neighbour gates, and deterministic one-shot selection before any
online outcome exists.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `protocol/p2_low_hyperparameter_recovery.py` | 10,049 | `e92f9ac9b82ee798d4832179d112b40d20c84639bb3a5116d31f525d3fb046c4` |
| `analysis/p2_low_hyperparameter_recovery.py` | 35,201 | `cd67e563e1c64a7195d0c0f5c3061f11eb57fedb9297c4131e24758fee626d5f` |
| `protocol/schema.py` | 280,481 | `9609fe81251df50236de04c0ce21acb27cc03186bf25c30bd9d65ae893852b93` |
| `protocol/manifest.schema.json` | 43,700 | `a7aab7173f05401f600af5f0cb79d84ef0a76fbe17543eb7afb395cab5d8d595` |

The runtime is reused without rebuild from the protected G18 release target:

- source commit: `f3a1e0950c5a53a0ab614edacc2838703c2a9d81`;
- binary bytes: 4,918,272; and
- binary SHA-256:
  `aaa0980cf451a88f7b3652f55c3e8c624af2a71b6312c40f4b19aa83bf6af713`.

A read-only retained-log check confirms this binary emits both `r0` and
`quality_weight` in its `run_config` record. Float32 representation is checked
with the already frozen `1e-6` relative/`1e-8` absolute runtime tolerance.

## 2. Test evidence

- P2 protocol plus P2 analyzer directed tests: 13/13 pass;
- P2 plus adjacent G18 protocol tests: 16/16 pass;
- complete protocol suite: 267/267 pass in 774.301 s;
- complete analysis suite: 202/202 pass in 83.574 s;
- Python compilation and Black formatting pass; and
- `git diff --check` reports no whitespace error.

The directed cases prove exact product/order, exact parameter/runtime binding,
one shared tape and five distinct references per seed, frozen gates, mutation
rejection, immutable write behavior, conjunctive viability, per-seed floor,
runtime fail-closed behavior, deterministic label tie-break, and rejection of
incomplete or duplicate populations.

## 3. Zero-result manifest

Path:
`runs/tscv1_p2_low_hyperparameter_recovery_d121_d125_f3a1e09_20260905/p2-low.manifest.json`

- bytes: 585,684;
- file SHA-256:
  `2a34025eb9a6a412cc76d9560f9df9906d00fc812553871d59eed57b625b1bc7`;
- canonical manifest object hash:
  `e4503c5d0ef91062ae701f3e35901474ac9598bcf9b0cdf835e120bdd92b683c`;
- 25 unique run IDs and 25 unique run-spec hashes;
- five unique workload-tape keys, one shared by all five settings per seed;
- 25 unique parameter-specific reference keys;
- all tape and reference SHA-256 fields remain null;
- generic manifest validation, dedicated P2 validation, and static JSON Schema
  validation pass; and
- `capture_base_tapes`, `reference_builds`, and `online` did not exist at the
  freeze check.

Thus the manifest contains no metric, outcome, tape, reference, candidate
selection, baseline result, or paper-eligible row.

## 4. Authorization boundary

After this audit is committed, exactly five D121--D125 homogeneous-low base
tapes may be captured in fixed seed order. Tape capture is input generation,
not candidate execution. No parameter setting may execute during capture.

Offline-reference construction, online execution, analysis, formal Q81--Q100,
E7 figures, baseline runs, and manuscript claims remain blocked. A complete
tape-input binding audit must independently unlock the 25 reference builds.

