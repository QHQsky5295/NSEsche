# E1 Homogeneous-20 Low V161 Plan

This file is the human-readable mirror of the preregistered V161 JSON plan,
committed before implementation as `721e0a0`. The immutable source is
`scripts/reviewer_experiments/protocol/nse_e1_homogeneous_jit_parent_tail_slack_short_work_terminal_pipeline_queue8_low_diagnostic_plan_v161.json`
(SHA-256 `ca59b7819d132b6dbccc60a28784905fd33240d3ca10e7e6623490a9c312898f`).

V161 tested one causal change to V159: a nonterminal short-work child could be
placed only when every unfinished direct parent was active, had consecutive
task-level `left_calc` observations with positive realized service, and had a
predicted remaining time no greater than the child's immutable cold-start
time. The frozen work threshold (5.5), queue threshold (strictly below 8),
SRPT order, scoring router, solver, HPA, tapes, references and metrics were
unchanged.

Only E09, E18 and E20 were authorized, in that order. The unchanged complete
E01--E20 gate reused V155 for the other seventeen seeds and all 180 frozen
baseline rows. The remaining seventeen V161 seeds could run only if throughput,
both QPR conventions, paired counts, three-seed sums and the result-blind
mechanism audit all passed. They did not, so V161 is retired.

