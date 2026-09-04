# G16 Overflow-Magnitude Valve Analyzer and Selection Audit

Date: 2026-09-04 (Asia/Shanghai)

Offline-reference commit: `7711f85815c579276eb0d2cd409d8f34d57ec47a`

Analyzer commit: `563f68da95694d51b58de9f9b0c9642f4004134e`

Status: `zero_result_gate_frozen_exact_30_run_online_execution_authorized_once`

## 1. Result-free selection boundary

The G16 online parent directory did not exist when the selector was invoked.
The selector refuses to run if either that parent or its canonical child
already exists. It independently revalidated the complete reference-bound
manifest and rehashed the fixed runtime, all 15 workload tapes, all 30 offline
reference tables, and all 30 reference receipts before constructing the
selection.

The selection contains exactly the 30 manifest-ordered C0/G16 x
low/middle/high x D111--D115 specifications: 15 rows per method, 10 rows per
load, and six rows per seed. Run IDs, run-spec hashes, and matrix identities
are unique; each load/seed pair shares exactly one tape; every arm has a
distinct mode-specific reference hash. No online throughput, QPR, latency,
cost, completion, scheduler trace, or policy timing existed at freeze time.

| Artifact | Bytes | SHA-256 or object hash |
|---|---:|---|
| `g16.online.selection.json` file | 29,484 | `0c9eb944bc015047de3503ad017ce24e0aa729f9d88e9188f0a5bcad1174bdd4` |
| selection canonical document | n/a | `94fc4f533731c479a2297b21a0b4ac281c4997f7b964a03acd6e45ba71c21458` |
| analyzer source | 47,946 | `0c3721113dbb3dc2abfe6465a66398c1a797504ecdc95eb4f773fd3098c6f8e4` |
| reference-bound manifest file | 846,507 | `bdda8e7b8f790c692760e1eb5eb7369d0e4f078bb3140883e6db514fae63eb65` |
| reference-bound manifest object | n/a | `fbea597e13a10d032b5c9483c2b754d061d6d19062389e41ae02ffd7588cb50e` |

The selection embeds the committed analyzer's absolute path and source hash.
Any later analyzer edit invalidates analysis rather than silently changing the
gate.

## 2. Frozen nine-condition gate

The sole G16 candidate is evaluated against paired C0 by this exact
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
7. at least one seed per load records a material first-overflow bounded
   window, at least three runs across at least two loads record
   below-threshold first-overflow release, at least three runs across at least
   two loads record persistent-overflow release, no actual positive-deferral
   episode exceeds one window, and all nine telemetry violation totals are
   zero;
8. strict Eq. (15), strict-PNE, offline-reference, complete-dispatch,
   runtime-identity, and G16 magnitude-state-machine contracts pass for every
   arm; and
9. the ratio of candidate/control arithmetic means of per-run
   placement-policy wall time is at most 1.50 at every load.

The G16 analyzer reuses the already-frozen G12 metric extraction and paired
summary core by exact method/seed identity relabeling only. It independently
evaluates G16-specific conditions 3, 5, 6, and 7. There is no ranking,
favorable-seed choice, or outcome-conditioned extension: G16 either passes
every condition or closes as negative development evidence.

## 3. Magnitude-state-machine and retention contract

For every candidate scheduling window, the analyzer reconstructs the frozen
one-bit recurrence and exact widened-integer comparison from the complete
ordered trace. With feasible-ready count `F` and node count `N`, it requires
the logged operands to be exactly `4F` and `5N`; only a closed-valve current
overflow with `4F>=5N` may admit the first `N` players. A below-threshold
first overflow and every adjacent overflow must release the complete
feasible-ready sequence.

The analyzer checks current overflow, valve state before and after, all five
admission modes, magnitude applicability/pass flags, threshold constants,
admitted/deferred counts, admission limit, complete-set order hashes, arrival
range, solver-set cardinality, and the readiness, feasibility, legacy-order,
prefix, bound, magnitude-comparison, admission-rule, state-transition, and
dispatch-set counters. A drift, omitted window, adjacent positive deferral,
or invalid count fails both activation and runtime integrity.

A QC-valid zero-completion run remains in the 30-row population with zero
throughput and `qpr=null`; it fails the gate and is not a retry. Signed paired
differences, every per-seed ratio and win/nonloss, five-seed means/SDs,
descriptive paired 95% t intervals, every leave-one-seed-out mean,
completion, latency, cost, QPR factors, queue/resource/wait metrics, runtime
evidence, activation telemetry, and scheduler overhead are retained.

## 4. Verification and authorization boundary

- focused G16 analyzer tests: 15/15 passed;
- complete analysis regression suite: 172/172 passed in 86.265 seconds;
- Python compilation and Black formatting checks: passed;
- actual-manifest fail-closed validation and independent output inspection:
  passed;
- selection run/spec/matrix counts: exactly 30/30/30;
- unique paired tapes / reference hashes: exactly 15/30;
- manifest execution order and ordinals 1--30: exact;
- online parent/canonical result directories at freeze: absent; and
- result-conditioned selection flag: false.

After this audit and exact selection are committed, one result-blind execution
of all 30 selected specifications in manifest order is authorized. Retries
remain limited to the existing technical-QC policy. Every first QC-valid
outcome, including an unfavorable candidate result, must be retained.

Strong-baseline construction/execution remains blocked unless G16 passes all
nine conditions. Confirmation seeds, formal replay, figures, and manuscript
performance claims remain blocked regardless of this development selection.
