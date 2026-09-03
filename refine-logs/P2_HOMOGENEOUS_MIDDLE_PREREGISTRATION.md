# P2 Homogeneous-Middle Claim-Reframed Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Status: `preregistered_implementation_only_online_blocked`

## 1. Paper role and authorization

This is the first new online cell after P1. It fills the middle-load group in
the submitted paper's 20-node homogeneous main comparison (Fig. 6) under the
claim-reframed V4 route. It does not overwrite, replace, or rerun the complete
homogeneous-low Q61--Q80 cell.

The former G1 cell report has `next_cell_authorized=false` because it applied
the superseded rule that NSESche had to rank first in both throughput and QPR.
V4 explicitly says that this flag is not automatically overridden: a new
claim-reframed protocol must first be preregistered after P1. That condition is
now met. P1-A passed its retained-log structural gate, and P1-B passed every
hard exact-small gate with the highest preregistered reference-quality label.

Authorization receipts frozen before any middle-load online result exists:

| Receipt | SHA-256 |
|---|---|
| `TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V4.md` | `68369bd695e56232fba76d7be6b91e11d899a2e6372c08234635ea53ec8295c0` |
| `P1_A_RETAINED_EVIDENCE_RESULT_AUDIT.md` | `16c221a2512b2afcc4923e690f9f3320154749359636a5ae1b87c1a8348425c4` |
| `P1_B_EXACT_SMALL_RESULT_AUDIT.md` | `33b8627a81560fd296508adebb5408c99ddacdd0541ff8a67d7d2074f45b093c` |
| retained low-load result audit | `9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16` |
| retained low-load machine report | `98558269dc6303f9245479f1a4aaa02d40ad0f727c3db491780558a0802f8073` |

No homogeneous-middle online workspace exists at preregistration. Source
implementation and tests, an immutable 200-run selection receipt, and a
zero-result implementation audit must be committed before execution.

## 2. Frozen scientific population

- Experiment: E1, steady middle load, homogeneous 20-node cluster.
- Methods: Greedy, Random, Hash, Load Balance, FaaSRank, OCS, Hiku, Jiagu,
  Orion, and NSESche, in the submitted-paper display order.
- Seeds: exactly Q61--Q80; workload, topology, and algorithm seed fields are
  equal within each run and paired across all ten methods.
- Runs: exactly `10 methods x 20 seeds = 200`. Every first canonical QC-valid
  result is retained. There is no result-conditioned extension, deletion,
  replacement, or method-specific replay.
- Workload inputs: the 20 existing middle/homogeneous tapes already bound in
  the ready manifest, one per seed and byte-identical across methods within a
  seed. Their measured arrival rates are accepted as frozen observations.
