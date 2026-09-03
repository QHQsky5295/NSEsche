# M0 final storage cleanup

Date: 2026-09-03 (Asia/Shanghai)

Status: complete; current G1 evidence retained; closed development material
archived to `E:\NSEsche_experiment_archives`

## Redundant historical development copy

`C:\Users\99349\Desktop\serverless_sim_game_nse_dev` was not a Git
worktree.  It was a restored copy of the earlier isolated NSESche development
tree.  A comparison against the 2026-09-02 archive found 332 added files and
4,849 missing files, so the directory was not deleted as a presumed duplicate.
Its current non-build state was archived again and fully verified first.

- Archived files: 61,641.
- Archived source bytes: 10,193,340,713 (9.493 GiB).
- ZIP bytes: 738,302,026.
- ZIP SHA-256:
  `ca76a42833b8962eae9ecafa3db28692bf6cc87a748e12f169b92498f44fd0a7`.
- Inventory hash:
  `8994830029fbce5273f3fed2a28c0974b29edb423a8c1d56d9f8280da4e49291`.
- Final receipt hash:
  `1c0192662035f2386825d2efa81e992808ed43d0504601eeaf7a187fbbd95f7f`.
- ZIP CRC, archive membership, every decompressed member hash, and the source
  tree re-hash immediately before deletion: passed.
- Archive:
  `E:\NSEsche_experiment_archives\nse_dev_final_cleanup_20260903\nse_dev_final_nonbuild_20260903.zip`.
- Receipt:
  `E:\NSEsche_experiment_archives\nse_dev_final_cleanup_20260903\nse_dev_final_nonbuild_20260903.receipt.json`.
- Completion-context document SHA-256:
  `9c376eddc881a96390513d3959db36521e29d7cf58b177bbd64d8c37d9d9dd31`.

The exact Desktop source was removed only after those checks.  It is
recoverable from the ZIP.  The active revision worktree and the rollback
worktrees were not modified by this deletion.

## Closed development runs and build caches

Six completed, non-paper M1/G0 run roots were archived as one immutable ZIP:
the failed M1 qualification, completion-guard screen, dynamic-contention
screen, pilot, mechanism diagnosis, and G0 transition diagnostic.

- Archived files: 47,126.
- Archived source bytes: 7,132,501,995 (6.643 GiB).
- ZIP bytes: 1,340,937,221.
- ZIP SHA-256:
  `e8923faf18091d56453395c663a2decf2d3d798480fd94f0791eb6e5da8778fe`.
- Receipt document SHA-256:
  `08ab0052a1f68402c52bcceaec46052869edda35c91f807e0ca5705aae091060`.
- ZIP CRC, every decompressed member hash, and the source-tree re-hash before
  deletion: passed.
- Archive:
  `E:\NSEsche_experiment_archives\revision_closed_development_20260903\revision_closed_development_runs_20260903.zip`.

Six superseded Rust build trees totaling 4.255 GiB were deleted as
reproducible caches.  Their exact `serverless_sim.exe` binaries were copied to
`E:\NSEsche_experiment_archives\superseded_dev_binaries_20260903` first.  The
binary archive receipt file SHA-256 is
`368634cd44ebcb003118025d25d2076bba94cb5dbdfe3ee526e8d1b1c5778dc5`.

## Retained current experiment block

Only the current G1 corrected-runtime block remains under the active
revision's large-output locations:

- `runs\tscv1_g1_corrected_98f822c_20260903` (development selection evidence);
- `serverless_sim\target_g1_corrected_runtime_98f822c` (the selected runtime,
  executable SHA-256
  `7f1d1ad88e502cf49d59deb8886545c110bf488506941f778b6d184fdaf206a4`).

Observed C-drive free space increased from 311.94 GiB at the start of this
cleanup to 331.55 GiB after all removals.  The logical sizes above exceed the
observed free-space delta because Windows reports allocated filesystem space
differently from summed logical file lengths.

