# G3 post-failure analyzer correction audit

Date: 2026-09-04

## Decision

Commit `43988d1` implements only the preregistered trace-list correction. The
first failed invocation produced no output, the canonical 135-run product is
unchanged, and exactly one retry of the frozen diagnosis is authorized.

## Correction evidence

- `selection.rounds` is now required to be a list of objects.
- The selection-round count is `len(selection.rounds)`.
- `selected_non_o0_rounds` remains a validated numeric count and must not
  exceed the trace-list length.
- Scalar `rounds`, a non-object trace member, and an impossible selected count
  all fail closed in directed tests.
- No other analyzer rule, field, statistic, threshold, hash, or output changed.

Frozen corrected hashes:

- analyzer SHA-256:
  `eef3536c7825c85baa98332f77f4195de25c0d06ec3ed8d5986ddfcfbe01e2bf`;
- directed-test SHA-256:
  `a9bf2ea4dfae39c04a8a2e805e2d21d6cd5984f07c671e3023cbd4d31381fc3b`.

## Verification

- Python compilation: pass.
- Black formatting: pass.
- All G3 analysis tests: 18/18 pass, including the new trace-list test.
- Frozen G3-E0 protocol tests: 9/9 pass.
- `git diff --check`: pass before commit.
- Diagnostic output directory before retry: absent.

The authorized retry uses the same selection, canonical root, and output
directory recorded in `G3_POSTFAIL_DIAGNOSIS_IMPLEMENTATION_AUDIT.md`. It may
not start the simulator or modify any canonical input. After the retry, stop
for a result-integrity audit.
