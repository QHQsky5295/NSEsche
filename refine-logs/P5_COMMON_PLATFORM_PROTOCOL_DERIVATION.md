# P5 common-platform protocol derivation

Date: 2026-09-05 (Asia/Shanghai)

Status: complete read-only derivation. This document uses source, frozen
workload profiles, and the complete retained Q61--Q80 homogeneous-low and
homogeneous-middle products. It creates no tape, reference, simulator result,
or method selection.

## 1. Scope and immutable boundary

P5 repairs the experiment harness shared by all ten methods. It does not
change NSESche Eqs. (1)--(20), strict Eq. (15), Eq. (19), the action set,
`ready_order`, load-specific `(r0,wq)`, or the run-level QPR identity

\[
QPR = \frac{T}{L C}.
\]

The repair is required because the current harness exposes every external
arrival to every placement method immediately, while the nominal drained
cohort has no drain in E1. A common, method-neutral admission layer is a
platform control variable, not an NSESche mechanism.

## 2. Exact state definitions

For one immutable arrival tape, let each event be identified by its tape
sequence number, arrival frame, and DAG id.

- **External arrival**: an event whose frame has been reached. It is counted
  once even if it has not entered the scheduler.
- **Admission queue**: arrived but not admitted requests, ordered strictly by
  `(arrival_frame, tape_sequence)`. No method, DAG class, expected size, or
  seed-dependent priority may change this order.
- **Active DAG cohort**: admitted and not completed requests in
  `SimEnvCoreState.requests`. These are the only requests visible to the
  common HPA and the placement method.
- **Dependency-ready function**: a function in an active request for which all
  DAG parents have completed and which has not already been placed.
- **Pending node task**: a placed `(request,function)` pair waiting outside a
  container on its selected node.
- **Resident task**: a pair held by a function container. It is separately
  classified as starting-resident, parent-blocked, data-blocked, or runnable.
- **Completed request**: an admitted request whose complete DAG has finished
  and has moved to `done_requests`.
- **Right-censored request**: an external arrival not completed at the frozen
  hard drain deadline. It remains either waiting or active and is never
  silently dropped.

At every recorded frame the conservation identity must hold:

\[
A = Q_{adm} + X_{active} + C,
\]

where `A` is external arrivals so far, `Q_adm` is admission-queue length,
`X_active` is active requests, and `C` is completed requests. At finalization,
`censored = Q_adm + X_active = A-C`.

## 3. Source audit of the old protocol

The old implementation has no external admission queue:

1. `request.rs:464--514` generates or replays each arrival, constructs a
   `Request`, and immediately inserts it into `core.requests`.
2. `sim_env.rs:178--179` stores only active and completed requests; it has no
   arrived-but-waiting state.
3. `experiment_record.rs:490` counts arrivals as active plus completed, so a
   future waiting population would be omitted unless the recorder is changed.
4. `experiment_record.rs:551--584` repeats the same two-population assumption
   at finalization and treats configured `total_frame` as the drain endpoint.
5. `experiment_record.rs:703--706` hard-codes zero admission drop/reject and
   labels the queue `unbounded_wait_by_design`; those fields do not enforce a
   constraint.
6. `sim_loop.rs:32--52` generates requests every frame and stops only at the
   fixed total frame. The frozen E1 protocol sets arrival, observation, and
   total horizons all to 1,000 frames, so the reported drain is exactly zero.

G9/G12 and the other closed development families do not implement the missing
layer. They restrict or reorder NSESche players only after requests already
belong to `core.requests`; they are method-specific and cannot substitute for
common external request admission.

## 4. Retained-result diagnosis

All figures below were recomputed read-only from the complete canonical
products; no run was omitted.

| Existing scene | Runs | Mean arrivals | Zero-completion runs | Drain duration |
|---|---:|---:|---:|---:|
| homogeneous-20 low | 200 | 1,925.45 | 0 | 0 ms in 200/200 |
| homogeneous-20 middle | 200 | 2,525.95 | 5 | 0 ms in 200/200 |

