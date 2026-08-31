# Experiment Tracker: E1 Homogeneous-20 Low V155

| Run ID | Milestone | Purpose | System / variant | Split | Metrics | Priority | Status | Notes |
|---|---|---|---|---|---|---|---|---|
| CLN-01 | M0 | Lossless archive and disk cleanup | historical `nse_dev/tmp` | all retained history | SHA-256, CRC, bytes/files | MUST | COMPLETE | Verified archive SHA `060ad285...bf1`; receipt SHA `03a27e4e...ad2`; expanded source removed only after full content verification |
| V155-PRE | M1 | Freeze queue-gated low mechanism | `srpt_ready_hiku2_ocs_queue8` | no online data | unit and blind-audit invariants | MUST | RUNNING | Rust source `cc4179f`; release SHA `cd91cf...7a23`; immutable JSON plan committed before orchestrator/manifest/reference/run |
| V155-REF | M2 | Build state-matched references | V155 | E01-E20 low | reference integrity | MUST | BLOCKED | Waits for CLN-01 and V155-PRE |
| V155-TRN | M2 | Complete low-load training screen | V155 | E01-E20 low | throughput, two QPR conventions, queue diagnostics | MUST | BLOCKED | 20/20, no selective deletion |
| V155-DEC | M3 | Blind audit then one reveal | V155 + frozen ceilings | E01-E20 low | six fixed gates | MUST | BLOCKED | Pass alone authorizes confirmation |
| V155-CAP | M4 | Capture fresh confirmation inputs | V155/Orion/OCS | E1530-E1549 low | tape/environment hashes | MUST IF AUTHORIZED | BLOCKED | Inputs remain unopened until training pass |
| V155-CONF | M4 | Fresh paired ceiling confirmation | V155/Orion/OCS | E1530-E1549 low | throughput, two QPR conventions | MUST IF AUTHORIZED | BLOCKED | Exact 3 x 20 product |
| V155-FRZ | M5 | Freeze publication group | publication label `NSESche` | homogeneous n20 low | catalog/table/figure hashes | MUST IF PASS | BLOCKED | Middle remains blocked until complete |

## Paper-Section State

- Homogeneous 20-node high: frozen historical result retained; no rerun.
- Homogeneous 20-node low: current active paper blocker; V155 planned, not run.
- Homogeneous 20-node middle: V154 negative block retained; no new run until low
  closes.
- Heterogeneous, scaling, burst, QoS, and ablation sections: no new execution
  authorized by this tracker.
