# P3 Low-Load Root-Cause Diagnosis Preregistration

Date: 2026-09-05 (Asia/Shanghai)

Status: `preregistered_read_only_no_sampling`

## 1. Purpose and boundary

P2 showed that the submitted local `r0`/`wq` axial grid cannot recover the
homogeneous-low throughput and QPR shortfalls. P3 is one result-preserving,
read-only diagnosis of the complete retained P2 population. It asks whether a
previously untested, formula-parameter direction is justified before another
development bank is created.

P3 does not estimate a new scheduler's effect, run the simulator, build an
offline reference, change `sche_nash.rs`, select a seed subset, or authorize a
paper claim. It retains all 25 P2 observations. The rejected warm-init,
lookahead, player-order, backpressure, remaining-work, and ready-cap/valve
families remain closed.

## 2. Frozen inputs

The exact P2 root is
`runs/tscv1_p2_low_hyperparameter_recovery_d121_d125_f3a1e09_20260905`.

- ready manifest: 680,965 bytes, file SHA-256
  `544d884bdb4d990115213ef13fce19de24ab20f899588e5666e96de375823568`,
  object hash `8e89bca4604f17ef9dc28e2e09887b6070fed971e6a560903c00cf7281320758`;
- frozen online selection: 15,703 bytes, file SHA-256
  `97a8fed754a2980726e5eb6984b36f279a72fbd17cecc7b788639e4dc62586be`,
  object hash `d6daefea4e7a49df6a6a71285aeab461591329555748df921ae85c0cc2d482e3`;
- frozen gate report: 146,457 bytes, file SHA-256
  `02cf7e36cdccc3969bc690ac028069d3de7870cdc06759dc6b1b0aad25d5a1a9`,
  object hash `7f6a074926580f548b224e595df0739cb8a7f7af5d0d6615fd11ddb2ddcbb1c3`;
- online canonical tree: 375 files, 23,386,180 bytes, sorted inventory hash
  `7a06b6a3ce83ef8c4beea21f0f26b1f486c1a87a671c075c3e46565383fd1e98`;
- result audit: file SHA-256
  `afda620abf66922a85ab5d7c7043c0f4559b4fc228c96d76a07eaa780a179049`;
- audited scheduler source: file SHA-256
  `8423e3bdffbe18aaf72faa39926e099cc99fc7eda3b7b3759a45c3e26f0aa949`;
  and P2 result commit
  `38f9f7f53546359ecadafb52c2d46902b40bc394`.

Context-only claims are bound to the complete G1, G3, G4, and G5 audit files
with respective SHA-256 values
`9376c7202a01de1b3706ed92d68f90580ef576ab7b780c8e74cad5028e9b5c16`,
`c56a3b5d2ba51667f8871555097b565bbd49a1d2a2678a2a0137141c93e22ed3`,
`36212b99bb8eeb62c83886c17ec2d0973c2cdc8381dd8fefce29cb8ae00cb4b9`,
and `d975149d4d062d3950bead38f575bbdbc9264bebf0f626a07153cad17a2f2c95`.
They may be quoted to prevent a closed family from being reopened, but no
value is pooled across seed banks.

## 3. Exact population and validation

The analyzer must fail before output unless it revalidates:

- exactly five settings in the frozen order `centre`, `r0_minus`, `r0_plus`,
  `wq_minus`, `wq_plus` for each of D121--D125;
- exactly 25 unique run/spec identities and five within-seed shared tape
  hashes;
- every canonical run's manifest, QC report, process observation, audit
  inventory, and runtime binary/source identity;
- exactly 1,000 aligned scheduler windows per run; and
- the gate report's complete retained population and no selected P2 setting.

No run, window, player, request, or function may be omitted because a value is
zero, negative, missing, or directionally inconvenient. Structurally invalid
input fails closed and does not authorize reconstruction from a subset.

## 4. Frozen diagnostics

### D1: price-feedback dormancy

