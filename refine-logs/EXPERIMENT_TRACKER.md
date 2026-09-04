# NSESche TSC Resubmission Experiment Tracker

| ID | Paper section | Status | Runs | Paper-ready gate | Evidence |
|---|---|---|---:|---|---|
| M0-WORKTREE | Revision workspace | COMPLETE | 0 | Separate rollback-safe worktree | `agent/tsc-resubmit-final` |
| M0-PROTOCOL | Goal, plan and tracker freeze | COMPLETE | 0 | Files committed with hashes | commits `251633f`, `7e239df` |
| P0-CLAIMS | Reviewer/claim/evidence/runtime contract | COMPLETE / P1 AUTHORIZED | 0 | 13 issues and all material manuscript claims mapped; exact runtime recovered; P1 needs no replay | 31-claim map, reviewer evidence matrix, and runtime audit; exact `98f822cf` binary SHA `7f1d1ad8...06a4`; see `P0_CLAIM_RUNTIME_AUDIT_RESULT.md` |
| P1-FREEZE | Convergence/reference/exact-small reviewer package | PERMANENTLY CLOSED / PAPER-WRITING READY | 20 retained seeds + 300 exact games | Immutable root-level package, complete manifest, exact source-result match, and no later algorithm mutation | 31 read-only files / 1,988,774 bytes; manifest SHA `D1E17072...0B579`; see `closed-experiments/P1_convergence_offline_reference_exact_small_PoA` and `P1_PERMANENT_FREEZE_AUDIT.md` |
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
| G3-DIAG | Decision-neutral mechanism diagnosis | COMPLETE / E0 ONLY ELIGIBLE FOR SEPARATE PREREGISTRATION | 50/50 corrected diagnostic replays | Integrity passes and a candidate may qualify only from frozen welfare/startup/projected-finish rules, never replay throughput/QPR | 50,000 streams and 300,000 mechanism rows complete; E0 is the sole eligible option, with no added bad window in seven strata; `D71_authorized=false`; see `G3_ORDER_COUNTERFACTUAL_CORRECTED_RESULT_AUDIT.md` |
| G3-E0 | Operational E0 equilibrium-selector development | PREREGISTERED / IMPLEMENTATION AUTHORIZED / D71 SAMPLING BLOCKED | 0/135 online; 0/90 references; 0/30 tapes | A non-control E0 variant must beat C0 in throughput and QPR in all six cells, lead all nine homogeneous-low baselines in both metrics, and stay within the frozen 9x solve-time cap | C0 plus first-round and every-round E0 variants frozen on D71--D75; no D71--D75 artifact existed at preregistration; implementation/protocol/runtime freeze required before sampling; see `G3_E0_OPERATIONAL_CANDIDATE_PREREGISTRATION.md` |
| M1-PILOT | Workload/SLA/reference pilot | COMPLETE | 9 tape captures + 24 SLA runs | 1.9k/2.6k/7.0k tapes and three-seed SLA frozen | `M1_PILOT_AUDIT.md`; frozen SLA SHA `496f7053...cf3f2` |
| M1-QUAL | Six-cell method qualification | FAILED GATE / DIAGNOSIS COMPLETE | 90/90 screen; 1200/1200 qualification; 30/30 diagnostic canonical | Development throughput/QPR gates pass | `ready_order` failed 6/6 cells; decision-neutral audit passed 30 pairs/30,000 windows; objective conflict supported, supply limitation not supported; local family exhausted; see `M1_MECHANISM_DIAGNOSIS_RESULT_AUDIT.md`; no M2 run authorized |
| M1-GUARD | Fresh-bank completion-guard redesign | FAMILY REJECTED / DIAGNOSIS COMPLETE | 90/90 screen; 0/1200 forbidden qualification | Guard candidate wins global screen, then six-cell dual-first qualification | `ready_order` won frozen maximin rule; static finish proxy caused within-window concentration and seed-level collapse; see `M1_COMPLETION_GUARD_RESULT_AUDIT.md`; no M2 run authorized |
| M1-DYNAMIC | Fresh-bank dynamic-contention guard | SCREEN COMPLETE / TERMINAL FAILURE | 90/90 screen; 0/1200 forbidden qualification | Dynamic guard wins global screen, then six-cell dual-first qualification | Frozen screen could not rank three zero-completion rows; later G0 audit proved a common cold-start transition-starvation defect, so D41--D45 remains historical diagnosis and cannot select a corrected-runtime candidate; see `M1_DYNAMIC_CONTENTION_GUARD_RESULT_AUDIT.md`, `M1_DYNAMIC_CONTENTION_TERMINAL_DIAGNOSIS.md`, and `G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md`; no M2 run authorized |
| M2-HOM-LOW | Homogeneous-20 low | FORMAL DATA CLOSED / CLAIM NOT LEADING | 200/200 | Complete paired QC and transparent rank/interval report | all rows retained; FaaSRank leads both primary means; V4 reuses this cell and removes the old universal claim; see `G1_FORMAL_HOMOGENEOUS_LOW_RESULT_AUDIT.md` |
| M2-HOM-MID | Homogeneous-20 middle | FORMAL COMPLETE / NOT PAPER-READY | 200/200 | Complete paired QC, full defined QPR, and transparent rank/interval report | all first QC-valid rows retained; five Q71 rows have zero completion and undefined QPR; NSESche ranks 5th in throughput and 8th in applicable QPR; no figure/high progression; see `P2_HOMOGENEOUS_MIDDLE_RESULT_AUDIT.md` |
| P2-DIAG | Homogeneous-middle mechanism diagnosis | EXPLORATORY COMPLETE / NEW-ALGORITHM BOUNDARY | 0 new runs | Read-only diagnosis may explain the retained result but cannot select or confirm a candidate | dominant-DAG complexity drives seed spread; Q71 is valid; broad in-flight request concurrency exposes an end-to-end completion objective mismatch; only a separately governed admission/backpressure contribution remains plausible; see `P2_HOMOGENEOUS_MIDDLE_MECHANISM_DIAGNOSIS.md` |
| G9-BACKPRESSURE | Request-level bounded-concurrency successor | PERMANENTLY CLOSED / FAILED GATE | 75/75 development | Exact fixed population must pass all dual-metric, paired, safety, activation, runtime, and overhead gates | request backpressure failed its frozen gate and is archived as negative development evidence; no confirmation/formal progression; see `G9_REQUEST_BACKPRESSURE_RESULT_AUDIT.md` and `closed-experiments/G9_request_backpressure_development_gate_failed` |
| G10-WORK-CONSERVING | Remaining-work/frontier successors | PERMANENTLY CLOSED / FAILED GATE | 45/45 development | One candidate must pass all nine C0-relative conditions across three loads | neither work-conserving candidate qualified; no strong-baseline or confirmation authorization; see `G10_WORK_CONSERVING_RESULT_AUDIT.md` and `closed-experiments/G10_work_conserving_development_gate_failed` |
| G11-DIAG | Closed G10 state-regime diagnosis | COMPLETE / READY-THRESHOLD FAMILY CLOSED | 0 new runs | Read-only retained-evidence gate only | diagnosis found no justified successor in the ready-threshold family; see `G11_STATE_REGIME_DIAGNOSIS_RESULT_AUDIT.md` |
| G12-GLOBAL-READY | Global-ready fixed-N admission | PERMANENTLY CLOSED / FAILED GATE | 30/30 development | Exact C0/G12 population must pass all nine conditions across three loads | fixed-N repeated deferral failed seven conditions and exposed a persistent-backlog pathology; see `G12_GLOBAL_READY_ADMISSION_RESULT_AUDIT.md` and `closed-experiments/G12_global_ready_admission_development_gate_failed` |
| G13-DIAG | Deferral-persistence diagnosis | COMPLETE / G14 AUTHORIZED AND CONSUMED | 0 new runs | Five result-blind read-only conditions | isolated deferral outperformed persistent deferral with sign-stable LOO contrasts; this authorized only G14; see `G13_DEFERRAL_PERSISTENCE_DIAGNOSIS_RESULT_AUDIT.md` |
| G14-RELEASE-VALVE | One-bit deferral release valve | PERMANENTLY CLOSED / FAILED GATE | 30/30 development | Exact C0/G14 population must pass all nine conditions across low/middle/high | state-machine activation passed and high-load throughput/QPR improved 15.1%/27.1%, but middle throughput and low/middle paired gates failed; no strong baselines or confirmation; see `G14_DEFERRAL_RELEASE_VALVE_RESULT_AUDIT.md` and `closed-experiments/G14_deferral_release_valve_development_gate_failed` |
| G15-DIAG | First-overflow magnitude diagnosis | COMPLETE / G16 PREREGISTRATION AUTHORIZED | 0 new runs | Fixed threshold classifier, dual-effect direction, and complete LOO stability must all pass | all five frozen conditions passed; `h=1.25` gives BA/sensitivity/specificity 0.80/0.80/0.80 and sign-stable dual effects across every LOO; this authorizes only a separate G16 preregistration; see `G15_OVERFLOW_MAGNITUDE_DIAGNOSIS_RESULT_AUDIT.md` |
| G16-MAGNITUDE-VALVE | Overflow-magnitude-gated release valve | PERMANENTLY CLOSED / FAILED GATE | 30/30 development | Exact C0/G16 D111--D115 product must pass all nine across-load primary, robustness, safety, activation, runtime, and overhead conditions | activation and high-load throughput/QPR gains passed, but middle throughput/QPR fell 5.55%/1.01% and low/middle robustness failed; no strong baselines or confirmation; see `G16_OVERFLOW_MAGNITUDE_VALVE_RESULT_AUDIT.md` and `closed-experiments/G16_overflow_magnitude_valve_development_gate_failed` |
| G17-DIAG | Closed G16 threshold-safety diagnosis | COMPLETE / FIXED-THRESHOLD FAMILY CLOSED | 0 new runs | Exact closed-root validation plus six fixed threshold-safety conditions; may authorize at most one stricter current-window magnitude threshold | only integrity passed; selected `h=4` predicts 0/15 safe runs, while `h=1.5` has BA 0.45 and no middle safe group; no successor or sampling authorized; see `G17_THRESHOLD_SAFETY_DIAGNOSIS_RESULT_AUDIT.md` |
| G18-SOFT-CAP | 125%-capacity first-overflow release valve | PREREGISTERED / IMPLEMENTATION NEXT | 0/30 development | Exact C0/G18 D116--D120 product must pass all nine primary, robustness, safety, activation, runtime, and overhead conditions | one load-blind action-smoothing hypothesis only: material first overflow admits `ceil(5N/4)`, adjacent overflow releases all; no input or sampling yet; see `G18_OVERFLOW_SOFT_CAP_RELEASE_VALVE_PREREGISTRATION.md` |
| M2-HOM-HIGH | Homogeneous-20 high | BLOCKED UNTIL P1 AND MIDDLE | 0/200 | 20/20 paired QC plus statistics/receipt closure, independent of rank | inputs/reference already frozen; staged authorization pending |
| M2-HYPER | Parameter validation | BLOCKED UNTIL P1/P2 | 0/240 | frozen-grid evidence and complete uncertainty report | pending V4 preregistration |
| M2-ABLATION | Four mechanism ablations | BLOCKED UNTIL P1/P2 | 0/240 | complete paired component estimates; no required favorable sign | pending V4 preregistration |
| M2-HET | Heterogeneous-20 comparison | BLOCKED UNTIL P1/P2 | 0/600 | all three 20-seed cells close with ranks/intervals | pending V4 preregistration |
| M2-SCALE | Proportional 100/500-node scaling | BLOCKED UNTIL P1/P2 | 0/1200 | workload scales with capacity and complete paired evidence | pending V4 preregistration |
| M3-BURST | Controlled burst comparison | BLOCKED UNTIL P2 VALUE GATE | 0/600 | queue/recovery/tail/drop evidence complete | pending V4 P3 preregistration |
| M3-QOS | Balanced-QoS comparison | BLOCKED UNTIL P2 VALUE GATE | 0/200 | class/SLA/fairness evidence complete | pending V4 P3 preregistration |
| M3-WELFARE | Pricing/welfare comparators and exact PoA | P1 EXACT-SMALL CLOSED / P3 COMPARATORS BLOCKED | 0/80 online + 300/300 states | exact-small evaluator/reference/PNE consistency; later comparator evidence | exact PoA median/p95/max 1.002848/1.010731/1.018114 and independent verification pass; pricing/welfare comparators remain P3; see `P1_B_EXACT_SMALL_RESULT_AUDIT.md` |
| M3-FEATURES | Feature validation | BLOCKED UNTIL P2 | reuse | preregistered correlation/ablation analysis complete | reuse P2 E5/E7; no separate online matrix |
| M3-CONVERGENCE | Convergence/reference overhead | P1 SCOPE CLOSED / WRITING READY | 0 new runs; reuse 20 + 300 exact states | formal potential proof, retained-window statistics, reference accuracy/cost/fallback, and reviewer sufficiency audit complete | inner stability 19,509/19,509; outer placement stability 97.396%; 9 cap hits; exact-small reference p95 shortfall 0.0935%; see `P1_REVIEWER_SUFFICIENCY_AUDIT.md` and root `PROOF_PACKAGE.md` |

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

G3 corrected counterfactual closure (2026-09-03): all 50 repeated diagnostics
completed on attempt 1 and were retained. Result-blind reconciliation verified
50 exact canonical paths with no simulator rerun; the 102-event ledger chain is
valid. Analyzer V2 accepted 50/50 runs, 50,000 streams, and all 300,000
mechanism/window rows with zero parity or diagnostic errors. Relative to O0,
E0 improved all seven preregistered strata in startup burden and projected
finish while preserving the welfare envelope and adding no bad window. It is
the only eligible later-preregistration option. A correction comparison shows
exactly the intended three discrete E0-selection changes; every other discrete
candidate result is identical, with only <=1.7882e-7 binary32 dispersion
accumulation variation. Replay throughput/QPR were not used. The diagnostic
does not authorize D71 or any formal cell; the next step is a separate
operational-candidate preregistration on fresh D71--D75. No main-paper group is
closed. See `G3_ORDER_COUNTERFACTUAL_CORRECTED_RESULT_AUDIT.md`.

