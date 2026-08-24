# Experiment Plan

**Problem**: Freeze a middle-load NSESche profile that is strictly first in fixed-window throughput and QPR without seed selection or outcome-feedback routing.
**Method Thesis**: Current-frontier resource orientation and topology width identify when frozen ready-frontier FaaSRank should replace frozen OCS current-demand behavior.
**Date**: 2026-08-25

## Claim Map

| Claim | Minimum Convincing Evidence | Block |
|---|---|---|
| C1: resource/topology routing jointly improves throughput and QPR | One V56 candidate is strictly first against all eleven paired comparators on throughput and both QPR definitions | B1 |
| C2: resource orientation and topology bound have distinct roles | Full router beats both deletion controls on identical seeds | B2 |
| Anti-claim: gains come from seed labels or fitted cutoffs | Complete E200--E204 product, relative state predicates, joint result-blind reveal, no replacement | B3 |

## Experiment Blocks

### B1: Fresh paired main result
- E1 middle, homogeneous 20-node, mixed shared-QoS, untouched E200--E204.
- Nine frozen baselines plus V56a/V56b/V56c.
- Primary metrics: fixed-window throughput and two QPR definitions.
- Success: one candidate strictly exceeds every other method on all three metrics.
- Failure: close V56; do not weaken either relative predicate.

### B2: Mechanism deletions
- V56a: memory-oriented frontier AND topology-bounded frontier selects FaaSRank; otherwise OCS.
- V56b: delete resource-orientation predicate.
- V56c: delete topology-bound predicate.
- A deletion may be frozen only if it independently passes the full strict gate.

### B3: Integrity
- Require 5 tapes, 15 references, 60 canonical online runs, 0 quarantine, five complete 12-method groups, and common runtime identity before reveal.
- E205--E209 stay uncaptured; E120--E129 stay sealed.

## Milestones

| ID | Goal | Runs | Gate |
|---|---|---:|---|
| M0 | code sanity | 108 tests | all pass; binary sealed |
| M1 | common inputs | 5 tapes | exact seed set; no quarantine |
| M2 | offline dependencies | 15 references | all receipts and ledgers pass |
| M3 | paired cohort | 60 online | complete first-pass/QC evidence or frozen retries |
| M4 | blind audit | 0 | 60 runs, 5 groups, 12 methods |
| M5 | selection | 0 | strict three-metric winner or none |

## Exclusions

- No seed substitution, threshold sweep, weight tuning, post-hoc composite, selective rerun, or confirmation-seed access.
- No completion, latency, cost, seed, or workload-label input to the router.
- Low remains `orion_ocs2_borda`; high remains `jiagu_current_demand` at the frozen 7k profile.
