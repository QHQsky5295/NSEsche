# G9 Request-Level Backpressure Analyzer and Selection Audit

Date: 2026-09-04 (Asia/Shanghai)

Offline-reference commit: `c12411aaa6309246a492e7cd1bc3dde963519b07`

Analyzer commit: `1cebbd3fd3d9530c3041d58afa904ce4298fdb2b`

Status: `zero_result_gate_frozen_exact_75_run_online_execution_authorized_once`

## 1. Result-free boundary

The G9 online workspace did not exist when the selector was invoked. The
selector itself refuses to run if either the registered canonical directory or
its parent online directory already exists. Consequently, the exact run list,
all thresholds, and the analyzer source hash were frozen before any candidate,
control, or baseline outcome was available.

The selection contains exactly 75 unique runs: five methods x low/middle/high
x D81--D85. Every load/seed group binds the same workload-tape hash across all
five methods. Every NSESche run binds its separately built offline-reference
hash. The selector independently rehashed the 15 unique tapes, 30 reference
tables, and the fixed runtime binary before admitting the population.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `g9.online.selection.json` | 60,744 | `053e9bd5fff960c958541c32e151eaa5a09a0d04c0ab2ec0d9148d0199595153` |
| selection document | n/a | `2e971ededd966e445c3d5134a60414c31e8eb49724e018810d3b0655f192e583` |
| analyzer source | 47,019 | `2b055dfe05fa97cdcc67bcd1efcf6077760399f981a58fae27a460735aee638a` |

The analyzer source hash is embedded in the selection and is rechecked before
analysis. Any source edit after this freeze makes the analysis fail closed.

## 2. Frozen ten-condition gate

The analyzer evaluates the following exact conjunction without threshold
weakening:

1. all 75 run IDs/specifications are unique, tape-paired, and QC-valid;
2. all 75 runs have positive completion and a defined run-level QPR;
3. the candidate has the strictly highest five-seed mean throughput at every
   load;
4. the candidate has the strictly highest five-seed mean QPR at every load;
5. versus `ready_order`, the candidate wins at least 4/5 paired seeds for both
   throughput and QPR at every load;
6. versus each of Load Least, FaaSRank, and Hiku, the paired mean difference is
   positive for both metrics at every load;
7. every candidate load/seed has throughput and QPR ratios of at least 0.80
   versus its paired control;
8. all 15 candidate runs activate the bounded oldest-live-request cohort and
   satisfy cohort, retention, and dispatch membership accounting;
9. both NSESche arms satisfy the strict Eq. (15), inner-PNE, offline-reference,
   dispatch, fixed-binary, and common execution-identity contracts; and
10. at every load, the ratio of candidate/control arithmetic means of per-run
    `placement_policy_wall_ns.mean` is at most 1.25.

Every run metric, candidate/comparator paired difference and ratio, win count,
five-seed mean, and leave-one-seed-out mean is retained in the report. Signed
negative paired differences remain valid observations. A QC-valid zero-
completion run is retained with `qpr=null` and an explicit reason; it fails the
gate but never becomes a technical retry or an omitted row.

Passing this development gate can authorize only construction of a separate
D86--D95 confirmation preregistration. It cannot authorize confirmation
sampling, formal progression, figures, or paper performance claims directly.

## 3. Verification

- focused analyzer plus G9 protocol tests: 12/12 passed;
- complete analysis suite: 98/98 passed in 104.951 seconds;
- Python compilation and Black formatting: passed;
- manifest/artifact/result-free selection dry validation: passed; and
- Git diff whitespace check: passed.

The analyzer's synthetic fixtures cover a full pass, retained zero completion,
an exact 4/5 win-threshold failure, activation failure, policy-overhead
failure, matrix incompleteness, and preservation of negative paired values.

## 4. Authorization boundary

After this audit and the selection are committed, one result-blind execution of
the exact 75 selected run specifications is authorized. Retries are limited to
the existing technical-QC policy. Scientific outcomes, including zero
completion or an unfavorable rank, are not retryable. All QC-valid results must
be retained and analyzed with the hash-bound source above.

D86--D95 confirmation remains blocked unless all ten conditions pass. Q61--Q80
formal replay, G9 figures, and any paper claim remain blocked until a separately
committed confirmation preregistration exists and passes.