G3 E0 operational-candidate preregistration (2026-09-03): before source,
protocol, runtime, tape, reference, or online creation, C0 `ready_order`, C1
first-outer-round E0, and C2 every-outer-round E0 were frozen as the complete
candidate family. C1/C2 select only among complete, stable, independently
strict-PNE-certified outcomes under the unchanged G3 welfare envelope and
lexicographic burden rule; Eqs. (1)--(20), strict Eq. (15), price feedback,
parameters, and common runtime remain fixed. The fresh D71--D75 product is 30
tapes, 90 candidate-specific references, 90 six-cell candidate runs, and 45
paired homogeneous-low baseline runs. A non-control winner must have every one
of its twelve cell/metric mean ratios strictly above C0, then strictly exceed
all nine baselines in both homogeneous-low means, with complete QPR and at
most 9x C0 aggregate active-window `solve_us` in every cell. All valid rows
must be retained. Implementation and protocol work are authorized, but D71
sampling remains blocked until source, tests, one release binary, analyzer,
and a zero-data manifest freeze are committed. See
`G3_E0_OPERATIONAL_CANDIDATE_PREREGISTRATION.md`.

G3 E0 operational implementation closure (2026-09-03): source commit
`47da450` implements only the preregistered C1 first-round and C2 every-round
applications of the corrected E0 strict-PNE selector; C0 remains on its old
path. Eqs. (1)--(20), strict Eq. (15), prices, limits, dispatch, workload, and
metrics are unchanged. Selected-path convergence fields are separated from
all-order evaluation work and operational overhead. Formatting, 39/39 NSESche
tests, 10/10 configuration tests, and the Anaconda-backed Python consistency
test pass. The full Rust suite is 116/118; the two nonpassing cases are the
existing wall-clock assertion and default-Python missing-NumPy environment
case, with the latter passing 1/1 under the repository's Anaconda interpreter.
No D71--D75 data exists or has been inspected. Protocol/analyzer construction
is the only next authorized stage; D71 sampling, formal homogeneous-middle,
and all paper groups remain blocked. See
`G3_E0_OPERATIONAL_IMPLEMENTATION_AUDIT.md`.

G3 E0 protocol/runtime freeze (2026-09-03): protocol/analyzer commit
`9c8789f` freezes the exact 135-run D71--D75 product, runtime/state-hash
validation, global maximin rule, strict control and nine-baseline gates, and
the per-cell 9x aggregate active-window `solve_us` cap. Commit `93b572d` adds
the explicit incompatibility, deterministic fresh-scheduler, and O0-fallback
tests without changing an operational decision. NSESche is 42/42, the new
G3 analyzer is 6/6, cross-protocol regression is 66/66, and the Anaconda-backed
full Rust suite is 120/121 with only the existing unrelated wall-clock failure.
The final 4,811,264-byte release SHA-256 is `6f700b2b...a0c3`. The authorized
unbound manifest has document/file hashes `c0bbfd2a...a6d6` and
`a277e130...1d21`, binds 135 runs/27 cells/90 references, and is the sole file
in its run root. The earlier `9c8789f` root is a prohibited zero-data draft.
Exactly the complete 30-tape capture is now authorized; references remain
blocked until every tape is captured and bound, online runs remain blocked
until all references/model bindings complete, and formal execution remains
blocked. See `G3_E0_OPERATIONAL_PROTOCOL_RUNTIME_FREEZE.md`.

G3 E0 tape/model binding closure (2026-09-03): the final `93b572d` release
captured the complete 30-key D71--D75 tape product with 30 canonical paths and
receipts, zero failed/quarantined directories, and no online result creation or
inspection. The 30 topology keys correctly form 15 identical-event-stream
pairs, one per `(load, seed)`, while topology environments remain separately
hash-bound. The fail-closed binder reverified every tape, receipt, workload
profile, Azure-derived CDF provenance, and semantic environment bundle. The
tape catalog document/file hashes are `890bac97...27fb` and
`95b638e0...75a4`; the 135-run tape-bound manifest document hash is
`025755fc...7210`. The unchanged G1 frozen FaaSRank-P artifact
`4853fffa...f17e` was then bound after proving its calibration tape
`28a48254...25b9` is absent from all D71--D75 evaluation tapes, yielding model-
bound manifest hash `333a4394...9318`. Exactly all 90 offline references are
now authorized as the next atomic stage. All online runs, selection, extension,
formal execution, and paper-ready groups remain blocked. See
`G3_E0_TAPE_MODEL_BINDING_AUDIT.md`.

G3 E0 offline-reference closure (2026-09-03): all 90 frozen dependencies were
canonicalized on attempt 1, with 90 canonical directories and zero failed or
quarantined directories. The product exactly covers 3 candidates x 3 loads x
2 topologies x 5 seeds, with zero missing/extra keys and unique table, receipt,
process-observation, build-spec, state-pair-sequence, and assignment-sequence
hashes. All builder integrity checks passed, and independent catalog/receipt
reconciliation found zero metadata mismatches. The reference catalog
document/file hashes are `97b916f1...e34f` and `2ed0cb2c...118c`. The fail-
closed binder reverified all artifacts and produced the 135-run ready manifest
with document/file hashes `c7beed33...a657` and `a54f0fbb...02f4` and all tape,
model, and reference flags true. Exactly the complete 135-run online D71--D75
development stage is now authorized; selection, extension, formal execution,
and paper-ready groups remain blocked. See
`G3_E0_REFERENCE_BINDING_AUDIT.md`.

G3 E0 analyzer correction preregistration (2026-09-04): the complete 135-run
online product finished with exact run-ID coverage, all attempt 1, zero failed
or quarantined directories, and a valid 272-event ledger. The first frozen-
analyzer invocation failed on the first C0 runtime config before aggregate or
metric exposure and created no selection artifact. Result-blind inspection
identified one integration-only defect: the analyzer/test fixture read the
nonexistent `observation.order_counterfactual_enabled`, while C0/C1/C2 and the
established Rust schema emit
`decision_neutral_diagnostics.order_counterfactual_enabled=false`. The only
authorized production change is that exact lookup-path replacement, with the
fixture corrected and a fail-closed regression against a true real flag. No
data, simulator, binary, formula, metric, candidate, seed, selection rule, or
gate may change, and no simulator rerun is authorized. Analysis remains
blocked until the correction is tested, audited, and committed. See
`G3_E0_ANALYZER_CORRECTION_PREREGISTRATION.md`.

G3 E0 analyzer correction closure (2026-09-04): commit `a3ac15d` replaces
only the invalid analyzer lookup of
`observation.order_counterfactual_enabled` with the actual Rust-emitted
`decision_neutral_diagnostics.order_counterfactual_enabled`; it adds no
fallback. The fixture now matches the real schema, and a new explicit test
proves a false synthetic legacy field cannot mask a true real flag. Analyzer/
test SHA-256 values are `93a86896...3821` and `29233dea...2ce3`. G3 is 7/7,
combined G2/G3 regression is 13/13, Python compilation and Black checks pass,
and the reviewed production diff contains no metric, candidate, gate,
simulator, or artifact change. No rerun occurred and the first invocation
created no selection output. Exactly one analysis of the unchanged 135-run
canonical product is now authorized; formal execution remains blocked. See
`G3_E0_ANALYZER_CORRECTION_AUDIT.md`.

G3 E0 convergence/fallback analyzer correction preregistration (2026-09-04):
the second analysis passed the corrected C0/C1/C2 run-config check, then failed
before metric exposure on unconditional outer-round/feedback length equality;
no selection file was created. Source review proves an outer round is counted
when attempted but its feedback row exists only after stable inner completion.
A result-blind census of all 90 candidate streams found exactly 15 terminal
`inner_iteration_limit` windows (C0/C1/C2: 6/5/4) with the expected one-row
shortfall, plus ten authorized C1/C2 no-eligible O0 fallbacks. Nine unstable
fallbacks have no feedback row but match the final decision hash; one stable
uncertified fallback has a matching feedback row. Every non-fallback selection
is complete, stable, certified, positive-eligible, and feedback-hash matched;
there are zero structural exceptions. A narrowly enumerated correction and
directed negative tests are frozen; no metric, selection rule, gate, data,
simulator, or binary may change, and no rerun is authorized. Analysis remains
blocked pending tested/committed correction closure. See
`G3_E0_ANALYZER_FALLBACK_CORRECTION_PREREGISTRATION.md`.

G3 E0 convergence/fallback analyzer correction closure (2026-09-04): commit
`604a915` now validates feedback rows against completed stable outer rounds,
allows only the three source-defined terminal inner failures to omit the final
row, and handles preregistered zero-eligible O0 fallback without weakening
non-fallback strict-PNE checks. Stable fallback requires feedback-hash identity;
unstable terminal fallback requires final decision/dispatch-hash identity.
Normal missing traces, uncertified non-fallback selections, malformed fallback,
and mismatched dispatch identities still fail closed. Analyzer/test SHA-256
values are `93e532ea...295a` and `ba81bc13...553a`; G3 is 9/9, combined G2/G3
is 15/15, and compile, Black, and diff checks pass. Simulator, binary, all 135
runs, metrics, candidates, seeds, and gates are unchanged. Exactly one further
analysis of the same canonical product is authorized; no rerun or extension is
permitted and formal execution remains blocked. See
`G3_E0_ANALYZER_FALLBACK_CORRECTION_AUDIT.md`.

G3 E0 operational development closure (2026-09-04): the corrected frozen
analyzer completed on the unchanged 135/135-run D71--D75 product, with all
runs canonical on attempt 1 and zero failed/quarantined runs. The selection
artifact has document/file SHA-256 values `4cb006a3...6a34` and
`22e5cf35...f3f7`. Neither C1 nor C2 passes the all-12 control-improvement
gate: their worst throughput/QPR ratios relative to C0 are 0.7624 and 0.7372.
All 24 five-seed paired-difference 95% t intervals include zero. The
homogeneous-low nine-baseline gate also fails: C0 beats both primary means for
2/9 baselines, while C1 and C2 each do so for 4/9. All E0 solve-time ratios
remain below the preregistered 9x cap and non-O0 selection rates of roughly
31--45% show that the intervention is active, so the failure is not attributable
to an inert implementation or the cost ceiling. Status is
`complete_g3_e0_development_gate_failed`; selected candidate remains
`ready_order`; no extension, formal execution, burst/scaling experiment, or
paper-ready group is authorized. The only next admissible work is a
result-blind QPR/completion/resource/waiting/cold-start and state-regime
diagnosis over retained data, before any fresh-bank mechanism proposal. See
`G3_E0_OPERATIONAL_RESULT_AUDIT.md` and its three retained CSV tables.

G3 post-failure claim/scene diagnosis preregistration (2026-09-04): after the
complete three-candidate E0 bank failed, no fourth rule or new sample is
authorized. One read-only analysis of the unchanged 135-run D71--D75 product
is frozen before detailed decomposition. It will factor paired log-QPR exactly
into throughput, latency, and unit-completion-cost contributions; compare
completion, queue, resource, and starting-container occupancy proxies; measure
E0 intervention/state associations; and exploit the topology-paired event
streams for a high-load difference-in-differences diagnostic with low/middle
negative controls. All five seeds remain in every comparison, nominal and
Holm-adjusted association results plus leave-one-seed-out stability are
required, and proxy quantities cannot be relabeled as measured waiting or cold-
start latency. A single actionable cause requires convergent QPR-component,
topology, state-association, advanced-baseline, and source-path evidence. Even a
positive diagnosis authorizes only a separate plan amendment and future
preregistration, not implementation or sampling. See
`G3_POSTFAIL_CLAIM_SCENE_DIAGNOSIS_PREREGISTRATION.md`.

G3 post-failure diagnosis implementation closure (2026-09-04): commit
`83c2a96` freezes the read-only analyzer and directed tests with SHA-256 values
`2a19a8a2...1f1d` and `0b2e07fd...3789`. The analyzer hard-binds the failed
G3-E0 selection hashes, revalidates the ready manifest and all 135 canonical
run receipts, reduces within-run streams to seed-level observations, refuses
to overwrite output, and preserves all five seeds. Python compilation and
format checks pass; the new tests pass 4/4, all G3 analysis tests pass 17/17,
and the frozen G3-E0 protocol tests pass 9/9. Exactly one invocation against
the unchanged D71--D75 canonical product is now authorized, writing only the
six preregistered files under the run root's `diagnosis` directory. New online
runs, candidate changes, formal execution, and plots remain blocked pending a
result audit. See `G3_POSTFAIL_DIAGNOSIS_IMPLEMENTATION_AUDIT.md`.

G3 post-failure analyzer correction preregistration (2026-09-04): the first
authorized diagnostic invocation stopped on the first active E0 run before
forming pairs, aggregates, associations, decisions, or output files. The
`diagnosis` directory remains absent and no simulator ran. Rust source and a
structure-only event check show that
`operational_equilibrium_selection.rounds` is the serialized per-round trace
list, not a numeric count. The sole correction is to require a list of objects,
use its length, retain numeric validation of `selected_non_o0_rounds`, enforce
that the count does not exceed the list length, and add positive/negative
tests. All scientific fields, metrics, tests, thresholds, runs, and hashes are
unchanged. A retry remains blocked until the correction is tested, audited,
and committed. See `G3_POSTFAIL_ANALYZER_CORRECTION_PREREGISTRATION.md`.

G3 post-failure analyzer correction closure (2026-09-04): commit `43988d1`
implements only the frozen structure correction. `selection.rounds` must now
be a list of objects, its length is the round count, and the separately emitted
numeric `selected_non_o0_rounds` cannot exceed that length. Analyzer/test
SHA-256 values are `eef3536c...e2bf` and `a9bf2ea4...fc3b`. Compilation and
formatting pass; all G3 analysis tests pass 18/18 and the unchanged G3-E0
protocol tests pass 9/9. The first failed invocation left the diagnostic output
directory absent, and no canonical input or simulator result changed. Exactly
one retry of the same read-only 135-run diagnosis is authorized; new sampling
and experiment progression remain blocked. See
`G3_POSTFAIL_ANALYZER_CORRECTION_AUDIT.md`.

