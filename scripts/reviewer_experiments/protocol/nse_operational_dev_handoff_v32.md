# NSESche operational development handoff V32

V32 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E71--E75 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `aa792fb5cb07f8c7e78ccdac9b734da69c9866b1`
- plan SHA-256: `254f478552451d48cb502a77c6bee2f9c7d33fdfd096d4bae835676029006ba8`
- scheduler code commit: `1eeee6e513a5b55529a4fd37a543c6b3364e4c02`
- scheduler source SHA-256: `46f089b85809d38f6e7120b181e4ce4614a93411b35a6c1768923ef6bd8aa58d`
- release binary SHA-256: `b8c445e231f3b675adfcb5ce62ba5353a394d16c5d73bb8b68dc064962c7cf12`
- result: `tmp/nse_operational_dev_20260824_v32/candidate-screen.v32-hiku-preserving-experts.json`
- result SHA-256: `757aea6bd020f1a92b6f0b32bd6372b2866bf543549be5d70ab8ad99bb547ad4`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 20 paired environment groups passed. Online and
reference quarantine counts were zero, execution was strictly serial, and
`serverless_sim/records` remained empty.

## Revealed result

Jiagu led both E71--E75 baseline metrics: mean fixed-window throughput `1.7206`
and mean per-run QPR `0.0554326797`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V32a Hiku load-faithful | 1.6704 | 4 | 0.0513161467 | 4 | no |
| V32b Hiku + FaaSRank exact-tie | 1.6232 | 9 | 0.0508358623 | 5 | no |
| V32c Hiku + Jiagu exact-tie | 1.6746 | 3 | 0.0506232113 | 6 | no |

The Hiku-primary exact-tie family is closed without subdivision. FaaSRank and
Jiagu final tie-breaking did not reproduce the Jiagu baseline's joint lead.
Frozen V8 remains the middle/high rollback winner and V11 remains the best
low-load rollback point. E71--E75 must not be reused for candidate selection.
