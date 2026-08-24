# NSESche operational development handoff V54

V54 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E190--E194 cohort. E195--E199 remained
uncaptured reserve, and sealed confirmation seeds E120--E129 remain unused.

## Provenance and gates

- plan/runtime commit: `06fe2e7cfbec9f3cc7ff4e8adaf0e79fd7b75259`
- plan SHA-256: `b0e33bd9e0b9d350876027dde948705328d53eb77cb5c83f96bf55650a8857d3`
- scheduler code commit: `e0cf2892b36b65762fcc50727ede9e5d74509a4e`
- scheduler source SHA-256: `121acbb4fa4ffb6d099427be2f376079ba2d2c914c99e1aad24c6b16abf4778a`
- release binary SHA-256: `c46bad15a01bcf2f1d62419b268acb1a2b0490268d1e3aec2ec919724a788512`
- result-blind joint pairing SHA-256: `009a17cde2c4c85c219d5fbe927a3db48279c6451185c7c986a4034cbbdec944`
- result-blind audit hash: `e48b404ae68dc91deb8143f1f454ad00b496544e4460ae65186ec76096a6d863`
- result: `tmp/nse_operational_dev_20260825_v54/paired-screen.v54-middle.json`
- result SHA-256: `1710b85594c6f1ece6425e28c744866d9892f75e8c04bae04bac516926e6b72b`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. All ledgers passed, quarantine was empty,
and no canonical directory repair was needed. The joint result-blind audit
verified 60 runs in five complete 12-method groups with common tape, HPA,
simulation, binary, Python, Cargo.lock, and runtime identities before metrics
were read.

## Revealed result

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V54a mature+sparse+idle | 1.6806 | 3 | 0.107273243 | 7 | no |
| V54b delete idle | 1.6898 | 2 | 0.110576498 | 4 | no |
| V54c delete maturity | 1.5566 | 7 | 0.126633674 | 1 | no |

Jiagu led throughput at `1.6956`; V54b trailed by about `0.34%`. V54c led
both QPR definitions, exceeding LoadLeast (`0.123788497`) by about `2.30%`,
but lost substantial throughput. All five QPR values were finite. Therefore
`selection=none` and `freeze_middle=false`. The conjunction of narrow
frontier, cluster maturity, and idle-warm feasibility is not sufficient for
joint closure and is closed without threshold tuning.

## Mechanistic next step

The revealed per-seed results isolate a distinct capacity-coverage question.
V54b was already stronger than Jiagu in E190, E191, and E193 throughput, while
V54c's QPR gain was concentrated in E192. Under V54b, the player-weighted
share of windows where pending-plus-runnable work did not exceed the number of
running containers was `0.097`, `0.529`, `0.825`, `0.152`, and `0.063` for
E190--E194 respectively. This current-state relation separates the beneficial
light-capacity regime from E190 without introducing another fitted numeric
threshold.

A future V55 may retain V54b's narrow-mature Hiku branch and add an idle-warm
Hiku branch only when the current runnable queue is covered by current running
containers. The full rule is the union of those two state-semantic premises;
deletion controls should remove the capacity-coverage guard or remove the
narrow-mature branch. This tests whether idle-worker placement is safe only
under service-capacity coverage. It must not use completed-request, latency,
cost, seed, workload-label, or post-hoc outcome feedback.

Any V55 execution must use a newly committed plan, untouched E195--E199, all
nine paired baselines, simultaneous reveal, and the same strict throughput
plus two-QPR gate. Low remains frozen as `orion_ocs2_borda`, high remains
frozen as `jiagu_current_demand`, and E120--E129 remain sealed.
