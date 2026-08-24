# Experiment Plan

**Problem**: Freeze a middle-load NSESche profile that is strictly first in fixed-window throughput and QPR without seed selection or completion-feedback routing.
**Method Thesis**: Hiku should replace the frozen V52c low-density expert only when current pre-placement state shows that Hiku's pull-worker premise is applicable: a narrow frontier, a mature cluster, and an idle-warm feasible worker.
**Date**: 2026-08-25

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: structural applicability jointly improves throughput and QPR | V53 led throughput but missed the QPR gate | One V54 candidate is strictly first against all nine paired baselines and both other candidates on throughput and both QPR definitions | B1 |
| C2: both maturity and idle-worker evidence matter | The full gate has global and per-player components | Full gate beats both mechanism-deletion controls on the same five paired seeds | B2 |
| Anti-claim: the result comes from favorable seeds or threshold tuning | That would invalidate the paper claim | Complete E190--E194 method product, fixed predicates, zero deletion/replacement, joint result-blind pairing before reveal | B1, B3 |

## Paper Storyline

- Main paper must prove simultaneous throughput/QPR dominance and a state-semantic explanation.
- Appendix can support current-frontier width, warm-container coverage, idle-worker availability, and deletion controls.
- Experiments intentionally cut: threshold sweeps, weight tuning, seed substitution, post-hoc composites, and any use of completion/latency/cost feedback in routing.

## Experiment Blocks

### Block 1: Fresh paired main result
- Claim tested: C1 and the anti-claim.
- Dataset / split / task: simulator E1 middle, homogeneous 20-node, mixed shared-QoS, untouched E190--E194.
- Compared systems: nine frozen baselines plus V54a/V54b/V54c.
- Metrics: fixed-window throughput; finite-only QPR; zero-completion-as-zero QPR. Latency and cost are diagnostic only.
- Setup: exact common HPA, tape, model, binary and runtime identity; five seeds; serial execution.
- Success criterion: one candidate strictly exceeds every other method on all three primary metrics.
- Failure interpretation: close V54; do not tune any structural threshold on these seeds.
- Priority: MUST-RUN.

### Block 2: Mechanism deletion study
- Claim tested: C2.
- Compared systems: full maturity-plus-idle gate; delete idle-worker requirement; delete global maturity requirement.
- Success criterion: full gate passes the main gate and exceeds both deletions.
- Failure interpretation: a simpler deletion is preferred only if it independently passes the strict main gate; otherwise no freeze.
- Priority: MUST-RUN.

### Block 3: Result-blind integrity audit
- Claim tested: anti-claim.
- Setup: 60 canonical runs, five complete 12-method groups, common runtime consensus, empty quarantine, pairing report with `metrics_consulted=false` before reveal.
- Success criterion: every gate passes without replacing a seed or method.
- Failure interpretation: no performance reveal until a frozen technical-retry rule resolves the issue.
- Priority: MUST-RUN.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---:|---|---|---|
| M0 | Code and metric sanity | 104 unit tests | all pass; binary hash sealed | completed | branch/enum error |
| M1 | Capture common inputs | 5 tapes | 5/5 canonical, zero quarantine | ~3--5 min | port collision |
| M2 | Build offline dependencies | 15 references | exact tables and receipts pass | ~5--15 min | reference mismatch |
| M3 | Paired online cohort | 45 baseline + 15 candidate | all method/seed cells accounted for | ~30--60 min | Windows directory-label drift |
| M4 | Joint blind audit and reveal | 0 simulator runs | 60 runs, 5 groups, 12 methods, runtime consensus | <2 min | premature metric read |
| M5 | Freeze or close | 0 | strict three-metric winner or `none` | <1 min | post-hoc retuning |

## Compute and Data Budget

- Total online processes: 60, strictly serial.
- Offline reference builds: 15; base tapes: 5.
- Estimated turnaround: 45--90 minutes including gates and archiving.
- Biggest bottleneck: serial simulator runtime and Windows atomic-publication reliability.

## Risks and Mitigations

- Seed heterogeneity: preserve complete pairing and arithmetic means; no replacement.
- Full-manifest shape: declare E190--E199, execute only E190--E194, and keep E195--E199 uncaptured reserve.
- Candidate-state feedback: gate only on each candidate's current pre-placement state.
- Overfitting: fix `3 * frontier_width < node_count`, `warm_containers >= node_count`, idle-warm feasibility, and density 24 before capture; no sweep.
- Complex story: retain two deletion controls; prefer the simplest candidate that independently passes the strict gate.

## Final Checklist

- [x] Main paper table is specified
- [x] Novelty is isolated
- [x] Simplicity is defended
- [x] No frontier component is claimed or forced
- [x] Must-run work is separated from excluded tuning
