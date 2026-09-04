# G12 Global-Ready Admission Development Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Analyzer/selection commit: `92b7b49`

Status: `complete_g12_development_gate_failed_strong_baselines_blocked`

## 1. Complete retained population

The one authorized result-blind invocation executed all 30 frozen C0/G12 x
low/middle/high x D101--D105 specifications in manifest order. All 30 runs
canonicalized on attempt 1. There were no technical retries, seed replacements,
run omissions, result-conditioned extensions, or quarantined attempts.
Reconciliation found all 30 paths exact and performed zero repairs.

Independent validation reopened every canonical directory against the bound
manifest. All 30 runs are QC-valid, have positive fixed-window completion, and
have defined run-level QPR. The 450-file canonical online tree contains
28,587,427 bytes and has sorted inventory hash
`42a78c0318f78da5afe5bcf86b82a2a39dcf0db09841b92c89ee93489d658ae2`.
The partial tree contains zero files.

The append-only online ledger contains 62 valid chained events, has final event
hash `bf0832f6439c79e2a2b292e1febbc270119cf5f91a3066397642e271c41ec60b`,
and file SHA-256
`14a6621715c373fb71adb1723f234c2e1ac69930431755f7853abb2dee22326e`.
The reconciliation report has canonical document hash
`6ea067cdaa8dd2cb18eea329989e0f7f33766bb8b09d825d67dad54d6e945028`
and file SHA-256
`353c6b622d995562a6f696987860205c402893b78c8b736756e278204c2fbe1f`.

## 2. Frozen gate outcome

The frozen analyzer returned `complete_g12_development_gate_failed` and
selected no candidate. Its complete 374,552-byte report has canonical document
hash `7fc6f143cef017e785077b939c27c62b3eb0197f56ec498b9cc1132e22b20e52`
and file SHA-256
`6c5e0882248a5c0078e0c7f0221fefdfd88d2e2c931b8d4342b7fd41bf78f5a5`.
An independent second implementation recomputed throughput, latency, cost,
QPR, and all 30 run contributions directly from canonical summary files and
matched every reported aggregate exactly (maximum absolute difference 0).

| Load | G12 throughput mean | G12/C0 | G12 QPR mean | G12/C0 | Paired wins T/QPR/joint |
|---|---:|---:|---:|---:|---:|
| low | 1.7686 req/ms | 0.99763 | 0.0907906 | 1.00135 | 1/2/1 |
| middle | 0.9364 req/ms | 1.00086 | 0.0202619 | 1.01242 | 3/3/3 |
| high | 1.0100 req/ms | 0.98768 | 0.00820764 | 0.95754 | 1/0/0 |

G12 passes population integrity and policy-overhead conditions (1 and 9). It
fails the dual-mean, paired-win, per-seed floor, leave-one-seed-out,
completion/latency, activation, and strict runtime-integrity conditions
(2--8).

The sole 0.80-floor failure is high D101: throughput/C0 is 0.89500 and QPR/C0
is 0.56969. All five high-load leave-one-seed-out throughput and QPR means are
negative. Low-load throughput also has four negative leave-one-out means; the
middle-load throughput effect is only marginal and changes sign under three
of five seed omissions. The middle-load 3/3/3 paired-win result is therefore
retained but cannot qualify a mechanism that must work across all loads.

Mean completion/latency are 0.91486/75.49 ms for G12 versus 0.91697/76.84 ms
for C0 at low load, 0.38007/231.26 ms versus 0.37976/234.15 ms at middle load,
and 0.14372/301.71 ms versus 0.14547/269.92 ms at high load. Thus the candidate
slightly lowers latency at low/middle load but lowers completion at low and
high load and materially raises high-load latency. Its placement-policy
wall-time ratios are 1.0347, 1.0107, and 1.2543, all below the fixed 1.50 cap.

## 3. Mechanism activation and runtime integrity

The candidate's exact global-ready prefix rule is genuinely exercised in 2/5,
4/5, and 5/5 seeds at low, middle, and high load. All readiness, feasibility,
legacy-order, prefix, bound, and dispatch-set violation totals are zero. The
low-load 3/5 activation threshold fails. Across all candidate runs, 5,264,553
feasible-ready player observations produce 131,888 admissions and 5,132,665
deferred observations. High D101 alone contributes 5,089,902 deferrals and is
also the severe throughput/QPR tail. This is direct evidence that repeated
fixed-`N` release can accumulate excessive ready backlog in one high-pressure
trajectory.

G12 records 14,705 strict-PNE/reference windows among 14,706 active windows.
High D103 frame 706 reaches the unchanged inner-iteration limit for its 20
admitted players, so no offline reference is requested for that unstable
state. C0 records 14,690 strict-PNE and 14,688 reference windows among 14,695
active windows: five windows reach the same unchanged inner limit, and two
stable states retrieve retained negative reference values (-121.681 and
-1330.529), producing explicit `offline_table_nonpositive` terminations.
These are valid retained outcomes, not retry conditions.

The runtime exceptions make condition 8 fail, but they do not drive the
negative decision: G12 separately fails six performance/robustness/activation
conditions, including both primary means and every paired high-load QPR
comparison.

## 4. Evidence-bounded interpretation

**Observation.** The global-ready prefix is structurally correct and has low
policy overhead. It produces a small middle-load QPR improvement and modest
low/middle latency reductions, but its fixed one-node-count release quantum
does not preserve throughput across loads. Under the strongest observed
backlog it repeatedly defers work, reducing completion and increasing latency
and cost.

**Interpretation.** Merely bounding each scheduling window to `N` players is
not a generally beneficial congestion-control rule. The mechanism has no
memory of already admitted but unfinished work and no principled way to make
the release budget work-conserving when demand is high. This interpretation is
development evidence, not a manuscript claim.

**Implication.** G12 may not be compared with strong baselines, confirmed,
replayed on Q61--Q80, or used in a figure. D101--D105 are exhausted
development evidence and cannot be rerun, filtered, or reused to validate a
successor.

**Next step.** A read-only diagnosis may use all retained G12 traces to test
whether the failure is specifically associated with accumulated admitted-but-
unfinished work and repeated deferral. At most one genuinely new, load-blind
successor may then be preregistered on a fresh seed bank. No new online
sampling is authorized by this result audit alone.

## 5. Immutable archive

The complete G12 run root was copied without deletion to:

`E:\NSEsche_experiment_archives\tscv1_g12_global_ready_admission_d101_d105_c4e31a9_20260904`

Source and archive inventories match exactly: 1,092 files, 390,090,635 bytes,
and sorted inventory hash
`5a41481e09fa159364741b8158e385367c81920350e3a1231ffe3baaf1f1b20a`.
The C-drive source remains intact.

## 6. Authorization boundary

- `g12_candidate_selected=false`;
- `g12_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_successor_diagnosis_authorized=true`.
