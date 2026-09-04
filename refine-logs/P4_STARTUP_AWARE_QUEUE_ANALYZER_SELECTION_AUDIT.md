# P4 Startup-Aware Queue Analyzer and Online-Selection Audit

Date: 2026-09-05 (Asia/Shanghai)

Parent offline-reference audit commit: `02e6da647f6844b4fd57ed28aa6d6baeb69c7823`

Status: `result_blind_selection_frozen_exact_ten_online_runs_authorized_after_commit`

## 1. Frozen analysis contract

The P4 analyzer remains the implementation committed before any P4 input,
reference, or online result. It accepts only the exact ready-manifest product:
D126--D130 in seed-major order, with `execution_ready` then `startup_aware`
within seed. It independently reopens and hash-checks the runtime, five tapes,
ten reference tables, receipts, and future canonical artifacts.

Analyzer:
`scripts/reviewer_experiments/analysis/p4_startup_aware_queue.py`

- bytes: 39,996;
- SHA-256:
  `dfde692cd303a2af4a6b30efd6a0516500aebe15178d748f1e91b447380e9aa5`;
- gate conditions: ten, conjunctive; and
- protocol/analyzer source commit:
  `dc242339790e97ef6f472edd865265adb50c75ef`.

The conditions cover exact population/identity, formula/method boundary,
mechanism activation, dual-mean viability, paired robustness, per-seed safety,
leave-one-seed-out stability, completion/latency, runtime/reference integrity,
and policy overhead. Failure of any condition closes the candidate family.
No seed, setting, run, metric, or threshold may be selected after outcomes.

## 2. Exact result-blind selection

Path:
`runs/tscv1_p4_startup_aware_queue_d126_d130_dc24233_20260905/p4_startup_aware_queue.online.selection.json`

- bytes: 7,078;
- file SHA-256:
  `f3358b0d1162b72aaf2bb89e355dab28d6cfb43437e4d1448c8c0f5556880e6c`;
- canonical object hash:
  `7c32c41af9fcf909c044f699d725d7221900ea2a82daadcb56fb0fcb645d0483`;
- ready-manifest file SHA-256:
  `835625463b598fbd4fb24242d3779013c80505bd2fa5f17478a773924a5d676a`;
- ready-manifest object hash:
  `c3db56e4ad4cd891e02b809686575942f1f896bb07f32901b442f601ab700d08`;
- ten rows, ten unique run IDs/spec hashes/reference hashes, five paired tape
  hashes, and the exact preregistered seed-major/setting-ordinal order; and
- no metric, result, observed status, candidate decision, or baseline row.

The selection builder and independent validator both passed. The target
canonical path is `online/canonical`; neither it nor its `online` parent
existed at freeze. The selection explicitly records
`online_results_present_at_freeze=false`, all-valid-run retention, technical-
retry-only handling, and no scientific-outcome retry.

## 3. Authorization boundary

After this audit is committed, exactly one full-batch execution of the ten
selected rows is authorized in the frozen order. Every first QC-valid
canonical result must be retained. Only same-run technical retries permitted
by the existing protocol may occur; outcome-dependent seed, setting, run,
tape, or reference replacement is forbidden.

Gate analysis, baseline compatibility, formal confirmation, later loads,
figures, and manuscript claims remain blocked until all ten rows are complete
and the complete retained product is independently audited.
