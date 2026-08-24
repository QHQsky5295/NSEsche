# V44 queue-aware middle-load handoff

V44 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E140--E144 cohort. All five tapes,
15 references, 45 frozen-baseline runs, and 15 candidate runs canonicalized
on their first attempt with zero quarantine. The result-blind joint pairing
audit passed 5/5 seed groups and 60/60 runs. Its file SHA-256 is
`b688f1976c71c58b1d0e146e7106ea470c19c122fd3d48432c9de40a3d33b248`
and its internal audit hash is
`2dfced9687a4b74e2ba6ed8da188f6d5132e0336897200dbfa0dc7a42d2002bf`.
The paired screen SHA-256 is
`682e0b8e80063143cebc1cf862dfc97ec437877c9086fd08b310a19986e7d224`.

No candidate passed the frozen simultaneous rank-one gate. Orion led mean
fixed-window throughput at `0.8766` requests/ms, while FaaSRank led both QPR
definitions at `0.0300545855`. The best candidate was the 8-task/node router:
it ranked fourth in throughput (`0.7914`) and second in QPR (`0.0187908932`).
The 16- and 32-task/node routers were worse on both metrics. All five QPR
values were finite for every method, so finite-only and zero-as-zero rankings
were identical.

The revealed per-seed evidence rejects the V44 mechanism rather than merely
its larger thresholds. Even the 8-task router used Hiku in only about 4--27%
of active windows, yet it reduced QPR relative to FaaSRank in every seed and
reduced throughput in four of five seeds. In the easy, QPR-dominant E143 run,
the first low-density Hiku decisions produced QPR `0.0876388`, versus
`0.1426211` for frozen FaaSRank. Low-pressure Hiku switching is therefore
closed and must not be rescued by post-hoc seed subdivision.

The next defensible state-only hypothesis preserves exact FaaSRank at low
pressure and uses the already-defined load-faithful Orion proxy only after
queue density becomes high. This direction matches the paired baselines:
FaaSRank owns the QPR-dominant low-density seed, while Orion improves
throughput in the high-density seeds. A fresh cohort may compare the pure
V43 faithful-ready profile with fixed FaaSRank-low/Orion-high boundaries at
24 and 32 pending+runnable tasks/node. These are new preregistered candidates,
not a post-hoc V44 composite.

E140--E144 are permanently closed. E145--E149 were untouched reserve members:
no tape, reference, or run was created for them in V44. E120--E129 remain
sealed holdout seeds. Frozen low `orion_ocs2_borda` and high
`jiagu_current_demand` remain unchanged.

