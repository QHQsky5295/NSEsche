# Current Experiment Plan

The current paper blocker is the E1 homogeneous-20 **low-load** comparison.
The earlier five-seed operational catalog is retained as development evidence,
but it is not sufficient for the present 20-seed current-baseline claim.

The active algorithm source/worktree is documented in
[WORKSPACE_LAYOUT.20260901.md](WORKSPACE_LAYOUT.20260901.md); the stable main
worktree is deliberately left unchanged for rollback.

The latest completed adaptive result is:
[EXPERIMENT_RESULT.20260901-e1-low-v188.md](EXPERIMENT_RESULT.20260901-e1-low-v188.md).

V188 failed every preregistered throughput and QPR gate after a clean 20-seed
NSESche-only execution on the frozen V187 tapes. It lost throughput to the
same-tape control in all 20 seeds and lost QPR in 18 of 20 seeds. The native
clearance/response axis is closed and all valid observations are retained.

The next and final currently authorized adaptive plan is
[EXPERIMENT_PLAN.20260901-e1-low-v189.md](EXPERIMENT_PLAN.20260901-e1-low-v189.md).
It tests one coefficient-free native earliest-executable-finish score using
equal-share runnable work and overlapping readiness delays. Implementation,
tests, binary and a pre-execution receipt must be sealed before any V189
reference or online run. Middle-load and all later experiment chapters remain
blocked until the low-load group closes.
