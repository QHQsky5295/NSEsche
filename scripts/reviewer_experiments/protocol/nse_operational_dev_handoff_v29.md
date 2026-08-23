# NSESche V29 development closure

V29 is closed on the permanently non-formal E56-E60 cohort. None of the three
fixed demand-routed ordinal profiles passed both low-load gates. E11-E20 remain
sealed.

## Frozen identities

- Plan SHA-256: `2ea98746605fa4ed0ac49f08cb68c39fd7c5b4c64cf79161b5b27a25c0bd4b97`
- Scheduler code commit: `7cd971ed9401760f71a9575897715a4798e165b9`
- Scheduler source blob: `a1604d4fed812fad4c4637ddb9afdcbff736efea`
- Scheduler source SHA-256: `9d7ae749f22aab320a7c0c79d9ae8a5749b595803116fde30ae35f5565fe7046`
- Release binary SHA-256: `3121282dcb621e63fa68a5342eb7ae705e3affd2f4f0c75ce3a9f0869a87aeb2`
- Result: `tmp/nse_operational_dev_20260824_v29/candidate-screen.v29-demand-routed-ordinal.json`
- Result SHA-256: `73249fde874e93d993c6c3e5be9a30b210cab0a71bbdade22b898627164297fb`
- Runtime Git commit: `b68d830b58dd0b5008b9663be427c2ac9972aab8`

## Protocol closure

- E56-E60 low/homogeneous/n20; permanently non-formal.
- Tapes 5/5, baselines 45/45, references 15/15, and candidates 15/15 all
  canonicalized on attempt one with zero quarantine.
- Result-blind pairing passed 60/60 runs; execution was strictly serial.
- `serverless_sim/records` remained empty; E11-E20 were not read.
- E56-E60 are closed to further tuning. E61-E65 in the full source remain
  uncaptured, unreferenced, unexecuted, and uninspected.

## Result

Baseline leaders were FaaSRank in throughput (`1.447`) and Hiku in QPR
(`0.08910173833571113`).

| Candidate | Throughput | T rank | QPR | QPR rank | Decision |
|---|---:|---:|---:|---:|---|
| V29a equal-three singleton / 2:1 repeated | 1.4154 | 5 | 0.08307711713066654 | 6 | Fails both |
| V29b 2:1 singleton / equal-three repeated | 1.4020 | 8 | 0.088561363590035 | 2 | Fails both |
| V29c 2:1:1 singleton / equal-three repeated | 1.4534 | 1 | 0.08616506432273266 | 5 | Throughput only |

No candidate is selected; confirmation remains sealed.

## Bounded next hypothesis

V29b and V29c share the same repeated-demand profile and differ only in the
LoadLeast singleton vote. A fresh cohort may test whether that vote should be
enabled only when the current function lacks a feasible reusable warm
container. The bounded family is: any-warm gating, idle-warm gating, and the
any-warm complement as a directional control. Repeated demand remains frozen
equal-three. No new expert, fitted threshold, scalar score, or reuse of
E56-E60 is allowed.
