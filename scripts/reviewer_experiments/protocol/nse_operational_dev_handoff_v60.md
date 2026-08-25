# NSESche operational development handoff V60

V60 evaluates E1 heterogeneous-20 low, middle, and high with four
pre-registered, load-specific NSESche candidates on fresh E240--E244. The
publication-facing algorithm label is `NSESche`; every `v60*` identifier is
internal provenance only.

## Frozen final group

- `NSESche-heterogeneous-n20-low-final-v1` is closed. Its internal source is
  `v60a-homogeneous-transfer`, profile `srpt_ready_hiku2_ocs_borda`. Five-seed
  mean throughput is `1.4216` requests/ms and both QPR conventions are
  `0.040295359405823614`. The frozen twenty-seed nine-baseline maxima are
  `1.2338` and `0.03849669170213395`; the minimum relative margin is
  `4.6723%`.

The low group is `rerun_forbidden=true`. Downstream experiments with the same
simulation configuration must reuse its frozen runs rather than launch another
E1 heterogeneous-20 low NSESche process.

## Open groups

- Middle remains open. All four candidates beat the frozen throughput maximum
  `0.68725`, but none beat both QPR thresholds. The best observed QPR was the
  internal balanced candidate at `0.020320157743486757`, below the finite-only
  threshold `0.025338391550243932` and zero-as-zero threshold
  `0.024071471972731733`.
- High remains open. No candidate beat the frozen throughput maximum `0.47465`
  or QPR maximum `0.00550856706612981`; each candidate had one zero-completion
  run among five seeds. The best observed throughput was `0.314` and the best
  finite-only QPR was `0.0014398499228821405`.

All unsuccessful trials are retained as audit evidence. They are not
publication rows, are not deleted or replaced, and cannot be selectively
rerun. E245--E249 remain untouched pending a separately committed plan for only
the open middle/high groups.

## Execution and audit boundary

- Frozen formal baseline online runs: `0`; homogeneous online runs: `0`.
- Input capture: `15/15` attempt-1 canonical, zero quarantine, one valid
  15-event ledger.
- Offline references: `60/60` attempt-1 canonical, zero quarantine, four valid
  15-event ledgers.
- Online NSESche: `60/60` attempt-1 QC pass, zero quarantine, four valid
  32-event ledgers.
- Result-blind audit: `60` runs, `15` load/seed groups, `4` candidates,
  `metrics_consulted=false`; audit hash
  `2cd68ffbdd5b31cef293dbe815429ea300292c2330ee09bde4e2b0a0e1fa928b`.
- Audit file SHA-256:
  `5e8f358677535fbd840a142d5ebdd3c1c4014e89a6139ad7cda8e95855591056`.
- Revealed V60 result SHA-256:
  `c6a227cccf2bb6850beaf1390e2eb69196b0a95b8d03758210408253d0ebea3b`.
- Frozen partial catalog:
  `scripts/reviewer_experiments/protocol/NSESche_E1_heterogeneous_n20_final_v1.json`;
  catalog hash
  `03610a0c9e60071f09ccf9046a7c90caddcef8489d19c0bc3f420b2e6de9be9f`,
  file SHA-256
  `56ac641fbbe221d33a63e619adf8f64fa4fce2b009b771fe7ff892d586e802c3`.

The catalog currently exposes five stable
`NSESche.E1.heterogeneous.n20.low.*.final-v1` run IDs and binds each to its
canonical summary, QC report, audit manifest, workload tape, and hashes. Its
`bundle_status` is `partial_open`, with middle and high explicitly listed as
open.

## Implementation boundary

V60 adds exact ready-frontier SRPT wrappers for the frozen FaaSRank and Load
Balance placement experts and their equal ordinal Borda combination. Paper
utility, social welfare, pricing, convergence, offline reference search,
candidate feasibility, common HPA, and workload generation are unchanged.

The V60 runtime is fixed at git commit
`5288a815d8a0813166f39c9b0909cbd1dc8f873a`, binary SHA-256
`564ba5d80434847fb88baa9f07d6f5af7b0599f269710a8fa041d4f1b96aa749`,
and simulator port `3107`. The release binary lives in a separate external
target directory, so the earlier V58/V59 rollback points remain intact.
