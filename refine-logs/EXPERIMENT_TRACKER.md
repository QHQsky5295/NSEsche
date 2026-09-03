# NSESche TSC Resubmission Experiment Tracker

| ID | Paper section | Status | Runs | Paper-ready gate | Evidence |
|---|---|---|---:|---|---|
| M0-WORKTREE | Revision workspace | COMPLETE | 0 | Separate rollback-safe worktree | `agent/tsc-resubmit-final` |
| M0-PROTOCOL | Goal, plan and tracker freeze | COMPLETE | 0 | Files committed with hashes | commits `251633f`, `7e239df` |
| M0-STORAGE | Redundant `nse_dev` archive/cleanup | COMPLETE / RE-CLOSED 2026-09-03 | 0 | Verified archives; only current G1 large-output block remains on C | `STORAGE_CLEANUP.20260903-final.md`; 61,641-file redundant-copy archive, 47,126-file closed-development archive, and six archived historical binaries all verified before deletion |
| M0-METHOD | Formula-consistent implementation audit | COMPLETE | 0 | Method boundary tests pass | `M0_METHOD_AUDIT.md`; NSESche 25/25 pass |
| M0-PIPELINE | Manifest, metrics and QC audit | COMPLETE / PATH RELIABILITY RE-CLOSED | 0 | Required fields and invariants pass | `M0_PIPELINE_AUDIT.md`; current regression protocol 176/176, analysis 48/48; verified exact-copy promotion and result-blind canonical reconciliation |
| G0-RUNTIME | Common cold-start transition semantics | CORRECTION REFROZEN / G1 VERIFIED | 1 original same-tape diagnostic + 1 final D44 build/replay pair | Starting containers finish within hard memory and matching references are rebuilt | Commit `16c32c2` reserves transition memory before runnable tasks; the final runtime is commit `98f822c`, binary SHA `7f1d1ad8...06a4`; final D44 build/replay both completed 112 requests with 984 matched state pairs; see `G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md` and `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md` |
| G0-EQUATIONS | Paper Eqs. (1)--(20), code and log alignment | AUDIT COMPLETE / STRICT CANDIDATE SELECTED | 0 | Formal candidate uses strict Eq. (15), reference/gap bases and Eq. (14) proxy are disclosed | Guarded variants remain ineligible; all three G1 candidates declared strict best response and zero regret guard; `ready_order` won the frozen screen without changing paper equations; see `G0_PAPER_CODE_EQUATION_ALIGNMENT.md` and `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md` |
| G0-FEEDBACK | Eq. (16)--(20) control-path observability | CORRECTED-RUNTIME VERIFIED | D44 + 90 G1 screen runs | Control gap, gamma, price multiplier and outer assignment trace revalidate exactly from real logs | D44 passed `stream_contract_ready=true`; all 90 G1 runs passed canonical formula gates; G1 contained 140,034 feedback-trace rounds and 51,550 applied rounds; see `G0_OUTER_FEEDBACK_OBSERVABILITY_AUDIT.md` and `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md` |
| G1-TECH | Corrected-runtime D44 technical gate | PASSED / TECHNICAL ONLY | 1 reference build + 1 replay; 0 new seeds | Matching reference, runtime identity, pairing, `stream_contract_ready=true`, and analyzer pass | Build/replay completed 112; 984 matched state pairs; 1,000 policy/contract/feedback windows; technical-gate document SHA `c42071ee...b85e`; not paper-eligible; see `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md` |
| G1-SCREEN | Strict-Eq.15 corrected-runtime candidate screen | COMPLETE / `ready_order` SELECTED | 90/90 | Complete D61--D65 `3 candidates x 6 cells x 5 seeds` global-maximin selection | 30 tapes, 90 references and 90 runs completed; all valid observations retained; worst control-relative ratio: C0 1.000, C1 0.9427, C2 0.4151; selection document SHA `30f15c1a...98a6`; development-only, not paper-eligible; see `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md` |
| G1-QUAL | Independent corrected-runtime E1 qualification/main result | HOM-LOW COMPLETE / FAILED GATE / DEVELOPMENT RETURN | 200/1200 | NSESche mean throughput and mean QPR are first in all six cells with complete QC | homogeneous-low completed 200/200 on attempt 1 but NSESche is -1.04% throughput and -9.26% QPR versus FaaSRank; old-PDF alignment also failed; middle remains blocked; see `G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md` |
| G2-INIT | Strict Eq.15 feasible-initialization successor family | COMPLETE / C0 SELECTED / FAILED BASELINE GATE | 135/135 online; 90/90 references; 30/30 tapes | Global six-cell maximin winner also strictly leads all nine paired low-load baselines on D66--D70 | C0 worst ratio 1.000; C1 0.8574; C2 0.4810; C0 beats only random/hash in both low-load metrics; formal confirmation false; see `G2_STRICT_INITIALIZATION_RESULT_AUDIT.md` |
| B0-PROVENANCE | Old-result/whole-scene protocol identifiability | CLOSED / `legacy protocol unidentifiable` | 0 new runs | Recover one unique common historical protocol or fail closed without calibration | Empty repeated seed, overwrite export, missing binary/config binding, nine baseline rewrites and coupled common-runtime changes prevent unique recovery; 30-run calibration not authorized; see `B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md` |
| G3-DIAG | Decision-neutral mechanism diagnosis | PROTOCOL/RUNTIME/MANIFEST FROZEN / REPLAY AUTHORIZED | 0/50 diagnostic replays | One falsifiable formula-consistent cause is declared before candidate design | Protocol/analyzer commit `721b7a1`; binary SHA `3029160d...9f891`; ready-manifest document hash `d3f7b18c...b0a91`; exact 20+30 source binding validates; D71 unopened; see `G3_ORDER_COUNTERFACTUAL_PROTOCOL_FREEZE.md` |
| M1-PILOT | Workload/SLA/reference pilot | COMPLETE | 9 tape captures + 24 SLA runs | 1.9k/2.6k/7.0k tapes and three-seed SLA frozen | `M1_PILOT_AUDIT.md`; frozen SLA SHA `496f7053...cf3f2` |
| M1-QUAL | Six-cell method qualification | FAILED GATE / DIAGNOSIS COMPLETE | 90/90 screen; 1200/1200 qualification; 30/30 diagnostic canonical | Development throughput/QPR gates pass | `ready_order` failed 6/6 cells; decision-neutral audit passed 30 pairs/30,000 windows; objective conflict supported, supply limitation not supported; local family exhausted; see `M1_MECHANISM_DIAGNOSIS_RESULT_AUDIT.md`; no M2 run authorized |
| M1-GUARD | Fresh-bank completion-guard redesign | FAMILY REJECTED / DIAGNOSIS COMPLETE | 90/90 screen; 0/1200 forbidden qualification | Guard candidate wins global screen, then six-cell dual-first qualification | `ready_order` won frozen maximin rule; static finish proxy caused within-window concentration and seed-level collapse; see `M1_COMPLETION_GUARD_RESULT_AUDIT.md`; no M2 run authorized |
| M1-DYNAMIC | Fresh-bank dynamic-contention guard | SCREEN COMPLETE / TERMINAL FAILURE | 90/90 screen; 0/1200 forbidden qualification | Dynamic guard wins global screen, then six-cell dual-first qualification | Frozen screen could not rank three zero-completion rows; later G0 audit proved a common cold-start transition-starvation defect, so D41--D45 remains historical diagnosis and cannot select a corrected-runtime candidate; see `M1_DYNAMIC_CONTENTION_GUARD_RESULT_AUDIT.md`, `M1_DYNAMIC_CONTENTION_TERMINAL_DIAGNOSIS.md`, and `G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md`; no M2 run authorized |
| M2-HOM-LOW | Homogeneous-20 low | FORMAL COMPLETE / FAILED GATE / NOT CLOSED | 200/200 | NSESche mean throughput and QPR highest | all rows retained; FaaSRank leads both primary means; no baseline passes the joint old-PDF +/-15% alignment check; `next_cell_authorized=false`; see `G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md` |
| M2-HOM-MID | Homogeneous-20 middle | TODO | 200 | NSESche mean throughput and QPR highest | pending |
| M2-HOM-HIGH | Homogeneous-20 high | TODO | 200 | NSESche mean throughput and QPR highest | pending |
| M2-HYPER | Parameter validation | TODO | 240 | Published centres Pareto-undominated | pending |
| M2-ABLATION | Four mechanism ablations | TODO | 240 | Full exceeds all ablations | pending |
| M2-HET | Heterogeneous-20 comparison | TODO | 600 | All three cells close | pending |
| M2-SCALE | Proportional 100/500-node scaling | TODO | 1200 | Complete Fig.10 evidence | pending |
| M3-BURST | Controlled burst comparison | TODO | 600 | Recovery/tail evidence complete | pending |
| M3-QOS | Balanced-QoS comparison | TODO | 200 | Class/SLA/fairness evidence complete | pending |
| M3-WELFARE | Pricing, welfare and exact PoA | TODO | 80+300 states | Welfare evidence complete | pending |
| M3-FEATURES | Feature validation | TODO | reuse | Correlation analysis complete | pending |
| M3-CONVERGENCE | Convergence/reference overhead | TODO | reuse | Reviewer audit table and Fig.13 complete | pending |

