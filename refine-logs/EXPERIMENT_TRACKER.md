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
| G1-QUAL | Independent corrected-runtime E1 qualification/main result | EXECUTION AUTHORIZED / PREREGISTRATION PENDING | 0/1200 | NSESche mean throughput and mean QPR are first in all six cells with complete QC | Q61--Q80 is not yet preregistered or captured; it must compare the same frozen `ready_order` against all nine baselines, beginning with homogeneous-low, before later cells can open |
| M1-PILOT | Workload/SLA/reference pilot | COMPLETE | 9 tape captures + 24 SLA runs | 1.9k/2.6k/7.0k tapes and three-seed SLA frozen | `M1_PILOT_AUDIT.md`; frozen SLA SHA `496f7053...cf3f2` |
| M1-QUAL | Six-cell method qualification | FAILED GATE / DIAGNOSIS COMPLETE | 90/90 screen; 1200/1200 qualification; 30/30 diagnostic canonical | Development throughput/QPR gates pass | `ready_order` failed 6/6 cells; decision-neutral audit passed 30 pairs/30,000 windows; objective conflict supported, supply limitation not supported; local family exhausted; see `M1_MECHANISM_DIAGNOSIS_RESULT_AUDIT.md`; no M2 run authorized |
| M1-GUARD | Fresh-bank completion-guard redesign | FAMILY REJECTED / DIAGNOSIS COMPLETE | 90/90 screen; 0/1200 forbidden qualification | Guard candidate wins global screen, then six-cell dual-first qualification | `ready_order` won frozen maximin rule; static finish proxy caused within-window concentration and seed-level collapse; see `M1_COMPLETION_GUARD_RESULT_AUDIT.md`; no M2 run authorized |
| M1-DYNAMIC | Fresh-bank dynamic-contention guard | SCREEN COMPLETE / TERMINAL FAILURE | 90/90 screen; 0/1200 forbidden qualification | Dynamic guard wins global screen, then six-cell dual-first qualification | Frozen screen could not rank three zero-completion rows; later G0 audit proved a common cold-start transition-starvation defect, so D41--D45 remains historical diagnosis and cannot select a corrected-runtime candidate; see `M1_DYNAMIC_CONTENTION_GUARD_RESULT_AUDIT.md`, `M1_DYNAMIC_CONTENTION_TERMINAL_DIAGNOSIS.md`, and `G0_COLD_START_TRANSITION_SEMANTICS_AUDIT.md`; no M2 run authorized |
| M2-HOM-LOW | Homogeneous-20 low | TODO | 200 | NSESche mean throughput and QPR highest | pending |
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
