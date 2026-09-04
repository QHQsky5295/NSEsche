# P2 Low-Load Hyperparameter Recovery Result Audit

Date: 2026-09-05 (Asia/Shanghai)

Protocol/analyzer commits: `fab5df83b8040c9e4a875b1581d46aed84ae4aa7`,
`d664e3a8554fbf3e560b1b2b1399d3a934417449`

Status: `complete_p2_low_parameter_recovery_failed_formal_blocked`

## 1. Complete retained population

The one authorized result-blind batch executed all 25 frozen homogeneous-low
`ready_order` specifications: the submitted centre and four E7 axial
neighbours on shared D121--D125 tapes. All 25 runs canonicalized on attempt 1.
There were no retries, seed replacements, omissions, quarantines, or
outcome-conditioned extensions.

Independent reconciliation reopened every result against the exact
reference-bound manifest. All 25 paths were already exact and zero repairs
were performed. Every run is QC-valid and has positive fixed-window
completion and defined run-level QPR. The 375-file canonical tree contains
23,386,180 bytes and has path-independent sorted inventory hash
`7a06b6a3ce83ef8c4beea21f0f26b1f486c1a87a671c075c3e46565383fd1e98`.
The partial and quarantine trees contain zero files.

The append-only online ledger contains 52 valid chained events and ends at
`162df0725d8c57a145464c4fa5553557430fe52559462adf195fd50218e2b54c`;
the 49,370-byte ledger has SHA-256
`17cb145c994561a3bb50a451ac92a852f9c41eae6d895732e7897d81722587ae`.
The 20,670-byte reconciliation report has document/file hashes
`3ba1e67dfcae2c20f7ece0027e161725e89732573922879898aac11319057291`/
`ef218ed1cccfe0fe5366f0b654fc9724b5aca805b408bd36ccc24c2bec0ad899`.

## 2. Frozen gate outcome

The one-shot analyzer returned
`complete_p2_low_parameter_recovery_failed_formal_blocked`, admitted no
neighbour, and authorized no formal sampling. Its complete 146,457-byte
report has canonical document hash
`7f6a074926580f548b224e595df0739cb8a7f7af5d0d6615fd11ddb2ddcbb1c3`
and file SHA-256
`02cf7e36cdccc3969bc690ac028069d3de7870cdc06759dc6b1b0aad25d5a1a9`.

An independent calculation reopened every canonical `summary.json` and
recomputed fixed-window throughput, drained-cohort mean latency, simulator
cost per completion, QPR, completion ratio, and policy wall time. Throughput,
completion, latency, and policy-time maximum absolute errors versus the
frozen report are zero; the QPR maximum absolute error is
`6.94e-18` (floating-point roundoff).

| Setting | Mean T (req/ms) | T / centre | Mean QPR | QPR / centre | Joint wins / nonlosses |
|---|---:|---:|---:|---:|---:|
| centre (`r0=0.60,wq=0.50`) | 1.2910 | 1.000000 | 0.0325134 | 1.000000 | -- |
| r0_minus (`0.55,0.50`) | 1.2910 | 1.000000 | 0.0325134 | 1.000000 | 0 / 5 |
| r0_plus (`0.65,0.50`) | 1.2910 | 1.000000 | 0.0325134 | 1.000000 | 0 / 5 |
| wq_minus (`0.60,0.40`) | 1.2812 | 0.992409 | 0.0323671 | 0.995501 | 1 / 1 |
| wq_plus (`0.60,0.60`) | 1.2904 | 0.999535 | 0.0319295 | 0.982043 | 2 / 2 |

Neither price-feedback neighbour changes throughput, QPR, completion, or
latency in any seed. Both are exact run-level ties with the centre and fail
the required 1.015/1.11 dual-mean margins, the three joint-win condition, and
the requirement for at least four strictly positive leave-one-seed-out
differences per metric.

Both quality-weight neighbours also fail the dual-mean, paired-robustness,
leave-one-out, and nondecreasing-completion conditions. `wq_minus` has mean
completion ratio 0.992339, one joint win/nonloss, and only one nonnegative
leave-one-out mean for each primary metric. `wq_plus` has mean completion
ratio 0.999611, two joint wins/nonlosses, two nonnegative throughput
leave-one-out means, and one nonnegative QPR leave-one-out mean. All four
neighbours satisfy the 0.80 per-seed safety floors and the 1.50 policy-time
limit; none is close to the required positive effect size.

## 3. Offline-reference integrity

The centre, both `r0` neighbours, and `wq_minus` pass runtime identity and
strict-PNE/offline-reference integrity. The retained `wq_plus` D123 run has
976 strict-PNE active windows but only 974 positive reference hits. Its
prebuilt table contains the two previously disclosed finite negative values,
loaded at active windows 581 and 741. This correctly fails only
`wq_plus` condition 7. It is not the deciding weakness: `wq_plus`
independently fails the performance, robustness, leave-one-out, and
completion/latency conditions.

No run reaches the inner best-response limit and no oscillation is observed.
Thus the negative result is not caused by convergence failure or online
execution instability.

## 4. Evidence-bounded interpretation

**Observation.** Moving `r0` from 0.60 to 0.55 or 0.65 produces identical
decisions and performance on all five low-load tapes. Moving `wq` by 0.10 is
decision-active but does not improve both target metrics: the lower value
slightly reduces throughput and QPR, while the higher value is nearly neutral
in throughput and reduces mean QPR by 1.80%.

**Interpretation.** The low-load shortfall cannot be recovered by the
submitted local axial sensitivity points. In this regime, the tested `r0`
interval is operationally dormant; changing `wq` perturbs marginal placement
choices without delivering a robust benefit. Enlarging this same local grid
after seeing the result would be a new exploratory study, not completion of
the preregistered screen.

**Implication.** The submitted centre is retained for faithful reporting, but
the existing homogeneous-low Q61--Q80 result remains non-leading. No new
Q81--Q100 ten-method formal bank, E7 formal panel, figure, or comparative
claim is authorized. D121--D125 are exhausted development evidence and may
not be filtered, rerun, or reused to validate a successor.

**Next step.** A separately preregistered, read-only diagnosis may use all 25
P2 runs together with the complete retained low-load Q61--Q80 comparison to
identify (i) why `r0` is decision-dormant, (ii) which pre-decision terms make
`wq` changes harmful, and (iii) which mechanism component, already outside
Eqs. (1)--(20), could change completion and latency without changing the
paper's game or QPR definitions. Any successor must be fixed before new data
and tested on a fresh seed bank.

## 5. Authorization boundary

- `p2_candidate_selected=false`;
- `formal_q81_q100_sampling_authorized=false`;
- `e7_formal_panel_authorized=false`;
- `strong_baseline_sampling_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_low_root_cause_diagnosis_authorized=true`.