No main-paper experiment group is currently `paper_ready_closed`.

M1 diagnosis closure: the 30 fixed D01--D05 runs completed on attempt 1 with
zero quarantine.  Running-warm candidates were available for 79.56% of
273,972 players, and 29.40% of those candidates were bypassed.  The next
selection stage requires a new preregistered operational family and a fresh
development seed bank; D01--D20 cannot be reused for that selection.

M1 completion-guard closure: all 30 tapes, 90 references, and 90 screen runs
completed on attempt 1 with zero quarantine.  The unchanged `ready_order`
control won the preregistered global maximin rule, so the guard family was
rejected and qualification derivation failed closed.  The result audit traced
the failure to a static projected-finish proxy overriding the paper utility's
dynamic within-window externality and concentrating assignments.  Any
successor must be a separately preregistered contention-aware family on a new
seed bank; the D21--D40 guard qualification and M2 remain unauthorized.

M1 dynamic-contention freeze: the paper utility and Eqs. 1--20 remain
unchanged.  The two preregistered guards add the current-solve assigned-request
count only to the operational projected-finish safeguard.  Source commit
`99a5e7f3a800e2542e41b767afedc0b8052b4461` produced the frozen executable
SHA-256 `e5a1b1fe9c26853554c459a10cc71924c107f545afbc5a1d96b64da4eb6e2df8`
(4,678,144 bytes).  Protocol commit
`ca7df95c73cbb413d6af6c24a318f53a17d79a33` freezes D41--D60, the D41--D45
90-run screen, the unchanged global maximin selection rule, and fail-closed
qualification authorization.  Verification passed 30/30 directed Rust tests,
166/166 protocol tests and 48/48 analysis tests; the post-format targeted
dynamic/guard rerun passed 14/14.  No D41 data existed before the protocol
commit.

