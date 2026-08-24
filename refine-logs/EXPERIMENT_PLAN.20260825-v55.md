# Experiment Plan

**Problem**: Freeze a middle-load NSESche profile that is strictly first in fixed-window throughput and QPR without seed selection or outcome-feedback routing.
**Method Thesis**: An idle-warm Hiku branch is safe when current running containers cover current runnable work; combining that premise with V54b's mature-sparse branch can preserve throughput while recovering QPR.
**Date**: 2026-08-25

## Claim Map

| Claim | Minimum Convincing Evidence | Block |
|---|---|---|
| C1: capacity-covered routing jointly improves throughput and QPR | One V55 candidate is strictly first against all eleven paired comparators on throughput and both QPR definitions | B1 |
| C2: the capacity guard and mature-sparse branch have distinct roles | Full union beats both deletion controls on identical seeds | B2 |
| Anti-claim: gains come from favorable seeds or fitted cutoffs | Complete E195--E199 product, parameter-free coverage relation, joint result-blind reveal, no replacement | B3 |

## Experiment Blocks

### B1: Fresh paired main result
- E1 middle, homogeneous 20-node, mixed shared-QoS, untouched E195--E199.
- Nine frozen baselines plus V55a/V55b/V55c.
- Primary metrics: fixed-window throughput and two QPR definitions.
- Success: one candidate strictly exceeds every other method on all three metrics.
- Failure: close V55; do not weaken or ratio-tune the coverage relation.

### B2: Mechanism deletions
- V55a: capacity-covered idle branch OR mature-sparse branch.
- V55b: delete capacity guard.
- V55c: delete mature-sparse branch.
- A simpler deletion may be frozen only if it independently passes the full strict gate.

### B3: Integrity
- Require 5 tapes, 15 references, 60 canonical online runs, 0 quarantine, five complete 12-method groups, and common runtime identity before reveal.
- E200--E204 stay uncaptured; E120--E129 stay sealed.

## Milestones

| ID | Goal | Runs | Gate |
|---|---|---:|---|
| M0 | code sanity | 106 tests | all pass; binary sealed |
| M1 | common inputs | 5 tapes | exact seed set; no quarantine |
| M2 | offline dependencies | 15 references | all receipts and ledgers pass |
| M3 | paired cohort | 60 online | complete first-pass/QC evidence or frozen retries |
| M4 | blind audit | 0 | 60 runs, 5 groups, 12 methods |
| M5 | selection | 0 | strict three-metric winner or none |

## Exclusions

- No seed substitution, threshold sweep, weight tuning, post-hoc composite, selective rerun, or confirmation-seed access.
- No completion, latency, cost, seed, or workload-label input to the router.
- Low remains `orion_ocs2_borda`; high remains `jiagu_current_demand` at the frozen 7k profile.