In low load, the per-method median peak active population ranges from 461.5 to
1,378 requests, with an overall maximum of 1,875. In middle load the ten
per-method medians lie between 2,223.5 and 2,272, with an overall maximum of
2,630. Middle-load median task peaks range from 6,764 to 13,506.5 and the
maximum is 48,204. Thus the simulator is not merely keeping a short node
queue; it is expanding thousands of complete active DAGs.

Q71 makes the failure concrete. NSESche receives 2,459 arrivals, completes
zero, and ends with all 2,459 requests active, 43,677 function tasks in the
system, and 10,307 running tasks. Greedy, Load Least, OCS, Hiku, and NSESche
all have a zero-completion Q71 observation. These are valid outcomes of the
old code, not technical retries, but they do not form an interpretable final
measurement protocol.

## 5. Result-blind capacity audit

For each node `n`, the source exposes CPU capacity `c_n`, memory capacity
`m_n`, the platform memory reserve `R=3500`, and basic container footprint
`b=300`. Define the platform's aggregate activation slots as

\[
B(\mathcal N)=\sum_{n\in\mathcal N}
\left\lfloor\frac{\max(0,m_n-R)}{b}\right\rfloor.
\]

P5 sets `max_active_requests = max(1,B(N))`. Every request consumes exactly
one active slot regardless of method, seed, DAG id, DAG size, predicted
latency, or result. This uses the same public memory headroom that governs
container placement (`main.rs:92--93`, `node.rs:181--188`); it does not use any
throughput or QPR value.

For the homogeneous profile (`m_n=5000`), the rule gives five slots per node:

| Nodes | Active-request limit | Workload scale |
|---:|---:|---:|
| 20 | 100 | 1x |
| 100 | 500 | 5x |
| 500 | 2,500 | 25x |

Both admission capacity and frozen tape intensity therefore scale by the same
factor in weak-scaling experiments. Heterogeneous runs recompute the sum from
their frozen node capacities; they do not substitute the homogeneous mean.
The strict FCFS queue absorbs excess offered traffic without deleting or
relabeling it.

This active-DAG limit is a control-plane bound, not a claim that one request
equals one container or that memory alone predicts service time. CPU work,
cold start, network, and DAG width remain part of the simulator and determine
which admitted requests complete. The bound's purpose is to prevent the
number of complete active DAG state machines from growing without limit.

## 6. Offered-load audit

The frozen profiles specify positive-truncated-normal per-DAG arrivals. For
`X~N(mu,(cv*mu)^2)` conditioned on `X>0`, the expected generated rate is

\[
E[X\mid X>0]=\mu+\sigma
\frac{\phi(-\mu/\sigma)}{1-\Phi(-\mu/\sigma)}.
\]

This reproduces the frozen expected rates of 1,934.66, 2,533.14, and 7,000
requests/s for low, middle, and high. The retained tapes average 1,925.45 and
2,525.95 requests/s for low and middle; the small differences are ordinary
finite-tape variation.

To distinguish a rate label from actual work demand, the read-only audit also
computed

\[
\rho_{ideal}=\frac{\lambda\,E[W_g]}{\sum_n c_n},\qquad
W_g=\sum_{f\in g}cpu_f.
\]

This is an optimistic CPU-only lower bound: it ignores cold starts, memory,
network transfer, dependency stalls, and scheduler inefficiency. Across the
frozen Q61--Q80 environments its median/minimum/maximum values are:

| Load | Expected rate (req/s) | median `rho_ideal` | min | max |
|---|---:|---:|---:|---:|
| low | 1,934.66 | 0.3428 | 0.1990 | 1.2099 |
| middle | 2,533.14 | 0.8240 | 0.1441 | 3.4966 |
| high | 7,000.00 | 1.9852 | 0.4588 | 13.1343 |