- Runtime: source commit
  `98f822cf2dcb878024a2ca39cc56533895ea692c`; binary 4,707,328 bytes; SHA-256
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`.
- Ready source manifest: document hash
  `5c5868a217cc47964752a036c0a25911f6dd18404447fe30d60fdd0d7597a91b`;
  file SHA-256
  `d8892c7226c0cd91757659f7a6ea61c5a095af6eee51045b2a31551f7ea8a38a`.
- NSESche: unchanged `ready_order`, strict Eq. (15),
  `(r0=0.5, wq=0.6)`, maximum four inner and two outer rounds, and the 20
  already-built state-matched middle/homogeneous offline-reference tables.
- Common simulation: 1 ms/frame, 1,000 arrival/observation frames, shared HPA,
  homogeneous CPU 150 and memory 5,000, shared candidate/lifecycle rules, and
  the already frozen 8,000--10,000 MB/s network profile.

The selection implementation must revalidate the complete 1,200-run source
manifest, then admit exactly the 200 runs matching E1 + homogeneous + middle.
It must verify 20 runs per method, 20 runs per seed, 200 unique run IDs and
specification hashes, 20 tape keys/hashes, 20 complete NSESche references,
the frozen FaaSRank model, and the runtime binary before writing the selection
receipt. Existing tape/reference artifacts are reused read-only; none is
rebuilt.

## 3. Output and execution contract

Registered root:
`runs/tscv1_p2_homogeneous_middle_q61_q80_98f822c_20260904/`

The root is separate from the preserved low-load workspace. The online batch
must use the full ready source manifest plus the exact run-ID allowlist in the
selection receipt. The protocol runner supplies the same manifest hash and
run-spec hashes used by the frozen inputs, permits at most three same-spec
attempts for declared technical failures, and compresses admitted JSONL files.
A scientifically poor but structurally valid outcome is canonical and cannot
be retried.

Required outputs are:

1. immutable selection receipt and its document/file hashes;
2. 200 canonical run directories plus append-only ledger;
3. result-blind canonical-path reconciliation scoped to homogeneous/middle;
4. the existing G1 integrity report (used only for raw-row and provenance
   validation; its old dual-first decision is retained as a diagnostic);
5. P2 run rows, method summaries, paired comparisons, old-PDF alignment,
   machine result receipt, and a middle-cell publication-diagnostic figure;
6. final result audit with hashes for all table and figure sources.

The generated page-9 image used to freeze old-PDF reading coordinates is a
temporary preregistration aid, not scientific data. It is removed after the
alignment extractor and its source hash are committed.

## 4. Frozen metrics and statistics

The independent unit is one complete run (`n=20` paired seeds). QPR is
calculated inside each run as throughput in requests/ms divided by mean drained
cohort latency in ms and simulator-internal cost per completed request. It is
never reconstructed from averaged bars.

For throughput, run-level QPR, completion ratio, mean latency, and cost per
completed request, report all 20 points per method, mean, sample SD, median,
and deterministic 10,000-resample BCa 95% intervals. Report ranks for the two
primary higher-is-better metrics with a frozen manuscript-order tie-break.

For NSESche against each of nine baselines in throughput and QPR, report paired
mean/median difference, 10,000-resample paired-difference BCa interval,
100,000-sign-flip two-sided paired permutation p-value, Cohen's `dz`, matched-
pairs rank-biserial effect, paired wins/ties/losses, and a paired relative-
change interval when every comparator denominator is positive. Holm correction
uses one frozen family of all 18 primary comparisons. All raw and adjusted
p-values remain descriptive; neither controls retention or retry.

QPR non-applicability from a valid zero-completion run is retained as a
scientific result. However, the cell cannot satisfy the full-analysis gate or
authorize high load unless all ten methods have 20/20 applicable QPR values.

The old Fig. 6 bars are provenance diagnostics only. Before middle outcomes
are exposed, the source PDF hash, page, axes, method order, bar centers, and
pixel-to-axis conversion are frozen in code. Approximate PDF readings are
reported as such, and `+/-15%` differences trigger a whole-scene explanation,
never a seed deletion, retry, or parameter change.

## 5. V4 continuation gate

Cell completion requires 200/200 canonical QC-valid runs, exact paired
coverage, one frozen runtime identity, complete run-level QPR, closed tables,
figure, receipts, and explicit reporting of all outcomes. NSESche need not rank
first for the cell to be publishable under V4.

The expensive-route stop rule is frozen exactly as follows:

1. rank methods by mean throughput and separately by mean QPR, descending;
2. NSESche must rank 6--10 in both metrics to enter the possible-stop branch;
3. for throughput, compare NSESche with the method ranked fifth in throughput;
   for QPR, compare it with the method ranked fifth in QPR;
4. stop only if the upper endpoint of both paired-difference BCa 95% intervals
   is strictly below zero.

If any integrity/full-QPR gate fails, high load is blocked and the valid data
remain retained. If the possible-stop branch is confirmed, high load and later
expensive matrices pause for resubmission-value review. Otherwise, a separate
homogeneous-high preregistration is authorized after this cell's result audit;
high is not authorized merely by completing online simulation.

## 6. Current stage decision

Only selection/analyzer/alignment/figure implementation and zero-result tests
are authorized now. The 200-run online batch remains blocked until those
sources, tests, source hashes, selection receipt, and an implementation audit
are committed. Heterogeneous, parameter, ablation, scaling, burst, QoS, and
pricing/welfare online blocks remain unopened.

