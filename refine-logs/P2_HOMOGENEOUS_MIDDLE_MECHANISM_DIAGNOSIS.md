# P2 Homogeneous-Middle Mechanism Diagnosis

Date: 2026-09-04 (Asia/Shanghai)

Status: `exploratory_complete_new_algorithm_boundary_reached`

## Scope and integrity boundary

This is a post-result, read-only diagnosis of the complete P2 product. It
created no workload, reference, simulator run, replacement observation, or
paper figure. All 200 first QC-valid observations remain included. The
descriptive correlations below were inspected after result exposure and are
therefore mechanism hypotheses, not confirmatory tests or candidate-selection
evidence.

Input roots:

- `runs/tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904/`
- `runs/tscv1_g1_formal_q61_q80_98f822c_20260903/stages/capture_base_tapes/`

The formal outcome remains the one recorded in
`P2_HOMOGENEOUS_MIDDLE_RESULT_AUDIT.md`: NSESche ranks fifth in throughput,
eighth in applicable-run QPR, and homogeneous-high is not authorized.

## Workload structure explains much of the seed spread

Every Q61--Q80 tape contains arrivals from 18 DAG IDs, but DAG 16 contributes
88.7%--89.7% of all arrivals. The topology seed changes the generated DAG 16
itself. Across the 20 paired seeds, that dominant DAG ranges from 2 to 22
functions, from 126.9 to 4,554.6 total CPU-work units, and from 299 to 3,784
total cold-start frames. Thus the seed-to-seed variation is not small arrival
noise around one fixed application: it also samples markedly different
dominant application graphs.

Consistent with that construction, exploratory Spearman associations between
NSESche throughput and dominant-DAG descriptors are strongly negative:

| Descriptor | Spearman rho | two-sided p |
|---|---:|---:|
| function count | -0.666 | 0.0014 |
| total CPU work | -0.738 | 0.0002 |
| total cold-start frames | -0.709 | 0.0005 |
| mean resident task queue | -0.929 | <0.0001 |

These associations show why bootstrap intervals are wide and why an isolated
seed must not be treated as a replaceable simulator failure. They do not make
the within-seed ten-method comparison unfair: all methods still receive the
same tape and topology for a seed.

## Q71 is an extreme but valid application mix

Q71 has 2,459 arrivals. DAG 16 contributes 2,182 (88.74%); the remaining 277
arrivals are spread over 17 DAGs. In this topology, DAG 16 has 21 functions,
six sources, two sinks, 4,229.16 total CPU-work units, and 2,346 total
cold-start frames. Its longest source-to-sink path has 1,691.8 CPU-work units,
or 2,753.0 units when each function's cold-start duration is added once.

The Q71 first-attempt observations are:

| Method | completed requests | mean latency (ms) when defined |
|---|---:|---:|
| Greedy | 0 | -- |
| Hash | 40 | 47.225 |
| Load Balance | 0 | -- |
| Random | 11 | 418.182 |
| FaaSRank | 49 | 28.367 |
| Hiku | 0 | -- |
| Jiagu | 27 | 17.926 |
| NSESche | 0 | -- |
| OCS | 0 | -- |
| Orion | 48 | 29.292 |

The positive FaaSRank, Jiagu, and Orion completions come only from the small
minority DAGs 4 and/or 7; none completes the dominant DAG 16. Random completes
ten DAG-16 requests but only one minority request. This is evidence of a
service-order effect under a difficult mix, not evidence that the shared tape
is empty or corrupt.

NSESche's Q71 execution is mechanically healthy: 1,000 scheduler windows,
strict Eq. (15), stable solver operation, all prepared commands dispatched,
zero placement rejection, and nonzero CPU/memory use. At the final frame it
has 43,677 function tasks in the system, including 10,307 running tasks, but
no end-to-end request completion. Its resident task queue reaches 10,300 in
the NSESche stream. This is forward progress distributed across many
unfinished requests, not a crash or failed placement path.

## First-principles mechanism interpretation

Two implementation semantics interact:

1. `ready_order` collects every dependency-ready `(request, function)` pair
   from all live requests and then applies the paper-faithful strict Eq. (15)
   node choice.
2. On each node, the simulator divides CPU capacity equally over every
   runnable request-function task plus starting containers.

At roughly 2.5 thousand request arrivals per second, the number of admitted
runnable tasks grows faster than complete DAGs drain. Per-pair utility and
social welfare can remain well behaved while CPU is spread over a broad set
of unfinished requests. Neither Eq. (15) nor the potential/PNE result contains
an end-to-end request-completion term. The resulting mismatch is therefore:

`placement-game equilibrium != finite-window completed-DAG throughput`.

This diagnosis also explains the QPR rank. Run-level QPR is
`throughput / (mean latency * cost per completion)`. Across P2, NSESche's
mean cost per completion (2.647 internal units) is essentially the same as
Load Balance (2.648), but its mean defined latency is 253.42 ms versus
171.84 ms for Hiku. The main QPR deficit is therefore not an accounting bug or
excess cost alone; it is the joint completion/latency consequence of service
ordering and broad in-flight concurrency.

## Candidate boundary after all retained evidence

The retained G2/G3/G6/G7/M1 products already reject warm initialization,
equilibrium-order envelopes, parent lookahead, bounded-frontier lookahead,
static completion guards, and dynamic contention guards as a reliable route
to dual-metric leadership. P2 supplies no new evidence that another local
node-score tie-break or parameter change will solve the end-to-end objective
mismatch.

The only materially distinct hypothesis exposed by this diagnosis is a
request-level admission/backpressure or service-discipline layer that bounds
in-flight DAGs and concentrates service on a disclosed cohort while retaining
strict Eq. (15) for the admitted players. That is not a harmless tuning of the
existing paper method:

- if applied only to NSESche, it defines a new compound algorithm and must be
  described and evaluated as such;
- if made a common simulator service discipline, all baselines must receive
  it and the ten-method cells must be rerun;
- either route needs a new zero-data protocol, fresh development seeds,
  disjoint confirmation seeds, and a revised manuscript method boundary.

Consequently, no existing-candidate implementation, NSESche-only replay,
Q71 replacement, high-load run, or later online block is authorized from P2.
The current resubmission route can proceed only with transparent rank claims
and the already closed convergence/reference/exact-small evidence. Universal
throughput-and-QPR leadership requires a separately approved new-algorithm
research cycle; it cannot be obtained scientifically by deleting valid seeds
or repeatedly sampling until favorable observations accumulate.
