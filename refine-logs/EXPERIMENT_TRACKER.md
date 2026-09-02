# NSESche TSC Resubmission Experiment Tracker

| ID | Paper section | Status | Runs | Paper-ready gate | Evidence |
|---|---|---|---:|---|---|
| M0-WORKTREE | Revision workspace | COMPLETE | 0 | Separate rollback-safe worktree | `agent/tsc-resubmit-final` |
| M0-PROTOCOL | Goal, plan and tracker freeze | COMPLETE | 0 | Files committed with hashes | commits `251633f`, `7e239df` |
| M0-STORAGE | Redundant `nse_dev` archive/cleanup | COMPLETE | 0 | Verified archive and freed C-drive copy | `STORAGE_CLEANUP.20260902-recreated-nse-dev.md` |
| M0-METHOD | Formula-consistent implementation audit | COMPLETE | 0 | Method boundary tests pass | `M0_METHOD_AUDIT.md`; NSESche 25/25 pass |
| M0-PIPELINE | Manifest, metrics and QC audit | COMPLETE | 0 | Required fields and invariants pass | `M0_PIPELINE_AUDIT.md`; current regression protocol 152/152, analysis 48/48 |
| M1-PILOT | Workload/SLA/reference pilot | COMPLETE | 9 tape captures + 24 SLA runs | 1.9k/2.6k/7.0k tapes and three-seed SLA frozen | `M1_PILOT_AUDIT.md`; frozen SLA SHA `496f7053...cf3f2` |
| M1-QUAL | Six-cell method qualification | FAILED GATE / DIAGNOSIS COMPLETE | 90/90 screen; 1200/1200 qualification; 30/30 diagnostic canonical | Development throughput/QPR gates pass | `ready_order` failed 6/6 cells; decision-neutral audit passed 30 pairs/30,000 windows; objective conflict supported, supply limitation not supported; local family exhausted; see `M1_MECHANISM_DIAGNOSIS_RESULT_AUDIT.md`; no M2 run authorized |
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