Within each seed, align centre and both `r0` neighbours by window index. Report
the equality count and share for final assignment hash, assigned-player count,
prepared-command count, strict-PNE status, outer price-adjustment count, and
final completion/throughput/QPR. Also report the number of windows in which
the price multiplier differs while the final assignment hash is unchanged.

`r0` is declared operationally dormant on P2 only if both neighbours have
identical final assignments and command counts to centre in every aligned
window of all five seeds. This is a scope-limited observation, not a proof that
Eq. (20) is globally irrelevant.

### D2: quality-weight activity

For each `wq` neighbour and seed, report aligned active-window assignment-hash
changes, their share, and the already frozen run-level throughput, QPR,
completion, and latency differences. This diagnostic may establish that `wq`
is decision-active but cannot reopen the failed local `wq` grid.

### D3: centre-path accounting

For every centre seed, sum the already emitted window fields:

- assigned players `A`;
- selected running-warm, starting-container, and cold/non-running players
  `R`, `S`, and `C`;
- running-warm-available and bypassed players `W` and `B`;
- ranking-diagnostic and differentiation-changed-top-choice players `P` and
  `D`;
- near-tie players, warm-bypass utility advantage and projected-finish
  penalty; and
- paper-utility component totals plus outer price-adjustment activity.

The mandatory invariants are `A=R+S+C`, `0<=B<=W<=A`, and `0<=D<=P<=A`.
Report per-seed and pooled `S+C`/`A`, `W/A`, `B/W`, and `D/P`; pooled values
are descriptive and cannot replace the five run-level checks.

For each seed, split active windows into `D>0` and `D=0`. In both groups,
compute the player-weighted non-running share `(S+C)/A`. A missing group is
reported as undefined and fails the corresponding directional check.

### D4: fixed candidate-direction rule

The only candidate direction that P3 may admit is **contribution tempering**:
retain Eqs. (1)--(20), strict Eq. (15), `ready_order`, all feasibility and HPA
semantics, and reduce the already published Eq. (9) coefficient `mu` from the
current 1.0. This direction is supported only if all conditions pass:

1. population, identity, window alignment, and all D3 invariants pass;
2. `D/P >= 0.05` in at least four of five centre seeds;
3. `(S+C)/A >= 0.20` in at least four of five centre seeds;
4. the player-weighted non-running share in `D>0` windows is at least that in
   `D=0` windows in at least three seeds, with both groups defined in at least
   four seeds;
5. both P2 `r0` neighbours satisfy the D1 dormancy rule; and
6. neither failed `wq` neighbour is relabelled as a successful candidate.

If all six pass, P3 authorizes only a separate zero-result preregistration for
the centre `mu=1.0` and exactly two candidates, `mu=0.75` and `mu=0.50`, on a
fresh D126--D130 bank. It does not authorize implementation or sampling. The
future gate must retain the P2 dual-effect margins (mean throughput/QPR ratios
at least 1.015/1.11), paired robustness, per-seed safety, leave-one-out,
completion/latency, runtime/reference, and overhead requirements.

If any condition fails, no parameter or mechanism successor is admitted from
P3. In particular, P3 cannot fall back to a warm guard, action-set restriction,
lookahead, order, or ready-cap candidate; those paths require evidence not
supplied by this diagnostic and remain closed.

## 5. Outputs and stopping point

One machine JSON and concise CSV tables are written in a new P3 diagnosis
root. The machine report must include all run/window contributions, invariant
checks, D1/D2 pair rows, D3 run rows, six D4 conditions, input receipts, and a
canonical document hash. The analyzer is run once after source/tests and a
result-blind selection receipt are committed.

At completion it sets exactly one of:

- `complete_contribution_tempering_preregistration_authorized`; or
- `complete_no_p3_successor_authorized`.

In both cases, formal Q81--Q100 sampling, strong baselines, E7 figures, and
paper performance claims remain blocked.
