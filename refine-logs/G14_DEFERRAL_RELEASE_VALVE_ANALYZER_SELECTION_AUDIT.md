# G14 Deferral Release-Valve Analyzer and Selection Audit

Date: 2026-09-04 (Asia/Shanghai)

Offline-reference commit: `b03f6c8965a2ed08a2c35d9e71e8ac9572eaa089`

Analyzer commit: `4da9b196cd11be443db239931ac15a721ad5ab8a`

Status: `zero_result_gate_frozen_exact_30_run_online_execution_authorized_once`

## 1. Result-free selection boundary

The G14 online parent directory did not exist when the selector was invoked.
The selector refuses to run if either that parent or its canonical child
already exists. It independently revalidated the complete reference-bound
manifest and rehashed the fixed runtime, all 15 workload tapes, all 30 offline
reference tables, and all 30 reference receipts before constructing the
selection.

The selection contains exactly the 30 manifest-ordered C0/G14 x
low/middle/high x D106--D110 specifications. Run IDs, run-spec hashes, and
matrix identities are unique; each load/seed pair shares exactly one tape;
every arm has a distinct mode-specific reference hash. No online throughput,
QPR, latency, cost, completion, scheduler trace, or policy timing existed at
freeze time.

| Artifact | Bytes | SHA-256 or object hash |
|---|---:|---|
| `g14.online.selection.json` file | 29,326 | `887fc413d2de23cd223fcc67775d80cd18509f3b64ffa6a500096c30b7b968b4` |
| selection canonical document | n/a | `3e750866cde6b11a5ebae84bccdb09846e7e9d9a4eef1787dab64d29e3779169` |
| analyzer source | 40,341 | `13997e4f476226acc5b4a5fbf90ca9b0cb8978ffb9fe5a21fa66fd96040aefe3` |

The selection embeds the committed analyzer's absolute path and source hash.
Any later analyzer edit invalidates analysis rather than silently changing the
gate.

## 2. Frozen nine-condition gate

The sole G14 candidate is evaluated against paired C0 by this exact
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
7. at least one seed per load records a bounded first-overflow window, at
   least three runs across at least two loads record persistent-overflow full
   release, no actual positive-deferral episode exceeds one window, and all
   readiness, feasibility, legacy-order, prefix, admission-rule,
   state-transition, and dispatch-set violation totals are zero;
8. strict Eq. (15), strict-PNE, offline-reference, complete-dispatch,
   runtime-identity, and G14 state-machine contracts pass for every arm; and
9. the ratio of candidate/control arithmetic means of per-run
   placement-policy wall time is at most 1.50 at every load.

The G14 analyzer reuses the already-frozen G12 paired-statistics core by exact
method/seed identity relabeling only. It evaluates condition 7 independently
from the raw G14 state-machine telemetry. There is no ranking or
favorable-seed choice: G14 either passes every condition or closes as negative
development evidence.

## 3. State-machine and retention contract

For every candidate scheduling window, the analyzer reconstructs the frozen
one-bit recurrence from the complete ordered trace. It checks current
overflow, valve state before and after, admission mode, admitted/deferred
counts, admission limit, complete-set order hashes, arrival range, solver-set
cardinality, and all eight telemetry violation counters including the
auxiliary bound counter. A drift, omitted window, adjacent positive deferral,
or invalid count fails both activation and runtime integrity.

A QC-valid zero-completion run remains in the 30-row population with zero
throughput and `qpr=null`; it fails the gate and is not a retry. Signed paired
differences, every per-seed ratio and win, five-seed means/SDs, descriptive
paired 95% t intervals, every leave-one-seed-out mean, completion, latency,
cost, QPR factors, queue/resource/wait metrics, runtime evidence, activation
telemetry, and scheduler overhead are retained.

## 4. Verification and authorization boundary

- focused G14 analyzer tests: 14/14 passed;
- complete analysis regression suite: 149/149 passed in 100.49 seconds;
- Python compilation and Black formatting checks: passed;
- actual-manifest fail-closed validation and independent output inspection:
  passed;
- selection run/spec/matrix counts: exactly 30/30/30;
- unique paired tapes / reference hashes: exactly 15/30;
- manifest execution order: exact;
- online parent/canonical result directories at freeze: absent; and
- result-conditioned selection flag: false.

After this audit and exact selection are committed, one result-blind execution
of all 30 selected specifications in manifest order is authorized. Retries
remain limited to the existing technical-QC policy. Every first QC-valid
outcome, including an unfavorable candidate result, must be retained.

Strong-baseline construction/execution remains blocked unless G14 passes all
nine conditions. Confirmation seeds, formal Q61--Q80 replay, figures, and
manuscript performance claims remain blocked regardless of this development
selection.
