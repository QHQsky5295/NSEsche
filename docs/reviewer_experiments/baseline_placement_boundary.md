# Baseline placement boundary under the common HPA protocol

## 1. Scope of the comparison

The revised experiments compare **request-placement policies under one common
serverless control plane**.  Every method uses exactly the same:

- HPA implementation, scaling signal, scaling interval, and instance limits;
- cold-start model and container-start state transition;
- container memory accounting, lifecycle, and eviction/cache policy;
- request/workflow input, queueing/execution engine, and admission behavior;
- legacy simulator network topology and bandwidth values.

The advanced baselines are therefore placement-only adaptations, not claims of
reproducing each paper's complete end-to-end system.  A baseline scheduler may
emit `MechScheduleOnceRes::ScheCmd` only.  It must not emit or emulate native
scale-up, scale-down, prewarm, cache-admission, or eviction actions.

In `scale_sche_separated` mode, a placement candidate must be a node already
listed for the function in `fn_2_nodes`.  This means the common HPA first owns
instance availability; the placement policy only chooses among the instances
that HPA has provisioned.  When no such candidate exists, the scheduler waits
instead of silently creating an instance.

All five adaptations call the same
`schedule_helper::placement_candidate_ids(req, fnid, env)` API.  Besides the
existing-container condition, this API rejects candidates with an unavailable
parent-to-child network path and returns a stable node-id ordering.

Placement binds a function invocation to the queue owned by an HPA-provisioned
container; it does not immediately reserve the invocation's execution memory.
The common runtime admits queued invocations only when their memory fits, and
holds a cold container in `Starting` when its transition to `Running` would
exceed the node limit. Thus memory remains a hard execution constraint without
turning temporary pressure into an algorithm-specific placement rejection.

Workflow execution dependencies are always enforced by the common runtime.
Baseline-specific *placement timing* is retained only where it is part of the
placement policy: ORION-P, Jiagu-P, and Hiku-P may pre-assign unscheduled DAG
nodes; OCS-P waits until predecessors have placements; FaaSRank-P waits until
predecessors complete.  An early placement never allows a function to execute
before its data/dependency conditions are satisfied.

## 2. Names used in the paper and retained placement logic

| Paper label | Accurate description | Retained placement-side mechanism | Explicitly excluded under the common protocol |
|---|---|---|---|
| **ORION-P** | ORION-inspired critical-path-aware placement policy | DAG upward/critical-path rank, same-function warm affinity, resource/load ranking, and data-locality ranking using the simulator bandwidth matrix | ORION-native prewarming and scaling |
| **Jiagu-P** | Jiagu-inspired predictive pre-decision placement policy | Per-function pending-demand history, moving/trend forecast, ranked pre-decisions, and forecast-dependent spreading over HPA-provisioned workers | Jiagu-native dual-stage scaling and instance-count adjustment |
| **Hiku-P** | Hiku-inspired pull-based placement policy | Per-function idle-running-worker heaps, least-connection pull, and deterministic least-loaded fallback | Worker creation, prewarming, or lifecycle control |
| **OCS-P** | OCS-inspired container-state-aware placement policy | Greedy invocation distribution using idle/busy/starting container state, actual node memory/load, and bounded placement affinity history | OCS-native randomized cache admission/eviction and synthetic cache/memory accounting |
| **FaaSRank-P** | FaaSRank-inspired Score-Rank-Select placement policy using a frozen linear score model | Frozen CPU/memory-headroom, warm-affinity, network-locality, load-balance, and diversity coefficients; score/rank/select; and seeded epsilon diversity | Online learning, PPO, a baseline-owned scaler/cache manager, or a claim of reproducing a complete learned end-to-end controller |

The `-P` suffix is substantive: it identifies the placement adaptation evaluated
inside the shared simulator control plane.  Figures, tables, captions, and the
response letter should use these labels consistently.

## 3. Corrections made for an auditable comparison

