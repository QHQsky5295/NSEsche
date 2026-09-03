# G3 Strict-PNE Order Counterfactual Implementation Audit

Date: 2026-09-03 (Asia/Shanghai)

Status: source implementation complete and tested; release executable,
50-replay manifest, and diagnostic results do not yet exist; replay remains
unauthorized

## 1. Implemented boundary

`serverless_sim/src/sche/sche_nash.rs` now implements the preregistered
decision-neutral order counterfactual behind the default-off environment flag
`NASH_ORDER_COUNTERFACTUAL`. The flag is accepted only when the live
operational refinement is C0 `ready_order`; any other live policy fails closed.

When enabled, every scheduling window reports O0 `ready_order`, O1
`reverse_ready_order`, O2 `service_scarcity_first`, O3
`capacity_scarcity_first`, O4 `resource_impact_first`, and the predeclared E0
nonworse-welfare envelope. Each outcome contains the frozen order/candidate/
assignment hashes, inner-loop status, an independent strict-PNE certificate,
paper-welfare components, startup/projected-finish proxies, container-state
counts, dispersion/conflict, pressure, projected reserved memory, and a
separate diagnostic time.

No paper equation, operational refinement, reference-key version, common
candidate filter, HPA mechanism, container lifecycle, or formal metric was
changed. With the flag absent, the added branch is not executed and the new
timing field remains zero.

## 2. Decision-neutrality and formula checks

- The counterfactual routine takes `&self`; Rust prevents it from mutating the
  scheduler's candidate sets, price/reference caches, container snapshots, or
  control state.
- Its return type contains diagnostics only. `dispatch` continues to receive
  the live `state` returned by the unchanged `solve`; no counterfactual
  assignment is in the dispatch call signature.
- The counterfactual is computed from a clone of the original empty
  window-aggregate vector and immutable baseline price signal. It never calls
  reference lookup, price feedback, or command emission.
- Initialization remains sequential paper-utility best selection. Every inner
  move uses the existing `best_response` and strict `candidate_is_better`
  implementation; no lower-utility warm or finish guard is introduced.
- The independent certificate removes each player in turn and rejects an
  outcome if any feasible candidate improves utility by more than
  `EPSILON=1e-6`.
- O0 is reconstructed independently and compared with the first live
  baseline-price inner assignment hash. This parity gate must pass on the real
  50-replay bank before aggregate inspection.

## 3. Directed verification

`cargo fmt --all -- --check` passed. The complete NSESche directed group
passed 36/36, including four new tests:

1. all five player orders are deterministic and preserve the candidate-set
   fingerprint;
2. O0 exactly reconstructs the live first-inner PNE in a controlled state;
3. the independent certificate rejects a deliberately profitable deviation;
4. the counterfactual leaves scheduler inputs/caches unchanged and E0 never
   selects welfare below the frozen O0 tolerance.

The Python protocol test discovery passed 185/185 under the existing
`D:/Anaconda3/python.exe` environment in 943.420 seconds. This covers the
existing manifest, QC, pairing, runner, canonicalization, and timeout-recovery
contracts; no package was installed or changed.

The full Rust suite produced 113/115 on its first run. The two nonpassing
tests were audited separately:

- `mechanism_thread::tests::test_algo_latency` still fails in isolation at its
  existing wall-clock assertion (`begin_frame:2 current_frame:3 calltime:2`);
  no counterfactual code is on that path.
- `sim_env::tests::test_python_res_consistency` initially inherited the system
  Python 3.14 without NumPy. With PATH pointed to the project's existing
  Anaconda environment, it passed 1/1 in 116.46 seconds.

These are pre-existing test/environment constraints rather than changes to a
scientific result. The relevant NSESche and experiment-protocol suites are
green.

## 4. Remaining freeze gates

Source completion does not authorize inspection of a replay result. Before
the 50-run diagnostic bank can execute, the following still must be committed
and frozen:

1. a source-run inventory and immutable diagnostic manifest binding all 50
   source run IDs, tapes, observations, configurations, and hashes;
2. a result-blind replay adapter that writes to a new diagnostic root and sets
   only the output identity plus `NASH_ORDER_COUNTERFACTUAL=1`;
3. a parity/eligibility analyzer and synthetic schema tests implementing every
   predeclared gate and seven-stratum rule;
4. one release executable whose hash and source drift are verified against
   this implementation commit.

At this closure, diagnostic replays completed are 0/50,
`candidate_effect_estimation=false`, `D71_authorized=false`,
`homogeneous_middle_formal_authorized=false`, and no paper group is closed.
