# G7 bounded-frontier warm-initialization candidate preregistration

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Preregistration commit base: `8cb15a559700bb32e144b1906f19d10d54fdd386`  
Status: candidate frozen; implementation and tests authorized; sampling blocked

## Purpose and evidence boundary

G6 proved that parent-scheduled lookahead is active and can reduce post-ready
cold-start wait, but its unrestricted cascade failed throughput, QPR,
completion, and per-seed safety gates.  G7 defines one integrated operational
candidate before its code or data product exists.  It changes no paper
equation, utility term, price feedback, reference definition, HPA setting, or
baseline.

This candidate is informed by explicitly exploratory, post-G6 diagnostics.  It
is not presented as confirmation evidence:

- G6 created parent-blocked queue means of 481.1--3384.4 tasks across the five
  seeds, versus exactly zero for dependency-ready C0.  Mean resident queues
  increased in all five pairs by 678.3--3062.5 tasks.
- Among completed pre-ready-bound functions, bindings at least two dependency
  frontier hops ahead existed in every seed and represented 8.0%--67.2% of
  early bindings.  Between 87.1% and 99.8% of early bindings retained lead
  time after subtracting useful cold-start overlap.
- Nevertheless, G6 reduced mean post-ready cold-start wait in every seed and
  improved throughput in three seeds.  The warranted response is to bound the
  cascade, not remove lookahead completely.
- In the independent earlier D66--D70 initialization development bank,
  `ready_warm_init` improved homogeneous-low throughput from 1.5104 to 1.5508,
  QPR from 0.0408954 to 0.0421808, latency from 138.864 to 125.263 ms, cost per
  completion from 0.384144 to 0.368871, and completion ratio from 0.787860 to
  0.808689 relative to `ready_order`.  It did not pass its own all-cell gate;
  it is used here only as prior development evidence for an initialization
  rule, not as a publishable result.

Source receipts:

| Source | File SHA-256 | Document SHA-256 |
|---|---|---|
| G6 failed selection | `6fa6446ef8a84432dee6607c8a58b3cbd02548e67aa0f22dbbbb787c2e60d3f6` | `842a20e410c1f1a188b76d42b4398251171574241d39121b0e33630371d04592` |
| G2 initialization analysis | `414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db` | `e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79` |

## Sole candidate

The only G7 candidate is named `lookahead_frontier1_warm_init`.

### Player admission

For each unplaced `(ReqId, FnId)`, admission is deterministic:

1. every direct parent must already have a concrete placement;
2. a direct parent that is already complete imposes no additional condition;
3. for every unfinished direct parent, all of that parent's own direct parents
   must be complete.

Dependency-ready functions therefore remain admitted.  A not-yet-ready child
may be admitted only when each unfinished parent lies on the current executable
frontier.  An early placement cannot recursively authorize a grandchild while
its parent is itself dependency-blocked.  This is a one-frontier-hop bound,
not a seed, load, DAG-ID, time, or result-specific exception.

Players retain the stable order
`arrival_frame, ReqId, DAG topological rank, FnId`.

### Feasible initialization

For the initial feasible assignment only:

- if at least one feasible running-warm container exists, select the running-
  warm candidate with minimum dynamic projected finish time, then higher paper
  utility, then smaller NodeId;
- otherwise use the ordinary strict paper-utility argmax.

The unchanged inner loop then performs strict best responses until its existing
termination condition.  A final assignment is acceptable only with the same
strict-PNE certificate used by G6.  Initialization may select a lower-utility
start, but no lower-utility move is permitted by the equilibrium solver.

## Frozen invariants

- Paper Eqs. (1)--(20), including strict Eq. (15), are unchanged.
- `utility_guard_relative_regret=0`; no bounded-regret or finish-time override
  is allowed in a best response.
- Price parameters remain low-load `r0=0.6`, `wq=0.5`; Eq. (19) uses immutable
  window baseline prices exactly as before.
- Common HPA, container cache/lifecycle, topology, network, workload tapes,
  candidate-node feasibility, SA/reference search, convergence caps, and all
  nine baselines remain unchanged.
- G3's 50 homogeneous-low D71--D75 controls remain the only comparison source.
  They will not be rerun.
- G6's five negative candidate runs and all earlier valid runs remain retained.

Pre-implementation source SHA-256 values are:

| File | SHA-256 |
|---|---|
| `serverless_sim/src/sche/sche_nash.rs` | `3f1c5c3a876c4dc63e553b79cd0afacbf1708e31c3c24a634ce3c468165adb43` |
| `serverless_sim/src/sim_run.rs` | `8226f8c66a7f26c641a07a3802f4440e51bd26c61ea02d2e6e46296fdeda3cb7` |
| `serverless_sim/src/config.rs` | `a973967c8c378d23d0ec3b861b289e374a95e49559aacae1d245d268ea4fc1e8` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | `db75ac8abc2c1eb874d78e7ea43bb9af1aace3bd58fd34e498d2e8ad66aa4a39` |
| `scripts/reviewer_experiments/protocol/schema.py` | `6155484a6f57c7e0fbf60c6b9684300e14c9158230309d8e512f210c57d6acce` |

## Development product

G7 adaptively reuses D71--D75 as an optimization bank.  Because its design was
informed by G6 outcomes, it is not independent evidence and can never be mixed
with confirmation or formal data.

- five candidate-only online runs, one for each D71--D75 tape;
- five new candidate-specific offline reference builds;
- exact reuse of the 5 G3 C0 and 45 baseline source runs;
- no G6 candidate run is a control and no baseline is resampled;
- every first valid canonical result is retained; no seed extension,
  substitution, or result-conditioned retry is permitted.

The implementation must expose a new reference-key tag and runtime schema so a
G7 reference cannot collide with G3 or G6.  Protocol/runtime/zero-data and
reference-binding freezes are required before their respective next stages.

## Fixed gates

Integrity and activation must all pass:

1. runtime reports `lookahead_frontier1_warm_init`, strict Eqs. (1)--(20), the
   stable player order, bounded-frontier admission, and warm initialization;
2. every seed has complete assignment/dispatch accounting, zero invalid
   assignments, zero channel failures, and a hit for every required offline
   reference window;
3. every seed contains at least one completed function bound before readiness,
   positive startup overlap, and at least one warm-refined initial choice;
4. completed-function reconstruction finds no binding more than one executable
   frontier hop ahead.  This is an integrity check, not an outcome metric.

Performance gates are unchanged from G6:

1. mean throughput is strictly above 1.1514 requests/ms;
2. mean QPR is strictly above 0.040391615;
3. versus paired G3 C0, throughput improves in at least 3/5 seeds, QPR in at
   least 4/5, and both jointly in at least 3/5;
4. no seed's throughput or QPR is below 80% of its C0 value;
5. mean completion ratio is not below C0 and mean latency is strictly lower;
6. mean active-window solve-time ratio to C0 is at most 3.0;
7. all five values, mean, sample SD, paired 95% t interval, sign counts, and
   leave-one-seed-out means are reported without filtering.

Passing all gates authorizes only a separately preregistered Q61--Q80
confirmation.  Failure retains and closes the full G7 product, blocks
confirmation, and returns to diagnosis; it does not authorize threshold or
seed changes.

## Authorization boundary

This preregistration authorizes implementation, unit tests, protocol/analyzer
construction, and their audits.  It does not yet authorize release construction,
reference building, online simulation, confirmation, figures, or paper claims.
