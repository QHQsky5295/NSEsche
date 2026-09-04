# G11 state-regime diagnosis result audit

Date: 2026-09-04 (Asia/Shanghai)

Base preregistration commit: `fba92be`

Status: `complete_g11_state_regime_path_not_admitted`

## Decision

The preregistered read-only diagnosis completed over all 45 retained G10
D96--D100 runs. The only allowed successor used a load-blind ready-player
saturation threshold. It is not admitted: the best of the four fixed
thresholds has balanced accuracy 0.55, below the frozen 0.70 requirement, and
none of its leave-one-seed-out recomputations passes. No G11 implementation,
fresh seed bank, strong-baseline addendum, confirmation, formal replay,
figure, or paper claim is authorized from this path.

This is a mechanism-evidence failure, not a technical failure. All 45 runs and
all fixed features reproduce, every C2 activation/integrity check passes, and
the prespecified saturation association is positive for throughput and QPR.
That association is too weak to classify where the frontier is jointly safe
and favorable.

## Frozen product and integrity

Input G10 remains exactly 1,527 files and 566,678,494 bytes with inventory
SHA-256
`aed84ef942171c77d6ed340b9f2cfabb062a0b57b09b8cf02111443499704ff9`.
The analyzer rechecked the frozen G10 gate-report SHA-256
`e0581b60b64382d886e219ab4b73d8f36c33f1dce5723c1f27da8607ae3a0870`
and recomputed throughput, QPR, latency, unit cost, completion, queue area,
CPU/memory utilization, stage waits, and policy time from canonical artifacts.

Run output:
`runs/tscv1_g11_state_regime_diagnosis_from_g10_20260904`.
It contains five files and 515,832 bytes with inventory SHA-256
`7b62785bcea170dc4c3d893f2558a9ddd0960e444a2a57d46b1abbddf4d3fac2`.
An exact mirror exists at
`E:/NSEsche_experiment_archives/tscv1_g11_state_regime_diagnosis_from_g10_20260904`
with the same file list, byte count, and inventory hash.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `g11.diagnosis.json` | 428,207 | `54f4d540f159f06f3fd8a7dacc6db9a5b5cda7d833766313ce11ebed65241db1` |
| `g11.run_state_features.csv` | 30,161 | `80f485df9a7c18c25d5f9ca295f62394bbe36da8eb441e395e44186557bd6e17` |
| `g11.paired_outcomes.csv` | 27,377 | `a7a7f5b0b4db01a18f9644b391c51e5acd02b4900ea16fd76b4505768752b404` |
| `g11.correlations.csv` | 29,661 | `1b738392a557157d9867270b4a703567d1253749b6b354a4be9872ec494d86d8` |
| `g11.thresholds.csv` | 426 | `0d31e9f0e6f49c5436a674076e2d3d49bbeaa9acc852e4e231a2b2b0cb384509` |

The report's stored canonical document hash is
`1eae239239def4dfb69a560a4015c1e377be9da1264ef3d428a50996fd677a67`
and independently reproduces after removing that field. Coverage is 45
run-feature rows, 30 exact candidate/C0 outcome pairs, 82 C2 features, 410 C2
feature/outcome correlations, 246 load-feature summaries, and all four fixed
thresholds. Every D96--D100 observation is retained.

## Fixed-threshold result

There are five jointly favorable C2 runs and ten unfavorable runs. The exact
classifier results are:

| Ready players / nodes | TP | TN | FP | FN | Sensitivity | Specificity | Balanced accuracy | Result |
|---:|---:|---:|---:|---:|---:|---:|---:|---|
| 1 | 3 | 5 | 5 | 2 | 0.60 | 0.50 | 0.55 | fail |
| 2 | 0 | 10 | 0 | 5 | 0.00 | 1.00 | 0.50 | fail |
| 4 | 0 | 10 | 0 | 5 | 0.00 | 1.00 | 0.50 | fail |
| 8 | 0 | 10 | 0 | 5 | 0.00 | 1.00 | 0.50 | fail |

The 1x threshold is selected by the frozen maximum-balanced-accuracy rule.
Its leave-one-seed-out balanced accuracies are 0.6250, 0.5625, 0.6250,
0.5000, and 0.4375 for omitted D96--D100; none satisfies the full frozen
sensitivity/specificity/accuracy gate. The 2x, 4x, and 8x rules classify every
run as unfavorable and remain at balanced accuracy 0.50 in every omission.

Joint favorability is also not a load-equivalent proxy: it occurs in 2/5 low,
1/5 middle, and 2/5 high runs. C2's arithmetic throughput/QPR mean ratios are
0.9852/1.0409 low, 0.9380/0.8695 middle, and 1.3224/2.8640 high. The large
high-load arithmetic gains therefore coexist with only two fully favorable
high-load seeds and cannot authorize an outcome- or load-conditioned rule.

## Coherence and interpretation

For the selected 1x saturation feature, Spearman rho is +0.2321 with paired
log-throughput and +0.3500 with paired log-QPR. The signs remain positive in
every seed omission: throughput rho ranges from +0.0979 to +0.4196 and QPR
rho from +0.2448 to +0.4196. Thus the frozen coherence condition passes.

That directional association is insufficient for a switching mechanism. The
1x rule produces five false positives and two false negatives, while higher
thresholds detect none of the favorable runs. Ready-set saturation describes
pressure but does not distinguish the queue/DAG states in which a one-hop
frontier preserves completion, latency, and both primary metrics. Selecting a
load, a favorable seed, or a post-hoc threshold would directly violate the
preregistration and would not solve this identification failure.

## Authorization boundary

The four frozen conditions are respectively pass, pass, **fail**, and pass.
Therefore:

- `g11_successor_preregistration_authorized=false`;
- `g11_implementation_authorized=false`;
- `g11_sampling_authorized=false`;
- `strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`; and
- `paper_claim_authorized=false`.

The remaining-work/frontier/ready-count family is closed. Further seed search,
threshold search, or another local ordering/frontier variant is not justified
by the retained evidence. The ordered main experiment remains blocked because
NSESche has not established the required throughput-and-QPR leadership in the
20-node homogeneous gate. Proceeding requires either a genuinely new research
contribution with an independent mechanism rationale and new preregistration,
or a manuscript claim-contract change that reports the retained rankings and
centers the response on convergence, welfare, and robustness rather than
universal dual-metric superiority.

## Verification

- Analyzer: 27,861 bytes, SHA-256
  `d98a09d3d28331218c85538510608f2df0e77471afe8d373de3858e4029ac0a9`.
- Directed G11 tests: 6/6 passed.
- Complete analysis regression after adding G11: 115/115 passed.
- Test source: 5,988 bytes, SHA-256
  `d2aee47e8562dd72120b8c671b458092e79793bdb558241a8274200ef854664e`.
- Python compilation, Black formatting check, and Git whitespace check passed.
- No simulator, workload generator, reference builder, or scheduler was run by
  G11; the G10 input inventory remains byte-for-byte unchanged.
