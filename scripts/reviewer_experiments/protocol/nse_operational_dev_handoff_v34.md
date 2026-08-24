# NSESche operational development handoff V34

V34 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E81--E85 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `f42b928e7d6dd9f956b926964178b64475c22a43`
- plan SHA-256: `926270dac95157d46456fe59d08931c486c302ed334f9fe194ea041a823353c1`
- scheduler code commit: `aff77eb32d825d8f9e7b82db1bf9db540717af63`
- scheduler source SHA-256: `6fd81acfd33847ae0398d1ab84306f82fad5035f54d887095a07088fe2afb90b`
- release binary SHA-256: `cdb7504876cac07c32e7479ff308960ca23830a5a5ede2e17725c9846ced5c83`
- result: `tmp/nse_operational_dev_20260824_v34/candidate-screen.v34-orion-semantics.json`
- result SHA-256: `463a13579408d1a6b535032c57dbda4f403f4a90c4876f8ac21a6cd0dac654c9`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 20 paired environment groups passed. Online and
reference quarantine counts were zero, execution was strictly serial, and
`serverless_sim/records` remained empty.

## Revealed result

LoadLeast led E81--E85 baseline mean fixed-window throughput at `1.5902`.
Orion led baseline mean per-run QPR at `0.1158103190`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V34a load-faithful Orion | 1.5254 | 8 | 0.1086106533 | 5 | no |
| V34b equal FaaSRank--Orion Borda | 1.5170 | 9 | 0.1153493871 | 3 | no |
| V34c 2:1 FaaSRank--Orion Borda | 1.5486 | 5 | 0.1169467991 | 1 | no |

The corrected pending-plus-running Orion load semantics and its two fixed
FaaSRank consensus rules are closed without subdivision. V34c establishes the
best QPR in this cohort but does not pass the throughput gate, so it is not
selected. Frozen V8 remains the middle/high rollback winner and V11 remains
the best low-load rollback point. E81--E85 must not be reused for candidate
selection.
