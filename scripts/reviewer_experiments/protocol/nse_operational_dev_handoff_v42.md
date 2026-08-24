# V42 ready-frontier middle-load handoff

V42 is closed without a selected middle-load profile.  It used only the
preregistered, permanently non-formal E130--E134 cohort.  All five tapes,
state-matched references, and online runs completed on their first attempt;
there were no quarantined runs.  The result-blind pairing audit passed 5/5
groups and has SHA-256
`df7c278ef0c6c89285667295d54660f4b4968032297d9d99e1ac29cd7fa1d71e`.

`faasrank_ready_only` achieved mean fixed-window throughput `1.0950` and mean
QPR `0.0187506902` (five finite runs, zero zero-completion runs).  It therefore
did not strictly exceed the frozen E11--E20 FaaSRank thresholds `1.1348`,
`0.0673776749` finite-only QPR, and `0.0606399074` zero-completion-as-zero QPR.

Per-seed throughput/QPR were:

| Seed | Throughput | QPR |
|---|---:|---:|
| E130 | 1.660 | 0.0162527 |
| E131 | 1.099 | 0.00696929 |
| E132 | 0.319 | 0.000426917 |
| E133 | 0.173 | 0.000420016 |
| E134 | 2.224 | 0.0696845 |

The ready-frontier change did solve the V41 technical bottleneck: all five
reference builds completed in about 64 seconds total rather than reaching the
30-minute adapter limit.  However, the large environment-seed spread also
shows that comparing fresh candidates only to an old unpaired scalar threshold
is not a reliable way to establish first place.  E130--E134 are closed and
must not be subdivided or reused for tuning.

A subsequent cohort should run all frozen baselines and all preregistered
candidates on the same tapes and reveal them together.  E135--E139 were only
declared as unused full-manifest reserve members; they were not captured or
executed in V42.  E120--E129 remain sealed holdout seeds.  Frozen low
`orion_ocs2_borda` and high `jiagu_current_demand` remain unchanged.
