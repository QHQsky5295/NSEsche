# NSESche operational development handoff V36

V36 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E91--E95 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `587614c8722a7e2cec702ea0b30aea1e78b8ed54`
- plan SHA-256: `68348964724cc84ddbb6b4e00b73345802d3524b41cb526da47f81b91fd91432`
- scheduler code commit: `efacc6eac4e91271f0af9f47a1474f4936e9724c`
- scheduler source SHA-256: `98983d9e5ace9435f66d7ec24b2a0cd01020aed376b8081a17738f00c98ab93c`
- scheduler source blob: `91c8885429a694546d4195bb9e40483247284c01`
- release binary SHA-256: `eaef0b832bd45089212f204199a0fe9f4897ec6af6ec9ce1ea8bb1a01946908f`
- result: `tmp/nse_operational_dev_20260824_v36/candidate-screen.v36-hybrid-majority.json`
- result SHA-256: `9d317334214144e1e58d99cc22e3c44742a2d9709af203fb37fd4f213347252a`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 60 online runs passed QC and pairing; online and
reference quarantine counts were zero. Execution was strictly serial, and
`serverless_sim/records` remained empty.

One baseline canonical directory was externally named `attempt-01`. Its
embedded run identity, ledger event, QC, and 15-file content tree uniquely
identified Hiku/E92. It was repaired by same-parent atomic rename without
editing or rerunning content. The receipt is
`tmp/nse_operational_dev_20260824_v36/runs-baselines/canonical_rename_receipt_v36.json`
(SHA-256 `bbf6b3d80a6b1643b258b5a31e8afe81dcdff9427c74c92fc6454e00fc0906ad`).

## Revealed result

FaaSRank led E91--E95 baseline mean fixed-window throughput at `1.5128`.
Orion led baseline mean per-run QPR at `0.0703488357`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V36a hybrid3 FaaSRank | 1.4752 | 5 | 0.0735231160 | 3 | no |
| V36b hybrid3 Orion | 1.4932 | 3 | 0.0800453451 | 1 | no |
| V36c hybrid3 Jiagu | 1.5000 | 2 | 0.0769432170 | 2 | no |

All three hybrid-majority candidates beat every baseline on mean QPR, but none
strictly beat every baseline on throughput. V36b won QPR but ranked third on
throughput; V36c was the closest balanced result at rank two on both metrics.
The fixed three-hybrid-vote plus one minority-expert family is closed without
subdivision. Frozen V8 remains the middle/high rollback winner and V11 remains
the best low-load rollback point. E91--E95 must not be reused for candidate
selection.
