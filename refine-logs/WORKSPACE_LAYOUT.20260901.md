# Active Experiment Workspace

The stable repository worktree is
`C:\Users\99349\Desktop\serverless_sim_game`, on branch
`agent/reviewer-experiments`. Its NSESche source is intentionally not modified
by the current low-load tuning series, preserving the earlier version for
rollback.

The active low-load algorithm worktree is
`C:\Users\99349\Desktop\serverless_sim_game_e1_closure`, on branch
`agent/nse-e1-main-closure`. All V155--V188 plans, NSESche Rust changes,
training harnesses and result receipts are developed here. The modified
algorithm source is
`C:\Users\99349\Desktop\serverless_sim_game_e1_closure\serverless_sim\src\sche\sche_nash.rs`.

At the V187 result checkpoint, the active source SHA-256 is
`0c6d492d22c083f84ef2e4cae6fb703854f544844d48162ea2ebb8cfa83b63a7`;
the stable worktree source SHA-256 is
`bd106e4646ff6d56ae8dceceb731945667034dc46eb87aaf58da368e19f75814`.
V187's algorithm change is commit `9db6f75`, which modifies only
`serverless_sim/src/sche/sche_nash.rs` (200 insertions, 2 deletions).

The former `serverless_sim_game_nse_dev` directory was neither of these Git
worktrees. It was a redundant, partially restored development copy and has
been archived and removed as documented in
[STORAGE_CLEANUP.20260901-nse-dev.md](STORAGE_CLEANUP.20260901-nse-dev.md).
