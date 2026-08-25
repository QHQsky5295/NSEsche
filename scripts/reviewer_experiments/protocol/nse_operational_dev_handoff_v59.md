# NSESche operational development handoff V59

V59 closes the two homogeneous-20 load groups that remained open after V58.
The publication-facing algorithm label is `NSESche`; `v59*` identifiers below
are internal provenance only.

## Frozen final groups

- `NSESche-low-final-v1`: internal source `v59b-moderate-majority`, profile
  `srpt_ready_hiku2_ocs_borda`, five-seed mean throughput `1.739` requests/ms,
  finite-only QPR and zero-as-zero QPR `0.07536567294649296`. The frozen
  nine-baseline maxima were `1.3188` and `0.07267390332166279`; minimum
  relative margin is `3.7039%`.
- `NSESche-middle-final-v1`: internal source `v59c-strong-majority`, profile
  `srpt_ready_hiku_ocs3_borda`, five-seed mean throughput `0.9306`
  requests/ms, finite-only QPR and zero-as-zero QPR
  `0.03567559173293096`. The frozen nine-baseline maxima were `0.65` and
  `0.02125119673759525`; minimum relative margin is `43.1692%`.
- `NSESche-high-final-v1` remains the unchanged V58 result, profile
  `srpt_ready_ocs_current_demand`, throughput `0.3464` requests/ms and both
  QPR conventions `0.0026173145305277163`.

All three groups are closed and `rerun_forbidden=true`. Downstream experiments
with the same simulation configuration must reuse the frozen catalog instead of
launching another E1 homogeneous-20 NSESche process.

## Execution and audit boundary

- V59 used only low/middle E230--E234. E235--E239 remain untouched.
- High online runs: `0`; baseline online runs: `0`.
- Input capture: `10/10` attempt-1 canonical, zero quarantine.
- Offline references: `40/40` attempt-1 canonical, zero quarantine, four valid
  ledgers.
- Online NSESche: `40/40` attempt-1 QC pass, zero quarantine, four valid
  22-event ledgers.
- Result-blind audit: `40` runs, `10` load/seed groups, `4` candidates,
  `metrics_consulted=false`; audit hash
  `399a467feb098c08e7c426fbd537ba29e38ecb35cda5e1554ebf9e3b598577dd`.
- Audit file SHA-256:
  `01fc87ca9cc76847eb753483d09ff64b4dd3d50bed3485891300050969c30ba1`.
- Revealed V59 result SHA-256:
  `3ecb57ff1c56ea9255e5ef4e1e6ce6431583783adc1639b5b2ca8352fe9f126b`.
- Frozen final catalog:
  `scripts/reviewer_experiments/protocol/NSESche_E1_homogeneous_n20_final_v1.json`;
  catalog hash
  `97332fc3acaf6264777f6199c99f612aed9ce7ded971ee59244fc14e8f2b36e0`,
  file SHA-256
  `102aaa046c0427f25cbffe78d4390deadbb31132bf7bcb68a32c7e47b6b61e53`.

The final catalog exposes 15 stable `NSESche.*.final-v1` run IDs and binds each
to its original canonical summary, QC report, audit manifest, workload tape,
and hashes. Failed development candidates remain compressed audit provenance;
they are not publication rows and are not substituted for any selected seed.
The shared `serverless_sim/records` directory remains empty.

## Implementation boundary

V59 changes only the run-level operational expert used inside the predeclared
paper-utility indifference band. It retains the ready frontier and deterministic
SRPT workflow ordering from V58 and adds exact integer Hiku/OCS ordinal votes.
Paper utility, social welfare, pricing, convergence, offline reference search,
candidate feasibility, common HPA, and workload generation are unchanged.

Rollback points remain intact:

- V58 implementation: `4e71b0a7e4955f9d4fae660491531cb961bce5bc`.
- V59 implementation: `51d9fc5f18be32173299cfb335ee345a200314b4`.
- V58 and V59 release binaries live in separate external target directories.
