# G18 Overflow Soft-Cap Valve Development Result Audit

Date: 2026-09-05 (Asia/Shanghai)

Analyzer/selection commits: `8b95ca8cf997a22b0d0017630e30c37aa4f6b82a`,
`a3a12fdc31745406382672e39f7e210b4fa4e069`

Status: `complete_g18_development_gate_failed_strong_baselines_blocked`

## 1. Complete retained population

The one authorized result-blind population executed all 30 frozen C0/G18 x
low/middle/high x D116--D120 specifications in selection order, operationally
checkpointed after each complete 10-run load block. All 30 runs canonicalized
on attempt 1. There were no technical retries, seed replacements, omissions,
outcome-conditioned extensions, or quarantined attempts.

Independent path reconciliation reopened every canonical directory against
the bound manifest. All 30 paths were already exact and zero repairs were
performed. Every row is QC-valid, has positive fixed-window completion, and
has defined run-level QPR. The 450-file canonical online tree contains
29,096,270 bytes and has sorted inventory hash
`6836c782cb102107da21d7e4ab6c4312f83e7a254f3553a51bc62e56bc74b58d`.
The partial and quarantine trees contain zero files.

The append-only online ledger contains 66 valid chained events because three
complete result-blind load blocks were invoked. Its final event hash is
`8e95b5e37b53fc5d5105bd360998e8ac918648710535ec46b3a66ce576f43be2`;
the 61,040-byte file has SHA-256
`afd8b83e2dbc93980f34706eb1317f0ba805dfd35339bc8ac7b62c9c7de422dc`.
The 26,455-byte reconciliation report has document/file hashes
`9ad6f6344a50f2bfe9114d874ae7add7a64e291bf5e76d706cfc65e093a796a3`/
`fe99a2ef1872413e0d60183568d2b41fcdf33553339394cdebec598924b52e00`.

## 2. Frozen gate outcome

The frozen analyzer returned `complete_g18_development_gate_failed` and
selected no candidate. Its complete 401,906-byte report has canonical
document hash
`b9b47c1fb4d8a36b222d922e88e3df06879b3398eab8864c865deeb21ec797b3`
and file SHA-256
`e0ecd5f07ac9e516781797591ac4d70d0f04cd123e48e8a3c6ffe773b21228bc`.
An independent implementation recomputed throughput, drained latency,
simulator cost per completion, QPR, completion, policy time, all 30 run
contributions, arithmetic means, ratios, and paired wins/nonlosses directly
from canonical summaries. Every recomputed scalar matched the frozen report
exactly; the maximum absolute error was zero for all five audited metrics.

| Load | G18 throughput mean | G18/C0 | G18 QPR mean | G18/C0 | Joint wins / nonlosses |
|---|---:|---:|---:|---:|---:|
| low | 1.5866 req/ms | 0.999874 | 0.0425601 | 1.001917 | 1/5 / 4/5 |
| middle | 1.5998 req/ms | 1.000000 | 0.0778602 | 0.998613 | 1/5 / 4/5 |
| high | 1.4332 req/ms | 0.980972 | 0.0412827 | 0.982283 | 2/5 / 2/5 |

G18 passes exact population/runtime identity, complete soft-cap activation,
and policy-overhead conditions (1, 7, and 9). It fails the all-load dual-mean,
paired win/nonloss, per-seed floor, leave-one-seed-out,
completion/latency, and strict runtime-integrity conditions (2--6 and 8).

At low load, D116, D117, and D119 are exact ties. D118 gains 0.010 req/ms and
a small amount of QPR; D120 loses 0.011 req/ms while gaining QPR. The mean
throughput therefore falls by 0.0002 req/ms even though mean QPR rises 0.192%.
Only one of the five throughput leave-one-out differences is nonnegative, so
the effect is not seed-robust.

