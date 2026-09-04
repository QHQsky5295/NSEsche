# G9 Request-Level Backpressure Tape Capture and Input-Binding Audit

Date: 2026-09-04 (Asia/Shanghai)

Parent freeze commit: `c521e4e42a466e22ef79b2ba63b78a593f786bd6`

Status: `tapes_and_faasrank_model_bound_reference_build_authorized_after_commit`

## 1. Result-blind stage completed

The exact 15 base tapes declared before sampling were captured in sorted tape-
key order. Every tape canonicalized on attempt 1. There is no quarantine
directory and no partial attempt remains. These capture runs used the random
scheduler to materialize arrival events and environment/provenance receipts;
they did not run or compare G9, its NSESche control, or the three performance
baselines.

The canonical capture tree contains 210 files and 59,140,916 bytes. Its
inventory object hash is
`f382b03efc83465bf40f3db3cb793d4f526d72fd7a4ba8e32655a1c0431942e0`.
The append-only capture ledger has SHA-256
`8bff3b3c4c56b5847c3416de30f83a42bd74694c594029e929c4caeeaf17aea8`.

| Load | Tapes | Minimum events | Maximum events | Total events |
|---|---:|---:|---:|---:|
| low | 5 | 1,897 | 1,960 | 9,624 |
| middle | 5 | 2,448 | 2,585 | 12,553 |
| high | 5 | 6,811 | 7,038 | 34,608 |
| total | 15 | 1,897 | 7,038 | 56,785 |

All 15 tape files were independently streamed through `inspect_tape`; their
observed hashes and event counts equal the catalog entries.

## 2. Binding receipts

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `g9.tape.catalog.json` | 88,720 | `8bc13cb6af19122a8afbfbb35937c76ff1fa7cefb86f531e701b62e4c587929f` | `dea1e014915b9211cbe2a6aaf9c1b4c79f66ffa4d07d5ece517853fd0920c1fd` |
| `g9.tapes.json` | 1,410,219 | `427316febe895a47940263d48c13a45557deb8d08b1dea33023d864141349da9` | `b30def83f6f00b15c46c0ec0501a485270459c40064d6c433fd213fb40eeefef` |
| `g9.model.json` | 1,760,993 | `b21f0eb74cb8dc75802c9a45a6441df54870d3b1ae950124ae885e842f16c948` | `cbc15c41d5fa3586ec0fe7e64bbc453b20138981e4bba228bc575aa9adff604a` |

The final input-bound manifest has 75 runs, 15 distinct tape hashes, and 30
reference dependencies. `all_tapes_bound=true` and
`all_faasrank_models_bound=true`. Every one of the 15 FaaSRank runs binds the
same previously calibrated artifact SHA-256
`4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`.
Its independent training tape SHA-256 is
`28a48254c9a8589d708c305dc6c1a89be2714f8ab3df307058637c5f142325b9`,
which differs from all 15 evaluation tape hashes. No new model selection or
calibration was performed. G9 uses mixed non-QoS traffic, so SLA binding is not
applicable and `all_sla_targets_bound=false` is correct.

## 3. Pre-outcome schema correction

The first attempt to advance from the unbound to the model-bound manifest
identified a fail-closed implementation error in the G9-specific validator:
it required `all_faasrank_models_bound=false` at every stage. That condition
correctly described the zero-result manifest but made the already authorized
immutable model-binding stage unreachable. No online G9/control/baseline run
or offline-reference build existed when this was detected.

The correction changes only that stage flag from the constant `false` to a
Boolean. The generic schema remains authoritative: a `true` value is accepted
only when every FaaSRank run has a complete frozen binding and matching Rust
payload; an incomplete binding fails closed. The G9 method set, seed bank,
loads, tapes, runtime, equations, candidate, reference identities, and all ten
development gates are unchanged. Because all G9 runs use mixed non-QoS
traffic, the G9-specific validator continues to require
`all_sla_targets_bound=false`.

Corrected source receipts:

| File | Bytes | SHA-256 |
|---|---:|---|
| `scripts/reviewer_experiments/protocol/schema.py` | 212,598 | `c186b5341dac224037e04cd7f98296ef58eaf2e056d746eb990ef46095f3ec35` |
| `scripts/reviewer_experiments/protocol/tests/test_g9_request_backpressure.py` | 7,165 | `635ce8dd6babf8c607cc5beee85ecbb4ffa5fa9f8207272dd9ee5ff5157c7593` |

Black formatting and `git diff --check` pass. The corrected G9 directed suite
passes 6/6, including explicit rejection of a `true` flag with unbound model
records and acceptance only after complete frozen bindings are present. The
actual `g9.model.json` independently passes the complete manifest validator.

## 4. Authorization boundary

After this audit, corrected schema, tape catalog, and two bound manifests are
committed, only the exact 30 declared offline-reference builds are authorized.
They must use the already frozen G9 release runtime, the 15 tapes above, and
the two preregistered NSESche identities. Online execution, outcome analysis,
D86--D95 confirmation, formal Q61--Q80 replay, figures, and paper performance
claims remain blocked until a separate 30/30 reference audit is committed.
