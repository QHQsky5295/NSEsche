# G1 Q61--Q80 formal E1 preregistration

Date: 2026-09-03 (Asia/Shanghai)

Status: protocol-frozen before Q61--Q80 tape capture, offline-reference
construction, or online execution; zero formal result rows existed when this
document was written

## 1. Paper role and admission boundary

This block is both the independent corrected-runtime qualification and the E1
main-comparison source for Fig. 6 and Fig. 9.  It contains the complete
`10 methods x 2 topologies x 3 loads x 20 paired seeds = 1,200 runs` product.
It becomes reusable formal evidence only after its frozen per-cell gates pass.

The six online cells must be opened in this order:

1. homogeneous low;
2. homogeneous middle;
3. homogeneous high;
4. heterogeneous low;
5. heterogeneous middle;
6. heterogeneous high.

Each cell contains 200 runs.  A later cell is unauthorized until the preceding
cell has 200 canonical QC-valid rows and NSESche is strictly first in both mean
throughput and mean run-level QPR with complete QPR coverage.  Completing the
online rows alone is `formal_complete_not_closed`; statistical tables, old-PDF
alignment and the publication figure are still required for
`paper_ready_closed`.

## 2. Frozen identities

- Protocol freeze commit:
  `125a741b7cffec1973f8d6632c781f9ff83d38ac`.
- Runtime source commit:
  `98f822cf2dcb878024a2ca39cc56533895ea692c`.
- Runtime binary SHA-256:
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Runtime binary size: 4,707,328 bytes.
- Selected NSESche candidate: `ready_order`.
- Candidate-selection document SHA-256:
  `30f15c1a17549024d1b879f92a5d8cbadf50a2de6ee4143bbc751c38113a98a6`.
- Candidate-selection file SHA-256:
  `d3c318605f5ffb583e4213ef7f6c806ed74027d8f1fa38c797e31511e804f40d`.
- Unbound formal manifest document hash:
  `002381757b87fa407e4f2d60c851a745ece2bdef986c72760823a62f806f4361`.
- Unbound formal manifest file SHA-256:
  `5db12b5b44c8f549535f8043274827df01a0e1280aa4a0becbb3087488f36280`.
- Frozen FaaSRank model artifact SHA-256:
  `4853fffa378ade5aed7c6de50667ddfd6231704ca7b81c82b3b4208fec43f17e`.
- FaaSRank training-tape SHA-256:
  `28a48254c9a8589d708c305dc6c1a89be2714f8ab3df307058637c5f142325b9`.

The archived FaaSRank model is a previously frozen independent FTR01--FTR05
calibration artifact.  Its historical source paths remain recoverable from the
verified `revision_closed_development_20260903` archive.  The model cannot be
bound to the formal manifest until every Q61--Q80 evaluation-tape hash exists
and all 120 hashes are shown to differ from its training-tape hash.

## 3. Frozen matrix and inputs

- Phase: `formal`.
- Bank: `TSCv1.formal.G1.E1.Q61-Q80`.
- Seeds: exactly Q61 through Q80; all three run seed fields use the same paired
  seed.
- Methods: greedy, random, hash, load-least, FaaSRank, OCS, Hiku, jiagu,
  Orion and NSESche.
- Topologies: 20-node homogeneous and 20-node heterogeneous.
- Loads: low, middle and high.
- NSESche parameters: low `(r0=0.6, wq=0.5)`; middle/high
  `(r0=0.5, wq=0.6)`.
- NSESche operational refinement: `ready_order` for every load and topology.
- Common HPA, node/network profiles, workload profile set, frame duration,
  simulation horizon and runtime binary are identical across compared methods.
- Unique workload-tape keys: 120, shared byte-identically across all ten
  methods within a `(topology, load, seed)` group.
- Unique state-matched NSESche reference dependencies: 120.
- Analysis reuse is frozen for E2, E5, E6, E7, E8 and E9; each appears exactly
  once in the manifest summary.

At freeze time, tape SHA values were unbound, all 120 reference dependencies
were unbuilt, and the run root contained only the unbound manifest and the
frozen FaaSRank model.  There were no Q61--Q80 result, QC, canonical,
reference-table or tape-catalog files.

## 4. Observation retention and failure handling

All 20 preregistered observations per method/cell are retained after canonical
QC.  Statistical disadvantage is not a technical failure and does not permit
seed removal, replacement or result-conditioned reruns.  A technical failure
is limited to the plan's crash, panic, OOM, I/O, truncation, hash, nonfinite,
frame-continuity or count-invariant conditions and may retry only the same
seed/tape/config/binary.

If a complete cell fails the dual-first gate, execution stops before the next
cell.  The complete failed batch is retained for diagnosis.  Any later method
change requires a new method hash, a development-stage diagnosis and an
independent fresh 20-seed confirmation bank; it cannot rewrite this formal
batch.

## 5. Canonicalization and analysis gate

After each 200-run cell, the result-blind Windows canonical-path reconciler
must produce a receipt scoped to exactly that topology/load and manifest.  It
may verify or copy byte-identical run trees but cannot inspect scientific
metric values for selection or reexecute the simulator.

The cell analyzer then requires:

- exactly 200 canonical QC-valid runs and exactly 20 paired seeds per method;
- one pairing signature per seed across all ten methods;
- one runtime identity and the frozen binary hash;
- a valid `NSE_SUMMARY_V1` for every run;
- `strict_eq15_ready=true` and `stream_contract_ready=true` on every NSESche
  run;
- complete finite run-level QPR coverage;
- NSESche mean throughput strictly above all nine baselines; and
- NSESche mean QPR strictly above all nine baselines.

The immutable cell report records all seed-level rows and artifact hashes.  A
passing dual-metric report authorizes only the next cell; it does not by itself
close a paper section.

## 6. Verification at freeze

The generated manifest validated with 1,200 unique run IDs, 1,200 unique run
specification hashes, 60 cells of 20 runs, 120 tape keys and 120 unique
reference keys.  The full protocol suite passed 178/178 tests after the formal
protocol implementation; the focused corrected-runtime suite passed 7/7 after
the reuse-summary regression assertion was added.  `git diff --check` passed.

No main-paper experiment was paper-ready closed at this freeze point.  The next
scientific operation is input-only capture of all 120 Q61--Q80 tapes, followed
by tape/model/reference binding.  The first authorized online operation is the
200-run homogeneous-low cell.
