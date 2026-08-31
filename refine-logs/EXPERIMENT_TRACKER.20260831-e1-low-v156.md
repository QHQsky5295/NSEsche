# Experiment Tracker: E1 Homogeneous-20 Low V156

| Run ID | Paper milestone | Evidence | Status | Closure implication |
|---|---|---|---|---|
| V155-FRZ | Retain prior low-load evidence | 20/20 valid; throughput 1.49915 > Orion 1.47410; QPR 0.0537231 < OCS 0.0555772 | COMPLETE / NOT CLOSED | V155 remains immutable training evidence; no confirmation opened |
| V156-PLAN | Freeze single-change diagnostic | E09/E18/E20, pipeline frontier only, fixed hybrid gates | COMPLETE | Authorizes implementation and exactly 3 diagnostic runs |
| V156-IMP | Implement and verify profile | enum/parser/frontier/order/scoring/telemetry tests; independent binary receipt | PENDING | No run until all result-blind contracts pass |
| V156-REF | Build state-matched references | E09/E18/E20 only | PENDING | 3/3 required; no baseline reference rebuild |
| V156-RUN | Execute diagnostic | 3 NSESche runs, fixed order, all valid retained | PENDING | No additional seed before sealed audit and reveal |
| V156-BLIND | Seal mechanism/provenance audit | exact frontier, route, identity, QC, reference pairing; no performance read | PENDING | Failure retires V156 |
| V156-DEC | Apply frozen hybrid replacement gate | 20-seed hybrid throughput/QPR means and paired wins | PENDING | Pass opens a new 17-seed training plan; fail retires V156 |
| LOW-CONF | Fresh E1530-E1549 confirmation | NSESche/Orion/OCS paired block | NOT AUTHORIZED | Requires complete V156 E01-E20 training pass first |
| LOW-FRZ | Freeze E1 homogeneous low publication result | catalog, table, figure, hashes | NOT AUTHORIZED | Low closes only after fresh confirmation |

## Paper-section state

- **Homogeneous 20-node low**: current blocker; not closed.
- **Homogeneous 20-node middle/high**: prior frozen evidence retained; no new
  run while low is open.
- **Heterogeneous, scaling, burst, QoS, ablation**: no new execution authorized.
