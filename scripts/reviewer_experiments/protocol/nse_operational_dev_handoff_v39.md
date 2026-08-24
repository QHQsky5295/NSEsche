# NSESche operational development handoff V39

V39 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E105--E109 cohort; E11--E20 remain sealed.

## Provenance and gates

- scheduler code commit: `faf2614ffe1b2ac4a46ec9c62e8881c4bf8b33fa`
- plan commit: `59a6984a86039176aabc738feaff3a9d56afa733`
- plan SHA-256: `d37f4edaddc49f1f829eb6db04f910f058c3c8524bee215db9d20634bd323d3f`
- scheduler source SHA-256: `a0cae2b5e8db4af44a0b905250fe185157e56d2a7ecf459fe4284283a22070ab`
- scheduler source blob: `50970ec12f507fa255b3ceb953687599dd0d3498`
- release binary SHA-256: `3af21b79361b8d6ddd5886fb2f94bfc902f94233cb36de4acf7049611e13d7e4`
- result: `tmp/nse_operational_dev_20260824_v39/candidate-screen.v39-loadleast.json`
- result SHA-256: `d3d8a1cbe83b1b58448fb244b957402202cd38564f5c93148140bf17a832fcd8`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 60 online runs passed QC and pairing; capture,
online, and reference quarantine counts were zero. Execution was strictly
serial, `serverless_sim/records` remained empty, and all 60 runs shared one Git,
binary, Python, and Cargo.lock identity. No canonical-name repair was required.

## Revealed result

OCS led both E105--E109 baseline means: fixed-window throughput `1.5384` and
per-run QPR `0.0598675337`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V39a hybrid3 + LoadLeast | 1.5294 | 4 | 0.0519761570 | 6 | no |
| V39b hybrid3 + LoadLeast + Greedy | 1.4286 | 10 | 0.0485793245 | 9 | no |
| V39c hybrid3 + LoadLeast + OCS | 1.5548 | 1 | 0.0537141934 | 4 | no |

V39c is the first fresh-cohort low-load candidate to strictly beat every
baseline in mean throughput, by `0.0164` over OCS, but it did not pass the QPR
gate. The Greedy conjunction regressed sharply, so that branch is closed. The
V39 LoadLeast family is closed without subdivision on E105--E109. A later
cohort may preregister a discrete OCS-vote extension of frozen V39c, but may not
reuse these seeds. Frozen V8 remains the middle/high rollback winner and V11
remains the best low-load rollback point.
