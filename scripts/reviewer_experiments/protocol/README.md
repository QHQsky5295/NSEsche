# Reviewer experiment protocol

This directory implements the result-blind execution boundary for E1-E9. The
formal adapter minimally wires immutable workload profiles and provenance into
the simulator; it does not change scheduler formulas, HPA decisions, or the
scientific result-acceptance policy.

## Frozen matrix

The default bank-A manifest contains 1,880 runs in 188 newly executed cells;
the bank-B manifest contains the same Cartesian product on disjoint seeds, for
3,760 fixed formal runs in total:

| Experiment | Newly executed cells | Seeds | Reuse rule |
| --- | ---: | ---: | --- |
| E1 | 10 methods x 3 loads x 2 topologies x 20 nodes = 60 | E01-E10 | none |
| E2 | 10 methods x 3 loads x 100/500 nodes = 60 | E01-E10 | 20-node homogeneous points reuse E1; load scales are 5/25 |
| E3 | 10 methods x 3 burst processes = 30 | E01-E10 | none |
| E4 | 10 methods x steady balanced-QoS = 10 | E01-E10 | none |
| E5 | 4 NSEsche ablations x 3 loads = 12 | E01-E10 | workload/QoS exactly match E1 (`mixed`); full NSEsche reuses paired E1 |
| E6 | cp_br/onsocmax x middle/high = 4 new cells | E01-E10 | the original 10 methods at heterogeneous middle/high are identity-checked reuse of E1 (20 cells); each new policy builds and replays its own state-matched offline welfare reference |
| E7 | 3 loads x 4 axial neighbours = 12 | E01-E10 | centre points are reused; only 12 neighbour cells run |
| E8/E9 | 0 | 0 | analysis-only reuse of canonical E1-E7 artifacts |

E11-E20 are a mandatory, predeclared second bank for every formal cell. The
legacy internal name `ci_extension` means bank B; it is not conditional on any
observed result. E7 uses the same fixed `n=20` paired seed bank as E1-E6.

The manifest seals every reused analysis point as an
`NSE_ANALYSIS_REUSE_RULE_V1` record.  E2's 20-node point, E5's Full NSESche
arm, E6's original ten methods, and E7's three centre points are projected only
from their declared E1 runs.  Every rule fixes its source selector, requires an
identity workload and cluster transformation, states the target cell template,
and carries a SHA-256 of the rule itself.  A rule is provenance, not permission
to substitute a similar-looking workload.

## Common-HPA, placement-only invariant

Every run entry embeds the same HPA object and references the same
`common_hpa_hash`. The frozen defaults are target `0.5`, tolerance `0.1`, a
one-frame check period, scale-to-zero when idle, at least one instance while a
request is pending, 100 observations for `careful_down`, `least_task` scale-up
placement, and `no_evict` container retention. `max_instances: null` is an
explicit value: it means that this protocol adds no separate numeric instance
cap beyond the common simulator/runtime capacity. It is not an unfrozen field.

The study object is request placement. Thus every legend name denotes a
placement-only adaptation running with the common HPA, cold-start model,
container lifecycle, queue, and runtime:

```text
Scheduling Policy + Common HPA/Runtime
```

It does not claim to reproduce or compare each baseline's complete native
scaling, prewarming, or container-management system. Scheduler implementations
may emit placement `ScheCmd` decisions; common HPA/runtime owns scale-up and
scale-down decisions.

The legacy legend names are retained for figure compatibility. They denote the
following placement-only adaptations, with every non-placement subsystem
provided by the common platform:

| Legend method | Retained scheduling/placement mechanism | Replaced by the common platform |
| --- | --- | --- |
| ORION | DAG critical-path priority, function priority, locality, and node scoring | right-sizing, bundling, prewarming, and scaling |
| Jiagu | prediction, pre-decision, capacity-aware ordering, and decision cache | dual-stage scaling |
| Hiku | idle-worker queue and active-connection ordering | worker provisioning and container eviction |
| OCS | invocation history, container state, and node-placement scoring | Zygote, help-start, and cache lifecycle |
| FaaSRank | frozen score--rank--select placement model | non-public scaling/prewarming |

The figure caption and manuscript should use the following boundary statement:
“Baseline names denote placement-only adaptations under a common HPA,
cold-start model, and container runtime, rather than complete reproductions of
the original end-to-end systems.”

Each separated-HPA window is committed as one atomic batch in the order
`scale-up -> placement -> scale-down`. A scale-down targeting the same
`(function, node)` selected by a placement in that window is deferred; formal
QC requires zero placement-command rejection at commit time.

NSESche keeps Eq. (6)'s queue term dimensionless by freezing
`queue_normalization_mode: window_max`:

\[
q_{\max}(t)=\max\left(1,\max_{n\in N}q_n(t)\right),\qquad
\mathrm{Pressure}_n(t)=u_n^{cpu}+u_n^{mem}+\frac{q_n(t)}{q_{\max}(t)}.
\]

Here `q_n(t)` is the pending-plus-runnable backlog observed at the scheduling
window. Thus the queue ratio is in `[0,1]`; parent-blocked, data-blocked, and
starting-container tasks remain separately observable. A fixed normalizer is
available only as an explicit non-default protocol mode and must carry a
finite positive value. The selected mode/value and the per-window normalizer
are stored in the manifest and scheduler log, and changing them invalidates
the offline-reference state-key schema.

## End-to-end execution order

Run the stages below from the repository root. Each binding writes a new
manifest; do not overwrite the earlier stage, because its hash is provenance.
The reviewed protocol is pinned to the Python environment that contains the
validated NumPy/Matplotlib/psutil stack; the adapter passes this same
interpreter to Rust helpers through `SERVERLESS_SIM_PYTHON`:

```powershell
$ReviewerPython = 'D:\Anaconda3\python.exe'
```

