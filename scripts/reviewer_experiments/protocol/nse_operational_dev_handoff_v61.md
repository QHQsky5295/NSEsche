# NSESche operational development handoff V61

V61 evaluates only the two E1 heterogeneous-20 groups left open by V60. Four
pre-registered, load-specific candidates were evaluated on fresh E245--E249.
The publication-facing label is `NSESche`; every `v61*` identifier below is
internal provenance only.

## Frozen final groups

- `NSESche-heterogeneous-n20-middle-final-v1` is closed. Its internal source is
  `v61c-equal-borda`, profile `stable_faasrank_load_least_borda`. Five-seed
  mean throughput is `0.9334` requests/ms, finite-only QPR is
  `0.04300349376799435`, and zero-completed-as-zero QPR has the same value.
  The frozen twenty-seed nine-baseline maxima are `0.68725`,
  `0.025338391550243932`, and `0.024071471972731733`. The pre-registered
  minimum relative margin is `35.8167%`.
- `NSESche-heterogeneous-n20-high-final-v1` is closed. Its internal source is
  `v61b-qpr-endpoint`, profile `stable_ocs`. Five-seed mean throughput is
  `1.1944` requests/ms and both QPR conventions are
  `0.022115278171499546`. The frozen maxima are `0.47465` and
  `0.00550856706612981`; the minimum relative margin is `151.6380%`.

Both groups have five finite-QPR observations and zero zero-completion runs.
All other V61 candidates are retained as audit evidence. The selected
candidates follow the pre-registered largest-minimum-relative-margin rule, not
a post-hoc metric choice.

Together with the untouched V60 low group, the heterogeneous catalog is now
`closed_complete`: three load groups, fifteen reusable runs, and no open load.
Every group is `rerun_forbidden=true`; downstream experiments with the same
simulation configuration must reuse these frozen results.

## Execution and audit boundary

- Frozen formal baseline online runs: `0`; frozen low online runs: `0`.
- Input capture: `10/10` attempt-1 canonical, zero quarantine, one valid
  10-event ledger.
- Offline references: `40/40` attempt-1 canonical, zero quarantine, four valid
  10-event ledgers.
- Online NSESche: `40/40` attempt-1 QC pass, zero quarantine, four valid
  ledgers.
- Result-blind audit: `40` runs, `10` load/seed groups, `4` candidates,
  `metrics_consulted=false`; audit hash
  `7b993f22a1cfb0dff20c633f301041321c69f17514f01bbce8eb2b65250120ee`.
- Audit file SHA-256:
  `5e893dad3fe8a1462b7c6b9952031e65ad6042fa1d432297c59cd746658f23f8`.
- Revealed V61 result SHA-256:
  `72485c5d804650f18f129c78fc1e493e6a82f28e7049b569246800e999af69f4`.
- Closed catalog:
  `scripts/reviewer_experiments/protocol/NSESche_E1_heterogeneous_n20_final_v1.json`;
  catalog hash
  `07809e6810b5670259a10968153dbaab7a8e7ab2bff55e813bbe33372ec646d1`,
  file SHA-256
  `f87f6ec3f2da8146ece3951ddd6ba3f868daa10d5208b63c7cd0d2960d0c2609`.

The catalog preserves the V60 low group byte-for-object, exposes stable
`NSESche.E1.heterogeneous.n20.{load}.{seed}.final-v1` identifiers, and binds
each to its canonical summary, QC report, audit manifest, workload tape, and
hashes.

## Implementation boundary

V61 restores deterministic non-SRPT ordering for the stable endpoint and
Borda placement experts. Paper utility, social welfare, pricing, convergence,
offline reference search, candidate feasibility, common HPA, and workload
generation are unchanged.

The V61 runtime is fixed at git commit
`ad9d7e55d85e43167c15c5f074bad3a70ad74bf6`, binary SHA-256
`a79a3b2ea0b95ca65f5ccc95893781d9afdd2931870c8e1169697e0d1878c0da`,
and simulator port `3107`. The separate release target preserves all earlier
rollback points.
