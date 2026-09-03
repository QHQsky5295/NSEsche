# Post-G8 claim/scene feasibility result audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Analyzer audit commit: `cbad69d`  
Status: `complete_no_existing_candidate_confirmation_supported`

## Integrity and outputs

The single authorized invocation completed with exit code 0 over the exact
frozen products: 270 G2/G3 development rows and 200 formal Q61--Q80 rows. It
created 36 candidate-cell summaries, 36 same-bank homogeneous-low candidate/
baseline pairs, and ten formal method summaries. No simulator, reference
builder, workload generator, or scheduler ran.

| Product | Rows | SHA-256 |
|---|---:|---|
| `post_g8_claim_scene_feasibility.json` | n/a | `bc0fc84d5306cfe3ed29c282f87bf00f99dec85effb628bb74f26d3f1924369a` |
| `post_g8_candidate_cells.csv` | 36 | `1c2ea68fcbabffbe96e1f7270b118bce8a4a2548c9d8a11d7bdbd029e8120890` |
| `post_g8_hom_low_baseline_pairs.csv` | 36 | `dfc72e0a73af49fcb4662c583b33d3185b38e4de24f40cc82c2e8d86715447df` |
| `post_g8_formal_hom_low.csv` | 10 | `57b315313983c4c0268343358c60a9d4ee3eb1e01a718e6b699f546e16d2e416` |

The JSON document hash is
`425b073ec0b159960d2b210175c461b60846dbcfb6e2c95102c96a49bd5ced03`;
it reproduces after removing the stored field. All eight input receipts, source
receipt, definitions, decision rows, and three CSV hashes are bound.

## Existing-candidate gate

No noncontrol candidate passed. In fact, every candidate passed only the
retained-product integrity condition and failed the other five fixed
conditions.

| Family / candidate | Dual-improvement cells | Mean T/QPR relative ratio | Worst ratio | Result |
|---|---:|---:|---:|---|
| G2 `ready_warm_init` | 4/6 | 1.087448 | 0.857376 | fail |
| G2 `ready_finish_init` | 2/6 | 1.005392 | 0.481038 | fail |
| G3 `ready_pne_envelope_first` | 1/6 | 1.009453 | 0.762448 | fail |
| G3 `ready_pne_envelope_each` | 1/6 | 1.000611 | 0.737156 | fail |

`ready_warm_init` is the strongest exploratory candidate but still misses the
5/6 consistency rule, the 90% floor, homogeneous-low dual leadership, near-
leader paired wins, and all-positive leave-one-out margins. Its cell behavior
is heterogeneous: relative to its own C0 it has T/QPR ratios 1.0267/1.0314 in
homogeneous-low and 1.1854/1.5997 in heterogeneous-high, but only
0.8574/1.0437 in heterogeneous-middle. This is useful mechanism evidence, not
a basis for a general method claim or confirmation bank.

The G3 envelope candidates likewise produce isolated QPR gains alongside
large throughput or QPR losses. No aggregation or scene selection can convert
those incomplete patterns into a globally superior algorithm.

## Formal claim label

In the complete 20-seed, ten-method homogeneous-low product, NSESche is rank 3
for throughput and rank 4 for QPR:

- throughput 1.5815 req/ms versus FaaSRank 1.5981, margin -0.0166 (-1.04%);
  paired 95% descriptive interval [-0.09683, 0.06363], with 9 wins, 1 tie,
  and 10 losses;
- QPR 0.0581071 versus FaaSRank 0.0640394, margin -0.0059323 (-9.26%);
  paired 95% descriptive interval [-0.0105011, -0.0013635], with 4 wins and
  16 losses.

Because the QPR interval is entirely below zero, the frozen label is
`not_leading`, not `not_leading_interval_compatible`. NSESche's lower mean
cost per completion (0.533315 versus FaaSRank 0.541000) does not reverse either
primary ranking. The other five 20-node load/topology scenes remain
`unmeasured_against_all_baselines`; development candidate-to-C0 rows cannot be
used as substitute all-method evidence.

## Interpretation and next action

The accumulated evidence does not support the premise that an already tested
formula-consistent operational variant is ready to make throughput and QPR
both best. It also does not support spending a fresh bank merely to hope that
G2 warm initialization reverses the ranking. Result-conditioned scene or seed
selection would be especially visible because the worst-cell ratios and
leave-one-out failures are now audit-bound.

Therefore:

- `existing_candidate_confirmation_preregistration_supported=false`;
- `new_candidate_implementation_authorized=false`;
- `new_sampling_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

The scientifically defensible route is to freeze the paper-faithful
`ready_order` semantics, remove universal throughput/QPR-superiority claims,
and make equilibrium/convergence/welfare validation the central reviewer
response while reporting performance ranks transparently. A V4 plan must
place a manuscript claim contract and low-cost reuse/exact-PoA checks before
any additional large online matrix. If universal dual-metric leadership is a
non-negotiable submission requirement, this project is blocked on a genuinely
new research contribution rather than more reruns of the existing candidates.
