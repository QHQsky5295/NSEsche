# Active Experiment Workspace

The stable repository worktree is
`C:\Users\99349\Desktop\serverless_sim_game`, on branch
`agent/reviewer-experiments`. Its NSESche source is intentionally not modified
by the current low-load tuning series, preserving the earlier version for
rollback.

The active low-load algorithm worktree is
`C:\Users\99349\Desktop\serverless_sim_game_e1_closure`, on branch
`agent/nse-e1-main-closure`. All V155--V189 plans, NSESche Rust changes,
training harnesses and result receipts are developed here. The modified
algorithm source is
`C:\Users\99349\Desktop\serverless_sim_game_e1_closure\serverless_sim\src\sche\sche_nash.rs`.

At the V189 result checkpoint, the active source SHA-256 is
`6ebe21d6afea6e648c79ab3a4231a723e0338c1e84c34ef04ac9fd1859ab4181`;
the stable worktree source SHA-256 is
`bd106e4646ff6d56ae8dceceb731945667034dc46eb87aaf58da368e19f75814`.
V189's algorithm change is commit `549dbe4`, and its sealed training harness is
commit `0ed605f`. The V189 result closes the current native
earliest-executable-finish axis without authorizing another online run.

The former `serverless_sim_game_nse_dev` directory was neither of these Git
worktrees. It was a redundant, partially restored development copy and has
been archived and removed as documented in
[STORAGE_CLEANUP.20260901-nse-dev.md](STORAGE_CLEANUP.20260901-nse-dev.md).
