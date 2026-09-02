# G0 Cold-Start Transition Semantics Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: common-simulator defect identified, corrected, unit-tested, and
technically replayed; formal runtime/reference refreeze still required

## Scope and result

This audit asks whether the zero-completion high-load observations in the
closed D41--D45 dynamic screen were caused primarily by an NSESche placement
mechanism or by the common simulator execution semantics.  It changes no paper
utility, Eq. 1--20 term, QPR definition, HPA rule, workload, or observation
window.

The authoritative result is a common-runtime defect: per-frame runnable-task
memory was admitted before reserving the additional memory required for a
container at the end of cold start to enter the running state.  Under sustained
load, tasks repeatedly consumed the remaining memory and held containers at
`left_frame == 1` far beyond their configured cold-start duration.

## Frozen-run evidence

For the nine same-tape control/5%/15% high-load runs surrounding the three
zero-completion observations:

- the last common-HPA scale-up occurred between frames 59 and 137;
- the maximum configured function cold start was 278--298 frames;
- 14--119 containers were still starting at frame 1,000;
- the post-scale-up slack beyond the maximum cold start was 565--663 frames.

Consequently, these final starting containers cannot be explained by late HPA
creation.  The terminal queue breakdown also shows that `running_tasks` was a
resident-task count, not the CPU-runnable count:

| Candidate | Topology | Seed | Completed | Resident | Runnable | Starting-resident | Running containers | Starting containers |
|---|---|---|---:|---:|---:|---:|---:|---:|
| ready_order | homogeneous | D44 | 0 | 31,125 | 7,011 | 24,114 | 103 | 119 |
| ready_order | heterogeneous | D42 | 0 | 13,954 | 11,618 | 2,336 | 205 | 24 |
| guarded_dynamic_finish_15 | heterogeneous | D44 | 0 | 32,140 | 15,107 | 17,033 | 90 | 70 |

Parent-blocked and data-blocked counts were zero in these terminal snapshots.
The dominant non-runnable state was therefore residence in starting
containers.

## Code-path cause

At frame begin, the node accounts 100 memory units for a starting container and
300 for its running footprint.  The old per-frame order was:

1. admit runnable tasks in deterministic `(fn_id, request_id)` order until task
   memory nearly fills the node;
2. then check whether each finishing cold start can acquire its additional 200
   memory units;
3. hold the transition at `left_frame == 1` when the check fails.

Because new runnable work arrives every frame, step 1 can starve step 2
indefinitely.  This behavior was introduced with the hard-memory transition
check in commit `6d98504589851f5425d6567308808e339afc5ef7`; the original imported
checkpoint did not hold the transition this way.

## Common-runtime correction

Source commit:
`16c32c23ce88c5809cca03c5b1674c215abfbbcc`

The corrected executor:

1. identifies containers that will finish cold start in the current frame;
2. deterministically authorizes transitions by function ID while respecting
   the hard node-memory limit;
3. reserves the authorized transition delta before runnable-task admission;
4. admits tasks only from the remaining memory;
5. applies the reserved transition later in the same frame and asserts that
   the node remains within its hard limit.

This is one common execution path for every scheduler; it is not an NSESche
advantage or a load-specific parameter.

Built regression runtime:

- path:
  `serverless_sim/target_g0_transition_16c32c2/release/serverless_sim.exe`;
- bytes: 4,684,800;
- SHA-256:
  `ce60b0247ea0b377e9af8c68ce6aa81f00e53c2f9029417b3b468ac5f4eaaac4`.

## Verification

- `cargo fmt -- --check`: pass;
- directed `deterministic_order_tests`: 4/4 pass;
- complete Rust suite: 106/108 pass;
- the two complete-suite failures are pre-existing/out-of-scope: one
  wall-clock timing assertion in `mechanism_thread::tests::test_algo_latency`
  and one optional Python emulation test whose interpreter lacks `numpy`.

The added tests prove that transition reservation has priority over runnable
task memory and that insufficient capacity authorizes the smallest function ID
deterministically.

## Same-tape technical replay

The unchanged D44 homogeneous/high `ready_order` tape was replayed with the new
runtime in
`runs/g0_transition_16c32c2/workspace_after_port_release`.  The original
canonical run remains untouched.

| Diagnostic | Old runtime | Corrected runtime |
|---|---:|---:|
| Completed requests | 0 | 115 |
| Throughput (requests/s) | 0 | 115 |
| Final running containers | 103 | 222 |
| Final starting containers | 119 | 0 |
| Final resident tasks | 31,125 | 27,397 |
| Final runnable tasks | 7,011 | 27,397 |
| Final starting-resident tasks | 24,114 | 0 |
| Final queue | 23,045 | 22,826 |
| Peak normalized node memory | 0.999990137 | 0.999990137 |

Both technical attempts produced the same 115 completions and terminal state.
The protocol correctly quarantined them as `reference_pair_failure`: the old
offline reference was built from the defective state trajectory, while the
corrected runtime produced new state keys and 115 rather than zero completions.
This replay therefore verifies the executor correction only.  It is not a
canonical performance or QPR observation and must not be plotted.

## Experimental consequence

1. All D01--D60 performance and QPR results remain historical development
   diagnostics only; none was paper-ready, so no formal paper group is lost.
2. Every offline social-reference table must be rebuilt with the corrected
   runtime before any corrected-runtime NSESche replay.
3. An NSESche-specific serviceability/admission mechanism is no longer the
   supported immediate next step.  The unchanged existing NSESche candidates
   must first be re-screened under the corrected common runtime.
4. Any corrected-runtime screen needs a new preregistration and fresh seed
   bank.  Old D41--D45 results cannot select a corrected-runtime candidate.
5. No M2 experiment is authorized until the corrected runtime, references, and
   six-cell NSESche qualification are frozen and pass.