M1 dynamic-contention closure: all 30 tapes, 90 references, and 90 screen runs
completed on attempt 1 with zero quarantine.  One completed capture directory
was renamed inside the same canonical root after its tape and receipt hashes
were verified; no scientific process was rerun and the strict binder passed.
The complete screen contained three fixed high-load zero-completion rows, so
their latency, cost per completion, and QPR were undefined.  The frozen global
screen analyzer failed closed and wrote no selection receipt.  No seed was
dropped, replaced, or rerun.  The family and further local M1 candidate
addition are terminally closed under the preregistration; qualification and M2
remain unauthorized pending explicit user-level redesign direction.

G1 corrected-runtime closure: final D44 technical build/replay passed exact
state/assignment pairing and the stream-contract gate.  The fresh D61--D65
screen then completed 30 tape captures, 90 reference builds, and 90 candidate
runs on attempt 1 with zero quarantine.  All 90 QC-valid rows were retained.
The frozen global-maximin rule selected `ready_order`: its worst of twelve
throughput/QPR ratios was 1.000, versus 0.9427 for `ready_finish_tie` and
0.4151 for `formula`.  Two D62 middle-load environments were shared difficult
instances across all candidates and remain in the receipt.  Three capture,
one reference, and three result directories experienced a Windows name-placement
drift; exact key/run-id and file hashes were verified, no simulator process was
rerun, and the final analyzer accepted all 90 exact canonical paths.  G1 is a
development selection only.  A generalized result-blind reconciliation then
verified 87 already-exact paths and reconciled the three affected result paths,
adding exactly three ledger events; the immutable receipt is idempotent and the
185-event ledger chain is valid.  No main-paper group is closed.  Execution of
the frozen plan is now authorized, so Q61--Q80 preregistration is the next
scientific step; see `G1_CORRECTED_RUNTIME_RESULT_AUDIT.md`.

