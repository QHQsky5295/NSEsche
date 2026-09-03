# P1-A Eq. (19) Network-Beta Validation Correction Audit

Date: 2026-09-04 (Asia/Shanghai)

Status: fail-before-output implementation correction; one P1-A retry authorized

## 1. Failure boundary

The first authorized P1-A command exited during structural validation on Q61
with `Eqs. (19)-(20) mismatch`. The registered output directory
`runs/tscv1_p1_retained_evidence_98f822c_20260904/` did not exist after the
failure. Consequently no retained metric table, confidence interval, or
scientific result was exposed and no result-conditioned decision was possible.

## 2. Cause

The analyzer checked the next-round multiplier as
`1 + gamma * gap`. The anchor implements Eq. (19)--(20) as
`1 + gamma * network_beta * gap`, where the trace's `gamma` is the load-scaled
price-feedback factor and `pricing.network_beta` is the separately logged
network term. A read-only scan of Q61 found 14 applied-feedback records where
the omitted beta made the validator reject a valid trace. This was an analyzer
contract error, not a simulator or data failure.

## 3. Correction and frozen identity

The validator now requires a finite logged `pricing.network_beta` and includes
it in the multiplier recomputation. It still fails closed on malformed Eq. (16)
gaps and applied feedback without a positive gap. The evidence receipt now
records the analyzer's own source hash.

| File | Corrected SHA-256 |
|---|---|
| `analysis/p1_retained_evidence.py` | `d1c51003e9e0ba90c2ed9f5e09142c7a2cb1c3132d58eef0e2afe5ee055ceb25` |
| `analysis/tests/test_p1_retained_evidence.py` | `e3292892e3150f7a8d8f6a9ee2113064cd07339121d8d457498d858b4cfc3806` |

Black, `git diff --check`, and all three P1-A tests pass. The added regression
fixture uses `network_beta=1.5` and verifies the full multiplier identity.

## 4. Authorization

After committing this correction audit and code, one retry of the same P1-A
command is authorized. It is a fail-before-output recovery under the frozen
population and definitions, not an additional analysis or an opportunity to
change seeds, metrics, or thresholds.
