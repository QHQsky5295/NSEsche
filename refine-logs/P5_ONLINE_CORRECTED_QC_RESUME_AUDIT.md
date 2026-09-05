# P5 corrected-QC resume-control audit

Date: 2026-09-05 (Asia/Shanghai)

Parent preregistration commit: `74ac0ba543da53b3f371098fa3ef7b3d108bb4f0`

Implementation commit: `3fb43c5dcad75589313b64774583e479179adcd1`

Status: `audited_explicit_same_run_attempt_three_authorized_after_commit`

## 1. Implemented control

The ordinary runner's repeated-signature lock is unchanged. The new explicit
resume path requires one exact run ID, the retained 64-hex failure signature,
and a correction-audit file. It forbids method/experiment filters and command
overrides. Under the workspace lock and before launch it verifies:

- the three-attempt maximum and exact used set `{1,2}`;
- absence of canonical and live partial attempts;
- the repeated signature derived from the retained reports;
- exactly one stored issue, `queue_semantics_mismatch`, in each report;
- run/spec/seed/tape/reference/config/result/process identities for both
  attempts;
- exit zero and no timeout for both attempts; and
- read-only current-QC pass for both retained artifact trees.

It then appends `corrected_qc_resume_authorized`, binding both attempts, the
current QC source, the correction audit, the failure signature, and next
attempt 3. It does not rewrite, promote, or delete any prior artifact and does
not reset the attempt budget.

## 2. Implementation identities

- `scripts/reviewer_experiments/protocol/runner.py`: 168,356 bytes, SHA-256
  `2a966cc63d6fe8b141aa61fdf136762bd7a8825f8e4e5f95ce8c6543caa97295`;
- `scripts/reviewer_experiments/protocol/cli.py`: 90,120 bytes, SHA-256
  `49d73c9588f43f049542bc10d8944be93fc3113fd618422e804e9f8a97a41d7c`;
- `scripts/reviewer_experiments/protocol/tests/test_protocol.py`: 110,509
  bytes, SHA-256
  `e1a62e9d4bd75bd567016b2e0bd8c3f2ceadd1ffc018d364d7f66936905198eb`;
  and
- queue-semantics QC source: SHA-256
  `3897b8b26fa6e8f337d184c28f3643c7004c0156defe06120195b22d6f5c4730`.

## 3. Validation

- three directed resume/lock tests pass in 29.415 s;
- ordinary repeated-signature blocking remains unchanged;
- explicit recovery canonicalizes only attempt 3 in the positive fixture;
- incorrect signature, result-artifact drift, stored issue-set drift, and
  filtered selection all fail closed;
- complete protocol suite: 291/291 pass in 793.363 s;
- complete analysis suite: 223/223 pass in 81.176 s; and
- Black, Python compilation, `git diff --check`, CLI help, and ledger
  verification pass.

## 4. Real-workspace dry validation

The real P5 workspace was validated through the new control without appending
an event or launching a process. The returned evidence states:

- run ID:
  `TSCv1.E1.homogeneous.n20.low.greedy.FP5P01.1ce7b703`;
- next attempt: 3;
- retained attempts 1 and 2: current QC pass;
- metric values consulted: false;
- correction-audit SHA-256:
  `bfa4bc68b9150e44fd7b2220c275ee10e2a141971cd622f25f5149972632704a`;
- dry evidence object hash:
  `9839add441a944730d94629470b5f6bb95a3894be344f9957620bf78ede595e8`.

After dry validation the real ledger remained ten events, 7,061 bytes, file
SHA-256
`fb69ff7214bc9c45bc53484d28a30afb232b667c774749ac1d720ab7560965ff`,
with tip
`4f008e48dfe4c0dc4e2dcec32f9516beb1f6e767f7d9c5f48d3492a3d0397618`.
Canonical count remained zero and attempt 3 remained absent.

## 5. Authorization boundary

After this audit is committed, invoke the explicit resume path once for the
exact first row, the retained signature
`18760708ffb872fe4536c553818a0a16bfafa4fa91e7573f972baa4d1b0a224f`,
and `P5_ONLINE_QUEUE_SEMANTICS_QC_CORRECTION_AUDIT.md`. If attempt 3 is
QC-valid, it becomes canonical and the remaining 89 rows may proceed in the
frozen selection order without the resume option. Otherwise P5 stops. No
result-conditioned retry or replacement is authorized.
