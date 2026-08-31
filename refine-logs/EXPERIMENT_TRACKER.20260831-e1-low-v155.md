# Experiment Tracker: E1 Homogeneous-20 Low V155

| Run ID | Milestone | Purpose | System / variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| CLN-01 | M0 | Lossless archive and disk cleanup | historical `nse_dev/tmp` | all retained history | SHA-256, CRC, bytes/files | MUST | COMPLETE | Verified archive SHA `060ad285...bf1`; receipt SHA `03a27e4e...ad2`; expanded source removed only after full content verification |
| V155-PRE | M1 | Freeze queue-gated low mechanism | `srpt_ready_hiku2_ocs_queue8` | no online data | unit and blind-audit invariants | MUST | COMPLETE | Rust source `cc4179f`; release SHA `cd91cf...7a23`; immutable JSON plan committed before orchestrator/manifest/reference/run |
| V155-REF | M2 | Build state-matched references | V155 | E01-E20 low | reference integrity | MUST | COMPLETE | 20/20 attempt-1 canonical, zero quarantine |
| V155-TRN | M2 | Complete low-load training screen | V155 | E01-E20 low | throughput, two QPR conventions, queue diagnostics | MUST | COMPLETE | 20/20 QC pass; no technical retry or selective deletion; execution receipt `b2926008...fc2c` |
| V155-DEC | M3 | Blind audit then one reveal | V155 + frozen ceilings | E01-E20 low | six fixed gates | MUST | FAILED | Blind audit `5baf5db1...68d` passed; throughput passed at 1.49915 req/ms and 12/20 wins, but QPR mean 0.0537231 remained below OCS 0.0555772; result `d13908a1...1fb0` |
| V155-CAP | M4 | Capture fresh confirmation inputs | V155/Orion/OCS | E1530-E1549 low | tape/environment hashes | MUST IF AUTHORIZED | NOT AUTHORIZED | Joint training gate failed; no confirmation input was generated or opened |
| V155-CONF | M4 | Fresh paired ceiling confirmation | V155/Orion/OCS | E1530-E1549 low | throughput, two QPR conventions | MUST IF AUTHORIZED | NOT AUTHORIZED | V155 retired unchanged before confirmation |
| V155-FRZ | M5 | Freeze publication group | publication label `NSESche` | homogeneous n20 low | catalog/table/figure hashes | MUST IF PASS | NOT AUTHORIZED | Low remains open; middle and later sections remain blocked |

## Paper-Section State

- Homogeneous 20-node high: frozen historical result retained; no rerun.
- Homogeneous 20-node low: current active paper blocker; V155 is a complete
  training-only negative result. It leads throughput but not QPR, so it is not
  a publication row and its fresh confirmation was not opened.
- Homogeneous 20-node middle: V154 negative block retained; no new run until low
  closes.
- Heterogeneous, scaling, burst, QoS, and ablation sections: no new execution
  authorized by this tracker.
