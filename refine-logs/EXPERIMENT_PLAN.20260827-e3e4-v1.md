# E3/E4 burst-recovery and balanced-QoS experiment plan

**Problem**: Defend NSESche under transient bursts and balanced-QoS workloads
after closing the 20-node homogeneous/heterogeneous comparisons and the
NSESche-only resource-scaling result.

**Method thesis**: NSESche's coordinated placement should preserve throughput
and quality-price ratio while recovering faster from bursts and serving QoS
classes more evenly than the nine frozen placement baselines.

**Date**: 2026-08-27

## Current paper boundary

- E1 homogeneous n20 is closed for low/middle/high in
  `NSESche_E1_homogeneous_n20_final_v1.json`; those NSESche rows and all nine
  baseline rows are immutable reuse sources.
- E1 heterogeneous n20 is closed for low/middle/high in
  `NSESche_E1_heterogeneous_n20_final_v1.json`; those rows are also immutable.
- The NSESche-only 20/100/500-node proportional-load trend is closed in
  `nse_homogeneous_low_resource_scaling_result_v1.json`. It makes no baseline
  superiority claim.
- V78 and V86 are retained failed 100-node overlay confirmations. They do not
  block or enter the NSESche-only resource-scaling figure, and they will not be
  tuned or rerun on their revealed seeds.

## Claim map

| Claim | Why it matters | Minimum convincing evidence | Block |
|---|---|---|---|
| C1: burst robustness | Reviewers need behavior beyond steady workload | On each frozen burst process, formal NSESche is first in mean fixed-window throughput and both QPR conventions; recovery time and censoring are reported without deletion | E3 |
| C2: QoS-aware operation | Aggregate throughput alone does not establish service quality | Under the frozen balanced-QoS tape, formal NSESche is first in mean throughput and both QPR conventions; SLA violation, function-level normalized satisfaction, Jain fairness, and worst-10% satisfaction are reported | E4 |
| Anti-claim: gains come from different inputs | A stronger scheduler claim is invalid if tapes/HPA/SLA/model differ | Exact same-seed tape, cluster, common-HPA, workload-profile, frozen-SLA, and FaaSRank hashes across all publication methods | E3/E4 audit |

## Paper storyline

- Main paper: E3 recovery curves/table and E4 QoS/fairness table.
- Appendix: convergence/reference diagnostics, censored recovery cases, and
  per-seed distributions.
- Cut: further 100-node baseline overlay tuning; multi-node scaling is already
  a NSESche-only resource trend.

## Experiment blocks

### Block 1: frozen E3/E4 inputs

- Dataset/task: middle-load heterogeneous 20-node balanced-QoS base tapes;
  three preregistered E3 burst transforms and one E4 steady process.
- Inputs: E01--E10, 10 base tapes, 30 derived burst tapes, six isolated SLA
  pilots, one frozen FaaSRank model, and 40 state-matched references.
- Success criterion: every input hash/count/schema gate passes before any
  formal metric is read.
- Target: provenance and methods subsection.
- Priority: MUST-RUN.

### Block 2: immutable baseline frontier

- Compared systems: Greedy, Random, Hash, LoadLeast, FaaSRank, OCS, Hiku,
  Jiagu, and Orion.
- Runs: 360 formal E01--E10 observations (nine methods x 30 E3 cells plus nine
  methods x 10 E4 cells), with no NSESche run in this stage.
- Metrics remain hidden until all baseline artifacts pass result-blind QC and
  pairing. Once revealed, the baseline maxima/minima are frozen constants; no
  baseline rerun is permitted for performance reasons.
- Priority: MUST-RUN.

### Block 3: NSESche development and one-shot confirmation

- Development uses a separately preregistered, untouched seed cohort and a
  small candidate set derived only from already frozen E1 profiles plus any
  paper-compatible QoS/burst adaptation justified before seeing that cohort.
- Development runs never become publication rows.
- One candidate per E3 burst and one candidate for E4 are frozen before formal
  E01--E10 NSESche metrics are opened. The formal stage adds exactly 40
  NSESche runs and their state-matched references; it does not rerun baselines.
- Success criterion: C1/C2 mean-ranking gates above, attempt-1 QC, zero
  quarantine, and exact 10-seed coverage. BCa intervals and paired differences
  are reported but do not permit seed replacement or post-reveal tuning.
- Failure interpretation: retain the complete cohort, close that candidate as
  failed, and begin a new development/confirmation version on fresh seeds only.
- Priority: MUST-RUN.

## Run order and milestones

| Milestone | Goal | Runs | Decision gate | Estimated cost |
|---|---|---:|---|---|
| M0 | Static preflight | 0 | 400 runs/40 refs/model/template hashes pass | completed |
| M1 | Prepare tapes/SLA/references | 10 captures + 6 pilots + 40 refs | ready manifest, no formal result read | about 1--2 h |
| M2 | Freeze nine-baseline frontier | 360 formal | all QC/pairing pass, then one simultaneous reveal | about 6--9 h |
| M3 | Preregister and screen compact NSESche candidates | versioned development cohort | no formal E01--E10 metric consulted | budget fixed in the versioned development plan |
| M4 | One-shot formal NSESche confirmation | 40 formal | C1/C2 gates, 40/40 attempt-1 QC | about 1 h plus references |
| M5 | Final analysis/figures | 0 | exact 400-run pairing and frozen artifact bundle | about 1 h |

## Risks and mitigations

- E3 4000-frame runs are slower: baseline-first execution freezes useful rows
  once and avoids rerunning them during NSESche development.
- Balanced-QoS SLA capacity may fail the preregistered bracket: the freezer
  fails closed; no target is hand-entered or selected from formal results.
- A default NSESche reference prepared in M1 may not match the eventual frozen
  candidate: preserve it as input provenance and build candidate-specific
  references after M3; never relabel a mismatched table.
- Disk growth: retain formal canonical/quarantine evidence and remove only
  explicitly disposable development build outputs after their audit bundle is
  frozen. `serverless_sim/records` remains outside the formal archive path.

## Final checklist

- [x] E1 homogeneous and heterogeneous comparison groups are frozen.
- [x] NSESche-only resource-scaling result is frozen.
- [x] E3/E4 static preflight passes.
- [ ] E3/E4 ready inputs are frozen.
- [ ] Nine-baseline E3/E4 frontier is frozen.
- [ ] NSESche development profile is preregistered on fresh seeds.
- [ ] Formal NSESche E3/E4 confirmation passes the claim gates.
- [ ] Main-paper E3/E4 tables and figures are frozen.
