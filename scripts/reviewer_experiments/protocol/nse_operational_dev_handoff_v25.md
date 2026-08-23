# NSESche V25 development handoff

- Plan: `nse_operational_dev_plan_v25.json`
- Plan SHA-256: `6c4343f82d0d7b3c61b67407798092466211afc0c340d8a6ab24aaee93814b7f`
- Result: `tmp/nse_operational_dev_20260824_v25/candidate-screen.v25-leader-state.json`
- Result SHA-256: `e224e2e3c04361ca8a2d61fea026dc79e9f6b75b4e7b6b208b8b7c7abd6b07a5`
- Runtime Git: `618685416d97439267466bd72e57890586488b24`
- Scheduler code commit: `a2abfec00679703e181e1bb9caae3432d70abac2`
- Binary SHA-256: `89b4c3815a081cf4d1e8d3d012e271d86b5ef377de52df88ff99be3889886cce`

## Integrity gates

- Fresh development seeds: E36-E40, low/homogeneous/n20 only.
- Tape capture: 5/5 first-attempt canonical, zero quarantine.
- Reference builds: 15/15 first-attempt canonical, zero quarantine.
- Online runs: 60/60 first-attempt canonical and QC pass, zero quarantine.
- Pairing: all four reports passed; all 60 runs share the frozen tape/common-HPA/runtime identities required by their manifests.
- Simulator processes were serialized on development port 3107.
- `serverless_sim/records` remained empty.

## Result-blind decision

No V25 candidate passed the preregistered combined gate. The frozen E36-E40 baseline leaders were Hiku for mean fixed-window throughput (`1.4984`) and Orion for mean per-run QPR (`0.0507143099`).

| Candidate | Throughput | Throughput rank | QPR | QPR rank | Selected |
|---|---:|---:|---:|---:|---|
| v25a-faasrank-score | 1.4488 | 5 | 0.0512997644 | 2 | no |
| v25b-load-least-faasrank-tie-current-demand | 1.3992 | 9 | 0.0453116244 | 8 | no |
| v25c-faasrank-singleton-load-least-burst | 1.4756 | 3 | 0.0513534363 | 1 | no |

V25c is the first fresh-cohort candidate in this track to rank first for QPR, but it remains 1.52% below the throughput leader. E36-E40 are closed permanently for tuning and may not be subdivided, retried, or reused for candidate selection. E11-E20 remain sealed confirmation seeds.

E41-E45 were declared in the V25 full source manifest but were never captured, referenced, or executed, so they remain a fresh development cohort. The result supports one bounded next hypothesis only: retain V25c's frozen FaaSRank singleton branch and replace its repeated-demand LoadLeast branch with one of the two already implemented, outcome-blind Hiku state rules (legacy one-shot Hiku or load-faithful Hiku). Do not fit a mixing weight or inspect E41-E45 before the next plan is committed.
