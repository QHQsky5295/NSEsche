# G1 corrected-runtime result audit

Date: 2026-09-03 (Asia/Shanghai)

Status: D44 technical gate passed; D61--D65 development screen complete;
`ready_order` selected; no main-paper experiment is paper-ready closed

## 1. Decision

The frozen G1 global-maximin rule selected C0 `ready_order`.  This is the only
candidate whose minimum of the twelve six-cell throughput/QPR ratios relative
to C0 is 1.000.  C1 `ready_finish_tie` falls to 0.9427; C2 `formula` falls to
0.4151.  The result authorizes an independent qualification protocol at the
screen level, but the user authorization covered only G1.  Q61--Q80 has not
been preregistered, captured, or run.

G1 is not a baseline comparison and is not formal paper evidence.  It cannot
support the claim that NSESche is first.  No main-paper experiment group is
`paper_ready_closed`.

## 2. Frozen provenance

- Preregistration/protocol commit:
  `98f822cf2dcb878024a2ca39cc56533895ea692c`.
- Runtime source commit:
  `98f822cf2dcb878024a2ca39cc56533895ea692c`.
- Runtime binary SHA-256:
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Runtime binary size: 4,707,328 bytes.
- Runtime binary:
  `serverless_sim/target_g1_corrected_runtime_98f822c/release/serverless_sim.exe`.
- Run root:
  `runs/tscv1_g1_corrected_98f822c_20260903`.
- Ready-screen manifest hash:
  `500fb9c91a0a8f07b4ade8a5d6097413b5e189a74120295585df1fc62b89b9c2`.
- Ready-screen file SHA-256:
  `11a1e7a21733253b65a9adc22405c0b18b517dd96856860829fb1d7141577d51`.
- Selection document hash:
  `30f15c1a17549024d1b879f92a5d8cbadf50a2de6ee4143bbc751c38113a98a6`.
- Selection file SHA-256:
  `d3c318605f5ffb583e4213ef7f6c806ed74027d8f1fa38c797e31511e804f40d`.
- Selection receipt:
  `runs/tscv1_g1_corrected_98f822c_20260903/g1.selection.json`.

The paper equations were not changed.  Every candidate declared
`strict_best_response=true` and `utility_guard_relative_regret=0.0`.

## 3. D44 technical gate

The technical-only D44 tape was used to build a new state-matched reference
and replay the final binary.  Build and replay each completed 112 requests.
The gate matched 984 state pairs and the final assignment sequence, validated
1,000 policy/contract/feedback windows, and observed 1,893 feedback-trace
rounds with 909 applied rounds.  Both `strict_eq15_ready` and
`stream_contract_ready` were true; analyzer-invalid feedback rows were zero.

- Technical-gate document hash:
  `c42071eea5c7945eac4f252303bcdb6e2e2d4692406853a4f760a20d8eceb85e`.
- Technical-gate file SHA-256:
  `de53a460d57def3013173fda6330da60dabe1e83f9140a3582534180a662e4c7`.

D44 is not selection-eligible and is not a paper result.

## 4. Completed development matrix

- Seeds: exactly D61--D65.
- Cells: three loads by two topologies, 20 nodes.
- Candidates: `ready_order`, `ready_finish_tie`, and `formula`.
- Tape captures: 30/30, all attempt 1.
- State-matched reference builds: 90/90, all attempt 1.
- Candidate runs: 90/90, all attempt 1.
- Quarantined scientific attempts: zero.
- Analyzer-accepted run rows: 90/90.
- Result-conditioned seed removal/replacement: none.

There are 30 tape keys and 15 unique event-stream hashes.  The latter is
expected: topology changes the environment snapshot, while a fixed load/seed
pair retains the same workload event stream across topologies.

## 5. Frozen selection scores

| Candidate | Worst of 12 ratios | Mean of 12 ratios | Joint throughput/QPR first cells | Simplicity order |
|---|---:|---:|---:|---:|
| `ready_order` | 1.0000 | 1.0000 | 2 | 0 |
| `ready_finish_tie` | 0.9427 | 0.9923 | 1 | 1 |
| `formula` | 0.4151 | 0.9497 | 2 | 2 |

The primary rule decides the result.  Secondary and tertiary scores do not
override a worse primary minimum.

## 6. Six-cell means and control-relative evidence