- The previous ORION code computed a prewarm candidate list and resource budget,
  but its command was commented out.  This dead native-control path was removed;
  critical-path ordering and placement locality remain.
- The previous Jiagu code computed two stages of instance adjustment without
  issuing scale commands or affecting placement.  These no-op scaling stages
  were removed; demand prediction now directly controls placement pre-decisions
  and spreading among common-HPA instances.
- The previous OCS cache decision only updated private history and never changed
  the simulator cache.  It and its synthetic fixed memory/startup statistics
  were removed.  OCS placement history remains bounded and placement-only.
- The old OCS greedy implementation minimized a score that assigned larger
  positive values to warm/idle containers, thereby preferring the opposite
  state.  OCS-P now maximizes its score and enforces
  `idle warm > busy warm > starting > missing` when other signals are equal.
- FaaSRank-P no longer uses process-global random numbers.  Its diversity choice
  is a stable function of `rand_seed`, frame, request id, and function id.
- FaaSRank-P does not train or update coefficients on an evaluation workload.
  Each formal configuration must declare `faasrank_model.state=frozen`, record
  the model SHA-256 and the separate training-tape SHA-256, and carry the six
  finite linear-score coefficients plus epsilon.  The protocol provenance
  layer is responsible for proving that the training tape is distinct from the
  paired evaluation tape.  Missing model fields retain the historical defaults
  only for legacy, non-formal runs.
- Every adapted scheduler suppresses duplicate `(request, function)` commands
  while a command is in flight and deterministically resolves equal scores by
  node id.

These corrections do not change the common HPA, request execution, cold-start,
network, or container-lifecycle model, and they do not modify NSEsche.

## 4. Reproducibility and audit checks

For every reported run, store the complete configuration and a non-empty,
run-specific `rand_seed`.  All methods within one paired comparison must use the
same seed and workload tape; independent replications use different seeds.

Before producing reviewer figures, verify:

1. `batch_run.yml` selects the same mechanism/HPA/cache/cold-start settings for
   all methods and varies only the scheduler name within a comparison block.
2. Repository search finds no `UpCmd`, `DownCmd`, native prewarm, cache insert,
   or eviction command in these five scheduler files.
3. Runtime command logs for these schedulers contain `ScheCmd` only.
4. In separated mode, every emitted `(fn_id, node_id)` exists in the observed
   `fn_2_nodes[fn_id]` candidate set at decision time.
5. Repeating a run with the same configuration and seed reproduces the same
   workload and placement decisions; changing the replication seed changes the
   independent sample.
6. Every formal FaaSRank-P manifest records a frozen model hash and training
   tape hash, and the protocol provenance check rejects reuse of an evaluation
   tape as training data.  Testing performs inference only; it does not update
   the configured score coefficients.

## 5. Reviewer-facing wording

Recommended wording:

> To isolate request-placement quality, all methods were evaluated under the
> same HPA, cold-start, container-lifecycle/cache, queueing, and network model.
> We implemented placement-only adaptations of the advanced baselines, denoted
> ORION-P, Jiagu-P, Hiku-P, OCS-P, and FaaSRank-P.  We retained placement-related
> ordering, prediction, container-state, locality, and ranking signals when they
> did not conflict with the common control plane.  Baseline-native scaling,
> prewarming, and cache-management actions were intentionally disabled.  Thus,
> the comparison evaluates scheduling/placement modules under identical system
> mechanisms and does not claim a full end-to-end reimplementation of those
> systems.

Do not describe ORION-P, Jiagu-P, or OCS-P as a complete reproduction of the
corresponding system.  Do not say that their original scaling/prewarm/cache
mechanisms were executed.  This explicit boundary is more defensible than a
nominal “full-system” label for behavior that the common HPA necessarily
replaces.

Likewise, describe FaaSRank-P as a placement-only adaptation with a frozen
linear Score-Rank-Select model.  Do not call this implementation PPO or imply
that it retrains on the test workload.
