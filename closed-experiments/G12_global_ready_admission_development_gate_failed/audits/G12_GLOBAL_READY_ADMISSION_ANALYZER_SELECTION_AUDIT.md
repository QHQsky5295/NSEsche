# G12 Global-Ready Admission Analyzer and Selection Audit

Date: 2026-09-04 (Asia/Shanghai)

Offline-reference commit: `1690f72`

Status: `zero_result_gate_frozen_exact_30_run_online_execution_authorized_once`

## 1. Result-free selection boundary

The G12 online parent directory did not exist when the selector was invoked.
The selector refuses to run if either that parent or its canonical child
already exists. It independently revalidated the complete reference-bound
manifest and rehashed the fixed runtime, all 15 workload tapes, all 30 offline
reference tables, and all 30 reference receipts before constructing the
selection.

The selection contains exactly the 30 manifest-ordered C0/G12 x
low/middle/high x D101--D105 specifications. Run IDs and run-spec hashes are
unique; each load/seed pair shares exactly one tape; every arm has a distinct
mode-specific reference hash. No online throughput, QPR, latency, cost,
completion, scheduler trace, or policy timing existed at freeze time.

| Artifact | Bytes | SHA-256 or object hash |
|---|---:|---|
| `g12.online.selection.json` file | 29,266 | `784f40c3e97ed75d018a948c2f5f1a23c1f46428f77217d48b8fc237e640a7fd` |
| selection canonical document | n/a | `3e5665dca85af7e86cd3dd4e0b0bacbf33c3f323ccacf3ac4f0db854f6cd014f` |
| analyzer source | 54,512 | `d0b5cbdf15298f5c149550c9971f04e586ffb1737c6772fbd4fa8ccd642f5268` |

The selection embeds the analyzer's absolute path and source hash. Any later
analyzer edit invalidates analysis rather than silently changing the gate.

## 2. Frozen nine-condition gate

The sole G12 candidate is evaluated against paired C0 by this exact
conjunction:

1. all 30 rows are unique, tape-paired, QC-valid, positive-completion,
   defined-QPR observations from one verified runtime;
2. candidate/control ratios of five-seed arithmetic-mean throughput and QPR
   are strictly above 1 at each load;
3. throughput, QPR, and joint paired wins are each at least 3/5 per load;
4. every per-seed throughput and QPR ratio is at least 0.80;
5. every leave-one-seed-out mean paired difference is positive for both
   primary metrics at every load;
6. mean completion ratio is not below C0 and mean request latency is below C0
   at every load;
7. at least 3/5 seeds per load have positive deferred feasible work, every G12
   telemetry window obeys exact `min(feasible,N)` prefix accounting, and all
   readiness, feasibility, legacy-order, prefix, bound, and dispatch-set
   violation totals are zero;
8. strict Eq. (15), strict-PNE, offline-reference, complete-dispatch, runtime-
   identity, and G12 telemetry contracts pass for every arm; and
9. the ratio of candidate/control arithmetic means of per-run placement-policy
   wall time is at most 1.50 at every load.

No ranking or favorable-seed choice remains: G12 either passes every condition
or closes as negative development evidence.

## 3. Retention and reporting contract

A QC-valid zero-completion run remains in the 30-row population with zero
throughput and `qpr=null`; it fails the gate and is not a retry. Signed paired
differences, all per-seed ratios and wins, five-seed means/SDs, descriptive
paired 95% t intervals, and every leave-one-seed-out mean are retained.

The report also preserves completion, mean/p95/p99 request latency, cost, queue
area, CPU/memory utilization, scheduling/cold-start/data/execution waits,
stage latency, solver/reference coverage, all six admission violation counts,
deferred-work activation, and scheduler overhead. Per-run QPR ratios are
factored into throughput, latency, and cost ratios with a numerical identity
residual.

## 4. Verification and authorization boundary

- focused G12 analyzer tests: 11/11 passed;
- complete analysis regression suite: 126/126 passed in 100.050 seconds;
- Python compilation and Black formatting checks: passed;
- actual-manifest selection construction and independent output inspection:
  passed;
- selection run count: exactly 30;
- online parent/canonical result directories at freeze: absent; and
- result-conditioned selection flag: false.

After this audit and exact selection are committed, one result-blind execution
of all 30 selected specifications in manifest order is authorized. Retries
remain limited to the existing technical-QC policy. Every first QC-valid
outcome, including an unfavorable candidate result, must be retained.

Strong-baseline construction/execution remains blocked unless G12 passes all
nine conditions. Confirmation seeds, formal Q61--Q80 replay, figures, and
manuscript performance claims remain blocked regardless of this development
selection.
