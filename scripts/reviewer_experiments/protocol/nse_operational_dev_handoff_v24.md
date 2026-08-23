# NSESche V24 development handoff

- Plan: `nse_operational_dev_plan_v24.json`
- Plan SHA-256: `7d44a911b9288013aa31cb7b328a27e9cd1813a464d70f0ad9ce0f7481cdfbd9`
- Result: `tmp/nse_operational_dev_20260824_v24/candidate-screen.v24-leader-state.json`
- Result SHA-256: `b597ddc25a7444044f1734e5dc5187ff4ed39a8323280f7e8ddd848ec35309d4`
- Runtime Git: `45523ab9e21e7c9f66467c9fa4b360312aaef4ab`
- Scheduler code commit: `c8ef1d0b7581855aa38a5e17517e3dcdeba49ec4`
- Binary SHA-256: `41190842bc32534017bd3eb978d92951ee9f085a5a6bd11826fc655ef879b389`

## Integrity gates

- Fresh development seeds: E31-E35, low/homogeneous/n20 only.
- Tape capture: 5/5 first-attempt canonical, zero quarantine.
- Reference builds: 15/15 first-attempt canonical, zero quarantine.
- Online runs: 60/60 first-attempt canonical and QC pass, zero quarantine.
- Pairing: all four reports passed; all 60 runs share the frozen tape/common-HPA/runtime identities required by their manifests.
- Simulator processes were serialized on development port 3107.
- `serverless_sim/records` remained empty.

## Result-blind decision

No V24 candidate passed the preregistered combined gate. The frozen E31-E35 baseline leaders were LoadLeast for mean fixed-window throughput (`1.2390`) and FaaSRank for mean per-run QPR (`0.0538564946`).

| Candidate | Throughput | Throughput rank | QPR | QPR rank | Selected |
|---|---:|---:|---:|---:|---|
| v24a-load-least-current-demand | 1.1126 | 8 | 0.0456432078 | 5 | no |
| v24b-ocs-current-demand | 1.1700 | 5 | 0.0382455313 | 9 | no |
| v24c-ocs-singleton-load-least-burst | 1.1878 | 3 | 0.0435919442 | 6 | no |

E31-E35 are closed permanently for tuning and may not be subdivided, retried, or reused for candidate selection. E11-E20 remain sealed confirmation seeds. A subsequent development epoch must be preregistered before capturing a fresh cohort (next reserved cohort: E36-E40).

The V24 result supports one bounded next hypothesis only: combine the frozen LoadLeast primary load key with the frozen FaaSRank state score, because those are the two E31-E35 baseline leaders. Do not fit new continuous weights or inspect E36-E40 before the next plan is committed.
