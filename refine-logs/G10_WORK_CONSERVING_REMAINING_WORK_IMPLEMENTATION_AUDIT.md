# G10 Work-Conserving Remaining-Work Implementation and Runtime Audit

Date: 2026-09-04 (Asia/Shanghai)  
Implementation commit: `ab0ae94f0a8314db348078040a49dfe59281653e`  
Status: `implementation_runtime_frozen_zero_result_protocol_construction_authorized`

## 1. Frozen mechanism boundary

The implementation adds exactly the two candidates preregistered in
`G10_WORK_CONSERVING_REMAINING_WORK_PREREGISTRATION.md`.

- C0, `ready_order`, remains the paper-faithful control. Its decision order is
  still arrival frame, request ID, DAG topological rank, and function ID.
- C1, `ready_remaining_work`, collects the same dependency-ready request-
  function players as C0 and changes only their deterministic order. The first
  key is the ascending number of unfinished functions in the request; all
  legacy C0 keys follow.
- C2, `ready_remaining_work_bounded_frontier`, admits every C1-ready player
  before adding any frontier player. A frontier player is unplaced and not
  ready, all of its incomplete direct parents are placed, and the parents of
  those direct parents are complete. If `B(t)` is the already placed,
  unfinished, parent-blocked population, at most `max(0, |N|-B(t))` new
  frontier players are admitted.

Neither candidate contains a load-specific branch, warm-first rule,
finish-score override, utility-regret relaxation, learned model, random tie
break, or baseline expert. The implementation has operational schema version
9. Reference-key tags 14 and 15 are unique to C1 and C2, so offline-reference
tables cannot cross C0/C1/C2 identities.

## 2. Formula and convergence boundary

No displayed manuscript equation was changed. Source-diff inspection confirms
that the paper utility, social-welfare calculation, strict Eq. (15) best-
response selector, Eq. (19) price update, empirical gap, and offline-reference
search functions are outside the modified decision hunks. Initialization is
the existing sequential feasible-node utility choice and every later accepted
move remains a strict utility improvement.

For C1, the fixed-window player set, feasible action sets, utilities, and price
vector are identical to C0; only initialization/update order can select a
different strict PNE. For C2, the fixed-window game additionally contains the
bounded one-hop frontier, but strict Eq. (15) is still applied to the exact
frozen player set. Therefore the existing weighted-potential finite-
improvement argument applies separately to each C0/C1/C2 fixed snapshot.
This supports convergence of the implemented game; it does not assert that a
candidate improves throughput or QPR.

## 3. Fail-closed runtime evidence

The run configuration records the operational identity, schema, remaining-
work definition, all-ready guarantee, conditional frontier eligibility and
global bound, and the absence of load-specific or baseline feedback. The
runtime-contract validator rejects any mismatch.

Each active scheduling window records:

- whether remaining-work order and bounded frontier are enabled;
- ready candidates/admissions/omissions plus a ready-set fingerprint;
- frontier candidates, outstanding frontier `B(t)`, node-count limit, residual
  budget, admissions, and a frontier-set fingerprint;
- frontier-bound, one-hop, and dispatch-class violations;
- ready/frontier dispatch counts and the unfinished-work range.

The scheduler panics rather than emitting a scientific observation if it omits
a ready player, exceeds the global frontier bound, admits a non-one-hop player,
or dispatches outside the frozen ready/frontier classes. C0 emits a comparable
ready-set fingerprint while explicitly recording that remaining-work order is
disabled.

Synthetic unit tests cover remaining-work priority and deterministic ties,
legacy C0 order, zero/partial/full frontier budgets, all-ready retention,
nonconsecutive duplicate removal, ready/frontier de-duplication, one-hop
eligibility, unique schema/reference identities, strict Eq. (15), and existing
strict-PNE certification.

## 4. Runtime and source receipts

One release runtime was built with Cargo 1.86.0 / rustc 1.86.0 from the clean
implementation commit. It is the only runtime that a G10 protocol may bind.

| Artifact | Bytes | SHA-256 |
|---|---:|---|
| `serverless_sim/target_g10_work_conserving_impl/release/serverless_sim.exe` | 4,869,120 | `39d56c1bf332635a51962a061c3e001c04a5eab23ab2e54ffb27175c3adc12e8` |
| `serverless_sim/src/sche/sche_nash.rs` | 375,477 | `5d1fe37dc89e5b3ca0211dbef593ef0b56b527007d45ad6c6dc2c54efdaa609f` |
| `serverless_sim/src/config.rs` | 48,161 | `bea6fa4fd7ef72e67d17500b5bdd0853ea6d7c586af2792702d36fba214f82b6` |
| `scripts/reviewer_experiments/analysis/feedback_trace.py` | 21,224 | `0741ec5d1301bd4fce4f553101fbc09eaf50a66261692799898fa321d33a792e` |
| `scripts/reviewer_experiments/protocol/schema.py` | 212,685 | `822df5ae249db188c1c4e9be4a0ef4c2365f222570d8501959ff0d70986d7e3e` |
| `scripts/reviewer_experiments/protocol/tests/test_g10_work_conserving.py` | 5,138 | `201b0de0bb88eb81666ea7782a0e2af7634ce35425edf8b881cffc300551e5ba` |

The target directory is protected build evidence. It must not be deleted,
moved, or added to Git.

## 5. Verification receipts and disclosed limitations

Verification against the final implementation commit produced:

- Rust formatting: pass;
- complete `sche_nash` directed suite: 50/50 pass;
- configuration-validation directed suite: 10/10 pass;
- complete reviewer-protocol regression: 219/219 pass in 921.495 seconds;
- complete reviewer-analysis regression: 98/98 pass in 105.788 seconds;
- release compilation with `--no-default-features`: pass;
- `git diff --check` before the implementation commit: pass.

The unfiltered Rust repository suite is not reported as fully passing: 127/129
tests pass. `mechanism_thread::tests::test_algo_latency` fails an existing
wall-clock/thread-scheduling assertion, and
`sim_env::tests::test_python_res_consistency` invokes a different default
Python environment that lacks NumPy. Neither failure touches the G10 source
path, and all 50 NSESche tests plus all 10 configuration tests pass, but the two
repository-wide failures remain explicitly disclosed rather than suppressed.

At audit time there is no G10 run root and no path bound to D96--D100. No
workload tape, offline reference, online metric, throughput value, QPR value,
or baseline result has been generated or inspected.

## 6. Authorization boundary

After this audit is committed, only construction and result-free validation of
the exact G10 zero-result protocol is authorized. That protocol must freeze C0,
C1, and C2 across three homogeneous 20-node loads and the five fixed seeds
D96--D100, for exactly 15 tape identities, 45 candidate-specific reference
dependencies, and 45 online run specifications.

Tape capture remains blocked until a separately committed protocol/manifest
audit proves the exact Cartesian product, runtime binding, shared-tape pairing,
reference separation, and unchanged preregistered gates. Reference builds,
online execution, strong baselines, confirmation, formal Q61--Q80 replay,
figures, and manuscript performance claims remain blocked.

