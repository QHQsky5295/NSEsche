# NSESche V26 development closure

V26 is closed on the permanently non-formal E41-E45 cohort. Both preregistered
FaaSRank-singleton/Hiku-repeated-demand routers completed, but neither passed
the combined low-load gate. E11-E20 remain sealed.

## Frozen identities

- Plan: `nse_operational_dev_plan_v26.json`
- Plan SHA-256: `9e42b10f9b977c242095693a8d91ce4a165371c271c4b379c5d7765fda839efe`
- Scheduler code commit: `1351f39343c5b8d697813a40fe88df56b04b2b5c`
- Scheduler source blob: `0b04f267b15fcc784697d67dcb63f65c7be7f2b0`
- Scheduler source SHA-256: `3dded564005fb16d258b8269ed4477881aea2b17eafb16886bd6c420eb48bd85`
- Release binary SHA-256: `c081198e7656ac9b14454eb2d839e64134a34f86fb2614918f053b6fa070125b`
- Result: `tmp/nse_operational_dev_20260824_v26/candidate-screen.v26-faasrank-hiku-router.json`
- Result SHA-256: `ee408a21ea528b65c24693738db16873c01f78988257ebbb13f4eea030a7ea45`
- Runtime Git commit recorded by all online runs: `f07ba117685c32e69447e5954f3f8c180f6a419b`

## Protocol closure

- Fresh development seeds: E41-E45, low/homogeneous/n20 only.
- Tape capture: 5/5 first-attempt canonical, zero quarantine.
- Baselines: 45/45 first-attempt canonical and QC pass.
- Candidate references: 10/10 first-attempt canonical, zero quarantine.
- Candidate online runs: 10/10 first-attempt canonical and QC pass.
- Result-blind pairing: 55/55 online runs across all three manifests.
- Execution was strictly serial; `serverless_sim/records` remained empty.
- E21-E40 were not reused for selection; E04-E10 and E11-E20 were not read.
- E41-E45 are permanently closed to further tuning.
- E46-E50 were present only as unused reserve seeds in the full source. They
  were not captured, referenced, executed, or inspected.

## Result

The E41-E45 baseline leaders were Greedy in throughput (`1.4108`) and Hiku in
QPR (`0.04693837374677384`).

| Candidate | Throughput | Throughput rank | QPR | QPR rank | Decision |
|---|---:|---:|---:|---:|---|
| V26a: FaaSRank singleton + load-faithful Hiku repeated demand | 1.2996 | 7 | 0.04968285777436436 | 2 | QPR only |
| V26b: FaaSRank singleton + legacy Hiku repeated demand | 1.3044 | 6 | 0.04969435415496561 | 1 | QPR only |

Neither candidate strictly exceeded all nine baselines in both metrics. No
candidate is selected, and confirmation remains sealed.

## Bounded next hypothesis

V23's current-demand Jiagu proxy was second in both metrics, while V25/V26
showed that the frozen FaaSRank singleton rule can lead QPR. The next fresh
cohort may therefore test only a fixed FaaSRank-singleton/Jiagu-repeated-demand
router and equal-vote ordinal combinations of the already frozen FaaSRank,
Jiagu, and LoadLeast state rules. No learned or fitted scalar weights, result-
dependent thresholds, or reuse of E41-E45 is allowed.
