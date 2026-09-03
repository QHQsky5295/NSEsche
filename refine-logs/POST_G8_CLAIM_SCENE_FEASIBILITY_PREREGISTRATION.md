# Post-G8 claim/scene feasibility audit preregistration

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Base commit: `66e3e95`  
Status: retained-product audit authorized; all implementation and sampling blocked

## Purpose

P1.1 ended with `complete_no_g8_authorized`, so the lookahead family is closed.
Before rewriting the experiment roadmap, this audit asks two bounded questions:

1. Does any already tested, equation-preserving operational candidate have
   enough complete retained evidence to justify a fresh confirmation bank?
2. If not, what is the strongest result-faithful performance wording and scene
   scope available to a paper-faithful `ready_order` revision?

The audit is not a new candidate search and cannot resurrect G6/G7, choose
seeds, or authorize experiments. It prevents the next roadmap from assuming a
performance-superior algorithm that the retained evidence does not support.

## Frozen inputs

| Input | Path | Binding |
|---|---|---|
| Formal Q61--Q80 cell report | `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/online/homogeneous-low/homogeneous-low.cell-report.json` | file SHA-256 `98558269dc6303f9245479f1a4aaa02d40ad0f727c3db491780558a0802f8073`; document SHA-256 `10dada54be25f19efa647d5c46bf5f7bf6528f12a6f55f33e02349d2ffa7f709` |
| G1 result audit | `refine-logs/G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md` | SHA-256 `9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16` |
| G2 initialization analysis | `runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.analysis.json` | file SHA-256 `414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db`; document SHA-256 `e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79` |
| G3 operational analysis | `runs/tscv1_g3_e0_operational_d71_d75_93b572d_20260903/g3_e0.selection.json` | file SHA-256 `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`; document SHA-256 `4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34` |
| G8 attribution | `runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/frontier_only_attribution/g8_frontier_only_attribution.json` | file SHA-256 `a95860a5e4ca3ee3a087bd0067c160ff1e955ac76af9065b6a23548aa44905c7`; document SHA-256 `d43bf3e4ce1e603211a20ddd94a38850258a87d69a2e1100e0809b84e67180fb` |
| G8 result audit | `refine-logs/G8_FRONTIER_ONLY_ATTRIBUTION_RESULT_AUDIT.md` | SHA-256 `9a411c6186cb60e3c52f21358d3e4d42a01639bc8e7f4f01a13607df2cfa66fa` |
| B0 scene/protocol audit | `refine-logs/B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md` | SHA-256 `c4a528e0a9347d59c98531c8c89556cabe0b4874b3c547a94eb1256e232c95bc` |
| Legacy-result provenance audit | `refine-logs/LEGACY_RESULT_PROVENANCE_AUDIT.md` | SHA-256 `71619733d1b2eac94e66b84e5bf33396e745d876fe88d8e010b8e417d83f42f9` |

No canonical stream beyond the rows already embedded in the validated G1/G2/G3/G8
products is needed. Each JSON document hash and file hash must be revalidated.

## Fixed candidate and scene matrix

The only reusable candidate families are:

- G2: `ready_order`, `ready_warm_init`, `ready_finish_init`, six development
  cells, five D66--D70 seeds each;
- G3: `ready_order`, `ready_pne_envelope_first`,
  `ready_pne_envelope_each`, six development cells, five D71--D75 seeds each.

G6 and G7 are reported as closed negative evidence and are ineligible for
selection. No cross-bank pair or pooled mean is permitted. The only complete
ten-method formal scene is Q61--Q80 homogeneous-low `ready_order`; the other
five 20-node scenes have candidate-versus-control development evidence but no
current-protocol all-baseline result and must be labelled as such.

For every family/candidate/load/topology, report all five run values, mean,
sample SD, candidate-minus-own-C0 paired values, 95% descriptive paired-t
interval, sign counts, and all leave-one-seed-out means for throughput, QPR,
latency, completion, and cost. For homogeneous-low, report all nine same-bank
baseline margins and paired win/tie/loss counts. Separately reproduce all ten
Q61--Q80 formal means, ranks, NSESche-to-leader margins, and paired uncertainty
from the frozen formal product.

## Existing-candidate confirmation gate

An already tested noncontrol candidate is eligible only if all conditions hold
within one family, without borrowing evidence from another seed bank:

1. homogeneous-low mean throughput and mean QPR are both strictly above all
   nine same-bank baselines;
2. it improves on its own C0 in both mean throughput and mean QPR in at least
   five of six development cells;
3. homogeneous-low paired wins are at least 3/5 for throughput, 4/5 for QPR,
   and 3/5 jointly against every baseline that is within 5% of either leading
   mean;
4. no cell has mean throughput or QPR below 90% of its C0;
5. all five leave-one-seed-out homogeneous-low throughput and QPR margins to
   the best baseline remain positive;
6. the candidate's retained analysis has complete QC/reference/dispatch
   coverage and no previously failed integrity condition.

If exactly one candidate passes, the audit may set
`existing_candidate_confirmation_preregistration_supported=true` and name it.
If more than one passes, apply the already frozen within-family score/tie-break,
then prefer the simpler operational change. If none passes, no existing or new
candidate is authorized and there is no further local mechanism search.

## Claim and scene labels

The audit uses result descriptions, not outcome-engineered success thresholds:

- `dual_metric_superiority`: NSESche is rank 1 in both primary formal means;
- `single_metric_leading`: rank 1 in exactly one primary formal mean;
- `not_leading_interval_compatible`: not rank 1, but the paired 95% descriptive
  interval against the leader includes zero for both primary metrics;
- `not_leading`: all remaining complete formal outcomes;
- `unmeasured_against_all_baselines`: any scene lacking a complete current-
  protocol all-baseline matrix.

These labels limit manuscript wording; they do not authorize selective figures.
Old-PDF values are reported only as provenance/alignment anchors. Because B0
already classified the legacy protocol as unidentifiable, no old number may be
used as a baseline for candidate selection or as evidence that new output is
wrong.

## Outputs and authorization boundary

After analyzer/test audit, one invocation may create a no-overwrite directory
with exactly:

- `post_g8_claim_scene_feasibility.json`;
- `post_g8_candidate_cells.csv`;
- `post_g8_hom_low_baseline_pairs.csv`;
- `post_g8_formal_hom_low.csv`.

The JSON must bind all inputs, output CSVs, source receipts, raw/paired rows,
decision conditions, and wording labels. Regardless of result:

- `new_candidate_implementation_authorized=false`;
- `new_sampling_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`.

Only a result audit and a V4 roadmap may follow. V4 must either preregister a
passing existing candidate on genuinely fresh seeds or freeze a paper-faithful
claim-reduction path; it cannot weaken this gate after exposure.
