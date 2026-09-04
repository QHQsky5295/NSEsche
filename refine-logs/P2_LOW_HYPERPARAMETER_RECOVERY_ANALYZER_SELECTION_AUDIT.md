# P2 Low-Load Hyperparameter Analyzer and Online-Selection Audit

Date: 2026-09-05 (Asia/Shanghai)

Ready-reference commit: `ee49922e515c0076fbd05edf1b7fc5086e1c6288`

Status: `result_blind_exact_25_run_online_batch_authorized_after_commit`

## 1. Frozen result-blind contract

The analyzer was committed at `fab5df83b8040c9e4a875b1581d46aed84ae4aa7`
before any D121--D125 tape, reference, or online result existed. Its 35,201-
byte source has SHA-256
`cd67e563e1c64a7195d0c0f5c3061f11eb57fedb9297c4131e24758fee626d5f`.
It admits only the exact 25-run ready manifest and fails closed on a missing,
duplicate, reordered, cross-tape, unbound, or identity-mismatched row.

For each of the four neighbours it independently enforces all eight frozen
conditions: complete population, >=1.015/1.11 viable dual mean ratios, 3/5
joint wins and 4/5 joint nonlosses, 0.80 per-seed floors, all-nonnegative and
at-least-four-positive leave-one-out means, nondecreasing completion and <=1.05
latency ratio, runtime/reference integrity, and <=1.50 policy overhead.

The deterministic choice among all-pass neighbours maximizes the smaller of
the two primary mean ratios, then their geometric mean, then uses fixed label
order. No-pass retains the submitted centre and blocks formal confirmation.
The analyzer produces no formal result or paper figure.

## 2. Exact selection receipt

Path:
`runs/tscv1_p2_low_hyperparameter_recovery_d121_d125_f3a1e09_20260905/p2-low.online.selection.json`

- bytes: 15,703;
- file SHA-256:
  `97a8fed754a2980726e5eb6984b36f279a72fbd17cecc7b788639e4dc62586be`;
- canonical document hash:
  `d6daefea4e7a49df6a6a71285aeab461591329555748df921ae85c0cc2d482e3`;
- embedded analyzer SHA-256:
  `cd67e563e1c64a7195d0c0f5c3061f11eb57fedb9297c4131e24758fee626d5f`;
- ready-manifest object hash:
  `8e89bca4604f17ef9dc28e2e09887b6070fed971e6a560903c00cf7281320758`;
- run count: exactly 25;
- order: D121--D125, with `centre`, `r0_minus`, `r0_plus`, `wq_minus`,
  `wq_plus` inside every seed; and
- first/last identities: D121/centre and D125/wq_plus.

Every selection row binds run-spec, seed, setting, `r0`, `wq`, tape, and
offline-reference hashes. The online parent and canonical root did not exist at
freeze. The selection's stored document hash and all embedded input hashes
were reopened and revalidated.

## 3. Authorization boundary

After this audit is committed, exactly one result-blind invocation of the full
25-run online batch is authorized. All first QC-valid rows must be retained.
Technical retry is limited to the frozen crash/timeout/OOM/I/O/hash/structural-
QC reasons with the identical specification; performance is not retryable.

The analyzer may be invoked once only after all 25 canonical rows reconcile to
the selection. Formal Q81--Q100, baselines, E7 figures, manuscript claims, and
all middle/high-load work remain blocked pending the eight-condition decision.

