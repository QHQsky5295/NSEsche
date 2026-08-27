# Current Experiment Plan

The E1 homogeneous and heterogeneous 20-node load groups are closed in their
stable final catalogs. The NSESche-only 20/100/500-node proportional-load
resource-scaling result is also closed and does not require baseline overlays.

V78 and V86 are retained failed 100-node overlay confirmations. They are no
longer the active paper blocker because the scaling section is explicitly
NSESche-only.

The current execution plan is E3 burst recovery plus E4 balanced-QoS:
[EXPERIMENT_PLAN.20260827-e3e4-v1.md](EXPERIMENT_PLAN.20260827-e3e4-v1.md).

The next action is M1 input preparation only. Formal baseline and NSESche runs
remain separate later milestones so a failed default NSESche configuration
cannot waste or invalidate frozen baseline observations.