The wide range occurs because a heavy-tailed popularity profile is mapped to
random, seed-specific DAGs. A value above one proves that the arrival cohort
cannot finish inside its 1,000-ms arrival window even under ideal CPU use. P5
therefore keeps the named loads and exact tapes but reports both request rate
and CPU-work offered load; it does not rename strata or tune a load after
seeing a method result.

## 7. Frozen phase and drain derivation

The arrival and primary observation interval remains `[0,1000)` frames to
retain the submission-era workload and fixed-window throughput meaning.
Arrivals cease at frame 1,000. Admission and execution continue during drain.
The run stops at the first frame at or after 1,000 for which both the admission
queue and active cohort are empty, or at a result-blind per-tape hard deadline.

For a replay tape, define total static CPU work

\[
W_{tape}=\sum_{e\in tape} W_{dag(e)},
\]

cluster capacity `C=sum_n c_n`, and `L_static` as the maximum, over DAGs present
in the tape, of the longest dependency path when each function contributes its
cold-start frames plus `ceil(cpu_f/max_n c_n)` and each edge contributes
`ceil(output_MB/min_network_MB_per_ms)`. The maximum post-arrival drain is

\[
D_{max}=\max\left(1000,
\left\lceil4W_{tape}/C\right\rceil+L_{static}\right).
\]

The multiplier four is fixed before results and corresponds to a conservative
25% aggregate CPU progress floor relative to the CPU-only ideal. The formula
is recomputed from each bound tape and environment, is invariant under the
5x/25x weak-scaling transforms, and cannot depend on which method is running.
All ten methods sharing a tape must record the same `W_tape`, `C`, `L_static`,
`D_max`, and hard end frame. An unfinished request at that point is retained
as right-censored, not retried or replaced.

## 8. Metric contract

- **Paper throughput `T`**: requests from the arrival cohort completed at or
  before frame 1,000, divided by 1,000 ms, reported in requests/ms. Drain time
  never enters this denominator.
- **End-to-end latency `L`**: external arrival to completion, including FCFS
  admission wait. The primary mean and p50/p95/p99 use completed members of
  the frozen arrival cohort through the terminal frame; completion and
  censoring ratios accompany them.
- **Cost `C`**: common simulator resource cost accumulated through the
  terminal frame divided by completed members of the arrival cohort.
- **QPR**: computed per run as `T/(L*C)` only when `T`, `L`, and `C` are finite
  and strictly positive. The algebra is unchanged. A run with undefined QPR
  remains present with the reason; it is never imputed as zero.
- **Sensitivity throughput**: completed cohort requests divided by actual run
  duration is recorded separately as cohort-clearance throughput and cannot be
  substituted for paper throughput after results are visible.
- **Queue reporting**: admission queue peak/area/wait and node-task queue
  peak/area are separate fields. Combining them into one unlabeled queue value
  is forbidden.

Paper-ready cells require at least 95% terminal cohort completion in every
retained run, in addition to the ordinary QC and full censoring report. This
prevents a favorable QPR calculated only on a small fast-completion subset
from closing a cell.

## 9. Implementation consequences

The smallest source change is to add a FIFO of fully identified `Request`
objects outside `core.requests`, admit from its head until the static limit is
reached, and extend the recorder and stop condition. `Request.begin_frame`
remains the external arrival frame; a new `admission_frame` records the
transition to active. Admission happens after that frame's tape events and
before HPA/placement observation. Slots released by execution in frame `t`
are filled at frame `t+1`, a common one-frame-granularity rule.

Formal mode must fail closed unless replay tape, admission rule, active limit,
phase contract, derived drain identity, workload/profile hashes, common HPA,
source commit, and binary hash are all bound. Offline social-reference build
and online replay must use the same admission and terminal-state identity.

## 10. Decision

The source and retained evidence support exactly one P5 implementation:
external FCFS queue, static capacity-derived active-DAG limit, explicit fixed
arrival/observation phase, result-blind bounded drain with early completion,
and complete conservation/censoring telemetry for every method. No simulator
sampling is authorized by this derivation alone.