### 1. Initialize and expand

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol init-config protocol.local.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol expand manifest.unbound.json --config protocol.local.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol validate manifest.unbound.json
```

### M1 non-formal method qualification

Before any E01--E20 formal run, execute the frozen M1 gate on the disjoint
paired D01--D20 bank.  The complete development manifest contains the nine
baselines and three preregistered, equation-preserving NSESche operational
candidates over all six 20-node E1 load/topology cells.  It is explicitly
non-formal and cannot be exported into paper figures.

First create the complete source, capture each of its 120 unique workload
tapes exactly once, and derive the fixed D01--D05 NSESche-only screen:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol m1-development `
  m1.development.unbound.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  m1.development.unbound.json m1-ledger m1-tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  m1.development.unbound.json m1-tapes.catalog.json m1.development.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-m1-screen `
  m1.development.tapes.json m1.screen.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  m1.screen.tapes.json m1-ledger m1-screen-references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  m1.screen.tapes.json m1-screen-references.catalog.json m1.screen.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  m1.screen.ready.json m1-ledger
& $ReviewerPython -m scripts.reviewer_experiments.protocol analyze-m1-screen `
  m1.screen.ready.json m1-ledger\canonical m1.candidate-selection.json
```

The selection receipt maximizes the worst candidate-relative mean across
throughput and QPR in all six cells, then the mean of those twelve ratios,
then joint first-place cell count, with the preregistered simplicity order as
the final tie-break.  All five paired observations are retained.

Next derive the selected-candidate qualification product from the same
tape-bound source.  This contains all ten comparison methods over all six
cells and all D01--D20 tapes (1,200 runs).  Calibrate FaaSRank using the
tape-bound development source and the fixed commands in step 4, then bind its
frozen model to the qualification shard before building the selected
NSESche candidate's 120 offline references:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-m1-qualification `
  m1.development.tapes.json m1.candidate-selection.json `
  m1.qualification.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  m1.qualification.tapes.json faasrank.frozen.json `
  m1.qualification.model.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  m1.qualification.model.json m1-ledger m1-qualification-references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  m1.qualification.model.json m1-qualification-references.catalog.json `
  m1.qualification.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  m1.qualification.ready.json m1-ledger
```

Only if the selected NSESche candidate has the highest mean throughput and
QPR in each of the six complete D01--D20 cells may its binary and parameters
be frozen for E01--E20.  A failed qualification remains complete development
evidence; no seed may be removed or replaced based on its observed result.

### G1 corrected-runtime refreeze and D61--D65 screen

After the common cold-start transition correction, build one final runtime and
bind its full Git commit and executable SHA-256. Reuse D44 only as the
technical tape, rebuild its reference, and admit the real feedback stream
before creating any D61 workload:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol g1-technical-replay `
  m1.dynamic.screen.ready.json g1.technical.unbound.json `
  --simulator-exe $FrozenSimulator --runtime-source-commit $FrozenCommit
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  g1.technical.unbound.json g1-stages g1.technical.reference.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  g1.technical.unbound.json g1.technical.reference.catalog.json `
  g1.technical.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  g1.technical.ready.json g1-technical-workspace
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  admit-g1-technical-replay g1.technical.ready.json `
  g1-technical-workspace\canonical g1.technical-gate.json
```

Only after the immutable technical-gate receipt exists, create and execute the
fresh strict-Eq.15 `3 x 6 x 5 = 90` screen:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol g1-corrected-screen `
  g1.screen.unbound.json --technical-gate g1.technical-gate.json `
  --simulator-exe $FrozenSimulator --runtime-source-commit $FrozenCommit
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  g1.screen.unbound.json g1-stages g1.tape.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  g1.screen.unbound.json g1.tape.catalog.json g1.screen.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  g1.screen.tapes.json g1-stages g1.reference.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  g1.screen.tapes.json g1.reference.catalog.json g1.screen.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  g1.screen.ready.json g1-screen-workspace
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  analyze-g1-corrected-screen g1.screen.ready.json `
  g1-screen-workspace\canonical g1.selection.json
```

The D61--D65 observations are non-formal and result-blind. The analyzer uses
the preregistered candidate/C0 global maximin rule and refuses an incomplete,
undefined, contract-invalid, or selectively edited screen.

### G2 D66--D70 strict-initialization development

After freezing the G2 source and one release executable, create the complete
non-formal product. It contains 90 candidate runs over all six cells and 45
paired homogeneous-low runs for the nine baselines. The 135 runs share exactly
30 workload tapes, and only the 90 NSESche runs require state-matched reference
tables:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  g2-initialization-development g2.unbound.json `
  --simulator-exe $FrozenSimulator --runtime-source-commit $FrozenCommit
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  g2.unbound.json g2-stages g2.tape.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  g2.unbound.json g2.tape.catalog.json g2.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  g2.tapes.json $FrozenFaasRankModel g2.model.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  g2.model.json g2-stages g2.reference.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  g2.model.json g2.reference.catalog.json g2.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  g2.ready.json g2-workspace
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  analyze-g2-initialization g2.ready.json `
  g2-workspace\canonical g2.selection.json
```

The analyzer requires every one of the 135 QC-valid rows, the exact runtime
initialization contract, and complete run-level QPR. It first applies the
six-cell candidate/C0 global maximin rule and then requires the selected
candidate to strictly exceed all nine paired homogeneous-low baselines in both
mean throughput and mean QPR. Failure closes G2 and authorizes no formal bank.
The D66--D70 observations never become paper evidence.

### G3 D71--D75 operational E0 development

After the operational E0 source, protocol/analyzer, and one release executable
are frozen, create the complete non-formal product. C0 is unchanged
`ready_order`; C1 applies the corrected strict-PNE E0 selector only in the
first outer round; C2 applies it in every outer round. The product contains 90
candidate runs over all six cells and 45 paired homogeneous-low runs for the
nine baselines, sharing exactly 30 workload tapes:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  g3-e0-operational-development g3-e0.unbound.json `
  --simulator-exe $FrozenSimulator --runtime-source-commit $FrozenCommit
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  g3-e0.unbound.json g3-e0-stages g3-e0.tape.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  g3-e0.unbound.json g3-e0.tape.catalog.json g3-e0.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  g3-e0.tapes.json $FrozenFaasRankModel g3-e0.model.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  g3-e0.model.json g3-e0-stages g3-e0.reference.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  g3-e0.model.json g3-e0.reference.catalog.json g3-e0.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  g3-e0.ready.json g3-e0-workspace
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  analyze-g3-e0-operational g3-e0.ready.json `
  g3-e0-workspace\canonical g3-e0.selection.json
