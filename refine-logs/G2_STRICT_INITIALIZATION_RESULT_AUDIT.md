# G2 Strict-Initialization Result Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: complete development family; C0 `ready_order` selected by the frozen
global rule; homogeneous-low baseline gate failed; no formal confirmation is
authorized

## 1. Scope and evidence boundary

G2 is the preregistered D66--D70 development bank for three Algorithm 1
feasible-initialization policies. It is not a formal or paper-eligible result
bank. The paper utility, Eqs. (1)--(20), strict Eq. (15) best-response updates,
common HPA, workload profiles, source revision, executable, and all selection
rules remained frozen throughout execution.

- Ready manifest document hash:
  `8173ab619744d7794106489c67e5ef017160c90e5bdcc4dd597be075f9bcd3f4`.
- Ready manifest file SHA-256:
  `d49bc3865244f9b231b7dba312819f4c715059ca4ce7d7bb97b185add7481f18`.
- Candidate implementation commit:
  `3ae7792782adcef60a254fa7c6bdb60a43d8171d`.
- Executable SHA-256:
  `18f5f85ac6bd5276948709ed1c0abc42dfdb4c070fbd63af6cd0a00cb19c810d`.
- Seeds: exactly D66--D70.
- Product: 90 candidate runs over six cells plus 45 nine-baseline controls in
  homogeneous-low, for 135 online runs total.
- `formal_results_eligible=false` in both the manifest and final analysis.

## 2. Execution and integrity closure

All 135 runs completed and canonicalized on attempt 1. There are 135 canonical
directories, 135 summaries, and 135 QC reports, with zero missing or unexpected
run IDs. No attempt-02 or attempt-03 directory and no quarantined file exists.
All valid observations were retained; no seed was dropped, replaced, or rerun
after observing throughput, QPR, or any other scientific metric.

The result-blind full-workspace reconciliation verified all 135 paths as
already exact and performed zero path moves:

- reconciliation status: `canonical_paths_verified`;
- exact count: 135; reconciled count: 0;
- scientific process re-executed: false;
- scientific metric values used for selection: false;
- reconciliation document hash:
  `029838d7923ebf2b8b203238509e30415422b548c05cc9df3cb3f921a0002533`;
- reconciliation file SHA-256:
  `2db00e3401b0ac305f119fe21fdc5caac7b698559f34bea35b21461b56aca269`.

The append-only online ledger validates 282 events and terminates at hash
`8fea1bb2c03ae108dcf1442b5c505181331124c6217a0621d2d106e0847d2f34`.

## 3. Frozen candidate selection

The selection rule maximizes the minimum of the twelve candidate/C0 mean
ratios formed by throughput and QPR in all six topology/load cells, followed
by their mean, the number of dual-first cells, and the declared simplicity
order. The complete screen produced:

| Candidate | Worst ratio | Mean ratio | Dual-first cells | Frozen outcome |
|---|---:|---:|---:|---|
| C0 `ready_order` | 1.0000 | 1.0000 | 0 | selected |
| C1 `ready_warm_init` | 0.8574 | 1.0874 | 3 | rejected by worst cell |
| C2 `ready_finish_init` | 0.4810 | 1.0054 | 1 | rejected by worst cell |

C1's worst ratio is its heterogeneous-middle throughput: 0.2104 req/ms
versus C0's 0.2454 req/ms. C2's worst ratio is its homogeneous-middle QPR:
0.001140 versus C0's 0.002370. Although C1 improves both mean metrics in
three cells and has the largest twelve-ratio mean, the preregistered maximin
rule therefore selects C0. The selection rule was not changed after seeing
the data.

The six-cell means are:

| Topology | Load | C0 T | C0 QPR | C1 T | C1 QPR | C2 T | C2 QPR |
|---|---|---:|---:|---:|---:|---:|---:|
| homogeneous | low | 1.5104 | 0.040895 | 1.5508 | 0.042181 | 1.5404 | 0.040849 |
| homogeneous | middle | 0.4116 | 0.002370 | 0.4058 | 0.002371 | 0.3366 | 0.001140 |
| homogeneous | high | 0.8862 | 0.004612 | 0.9326 | 0.005054 | 1.0712 | 0.007058 |
| heterogeneous | low | 1.1690 | 0.025092 | 1.2044 | 0.028618 | 1.1988 | 0.028012 |
| heterogeneous | middle | 0.2454 | 0.001559 | 0.2104 | 0.001628 | 0.2144 | 0.001597 |
| heterogeneous | high | 0.3366 | 0.001326 | 0.3990 | 0.002121 | 0.3260 | 0.001326 |

