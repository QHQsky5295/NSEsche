# G6 lookahead protocol/analyzer audit

Date: 2026-09-04

Implementation commit: `e414eb9285fc090b6b371dfedc2cc6df81be7b5b`

Status: protocol/analyzer frozen; release build and zero-data freeze authorized;
reference construction and simulator sampling not yet authorized

## Frozen product

The G6 protocol creates exactly five non-formal NSESche runs: homogeneous,
20 nodes, low load, mixed QoS, and seeds D71--D75, all using
`lookahead_preall_sched`.  It creates no control or baseline reruns.  Instead,
the manifest hard-binds the closed G3 ready manifest and failed selection, the
exact five C0 plus 45 nine-baseline run identities, and the canonical control
root.  Candidate workload fields and tape keys must equal paired G3 C0 inputs.

The five candidate runs have five distinct candidate-specific offline social-
reference dependencies.  Existing C0 references cannot satisfy them.  The
generic tape projection and binding path is used to hash-bind only the five
already retained D71--D75 homogeneous-low tapes.

## Fail-closed analysis

The analyzer requires a tape- and reference-bound ready manifest and validates
all five candidate canonical runs.  Each runtime must report schema 6,
`player_collection=parents_scheduled`, stable player order, strict paper
Eqs. (1)--(20), strict Eq. (15), unchanged initialization, offline-required
reference loading, complete command preparation/sending, zero invalid
assignments, and no failed dispatch channel or operational-envelope output.
Every active window must use a finite offline-table reference with a valid
state key.

Activation is measured only over completed functions and must show both at
least 0.10 pre-ready binding share and positive mean startup overlap in every
seed.  Performance uses one row per seed, retains all five rows, and reports
mean, sample SD, paired 95% t intervals, sign counts, and leave-one-seed-out
means.  The frozen gate requires candidate mean throughput above Hiku's 1.1514
requests/ms, mean QPR above Jiagu's 0.040391615, the preregistered paired win
counts and 80% floors, noninferior mean completion, lower mean latency, and
mean per-seed solve-time ratio no greater than 3.0.

The G3 selection's 135 metric and artifact receipts are revalidated.  A live
read-only integration check matched all 50 reused run receipts, five C0 rows,
and nine baseline methods.  The analyzer exposes a pass only as authorization
to write a separate Q61--Q80 confirmation preregistration; it never directly
authorizes confirmation sampling or formal progression.

## Source receipts

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/protocol/g6_lookahead.py` | `12110fd82815d771be3900895ae74b30b6e20f22eb043df6e4968c68f0902d77` |
| `scripts/reviewer_experiments/protocol/tests/test_g6_lookahead.py` | `e59d68a9f199d079408ff655c115b2d42dac2cce54539c22d30dd8081ccf35e9` |
| `scripts/reviewer_experiments/protocol/schema.py` | `6155484a6f57c7e0fbf60c6b9684300e14c9158230309d8e512f210c57d6acce` |
| `scripts/reviewer_experiments/protocol/cli.py` | `c82d803bdb988cec688447f38664eb7b7558d8ce70c1edda722ce24313d44843` |
| `scripts/reviewer_experiments/protocol/__init__.py` | `ceb59a19a6fb2a81122062dd32aa43efb496db6419acf6c395eb757c4bc49c42` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | `db75ac8abc2c1eb874d78e7ea43bb9af1aace3bd58fd34e498d2e8ad66aa4a39` |
| `scripts/reviewer_experiments/protocol/README.md` | `03348b0eda2ba0a2ea8db30574f0b207b370e630a83ae0f1aa4d92ccd4f4a70e` |

## Verification

- Python compilation: pass.
- Black formatting: pass.
- New G6 directed tests: 5/5 pass.
- G2/G3/G6 protocol regression subset: 20/20 pass.
- G3--G6 analysis regression set: 32/32 pass.
- Complete generic reviewer-protocol tests: 40/40 pass in 245.417 seconds.
- CLI discovery of both G6 commands: pass.
- Real G3 source manifest/selection in-memory integration: exact 5 candidate
  runs, 5 references, and 50 source-control bindings.
- Real G3 canonical receipt revalidation: 50/50 pass.
- `git diff --check`: pass before the implementation commit.

## Authorization boundary

No G6 manifest, reference, online result, candidate metric, figure, or paper
claim was created by this closure.  The next authorized stage is a release
build from the committed source, followed by a unique G6 run root and a
zero-data unbound/tape-bound manifest audit.  Offline-reference construction
and candidate online execution remain blocked until that runtime/zero-data
freeze is committed.  All protected prior target and run directories remain
unchanged.