```

The analyzer retains all 135 QC-valid rows and fails closed on any runtime
schema, strict-PNE certificate, selected-state/outer-feedback hash, QPR, or
artifact mismatch. A non-control winner must improve both throughput and QPR
over C0 in all six cell means, beat all nine homogeneous-low baselines in both
metrics, and remain at or below 9x C0 aggregate active-window `solve_us` in
every cell. D71--D75 never become formal evidence, and no result-conditioned
seed replacement or extension is permitted.

### G6 D71--D75 parent-scheduled lookahead development

G6 reuses the frozen G3 workload tapes and the 50 retained homogeneous-low C0
and nine-baseline results. It creates only five new NSESche runs, one for each
D71--D75 tape, under the `lookahead_preall_sched` operational refinement. The
new candidate must build its own five offline social-reference tables; a C0
reference cannot be relabeled or reused.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  g6-lookahead-development g6.unbound.json `
  --simulator-exe $FrozenSimulator --runtime-source-commit $FrozenCommit `
  --g3-manifest $G3ReadyManifest --g3-selection $G3Selection `
  --g3-canonical-root $G3CanonicalRoot
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  project-tape-catalog g6.unbound.json $G3TapeCatalog g6.tape.catalog.json `
  --output-root g6-stages
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  bind-tapes g6.unbound.json g6.tape.catalog.json g6.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  build-references g6.tapes.json g6-stages g6.reference.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  bind-references g6.tapes.json g6.reference.catalog.json g6.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  run g6.ready.json g6-workspace
& $ReviewerPython -m scripts.reviewer_experiments.protocol `
  analyze-g6-lookahead g6.ready.json g6-workspace\canonical g6.selection.json
```

The analyzer revalidates all five new runs and all 50 frozen controls. It
requires parent-scheduled early binding and positive startup overlap in every
seed, complete dispatch and offline-reference accounting, the frozen paired
win/floor/completion/latency/solve-time gates, and mean throughput/QPR above
the best frozen baselines. All valid runs are retained. A pass authorizes only
a separate Q61--Q80 confirmation preregistration; it does not make D71--D75
formal evidence or directly authorize confirmation sampling.

### Formal E1 homogeneous execution shard

Use `shard-e1-homogeneous` when the immediate execution block is the complete
20-node homogeneous E1 comparison. This is a formal execution manifest, not a
free-form selector: the command accepts no run IDs or method/load filters. It
derives exactly the following Cartesian product from a complete validated full
manifest:

- all ten frozen placement methods;
- low, middle, and high load;
- every seed fixed by the source `seed_stage`;
- E1, homogeneous topology, and 20 nodes only.

This produces 300 runs for `initial` (`E01`--`E10`), 300 for
`ci_extension` (`E11`--`E20`), or 600 for `all` (`E01`--`E20`). The shard has
`formal_results_eligible: true`, seals the source manifest and file hashes plus
every source run and reuse rule, and recomputes its 30/60 offline-reference
dependencies. A derived or incomplete source is rejected. Tape, model, and
reference binding may change run IDs, so validation follows each run by the
sealed `(cell_id, seed)` lineage and immutable workload/cluster fields.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e1-homogeneous `
  manifest.unbound.json manifest.e1-homogeneous.unbound.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  manifest.e1-homogeneous.unbound.json e1-homogeneous-ledger e1-homogeneous-tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  manifest.e1-homogeneous.unbound.json e1-homogeneous-tapes.catalog.json `
  manifest.e1-homogeneous.tapes.json
```

E1 uses the mixed QoS profile, for which SLA targets are disabled;
therefore `run-sla-pilots`, `freeze-sla`, and `bind-sla` are not dependencies
of this shard. FaaSRank-P still requires its independent calibration and frozen
model, using `manifest.e1-homogeneous.tapes.json` in step 4 below. Then build
and bind the shard's NSESche references:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  manifest.e1-homogeneous.tapes.json faasrank.frozen.json `
  manifest.e1-homogeneous.model.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  manifest.e1-homogeneous.model.json e1-homogeneous-ledger `
  e1-homogeneous-references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  manifest.e1-homogeneous.model.json e1-homogeneous-references.catalog.json `
  manifest.e1-homogeneous.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol validate `
  manifest.e1-homogeneous.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  manifest.e1-homogeneous.ready.json e1-homogeneous-ledger
```

The FaaSRank calibration commands remain exactly those in step 4; substitute
the tape-bound E1 shard wherever that step names `manifest.sla.json`. The
training tape is checked against all 30 or 60 evaluation-tape hashes in the
shard before the frozen model can be bound.

### Formal E1 heterogeneous execution shard

`shard-e1-heterogeneous` is the topology-symmetric formal boundary for Fig. 9.
It accepts the same complete validated full manifest as the homogeneous
command, but derives only the fixed 20-node heterogeneous E1 Cartesian product:
all ten methods, all three loads, and every seed declared by `seed_stage`. It
does not accept run IDs or method/load filters. The output contains 300 runs and
30 reference-build dependencies for `initial` or `ci_extension`, and 600 runs
and 60 dependencies for `all`. Its source/file hashes, per-run lineage,
reuse-rule hashes, heterogeneous node/network bindings, and reference
dependencies remain validated after tape, model, and reference binding.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e1-heterogeneous `
  manifest.full.unbound.json manifest.e1-heterogeneous.unbound.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  manifest.e1-heterogeneous.unbound.json e1-heterogeneous-ledger `
  e1-heterogeneous-tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  manifest.e1-heterogeneous.unbound.json e1-heterogeneous-tapes.catalog.json `
  manifest.e1-heterogeneous.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  manifest.e1-heterogeneous.tapes.json faasrank.frozen.json `
  manifest.e1-heterogeneous.model.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  manifest.e1-heterogeneous.model.json e1-heterogeneous-ledger `
  e1-heterogeneous-references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  manifest.e1-heterogeneous.model.json e1-heterogeneous-references.catalog.json `
  manifest.e1-heterogeneous.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol validate `
  manifest.e1-heterogeneous.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  manifest.e1-heterogeneous.ready.json e1-heterogeneous-ledger
```

These commands are intentionally separate from the homogeneous artifact tree;
they do not launch when the shard is derived, and neither topology can be used
as the source of another formal shard.

### Formal E2 weak-scaling execution shard