M0 storage re-closure: the non-Git `serverless_sim_game_nse_dev` directory
had been restored after the previous cleanup and differed from its older
archive.  Its current 61,641-file non-build state was therefore archived and
fully reverified before deletion.  Six closed M1/G0 development run roots
(47,126 files) were also archived and removed, while six superseded Rust build
trees were deleted after their exact executables were preserved on E.  C-drive
free space rose from 311.94 to 331.55 GiB.  The active G1 run root and final
runtime are the only retained large current block; see
`STORAGE_CLEANUP.20260903-final.md`.

G1 formal Q61--Q80 freeze: protocol commit
`125a741b7cffec1973f8d6632c781f9ff83d38ac` fixes the 10-method, six-cell,
20-paired-seed product, the `ready_order` NSESche candidate, one global binary,
the low and middle/high parameter centres, the homogeneous-low-first execution
order and the strict per-cell throughput/QPR gate.  The unbound manifest has
document hash `00238175...f4361` and file SHA-256 `5db12b5b...f36280`.
At preregistration the run root contained only that manifest and the frozen
FaaSRank model; no Q tape, reference or result existed.  The next step is
input-only capture and binding of 120 tapes, then 120 state-matched references;
the first online cell remains homogeneous-low 200/200.  No paper section is
closed; see `G1_FORMAL_Q61_Q80_PREREGISTRATION.md`.

G1 formal input/reference closure: all 120 workload captures and all 120
state-matched NSESche references completed on attempt 1.  The tape means are
1,925.45/2,525.95/6,970.40 requests/s for low/middle/high.  All artifact and
catalog hashes validate, all 120 FaaSRank rows bind the frozen independent
model, and the ready manifest has document hash `5c5868a2...7a91b`.  Across
117,138 reference state rows, 15 are negative and zero are exactly zero; all
are retained under the explicit nonpositive-reference fallback.  Middle Q71
has zero completed reference-build requests in both topologies and is retained
as a shared difficult workload.  Input/reference data are final dependencies
and must not be deleted.  Homogeneous-low 200-run online execution is now the
only open performance cell; no paper section is closed.  See
`G1_FORMAL_INPUT_REFERENCE_FREEZE.md`.

G1 formal homogeneous-low result: all ten methods by Q61--Q80 completed
200/200 canonical online runs on attempt 1, with complete QPR coverage and no
result-conditioned deletion or rerun. FaaSRank leads at 1.59810 req/ms and
0.064039 mean QPR; NSESche reaches 1.58150 and 0.058107, margins of -1.04% and
-9.26%. NSESche has lower mean cost than FaaSRank, but +8.467 ms paired mean
latency and -0.008747 completion ratio erase that advantage. Warm bypass and
starting-container placement are the main broad QPR correlates, while Q69/Q74
also expose tail throughput and convergence/reference cases. Pixel-calibrated
Fig. 6 readings show that none of the nine new baseline triples is jointly
within the frozen old-PDF +/-15% throughput/QPR/cost bands, so the baseline
rows are retained but not declared final frozen controls. The cell report sets
`next_cell_authorized=false`; homogeneous-middle and all later paper
experiments remain unopened. See
`G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md`.

