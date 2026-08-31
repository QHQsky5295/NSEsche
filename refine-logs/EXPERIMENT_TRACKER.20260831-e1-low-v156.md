# Experiment Tracker: E1 Homogeneous-20 Low V156

| Run ID | Paper milestone | Evidence | Status | Closure implication |
|---|---|---|---|---|
| V155-FRZ | Retain prior low-load evidence | 20/20 valid; throughput 1.49915 > Orion 1.47410; QPR 0.0537231 < OCS 0.0555772 | COMPLETE / NOT CLOSED | V155 remains immutable training evidence; no confirmation opened |
| V156-PLAN | Freeze single-change diagnostic | E09/E18/E20, pipeline frontier only, fixed hybrid gates | COMPLETE | Authorizes implementation and exactly 3 diagnostic runs |
| V156-IMP | Implement and verify profile | source `182a202`; 279/279 scheduler tests; release SHA `b68c2ee0...aa18`; V155/V156 frontier and scoring contracts pass | COMPLETE | Authorizes exactly 3 references and 3 diagnostic runs |
| V156-REF | Build state-matched references | E09/E18/E20 only; 3/3 attempt-1 canonical | COMPLETE | No baseline reference rebuilt |
| V156-RUN | Execute diagnostic | 3/3 QC-pass, fixed order, all valid retained | COMPLETE | No additional seed was run |
| V156-BLIND | Seal mechanism/provenance audit | 3,000 windows; 10,522 pipeline-ahead players; both routes; zero performance read | COMPLETE / PASS | Reveal authorized |
| V156-DEC | Apply frozen hybrid replacement gate | T mean 1.4772; QPR .0560685; throughput wins 11/20 < 12/20 | COMPLETE / FAILED | V156 retired; no remaining-17 run |
| LOW-CONF | Fresh E1530-E1549 confirmation | NSESche/Orion/OCS paired block | NOT AUTHORIZED | Requires complete V156 E01-E20 training pass first |
| LOW-FRZ | Freeze E1 homogeneous low publication result | catalog, table, figure, hashes | NOT AUTHORIZED | Low closes only after fresh confirmation |

## Paper-section state

- **Homogeneous 20-node low**: current blocker; V156 failed and V157 is next.
- **Homogeneous 20-node middle/high**: prior frozen evidence retained; no new
  run while low is open.
- **Heterogeneous, scaling, burst, QoS, ablation**: no new execution authorized.
