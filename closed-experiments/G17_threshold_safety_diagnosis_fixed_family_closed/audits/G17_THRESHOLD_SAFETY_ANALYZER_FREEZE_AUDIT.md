# G17 Threshold-Safety Analyzer Freeze Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `565334a`

Status: `analyzer_frozen_before_first_real_feature_extraction`

## Frozen implementation

- Analyzer: `scripts/reviewer_experiments/analysis/g17_threshold_safety_diagnosis.py`
- Bytes: 45,904
- SHA-256: `b3c0bcea8cc4db7bb85e3305b2e32ebdaaee9d9daaba4a63103152781c22ec71`
- Unit tests: `scripts/reviewer_experiments/analysis/tests/test_g17_threshold_safety_diagnosis.py`
- Test bytes: 12,376
- Test SHA-256: `51e59dc76a7cada644908350e6e8043bbf21e11d3e62df3d6846c6ea70cb9907`

The analyzer is fail closed and one shot. The output path and its parent must
both be absent before invocation. It binds the complete closed G16 root,
manifest, selection, gate report, ledger, G16 analyzer source, 15 canonical
candidate receipts, paired C0 metrics, and every raw candidate scheduler
window before it computes a decision.

## Result-blind verification

Before this freeze, no G17 report directory existed and no unreported G16
window feature had been extracted. Verification used synthetic fixtures only:

- focused G17 tests: 9/9 passed;
- complete analysis test suite: 181/181 passed in 81.444 seconds;
- Python compilation: passed;
- Black formatting check: passed; and
- Git whitespace check: passed.

The tests cover exact widened-integer thresholds, all five G16 admission
modes, episode reconstruction, actual dose accounting, joint-nonloss and
joint-win confusion matrices, the disclosed optimistic envelope, ordered
threshold selection, every successor condition, and failure on integrity,
all-load, and leave-one-run-out violations.

## Immutable decision boundary

The first real invocation must use:

- source root:
  `runs/tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904`;
- output:
  `runs/tscv1_g17_threshold_safety_diagnosis_g16_closed_20260904/g17.report.json`.

No analyzer, test, feature, threshold, tie-break, or condition may be edited
after that invocation. A pass can authorize only a separate preregistration
for the selected stricter current-window threshold. It cannot directly
authorize implementation, sampling, strong baselines, confirmation, or a
paper claim. A failure closes the fixed-threshold valve family.
