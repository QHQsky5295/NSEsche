# G17 Threshold-Safety Diagnosis Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Preregistration commit: `565334a`

Frozen analyzer commit: `3177622`

Status: `complete_fixed_threshold_valve_family_closed`

## 1. One-shot product and integrity

The frozen analyzer was invoked exactly once over
`runs/tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904`.
It created no simulator run and wrote one report:

- path:
  `runs/tscv1_g17_threshold_safety_diagnosis_g16_closed_20260904/g17.report.json`;
- bytes: 2,204,444;
- file SHA-256:
  `01f60135b6d9f1d9f91aa06a56096661186b0d758ab777041e0641e84a3b0464`;
- document SHA-256:
  `eef43d9fe6fabedd5c99c4a3e9e43c9936ed1e1596d8109c4160bbf32078356e`.

The stored document hash independently recomputes exactly. All 15 candidate
runs, 15 distinct load/seed identities, 15 tapes, and 15 canonical artifact
receipts are present. The complete 1,092-file G16 root, all bound file and
document hashes, the 62-event ledger, and the frozen G16 analyzer identity
validated before feature extraction. Every candidate passed G16 activation
and runtime-identity reconstruction, and all nine telemetry violation totals
are zero. Therefore condition 1 passed.

The five already-retained runtime exceptions remain visible: G16 high D111
has two missing offline references and G16 high D112 has one active window
without a strict-PNE certificate and offline reference. They are not omitted,
retried, or relabeled. They do not explain the threshold-family failure.

## 2. Exact decision

Only condition 1 of the six frozen conditions passed:

| Condition | Result |
|---|---:|
| exact 15-pair activation/identity/zero-violation integrity | pass |
| selected stricter-threshold classifier and group floors | fail |
| predicted-safe dual mean-log primary effects | fail |
| all-load optimistic-envelope primary and paired floors | fail |
| all envelope LOO mean-difference robustness | fail |
| classifier and dual-effect robustness under every LOO | fail |

Accordingly:

- `stricter_threshold_successor_preregistration_eligible=false`;
- `implementation_authorized=false`;
- `sampling_authorized=false`;
- `confirmation_sampling_authorized=false`; and
- `formal_progression_authorized=false`.

No G18 threshold-valve implementation may be constructed from this result.

## 3. Threshold screens

The independent recomputation exactly reproduces the frozen lexicographic
scores and selects `h=4.0`:

| h | minimum six envelope ratios | BA | sensitivity | specificity | predicted safe |
|---:|---:|---:|---:|---:|---:|
| 1.25 | 0.995819 | 0.25 | 0.30 | 0.20 | 7 |
| 1.50 | 0.999963 | 0.45 | 0.10 | 0.80 | 2 |
| 2.00 | 1.000000 | 0.50 | 0.00 | 1.00 | 0 |
| 4.00 | 1.000000 | 0.50 | 0.00 | 1.00 | 0 |

The final tie prefers the larger threshold as preregistered. This is not a
useful policy: both `h=2` and `h=4` classify zero runs as safe and the
optimistic envelope becomes C0 identically. Hence it has no joint win and all
30 primary LOO means are exactly zero, failing the required strict-positive
counts. A threshold that disables the mechanism cannot authorize a successor.

The less-degenerate `h=1.5` screen is also inadequate. It identifies only two
safe runs across low/high, none at middle, with joint-nonloss confusion
`TP=1, FP=1, TN=4, FN=9`. Its high-load envelope QPR ratio is 0.999963, it has
no middle or high joint win, and its safe group is below all population and
robustness floors.

At the original `h=1.25`, the envelope remains below C0 for middle QPR
(0.995819), with zero middle joint wins. Low has only three joint nonlosses.
The optimistic replacement therefore cannot rescue the observed G16 pattern
even though it uses realized run outcomes in a way an online policy cannot.

## 4. Activation and dose evidence

Across all 15 G16 traces, the raw reconstruction contains:

- 1,252 first-overflow windows: 753 magnitude-bounded and 499
  below-threshold releases;
- 1,201 persistent-overflow release windows;
- 9,105 actually deferred players;
- first-overflow `F/N` from 1.05 to 4.80, with median 1.30; and
- 390/92/3 first-overflow windows at or above thresholds 1.5/2/4.

By load, actual bounded windows and deferred players are 11/205 at low,
255/2,605 at middle, and 487/6,295 at high. The most damaging run, middle
D112, has 66 bounded events and 558 deferred players, but middle D113 has a
similar 56/477 dose and is a joint win. Middle D114 has the largest middle
dose (133/1,570) yet gains throughput while losing QPR. Likewise low D111 and
D113 have comparable small bounded-event counts but opposite QPR directions.
Magnitude or scalar accumulated dose alone therefore does not separate safe
from unsafe runs.

The fixed first-event budgets retain 11/41/139/473 bounded events and
124/575/1,897/5,308 deferred players for budgets 1/4/16/64, respectively.
These are trace-coverage counts only. They do not estimate performance after
changing state and cannot authorize a budget or cooldown mechanism.

## 5. Interpretation and stopping rule

The positive high-load association between the amount of activation and
throughput is driven mainly by between-load regime differences; among the 11
activated runs, the Spearman association between bounded-window count and
log-throughput ratio is only 0.0182, and that between deferred-player total
and log-throughput ratio is -0.0545. Thus neither a stricter fixed magnitude
threshold nor a scalar run-level dose rule has stable retained support.

G17 is explanatory negative evidence, not a paper result. The fixed-threshold
valve family is permanently closed. Reusing D111--D115 to tune another
threshold, selecting only favorable seeds, omitting exact ties, or presenting
the noncausal envelope as measured performance is prohibited. Any distinct
future mechanism would require its own result-free rationale and
preregistration; G17 itself authorizes none.
