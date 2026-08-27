# E3/E4 experiment tracker

| Run ID | Paper step | Scope | Priority | Status | Closure rule |
|---|---|---|---|---|---|
| E3E4-M0 | Static preflight | 400-run shard, E1 SLA template, frozen model | MUST | DONE | manifest 66abe3f9... and all pinned hashes pass |
| E3E4-M1 | Prepare formal inputs | 10 base tapes, 30 bursts, 6 pilots, 40 refs | MUST | TODO | ready manifest passes every result-blind gate |
| E3E4-M2 | Freeze baselines | 9 methods x 40 cells = 360 formal runs | MUST | TODO | complete QC/pairing then immutable simultaneous reveal |
| E3E4-M3 | NSESche development | fresh nonpublication cohort | MUST | BLOCKED_BY_M2 | versioned plan freezes candidates/seeds before execution |
| E3E4-M4 | NSESche formal confirmation | 40 E01--E10 runs | MUST | BLOCKED_BY_M3 | first throughput and both QPR means; recovery/QoS reported |
| E3E4-M5 | Paper analysis | E3 recovery + E4 QoS/fairness | MUST | BLOCKED_BY_M4 | exact 400-run bundle, pairing, figures, data table |

Frozen and never rerun: E1 homogeneous/heterogeneous final catalogs and the
NSESche-only 20/100/500 resource-scaling bundle. V78/V86 remain archived failed
overlay confirmations and are not prerequisites for E3/E4.
