# M1 Dynamic-Contention Guard Screen Result Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: complete non-formal screen; frozen selection is not rankable; family
rejected; qualification forbidden; local M1 candidate development terminated

## Frozen boundary

The dynamic-contention family was preregistered before source modification,
D41--D45 capture, or execution.  It contained exactly the unchanged
`ready_order` control, `guarded_dynamic_finish_05`, and
`guarded_dynamic_finish_15`.  The paper utility, Eqs. 1--20, load-dependent
`(r0, wq)`, QPR definition, common HPA, and six E1 cells were unchanged.  The
only new implementation/prose term was the current-solve assigned-request count
in the operational projected-finish safeguard.

Runtime and protocol identity:

- preregistration commit:
  `0e1b3291819946733c831cb36bd73febf7d6e1f8`;
- scheduler source commit:
  `99a5e7f3a800e2542e41b767afedc0b8052b4461`;
- runtime SHA-256:
  `e5a1b1fe9c26853554c459a10cc71924c107f545afbc5a1d96b64da4eb6e2df8`;
- runtime bytes: 4,678,144;
- frozen protocol commit:
  `ca7df95c73cbb413d6af6c24a318f53a17d79a33`;
- complete development manifest internal hash:
  `2f4771339f34d30fc09652a3397c4a09d720291a4ff48dbeac5a9f3b6bedcbba`;
- complete development manifest file SHA-256:
  `e34750f32b10aae8885515ef82d65c73535c49a511b12e4412a4a313d18cef87`;
- ready screen manifest internal hash:
  `4112985dfa1355f58fa3a141ca158442bec0aebb3b0976de7573be425ec29591`;
- ready screen manifest file SHA-256:
  `bff72c870020b8fafc76f83789d3ce0bd8dd928966315853f94e059d58da5506`.

## Dependency and execution audit

- 30/30 D41--D45 base tapes completed on attempt 1;
- capture quarantine count: 0;
- capture ledger: 30 events, final hash
  `a2116bd020db00667adb4a46a016de56413a6a970b18612d7c74a5678f5b356a`;
- tape catalog: 30 entries, internal hash
  `119bba41c0e5ec1e02f8cceea84a0928880d244541722569b3c1ec3b5dd6e3b9`,
  file SHA-256
  `d46101f6a2c70c4ab7aeb4f112369e60bbe35522e9753e161b85f55888455f44`;
- 90/90 candidate-state-matched offline references completed on attempt 1;
- reference quarantine count: 0;
- reference ledger: 90 events, final hash
  `65b376f7a4fb0678c7712c8c9c1aa153a9a986131c5434da71012ec51923dcdc`;
- reference catalog: 90 entries, internal hash
  `6e063b83ff417dccbe3ecfd5a532d7becec053faee4417d56b12da429b370e82`,
  file SHA-256
  `6cae71377ab44c67b71348c15f6941ebe4a518758a846fa7fae305e7f1957fee`;
- screen: 90/90 canonical runs, every run on attempt 1, quarantine count 0;
- screen ledger: 182 events, final hash
  `19c1e7bb1ba7dd03f416b17e209f46a9de14516916809340ddc12130c405dc53`.

No candidate performance result was read before all 90 runs were canonical.
Every fixed row was retained.

## Byte-preserving capture-path repair

The capture stage was accidentally given a workspace path that already ended
in `capture_base_tapes`; the stage added its own directory of the same name.
One completed D41/middle/heterogeneous canonical promotion consequently kept
the directory basename `attempt-01` instead of the receipt key
`steady.middle.heterogeneous.mixed.D41.a810c9573584`.

The catalog path was therefore absent even though the completed artifact was
present.  Before any reference or candidate run, the source and destination
were resolved and verified to remain inside the same canonical root, the
destination was confirmed absent, and the directory was renamed without
re-execution or content modification.  Pre- and post-move hashes were
identical:

- workload tape SHA-256:
  `0f5f50de114ff6d9fd213615df6d1cbe6a944ea3eec305e0f9576c6beacf5275`;
- capture receipt SHA-256:
  `df0c506420033a7a636833d578e3e2358ca151f8cb0a66cbaf15720e304aea47`.

The receipt key and tape SHA matched the frozen catalog entry.  Strict tape
binding then passed and produced manifest hash
`378ae198a0a908bf9f16a18e91e1294bdd7b3712e4cfd9da2161d9571f858d0e`.
This was a technical path recovery, not a scientific retry.

## Frozen selection failure

After the complete 90-run screen, the frozen analyzer stopped with:

`screen summary has non-applicable throughput; candidate screen cannot rank it`

