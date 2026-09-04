# G16 Overflow-Magnitude Valve Development Result Audit

Date: 2026-09-04 (Asia/Shanghai)

Analyzer/selection commits: `563f68da95694d51b58de9f9b0c9642f4004134e`,
`1975555c786b4a7b2b542e46da9d8790539c8d5a`

Status: `complete_g16_development_gate_failed_strong_baselines_blocked`

## 1. Complete retained population

The one authorized result-blind invocation executed all 30 frozen C0/G16 x
low/middle/high x D111--D115 specifications in manifest order. All 30 runs
canonicalized on attempt 1. There were no technical retries, seed
replacements, run omissions, result-conditioned extensions, or quarantined
attempts. Reconciliation found all 30 paths exact and performed zero repairs.

Independent validation reopened every canonical directory against the bound
manifest. All 30 runs are QC-valid, have positive fixed-window completion,
and have defined run-level QPR. The 450-file canonical online tree contains
29,465,046 bytes and has sorted inventory hash
`42dcc3f4c3461b07a47eb5a48ce8b892c810f21aabccde8a02bd4ca238b958c3`.
The partial and quarantine trees contain zero files.

The append-only online ledger contains 62 valid chained events, has final
event hash
`5ef27a3a6a4e57a7dc1949ff4c68b12d53d98c3eb540921a3312f891028d57fa`,
and its 59,096-byte file has SHA-256
`9e36a4f171ae8d394480c13eb9e09c2fea12a2991a26536cb31c4fb3db264f2a`.
The reconciliation report has canonical document hash
`baedd52e75b8ad1c49e4f347c4f8837416dcb0fba897cc917ba3a3276a2dbef7`
and file SHA-256
`9d7f9bd35e1ec4cca260fe6078a7c17f1d00311219b27700c5ebeeec026e16fc`.

## 2. Frozen gate outcome

The frozen analyzer returned `complete_g16_development_gate_failed` and
selected no candidate. Its complete 400,457-byte report has canonical
document hash
`c1856ac8748412b303ee8f131533267c1041c346893624fff21a11e5bc3aea37`
and file SHA-256
`7fdf5456cdb68d12dd738658813729065669d9ed5f57c57e658414ca695000e3`.
An independent second implementation recomputed throughput, latency, cost,
QPR, completion, all 30 run contributions, method means, ratios, and paired
wins/nonlosses directly from canonical summaries. It matched reported
throughput, latency, cost, and completion exactly; the maximum QPR absolute
difference was numerical roundoff of `6.94e-18`.

| Load | G16 throughput mean | G16/C0 | G16 QPR mean | G16/C0 | Joint wins / nonlosses |
|---|---:|---:|---:|---:|---:|
| low | 1.5654 req/ms | 1.00772 | 0.0327844 | 1.00810 | 1/5 / 3/5 |
| middle | 0.4562 req/ms | 0.94451 | 0.00435644 | 0.98995 | 1/5 / 3/5 |
| high | 0.5732 req/ms | 1.03056 | 0.00471341 | 1.10285 | 4/5 / 4/5 |

G16 passes exact population/runtime identity, complete magnitude-valve
activation, and policy-overhead conditions (conditions 1, 7, and 9). It fails
the all-load dual-mean, paired win/nonloss, per-seed floor,
leave-one-seed-out, completion/latency, and strict runtime-integrity
conditions (2--6 and 8).

Low-load arithmetic means improve slightly in both primary metrics, but only
D111 is a strict paired joint win. D112 and D114 are exact ties, D113 loses
both metrics, and D115 gains throughput while losing QPR. Omitting D111 makes
both low-load mean paired differences negative, so low fails both paired and
leave-one-seed-out robustness gates.

Middle load is the primary performance failure. G16 throughput and QPR are
5.55% and 1.01% below C0. D112 has retained throughput/QPR ratios of
0.57053/0.45972, violating both 0.80 floors; only D113 is a joint win. All
middle QPR leave-one-seed-out differences and four of five throughput
leave-one-seed-out differences are negative.

High load satisfies its mean, paired, floor, and leave-one-seed-out primary
tests. Four seeds are strict joint wins; D111 has equal throughput and a
slightly lower QPR. Every high-load leave-one-seed-out primary difference
remains positive, so the gain does not depend on one favorable seed.

