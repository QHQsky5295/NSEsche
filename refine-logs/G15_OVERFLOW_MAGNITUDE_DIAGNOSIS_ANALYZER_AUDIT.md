# G15 Overflow-Magnitude Diagnosis Analyzer Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `b0ec611c8ed51c4de8a10a72d3ff07f9ee954ade`

Status: `zero_feature_result_analyzer_frozen_single_read_only_invocation_authorized`

## 1. Result-free implementation boundary

The G15 analyzer was implemented and tested after the diagnosis questions,
four fixed thresholds, classifier, tie-break, associations, five admission
conditions, and stopping rule were committed. The real G15 output directory
does not exist. No unreported G14 first-overflow ratio, episode-level
magnitude, fixed-threshold confusion matrix, group contrast, correlation, or
leave-one-run-out diagnostic has been extracted.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `g15_overflow_magnitude_diagnosis.py` | 31,945 | `72b6762c43feeadcf25fa3f3ef5bb9ac5fb0ef14c9f22d1e71586b8996bb6a50` |
| `test_g15_overflow_magnitude_diagnosis.py` | 10,174 | `12771f8b12f04ef5e167943fb1e5a9548fdf962a007f16c1bc6fe3b7cc3a7170` |

## 2. Frozen input and reconstruction checks

Before reading outcomes, the analyzer requires the exact 1,092-file,
396,182,667-byte closed G14 root with inventory hash
`fdb9706343dd4871e49c75be0cd7a2f81f15e095b9ea7aacf65d4ba04de59b63`.
It independently checks the manifest, selection, gate-report, online-ledger,
and G14-analyzer hashes and canonical document identities. Every candidate run
is revalidated against its manifest and paired same-tape C0 row.

For every recorded G14 window, it replays the frozen valve state machine and
requires exact agreement with the closed gate report. It then reconstructs
maximal overflow episodes, first/persistent modes, feasible-ready/node ratios,
deferred counts, queue context, all eight violation totals, runtime identity,
and strict-PNE/reference coverage. The five retained inner-limit exceptions
remain explicit and are not filtered.

## 3. Frozen diagnostic and stopping rule

The complete run/seed table contains all 15 candidate/control pairs. Type-7
linear interpolation is fixed for median/p90/p95 summaries. Each ratio in
`{1.25,1.5,2,4}` is evaluated with the preregistered at-least-half classifier;
selection uses balanced accuracy, then the minimum of sensitivity/specificity,
then the smaller threshold. All confusion cells, group effects, per-load
summaries, Spearman coefficients, and 15 leave-one-run-out values are retained.

The analyzer may only authorize a later *preregistration* when exact evidence
integrity, classifier/group floors, positive dual-metric group contrasts,
complete LOO robustness, and sign-stable p90 associations with persistence and
throughput all pass. It never authorizes implementation or sampling directly.
Failure closes this mechanism path.

## 4. Verification and authorization

- focused G15 synthetic tests: 8/8 passed;
- complete analysis regression suite: 157/157 passed in 101.86 seconds;
- Python compilation and Black formatting: passed;
- G14 source-root file count at freeze: exactly 1,092; and
- G15 output parent at freeze: absent.

After this audit and analyzer are committed, exactly one read-only invocation
against the immutable G14 root is authorized. No source edit, threshold edit,
output retry, scheduler change, tape/reference construction, or online run is
authorized before the result audit.
