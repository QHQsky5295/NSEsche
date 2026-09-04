# G13 Deferral-Persistence Diagnosis Preregistration

Date: 2026-09-04 (Asia/Shanghai)

Parent closure commit: `deb705a83a80189b18841e00e658bace3bba30ff`

Status: `preregistered_read_only_no_sampling_authorized`

## 1. Question and boundary

G12 is closed negative development evidence. Its fixed per-window `N` prefix
was structurally correct but repeatedly deferred 5,132,665 feasible-player
observations and failed throughput/QPR robustness. G13 asks one narrower
question before any further scheduler change:

> Is the harmful part of G12 associated with *persistent* deferral across
> adjacent scheduler windows, while isolated one-window deferral retains more
> favorable paired outcomes?

G13 is read-only. It uses exactly the retained 15 G12 candidate runs and their
15 same-load/same-seed C0 controls from D101--D105. It creates no tape,
reference, simulator run, seed extension, baseline comparison, confirmation,
figure, or paper claim. All rows and signs are retained.

## 2. Fixed inputs

The analyzer must bind and revalidate:

- the complete G12 run root: 1,092 files, 390,090,635 bytes, sorted inventory
  hash `5a41481e09fa159364741b8158e385367c81920350e3a1231ffe3baaf1f1b20a`;
- `g12.references.json` file/document hashes
  `4c0140a0...4209` / `ec5708cc...bb96`;
- the frozen online selection file/document hashes
  `784f40c3...0a7fd` / `3e5665dc...d014f`;
- the frozen gate report file/document hashes
  `6c5e0882...f5a5` / `7fc6f143...0e52`;
- the 62-event online ledger ending at
  `bf0832f6...c60b`; and
- every canonical manifest/QC/artifact inventory and same-tape pair.

The root hash is checked before any output is written. The G12 analyzer source
and report remain immutable.

## 3. Frozen run-level features

For every G12 candidate run, scheduler windows remain in recorded frame order.
Let `d_t` be `deferred_feasible_players` in window `t`.

The analyzer reports without filtering:

- total, active, and positive-deferral windows;
- `sum(d_t)`, `max(d_t)`, and positive-window arithmetic mean;
- deferral episode count, where an episode starts at `d_t>0` after either the
  beginning of the trace or `d_(t-1)=0`;
- isolated-deferral windows, where `d_t>0` and both existing neighbors (if
  present) have zero deferral;
- persistent-deferral transitions, where `d_(t-1)>0` and `d_t>0`;
- longest consecutive positive-deferral episode;
- fractions of all windows that are positive, isolated, or persistent;
- admitted and feasible-ready totals and their ratio;
- arithmetic mean and maximum cluster pending, resident, and total queue
  counts, separately for all windows and positive-deferral windows; and
- all six G12 violation totals plus runtime/PNE/reference status.

Each feature row is joined to the already frozen paired throughput, QPR,
latency, cost, and completion ratios/differences. Outcome labels are fixed as:

- `joint_win`: throughput ratio >1 and QPR ratio >1;
- `joint_nonwin`: the complement, including exact ties; and
- `isolated_only_activation`: positive deferral exists and the longest episode
  is exactly one window.

No threshold is estimated from outcomes.

## 4. Fixed summaries and association checks

The report contains all 15 raw feature/outcome rows and, for each feature,
Spearman association with log throughput ratio and log QPR ratio. Ties use
average ranks. Associations are reported overall and separately by load, with
all 15 leave-one-run-out values for the overall coefficients. These are
descriptive diagnostics, not hypothesis tests or paper evidence.

The isolated-versus-persistent table reports group sizes, loads represented,
joint-win counts/rates, mean log throughput ratio, mean log QPR ratio, and all
leave-one-run-out differences in those group means and win rates. Undefined
quantities remain null; no row is imputed or discarded.

## 5. Frozen successor-admissibility rule

A single parameter-free successor concept, `deferral_release_valve`, may be
preregistered only if every condition below passes:

1. all 15 G12/C0 pairs and all canonical/runtime identities validate, and all
   six G12 structural violation totals are zero;
2. at least three candidate runs have isolated-only activation and at least
   three have persistent activation, with each group spanning at least two
   loads;
3. the isolated-only joint-win rate is strictly above the persistent-group
   joint-win rate;
4. the isolated-only minus persistent mean log-throughput ratio and mean
   log-QPR ratio are both positive; and
5. after leaving out any one run for which both comparison groups remain
   defined, the signs of both mean-log-ratio differences remain positive.

This rule does not claim causality. It only asks whether the retained evidence
is coherent enough to justify one fresh validation of a stateful release valve:
use the bounded prefix on the first window of a deferral episode; if the
immediately previous bounded window deferred feasible players, use the full C0
feasible-ready sequence until a no-deferral window resets the episode. The
state is one bit, uses no load/seed/outcome label, no learned or numeric
threshold, no baseline expert, and leaves Eqs. (1)--(20) unchanged on each
actually admitted player set.

If any condition fails, no release-valve implementation or sampling is
authorized. Passing G13 would authorize only a separate implementation
preregistration; it would not authorize code changes or runs by itself.

## 6. Integrity and stopping rule

- D101--D105 are diagnosis-only and cannot validate a successor.
- Every QC-valid row, tie, loss, runtime exception, and nonpositive offline
  reference remains visible.
- No feature, grouping, threshold, condition, or successor definition may be
  edited after the first real analyzer invocation.
- G13 stops after one validated report. There is no result-conditioned retry.
- Strong baselines, fresh seeds, confirmation, formal replay, figures, and
  paper claims remain blocked throughout G13.