G3 post-failure claim/scene diagnosis closure (2026-09-04): the successful
retry validated and reduced all 135 retained D71--D75 runs, yielding 60 exact
candidate/C0 pairs and 45 exact baseline/C0 pairs. The report document/file
SHA-256 values are `003cf898...284d9` and `1dc51c9d...0716`; all five CSV
products are retained under the run root's `diagnosis` directory. Status is
`complete_no_single_actionable_cause`: none of the five joint root-cause
conditions passed. High-load heterogeneous-minus-homogeneous log-QPR
difference-in-differences is positive for only 2/5 seeds for either E0
candidate, and intervention share has weak association with log-QPR change
(`rho=0.1199/0.0687`, Holm `p=1.0`). The advanced-baseline homogeneous-low
advantage is consistently a latency advantage: C0 is 1.1434 req/ms at 84.46 ms
and QPR 0.024900, while Hiku is 1.1514 at 54.47 ms and QPR 0.039986, and Jiagu
QPR is 0.040392. C1 lowers latency to 79.68 ms but trades away throughput and
cost, leaving QPR 28.45% below Jiagu. No new candidate, seed, formal cell, or
paper-ready group is authorized. The next admissible work is a separately
preregistered read-only latency-path/source comparison against the five
advanced baselines. See
`G3_POSTFAIL_CLAIM_SCENE_DIAGNOSIS_RESULT_AUDIT.md`.

G4 homogeneous-low latency-path diagnosis preregistration (2026-09-04): the
next read-only stage is frozen around the publication-blocking latency gap. It
uses exactly the 50 retained homogeneous-low D71--D75 runs for NSESche C0 and
all nine baselines, with FaaSRank-P, OCS, Hiku, Jiagu, and Orion as the declared
primary latency comparators. It will decompose every completed function into
schedule, cold-start, data, and execution boundaries; retain full-cohort and
common-completion request/function comparisons; reduce NSESche waiting,
feasibility, warm/starting, queue, data, pressure, and dispatch exposures; and
then perform a source-symbol inventory of the six primary schedulers. A unique
cause requires 4/5 seed consistency against at least three primary baselines,
largest-stage agreement, common-completion confirmation, a stable expected-
direction exposure association, and one source-mapped operational difference
outside Eqs. (1)--(20). No simulator, source change, candidate, or new seed is
authorized. See `G4_HOM_LOW_LATENCY_PATH_DIAGNOSIS_PREREGISTRATION.md`.

G4 homogeneous-low latency analyzer closure (2026-09-04): commit `99abf4e`
freezes the read-only stage/common-completion/exposure analyzer and its tests,
with SHA-256 values `733105bd...2656` and `7c4f4919...a6aa`. It hard-binds the
parent selection, revalidates the ready manifest and every canonical input,
requires exactly five C0 plus 45 baseline runs, preserves asymmetric completed
sets, and refuses output overwrite. Compilation/formatting pass, the new tests
pass 4/4, all G3/G4 analysis tests pass 22/22, and the unchanged G3-E0 protocol
tests pass 9/9. Exactly one read-only invocation on the 50 retained
homogeneous-low runs is authorized under `latency_diagnosis`; simulator runs,
source changes, new candidates/seeds, formal progression, and plots remain
blocked. See `G4_HOM_LOW_LATENCY_ANALYZER_AUDIT.md`.

G4 homogeneous-low latency/source diagnosis closure (2026-09-04): the single
authorized invocation completed over all 50 frozen homogeneous-low D71--D75
runs and retained all seeds, full cohorts, and common-completion cohorts. The
report document/file SHA-256 values are `d65feedb...49e` and
`1f58e404...56c5`. Cold-start wait is the strongest candidate stage: its
full-completed-function difference is positive in 5/5 seeds against every
primary comparator and is the largest positive stage against OCS, Hiku, Jiagu,
and Orion; starting-container mean versus cold-wait mean has `rho=0.90` with
all leave-one-seed-out signs positive. However, common-completion confirmation
passes only for Jiagu, so the preregistered unique-stage gate fails. Source
inspection shows that C0 strict Eq. (15) utility contains no warm/cold term and
does not activate the separate exact-tie warm rule, whereas several advanced
baselines rank container state directly. This is a plausible operational
difference, not causal attribution: retained traces do not yet distinguish
common-HPA warm-capacity absence from strict-utility warm-node bypass, and the
active G3-E0 envelope already failed its gates. Status remains
`complete_trace_no_unique_latency_stage`; no source change, new candidate,
seed, formal cell, plot, or paper claim is authorized. See
`G4_HOM_LOW_LATENCY_RESULT_AND_SOURCE_AUDIT.md`.

G5 lookahead/warm-path diagnosis preregistration (2026-09-04): before any
fourth operational candidate, one further read-only use of the same 50 retained
homogeneous-low D71--D75 runs is frozen to distinguish proactive DAG binding
from strict-utility warm-node bypass. Completed-function timing will measure
pre-ready placement lead, startup overlap, and post-ready cold wait in both full
and common-completion cohorts. C0 windows will account exactly for warm
availability, selected warm/starting/non-running state, bypass, utility
advantage, dispatch integrity, and same-frame completed-only cold events. A
lookahead signal requires consistent full/common evidence against at least
three of OCS/Hiku/Jiagu/Orion plus failure of the same-admission FaaSRank-P
control; warm bypass is dominant only if it explains at least half of non-warm
decisions in 4/5 seeds and the pooled total with adequate completed-only frame
coverage. Even a passing path can authorize only a separate candidate
preregistration, not implementation or sampling. See
`G5_LOOKAHEAD_WARM_PATH_DIAGNOSIS_PREREGISTRATION.md`.

G5 lookahead/warm-path analyzer closure (2026-09-04): commit `18e911e`
freezes the retained-data analyzer and directed tests with SHA-256 values
`34f31006...1acc` and `0c4435c1...0f31`. It hard-binds the closed G4 report,
failed G3-E0 selection, ready manifest, exact 50-run set, prior canonical
receipts, and seven-file source contract. C0 window accounting fails closed on
any assignment partition, warm availability/bypass, strict-utility, dispatch,
or completed-only join inconsistency. Python compilation and Black checks pass;
new G5 tests pass 5/5, combined G3--G5 tests pass 27/27, and live source-contract
validation passes. Exactly one invocation on the unchanged retained product is
authorized, writing only the five frozen products under
`lookahead_warm_diagnosis`. Simulator runs, source changes, new candidates or
seeds, formal progression, figures, and paper claims remain blocked pending a
result audit. See `G5_LOOKAHEAD_WARM_PATH_ANALYZER_AUDIT.md`.

G5 lookahead/warm-path result closure (2026-09-04): the single read-only
invocation retained all 50 homogeneous-low D71--D75 runs and completed with
status `complete_lookahead_candidate_preregistration_authorized`. Report
document/file SHA-256 values are `d99dbedf...911a` and `6ffa0e4e...44ca`.
NSESche C0 and the same-admission FaaSRank-P control have zero pre-ready binding,
lead, and startup overlap in every seed. OCS, Hiku, Jiagu, and Orion bind about
30.8--34.3% of completed functions early, with mean leads of 22.2--32.1 ms and
startup overlap of 3.73--7.89 ms. All four beat C0 on lead and overlap in 5/5
full-cohort and 5/5 common-completion pairs; positive overlap and positive C0
post-ready cold disadvantage co-occur in 5/5 seeds for each. Warm bypass is not
dominant: `B/N >= 0.5` in only 3/5 seeds, four seeds fail completed-only frame
coverage, and bypass-active cold-event rate is never higher than the inactive
rate. This supports only a separately preregistered strict-Eq.-(15)
`PreAllSched` candidate; it does not authorize implementation, sampling,
formal progression, figures, or paper claims. See
`G5_LOOKAHEAD_WARM_PATH_RESULT_AUDIT.md`.

G6 lookahead candidate/development preregistration (2026-09-04): the sole new
candidate is `lookahead_preall_sched`, which changes player admission from
parents-completed to parents-scheduled while leaving stable order, feasible
nodes, Eqs. (1)--(20), strict Eq. (15), initialization, convergence, offline
reference, price feedback, dispatch, HPA, cache, and all baselines unchanged.
Development is limited initially to five candidate-only homogeneous-low
D71--D75 replays using frozen tapes and existing C0/nine-baseline controls, with
five candidate-specific offline references. Every valid seed is retained. The
candidate must activate early binding in every seed, exceed Hiku's frozen
1.1514 throughput mean and Jiagu's 0.040391615 QPR mean, improve paired C0 with
the frozen sign counts, avoid any <80% per-seed regression, lower mean latency,
preserve completion, and stay within 3x C0 solve time. A pass can authorize only
candidate execution on development-disjoint Q61--Q80 tapes with frozen
baselines; a failure blocks confirmation and later cells. Implementation and
all sampling remain blocked pending separate tested audits. See
`G6_LOOKAHEAD_CANDIDATE_AND_DEVELOPMENT_PREREGISTRATION.md`.

G6 lookahead implementation closure (2026-09-04): commit `f554fd4` implements
only the preregistered `lookahead_preall_sched` admission change, reusing the
shared `PreAllSched` primitive while preserving stable order, feasible nodes,
Eqs. (1)--(20), strict Eq. (15), initialization, convergence, offline social
reference, price feedback, dispatch, HPA, cache, baselines, and metrics.  A new
reference tag/schema prevents reuse of prior candidate references and the run
config discloses `player_collection=parents_scheduled`.  Rust formatting and
Black checks pass; all 42 NSESche tests, 10 configuration tests, 40 reviewer-
protocol tests, and 27 G3--G5 analysis regressions pass.  The four source/test
SHA-256 receipts are frozen in `G6_LOOKAHEAD_IMPLEMENTATION_AUDIT.md`.  Only
G6 protocol/analyzer construction, release build, and zero-data freezing are
now authorized; reference construction, online simulation, confirmation,
figures, and paper claims remain blocked.

G6 lookahead protocol/analyzer closure (2026-09-04): commit `e414eb9` freezes
an exact five-run candidate-only D71--D75 product.  It hash-binds the failed G3
ready manifest/selection and exact 50 retained homogeneous-low controls,
requires five new candidate-specific offline references, and pairs only
identical workload tapes.  The analyzer checks schema-6 parent-scheduled
collection, strict Eqs. (1)--(20), offline-reference hits, complete dispatch,
completed-function activation in every seed, all frozen performance gates,
and run/seed-level mean, sample SD, paired 95% t intervals, sign counts, and
leave-one-seed-out results.  All 50 live source receipts revalidated.  New G6
tests pass 5/5, G2/G3/G6 protocol regressions 20/20, G3--G6 analysis regressions
32/32, and the complete generic protocol suite 40/40.  Release build and a
zero-data manifest freeze are authorized next; reference construction, online
simulation, Q61--Q80 confirmation, figures, and paper claims remain blocked.
See `G6_LOOKAHEAD_PROTOCOL_ANALYZER_AUDIT.md`.

G6 runtime/zero-data freeze (2026-09-04): release executable SHA-256
`90988e545679a04f46f680d6ac7e0e0a52d8e1335c2d0309e73d4383c3147611`
was built from commit `b43b5c7`.  Run root
`runs/tscv1_g6_lookahead_d71_d75_b43b5c7_20260904` contains exactly five
tape-bound candidate specifications for D71--D75, five new unbuilt reference
dependencies, and bindings to 50 unique retained G3 homogeneous-low controls.
All projected tapes exist and match their recorded hashes; the five new
reference keys do not overlap the G3 NSESche keys.  No reference-build or
online directory existed at freeze time.  Exactly these five offline
references may now be constructed; online sampling, result analysis,
Q61--Q80 confirmation, figures, and paper claims remain blocked.  See
`G6_LOOKAHEAD_PROTOCOL_RUNTIME_ZERO_DATA_FREEZE.md`.

G6 offline-reference closure (2026-09-04): all five predeclared D71--D75
candidate-specific reference builds passed on attempt 1 with process exit code
0, no timeout, the frozen release binary, and exact module-inventory restore.
Their tables contain 4,975 records and all table, receipt, and process hashes
revalidated after binding.  `g6.ready.json` has canonical hash
`d5b7a2143688f618a9ef286466d0c7c7a6b92687bb5bf97dab6e28ce9ca4c1f3`;
the online directory did not exist at audit time.  Exactly five manifest-order
candidate runs are now authorized.  Additional seeds, confirmation, figures,
and paper claims remain blocked.  See
`G6_LOOKAHEAD_REFERENCE_BINDING_AUDIT.md`.

G6 development result closure (2026-09-04): all five fixed D71--D75 online
runs passed QC on attempt 1 and remain retained.  The active
`lookahead_preall_sched` candidate failed its preregistered gate: mean
throughput 1.078400 and QPR 0.029572 did not exceed frozen best baselines
1.151400 and 0.040391615; paired wins were 3/5 throughput, 2/5 QPR, and 2/5
joint.  D73 violated both 80% C0 floors, and mean completion fell below C0.
Activation, latency, and solve-time gates passed, confirming a real but unsafe
early-binding effect rather than a dormant or computationally expensive
mechanism.  Confirmation and formal progression are blocked.  Only read-only
post-failure diagnosis may proceed before any new candidate is preregistered.
See `G6_LOOKAHEAD_DEVELOPMENT_RESULT_AUDIT.md`.

G7 candidate preregistration (2026-09-04): post-G6 read-only diagnosis shows
that unrestricted lookahead both reduces post-ready cold wait and creates a
large parent-blocked/resident queue.  Multi-hop cascade appears in every seed;
most pre-ready lead exceeds useful startup overlap.  Prior D66--D70 evidence
also shows positive homogeneous-low effects from warm initialization.  The sole
new candidate `lookahead_frontier1_warm_init` therefore admits at most one
executable-frontier hop and uses the previously defined warm feasible start,
then retains the unmodified strict Eq. (15) best-response loop.  It adaptively
reuses D71--D75 for exactly five candidate runs and five new references while
reusing all 50 G3 controls.  Gates remain stricter than the frozen best
throughput/QPR baselines and include one-hop reconstruction plus warm/overlap
activation.  Only implementation and protocol/analyzer construction are now
authorized; release, references, online runs, confirmation, figures, and paper
claims remain blocked.  See `G7_FRONTIER_WARM_CANDIDATE_PREREGISTRATION.md`.

