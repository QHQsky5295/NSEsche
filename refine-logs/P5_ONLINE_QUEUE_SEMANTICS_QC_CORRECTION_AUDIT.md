# P5 online queue-semantics QC correction audit

Date: 2026-09-05 (Asia/Shanghai)

Parent preregistration commit: `d5cb4f60054d03769ad179d37517d2c98bc47507`

Correction implementation commit: `dfdf87e288e961da849b2069a6ef076b46e1f046`

Status: `qc_correction_audited_same_run_attempt_three_authorized_after_commit`

## 1. Correction boundary

The implementation changes only the expected `queue_semantics` label in the
generic NSE summary validator:

- a P5 dynamic reviewer-v4 run requires
  `external_fcfs_bounded_active_dag_plus_node_task_queue`;
- every non-P5 run continues to require `unbounded_wait_by_design`; and
- both branches continue to reject nonzero drops, rejections, or timeouts.

No simulator, scheduler, paper equation, manifest, selection, tape, reference,
model, seed, admission, active-limit, horizon, drain, metric, or performance
threshold changed. In particular, the frozen manifest's rule that scientific
zero or low completion is QC-valid is preserved.

Implementation identities:

- `scripts/reviewer_experiments/protocol/qc.py`: 169,959 bytes, SHA-256
  `3897b8b26fa6e8f337d184c28f3643c7004c0156defe06120195b22d6f5c4730`;
- `scripts/reviewer_experiments/protocol/tests/test_p5_common_platform.py`:
  11,733 bytes, SHA-256
  `a7f0394841cb499ce2839e3bf34f5160f462aff94068d7b2762a57ed01fa954b`.

## 2. Validation

- directed P5 plus generic protocol tests: 49/49 pass in 260.035 s;
- complete protocol suite: 289/289 pass in 754.999 s;
- complete analysis suite: 223/223 pass in 82.270 s;
- post-format focused semantics tests: 2/2 pass in 1.503 s;
- Black check, Python compilation, and `git diff --check` pass; and
- a P5 summary using the legacy label fails closed, while a P5 summary using
  the frozen v4 label with a nonzero drop still fails closed.

The corrected validator was applied read-only to both retained summaries. Both
returned an empty issue list without modifying either artifact.

## 3. Retained failed-attempt evidence

Online workspace:
`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/online`

Run:
`TSCv1.E1.homogeneous.n20.low.greedy.FP5P01.1ce7b703`

- canonical count: 0;
- quarantined attempt count: 2;
- attempt-01 summary: 6,064 bytes, SHA-256
  `bd2a0c30726b231aa1bca30717f5c0efdac7e78a43a7970ce1e5142bef79c828`;
- attempt-02 summary: 6,066 bytes, SHA-256
  `d9eeb1c68894ef504fb17f54bb03734d0a8ceede4f8a552bcc4026447870ad0a`;
- ledger: seven events, 5,458 bytes, file SHA-256
  `cec78c674abf5262a83146fac29c7e89635fe9e8360150d918f4c68117c4b5fe`;
  and
- ledger tip:
  `e110db0939b4ec7d0757407f7dd017ca57c08be29fbc6f450d865074bfd34b09`.

The two attempts remain quarantined and cannot be promoted or substituted.

## 4. Frozen inputs remain identical

- ready manifest: 2,770,804 bytes, SHA-256
  `7f9720e9dc7aa8dfe00d96e00c4d8deee8df6863d0c914d2490f51d625353d19`;
- result-blind selection: 50,808 bytes, SHA-256
  `e70dd418a48c8c5e21f2cc047dec9182ea4834442e337b8fd3aefeec89e90d8f`;
  and
- runtime binary: 5,013,504 bytes, SHA-256
  `945e0deca86466f9ef322bba25c779f5240d45d7e376c740ed54d240688262d8`.

## 5. Authorization boundary

After this audit is committed, only the exact same first selected run may use
its remaining attempt 3. If attempt 3 is QC-valid, it becomes the first
canonical result and the other 89 selection rows are authorized in their
existing order. If attempt 3 is not QC-valid, P5 remains blocked. No seed,
method, parameter, runtime, input, reference, or result-conditioned replacement
is authorized.
