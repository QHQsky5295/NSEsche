# G15 First-Overflow Magnitude Diagnosis Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `b0ec611c8ed51c4de8a10a72d3ff07f9ee954ade`

Analyzer freeze commit: `583b50a6071a4b53a50cc342959ce11aa0df3952`

Status: `complete_magnitude_gated_valve_preregistration_authorized`

## 1. Closed evidence and one-shot execution

G15 is a read-only diagnosis over all 15 retained G14 candidate/control pairs
at low, middle, and high load on D106--D110. It created no workload, reference,
or online run and did not alter, omit, replace, or resample any G14 outcome.
The frozen analyzer was invoked exactly once against the immutable G14 root.

The analyzer revalidated the exact 15-pair population, bound run-spec hashes,
workload-tape hashes, audit manifests, QC reports, complete G14 activation,
candidate/control runtime identity, and zero totals for all eight mechanism
violation counters. All five preregistered admission conditions passed.

The sole output is the 592,404-byte `g15.report.json`. Its file SHA-256 is
`91732008c1d5b38cad6964643d2d061cac3634de71c2476d1893b2139c7662e5`,
and an independent canonical serialization reproduced its embedded document
SHA-256
`f7bc5405518f625612742783d27e28c9f37bc30615258041870ccb9a2b80007c`.
The output directory contains exactly this one file.

## 2. Fixed-threshold decision

The frozen candidate set was `{1.25, 1.5, 2, 4}`. A run is predicted
valve-favorable only when it has a first-overflow event and at least half of
its first-overflow windows have pre-decision feasible-ready magnitude
`F/N >= h`. Selection maximizes balanced accuracy, then the smaller of
sensitivity and specificity, then prefers the smaller threshold.

| Threshold | TP/FP/TN/FN | Balanced accuracy | Sensitivity | Specificity | Positive/negative n | Mean log-throughput contrast | Mean log-QPR contrast |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1.25 | 4/2/8/1 | 0.800 | 0.800 | 0.800 | 6/9 | +0.09715 | +0.15016 |
| 1.50 | 2/1/9/3 | 0.650 | 0.400 | 0.900 | 3/12 | -0.01092 | -0.02879 |
| 2.00 | 0/1/9/5 | 0.450 | 0.000 | 0.900 | 1/14 | -0.05849 | -0.07482 |
| 4.00 | 0/0/10/5 | 0.500 | 0.000 | 1.000 | 0/15 | undefined | undefined |

Thus `h=1.25` is the unique admissible fixed threshold. Its predicted-positive
and predicted-negative groups both span all three load levels, so the result
is not equivalent to a load label. The positive group contains four actual
joint wins and two false positives; the negative group contains eight true
negatives and one false negative.

The 15 leave-one-run-out evaluations remain on the favorable side of every
fixed robustness floor. Minimum balanced accuracy, sensitivity, and
specificity are 0.775, 0.750, and 0.7778. More importantly, the minimum
positive-minus-negative mean log effect is still +0.02506 for throughput and
+0.01495 for QPR. The selected classifier and both effect directions
therefore do not depend on retaining any single G14 run, including high-load
D110.

## 3. Observable-state association

Twelve runs contain at least one first-overflow event and therefore define a
first-overflow `F/N` p90. Across those 12 runs, its Spearman association is
0.88829 with the persistent-episode fraction and 0.30070 with the G14/C0 log
throughput ratio. The corresponding minima over every leave-one-run-out
analysis are +0.85257 and +0.09091. Both associations retain their required
positive signs.

The selected 1.25 classifier predicts favorable runs at all three loads:
low D108; middle D109; and high D106, D108, D109, and D110. It also predicts
non-favorable runs at all three loads. The two false positives are middle D109
and high D109; the sole false negative is low D110. These retained errors are
material: first-overflow magnitude is a justified development gate, not a
perfect outcome predictor.

The previously disclosed G14 strict-runtime exception remains visible. High
D108 lacks a strict PNE certificate/offline reference at active frame 979
after the unchanged inner-iteration limit. G15 neither removes nor repairs
that observation. It does not affect the fixed diagnostic admission result,
but it prevents treating this development diagnosis as formal or paper-ready
evidence.

## 4. Evidence-bounded interpretation

**Observation.** The magnitude of the pre-decision first-overflow feasible
set separates most G14 joint wins from non-wins, survives every leave-one-run
out check, and is positively associated with both persistence and throughput
benefit. The fixed 1.25 threshold is the only tested value that satisfies the
classifier, group-size, cross-load, dual-effect, and robustness gates.

**Interpretation.** G14's one-frame deferral is useful mainly when the first
overflow is material rather than merely `F=N+1`. Applying the bound to mild
overflows can explain the middle-load throughput loss, while unconditional
release on a persistent overflow remains necessary to avoid G12's repeated-
deferral pathology. This is a development hypothesis derived from complete
retained evidence, not a manuscript claim.

**Implication.** G15 authorizes only a separate preregistration for a
load-blind magnitude-gated release valve with fixed `h=1.25`. It does not
authorize implementation, sampling, confirmation, strong-baseline
comparison, formal progression, figures, or paper claims. D106--D110 are
exhausted development evidence and may not validate that successor.

## 5. Immutable archive

The complete one-file G15 output directory was copied without deletion to:

`E:\NSEsche_experiment_archives\tscv1_g15_overflow_magnitude_diagnosis_g14_closed_20260904`

Source and archive inventories match exactly: one file, 592,404 bytes, with
the file SHA-256 reported above. The C-drive source remains intact.

## 6. Authorization boundary

- `magnitude_gated_valve_preregistration_authorized=true`;
- `implementation_authorized=false`;
- `sampling_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`; and
- `paper_figure_or_claim_authorized=false`.