G7 implementation/protocol closure (2026-09-04): commits `e5f8802`,
`c183c84`, `264cfec`, and `9c16366` add and audit only the preregistered
`lookahead_frontier1_warm_init` candidate.  The common `sim_run.rs` hash is
unchanged.  NSESche uses a fail-closed one-executable-frontier-hop predicate,
the registered running-warm feasible start, then unchanged strict Eq. (15)
best responses.  The analyzer independently reconstructs frontier depth from
the environment DAG and completed-function timings and requires positive
pre-ready/overlap/warm activation in every seed.  All 43 NSESche tests, 10
configuration tests, 45 G7/general protocol tests, 5 G6 regressions, and 6 G2
regressions passed.  See `G7_FRONTIER_WARM_IMPLEMENTATION_AUDIT.md` and
`G7_FRONTIER_WARM_PROTOCOL_ANALYZER_AUDIT.md`.

G7 runtime/zero-data freeze (2026-09-04): release executable SHA-256
`593f79671b7b8659b7df6ef2c2c240e74f409ed53c3956e4e2cfaca93e2918b7`
was built from commit `9c16366`.  Run root
`runs/tscv1_g7_frontier_warm_d71_d75_9c16366_20260904` contains exactly five
tape-bound D71--D75 candidate specifications, five unique unbuilt reference
dependencies, and bindings to 50 unique retained G3 homogeneous-low controls.
All five projected tapes match their live hashes; the new reference keys do
not overlap G3 or G6.  No reference-build or online directory existed at
freeze time.  Exactly these five offline references may now be built once in
manifest order; online runs, analysis, confirmation, later formal cells,
figures, and claims remain blocked.  See
`G7_FRONTIER_WARM_PROTOCOL_RUNTIME_ZERO_DATA_FREEZE.md`.

G7 offline-reference closure (2026-09-04): all five predeclared D71--D75
candidate-specific reference builds passed on attempt 1 with process exit code
0, no timeout or launch error, the frozen release binary, and exact module-
inventory restore. Their tables contain 4,939 records and all table, receipt,
process, state-pair, assignment-sequence, build-spec, and workload-tape hashes
revalidated after binding. `g7.ready.json` has canonical hash
`37f26c48f6a78779d62d42acbedd440774d716ffc6818623a196925d97b6f4ae`;
it validates as five development runs with `formal_results_eligible=false`.
The online directory did not exist at audit time. Exactly five manifest-order
candidate runs D71--D75 are now authorized. Additional seeds, confirmation,
later formal cells, figures, and paper claims remain blocked. See
`G7_FRONTIER_WARM_REFERENCE_BINDING_AUDIT.md`.

G7 first-analysis structural failure (2026-09-04): all five online D71--D75
runs passed QC on attempt 1 and remain canonical. The first frozen analyzer
invocation exited before output because 14 active windows across D72--D75 have
the runtime-consistent shape `reference_source=not_requested`, null state key,
and null reference. This is a real failure of the preregistered requirement
that every active window hit its offline table, not a value that may be
dropped. A reporting-only correction is frozen: count only this exact null
shape, add an explicit all-active-window reference-coverage condition that is
guaranteed to fail on the retained product, and continue to report all other
fixed gates; every malformed or mismatched shape remains fail closed. No
selection file was written and no simulator/reference rerun is authorized.
After implementation/test audit, exactly one analyzer retry on the unchanged
product is allowed. See
`G7_ANALYZER_REFERENCE_COVERAGE_CORRECTION_PREREGISTRATION.md`.

G7 analyzer coverage-correction closure (2026-09-04): only the G7 reporting
path and directed tests changed. Exact `offline_table` rows remain strict
hits; exact `not_requested`/null rows are now counted as unreferenced active
windows, and a new per-seed coverage condition requires zero such rows and
hits equal to all active windows. Consequently the retained 14-window deficit
is guaranteed to fail rather than abort or disappear. Malformed and alternate
reference shapes remain fail closed. Python compilation/Black pass; G7/G6
tests pass 10/10 and generic-protocol/G2 regressions pass 46/46. No selection
file or new simulator product was created. Exactly one corrected analysis of
the unchanged retained G7/G3 product is now authorized; all sampling,
confirmation, formal progression, figures, and claims remain blocked. See
`G7_ANALYZER_REFERENCE_COVERAGE_CORRECTION_AUDIT.md`.

G7 development result closure (2026-09-04): all five fixed D71--D75 online
runs passed QC on attempt 1 and remain retained. The corrected analyzer
returned `complete_g7_development_gate_failed`. Mean throughput was 1.058000
versus C0 1.143400 and frozen-best 1.151400; mean QPR was 0.021155059 versus
C0 0.024900429 and frozen-best 0.040391615. Paired throughput/QPR/joint wins
were only 2/5, 1/5, and 1/5; mean latency worsened by 15.6595 ms and completion
fell by 0.044859. Only activation and solve-time conditions passed. The
one-hop bound worked in all seeds (maximum depth 1, zero violations), and warm
initialization/overlap were active, but 14 of 4,953 active windows lacked the
required offline-table reference. Every leave-one-seed-out paired throughput
and QPR difference remains negative. G7 is closed; confirmation and formal
progression are blocked. Only a separately preregistered read-only G7/G6/C0/
warm-only diagnosis may precede any new candidate. See
`G7_FRONTIER_WARM_DEVELOPMENT_RESULT_AUDIT.md`.

Post-G7 master-plan V3 (2026-09-04): G7 remains closed and cannot enter
confirmation. The next and only active stage is a separately preregistered
read-only G7/G6/G3-C0/G2-warm attribution. If it supports separating the
mechanisms, the last allowed lookahead-family candidate is frontier-only with
ordinary strict utility initialization; it may be screened only under the
unchanged dual-metric, paired, safety, completion, latency, runtime, frontier,
dispatch, and all-active-window reference gates. A passing candidate must use
fresh Q81--Q100 and all ten methods for independent homogeneous-low
confirmation before the ordered old-paper rerun begins. Old PDF bars remain
alignment anchors rather than result targets; seed filtering and result-
conditioned reruns remain prohibited. Reviewer additions then reuse formal
logs for convergence/reference/features and separately add only burst, QoS,
pricing/welfare, proportional scaling, and 300 exact-small states. See
`TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V3.md`.

G8 frontier-only attribution preregistration (2026-09-04): before any final
lookahead-family candidate, one read-only diagnosis is frozen over exactly 25
retained runs and 20 valid within-bank/same-tape pairs: G2 C0/warm-init,
G3 C0, G6 unrestricted lookahead, and G7 bounded-frontier/warm-init. Raw rows
cover outcomes, queues, solver termination, reference coverage, warm choices,
completed-function activation, and reconstructed frontier depth; each contrast
reports five values, mean/SD/paired t interval/signs/leave-one-out. G8
preregistration requires all frozen frontier-control and warm-path-separation
conditions, including majority queue reductions, all-seed one-hop integrity,
all-seed lower-utility warm perturbation, majority G7-vs-G6 dual-metric losses,
and worse reference coverage. G2 is directional context only and is never
pooled with D71--D75. Implementation/tests and one later read-only invocation
are authorized; scheduler changes, sampling, confirmation, figures, and claims
remain blocked. See `G8_FRONTIER_ONLY_ATTRIBUTION_PREREGISTRATION.md`.

G8 attribution analyzer closure (2026-09-04): the fail-closed analyzer now
admits exactly 25 frozen canonical runs and 20 within-bank/same-tape pairs,
retains all raw values, and reports cohort and paired mean/SD, descriptive
95% t intervals, signs, ratios, and every leave-one-seed-out mean. Canonical
audit inventories, runtime streams, dispatch partitions, exact reference
shapes, completed-function frontier reconstruction, all eight frozen input
products, and seven code-source receipts are validated before analysis. Black
and compilation passed; 6/6 directed tests and 31/31 combined G2/G3/G6/G7/G8
regressions passed. The one permitted source-contract dry validation found 25
unique runs and 20 exact pairs while leaving the output directory absent.
Commit this audit before the one authorized real read-only invocation. All
scheduler changes and sampling remain blocked. See
`G8_FRONTIER_ONLY_ATTRIBUTION_ANALYZER_AUDIT.md`.

G8 frontier-only attribution result closure (2026-09-04): the one authorized
read-only invocation completed over all 25 runs and 20 exact pairs with valid
document/CSV/input/code/canonical receipts. Six of seven frozen conditions
passed: G7 enforced one-hop depth with zero violations; G6 was deeper than one
hop in 5/5 seeds; G7 reduced parent-blocked and resident queues in 5/5; the
warm/lower-utility perturbation appeared in 5/5; and its 14 exact
`not_requested` windows exceeded G6 in 4/5. B2 failed. G7 minus G6 mean
throughput was -0.0204 but G7 lost throughput only 2/5, not the required 3/5;
mean QPR was -0.008417174 with losses in 5/5. The throughput direction is
seed-sensitive, so warm initialization is not isolated as a consistent
dual-metric regression cause. Status is `complete_no_g8_authorized`; G8 and
all new/confirmation/formal sampling are blocked, and the lookahead-family
search is closed. Next work is limited to a separately frozen retained-product
claim/scene feasibility audit and revised plan. See
`G8_FRONTIER_ONLY_ATTRIBUTION_RESULT_AUDIT.md`.

Post-G8 claim/scene feasibility preregistration (2026-09-04): with G8 rejected
and local mechanism search closed, the next audit is frozen over validated G1
formal Q61--Q80, G2, G3, G8, B0, and legacy-provenance products. It will test
whether any already implemented equation-preserving noncontrol candidate
strictly clears all nine homogeneous-low baselines, improves its own C0 across
at least 5/6 cells, has robust paired/leave-one-out margins, avoids 90% floors,
and has no integrity failure. Six-cell candidate evidence cannot be confused
with an all-baseline scene: only homogeneous-low has a current-protocol full
comparison. If no candidate passes, no confirmation or new mechanism follows;
V4 must use a paper-faithful claim reduction or halt the performance-centered
route. Old bars remain provenance anchors only. Analyzer/test construction is
authorized; all implementation and sampling stay blocked. See
`POST_G8_CLAIM_SCENE_FEASIBILITY_PREREGISTRATION.md`.

Post-G8 claim/scene analyzer closure (2026-09-04): the analyzer now validates
all eight frozen inputs, the separate 135-row G2 and G3 matrices, and the
complete 200-row formal homogeneous-low product. It reports five-/twenty-seed
raw summaries, paired differences and intervals, all leave-one-out means,
nine-baseline margins, formal ranks, and explicit labels for the five scenes
without a current all-baseline matrix. The six-condition candidate gate and
deterministic simplicity tie-break are frozen; all action authorization flags
remain false. Black/compilation, 3 directed tests, 24 combined G8/G2/G3
regressions, and diff checks passed. The output directory is absent. Commit
this audit before the one allowed retained-product invocation. See
`POST_G8_CLAIM_SCENE_ANALYZER_AUDIT.md`.

Post-G8 claim/scene result closure (2026-09-04): the one authorized invocation
validated 270 development and 200 formal rows and produced 36 candidate-cell,
36 homogeneous-low baseline-pair, and ten formal method summaries. No existing
candidate passed. G2 warm-init was strongest but improved both primary means
in only 4/6 cells and had a worst C0 ratio 0.8574; every G2/G3 noncontrol
failed homogeneous-low dual leadership, near-leader paired wins, 90% floors,
all-positive leave-one-out margins, and the 5/6 consistency gate. In formal
Q61--Q80, NSESche ranks 3rd in throughput (-1.04% versus FaaSRank; paired CI
crosses zero) and 4th in QPR (-9.26%; paired 95% descriptive CI
[-0.0105011,-0.0013635]). The scene label is `not_leading`; the other five
scenes lack current-protocol all-baseline results. No candidate confirmation,
implementation, or sampling is authorized. V4 must freeze a paper-faithful
claim-reduction route, or declare the performance-centered resubmission blocked
on genuinely new research. See
`POST_G8_CLAIM_SCENE_FEASIBILITY_RESULT_AUDIT.md`.

Post-G8 master-plan V4 (2026-09-04): V3 is superseded. The evidence does not
support any existing candidate confirmation or a promise of universal
throughput/QPR leadership. The final paper-faithful method is therefore
`ready_order` at the corrected-runtime Q61--Q80 semantics; unsupported
superiority wording must be removed before more data are collected. The first
ordered cell is the already complete 200-run homogeneous-low product and must
not be rerun. Next priority is reviewer-facing convergence/overhead and offline
reference extraction from those logs plus a separately preregistered 300-state
exact PoA/reference validation. Only after those integrity/mechanism gates may
the remaining old-paper cells proceed in order: homogeneous middle/high,
parameter/ablation, heterogeneous low/middle/high, then proportional scaling.
Burst, QoS, and pricing/welfare comparators are late, separately gated blocks;
native/fault/extra-stress/soak remain excluded. The maximum new online budget
is 3,560, but no block is authorized en masse. If universal dual-metric first
place remains mandatory, experiments pause and a separate new-algorithm
research project is required. See `TSC_RESUBMISSION_BEST_EXPERIMENT_PLAN_V4.md`.

P0 claim/runtime closure (2026-09-04): the raw review was normalized into 13
atomic issues and the submitted PDF into 31 material claims. Universal
throughput/QPR leadership, the old 55.4%/74.3% values, physical-cluster
wording, unconditional outer convergence, and exact-large-state reference
language are now prohibited by the claim contract. Every reviewer issue maps
to a writing, retained-log, P2, or P3 evidence block. The preserved
`98f822cf` executable exists and independently matches SHA-256
`7f1d1ad8...06a4`; current HEAD is not source-equivalent and is not authorized
as a replacement. All 20 formal NSESche Q61--Q80 logs contain the required
convergence, reference, scheduler timing, process CPU/RSS, and request streams,
so P1 needs no replay. The sole next stage is a frozen P1 retained-log analysis
plus 300-state exact-small reference/PNE/PoA protocol. See
`P0_CLAIM_RUNTIME_AUDIT_RESULT.md`, `P0_READY_ORDER_RUNTIME_TELEMETRY_AUDIT.md`,
and `rebuttal/`.