At middle load, D117, D118, and D120 are exact ties. D116 gains 0.006 req/ms
and QPR, while D119 loses the same 0.006 req/ms and 1.50% QPR. Decimal mean
throughput ties C0, but the strict-above condition fails and mean QPR falls
0.139%. Only one of five leave-one-out differences is nonnegative for either
primary metric.

At high load, D116 and D119 are joint wins, whereas D117, D118, and D120 lose
throughput and QPR. D120 is the material safety failure: retained
candidate/control throughput and QPR ratios are 0.72048 and 0.52009, below
the preregistered 0.80 floor. All five high-load throughput leave-one-out
differences and four of five QPR leave-one-out differences are negative.

Mean completion/latency are 0.821918/124.35 ms for G18 versus
0.822018/124.34 ms for C0 at low, 0.636104/228.24 ms versus
0.636115/226.62 ms at middle, and 0.209502/316.19 ms versus
0.213501/318.07 ms at high. G18 misses the nondecreasing-completion condition
at every load. Candidate/control policy-wall-time ratios are 1.0313, 1.0029,
and 1.0026, safely below the fixed 1.50 limit.

## 3. Mechanism activation and runtime integrity

The soft-cap valve is genuinely exercised. Positive material deferral occurs
in 2/5, 2/5, and 5/5 seeds at low, middle, and high load. Across all candidate
runs, 490 material first-overflow windows defer 3,432 feasible players, 527
at/below-cap first-overflow windows release the complete feasible-ready set,
and 701 adjacent persistent-overflow windows also release the full set. No
positive-deferral episode exceeds one window. All readiness, feasibility,
legacy-order, prefix, bound, cap-arithmetic, admission-rule,
state-transition, and dispatch-set violation totals are zero.

C0 records 14,672 strict-PNE windows and 14,672 offline-reference hits among
14,681 active windows. G18 records 14,673 strict-PNE windows and 14,673
offline-reference hits among the same number of active windows. Seventeen
retained high-load windows reach the unchanged inner-iteration limit: eight
in high D117 C0, one in high D120 C0, and eight in high D117 G18. No offline
reference is requested for those uncertified assignments, so condition 8
fails. Unlike G16, every loaded G18 offline reference is strictly positive;
the missing hits are iteration-limit consequences, not bad reference tables.
Runtime integrity is not the deciding weakness because G18 independently
fails all five performance/robustness/secondary conditions 2--6.

## 4. Evidence-bounded interpretation

**Observation.** Replacing the hard `N` first-overflow cap with
`ceil(5N/4)` nearly neutralizes low/middle aggregate throughput changes and
keeps scheduler overhead small. It does not produce robust dual-metric gains,
and high D120 still suffers a large completion, throughput, and QPR loss.

**Interpretation.** A larger one-window prefix reduces intervention intensity
but does not make burst deferral outcome-safe. Low/middle contain many exact
ties because the material soft-cap rule activates in only two seeds per load;
where it activates, sign and magnitude remain state-dependent. Under high
pressure, 490 material windows and 3,432 deferred players are sufficient for
a rare but severe negative trajectory. These data reject a fixed soft-cap
action as the across-load solution and do not justify choosing a new cap after
seeing D120.

**Implication.** G18 may not be compared with strong baselines, confirmed,
replayed on formal seeds, used in a figure, or used for a manuscript
performance claim. D116--D120 are exhausted development evidence and cannot
be rerun, filtered, or reused to validate a successor.

**Next step.** Only a separately preregistered read-only diagnosis over all 15
retained C0/G18 pairs may test whether signed effects are associated with
intervention mass, episode timing, queue state, or another already logged
pre-decision variable. A successor requires a result-independent operational
rule and a fresh seed bank; this audit alone authorizes no scheduler edit or
sampling.

## 5. Authorization boundary

- `g18_candidate_selected=false`;
- `g18_strong_baseline_addendum_authorized=false`;
- `confirmation_sampling_authorized=false`;
- `formal_progression_authorized=false`;
- `paper_figure_or_claim_authorized=false`; and
- `read_only_successor_diagnosis_authorized=true`.

