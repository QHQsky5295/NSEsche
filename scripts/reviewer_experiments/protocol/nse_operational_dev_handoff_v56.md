# NSESche operational development handoff V56

V56 freezes the middle-load NSESche profile as `topology_faasrank_or_ocs`
(`v56b-delete-resource-guard`). It is the first preregistered candidate to be
strictly rank one for fixed-window throughput and both prespecified QPR
conventions in the same complete paired cohort. Low remains frozen as
`orion_ocs2_borda`; high remains frozen as `jiagu_current_demand`.

V56 used only the complete, permanently non-formal E200--E204 cohort. The
E205--E209 reserve was never captured or inspected and is now retired from
development rather than reused after a successful selection. Confirmation
seeds E120--E129 remain sealed until a separate confirmation plan is committed.

## Provenance and gates

- plan/runtime commit: `c4a1d80323fbd3bd6938c74e481d2b3cf46b2d65`
- plan SHA-256: `10c86a83427909c1ceb6407685de8aaf380859d2afc5bcadc715047f0038b262`
- scheduler code commit: `2c5c7a7eed37516d0054d43b555341ac974142ea`
- scheduler source SHA-256: `76aa2654a1ba06a5fa88470d696d0249d7536cba37da06e9e9bdc107415c7208`
- release binary SHA-256: `1aa42fb04e2ab4dc33dc405008a592b2d7be4aa32a41712e7219b339cd6f1d45`
- result-blind joint pairing SHA-256: `5df7d1da47438dd724a129406b51d4dc9da029adfd81ced56abf82ba6ec4d94c`
- result-blind audit hash: `a9091a8133689e4b87413a8bc3d355626f160453186ce3ea321d65323d9029f4`
- result: `tmp/nse_operational_dev_20260825_v56/paired-screen.v56-middle.json`
- result SHA-256: `4f302cd5939932e2dcfff75760e8c83239a42010da33313d22fbfb7f4a5a898b`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. Every ledger passed, quarantine was
empty, and no canonical directory repair was required. Before any metric was
read, the joint result-blind audit verified 60 runs in five complete 12-method
groups with common tape, HPA, simulation, binary, Python, Cargo.lock, and Git
runtime identities.

## Revealed result and frozen selection

| Candidate | Throughput | T rank | QPR | Q rank | Strict triple gate |
|---|---:|---:|---:|---:|---|
| V56a resource + topology router | 1.2168 | 9 | 0.060212460 | 3 | no |
| V56b delete resource guard | 1.4268 | 1 | 0.062444703 | 1 | **yes** |
| V56c delete topology guard | 1.2168 | 10 | 0.060212460 | 4 | no |

The strongest noncandidate throughput was FaaSRank at `1.3758`; the strongest
noncandidate QPR was LoadLeast at `0.061331138`. V56b exceeded both. All five
V56b QPR observations were finite, so finite-only and
zero-completion-as-zero QPR are identical and both strictly rank one.

The frozen middle policy deletes the resource-orientation guard: on each
current parent-complete frontier, use the faithful ready-frontier FaaSRank
expert when demand-weighted mean DAG size is no greater than current cluster
width; otherwise use the frozen OCS current-demand expert. The decision uses
only preplacement state and does not read seed, workload label, completion,
latency, cost, QPR, or any post-hoc result.

No threshold, weight, seed, retry, or post-hoc composite was tuned after
reveal. V56 is closed with `selection=v56b-delete-resource-guard` and
`freeze_middle=true`; V1--V55 remain rollback points.

## Confirmation boundary

The next action is a separately committed, result-blind confirmation plan on
the still-sealed E120--E129 cohort. It must bind the frozen three-load stack
without further development:

- low: `orion_ocs2_borda`
- middle: `topology_faasrank_or_ocs`
- high: `jiagu_current_demand`

The confirmation must use all ten seeds for all three loads, the frozen paired
baseline evidence and thresholds specified before reveal, strict serial
execution, no seed replacement/deletion, and a result-blind pairing gate
before metrics. A failed load closes confirmation as a failure; it does not
reopen E205--E209 or authorize retuning.
