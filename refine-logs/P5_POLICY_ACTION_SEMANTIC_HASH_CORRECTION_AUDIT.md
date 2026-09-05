# P5 policy-action semantic-hash correction audit

Date: 2026-09-05 (Asia/Shanghai)

Status: completed reporting-only correction; no simulator rerun and no
scientific result changed

## Scope and cause

The predeclared duplicate of
`TSCv1.E1.homogeneous.n20.low.sche_nash.FP5P01.824fd6ca` reproduced the
workload, terminal counts, and scientific result exactly, but the original
full decision-object hash differed. A field-level comparison of all 4,588
scheduler windows found exactly eight mismatches, at indices 276, 304, 347,
351, 355, 356, 367, and 432. The sole differing field was
`placement_dispersion_normalized`; its maximum absolute difference was
`5.960464477539063e-08`.

Every scheduling action was identical: initial and final assignment hashes,
complete-assignment flags, assigned players, assigned-node counts, prepared
commands, sent commands, scale-up commands, invalid assignments, infeasible
players, and waiting-for-candidate counts all matched. All non-timing fields
in the 4,588 `scheduler_windows` also matched. The original hash therefore
mixed a decision-neutral floating-point diagnostic into an exact action
identity and was too broad for the declared determinism question.

## Frozen correction

Preregistration commit `ba378f9` froze the correction before it was
implemented. Source commit `3f624e7` adds an explicit policy-action semantic
hash over this exact whitelist:

- `initial_assignment_hash` and `assignment_hash`;
- `complete_assignment`, `assigned_players`, and `assigned_node_count`;
- `commands_prepared`, `commands_sent`, `scale_ups_prepared`, and
  `scale_ups_sent`;
- `dispatch_channel_failed`, `invalid_assignments`, and
  `no_feasible_players`; and
- `waiting_for_candidate_nodes`.

The legacy full decision-object hash remains in every report. The new hash is
computed from retained `nash_metrics.jsonl.gz` evidence and does not rewrite a
canonical result, summary, QC receipt, workload tape, reference table, or
attempt history.

## Verification

- Focused correction tests: 10/10 passed.
- Full reviewer-protocol suite: 294/294 passed in 859.80 s.
- Full analysis suite: 223/223 passed in 86.55 s.
- Git whitespace check: passed.
- Canonical and duplicate policy-action semantic hashes are both
  `d6c1c217a69ed02f80ebc66a6cdd87ced468afd9f84a4a03855a09f7b90d9c77`.
- Workload, terminal-count, and scientific-result semantic hashes remain exact.

Corrected duplicate evidence:
`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/p5_common_platform.duplicate_evidence.action_semantic_v2.json`
(file SHA-256
`6c86b4d01d90b54284b942b66bc2ce3155b6376cfb402e403726b8bcdb47bb7f`).

Corrected gate report:
`runs/tscv1_p5_common_platform_p5p01_p5p03_2cbeb9a_20260905/p5_common_platform.gate_report.action_semantic_v2.json`
(file SHA-256
`149b2245c0a34467b66ad2348f153995f720f096d170366ffa5d8baf22d58053`).

## Decision

P5 condition 11, the determinism duplicate, passes under the corrected
action-semantic definition. This correction does not repair condition 8, does
not make P5 paper-ready, and does not authorize formal sampling. It only
removes a false determinism failure caused by a decision-neutral float.
