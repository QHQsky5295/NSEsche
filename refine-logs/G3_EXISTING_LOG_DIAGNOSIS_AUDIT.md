# G3 Existing-Log Mechanism Diagnosis Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: complete observation-only diagnosis; no candidate effect estimated;
scarcity/order counterfactual is the only authorized next diagnostic;
`D71_authorized=false`

## 1. Scope and integrity

This audit applies the frozen
`G3_MECHANISM_DIAGNOSIS_PREREGISTRATION.md` to already retained runs. It does
not add an online run, estimate a new candidate, reopen G1/G2 selection, or
exclude a seed after observing its result.

- G1 input: all 200 homogeneous-low online runs in Q61--Q80, including all 20
  state-matched NSESche/FaaSRank pairs.
- G2 input: all 135 D66--D70 online runs, including all 90 NSESche candidate
  runs.
- Missing, incomplete, or quarantined input: zero.
- Each per-request stream has exactly the completed-request count stated in
  its run summary and every event is complete.
- Formal aggregation weights each of the 20 seeds equally; requests are not
  treated as independent repetitions.
- Candidate effect estimation: false.
- New online runs: zero.

Machine-readable artifacts:

- `G3_EXISTING_LOG_DIAGNOSIS.json`, 811,071 bytes, SHA-256
  `8f5e36380450b3281389fb5ebbb8da7ff37e16714ed2fce923da9ef3ed953c62`;
- `G3_EXISTING_LOG_DIAGNOSIS_RUNS.csv`, 281,789 bytes, SHA-256
  `fdb3f461814e5fd39d218ffe59a4de65a665a11cdee04edefad91408de51d6ae`.

## 2. Formal-pair operational decomposition

The complete 20-seed means are:

| Metric | FaaSRank | NSESche | NSESche direction |
|---|---:|---:|---|
| Throughput (req/ms) | 1.598100 | 1.581500 | worse |
| Completion ratio | 0.830015 | 0.821267 | worse |
| Mean latency (ms) | 89.4752 | 97.9426 | worse |
| p95 latency (ms) | 353.75 | 373.85 | worse |
| p99 latency (ms) | 463.30 | 458.75 | better |
| Cost/completed | 0.541000 | 0.533315 | better |
| QPR | 0.064039 | 0.058107 | worse |
| Cold-start event share | 0.175359 | 0.245413 | worse |

The preregistered primary positive stage is cold-start wait. NSESche minus
FaaSRank is:

| Completed-function stage | Mean difference (ms) | Positive seeds / 20 |
|---|---:|---:|
| Schedule wait | -0.010369 | 10 |
| Cold-start wait | +3.627739 | 15 |
| Data wait | +0.029422 | 18 (one tie) |
| Execution | +0.118410 | 11 |

Data wait is more often positive but is two orders of magnitude smaller than
the cold-start difference. The observed low-load deficit is therefore not a
generic scheduling-wait or execution-time regression; its largest mean stage
component is additional cold-start exposure.

## 3. Paper-welfare alignment check

NSESche has *higher* post-hoc paper welfare per assigned player, 37.436913
versus 36.940135 for FaaSRank (about +1.35%), while its operational QPR is
9.26% lower. Its per-player cost and externality components are also lower:
1.290868 versus 1.342383 and 0.371143 versus 0.778745. Quality and contribution
components are slightly higher.

This comparison does not call the FaaSRank assignment a Nash equilibrium and
is not a same-state causal effect. It does establish the intended diagnostic
fact: maximizing the implemented manuscript objective can rank NSESche's
realized path more highly while the runtime exposes more cold starts and
produces worse QPR. A formula change is neither authorized nor implied;
the admissible search space is deterministic selection among solutions that
still satisfy the existing strict Eq. (15) best-response rule.

## 4. Complete preregistered association table

All 24 Spearman correlations are reported below. They are exploratory
mechanism evidence, not confirmatory p-values.

| Diagnostic | rho vs T gap | rho vs QPR gap | `abs(rho) >= 0.40` |
|---|---:|---:|---|
| Waiting share | -0.1564 | +0.3068 | no |
| Candidates/player | +0.1940 | +0.0045 | no |
| Selected-starting share | -0.0827 | -0.4962 | QPR |
| Warm-bypass share | -0.0346 | -0.5218 | QPR |
| Placement dispersion | -0.1263 | +0.4421 | QPR |
| Co-location conflict ratio | +0.0301 | -0.2722 | no |
| Cross-node placement ratio | -0.1338 | +0.3083 | no |
| Assignment moves/player | +0.1714 | -0.1970 | no |
| Outer-feedback active share | -0.0541 | +0.2827 | no |
| Mean price spread | -0.0286 | -0.0872 | no |
| Queue area/arrival | -0.4782 | +0.4316 | T and QPR |
| Mean node-memory utilization | +0.0211 | +0.5534 | QPR |

Selected-starting and warm-bypass shares meet the numerical threshold in the
expected QPR direction, but they belong to the already rejected warm/finish/
initialization intervention family and do not authorize another direct warm
guard. Solver movement, price spread, and outer feedback do not qualify.
Placement dispersion, queue area, and memory utilization support the frozen
feasibility/concentration branch, while the opposite outcome directions for
some quantities must remain visible rather than being reduced to a one-sided
claim.

## 5. Six-cell consistency and rejected explanations

For unchanged C0 `ready_order` in G2, selected-starting share ranges from
0.284 to 0.356 and warm-bypass share from 0.194 to 0.272 across the six cells.
Waiting share ranges from 0.259 to 0.488, and placement dispersion from 0.734
to 0.869. Active inner stability is 99.92--100%; explicit inner/outer limit
rates remain approximately zero. This is inconsistent with a pure
convergence-budget explanation and does not reopen that candidate family.

The counterexamples are also retained. Some seeds have a large QPR loss with
greater cold-start wait, but Q74 loses substantial throughput while its mean
cold-start wait is slightly lower than FaaSRank. Hence cold starts explain the
dominant mean QPR pathway, not every throughput tail. Any successor must be
tested on all fixed seeds and all six cells rather than tuned to one favorable
case.

## 6. Frozen decision

The existing-log stage is closed with the following decision:

1. No previously tried direct warm, finish, initialization, or iteration-
   budget refinement is reopened.
2. No feedback or convergence candidate is authorized by these associations.
3. The only authorized next step is an observation-only scarcity/order
   counterfactual on the same solver snapshots and shared feasible candidate
   sets. It may compare a small preregistered set of deterministic player
   orders while preserving the same utility and strict best responses. It
   must not feed commands back to the simulator.
4. The counterfactual must report every order's PNE hash, paper welfare,
   projected-finish/cold-path proxies, dispersion, and status on every retained
   diagnostic state. It is a falsification step, not a candidate screen.
5. Only a directionally consistent result may justify a separate G3 candidate
   preregistration and a fresh D71--D75 development bank.

Accordingly, `candidate_effect_estimation=false`, `D71_authorized=false`, and
`homogeneous_middle_formal_authorized=false`. No main-paper group is ready.