G2 strict-initialization preregistration: the Q61--Q80 diagnosis motivates a
new three-candidate family that changes only construction of Algorithm 1's
initial feasible assignment. All subsequent moves remain strict Eq. (15)
utility best responses. C0 is unchanged `ready_order`; C1 initializes on a
feasible running-warm node when available; C2 initializes by the frozen
dynamic finish score. The fresh D66--D70 matrix contains 30 tapes, 90 matching
candidate references, 90 candidate runs, and 45 paired homogeneous-low
baseline controls. The frozen six-cell global-maximin winner must also lead all
nine low-load baselines in both throughput and QPR before a new disjoint formal
bank can be authorized. No D66 artifact existed at preregistration; see
`G2_STRICT_INITIALIZATION_PREREGISTRATION.md`.

G2 strict-initialization implementation freeze: source commit
`3ae7792782adcef60a254fa7c6bdb60a43d8171d` implements exactly C1 and C2 with
distinct reference-key tags and initialization-only diagnostics. The running-
warm registry is populated only by containers in the `Running` state. Inner
best responses for C0/C1/C2 remain strict Eq. (15) utility argmax updates.
Formatting, 32 directed NSESche tests, 11 Rust configuration tests, 64 frozen-
protocol regression tests, and the new Python schema test passed. Sampling is
still prohibited until the G2-specific protocol, release executable, and
source-bound manifest are frozen. No D66--D70 artifact exists; see
`G2_STRICT_INITIALIZATION_IMPLEMENTATION_AUDIT.md`.

G2 protocol/runtime freeze: protocol commit
`5926c99d35f7788140d40f6bbcb4f879033f88ad` fixes the complete 135-run
development product, 30 shared tape keys, 90 candidate-specific references,
global maximin selection, and the nine-baseline homogeneous-low dual-metric
gate. The unique release executable is 4,740,096 bytes with SHA-256
`18f5f85ac6bd5276948709ed1c0abc42dfdb4c070fbd63af6cd0a00cb19c810d`;
Rust-source drift from commit `3ae7792` is zero. The validated unbound manifest
has document hash `afcb15cc...b7d19` and file SHA-256 `d182155a...db7c9`.
Complete verification passed 185/185 protocol and 48/48 analysis tests. The
run root initially contained only the unbound manifest, so the next authorized
operation is exactly 30 input-only D66--D70 tape captures; no online run is yet
authorized. See `G2_PROTOCOL_RUNTIME_FREEZE.md`.

G2 input/reference closure: all 30 frozen D66--D70 workload tapes and all 90
candidate-specific matching references completed, canonicalized, and verified
on attempt 1. The catalogs contain 30 and 90 exact entries, both ledgers are
complete, and no partial or quarantined artifact exists. Across 87,770
reference state rows, 58 are negative and all are retained under the frozen
fallback; every reference build completed at least one request. The final
ready manifest validates 135 runs and 90 reference dependencies with document
hash `8173ab61...cd3f4`; tapes, FaaSRank models, and references are all bound.
The expected `all_sla_targets_bound=false` reflects that G2 has no offline-SLA
product. The complete online development screen is now authorized, but its
rows remain non-formal and a new formal bank is prohibited unless both frozen
selection gates pass. See `G2_INPUT_REFERENCE_FREEZE.md`.

