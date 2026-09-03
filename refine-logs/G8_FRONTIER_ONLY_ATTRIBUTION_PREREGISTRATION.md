# G8 frontier-only retained-product attribution preregistration

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Base commit: `bb67c51754871b11d82ac22aa7ef4943efafb516`  
Status: read-only diagnosis frozen; implementation and one invocation authorized;
new candidate implementation and all sampling blocked

## Question and evidence boundary

G6 changed dependency-ready admission to unrestricted parent-scheduled
lookahead and failed. G7 simultaneously bounded lookahead to one executable
frontier hop and changed the initial feasible assignment to a running-warm
preference; it also failed. Because two operational factors differ between G6
and G7, their result contrast cannot by itself identify a causal warm effect.

This diagnosis asks only whether the retained evidence is sufficiently
consistent to justify one final, clean factorial isolation:
`lookahead_frontier1_utility_init` (G7 admission with G6/C0 strict-utility
initialization). It does not claim that warm initialization caused the G7
regression, does not select a publishable method, and cannot authorize
confirmation or formal sampling.

No simulator, offline-reference builder, model trainer, or workload generator
may run. No canonical artifact may be edited, moved, deleted, or regenerated.

## Frozen inputs

| Product | Path | Document hash | File SHA-256 |
|---|---|---|---|
| G2 ready manifest | `runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.ready.json` | `8173ab619744d7794106489c67e5ef017160c90e5bdcc4dd597be075f9bcd3f4` | `d49bc3865244f9b231b7dba312819f4c715059ca4ce7d7bb97b185add7481f18` |
| G2 analysis | `runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.analysis.json` | `e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79` | `414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db` |
| G3 ready manifest | `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.ready.json` | `c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657` | `a54f0fbbbe02d0b1559b1b094eeefe77f1860b522a6c26b9c69b03262ced02f4` |
| G3 selection | `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json` | `4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34` | `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7` |
| G6 ready manifest | `runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904/g6.ready.json` | `d5b7a2143688f618a9ef286466d0c7c7a6b92687bb5bf97dab6e28ce9ca4c1f3` | `69f34423d632fbdb1de286f9dc0ca27c1e3da24fbb629b4dc7e52614b2b96965` |
| G6 selection | `runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904/g6.selection.json` | `842a20e410c1f1a188b76d42b4398251171574241d39121b0e33630371d04592` | `6fa6446ef8a84432dee6607c8a58b3cbd02548e67aa0f22dbbbb787c2e60d3f6` |
| G7 ready manifest | `runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/g7.ready.json` | `37f26c48f6a78779d62d42acbedd440774d716ffc6818623a196925d97b6f4ae` | `4e285e025a1612480177ad1b2bcab52f4a0fe28886abca2186441cf75bd39567` |
| G7 selection | `runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/g7.selection.json` | `549ce335172d0cbeae90e54951b772c097a5cc76bc02cdab56d3d47f7019a3ca` | `6e465ad1e7d3156b092d83f547cefd15f4959565bd7d3f74c99f5b864ae58806` |

Canonical roots are the `online/canonical` directories beside these manifests.
The analyzer must validate every selected canonical run against its manifest
and audit receipt before using any scientific field.

## Exact run set and pairing

The raw table contains exactly 25 rows:

- G2 D66--D70 homogeneous-low `ready_order`: 5;
- G2 D66--D70 homogeneous-low `ready_warm_init`: 5;
- G3 D71--D75 homogeneous-low `ready_order` C0: 5;
- G6 D71--D75 `lookahead_preall_sched`: 5;
- G7 D71--D75 `lookahead_frontier1_warm_init`: 5.

The pair table contains exactly 20 rows:

- G2 warm-init minus G2 C0, paired only within D66--D70: 5;
- G6 minus G3 C0, paired by identical D71--D75 tape SHA-256: 5;
- G7 minus G3 C0, paired by identical D71--D75 tape SHA-256: 5;
- G7 minus G6, paired by identical D71--D75 tape SHA-256: 5.

G2 is directional context only. Its D66--D70 values must never be pooled,
paired, or averaged with D71--D75.

## Frozen raw metrics

Every raw row reports identifiers and receipt hashes plus:

- primary/secondary outcomes: throughput, run-level QPR, latency, completion
  ratio, and cost per completed request;
- active-window counts, assigned players, complete dispatch, assignment moves,
  inner/outer limit hits, oscillations, stable shares, and termination counts;
- active-window means for parent-blocked, resident, runnable,
  starting-resident, and data-blocked queues;
- warm initial/refined/lower-utility choices and final selected warm/starting/
  cold shares;
- offline-table hits, exact `not_requested` active windows, and other reference
  sources (which fail closed);
- completed-request/function counts, pre-ready-bound share, startup-overlap
  mean/sum, maximum unfinished-ancestor depth, and frontier violations.

Queue means use all active scheduling windows as the denominator. Function
activation uses only completed functions. Reference coverage uses all active
windows. No no-player window enters active-window rates.

For each pair and numeric metric, output the signed difference `left-right`;
positive means more of the named raw quantity. Outcome ratios are also
reported. For every contrast, report all five values, mean, sample SD, paired
95% t interval, positive/zero/negative sign counts, and all five
leave-one-seed-out means. At n=5 these statistics are descriptive diagnostics,
not confirmatory p-values.

## Frozen authorization rule

All conditions below must pass to authorize only a G8 candidate
preregistration:

### A. Frontier control is real

1. G7 has maximum unfinished-ancestor depth `<=1` and zero frontier violations
   in all 5 seeds.
2. G6 has at least one `>1`-hop completed function in at least 4/5 seeds.
3. G7 parent-blocked queue mean is below G6 in at least 4/5 seeds.
4. G7 resident queue mean is below G6 in at least 4/5 seeds.

### B. Warm-path perturbation is exposed

1. G7 has positive warm-refined and lower-utility initial choices in all 5
   seeds; G6 has zero lower-utility initial choices in all 5 seeds.
2. Mean G7 throughput and QPR are both below G6, and G7 loses each metric to
   G6 in at least 3/5 paired seeds.
3. G7 has a positive total of exact `not_requested` active windows and more
   such windows than G6 in at least one paired seed.

G2 warm-only signs and means are always reported but are not a gate, because
they use a different development bank. The rule establishes only that a clean
frontier-only ablation is warranted; it does not identify a causal warm effect.

If every A/B condition passes, status is
`complete_g8_frontier_only_preregistration_authorized`. Otherwise status is
`complete_no_g8_authorized`. In both cases:

- `g8_candidate_preregistration_authorized` is the conjunction above;
- `g8_implementation_authorized=false`;
- `new_sampling_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

## Outputs and no-overwrite rule

The initially absent output directory is:
`runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/frontier_only_attribution`.

One invocation may atomically create exactly:

- `g8_frontier_only_attribution.json`;
- `g8_frontier_only_runs.csv` (25 raw rows);
- `g8_frontier_only_pairs.csv` (20 paired rows).

The JSON must hash-bind both CSVs, all eight frozen input files, all 25
canonical run receipts, code-source receipts, definitions, conditions, raw
rows, pair rows, summaries, and the authorization decision. Existing outputs
must never be overwritten.

## Authorization boundary

Implementation, compilation, formatting, synthetic tests, and one live
source-contract dry validation are authorized. After a separate implementation
audit commit, exactly one read-only invocation is authorized on the unchanged
inputs. No G8 scheduler code, offline reference, workload tape, simulator run,
Q81--Q100 run, formal cell, figure, or paper claim is authorized by this
preregistration.