P1 retained/exact-small preregistration and implementation freeze (2026-09-04):
P1 is split into a zero-replay retained-log block and 300 constructed exact
small games. Q61--Q80 and all 120 existing offline references are included
without value-dependent selection; convergence has no favorable threshold.
The exact population is fixed at 3 nodes, 4/6/8 players, 100 states per size,
and seed `NSE-P1-EXACT-V2`. V2 removes legacy `existing_impact`, uses a shared
state quality weight, enumerates every assignment/PNE, verifies the weighted
potential identity, reports `ready_order` termination separately from
worst-PNE PoA, and measures the frozen offline estimator against exact optima.
An independent verifier reimplements the exact path without importing the
primary solver. Eight directed tests pass; the correctly rooted full suite
passes 304/304. Both output roots remain absent. Commit the frozen source
hashes before the one authorized P1-A invocation. See
`P1_RETAINED_AND_EXACT_SMALL_PREREGISTRATION.md` and
`P1_ANALYZER_AND_EXACT_SMALL_IMPLEMENTATION_AUDIT.md`.

P1-A fail-before-output validator correction (2026-09-04): the first retained
analysis command stopped on Q61 before creating its registered output root.
The analyzer had omitted logged `pricing.network_beta` when recomputing the
Eq. (19)--(20) next-round multiplier (`1 + gamma * beta * gap`). A read-only
scan identified 14 valid applied-feedback records affected by this omission;
no metric table or result was generated. The corrected analyzer requires and
uses the finite logged beta, records its own source hash, and passes three
directed tests including a beta=1.5 fixture. One same-command retry is
authorized after commit; the population, definitions, and thresholds remain
unchanged. See `P1_A_EQ19_BETA_VALIDATION_CORRECTION_AUDIT.md`.

P1-A second fail-before-output validator correction (2026-09-04): the retry
again stopped before creating its output root because three Q61 below-current
reference rounds correctly had no eligible feedback and logged null gamma,
gap, and next multiplier. The validator had required gamma on every trace row.
It now requires gamma only for an applied update while preserving finiteness,
Eq. (16), and full `1 + gamma * network_beta * gap` checks when fields apply.
Four directed tests pass, including the null non-applied boundary. One
same-command retry is authorized after commit; inputs, inclusion, statistics,
and thresholds are unchanged. See
`P1_A_NULL_GAMMA_VALIDATION_CORRECTION_AUDIT.md`.

P1-A retained-evidence result closure (2026-09-04): the successful invocation
validated all 20 Q61--Q80 NSESche runs and all 120 reference builds. Across
19,509 active windows, inner stability was 100%, outer stability 97.396%,
nonconvergence 2.604%, limit hits 0.0461%, and oscillations zero. The 508
nonconverged windows are exactly 499 below-current heuristic references plus
nine outer caps. All active windows had a positive offline-table value, with
no missing/unavailable/zero/negative online reference; 499 (2.558%) were below
current welfare and explicitly classified search-suboptimal. Mean seed-level
solve/lookup/policy-wall costs were 27.435 us, 14.202 us, and 0.348 ms. The 120
tables contain 117,138 rows and required 1,794.156 wall seconds to build.
P1-A passes its structural gate without a favorable-rate condition. P1-B is
authorized once; P2 remains blocked. See
`P1_A_RETAINED_EVIDENCE_RESULT_AUDIT.md`.

P1-B exact-small result closure (2026-09-04): the generator, exhaustive
primary enumerator, and independent verifier were each invoked exactly once
over the frozen 300-state V2 population. Coverage is exactly 100 states at
each of 4, 6, and 8 players and 737,100 feasible assignments in total. All
300 states have at least one PNE, all weighted-potential identities pass, and
the independent raw-dictionary solver exactly matches the primary results.
`ready_order` terminates stable at a PNE in 300/300 states. Exact worst-PNE
PoA has median 1.002848, p95 1.010731, and maximum 1.018114; this is an
empirical finite-population result, not a universal bound. The offline
reference exactly hits 192/300 optima and has zero median, 0.0935% p95, and
0.2008% maximum normalized shortfall, earning the preregistered
`accurate_small_state_reference` label. P1 is closed and P2 is authorized
only through a separately frozen homogeneous-middle/high protocol in V4
order; no later block or value-conditioned selection is authorized. See
`P1_B_EXACT_SMALL_RESULT_AUDIT.md`.

P2 homogeneous-middle claim-reframed preregistration (2026-09-04): P1-A and
P1-B both pass, including all exact-small hard gates and the highest
`accurate_small_state_reference` label. V4 therefore opens a new protocol for
the first previously unexecuted online cell without overwriting the retained
Q61--Q80 homogeneous-low result. The population is exactly the existing 20
middle/homogeneous tapes x ten methods x Q61--Q80 = 200 runs, using the same
`98f822cf` binary and the 20 already-built NSESche references. All first
QC-valid rows are retained. Statistics, the one-family 18-comparison Holm
rule, old-PDF diagnostic, and the V4 bottom-half/paired-interval stop gate are
frozen before outcome exposure. Only implementation, tests, and an immutable
selection receipt are currently authorized; online middle execution remains
blocked until their zero-result audit is committed. See
`P2_HOMOGENEOUS_MIDDLE_PREREGISTRATION.md`.

P2 homogeneous-middle zero-result implementation closure (2026-09-04): the
result-blind selector froze exactly ten methods x Q61--Q80 = 200 unique runs,
20 paired tape receipts, 20 complete NSESche reference receipts, the preserved
`98f822cf` runtime, and the frozen FaaSRank model. Selection file/document
SHA-256 values are `3d72f9fd...b2d04` and `6f6a8682...a0a18`. The analyzer
rechecks the run-level QPR identity, writes five-metric run summaries, performs
the preregistered 18 paired comparisons with one Holm family, and implements
the exact V4 bottom-half/fifth-place BCa stop rule. The old Fig. 6 page-9
coordinates and axis conversions were frozen only for a +/-15% whole-scene
provenance diagnostic. The publication diagnostic shows all run points and
BCa intervals in vector PDF/SVG and 900-dpi PNG with shape-plus-color encoding.
All focused tests pass; complete protocol, analysis, and figure suites pass
209/209, 92/92, and 1/1 (302/302 total), and the registered online root is
still absent. After commit, the exact 200-run selection is authorized once;
all other online blocks remain closed. See
`P2_HOMOGENEOUS_MIDDLE_IMPLEMENTATION_AUDIT.md`.

P2 homogeneous-middle result closure (2026-09-04): the one frozen invocation
canonicalized all 200 runs without a block; result-blind reconciliation found
200 exact paths and zero repairs/re-executions, pairing passed for all 20
seeds, and one runtime identity was used. The cell is formal-complete but not
paper-ready. Five QC-valid Q71 rows (Greedy, Load Balance, OCS, Hiku, NSESche)
had zero throughput/completion, making QPR correctly undefined; Q71 itself has
2,459 hash-paired arrivals and five other methods complete requests, so this is
not a technical retry case. NSESche ranks 5th in throughput (mean 0.59750;
leader Load Balance 0.67970; paired difference CI [-0.21673,0.00720]) and 8th
in applicable QPR (0.006368; leader Hiku 0.012127; paired difference CI
[-0.022539,-0.000047]). No comparison survives the 18-test Holm family. Old
Fig. 6 alignment triggers in 34/40 cells, showing broad scene drift. The
preregistered figure correctly refused to hide incomplete QPR and wrote no
output. High and every later online block remain closed. The full 3,009-file,
285,034,689-byte workspace is mirrored on E with exact tree hash
`b20256c3...aded7f`. See `P2_HOMOGENEOUS_MIDDLE_RESULT_AUDIT.md`.

G9 request-backpressure implementation/protocol closure (2026-09-04): source
commit `d5241f9` implements only the preregistered oldest-first request cohort
of size at most the configured node count while retaining deferred requests
and preserving strict Eq. (15) within the cohort. Operational schema 8,
reference tag 13, cohort/dispatch telemetry, and fail-closed runtime checks are
present. The release binary is 4,820,992 bytes with SHA-256
`5f41999c...5330`. The zero-result manifest freezes exactly five methods x
three loads x D81--D85 = 75 runs, 15 paired tape identities, and 30 distinct
NSESche references; its file SHA-256 is `fad2a3bb...5192`, and the run root
contains no other file. Directed G9 tests pass 5/5 and the complete protocol
suite passes 214/214. After the audit commit, only staged construction and
one result-blind execution of this product are authorized. D86--D95,
Q61--Q80 formal replay, figures, and performance claims remain blocked. See
`G9_REQUEST_BACKPRESSURE_IMPLEMENTATION_PROTOCOL_AUDIT.md`.

G9 tape/input-binding closure (2026-09-04): all 15 fixed D81--D85 base tapes
canonicalized on attempt 1 with no partial or quarantine artifact. The 210-file
canonical capture tree contains 59,140,916 bytes and has inventory hash
`f382b03e...42e0`; all tape hashes and 56,785 arrival events were independently
verified. The final 75-run manifest binds those 15 tape hashes and the one
previously calibrated FaaSRank model (`4853fffa...f17e`) while retaining 30
distinct reference dependencies. A pre-outcome G9 validator defect that made
the authorized model-binding stage unreachable was corrected by allowing only
a Boolean binding-stage flag; generic validation still rejects an incomplete
`true` binding. Directed tests pass 6/6 and the actual bound manifest validates.
No G9/control/baseline outcome or offline reference existed at correction time.
After commit, only the exact 30 reference builds are authorized; online runs
and all later stages remain blocked. See
`G9_REQUEST_BACKPRESSURE_INPUT_BINDING_AUDIT.md`.

G9 offline-reference closure (2026-09-04): all 30 preregistered references
canonicalized on attempt 1 with no remaining partial or quarantine artifact.
The 420-file canonical tree contains 265,351,044 bytes and has inventory hash
`b91c61ba...54a3`. Independent inspection verified every table/catalog/receipt
hash and row count: 30 distinct tables, 18,715 total reference-state rows, and
both operational identities represented. The final reference-bound 75-run
manifest passes complete validation; its file SHA-256 is `8ccf6831...10bb`,
and all 30 NSESche rows have unique bound reference hashes. No online workspace
or performance outcome existed. After commit, only result-free construction
and freeze of the ten-gate G9 analyzer/selector are authorized; online
execution and all later stages remain blocked. See
`G9_REQUEST_BACKPRESSURE_OFFLINE_REFERENCE_AUDIT.md`.

G9 analyzer/selection zero-result closure (2026-09-04): commit `1cebbd3`
freezes a fail-closed ten-condition analyzer before any G9 online workspace
exists. The selector independently rehashed the runtime, all 15 tapes, and all
30 NSESche references, then fixed exactly five methods x three loads x
D81--D85 = 75 unique run specifications with no result-conditioned choice.
Selection file/document SHA-256 values are `053e9bd5...95153` and
`2e971ede...2e583`; it also binds analyzer source SHA-256
`2b055dfe...638a`. The gate retains scientific failures and zero-completion
rows with null QPR, reports all paired differences/wins/ratios and
leave-one-seed-out means, and cannot weaken any threshold. Focused tests pass
12/12 and the complete analysis suite passes 98/98. After this audit commit,
one result-blind execution of the exact 75-run selection is authorized;
D86--D95, formal replay, figures, and claims remain blocked unless all ten
conditions pass. See `G9_REQUEST_BACKPRESSURE_ANALYZER_SELECTION_AUDIT.md`.

G9 request-backpressure result closure (2026-09-04): the one authorized
result-blind execution canonicalized all 75 selected runs on attempt 1 with no
quarantine; all paths were exact and reconciliation performed zero repairs.
All 75 rows are QC-valid with positive completion and defined QPR, but the
candidate fails 6/10 frozen conditions. It ranks 5/5 in both throughput and
QPR at every load. Versus `ready_order`, mean throughput changes are -90.54%,
-72.88%, and -88.18%; QPR changes are -99.70%, -97.87%, and -98.04%. The
fixed 20-request cohort correctly activates in 15/15 runs and passes overhead,
but dependency blocking leaves only about 0.24--3.24 schedulable players per
window in individual runs while thousands of ready players can exist outside
the cohort. This is a decisive non-work-conserving mechanism failure, not a
technical retry case. Candidate integrity passes 15/15; three control runs
contain four separately retained strict-PNE/nonpositive-reference exceptions,
and all 75 runtime identities agree. D86--D95 and all formal use are blocked.
The complete 1,768-file, 461,180,190-byte run root is mirrored on E with tree
SHA-256 `f5892e6e...cb1c`. The permanent root-level closed-experiment package
contains 28 files and 7,834,737 bytes with full tree hash
`2fb554b4...2bc3` and payload-inventory hash `fc4e3820...8620`. After the
closure commit, only diagnosis and a separately preregistered fresh-seed,
work-conserving mechanism study may proceed. See
`G9_REQUEST_BACKPRESSURE_RESULT_AUDIT.md` and
`closed-experiments/G9_request_backpressure_development_gate_failed/`.

G10 work-conserving remaining-work preregistration (2026-09-04): G9's fixed
request cohort is permanently rejected. A fresh D96--D100 homogeneous
development family is now frozen before implementation or outcome generation.
C1 retains the exact dependency-ready game but orders requests by ascending
unfinished DAG functions; C2 adds only a globally node-count-bounded one-hop
frontier while admitting every ready player first. Both preserve Eqs. (1)--
(20), strict Eq. (15), the PNE definition, and the weighted-potential finite-
improvement argument. The first stage is exactly C0/C1/C2 x three loads x five
paired seeds = 45 online runs after 15 tapes and 45 mode-specific references.
All QC-valid observations are retained. A candidate must improve both mean
throughput and mean QPR over C0 at every load, pass paired/leave-one-out/safety,
latency/completion, integrity, activation, and overhead gates before any
strong-baseline addendum can be written. At this checkpoint only source,
tests, compilation, and an implementation audit are authorized; no D96 tape,
reference, online run, confirmation, formal figure, or manuscript claim is
authorized. See `G10_WORK_CONSERVING_REMAINING_WORK_PREREGISTRATION.md`.

