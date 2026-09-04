# G9 Request-Level Backpressure Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Status: `zero_result_preregistered_implementation_authorized_sampling_blocked`

## 1. Motivation and research boundary

P2 completed the fixed Q61--Q80 homogeneous-middle product and retained every
first QC-valid observation. The post-result diagnosis found a mismatch between
per-function placement equilibrium and finite-window completed-DAG throughput:
all dependency-ready request-function pairs may be placed, while node CPU is
shared over every runnable task. The resulting broad in-flight population can
advance many requests without completing them.

G2/G3/G6/G7/M1 already tested node-choice initialization, equilibrium-order,
lookahead, warm-path, and finish-guard variants. G9 is intentionally outside
that exhausted local family. It introduces one request-level service discipline
before the unchanged placement game. It is a new compound method and must be
described as such if it survives independent confirmation.

No G9 result exists at this freeze. D81--D95 do not appear in any registered
experiment product. The exposed Q61--Q80 and D61--D75 observations may motivate
G9 but may not select its parameter, seed subset, load subset, or reported
result.

## 2. Sole candidate and fixed rule

Candidate identifier: `ready_request_backpressure`.

At scheduler frame `t`, let `R_t` be all live, incomplete requests ordered by
the existing deterministic key `(arrival_frame, request_id)`. Let `N` be the
configured node count. The admitted cohort is

`A_t = first min(N, |R_t|) requests in R_t`.

Only dependency-ready, not-yet-placed request-function players belonging to
`A_t` enter the NSESche game in that frame. Requests outside `A_t` remain in
the simulator without rejection or deletion and become eligible when older
requests complete. A request cannot leave the cohort except by completion or
normal simulator removal. There is no load-specific constant, learned model,
result feedback, random tie-break, timeout exception, or Q61--Q80 special case.

For every admitted player, Eqs. (1)--(20), strict Eq. (15), the existing
`ready_order` initialization, pricing feedback, reference definition, and
node candidate set remain unchanged. The reference identity must receive a
new operational-refinement tag because the player population differs.

The implementation must log per window:

- live request count;
- cohort limit (`N`), admitted request count, and deferred request count;
- ready players before cohort filtering and admitted ready players;
- cohort minimum/maximum arrival frame when nonempty;
- cumulative request admissions and cohort completions if observable without
  changing simulator semantics.

## 3. Development population

The development bank is fixed before implementation:

- seeds: D81, D82, D83, D84, D85;
- topology: homogeneous;
- nodes: 20;
- loads: low, middle, high;
- methods: NSESche `ready_order` control, G9
  `ready_request_backpressure`, Load Balance, FaaSRank, and Hiku;
- workload generation, trace profile, observation/drain horizon, common HPA,
  QPR definition, and QC rules: unchanged reviewer-v3 protocol;
- one first QC-valid run per exact method/load/seed cell;
- 75 online runs total, plus the exact offline references required by the two
  NSESche operational identities.

The same tape must be used by all five methods within each load/seed pair.
Technical failures may be reconciled only by the existing result-blind rules.
Scientific zero completion, high latency, poor QPR, or an unfavorable rank is
not retryable.

## 4. Frozen development gate

G9 qualifies only if every condition below is true:

1. all 75 cells are present, unique, paired, and QC-valid;
2. all 75 runs have positive completion and defined run-level QPR;
3. G9 has the highest arithmetic mean throughput among the five methods in
   each of low, middle, and high load;
4. G9 has the highest arithmetic mean QPR among the five methods in each load;
5. against `ready_order`, G9 wins throughput in at least 4/5 seeds and QPR in
   at least 4/5 seeds in each load;
6. against each of Load Balance, FaaSRank, and Hiku, G9's paired mean
   throughput difference and paired mean QPR difference are both positive in
   every load;
7. no G9 seed has throughput or QPR below 80% of the paired `ready_order`
   value;
8. the mechanism activates: whenever live requests exceed `N`, deferred
   requests are positive, admitted requests do not exceed `N`, and every
   dispatched player belongs to the logged cohort;
9. strict Eq. (15), PNE/reference-stream, dispatch, and runtime-identity gates
   pass; and
10. G9 mean policy wall time is no more than 1.25 times `ready_order` in any
    load.

Ranks are descriptive development gates, not confirmatory significance
claims. All per-seed values, paired differences, win counts, leave-one-seed-out
means, and failure reasons must be reported. No condition may be weakened after
exposure.

If any condition fails, G9 is closed as a negative result. D81--D85 may not be
relabelled, filtered, supplemented, or reused to tune a successor. A successor
requires a new named mechanism and fresh seeds.

## 5. Independent confirmation boundary

Only a passing development gate may authorize a separately frozen confirmation
selection over D86--D95. The intended confirmation population is the same
three loads, topology, node count, and five methods (150 online runs), but its
exact manifest, hashes, inference family, and success thresholds must be
committed after development selection and before D86 is materialized.

D86--D95 cannot repair or be pooled with D81--D85. Q61--Q80 formal cells remain
untouched until confirmation passes. A confirmed G9 would then require a new
formal protocol that runs G9 on the exact Q61--Q80 tapes and compares it with
all retained/fresh same-protocol baselines without deleting the original
`ready_order` rows.

## 6. Authorization after this freeze

After this document is committed, only the following are authorized:

- implement `ready_request_backpressure` and its telemetry;
- extend configuration/schema validation with the new identifier;
- build unit, protocol, and QC tests;
- construct a result-blind D81--D85 manifest/selector/analyzer;
- verify D81--D95 freshness and registered output-root absence.

Simulator sampling, workload capture, offline-reference construction, and
online execution remain blocked until the implementation and zero-result
protocol audit are committed. Homogeneous-high P2, heterogeneous, scaling,
ablation, burst, QoS, and pricing/welfare blocks remain closed.