G2 strict-initialization closure: all 135 online runs completed and
canonicalized on attempt 1, with 135 summaries, 135 QC reports, zero missing or
unexpected IDs, zero retry directories, and zero quarantine. Result-blind
reconciliation verified all 135 paths as exact; the 282-event ledger chain is
valid. The frozen global maximin rule selected unchanged C0 `ready_order`:
worst twelve-ratio scores are 1.0000 for C0, 0.8574 for C1, and 0.4810 for C2.
C0 then passed both homogeneous-low metrics only against random and hash, so
the nine-baseline gate failed and formal confirmation remains unauthorized.
C1 led all nine baselines in low-load throughput but not QPR and cannot be
substituted post hoc. Initialization refinements selected lower instantaneous
utility in about 99--100% of changed choices. A corrected active-window audit
shows that explicit inner/outer limit hits are rare (the aggregate
`nonconvergence_rate` also counted no-player windows), so G2 does not justify a
convergence-budget successor. The next step is a result-blind whole-scene
provenance/configuration audit because all nine G1 baselines failed the frozen
old-PDF joint alignment bands. Any later G3 requires a fresh preregistered
development bank. See
`G2_STRICT_INITIALIZATION_RESULT_AUDIT.md`.

Legacy-result provenance audit (2026-09-03): two tracked 2025-07-21 Excel
workbooks recover the old low-load NSESche anchor (`T=1.700`,
`cost=0.313890`, `latency=34.0659 ms`, `QPR=0.158983`). They contain one
constant per variant/load and no seed/run/config identifiers. The exporter
stores one dictionary entry per `(load, algorithm)` and overwrites duplicate
JSONs instead of averaging them; the source cache JSON is absent from Git.
The historical NSESche implementation also differs materially from the
current paper-equation implementation. Old bars are therefore provenance
anchors, not a replayable 20-seed bank. B0 whole-scene audit is now the only
open experiment-plan stage; D71, homogeneous-middle formal, and later paper
experiments remain unopened. See `LEGACY_RESULT_PROVENANCE_AUDIT.md` and
`TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V2.md`.

B0 whole-scene closure (2026-09-03): historical and current steady E1 share
the visible 1000-frame horizon, load multipliers, node/resource ranges and
primary metric formulas, so drain or a simple unit conversion does not explain
the discrepancy. The historical batch repeated the empty seed, the exporter
overwrote duplicate JSONs, and the workbook lacks binary/config/run binding.
In addition, all nine baselines, NSESche, HPA scale-up, placement feasibility,
atomic scale/place commit, deterministic ordering, and cold-start transition
semantics crossed implementation versions. No unique legacy estimand can be
recovered, so the immutable decision is `legacy protocol unidentifiable` and
the conditional 30-run calibration pilot is not authorized. TSCv1 remains the
independent rerun protocol; D71 and homogeneous-middle remain blocked pending
G3 preregistration. See `B0_SCENE_PROTOCOL_DIFFERENCE_AUDIT.md`.

G3 existing-log diagnosis closure (2026-09-03): the preregistered analyzer
retained all 200 G1 online runs, all 135 G2 online runs, and all 20 formal
NSESche/FaaSRank pairs. NSESche attains higher post-hoc paper welfare/player
(37.4369 versus 36.9401) but lower throughput (1.5815 versus 1.5981) and QPR
(0.058107 versus 0.064039). Cold-start wait is the largest positive stage
difference (+3.6277 ms, positive in 15/20 seeds), and cold-start event share
rises from 0.1754 to 0.2454. All 24 frozen correlations are reported. Direct
warm/finish/initialization and convergence-budget families remain rejected;
solver/feedback axes do not qualify. Feasibility/concentration evidence
authorizes only a no-feedback scarcity/order counterfactual on retained solver
states, not a new candidate. `D71_authorized=false`, homogeneous-middle formal
remains blocked, and no paper group is closed. See
`G3_EXISTING_LOG_DIAGNOSIS_AUDIT.md`.

