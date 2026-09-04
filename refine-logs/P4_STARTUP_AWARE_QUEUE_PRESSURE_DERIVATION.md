# P4 Startup-Aware Queue-Pressure Derivation

Date: 2026-09-05 (Asia/Shanghai)

Status: `derived_from_retained_evidence_no_candidate_result`

## 1. Question and invariant object

The submitted method already defines node pressure in Eq. (6) as CPU
utilization plus memory utilization plus a normalized request-queue term. The
P4 question is whether the operational observation used for that queue term
omits latency-bearing service backlog during container startup.

P4 changes neither the displayed pressure equation nor any other displayed
equation. It changes exactly one operational slice: which mutually exclusive
queue categories are counted as `q_n(t)`.

For node `n` and decision window `t`, let:

- `q_pending` be unplaced dependency-ready request-function pairs;
- `q_run` be resident pairs whose container is running and whose parents and
  inputs are ready;
- `q_start` be resident pairs waiting for their container to finish startup;
- `q_parent` be resident pairs blocked by unfinished DAG parents; and
- `q_data` be resident pairs blocked by input transfer.

The simulator's queue breakdown is exclusive and satisfies

`q_resident = q_run + q_start + q_parent + q_data`.

The current control observation is

`q_exec(n,t) = q_pending(n,t) + q_run(n,t)`.

The sole P4 candidate observation is

`q_startup(n,t) = q_pending(n,t) + q_run(n,t) + q_start(n,t)`.

Parent-blocked and data-blocked pairs remain excluded. The corresponding
current-window normalizer and queue ratio are

`q_max^m(t) = max(1, max_n q_m(n,t))`,

`rho_m(n,t) = q_m(n,t) / q_max^m(t)`,

where `m` is either `exec` or `startup`. Eq. (6) remains

`Pressure_n^m(t) = u_cpu,n(t) + u_mem,n(t) + rho_m(n,t)`.

Because every `q_m` is nonnegative and the denominator is at least every
numerator, `0 <= rho_m <= 1`; therefore P4 preserves the queue-term bound and
does not create an unbounded penalty.

## 2. Propagation through the submitted utility

The candidate is evaluated through the submitted equations only:

- Eq. (5) quality uses `1/(1+Pressure_n)`, so a node's measured service
  backlog affects quality through the existing denominator;
- Eq. (8) consumes the same pressure state in the existing externality term;
- Eq. (11) makes the existing base node price pressure-aware, and Eq. (4)
  consumes that price in cost; and
- Eq. (9), Eqs. (16)--(20), the feasible candidate set, and strict Eq. (15)
  remain structurally unchanged.

No additional score, warm-container bonus, admission rule, future lookahead,
load branch, seed branch, baseline expert, or post-argmax override is added.
When `q_start(n,t)=0` for every node, control and candidate pressure inputs are
identical. When startup backlog is present, the candidate may change relative
node pressure and hence the strict Eq. (15) ranking through the existing
utility.

## 3. Mechanism hypothesis and anti-claim

The falsifiable hypothesis is:

> Counting startup-resident request-function pairs as current service backlog
> prevents new placements from repeatedly selecting nodes whose accepted work
> cannot yet execute, reducing cold-start backlog exposure enough to improve
> both low-load throughput and QPR.

This is not a claim that a warm node is always preferable. A starting node can
still win strict Eq. (15) when its complete paper utility is greatest. It is
also not a claim that startup-aware pressure must improve performance: the
window-max denominator changes with the augmented queue, and excess spreading
can increase cold starts or data movement. Those failure modes are part of the
test.

## 4. Why this direction remains open

P2 and P3 close the local `r0`, `wq`, and Eq. (9) contribution-tempering
directions. Earlier work also closes direct warm preference, initialization,
player order, lookahead, request admission/backpressure, remaining-work,
ready-cap, and release-valve families. P4 is distinct: it neither enlarges nor
restricts the action set and does not use container state as a tie-break or
bonus. It supplies the existing pressure equation with a latency-bearing
request category that the current implementation observes but explicitly
excludes from `q_n(t)`.

