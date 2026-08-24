# V43 fully paired middle-load handoff

V43 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E135--E139 cohort. All 60 online runs
(nine frozen baselines and three candidates on five common tapes) passed QC.
The result-blind joint pairing audit passed 5/5 seed groups and 60/60 runs;
its file SHA-256 is
`292facaa31c95498d174a1b2a0fed99068db43a8051ddd3c37446ad820c38878`
and its internal audit hash is
`5cb242c7e4d65c0276059286fe88eab912d8a6aa0e1a6ca15dd3abc3c8ec05e9`.
The revealed paired screen has SHA-256
`876c5361e3ef470b56eb061264bfade2696584d0b36c26b877dc50d141769396`.

The strongest candidate, `faasrank_ready_faithful`, ranked first in mean
fixed-window throughput (`0.9282` requests/ms) but only fifth in both QPR
definitions (`0.0182436450`; all five runs were finite and none had zero
completions). The QPR leader was `sche_Hiku` at `0.0214787812`; its throughput
was only `0.6382`. No candidate ranked first in throughput, finite-only QPR,
and zero-completion-as-zero QPR simultaneously, so the frozen V43 winner gate
failed. No seed is removed or replaced, and no post-hoc composite is selected.

| Rank | Throughput method | Mean throughput | QPR method | Mean QPR |
|---:|---|---:|---|---:|
| 1 | faasrank_ready_faithful | 0.9282 | sche_Hiku | 0.0214787812 |
| 2 | sche_orion | 0.8872 | load_least | 0.0197434331 |
| 3 | sche_FaaSRank | 0.8620 | sche_OCS | 0.0195606105 |
| 4 | faasrank_ready_ocs_borda | 0.7802 | sche_jiagu | 0.0183624935 |
| 5 | greedy | 0.7580 | faasrank_ready_faithful | 0.0182436450 |

The revealed development data support one outcome-blind follow-up mechanism.
The scheduler's existing `operational_queue_density()` is exactly
`(pending_tasks + runnable_tasks) / node_count`, and the same quantities are
recorded in every Nash window. For `faasrank_ready_faithful`, E136 (where Hiku
had its dominant QPR advantage) stayed below `28.4` tasks/node. The other four
seeds reached maxima `74.2`--`202.9`, with active-window medians approximately
`66.5`, `125.1`, `61.3`, and `56.6`. This justifies testing fixed thresholds
around 8, 16, and 32 tasks/node: below the threshold use the already-defined
load-faithful Hiku placement proxy, otherwise retain the V43 faithful
FaaSRank choice. The router reads only current queue state, never outcomes or
workload labels. These thresholds are diagnostic candidates, not a selected
profile; they require a new preregistered, fully paired cohort.

E135--E139 are permanently closed. E120--E129 remain sealed holdout seeds.
Frozen low `orion_ocs2_borda` and high `jiagu_current_demand` remain unchanged.

