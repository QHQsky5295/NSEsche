# G7 frontier-warm development result audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Runtime source commit: `9c16366d820b824db12bb6c320e6afabd934ec8`  
Reference-audit prerequisite: `54fd50524dabf9899c780eb35d800a6dba920393`  
Analyzer correction commit: `ee5a4466ad4c03053f5078a6c414d5927cb4fa30`  
Status: development gate failed; confirmation and formal progression blocked

## Outcome

The sole preregistered G7 `lookahead_frontier1_warm_init` candidate was
executed once for each of D71--D75, in manifest order. All five first attempts
passed QC and were retained. The corrected, preregistered reporting path
returned `complete_g7_development_gate_failed`:

- `candidate_development_qualified=false`;
- `confirmation_preregistration_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

The first analyzer invocation failed before output when it encountered a
runtime-valid null reference shape. Its reporting-only correction was frozen,
tested, and committed before one retry. The retry counted, rather than
discarded, those windows and preserved the offline-reference coverage gate.
The result is a valid negative development result. It must not be repaired by
dropping a seed, substituting a run, weakening a threshold, ignoring an
unreferenced window, or rebuilding a reference after viewing the metrics.

## Frozen result product

Run root:
`runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904`

| Artifact | Hash |
|---|---|
| ready manifest canonical hash | `37f26c48f6a78779d62d42acbedd440774d716ffc6818623a196925d97b6f4ae` |
| `g7.ready.json` file SHA-256 | `4e285e025a1612480177ad1b2bcab52f4a0fe28886abca2186441cf75bd39567` |
| selection document hash | `549ce335172d0cbeae90e54951b772c097a5cc76bc02cdab56d3d47f7019a3ca` |
| `g7.selection.json` file SHA-256 | `6e465ad1e7d3156b092d83f547cefd15f4959565bd7d3f74c99f5b864ae58806` |
| `online/ledger.jsonl` file SHA-256 | `b16dc654f8070074df454e1deeb3b22b1e270d84b8661d3d0e3b5c512bb6aa81` |

The selection revalidated five candidate artifact receipts and all 50 frozen
G3 source-control artifact receipts. The ledger hash chain validates with 12
events.

## Aggregate results

| Metric | G7 candidate mean | G3 C0 mean | Frozen best baseline | Gate |
|---|---:|---:|---:|---|
| throughput (requests/ms) | 1.058000 | 1.143400 | 1.151400 (`sche_Hiku`) | fail |
| QPR | 0.021155059 | 0.024900429 | 0.040391615 (`sche_jiagu`) | fail |
| latency (ms; lower is better) | 100.1229 | 84.4634 | n/a | fail versus C0 |
| completion ratio | 0.553675 | 0.598534 | n/a | fail versus C0 |
| cost/completed request | 0.725258 | 0.644437 | n/a | secondary regression |

Relative to C0, paired mean throughput difference was -0.0854 requests/ms
(95% t interval [-0.2711, 0.1003]), paired mean QPR difference was -0.003745
([-0.01430, 0.006811]), mean latency improvement was -15.6595 ms
([-57.2718, 25.9528]), and paired completion-ratio difference was -0.044859
([-0.14242, 0.05271]). Mean solve-time ratio was 1.0445 ([0.8383, 1.2507]),
so computational overhead was not the failed constraint.

Candidate sample SD was 0.451968 for throughput, 0.0132666 for QPR,
60.0228 ms for latency, 0.236951 for completion ratio, and 0.313654 for cost
per completed request. The selection retains the five values, sample SD,
95% intervals, signs, and every leave-one-seed-out mean for all metrics.

## Per-seed paired results

| Seed | Candidate T | T/C0 | Candidate QPR | QPR/C0 | Latency improvement (ms) | Completion delta | T win | QPR win |
|---|---:|---:|---:|---:|---:|---:|---|---|
| D71 | 1.835 | 1.0498 | 0.033222 | 0.7730 | -67.558 | +0.04560 | yes | no |
| D72 | 0.853 | 0.9162 | 0.011299 | 0.6509 | -30.455 | -0.04050 | no | no |
| D73 | 0.669 | 0.7336 | 0.006178 | 0.5712 | -0.531 | -0.12816 | no | no |
| D74 | 1.007 | 1.0360 | 0.036355 | 1.4323 | +13.430 | +0.01827 | yes | yes |
| D75 | 0.926 | 0.8024 | 0.018722 | 0.6694 | +6.816 | -0.11950 | no | no |

The fixed win requirements were throughput at least 3/5, QPR at least 4/5,
and joint improvement at least 3/5. Observed counts were 2/5, 1/5, and 1/5.
D73 violated the 80% throughput floor; D71, D72, D73, and D75 violated the
80% QPR floor. Mean completion and latency also failed their C0 gates. Every
leave-one-seed-out paired throughput and QPR difference remained negative, so
the aggregate loss is not caused by one removable seed.

## Mechanism activation and integrity

The bounded-frontier implementation itself passed its activation audit in all
five seeds:

| Seed | Pre-ready share | Mean overlap (ms) | Warm-refined choices | Running-warm initial choices | Max hops | Hop violations |
|---|---:|---:|---:|---:|---:|---:|
| D71 | 0.5217 | 7.959 | 3615 | 4692 | 1 | 0 |
| D72 | 0.1171 | 7.664 | 10986 | 13183 | 1 | 0 |
| D73 | 0.4273 | 6.909 | 4810 | 7669 | 1 | 0 |
| D74 | 0.3522 | 5.322 | 3855 | 6598 | 1 | 0 |
| D75 | 0.1851 | 1.646 | 4949 | 8236 | 1 | 0 |

Completed-function reconstruction found maximum frontier depth 1 and zero hop
violations in every seed. All prepared assignments were sent, with zero
invalid assignments and zero dispatch-channel failures. Warm initialization
and startup overlap were strongly active, so the negative result is not a
dormant-mechanism artifact.

Offline-reference coverage failed exactly as retained by the corrected
analyzer:

| Seed | Active windows | Offline-table hits | Unreferenced active windows |
|---|---:|---:|---:|
| D71 | 992 | 992 | 0 |
| D72 | 988 | 981 | 7 |
| D73 | 987 | 984 | 3 |
| D74 | 993 | 991 | 2 |
| D75 | 993 | 991 | 2 |

There are 4,939 hits in 4,953 active windows and 14 exact
`reference_source=not_requested` rows. Only D71 passes per-seed coverage.

All five canonical runs have attempt number 1, `qc_pass` status, process exit
code 0, no timeout, adapter status `completed`, frozen release-binary SHA-256
`593f79671b7b8659b7df6ef2c2c240e74f409ed53c3956e4e2cfaca93e2918b7`,
and exact module-inventory restoration. There are exactly five canonical run
directories and zero files in partial/quarantine.

## Interpretation and next boundary

The one-hop predicate successfully removes G6's multi-hop cascade, but the
combined warm-start candidate does not preserve performance. The very large
warm-refined counts and strict best-response path dependence are consistent
with initialization steering the solver toward different strict equilibria;
this is a diagnosis target, not yet a causal claim. In parallel, 14 active
windows never reach the stable state at which an offline reference is
requested. These issues coexist with broad throughput, QPR, completion, cost,
and latency regressions, so fixing coverage alone cannot qualify G7.

G7 is closed and cannot enter confirmation. No Q61--Q80 or later formal cell,
figure, or paper claim is authorized from this product. Any further mechanism
work must begin with a separately preregistered, read-only diagnosis comparing
G7, G6, C0, and the earlier warm-only evidence; a new candidate would then need
a new reference identity, fresh zero-data freeze, complete development bank,
and disjoint confirmation gate.