The submitted paper describes `q_n(t)` as request-queue length and does not
partition it into execution-ready and startup-resident categories. Therefore
the candidate is compatible with the displayed Eq. (6), provided the revised
text explicitly defines the operational queue observation.

## 5. Retained evidence, not candidate evidence

The following diagnostics use all five already retained P2 centre runs. They
were computed before P4 implementation from the complete 1,000-window stream
of each run. An active window has `assigned_players>0`; augmented queue mass is
`sum(q_exec+q_start)` over active windows.

| Seed | Active windows | Active windows with `q_start>0` | Share | `q_start` share of augmented queue mass | Selected starting/assigned | Selected cold/non-running |
|---|---:|---:|---:|---:|---:|---:|
| D121 | 980 | 333 | 33.9796% | 6.2723% | 1555/9221 = 16.8637% | 0 |
| D122 | 985 | 476 | 48.3249% | 15.4098% | 1109/5942 = 18.6638% | 0 |
| D123 | 976 | 553 | 56.6598% | 17.3605% | 1077/7676 = 14.0307% | 0 |
| D124 | 958 | 957 | 99.8956% | 61.8105% | 2208/3591 = 61.4871% | 0 |
| D125 | 971 | 696 | 71.6787% | 48.7196% | 1342/4140 = 32.4155% | 0 |

This establishes exposure and testability, not benefit. It does not authorize
reuse of D121--D125 for candidate evaluation.

G4 independently found that the retained NSESche homogeneous-low mean request
latency and cold-start wait exceeded FaaSRank, while G5 rejected a direct warm
preference as the dominant explanation. Together these facts motivate a
service-backlog definition without reopening the rejected warm-path family.

## 6. Assumptions and audit obligations

P4 depends on the following explicit assumptions:

1. the five queue categories remain mutually exclusive under the common
   runtime;
2. a startup-resident pair is latency-bearing work already accepted by the
   node, even though it cannot consume CPU yet;
3. the snapshot and current-window maximum are calculated from the same
   decision instant;
4. control mode remains byte-for-byte behaviorally equivalent to the current
   `pending+runnable` implementation; and
5. offline-reference keys distinguish the two queue semantics because the
   induced payoffs may differ.

Implementation must emit both the execution-ready count and startup addition,
the active semantics, normalizer, maximum ratio, and decision-activation
counters. A failed invariant, hidden branch, reference-key collision, or
change outside the declared slice fails P4 before performance interpretation.

## 7. Bound inputs

- submitted PDF: 15,108,672 bytes, SHA-256
  `03792fe876048ae13a55215463c53b54f9b8a97316ac2b91913de9ca7b107a18`;
- scheduler source: 445,999 bytes, SHA-256
  `8423e3bdffbe18aaf72faa39926e099cc99fc7eda3b7b3759a45c3e26f0aa949`;
- node queue source: 26,666 bytes, SHA-256
  `80b6c75d442c0dfda1f87f778786774767d71dc6daa9482c8212f7459b0db6ed`;
- P3 machine report: 58,482 bytes, SHA-256
  `b29488857646cd2de7cfd61ce369ef7f43a0b4fe13cb4416234d8ab6b1fb9ca2`;
- P3 result audit: 5,560 bytes, SHA-256
  `8f3f2c368f8c2efc073d602f07ac587171439a4f5cfa1c4c94648147bc00dd3a`;
- G4 latency audit: 9,523 bytes, SHA-256
  `36212b99bb8eeb62c83886c17ec2d0973c2cdc8381dd8fefce29cb8ae00cb4b9`;
- G5 warm-path audit: 5,990 bytes, SHA-256
  `d975149d4d062d3950bead38f575bbdbc9264bebf0f626a07153cad17a2f2c95`;
- repository state at derivation: commit
  `ae18d82494abea1c0ad50863583d6e9ea437fa79`.

No P4 code, workload tape, offline reference, online output, baseline result,
or paper claim existed when this derivation was written.