G10 implementation/runtime closure (2026-09-04): source commit `ab0ae94`
implements the frozen C1 remaining-work order and C2 all-ready-first, globally
node-count-bounded one-hop frontier without changing the manuscript utility,
strict Eq. (15), Eq. (19), QPR, or offline-reference definitions. Operational
schema 9, unique reference tags 14/15, comparable C0/C1 ready-set hashes,
frontier/dispatch invariants, and fail-closed runtime validation are present.
The sole protected release binary is 4,869,120 bytes with SHA-256
`39d56c1b...12e8`. NSESche and config tests pass 50/50 and 10/10; complete
protocol and analysis regressions pass 219/219 and 98/98. The unfiltered Rust
suite is transparently 127/129 because of one existing thread-timing assertion
and one default-Python NumPy dependency failure, neither in the G10 path. No
G10 run root, D96--D100 input, reference, online metric, throughput, or QPR
exists. After this audit commit only construction of the zero-result G10
protocol/manifest is authorized; tape capture and every result-bearing stage
remain blocked. See
`G10_WORK_CONSERVING_REMAINING_WORK_IMPLEMENTATION_AUDIT.md`.

G10 zero-result protocol/manifest closure (2026-09-04): protocol commit
`a3a31d5` freezes exactly C0/C1/C2 x low/middle/high x D96--D100 = 45
homogeneous 20-node run specifications, 15 shared tape identities, and 45
mode-specific offline-reference dependencies. The manifest file is 1,089,366
bytes with SHA-256 `e1811128...3e77`; its embedded object hash is
`4847961a...4b04`, and its run root contains only that file with no stages or
outcomes. The schema reconstructs the exact Cartesian product and rejects
seed/gate/method/reference/tape/runtime drift or early strong baselines. D100
required a result-free structural regex correction from two to two-or-three
digits; G10 remains locked to the exact five-seed set. Directed tests pass 9/9,
combined G10/G9 tests 14/14, and the complete protocol suite 224/224. After
the audit commit only the exact 15 tape captures are authorized; references,
online execution, analyzer selection, strong baselines, confirmation, formal
replay, figures, and claims remain blocked. See
`G10_WORK_CONSERVING_PROTOCOL_MANIFEST_AUDIT.md`.

G10 tape/input-binding closure (2026-09-04): all 15 frozen D96--D100 base
tapes canonicalized on attempt 1 with no partial or quarantine file. Independent
streaming inspection verified every tape hash, seed, event count, DAG order,
frame range, and capture receipt. The 210-file canonical tree contains
60,211,642 bytes with inventory hash `6152feb5...8ce6`; the capture ledger hash
is `f012217d...1c65`. Retained arrivals total 56,975: 9,589 low, 12,532 middle,
and 34,854 high. The final tape-bound manifest validates with 45 runs, 15 tape
hashes, 15 exact three-arm groups, and 45 distinct mode-specific references;
its file SHA-256 is `4861a5b8...607d`. No reference or online directory exists.
After this audit commit only the exact 45 offline-reference builds are
authorized; online execution and every later result-bearing stage remain
blocked. See `G10_WORK_CONSERVING_TAPE_INPUT_AUDIT.md`.

G10 offline-reference closure (2026-09-04): all 45 frozen candidate-load-seed
reference builds canonicalized on attempt 1 with no partial file. Independent
streaming verification rehashed each table, receipt, process observation,
run configuration, welfare observation, and summary and confirmed the exact
C0/C1/C2 x low/middle/high x D96--D100 Cartesian product. The 630-file,
455,388,235-byte canonical tree has inventory hash `e455ec57...ad18`; its 45
unique tables retain all 44,044 rows, including one valid negative-valued row.
The reference catalog file SHA-256 is `9af4338c...6c2f`; the final 45-run
reference-bound manifest validates with 15 tape hashes, 45 reference hashes,
no online results, and file SHA-256 `804cf98c...8921`. After this audit commit,
only result-free G10 analyzer and exact selection freezing are authorized.
Online execution and every later result-bearing stage remain blocked. See
`G10_WORK_CONSERVING_OFFLINE_REFERENCE_AUDIT.md`.

G10 analyzer/selection zero-result closure (2026-09-04): a hash-bound,
fail-closed nine-condition analyzer is frozen before the online parent exists.
Its source is 59,675 bytes with SHA-256 `45ada143...8884`; focused tests pass
11/11 and the complete analysis suite passes 109/109. The exact manifest-order
selection contains C0/C1/C2 x low/middle/high x D96--D100, 45 unique run/spec
identities, 15 tape hashes, and 45 reference hashes. Its file SHA-256 is
`722eadb7...31e3` and canonical document hash is `e8cfa0e3...4aac`. The gate
retains zero-completion/null-QPR and adverse rows; reports signed paired
effects, ratios, wins, SDs, intervals, leave-one-out means, QPR factorization,
activation, PNE/reference/runtime, and overhead; and cannot weaken thresholds.
After this audit commit, exactly one result-blind execution of all 45 selected
runs is authorized. Strong baselines, confirmation, formal replay, figures,
and claims remain blocked pending the corresponding gates. See
`G10_WORK_CONSERVING_ANALYZER_SELECTION_AUDIT.md`.

G10 work-conserving result closure (2026-09-04): all 45 selected D96--D100
runs canonicalized on attempt 1, all are QC-valid with positive completion and
defined QPR, and reconciliation repaired zero paths. Neither candidate passes.
C1 throughput/QPR mean ratios are 1.0009/0.9772 low, 1.0061/1.0071 middle,
and 1.0265/1.0450 high; its middle-D100 floor is 0.7791/0.5915. C2 ratios are
0.9839/1.0045 low, 0.9934/1.0444 middle, and 1.2340/1.5966 high; its middle-D96
floor is 0.7037/0.3559. C2 activates in 5/5 seeds per load with zero frontier
or ready-work violations, showing a real but non-robust high-pressure benefit.
The frozen analyzer conservatively mislabels C0's intentionally null remaining-
work range; it remains unchanged, and the conclusion is invariant because C0
also has one genuine inner-limit/non-reference window and one nonpositive-
reference window, while both candidates separately fail multiple performance
gates. The 675-file online canonical tree hash is `ed066974...997e`; the full
1,527-file, 566,678,494-byte run root is mirrored exactly on E with hash
`aed84ef9...4ff9`. Strong baselines, confirmation, formal replay, figures, and
claims are blocked. Only a read-only fresh-successor diagnosis is authorized.
See `G10_WORK_CONSERVING_RESULT_AUDIT.md`.

The permanent root-level G10 closure package contains 27 hash-enumerated
payload files (7,797,197 bytes) plus its inventory receipt. Its payload hash is
`2bd7aaf0...fdb5`; the complete 28-file tree is 7,801,839 bytes with hash
`45bdb9b1...785a`. See
`closed-experiments/G10_work_conserving_development_gate_failed/`.

G11 state-regime diagnosis preregistration (2026-09-04): before inspecting
run-level pressure distributions or correlations, freeze a read-only analysis
of all retained G10 runs. The independent unit remains run/seed. Pre-decision
ready, pending, waiting, and frontier counts are aggregated within run; all
paired throughput/QPR/latency/cost/completion outcomes and all fixed features
are reported. Exactly four load-blind ready-saturation thresholds (1x, 2x, 4x,
8x node count) are evaluated as training diagnostics. A successor is admitted
only if one threshold attains balanced accuracy >=0.70 with sensitivity and
specificity >=0.60, benefits move coherently with saturation, and leave-one-
seed-out results do not depend on a single seed. No implementation, fresh
input, online run, strong baseline, confirmation, or formal result is yet
authorized. See `G11_STATE_REGIME_DIAGNOSIS_PREREGISTRATION.md`.

G11 state-regime diagnosis result closure (2026-09-04): the read-only analyzer
reproduced all 45 retained G10 runs and emitted 45 run-feature rows, 30 paired
outcome rows, 82 C2 features, and all 410 fixed feature/outcome correlations.
C2 integrity passes in all 15 runs and the selected 1x saturation feature has
positive full and leave-one-seed-out associations with both log-throughput and
log-QPR. The successor path nevertheless fails its decisive fixed classifier
gate: best balanced accuracy is only 0.55 (sensitivity 0.60, specificity 0.50),
and its five leave-one-seed-out values range from 0.4375 to 0.6250; the 2x, 4x,
and 8x thresholds detect no favorable run. The report retains all five jointly
favorable and ten unfavorable C2 runs, including the large but non-robust high-
load gains. Its file/document SHA-256 values are `54f4d540...241db1` and
`1eae2392...77a67`; the five-file, 515,832-byte output and its E-drive mirror
share inventory hash `7b62785b...fac2`. G11 implementation/sampling, strong
baselines, confirmation, formal replay, figures, and claims are blocked. The
remaining-work/frontier/ready-count family is closed; the main ordered gate
still requires either a genuinely new research contribution or an explicit
claim-contract revision. See `G11_STATE_REGIME_DIAGNOSIS_RESULT_AUDIT.md`.

G12 global-ready player-admission preregistration (2026-09-04): after G11
closed the remaining-work/frontier/ready-threshold family, source inspection
identified the unbounded command-release boundary as a distinct mechanism
target. C0 presently solves and dispatches every feasible dependency-ready
player in one window, irrevocably binding burst work into unbounded node
queues. G12 fixes exactly one load-blind candidate: collect and feasibility-
filter the complete global C0 ready sequence, then admit only its first
`min(ready,N)` players in the unchanged arrival/request/topology/function
order. This avoids G9's request-cohort dependency blocking and uses no frontier,
warm override, remaining-work key, outcome, or tunable threshold. Eqs. (1)--
(20), strict Eq. (15), Eq. (19), QPR, and offline-reference definitions remain
unchanged on the admitted finite player set. If implementation and later zero-
result stages pass, the frozen development product is C0/G12 x three loads x
D101--D105 = 30 paired runs. At this checkpoint only source, tests, compilation,
and an implementation audit are authorized. See
`G12_GLOBAL_READY_PLAYER_ADMISSION_PREREGISTRATION.md`.

G12 global-ready player-admission implementation closure (2026-09-04): source
commit `c4e31a9` implements the exact post-feasibility prefix of at most the
configured node count from the complete global C0 ready order. Deferred work
remains unplaced; there is no request cohort, remaining-work key, frontier,
lookahead, warm override, load/seed/outcome branch, or tunable threshold. The
runtime fails closed on readiness, feasibility, legacy-order, prefix, bound,
solver-set, or prepared-dispatch mismatch and logs order-sensitive hashes and
all admission counts. Eqs. (1)--(20), strict Eq. (15), Eq. (19), QPR, and the
offline-reference algorithm are unchanged. Reference-key schema 11,
operational schema 10, and reference tag 16 isolate the candidate. The sole
release binary is 4,871,168 bytes with SHA-256 `35e7e3d2...4f27`. G12 core,
NSESche, configuration, and complete protocol tests pass 2/2, 52/52, 10/10,
and 224/224. The unfiltered Rust suite retains only its two known unrelated
failures (129/131). No G12 run root, tape, reference, or outcome exists. After
the audit commit, only zero-result protocol/manifest construction is
authorized. See `G12_GLOBAL_READY_PLAYER_ADMISSION_IMPLEMENTATION_AUDIT.md`.

G12 zero-result protocol and manifest closure (2026-09-04): protocol commit
`9b48415` freezes C0 `ready_order` versus
`ready_global_player_admission_n` on homogeneous 20-node low/middle/high x
D101--D105. The sole unbound manifest contains 30 unique run/spec identities,
15 tape identities shared only within load/seed pairs, and 30 distinct
mode-specific reference identities. It binds runtime source `c4e31a9`, the
4,871,168-byte release binary (`35e7e3d2...4f27`), operational schema 10,
reference-key schema 11, and tags 1/16. The file SHA-256 is
`cb14ab22...fc7d`; its canonical document hash is `811f62e6...d6fee`.
Generic/static validation, independent pairing/unbound-input checks, G12
directed tests 8/8, combined G9/G10/G12 tests 23/23, and the complete protocol
suite 232/232 pass. The run root has one file and no subdirectory or outcome.
After this audit commit, only the 15 bound base-tape captures are authorized;
references, online execution, analyzer, baselines, confirmation, formal
replay, figures, and claims remain blocked. See
`G12_GLOBAL_READY_ADMISSION_PROTOCOL_MANIFEST_AUDIT.md`.

G12 tape capture and input-binding closure (2026-09-04): all 15 frozen base
tapes were captured in paper order (low, middle, high; D101--D105 within each)
and canonicalized on attempt 1, with zero partial files and no quarantine.
Independent streaming inspection revalidated every tape, receipt, run config,
process observation, completion summary, event count, seed, DAG-order hash,
and file hash. The retained low/middle/high event totals are
9,679/12,366/35,192 (57,237 overall); all 15 tape hashes are unique. The
210-file, 59,776,212-byte canonical tree hash is `21340633...8ec4`, and the
15-record ledger SHA-256 is `26013c2c...6eb7`. The bound manifest has 30
unique C0/G12 run specs, 15 paired tape hashes, and 30 distinct mode-specific
reference identities; its file/document hashes are `2def7e2a...c58b` and
`8357f14b...496b`. No reference or online outcome exists. After this audit
commit, only the exact 30 bound offline-reference builds are authorized;
online execution and all later stages remain blocked. See
`G12_GLOBAL_READY_ADMISSION_TAPE_INPUT_AUDIT.md`.

G12 offline-reference closure (2026-09-04): all 30 declared C0/G12 x
low/middle/high x D101--D105 social-utility references were constructed in
paper/load order and canonicalized on attempt 1, with zero partial files and
no quarantine. Independent streaming verification reconciled every table,
state/assignment sequence, receipt, run config, process observation, Nash
stream, summary, tape hash, seed, load, and operational identity. The 30
unique tables contain 29,395 rows (931--998 each), including 29,393 positive
and 2 retained negative rows. The 420-file, 298,686,107-byte canonical tree
hash is `28f2d35e...1539`; the ledger SHA-256 is `1745e80d...6c92`.
The reference-bound manifest has 30 exact run specs, 15 tape hashes, and 30
reference hashes; its file/document hashes are `4c0140a0...4209` and
`ec5708cc...bb96`. No online result exists. After this audit commit, only
zero-result analyzer and 30-run selection construction are authorized; online
execution and later stages remain blocked. See
`G12_GLOBAL_READY_ADMISSION_OFFLINE_REFERENCE_AUDIT.md`.

