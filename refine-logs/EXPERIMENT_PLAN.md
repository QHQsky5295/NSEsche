# Current Experiment Plan

The current paper blocker is the E1 homogeneous-20 **low-load** comparison.
The earlier five-seed operational catalog is retained as development evidence,
but it is not sufficient for the present 20-seed current-baseline claim.

The active algorithm source/worktree is documented in
[WORKSPACE_LAYOUT.20260901.md](WORKSPACE_LAYOUT.20260901.md); the stable main
worktree is deliberately left unchanged for rollback.

The latest completed adaptive result is:
[EXPERIMENT_RESULT.20260901-e1-low-v187.md](EXPERIMENT_RESULT.20260901-e1-low-v187.md).

V187 passed both QPR gates but failed the frozen and same-tape throughput gates
after a clean 20-seed paired execution. Its response-time-majority axis is
closed. The next authorized plan is the baseline-independent native service
rule in
[EXPERIMENT_PLAN.20260901-e1-low-v188.md](EXPERIMENT_PLAN.20260901-e1-low-v188.md).
Implementation, tests and binding must complete before any V188 online run.
Middle-load and all later experiment chapters remain blocked until the low-load
group closes.
