# P1-A Non-Applied Null-Gamma Validation Correction Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: second fail-before-output implementation correction; one same-command P1-A retry authorized

## 1. Failure boundary

The retry after the network-beta correction exited during Q61 structural
validation with `trace.gamma must be numeric`. The registered P1-A output root
again remained absent. No metric table, interval, or scientific result was
written.

## 2. Cause and evidence

Three Q61 windows had a positive offline reference below the current Nash
welfare. Under the anchor's control rule they correctly record
`feedback_applied=false`, `feedback_gap=null`, `gamma=null`, and
`price_multiplier_for_next_round=null`. The analyzer incorrectly required a
finite gamma on every trace row even when no price update was eligible.

The correction preserves a strict gate:

- `price_multiplier_for_current_round` and the window-level
  `pricing.network_beta` must always be finite;
- a present gamma/gap/reference/Nash value must be finite;
- an applied update requires a positive gap, finite gamma, and a next
  multiplier satisfying `1 + gamma * network_beta * gap`;
- a non-applied below-current row may retain null feedback fields and remains
  explicitly counted as ineligible/below-current rather than being discarded.

## 3. Frozen corrected identity and tests

| File | Corrected SHA-256 |
|---|---|
| `analysis/p1_retained_evidence.py` | `6d87a7148d1c70d6ab696986fae885aea75f148e8deaca47e5e71f0329345591` |
| `analysis/tests/test_p1_retained_evidence.py` | `8675f95f78c09ff8add973937d65b15b9f864ba7fe5c280a8b0f199d57a76535` |

Black, `git diff --check`, and all four P1-A tests pass. The new regression
fixture verifies that a below-current, non-applied trace with null gamma/gap/
next multiplier is accepted while remaining outside the eligible-trace
denominator.

## 4. Authorization

After commit, one retry of the unchanged P1-A population and output command is
authorized. This is the second fail-before-output parser/validator recovery;
it changes no inclusion rule, statistic, scientific threshold, or input.
