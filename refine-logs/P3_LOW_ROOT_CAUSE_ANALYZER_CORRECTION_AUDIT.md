# P3 Low-Load Root-Cause Analyzer Correction Audit

Date: 2026-09-05 (Asia/Shanghai)

Status: `technical_failure_no_result_correction_preregistered`

## 1. Failed attempt retained

The first P3 analyzer invocation terminated before writing any report or CSV.
The P3 output directory still contained only the already committed
`p3.selection.json`; no D1--D4 aggregate, direction decision, candidate
selection, simulator run, or offline-reference run was produced.

The failed analyzer was commit
`e14d5c7decf5558a1d3b0a56d41428a934b1e985`, file SHA-256
`6f580561fcb2bc592125bfb54f7bb18623ae799931e08a85a7fb83160e75a3ab`.
Its frozen selection was commit
`4f254645138b872214c77bba16bcdbb0a62b33e8`, file SHA-256
`d067bc5a7078e7d953ad172f0c9987bff5cddfadb35dcfd76d5dbfbb40d30f0d`,
and document hash
`19b4748a6f2fd15988b7dd747be476511fae386471f039846b6893416f12260a`.
That receipt remains immutable and is not replaced or deleted.

## 2. Cause and result-blind field audit

The failed implementation required a nonempty `outer_feedback_trace` in every
one of the 1,000 scheduler windows. The simulator intentionally emits an empty
trace when `assigned_players A=0`. A field-presence-only audit of the frozen
25-run population found 25,000 windows: all 24,345 active windows had nonempty
traces, all 655 inactive windows had empty traces, and zero windows lacked any
other preregistered decision or utility-component field. The audit did not
compute or print D1--D4 aggregate values.

## 3. Exact correction and retry boundary

The corrected analyzer returns an empty price signature only when `A=0`. An
active window with an empty or missing outer-feedback trace still fails closed.
No population, identity, alignment, D1--D4 definition, threshold, six-condition
conjunction, candidate direction, or stopping rule changes.

The corrected source and tests must be committed first. A new
`p3.selection.corrected.json` must then bind the corrected analyzer while also
hash-binding the failed analyzer and selection above. Only after that corrected
receipt is committed may the same fixed 25-run population be retried once. The
old receipt, this audit, and the corrected receipt must all accompany the final
P3 report.
