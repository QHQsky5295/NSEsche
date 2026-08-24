# NSESche operational development handoff V38

V38 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E100--E104 cohort; E11--E20 remain sealed.

## Provenance and gates

- three-digit development seed grammar commit: `d7b3da2`
- scheduler code commit: `b9f0a69304a46cfe56f71405b0b686c308a2be8d`
- plan commit: `757d03a6480a76f43bd941c79f0379c949c70615`
- plan SHA-256: `f2909f33e6ee473581b2fdade0957dc1a00c67375669e7ac1eb27939c8b4144e`
- scheduler source SHA-256: `a5fda46420418e1780d791390db6be060fc1ed9376cae1b1034e7d48573d80d7`
- scheduler source blob: `aeedf2bd24637b797580251a30720d23d8d2190d`
- release binary SHA-256: `e67524a52b6a1f4abf505e15a1502383550356a890014969d8ff725e6db52b92`
- result: `tmp/nse_operational_dev_20260824_v38/candidate-screen.v38-greedy-ocs.json`
- result SHA-256: `8c1ceaa4df934827034bbfdae5b7a5b94baec5ba2fc882aad683945a10aebe3b`

The generic seed grammar was extended to E plus two or three digits before the
plan was committed. Exact formal-shard validators remain fixed to E01--E20, so
E100--E104 cannot enter formal results.

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 60 online runs passed QC and pairing; capture,
online, and reference quarantine counts were zero. Execution was strictly
serial, `serverless_sim/records` remained empty, and all 60 runs shared one Git,
binary, Python, and Cargo.lock identity. No canonical-name repair was required.

## Revealed result

LoadLeast led E100--E104 baseline mean fixed-window throughput at `1.8170`.
OCS led baseline mean per-run QPR at `0.1099125777`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V38a hybrid3 + Greedy | 1.8132 | 2 | 0.1002994117 | 3 | no |
| V38b hybrid3 + OCS | 1.8034 | 4 | 0.0948085432 | 5 | no |
| V38c hybrid3 + Greedy + OCS | 1.7990 | 5 | 0.0880310405 | 7 | no |

No candidate strictly beat every baseline on either mean metric. V38a missed
the throughput leader by `0.0038` but remained third in QPR. Adding OCS alone
or jointly did not improve the combined rank, so the Greedy/OCS hybrid-majority
family is closed without subdivision. Frozen V8 remains the middle/high
rollback winner and V11 remains the best low-load rollback point. E100--E104
must not be reused for candidate selection; E105--E109 remain unobserved and
available only to a separately preregistered cohort.