`shard-e2` is the fixed weak-scaling boundary.  It derives the two physical
products (100 nodes at (5\times) load and 500 nodes at (25\times) load) for
all ten placement methods, three loads, and every seed in the source stage.
The 20-node point is not re-executed: the shard seals the complete matching
20-node homogeneous E1 source lineage and the single
`E2_FROM_E1_20NODE_HOMOGENEOUS_V1` rule.  Counts are therefore 600 physical /
300 reused rows for `initial` or `ci_extension`, and 1200 / 600 for `all`.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e2 `
  manifest.full.unbound.json manifest.e2.unbound.json
```

E2 usually starts from the catalog already audited for homogeneous E1.  The
projection command verifies the source catalog hash and every parent tape,
copies only keys required by the E2 manifest, derives any missing 5x/25x tapes,
and refuses to leave extra keys in the result:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol project-tape-catalog `
  manifest.e2.unbound.json e1-tapes.catalog.json e2-tapes.catalog.json `
  --output-root .
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  manifest.e2.unbound.json e2-tapes.catalog.json manifest.e2.tapes.json
```

The 20-node point must be merged only after both E1 and E2 canonical trees
have passed their pairing audits.  The E2 initial shard may use either the
matching initial E1 homogeneous shard or an audited all-stage E1 homogeneous
manifest; in the latter case the exporter materializes only the sealed E01--E10
lineage and retains E11--E20 as non-projected source rows.  This command checks
the common HPA, profile, frozen model, sealed rule, and every E1 stable lineage
hash before writing the 20/100/500-node table and a separate audit record:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol export-e2-with-e1-reuse `
  --e2-manifest e2.ready.json --e2-workspace e2-ledger `
  --e1-manifest e1-homogeneous.ready.json --e1-workspace e1-homogeneous-ledger `
  --output analysis/e2-runs.csv --coverage analysis/e2-coverage.csv `
  --audit analysis/e2-e1-reuse-audit.json
```

The merged CSV labels reused rows as `materialized_reuse`; they are not new
simulator executions.  A missing source, changed tape/config hash, failed QC,
or duplicate cell/seed causes the export to fail closed.

### Combined initial E3/E4 execution shard

`shard-e3-e4` is the non-selectable formal boundary for the reviewer burst and
balanced-QoS block. It accepts only the complete bank-A 1,880-run source and
derives exactly 400 physical runs:

- E3: all ten methods, all three frozen burst transforms, and E01--E10 (300
  runs). Arrivals and the fixed throughput observation window end at frame
  1000; the admitted cohort may drain through frame 4000.
- E4: all ten methods under the steady balanced-QoS tape and E01--E10 (100
  runs), with a 1000-frame arrival/observation/total horizon.

All 400 runs use the middle-load frozen profile and the same 20-node
heterogeneous cluster. The marker seals the three exact burst definitions,
every source `(cell_id, seed)` lineage record, all reuse-rule hashes, 40
NSESche offline-reference dependencies, and the requirement to bind workload
tapes, SLA targets, the frozen FaaSRank model, and offline references before
execution. The CLI accepts no method, burst, or run-ID filters.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e3-e4 `
  manifest.initial.full.unbound.json manifest.e3-e4.initial.unbound.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  manifest.e3-e4.initial.unbound.json e3-e4-ledger e3-e4-tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol derive-required-tapes `
  manifest.e3-e4.initial.unbound.json e3-e4-tapes.catalog.json --output-root .
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  manifest.e3-e4.initial.unbound.json e3-e4-tapes.catalog.json `
  manifest.e3-e4.initial.tapes.json
```

Run the isolated SLA pilot/freezer against a separately tape-bound formal E1
template (the pilot implementation intentionally requires an E1 template),
then apply the resulting immutable SLA artifact with `bind-sla` to this
E3/E4 manifest. Finally apply `bind-faasrank-model`, `build-references`, and
`bind-references` in the documented order before `validate` and `run`. The E1
pilot and the E3/E4 evaluations still share the frozen common HPA/runtime and
workload-profile contract; no E3/E4 result is used to choose a target.
Deriving this shard does not start any pilot, reference build, or formal run.
`shard-smoke` output remains ineligible and cannot replace any of these 400
observations.

The ready manifest remains the immutable 400-run product even when execution
is staged. A preregistered baseline-first block may pass the nine baseline
method names through repeated `run --method METHOD` arguments; the runner
rejects any requested method absent from the selected manifest scope. Audit the
same frozen subset with repeated `protocol.pairing --method METHOD` arguments
and an exact `--expected-methods` declaration. This does not derive a smaller
manifest or relax final coverage: the later publication audit still requires
all ten methods and all 400 entries. Method staging must be fixed before any
selected metric is opened, and it never authorizes a performance-driven rerun.

### Formal E3/E4 bank-B shard

Use the compatibility command `shard-e3-e4-ci-extension` to derive the
mandatory, disjoint E11--E20 bank-B observations. It accepts only the complete
1,880-run `ci_extension` source and derives exactly
400 physical runs: 300 E3 runs (ten methods by three frozen bursts by ten
seeds) and 100 E4 balanced-QoS runs (ten methods by ten seeds), with 40
NSESche offline-reference dependencies.

The extension has no method, burst, seed, or run-ID selectors. Its marker
seals the exact balanced-QoS runtime, burst-parent and steady-tape keys,
physical source lineage, common reuse-rule hashes, and the same tape/SLA/model/
reference prerequisites as the initial shard. Keep the completed E01--E10
artifact immutable and combine it with this E11--E20 artifact only in the
audited analysis step; do not execute an `all` shard and duplicate initial
observations.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol expand `
  manifest.ci-extension.full.unbound.json --seed-stage ci_extension
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e3-e4-ci-extension `
  manifest.ci-extension.full.unbound.json `
  manifest.e3-e4.ci-extension.unbound.json
```

Project or capture the E11--E20 balanced base tapes, derive all three burst
tapes, and then bind tapes, the pre-frozen SLA artifact, the same frozen
FaaSRank model, and the 40 references before validation and execution. No
E3/E4 outcome participates in any execution decision or frozen input.

### Combined bank-A E5/E6/E7 execution shard

`shard-e5-e6-e7` derives the 280 physical bank-A runs (120 E5 ablations,
40 E6 welfare comparators, and 120 E7 axial neighbours), with 250 reference
build dependencies.  It seals 260 role-specific projections of 210 unique
heterogeneous E1 source runs: E5 full NSESche (30), E6 original placement
methods (200), and E7 centres (30).  The command is bank-A only and
does not run the simulator or mutate the E1 artifact tree.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e5-e6-e7 `
  manifest.initial.full.unbound.json manifest.e5-e6-e7.initial.unbound.json
```

