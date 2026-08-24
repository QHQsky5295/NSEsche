# Experiment Tracker

| Run ID | Milestone | Purpose | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|
| V57-P0 | P0 | freeze paired confirmation | E210--E219 | none | MUST | DONE | unchanged V56 profiles/binary; V56 failure retained |
| V57-P1 | P1 | common tape capture | 3 loads x 10 seeds | none | MUST | DONE | 30 unique tapes; attempt 1; zero quarantine |
| V57-P2 | P2 | references/model binding | 30 refs | none | MUST | DONE | frozen FaaSRank model; 30 references; attempt 1 |
| V57-P3B | P3 | nine baselines | 270 runs | hidden | MUST | DONE | strict serial; 270/270 attempt-1 QC pass |
| V57-P3N | P3 | frozen NSESche | 30 runs | hidden | MUST | DONE | unchanged algorithm; 30/30 attempt-1 QC pass |
| V57-P4 | P4 | joint result-blind audit | 300 runs | none | MUST | DONE | 30 groups x 10 methods; metrics_consulted=false |
| V57-P5 | P5 | simultaneous reveal | all loads | throughput + two QPR | MUST | FAILED | 1/9 gates passed; low throughput rank 1 only; no retuning on E210--E219 |
