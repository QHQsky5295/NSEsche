# NSESche operational development handoff V55

V55 is closed without a selected middle-load profile. It used only the
preregistered, permanently non-formal E195--E199 cohort. E200--E204 remained
uncaptured reserve, and sealed confirmation seeds E120--E129 remain unused.

## Provenance and gates

- plan/runtime commit: `b7d0e2cc5624b59fc8cfa423a79b7da64419ceaf`
- plan SHA-256: `7b5020b63481ed1ad91d9aa0defe3f7ab18f7a2fdd2890927abf7a01b2e0e5c0`
- scheduler code commit: `b5fb06863d8f4cdf68724be14426507863977d87`
- scheduler source SHA-256: `8ea74ed8ab597dfa5733333b68fd41faf580fff821e8433a7cecc5aaebbf2517`
- release binary SHA-256: `a571878f168e0135cb21f5611c52f3532b8811f72fde32d4af4354e21d302d45`
- result-blind joint pairing SHA-256: `2b4aad83f07307720133b93a886e160a1b1cf2c85624d96936faa394ce9c62b1`
- result-blind audit hash: `7de748bcd3dcaba44cec1478987a0658d8549a91f1d689cef3daf6e7592d82ee`
- result: `tmp/nse_operational_dev_20260825_v55/paired-screen.v55-middle.json`
- result SHA-256: `f1bdc29083e64c2a3c5cae77a6ad114b6ee80c832d46c35b2292382384f0d0d4`

Five tape captures, 15 reference builds, 45 baseline runs, and 15 candidate
runs all canonicalized on attempt 1. Every ledger passed, quarantine was
empty, and no canonical directory repair was required. The joint result-blind
audit verified 60 runs in five complete 12-method groups with common tape,
HPA, simulation, binary, Python, Cargo.lock, and runtime identities before
metrics were read.

## Revealed result

| Candidate | Throughput | T rank | QPR | Q rank | Both gates |
|---|---:|---:|---:|---:|---|
| V55a capacity-covered idle OR mature-sparse | 0.7324 | 5 | 0.004586215 | 4 | no |
| V55b delete capacity guard | 0.7408 | 4 | 0.004118016 | 6 | no |
| V55c delete mature branch | 0.6628 | 8 | 0.004250722 | 5 | no |

FaaSRank led throughput at `0.9342`; OCS led both finite-only and
zero-completion-as-zero QPR at `0.011350094`. All candidate QPR observations
were finite. No candidate satisfied any strict rank-one metric gate, so
`selection=none` and `freeze_middle=false`. The capacity-coverage/idle-worker
axis is closed without threshold, ratio, seed, or retry tuning.

## Mechanistic next step

V55 exposes a different expert-specialization axis. OCS had the best QPR in
E195, E196, E197, and E199, whereas FaaSRank led both throughput and QPR in
E198. A hypothetical run-level OCS/FaaSRank choice using FaaSRank only in
E198 would exceed the observed mean of either baseline, but no such post-hoc
composite is selected or reported as a result.

The preplacement function profiles supply a natural, outcome-blind mechanism
for testing that specialization on fresh data. E198 was the only cohort with
both (i) mean normalized CPU no greater than mean normalized memory and (ii)
mean DAG size bounded by the 20-node cluster. E195--E197 were CPU-oriented;
E199 was memory-oriented but had mean DAG size `26.12`, above the cluster
width. Corresponding mean `(normalized CPU - normalized memory)` values for
E195--E199 were `0.071`, `0.080`, `0.071`, `-0.012`, and `-0.010`; mean DAG
sizes were `7.98`, `4.25`, `5.62`, `4.69`, and `26.12`.

A future V56 may therefore test a parameter-free current-frontier router. It
uses the demand-weighted profiles already visible before placement: choose the
frozen ready-frontier FaaSRank expert only when aggregate normalized CPU is no
greater than aggregate normalized memory and aggregate mean DAG size is no
greater than the current node count; otherwise choose the frozen OCS
current-demand expert. Two deletion controls remove the resource-orientation
predicate or the topology-bound predicate. The router must select the entire
expert behavior (ready frontier, deterministic ordering, node score, and
history), not read a seed/workload label or any completion, latency, cost, or
post-hoc metric.

Any V56 execution must use a newly committed plan, untouched E200--E204, all
nine paired baselines, simultaneous reveal, and the same strict throughput
plus two-QPR gate. Low remains frozen as `orion_ocs2_borda`, high remains
frozen as `jiagu_current_demand`, and E120--E129 remain sealed.