G3 scarcity/order counterfactual preregistration (2026-09-03): before source
implementation or diagnostic replay, O0 `ready_order` and four deterministic
alternative orders were frozen on exactly 50 retained C0 source runs: Q61--Q80
homogeneous-low plus D66--D70 across all six G2 cells. Every alternative keeps
the same candidates, Eqs. (1)--(20), strict Eq. (15), prices, and four-round
cap; none can reach dispatch or feedback. The integrity gates require exact
live C0 parity, O0 first-inner hash parity, complete raw reporting, and an
independent PNE certificate. Selection ignores replay throughput/QPR and uses
predeclared seven-stratum welfare, startup-burden, and projected-finish rules.
No implementation or replay exists yet, `D71_authorized=false`, and no paper
group is closed. See `G3_ORDER_COUNTERFACTUAL_PREREGISTRATION.md`.

G3 order-counterfactual implementation closure (2026-09-03): a default-off
instrumented branch now reconstructs O0 and evaluates O1--O4 plus E0 from the
same immutable window snapshot. The return value is diagnostics only; live C0
remains the sole input to dispatch, reference, and price feedback. Independent
strict-PNE certification, hashes, welfare components, cold/projected-finish
proxies, placement metrics, and diagnostic overhead are emitted for every
order. NSESche tests pass 36/36 and Python protocol discovery passes 185/185.
The full Rust suite's two unrelated failures were isolated: the existing
wall-clock assertion remains failing, while the Python consistency test passes
with the existing Anaconda environment. No replay has run; source inventory,
analyzer, manifest, and release binary remain prerequisites. D71 and formal
middle remain blocked. See
`G3_ORDER_COUNTERFACTUAL_IMPLEMENTATION_AUDIT.md`.

G3 order-counterfactual protocol/runtime freeze (2026-09-03): protocol and
analysis commit `721b7a1` freezes the mixed-source 50-replay manifest schema,
source-artifact hashes, exact seven-stratum thresholds, fail-closed parity
checks, raw-output exporter, and result-blind source order before replay. The
release binary is 4,770,816 bytes with SHA-256 `3029160d...9f891` and is bound
to audited Rust source commit `14a61d2`; source drift is zero. The immutable
ready manifest is 1,459,713 bytes with document hash `d3f7b18c...b0a91` and
file SHA-256 `5b55a4d5...af22`; it binds every source run config, summary,
Nash stream, tape, reference and both source manifests. Four focused Rust
tests, 11 G3 Python tests, and 27 affected protocol/analysis regression tests
pass. No G3 replay existed at this freeze. Exactly the 50 declared diagnostic
replays are now authorized; they remain observation-only and cannot authorize
D71 until their complete post-run gate is applied. See
`G3_ORDER_COUNTERFACTUAL_PROTOCOL_FREEZE.md`.

G3 technical-correction freeze (2026-09-03): the first analysis retained
50/50 exact live C0 replays but failed closed. Analyzer V1 had three protocol-
interpretation defects and a binary32 boundary mismatch; corrected V2 was
frozen at commit `09828ca`, retained every 300,000 order/window row, and
reduced the remaining failure to three genuine E0 instrumentation records.
Those records exposed that a capped O0 could remain the E0 incumbent despite
eligible alternatives. The narrowly preregistered source fix is commit
`1666893`; five focused Rust and 13 G3 Python tests pass. The corrected release
binary SHA-256 is `6a05e0b1...b4ac3`, Rust-source drift is zero, and the new
50-run manifest document/file hashes are `df5d293d...3bbb` and
`1082c383...e2e7`. A recursive comparison proves all scientific inputs and
the ordered source bank unchanged. Exactly these 50 repeated diagnostics are
now authorized. D71, homogeneous-middle formal, and every paper group remain
blocked. See `G3_ORDER_COUNTERFACTUAL_ANALYZER_CORRECTION.md`,
`G3_ORDER_COUNTERFACTUAL_INSTRUMENTATION_CORRECTION_PREREGISTRATION.md`, and
`G3_ORDER_COUNTERFACTUAL_E0_CORRECTED_RUNTIME_FREEZE.md`.
