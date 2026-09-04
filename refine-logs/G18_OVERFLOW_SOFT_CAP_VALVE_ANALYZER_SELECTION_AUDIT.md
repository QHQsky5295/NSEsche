# G18 Overflow Soft-Cap Valve Analyzer and Selection Audit

Date: 2026-09-05 (Asia/Shanghai)

Offline-reference commit: `1ef7dfbce23d0affcdf1da794cbc6bb1f362abc1`

Analyzer commit: `8b95ca8cf997a22b0d0017630e30c37aa4f6b82a`

Status: `zero_result_gate_frozen_exact_30_run_online_execution_authorized_once`

## 1. Result-free selection boundary

The G18 online parent directory did not exist when the selector was invoked.
The selector independently revalidated the complete reference-bound manifest
and rehashed the frozen runtime, all 15 workload tapes, all 30 offline
reference tables, and all 30 reference receipts before writing the selection.
It refuses to freeze when either the online parent or its canonical child
already exists.

The selection contains exactly the 30 manifest-ordered C0/G18 x
low/middle/high x D116--D120 specifications: 15 rows per method, 10 rows per
load, and six rows per seed. Run IDs, run-spec hashes, and matrix identities
are unique; each load/seed pair shares one tape; every arm has a distinct
method-specific reference hash. Ordinals 1--30 and the paper load order
low--middle--high are exact. No online throughput, QPR, latency, cost,
completion, scheduler trace, or policy timing existed at freeze time.

| Artifact | Bytes | SHA-256 or object hash |
|---|---:|---|
| `g18.online.selection.json` file | 29,465 | `4bd389c84b102b3f62e9e32e02b689851d179f402ed3a72c2e96b3ff25829262` |
| selection canonical document | n/a | `1a5d9180ebe04bdb32de00e9b162ea71f4734d9515cbc0417ae590bf1eb92ee1` |
| analyzer source | n/a | `af9a617c9b535d9bcda624ded0f7e5726ca9ab838a692bfb0ae81583c5199e84` |
| reference-bound manifest file | 845,984 | `694e5ad1242f7bb6254aa614660d7ec30b687d0b5e42e84aa7d9e7b54afc4a8b` |
| reference-bound manifest object | n/a | `81859abdaa4ff48eaa484f82cf0e4089a341d12cce38ba30308b5dfaa75241c5` |

The selection embeds the committed analyzer's absolute path and exact source
hash. Any later analyzer edit invalidates analysis instead of silently
changing a gate after outcome exposure.

## 2. Frozen nine-condition gate

The sole G18 candidate is evaluated against paired C0 by this exact
conjunction:

1. all 30 rows are unique, tape-paired, QC-valid, positive-completion,
   defined-QPR observations from one verified runtime;
2. candidate/control ratios of five-seed arithmetic-mean throughput and QPR
   are strictly above 1 at each load;
3. at least one paired joint throughput-and-QPR strict win and at least four
   paired joint nonlosses occur at each load;
4. every per-seed throughput and QPR ratio is at least 0.80;
5. all five leave-one-seed-out mean paired differences are nonnegative and at
   least four are strictly positive for each primary metric at each load;
6. mean completion ratio is not below C0 and the candidate/control mean
   request-latency ratio is at most 1.05 at every load;
7. at least one seed per load records positive material soft-cap deferral, at
   least three runs across at least two loads record an at/below-cap
   first-overflow release, at least three runs across at least two loads record
   persistent-overflow release, no positive-deferral episode exceeds one
   window, and all nine telemetry violation totals are zero;
8. strict Eq. (15), strict-PNE, offline-reference, complete-dispatch,
   retained-exception, runtime-identity, and soft-cap-state contracts pass for
   every arm; and
9. the ratio of candidate/control arithmetic means of per-run
   placement-policy wall time is at most 1.50 at every load.

The analyzer reuses the frozen G12 metric extraction and paired-statistics
core by exact method/seed identity relabeling only. G18-specific paired
win/nonloss, leave-one-out, completion/latency, and activation conditions are
evaluated independently. There is no ranking, favorable-seed choice, or
outcome-conditioned extension: G18 either passes every condition or closes as
negative development evidence.

## 3. Soft-cap state machine and retention contract

For every candidate scheduling window, the analyzer reconstructs the frozen
one-bit recurrence. With feasible-ready count `F`, node count `N`, and
`C=(5N+3)//4`, only a closed-valve current-overflow window with `F>C` may
admit the first `C` players. `F=C`, every at/below-cap first overflow, and
every adjacent overflow must release the complete feasible-ready sequence.

The analyzer checks current overflow, valve state before and after, all five
admission modes, applicability/material-pass flags, numerator, denominator,
exact scaled-node operand, rounded cap, admitted/deferred counts, admission
limit, complete-set order hashes, arrival range, solver-set cardinality, and
the readiness, feasibility, legacy-order, prefix, bound, cap-arithmetic,
admission-rule, state-transition, and dispatch-set counters. A drift, omitted
window, adjacent positive deferral, or invalid count fails activation and
runtime integrity.

A QC-valid zero-completion run remains in the 30-row population with zero
throughput and `qpr=null`; it fails the gate and is not a retry. Signed paired
differences, every per-seed ratio and win/nonloss, five-seed means/SDs,
descriptive paired 95% t intervals, every leave-one-seed-out mean,
completion, latency, cost, QPR factors, queue/resource/wait metrics, runtime
evidence, activation telemetry, and scheduler overhead are retained.

## 4. Verification and authorization boundary

- focused G18 analyzer tests: 15/15 passed;
- complete analysis regression suite: 196/196 passed in 87.63 seconds;
- Python compilation and Black formatting checks: passed;
- actual-manifest fail-closed validation and independent selection inspection:
  passed;
- selection run/spec/matrix counts: exactly 30/30/30;
- unique paired tapes / reference hashes: exactly 15/30;
- manifest order and ordinals 1--30: exact low--middle--high;
- online parent/canonical result directories at freeze: absent; and
- result-conditioned selection flag: false.

After this audit and exact selection are committed, one result-blind
execution of all 30 selected specifications in frozen manifest order is
authorized. Execution may be operationally checkpointed after each complete
10-run load block, but no loadwise outcome may stop, extend, replace, or alter
the remaining fixed population. Retries remain limited to the existing
technical-QC policy. Every first QC-valid outcome, including an unfavorable
candidate result, must be retained.

Strong-baseline construction/execution remains blocked unless G18 passes all
nine conditions. Confirmation seeds, formal replay, figures, manuscript
performance claims, heterogeneous runs, scalability, and burst experiments
remain blocked at this checkpoint.
