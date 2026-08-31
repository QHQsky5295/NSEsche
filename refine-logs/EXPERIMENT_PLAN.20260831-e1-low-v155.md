# Experiment Plan: E1 Homogeneous-20 Low-Load Closure V155

**Problem**: The current 20-seed homogeneous low-load NSESche result does not
simultaneously exceed the strongest frozen throughput and QPR baselines.
**Method thesis**: A simple current-queue gate can keep the V150
Hiku2/OCS throughput path at low pressure and use the OCS current-demand path
before the backlog that damages latency and cost accumulates.
**Date**: 2026-08-31

## Claim Map

| Claim | Why it matters | Minimum convincing evidence | Linked blocks |
|---|---|---|---|
| C1: NSESche is the best low-load scheduler on the decisive throughput and QPR metrics | E1 homogeneous-20 is the first unresolved main-paper comparison | Candidate mean strictly exceeds the frozen nine-baseline maxima for throughput and both QPR conventions; at least 12/20 positive paired differences against Orion for throughput and OCS for QPR; 20/20 finite QPR | B1, B2 |
| C2: The gain is caused by backlog control, not seed selection or a larger search | A reviewer must be able to distinguish a mechanism gain from simulator noise | Every valid run is retained; no result-selective rerun; the queue gate reads only current pending+runnable tasks per node; queue-area and queue-density telemetry improve relative to V150 | B1, B3 |
| Anti-claim: the result comes from changing baselines, load, formulas, welfare, pricing, or HPA | These would invalidate the main comparison | Frozen E01-E20 baselines, tapes, common HPA, formulas, and metric code remain byte-bound; only the operational expert router changes | B1, B2 |

## Paper Storyline

- Main paper must prove: low-load NSESche is first in throughput and QPR under
  the current homogeneous-20 protocol, then freeze that group before middle.
- Appendix can support: queue-density trajectories, queue-area reduction, and
  the V149/V150/V151/V154 negative-result lineage.
- Intentionally cut: new heterogeneous, scaling, burst, QoS, and ablation runs
  before the homogeneous low group closes.
- Frontier-model necessity is not claimed; this is a deterministic scheduling
  mechanism and no LLM/VLM/diffusion/RL component is introduced.

## Frozen Evidence and Diagnosis

- Frozen baselines: E01-E20 homogeneous-20, 180 non-NSESche runs; do not rerun.
- V150 low (`srpt_ready_hiku2_ocs_borda`): throughput mean 1.47905 req/ms,
  9/20 paired wins against Orion; QPR mean 0.05104068, 11/20 paired wins
  against OCS.
- Frozen maxima: Orion throughput 1.4741 req/ms; OCS QPR 0.05557716.
- V150 mean queue-area is 900,683.85 request-frames versus 28,671.5 for OCS;
  mean V150 pending+runnable density is 25.343 tasks/node.
- The V149/V150 per-seed oracle still misses the OCS QPR mean, so merely
  selecting between old candidates is insufficient and is forbidden.

## Experiment Blocks

### B0: Lossless cleanup gate

- Claim tested: none; this is the storage/provenance prerequisite.
- Setup: finish and verify the Zip64 archive of
  `serverless_sim_game_nse_dev/tmp`, publish its receipt, then delete only the
  exact archived source tree.
- Success criterion: archive CRC and every decompressed file SHA-256 pass;
  final receipt exists; source `tmp` is absent; restore tool is retained.
- Failure interpretation: stop; do not delete source and do not start V155.
- Priority: MUST-RUN.

### B1: V155 low-load training screen

- Claim tested: C1 and C2.
- Compared systems: one NSESche candidate against frozen Orion/OCS and the
  frozen nine-baseline maxima. No baseline online reruns.
- Candidate: `srpt_ready_hiku2_ocs_queue8`.
  - If current `(pending+runnable)/node < 8`, use the exact V150
    Hiku2/OCS ordinal-Borda penalty.
  - Otherwise use the exact OCS current-demand penalty.
  - Keep SRPT-ready player order, NSESche solver/reference, welfare, pricing,
    feasibility, common HPA, and metric definitions unchanged.
  - The gate reads no load label, seed, tape path/hash, future arrival, or
    completion/latency/cost/QPR outcome.
- Dataset: the complete retained E01-E20 low-load tape block, used explicitly
  as training because its telemetry motivated the fixed threshold.
- Runs: 20 NSESche online runs plus 20 state-matched offline references;
  strictly serial; all valid runs retained.
- Primary metrics: fixed-window throughput, finite-only QPR, and
  zero-completed-as-zero QPR.
