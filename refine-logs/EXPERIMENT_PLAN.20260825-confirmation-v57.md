# Experiment Plan

**Problem**: Determine whether the unchanged frozen NSESche stack is strictly first under the same random workloads as every baseline, after V56's cross-cohort historical-threshold confirmation failed.
**Method Thesis**: Same-tape paired evaluation separates relative scheduler quality from large seed-to-seed DAG variance without retuning the algorithm or discarding the failed V56 evidence.
**Date**: 2026-08-25

## Claim Map

| Claim | Why It Matters | Minimum Convincing Evidence | Linked Block |
|---|---|---|---|
| C1: frozen NSESche is relatively best under identical conditions | The paper claims comparison to baselines, not invariance of absolute metrics across unrelated random cohorts | NSESche strictly ranks first for throughput and both QPR definitions in each load across 30 complete paired groups | B1 |
| C2: success is not a rescue retune or seed filter | V56 failed and must remain visible | Identical V56 profiles/binary, all E210--E219 seeds, all 300 runs revealed together, no deletion or selective rerun | B2 |

## Paper Storyline

- Main paper must prove: same-condition, same-tape strict rank one in low, middle, and high.
- Appendix must disclose: V56's unpaired historical-threshold failure and the preregistered V57 design correction.
- Experiments intentionally cut: any profile change, E120/E205 reuse, threshold tuning, method removal, or post-hoc subgroup.
- No frontier-model contribution is claimed.

## Experiment Blocks

### B1: Fresh 10-method paired confirmation

- Split: E210--E219, three steady loads, homogeneous 20-node, mixed shared-QoS.
- Systems: nine frozen baselines plus unchanged frozen NSESche.
- Metrics: fixed-window throughput, finite-only QPR, zero-completion-as-zero QPR.
- Runs: 300 online, 30 tapes, 30 NSESche references; strict serial port 3107.
- Success: NSESche strictly exceeds all nine baselines on all three metrics separately for every load.
- Failure: retain and report; no seed selection or tuning on this cohort.
- Target: definitive paired main comparison table.
- Priority: MUST-RUN.

### B2: Result-blind integrity

- Exact 10 methods x 3 loads x 10 seeds.
- Same tape/HPA/simulation/seed/environment semantic hashes within each group.
- Common binary/Python/Cargo.lock/Git identity, exact manifest IDs, QC/archive/ledger gates, zero unresolved quarantine.
- Metrics remain unread until all 300 runs form 30 complete groups.
- Priority: MUST-RUN.

## Run Order and Milestones

| Milestone | Goal | Runs | Decision Gate | Expected Cost | Risk |
|---|---|---:|---|---|---|
| P0 | commit/freeze | 0 | V56 profiles and binary unchanged | minutes | accidental source drift |
| P1 | common tapes | 30 | exact three-load ten-seed set | ~6--12 min | capture failure |
| P2 | references/model | 30 refs | all dependencies and frozen model bound | ~8--20 min | reference timeout |
| P3B | baselines | 270 | exact first-pass/QC coverage | ~45--75 min | long high-load runs |
| P3N | NSESche | 30 | exact first-pass/QC coverage | ~8--20 min | technical retry |
| P4 | joint blind audit | 0 | 300 runs / 30 groups / 10 methods | minutes | provenance mismatch |
| P5 | simultaneous reveal | 0 | NSESche strict first on all 9 gates | minutes | genuine rank failure |

## Compute and Data Budget

- Online runs: 300; references: 30; tapes: 30; GPU-hours: none expected.
- Biggest bottleneck: serial baseline execution under high-load random DAGs.

## Risks and Mitigations

- Cross-cohort variance: eliminated from relative rank by exact same-tape groups.
- Zero-completion runs: finite-only and conservative zero-as-zero QPR both required.
- Multiple validation history: V56 failure remains disclosed and immutable.

## Final Checklist

- [x] Frozen profiles and binary unchanged
- [x] Fresh E210--E219 verified unused
- [x] V56 failure retained
- [ ] 30 tapes and 30 references complete
- [ ] 300 online runs QC-pass
- [ ] 30 complete result-blind groups pass
- [ ] All nine strict load/metric gates pass
