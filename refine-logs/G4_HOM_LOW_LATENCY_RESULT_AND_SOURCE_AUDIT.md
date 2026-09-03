# G4 homogeneous-low latency result and source audit

Date: 2026-09-04

Branch: `agent/tsc-resubmit-final`

Analysis source snapshot: `cfd28eee4408439c4d2eea135451c87707498b63`

Status: `complete_trace_no_unique_latency_stage`

## Decision

The single authorized G4 invocation completed over exactly the frozen 50-run
homogeneous-low D71--D75 cohort: five NSESche C0 runs and 45 runs covering all
nine baselines.  All valid seeds and both the full-cohort and common-completion
views were retained.  No simulator was run and no result was discarded,
replaced, or selected after inspection.

Cold-start wait is the strongest remaining latency-path hypothesis, but it does
not pass the preregistered unique-stage gate.  Consequently this audit does not
authorize a scheduler change, a fourth E0 candidate, new seeds, formal-cell
progression, plots, or paper-ready claims.  The formal homogeneous-middle cell
remains blocked by the failed homogeneous-low formal gate.

## Immutable product receipts

The machine-readable report records document SHA-256
`d65feedbd8894df12a38f583b23ee319f008507188671985c9ad8621b3e1749e`.
File receipts are:

| Product | SHA-256 |
|---|---|
| `g4_hom_low_latency.json` | `1f58e404f39f3aa03cd4c2e03865800caa95e0a687f3a00c335bd0d8798556c5` |
| `g4_hom_low_exposure_associations.csv` | `1fc1a6314204ad4d14280abfb521efbf8adfe82eb1e34777501994626720a44f` |
| `g4_hom_low_matched_pairs.csv` | `693ec9ec05beaae5e09bf4861fd24f049c98f19e2d9f62fa9df9ad76ef245ebc` |
| `g4_hom_low_pair_aggregates.csv` | `7956bb973529c5e94b489e37209b297ff9d6dfb16c8a8083f038af08f8dd9364` |
| `g4_hom_low_run_stage_metrics.csv` | `f586b56c000de5c59bac992abc134c5ca5a1c494a62990d7ab6a295dec3f8483` |

The report is bound to G3-E0 selection document/file hashes
`4cb006a35be028961f337279f9b13ca27fa6e946dee5b28a44e397047fc96a34`
and `22e5cf3573b5e15a0840ac3ead8db4bf4741a33cab33d4f48e6bd5e83950f3f7`,
and ready-manifest hash
`c7beed33f706333833e4aca7b66a3e0508761c1babf40f70a2e75d4de6c5a657`.

## Retained descriptive result

The entries below are unweighted means of five independent run/seed summaries.
Function-stage means cover completed functions and are not asserted to add
causally to request latency.

| Method | Request latency (ms) | Schedule wait (ms) | Cold-start wait (ms) | Data wait (ms) | Execution (ms) | Cold-event share |
|---|---:|---:|---:|---:|---:|---:|
| NSESche C0 | 84.4634 | 1.0041 | 23.7249 | 0.0419 | 26.7234 | 0.2641 |
| Greedy | 72.1235 | 0.6624 | 18.1135 | 0.2238 | 24.8199 | 0.2815 |
| Random | 380.2542 | 148.8279 | 27.8396 | 0.2729 | 14.5959 | 0.4297 |
| Hash | 104.6488 | 0.7710 | 23.5974 | 0.1406 | 51.5535 | 0.3277 |
| Load-least | 78.7505 | 0.6607 | 16.7157 | 0.2281 | 28.4787 | 0.2529 |
| FaaSRank-P | 58.2029 | 1.0039 | 17.3880 | 0.0181 | 16.8709 | 0.1748 |
| OCS | 64.2980 | 0.6707 | 9.7481 | 0.2372 | 27.8051 | 0.1247 |
| Hiku | 54.4733 | 0.6651 | 10.4029 | 0.2621 | 20.7385 | 0.1299 |
| Jiagu | 63.1032 | 0.6342 | 11.4011 | 0.2844 | 23.5082 | 0.1468 |
| Orion | 66.5697 | 0.6528 | 16.8480 | 0.2223 | 21.5803 | 0.2379 |

Against the five declared primary baselines, NSESche's full-completed-function
cold-start-wait difference is positive in all five seeds for every comparator.
Its five-seed mean differences are +6.3369 ms versus FaaSRank-P, +13.9768 ms
versus OCS, +13.3220 ms versus Hiku, +12.3238 ms versus Jiagu, and +6.8769 ms
versus Orion.  Cold-start wait is the largest positive mean stage versus OCS,
Hiku, Jiagu, and Orion; execution time is largest versus FaaSRank-P.

The request-level evidence is less uniform.  Full-cohort latency is higher for
NSESche in 5/5 seeds versus FaaSRank-P and 4/5 versus each of OCS, Hiku, and
Jiagu, but only 3/5 versus Orion.  Once restricted to requests/functions
completed by both paired policies, full/matched latency signs agree in 5/5
seeds for FaaSRank-P and Jiagu, 4/5 for Hiku, and 3/5 for OCS and Orion.  The
common-completion cold-stage confirmation condition passes only for Jiagu.
Thus the full-completion result cannot be promoted to a unique causal stage.

