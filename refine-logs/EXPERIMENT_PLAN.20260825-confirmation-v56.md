# Experiment Plan

**Problem**: Confirm that the fully frozen three-load NSESche stack transfers to an untouched ten-seed holdout while remaining above the preregistered baseline-leader thresholds.
**Method Thesis**: Load-specific, outcome-blind operational experts can jointly preserve throughput and QPR gains: Orion/OCS voting at low load, topology-routed FaaSRank/OCS at middle load, and Jiagu current-demand placement at high load.
**Date**: 2026-08-25

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Block |
|---|---|---|---|
| C1: the frozen stack transfers across unseen environments | Development dominance is insufficient without an untouched holdout | Every load strictly exceeds its frozen throughput and both QPR thresholds on all E120--E129 seeds | B1 |
| C2: the result is not seed selection or post-hoc retuning | Confirmation must be scientifically independent | 30/30 exact runs, complete-product blind audit, no seed deletion/replacement, no profile change | B2 |

## Paper Storyline

- Main paper must prove: all three frozen profiles pass their preregistered holdout gates.
- Appendix can support: complete ledger, tape/reference/runtime hashes and per-seed sensitivity rows.
- Experiments intentionally cut: baseline reruns, additional ablations, E205--E209 development, threshold sweeps, and post-confirmation rescue variants.
- No frontier-model component is claimed; no frontier-necessity block is applicable.

## Experiment Blocks

### B1: One-time three-load holdout

- Claim tested: the frozen low/middle/high operational stack transfers.
- Dataset / split / task: E1 homogeneous 20-node, mixed shared-QoS, steady low/middle/high, untouched E120--E129.
- Compared systems: one frozen NSESche profile per load versus the already frozen E11--E20 baseline-leader thresholds; no baseline reruns.
- Metrics: fixed-window throughput, finite-only QPR, zero-completion-as-zero QPR.
- Setup: 30 tapes, 30 state-matched references, 30 optimized runs, strict serial simulator on port 3107.
- Success: every load strictly exceeds all three load-specific thresholds; ties fail.
- Failure: close confirmation as failed, report the failed metrics, and do not retune or reopen any seed.
- Target: final three-load confirmation table in the main paper.
- Priority: MUST-RUN.

### B2: Integrity and anti-selection audit

- Claim tested: gains are not artifacts of seed selection, incompatible runtime state, or partial reveal.
- Setup: commit plan before expansion; exact E120--E129 product; identical code/binary/common-HPA per manifest; attempt/QC/archive/ledger gates; result-blind audit before metric access.
- Success: 30/30 canonical runs, exact seed/load set, zero unresolved quarantine, common runtime identity, all tape/reference bindings valid.
- Failure: stop before metric reveal; only frozen technical retry rules may run.
- Target: reproducibility appendix and artifact manifest.
- Priority: MUST-RUN.

## Frozen Gates

| Load | Profile | Throughput must exceed | Finite QPR must exceed | Zero-as-zero QPR must exceed |
|---|---|---:|---:|---:|
| low | `orion_ocs2_borda` | 1.4257 | 0.0534051338 | 0.0534051338 |
| middle | `topology_faasrank_or_ocs` | 1.1348 | 0.0673776749 | 0.0606399074 |
| high | `jiagu_current_demand` | 0.4384 | 0.0047864679 | 0.0047864679 |

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Expected Cost | Risk |
|---|---|---:|---|---|---|
| C0 | commit/freeze | 0 | plan, profiles, binary and thresholds hashed | minutes | accidental post-plan code change |
| C1 | common inputs | 30 tapes | exact E120--E129 x three loads; zero quarantine | ~6--12 min | capture technical failure |
| C2 | offline dependencies | 30 refs | all receipts/tables/ledgers valid | ~8--20 min | state/reference timeout |
| C3 | frozen method | 30 online | exact set; QC pass; no unresolved quarantine | ~8--20 min | technical retry |
| C4 | blind audit | 0 | 30/30 product and runtime/tape/reference consensus | minutes | provenance mismatch |
| C5 | one-time reveal | 0 | all three loads pass all strict gates | minutes | genuine transfer failure |

## Compute and Data Budget

- Online processes: 30; offline references: 30; unique tapes: 30.
- GPU-hours: none expected; CPU execution is strictly serial.
- Biggest bottleneck: state-matched reference and simulator runtime under high load.

## Risks and Mitigations

- Technical failure: retain evidence and use only the frozen runner retry policy.
- Zero-completion observations: report finite-only and conservative zero-as-zero QPR; never impute latency/cost.
- Confirmation miss: report failure without reopening development or changing thresholds.

## Final Checklist

- [x] Profiles and thresholds frozen before holdout access
- [x] Must-run block separated from all cut experiments
- [x] Failure action preregistered
- [ ] 30 tapes captured
- [ ] 30 references bound
- [ ] 30 online runs QC-pass
- [ ] Blind audit passes before reveal
- [ ] Three-load gate evaluated once
