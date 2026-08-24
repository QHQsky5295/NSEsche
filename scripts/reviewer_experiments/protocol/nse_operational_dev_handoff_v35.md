# NSESche operational development handoff V35

V35 is closed without a selected candidate. It used only the preregistered,
permanently non-formal E86--E90 cohort; E11--E20 remain sealed.

## Provenance and gates

- plan commit: `dd44286`
- plan SHA-256: `93b404e659ed6e39122c0235bc01dd03e32eb3b630c9ff8c97575c3914148969`
- scheduler code commit: `0a76200ab94c1e9b64c29b8b5e232bf84da68c63`
- scheduler source SHA-256: `9d0648a032531840da373bd40692ee10db569f601af906c9cb07b47c60a7b88f`
- release binary SHA-256: `6e72a41888342a0508f867c0b48ab27a75b79413d91fa9b02df291fc22baa700`
- result: `tmp/nse_operational_dev_20260824_v35/candidate-screen.v35-loadleast-consensus.json`
- result SHA-256: `373be2aff1454a882d7581c47975bb2e3870b52da5d85de17c5cee1fc344852b`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. The tape, three reference, and four online
ledger hash chains passed. All 20 paired environment groups passed. Online and
reference quarantine counts were zero, execution was strictly serial, and
`serverless_sim/records` remained empty.

## Revealed result

Orion led E86--E90 baseline mean fixed-window throughput at `1.5110`.
FaaSRank led baseline mean per-run QPR at `0.0695578618`.

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V35a equal FaaSRank--Orion--LoadLeast | 1.4986 | 2 | 0.0483800764 | 8 | no |
| V35b 2:1:1 FaaSRank--Orion--LoadLeast | 1.4634 | 5 | 0.0491849009 | 6 | no |
| V35c 2:1:2 FaaSRank--Orion--LoadLeast | 1.4872 | 4 | 0.0485271870 | 7 | no |

Adding the exact LoadLeast rank to the V34 FaaSRank--Orion consensus did not
preserve the prior QPR advantage. The fixed 1:1:1, 2:1:1, and 2:1:2 integer
vote family is closed without subdivision. Frozen V8 remains the middle/high
rollback winner and V11 remains the best low-load rollback point. E86--E90
must not be reused for candidate selection.
