# Current Experiment Plan

The current paper blocker is the E1 homogeneous-20 **low-load** comparison.
The earlier five-seed operational catalog is retained as development evidence,
but it is not sufficient for the present 20-seed current-baseline claim.

The active algorithm source/worktree is documented in
[WORKSPACE_LAYOUT.20260901.md](WORKSPACE_LAYOUT.20260901.md); the stable main
worktree is deliberately left unchanged for rollback.

The latest completed adaptive result is:
[EXPERIMENT_RESULT.20260901-e1-low-v189.md](EXPERIMENT_RESULT.20260901-e1-low-v189.md).

V189 was the final currently authorized adaptive test. It completed cleanly on
all 20 frozen V187 tapes, but failed every throughput and QPR gate: throughput
lost on all 20 paired seeds and QPR lost on 17 of 20. Its full-cohort diagnostic
shows that excluding blocked work repaired part of V188's accounting error but
did not restore CPU utilization, warm-container reuse, backlog control, or
completion volume.

The native earliest-executable-finish axis is closed. All valid V187--V189
observations remain retained. No further adaptive low-load online experiment is
authorized under the current objective; the next activity is a broader review
of the NSESche objective and paper claim boundary, which must produce a new
independent preregistration before any future execution. Homogeneous-20 low is
not closed, and middle load, high load, and all later chapters remain blocked.