The marker and JSON schema validate each physical lineage after binding;
the role-specific E1 merge audit additionally verifies the supplied formal
heterogeneous E1 manifest before those points enter an analysis table.

### Formal bank-B E5/E6/E7 execution shard

`shard-e5-e6-ci-extension` is retained as a compatibility command name and
derives the mandatory, disjoint E11--E20 bank-B observations.  Its fixed
product is 280 physical runs (E5=120, E6=40, and E7=120), 250 offline-reference
dependencies, and 260 E1 reuse projections over 210 unique heterogeneous E1
sources.  No result-dependent trigger controls whether this bank is executed.

The command accepts only a complete `ci_extension` E1--E7 manifest.  It has no
method, load, variant, seed, or run-ID selectors, so a precision trigger cannot
be used to select favourable cells.  The completed bank-A shard remains
immutable; final E5/E6/E7 statistics audit and combine E01--E10 from bank A
with E11--E20 from bank B.  Do not execute an `all` shard after the two banks,
because that would duplicate already-valid observations.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol expand `
  manifest.ci-extension.full.unbound.json --seed-stage ci_extension
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-e5-e6-ci-extension `
  manifest.ci-extension.full.unbound.json `
  manifest.e5-e6.ci-extension.unbound.json
```

The existing `project-tape-catalog` command can project the exact E5/E6/E7 tape
key set from an audited E11--E20 source catalog.  Before reuse rows enter the
final analysis, their sealed E5/E6/E7 lineage must be matched to the corresponding
formal E1 heterogeneous CI-extension manifest and canonical results.

### Auditable integration-smoke shard (optional, never formal data)

Use `shard-smoke` to exercise the real capture, binding, reference-build,
runner, and QC path without preparing all 1,880 bank-A tapes or 410 reference
tables. The command selects exact run declarations from a validated full
manifest; it preserves their specifications and all sealed reuse rules, records
the source manifest/file hashes and source run/spec hashes, and writes
`formal_results_eligible: false`. For the default E1 low-load Greedy/NSESche
pair:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol shard-smoke `
  manifest.unbound.json manifest.smoke.unbound.json `
  --run-id TSCv1.E1.homogeneous.n20.low.greedy.FE01.ce00a105 `
  --run-id TSCv1.E1.homogeneous.n20.low.sche_nash.FE01.8720160a `
  --purpose 'Greedy/NSESche capture-bind-reference-replay-QC integration check'
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes `
  manifest.smoke.unbound.json smoke-ledger smoke-tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes `
  manifest.smoke.unbound.json smoke-tapes.catalog.json manifest.smoke.tapes.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references `
  manifest.smoke.tapes.json smoke-ledger smoke-references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references `
  manifest.smoke.tapes.json smoke-references.catalog.json manifest.smoke.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol run `
  manifest.smoke.ready.json smoke-ledger
```

Run IDs are content-addressed and can change if the full configuration changes;
select the exact IDs from that newly expanded source manifest. Binding may also
change the derived shard's current run-ID suffix, so omitting `--run-id` on the
final `run` safely executes only the shard's selected entries. The canonical
analysis exporter rejects a smoke marker even if someone changes the eligibility
field, and rejects an explicit false eligibility field even if the marker is
removed. Smoke outputs are pipeline evidence only and must never enter figures,
confidence intervals, or significance tests.

### 2. Capture, derive, and bind workload tapes

The `reviewer-v3` formal protocol freezes one tracked per-DAG frequency profile
for each load before any seed is run. Low and middle preserve the exact
submission-era cache maps, with audited expected rates of 1934.66 and 2533.14
requests/s. High is the explicit
`submission-era-azure-cdf-high-7k-v1` profile: every one of the 50 historical
per-DAG means is multiplied by `0.24372876535488303`, every CV is unchanged,
and the audited expected rate is 7000 requests/s. Its provenance retains the
historical cache SHA-256, the pre-normalization expected rate (28720.45
requests/s), and the submission-era observed rate (27924 requests/s).

The tracked JSON file, full-file SHA-256, per-DAG map hash, profile ID, and
source metadata are sealed into the protocol, manifest, tape plan, capture
receipt, runtime environment, and QC checks. The simulator never reads the
ignored legacy cache in formal mode. Seeds `E01`--`E20` still independently
control per-frame arrival noise, DAG/topology generation, and algorithm RNG;
they no longer resample the heavy-tailed Azure CDF itself.

This identity change invalidates every earlier unbound manifest, V1 tape
catalog/receipt, and captured tape. Start in a fresh formal result directory
and expand a new `reviewer-v3` manifest. In particular, do not bind or reuse the
partially captured `formal_e1_homogeneous_v3_20260811` directory.

Capture every unique same-seed base tape, derive the predeclared E2 5x/25x
weak-scaling tapes and E3 burst tapes, then bind the complete catalog:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-base-tapes manifest.unbound.json run-ledger tapes.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol derive-required-tapes manifest.unbound.json tapes.catalog.json --output-root .
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-tapes manifest.unbound.json tapes.catalog.json manifest.tapes.json
```

The **workload package** is more than a displayed load label. Its immutable core
is a versioned tape containing `workload_seed` and the ordered
`{frame, dag_id}` arrival events. The catalog binds its file SHA-256, event
count, DAG-order hash, first/last frame, measured arrival rate and derivation
receipt. A capture receipt additionally binds the function/DAG/QoS semantic
hash and the capture environment; formal QC checks the runtime semantic hash
against it. E2 copies each parent event exactly 5 or 25 times in its frame. E3
CDF-remaps arrival frames while retaining the event count and DAG order. The
package provenance describes the Azure-trace-derived empirical CDF artifacts;
it is not represented as a direct one-event-per-raw-trace replay. Every method
in a paired cell reads the exact same package hash.

### 3. Run isolated SLA pilots, freeze, and bind targets

Before formal balanced-QoS E3/E4 runs, launch the measured isolated pilots from
the tape-bound manifest. `run-sla-pilots` runs one `all_latency` and one
`all_cost` pilot plus every predeclared `all_throughput` capacity factor before
inspecting any capacity result. The sustainable capacity must be a contiguous
passing prefix followed by an observed failing factor; otherwise the stage
fails closed and no target is frozen. With the default predeclared grid this is
six measured runs (two class pilots plus four capacity candidates), which
produce exactly three immutable freezer inputs.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol run-sla-pilots `
  manifest.tapes.json sla-pilots `
  --seed E01 --load low --topology homogeneous `
  --capacity-factor 1 --capacity-factor 2 --capacity-factor 3 --capacity-factor 4
