# G8 frontier-only attribution analyzer audit

Date: 2026-09-04  
Branch: `agent/tsc-resubmit-final`  
Implementation base: `cf0e82bf6d1cfb525e70cb0b0e8456c86f759e25`  
Status: implementation frozen; exactly one real read-only invocation authorized

## Scope closed

The preregistered attribution analyzer is implemented without changing the
simulator, scheduler, workload tapes, offline references, canonical runs, or
prior selections. It admits exactly the frozen 25-run set and 20 within-bank,
same-tape pairs. G2 D66--D70 remains directional context and cannot be paired
or pooled with D71--D75.

Every selected canonical directory is revalidated against its formal manifest,
passing QC report, audit-manifest inventory, result path, runtime stream
contract, and artifact hashes before a scientific field is loaded. Active
windows are exactly those with `assigned_players > 0`; queue means use all and
only those windows. Dispatch classes must exactly partition assignments.
Reference coverage accepts only a finite keyed `offline_table` row or the exact
null/false `not_requested` shape; every other source or malformed record fails
closed.

The analyzer reports all frozen outcomes, solver/queue/initialization/reference
counters, completed-function activation and reconstructed frontier depth. It
emits five-value paired differences, ratios for positive outcome metrics,
mean, sample SD, descriptive 95% paired-t interval, sign counts, and all five
leave-one-seed-out means. The authorization decision is the exact conjunction
in `G8_FRONTIER_ONLY_ATTRIBUTION_PREREGISTRATION.md`; output flags always keep
implementation, new sampling, confirmation, and formal progression false.

## Frozen implementation receipts

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/analysis/g8_frontier_only_attribution.py` | `998793091293585ce8d224cdec08b719dcf5eed1fb4ca31f75bcf5369eff2ad2` |
| `scripts/reviewer_experiments/analysis/tests/test_g8_frontier_only_attribution.py` | `0fb6b67d0d342f282e5f907d5c3367f301ef60d4bdc355ad9d0448da9f3d6775` |

The analyzer additionally hash-checks six frozen helper/protocol sources and
records its own live source hash in the final report.

## Verification

- Black: 2 files unchanged after final formatting.
- Python compilation: passed for analyzer and directed test module.
- Directed analyzer tests: 6/6 passed.
- Combined G2/G3/G6/G7 protocol plus G8 analyzer regression: 31/31 passed.
- The single authorized source-contract dry validation passed with 8 frozen
  input receipts, 7 source receipts, 25 unique canonical runs, and 20 exact
  pairs.
- The target output directory
  `runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904/frontier_only_attribution`
  remained absent after validation.

## Authorization boundary

After this audit is committed, exactly one invocation may read the unchanged
inputs and atomically create the three preregistered attribution products. The
output directory is no-overwrite. A failed invocation must be retained and
audited before any correction or retry. No G8 scheduler implementation,
offline-reference build, workload generation, simulator sampling,
confirmation, formal-cell execution, figure, or manuscript claim is
authorized by this audit.