G12 analyzer and online-selection freeze (2026-09-04): the fail-closed
analyzer now binds the exact 30-run C0/G12 x low/middle/high x D101--D105
population before any online result directory exists. Its fixed nine-part gate
requires full unique paired QC-valid positive-completion evidence, mean
throughput and QPR superiority at every load, at least 3/5 paired wins, the
0.80 per-seed floors, positive leave-one-seed-out differences, non-inferior
completion with lower latency, positive global-ready deferral in at least 3/5
seeds per load with all six violation counts zero, strict PNE/reference/
dispatch/runtime integrity, and <=1.50 mean policy-wall overhead. Zero-
completion and unfavorable QC-valid runs remain retained. The 29,266-byte
selection has file/document hashes `784f40c3...0a7fd` and
`3e5665dc...d014f`; it embeds the 54,512-byte analyzer hash
`d0b5cbdf...f5268`. Focused and full analysis tests pass 11/11 and 126/126.
After the audit commit, exactly one result-blind manifest-order execution of
all 30 rows is authorized; strong baselines and all later stages remain
blocked. See `G12_GLOBAL_READY_ADMISSION_ANALYZER_SELECTION_AUDIT.md`.

G12 global-ready admission result closure (2026-09-04): all 30 selected
D101--D105 runs canonicalized on attempt 1 with positive completion and
defined QPR; there were no retries, quarantines, omissions, or path repairs.
G12/C0 throughput and QPR mean ratios are 0.9976/1.0014 low,
1.0009/1.0124 middle, and 0.9877/0.9575 high. Only middle load attains the
3/5 paired joint-win threshold; high D101 is the sole per-seed floor failure
at 0.8950/0.5697. Low, middle, and high positive-deferral activation is 2/5,
4/5, and 5/5, with all six structural violation totals zero. The severe high
D101 tail contributes 5,089,902 of 5,132,665 candidate deferral observations,
showing that repeated fixed-`N` admission can accumulate harmful ready backlog.
The candidate therefore fails seven of nine conditions and is closed before
strong baselines. The 450-file online canonical tree hash is
`42a78c03...8ae2`; the full 1,092-file, 390,090,635-byte run root is mirrored
exactly on E with hash `5a41481e...b20a`. Strong baselines, confirmation,
formal replay, figures, and claims remain blocked. Only a read-only successor
diagnosis is authorized. See `G12_GLOBAL_READY_ADMISSION_RESULT_AUDIT.md`.

The permanent root-level G12 closure package contains 28 hash-enumerated
payload files (3,905,923 bytes) plus its inventory receipt. Its payload hash is
`cb5a8c84...38f8`; the complete 29-file tree is 3,910,812 bytes with hash
`bf634ab6...09fe`. See
`closed-experiments/G12_global_ready_admission_development_gate_failed/`.

G13 deferral-persistence diagnosis preregistration (2026-09-04): before
extracting any unreported G12 window-sequence feature, freeze one read-only
analysis over exactly the retained 15 G12/C0 D101--D105 pairs. It reports every
deferral episode, isolated window, adjacent-window persistence, longest streak,
admission ratio, queue context, paired primary outcome, overall/load-specific
Spearman association, and all leave-one-run-out values. A future one-bit,
load-blind `deferral_release_valve` concept is admissible only if isolated-only
and persistent groups each contain at least three runs across two loads,
isolated-only has a higher joint-win rate and positive mean log-throughput and
log-QPR contrasts, and both mean-contrast signs survive every defined
leave-one-run-out check. G13 authorizes no scheduler change or sampling. See
`G13_DEFERRAL_PERSISTENCE_DIAGNOSIS_PREREGISTRATION.md`.

G13 deferral-persistence analyzer closure (2026-09-04): the 27,471-byte
read-only analyzer (`77b42a1e...59fe`) binds the exact closed G12 root,
manifest, selection, report, 62-event ledger, every candidate canonical
inventory, and all 15 same-tape pairs before extracting the frozen sequence
features. It reports all raw rows, average-tie Spearman coefficients,
load-specific coefficients, all leave-one-run-out coefficients, isolated/
persistent groups, and every leave-one-run-out group contrast. Focused tests
pass 9/9 and the complete analysis suite passes 135/135. A pre-feature dry-run
genesis-sentinel mismatch was corrected and all checks rerun before freeze.
After the audit commit, exactly one read-only invocation is authorized; code
changes and all sampling remain blocked. See
`G13_DEFERRAL_PERSISTENCE_DIAGNOSIS_ANALYZER_AUDIT.md`.

G13 deferral-persistence diagnosis result closure (2026-09-04): the sole
read-only invocation retained and revalidated all 15 G12/C0 D101--D105 pairs.
The isolated-only group has 3/3 joint wins across low and middle loads, versus
1/8 across all three loads for persistent deferral. Isolated-minus-persistent
mean log-throughput and log-QPR contrasts are +0.024614 and +0.100563, and
both stay positive in all 15 leave-one-run-out recomputations; their minima
are +0.011890 and +0.032711 after omitting high D101. Persistent-transition
fraction is negatively associated with log throughput/QPR (-0.5827/-0.6838),
with both signs stable under every run omission. All five frozen conditions
pass, authorizing only a separate preregistration for a parameter-free,
load-blind deferral release valve; implementation and sampling remain blocked.
The one-file, 124,669-byte output and exact E-drive mirror share inventory hash
`1015d838...9ef5`; report file/document hashes are `45c45608...f556` and
`42c258f2...77b`. See
`G13_DEFERRAL_PERSISTENCE_DIAGNOSIS_RESULT_AUDIT.md`.

G14 deferral release-valve preregistration (2026-09-04): G13 authorizes one
fresh, parameter-free successor and no result reuse. For the complete global
feasible-ready legacy sequence `A_t`, define overflow `o_t=1[|A_t|>N]` and a
one-bit state `v_0=0`, `v_(t+1)=o_t`. G14 admits the first `N` players only
when current overflow begins with `v_t=0`; otherwise it admits all of `A_t`.
Consequently the first overflow window equals G12, later adjacent overflow
windows equal C0, and actual positive-deferral windows cannot be adjacent.
The rule uses no fitted threshold, load, seed, outcome, frontier, request
cohort, remaining-work key, or baseline expert; Eqs. (1)--(20) and strict
Eq. (15) remain unchanged on the admitted set. Only implementation, directed
tests, compilation, and an implementation audit are currently authorized.
Any later development product is frozen as C0/G14 x low/middle/high x fresh
D106--D110, with all valid rows retained and the same nine-part primary,
robustness, secondary, structural, runtime, and overhead gate. See
`G14_DEFERRAL_RELEASE_VALVE_PREREGISTRATION.md`.

G14 deferral release-valve implementation closure (2026-09-04): source commit
`64d36b7` implements the exact one-bit recurrence `v_(t+1)=1[|A_t|>N]` and
bounds only the first window of each consecutive overflow episode. Later
adjacent overflow windows release the complete global feasible-ready legacy
sequence, making actual positive-deferral windows structurally nonadjacent.
All readiness, feasibility, ordering, prefix, admission-rule, state-transition,
solver-set, and dispatch checks fail closed. Eqs. (1)--(20), strict Eq. (15),
QPR, and offline-reference computation are unchanged on the admitted set.
Operational schema 11, reference-key schema 12, and tag 17 isolate G14 while
the legacy G12 JSON contract remains unchanged. The dedicated 4,885,504-byte
release binary has SHA-256 `ed885d50...873c7`. G14 state tests pass 2/2,
NSESche 54/54, configuration 10/10, G14+G12 contract tests 10/10, complete
protocol 234/234, and complete analysis 135/135. The unfiltered Rust suite
retains only its two known unrelated failures (131/133). No G14 input or
outcome exists. After this audit commit, only a zero-result protocol/manifest
may be constructed. See `G14_DEFERRAL_RELEASE_VALVE_IMPLEMENTATION_AUDIT.md`.

G14 zero-result protocol and manifest closure (2026-09-04): protocol commit
`88e2bf9` freezes exactly C0/G14 x homogeneous 20-node
low/middle/high x fresh D106--D110: 30 run specifications, 15 same-tape
load/seed pairs, and 30 mode-specific offline-reference dependencies. The
one-bit recurrence, operational/reference schemas 11/12, reference tags 1/17,
all-valid-row retention rule, activation conditions, and complete nine-part
performance/robustness/secondary/structural/runtime/overhead gate are
fail-closed and immutable after outcome exposure. Directed G14+G12 tests pass
18/18 and the complete protocol regression passes 242/242 in 952.70 seconds.
The sole 732,824-byte manifest has file SHA-256 `0d0d1983...3219` and embedded
canonical hash `7d0e6e29...b979`; its run root contains one file and no
subdirectories, and every tape/reference binding and all outcomes remain
null. After this audit commit, only the exact 15 base tape captures are
authorized. Offline references, online runs, analyzers, baselines,
confirmation, formal replay, figures, and claims remain blocked. See
`G14_DEFERRAL_RELEASE_VALVE_PROTOCOL_MANIFEST_AUDIT.md`.

G14 tape capture and input-binding closure (2026-09-04): all 15 frozen base
tapes were captured in low, middle, high paper order across D106--D110; every
tape canonicalized on attempt 1, the partial tree has zero files, and no
quarantine exists. Event totals are 9,557 low, 12,806 middle, and 34,632 high
(56,995 total), with all 15 tape hashes unique. Independent inspection
rechecked tape contents, seeds, hashes, DAG order, frames, measured rates,
capture receipts, process/run-config hashes, semantic environments, source
provenance, and the 15-event ledger chain. The 210-file canonical tree is
60,077,953 bytes with inventory hash `69808c45...fd66`; the ledger tip is
`3989ada9...6270`. The bound manifest has 30 unique C0/G14 run specs, 15
same-tape pairs, and 30 distinct mode-specific reference keys; generic,
G14-specific, and static JSON Schema validation pass. No scheduler outcome or
reference exists. After this audit commit, only the exact 30 offline-reference
builds are authorized; online runs and all later stages remain blocked. See
`G14_DEFERRAL_RELEASE_VALVE_TAPE_INPUT_AUDIT.md`.

G14 offline-reference closure (2026-09-04): all 30 declared C0/G14 x
low/middle/high x D106--D110 mode-specific social-utility references were
built in paper order and canonicalized on attempt 1. Independent streaming
verification rechecked each table, 29,414 total unique state rows, numeric
status/value consistency, build/assignment sequence hashes, receipts,
process observations, run configurations, summaries, Nash observations,
build specifications, tape hashes, seeds, loads, and operational identities.
All 29,414 rows are positive and retained; this observed sign distribution
did not alter the fixed bank. The 420-file, 303,952,789-byte canonical tree
has inventory hash `a8f912c0...2d17`; the 30-event ledger tip is
`c2539f3e...5fcb`. The reference-bound manifest passes generic, G14-specific,
and static JSON Schema validation with 15 tape hashes and 30 distinct table
hashes. No online result exists. After this audit commit, only result-free G14
analyzer and exact-selection construction is authorized; online execution and
all later stages remain blocked. See
`G14_DEFERRAL_RELEASE_VALVE_OFFLINE_REFERENCE_AUDIT.md`.

G14 analyzer and online-selection freeze (2026-09-04): committed analyzer
`4da9b19` binds the exact 30-run C0/G14 x low/middle/high x D106--D110
population before any online result directory exists. Its immutable
nine-condition gate retains the shared paired performance, 3/5 win, 0.80
floor, leave-one-seed-out, completion/latency, runtime-identity, and <=1.50
overhead tests, while independently validating G14's one-bit window sequence,
bounded first overflow in every load, persistent release in at least three
runs across two loads, nonadjacent positive deferral, and seven zero violation
contracts. Zero-completion and unfavorable QC-valid runs remain retained. The
29,326-byte selection has file/document hashes `887fc413...68b4` and
`3e750866...9169`; it embeds the 40,341-byte analyzer hash
`13997e4f...efe3`. Focused and complete analysis suites pass 14/14 and
149/149. After this audit commit, exactly one result-blind manifest-order
execution of all 30 rows is authorized; strong baselines and all later stages
remain blocked. See
`G14_DEFERRAL_RELEASE_VALVE_ANALYZER_SELECTION_AUDIT.md`.

G14 deferral release-valve result closure (2026-09-04): the sole authorized
result-blind invocation completed all 30 D106--D110 runs on attempt 1 with no
retry, omission, quarantine, or path repair. All rows have positive completion
and defined QPR. G14/C0 throughput and QPR mean ratios are 1.0193/1.0179 low,
0.9951/1.0270 middle, and 1.1511/1.2712 high; paired joint wins are 2/5, 0/5,
and 3/5. It passes population, 0.80-floor, state-machine activation, and
overhead conditions but fails the other five frozen conditions. The valve
records 836 isolated first-overflow deferrals, 1,069 persistent-overflow full
releases, 9,440 deferred feasible-player observations, no adjacent positive
deferral, and zero structural violation counts. Four C0 rows and one G14 row
contain five retained high-load `inner_iteration_limit` windows, so runtime
integrity also fails. The 450-file online canonical tree hash is
`c3d12f92...d3fb`; the complete 1,092-file, 396,182,667-byte root is mirrored
exactly on E with hash `fdb97063...59b63`. Strong baselines, confirmation,
formal replay, figures, and claims remain blocked; only a separately
preregistered read-only diagnosis is authorized. See
`G14_DEFERRAL_RELEASE_VALVE_RESULT_AUDIT.md`.