Mean completion/latency are 0.81500/137.63 ms for G16 versus
0.80880/137.24 ms for C0 at low load, 0.18295/220.08 ms versus
0.19345/245.59 ms at middle load, and 0.08261/234.18 ms versus
0.08015/238.49 ms at high load. Low and high pass the secondary gate. Middle
has lower latency but fails because completion is below C0. The
candidate/control placement-policy wall-time ratios are 1.1191, 0.9800, and
0.9437, all below the frozen 1.50 cap.

## 3. Mechanism activation and runtime integrity

The magnitude valve is genuinely exercised. The numbers of seeds with at
least one material first-overflow bounded window are 3/5, 3/5, and 5/5 at
low, middle, and high load. Eleven runs across all three loads record
below-threshold first-overflow release, and ten runs across all three loads
record persistent-overflow full release.

Across all 15 candidate runs, 753 material first-overflow windows defer 9,105
feasible players, 499 below-threshold first-overflow windows release the
complete feasible-ready set, and 1,201 adjacent persistent-overflow windows
also release the full set. No positive-deferral episode exceeds one window.
All readiness, feasibility, legacy-order, prefix, bound,
magnitude-comparison, admission-rule, state-transition, and dispatch-set
violation totals are zero.

C0 records 14,728 strict-PNE windows and 14,727 offline-reference hits among
14,729 active windows. G16 records 14,739 strict-PNE windows and 14,737
offline-reference hits among 14,740 active windows. Five retained high-load
window exceptions make condition 8 fail:

- high D111 C0 frame 86 loads the retained negative reference
  `-267.3174743652344`;
- high D111 G16 frames 84 and 86 load retained negative references
  `-490.8881530761719` and `-267.3174743652344`;
- high D113 C0 frame 911 reaches the unchanged inner-iteration limit for 27
  assigned players, so no reference is requested; and
- high D112 G16 frame 631 reaches the same limit for 32 assigned players, so
  no reference is requested.

The three negative-table observations were already disclosed and retained in
the reference audit. The two iteration-limit observations are also retained.
Runtime integrity is not the deciding weakness: G16 independently fails five
performance/robustness/secondary conditions.

## 4. Evidence-bounded interpretation

**Observation.** The exact `4F>=5N` predicate activates cleanly, preserves the
frozen order and one-bit recurrence, adds bounded scheduler overhead, and
retains a robust high-load throughput/QPR gain. It does not preserve middle
completion/throughput and does not make low-load gains seed-robust.

**Interpretation.** Magnitude-gating removes many mild-overflow deferrals but
still bounds hundreds of material first-overflow windows. The retained data
show that this behavior is beneficial under sustained high pressure but can
be costly in middle-load traces, especially D112. The outcome rejects the
claim that one fixed `1.25N` threshold solves the full across-load objective;
it does not justify changing the threshold after seeing these results.

**Implication.** G16 may not be compared with strong baselines, confirmed,
replayed on formal seeds, used in a figure, or used for a manuscript
performance claim. D111--D115 are exhausted development evidence and cannot
be rerun, filtered, or reused to validate a successor.

**Next step.** Only a separately preregistered read-only diagnosis over all
15 retained C0/G16 pairs may test whether outcome differences are associated
with activation intensity, bounded-player mass, overflow persistence, or
another already logged state variable. A successor is admissible only if
that diagnosis gives a result-independent operational rule and a fresh seed
bank; this result audit alone authorizes no scheduler edit or sampling.

## 5. Immutable archive

The complete G16 run root was copied without deletion to:

`E:\NSEsche_experiment_archives\tscv1_g16_overflow_magnitude_valve_d111_d115_8da3dbd_20260904`

Source and archive inventories match exactly: 1,092 files, 395,532,897 bytes,
and sorted inventory hash
`28a7d5a16592e928e4c63d11901f76629c75d8a5041d69955baec12e36f04c9f`.
The C-drive source remains intact.

## 6. Authorization boundary

- `g16_candidate_selected=false`;
- `g16_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_successor_diagnosis_authorized=true`.
