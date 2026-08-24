# Experiment Tracker

| Run ID | Milestone | Purpose | System / Variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| V54-M0 | M0 | code sanity | three structural profiles | unit fixtures | branch equality | MUST | DONE | 104/104 sche_nash tests passed |
| V54-M1 | M1 | common workload | tape capture | E190--E194 middle | input hashes | MUST | PLANNED | E195--E199 reserve stays untouched |
| V54-M2 | M2 | welfare dependency | 3 candidates x 5 seeds | E190--E194 | reference receipts | MUST | PLANNED | build only after common tape binding |
| V54-M3B | M3 | paired baselines | 9 baselines x 5 seeds | E190--E194 | QC only before reveal | MUST | PLANNED | exact frozen baselines |
| V54-M3C | M3 | candidate cohort | V54a/b/c x 5 seeds | E190--E194 | QC only before reveal | MUST | PLANNED | strict serial execution |
| V54-M4 | M4 | integrity | joint result-blind pairing | complete cohort | provenance | MUST | PLANNED | 60 runs / 5 groups required |
| V54-M5 | M5 | selection | strict winner gate | complete cohort | throughput + two QPR | MUST | PLANNED | ties or missing values fail |