Exactly three fixed high-load rows completed zero requests in the 1,000 ms
observation window.  Their drained cohort also had zero completions, so latency,
cost per completed request, and run-level QPR were undefined:

| Candidate | Topology | Seed | Arrivals | Completed | Throughput (req/ms) | QPR |
|---|---|---|---:|---:|---:|---|
| ready_order | homogeneous | D44 | 7,038 | 0 | 0 | undefined |
| ready_order | heterogeneous | D42 | 6,965 | 0 | 0 | undefined |
| guarded_dynamic_finish_15 | heterogeneous | D44 | 7,038 | 0 | 0 | undefined |

These are QC-valid scientific observations.  The preregistered selection rule
requires all twelve candidate-relative cell means for throughput and run-level
QPR.  The existing frozen analyzer requires positive finite throughput,
latency, and cost before defining QPR.  It would be result-conditioned to map
undefined QPR to zero, drop a row, replace a seed, rerun a valid row, or rank
only the applicable subset.  None was done.

The analyzer writes its immutable selection receipt only after successful
complete ranking.  Therefore `m1.dynamic.selection.json` does not exist, no
candidate was selected, and qualification is not authorized.

## Descriptive complete-screen summary

The following is a post-failure descriptive audit of all fixed rows.  Mean
throughput includes zero-throughput rows.  Mean QPR is shown only over the
explicitly applicable rows and must not be used as the frozen selection score
when coverage is below 5/5.

| Candidate | Topology | Load | Mean throughput (req/ms) | QPR coverage | Mean applicable QPR | Mean completion ratio |
|---|---|---|---:|---:|---:|---:|
| ready_order | homogeneous | low | 1.2778 | 5/5 | 2.91508e-2 | 0.67075 |
| ready_order | homogeneous | middle | 0.6874 | 5/5 | 6.41975e-3 | 0.27100 |
| ready_order | homogeneous | high | 0.1622 | 4/5 | 2.66485e-4 | 0.02322 |
| ready_order | heterogeneous | low | 1.0912 | 5/5 | 4.04206e-2 | 0.57254 |
| ready_order | heterogeneous | middle | 0.2992 | 5/5 | 1.16738e-3 | 0.11800 |
| ready_order | heterogeneous | high | 0.2236 | 4/5 | 7.78439e-4 | 0.03186 |
| guarded_dynamic_finish_05 | homogeneous | low | 1.2344 | 5/5 | 2.68116e-2 | 0.64762 |
| guarded_dynamic_finish_05 | homogeneous | middle | 0.6928 | 5/5 | 7.03141e-3 | 0.27330 |
| guarded_dynamic_finish_05 | homogeneous | high | 0.1424 | 5/5 | 1.51676e-4 | 0.02028 |
| guarded_dynamic_finish_05 | heterogeneous | low | 1.2268 | 5/5 | 2.75109e-2 | 0.64397 |
| guarded_dynamic_finish_05 | heterogeneous | middle | 0.2878 | 5/5 | 7.89939e-4 | 0.11350 |
| guarded_dynamic_finish_05 | heterogeneous | high | 0.2016 | 5/5 | 4.06054e-4 | 0.02886 |
| guarded_dynamic_finish_15 | homogeneous | low | 1.2110 | 5/5 | 2.55203e-2 | 0.63537 |
| guarded_dynamic_finish_15 | homogeneous | middle | 0.5876 | 5/5 | 3.88102e-3 | 0.23179 |
| guarded_dynamic_finish_15 | homogeneous | high | 0.0906 | 5/5 | 7.39770e-5 | 0.01296 |
| guarded_dynamic_finish_15 | heterogeneous | low | 1.2574 | 5/5 | 2.54621e-2 | 0.66034 |
| guarded_dynamic_finish_15 | heterogeneous | middle | 0.1874 | 5/5 | 4.09060e-4 | 0.07391 |
| guarded_dynamic_finish_15 | heterogeneous | high | 0.2814 | 4/5 | 1.48756e-3 | 0.04059 |

Even descriptively, the fully applicable dynamic 5% guard is not a global
dual-metric improvement: it has lower mean throughput than the control in four
of six cells and lower mean applicable QPR in five of six cells.  This is
supporting diagnosis only, not a replacement selection rule.

## Gate consequence

The frozen screen could not produce a complete QPR ranking, so the dynamic
family is rejected and no D41--D60 qualification manifest or 1,200-run
qualification is created.  Under the preregistered terminal rule, this was the
final local M1 family: no fourth candidate, revised coefficient, load-specific
mechanism, result-conditioned seed reuse, or M2 execution is authorized.
Further mechanism redesign requires explicit user-level direction.
