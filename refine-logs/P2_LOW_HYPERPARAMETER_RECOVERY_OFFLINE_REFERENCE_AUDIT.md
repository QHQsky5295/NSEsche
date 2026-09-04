# P2 Low-Load Hyperparameter Recovery Offline-Reference Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent tape-input commit: `82a08aeefa67af1c597748a9aab613773b168379`

Status: `all_25_references_bound_result_blind_selection_freeze_authorized_after_commit`

## 1. Complete retained build population

All 25 parameter-specific offline social-utility references canonicalized on
attempt 1 using the protected binary, the five bound D121--D125 tapes, and the
exact centre/four-neighbour configurations. There was no retry, parameter or
seed replacement, quarantine, omission, or online execution.

Independent inspection reopened every JSONL table and revalidated its file
hash, unique state keys, initial-assignment hashes, line count, state-pair
sequence, receipt, assignment sequence, build specification, workload-tape
hash, run configuration, process observation, exit code, timeout state, and
parameter/`ready_order` identity.

| Setting | Tables | Rows | Positive | Negative | Null/zero |
|---|---:|---:|---:|---:|---:|
| centre | 5 | 4,870 | 4,870 | 0 | 0 |
| r0_minus | 5 | 4,870 | 4,870 | 0 | 0 |
| r0_plus | 5 | 4,870 | 4,870 | 0 | 0 |
| wq_minus | 5 | 4,869 | 4,869 | 0 | 0 |
| wq_plus | 5 | 4,866 | 4,864 | 2 | 0 |
| **Total** | **25** | **24,345** | **24,343** | **2** | **0** |

The two finite negative rows are retained in `wq_plus` D123:

- state `0xf4a653221c6cc43c`: -156.86009216308594; and
- state `0x94af4b4e5e898972`: -212.30160522460938.

Both rows carry the explicit `negative` status. They are not treated as a
technical failure and are not removed or rebuilt. The preregistered runtime
condition requires every reference actually loaded by an online active window
to be positive. Therefore `wq_plus` will fail that condition if its online
D123 trajectory reaches either retained state. This cannot affect the runtime
condition of the other three neighbours, which have distinct reference tables
and are evaluated separately against the centre.

## 2. Evidence receipts

The 350-file canonical reference tree contains 247,587,698 bytes and has
path-independent inventory hash
`747444aa5c761f8546334f20b3944c1eb7d5dd4a427480cb6b1fb9e60c032d85`.
The append-only build ledger contains exactly 25 valid chained events. Its tip
is `f9369a3264deb1738f1a873965b4c7f0d7fd43228671ec67e2a2abc6a1423ec6`;
the 24,555-byte file has SHA-256
`09c71c9b00f46f86dea19dcc93c6dcedd5182a6e48cc51174378866250b52a95`.

| Artifact | Bytes | File SHA-256 | Canonical object hash |
|---|---:|---|---|
| `p2-low.reference.catalog.json` | 47,940 | `a057a873e166236fab18944f226b1ff2ba910c5a0abf26b06a44ff45f4fd9efa` | `b20b512ebafa5a277b7444c6c9fbd75820eb759572953b32c6bba459981e862b` |
| `p2-low.ready.json` | 680,965 | `544d884bdb4d990115213ef13fce19de24ab20f899588e5666e96de375823568` | `8e89bca4604f17ef9dc28e2e09887b6070fed971e6a560903c00cf7281320758` |

The ready manifest passes generic, dedicated P2, static JSON Schema, and
disk-reopen validation. It binds five distinct tape hashes, 25 distinct table
hashes, the one protected runtime, and all 25 final run specifications.
`online` and `p2-low.online.selection.json` did not exist at audit time.

## 3. Scientific status and authorization

No throughput, latency, cost, completion, QPR, paired effect, gate decision,
or parameter selection exists. Reference signs cannot change the fixed online
population. All five settings and all five seeds remain required.

After this audit is committed, the frozen result-blind analyzer may be invoked
only to create the exact 25-row online selection while the canonical online
root is absent. The selection must preserve seed-major/setting-minor order and
embed the analyzer, manifest, binary, tape, and reference hashes.

Online execution remains blocked until that selection and its audit are
committed. Formal Q81--Q100, baselines, E7 figures, and manuscript claims
remain blocked until a neighbour passes all eight frozen conditions.

