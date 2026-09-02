# M1 Decision-Neutral Mechanism Diagnosis Result Audit

Date: 2026-09-02 (Asia/Shanghai)

Status: complete; non-formal diagnosis only

## Sealed inputs and execution

- Preregistered plan: `M1_MECHANISM_DIAGNOSIS_PLAN.md`.
- Diagnostic manifest: `runs/tscv1_m1_diag_846991f_20260902/m1.diagnosis.ready.json`.
- Manifest file SHA-256: `d49ab0913d3b2d1e0e26d487c71f1f16eaa5d8431d8d16944cd423bd09891c65`.
- Manifest internal hash: `df7ec60ad4d5b7e9a1f6ba59a989f717ae5b7bb7b7d1628555da22fde3be3c00`.
- Runtime binary SHA-256: `73400031ac3e098b0c672830f5e7bc7f322c28ad198f89896c74122ddd5bc42e`.
- Diagnostic source commit: `846991f`; execution/protocol commit: `e42d6ae`.
- Fixed cohort: D01--D05 x homogeneous/heterogeneous x low/middle/high, NSESche `ready_order` only.
- Outcome: 30/30 canonical on attempt 1; quarantine 0; no baseline run and no replacement seed.
- Ledger: 62 events; final hash `0b9f818be17d9bb0d95b46619bfd4882f7b38859bc84d28349667c04c58cec31`.

## Decision-neutrality audit

Every diagnostic run was mapped to its exact parent qualification run through
the stored parent run ID and run-spec hash.  The audit passed for all 30 pairs:

- scientific summary after excluding run ID and scheduler/observation timing: 30/30 exact;
- frame stream: 30/30 semantic hashes exact;
- request stream: 30/30 semantic hashes exact;
- assignment, command, feasibility, solver, traffic, cluster, price, cost,
  network, and social-welfare window semantics: 30,000/30,000 exact;
- function-profile records: 30/30 exact.

The only excluded difference was an existing observation-only floating-point
dispersion reduction that can differ by one `f32` ULP across processes.  It is
not consumed by best response, pricing, HPA, or dispatch.

Machine report:
`runs/tscv1_m1_diag_846991f_20260902/m1.diagnosis.report.json`.
Its file SHA-256 is
`20079e21db68115cecd1ec2fac2b4452f91b853e81bd8c7cfac5b57e2deabb92` and
its internal document hash is
`52fcdf51854ccd10877ac8b9f95111aa68dd88734a3003cf3bd39fc4a0e4ff77`.

## Warm-path evidence

All quantities below aggregate the five fixed seeds in each cell.  A positive
finish delta means the selected path has a worse projected completion score
than the best running-warm alternative.

| Topology | Load | Players | Warm available | Bypassed / available | Selected starting | Mean utility advantage | Mean finish delta | Lower-utility players |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
| homogeneous | low | 29,563 | 88.36% | 11.85% | 22.11% | +1.692 | +47.20 | 0 |
| homogeneous | middle | 33,702 | 86.74% | 23.14% | 33.34% | +2.326 | -20.98 | 0 |
| homogeneous | high | 80,521 | 69.55% | 31.86% | 52.61% | +1.589 | +93.34 | 0 |
| heterogeneous | low | 27,060 | 85.55% | 15.08% | 27.35% | +1.444 | +52.18 | 0 |
| heterogeneous | middle | 30,682 | 86.56% | 24.48% | 34.63% | +2.111 | +83.35 | 0 |
| heterogeneous | high | 72,444 | 78.57% | 46.37% | 57.86% | +1.363 | +143.54 | 6 |
| **all** | **all** | **273,972** | **79.56%** | **29.40%** | **43.83%** | **+1.624** | **+96.46** | **6** |

The selected path was always either running or starting; no assignment used a
cold/nonrunning path.  Running-warm supply is therefore common, not rare.  The
paper utility positively rewards bypassing warm candidates in every cell.  In
five of six cells, including both high-load cells, the same bypass also has a
worse projected completion score.  The preregistered objective-conflict
interpretation is strongly supported, while supply limitation is not.

Homogeneous middle load is an important exception: its selected starting path
has a better projected finish score on average.  This rules out an unconditional
"warm first" rule and supports a completion-aware guard rather than a state-only
priority.

## Rare termination edge

Six lower-utility final assignments occurred in one window only:

- seed D05, heterogeneous high, frame 322/window 323;
- termination `inner_iteration_limit` after four rounds with moves 7, 5, 4, 3;
- the bounded solver returned its best-social-welfare state without Nash stability.

Thus no best-response ranking defect was established.  The event is a genuine
bounded-termination edge and must remain visible; it cannot explain the broad
throughput/QPR gap or the other 64,086 warm bypasses.

## Protocol consequence

The three-candidate local tie/order family is exhausted.  Equal-utility
tie-breaking cannot correct a positive utility preference for a slower
starting path.  M2 remains unauthorized.

Any next candidate must be a separately preregistered, paper-compatible
operational family on a fresh development bank.  The evidence favors a bounded
utility-regret completion guard: retain the published utility unchanged as a
quality floor, then minimize projected completion score only among candidates
inside that floor.  This is materially different from a fourth local tie rule
and must be screened without reusing D01--D20 for selection.

## Verification

- Protocol regression: 152/152 passed before diagnostic execution.
- Focused diagnosis-manifest tests: 8/8 passed after the executable-boundary check.
- Analysis regression after result audit: 48/48 passed.
- Diagnosis-analysis focused tests: 3/3 passed.
- Git whitespace check: passed (only normal Windows LF-to-CRLF notices).

Nothing in this diagnosis is eligible for a paper figure or a superiority
claim.  All failed qualification and diagnostic artifacts remain retained.
