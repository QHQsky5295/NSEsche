# NSESche V27 development closure

V27 is closed on the permanently non-formal E46-E50 cohort. The fixed
FaaSRank/Jiagu router and both equal-vote ordinal ensembles completed, but none
passed the combined low-load gate. E11-E20 remain sealed.

## Frozen identities

- Plan: `nse_operational_dev_plan_v27.json`
- Plan SHA-256: `c75b67f0d3867488f5a72d3098ba4b2e2dbaffe2c7b78f49f8feb252a5a10e16`
- Scheduler code commit: `cb1777f29ef8a7df91c52599e7bf575d3026b0b4`
- Scheduler source blob: `3118243323b17694608573381fc1003a4cb3f392`
- Scheduler source SHA-256: `c0bb63d1e359337a9d4b0e2bd85a7c050d60c209b6fde3137609fdaf6feb753c`
- Release binary SHA-256: `9ec55094619a7f3fd482ddee63bd442ec76f0d93e02c15cc45b421be01aa40d6`
- Result: `tmp/nse_operational_dev_20260824_v27/candidate-screen.v27-ordinal-ensemble.json`
- Result SHA-256: `d927f2c41a3dcf93880aa881cb73faef7a2d20536650afb83a765c0829dbd8dd`
- Runtime Git commit recorded by all online runs: `c82f89ac4437d18924b835125366468f7fcba633`

## Protocol closure

- Fresh development seeds: E46-E50, low/homogeneous/n20 only.
- Tape capture: 5/5 first-attempt canonical, zero quarantine.
- Baselines: 45/45 first-attempt canonical and QC pass.
- Candidate references: 15/15 first-attempt canonical, zero quarantine.
- Candidate online runs: 15/15 first-attempt canonical and QC pass.
- Result-blind pairing: 60/60 online runs across all four manifests.
- Execution was strictly serial; `serverless_sim/records` remained empty.
- E21-E45 were not reused for selection; E04-E10 and E11-E20 were not read.
- E46-E50 are permanently closed to further tuning.
- E51-E55 were present only as unused reserve seeds in the full source. They
  were not captured, referenced, executed, or inspected.

## Result

The E46-E50 baseline leaders were Greedy in throughput (`1.609`) and Orion in
QPR (`0.05139888811269051`).

| Candidate | Throughput | Throughput rank | QPR | QPR rank | Decision |
|---|---:|---:|---:|---:|---|
| V27a: FaaSRank singleton / Jiagu repeated-demand router | 1.5176 | 6 | 0.04783040565082007 | 4 | Fails both gates |
| V27b: equal-vote FaaSRank + Jiagu Borda | 1.4652 | 7 | 0.04657885628696322 | 7 | Fails both gates |
| V27c: equal-vote FaaSRank + Jiagu + LoadLeast Borda | 1.5878 | 3 | 0.05392199372874986 | 1 | QPR only |

No candidate strictly exceeded all nine baselines in both metrics. No
candidate is selected, and confirmation remains sealed.

## Bounded next hypothesis

V27c led QPR while falling only `0.0212` requests/ms below the throughput
leader. The frozen FaaSRank baseline was second in throughput (`1.6022`) but
weaker in QPR. A final fresh-cohort ordinal-family test may therefore shift the
same three already frozen expert ranks toward FaaSRank using only preregistered
small integer vote multiplicities. The allowed family is bounded to 2:1:1,
2:1, and 3:1:1 FaaSRank-majority Borda variants, with the existing worst-rank
and node-ID tie breaks. No continuous weight fitting, score normalization,
threshold search, result-dependent candidate addition, or reuse of E46-E50 is
allowed.
