# P5 policy-action semantic-hash correction preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: frozen after the complete 90-row P5 pilot and its predeclared
low/P5P01/NSESche duplicate, before any relative throughput, QPR, rank, or
old-PDF comparison was read.

## 1. Result-blind trigger

All 90 declared P5 rows are canonical and passed their frozen QC.  A separate
duplicate of `TSCv1.E1.homogeneous.n20.low.sche_nash.FP5P01.824fd6ca` also
canonicalized on attempt 1 with the identical run specification, tape,
reference, source, binary, and configuration.

The frozen duplicate evidence showed exact equality for:

- the ordered workload-arrival semantic hash;
- the final-frame and terminal-count semantic hash; and
- the scientific-result semantic hash.

Only the legacy `command_semantic_sha256` differed.  Direct comparison of all
4,588 policy windows found eight unequal full `decision` objects.  In every
case the sole unequal field was the decision-neutral diagnostic
`placement_dispersion_normalized`; its maximum absolute difference was
`5.960464477539063e-08`.  All initial-assignment hashes, final-assignment
hashes, prepared-command counts, and sent-command counts matched exactly.
The timing-free fields of all 4,588 `scheduler_windows` records also matched
exactly.  No performance value or cross-method outcome was inspected to reach
this diagnosis.

The failure therefore comes from hashing a floating-point diagnostic as if it
were a scheduling action.  It is not evidence of a different placement,
command stream, terminal population, or scientific result.

## 2. Frozen minimal correction

The original full-decision digest remains retained in every QC report as
diagnostic provenance.  It is not rewritten or deleted.

For P5 condition 11, add a second, explicitly action-semantic digest computed
from the ordered policy windows using exactly these discrete control fields:

- `initial_assignment_hash`;
- `assignment_hash`;
- `complete_assignment`;
- `assigned_players`;
- `assigned_node_count`;
- `commands_prepared`;
- `commands_sent`;
- `scale_ups_prepared`;
- `scale_ups_sent`;
- `dispatch_channel_failed`;
- `invalid_assignments`;
- `no_feasible_players`;
- `waiting_for_candidate_nodes`.

The digest also binds the window ordinal.  Missing fields are represented
explicitly as JSON null; no floating-point field is permitted.  This whitelist
is frozen here before implementation.

The corrected duplicate evidence must require exact equality of:

1. workload-arrival semantics;
2. the new policy-action semantic digest;
3. terminal-count semantics; and
4. scientific-result semantics.

The old failing duplicate-evidence file is permanent provenance.  The
corrected evidence must be written to a new path and may not overwrite it.

## 3. Implementation and validation boundary

Authorized source changes are limited to:

- one shared action-field constant and action-digest helper;
- QC emission of the new action digest for future runs;
- result-blind recomputation of the same digest from the retained compressed
  policy streams for the already-complete canonical and duplicate; and
- focused tests proving exact pass for diagnostic-only float drift and exact
  failure for any whitelisted action-field drift.

The simulator, `sche_nash.rs`, Eqs. (1)--(20), workload, reference, run
configuration, runtime binary, all 90 canonical results, and the duplicate are
immutable.  No simulator rerun is authorized by this correction.  Gate
analysis remains blocked until the correction is implemented, tested, audited,
and the new duplicate evidence passes.