## Exposure checks

The strongest expected-direction association is between NSESche's mean number
of starting containers and mean cold-start wait: Spearman rho is 0.90, and all
five leave-one-seed-out estimates remain positive (0.8 or 1.0).  This is a
useful state-regime association, not proof that a particular placement caused
a later function's cold wait.

Mean schedule wait is positively associated with resident-queue mean
(`rho=0.70`) and runnable-queue mean (`rho=0.60`), but schedule wait is not the
largest positive stage against any primary baseline.  Data-wait p95 is
associated with the data-blocked queue (`rho=0.866`), while NSESche's mean data
wait is generally lower rather than higher.  Execution exposures do not pass
the stable expected-direction screen.  Zero no-feasible share and zero parent-
blocked-queue variation make those two associations unidentifiable in this
five-seed cell.

## Source-symbol inventory

This is a source-level mechanism comparison, not an empirical attribution.
The six source files were inspected at commit `cfd28ee`; their SHA-256 values
are respectively `35dcce5e...a46` (NSESche), `88165558...bac` (FaaSRank),
`f5a10d0d...715` (OCS), `47ab2703...bef` (Hiku), `e81230a8...3f3` (Jiagu),
and `0a1fe41b...dfc` (Orion).

| Method | DAG admission/order | Container-state treatment in node choice | Load/queue treatment | Dispatch form |
|---|---|---|---|---|
| NSESche C0 | `PreAllDone`; stable arrival/request/topological/function order (`sche_nash.rs:2083-2127`) | Eq. (2)--(9) utility has no warm/cold term (`2490-2531`). C0 `ready_order` does not activate the warm/finish exact-tie rule; an exact utility tie falls to incumbent then node ID (`2573-2609`). Existing containers still affect feasibility and memory reservation. | Node pressure/utilization enter utility; all players repeatedly take strict best responses (`2510-2523`, `3813-3909`). | One validated batch for the solved window (`4979-5045`). |
| FaaSRank-P | `PreAllDone` (`sche_FaaSRank.rs:245-250`) | Running/starting/missing affinity is an explicit weighted score term (`122-137`). | CPU/memory headroom and projected task load are explicit score terms (`118-137`). | One command per selected request/function (`262-266`). |
| OCS | `PreAllSched` (`sche_ocs.rs:183-188`) | Idle-running, busy-running, starting, and missing states receive ordered warm scores; warm score has weight 0.55 (`50-68`, `145-164`). | Memory utilization and projected load enter the score (`80-96`). | One command per selected request/function (`198-202`). |
| Hiku | `All` (`sche_hiku.rs:139-144`) | Idle running workers are pulled first; fallback ranks running before starting before missing (`65-95`, `97-120`). | Active connection/task count breaks warm-worker/fallback choices (`76-79`, `115-119`). | One command per selected request/function (`165-169`). |
| Jiagu | `All` (`sche_jiagu.rs:42-55`) with predicted-demand ordering | Container state is the first lexicographic key: idle running, busy running, starting, missing (`84-105`). | Utilization, task count, projected assignments, and forecast-dependent active width follow container state (`101-105`, `127-160`). | One command per selected request/function (`224-228`). |
| Orion | `All` plus critical-path rank (`sche_orion.rs:58-90`, `229-245`) | Running/starting/missing affinity is an explicit weighted term (`143-157`). | Resource headroom and projected task load enter the node score (`128-157`). | One command per selected request/function (`262-266`). |

The inventory supplies a plausible operational difference outside the fixed
paper equations: several advanced baselines directly prioritize warm/container
state, whereas C0 first enforces the strict Eq. (15) utility argmax and does not
use warm state as a primary choice variable.  It does **not** establish whether
NSESche's observed cold waits are caused by (a) unavailable warm capacity under
the common HPA/lifecycle, or (b) strict-utility placement bypassing an available
warm node.  G3-E0's active but unsuccessful warm/cold envelope also prevents
treating source plausibility alone as authorization for another mechanism.

## Gate accounting

The preregistered unique-stage decision required all of the following for one
stage: a positive gap in at least 4/5 seeds against at least three primary
baselines, largest-stage agreement for the same comparators, common-completion
confirmation, a stable expected-direction exposure association, and a mapped
source difference outside Eqs. (1)--(20).

Cold-start wait passes the first, second, fourth, and source-plausibility parts,
but fails the same-comparator common-completion requirement.  Schedule wait,
data wait, and execution time fail earlier joint conditions.  The frozen
machine decision `complete_trace_no_unique_latency_stage` is therefore upheld.

## Permitted next step

Only one narrower, separately preregistered read-only analysis of retained C0
traces could now be justified: distinguish warm-capacity absence from warm-node
bypass using the already emitted `running_warm_available_players`,
`running_warm_bypassed_players`, selected container-state, utility-advantage,
and projected-finish-delta diagnostics.  It must preserve all D71--D75 seeds,
define its decision rule before inspecting the reduced values, and cannot
authorize a source change unless bypass, utility loss, and later cold exposure
can be linked without relabeling window proxies as per-invocation causality.