The permanent root-level G14 closure package contains 28 hash-enumerated
payload files (3,953,614 bytes) plus its inventory receipt. Its payload hash is
`b86996b3...f4f7`; the complete 29-file tree is 3,959,304 bytes with hash
`e3501702...f5f1`. See
`closed-experiments/G14_deferral_release_valve_development_gate_failed/`.

G15 overflow-magnitude diagnosis preregistration (2026-09-04): before
extracting any unreported G14 overflow-magnitude feature, freeze one read-only
analysis over exactly the retained 15 G14/C0 D106--D110 pairs. It reports every
overflow episode, first-window feasible-ready/node ratio, fixed threshold
classifier in `{1.25,1.5,2,4}`, confusion cell, group contrast, Spearman
coefficient, and leave-one-run-out value. A future load-blind magnitude-gated
valve concept is admissible only if one fixed threshold attains the frozen
classification floor, predicted-positive effects are better in both primary
metrics with sign-stable LOO contrasts, and first-overflow magnitude has
sign-stable positive association with persistence and throughput. G15
authorizes no scheduler change or sampling. See
`G15_OVERFLOW_MAGNITUDE_DIAGNOSIS_PREREGISTRATION.md`.

G15 overflow-magnitude analyzer freeze (2026-09-04): the 31,945-byte
fail-closed analyzer (`72b6762c...6a50`) binds the exact closed G14 root,
manifest, selection, report, 62-event ledger, frozen G14 analyzer, every
candidate canonical inventory, and all 15 same-tape pairs before extracting
the preregistered episode/magnitude features. It reconstructs the one-bit
state machine, evaluates all four fixed classifiers and complete run-level
associations/LOO values, and can authorize only a later preregistration when
all five conditions pass. Focused tests pass 8/8 and the complete analysis
suite passes 157/157. The G15 output parent remains absent. After this audit
commit, exactly one read-only invocation is authorized; implementation and all
sampling remain blocked. See
`G15_OVERFLOW_MAGNITUDE_DIAGNOSIS_ANALYZER_AUDIT.md`.

G15 overflow-magnitude result closure (2026-09-04): the sole read-only
invocation retained and validated all 15 G14/C0 pairs. All five fixed
conditions passed. Threshold 1.25 was uniquely selected with TP/FP/TN/FN
4/2/8/1 and balanced accuracy/sensitivity/specificity 0.80/0.80/0.80. Across
every leave-one-run-out recomputation, balanced accuracy is at least 0.775 and
the positive-minus-negative mean log-throughput and log-QPR contrasts stay
positive. First-overflow p90 magnitude has positive persistence and
throughput associations after every omission. The one-file result was copied
exactly to E; G15 authorizes only G16 preregistration, not implementation or
sampling. See `G15_OVERFLOW_MAGNITUDE_DIAGNOSIS_RESULT_AUDIT.md`.

G16 overflow-magnitude valve preregistration (2026-09-04): before any new
input or result, freeze the sole operational identity
`ready_global_overflow_magnitude_release_valve`. It bounds a first-overflow
window only when the exact widened-integer test `4F>=5N` passes, otherwise
releases the complete feasible-ready order; all adjacent overflow windows are
also fully released through the unchanged one-bit recurrence. Eqs. (1)--(20)
and the game solver remain unchanged. A fresh D111--D115 C0/G16 x three-load
30-run product is permitted only after implementation and zero-result
protocol audits. At this checkpoint source, tests, and a dedicated build are
authorized; manifest construction, inputs, references, online execution,
strong baselines, confirmation, formal replay, figures, and claims remain
blocked. See `G16_OVERFLOW_MAGNITUDE_VALVE_PREREGISTRATION.md`.

G16 overflow-magnitude valve implementation closure (2026-09-04): source
commit `8da3dbd` adds the sole registered identity, exact widened-integer
`4F>=5N` first-overflow gate, unchanged previous-overflow recurrence, five
mutually exclusive modes, independent runtime recomputation, and nine
fail-closed violation counters. Operational schema 12, reference-key schema
13, and tag 18 isolate the candidate; Eqs. (1)--(20), strict Eq. (15), Eq.
(19), social reference, and QPR remain unchanged on the admitted set. The
4,901,888-byte protected release binary has SHA-256 `652d1831...51cfd`.
Verification passes G16 state/equivalence tests 3/3, complete NSESche 57/57,
directed G16+G14+G12 contracts 21/21, analysis 157/157, and protocol 245/245.
No D111--D115 or G16 input/result exists. Only a zero-result protocol/manifest
may now be constructed. See
`G16_OVERFLOW_MAGNITUDE_VALVE_IMPLEMENTATION_AUDIT.md`.

G16 zero-result protocol and manifest closure (2026-09-04): protocol commit
`7e7bdc5` freezes exactly C0/G16 x homogeneous 20-node low/middle/high x
fresh D111--D115: 30 unique run specifications, 15 same-tape load/seed pairs,
and 30 mode-specific offline-reference dependencies. The exact `4F>=5N`
gate, previous-overflow recurrence, operational/reference schemas 12/13,
reference tags 1/18, all-valid-row retention, activation contracts, and
complete performance/robustness/secondary/structural/runtime/overhead gate
are fail-closed and immutable after outcome exposure. Focused, directed,
complete protocol, and complete analysis regressions pass 9/9, 27/27,
251/251, and 157/157. The sole 735,443-byte manifest has file SHA-256
`6a1145c7...7dae` and embedded canonical hash `23aa24bd...cca7`; its run root
contains one file and no subdirectories, and every tape/reference binding and
all outcomes remain null. After this audit commit, only the exact 15 base tape
captures are authorized. Offline references, online runs, analyzers, strong
baselines, confirmation, formal replay, figures, and claims remain blocked.
See `G16_OVERFLOW_MAGNITUDE_VALVE_PROTOCOL_MANIFEST_AUDIT.md`.

G16 tape capture and input-binding closure (2026-09-04): all 15 frozen base
tapes were captured in low, middle, high paper order across D111--D115; every
tape canonicalized on attempt 1, the partial tree has zero files, and no
quarantine exists. Event totals are 9,614 low, 12,588 middle, and 34,680 high
(56,882 total), with all 15 tape hashes unique. Independent streaming
inspection rechecked tape contents, seeds, hashes, DAG order, frames, measured
rates, capture receipts, process observations, run configurations, semantic
environments, source provenance, and the 15-event ledger chain. The 210-file
canonical tree is 59,073,907 bytes with inventory hash `2fbfece1...453e`; the
ledger tip is `01569b3c...de4e`. The bound manifest has 30 unique C0/G16 run
specifications, 15 same-tape pairs, and 30 distinct mode-specific reference
keys; generic, G16-specific, and static JSON Schema validation pass. No
C0/G16 scheduler outcome or reference exists. After this audit commit, only
the exact 30 offline-reference builds are authorized; online runs and all
later stages remain blocked. See
`G16_OVERFLOW_MAGNITUDE_VALVE_TAPE_INPUT_AUDIT.md`.

G16 offline-reference closure (2026-09-04): all 30 declared C0/G16 x
low/middle/high x D111--D115 mode-specific social-utility references were
built in paper order and canonicalized on attempt 1. Independent streaming
verification rechecked 29,467 unique state rows, status/value consistency,
state and assignment sequences, receipts, process observations, run
configurations, summaries, Nash observations, build specifications, tape
hashes, seeds, loads, and operational identities. The complete fixed bank
contains 29,464 positive and three retained negative rows; all three negatives
occur in high D111 and did not alter the bank or gate. The 420-file,
303,921,953-byte canonical tree has inventory hash `f7308394...cf55`; the
30-event ledger tip is `48e52227...e7cc`. The reference-bound manifest passes
generic, G16-specific, and static JSON Schema validation with 15 tape hashes
and 30 distinct table hashes. No online result exists. After this audit
commit, only result-free G16 analyzer and exact-selection construction is
authorized; online execution and all later stages remain blocked. See
`G16_OVERFLOW_MAGNITUDE_VALVE_OFFLINE_REFERENCE_AUDIT.md`.

G16 analyzer and online-selection freeze (2026-09-04): committed analyzer
`563f68d` binds the exact 30-run C0/G16 x low/middle/high x D111--D115
population before any online result directory exists. Its immutable
nine-condition gate retains all QC-valid rows and independently enforces
G16's at-least-one joint win plus four joint nonlosses per load, nonnegative
leave-one-out differences with at least four strict positives, completion and
1.05-latency-ratio bounds, exact `4F>=5N` telemetry, all three required valve
activation modes, one-window deferral, nine zero-violation contracts, strict
runtime integrity, and <=1.50 policy overhead. The 29,484-byte selection has
file/document hashes `0c9eb944...bdd4` and `94fc4f53...1458`; it embeds the
47,946-byte analyzer hash `0c372111...f8e4`. Focused and complete analysis
suites pass 15/15 and 172/172. After this audit commit, exactly one
result-blind manifest-order execution of all 30 rows is authorized; strong
baselines and all later stages remain blocked. See
`G16_OVERFLOW_MAGNITUDE_VALVE_ANALYZER_SELECTION_AUDIT.md`.

G16 overflow-magnitude valve result closure (2026-09-04): the sole
authorized result-blind invocation completed all 30 D111--D115 runs on
attempt 1 with no retry, omission, quarantine, or path repair. All rows have
positive completion and defined QPR. G16/C0 throughput and QPR mean ratios
are 1.0077/1.0081 low, 0.9445/0.9899 middle, and 1.0306/1.1029 high; paired
joint wins/nonlosses are 1/3, 1/3, and 4/4 out of five. G16 passes population,
activation, and overhead conditions but fails the other six frozen
conditions. It records 753 material bounded windows, 499 below-threshold
first-overflow releases, 1,201 persistent releases, 9,105 deferred-player
observations, no adjacent positive deferral, and zero structural violations.
Three retained negative offline references and two retained inner-limit
windows also fail runtime integrity. The 450-file online canonical tree hash
is `42dcc3f4...58c3`; the complete 1,092-file, 395,532,897-byte root is
mirrored exactly on E with hash `28a7d5a1...4c9f`. Strong baselines,
confirmation, formal replay, figures, and claims remain blocked; only a
separately preregistered read-only diagnosis is authorized. See
`G16_OVERFLOW_MAGNITUDE_VALVE_RESULT_AUDIT.md`.

The permanent root-level G16 closure package contains 28 hash-enumerated
payload files (4,018,715 bytes) plus its inventory receipt. Its payload hash
is `eae91d1f...fc5f`; the complete 29-file tree is 4,024,427 bytes with hash
`bdcf1e85...acf6`. See
`closed-experiments/G16_overflow_magnitude_valve_development_gate_failed/`.

G17 threshold-safety diagnosis preregistration (2026-09-04): before
extracting any unreported G16 magnitude, episode, queue, or dose feature,
freeze one read-only analysis over exactly the retained 15 G16/C0 D111--D115
pairs. It evaluates fixed thresholds `{1.25,1.5,2,4}`, complete
joint-nonloss classifiers, all LOO recomputations, and an explicitly
optimistic G16-or-C0 screening envelope. A stricter threshold may be proposed
only if all six integrity, classifier, dual-effect, all-load performance,
per-seed/LOO, and robustness conditions pass. The envelope is declared
noncausal and cannot become a paper result. G17 authorizes no scheduler change
or sampling. See `G17_THRESHOLD_SAFETY_DIAGNOSIS_PREREGISTRATION.md`.

G17 threshold-safety diagnosis closure (2026-09-04): the result-blind
analyzer was frozen at commit `3177622` and invoked once over the exact closed
G16 root. All 15 pairs passed activation, identity, and zero-violation
integrity, but the remaining five conditions failed. The preregistered score
selected `h=4`, which predicts zero safe runs and merely reproduces C0; the
nondegenerate `h=1.5` alternative has BA/sensitivity/specificity
0.45/0.10/0.80, covers only two low/high runs, and misses the all-load gates.
The report is 2,204,444 bytes with SHA-256 `01f60135...b0464` and document hash
`eef43d9f...356e`. The fixed-threshold valve family is closed; G17 authorizes
no implementation, sampling, confirmation, or paper claim. See
`G17_THRESHOLD_SAFETY_DIAGNOSIS_RESULT_AUDIT.md`.

G17 permanent closure package (2026-09-04):
`closed-experiments/G17_threshold_safety_diagnosis_fixed_family_closed`
contains the preregistration, analyzer-freeze audit, result audit, one-shot
report, and exact analyzer/test sources. Its seven-file payload is 2,281,274
bytes with inventory hash `0de30928...f8c46`; including the frozen inventory
receipt, the complete eight-file tree is 2,282,967 bytes with hash
`2df04a2a...2918`.

G18 soft-cap release-valve preregistration (2026-09-05): the next mechanism
changes action intensity, not the fixed-threshold classifier closed by G17.
On a material first-overflow window it admits the unchanged feasible-ready
prefix of length `ceil(5N/4)`; at/below cap and on every adjacent overflow it
releases all players. The 125% cap is fixed before implementation, with no
alternative cap screen. Development is exactly C0/G18 x low/middle/high x
D116--D120 under nine all-pass gates. Only implementation, directed tests,
release build, and a source/binary audit are currently authorized; tapes,
references, online runs, strong baselines, confirmation, and paper claims
remain blocked. See
`G18_OVERFLOW_SOFT_CAP_RELEASE_VALVE_PREREGISTRATION.md`.

G18 soft-cap release-valve implementation freeze (2026-09-05): source commit
`f3a1e09` adds only the preregistered load-blind
`ready_global_overflow_soft_cap_release_valve`, exact checked
`C=ceil(5N/4)`, one-bit first-overflow state, five-mode telemetry, independent
runtime reconstruction, and fail-closed contract validation. The dedicated
4,918,272-byte release binary has SHA-256 `aaa0980c...af713` and its 4,065-file
target is now protected. G18 selector tests, all 59 NSESche tests, all 10
config tests, 3 directed runtime-contract tests, 181 analysis tests, and 254
protocol tests pass. No D116--D120 input, reference, online run, or metric
existed at freeze. Only a separately audited zero-result G18 protocol and
manifest are authorized next; all result-bearing stages remain blocked. See
`G18_OVERFLOW_SOFT_CAP_RELEASE_VALVE_IMPLEMENTATION_AUDIT.md`.