| Candidate | Load | Topology | Throughput (req/ms) | Throughput/C0 | QPR | QPR/C0 | Mean latency (ms) | Mean nonconvergence |
|---|---|---|---:|---:|---:|---:|---:|---:|
| `ready_order` | low | homogeneous | 1.5810 | 1.0000 | 0.051356 | 1.0000 | 111.95 | 0.0348 |
| `ready_order` | low | heterogeneous | 1.3670 | 1.0000 | 0.041676 | 1.0000 | 110.07 | 0.0324 |
| `ready_order` | middle | homogeneous | 0.9604 | 1.0000 | 0.008407 | 1.0000 | 303.64 | 0.0744 |
| `ready_order` | middle | heterogeneous | 0.6840 | 1.0000 | 0.004906 | 1.0000 | 250.73 | 0.0540 |
| `ready_order` | high | homogeneous | 1.4168 | 1.0000 | 0.017051 | 1.0000 | 260.16 | 0.0358 |
| `ready_order` | high | heterogeneous | 0.8078 | 1.0000 | 0.004570 | 1.0000 | 287.90 | 0.0452 |
| `ready_finish_tie` | low | homogeneous | 1.5874 | 1.0040 | 0.051711 | 1.0069 | 112.23 | 0.0340 |
| `ready_finish_tie` | low | heterogeneous | 1.3670 | 1.0000 | 0.041676 | 1.0000 | 110.07 | 0.0330 |
| `ready_finish_tie` | middle | homogeneous | 0.9054 | 0.9427 | 0.008134 | 0.9674 | 311.39 | 0.0732 |
| `ready_finish_tie` | middle | heterogeneous | 0.6840 | 1.0000 | 0.004906 | 1.0000 | 250.73 | 0.0530 |
| `ready_finish_tie` | high | homogeneous | 1.4210 | 1.0030 | 0.016836 | 0.9874 | 264.46 | 0.0374 |
| `ready_finish_tie` | high | heterogeneous | 0.8058 | 0.9975 | 0.004561 | 0.9980 | 288.07 | 0.0460 |
| `formula` | low | homogeneous | 1.6212 | 1.0254 | 0.058059 | 1.1305 | 103.59 | 0.0044 |
| `formula` | low | heterogeneous | 1.3576 | 0.9931 | 0.030438 | 0.7303 | 149.76 | 0.0052 |
| `formula` | middle | homogeneous | 0.9066 | 0.9440 | 0.009034 | 1.0745 | 254.07 | 0.0148 |
| `formula` | middle | heterogeneous | 0.7618 | 1.1137 | 0.008461 | 1.7246 | 239.10 | 0.0090 |
| `formula` | high | homogeneous | 0.8768 | 0.6189 | 0.007078 | 0.4151 | 191.37 | 0.0270 |
| `formula` | high | heterogeneous | 0.6486 | 0.8029 | 0.003762 | 0.8231 | 353.20 | 0.0212 |

`formula` sharply reduces queue peaks and nonconvergence, but that benefit does
not translate into robust high-load throughput or QPR.  Selecting it would
optimize a diagnostic at the cost of the two paper-priority metrics.
`ready_finish_tie` is close to C0 but loses 5.73% throughput in the
middle/homogeneous cell.  `ready_order` is therefore the most robust frozen
candidate, not a claim that it is pointwise first in every cell.

## 7. Feedback, convergence, and difficult seeds

Across 30 runs per candidate:

| Candidate | Mean throughput | Mean QPR | Mean nonconvergence | Feedback trace rounds | Applied rounds | Applied rate |
|---|---:|---:|---:|---:|---:|---:|
| `ready_order` | 1.1362 | 0.021328 | 0.0461 | 45,845 | 16,528 | 0.3605 |
| `ready_finish_tie` | 1.1284 | 0.021304 | 0.0461 | 45,771 | 16,443 | 0.3592 |
| `formula` | 1.0288 | 0.019472 | 0.0136 | 48,418 | 18,579 | 0.3837 |

The feedback path is active in every candidate/cell.  For `ready_order`, the
mean inner-limit rate is 0.0004 and the mean outer-limit rate is 0.0011.  Its
largest observed nonconvergence rate is 0.185 in the
middle/homogeneous/D62 run; this remains in the receipt.

Two especially difficult D62 environments are shared across all candidates:

- middle/homogeneous/D62: throughput 0.020 and completion ratio 0.007758 for
  all three candidates;
- middle/heterogeneous/D62: throughput 0.027 and completion ratio 0.010473 for
  all three candidates.

Their paired equality shows that these two extremes are common environment
instances rather than a `ready_order`-specific collapse.  They were not
dropped, replaced, or rerun.  The independent 20-seed qualification must
retain the same fail-closed treatment and determine whether they materially
affect NSESche-versus-baseline ranking.

## 8. Host directory-placement incident

The Windows host intermittently renamed a successfully promoted directory to
its old `attempt-01` basename under the same canonical parent.  This affected
three tape captures, one reference build, and three candidate results.  It did
not change file contents or rerun a simulator process.

- Tape recovery required exact embedded key and tape SHA agreement before an
  in-root move; all 30 catalog entries then verified from disk.
- The reference recovery retained the source and copied the complete tree to
  the frozen key path; table, receipt, and process-observation SHA values all
  matched the 90-entry catalog.
- Each result recovery required a unique ready-manifest run ID, `qc_pass`, one
  matching ledger event, equal result SHA, and equal audit-manifest SHA.  The
  three 15-file trees were copied byte-for-byte to their exact run-ID paths;
  the recovery sources remain available.
- Commit `dda7a5a1c275450b518d5a39a36ac67e5841ad50` adds immediate
  stage-promotion recovery and a directed test.  Because one later name drift
  occurred after the immediate check, Q61--Q80 must also include deterministic
  post-stage run-ID/path reconciliation before analysis.

After recovery, the ready manifest had 90 expected run IDs, 90 exact canonical
directories, and zero missing IDs.  The G1 analyzer revalidated all run
receipts and wrote the immutable selection document.

## 9. Publication boundary and next gate

The selected candidate is now fixed as `ready_order` for the next independent
qualification.  It must not vary by load or topology.  The next authorized
scientific operation, once explicitly approved, is to preregister Q61--Q80
and execute ten methods by six cells by twenty paired seeds (1,200 runs) in
paper order: homogeneous low, middle, high, then heterogeneous low, middle,
high.  Those runs are both the corrected-runtime qualification and the E1
formal main result if and only if NSESche is first in mean throughput and mean
QPR in all six cells with complete QC.

Until that gate passes, M2/M3, figures, old-PDF numerical alignment claims,
and reviewer-facing performance claims remain unopened.