- Secondary diagnostics: queue-area, queue peak, current queue-density bands,
  latency, cost/completed request, solver termination, placement rejection.
- Success criterion: all three mean gates and all three fixed paired gates pass;
  finite QPR is available for 20/20 runs; zero placement rejection; blind audit
  passes before reveal.
- Failure interpretation: retain and archive all V155 runs, retire the profile,
  and diagnose the full block without deleting or replacing a valid seed.
- Table/figure target: main Fig. 6/Table E1 only after B2 confirms; queue
  diagnostics belong in the appendix.
- Priority: MUST-RUN.

### B2: Fresh ceiling-baseline confirmation

- Claim tested: C1 without reusing V155 training outcomes.
- Authorization: only if B1 passes unchanged.
- Dataset: unopened E1530-E1549 low-load tapes captured after the confirmation
  plan is committed.
- Compared systems: frozen V155 candidate, Orion, and OCS on the same 20 tapes.
- Runs: 60 online runs, exact three-method paired product; no candidate
  selection inside the confirmation cohort.
- Success criterion: NSESche mean strictly exceeds both fresh ceiling
  comparators for all three metrics; at least 12/20 positive paired throughput
  differences versus Orion and 12/20 positive paired QPR differences versus
  OCS; 20/20 finite QPR; blind audit before reveal.
- Failure interpretation: no paper superiority claim and no selective seed
  replacement; retain the block and return to mechanism analysis.
- Table/figure target: final low-load row/panel in the homogeneous main result.
- Priority: MUST-RUN IF AUTHORIZED.

### B3: Simplicity and mechanism check

- Claim tested: C2.
- Comparison: V155 against retained V150 telemetry only; no new online run.
- Success criterion: report queue-area/density changes and the fraction of
  windows routed to each expert. Do not add another threshold or router based
  on B1/B2 outcomes.
- Table/figure target: appendix diagnostic panel or concise text.
- Priority: MUST-RUN analysis after B1.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision gate | Cost | Risk |
|---|---|---:|---|---|---|
| M0 | Finish historical archive and reclaim disk | 0 | Verified final receipt; source deleted only after verification | I/O only | Archive or junction failure; fail closed |
| M1 | Commit V155 plan, implementation, telemetry, and tests | 0 | Unit tests, formatting, result-blind preflight | <1 h engineering | Router does not activate or changes forbidden code |
| M2 | Build E01-E20 V155 references and run training screen | 20 online + 20 offline refs | Joint blind audit, then all six gates | About 0.5-1.5 h serial | QPR tail remains below OCS |
| M3 | Freeze V155 or retire it | 0 | Pass opens fresh confirmation; fail blocks it | Minutes | Post-result threshold temptation; prohibited |
| M4 | Capture fresh E1530-E1549 and run paired confirmation | 60 online + inputs/refs | Fresh three-method paired gate | About 1-3 h serial | Fresh-DAG variance; handled by full cohort, not seed deletion |
| M5 | Freeze low-load publication group | 0 | Hash-bound catalog, results table, figure, handoff | <1 h | Provenance mismatch; fail closed |

## Compute and Data Budget

- GPUs: none.
- Maximum online runs before low-load closure: 80 (20 training + 60 conditional
  confirmation).
- Baseline reuse: all 180 existing formal baseline runs remain immutable; only
  Orion/OCS are rerun on the fresh confirmation tapes if M2 passes.
- Storage: archive/retain complete valid blocks; compress verbose logs; never
  fill shared `serverless_sim/records`.
- Biggest bottleneck: improving QPR without losing the small throughput margin.

## Risks and Mitigations

- Queue threshold overfits E01-E20: threshold 8 is an existing protocol constant
  and must be tested unchanged on E1530-E1549.
- Mean improvement hides unstable seeds: keep the fixed 12/20 paired gate.
- V155 degenerates to OCS: report routing fractions and require throughput to
  exceed Orion, not merely match OCS.
- Platform instability: technical failures may use the preregistered retry
  policy; QC-passing outcomes are never removed because of performance.

## Final Checklist

- [x] Main-paper claim and strongest ceiling baselines identified
- [x] Failed V149-V154 evidence retained
- [x] Baseline reruns minimized
- [x] Result-selective seed replacement prohibited
- [ ] Historical archive verified and source removed
- [ ] V155 code/test preflight complete
- [ ] V155 training block passes
- [ ] Fresh confirmation passes
- [ ] Low-load catalog, table, and figure frozen
- [ ] Only then may middle-load work resume
