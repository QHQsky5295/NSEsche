# M1 Decision-Neutral Diagnosis Implementation Receipt

Date: 2026-09-02 (Asia/Shanghai)

Status: sealed before diagnostic binary build or online execution

- Preregistered plan: `M1_MECHANISM_DIAGNOSIS_PLAN.md`.
- Parent commit: `7e2798b`.
- Modified source: `serverless_sim/src/sche/sche_nash.rs`.
- Source SHA-256 before this receipt commit:
  `cf65e626aa5c7a5ef454d8a592d9b1436b531e82aac0f236f402f73eaa3d41c1`.
- Diagnostic patch SHA-256 before this receipt commit:
  `920bad09e4e81e462b2895a3a763407cdad50a6bc6b3f311793cecc2c5a7c0e5`.
- Paper equations changed: no.
- Candidate ordering, utility, price feedback, feasible-set construction,
  best response, HPA, and dispatch changed: no.
- Observation record extension: warm-path schema 1.

The implementation extends only the post-decision
`placement_diagnostics` calculation and the emitted JSON observation.  It
classifies the final selected container state and recomputes the selected and
best running-warm utilities from the same immutable price signal, common
candidate set, function profile, and other-player impact.  The calculation is
called from `log_window` after solve and dispatch; its output has no path back
to any scheduler decision.

Verification before sealing:

- `cargo fmt`: passed.
- NSESche scheduler tests: 27 passed, including two new diagnostic tests.
- The classification test covers running-warm, starting, and cold/nonrunning
  selections and verifies an unchanged assignment fingerprint.
- The bypass test verifies positive selected-minus-warm utility and finish
  deltas in a controlled state and verifies an unchanged assignment
  fingerprint.
- Git whitespace check: passed with only the expected Windows LF-to-CRLF
  notice.

No diagnostic tape, reference, or online run was built or executed before
this implementation receipt was created.