& $ReviewerPython -m scripts.reviewer_experiments.protocol freeze-sla frozen-sla.json `
  --latency-pilot sla-pilots-E01\pilot_artifacts\isolated-latency.json `
  --latency-pilot sla-pilots-E02\pilot_artifacts\isolated-latency.json `
  --latency-pilot sla-pilots-E03\pilot_artifacts\isolated-latency.json `
  --throughput-pilot sla-pilots-E01\pilot_artifacts\isolated-throughput-capacity.json `
  --throughput-pilot sla-pilots-E02\pilot_artifacts\isolated-throughput-capacity.json `
  --throughput-pilot sla-pilots-E03\pilot_artifacts\isolated-throughput-capacity.json `
  --cost-pilot sla-pilots-E01\pilot_artifacts\isolated-cost.json `
  --cost-pilot sla-pilots-E02\pilot_artifacts\isolated-cost.json `
  --cost-pilot sla-pilots-E03\pilot_artifacts\isolated-cost.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-sla manifest.tapes.json frozen-sla.json manifest.sla.json
```

The launcher records its immutable audit at
`sla-pilots\sla_pilot_report.json`. Its default capacity acceptance rule is
completion ratio at least `0.99`, zero drop/reject/timeout, and zero final
queue, active requests, and tasks in the system. The total horizon is 4000 ms,
with arrivals confined to the first 1000 ms. The isolated latency and cost
pilots must satisfy the same completion and final-drain rule before their
measurements can be frozen.

For the resubmission, repeat the complete preregistered pilot stage for the
fixed E01--E03 pilot seeds. The freezer requires the same three seeds for all
roles, then uses a conservative envelope before applying the unchanged target
multipliers: maximum latency p95, minimum sustainable throughput, and maximum
cost per request. A single-seed invocation remains supported for protocol
fixtures, but the paper workflow uses the three-seed form above.

If the complete default grid fails because even factor 1 is unsustainable, do
not relax those acceptance rules. Preregister a new workspace and a nested
lower-base bracket with `--capacity-base-divisor D` and every factor `1..D`.
Candidate `k` retains the stable parent-event ranks whose residue modulo `D`
is below `k`; consequently candidates are nested, preserve event order, and
candidate `D` contains the complete original tape exactly once. For example,
`D=4` applied to a 1920-event parent declares 480, 960, 1440, and 1920-event
candidates. The failed workspace remains immutable and must not be overwritten.

### 4. Calibrate, freeze, and bind FaaSRank-P

Calibration uses a separately captured tape and a fully executable,
result-blind stage. First capture and hash-check the independent training tape;
then preregister the complete candidate-by-seed matrix, run every cell, select
by the frozen mean-QPR objective, freeze the resulting linear
Score-Rank-Select model, and bind it. The supplied candidate grid is
`scripts\reviewer_experiments\protocol\faasrank_candidates.json`. Use
`FTR01`--`FTR05` as the paired calibration seeds; these are deliberately
distinct from the formal `E01`--`E20` evaluation seeds. The runner rejects a
model whose training-tape hash equals any evaluation-tape hash.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol capture-faasrank-training-tape `
  manifest.sla.json faasrank-calibration `
  --workload-seed FAASRANK-TRAIN-W01 --template-seed E01 --load low
& $ReviewerPython -m scripts.reviewer_experiments.protocol preregister-faasrank-calibration `
  faasrank-calibration\faasrank.calibration-plan.json `
  --training-tape faasrank-calibration\training_input\faasrank_training_tape.json `
  --candidates scripts\reviewer_experiments\protocol\faasrank_candidates.json `
  --seed FTR01 --seed FTR02 --seed FTR03 --seed FTR04 --seed FTR05
& $ReviewerPython -m scripts.reviewer_experiments.protocol run-faasrank-calibration `
  manifest.sla.json faasrank-calibration `
  --training-tape faasrank-calibration\training_input\faasrank_training_tape.json `
  --plan faasrank-calibration\faasrank.calibration-plan.json `
  --template-seed E01 --load low
& $ReviewerPython -m scripts.reviewer_experiments.protocol freeze-faasrank-model `
  faasrank.frozen.json `
  --training-tape faasrank-calibration\training_input\faasrank_training_tape.json `
  --plan faasrank-calibration\faasrank.calibration-plan.json `
  --training-results faasrank-calibration\faasrank_calibration_results.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-faasrank-model `
  manifest.sla.json faasrank.frozen.json manifest.model.json
```

The training-tape receipt is written under
`faasrank-calibration\training_input`, and calibration results retain the
summary/config hashes for every preregistered candidate-seed cell. No weight is
entered manually after looking at formal evaluation results.

A technically complete calibration run with zero completed requests remains a
canonical scientific result and is not retried. Its QPR is recorded as
non-applicable rather than replaced by zero or another synthetic value. The
preregistered selection order places fully applicable candidates first, then
uses applicable-seed count, mean QPR over applicable seeds, and finally the
lowest candidate-parameter SHA-256. Per-run applicability and reasons are
retained in the frozen model provenance.

### 5. Build and bind offline social references

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol build-references manifest.model.json run-ledger references.catalog.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol bind-references manifest.model.json references.catalog.json manifest.ready.json
& $ReviewerPython -m scripts.reviewer_experiments.protocol validate manifest.ready.json
```

Build time and replay lookup time remain separate observations. Formal replay
reads the hash-bound table; it does not rebuild the reference online. This
applies both to coordinated NSESche runs and to the E6 CP-BR/OnSocMax-P
post-hoc welfare comparison. The reference search is policy-independent: its
state key excludes the placement proposed by the evaluated policy, and its
deterministic social-greedy and Nash-feasible starts are constructed only from
the observed state, candidate sets, prices, and frozen utility inputs. Each E6
method/seed/load pair still builds its own state-matched table because different
policies produce different runtime state trajectories; references are never
borrowed from an NSESche trajectory. Each execution bank therefore has 410
reference-build dependencies (370 coordinated-NSESche and 40 E6), and the
complete fixed E01--E20 budget has 820 (740 coordinated-NSESche and 80 E6).
The two banks are exact paired repetitions on disjoint seeds.

### 6. Run, audit pairing, then analyze

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol run manifest.ready.json run-ledger
& $ReviewerPython -m scripts.reviewer_experiments.protocol verify-ledger run-ledger\ledger.jsonl
& $ReviewerPython -m scripts.reviewer_experiments.protocol.pairing manifest.ready.json run-ledger `
  --output run-ledger\pairing-audit.json
