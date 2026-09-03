# G7 bounded-frontier warm protocol/analyzer audit

Date: 2026-09-04

Protocol implementation commit: `264cfec95c6799fe6fbd8b81c8aa6f416016e629`

Status: implementation and protocol frozen; release construction and a
zero-data manifest are authorized; reference building and online sampling
remain blocked

## Frozen protocol product

The G7 writer creates exactly five candidate-only homogeneous-low runs on
D71--D75.  It binds each run to the matching G3 C0 workload tape, creates five
candidate-specific offline-reference dependencies, and binds the exact 5 C0
plus 45 baseline artifacts from the immutable G3 product.  It never resamples
a control or baseline and declares all G7 outcomes non-formal development data.

Manifest validation fixes the candidate name, runtime identity, one cell/five
run/five reference counts, all five seeds, workload and common-HPA identity,
strict Eq. (15), zero regret, stable order, bounded-frontier collection, warm
initialization semantics, all-retained sampling, and the complete activation
and performance gates.  Candidate, seed, gate, role, runtime, source binding,
or reference-count tampering fails closed.

## Runtime and reconstruction checks

The analyzer requires one schema-7 runtime declaration for
`lookahead_frontier1_warm_init`, strict Eqs. (1)--(20), the exact player order,
`ready_plus_one_executable_frontier_hop`, and the registered warm-start
semantics.  Every active window must have a complete assignment, equal
assigned/prepared/sent counts, zero invalid assignments, no channel failure,
and an offline-table reference hit.  It sums the existing
`initialization_refined_choices`, `initialization_lower_utility_choices`, and
`initialization_running_warm_choices` counters without changing runtime
decisions.

For each completed request, the analyzer independently reconstructs the
dependency frontier from the hash-audited `environment.json` function-parent
graph and per-function scheduling/completion times.  It checks that every
parent was placed no later than its child and recursively measures the number
of unfinished ancestor levels at binding.  Missing topology, unknown parents,
duplicate edges, cycles, missing parent timing, invalid timing, and any depth
above one fail the integrity gate.  This reconstruction is restricted to the
predeclared completed-function population and is not used as an independent
sample or a performance endpoint.

The result reports all five absolute values, sample means and SDs, paired 95%
t intervals, signs, leave-one-seed-out means, paired C0 ratios, all nine frozen
baseline summaries, activation rows, runtime counters, and artifact receipts.
Passing can authorize only a later confirmation preregistration; this analyzer
always leaves confirmation sampling and formal progression false.

## Identity receipts

| File | SHA-256 |
|---|---|
| `scripts/reviewer_experiments/protocol/g7_frontier_warm.py` | `7447321c4677279c54c566ffb901e498553775e533f95424f08973c8935c8136` |
| `scripts/reviewer_experiments/protocol/schema.py` | `199afcf721302f7af09b3c48bf1f1de64bf63b3ce9dae660d0b334b778d73bde` |
| `scripts/reviewer_experiments/protocol/cli.py` | `adeeeabc0798f1a19c5fe2bbd8b17ef351844245df5b1f3aba67671348148ac0` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | `564ec9cbca9c64e823d2f4a780e73e66d430c61d34faa6e3a68712afc555c4a8` |
| `scripts/reviewer_experiments/protocol/tests/test_g7_frontier_warm.py` | `2d3d2d29962f34768fbf72970a787ec85958d81a135259a3c7320bacc1a03c29` |
| `scripts/reviewer_experiments/protocol/tests/test_protocol.py` | `96c59eb90374858706ae909aca3f7fe21f9a1f038e226a866ae8e6bda82d42d1` |

## Verification

- Python compilation: pass for the new protocol, schema, CLI, package export,
  and shared runtime-contract validator.
- Black formatting check: 7/7 changed Python files pass.
- G7 protocol/analyzer plus general protocol tests: 45/45 pass in 253.151 s.
- G6 lookahead regression tests: 5/5 pass.
- G2 initialization/runtime-contract regression tests: 6/6 pass.
- Exact real G3 source-binding dry construction: pass; five D71--D75 runs,
  five unique reference dependencies, and the exact five frozen tape keys were
  accepted without writing a manifest.
- `git diff --check`: pass before the protocol implementation commit.

Directed tests cover one-hop admission reconstruction, deliberate two-hop
rejection, warm-counter activation, runtime semantics, all-gate success,
activation failure, manifest identity, and tamper rejection.

## Authorization boundary

No G7 result, workload tape, reference table, release binary, candidate seed
outcome, figure, or paper claim was created by this stage.  The next authorized
stage is to build one release binary from the audited commit, create a new
zero-data G7 run root, generate and bind the five exact G3 tapes, and freeze the
unbound/tape-bound manifests.  Offline reference construction remains blocked
until that zero-data product is separately audited and committed.  Online
simulation remains blocked until all five reference tables are built once,
bound, and separately audited.
