# NSESche paired operational confirmation handoff V57

The fresh E210--E219 same-tape confirmation is complete and did not close the
three-load objective. The unchanged V56/V41 frozen stack must not be reported
as a universal throughput-and-QPR winner. E210--E219 is a spent confirmation
cohort and must not be used for tuning, seed selection, deletion, or rerun.

## Provenance and result-blind gates

- preregistration/runtime commit: `58c60c4aab2b4e87761fdc2a9bf9c1144973ffcd`
- plan SHA-256: `a1f4096eeca8a1d7cbd65fb9f91c3a35547b76705f0c94744097fe61bca759d0`
- frozen scheduler binary SHA-256: `1aa42fb04e2ab4dc33dc405008a592b2d7be4aa32a41712e7219b339cd6f1d45`
- baseline ready manifest hash: `0da76b7e1aae258c28f2e7b85695a1f037d0e631174018b2881670b03ddacbfb`
- baseline ready file SHA-256: `333963468c88606e8d8c1db673e6c1d1ddb7c2b414e6c1ee6d0826b4a95ca38c`
- NSESche ready manifest hash: `b9669d20c464d2e07653c88be0e3240568de170774341b9151f9df8befca1cb8`
- NSESche ready file SHA-256: `8f87f23cdc542288128e708312d92986e5fcac04fb12ca9dcf806d2809229a0d`
- result-blind audit SHA-256: `8aca89028db252bed63d0a513bc263a429a943437f875d09a48de63cd354bde0`
- result-blind audit hash: `6415b559f14fb63668f3101e51bb274d4dbea916b9c0aa2091aa1f8e0ffd34e5`
- result: `tmp/nse_operational_confirmation_v57/paired-confirmation-result.v57-e210-e219.json`
- result SHA-256: `8a0639db9b4d7d156152764a9a4e2f3882389f49fe55b20edf04e0384d299d02`

Thirty fresh tapes and 30 state-matched NSESche references were prepared.
All 270 baseline runs and all 30 NSESche runs canonicalized on attempt 1 with
zero quarantine. The two online ledgers verify at 542 and 62 events. Before
any metric was read, the joint result-blind audit verified the exact 300-run
set, 30 complete load/seed groups, ten methods per group, common tape/HPA/
simulation/environment hashes, and one Git/binary/Python/Cargo.lock identity.

## Revealed E210--E219 result

| Load | NSESche throughput (rank) | NSESche finite QPR (rank) | NSESche zero-as-zero QPR (rank) | Strict gates |
|---|---:|---:|---:|---|
| low | 1.5572 (1) | 0.06734831 (5) | 0.06734831 (5) | throughput only |
| middle | 0.9747 (5) | 0.01603226 (7) | 0.01603226 (7) | none |
| high | 0.8552 (6) | 0.01555364 (6; n=9) | 0.01399828 (6) | none |

The leaders were Hiku for low QPR, OCS for middle throughput, Hiku for middle
QPR, and Orion for all three high-load metrics. NSESche passed one of nine
preregistered strict gates: low-load throughput. Therefore
`confirmation_closed=false`.

## Scientific boundary

V56's cross-cohort failure and V57's stronger paired failure are both retained.
No seed was deleted or replaced, no selective rerun occurred, and all 300
technical results remain immutable. A later optimization may use a new
preregistered development cohort and a general algorithmic rationale, but it
must not tune to E210--E219 or relabel this failed confirmation as a success.
V1--V57 remain rollback and audit points.