& $ReviewerPython -m scripts.reviewer_experiments.analysis.protocol_results `
  --manifest manifest.ready.json `
  --canonical-root run-ledger\canonical `
  --pairing-audit run-ledger\pairing-audit.json `
  --output analysis\runs.csv `
  --coverage analysis\coverage.csv
& $ReviewerPython -m scripts.reviewer_experiments.analysis.observability `
  --manifest manifest.ready.json `
  --canonical-root run-ledger\canonical `
  --pairing-audit run-ledger\pairing-audit.json `
  --output-dir analysis\observability `
  --sla-targets frozen-sla.json
```

For the physical-only combined E5/E6/E7 shard, pass the completed E1
heterogeneous source explicitly; the exporter does not infer a sibling path:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.analysis.protocol_results `
  --manifest manifest.ready.json `
  --canonical-root run-ledger\canonical `
  --pairing-audit run-ledger\pairing-audit.json `
  --reuse-source-manifest ..\e1-heterogeneous\manifest.e1-heterogeneous.ready.json `
  --reuse-source-canonical-root ..\e1-heterogeneous\run-ledger\canonical `
  --output analysis\runs.csv `
  --coverage analysis\coverage.csv
```

The source manifest and canonical root must belong to the same hash-bound E1
run ledger. The exporter verifies the sealed role lineage and emits the
materialized-reuse rows in the coverage audit.

The independent pairing entry point validates the manifest and every canonical
`qc_report.json`, groups by experiment/scenario/cluster size/seed/variant, and
requires paired methods to agree on the workload tape, function/DAG/QoS,
node/network, common-HPA, simulation and seed hashes. This grouping keeps E2's
100- and 500-node cells separate. Formal audits additionally require one global
Git commit, simulator binary hash, Python executable hash, and Cargo.lock hash
across every audited run, not merely within each seed group. The final E01--E20
artifact must therefore pass pairing against the combined `all` manifest before
paper analysis. A comparison with a deliberately different method set can
declare it explicitly, for example
`--expected-methods E6=cp_br,onsocmax`. Run statistical analysis only after this
report passes.

The adapter receives the same frozen run through both `run_config.json` and
environment variables. Formal output uses the `NSE_SUMMARY_V1` contract (the
manifest QC format is `nse_reviewer_v1`), for example:

```json
{
  "schema": "NSE_SUMMARY_V1",
  "run_id": "...",
  "protocol_version": "reviewer-v2",
  "run_complete": true,
  "final_frame": 1000,
  "frames_recorded": 1001,
  "frame_duration_ms": 1,
  "observation_time_ms": 1000,
  "arrivals": 1,
  "completed": 1,
  "completion_ratio": 1.0,
  "throughput_requests_per_second": 1.0,
  "latency_ms": {"mean": 1.0, "p50": 1.0, "p95": 1.0, "p99": 1.0},
  "fixed_observation_window": {
    "start_frame": 0,
    "end_frame": 1000,
    "duration_ms": 1000,
    "arrivals": 1,
    "completed": 1,
    "completion_ratio": 1.0,
    "throughput_requests_per_second": 1.0
  },
  "drained_arrival_cohort": {
    "arrival_start_frame": 0,
    "arrival_end_frame": 1000,
    "drain_end_frame": 1000,
    "drain_duration_after_arrivals_ms": 0,
    "arrivals": 1,
    "completed": 1,
    "completion_ratio": 1.0,
    "latency_ms": {"mean": 1.0, "p50": 1.0, "p95": 1.0, "p99": 1.0}
  },
  "simulator_internal_cost_total": 1.0,
  "simulator_internal_cost_per_completed_request": 1.0
}
```

`summary_json_v1` and `serverless_record_v1` remain compatibility inputs only;
the latter is decoded one frame at a time and requires a `provenance.json`
sidecar for formal legacy use.

## Result-blind lifecycle

Each attempt starts in `partial/<run_id>/attempt-NN`. Rust/its adapter should use `PROTOCOL_REVIEWER_RECORD_ROOT` and complete every `*.jsonl.partial` by atomically renaming it to `*.jsonl`. A successful technical QC is atomically moved to `canonical/<run_id>`. Every technically failed, timed-out, crashed, truncated, nonfinite, semantically inconsistent, or still-partial attempt is atomically moved to `quarantine/<run_id>/attempt-NN`. stdout, stderr, run config, QC report, and attempt metadata are retained. A consistent zero-completion result is not in this failure set.

Before canonicalization, each completed JSONL is gzip-compressed in a streaming 1 MiB loop with deterministic `mtime=0`. The runner streams the gzip back and verifies decompressed SHA-256, byte count, and original line count before removing the uncompressed copy. `jsonl_archive_summary.json` retains raw SHA-256/bytes/lines and gzip SHA-256/bytes for every artifact. No whole JSONL file is loaded in memory.

The append-only `ledger.jsonl` is sequence checked and SHA-256 hash chained. A stale partial left by a runner crash is quarantined as an abandoned attempt and consumes one of the three attempts.

Retries always use the identical `run_spec_hash`, seed, workload specification, common-HPA hash, and command. There are at most three attempts total. Exhaustion produces `run_blocked`; it never substitutes a different seed.

Each failed attempt also records a result-blind technical-failure signature.
The signature excludes observed counters, metric values, output hashes,
timestamps, and attempt paths. Two consecutive attempts with the same
signature are treated as a reproducible technical defect and block the run
without launching a third attempt. A third same-spec attempt remains available
only when the first two failures have distinct technical signatures.

QC never compares a result with the old PDF, another method, a desired ranking,
an expected effect size, or statistical significance. Low throughput, high
latency, zero completions, non-recovery, a changed ranking, or a surprising bar
is an experimental result and cannot trigger deletion or retry. Only the
predeclared technical failures (crash/panic/OOM/real I/O failure, truncation,
hash/provenance mismatch, nonfinite required output, broken frame/counter
invariants, or missing completion marker) may consume a same-seed retry.

## Freezing SLA targets from isolated pilots

SLA thresholds are frozen from measured pilot artifacts before formal E3/E4 runs. The freezer does not synthesize missing values, aggregate runs, interpolate, or round them. It applies only the predeclared transformations:

\[
L_{\mathrm{deadline}}=1.5L^{\mathrm{isolated}}_{p95},\qquad
T_{\mathrm{target}}=0.9T^{\mathrm{isolated}}_{\mathrm{sustainable}},\qquad
C_{\mathrm{budget}}=1.25C^{\mathrm{isolated}}_{/\mathrm{request}}.
\]

Use exactly one class-isolated source artifact for each metric. The latency
source must have `class_assignment: "all_latency"`, the selected capacity
source must have `class_assignment: "all_throughput"`, and the cost source must
have `class_assignment: "all_cost"`. `run-sla-pilots` creates these artifacts
from measured runs and records the complete throughput capacity grid. A
`balanced` or mixed-QoS summary cannot be reused to set any threshold.

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol freeze-sla frozen-sla.json `
  --latency-pilot sla-pilots\pilot_artifacts\isolated-latency.json `
  --throughput-pilot sla-pilots\pilot_artifacts\isolated-throughput-capacity.json `
  --cost-pilot sla-pilots\pilot_artifacts\isolated-cost.json
