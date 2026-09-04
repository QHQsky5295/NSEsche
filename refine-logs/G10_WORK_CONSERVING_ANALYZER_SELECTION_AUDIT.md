# G10 Work-Conserving Analyzer and Selection Audit

Date: 2026-09-04 (Asia/Shanghai)

Offline-reference commit: `5974a61`

Status: `zero_result_gate_frozen_exact_45_run_online_execution_authorized_once`

## 1. Result-free selection boundary

The G10 online parent directory did not exist when the selector was invoked.
The selector refuses to run if either that directory or its canonical child
already exists. It independently revalidated the complete bound manifest and
rehashed the fixed runtime, all 15 workload tapes, all 45 offline-reference
tables, and all 45 reference receipts before constructing the selection.

The resulting selection contains exactly the 45 manifest-ordered run
specifications: C0/C1/C2 x low/middle/high x D96--D100. Run IDs and run-spec
hashes are unique; each load/seed group uses one shared tape; every arm has its
own reference hash. No throughput, QPR, latency, cost, completion, or scheduler
outcome existed at freeze time.

| Artifact | Bytes | SHA-256 or object hash |
|---|---:|---|
| `g10.online.selection.json` file | 43,183 | `722eadb7d03d139b3f62f0094cff48b919dbe731bcd920ce8ffa5b5be36431e3` |
| selection canonical document | n/a | `e8cfa0e3960bc114a3bb6e541aa89c5ec8abd462285e564fec8f8be763994aac` |
| analyzer source | 59,675 | `45ada143a0f2fdc15b4093638e00928af1e9701698e22cb8b022a5b125988884` |

The selection embeds the analyzer path and source hash. Any later source edit
invalidates analysis rather than silently changing a gate.

## 2. Frozen nine-condition gate

Each candidate is evaluated against the paired C0 control using the exact
conjunction below:

1. all 45 rows are unique, tape-paired, QC-valid, positive-completion,
   defined-QPR observations from one verified runtime;
2. candidate/control ratios of five-seed arithmetic-mean throughput and QPR
   are strictly above 1 at each load;
3. throughput, QPR, and joint paired wins are each at least 3/5 per load;
4. every per-seed throughput and QPR ratio is at least 0.80;
5. every leave-one-seed-out mean paired difference is positive for both
   primary metrics at every load;
6. mean completion ratio is not below C0 and mean request latency is below C0
   at every load;
7. C1 retains the complete state-local dependency-ready set with no frontier;
   C2 has zero ready omission, frontier-bound, one-hop, and dispatch-class
   violations and positive frontier admission in at least 3/5 seeds per load;
8. strict Eq. (15), strict-PNE, offline-reference, complete-dispatch, runtime-
   identity, and G10 telemetry contracts pass for every arm; and
9. the ratio of candidate/control arithmetic means of per-run placement-policy
   wall time is at most 1.50 at every load.

For C1, ready-set identity is intentionally state-local: runtime evidence must
show `ready_candidates == ready_admitted`, zero omission, zero frontier, and a
valid ready-set hash in every window. It is not scientifically meaningful to
require equal per-frame hashes between two dynamic trajectories after their
earlier placement choices diverge. The implementation-stage frozen-state tests
already prove that C0 and C1 invoke the same eligibility predicate.

If both candidates qualify, the immutable selection order is maximum minimum
of the six primary ratios, then maximum mean of those ratios, then maximum
joint paired wins, with an exact tie assigned to simpler C1. If neither
qualifies, G10 closes as negative development evidence.

## 3. Retention and reporting contract

A QC-valid zero-completion run remains in the 45-row population with zero
throughput and `qpr=null`; it fails the gate and is not a retry. Signed paired
differences, all per-seed ratios and wins, five-seed means/SDs, descriptive
paired 95% t intervals, and every leave-one-seed-out mean are retained.

The report also preserves completion, mean/p95/p99 request latency, cost, queue
area, CPU/memory utilization, scheduling/cold-start/data/execution waits,
stage latency, solver/reference coverage, frontier activity, and scheduler
overhead. Per-run QPR ratios are factored into throughput, latency, and cost
ratios with an explicit numerical identity residual.

## 4. Verification and authorization boundary

- focused G10 analyzer tests: 11/11 passed;
- complete analysis regression suite: 109/109 passed in 103.510 seconds;
- Python compilation and Black formatting checks: passed;
- actual-manifest selection validation and independent artifact rehashing:
  passed; and
- result-conditioned selection flag: false.

After this audit and its exact selection are committed, one result-blind
execution of all 45 selected specifications in manifest order is authorized.
Retries remain limited to the existing technical-QC policy. Every first
QC-valid outcome, including an unfavorable candidate result, must be retained.

Strong-baseline construction/execution remains blocked unless one candidate
passes all nine conditions. Confirmation seeds, formal Q61--Q80 replay,
figures, and manuscript performance claims remain blocked regardless of this
development selection.
