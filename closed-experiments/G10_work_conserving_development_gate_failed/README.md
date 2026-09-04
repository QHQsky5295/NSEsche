# G10 Work-Conserving Development Experiment (Closed)

Status: `complete_g10_development_gate_failed_strong_baselines_blocked`

This directory is the permanent root-level evidence package for the closed G10
development experiment. It retains the result-free protocol lineage, exact
45-run selection, reconciliation and gate reports, append-only ledgers, audits,
and exact mechanism/analyzer source files.

C1's remaining-work order produced small mean gains at middle/high load but
failed low-load QPR, paired robustness, and the per-seed floor. C2's bounded
frontier produced a large high-load gain and passed all work-conserving
activation invariants, but reduced low/middle throughput and had a severe
middle-load tail. Neither candidate is eligible for a strong-baseline addendum,
confirmation, formal replay, a figure, or a paper performance claim. See
`audits/G10_WORK_CONSERVING_RESULT_AUDIT.md` for the complete gate outcome and
the disclosed non-applicable C0 analyzer check.

The complete immutable raw workspace is stored at:

`E:\NSEsche_experiment_archives\tscv1_g10_work_conserving_d96_d100_ab0ae94_20260904`

It contains 1,527 files and 566,678,494 bytes. Its sorted inventory SHA-256 is
`aed84ef942171c77d6ed340b9f2cfabb062a0b57b09b8cf02111443499704ff9`,
which exactly matches the source run root at closure.

Key commits:

- mechanism source: `ab0ae94f0a8314db348078040a49dfe59281653e`;
- final bound inputs: `5974a61`;
- frozen analyzer and zero-result selection: `4283957`.

Do not reuse D96--D100 for tuning, seed selection, or successor validation. A
future mechanism requires a distinct name, a fresh seed bank, and a committed
result-free protocol after read-only diagnosis of this retained evidence.
