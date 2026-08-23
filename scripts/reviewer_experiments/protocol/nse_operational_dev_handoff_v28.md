# NSESche V28 development closure

V28 is closed on the permanently non-formal E51-E55 cohort. All three
preregistered FaaSRank-majority ordinal ensembles completed, but none passed
the combined low-load gate. E11-E20 remain sealed.

## Frozen identities

- Plan: `nse_operational_dev_plan_v28.json`
- Plan SHA-256: `dde4606554c4bc411c248aa0e0aa42aaccd673812ef0c57e45616fc58f563e9f`
- Scheduler code commit: `0667c9db394a79c312fa35d525dde4396ac6b2e2`
- Scheduler source blob: `cc17f6fde33606d39b0c1e76700c069f5b98531e`
- Scheduler source SHA-256: `6e5ab183e5d2417d375e174cde78813f83ef6885572fdb317c89c934eb74cebe`
- Release binary SHA-256: `411c6e74b19721b78c6711951e5221a80208412a02fb521adcd8b82c57e8de48`
- Result: `tmp/nse_operational_dev_20260824_v28/candidate-screen.v28-faasrank-majority.json`
- Result SHA-256: `9b28798604e8de0fd419b83e9296d31a3ba8ee66e4bdb3bc097a11138b7f468a`
- Runtime Git commit recorded by all online runs: `ef846aae8f87adc8c5d070b5320ee81534fb8fdf`

## Protocol closure

- Fresh development seeds: E51-E55, low/homogeneous/n20 only.
- Tape capture: 5/5 first-attempt canonical, zero quarantine.
- Baselines: 45/45 first-attempt canonical and QC pass.
- Candidate references: 15/15 first-attempt canonical, zero quarantine.
- Candidate online runs: 15/15 first-attempt canonical and QC pass.
- Result-blind pairing: 60/60 online runs across all four manifests.
- Execution was strictly serial; `serverless_sim/records` remained empty.
- E21-E50 were not reused for selection; E04-E10 and E11-E20 were not read.
- E51-E55 are permanently closed to further tuning.
- E56-E60 were present only as unused reserve seeds in the full source. They
  were not captured, referenced, executed, or inspected.

## Result

The E51-E55 baseline leaders were Greedy in throughput (`1.4676`) and Hiku in
QPR (`0.0527669739258827`).

| Candidate | Throughput | Throughput rank | QPR | QPR rank | Decision |
|---|---:|---:|---:|---:|---|
| V28a: 2:1:1 FaaSRank/Jiagu/LoadLeast Borda | 1.4880 | 2 | 0.05107407098905216 | 4 | Throughput only |
| V28b: 2:1 FaaSRank/Jiagu Borda | 1.4978 | 1 | 0.047403078790204715 | 5 | Throughput only |
| V28c: 3:1:1 FaaSRank/Jiagu/LoadLeast Borda | 1.4400 | 5 | 0.045925087128221034 | 7 | Fails both gates |

No candidate strictly exceeded all nine baselines in both metrics. No
candidate is selected, and confirmation remains sealed.

## Bounded next hypothesis

The V27 equal-vote three-expert profile led QPR, whereas the V28 2:1
FaaSRank/Jiagu profile led throughput. A final fresh-cohort router family may
therefore switch only between these already frozen ordinal profiles at the
pre-existing current-function-demand boundary of one versus more than one.
The allowed family is bounded to: equal-three for singleton and 2:1 for
repeated demand; the complementary direction; and 2:1:1 for singleton with
equal-three for repeated demand. No new expert, threshold, scalar score,
continuous weight, result-dependent candidate addition, or reuse of E51-E55
is allowed.
