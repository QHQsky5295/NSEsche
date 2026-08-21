# NSESche operational development handoff (V20)

Date: 2026-08-21

This development track is result-ineligible and used only low-load E01–E03. E04–E10 were not used for selection or confirmation, and E11–E20 remain sealed.

## Frozen development outcome

- Middle and high remain frozen at V8. Their E01–E03 mean throughput/QPR ranks are both first: middle `0.706 / 0.0076616560`; high `1.108 / 0.0101898417`.
- The best low-load throughput candidate remains V11: mean throughput `1.852`, mean QPR `0.0663880577`, both rank second behind Hiku (`1.854`, `0.0666664754`).
- V19 isolated the pre-window resident exact-function backlog. It passed all technical gates but ranked second in both low throughput (`1.822`) and QPR (`0.0665349145`). The exact-function-load branch is closed.
- The final preregistered V20 queue grid moved QPR to first but created a throughput tradeoff. V20a (`queue=0.21`) produced throughput/QPR `1.713333 / 0.0672635361` (ranks `5/1`); V20b (`queue=0.225`) produced `1.768 / 0.0697221930` (ranks `3/1`). Neither candidate passed all gates.
- Per the V20 termination rule, no optimized configuration was selected and confirmation was not unsealed.

## Audit bindings

- V8 screen: `tmp/nse_operational_dev_20260820/candidate-screen.v8-deployment-profile-experts.json`, SHA-256 `a8ead4edf8bc10e690b4eb5af83abd4d73e9605d91630a7abae3ed0decb1d709`.
- V11 screen: `tmp/nse_operational_dev_20260820/candidate-screen.v11-low-direct-idle-efficiency-unrestricted-init.json`, SHA-256 `e25db9461e0fd6adc6bc47633b410cebb946fd18d8301cd8c33cbb54fc732700`.
- V19 plan: `nse_operational_dev_plan_v19.json`, SHA-256 `48e2b337e2ea15f78aa84b29d0c56503b892114668abab30a66aa07fecddd7b0`.
- V19 screen: `tmp/nse_operational_dev_20260820/candidate-screen.v19-low-direct-resident-function-load.json`, SHA-256 `27d8aaebe8ad8ea407b1016077246f3938268fb61b455d7bdb91beacb00a01c6`.
- V20 plan: `nse_operational_dev_plan_v20.json`, SHA-256 `158b6f7cd2d2d31d155dbf3cf149293ead0fee4cd2a7bf528f7a3d84515ae16a`.
- V20 screen: `tmp/nse_operational_dev_20260820/candidate-screen.v20-final-low-queue-grid.json`, SHA-256 `a5aa552dc06975a33195c493347b465d7e9affda50cf12d7f38c33c7a6ce3285`.
- Release binary: SHA-256 `3fae18ffd396162d94343e716ab96c169eac842e1684344736c91db454cc96f1`.
- Code checkpoint: `ed19d96` (`feat: isolate resident function load signal`).
- Plan checkpoints: `43cd16b` (V19) and `5288d51` (V20).

All V19/V20 reference builds and online runs canonicalized on attempt 1, protocol QC and result-blind pairing passed, quarantine count was zero, and `serverless_sim/records` remained empty.

## Unexecuted future hypothesis

After V20 was read, a post-hoc state hypothesis became visible: V11 pre-window queue density was materially higher for E02 (mean `13.13`, p50 `13.7`) than E01/E03 (means `5.63/4.23`, p50 `5.9/1.0`). A future protocol could preregister a queue-density-gated weight (`0.21` only at low density, otherwise V11's `0.20`). It was not preregistered before V20 and was therefore not run in this development track.