Throughput uses requests/ms. Each displayed mean contains all five fixed
seeds.

## 4. Homogeneous-low baseline gate

The selected C0 has mean throughput 1.5104 req/ms and mean QPR 0.040895. It
strictly exceeds both metrics only for `random` and `hash`; seven of nine
baseline rows fail at least one required comparison.

| Baseline | Mean T | Mean QPR | C0 T margin | C0 QPR margin | Passed |
|---|---:|---:|---:|---:|---|
| greedy | 1.5460 | 0.041260 | -0.0356 | -0.000365 | no |
| random | 0.5616 | 0.002398 | +0.9488 | +0.038498 | yes |
| hash | 0.9120 | 0.011305 | +0.5984 | +0.029591 | yes |
| load_least | 1.5464 | 0.044811 | -0.0360 | -0.003915 | no |
| sche_FaaSRank | 1.5098 | 0.045724 | +0.0006 | -0.004829 | no |
| sche_OCS | 1.5180 | 0.046053 | -0.0076 | -0.005157 | no |
| sche_Hiku | 1.5356 | 0.045822 | -0.0252 | -0.004926 | no |
| sche_jiagu | 1.5392 | 0.043491 | -0.0288 | -0.002596 | no |
| sche_orion | 1.5366 | 0.046158 | -0.0262 | -0.005262 | no |

C1 is not a post-hoc rescue. Its homogeneous-low throughput, 1.5508 req/ms,
is higher than all nine baseline means, but its QPR, 0.042181, remains below
FaaSRank, OCS, Hiku, jiagu, and Orion. It also failed the frozen maximin rule.
Changing the chosen candidate or selection rule after observing these results
would invalidate the development protocol.

## 5. Mechanism diagnosis

The initialization-only policies changed many choices, but almost every
changed choice deliberately gave up current Eq. (15) utility:

- C1 changed 13,397 initial choices in homogeneous-low, of which 13,285
  (99.16%) had lower instantaneous utility than C0's strict utility choice.
- C1 changed 29,065 choices in heterogeneous-middle, all 29,065 of which had
  lower instantaneous utility.
- C2 changed 14,876 choices in homogeneous-low, of which 14,752 (99.17%) had
  lower instantaneous utility.
- Across the remaining C1/C2 cells, the lower-utility share is effectively
  100% whenever the refined initializer differs from C0.

The mean window-level nonconvergence rate also generally rises when a refined
initializer is used. For example, it is 0.0650 for C0 versus 0.0796 for C1 in
heterogeneous-middle, and 0.0378 for C0 versus 0.0458 for C1 in
homogeneous-low. With the current four-round inner budget, the strict
best-response loop often cannot erase the path imposed by thousands of
lower-utility initialization choices.

The seed-level low-load behavior is correspondingly nonuniform. C1's largest
gain occurs on difficult seed D67 (throughput 0.963 to 1.232 req/ms and QPR
0.007189 to 0.013906 versus C0), while D66 and D70 lose throughput. This is
useful diagnosis but cannot justify retaining only favorable seeds.

## 6. Paper alignment and decision

The manuscript states that inner-loop iterations continue until no unilateral
utility-improving reassignment exists, and Algorithm 1 Lines 9--14 repeat
until the assignment is unchanged. It also acknowledges bounded iteration
budgets and small empirical `T`. The implementation currently caps each inner
solve at four rounds and, on a limit hit, returns the highest-social-welfare
state encountered so far. That is a defensible practical budget, but G2 shows
that it is too small to make aggressive initialization changes robust.

Therefore:

- G2 is closed as a complete negative development result.
- C0 `ready_order` remains the only selected candidate from this bank.
- `baseline_gate_passed=false` and
  `formal_confirmation_authorized=false`.
- No homogeneous-middle formal run, new formal seed bank, or later paper
  experiment is authorized by G2.
- The next admissible mechanism study must use a fresh development bank and
  preregister a convergence-budget family before sampling. The most defensible
  axis is to keep Eq. (15) and the paper utility unchanged while increasing or
  adaptively exhausting the inner best-response budget, including a guarded
  combination with C1 to test whether adequate convergence preserves its
  throughput benefit without its heterogeneous-middle collapse.

Final analysis artifact:
`runs/tscv1_g2_init_d66_d70_3ae7792_20260903/g2.initialization.analysis.json`.

- Analysis status: `complete_g2_development_failed_baseline_gate`.
- Analysis document hash:
  `e1c756041e7155b36c87fb9a15a2c184f6967b1356b2563038e2805b96a57d79`.
- Analysis file SHA-256:
  `414f42b286358277c6dd30dd3943074067cefa590f3a0ff45ed74b6c809f18db`.