```

The generated artifact contract is:

```json
{
  "schema_version": "NSE_ISOLATED_SLA_PILOT_V1",
  "pilot_id": "isolated-qos-pilot-E01",
  "pilot_scope": "isolated",
  "class_assignment": "all_latency",
  "completed": true,
  "provenance": {
    "config_sha256": "...",
    "workload_tape_sha256": "..."
  },
  "metrics": {
    "latency_p95_ms": 12.5
  }
}
```

The `all_throughput` and `all_cost` artifacts follow the same contract with their matching metric. `class_assignment` may instead be present in `pilot`, `provenance`, or an embedded `experiment.qos`/`simulator_experiment.qos` configuration. For a normal simulator `summary.json`, the freezer also reads a sibling `environment.json`, verifies its `NSE_ENVIRONMENT_V1` schema and matching run ID, then hashes and records `config.experiment.qos.class_assignment` as evidence. Conflicting declarations are rejected.

`NSE_SUMMARY_V1` is also accepted when it has `run_complete: true` and the matching class-assignment provenance in the summary or its sibling environment artifact. `pilot_scope: "isolated"` is recommended; if any scope marker is present, every declaration must equal `isolated`. An ordinary `throughput_requests_per_second` field is not silently interpreted as sustainable capacity: the artifact must additionally carry `throughput_is_sustainable: true`, or expose the explicitly named `sustainable_throughput_rps` metric.

The frozen JSON records the exact source path, byte length, SHA-256, JSON field path, observed value, artifact provenance and derivation formula for every target. Existing files are protected. Replacement requires an optimistic-lock token matching the current file:

```powershell
& $ReviewerPython -m scripts.reviewer_experiments.protocol freeze-sla frozen-sla.json `
  --latency-pilot corrected-all-latency.json `
  --throughput-pilot corrected-all-throughput.json `
  --cost-pilot corrected-all-cost.json `
  --replace-existing-sha256 CURRENT_FILE_SHA256
```

`bind-sla` copies the three frozen values and their source hashes into a new
manifest. The source JSON remains the immutable audit record.

## Zero and nonfinite policy

Legal zeros include no-arrival/no-completion windows, a completed run with zero
completed requests, empty queues, no drops/rejections/timeouts, no scheduler
oscillation, and no-player solver rounds. If final `completed == 0`, throughput
must be zero and completed-request latency percentiles and cost per completed
request must be JSON `null`; this is canonical scientific output, not an
technical retry condition. With positive completions, latency and
per-completed cost must be finite and internally consistent. NaN/infinity,
truncation, a missing run-completion marker, wrong final frame, broken counters,
or mismatched provenance fails technical QC.

## Units and denominators

- One simulator frame is exactly `1 ms`. E1, E2, E4--E7 retain the frozen
  `1000 ms` submission observation horizon. E3 admits its frozen arrival
  cohort during frames `[0, 1000)` and drains it through frame `4000`, as
  required by the burst/recovery protocol.
- Primary throughput is
  `fixed_observation_window.completed * 1000 / fixed_observation_window.duration_ms`.
  A completion timestamp exactly at frame `1000` is on the observation boundary
  and is counted. Analysis divides this physical requests/s value by 1000 for plots labeled
  `Throughput (10^3 requests/s)`, numerically equal to requests/ms.
- Mean/p50/p95/p99 latency and completion ratio come from
  `drained_arrival_cohort`. For E3, the same requests arriving before frame
  `1000` are observed through frame `4000`; for the 1000 ms steady experiments,
  this object makes the unchanged fixed-horizon population explicit.
- The top-level `observation_time_ms`, `completed`, `completion_ratio`,
  `throughput_requests_per_second`, and `latency_ms` fields retain their legacy
  final-run semantics for compatibility. Formal analysis prefers the two
  explicit cohort objects.
- Latencies and scheduler wall-time plots use milliseconds. The primary
  placement-policy wall/thread-CPU fields and the read-only welfare-evaluator
  wall/thread-CPU fields are timed at separate exact boundaries and stored in
  nanoseconds before conversion. The broader mechanism duration is retained as
  a third, separately labelled measurement; policy time is never derived by
  subtracting evaluator time from it.
- Cost is simulator internal cost, never currency. The main cost denominator is
  completed requests; total internal cost is retained separately.
- CPU capacity `150` and memory capacity `5000` are simulator internal resource
  units. Normalized CPU/memory utilization is dimensionless and may exceed one
  under shared-capacity contention; invalid denominators are counted rather
  than imputed.
- QPR is computed per run as throughput in requests/ms divided by internal
  cost/completed request and latency in ms. It is not computed from averaged
  bars.

## Tests

```powershell
& $ReviewerPython -m unittest discover scripts/reviewer_experiments/protocol/tests -v
```
