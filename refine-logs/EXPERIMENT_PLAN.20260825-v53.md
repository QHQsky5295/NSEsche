# Experiment Plan

**Problem**: Freeze a middle-load NSESche profile that is strictly first in fixed-window throughput and QPR without seed selection or completion-feedback routing.
**Method Thesis**: A current-queue-regime router can retain V52c's low-density efficiency while invoking OCS-P and Hiku-P only where their pre-placement state semantics are appropriate.
**Date**: 2026-08-25

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Blocks |
|---|---|---|---|
| C1: queue-regime triage jointly improves throughput and QPR | V52 showed a fixed vote trade-off rather than joint dominance | One V53 candidate is strictly first against all nine paired baselines and both other candidates on throughput and both QPR definitions | B1 |
| C2: the gain comes from regime specialization, not extra complexity | The full router has three frozen experts | Full triage beats both deletion controls on the same five paired seeds | B2 |
| Anti-claim: the result comes from favorable seeds or selective reruns | That would invalidate the paper claim | Complete E185--E189 method product, first-pass QC or protocol-preserved failures, zero deletion/replacement, joint result-blind pairing before reveal | B1, B3 |

## Paper Storyline

- Main paper must prove: simultaneous throughput/QPR dominance and a mechanism-level explanation.
- Appendix can support: per-seed regime shares, deletion controls, QC/provenance hashes.
- Experiments intentionally cut: further vote interpolation, threshold sweeps, seed substitution, post-hoc composites, and any frontier-model component.

## Experiment Blocks

### Block 1: Fresh paired main result
- Claim tested: C1 and the anti-claim.
- Dataset / split / task: simulator E1 middle, homogeneous 20-node, mixed shared-QoS, untouched E185--E189.
- Compared systems: nine frozen baselines plus V53a/V53b/V53c.
- Metrics: fixed-window throughput; finite-only QPR; zero-completion-as-zero QPR. Latency and cost are diagnostic only.
- Setup: exact common HPA, tape, model, binary and runtime identity; five seeds; serial execution.
- Success criterion: one candidate strictly exceeds every other method on all three primary metrics.
- Failure interpretation: close V53; do not subdivide the 24/48 thresholds on these seeds.
- Table / figure target: middle-load method table and paired-seed appendix.
- Priority: MUST-RUN.

### Block 2: Mechanism deletion study
- Claim tested: C2.
- Compared systems: full triage; delete-middle; delete-low-composite.
- Success criterion: full triage passes the main gate and exceeds both deletions.
- Failure interpretation: a simpler deletion is preferred only if it independently passes the strict main gate; otherwise no freeze.
- Table / figure target: compact ablation rows beside the main result.
- Priority: MUST-RUN.

### Block 3: Result-blind integrity audit
- Claim tested: anti-claim.
- Setup: 60 canonical runs, five complete 12-method groups, common runtime consensus, empty quarantine, pairing report with `metrics_consulted=false` before reveal.
- Success criterion: every gate passes without replacing a seed or method.
- Failure interpretation: no performance reveal until the technical issue is resolved by the frozen retry protocol.
- Table / figure target: reproducibility appendix.
- Priority: MUST-RUN.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Cost | Risk |
|---|---|---:|---|---|---|
| M0 | Code and metric sanity | 102 unit tests | all pass; binary hash sealed | completed | branch/enum error |
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
- Full-manifest shape: declare E185--E194, execute only E185--E189, and keep E190--E194 uncaptured reserve.
- Candidate-state feedback changes density: gate on each candidate's own current pre-placement state and audit all regime definitions.
- Overfitting the boundary: use only frozen 24 and doubled 48; no V53 threshold sweep.
- Complex method story: retain two deletion controls; prefer the simplest candidate that independently passes the strict gate.

## Final Checklist

- [x] Main paper table is specified
- [x] Novelty is isolated
- [x] Simplicity is defended
- [x] No frontier component is claimed or forced
- [x] Must-run work is separated from excluded tuning
